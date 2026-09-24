#!/usr/bin/env python3
"""Scan Claude Code subagent definition files and report optimisation signals.

Deterministic pass that does the measuring so the skill can spend its reasoning
on judgement calls. Parses YAML-ish frontmatter (line based, tolerant of the
JSON-escaped multi-line `description` strings the agent-creator emits), counts
sizes, estimates tokens (~chars/4), and raises heuristic flags.

Usage:
    python scan_agents.py [PATH ...] [--json] [--body-lines N] [--desc-chars N]

PATH may be an agent .md file or a directory (searched recursively; a file with
frontmatter carrying `name` is treated as an agent, and a missing `description`
is reported as a flag rather than silently dropping the file).
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
# Documented "universal blacklist" for subagents (code.claude.com/docs/en/sub-agents).
# `ExitPlanMode` is usable only with `permissionMode: plan`. `Agent` is NOT here:
# nested subagents are on by default (up to three layers), so a fan-out agent may
# legitimately list it; it is surfaced as a question instead (NESTED_AGENT_TOOL).
SUBAGENT_DEAD_TOOLS = {
    "AskUserQuestion", "EndConversation", "EnterPlanMode", "ExitPlanMode",
    "ScheduleWakeup", "TaskOutput", "WaitForMcpServers", "Workflow",
}
# Names from older Claude Code releases that no longer appear in the tools reference.
LEGACY_TOOL_NAMES = {
    "Task": "Agent", "LS": "Glob or Read", "NotebookRead": "Read",
    "MultiEdit": "Edit", "BashOutput": "Monitor", "KillShell": "TaskStop",
}
# Removed from background subagents (the default) whether inherited or listed.
BACKGROUND_STRIPPED_TOOLS = {
    "TaskCreate", "TaskGet", "TaskUpdate", "TaskList", "ListAgents", "LSP",
    "ListMcpResourcesTool", "ReadMcpResourceTool",
}
# File-writing tools (presence on an agent that declares it doesn't write is a smell).
WRITE_FILE_TOOLS = {"Edit", "Write", "NotebookEdit"}
# Any of these (or no `tools` field at all) means the agent can change things.
MUTATING_TOOLS = WRITE_FILE_TOOLS | {"Bash"}
# Documented `effort` values (code.claude.com/docs/en/sub-agents); which ones a
# given model accepts varies, so this is only the outer set.
EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}
TOP_EFFORT_LEVELS = {"xhigh", "max"}
# Model aliases Claude Code's effort table leaves out ("Models not listed here do
# not support effort", code.claude.com/docs/en/model-config). Full model IDs and
# `inherit` are not resolved here, so they keep the ordinary effort checks.
EFFORT_UNSUPPORTED_MODELS = {"haiku"}
# An explicit "I don't write/edit/change code" statement in the BODY is a
# high-signal read-only mandate. Matching role words in the NAME instead caused
# false positives (e.g. "plan-driven-coder" matched "plan" yet genuinely codes),
# so we key off the body declaration.
NO_WRITE_DECL = re.compile(
    r"read[\s-]only"
    r"|\b(?:never|do not|does not|don'?t|doesn'?t|without)\b(?!\s+forget)"
    r"(?:\s+\w+){0,2}?\s+(?:writ|edit|modif|chang|implement)\w*"
    r"\s+(?:\w+\s+){0,2}?(?:code|files?|codebase|source|implementation|anything"
    r"|disk|repo(?:sitory)?|fixes)\b", re.I)
EMPHASIS = re.compile(r"\b(MUST|MUST NOT|NEVER|ALWAYS|DO NOT|CRITICAL|"
                      r"IMPORTANT|MANDATORY|REQUIRED)\b")

DEFAULT_BODY_LINES = 150   # official single-purpose examples run ~25-45 lines
DEFAULT_DESC_CHARS = 1200  # description loads session-wide for routing


def est_tokens(text: str) -> int:
    return round(len(text) / 4)


def _scalar(raw: str) -> str:
    """Decode a plain or quoted single-line YAML scalar (strip matching quotes)."""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _truthy(raw: str) -> bool:
    return _scalar(raw).lower() in {"true", "yes", "on", "1"}


def _split_tools(raw: str) -> list[str]:
    """Tokenize a `tools` value: comma/newline separated, `[...]` flow lists,
    quoted items, `- item` block lists and `# comments`. Parentheses protect
    their contents, so `Agent(worker, researcher)` and `Bash(git diff:*, git log:*)`
    stay one tool each (quotes inside them are kept verbatim); quotes at the top
    level are decoration and are dropped."""
    tokens: list[str] = []
    buf: list[str] = []
    depth = 0
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if depth == 0 and ch in "\"'":
            pass  # top-level quoting is decoration
        elif ch == "#" and depth == 0 and (i == 0 or raw[i - 1] in " \t\n"):
            while i < n and raw[i] != "\n":
                i += 1
            continue
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(depth - 1, 0)
            buf.append(ch)
        elif depth == 0 and ch in ",\n[]":
            tokens.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    tokens.append("".join(buf))
    out = []
    for tok in tokens:
        tok = tok.strip()
        if tok.startswith("-"):
            tok = tok[1:].strip()
        if tok:
            out.append(tok)
    return out


def _base_name(tool: str) -> str:
    """`Agent(worker)` -> `Agent`; `mcp__x__y` unchanged."""
    return tool.split("(", 1)[0].strip()


def _memory_value(raw: str) -> str:
    """`memory: false/no/off/0` means disabled; return "" for those."""
    v = raw.strip().strip("\"'")
    return "" if v.lower() in {"", "false", "no", "off", "0", "none"} else v


def parse_agent(path: Path):
    """Return a dict of parsed fields, or None if the file isn't an agent."""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
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
    key_re = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
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
    tools = _split_tools(tools_raw) if tools_raw is not None else []
    # An empty list (`tools: []`) is treated like a missing field: nothing is granted
    # explicitly, so the agent still inherits everything.
    has_tools = bool(tools)

    desc_raw = fields.get("description", "")
    desc = _scalar(desc_raw) if "\n" not in desc_raw else desc_raw
    return {
        "path": str(path),
        "name": _scalar(fields.get("name", "")),
        "model": _scalar(fields.get("model", "")),  # "" => inherit (default)
        "effort": _scalar(fields.get("effort", "")),  # "" => inherits from session
        "permission_mode": _scalar(fields.get("permissionMode", "")),
        "omit_claude_md": _truthy(fields.get("omitClaudeMd", "")),
        "memory": _memory_value(fields.get("memory", "")),
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
        bases = [_base_name(t) for t in a["tools"]]
        dead = [t for t in bases if t in SUBAGENT_DEAD_TOOLS
                and not (t == "ExitPlanMode" and a["permission_mode"] == "plan")]
        if dead:
            add("med", "DEAD_TOOL_ENTRY",
                f"Tools a subagent can never use: {', '.join(dead)}. Remove.")
        legacy = [t for t in bases if t in LEGACY_TOOL_NAMES]
        if legacy:
            add("med", "LEGACY_TOOL_NAME",
                "Names from older releases: " + "; ".join(
                    f"{t} -> {LEGACY_TOOL_NAMES[t]}" for t in legacy)
                + ". Rename (verify against the installed version first).")
        if "Agent" in bases:
            add("low", "NESTED_AGENT_TOOL",
                "Lists `Agent`: fine if the body delegates to sub-subagents (nesting is "
                "on by default, up to three layers); dead at the depth limit or with "
                "nesting off. Keep or drop? Ask, don't strip.")
        stripped = [t for t in bases if t in BACKGROUND_STRIPPED_TOOLS]
        if stripped:
            add("low", "BACKGROUND_STRIPPED",
                f"Removed from background subagents (the default): {', '.join(stripped)}. "
                "Keep only if the agent is launched in the foreground.")
        if len(a["tools"]) > 10:
            add("med", "MANY_TOOLS",
                f"{len(a['tools'])} tools listed; a single-purpose agent rarely needs more "
                "than ~10, and every extra schema costs tokens and selection accuracy. "
                "Trim to what the body actually uses.")
        # Read-only contradiction. A memory-enabled agent (memory: set) legitimately
        # needs Edit + Write to maintain its memory files, so those are justified
        # there and only the rest (e.g. NotebookEdit) is suspect.
        write_tools = [t for t in bases if t in WRITE_FILE_TOOLS]
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

    if a["omit_claude_md"]:
        add("info", "OMITS_CLAUDE_MD",
            "`omitClaudeMd: true`: this agent does NOT inherit CLAUDE.md, so rules "
            "written into its body may be the only copy. Do not trim them as duplicates.")

    if not a["model"]:
        add("low", "MODEL_INHERIT",
            "No `model`: defaults to `inherit` (uses parent's model). Pin "
            "haiku for mechanical/read-only, or sonnet/opus if competence is fixed.")

    if a["model"].lower() in EFFORT_UNSUPPORTED_MODELS:
        if a["effort"]:
            add("low", "EFFORT_UNSUPPORTED",
                f"effort {a['effort']} on `{a['model']}`: this model ignores effort. "
                "Drop the field, or move to a model that supports it if the job needs it.")
    elif not a["effort"]:
        add("low", "EFFORT_INHERIT",
            "No `effort`: runs at the session's effort level. Pin it with the model "
            "when the job's depth is fixed (low for lookups, high for planners).")
    elif a["effort"] not in EFFORT_LEVELS:
        add("med", "EFFORT_INVALID",
            f"effort '{a['effort']}' is not one of low, medium, high, xhigh, max.")
    elif (a["effort"] in TOP_EFFORT_LEVELS and a["has_tools"]
          and not {_base_name(t) for t in a["tools"]} & MUTATING_TOOLS):
        add("low", "HIGH_EFFORT_READONLY",
            f"effort {a['effort']} on a read-only agent. Does the job need it? "
            "A lower level is a candidate to verify on its real task.")

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
                r"\b(use when|use this|after|whenever|proactive(?:ly)?|immediately)\b",
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
            # A symlinked file could pull content from outside the scanned tree
            # into the report; only plain files are agents.
            out.extend(f for f in sorted(pth.rglob("*.md"))
                       if f.name != "SKILL.md" and not f.is_symlink())
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
                          "count": len(agents),
                          "metric": "definition text, chars/4; tool schemas and "
                                    "inherited context are not measured"}, indent=2))
        return

    if not agents:
        print("No agent files found in:", ", ".join(paths))
        return

    sev_order = {"high": 0, "med": 1, "low": 2, "info": 3}
    print(f"Scanned {len(agents)} agent(s); token figures are definition text only\n" + "=" * 60)
    for a in agents:
        tools = (f"{len(a['tools'])} tools" if a["has_tools"]
                 else "NO tools field (inherits all)")
        model = a["model"] or "inherit (default)"
        effort = a["effort"] or "inherit (session)"
        total = a["frontmatter_tokens"] + a["body_tokens"]
        print(f"\n● {a['name']}  [{model}, effort {effort}]  {tools}")
        print(f"  {a['path']}")
        print(f"  definition text: desc ~{a['desc_tokens']} tok | body {a['body_lines']} lines "
              f"~{a['body_tokens']} tok | total ~{total} tok "
              "(chars/4 of the file; tool schemas and inherited context not counted)")
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
