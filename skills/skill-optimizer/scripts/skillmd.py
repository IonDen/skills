"""Shared parsing for the skill-optimizer scripts. Standard library only.

A SKILL.md body is read as units: headings, lines inside code fences, table
cells, and paragraphs (soft-wrapped lines joined, the lines of one quote too;
list items and quotes kept apart). Paragraphs and cells split into sentences.
Every sentence the gate compares goes through normalise(), so reflowing a
paragraph or changing emphasis does not change a sentence, and any other edit
does. emphasis() keeps the bold and italic that normalise() drops, for the
gate's separate check on rules and anchored sentences.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\r?\n(?:.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.S)
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t#]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*([\w+-]*)")
# Fences in these languages hold examples and sample data. A whole block may be
# cut or moved; its lines are not literals. Every other fence, including one
# with no language, holds something to run, and each of its lines is a literal.
# Either way a block that survives must survive unedited.
EXAMPLE_LANGS = {"markdown", "md", "text", "txt", "plaintext", "json", "jsonc", "yaml", "yml",
                 "toml", "xml", "html", "csv", "diff", "mermaid"}
MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)]|>)\s+")
BLOCK_START_RE = re.compile(r"^\s*(?:[-*+]\s|\d{1,3}[.)]\s|\||>)")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+")
QUOTE_MARK_RE = re.compile(r"^\s*>[ \t]?")
# Any line-leading quote markers, nested ones included: `contains_literal` also
# reads the file with them removed, so a literal wrapped inside a quote is found.
QUOTE_MARKS_RE = re.compile(r"^[ \t]*(?:>[ \t]?)+", re.M)
# A sentence ends at . ! or ?, optionally followed by a closing quote or bracket.
SENTENCE_SPLIT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"'”’)\]]))\s+(?=[\"'(`*_\[]?[A-Z0-9])")
TABLE_ROW_RE = re.compile(r"^\s*\|")
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
TABLE_RULE_RE = re.compile(r"^:?-+:?$")
TOKEN_RE = re.compile(r"`[^`]+`|[\w][\w'’./:=+~-]*")

# A sentence carrying one of these is a rule: it may move, never change.
# Conditions ("if", "when") are deliberately not here: the freeze lists them
# as unprotected so the agent anchors the ones that are instructions.
RULE_WORD_RE = re.compile(
    r"\b(?:must|never|always|shall|only|unless|except|exceptions?|should|required|forbidden|"
    r"cannot|not|no|none|nothing|without|avoid|prefer|instead|until|other than|apart from|"
    r"even (?:if|when))\b|n['’]t\b",
    re.I,
)
# Rules that also keep their position: nothing new may be put in front of them.
STRONG_RE = re.compile(r"\b(?:must|never|always|shall|required|forbidden|cannot|do not)\b|\bdon['’]t\b", re.I)

BOUND_RE = re.compile(
    r"((?:under|over|below|above|at least|at most|up to|less than|more than|fewer than|"
    r"no more than|within|<=|>=|≤|≥|<|>)\s*~?\d+(?:[.,]\d+)*(?:\s?(?:%|×|[A-Za-z]+))?)",
    re.I,
)
THRESHOLD_RE = re.compile(
    r"(\d+(?:[.,]\d+)*\s?(?:%|[KMGT]i?B\b|ms\b|seconds?\b|sec\b|s\b|minutes?\b|min\b|hours?\b|h\b|"
    r"days?\b|tokens?\b|chars?\b|characters?\b|lines?\b|words?\b|bytes?\b|px\b|x\b|×))",
    re.I,
)
LITERAL_RES = [
    re.compile(r"`([^`\n]+)`"),                                   # inline code, kept exactly
    re.compile(r"(https?://[^\s`)>\]]+)"),                        # URLs
    re.compile(r"(?<![\w-])(--[A-Za-z][\w-]*(?:=[^\s`),;]+)?)"),  # bare long flags
    re.compile(r"\b([A-Za-z_][\w.-]*(?:==|>=|<=|~=|!=)[\w.*]+)"),  # version pins
    re.compile(r"(?<![\w.])(v?\d+(?:\.\d+)+\+?)"),                # versions: 3.10, 2.1.252+, v1.4.0
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),                       # dates
    BOUND_RE,                                                     # a number with its bound
    THRESHOLD_RE,                                                 # a number with its unit
]
PATH_RE = re.compile(r"(?<![\w/.~-])(~?/?(?:[\w.-]+/)+[\w.-]*)")


class SymlinkError(OSError):
    """A link where the scripts expect a real file. They never follow one: a link
    inside a skill can point anywhere, ~/.ssh included."""


def _real_file(path) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise SymlinkError(f"{path} is a symlink; the scripts do not follow links "
                           "(snapshot the skill with scripts/snapshot.py)")
    return path


def skill_md(path) -> Path:
    """The file to read for a skill's SKILL.md. A link is followed only when it
    resolves to a regular file named SKILL.md: a per-file install (stow,
    home-manager) of the skill the user named. Any other link is refused."""
    path = Path(path)
    if not path.is_symlink():
        return path
    target = path.resolve()
    if target.name != "SKILL.md" or not target.is_file():
        raise SymlinkError(f"{path} is a symlink to something other than a SKILL.md; "
                           "the scripts do not follow it")
    return target


def read_text(path) -> str:
    """Decode without newline translation, so a CRLF edit is still an edit."""
    return _real_file(path).read_bytes().decode("utf-8-sig")


def sha256_file(path) -> str:
    return hashlib.sha256(_real_file(path).read_bytes()).hexdigest()


SKIP_PARTS = {"__pycache__", ".git", ".DS_Store"}


def _walk(root: Path):
    """(path, is_link) for every file and directory under root, not descending into links."""
    for top, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS]
        for name in dirs + files:
            if name not in SKIP_PARTS:
                p = Path(top) / name
                yield p, p.is_symlink()


def package_files(root) -> list[Path]:
    """Real files of a skill directory, without caches, VCS data or Finder litter.
    Links are left out, and so is anything under a linked directory or outside the root."""
    root = Path(root)
    real_root = root.resolve()
    return sorted(p for p, link in _walk(root)
                  if not link and p.is_file() and p.suffix != ".pyc"
                  and p.resolve().is_relative_to(real_root))


def symlinks(root) -> list[str]:
    """Links inside a skill directory, as paths relative to it."""
    root = Path(root)
    return sorted(p.relative_to(root).as_posix() for p, link in _walk(root) if link)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter block with its delimiters, body). No frontmatter: ('', text)."""
    m = FRONTMATTER_RE.match(text)
    return (text[:m.end()], text[m.end():]) if m else ("", text)


