#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

DETECTORS = [
    "dead_unused_code",
    "duplication",
    "complexity_size",
    "dependency_coupling",
    "naming_consistency",
    "debug_logging_leftovers",
]

TIER_WEIGHT = {"T1": 20, "T2": 10, "T3": 4, "T4": 1}
SEVERITY_MULTIPLIER = {"high": 1.0, "med": 0.6, "low": 0.3}
CONFIDENCE_MULTIPLIER = {"high": 1.0, "med": 0.75, "low": 0.5}

SEVERITY_RANK = {"high": 3, "med": 2, "low": 1}
CONFIDENCE_RANK = {"high": 3, "med": 2, "low": 1}
TIER_RANK = {"T1": 4, "T2": 3, "T3": 2, "T4": 1}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def list_json_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*.json") if p.is_file())
    raise SystemExit(f"Path does not exist: {target}")


def load_findings(paths: list[Path]) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
            records = payload["findings"]
        elif isinstance(payload, list):
            records = payload
        else:
            continue
        for record in records:
            if isinstance(record, dict):
                record = deepcopy(record)
                record["_source"] = str(path)
                loaded.append(record)
    return loaded


def stronger(current: str, candidate: str, rank: dict[str, int]) -> str:
    if rank.get(candidate, 0) > rank.get(current, 0):
        return candidate
    return current


def merge_evidence(old: str, new: str) -> str:
    parts = []
    seen = set()
    for blob in [old, new]:
        for part in [p.strip() for p in blob.split(" || ")]:
            if part and part not in seen:
                parts.append(part)
                seen.add(part)
    return " || ".join(parts)


def normalized_fingerprint(record: dict[str, Any]) -> str:
    detector = str(record.get("detector", "")).strip()
    file_path = str(record.get("file", "")).strip()
    summary = normalize_text(str(record.get("summary", "")))
    return f"{detector}|{file_path}|{summary}"


def initial_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record.get("id", "")).strip() or "pending",
        "tier": str(record.get("tier", "T4")).strip(),
        "detector": str(record.get("detector", "")).strip(),
        "severity": str(record.get("severity", "low")).strip(),
        "file": str(record.get("file", "")).strip(),
        "line": record.get("line"),
        "summary": str(record.get("summary", "")).strip(),
        "evidence": str(record.get("evidence", "")).strip(),
        "recommended_fix": str(record.get("recommended_fix", "")).strip(),
        "confidence": str(record.get("confidence", "low")).strip(),
        "status": str(record.get("status", "open")).strip(),
        "conflict_note": str(record.get("conflict_note", "")).strip(),
        "needs_validation": bool(record.get("needs_validation", False)),
        "_sources": [str(record.get("_source", ""))],
    }


def merge_record(existing: dict[str, Any], candidate: dict[str, Any]) -> None:
    conflicts = []

    for field, rank in [
        ("tier", TIER_RANK),
        ("severity", SEVERITY_RANK),
        ("confidence", CONFIDENCE_RANK),
    ]:
        old_value = existing[field]
        new_value = str(candidate.get(field, old_value)).strip()
        if new_value != old_value:
            conflicts.append(f"{field}: {old_value} vs {new_value}")
        existing[field] = stronger(old_value, new_value, rank)

    new_line = candidate.get("line")
    old_line = existing.get("line")
    if isinstance(new_line, int) and new_line > 0:
        if old_line is None or (isinstance(old_line, int) and new_line < old_line):
            existing["line"] = new_line

    new_summary = str(candidate.get("summary", "")).strip()
    if len(new_summary) > len(existing["summary"]):
        existing["summary"] = new_summary

    existing["evidence"] = merge_evidence(
        existing.get("evidence", ""), str(candidate.get("evidence", "")).strip()
    )

    new_fix = str(candidate.get("recommended_fix", "")).strip()
    old_fix = existing.get("recommended_fix", "")
    if new_fix and new_fix != old_fix:
        conflicts.append("recommended_fix differs")
        if len(new_fix) > len(old_fix):
            existing["recommended_fix"] = new_fix

    new_status = str(candidate.get("status", "open")).strip()
    if new_status != existing.get("status", "open"):
        conflicts.append(f"status: {existing.get('status')} vs {new_status}")
        # Keep unresolved status if any source still marks open.
        existing["status"] = "open" if "open" in {existing["status"], new_status} else existing["status"]

    new_needs_validation = bool(candidate.get("needs_validation", False))
    if new_needs_validation:
        existing["needs_validation"] = True

    if conflicts:
        existing["needs_validation"] = True
        merged_note = existing.get("conflict_note", "")
        detail = "; ".join(sorted(set(conflicts)))
        existing["conflict_note"] = (
            f"{merged_note}; {detail}".strip("; ").strip()
            if merged_note
            else detail
        )

    existing["_sources"].append(str(candidate.get("_source", "")))


