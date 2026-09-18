#!/usr/bin/env python3
"""Check every skills/<name>/SKILL.md: frontmatter is valid YAML, `name` equals
the directory name and follows the Agent Skills spec (lowercase a-z0-9 with
single hyphens, at most 64 chars), `description` is a non-empty string of at
most 1024 chars, and, when a skill ships agents/openai.yaml, that file parses
and, if it carries an `interface` block, that `display_name` and
`short_description` are both non-empty strings. Exit 1 on the first problem. Pass a repository root to check
a different tree. Requires PyYAML."""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)


def frontmatter(text: str):
    """Return the parsed frontmatter mapping, None if absent, or a str error."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return f"frontmatter is not valid YAML: {str(exc).splitlines()[0]}"
    return data if isinstance(data, dict) else "frontmatter is not a mapping"


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def check_skill(skill_md: Path) -> list[str]:
    d = skill_md.parent
    problems = []
    fm = frontmatter(skill_md.read_text(encoding="utf-8-sig"))
    if fm is None:
        return [f"{d.name}: no frontmatter"]
    if isinstance(fm, str):
        return [f"{d.name}: {fm}"]
    name = fm.get("name")
    if not _nonempty_str(name):
        problems.append(f"{d.name}: name missing")
    elif name != d.name:
        problems.append(f"{d.name}: frontmatter name {name!r} != directory name")
    if not NAME_RE.match(d.name):
        problems.append(f"{d.name}: name must be lowercase a-z0-9 with single hyphens")
    if len(d.name) > NAME_MAX:
        problems.append(f"{d.name}: name longer than {NAME_MAX} chars")
    desc = fm.get("description")
    if not _nonempty_str(desc):
        problems.append(f"{d.name}: description missing or empty")
    elif len(" ".join(desc.split())) > DESCRIPTION_MAX:
        problems.append(f"{d.name}: description is {len(desc)} chars (max {DESCRIPTION_MAX})")
    sidecar = d / "agents" / "openai.yaml"
    if sidecar.exists():
        try:
            meta = yaml.safe_load(sidecar.read_text(encoding="utf-8-sig"))
        except yaml.YAMLError as exc:
            return problems + [f"{d.name}: agents/openai.yaml is not valid YAML: {str(exc).splitlines()[0]}"]
        if not isinstance(meta, dict):
            return problems + [f"{d.name}: agents/openai.yaml is not a mapping"]
        interface = meta.get("interface")
        if interface is None:
            problems.append(f"{d.name}: agents/openai.yaml has no `interface` block "
                            "(display fields must sit under it)")
        elif not isinstance(interface, dict):
            problems.append(f"{d.name}: agents/openai.yaml `interface` is not a mapping")
        else:
            # The interface block is optional; once present, both display fields
            # must be filled (ChatGPT imports reject a half-filled block).
            for field in ("display_name", "short_description"):
                if not _nonempty_str(interface.get(field)):
                    problems.append(f"{d.name}: agents/openai.yaml interface.{field} missing or empty")
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
