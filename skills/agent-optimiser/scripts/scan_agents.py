#!/usr/bin/env python3
"""Scan Claude Code subagent definition files and report optimisation signals.

Deterministic pass that does the measuring so the skill can spend its reasoning
on judgement calls. Parses YAML-ish frontmatter (line based, tolerant of the
JSON-escaped multi-line `description` strings the agent-creator emits), counts
sizes, estimates tokens (~chars/4), and raises heuristic flags.

Usage:
    python scan_agents.py [PATH ...] [--json] [--body-lines N] [--desc-chars N]

PATH may be an agent .md file or a directory (searched recursively; only files
with frontmatter containing both `name` and `description` are treated as agents).
With no PATH, scans ~/.claude/agents and ./.claude/agents. SKILL.md files are
skipped when walking a directory (they carry the same frontmatter but are skills).

Exit code is always 0; this is a reporter, not a gate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# --- Tool classification (mirror of references/tool-catalog.md) --------------
# Tools a SUBAGENT can never use even if listed -> dead entries in `tools`.
# Documented "universal blacklist" for subagents (code.claude.com/docs/en/sub-agents)
# plus `Task`, the pre-2.1.63 alias of `Agent`. `ExitPlanMode` is usable only with
# `permissionMode: plan`; `Agent` only while nested subagents are below the depth limit.
SUBAGENT_DEAD_TOOLS = {
    "Agent", "Task", "AskUserQuestion", "EndConversation", "EnterPlanMode",
    "ExitPlanMode", "ScheduleWakeup", "TaskOutput", "WaitForMcpServers", "Workflow",
}
# File-writing tools (presence on an agent that declares it doesn't write is a smell).
WRITE_FILE_TOOLS = {"Edit", "Write", "NotebookEdit"}
# An explicit "I don't write/edit/change code" statement in the BODY is a
# high-signal read-only mandate. Matching role words in the NAME instead caused
# false positives (e.g. "plan-driven-coder" matched "plan" yet genuinely codes),
# so we key off the body declaration.
NO_WRITE_DECL = re.compile(
    r"read[\s-]only"
    r"|\b(?:never|do not|does not|don'?t|doesn'?t|without)\b"
    r"(?:\s+\w+){0,2}?\s+(?:writ|edit|modif|chang|implement)\w*", re.I)
EMPHASIS = re.compile(r"\b(MUST|MUST NOT|NEVER|ALWAYS|DO NOT|CRITICAL|"
                      r"IMPORTANT|MANDATORY|REQUIRED)\b")

DEFAULT_BODY_LINES = 150   # official single-purpose examples run ~25-45 lines
DEFAULT_DESC_CHARS = 1200  # description loads session-wide for routing


def est_tokens(text: str) -> int:
    return round(len(text) / 4)


def parse_agent(path: Path):
    """Return a dict of parsed fields, or None if the file isn't an agent."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not raw.lstrip().startswith("---"):
        return None
    # Split frontmatter / body on the first two `---` fences.
    lines = raw.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() == "---"), None)
    if end is None:
        return None
    fm_lines = lines[start + 1:end]
    body = "\n".join(lines[end + 1:]).strip("\n")

    # Line-based key parse: a new key matches `key:`; other lines continue the
    # previous value (covers block scalars + the escaped multi-line description).
    fields: dict[str, str] = {}
    cur = None
    key_re = re.compile(r"^([A-Za-z_][\w-]*):\s?(.*)$")
    for l in fm_lines:
        m = key_re.match(l)
        if m and not l.startswith((" ", "\t", "-")):
            cur = m.group(1)
            fields[cur] = m.group(2)
        elif cur is not None:
            fields[cur] += "\n" + l
    # `name` is the agent-specific marker. A file with `name` but no
    # `description` is a BROKEN agent (description is required) — surface it and
    # flag the gap rather than silently dropping it.
    if "name" not in fields:
        return None

    tools_raw = fields.get("tools")
    has_tools = tools_raw is not None and tools_raw.strip() != ""
    tools: list[str] = []
    if has_tools:
        # Inline comma list and/or `- item` YAML list.
        flat = tools_raw.replace("\n", ",")
        for tok in flat.split(","):
            tok = tok.strip().lstrip("-").strip()
            if tok:
                tools.append(tok)

    desc = fields.get("description", "")
    return {
        "path": str(path),
        "name": fields.get("name", "").strip(),
        "model": fields.get("model", "").strip(),  # "" => inherit (default)
        "memory": fields.get("memory", "").strip(),
        "has_tools": has_tools,
        "tools": tools,
        "description": desc,
        "desc_chars": len(desc),
        "desc_tokens": est_tokens(desc),
        "body": body,
        "body_lines": body.count("\n") + 1 if body else 0,
        "body_chars": len(body),
        "body_tokens": est_tokens(body),
        "frontmatter_tokens": est_tokens("\n".join(fm_lines)),
        "_paragraphs": [p.strip() for p in re.split(r"\n\s*\n", body)
                        if len(p.strip()) >= 120],
    }


