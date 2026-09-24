"""Shared parsing for the skill-optimizer scripts. Standard library only.

A SKILL.md body is read as units: headings, lines inside code fences, table
cells, and paragraphs (soft-wrapped lines joined; list items and quotes kept
apart). Paragraphs and cells split into sentences. Everything the gate compares goes
through normalise(), so reflowing a paragraph or dropping emphasis is not a
change, and any other edit to a sentence is.
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


def _unemphasise(s: str) -> str:
    s = _outside_code(s, lambda p: p.replace("**", "").replace("__", ""))
    s = _outside_code(s, lambda p: re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"\1", p))
    s = _outside_code(s, lambda p: re.sub(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", r"\1", p))
    return s


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


def units(body: str) -> list[dict]:
    out: list[dict] = []
    para: list[str] = []
    para_line = 0
    depth = 0
    fence = None
    lang = ""
    block = 0

    def flush() -> None:
        if para:
            text = MARKER_RE.sub("", " ".join(para), count=1)
            out.append({"kind": "text", "text": text, "line": para_line, "depth": depth})
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
        if para and BLOCK_START_RE.match(line):
            flush()
        if not para:
            para_line = i
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
    carry a unit or a bound. Text inside example fences is not scanned."""
    found = set()
    kept = []
    for u in units(body):
        if u["kind"] == "code":
            if u["lang"] in EXAMPLE_LANGS:
                continue
            found.add(" ".join(u["text"].split()))
        kept.append(u["text"])
    text = "\n".join(kept)
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
    return sorted({w for v in found for w in _on_boundaries(text, v)})


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
    `main` not inside `origin/main`."""
    hay = " ".join(haystack.split())
    lit = " ".join(literal.split())
    return re.search(r"(?<![\w./-])" + re.escape(lit) + r"(?![\w/-])", hay) is not None
