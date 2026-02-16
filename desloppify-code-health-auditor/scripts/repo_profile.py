#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    "vendor",
    "target",
    "out",
    "DerivedData",
}

SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".m",
    ".mm",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".tsx",
    ".ts",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

SOURCE_FILENAMES = {
    "Dockerfile",
    "Makefile",
    "Rakefile",
    "BUILD",
    "BUILD.bazel",
    "WORKSPACE",
}

DETECTORS = [
    "dead_unused_code",
    "duplication",
    "complexity_size",
    "dependency_coupling",
    "naming_consistency",
    "debug_logging_leftovers",
]

LARGE_REPO_FILE_THRESHOLD = 500
LARGE_REPO_LOC_THRESHOLD = 100_000


def is_source_file(path: Path) -> bool:
    if path.name in SOURCE_FILENAMES:
        return True
    return path.suffix.lower() in SOURCE_EXTENSIONS


def source_line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def module_name_for(rel_path: Path, depth: int) -> str:
    if len(rel_path.parts) <= 1:
        return "__root__"
    module_depth = min(depth, len(rel_path.parts) - 1)
    return "/".join(rel_path.parts[:module_depth])


def scope_globs_for(module_name: str) -> list[str]:
    if module_name == "__root__":
        return ["*"]
    if module_name == "__repo__":
        return ["**/*"]
    return [f"{module_name}/**"]


def iter_source_files(repo_root: Path):
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in IGNORE_DIRS and not d.startswith(".")
        ]
        for filename in filenames:
            path = Path(dirpath) / filename
            if is_source_file(path):
                yield path


def build_module_splits(
    module_stats: dict[str, dict[str, int]], max_modules: int
) -> list[dict[str, object]]:
    ordered = sorted(
        module_stats.items(),
        key=lambda kv: (kv[1]["loc"], kv[1]["file_count"], kv[0]),
        reverse=True,
    )
    if not ordered:
        return [
            {
                "module": "__repo__",
                "file_count": 0,
                "loc": 0,
                "scope_globs": ["**/*"],
            }
        ]

    if max_modules > 1 and len(ordered) > max_modules:
        keep = ordered[: max_modules - 1]
        overflow = ordered[max_modules - 1 :]
        overflow_file_count = sum(item[1]["file_count"] for item in overflow)
        overflow_loc = sum(item[1]["loc"] for item in overflow)
        overflow_globs = []
        for module_name, _ in overflow:
            overflow_globs.extend(scope_globs_for(module_name))
        ordered = keep + [
            (
                "__small_modules__",
                {
                    "file_count": overflow_file_count,
                    "loc": overflow_loc,
                    "scope_globs": sorted(set(overflow_globs)),
                },
            )
        ]

    splits = []
    for module_name, stats in ordered:
        split = {
            "module": module_name,
            "file_count": int(stats["file_count"]),
            "loc": int(stats["loc"]),
        }
        if "scope_globs" in stats:
            split["scope_globs"] = list(stats["scope_globs"])
        else:
            split["scope_globs"] = scope_globs_for(module_name)
        splits.append(split)
    return splits


def build_profile(repo_root: Path, module_depth: int, max_modules: int) -> dict[str, object]:
    module_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"file_count": 0, "loc": 0}
    )
    language_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"file_count": 0, "loc": 0}
    )

    source_file_count = 0
    source_loc = 0

    for source_path in iter_source_files(repo_root):
        rel_path = source_path.relative_to(repo_root)
        module_name = module_name_for(rel_path, module_depth)
        loc = source_line_count(source_path)

        module_stats[module_name]["file_count"] += 1
        module_stats[module_name]["loc"] += loc

        language = source_path.suffix.lower() or source_path.name
        language_stats[language]["file_count"] += 1
        language_stats[language]["loc"] += loc

        source_file_count += 1
        source_loc += loc

    large_repo = (
        source_file_count > LARGE_REPO_FILE_THRESHOLD
        or source_loc > LARGE_REPO_LOC_THRESHOLD
    )
    module_splits = build_module_splits(module_stats, max_modules=max_modules)

    return {
        "repo_root": str(repo_root),
        "source_file_count": source_file_count,
        "source_loc": source_loc,
        "large_repo": large_repo,
        "large_repo_thresholds": {
            "source_files": LARGE_REPO_FILE_THRESHOLD,
            "source_loc": LARGE_REPO_LOC_THRESHOLD,
        },
        "module_depth": module_depth,
        "module_splits": module_splits,
        "languages": [
            {
                "language": language,
                "file_count": stats["file_count"],
                "loc": stats["loc"],
            }
            for language, stats in sorted(
                language_stats.items(),
                key=lambda kv: (kv[1]["loc"], kv[1]["file_count"], kv[0]),
                reverse=True,
            )
        ],
        "detectors": DETECTORS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile a repository for grouped subagent planning."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Repository root path (default: current directory).",
    )
    parser.add_argument(
        "--module-depth",
        type=int,
        default=1,
        help="Directory depth to use for module split (default: 1).",
    )
    parser.add_argument(
        "--max-modules",
        type=int,
        default=20,
        help="Maximum module entries to emit before folding small modules (default: 20).",
    )
    parser.add_argument("--out", help="Write JSON output to file.")
    args = parser.parse_args()

    if args.module_depth < 1:
        raise SystemExit("--module-depth must be >= 1")
    if args.max_modules < 2:
        raise SystemExit("--max-modules must be >= 2")

    repo_root = Path(args.repo_root).resolve()
    profile = build_profile(
        repo_root=repo_root,
        module_depth=args.module_depth,
        max_modules=args.max_modules,
    )
    payload = json.dumps(profile, indent=2, sort_keys=True)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
