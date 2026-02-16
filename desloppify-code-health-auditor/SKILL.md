---
name: desloppify-code-health-auditor
description: Run a Desloppify-style code health audit on an existing repository and return a deduplicated, prioritized findings report. Use when asked to analyze dead/unused code, duplication, complexity or oversized files/functions, dependency and coupling issues, naming consistency smells, and debug/logging leftovers without building software, scaffolding tools, proposing a new CLI, or editing files unless explicitly requested.
---

# Desloppify Code Health Auditor

## Constraints

- Analyze the existing repository only.
- Do not build software.
- Do not scaffold tools.
- Do not propose implementing a CLI.
- Do not edit files unless the user explicitly asks.
- Prefer read-only inspection commands and static analysis.

## Detectors

Run and report these detectors every time:

- `dead_unused_code`
- `duplication`
- `complexity_size`
- `dependency_coupling`
- `naming_consistency`
- `debug_logging_leftovers`

## Execution Model

Use subagents aggressively for parallel analysis.

1. Build module splits with `scripts/repo_profile.py`.
2. Build grouped tasks with `scripts/grouped_subagent_plan.py`.
3. Execute groups in order, parallelizing inside each group:
   - `G1_structural`: `dead_unused_code`, `duplication`
   - `G2_architecture`: `complexity_size`, `dependency_coupling`
   - `G3_hygiene`: `naming_consistency`, `debug_logging_leftovers`
4. Require each subagent to return structured findings only, no long prose.
5. Validate subagent outputs using `scripts/validate_findings.py`.
6. Run coordinator merge/score using `scripts/merge_and_score.py`.
7. If subagents disagree, keep the finding and tag `needs validation` with a one-line conflict note.

### Non-Clobbering Rules

- Never run two tasks with the same `detector + module`.
- Give each task a unique output path (for example `runs/<run_id>/findings/<task_id>.json`).
- Keep module scopes disjoint inside the same detector group.
- Coordinator only reads subagent outputs and does not overwrite them.
- Keep all analysis read-only unless the user explicitly asks for edits.

### Helper Commands

Use these commands when running the workflow:

```bash
python3 scripts/repo_profile.py . --out runs/profile.json
python3 scripts/grouped_subagent_plan.py --profile runs/profile.json --run-id run-001 --out runs/run-001/plan.json

# subagents write JSON arrays into runs/run-001/findings/*.json

python3 scripts/validate_findings.py runs/run-001/findings
python3 scripts/merge_and_score.py runs/run-001/findings --out runs/run-001/report.json
```

## Subagent Output Contract

Require each subagent to return findings as a JSON array where each item includes:

- `id` (temporary local id allowed; coordinator may rename)
- `tier` (`T1`-`T4`)
- `detector`
- `severity` (`low`/`med`/`high`)
- `file`
- `line` (single line number when possible)
- `summary`
- `evidence`
- `recommended_fix`
- `confidence` (`high`/`med`/`low`)
- `status` (`open` by default)
- `conflict_note` (only when `needs validation`)
- `needs_validation` (`true`/`false`)

## Tier and Severity Normalization

Normalize tiers consistently in coordinator pass:

- `T1`: High-risk correctness/security/reliability or very costly maintenance traps.
- `T2`: Significant maintainability/design issues likely to cause near-term defects.
- `T3`: Moderate quality smells with clear but non-urgent remediation.
- `T4`: Low-impact hygiene issues.

Normalize severity independently of tier:

- `high`: strong negative impact or broad blast radius
- `med`: moderate impact or localized risk
- `low`: minor impact

## Dedup Rules

Deduplicate findings before final output.

1. Build a fingerprint from `detector + file + normalized summary`.
2. Merge duplicates into one record and keep strongest severity/tier/confidence.
3. Merge evidence snippets; keep file and line references.
4. Preserve disagreements as `needs validation` with conflict note.

## Scoring

Compute two scores: `overall_score` and `strict_score`.

Penalty weights:

- Tier weights: `T1=20`, `T2=10`, `T3=4`, `T4=1`
- Severity multipliers: `high=1.0`, `med=0.6`, `low=0.3`
- Confidence multipliers: `high=1.0`, `med=0.75`, `low=0.5`

Per-finding penalty:

`penalty = tier_weight * severity_multiplier * confidence_multiplier`

Score formulas:

- `strict_score = max(0, min(100, 100 - sum(all penalties)))`
- `overall_score = max(0, min(100, 100 - (open_penalties + 0.5 * wontfix_penalties)))`

If no resolutions exist yet, `overall_score` and `strict_score` may be equal.

## Required Final Output

Return sections in this order:

1. Short executive summary.
2. Findings table (deduplicated, repo-specific, file paths and line refs when possible).
3. Scores and detector/tier breakdowns.
4. Top 10 highest-priority open findings in fix order.
5. Prioritized remediation plan grouped by quick wins vs refactors.
6. Resolve simulation commands for each top finding:
   - `resolve fixed <id>`
   - `resolve wontfix <id> --note "reason"`
   - `resolve false_positive <id> --note "reason"`
7. Explicit list of detectors with zero findings.

## Reporting Rules

- Mark uncertain findings as `needs validation`.
- Keep findings concrete and repository-specific.
- Include file paths and line references wherever possible.
- Do not include speculative implementation plans unrelated to findings.

## Prompt Templates

Use detector and coordinator templates from:

- `references/grouped-subagent-prompts.md`
