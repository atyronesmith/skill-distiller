# Contributing

## Development

All scripts are stdlib-only Python 3 — no virtualenv or dependencies needed.

```bash
# Run the deterministic pipeline against a test fixture
python3 scripts/analyze_skill.py tests/fixtures/convert-candidate.md
python3 scripts/estimate_savings.py tests/fixtures/convert-candidate.md
```

See [docs/testing.md](docs/testing.md) for full testing instructions.

## Adding or modifying scripts

Each script follows the same contract:

- Reads input from arguments or stdin
- Writes a single JSON value to stdout
- Logs to stderr
- Uses meaningful exit codes
- Stdlib only — no external dependencies

When modifying a script's output schema, update:
1. The script's docstring
2. `references/conversion-heuristics.md` if the change affects scoring
3. `SKILL.md` if it affects the workflow
4. `CLAUDE.md` architecture section

## Modifying the pipeline

The 9-step pipeline is defined in `SKILL.md`. When adding or reordering steps:
1. Update step numbers in `SKILL.md`
2. Update the architecture section in `CLAUDE.md`
3. Update the manual pipeline in `README.md`
4. Update `docs/testing.md` expected results if outcomes change

## Token cost model

Per-unit costs in `scripts/estimate_savings.py` were derived from comparing the all-LLM and hybrid versions of the cve-validate skill. If you have additional conversion data points, update the `UNIT_COSTS` dict in that file.
