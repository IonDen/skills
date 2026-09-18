#!/usr/bin/env python3
"""Check every skills/<name>/SKILL.md: frontmatter present, `name` equals the
directory name and follows the Agent Skills spec (lowercase a-z0-9 with single
hyphens, at most 64 chars), `description` present and at most 1024 chars, and
agents/openai.yaml (if shipped) has the two fields Codex/ChatGPT require.
Exit 1 on the first problem. Pass a repository root to check a different tree."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024


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


def check_skill(skill_md: Path) -> list[str]:
    d = skill_md.parent
    problems = []
    fm = frontmatter(skill_md.read_text(encoding="utf-8-sig"))
    if not fm:
        return [f"{d.name}: no frontmatter"]
    name = fm.get("name", "").strip()
    if name != d.name:
        problems.append(f"{d.name}: frontmatter name {name!r} != directory name")
    if not NAME_RE.match(d.name):
        problems.append(f"{d.name}: name must be lowercase a-z0-9 with single hyphens")
    if len(d.name) > NAME_MAX:
        problems.append(f"{d.name}: name longer than {NAME_MAX} chars")
    desc = " ".join(fm.get("description", "").split())
    if not desc:
        problems.append(f"{d.name}: description missing")
    elif len(desc) > DESCRIPTION_MAX:
        problems.append(f"{d.name}: description is {len(desc)} chars (max {DESCRIPTION_MAX})")
    yaml = d / "agents" / "openai.yaml"
    if yaml.exists():
        y = yaml.read_text(encoding="utf-8-sig")
        for field in ("display_name", "short_description"):
            if not re.search(rf"^\s*{field}:", y, re.M):
                problems.append(f"{d.name}: agents/openai.yaml lacks interface.{field}")
    return problems


def main(root: Path = ROOT) -> int:
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    problems = [p for s in skills for p in check_skill(s)]
    if not skills:
        problems.append(f"no skills found under {root / 'skills'}")
    for p in problems:
        print("FAIL", p)
    if not problems:
        print("OK", len(skills), "skill(s) valid")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT))
