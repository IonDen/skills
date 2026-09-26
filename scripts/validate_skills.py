#!/usr/bin/env python3
"""Check every skills/<name>/SKILL.md: frontmatter is valid YAML, `name` equals
the directory name and follows the Agent Skills spec (lowercase a-z0-9 with
single hyphens, at most 64 chars), `description` is a non-empty string of at
most 1024 chars, and, when a skill ships agents/openai.yaml, that file parses
and, if it carries an `interface` block, that `display_name` and
`short_description` are both non-empty strings. With the packaging checks it also confirms that
`skills/` is the plugin root for Claude Code and Codex and that skill folders ship nothing but the
skill. Exit 1 on the first problem. Pass a repository root to check a different tree. Requires PyYAML."""
import json
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


ALLOWED_SKILL_ENTRIES = {"SKILL.md", "README.md", "LICENSE", "agents", "references", "scripts", "assets"}
LISTING_MIN_WORDS = 40
FENCE_RE = re.compile(r"^```.*?^```[^\n]*$", re.S | re.M)


def _load_json(path: Path, root: Path, problems: list[str]):
    rel = path.relative_to(root)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        problems.append(f"{rel}: missing")
    except json.JSONDecodeError as exc:
        problems.append(f"{rel}: not valid JSON ({exc.msg}, line {exc.lineno})")
    return None


def check_plugin(root: Path) -> list[str]:
    """Packaging checks: skills/ is the plugin root for both hosts, and each
    skill folder holds only what users need."""
    problems: list[str] = []
    sk = root / "skills"
    names = sorted(p.parent.name for p in sk.glob("*/SKILL.md"))
    claude = _load_json(sk / ".claude-plugin" / "plugin.json", root, problems)
    codex = _load_json(sk / ".codex-plugin" / "plugin.json", root, problems)
    market = _load_json(root / ".claude-plugin" / "marketplace.json", root, problems)
    if isinstance(claude, dict) and claude.get("skills") != ["./"]:
        problems.append('skills/.claude-plugin/plugin.json: skills must be ["./"], '
                        "the plugin root that holds the skill folders")
    if isinstance(codex, dict):
        got, want = codex.get("skills"), [f"./{n}" for n in names]
        if not isinstance(got, list):
            problems.append('skills/.codex-plugin/plugin.json: skills must list each folder as "./<name>"; '
                            'Codex installs a plugin whose skills is "./" but loads none of its skills')
        elif sorted(got) != want:
            problems.append(f"skills/.codex-plugin/plugin.json: skills {sorted(got)} != skill folders {want}")
    if isinstance(claude, dict) and isinstance(codex, dict) and claude.get("version") != codex.get("version"):
        problems.append(f"plugin version differs: Claude {claude.get('version')!r}, Codex {codex.get('version')!r}")
    if isinstance(market, dict):
        sources = [p.get("source") for p in market.get("plugins", []) if isinstance(p, dict)]
        if sources != ["./skills"]:
            problems.append(f'.claude-plugin/marketplace.json: plugin source {sources} must be ["./skills"]')
    for stale in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        if (root / stale).exists():
            problems.append(f"{stale}: a manifest at the repository root ships the whole repository; "
                            "the plugin lives in skills/")
    for n in names:
        extra = sorted(e.name for e in (sk / n).iterdir()
                       if not e.name.startswith(".") and e.name not in ALLOWED_SKILL_ENTRIES)
        if extra:
            problems.append(f"{n}: ships {extra}; a skill folder holds only "
                            f"{sorted(ALLOWED_SKILL_ENTRIES)} (evals go under evals/{n}/)")
    readme = sk / "README.md"
    if not readme.is_file():
        problems.append("skills/README.md: missing (it is the plugin listing's description)")
    else:
        words = len(FENCE_RE.sub("", readme.read_text(encoding="utf-8-sig")).split())
        if words < LISTING_MIN_WORDS:
            problems.append(f"skills/README.md: {words} words outside code blocks "
                            f"(the listing needs at least {LISTING_MIN_WORDS})")
    if not (sk / "LICENSE").is_file():
        problems.append("skills/LICENSE: missing (the plugin folder must carry its own license)")
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


def validate_all(root: Path = ROOT) -> int:
    code = main(root)
    problems = check_plugin(root)
    for p in problems:
        print("FAIL", p)
    if not problems:
        print("OK plugin packaging")
    return 1 if code or problems else 0


if __name__ == "__main__":
    sys.exit(validate_all(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT))
