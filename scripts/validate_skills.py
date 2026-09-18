#!/usr/bin/env python3
"""Check every skills/<name>/SKILL.md: frontmatter present, `name` equals the
directory name, `description` present, and agents/openai.yaml (if shipped) has the
two fields Codex/ChatGPT require. Exit 1 on the first problem."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fields, cur = {}, None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s?(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            cur = km.group(1)
            fields[cur] = km.group(2)
        elif cur:
            fields[cur] += "\n" + line
    return fields


def main() -> int:
    problems = []
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        d = skill_md.parent
        fm = frontmatter(skill_md.read_text(encoding="utf-8"))
        if not fm:
            problems.append(f"{d.name}: no frontmatter")
            continue
        if fm.get("name", "").strip() != d.name:
            problems.append(f"{d.name}: frontmatter name {fm.get('name')!r} != directory name")
        if not NAME_RE.match(d.name):
            problems.append(f"{d.name}: name must be lowercase a-z0-9 with single hyphens")
        if not fm.get("description", "").strip():
            problems.append(f"{d.name}: description missing")
        yaml = d / "agents" / "openai.yaml"
        if yaml.exists():
            y = yaml.read_text(encoding="utf-8")
            for field in ("display_name", "short_description"):
                if not re.search(rf"^\s*{field}:", y, re.M):
                    problems.append(f"{d.name}: agents/openai.yaml lacks interface.{field}")
    for p in problems:
        print("FAIL", p)
    if not problems:
        print("OK", len(list((ROOT / 'skills').glob('*/SKILL.md'))), "skill(s) valid")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