# A code span: ``...`` (which may hold a single backtick) or `...`.
CODE_SPAN_RE = re.compile(r"(``[^`](?:[^`]|`(?!`))*?``|`[^`]*`)")


def _outside_code(s: str, fn) -> str:
    """Apply fn to the parts of s that fall outside a backtick code span, so a
    literal like `__init__.py` never gets its emphasis markers read as emphasis."""
    parts = CODE_SPAN_RE.split(s)
    for i in range(0, len(parts), 2):
        parts[i] = fn(parts[i])
    return "".join(parts)


ITALIC_RES = (re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])"),
              re.compile(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])"))


def _unemphasise(s: str) -> str:
    s = _outside_code(s, lambda p: p.replace("**", "").replace("__", ""))
    for pat in ITALIC_RES:
        s = _outside_code(s, lambda p, pat=pat: pat.sub(r"\1", p))
    return s


def _plain_parts(text: str):
    """(offset, part) for each part of text outside a code span."""
    pos = 0
    for i, part in enumerate(CODE_SPAN_RE.split(text)):
        if not i % 2:
            yield pos, part
        pos += len(part)


def _strip_marks(text: str, strength: list[int], found: list) -> tuple[str, list[int]]:
    """Drop the marker positions in `found` and raise the strength of what they enclose."""
    drop = set()
    for marks, (a, b), level in found:
        drop.update(marks)
        for k in range(a, b):
            strength[k] = max(strength[k], level)
    keep = [k for k in range(len(text)) if k not in drop]
    return "".join(text[k] for k in keep), [strength[k] for k in keep]