def penalty(record: dict[str, Any]) -> float:
    tier = record.get("tier", "T4")
    severity = record.get("severity", "low")
    confidence = record.get("confidence", "low")
    return (
        TIER_WEIGHT.get(tier, 1)
        * SEVERITY_MULTIPLIER.get(severity, 0.3)
        * CONFIDENCE_MULTIPLIER.get(confidence, 0.5)
    )


def priority_sort_key(record: dict[str, Any]) -> tuple:
    return (
        -TIER_WEIGHT.get(record.get("tier", "T4"), 1),
        -SEVERITY_RANK.get(record.get("severity", "low"), 1),
        -CONFIDENCE_RANK.get(record.get("confidence", "low"), 1),
        -penalty(record),
        record.get("file", ""),
        record.get("line") if isinstance(record.get("line"), int) else 10**9,
    )


def score(records: list[dict[str, Any]]) -> dict[str, float]:
    strict_penalty = sum(penalty(r) for r in records)
    open_penalty = sum(penalty(r) for r in records if r.get("status", "open") == "open")
    wontfix_penalty = sum(
        penalty(r) for r in records if r.get("status", "open") == "wontfix"
    )
    strict_score = max(0.0, min(100.0, 100.0 - strict_penalty))
    overall_score = max(
        0.0, min(100.0, 100.0 - (open_penalty + 0.5 * wontfix_penalty))
    )
    return {
        "overall_score": round(overall_score, 2),
        "strict_score": round(strict_score, 2),
    }


def breakdown(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_tier: dict[str, dict[str, float]] = {}
    for tier in ["T1", "T2", "T3", "T4"]:
        tier_records = [r for r in records if r.get("tier") == tier]
        by_tier[tier] = {
            "count": len(tier_records),
            "penalty": round(sum(penalty(r) for r in tier_records), 2),
        }

    by_detector: dict[str, dict[str, float]] = {}
    detector_counts = {}
    for detector in DETECTORS:
        detector_records = [r for r in records if r.get("detector") == detector]
        detector_counts[detector] = len(detector_records)
        by_detector[detector] = {
            "count": len(detector_records),
            "penalty": round(sum(penalty(r) for r in detector_records), 2),
        }

    zero = [d for d, count in detector_counts.items() if count == 0]
    return {
        "by_tier": by_tier,
        "by_detector": by_detector,
        "detectors_with_zero_findings": zero,
    }


def remediation_plan(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    quick_wins: list[str] = []
    refactors: list[str] = []
    for record in records:
        item = f"{record['id']}: {record['summary']}"
        detector = record.get("detector")
        tier = record.get("tier")
        if tier in {"T3", "T4"} or detector in {
            "naming_consistency",
            "debug_logging_leftovers",
        }:
            quick_wins.append(item)
        else:
            refactors.append(item)
    return {
        "quick_wins": quick_wins,
        "refactors": refactors,
    }


def resolve_simulation(top_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    commands = []
    for record in top_records:
        fid = record["id"]
        commands.append(
            {
                "id": fid,
                "commands": [
                    f"resolve fixed {fid}",
                    f'resolve wontfix {fid} --note "risk accepted or intentional pattern"',
                    f'resolve false_positive {fid} --note "heuristic mismatch, verify manually"',
                ],
            }
        )
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge deduplicated findings and compute scores."
    )
    parser.add_argument(
        "path", help="Path to findings JSON file or directory of JSON files."
    )
    parser.add_argument("--out", help="Write merged report JSON to file.")
    args = parser.parse_args()

    files = list_json_files(Path(args.path))
    if not files:
        raise SystemExit("No JSON files found.")

    loaded = load_findings(files)
    buckets: dict[str, dict[str, Any]] = {}
    for record in loaded:
        key = normalized_fingerprint(record)
        if key not in buckets:
            buckets[key] = initial_record(record)
        else:
            merge_record(buckets[key], record)

    merged = list(buckets.values())
    merged.sort(key=priority_sort_key)
    for idx, record in enumerate(merged, start=1):
        record["id"] = f"F{idx:03d}"

    top_open = [r for r in merged if r.get("status") == "open"][:10]
    report = {
        "total_findings": len(merged),
        "findings": merged,
        "scores": score(merged),
        "breakdown": breakdown(merged),
        "next": [r["id"] for r in top_open],
        "plan": remediation_plan(top_open),
        "resolve_simulation": resolve_simulation(top_open),
    }

    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
