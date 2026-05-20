# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

skill-distiller is a Claude Code **skill** (invoked via `/skill-distiller <path-to-SKILL.md>`) that analyzes an all-LLM SKILL.md and converts it into the hybrid form: a new SKILL.md with bundled Python scripts for deterministic work, keeping only judgment steps for the LLM. If conversion doesn't make sense, it explains why.

The skill produces a refactor **design** (new SKILL.md, script stubs with JSON contracts, schemas doc), not finished implementations. Script stubs raise `NotImplementedError`; the user fills them in.

## Running the Scripts

All scripts are stdlib-only Python 3 (no dependencies, no venv needed). Each reads/writes JSON via stdin/stdout and logs to stderr.

```bash
# Full pipeline (how SKILL.md invokes them):
python3 scripts/analyze_skill.py <input.md>                        # → analysis JSON
python3 scripts/analyze_skill.py <input.md> | python3 scripts/score_convertibility.py  # → recommendation JSON
python3 scripts/extract_commands.py <input.md>                     # → extracted commands JSON
python3 scripts/generate_skill_skeleton.py < spec.json             # → new SKILL.md to stdout
python3 scripts/generate_schema_doc.py < spec.json                 # → schemas.md to stdout
python3 scripts/package_skill.py <output-dir> --skill-md new.md --schemas schemas.md --script-stubs spec.json
```

There is no test suite, linter config, or build system.

## Architecture

The workflow is a 9-step pipeline defined in `SKILL.md` (the skill definition, not a doc). Steps alternate between **script** (deterministic) and **[LLM judgment]** (reasoning):

1. `analyze_skill.py` — structural metadata extraction (line count, headings, code blocks, decision-keyword density, extraction hints)
2. **LLM** — critique the skill: write `CRITIQUE.md` with overview, conversion assessment, strengths, and concrete improvements. Produced for every skill regardless of conversion outcome.
3. `estimate_savings.py` — project token savings from conversion (all-LLM vs hybrid costs, per-unit breakdown)
4. `score_convertibility.py` — heuristic scoring with savings threshold → `convert` / `partial` / `skip_too_short` / `skip_low_procedural` / `skip_low_savings`. Configurable via `--min-savings` (default 1000) or `SKILL_DISTILLER_MIN_SAVINGS` env var.
5. **LLM** — override heuristic using prose context, critique, and savings estimate; decide convert/partial/skip. For skips, `CRITIQUE.md` is the sole output.
6. `extract_commands.py` — pull all shell code blocks with line ranges
7. **LLM** — propose script catalog using extraction checklist (cluster commands, API queries, mechanical comparisons, report renderers into coherent scripts with JSON contracts)
8. **LLM** — identify remaining judgment-only steps using the judgment filter (API calls, comparisons, and rendering are scripts, not judgment)
9. `generate_skill_skeleton.py` + `generate_schema_doc.py` + `package_skill.py` — assemble output directory (includes `CRITIQUE.md`)

The LLM builds a spec JSON (shape documented in `SKILL.md` Step 8) that drives the generators. `references/conversion-heuristics.md` documents the scoring formula, skip/convert/partial criteria, and extraction patterns (API queries, mechanical comparisons, report rendering).

The `extraction_hints` field in `analyze_skill.py` output detects three categories of work that appear as prose but should be scripts: `api_references` (structured API calls), `mechanical_operations` (version comparisons, pass/fail checks), and `render_patterns` (report formatting from structured data).

## Key Conventions

- Any script returning non-zero terminates the entire workflow — no partial-data continuation.
- Script granularity: cluster related commands into 4–8 coherent scripts per converted skill, not one-per-command.
- The scoring formula: `procedural_score = (shell_blocks * 5) + (step_headings * 3) + min(decision_keywords, 20)`. Thresholds: ≥25 convert, 10–24 partial, <10 skip, with override rules for short/low-procedural skills.