def _marked(s: str) -> tuple[str, list[int]]:
    """_unemphasise(s), step for step, with each remaining character's emphasis:
    2 inside bold (** or __), 1 inside italic (* or _), 0 outside."""
    text, strength = s, [0] * len(s)
    for marker in ("**", "__"):
        found, opened = [], None
        for off, part in _plain_parts(text):
            for m in re.finditer(re.escape(marker), part):
                at = off + m.start()
                if opened is None:
                    opened = at
                else:
                    found.append(([opened, opened + 1, at, at + 1], (opened + 2, at), 2))
                    opened = None
        if opened is not None:        # an unpaired marker is dropped too, and marks nothing
            found.append(([opened, opened + 1], (0, 0), 0))
        text, strength = _strip_marks(text, strength, found)
    for pat in ITALIC_RES:
        found = []
        for off, part in _plain_parts(text):
            for m in pat.finditer(part):
                a, b = off + m.start(), off + m.end() - 1
                found.append(([a, b], (a + 1, b), 1))
        text, strength = _strip_marks(text, strength, found)
    return text, strength


def emphasis(body: str) -> dict[str, list[list]]:
    """For each sentence or heading that has emphasis, its emphasised phrases as
    [normalised phrase, strength] pairs (2 bold, 1 italic). Sentences are keyed like
    sentences(), headings like order(): "# " and the heading's key."""
    out: dict[str, list[list]] = {}
    for u in units(body):
        if u["kind"] not in ("text", "heading"):
            continue
        text, strength = _marked(u["text"])
        start = 0
        ends = [(len(text), len(text))]
        if u["kind"] == "text":
            ends = [m.span() for m in SENTENCE_SPLIT_RE.finditer(text)] + ends
        for a, b in ends:
            key = normalise(text[start:a])
            if key and u["kind"] == "heading":
                key = "# " + key
            k = start
            while key and k < a:
                j = k
                while j < a and strength[j] == strength[k]:
                    j += 1
                phrase = normalise(text[k:j])
                if strength[k] and tokens(phrase) and [phrase, strength[k]] not in out.get(key, []):
                    out.setdefault(key, []).append([phrase, strength[k]])
                k = j
            start = b
    return {k: sorted(v) for k, v in out.items()}


def has_wrapped_quote(body: str) -> bool:
    """True when two `>` lines follow each other outside a code fence: a quote that
    skill-optimizer 1.0.x read line by line and this version reads as one paragraph."""
    fence, prev = None, False
    for line in body.splitlines():
        fm = FENCE_RE.match(line)
        if fence:
            if fm and fm.group(1)[0] == fence[0] and len(fm.group(1)) >= len(fence):
                fence = None
            continue
        if fm:
            fence, prev = fm.group(1), False
            continue
        quote = line.lstrip().startswith(">")
        if quote and prev:
            return True
        prev = quote
    return False


def keeps_emphasis(phrase: str, level: int, now: list[list]) -> bool:
    """True when some phrase in `now` is at least as strong and holds `phrase`'s words in a row."""
    want = tokens(phrase)
    for p, lvl in now:
        have = tokens(p)
        if lvl >= level and any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1)):
            return True
    return False


def normalise(s: str) -> str:
    hm = HEADING_RE.match(s)
    if hm:
        s = hm.group(2)
    s = MARKER_RE.sub("", s, count=1)
    s = _unemphasise(s)
    return " ".join(s.split()).rstrip(".;:,!?").strip()


def tokens(s: str) -> list[str]:
    """Words of a normalised sentence, lower-cased, punctuation dropped; inline code kept whole."""
    return [t.lower().rstrip(".,;:!?") for t in TOKEN_RE.findall(s)]


def is_subsequence(small: list[str], big: list[str]) -> bool:
    it = iter(big)
    return all(any(t == b for b in it) for t in small)


