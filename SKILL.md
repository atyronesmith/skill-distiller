---
name: skill-distiller
description: "Convert a traditional all-LLM SKILL.md into the hybrid form with bundled scripts for deterministic work, or determine that conversion does not make sense and explain why. Use this skill whenever the user asks to refactor a skill, optimize a skill, convert a skill to use scripts, distill a skill, audit a skill for token efficiency, or asks whether an existing SKILL.md is a good candidate for the script-bundled pattern. Also triggers when the user provides a path to an existing SKILL.md and asks for an analysis of whether it should be restructured."
argument-hint: <path-to-existing-SKILL.md>
allowed-tools: ["Bash", "Read", "Write"]
---

# Skill Distiller

Convert an all-LLM SKILL.md into the hybrid form (SKILL.md + scripts/ + schemas.md) where deterministic work moves to bundled scripts and the LLM retains only the judgment steps. Or determine that conversion does not make sense and produce a categorized explanation.

The output is a refactor *design*: a new SKILL.md, a JSON Schema document, and script stubs with documented contracts. Actual script implementation belongs to whoever has access to the real artifacts the converted skill will operate on. This skill produces the spec; implementation comes after.

## Pre-flight

The argument is a path to an existing SKILL.md. Verify the file exists and is readable. If not, abort with a clear error.

## Step 1: Analyze structure

Run `scripts/analyze_skill.py <input-md>`. The script returns structural metadata as JSON on stdout: line count, frontmatter fields, heading inventory, code block counts by language, "Step N" heading count, decision-keyword density, and extraction hints.

## Step 2: [LLM judgment] Critique the skill

Read the original SKILL.md and the analysis output from Step 1. Write a `CRITIQUE.md` file to the output directory. This critique is produced for every skill regardless of the eventual conversion decision.

The critique must contain these sections:

### Overview

One paragraph summarizing what the skill does and its current form (all-LLM, hybrid, alias, reference material, etc.).

### Conversion assessment

Based on the analysis signals (line count, shell blocks, step headings, extraction hints), state whether the skill is likely a good conversion candidate, a partial candidate, or should be skipped. Explain why. This is a preliminary assessment — the formal heuristic score follows in Step 3.

### Strengths

What the skill does well — clear workflow structure, good error handling guidance, well-defined output format, appropriate use of tools, etc.

### Improvements

A numbered list of specific, actionable changes to improve the skill. Each item should be concrete enough that someone could implement it without further clarification. Examples of good improvement items:

- "Step 3 mixes data fetching (curl commands) and judgment (classifying results) — separate the deterministic fetching into a script with a JSON contract."
- "The report template in Step 7 duplicates the Affected Package table fields in the prose above — deduplicate by referencing the table."
- "Add error handling for when the Gerrit API returns no results for a Change-Id — currently the skill says nothing about this case."
- "The skill is 395 lines but most of it is example code blocks showing good vs. bad patterns. Consider moving the examples to a separate reference file and keeping the skill focused on the workflow."
- "The frontmatter is missing `context: fork` — add it so the skill runs in a forked context."

Focus on improvements that would make the skill more effective, not stylistic preferences. Prioritize: missing error handling, mixed deterministic/judgment work, unclear contracts, redundant content, missing edge cases.

## Step 3: Estimate savings

Run `scripts/estimate_savings.py <input-md>`. The script returns projected token savings from conversion: all-LLM vs hybrid costs with a per-unit breakdown. Save the output to a temporary file for use in Step 4.

## Step 4: Score convertibility

Pipe the analysis JSON into `scripts/score_convertibility.py`, passing the savings estimate:

```bash
scripts/analyze_skill.py <input-md> | scripts/score_convertibility.py --savings-json <savings-file> [--min-savings N]
```

The script returns a recommendation (`convert` / `partial` / `skip_too_short` / `skip_low_procedural` / `skip_low_savings`) and the underlying signal counts. The `--min-savings` threshold (default 1000 tokens, configurable via `SKILL_DISTILLER_MIN_SAVINGS` env var) sets the minimum estimated token savings for conversion to be worthwhile. If savings are below the threshold, the recommendation is downgraded to `skip_low_savings`.

## Step 5: [LLM judgment] Decide

Read the score, signals, savings estimate, and the critique from Step 2. Override the heuristic when the prose structure suggests otherwise. Read `references/conversion-heuristics.md` before deciding. There are four outcomes:

- **Convert.** Procedural workflow with separable deterministic and judgment work, and estimated savings above threshold. Proceed to Step 6.
- **Partial.** Some procedural extraction is worthwhile but the skill is mostly judgment. Proceed to Step 6 with a smaller proposed script catalog and a note in the IMPLEMENTATION.md output.
- **Skip.** Skill is style/voice guidance, reference material, subjective creative work, already short, trivially commanded, or pure automation. The CRITIQUE.md (already written in Step 2) serves as the output — its Conversion assessment section explains the skip. Stop here.
- **Skip (low savings).** The heuristic scored the skill as convertible, but estimated savings are below the configured threshold. The refactoring overhead doesn't pay back. Include the savings estimate in the CRITIQUE.md Conversion assessment section. Stop here.

## Step 6: Extract embedded commands

Run `scripts/extract_commands.py <input-md>`. Returns a JSON array of all bash/sh/shell code blocks in the source skill, with their line ranges and bodies. These are the procedural seeds for the script catalog.

## Step 7: [LLM judgment] Propose the script catalog

From the analysis, the extracted commands, the savings estimate, and a careful reading of the original SKILL.md, propose a list of scripts. For each:

- **name** (e.g., `analyze_thing.py`, `fetch_x.sh`)
- **language** (`python3` or `bash`)
- **invocation** (positional args, flags, stdin)
- **purpose** (one sentence)
- **output_schema** (JSON Schema draft-07)
- **exit_codes** (semantics)
- **code** (the full working implementation — see implementation guidelines below)

Cluster related commands. Do not produce one-script-per-command — that re-creates the brittleness one layer down. A good script is a coherent operation with a clean JSON contract.

### Implementation guidelines

For each script, write the **full working code** — not a stub. The extracted commands from Step 6 and the original skill's prose provide enough information to implement.

**Python scripts** (`*.py`):
- Shebang: `#!/usr/bin/env python3`
- Stdlib only — no external dependencies unless explicitly documented
- Read input from `sys.argv` (positional args) or `sys.stdin` (JSON input)
- Write a single JSON value to `sys.stdout` via `json.dump`
- Log to `sys.stderr` only
- Exit codes per the `exit_codes` spec

**Bash scripts** (`*.sh`):
- Shebang: `#!/usr/bin/env bash`
- Start with `set -euo pipefail`
- Use embedded Python one-liners for JSON output: `python3 -c "import json,sys; print(json.dumps({...}))"`
- Validate arguments immediately, exit 1 on bad input
- No external tools beyond standard POSIX + Python 3 for JSON serialization

**General**:
- The output must conform to the script's `output_schema`
- Use the original skill's embedded shell commands as the starting point
- Read the original skill's prose to understand edge cases and error handling
- Handle common failure modes (file not found, API unreachable, parse errors)
- When classifying or categorizing inputs, validate against authoritative sources (e.g., `go list std` for Go stdlib packages) rather than heuristic shortcuts (e.g., "no dots in the name"). Heuristics produce false positives on unexpected inputs.

### Extraction checklist

Before finalizing the script list, check the `extraction_hints` from Step 1 and apply these rules. Read `references/conversion-heuristics.md` section "Extraction patterns" for detailed guidance.

1. **API references** (`extraction_hints.api_references`): For each external data source mentioned in prose (NVD, Gerrit, GitHub, Jira, any REST endpoint), propose a script that calls the structured API and returns JSON. The LLM should be a fallback path described in the new SKILL.md prose (e.g., "if the script returns exit code 1, use WebSearch"), not the primary data-fetching mechanism.

2. **Mechanical operations** (`extraction_hints.mechanical_operations`): For each deterministic comparison or validation described in prose — version comparison, string matching, pass/fail checks, data filtering, threshold evaluation — propose a script. These have exactly one correct output for a given input and are not judgment.

3. **Render patterns** (`extraction_hints.render_patterns`): If the workflow ends with formatting structured data into a report, propose a render script that takes JSON on stdin and writes formatted output (markdown file, structured text). This ensures consistent output regardless of LLM variance.

## Step 8: [LLM judgment] Identify the remaining LLM steps

List the judgment points that stay in the new SKILL.md. Each should be a step that genuinely requires reasoning over unstructured input, synthesizing a verdict, or making a call that varies per invocation.

### Judgment filter

Before finalizing the list of judgment steps, check each candidate against these questions. If the answer to any of the first three is yes, the step is a script, not judgment:

- **Does it call a structured API or fetch data from a known source?** → Script. The data retrieval and parsing are deterministic even if the skill's prose describes it as "search" or "look up."
- **Is it a deterministic comparison?** (version strings, regex matches, thresholds, pass/fail, data filtering) → Script. One input always produces one output.
- **Is it rendering structured data to human-readable format?** (JSON → markdown report, JSON → table, structured data → formatted file) → Script.
- **Does it genuinely require reasoning over unstructured input, making a call that varies per invocation, or synthesizing a verdict from ambiguous signals?** → Keep as judgment.

Common false positives (things that look like judgment but are scripts): "compare the fix version against the current version," "check if the ticket type is valid," "format the results as a report," "query the API and extract field X."

Common true judgment: "assess whether the code is reachable by an attacker," "classify the difference as expected vs. concerning," "decide whether the skill is worth converting."

## Step 9: Generate outputs

Build a JSON spec describing the new skill:

```json
{
  "name": "...",
  "description": "...",
  "title": "...",
  "summary": "...",
  "argument_hint": "...",
  "allowed_tools": ["Bash", "Read", "Write"],
  "steps": [
    {"kind": "script", "command": "scripts/foo.sh <arg>", "purpose": "..."},
    {"kind": "judgment", "purpose": "..."},
    ...
  ],
  "outputs": ["..."],
  "scripts": [
    {"name": "foo.sh", "language": "bash", "invocation": "...", "purpose": "...", "output_schema": {...}, "exit_codes": "...", "code": "#!/usr/bin/env bash\nset -euo pipefail\n..."}
  ]
}
```

Then run:

1. `scripts/generate_skill_skeleton.py < spec.json > new-skill.md`
2. `scripts/generate_schema_doc.py < spec.json > schemas.md`
3. `scripts/package_skill.py <output-dir> --skill-md new-skill.md --schemas schemas.md --script-stubs spec.json --critique critique.md`

The output directory contains: `SKILL.md`, `scripts/` (working implementations with JSON contracts), `schemas.md`, `CRITIQUE.md` (quality assessment from Step 2), and `IMPLEMENTATION.md` (testing and validation notes).

## Abort on non-zero

Any script returning non-zero terminates the workflow. Report the script name and stderr to the user. No partial-data continuation.

## Verdicts

- **Converted.** Output directory written. Tell the user where it is, the estimated token savings, and what to do next (test the scripts against real inputs, then run the skill end-to-end).
- **Skipped.** CRITIQUE.md written explaining the category, reasoning, and estimated savings (if applicable). The original skill is not modified.