def flag_agent(a: dict, body_limit: int, desc_limit: int) -> list[dict]:
    flags = []

    def add(sev, code, msg):
        flags.append({"severity": sev, "code": code, "message": msg})

    if not a["has_tools"]:
        add("high", "NO_TOOLS_FIELD",
            "No `tools` field: inherits ALL tools every launch. Propose a "
            "minimal explicit allowlist (token + accuracy win).")
    else:
        dead = [t for t in a["tools"] if t in SUBAGENT_DEAD_TOOLS]
        if dead:
            add("med", "DEAD_TOOL_ENTRY",
                f"Tools a subagent can never use: {', '.join(dead)}. Remove.")
        if len(a["tools"]) > 10:
            add("med", "MANY_TOOLS",
                f"{len(a['tools'])} tools listed; tool-selection accuracy "
                "degrades past ~30-50. Trim to what the body actually uses.")
        # Read-only contradiction. A memory-enabled agent (memory: set) legitimately
        # needs Edit + Write to maintain its memory files, so those are justified
        # there and only the rest (e.g. NotebookEdit) is suspect.
        write_tools = [t for t in a["tools"] if t in WRITE_FILE_TOOLS]
        if write_tools and NO_WRITE_DECL.search(a["body"]):
            mem = bool(a["memory"])
            justified = {"Edit", "Write"} if mem else set()
            suspect = [t for t in write_tools if t not in justified]
            if suspect:
                extra = (f" (Edit/Write kept for memory upkeep; {', '.join(suspect)} "
                         "isn't needed for that)") if mem else ""
                add("med", "WRITE_ON_READONLY",
                    f"Body declares it doesn't write code, yet grants {', '.join(suspect)}. "
                    f"Drop unless it truly writes.{extra}")

    if not a["model"]:
        add("low", "MODEL_INHERIT",
            "No `model`: defaults to `inherit` (uses parent's model). Pin "
            "haiku for mechanical/read-only, or sonnet/opus if competence is fixed.")

    if not a["description"].strip():
        add("high", "MISSING_DESCRIPTION",
            "No `description` (a required field): the agent won't auto-delegate "
            "and may be ignored. Add trigger conditions + what it does.")
    else:
        if a["desc_chars"] > desc_limit:
            add("low", "LONG_DESCRIPTION",
                f"description is {a['desc_chars']} chars (~{a['desc_tokens']} tok); "
                "it loads session-wide for routing. Keep triggers + 1-2 tight examples.")
        if not re.search(
                r"\b(use when|use this|after|whenever|proactiv|immediately)\b",
                a["description"], re.I):
            add("med", "WEAK_TRIGGER",
                "description lacks explicit trigger conditions ('use when...', "
                "'after...', 'proactively'); may under-trigger.")

    if a["body_lines"] > body_limit:
        add("med", "LONG_BODY",
            f"body is {a['body_lines']} lines; single-purpose agents run "
            "~25-45. Check for redundancy / over-explaining.")
    if re.search(r"(persistent agent memory|## MEMORY\.md|your MEMORY\.md)",
                 a["body"], re.I):
        sev = "med" if a["memory"] else "low"
        add(sev, "MEMORY_BOILERPLATE",
            "Body hand-writes a persistent-memory section. With `memory:` set "
            "the harness already injects memory instructions + MEMORY.md; trim "
            "to a one-line 'update your memory as you learn'.")

    emph = len(EMPHASIS.findall(a["body"]))
    if emph >= 12:
        add("low", "EMPHASIS_DENSITY",
            f"{emph} ALL-CAPS imperatives (MUST/NEVER/ALWAYS...). High density "
            "reads as nagging; explain the why instead.")
    if not re.search(r"(output format|return|report|summary|deliverable)",
                     a["body"], re.I):
        add("low", "NO_OUTPUT_FORMAT",
            "No explicit output-format / 'return a concise summary' section; "
            "agent may dump verbose output into the parent's context.")

    if a["name"] and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a["name"]):
        add("med", "NAME_FORMAT",
            f"name '{a['name']}' isn't lowercase-hyphenated.")
    return flags


