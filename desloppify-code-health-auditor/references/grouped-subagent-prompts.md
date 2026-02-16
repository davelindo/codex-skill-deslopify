# Grouped Subagent Prompt Templates

Use these templates to keep subagents focused and non-overlapping.

## Shared Subagent Contract

Always include this in every detector subagent prompt:

1. Analyze only the assigned `scope_globs`.
2. Use only the assigned `detector`.
3. Do not edit files.
4. Return JSON array only.
5. If no findings, return `[]`.

Required fields per finding:

- `id`
- `tier` (`T1`-`T4`)
- `detector`
- `severity` (`low`/`med`/`high`)
- `file`
- `line` (int or null)
- `summary`
- `evidence`
- `recommended_fix`
- `confidence` (`high`/`med`/`low`)
- `status` (`open`)
- `conflict_note` (empty string unless needed)
- `needs_validation` (`false` unless needed)

## Detector Prompt Snippets

### dead_unused_code

Find unreachable code, stale exports, unused helpers, dead flags, and orphan modules in scope.

### duplication

Find near-duplicate logic blocks, copy-paste functions, and repeated literals/constants that should be consolidated.

### complexity_size

Find oversized files/functions, deep branching, and high cognitive complexity hot spots.

### dependency_coupling

Find cyclic imports, inappropriate layering, cross-module reach-ins, and tightly coupled dependency patterns.

### naming_consistency

Find inconsistent naming conventions, misleading symbols, and terminology drift within scope.

### debug_logging_leftovers

Find debug prints/log statements, temporary tracing flags, and test-only logging left in production paths.

## Coordinator Prompt Template

Use this after detector subagents finish:

1. Ingest all JSON findings files.
2. Deduplicate by `detector + file + normalized(summary)`.
3. Normalize tier/severity/confidence.
4. Keep disagreements and mark `needs_validation=true` with short `conflict_note`.
5. Compute scores and breakdowns.
6. Output final report sections in required order.
