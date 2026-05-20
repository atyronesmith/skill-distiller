#!/usr/bin/env python3
"""Analyze a SKILL.md and emit structural metadata as JSON.

Usage: analyze_skill.py <path-to-skill.md>
Output: JSON object to stdout
Exit codes:
  0 on success
  1 on file read error or argument error

stdlib only.
"""
import json
import re
import sys
from pathlib import Path


FRONTMATTER_DELIM = "---"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
STEP_RE = re.compile(r"^\s*step\s+\d+\b", re.IGNORECASE)
DECISION_RE = re.compile(r"\b(if|when|otherwise|else|unless)\b", re.IGNORECASE)
SHELL_LANGS = {"bash", "sh", "shell", "zsh"}

API_RE = re.compile(
    r"(?:REST\s*API|API\s*(?:endpoint|call|query|request|response))"
    r"|(?:GET|POST|PUT|DELETE)\s+https?://"
    r"|https?://[^\s)\"'>]+/(?:api|rest|v[0-9])/"
    r"|\bquery\s+(?:the\s+)?(?:\w+\s+)?(?:REST\s+)?API\b"
    r"|\bfetch\s+(?:the\s+)?(?:\w+\s+)?(?:ticket|issue|data|metadata)\b"
    r"|\b(?:WebSearch|WebFetch|MCP)\b"
    r"|\b(?:Gerrit|NVD|GitHub|Jira|GitLab)\s+(?:REST\s+)?API\b"
    r"|\bMCP\s*\(",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s)\"'>]+", re.IGNORECASE)

MECHANICAL_RE = re.compile(
    r"\bcompar(?:e|ing)\s+(?:version|string)"
    r"|\bversion\s+compar"
    r"|\b(?:semver|semantic\s+version)"
    r"|\bcheck\s+(?:if|whether|that)\b"
    r"|\bvalidat(?:e|ing)\s+that\b"
    r"|\bmatch(?:es|ing)?\s+against\b"
    r"|\bpass\s*/\s*fail\b"
    r"|\bfilter(?:ing)?\s+(?:to|by|out)\b"
    r"|\bsort(?:ing)?\s+(?:by|ascending|descending)\b"
    r"|\balready\s+fix(?:ed)?\b"
    r"|\bcurrent\s+version\b.*\bfix\s+version\b",
    re.IGNORECASE,
)

RENDER_RE = re.compile(
    r"\bproduc(?:e|ing)\s+(?:a\s+)?(?:structured\s+)?report\b"
    r"|\brender(?:ing)?\s+(?:the\s+)?(?:report|output|results)\b"
    r"|\bformat(?:ting)?\s+(?:as|to|into)\s+(?:markdown|html|table)\b"
    r"|\boutput\s+(?:a\s+)?(?:structured|formatted)\s+(?:markdown|report|table)\b"
    r"|\bstructured\s+(?:markdown\s+)?report\b"
    r"|\bwrite\s+(?:the\s+)?report\s+to\b"
    r"|\bgenerat(?:e|ing)\s+(?:a\s+)?report\b",
    re.IGNORECASE,
)


def parse_frontmatter(text):
    """Return (frontmatter_dict, body_text). Empty dict if no frontmatter."""
    if not text.startswith(FRONTMATTER_DELIM + "\n"):
        return {}, text
    end = text.find("\n" + FRONTMATTER_DELIM + "\n", len(FRONTMATTER_DELIM) + 1)
    if end == -1:
        return {}, text
    fm = {}
    block = text[len(FRONTMATTER_DELIM) + 1:end]
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m:
            val = m.group(2).strip()
            # Strip outer quotes (single or double) if present
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            fm[m.group(1)] = val
    body = text[end + len("\n" + FRONTMATTER_DELIM + "\n"):]
    return fm, body


def extract_hints(prose_lines):
    """Scan prose lines (outside code blocks) for extraction-relevant patterns."""
    api_hits = []
    urls = []
    mechanical_count = 0
    render_count = 0

    for line in prose_lines:
        if API_RE.search(line):
            api_hits.append(line.strip())
        for m in URL_RE.finditer(line):
            url = m.group(0)
            if any(seg in url for seg in ("/api/", "/rest/", "/v1/", "/v2/", "/v3/")):
                urls.append(url)
        if MECHANICAL_RE.search(line):
            mechanical_count += 1
        if RENDER_RE.search(line):
            render_count += 1

    return {
        "api_references": {
            "count": len(api_hits),
            "urls_with_api_paths": sorted(set(urls)),
        },
        "mechanical_operations": mechanical_count,
        "render_patterns": render_count,
    }


def analyze(text):
    lines = text.splitlines()
    frontmatter, _body = parse_frontmatter(text)

    in_block = False
    block_lang = None
    block_start = None
    code_blocks = []
    headings = []
    lang_counts = {}
    prose_lines = []

    for i, line in enumerate(lines):
        fence = FENCE_RE.match(line)
        if fence:
            if not in_block:
                in_block = True
                block_lang = (fence.group(1) or "plain").lower()
                block_start = i
            else:
                code_blocks.append({
                    "lang": block_lang,
                    "start_line": block_start + 1,
                    "end_line": i + 1,
                })
                lang_counts[block_lang] = lang_counts.get(block_lang, 0) + 1
                in_block = False
                block_lang = None
                block_start = None
            continue
        if in_block:
            continue
        prose_lines.append(line)
        h = HEADING_RE.match(line)
        if h:
            headings.append({
                "level": len(h.group(1)),
                "text": h.group(2).strip(),
                "line": i + 1,
            })

    shell_block_count = sum(1 for b in code_blocks if b["lang"] in SHELL_LANGS)
    step_heading_count = sum(1 for h in headings if STEP_RE.match(h["text"]))
    decision_count = sum(1 for ln in lines if DECISION_RE.search(ln))

    by_level = {str(lvl): sum(1 for h in headings if h["level"] == lvl)
                for lvl in range(1, 7)}
    top_level_sections = [h["text"] for h in headings if h["level"] == 2]

    return {
        "line_count": len(lines),
        "frontmatter": frontmatter,
        "headings": {
            "total": len(headings),
            "by_level": by_level,
            "top_level_sections": top_level_sections,
            "step_numbered_count": step_heading_count,
        },
        "code_blocks": {
            "total": len(code_blocks),
            "shell": shell_block_count,
            "by_lang": lang_counts,
        },
        "decision_keyword_count": decision_count,
        "extraction_hints": extract_hints(prose_lines),
    }


def main(argv):
    if len(argv) != 2:
        print("usage: analyze_skill.py <path-to-skill.md>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        return 1
    result = analyze(text)
    result["path"] = str(path)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
