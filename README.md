# skill-distiller

Convert all-LLM Claude Code skills into the hybrid form — where deterministic work moves to bundled scripts and the LLM retains only the judgment steps.

## Why this exists

Claude Code skills are markdown files that instruct the LLM to follow a workflow. When every step lives in the SKILL.md prose, the LLM spends tokens on work that a script could do faster and more reliably: parsing files, calling APIs, comparing version strings, rendering reports. The hybrid pattern fixes this by splitting the skill into:

- **Scripts** — deterministic operations with JSON contracts (stdin/stdout, exit codes, schemas)
- **LLM judgment steps** — reasoning over unstructured input, synthesizing verdicts, making calls that vary per invocation

The result is a skill that runs faster, uses fewer tokens, and produces more consistent output. The LLM focuses on what it's good at (judgment), and scripts handle the rest.

skill-distiller automates this refactoring. Given a SKILL.md, it analyzes the structure, critiques the skill quality, decides whether conversion makes sense, and produces a refactored design with script stubs and JSON Schema contracts.

## What it produces

For every skill analyzed:

- **CRITIQUE.md** — quality assessment with concrete improvement suggestions (produced for all skills, even those not converted)

For skills that are converted:

- **SKILL.md** — the new hybrid skill with script invocations and judgment steps
- **scripts/** — stub scripts with documented contracts (`NotImplementedError` placeholders)
- **schemas.md** — JSON Schema documentation for each script's output
- **IMPLEMENTATION.md** — notes for whoever implements the stubs

For skills that are skipped (reference material, style guides, aliases, etc.):

- **CRITIQUE.md** — includes the skip reasoning in its Conversion assessment section

## Usage

### As a Claude Code skill

```
/skill-distiller path/to/SKILL.md
```

### Manual pipeline

```bash
# Step 1: Analyze structure
python3 scripts/analyze_skill.py input.md > analysis.json

# Step 2: LLM critiques the skill and writes CRITIQUE.md

# Step 3: Estimate token savings
python3 scripts/estimate_savings.py input.md > savings.json

# Step 4: Score convertibility (with savings threshold)
python3 scripts/score_convertibility.py --savings-json savings.json < analysis.json

# Step 5: LLM decides convert/partial/skip

# Step 6: Extract embedded commands
python3 scripts/extract_commands.py input.md

# Steps 7-8: LLM proposes script catalog and identifies judgment steps

# Step 9: Generate outputs
python3 scripts/generate_skill_skeleton.py < spec.json > new-skill.md
python3 scripts/generate_schema_doc.py < spec.json > schemas.md
python3 scripts/package_skill.py output-dir \
  --skill-md new-skill.md \
  --schemas schemas.md \
  --script-stubs spec.json \
  --critique critique.md
```

All scripts are stdlib-only Python 3 — no dependencies, no venv needed.

### Configuration

The savings threshold controls when conversion is worthwhile:

```bash
# Default: 1000 tokens minimum savings
python3 scripts/score_convertibility.py --min-savings 1000 --savings-json savings.json < analysis.json

# Via environment variable
export SKILL_DISTILLER_MIN_SAVINGS=5000
python3 scripts/score_convertibility.py --savings-json savings.json < analysis.json
```

Skills with estimated savings below the threshold get `skip_low_savings` even if their procedural signals are strong.

## Writing efficient hybrid skills

### When to use a script vs. LLM judgment

**Script** — the operation has a deterministic output for a given input:

- Calling a structured API (NVD, Gerrit, GitHub REST) and parsing the JSON response
- Comparing version strings, checking thresholds, pass/fail evaluation
- Searching files with grep/find and structuring the results as JSON
- Rendering structured data (JSON) into a formatted report (markdown, table)
- Parsing and extracting fields from known file formats (go.mod, Dockerfile, YAML)

**LLM judgment** — the operation requires reasoning that varies per invocation:

- Reading unstructured text and identifying what's relevant
- Assessing risk, severity, or quality from ambiguous signals
- Classifying differences as "expected" vs. "concerning"
- Deciding between multiple valid approaches
- Synthesizing a verdict from multiple data sources

### The gray area

Some operations look like judgment but are actually deterministic. Common false positives:

- "Compare the fix version against the current version" — this is math, not judgment
- "Check if the ticket type is valid" — this is string matching
- "Format the results as a report" — this is template rendering
- "Query the API and extract field X" — this is a structured call with parsing

When in doubt, ask: "Given the same input, would this always produce the same output?" If yes, it's a script.

### JSON contracts

Every script should:

- Read input from arguments or stdin
- Write a single JSON value to stdout
- Log to stderr (never to stdout)
- Use meaningful exit codes (0 = success, 1+ = specific failure modes)
- Have a JSON Schema draft-07 contract documented in schemas.md

The SKILL.md orchestrates by piping script outputs into the next step. The LLM reads JSON outputs and uses them to inform its judgment steps.

### Script granularity

A good skill has **4 to 8 scripts**. Each script should be a coherent operation, not a one-liner wrapper:

- A script that "fetches X" includes the API call, response parsing, error handling, and structured output
- A script that "classifies Y" includes lookups, comparisons, and a categorical result
- A script that "searches Z" includes the search, result filtering, and JSON structuring

Don't create one script per shell command from the original skill — that recreates the brittleness one layer down. Cluster related commands into coherent operations.

### Three patterns to look for

When converting a skill, these three categories of work are commonly hiding in prose as "LLM tasks" but should be scripts:

1. **API queries** — When the skill says "search the web" or "fetch the data," check if a structured API exists. If so, script the API call and use the LLM only as a fallback when the structured source has no data.

2. **Mechanical comparisons** — Version comparison, regex matching, data filtering, threshold checks. These have exactly one correct output and belong in a script.

3. **Report rendering** — If the workflow produces structured JSON and the final step is formatting it into markdown, that formatting is deterministic. A render script ensures consistent output regardless of LLM variance.

### Common anti-patterns

**Reference material as a skill.** A 400-line file of "good vs. bad" code examples is not a workflow — it's a reference document. It won't benefit from conversion because there's nothing to extract. Keep it as-is or split it into a slim SKILL.md that orchestrates and a separate reference file.

**Example catalogs that look procedural.** A skill listing 16 `make` targets with examples scores high on the shell-block heuristic but has no sequential workflow. The heuristic counts code blocks; the LLM must recognize that illustrative examples are not pipeline stages.

**Prose that hides deterministic operations.** "Compare the version" buried in a paragraph about CVE assessment looks like judgment but is actually a one-line semver check. Read carefully and extract these.

**Aliases and thin orchestrators.** A 12-line skill that says "read another skill and follow it" doesn't need conversion. Neither does a skill that just validates inputs and dispatches a sub-agent.