def _cells(row: str) -> list[str]:
    """Split a table row on each unescaped "|" outside a backtick code span, so
    `ps aux | grep mlx` stays one cell and one literal."""
    cells = [""]
    for i, part in enumerate(CODE_SPAN_RE.split(row)):
        if i % 2:
            cells[-1] += part
            continue
        pieces = CELL_SPLIT_RE.split(part)
        cells[-1] += pieces[0]
        cells.extend(pieces[1:])
    return cells


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def units(body: str) -> list[dict]:
    """Blocks as CommonMark reads them. The lines of one blockquote paragraph join
    into one unit, markers stripped. A `>` line indented four or more columns past
    the paragraph's text continues that paragraph. A `>` line that interrupts a
    paragraph or a list item starts a quote, and its unit carries `"interrupts": True`
    because that `>` may be a bound's comparator wrapped to the start of a line."""
    out: list[dict] = []
    para: list[str] = []
    para_line = 0
    para_col = 0          # the column the paragraph's text starts at
    para_quote = False    # the paragraph is inside a blockquote
    interrupts = False
    depth = 0
    fence = None
    lang = ""
    block = 0

    def flush() -> None:
        if para:
            text = MARKER_RE.sub("", " ".join(para), count=1)
            unit = {"kind": "text", "text": text, "line": para_line, "depth": depth}
            if interrupts:
                unit["interrupts"] = True
            out.append(unit)
            para.clear()

    for i, line in enumerate(body.splitlines(), 1):
        fm = FENCE_RE.match(line)
        if fence:
            if fm and fm.group(1)[0] == fence[0] and len(fm.group(1)) >= len(fence):
                fence = None
            elif line.strip():
                out.append({"kind": "code", "text": line.strip(), "line": i, "depth": depth,
                            "lang": lang, "block": block})
            continue
        if fm:
            flush()
            fence, lang = fm.group(1), fm.group(2).lower()
            block += 1
            continue
        hm = HEADING_RE.match(line)
        if hm:
            flush()
            depth = len(hm.group(1))
            out.append({"kind": "heading", "text": hm.group(2).strip(), "line": i, "depth": depth})
            continue
        if not line.strip():
            flush()
            continue
        if TABLE_ROW_RE.match(line):
            # Each cell is its own unit, so re-padding a row changes no sentence.
            flush()
            cells = [c.strip() for c in _cells(line) if c.strip()]
            if not all(TABLE_RULE_RE.match(c) for c in cells):
                out.extend({"kind": "text", "text": c, "line": i, "depth": depth} for c in cells)
            continue
        quote = line.lstrip().startswith(">")
        if quote and not QUOTE_MARK_RE.sub("", line, count=1).strip():
            flush()               # a bare `>`: a paragraph break inside the quote
            continue
        if para and quote:
            rest = QUOTE_MARK_RE.sub("", line, count=1)
            if para_quote and not (BLOCK_START_RE.match(rest) or HEADING_RE.match(rest)):
                para.append(rest.strip())     # the next line of the same quote
                continue
            if _indent(line) >= para_col + 4:
                para.append(line.strip())     # indented continuation, not a quote
                continue
        started_by = quote and bool(para) and not para_quote
        if para and BLOCK_START_RE.match(line):
            flush()
        if not para:
            para_line = i
            para_quote = quote
            interrupts = started_by
            m = LIST_ITEM_RE.match(line)
            para_col = m.end() if m else _indent(line)
        para.append(line.strip())
    flush()
    return out


def code_blocks(body: str) -> list[dict]:
    """Each fenced block as {lang, text}, text being its non-blank lines, stripped."""
    blocks: dict[int, dict] = {}
    for u in units(body):
        if u["kind"] == "code":
            b = blocks.setdefault(u["block"], {"lang": u["lang"], "lines": []})
            b["lines"].append(u["text"])
    return [{"lang": b["lang"], "text": "\n".join(b["lines"])} for b in blocks.values()]


def sentences(body: str) -> list[dict]:
    """Sentences in body order. `offset` counts the normalised text in front of each;
    `section` is the nearest heading above it ('' before the first heading)."""
    out, offset, section = [], 0, ""
    for u in units(body):
        if u["kind"] == "heading":
            section = normalise(u["text"])
        if u["kind"] != "text":
            offset += len(u["text"]) + 1
            continue
        for piece in SENTENCE_SPLIT_RE.split(_unemphasise(u["text"])):
            key = normalise(piece)
            if key:
                out.append({"key": key, "text": piece.strip(), "line": u["line"],
                            "depth": u["depth"], "offset": offset, "section": section})
                offset += len(key) + 1
    return out


def order(body: str) -> list[str]:
    """Headings and sentences in body order, as the keys the prominence check compares."""
    out = []
    for u in units(body):
        if u["kind"] == "heading":
            out.append("# " + normalise(u["text"]))
        elif u["kind"] == "text":
            out.extend(normalise(p) for p in SENTENCE_SPLIT_RE.split(_unemphasise(u["text"])) if normalise(p))
    return out


