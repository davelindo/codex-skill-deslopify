#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GROUPS = [
    ("G1_structural", ["dead_unused_code", "duplication"]),
    ("G2_architecture", ["complexity_size", "dependency_coupling"]),
    ("G3_hygiene", ["naming_consistency", "debug_logging_leftovers"]),
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "scope"


def load_profile(path: Path) -> dict[str, Any]:
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in profile: {exc}") from exc

    if not isinstance(profile, dict):
        raise SystemExit("Profile must be a JSON object.")
    return profile


def module_scopes(profile: dict[str, Any]) -> list[dict[str, Any]]:
    if profile.get("large_repo"):
        splits = profile.get("module_splits", [])
        if not isinstance(splits, list) or not splits:
            raise SystemExit("Profile is missing non-empty module_splits.")
        return splits

    return [
        {
            "module": "__repo__",
            "scope_globs": ["**/*"],
            "file_count": int(profile.get("source_file_count", 0)),
            "loc": int(profile.get("source_loc", 0)),
        }
    ]


def build_plan(profile: dict[str, Any], run_id: str) -> dict[str, Any]:
    scopes = module_scopes(profile)
    tasks: list[dict[str, Any]] = []
    task_index = 0

    for group_name, detectors in GROUPS:
        for detector in detectors:
            for scope in scopes:
                task_index += 1
                module_name = str(scope.get("module", "__unknown__"))
                task_id = (
                    f"{slugify(group_name)}-{slugify(detector)}-"
                    f"{slugify(module_name)}-{task_index:03d}"
                )
                output_path = f"runs/{run_id}/findings/{task_id}.json"
                tasks.append(
                    {
                        "task_id": task_id,
                        "group": group_name,
                        "detector": detector,
                        "module": module_name,
                        "scope_globs": list(scope.get("scope_globs", ["**/*"])),
                        "file_count_hint": int(scope.get("file_count", 0)),
                        "loc_hint": int(scope.get("loc", 0)),
                        "output_path": output_path,
                        "prompt_contract": (
                            "Analyze only assigned scope. Do not edit files. "
                            "Return JSON array of findings with required schema. "
                            "Return [] if no findings."
                        ),
                    }
                )

    return {
        "run_id": run_id,
        "repo_root": profile.get("repo_root"),
        "large_repo": bool(profile.get("large_repo")),
        "execution": {
            "group_order": [group for group, _ in GROUPS],
            "parallel_within_group": True,
            "sequential_between_groups": True,
            "non_clobbering_rules": [
                "No duplicated detector+module tasks.",
                "Each task writes to its own output_path.",
                "Module scopes remain disjoint for each detector.",
                "Coordinator reads findings only; no output overwrite.",
            ],
        },
        "tasks": tasks,
        "coordinator": {
            "input_glob": f"runs/{run_id}/findings/*.json",
            "validator_command": f"python3 scripts/validate_findings.py runs/{run_id}/findings",
            "merge_command": (
                f"python3 scripts/merge_and_score.py runs/{run_id}/findings "
                f"--out runs/{run_id}/report.json"
            ),
            "dedup_key": "detector|file|normalized(summary)",
            "conflict_policy": "retain finding and mark needs_validation",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate grouped, non-clobbering subagent task plan."
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Path to JSON profile from scripts/repo_profile.py",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier used for output paths.",
    )
    parser.add_argument("--out", help="Write JSON output to file.")
    args = parser.parse_args()

    profile = load_profile(Path(args.profile))
    plan = build_plan(profile=profile, run_id=args.run_id)
    payload = json.dumps(plan, indent=2, sort_keys=True)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
