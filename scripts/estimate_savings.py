#!/usr/bin/env python3
"""Estimate token savings from converting a skill to hybrid form.

Usage: estimate_savings.py <path-to-skill.md>
  Optionally reads analysis JSON on stdin (output of analyze_skill.py).
  If no stdin, runs analyze_skill.py internally.
Output: JSON object to stdout with per-unit costs and projected savings.
Exit codes:
  0 on success
  1 on file read error

Token cost model derived from comparing all-LLM vs hybrid versions of
the cve-validate and backport-review skills.

stdlib only.
"""
import json
import re
import sys
from pathlib import Path

TOKENS_PER_LINE = 13  # ~10 words/line × 1.3 tokens/word

# Per-unit token costs (all-LLM vs hybrid)
# Derived from manual analysis of cve-validate and backport-review conversions.
UNIT_COSTS = {
    "shell_command": {
        "description": "Embedded shell command the LLM interprets and runs",
        "all_llm": 80,    # read command, reason about args, execute, parse output
        "hybrid": 0,       # script handles entirely
    },
    "api_call": {
        "description": "Structured API call (REST, MCP, CLI query)",
        "all_llm": 400,   # construct request, parse response, extract fields
        "hybrid": 30,      # read JSON output from script
    },
    "mechanical_comparison": {
        "description": "Version comparison, pass/fail check, threshold evaluation",
        "all_llm": 150,   # read values, reason about comparison, output result
        "hybrid": 0,       # script handles entirely
    },
    "file_scan_hit": {
        "description": "Per-file result from grep/search that needs analysis",
        "all_llm": 520,   # read grep line, Read tool, reason about usage, output
        "hybrid": 510,     # same minus grep parsing (judgment still dominates)
    },
    "render_section": {
        "description": "Report section rendered from structured data",
        "all_llm": 200,   # format table/section per template in SKILL.md
        "hybrid": 0,       # render script handles entirely
    },
    "dependency_graph_entry": {
        "description": "Transitive dependency path to trace",
        "all_llm": 130,   # parse graph line, trace path, output
        "hybrid": 0,       # script handles entirely
    },
    "build_target": {
        "description": "Dockerfile to analyze for Go build targets",
        "all_llm": 230,   # read Dockerfile, identify go build, classify
        "hybrid": 30,      # read JSON entry from script
    },
    "commit_or_item": {
        "description": "Per-commit or per-item processing in a loop",
        "all_llm": 350,   # parse data, validate, compare, output per item
        "hybrid": 50,      # read pre-processed JSON, judgment only
    },
}


def count_prose_lines(text):
    """Count non-empty, non-code-block, non-frontmatter lines."""
    lines = text.splitlines()
    in_block = False
    in_fm = False
    count = 0
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            continue
        if re.match(r"^```", line):
            in_block = not in_block
            continue
        if in_block:
            continue
        if line.strip():
            count += 1
    return count


def estimate_variable_units(text, analysis):
    """Estimate the number of variable-cost units from the skill text."""
    hints = analysis.get("extraction_hints", {})
    shell_blocks = analysis.get("code_blocks", {}).get("shell", 0)
    api_refs = hints.get("api_references", {}).get("count", 0)
    mech_ops = hints.get("mechanical_operations", 0)
    render_pats = hints.get("render_patterns", 0)

    step_count = analysis.get("headings", {}).get("step_numbered_count", 0)

    loop_re = re.compile(
        r"\b(?:for\s+each|per[- ](?:commit|file|hit|entry|target|item|result))"
        r"|\beach\s+(?:commit|file|hit|entry|target|item|result)\b",
        re.IGNORECASE,
    )
    loop_indicators = sum(1 for line in text.splitlines() if loop_re.search(line))

    grep_re = re.compile(r"\bgrep\b.*\bimport\b|\bsearch.*(?:import|usage|file)", re.IGNORECASE)
    file_scan_steps = sum(1 for line in text.splitlines() if grep_re.search(line))

    dockerfile_re = re.compile(r"\b(?:Dockerfile|build\s+target|container\s+image)", re.IGNORECASE)
    build_target_refs = sum(1 for line in text.splitlines() if dockerfile_re.search(line))

    dep_graph_re = re.compile(r"\b(?:go\s+mod\s+graph|transitive|dependency\s+graph)", re.IGNORECASE)
    dep_graph_refs = sum(1 for line in text.splitlines() if dep_graph_re.search(line))

    return {
        "shell_commands": shell_blocks,
        "api_calls": api_refs,
        "mechanical_comparisons": mech_ops,
        "file_scan_hits": min(file_scan_steps, 3),  # estimate typical hits
        "render_sections": render_pats,
        "dependency_graph_entries": min(dep_graph_refs, 5),
        "build_targets": min(build_target_refs, 3),
        "commits_or_items": min(loop_indicators, 5),
    }