def flat(body: str) -> str:
    """Normalised text of every unit, one per line, for anchor searches."""
    return "\n".join(normalise(u["text"]) for u in units(body))


def _prose(sentence: str) -> str:
    """The sentence without inline code: `No module named build` is an error message, not a rule."""
    return re.sub(r"`[^`]*`", " ", sentence)


def is_rule(sentence: str) -> bool:
    return bool(RULE_WORD_RE.search(_prose(sentence)))


def is_strong(sentence: str) -> bool:
    return bool(STRONG_RE.search(_prose(sentence)))


def _looks_like_path(p: str) -> bool:
    last = p.rstrip("/").rsplit("/", 1)[-1]
    return (p.endswith("/") or p.startswith(("/", "~")) or p.count("/") >= 2
            or ("." in last.strip(".") and not last.endswith(".")))


def literals(body: str) -> list[str]:
    """Exact text that must survive: inline code, lines of runnable code fences,
    URLs, long flags, version pins, versions, dates, paths, and numbers that
    carry a unit or a bound. Text inside example fences is not scanned.

    Two passes. Each unit (a paragraph, a list item, a table cell, a heading) is
    scanned on its own, so every literal holds at least what one unit says. The
    joined text is scanned too, which keeps a bound whose unit starts the next
    paragraph (`under 20` / `GiB`); a match from that pass is kept only when the
    file holds it as written, so `≤ 0.20` at the end of a table row never joins
    the first word of the next row.

    A quote that interrupts a paragraph or a list item is scanned with its `>`
    put back, so `≤ 23 fits,` / `> 27 never` wrapped that way keeps `> 27 never`."""
    out, kept = set(), []
    for u in units(body):
        if u["kind"] == "code":
            if u["lang"] in EXAMPLE_LANGS:
                continue
            out.add(" ".join(u["text"].split()))
        text = "> " + u["text"] if u.get("interrupts") else u["text"]
        kept.append(text)
        out.update(_scan(text))
    out.update(v for v in _scan("\n".join(kept)) if contains_literal(body, v))
    return sorted(out)


def _scan(text: str) -> set[str]:
    """Literal patterns over one piece of text, each match on token boundaries."""
    found = set()
    for pat in LITERAL_RES:
        for m in pat.finditer(text):
            v = " ".join(m.group(1).split())
            if pat is not LITERAL_RES[0]:
                v = v.rstrip(".,;:")
            if v:
                found.add(v)
    for m in PATH_RE.finditer(text):
        v = m.group(1).rstrip(".,;:")
        if _looks_like_path(v):
            found.add(v)
    return {w for v in found for w in _on_boundaries(text, v)}


def _on_boundaries(text: str, literal: str) -> list[str]:
    """The literal as `contains_literal` will look for it. A match inside a longer
    token (`v0.156.1` in `rust-v0.156.1`) is widened to that token, so the freeze
    never records a literal the survival check cannot find again."""
    if contains_literal(text, literal):
        return [literal]
    hay = " ".join(text.split())
    lit = " ".join(literal.split())
    out = []
    for m in re.finditer(re.escape(lit), hay):
        start, end = m.start(), m.end()
        while start and re.match(r"[\w./-]", hay[start - 1]):
            start -= 1
        while end < len(hay) and re.match(r"[\w/-]", hay[end]):
            end += 1
        out.append(hay[start:end])
    return out or [literal]


def contains_literal(haystack: str, literal: str) -> bool:
    """True when `literal` occurs in `haystack` on token boundaries, so `20 GiB`
    is not found inside `120 GiB`, `pytest -q` not inside `pytest -qq`, and
    `main` not inside `origin/main`. The haystack is read twice: as written, and
    with line-leading quote markers removed, so `under 20` / `GiB` wrapped inside
    a blockquote (`> under 20` / `> GiB`) is still found."""
    lit = " ".join(literal.split())
    pattern = re.compile(r"(?<![\w./-])" + re.escape(lit) + r"(?![\w/-])")
    return any(pattern.search(" ".join(h.split()))
               for h in (haystack, QUOTE_MARKS_RE.sub("", haystack)))
