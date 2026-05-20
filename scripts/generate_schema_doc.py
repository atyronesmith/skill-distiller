#!/usr/bin/env python3
"""Generate a JSON Schema documentation markdown from a structured spec.

Usage: generate_schema_doc.py
  Reads spec JSON on stdin. Looks for the "scripts" field.
Output: markdown to stdout.
Exit codes:
  0 on success
  1 on invalid input

stdlib only.
"""
import json
import sys


HEADER = (
    "# Script JSON Schemas\n\n"
    "JSON Schema draft-07 contracts for each script in `scripts/`. "
    "Scripts emit a single JSON value on stdout; log to stderr.\n"
)


def render_script(s):
    parts = []
    parts.append(f"## `{s['name']}`\n")
    if s.get("invocation"):
        parts.append(f"**Invocation:** `{s['invocation']}`\n")
    if s.get("purpose"):
        parts.append(f"**Purpose:** {s['purpose']}\n")
    if s.get("output_schema"):
        parts.append("**Output schema:**\n")
        parts.append("```json")
        parts.append(json.dumps(s["output_schema"], indent=2))
        parts.append("```\n")
    if s.get("exit_codes"):
        parts.append(f"**Exit codes:** {s['exit_codes']}\n")
    if s.get("notes"):
        parts.append(f"**Notes:** {s['notes']}\n")
    return "\n".join(parts)


def main():
    try:
        spec = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"invalid JSON on stdin: {e}", file=sys.stderr)
        return 1
    if "scripts" not in spec or not isinstance(spec["scripts"], list):
        print("spec missing 'scripts' list", file=sys.stderr)
        return 1
    sys.stdout.write(HEADER + "\n")
    for s in spec["scripts"]:
        if "name" not in s:
            print("script entry missing 'name'", file=sys.stderr)
            return 1
        sys.stdout.write(render_script(s) + "\n---\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
