#!/usr/bin/env python3
"""Generate a new SKILL.md from a structured spec on stdin.

Usage: generate_skill_skeleton.py
  Reads spec JSON on stdin. See SKILL.md of skill-distiller for the spec shape.
Output: SKILL.md content to stdout.
Exit codes:
  0 on success
  1 on invalid input

stdlib only.
"""
import json
import sys


REQUIRED_FIELDS = ["name", "description", "title", "summary", "steps", "outputs"]


def render_steps(steps):
    rendered = []
    for i, step in enumerate(steps, 1):
        kind = step.get("kind", "")
        purpose = step.get("purpose", "")
        if kind == "script":
            cmd = step.get("command", "")
            rendered.append(f"{i}. Run `{cmd}`. {purpose}")
        elif kind == "judgment":
            rendered.append(f"{i}. **[LLM judgment]** {purpose}")
        else:
            rendered.append(f"{i}. {purpose}")
    return "\n".join(rendered)


def render(spec):
    name = spec["name"]
    description = spec["description"]
    title = spec["title"]
    summary = spec["summary"]
    argument_hint = spec.get("argument_hint", "")
    allowed_tools = spec.get("allowed_tools", ["Bash", "Read", "Write"])
    steps_md = render_steps(spec["steps"])
    outputs_md = "\n".join(f"- {o}" for o in spec["outputs"])

    parts = [
        "---",
        f"name: {name}",
        f"description: \"{description}\"",
    ]
    if argument_hint:
        parts.append(f"argument-hint: {argument_hint}")
    parts.append(f"allowed-tools: {json.dumps(allowed_tools)}")
    parts.append("---")
    parts.append("")
    parts.append(f"# {title}")
    parts.append("")
    parts.append(summary)
    parts.append("")
    parts.append("## Workflow")
    parts.append("")
    parts.append(steps_md)
    parts.append("")
    parts.append("## Outputs")
    parts.append("")
    parts.append(outputs_md)
    parts.append("")
    parts.append("## Failure handling")
    parts.append("")
    parts.append("Any script returning a non-zero exit terminates the workflow. "
                 "Report the script name and stderr to the user and stop.")
    parts.append("")
    return "\n".join(parts)


def main():
    try:
        spec = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"invalid JSON on stdin: {e}", file=sys.stderr)
        return 1
    missing = [k for k in REQUIRED_FIELDS if k not in spec]
    if missing:
        print(f"missing required fields: {', '.join(missing)}", file=sys.stderr)
        return 1
    sys.stdout.write(render(spec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
