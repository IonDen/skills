"""Score when a skill loads in a `claude -p --output-format stream-json` session.

parse_events turns the session's JSON lines into a short list of the events
that matter here: a skill load, a write to a file, a hand-off to a subagent,
the final result and any error. classify turns that list into one outcome per
run; should_stop tells the runner when the outcome is already decided."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Iterable

SKILLS = ("writing-tests-that-can-fail", "skill-optimizer", "subagent-optimizer")
PLUGIN_PREFIX = "ionden-skills:"
CAP_SUBTYPES = {"error_max_turns", "error_max_budget_usd"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DELEGATE_TOOLS = {"Agent", "Task"}
TEST_DIRS = {"tests", "test", "__tests__", "spec"}
TEST_NAMES = ("test_*.py", "*_test.py", "*_test.go", "*.test.js", "*.test.jsx", "*.test.ts", "*.test.tsx",
              "*.test.mjs", "*.test.cjs", "*.spec.js", "*.spec.jsx", "*.spec.ts", "*.spec.tsx",
              "*Test.java", "*Test.kt", "*Tests.swift")
_REDIRECT = re.compile(r"(?:>>?|\btee\s+(?:-a\s+)?)\s*([^\s;&|<>'\"]+)")
_CAT = re.compile(r"\bcat\s+([^\s;&|<>'\"]+)")


@dataclass(frozen=True)
class Event:
    turn: int
    kind: str  # skill | read | write | delegate | result | error
    name: str = ""
    path: str = ""
    text: str = ""
    subagent: bool = False


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    if any(p in TEST_DIRS for p in parts[:-1]):
        return True
    return any(fnmatch(parts[-1], pat) for pat in TEST_NAMES)


def _skill_under(path: str, plugin_skills_dir: str) -> str:
    prefix = plugin_skills_dir.rstrip("/") + "/"
    if not path.startswith(prefix):
        return ""
    return path[len(prefix):].split("/", 1)[0]


def _tool_events(block: dict, turn: int, sub: bool, plugin_skills_dir: str) -> list[Event]:
    name, inp = block.get("name", ""), block.get("input") or {}
    if name == "Skill":
        skill = str(inp.get("skill", ""))
        return [Event(turn, "skill", name=skill.removeprefix(PLUGIN_PREFIX), subagent=sub)]
    if name == "Read":
        path = str(inp.get("file_path", ""))
        skill = _skill_under(path, plugin_skills_dir)
        return [Event(turn, "read", name=skill, path=path, subagent=sub)] if skill else []
    if name in WRITE_TOOLS:
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        return [Event(turn, "write", path=path, subagent=sub)]
    if name in DELEGATE_TOOLS:
        return [Event(turn, "delegate", text=str(inp.get("prompt", "")), subagent=sub)]
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        out = [Event(turn, "write", path=p, subagent=sub) for p in _REDIRECT.findall(cmd)]
        for p in _CAT.findall(cmd):
            skill = _skill_under(p, plugin_skills_dir)
            if skill:
                out.append(Event(turn, "read", name=skill, path=p, subagent=sub))
        return out
    return []


def parse_events(lines: Iterable[str], plugin_skills_dir: str) -> list[Event]:
    events: list[Event] = []
    turn = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = msg.get("type")
        if kind == "assistant":
            turn += 1
            sub = msg.get("parent_tool_use_id") is not None
            if msg.get("error"):
                events.append(Event(turn, "error", name=str(msg["error"]), subagent=sub))
            for block in (msg.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    events.extend(_tool_events(block, turn, sub, plugin_skills_dir))
        elif kind == "result":
            subtype = str(msg.get("subtype", ""))
            if msg.get("is_error") and subtype not in CAP_SUBTYPES:
                events.append(Event(turn, "error", name=subtype, text=str(msg.get("result", ""))))
            events.append(Event(turn, "result", name=subtype, text=str(msg.get("total_cost_usd", 0) or 0)))
    return events


def _loaded(e: Event, skill: str) -> bool:
    return e.kind in ("skill", "read") and e.name == skill and not e.subagent


def _test_write(e: Event) -> bool:
    return e.kind == "write" and not e.subagent and is_test_path(e.path)


def _names_skill(text: str, skill: str) -> bool:
    return skill in text


def should_stop(events: list[Event], skill: str, kind: str) -> bool:
    if kind == "should":
        tests_matter = skill == "writing-tests-that-can-fail"
        return any(_loaded(e, skill) or (tests_matter and _test_write(e)) for e in events)
    if kind == "delegate":
        return any(e.kind == "delegate" or _test_write(e) for e in events)
    return False


def classify(events: list[Event], skill: str, kind: str, capped: bool) -> str:
    if any(e.kind == "error" for e in events):
        return "invalid"
    if kind == "near":
        if any(_loaded(e, skill) for e in events):
            return "false-load"
        return "inconclusive" if capped else "no-load"
    if kind == "delegate":
        for e in events:
            if e.kind == "delegate":
                return "hit" if _names_skill(e.text, skill) else "miss"
            if e.kind in ("skill", "read") and e.name == skill and e.subagent:
                return "hit"
            if _test_write(e):
                return "miss"
        return "inconclusive" if capped else "n/a"
    for e in events:
        if _loaded(e, skill):
            return "hit"
        if skill == "writing-tests-that-can-fail" and _test_write(e):
            return "miss"
    if capped:
        return "inconclusive"
    if skill == "writing-tests-that-can-fail":
        return "n/a"
    return "miss"
