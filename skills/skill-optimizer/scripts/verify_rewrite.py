#!/usr/bin/env python3
"""Gate a candidate rewrite against the frozen inventory of the original.

Every check is deterministic and needs no model call. The contract is
extractive: text may be deleted, reordered, reflowed or moved into a new
references/ file, and a clause may be dropped from a sentence that carries no
rule word and no anchor; nothing may be added, and a sentence with a rule word
or an anchor may not be edited at all.

Rejects (exit 1):
  ORIGINAL_CHANGED     the skill on disk is not the one that was frozen
  FRONTMATTER_CHANGED  any byte of the frontmatter differs
  FILE_CHANGED         a file other than SKILL.md differs or is missing
  UNEXPECTED_FILE      a new file outside references/*.md
  NEW_TEXT             a sentence or heading uses words the original never put together
  CODE_EDITED          a code block that survives differs from every original block
  RULE_LOST            a sentence or heading with a rule word is gone or was edited
  ANCHOR_LOST          a sentence a requirement anchors is gone or was edited
  LITERAL_LOST         a command, path, flag, URL, version, date or threshold is gone or changed
  PROMINENCE_LOST      a strong rule has text in front of it that was behind it, or a deeper heading
  TERMINAL_MOVED       a closing rule no longer closes the body
  REFERENCE_UNLINKED   a new references/ file is not named in the body
  NOT_SMALLER          the body did not get smaller
Needs the user's decision (exit 3):
  MOVED_TO_REFERENCE   a rule or an anchored sentence now lives only in a new references/ file
Exit 0 with status `pass`, or `unchanged` when the candidate is the original.

Usage: verify_rewrite.py --frozen frozen.json --original <skill-dir> --candidate <dir> [--json]
Exit 2 on a missing or unreadable input.
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

NEW_REFERENCE_RE = re.compile(r"^references/[^/]+\.md$")
TERMINAL_WINDOW = 3


def verify(frozen: dict, candidate_dir, original_dir=None, approved=None) -> dict:
    """`approved`: normalised rule sentences or headings the user agreed may be deleted."""
    candidate_dir = Path(candidate_dir)
    approved = {skillmd.normalise(a) for a in (approved or ())}
    rejected: list[dict] = []
    confirm: list[dict] = []
    deleted: list[str] = []

    def reject(code: str, detail: str) -> None:
        rejected.append({"code": code, "detail": detail})

    def ask(detail: str, rel: str) -> None:
        confirm.append({"code": "MOVED_TO_REFERENCE", "file": rel, "detail": detail})

    if original_dir is not None:
        if skillmd.sha256_file(Path(original_dir) / "SKILL.md") != frozen["files"]["SKILL.md"]:
            reject("ORIGINAL_CHANGED", "the skill's SKILL.md changed after it was frozen")

    fm, body = skillmd.split_frontmatter(skillmd.read_text(candidate_dir / "SKILL.md"))
    if fm != frozen["frontmatter"]:
        reject("FRONTMATTER_CHANGED", "the frontmatter must stay byte-identical")

    new_refs: dict[str, str] = {}
    for p in skillmd.package_files(candidate_dir):
        rel = p.relative_to(candidate_dir).as_posix()
        if rel == "SKILL.md":
            continue
        if rel in frozen["files"]:
            if skillmd.sha256_file(p) != frozen["files"][rel]:
                reject("FILE_CHANGED", f"{rel} differs from the original")
        elif NEW_REFERENCE_RE.match(rel):
            new_refs[rel] = skillmd.read_text(p)
        else:
            reject("UNEXPECTED_FILE", f"{rel}: new files may only be references/<name>.md")
    for rel in frozen["files"]:
        if rel != "SKILL.md" and not (candidate_dir / rel).is_file():
            reject("FILE_CHANGED", f"{rel} is missing")

    body_sents = skillmd.sentences(body)
    load_keys = set()
    for rel in new_refs:
        lines = [s for s in body_sents if rel in s["text"]]
        if not lines:
            reject("REFERENCE_UNLINKED", f"the body never names {rel}, so nothing tells the agent to read it")
        else:
            load_keys.add(lines[0]["key"])

    # Extractive: every sentence and heading must come from one original sentence or heading.
    orig_sents = [skillmd.tokens(k) for k in frozen["sentences"]]
    orig_heads = [skillmd.tokens(k) for k in frozen["headings"]]
    sources = [("SKILL.md", body)] + list(new_refs.items())
    for where, text in sources:
        for s in skillmd.sentences(text):
            if s["key"] in load_keys:
                continue
            toks = skillmd.tokens(s["key"])
            if not any(skillmd.is_subsequence(toks, o) for o in orig_sents):
                reject("NEW_TEXT", f"{where}: {s['text']!r} is not cut from any original sentence")
        for u in skillmd.units(text):
            if u["kind"] == "heading":
                toks = skillmd.tokens(skillmd.normalise(u["text"]))
                if not any(skillmd.is_subsequence(toks, o) for o in orig_heads):
                    reject("NEW_TEXT", f"{where}: heading {u['text']!r} is not cut from any original heading")
        for block in skillmd.code_blocks(text):
            if block["text"] not in frozen["code_blocks"]:
                reject("CODE_EDITED", f"{where}: a code block differs from every original block: "
                                      f"{block['text'][:60]!r}")

    body_keys = {s["key"] for s in body_sents}
    body_heads = {skillmd.normalise(u["text"]) for u in skillmd.units(body) if u["kind"] == "heading"}
    ref_keys = {rel: {s["key"] for s in skillmd.sentences(t)} for rel, t in new_refs.items()}
    ref_heads = {rel: {skillmd.normalise(u["text"]) for u in skillmd.units(t) if u["kind"] == "heading"}
                 for rel, t in new_refs.items()}
    package_code = {" ".join(u["text"].split()) for _, t in sources
                    for u in skillmd.units(t) if u["kind"] == "code"}

    def locate(kind: str, key: str):
        """'body', a reference path, or None."""
        if kind == "code":
            return "body" if key in package_code else None
        in_body, in_refs = (body_heads, ref_heads) if kind == "heading" else (body_keys, ref_keys)
        if key in in_body:
            return "body"
        return next((rel for rel, keys in in_refs.items() if key in keys), None)

    for rule in frozen["rules"]:
        where = locate("sentence", rule["key"])
        if where is None and rule["key"] in approved:
            deleted.append(rule["key"])
        elif where is None:
            reject("RULE_LOST", f"{rule['text']!r} is gone or was edited")
        elif where != "body":
            ask(f"{'strong rule' if rule['strong'] else 'rule'} moved: {rule['text']!r}", where)
    for head in frozen["rule_headings"]:
        where = locate("heading", head)
        if where is None and head in approved:
            deleted.append(head)
        elif where is None:
            reject("RULE_LOST", f"heading {head!r} is gone or was edited")
        elif where != "body":
            ask(f"heading moved: {head!r}", where)
    for req in frozen["requirements"]:
        for target in req["protects"]:
            where = locate(target["kind"], target["key"])
            if where is None:
                reject("ANCHOR_LOST", f"{req['id']} ({req['requirement']}): {target['key']!r} is gone or was edited")
            elif where != "body":
                ask(f"{req['id']} moved: {target['key']!r}", where)

    # Prominence: nothing that stood behind a strong rule may stand in front of it.
    first = {}
    for i, key in enumerate(frozen["order"]):
        first.setdefault(key, i)
    cand_order = skillmd.order(body)
    depth_now = {}
    for s in body_sents:
        depth_now.setdefault(s["key"], s["depth"])
    for rule in frozen["rules"]:
        if not rule["strong"] or rule["key"] not in cand_order:
            continue
        ahead = cand_order[:cand_order.index(rule["key"])]
        jumped = [k for k in ahead if k not in load_keys and first.get(k, -1) > rule["index"]]
        if jumped:
            reject("PROMINENCE_LOST", f"{rule['text']!r} now has {jumped[0]!r} in front of it")
        elif depth_now[rule["key"]] > rule["depth"]:
            reject("PROMINENCE_LOST",
                   f"{rule['text']!r} moved under a deeper heading (level {rule['depth']} -> {depth_now[rule['key']]})")

    tail = {s["key"] for s in body_sents[-TERMINAL_WINDOW:]}
    for key in frozen["terminal"]:
        if key not in tail and key not in deleted:
            reject("TERMINAL_MOVED", f"{key!r} closed the original and no longer closes the body")

    package = "\n".join(t for _, t in sources)
    for lit in frozen["literals"]:
        if not skillmd.contains_literal(package, lit):
            reject("LITERAL_LOST", f"{lit!r} is gone or changed")

    before, after = frozen["body_chars"], len(body)
    unchanged = (skillmd.sha256_file(candidate_dir / "SKILL.md") == frozen["files"]["SKILL.md"]
                 and not new_refs)
    if not unchanged and after >= before:
        reject("NOT_SMALLER", f"the body is {after:,} chars against {before:,}")

    if rejected:
        status = "rejected"
    elif confirm:
        status = "needs_confirmation"
    else:
        status = "unchanged" if unchanged else "pass"
    return {"status": status, "rejected": rejected, "confirm": confirm,
            "body_chars_before": before, "body_chars_after": after,
            "moved_chars": sum(len(t) for t in new_refs.values()),
            "approved_deletions": deleted,
            "requirements": len(frozen["requirements"]),
            "unprotected": len(frozen["unprotected"])}


EXIT = {"pass": 0, "unchanged": 0, "rejected": 1, "needs_confirmation": 3}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frozen", required=True)
    ap.add_argument("--original", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--approved", help="file of rule sentences the user agreed may be deleted, one per line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        raw = Path(args.frozen).expanduser().read_bytes()
        frozen = json.loads(raw.decode("utf-8"))
        approved = ([ln for ln in skillmd.read_text(Path(args.approved).expanduser()).splitlines() if ln.strip()]
                    if args.approved else None)
        result = verify(frozen, Path(args.candidate).expanduser(), Path(args.original).expanduser(), approved)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        print(f"cannot verify: {exc}", file=sys.stderr)
        return 2
    result["frozen_sha256"] = hashlib.sha256(raw).hexdigest()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        b, a = result["body_chars_before"], result["body_chars_after"]
        pct = f" ({(a - b) * 100 // b:+d}%)" if b else ""
        print(f"{result['status'].upper()}  body {b:,} -> {a:,} chars{pct}, "
              f"{result['moved_chars']:,} chars moved to new references; "
              f"{result['requirements']} requirements, {result['unprotected']} unprotected sentences; "
              f"frozen {result['frozen_sha256'][:12]}")
        for f in result["rejected"]:
            print(f"  {f['code']}: {f['detail']}")
        for f in result["confirm"]:
            print(f"  ASK {f['code']} ({f['file']}): {f['detail']}")
        for d in result["approved_deletions"]:
            print(f"  deleted with the user's approval: {d!r}")
    return EXIT[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
