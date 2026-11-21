# Enslopify Recovery

Read this reference only after a workflow failure or a likely CLI defect. Keep
the last known-good scan state and retry the smallest failed unit.

## Failed review batches

Review packets are immutable snapshots under
`.enslopify/review_packets/holistic_packet_*.json`. Identify failed batch
indices from the runner output and retry only those slices:

```bash
enslopify review --run-batches \
  --packet .enslopify/review_packets/<packet>.json \
  --only-batches <indices>
```

Do not launch an independent child-agent harness. If a retry returns another
empty, partial, timeout-shaped, or rate-limit-shaped result, reduce concurrency
if the CLI supports it and retry the failed slice once more. After two
materially equivalent failures, stop, preserve the packet and logs, and report
the blocker instead of repeating the same experiment.

Do not combine manual score overrides with `--allow-partial`. Manual scores are
provisional and can expire on the next scan; prefer a trusted internal or
attested external import when the supported batch runner cannot complete.

## Stalled triage

Automated triage artifacts live under
`.enslopify/triage_runs/<timestamp>/`. Inspect `run.log` and
`run_summary.json` to find the last confirmed stage. Re-run the automated
command to resume, or retrieve the exact manual prompt for the failed stage:

```bash
enslopify plan triage --stage-prompt <stage>
```

Do not restart completed stages or invent a replacement gate report.

## Codex runner sandbox failures

The first-class Codex runner normally manages its own subprocess sandbox. If it
cannot start because the host lacks required sandbox support, capture the exact
failure first. `ENSLOPIFY_CODEX_SANDBOX` accepts `read-only`,
`workspace-write`, or `danger-full-access`; use the last value only when the
surrounding environment is already externally sandboxed and the user's scope
permits it. Never weaken sandboxing merely to avoid diagnosing another failure.

## Stale guidance or CLI defects

If the CLI reports stale skill guidance, compare this skill's recorded upstream
release and skill version with `docs/SKILL.md` and `docs/CODEX.md` in the
canonical repository. Do not let `setup` or `update-skill` overwrite this
repository or upgrade the CLI inside an active run. Keep using the version
pinned by the current skill release; evaluate a newer CLI, compatibility matrix,
and guidance together as a new skill release.

For a crash, inconsistent state, or likely false positive:

1. Capture the version, command, scan root, minimal reproduction, expected
   result, and actual result.
2. Verify current upstream source or documentation when network access is
   available.
3. Use a workaround only when it preserves state and scoring integrity.
4. File an issue or open a pull request only with explicit user authorization.

Canonical source: <https://github.com/peteromallet/enslopify>
