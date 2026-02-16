#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = [
    "id",
    "tier",
    "detector",
    "severity",
    "file",
    "line",
    "summary",
    "evidence",
    "recommended_fix",
    "confidence",
    "status",
    "conflict_note",
    "needs_validation",
]

VALID_TIERS = {"T1", "T2", "T3", "T4"}
VALID_DETECTORS = {
    "dead_unused_code",
    "duplication",
    "complexity_size",
    "dependency_coupling",
    "naming_consistency",
    "debug_logging_leftovers",
}
VALID_SEVERITY = {"low", "med", "high"}
VALID_CONFIDENCE = {"low", "med", "high"}
VALID_STATUS = {"open", "fixed", "wontfix", "false_positive"}


def list_json_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*.json") if p.is_file())
    raise SystemExit(f"Path does not exist: {target}")


def validate_record(record: Any, src: Path, index: int) -> list[str]:
    errs: list[str] = []
    if not isinstance(record, dict):
        return [f"{src}: finding[{index}] is not an object"]

    for field in REQUIRED_FIELDS:
        if field not in record:
            errs.append(f"{src}: finding[{index}] missing field '{field}'")

    if errs:
        return errs

    if record["tier"] not in VALID_TIERS:
        errs.append(f"{src}: finding[{index}] invalid tier '{record['tier']}'")
    if record["detector"] not in VALID_DETECTORS:
        errs.append(
            f"{src}: finding[{index}] invalid detector '{record['detector']}'"
        )
    if record["severity"] not in VALID_SEVERITY:
        errs.append(
            f"{src}: finding[{index}] invalid severity '{record['severity']}'"
        )
    if record["confidence"] not in VALID_CONFIDENCE:
        errs.append(
            f"{src}: finding[{index}] invalid confidence '{record['confidence']}'"
        )
    if record["status"] not in VALID_STATUS:
        errs.append(f"{src}: finding[{index}] invalid status '{record['status']}'")

    line = record["line"]
    if line is not None and (not isinstance(line, int) or line < 1):
        errs.append(f"{src}: finding[{index}] line must be null or int >= 1")

    for key in ["id", "file", "summary", "evidence", "recommended_fix"]:
        if not isinstance(record[key], str) or not record[key].strip():
            errs.append(f"{src}: finding[{index}] '{key}' must be non-empty string")

    if not isinstance(record["needs_validation"], bool):
        errs.append(
            f"{src}: finding[{index}] needs_validation must be true or false"
        )

    if not isinstance(record["conflict_note"], str):
        errs.append(f"{src}: finding[{index}] conflict_note must be a string")

    if record["needs_validation"] and not record["conflict_note"].strip():
        errs.append(
            f"{src}: finding[{index}] needs conflict_note when needs_validation=true"
        )

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate subagent findings JSON schema."
    )
    parser.add_argument(
        "path", help="Path to findings JSON file or directory of JSON files."
    )
    args = parser.parse_args()

    json_files = list_json_files(Path(args.path))
    if not json_files:
        raise SystemExit("No JSON files found to validate.")

    errors: list[str] = []
    total_findings = 0
    for json_file in json_files:
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{json_file}: invalid JSON ({exc})")
            continue

        if not isinstance(payload, list):
            errors.append(f"{json_file}: root JSON value must be an array")
            continue

        total_findings += len(payload)
        for idx, record in enumerate(payload):
            errors.extend(validate_record(record, json_file, idx))

    result = {
        "files_checked": len(json_files),
        "findings_checked": total_findings,
        "errors": errors,
        "valid": not errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