def find_duplicate_blocks(agents: list[dict]) -> list[dict]:
    """Paragraphs (>=120 chars) appearing verbatim in >=2 agents."""
    seen: dict[str, list[str]] = {}
    for a in agents:
        for p in set(a["_paragraphs"]):
            norm = re.sub(r"\s+", " ", p).strip()
            seen.setdefault(norm, []).append(a["name"])
    dups = []
    for text, names in seen.items():
        if len(names) >= 2:
            dups.append({"chars": len(text), "tokens": est_tokens(text),
                         "agents": sorted(set(names)),
                         "preview": text[:90] + ("..." if len(text) > 90 else "")})
    dups.sort(key=lambda d: d["chars"] * len(d["agents"]), reverse=True)
    return dups[:15]


def gather(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        pth = Path(p).expanduser()
        if pth.is_file() and pth.suffix == ".md":
            out.append(pth)
        elif pth.is_dir():
            # SKILL.md also carries `name` + `description` frontmatter but is a
            # skill, not an agent; a directory walk must not audit it as one.
            out.extend(f for f in sorted(pth.rglob("*.md")) if f.name != "SKILL.md")
    # de-dup, preserve order
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="agent .md files or directories")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--body-lines", type=int, default=DEFAULT_BODY_LINES)
    ap.add_argument("--desc-chars", type=int, default=DEFAULT_DESC_CHARS)
    args = ap.parse_args()

    paths = args.paths or [
        str(Path.home() / ".claude/agents"),
        str(Path.cwd() / ".claude/agents"),
    ]
    agents = []
    for f in gather(paths):
        parsed = parse_agent(f)
        if parsed:
            parsed["flags"] = flag_agent(parsed, args.body_lines, args.desc_chars)
            agents.append(parsed)

    dups = find_duplicate_blocks(agents)

    if args.json:
        for a in agents:
            a.pop("body", None)
            a.pop("_paragraphs", None)
        print(json.dumps({"agents": agents, "duplicate_blocks": dups,
                          "count": len(agents)}, indent=2))
        return

    if not agents:
        print("No agent files found in:", ", ".join(paths))
        return

    sev_order = {"high": 0, "med": 1, "low": 2}
    print(f"Scanned {len(agents)} agent(s)\n" + "=" * 60)
    for a in agents:
        tools = (f"{len(a['tools'])} tools" if a["has_tools"]
                 else "NO tools field (inherits all)")
        model = a["model"] or "inherit (default)"
        total = a["frontmatter_tokens"] + a["body_tokens"]
        print(f"\n● {a['name']}  [{model}]  {tools}")
        print(f"  {a['path']}")
        print(f"  desc ~{a['desc_tokens']} tok | body {a['body_lines']} lines "
              f"~{a['body_tokens']} tok | total ~{total} tok")
        for fl in sorted(a["flags"], key=lambda f: sev_order[f["severity"]]):
            print(f"    [{fl['severity']:>4}] {fl['code']}: {fl['message']}")
        if not a["flags"]:
            print("    (no flags)")

    if dups:
        print("\n" + "=" * 60 + "\nDUPLICATED BLOCKS (shared verbatim across agents)")
        for d in dups:
            print(f"  ~{d['tokens']} tok x{len(d['agents'])} "
                  f"[{', '.join(d['agents'])}]: {d['preview']}")
        waste = sum(d["tokens"] * (len(d["agents"]) - 1) for d in dups)
        print(f"  → ~{waste} tokens of repeated boilerplate across the set.")


if __name__ == "__main__":
    main()
