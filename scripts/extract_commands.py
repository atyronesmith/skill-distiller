#!/usr/bin/env python3
"""Extract embedded shell commands from a SKILL.md.

Usage: extract_commands.py <path-to-skill.md>
Output: JSON array to stdout. Each item: {start_line, end_line, lang, body}
Exit codes:
  0 on success
  1 on file read error or argument error

stdlib only.
"""
import json
import re
import sys
from pathlib import Path


FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
SHELL_LANGS = {"bash", "sh", "shell", "zsh"}


def extract(text):
    lines = text.splitlines()
    in_block = False
    block_lang = None
    block_start = None
    block_lines = []
    commands = []
    for i, line in enumerate(lines):
        fence = FENCE_RE.match(line)
        if fence:
            if not in_block:
                in_block = True
                block_lang = (fence.group(1) or "").lower()
                block_start = i
                block_lines = []
            else:
                if block_lang in SHELL_LANGS:
                    commands.append({
                        "start_line": block_start + 1,
                        "end_line": i + 1,
                        "lang": block_lang,
                        "body": "\n".join(block_lines),
                    })
                in_block = False
                block_lang = None
                block_start = None
                block_lines = []
            continue
        if in_block:
            block_lines.append(line)
    return commands


def main(argv):
    if len(argv) != 2:
        print("usage: extract_commands.py <path-to-skill.md>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        return 1
    commands = extract(text)
    json.dump(commands, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
