#!/usr/bin/env python3
"""Freeze what a rewrite must preserve. Run on the ORIGINAL skill, once, before
any rewrite exists: an inventory taken from the rewrite could only agree with it.

Records, from the original skill directory:
  - the frontmatter block, byte for byte (the rewrite may not touch it)
  - a SHA-256 of every file (only SKILL.md may change; new files may appear
    under references/). Symlinks are neither followed nor frozen, and a
    symlinked SKILL.md is refused.
  - every sentence and heading carrying a rule word (must, never, not, no,
    only, unless, without, ...), with its position, its heading depth (the
    shallowest, for a heading that repeats), the heading it sits under, and
    whether it is a strong rule
  - every literal: inline code, runnable code lines, URLs, flags, versions,
    pins, dates, paths, numbers with a unit or bound
  - every code block, and every sentence and heading, so the gate can refuse
    text the original never had
  - the sentences nothing protects word for word (no rule word, no anchor),
    marking the ones whose literal is the only thing the gate checks
  - the requirement list the agent wrote. Each anchor is copied verbatim from
    the original, has at least 3 words, and sits inside exactly one sentence,
    heading or code line; that whole sentence is then protected word for word.

requirements.md format, one entry per requirement:
  R1: <the requirement in your own words>
    anchor: <text copied verbatim from one sentence of the original>

Usage:
  extract_requirements.py <skill-dir> --requirements requirements.md --dry-run
      check the list and print, in two groups, the sentences nothing protects
      yet and those protected only through a literal; writes nothing
  extract_requirements.py <skill-dir> --requirements requirements.md -o frozen.json
      freeze; refuses if frozen.json already exists
Exit 2 on a refusal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmd  # noqa: E402

REQ_RE = re.compile(r"^R(\d+):[ \t]*(\S.*?)\s*$")
ANCHOR_RE = re.compile(r"^[ \t]+anchor:[ \t]*(\S.*?)\s*$")
TERMINAL_WINDOW = 3
MIN_ANCHOR_WORDS = 3
FORMAT = 3   # verify_rewrite.py refuses any other


class FreezeError(ValueError):
    pass


def parse_requirements(text: str) -> list[dict]:
    reqs: list[dict] = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = REQ_RE.match(line)
        if m:
            rid = f"R{m.group(1)}"
            if any(r["id"] == rid for r in reqs):
                raise FreezeError(f"line {n}: {rid} appears twice")
            reqs.append({"id": rid, "requirement": m.group(2), "anchors": []})
            continue
        a = ANCHOR_RE.match(line)
        if a and reqs:
            reqs[-1]["anchors"].append(a.group(1))
            continue
        raise FreezeError(f"line {n}: not a requirement or an anchor: {line.strip()[:60]!r}")
    if not reqs:
        raise FreezeError("the requirement list is empty")
    for r in reqs:
        if not r["anchors"]:
            raise FreezeError(f"{r['id']} has no anchor")
    return reqs


def _targets(body: str) -> list[dict]:
    """Everything an anchor may point at: sentences, headings, code lines."""
    out = [{"kind": "sentence", "key": s["key"]} for s in skillmd.sentences(body)]
    for u in skillmd.units(body):
        if u["kind"] == "heading":
            out.append({"kind": "heading", "key": skillmd.normalise(u["text"])})
        elif u["kind"] == "code":
            out.append({"kind": "code", "key": " ".join(u["text"].split())})
    return out


def resolve_anchors(body: str, reqs: list[dict]) -> list[dict]:
    targets = _targets(body)
    problems, resolved = [], []
    for r in reqs:
        protects = []
        for a in r["anchors"]:
            na = skillmd.normalise(a)
            if len(na.split()) < MIN_ANCHOR_WORDS:
                problems.append(f"{r['id']}: anchor {a!r} is shorter than {MIN_ANCHOR_WORDS} words")
                continue
            hits = list({(t["kind"], t["key"]): t for t in targets if na in t["key"]}.values())
            if not hits:
                where = "the original" if na not in skillmd.flat(body) else "a single sentence"
                problems.append(f"{r['id']}: anchor {a!r} is not inside {where}")
            elif len(hits) > 1:
                problems.append(f"{r['id']}: anchor {a!r} occurs {len(hits)} times; quote more of the sentence")
            else:
                protects.append(hits[0])
        resolved.append({"id": r["id"], "requirement": r["requirement"], "protects": protects})
    if problems:
        raise FreezeError("; ".join(problems))
    return resolved


def unprotected(body: str, reqs: list[dict]) -> list[dict]:
    """Sentences with no rule word and no anchor. `literal_only` marks the ones that
    carry a literal: the gate checks that literal, not the rest of the sentence, so
    "If the build fails, run `make clean`" can lose its condition unless anchored."""
    lits = skillmd.literals(body)
    anchored = {p["key"] for r in reqs for p in r["protects"]}
    return [{"text": s["text"], "literal_only": any(skillmd.contains_literal(s["text"], lit) for lit in lits)}
            for s in skillmd.sentences(body)
            if not skillmd.is_rule(s["key"]) and s["key"] not in anchored]


def freeze(skill_dir, requirements_text: str) -> dict:
    skill_dir = Path(skill_dir)
    fm, body = skillmd.split_frontmatter(skillmd.read_text(skill_dir / "SKILL.md"))
    reqs = resolve_anchors(body, parse_requirements(requirements_text))

    sents = skillmd.sentences(body)
    order = skillmd.order(body)
    section_of: dict[str, str] = {}
    for s in sents:
        section_of.setdefault(s["key"], s["section"])
    for r in reqs:
        for target in r["protects"]:
            if target["kind"] == "sentence":
                target["section"] = section_of.get(target["key"], "")
    rules, seen = [], set()
    for s in sents:
        if skillmd.is_rule(s["key"]) and s["key"] not in seen:
            seen.add(s["key"])
            rules.append({"key": s["key"], "text": s["text"], "line": s["line"], "depth": s["depth"],
                          "index": order.index(s["key"]), "strong": skillmd.is_strong(s["key"]),
                          "section": s["section"]})
    # One entry per rule heading: the index of its first copy, and the shallowest
    # level any copy sits at (the same thing when it occurs once).
    rule_headings, seen = [], {}
    for u in skillmd.units(body):
        key = skillmd.normalise(u["text"])
        if u["kind"] == "heading" and skillmd.is_rule(u["text"]):
            if key in seen:
                seen[key]["depth"] = min(seen[key]["depth"], u["depth"])
                continue
            seen[key] = {"key": key, "index": order.index("# " + key), "depth": u["depth"]}
            rule_headings.append(seen[key])
    # A closing reminder: rule sentences in a short final section (after the last heading).
    last_heading = max((u["line"] for u in skillmd.units(body) if u["kind"] == "heading"), default=0)
    closing = [s["key"] for s in sents if s["line"] > last_heading]
    tail = closing if 0 < len(closing) <= TERMINAL_WINDOW else []
    return {
        "format": FORMAT,
        "frontmatter": fm,
        "body_chars": len(body),
        "files": {p.relative_to(skill_dir).as_posix(): skillmd.sha256_file(p)
                  for p in skillmd.package_files(skill_dir)},
        "rules": rules,
        "rule_headings": rule_headings,
        "terminal": sorted({k for k in tail if skillmd.is_rule(k)}),
        "literals": skillmd.literals(body),
        "order": order,
        "sentences": sorted({s["key"] for s in sents}),
        "headings": sorted({skillmd.normalise(u["text"]) for u in skillmd.units(body) if u["kind"] == "heading"}),
        "code_blocks": sorted({b["text"] for b in skillmd.code_blocks(body)}),
        "requirements": reqs,
        "unprotected": unprotected(body, reqs),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill_dir")
    ap.add_argument("--requirements", required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("-o", "--out")
    group.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    skill_dir = Path(args.skill_dir).expanduser()
    try:
        if not (skill_dir / "SKILL.md").is_file():
            raise FreezeError(f"no SKILL.md in {skill_dir}")
        if args.out and Path(args.out).expanduser().exists():
            raise FreezeError(f"{args.out} exists. Freeze once, before the rewrite; "
                              "if a requirement turns out wrong later, say so in the report")
        data = freeze(skill_dir, skillmd.read_text(Path(args.requirements).expanduser()))
    except (FreezeError, OSError, UnicodeDecodeError) as exc:
        print(f"freeze refused: {exc}", file=sys.stderr)
        return 2
    summary = (f"{len(data['requirements'])} requirements, {len(data['rules'])} rule sentences, "
               f"{len(data['literals'])} literals, {len(data['files'])} files")
    plain = [u["text"] for u in data["unprotected"] if not u["literal_only"]]
    literal = [u["text"] for u in data["unprotected"] if u["literal_only"]]
    if plain:
        print(f"{len(plain)} sentence(s) with no rule word, literal or anchor. "
              "Anchor each one that is an instruction, a condition or a reason:")
        for s in plain:
            print(f"  - {s}")
    if literal:
        print(f"{len(literal)} sentence(s) with a literal but no rule word or anchor: "
              "only the literal is checked; anchor it if it is an instruction:")
        for s in literal:
            print(f"  - {s}")
    if args.dry_run:
        print(f"dry run: {summary}; nothing written")
        return 0
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    Path(args.out).expanduser().write_text(text, encoding="utf-8")
    print(f"froze {summary} -> {args.out} (sha256 {hashlib.sha256(text.encode()).hexdigest()[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
