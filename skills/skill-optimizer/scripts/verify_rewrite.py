#!/usr/bin/env python3
"""Gate a candidate rewrite against the frozen inventory of the original.

Every check is deterministic and needs no model call. The contract is
extractive: text may be deleted, reordered, reflowed or moved into a new
references/ file, and a clause may be dropped from a sentence that carries no
rule word and no anchor; nothing may be added, and a sentence with a rule word
or an anchor may not be edited at all. A sentence with neither is protected
only through its literals, if it has any. The one new sentence allowed per new
reference is the first body line naming it, with no strong rule word and at
most 25 words besides the path.

Deleting a rule sentence, rule heading or anchored sentence passes only when
the user approved that exact text (--approved) and it is gone whole. If a
candidate sentence (or heading) keeps some of its words in order, it was
trimmed, not deleted, and stays RULE_LOST or ANCHOR_LOST, naming that candidate
sentence, unless it is identical to another original sentence that survives
unchanged. A
literal lost with it passes only when every original sentence holding it was
approved and truly deleted, and no heading or code block of the original held
it; a literal that runs across sentences (`under 20` / `GiB`) is held by each
of them. Each approved deletion is listed.

Rejects (exit 1):
  ORIGINAL_CHANGED     the skill on disk is not the one that was frozen
  FRONTMATTER_CHANGED  any byte of the frontmatter differs
  FILE_CHANGED         a file other than SKILL.md differs or is missing
  UNEXPECTED_FILE      a new file outside references/*.md, a symlink anywhere, or a new
                       reference whose path already exists in the skill (as a file or link)
  NEW_TEXT             a sentence or heading uses words the original never put together
  CODE_EDITED          a code block that survives differs from every original block
  RULE_LOST            a sentence or heading with a rule word is gone or was edited
  ANCHOR_LOST          a sentence a requirement anchors is gone or was edited
  LITERAL_LOST         a command, path, flag, URL, version, date or threshold is gone or changed
  PROMINENCE_LOST      a strong rule or a rule heading has text in front of it that was behind
                       it, or sits deeper than it did (a rule heading the original repeats
                       has no single position; its shallowest copy may not sink below the
                       shallowest level it had)
  TERMINAL_MOVED       a closing rule no longer closes the body
  REFERENCE_UNLINKED   a new references/ file is not named in the body
  NOT_SMALLER          the body did not get smaller
Needs the user's decision (exit 3):
  MOVED_TO_REFERENCE   a rule or an anchored sentence now lives only in a new references/ file,
                       or a literal that ran across sentences moved there with all of them
                       and no longer reads as written
  SECTION_CHANGED      a rule or an anchored sentence now sits under a different heading
                       (a trimmed heading is the original heading it was cut from, when
                       exactly one fits and that original is not still in the body)
  EMPHASIS_LOST        a rule or an anchored sentence lost bold or italic it had (or bold
                       became italic); emphasis added or kept passes
Exit 0 with status `pass`, or `unchanged` when the candidate is the original.

Usage: verify_rewrite.py --frozen frozen.json --original <skill-dir> --candidate <dir>
                         [--approved approved.txt] [--json]
--original may name a skill whose SKILL.md is a link to a file named SKILL.md
(a per-file install); the gate reads that file. Exit 2 on a missing or
unreadable input, a candidate SKILL.md that is a symlink, an original SKILL.md
linked to anything but a SKILL.md, or a frozen file from an older
extract_requirements.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmd  # noqa: E402

NEW_REFERENCE_RE = re.compile(r"^references/[^/]+\.md$")
TERMINAL_WINDOW = 3
FORMAT = 3
LOAD_LINE_MAX_WORDS = 25


class FrozenFormatError(ValueError):
    pass


def verify(frozen: dict, candidate_dir, original_dir=None, approved=None) -> dict:
    """`approved`: rule sentences, rule headings or anchored sentences the user agreed may be deleted."""
    if frozen.get("format") != FORMAT:
        raise FrozenFormatError(f"the frozen file has format {frozen.get('format')!r}; this gate reads "
                                f"format {FORMAT}. It was written by an older extract_requirements.py")
    candidate_dir = Path(candidate_dir)
    approved = {skillmd.normalise(a) for a in (approved or ())}
    rejected: list[dict] = []
    confirm: list[dict] = []
    deleted: list[str] = []

    def reject(code: str, detail: str) -> None:
        rejected.append({"code": code, "detail": detail})

    def ask(detail: str, rel: str, code: str = "MOVED_TO_REFERENCE") -> None:
        confirm.append({"code": code, "file": rel, "detail": detail})

    def approve(key: str) -> None:
        if key not in deleted:
            deleted.append(key)

    if original_dir is not None:
        # A per-file install links SKILL.md to the real one; any other link is refused.
        original_md = skillmd.skill_md(Path(original_dir) / "SKILL.md")
        if skillmd.sha256_file(original_md) != frozen["files"]["SKILL.md"]:
            reject("ORIGINAL_CHANGED", "the skill's SKILL.md changed after it was frozen")

    fm, body = skillmd.split_frontmatter(skillmd.read_text(candidate_dir / "SKILL.md"))
    if fm != frozen["frontmatter"]:
        reject("FRONTMATTER_CHANGED", "the frontmatter must stay byte-identical")

    new_refs: dict[str, str] = {}
    for rel in skillmd.symlinks(candidate_dir):
        reject("UNEXPECTED_FILE", f"{rel} is a symlink; the gate does not follow links")
    present = set()
    for p in skillmd.package_files(candidate_dir):
        rel = p.relative_to(candidate_dir).as_posix()
        present.add(rel)
        if rel == "SKILL.md":
            continue
        if rel in frozen["files"]:
            if skillmd.sha256_file(p) != frozen["files"][rel]:
                reject("FILE_CHANGED", f"{rel} differs from the original")
        elif NEW_REFERENCE_RE.match(rel):
            new_refs[rel] = skillmd.read_text(p)
            # The snapshot skips links, so a per-file install can have a link (even
            # a dangling one) at this path; applying would write through or over it.
            if original_dir is not None and os.path.lexists(Path(original_dir) / rel):
                reject("UNEXPECTED_FILE", f"{rel} exists in the skill as a link or file; choose another name")
        else:
            reject("UNEXPECTED_FILE", f"{rel}: new files may only be references/<name>.md")
    for rel in frozen["files"]:
        if rel != "SKILL.md" and rel not in present:
            reject("FILE_CHANGED", f"{rel} is missing")

    body_sents = skillmd.sentences(body)
    # The one new sentence allowed per new reference: the first line naming it,
    # if it is short and carries no strong rule word. Any other is NEW_TEXT.
    load_keys, overlong = set(), {}
    for rel in new_refs:
        lines = [s for s in body_sents if rel in s["text"]]
        if not lines:
            reject("REFERENCE_UNLINKED", f"the body never names {rel}, so nothing tells the agent to read it")
            continue
        key = lines[0]["key"]
        words = [t for t in skillmd.tokens(key) if rel not in t]
        if skillmd.is_strong(key) or len(words) > LOAD_LINE_MAX_WORDS:
            overlong[key] = rel
        else:
            load_keys.add(key)

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
                why = (f"names {overlong[s['key']]}, but a load line may carry no strong rule word and at most "
                       f"{LOAD_LINE_MAX_WORDS} words besides the path" if s["key"] in overlong
                       else "is not cut from any original sentence")
                reject("NEW_TEXT", f"{where}: {s['text']!r} {why}")
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

    # An approved deletion must be a deletion. A candidate sentence (or heading)
    # whose words all fit, in order, inside the approved text is a trim of it,
    # unless it is itself another original sentence that survives unchanged.
    cand_text = {"sentence": {s["key"] for _, t in sources for s in skillmd.sentences(t)},
                 "heading": body_heads.union(*ref_heads.values())}
    orig_text = {"sentence": frozen["sentences"], "heading": frozen["headings"]}

    def trimmed(kind: str, key: str):
        """The candidate sentence (or heading) left of `key`, or None."""
        if kind not in cand_text:
            return None
        whole = skillmd.tokens(key)
        kept = {o for o in orig_text[kind] if o != key and o in cand_text[kind]}
        for c in sorted(cand_text[kind]):
            toks = skillmd.tokens(c)
            if toks and c not in kept and skillmd.is_subsequence(toks, whole):
                return c
        return None

    def deleted_with_approval(kind: str, key: str) -> bool:
        return key in approved and locate(kind, key) is None and trimmed(kind, key) is None

    def lost(key: str, kind: str) -> str:
        left = trimmed(kind, key) if key in approved else None
        return f"trimmed, not deleted: {left!r} is left of it" if left else "is gone or was edited"

    # Scope: a rule or anchored sentence still in the body must sit under the same
    # heading. A candidate heading is the original heading it was cut from: itself
    # if unchanged, else the one original heading whose words it keeps in order,
    # provided that heading is not still in the body. Otherwise it is a new section.
    def section_of(heading: str) -> str:
        if not heading or heading in frozen["headings"]:
            return heading
        toks = skillmd.tokens(heading)
        found = [o for o in frozen["headings"] if skillmd.is_subsequence(toks, skillmd.tokens(o))]
        return found[0] if len(found) == 1 and found[0] not in body_heads else heading

    section_now: dict[str, str] = {}
    for s in body_sents:
        section_now.setdefault(s["key"], section_of(s["section"]))
    asked_section = set()

    def same_section(key: str, text: str, section: str) -> None:
        if key in asked_section or section_now[key] == section:
            return
        asked_section.add(key)
        ask(f"{text!r} moved from section {section or '(top)'!r} to {section_now[key] or '(top)'!r}",
            "SKILL.md", "SECTION_CHANGED")

    for rule in frozen["rules"]:
        where = locate("sentence", rule["key"])
        if where is None and deleted_with_approval("sentence", rule["key"]):
            approve(rule["key"])
        elif where is None:
            reject("RULE_LOST", f"{rule['text']!r} {lost(rule['key'], 'sentence')}")
        elif where != "body":
            ask(f"{'strong rule' if rule['strong'] else 'rule'} moved: {rule['text']!r}", where)
        else:
            same_section(rule["key"], rule["text"], rule["section"])
    for head in frozen["rule_headings"]:
        where = locate("heading", head["key"])
        if where is None and deleted_with_approval("heading", head["key"]):
            approve(head["key"])
        elif where is None:
            reject("RULE_LOST", f"heading {head['key']!r} {lost(head['key'], 'heading')}")
        elif where != "body":
            ask(f"heading moved: {head['key']!r}", where)
    for req in frozen["requirements"]:
        for target in req["protects"]:
            where = locate(target["kind"], target["key"])
            if where is None and deleted_with_approval(target["kind"], target["key"]):
                approve(target["key"])
            elif where is None:
                reject("ANCHOR_LOST", f"{req['id']} ({req['requirement']}): {target['key']!r} "
                                      f"{lost(target['key'], target['kind'])}")
            elif where != "body":
                ask(f"{req['id']} moved: {target['key']!r}", where)
            elif target["kind"] == "sentence":
                same_section(target["key"], target["key"], target["section"])

    # Emphasis: a rule or an anchored sentence keeps every bold or italic phrase
    # it had, at least as strong, wherever it now lives. Stripping it asks the user.
    # A freeze from before the field existed is read from the original on disk.
    emph = frozen.get("emphasis")
    if emph is None and original_dir is not None:
        loud = {r["key"] for r in frozen["rules"]} | {t["key"] for r in frozen["requirements"]
                                                      for t in r["protects"] if t["kind"] == "sentence"}
        _, original_body = skillmd.split_frontmatter(skillmd.read_text(original_md))
        emph = {k: v for k, v in skillmd.emphasis(original_body).items() if k in loud}
    emph_now: dict[str, list] = {}
    for _, text in sources:
        for key, phrases in skillmd.emphasis(text).items():
            emph_now.setdefault(key, []).extend(phrases)
    rule_text = {r["key"]: r["text"] for r in frozen["rules"]}
    for key, phrases in sorted((emph or {}).items()):
        where = locate("sentence", key)
        if where is None:
            continue      # gone: RULE_LOST, ANCHOR_LOST or an approved deletion says so
        lost_here = [p for p, level in phrases if not skillmd.keeps_emphasis(p, level, emph_now.get(key, []))]
        if lost_here:
            ask(f"{rule_text.get(key, key)!r} lost the emphasis on " + ", ".join(repr(p) for p in lost_here),
                "SKILL.md" if where == "body" else where, "EMPHASIS_LOST")

    # Prominence: nothing that stood behind a strong rule or a rule heading may
    # stand in front of it, and it may not sit deeper than it did.
    first = {}
    for i, key in enumerate(frozen["order"]):
        first.setdefault(key, i)
    cand_order = skillmd.order(body)
    depth_now = {}
    for s in body_sents:
        depth_now.setdefault(s["key"], s["depth"])
    for u in skillmd.units(body):
        if u["kind"] == "heading":
            depth_now.setdefault("# " + skillmd.normalise(u["text"]), u["depth"])

    def prominence(label: str, key: str, index: int, depth: int) -> None:
        if key not in cand_order:
            return
        ahead = cand_order[:cand_order.index(key)]
        jumped = [k for k in ahead if k not in load_keys and first.get(k, -1) > index]
        if jumped:
            reject("PROMINENCE_LOST", f"{label} now has {jumped[0]!r} in front of it")
        elif depth_now[key] > depth:
            reject("PROMINENCE_LOST", f"{label} moved under a deeper heading (level {depth} -> {depth_now[key]})")

    for rule in frozen["rules"]:
        if rule["strong"]:
            prominence(repr(rule["text"]), rule["key"], rule["index"], rule["depth"])
    for head in frozen["rule_headings"]:
        # A heading the original repeats ("### Pitfalls to avoid" in two sections)
        # has no single position to keep; its shallowest copy may still not sink.
        if frozen["order"].count("# " + head["key"]) == 1:
            prominence(f"heading {head['key']!r}", "# " + head["key"], head["index"], head["depth"])
        else:
            levels = [u["depth"] for u in skillmd.units(body)
                      if u["kind"] == "heading" and skillmd.normalise(u["text"]) == head["key"]]
            if levels and min(levels) > head["depth"]:
                reject("PROMINENCE_LOST", f"heading {head['key']!r} now sits no higher than level "
                                          f"{min(levels)}; its highest copy was level {head['depth']}")

    tail = {s["key"] for s in body_sents[-TERMINAL_WINDOW:]}
    for key in frozen["terminal"]:
        if key not in tail and key not in deleted:
            reject("TERMINAL_MOVED", f"{key!r} closed the original and no longer closes the body")

    # A lost literal is approved only when every original sentence holding it was
    # approved and truly deleted (not trimmed), and no heading or code block of the
    # original held it. A literal that runs across sentences (`under 20` / `GiB`)
    # counts each of them as a holder. When those sentences all moved into the
    # same new reference, where the literal no longer reads as written, the user
    # decides. A freeze from before `literal_spans` has none.
    package = "\n".join(t for _, t in sources)
    spans = frozen.get("literal_spans", {})
    for lit in frozen["literals"]:
        if skillmd.contains_literal(package, lit):
            continue
        holders = [k for k in frozen["sentences"] if skillmd.contains_literal(k, lit)]
        across = sorted({k for run in spans.get(lit, ()) for k in run} - set(holders))
        holders += across
        elsewhere = any(skillmd.contains_literal(t, lit) for t in frozen["headings"] + frozen["code_blocks"])
        places = {locate("sentence", k) for k in holders}
        if holders and not elsewhere and all(deleted_with_approval("sentence", k) for k in holders):
            approve(f"literal: {lit}")
        elif across and not elsewhere and len(places) == 1 and places.isdisjoint({None, "body"}):
            ask(f"{lit!r} ran across sentences that moved together and no longer reads as written there: "
                + ", ".join(repr(k) for k in holders), places.pop())
        else:
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


def percent_change(before: int, after: int) -> str:
    """Signed percent change from `before` to `after`, one decimal place. Empty string when `before` is 0."""
    if not before:
        return ""
    return f"{(after - before) * 100 / before:+.1f}%"


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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, FrozenFormatError) as exc:
        print(f"cannot verify: {exc}", file=sys.stderr)
        return 2
    result["frozen_sha256"] = hashlib.sha256(raw).hexdigest()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        b, a = result["body_chars_before"], result["body_chars_after"]
        pct = f" ({percent_change(b, a)})" if b else ""
        print(f"{result['status'].upper()}  body {b:,} -> {a:,} chars{pct}, "
              f"{result['moved_chars']:,} chars moved to new references; "
              f"{result['requirements']} requirements, {result['unprotected']} unprotected sentences; "
              f"frozen {result['frozen_sha256'][:12]}")
        for f in result["rejected"]:
            print(f"  {f['code']}: {f['detail']}")
        for f in result["confirm"]:
            print(f"  ASK {f['code']} ({f['file']}): {f['detail']}")
        for d in result["approved_deletions"]:
            print(f"  deleted with the user's approval: {d}")
    return EXIT[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
