# AGENTS.md

This file describes how AI agents should interact with this repository.

## Repository purpose

skill-distiller analyzes Claude Code SKILL.md files and converts them from all-LLM form to a hybrid form where deterministic work moves to bundled scripts. It produces a refactored design (new SKILL.md + script stubs + JSON Schema contracts), not finished implementations.

## Key files

- `SKILL.md` — the skill definition (9-step pipeline). This is the primary entry point when invoked as `/skill-distiller`.
- `scripts/` — deterministic pipeline scripts (analyze, score, estimate savings, extract commands, generate skeleton/schemas, package output)
- `references/conversion-heuristics.md` — decision criteria for convert/partial/skip
- `tests/fixtures/` — test SKILL.md files for pipeline verification

## Agent guidelines

- All scripts are stdlib-only Python 3. Do not add external dependencies.
- Scripts communicate via JSON on stdin/stdout. Never log to stdout.
- The pipeline has 9 steps. Steps 1, 3, 4, 6 are deterministic scripts. Steps 2, 5, 7, 8 are LLM judgment. Step 9 is deterministic generation.
- The savings threshold (`--min-savings`, default 1000 tokens) is configurable. Respect the configured value — don't override it unless the user explicitly asks.
- When modifying the pipeline, keep step numbers consistent across SKILL.md, CLAUDE.md, README.md, and docs/testing.md.
