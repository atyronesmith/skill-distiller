#!/usr/bin/env python3
"""Score a skill's convertibility from the analysis output.

Usage: score_convertibility.py [--min-savings N] [--savings-json PATH]
  Reads analysis JSON on stdin (output of analyze_skill.py).
  Optionally reads savings estimate from --savings-json (output of estimate_savings.py).
Output: JSON object to stdout with recommendation and signals.
Exit codes:
  0 on success
  1 on invalid JSON input

The --min-savings threshold (default 1000, env SKILL_DISTILLER_MIN_SAVINGS)
sets the minimum estimated token savings for conversion to be worthwhile.

The heuristic is a starting point. The LLM should override the recommendation
when prose structure suggests otherwise.

stdlib only.
"""
import argparse
import json
import os
import sys


DEFAULT_MIN_SAVINGS = 1000


def score(analysis, savings_data=None, min_savings=DEFAULT_MIN_SAVINGS):
    lc = int(analysis.get("line_count", 0))
    shell = int(analysis.get("code_blocks", {}).get("shell", 0))
    steps = int(analysis.get("headings", {}).get("step_numbered_count", 0))
    decisions = int(analysis.get("decision_keyword_count", 0))
    sections = int(analysis.get("headings", {}).get("total", 0))

    procedural_score = (shell * 5) + (steps * 3) + min(decisions, 20)

    if lc < 150 and shell < 2 and steps < 2:
        recommendation = "skip_too_short"
        reason = ("Skill is under 150 lines with little procedural content. "
                  "Conversion overhead exceeds the win.")
    elif shell < 2 and steps < 2:
        recommendation = "skip_low_procedural"
        reason = ("Skill has few shell commands and no numbered workflow steps. "
                  "Likely style, voice, or reference material — not a procedural skill.")
    elif procedural_score >= 25:
        recommendation = "convert"
        reason = ("Procedural signals are strong (shell blocks + step headings + "
                  "decision keywords). Good candidate for hybrid refactor.")
    elif procedural_score >= 10:
        recommendation = "partial"
        reason = ("Some procedural content but mixed with judgment work. "
                  "Partial extraction may help. LLM should review.")
    else:
        recommendation = "skip_low_procedural"
        reason = ("Procedural score below threshold. "
                  "Most of the skill is prose or reference material.")

    # Savings-based override
    estimated_savings = None
    savings_pct = None
    savings_meets_threshold = None

    if savings_data:
        total = savings_data.get("total", {})
        estimated_savings = total.get("savings", 0)
        savings_pct = total.get("savings_pct", 0)
        savings_meets_threshold = (estimated_savings >= min_savings and savings_pct >= 20)

        if recommendation in ("convert", "partial") and not savings_meets_threshold:
            recommendation = "skip_low_savings"
            reason = (f"Estimated savings ({estimated_savings} tokens, {savings_pct}%) "
                      f"below threshold ({min_savings} tokens, 20%). "
                      "Conversion overhead likely exceeds the benefit.")

    result = {
        "recommendation": recommendation,
        "reason": reason,
        "signals": {
            "line_count": lc,
            "shell_block_count": shell,
            "step_heading_count": steps,
            "decision_keyword_count": decisions,
            "section_count": sections,
            "procedural_score": procedural_score,
        },
        "savings": {
            "estimated_savings": estimated_savings,
            "savings_pct": savings_pct,
            "min_savings_threshold": min_savings,
            "meets_threshold": savings_meets_threshold,
        },
        "note": ("This is a heuristic. The LLM should review the signals and "
                 "override the recommendation if the prose structure suggests "
                 "otherwise."),
    }
    return result


def main():
    p = argparse.ArgumentParser(description="Score a skill's convertibility.")
    p.add_argument("--min-savings", type=int,
                   default=int(os.environ.get("SKILL_DISTILLER_MIN_SAVINGS",
                                              DEFAULT_MIN_SAVINGS)),
                   help=f"Minimum token savings for conversion (default: {DEFAULT_MIN_SAVINGS})")
    p.add_argument("--savings-json",
                   help="Path to savings estimate JSON (from estimate_savings.py)")
    args = p.parse_args()

    try:
        analysis = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"invalid JSON on stdin: {e}", file=sys.stderr)
        return 1

    savings_data = None
    if args.savings_json:
        try:
            savings_data = json.loads(open(args.savings_json).read())
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: could not read savings JSON: {e}", file=sys.stderr)

    result = score(analysis, savings_data, args.min_savings)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
