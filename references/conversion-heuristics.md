# Conversion Heuristics

When to convert an all-LLM skill into the hybrid form, and when not to.

## Convert

A skill is a good conversion candidate when most of these hold:

- Line count above 200
- Three or more shell-flavored code blocks (bash / sh / shell / zsh)
- Two or more "Step N" headings or a clear sequential workflow
- The procedural work and judgment work are separable — a reader can point at specific paragraphs and say "this is data gathering" versus "this is reasoning"
- The skill is used more than a few times. One-off skills don't pay back the refactor cost.

## Partial

Some of the above hold but not all. The output may extract a few scripts but keep most of the prose intact. Common case: a skill with one or two procedural sections embedded in mostly-judgment work.

## Skip

A skill should not be converted when any of these apply:

- **Style or voice guidance.** The skill describes how something should be written — tone, vocabulary, structural patterns. The "operations" are not extractable. Example: a writing-voice skill.
- **Reference material.** The skill is a library of facts, patterns, or API examples for the LLM to draw from. There is no workflow. Example: a domain knowledge file.
- **Subjective creative work.** Image generation prompts, writing prompts, creative direction.
- **Already short.** Under ~150 lines with no clear procedural sections. The conversion overhead exceeds the win.
- **Trivially commanded.** Every "command" is a one-liner with no parsing needed. Putting one-liners in scripts adds indirection without benefit.
- **Pure automation, no judgment.** If there is no LLM judgment anywhere in the workflow, this is not a skill — it should be a CLI tool. The skill format is the wrong vehicle.

## Heuristic score

`score_convertibility.py` computes:

```
procedural_score = (shell_blocks * 5) + (step_headings * 3) + min(decision_keywords, 20)
```

| Score | Recommendation |
|-------|----------------|
| ≥ 25 | convert |
| 10–24 | partial |
| < 10 | skip |

Additional overrides:

- Line count < 150 AND shell_blocks < 2 AND step_headings < 2 → `skip_too_short`
- shell_blocks < 2 AND step_headings < 2 → `skip_low_procedural` regardless of score
- shell_blocks == 0 → `skip_low_procedural` regardless of score. A high procedural score from step headings and decision keywords alone indicates an orchestration or judgment-heavy skill (e.g., incident triage, RCA workflows), not one with scriptable work. Extraction hints (API references, mechanical operations) may count MCP tool invocations that require LLM judgment to select and parameterize — these are not the same as deterministic REST API calls that can be wrapped in a script.

The heuristic is a starting point. The LLM should override the recommendation when the prose structure suggests otherwise — for example, a reference-heavy skill might have a high decision-keyword count but no real workflow.

## On script granularity

When proposing the script catalog, do not produce one-script-per-command from the extracted shell blocks. That re-creates the brittleness one layer down. Cluster related commands into coherent operations:

- A script that "fetches X" includes whatever calls, parsing, and validation are needed to produce a clean JSON record of X.
- A script that "classifies Y" includes whatever lookups and comparisons are needed to produce a categorical result.
- A script that "searches Z" includes the search itself and the structuring of hits into a JSON array.

The right number of scripts is usually between 4 and 8 for a substantial skill. Fewer suggests under-extraction; more suggests over-fragmentation.

## Extraction patterns

Beyond embedded shell commands, three categories of work frequently appear in prose as "LLM tasks" but are actually deterministic and should be proposed as scripts.

### API query scripts

When a skill describes fetching data from a known structured source — NVD, Gerrit, GitHub API, Jira REST, any service with a JSON endpoint — propose a script that calls the API directly and returns structured JSON. Even if the original skill says "use WebSearch" or "use WebFetch," the presence of a structured API means the query and response parsing are deterministic. The LLM should only be the *fallback* when the structured source has no data, not the primary path.

Signals: `extraction_hints.api_references` count > 0 in the analysis output; prose mentioning "REST API," "query the API," "fetch the ticket," "MCP," "WebSearch," or "WebFetch" near a specific data source.

### Mechanical comparison scripts

Version comparison, semver checks, string matching, pass/fail evaluation, data filtering, threshold checks — these have exactly one correct output for a given input. They are not judgment. If the original skill says "compare the fix version against the current version," that is a script, not a step where the LLM reasons.

Signals: `extraction_hints.mechanical_operations` count > 0; prose containing "compare version," "check if," "validate that," "match against," "pass/fail," "already fixed."

### Report rendering scripts

If the workflow's final step takes structured data (JSON from prior scripts + LLM-assembled fields) and formats it into markdown, HTML, or a file, the rendering is deterministic. Propose a script that reads JSON on stdin and writes the formatted output. This ensures consistent report structure regardless of LLM variance.

Signals: `extraction_hints.render_patterns` count > 0; prose containing "produce report," "structured report," "output markdown," "format as table," "write report to."

## Savings threshold

`estimate_savings.py` projects the token savings from conversion. `score_convertibility.py` uses this to gate the recommendation:

- **`--min-savings`** (default 1000 tokens, env `SKILL_DISTILLER_MIN_SAVINGS`): minimum estimated savings for conversion to be worthwhile.
- If estimated savings are below the threshold OR below 20% of the all-LLM cost, the recommendation is downgraded to `skip_low_savings` regardless of the procedural score.

This prevents converting skills where the procedural signals look strong (high shell block count, many step headings) but the actual token savings are marginal — typically because the skill's procedural parts are short one-liners that don't save much when scripted.

The threshold should be tuned based on the team's conversion effort budget. A skill saving 9000 tokens per invocation across 50 invocations/week saves ~450K tokens/week — clearly worth the effort. A skill saving 500 tokens invoked twice a month saves ~1K tokens/month — not worth the maintenance.

### How these interact with the script catalog

These three patterns often add 2–3 scripts beyond what the embedded shell commands suggest. A skill with 4 shell blocks might actually warrant 6–7 scripts once API queries, comparisons, and rendering are factored in. The 4–8 range still applies — just count these additional scripts as part of the total.
