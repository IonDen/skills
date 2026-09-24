#!/usr/bin/env python3
"""Report what a skill costs, in two parts paid at different times.

  listing  description + when_to_use: in context every turn.
  body     the rest of SKILL.md: loaded when the skill runs.

Sizes are characters; `tokens_est` is characters / 4, an estimate. There is no
target: the report says how big a skill is, not how big it should be. Notes
mark a description over a documented limit, because text past a limit is
dropped or rejected, not because a smaller number is better.

Usage: measure_skills.py <skill-dir | SKILL.md> [...] [--json]
Exit 2 when a path does not exist or has no SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmd  # noqa: E402

SPEC_DESCRIPTION_MAX = 1024   # agentskills.io/specification
LISTING_DEFAULT_CAP = 1536    # Claude Code's default per-skill listing cap; the README cites the source

KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")


def _scalar(first: str, rest: list[str]) -> str:
    first = first.strip()
    if first[:1] in (">", "|"):
        lines = [ln.strip() for ln in rest]
        return (" " if first[0] == ">" else "\n").join(lines).strip()
    text = " ".join([first] + [ln.strip() for ln in rest]).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1].replace("''", "'")
    return text


def fields(frontmatter: str) -> dict:
    """Top-level scalar fields of a frontmatter block. Nested mappings are skipped."""
    lines = frontmatter.splitlines()[1:-1]
    out, key, first, rest = {}, None, "", []
    for line in lines + ["__end__:"]:
        m = KEY_RE.match(line)
        if m and not line[:1].isspace():
            if key is not None:
                out[key] = _scalar(first, rest)
            key, first, rest = m.group(1), m.group(2), []
        elif key is not None and line.strip():
            rest.append(line)
    return out


def skill_file(path: Path) -> Path:
    path = Path(path).expanduser()
    return path / "SKILL.md" if path.is_dir() else path


def measure(path) -> dict:
    p = skill_file(path)
    fm, body = skillmd.split_frontmatter(skillmd.read_text(p))
    f = fields(fm)
    description, when = f.get("description", ""), f.get("when_to_use", "")
    listing = len(description) + len(when)
    notes = []
    if len(description) > SPEC_DESCRIPTION_MAX:
        notes.append(f"DESCRIPTION_OVER_SPEC_LIMIT: description is {len(description)} chars; "
                     f"the Agent Skills spec allows {SPEC_DESCRIPTION_MAX}")
    if listing > LISTING_DEFAULT_CAP:
        notes.append(f"LISTING_OVER_DEFAULT_CAP: description + when_to_use is {listing} chars; "
                     f"Claude Code shows the first {LISTING_DEFAULT_CAP} by default")
    return {
        "path": str(p),
        "name": f.get("name") or p.parent.name,
        "description_chars": len(description),
        "listing_chars": listing,
        "body_chars": len(body),
        "body_lines": len(body.splitlines()),
        "body_tokens_est": len(body) // 4,
        "notes": notes,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    missing = [p for p in args.paths if not skill_file(Path(p)).is_file()]
    if missing:
        for p in missing:
            print(f"not found: {p} (expected a skill directory or a SKILL.md file)", file=sys.stderr)
        return 2
    try:
        rows = [measure(p) for p in args.paths]
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print(f"{r['name']}: listing {r['listing_chars']:,} chars (every turn); "
              f"body {r['body_chars']:,} chars, {r['body_lines']} lines, "
              f"~{r['body_tokens_est']:,} tokens est. (when it runs)")
        for n in r["notes"]:
            print(f"  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
