# Testing skill-distiller

## Quick test with fixtures

The repo includes 3 test fixtures in `tests/fixtures/`:

- `convert-candidate.md` — a deployment health checker with clear script/judgment separation
- `skip-reference.md` — a Go error patterns reference document (no workflow)
- `partial-candidate.md` — a PR summary generator with some extractable work

Run the deterministic pipeline steps against a fixture:

```bash
# Analyze + estimate savings + score
python3 scripts/analyze_skill.py tests/fixtures/convert-candidate.md > /tmp/analysis.json
python3 scripts/estimate_savings.py tests/fixtures/convert-candidate.md > /tmp/savings.json
python3 scripts/score_convertibility.py --savings-json /tmp/savings.json < /tmp/analysis.json
```

To run the full pipeline (including LLM judgment steps), invoke the skill:

```
/skill-distiller tests/fixtures/convert-candidate.md
```

## Testing against openstack-k8s-operators devskills

The [devskills repo](https://github.com/openstack-k8s-operators/devskills) contains 14 real-world skills that exercise a range of outcomes (convert, partial, skip with various reasons).

### Download

```bash
cd tests
git clone --depth 1 --filter=blob:none --sparse https://github.com/openstack-k8s-operators/devskills.git _repo
cd _repo && git sparse-checkout set skills && cd ..
for d in _repo/skills/*/; do cp -r "$d" "$(basename "$d")"; done
rm -rf _repo
```

### Run the full pipeline

```bash
# Deterministic steps only (no LLM):
for skill in tests/*/; do
  [ -f "${skill}SKILL.md" ] || continue
  name=$(basename "$skill")
  python3 scripts/estimate_savings.py "${skill}SKILL.md" > "/tmp/${name}-savings.json"
  echo "=== $name ==="
  python3 scripts/analyze_skill.py "${skill}SKILL.md" \
    | python3 scripts/score_convertibility.py --savings-json "/tmp/${name}-savings.json"
  echo
done
```

For the full pipeline with LLM judgment, critiques, and output generation, invoke the skill against each:

```
/skill-distiller tests/backport-review/SKILL.md
/skill-distiller tests/cve-validate/SKILL.md
```

### Expected results

From the 14 devskills, the pipeline produces:

| Outcome | Count | Skills |
|---------|-------|--------|
| Convert | 2 | backport-review (~10,750 tokens saved), cve-validate (~9,200 tokens saved) |
| Partial | 1 | code-review (~4,860 tokens saved) |
| Skip (too short) | 7 | bug, task-executor, analyze-zuul-ci-logs, support-triage, analyze-must-gather, explain-flow, feature |
| Skip (low procedural) | 1 | jira |
| Skip (LLM override) | 3 | code-style, debug-operator, test-operator (heuristic overridden — reference material, not workflows) |

### Adjusting the savings threshold

```bash
# Higher threshold — only convert skills saving 5000+ tokens
SKILL_DISTILLER_MIN_SAVINGS=5000 python3 scripts/score_convertibility.py \
  --savings-json /tmp/savings.json < /tmp/analysis.json

# Or per-invocation
python3 scripts/score_convertibility.py --min-savings 5000 \
  --savings-json /tmp/savings.json < /tmp/analysis.json
```
