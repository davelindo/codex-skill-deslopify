# Codex Skill: Enslopify

[![Bundle Skill](https://github.com/davelindo/codex-skill-enslopify/actions/workflows/bundle-skill.yml/badge.svg)](https://github.com/davelindo/codex-skill-enslopify/actions/workflows/bundle-skill.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

A Codex skill for the real [Enslopify](https://github.com/peteromallet/enslopify)
codebase-health workflow. It uses Enslopify for detection, persistent state,
subjective review, triage, prioritization, resolution, and scoring.

The skill supports three outcomes:

- A production-code read-only health audit
- An ordered cleanup plan without execution
- An explicitly authorized `scan -> plan -> execute -> rescan` improvement cycle

## Why This Version Is Different

The earlier `enslopify-code-health-auditor` skill used a fixed detector list,
custom JSON findings, and a synthetic score. Those components have been removed.
The `$enslopify` skill now follows the actual CLI and treats `enslopify next`
as the authoritative workflow queue.

This is intentionally a breaking rename. There is no compatibility alias for
`$enslopify-code-health-auditor`.

## Install

Make the `enslopify/` directory available in the Codex skills path, commonly
`$CODEX_HOME/skills`:

```bash
git clone git@github.com:davelindo/codex-skill-enslopify.git
cd codex-skill-enslopify
cp -R enslopify "${CODEX_HOME:?Set CODEX_HOME}/skills/enslopify"
```

The skill prefers an installed `enslopify` executable. If it is unavailable,
or does not report version 1.0, it directs Codex to run the pinned `v1.0` GitHub
source through `uvx` or a temporary Python 3.11+ virtual environment. It does
not alter the target project's environment.

## Use

Audit and report:

```text
Use $enslopify to audit this repository and report its current code-health scores and next action.
```

Create a plan without code changes:

```text
Use $enslopify to scan this repository and create a prioritized cleanup plan. Do not edit production code.
```

Run an improvement cycle:

```text
Use $enslopify to systematically improve this repository's strict score. Do not commit or push.
```

Enslopify writes local state to `.enslopify/`. Keep that directory out of
version control.

## Runtime Contract

- Enslopify owns findings, state, queue order, resolution commands, and scores.
- Skill release 1.0.0 embeds the exact Enslopify 1.0 support matrix: 8 full
  plugins and 22 generic plugins. It performs no runtime registry-discovery
  command.
- Full plugins and reduced-depth generic plugins are reported separately,
  including missing external tools and resulting coverage gaps.
- Unsupported, ambiguous, and non-code repositories receive no health score.
- Partial supported-language scans are never represented as whole-repository
  scores.
- Audits may write `.enslopify/` state but do not edit maintained source.
- Cleanup code changes require an explicit cleanup or score-improvement request.
- Commits, pushes, pull requests, published comments, accepted debt, and upstream
  issue/PR creation require separate authorization.
- Coherent polyglot applications use independent per-language state; unrelated
  monorepo applications are scanned as separate projects.
- Codex uses Enslopify's first-class review and triage runners instead of a
  second subagent orchestration layer.

## Upstream Maintenance

This repository uses deliberate manual updates rather than automatic upstream
mirroring. The current curated baseline is:

- Skill release: `1.0.0`
- Enslopify release: `1.0`
- Upstream skill version: `7`
- Last reviewed: `2026-08-22`

When updating:

1. Choose the exact Enslopify Git tag for the next skill release.
2. Compare that tag's `docs/SKILL.md`, `docs/CODEX.md`, and `enslopify langs`
   output with this skill.
3. Update the embedded compatibility matrix, pinned installation URLs, and all
   three version markers together.
4. Preserve the authorization and audit/cleanup boundaries documented here.
5. Run the validation and isolated CLI smoke tests below before tagging the
   skill release.

Do not run `enslopify setup` or `enslopify update-skill` against this
repository; those commands can replace curated agent guidance.

## Validate and Bundle

Validate the skill with Codex's Skill Creator validator:

```bash
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" enslopify
```

The GitHub workflow checks the package structure and builds
`dist/enslopify-skill-v1.0.0.zip`. For a runtime smoke test, resolve the pinned
canonical tag in an isolated fixture and observe `scan`, `status`, and `next`
before publishing a release.

## Project Layout

```text
enslopify/
|-- SKILL.md
|-- agents/openai.yaml
`-- references/recovery.md
```

The upstream project and CLI are maintained by
[peteromallet/enslopify](https://github.com/peteromallet/enslopify).
