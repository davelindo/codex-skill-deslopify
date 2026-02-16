# Codex Skill: Desloppify Code Health Auditor

[![Bundle Skill](https://github.com/davelindo/codex-skill-deslopify/actions/workflows/bundle-skill.yml/badge.svg)](https://github.com/davelindo/codex-skill-deslopify/actions/workflows/bundle-skill.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)

Desloppify-style code health auditing skill for Codex.  
It analyzes an existing repository with grouped subagents, then validates, deduplicates, scores, and prioritizes findings.

## What This Project Does

This repository packages a Codex skill named `desloppify-code-health-auditor` with:

- A strict read-only auditing contract (no builds, no scaffolding, no file edits unless explicitly requested)
- Detector coverage for dead code, duplication, complexity, dependency coupling, naming consistency, and debug/log leftovers
- Grouped, non-clobbering subagent planning
- Deterministic findings validation and merge/score reporting

Core skill definition:

- [`desloppify-code-health-auditor/SKILL.md`](desloppify-code-health-auditor/SKILL.md)

## Why This Project Is Useful

- Produces a consistent audit report format across runs
- Reduces subagent collisions with grouped execution and unique output paths
- Normalizes severity/tier/confidence across heterogeneous detector outputs
- Generates actionable next steps (top findings, remediation plan, resolve simulation commands)
- Works with plain Python scripts and JSON artifacts

## Project Layout

```text
desloppify-code-health-auditor/
├── SKILL.md
├── agents/openai.yaml
├── references/grouped-subagent-prompts.md
└── scripts/
    ├── repo_profile.py
    ├── grouped_subagent_plan.py
    ├── validate_findings.py
    └── merge_and_score.py
```

## Getting Started

### Prerequisites

- Python 3.9+
- A repository to audit
- A Codex environment that can run subagents (for full workflow)

### Install for Codex

Clone this repository and place the skill folder where your Codex instance loads skills (commonly `$CODEX_HOME/skills`):

```bash
git clone git@github.com:davelindo/codex-skill-deslopify.git
cd codex-skill-deslopify
```

Then make sure the `desloppify-code-health-auditor/` directory is available in your Codex skills path.

### Run the Workflow (Script Side)

From the skill directory:

```bash
cd desloppify-code-health-auditor
```

1) Profile the target repository:

```bash
python3 scripts/repo_profile.py /path/to/target-repo --out runs/profile.json
```

2) Generate grouped, non-clobbering tasks:

```bash
python3 scripts/grouped_subagent_plan.py \
  --profile runs/profile.json \
  --run-id run-001 \
  --out runs/run-001/plan.json
```

3) Execute subagents per plan and write JSON arrays to:

- `runs/run-001/findings/*.json`

4) Validate subagent outputs:

```bash
python3 scripts/validate_findings.py runs/run-001/findings
```

5) Merge/deduplicate/score results:

```bash
python3 scripts/merge_and_score.py \
  runs/run-001/findings \
  --out runs/run-001/report.json
```

### Usage Example (Codex Prompt)

```text
Use $desloppify-code-health-auditor to audit this repository and return a deduplicated, prioritized findings report.
```

Prompt templates and detector snippets:

- [`desloppify-code-health-auditor/references/grouped-subagent-prompts.md`](desloppify-code-health-auditor/references/grouped-subagent-prompts.md)

## Where To Get Help

- Open an issue in this repository: <https://github.com/davelindo/codex-skill-deslopify/issues>
- Review the skill contract: [`desloppify-code-health-auditor/SKILL.md`](desloppify-code-health-auditor/SKILL.md)
- Review prompt templates: [`desloppify-code-health-auditor/references/grouped-subagent-prompts.md`](desloppify-code-health-auditor/references/grouped-subagent-prompts.md)

## Maintainers and Contributing

Maintainer:

- [@davelindo](https://github.com/davelindo)

Contributions are welcome via pull requests. To keep changes easy to review:

1. Keep edits focused (skill spec, scripts, or references).
2. Include a short rationale in the PR description.
3. Run the script workflow locally on sample findings before opening the PR.
4. Avoid committing generated `runs/` artifacts.
