#!/usr/bin/env python3
"""Check every plugins/ionden-skills/skills/<name>/SKILL.md: frontmatter is valid YAML, `name` equals
the directory name and follows the Agent Skills spec (lowercase a-z0-9 with
single hyphens, at most 64 chars), `description` is a non-empty string of at
most 1024 chars, and, when a skill ships agents/openai.yaml, that file parses
and, if it carries an `interface` block, that `display_name` and
`short_description` are both non-empty strings. With the packaging checks it also confirms that
plugins/ionden-skills/ is laid out as the Anthropic directory, claude.ai and Codex expect (skills
under its own skills/ folder, no custom skills path) and that it ships nothing but the skills. Exit 1 on the first problem. Pass a repository root to check a different tree. Requires PyYAML."""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = "plugins/ionden-skills"
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
ICON_MIN_PX = 128
SVG_TAG_RE = re.compile(r"<svg\b[^>]*>", re.I)
VIEWBOX_ATTR_RE = re.compile(r"""\bviewBox\s*=\s*(["'])(.*?)\1""")


def _icon_size(svg: str):
    """Width and height from the root <svg> tag's viewBox, or None if it has none we can read."""
    tag = SVG_TAG_RE.search(svg)
    attr = VIEWBOX_ATTR_RE.search(tag.group(0)) if tag else None
    parts = attr.group(2).replace(",", " ").split() if attr else []
    try:
        numbers = [float(x) for x in parts]
    except ValueError:
        return None
    return (numbers[2], numbers[3]) if len(numbers) == 4 else None
FENCE_RE = re.compile(r"^```.*?^```[^\n]*$", re.S | re.M)


def _load_json(path: Path, root: Path, problems: list[str]):
    rel = path.relative_to(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        problems.append(f"{rel}: missing")
        return None
    except json.JSONDecodeError as exc:
        problems.append(f"{rel}: not valid JSON ({exc.msg}, line {exc.lineno})")
        return None
    if not isinstance(data, dict):
        problems.append(f"{rel}: top level must be a JSON object")
        return None
    return data


def _stray(folder: Path, allowed: set[str]) -> list[str]:
    """Names in folder, dotfiles aside, that are not in allowed."""
    return sorted(e.name for e in folder.iterdir() if not e.name.startswith(".") and e.name not in allowed)


def check_plugin(root: Path) -> list[str]:
    """Packaging checks: the plugin at PLUGIN_DIR uses the documented layout, and it
    holds only what users need."""
    problems: list[str] = []
    P = PLUGIN_DIR
    pr = root / P
    sk = pr / "skills"
    names = sorted(p.parent.name for p in sk.glob("*/SKILL.md"))
    claude = _load_json(pr / ".claude-plugin" / "plugin.json", root, problems)
    codex = _load_json(pr / ".codex-plugin" / "plugin.json", root, problems)
    market = _load_json(root / ".claude-plugin" / "marketplace.json", root, problems)
    if isinstance(claude, dict) and "skills" in claude:
        problems.append(f"{P}/.claude-plugin/plugin.json: remove the skills key; the directory and claude.ai "
                        "load skills only from skills/<name>/, and custom paths work in Claude Code alone")
    if isinstance(codex, dict) and codex.get("skills") != "./skills/":
        problems.append(f'{P}/.codex-plugin/plugin.json: skills must be "./skills/", not {codex.get("skills")!r}')
    versions = {}
    for rel, manifest in ((f"{P}/.claude-plugin/plugin.json", claude), (f"{P}/.codex-plugin/plugin.json", codex)):
        if isinstance(manifest, dict):
            if _nonempty_str(manifest.get("version")):
                versions[rel] = manifest["version"]
            else:
                problems.append(f"{rel}: version missing or empty")
    if len(set(versions.values())) > 1:
        problems.append(f"plugin version differs: {versions}")
    if isinstance(market, dict):
        sources = [p.get("source") for p in market.get("plugins", []) if isinstance(p, dict)]
        if sources != [f"./{P}"]:
            problems.append(f'.claude-plugin/marketplace.json: plugin source {sources} must be ["./{P}"]')
    for stale in (".claude-plugin/plugin.json", ".codex-plugin", "skills"):
        if (root / stale).exists():
            problems.append(f"{stale}: left over from an earlier layout; the plugin lives in {P}/")
    if pr.is_dir():
        stray = _stray(pr, {"README.md", "LICENSE", "skills"})
        if stray:
            problems.append(f"{P}/: ships {stray}; the plugin folder holds only skills/, README.md, LICENSE "
                            "and the two manifest folders")
    if sk.is_dir():
        stray = _stray(sk, set(names))
        if stray:
            problems.append(f"{P}/skills/: ships {stray}; it holds only skill folders, each with a SKILL.md")
    for n in names:
        extra = _stray(sk / n, ALLOWED_SKILL_ENTRIES)
        if extra:
            problems.append(f"{n}: ships {extra}; a skill folder holds only "
                            f"{sorted(ALLOWED_SKILL_ENTRIES)} (evals go under evals/{n}/)")
    readme = pr / "README.md"
    if not readme.is_file():
        problems.append(f"{P}/README.md: missing (it is the plugin listing's description)")
    else:
        words = len(FENCE_RE.sub("", readme.read_text(encoding="utf-8-sig")).split())
        if words < LISTING_MIN_WORDS:
            problems.append(f"{P}/README.md: {words} words outside code blocks "
                            f"(the listing needs at least {LISTING_MIN_WORDS})")
    if not (pr / "LICENSE").is_file():
        problems.append(f"{P}/LICENSE: missing (the plugin folder must carry its own license)")
    icon = pr / ".claude-plugin" / "icon.svg"
    if not icon.is_file():
        problems.append(f"{P}/.claude-plugin/icon.svg: missing")
    else:
        size = _icon_size(icon.read_text(encoding="utf-8-sig"))
        if size is None:
            problems.append(f"{P}/.claude-plugin/icon.svg: no readable viewBox on the root <svg>, "
                            "so its size can't be checked")
        else:
            w, h = size
            if w != h or w < ICON_MIN_PX:
                problems.append(f"{P}/.claude-plugin/icon.svg: viewBox is {w:g}x{h:g}; "
                                f"the listing icon must be square and at least {ICON_MIN_PX} px")
    return problems


def main(root: Path = ROOT) -> int:
    skills = sorted((root / PLUGIN_DIR / "skills").glob("*/SKILL.md"))
    problems = [p for s in skills for p in check_skill(s)]
    if not skills:
        problems.append(f"no skills found under {root / PLUGIN_DIR / 'skills'}")
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