def estimate(text, analysis):
    prose_lines = count_prose_lines(text)
    line_count = analysis.get("line_count", len(text.splitlines()))

    base_prompt_tokens = line_count * TOKENS_PER_LINE

    units = estimate_variable_units(text, analysis)

    # Map unit counts to cost categories
    unit_map = {
        "shell_commands": "shell_command",
        "api_calls": "api_call",
        "mechanical_comparisons": "mechanical_comparison",
        "file_scan_hits": "file_scan_hit",
        "render_sections": "render_section",
        "dependency_graph_entries": "dependency_graph_entry",
        "build_targets": "build_target",
        "commits_or_items": "commit_or_item",
    }

    all_llm_variable = 0
    hybrid_variable = 0
    breakdown = []

    for unit_key, cost_key in unit_map.items():
        count = units[unit_key]
        if count == 0:
            continue
        costs = UNIT_COSTS[cost_key]
        all_cost = count * costs["all_llm"]
        hyb_cost = count * costs["hybrid"]
        all_llm_variable += all_cost
        hybrid_variable += hyb_cost
        breakdown.append({
            "operation": costs["description"],
            "count": count,
            "all_llm_tokens": all_cost,
            "hybrid_tokens": hyb_cost,
            "savings": all_cost - hyb_cost,
            "per_unit_all_llm": costs["all_llm"],
            "per_unit_hybrid": costs["hybrid"],
        })

    # Hybrid SKILL.md is typically 25-35% the length of the original
    hybrid_prompt_ratio = 0.30
    hybrid_prompt_tokens = int(base_prompt_tokens * hybrid_prompt_ratio)

    all_llm_total = base_prompt_tokens + all_llm_variable
    hybrid_total = hybrid_prompt_tokens + hybrid_variable
    savings = all_llm_total - hybrid_total
    pct = (savings * 100 // all_llm_total) if all_llm_total > 0 else 0

    return {
        "skill_lines": line_count,
        "prose_lines": prose_lines,
        "base_prompt_tokens": {
            "all_llm": base_prompt_tokens,
            "hybrid": hybrid_prompt_tokens,
            "savings": base_prompt_tokens - hybrid_prompt_tokens,
        },
        "variable_costs": {
            "all_llm": all_llm_variable,
            "hybrid": hybrid_variable,
            "savings": all_llm_variable - hybrid_variable,
            "breakdown": breakdown,
        },
        "total": {
            "all_llm": all_llm_total,
            "hybrid": hybrid_total,
            "savings": savings,
            "savings_pct": pct,
        },
        "formula": {
            "all_llm": f"{base_prompt_tokens} + " + " + ".join(
                f"{b['count']}×{b['per_unit_all_llm']}" for b in breakdown
            ),
            "hybrid": f"{hybrid_prompt_tokens} + " + " + ".join(
                f"{b['count']}×{b['per_unit_hybrid']}" for b in breakdown
            ) if breakdown else str(hybrid_prompt_tokens),
        },
        "note": "Estimates assume typical invocation. Actual costs vary with input data. "
                "Per-unit costs derived from cve-validate and backport-review manual comparisons.",
    }


def main(argv):
    if len(argv) != 2:
        print("usage: estimate_savings.py <path-to-skill.md>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        return 1

    # Try reading analysis from stdin
    if not sys.stdin.isatty():
        try:
            analysis = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            print("invalid JSON on stdin, running analyze internally", file=sys.stderr)
            analysis = None
    else:
        analysis = None

    if analysis is None:
        # Run analyze_skill inline
        scripts_dir = Path(__file__).parent
        sys.path.insert(0, str(scripts_dir))
        from analyze_skill import analyze, parse_frontmatter
        analysis = analyze(text)

    result = estimate(text, analysis)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
