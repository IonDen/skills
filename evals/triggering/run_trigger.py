#!/usr/bin/env python3
"""Run the trigger eval: does the right skill load, at the right moment, in a
realistic Claude Code session?

    python3 run_trigger.py plan --phase 1
    python3 run_trigger.py run --phase 1 --cap 100 --out recorded/<date> --crowd <plugin dir> ...

Each session works in a fresh temp folder copied from one fixture project,
with this plugin loaded from the repository. The `+snippet` arms add a
CLAUDE.md that holds only the snippet from snippet.md (snippet2.md for
`+snippet2`); the `-crowded` arms
also load other plugins and a filler plugin with many skills. Every arm uses
the same setting sources, so the snippet is the only difference.

The runner stops a session as soon as its outcome is known, appends one
verdict per session to verdicts.jsonl, and on the next run skips the cells
already recorded. Verdicts hold no paths and no transcript."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLUGIN = ROOT / "plugins" / "ionden-skills"
FIXTURES = HERE / "fixtures"
SNIPPET = HERE / "snippet.md"
SNIPPET2 = HERE / "snippet2.md"
CANDIDATES = HERE / "candidates"
sys.path.insert(0, str(HERE))
import trigger  # noqa: E402

WT = "writing-tests-that-can-fail"
ALLOWED = ["Bash(python3 -m pytest:*)", "Bash(pytest:*)", "Bash(node --test:*)", "Bash(ls:*)", "Bash(cat:*)"]
TURN_CAP = 20
PRICE_PER_SESSION = {"sonnet": 0.15, "opus": 0.20}
SESSION_BUDGET_USD = 2.0
LAUNCH_TIMEOUT_S = 900
REPS = 3
NEAR_REPS_CANDIDATE = 5
MAX_ATTEMPTS = 3
MAX_INVALID_STREAK = 5
FILLER_SKILLS = 60
FILLER_TOPICS = ["invoice exports", "warehouse labels", "payroll slips", "calendar sync", "photo tagging",
                 "survey forms", "map tiles", "chat moderation", "fleet tracking", "recipe scaling"]


@dataclass(frozen=True)
class Cell:
    prompt_id: str
    arm: str
    model: str
    rep: int


def load_prompts() -> list[dict]:
    return json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))["prompts"]


def prepare_workspace(prompt: dict, arm: str, dest: Path) -> Path:
    shutil.copytree(FIXTURES / prompt["fixture"], dest)
    if arm.endswith("+snippet"):
        shutil.copy(SNIPPET, dest / "CLAUDE.md")
    elif arm.endswith("+snippet2"):
        shutil.copy(SNIPPET2, dest / "CLAUDE.md")
    return dest


def _phase1_arms(p: dict, model: str) -> list[str]:
    arms = ["current"]
    if p["skill"] == WT:
        arms.append("current+snippet")
        if model == "opus":
            arms.append("current-crowded")
    return arms


def matrix(phase: int, prompts: list[dict], gaps: set[str] | frozenset = frozenset()) -> list[Cell]:
    cells: list[Cell] = []
    if phase == 1:
        for model in ("sonnet", "opus"):
            for p in prompts:
                if p["half"] == "fresh" or (model == "opus" and p["half"] != "heldout"):
                    continue
                for rep in range(REPS):
                    cells += [Cell(p["id"], arm, model, rep) for arm in _phase1_arms(p, model)]
    elif phase == 2:
        # held-out prompts: candidate vs current for skills with a gap; for
        # writing-tests also the second snippet, whose near-miss check adds the
        # fresh prompts written after Phase 1
        for p in prompts:
            wt, near = p["skill"] == WT, p["kind"] == "near"
            if p["half"] == "heldout":
                arms = (["candidate"] if p["skill"] in gaps else []) + (["current+snippet2"] if wt else [])
            elif p["half"] == "fresh" and wt and near:
                arms = ["current+snippet2"]
            else:
                continue
            if not arms:
                continue
            for rep in range(NEAR_REPS_CANDIDATE if near else REPS):
                cells += [Cell(p["id"], arm, "opus", rep) for arm in ["current"] + arms]
    return cells


def estimate(cells: list[Cell], prices: dict[str, float] | None = None) -> float:
    prices = prices or PRICE_PER_SESSION
    return sum(prices[c.model] for c in cells)


# --- plugins for each arm ---------------------------------------------------

_DESC_RE = re.compile(r"^description:.*?(?=^\S)", re.M | re.S)


def description_of(skill_md: str) -> str:
    fm = skill_md.split("\n---\n", 1)[0]
    block = _DESC_RE.search(fm + "\nend:")
    text = block.group(0).split(":", 1)[1].strip() if block else ""
    if text.startswith(">-") or text.startswith(">"):
        text = text.lstrip(">-").strip()
    return " ".join(text.split())


def apply_description(skill_md: str, description: str) -> str:
    fm, body = skill_md.split("\n---\n", 1)
    wrapped = textwrap.fill(" ".join(description.split()), width=78, initial_indent="  ", subsequent_indent="  ")
    new_fm = _DESC_RE.sub(lambda _: f"description: >-\n{wrapped}\n", fm + "\nend:", count=1)[: -len("\nend:")]
    return new_fm + "\n---\n" + body


def make_candidate_plugin(dest: Path, candidates: Path = CANDIDATES) -> Path:
    shutil.copytree(PLUGIN, dest)
    for cand in sorted(candidates.glob("*.md")):
        md = dest / "skills" / cand.stem / "SKILL.md"
        md.write_text(apply_description(md.read_text(encoding="utf-8"), cand.read_text(encoding="utf-8")),
                      encoding="utf-8")
    return dest


def make_filler_plugin(dest: Path, n: int) -> Path:
    (dest / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (dest / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "filler", "version": "0.0.0", "description": "Unrelated skills that fill the listing."}),
        encoding="utf-8")
    for i in range(n):
        topic = FILLER_TOPICS[i % len(FILLER_TOPICS)]
        name = f"filler-{i:02d}"
        desc = (f"Use when working on {topic} (variant {i}): checking inputs, preparing the batch, "
                f"formatting the output for the {topic} team and explaining what changed since the last run.")
        d = dest / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\nFollow the {topic} checklist.\n",
                                    encoding="utf-8")
    return dest


def plugin_dirs(arm: str, work: Path, crowd: list[Path], candidates: Path = CANDIDATES) -> list[Path]:
    base = make_candidate_plugin(work / "candidate", candidates) if arm.startswith("candidate") else PLUGIN
    dirs = [base]
    if arm.endswith("-crowded"):
        dirs += list(crowd) + [make_filler_plugin(work / "filler", FILLER_SKILLS)]
    return dirs


# --- one session --------------------------------------------------------------

def build_command(text: str, model: str, dirs: list[Path], budget_usd: float) -> list[str]:
    cmd = ["claude", "-p", text, "--model", model, "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project,local", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED, "--max-turns", str(TURN_CAP),
           "--max-budget-usd", str(budget_usd), "--no-session-persistence"]
    for d in dirs:
        cmd += ["--plugin-dir", str(d)]
    return cmd


def _kill_group(proc: subprocess.Popen) -> None:
    """TERM the session's process group, give it 5 s, then KILL whatever is left
    in the group: tool processes can outlive the session or ignore TERM."""
    pgid = proc.pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):  # already gone (macOS reports a reaped group as EPERM)
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def install_stop_handlers() -> None:
    """Make SIGTERM and SIGHUP raise like Ctrl-C does, so `launch` still kills
    the running session (it lives in its own process group and gets neither)."""
    def _raise(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")
    signal.signal(signal.SIGTERM, _raise)
    signal.signal(signal.SIGHUP, _raise)


def launch(cmd: list[str], cwd: Path, stop: Callable[[list[str]], bool], timeout: float) -> tuple[list[str], bool]:
    """Stream the session's stdout; kill its process group once `stop` says the
    outcome is known, or at the timeout. Returns (lines, stopped_early)."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, start_new_session=True)
    timer = threading.Timer(timeout, _kill_group, [proc])
    timer.start()
    lines: list[str] = []
    stopped = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if stop(lines):
                stopped = True
                break
    finally:
        timer.cancel()
        if proc.poll() is None:
            _kill_group(proc)
        proc.wait()
    return lines, stopped


def _resolved_model(lines: list[str]) -> str:
    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "system" and msg.get("subtype") == "init":
            return str(msg.get("model", ""))
    return ""


def record(cell: Cell, prompt: dict, events: list, outcome: str, cli_version: str, resolved_model: str,
           crowd: list[str]) -> dict:
    skill = prompt["skill"]
    load = next((e for e in events if e.kind in ("skill", "read") and e.name == skill and not e.subagent), None)
    write = next((e for e in events if e.kind == "write" and not e.subagent and trigger.is_test_path(e.path)), None)
    cost = sum(float(e.text or 0) for e in events if e.kind == "result")
    return {"prompt_id": cell.prompt_id, "skill": skill, "kind": prompt["kind"], "half": prompt["half"],
            "arm": cell.arm, "model": cell.model, "resolved_model": resolved_model, "rep": cell.rep,
            "outcome": outcome, "load_turn": load.turn if load else None,
            "first_test_write_turn": write.turn if write else None, "load_via": load.kind if load else None,
            "cost_usd": round(cost, 6), "cli_version": cli_version,
            "crowd": crowd if cell.arm.endswith("-crowded") else [], "date": datetime.date.today().isoformat()}


def run_cell(cell: Cell, prompt: dict, launch_fn, crowd: list[Path], crowd_names: list[str], cli_version: str,
             candidates: Path = CANDIDATES) -> dict:
    with tempfile.TemporaryDirectory(prefix="trig-") as tmp:
        ws = prepare_workspace(prompt, cell.arm, Path(tmp) / "ws")
        dirs = plugin_dirs(cell.arm, Path(tmp), crowd, candidates)
        skills_dir = str(dirs[0] / "skills")

        def stop(lines: list[str]) -> bool:
            return trigger.should_stop(trigger.parse_events(lines, skills_dir), prompt["skill"], prompt["kind"])

        lines, stopped = launch_fn(build_command(prompt["text"], cell.model, dirs, SESSION_BUDGET_USD), ws, stop,
                                   LAUNCH_TIMEOUT_S)
        events = trigger.parse_events(lines, skills_dir)
        results = [e for e in events if e.kind == "result"]
        if not stopped and not results:  # died, was killed at the timeout, or never started: run it again
            outcome = "invalid"
        else:
            capped = not stopped and results[-1].name in trigger.CAP_SUBTYPES
            outcome = trigger.classify(events, prompt["skill"], prompt["kind"], capped)
        return record(cell, prompt, events, outcome, cli_version, _resolved_model(lines), crowd_names)


# --- a phase ------------------------------------------------------------------

def _key(c) -> tuple:
    if isinstance(c, Cell):
        return (c.model, c.prompt_id, c.arm, c.rep)
    return (c["model"], c["prompt_id"], c["arm"], c["rep"])


def _read(out: Path) -> list[dict]:
    f = out / "verdicts.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def _done(recs: list[dict]) -> set[tuple]:
    attempts: dict[tuple, list[str]] = defaultdict(list)
    for r in recs:
        attempts[_key(r)].append(r["outcome"])
    return {k for k, outs in attempts.items() if any(o != "invalid" for o in outs) or len(outs) >= MAX_ATTEMPTS}


def _crowd_name(d: Path) -> str:
    try:
        meta = json.loads((d / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        return f"{meta.get('name', d.name)}@{meta.get('version', '?')}"
    except (OSError, json.JSONDecodeError):
        return d.name


def run_phase(phase: int, cap: float, out: Path, crowd: list[Path] = (), prompts: list[dict] | None = None,
              launch_fn=launch, prices: dict[str, float] | None = None, cli_version: str = "",
              gaps: set[str] | frozenset = frozenset(), candidates: Path = CANDIDATES) -> int:
    prices = dict(prices or PRICE_PER_SESSION)
    prompts = prompts if prompts is not None else load_prompts()
    by_id = {p["id"]: p for p in prompts}
    cells = matrix(phase, prompts, gaps)
    out.mkdir(parents=True, exist_ok=True)
    recs = _read(out)
    done = _done(recs)
    todo = [c for c in cells if _key(c) not in done]
    crowd = list(crowd)
    crowd_names = [_crowd_name(d) for d in crowd]
    attempts = defaultdict(int)
    for r in recs:
        attempts[_key(r)] += 1
    observed: dict[str, list[float]] = defaultdict(list)  # costs of sessions that reported one
    for r in recs:
        if r["cost_usd"] > 0:
            observed[r["model"]].append(r["cost_usd"])

    def per_session(model: str) -> float:
        """Expected cost of one session: the model's observed mean once it has
        run, before that its listed price scaled by the overrun seen so far."""
        seen = observed[model]
        if seen:
            return max(prices[model], sum(seen) / len(seen))
        listed = sum(prices[m] * len(v) for m, v in observed.items())
        actual = sum(sum(v) for v in observed.values())
        return prices[model] * max(1.0, actual / listed if listed else 1.0)

    def charge(rec: dict) -> float:
        """What a session counts against the cap. A session stopped early never
        reports its cost, so it is charged the expected cost of a full one."""
        return rec["cost_usd"] if rec["cost_usd"] > 0 else per_session(rec["model"])

    spent = sum(charge(r) for r in recs)
    if spent + estimate(todo, prices) > cap:
        raise SystemExit(f"estimate ${spent + estimate(todo, prices):.2f} (spent ${spent:.2f}) is over the ${cap:.2f} cap")
    invalid_streak = 0

    groups: list[list[Cell]] = []
    for c in todo:
        if groups and (groups[-1][0].model, groups[-1][0].prompt_id, groups[-1][0].rep) == (c.model, c.prompt_id, c.rep):
            groups[-1].append(c)
        else:
            groups.append([c])
    with (out / "verdicts.jsonl").open("a", encoding="utf-8") as f:
        for group in groups:
            if spent + sum(per_session(c.model) for c in group) > cap:
                print(f"stopping: next group would pass the ${cap:.2f} cap (spent ${spent:.2f})")
                return 1
            for cell in group:
                tries = 0
                while attempts[_key(cell)] < MAX_ATTEMPTS:
                    if tries and spent + per_session(cell.model) > cap:  # the group check covered the first try
                        print(f"stopping: a retry would pass the ${cap:.2f} cap (spent ${spent:.2f})")
                        return 1
                    rec = run_cell(cell, by_id[cell.prompt_id], launch_fn, crowd, crowd_names, cli_version, candidates)
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    attempts[_key(cell)] += 1
                    tries += 1
                    if rec["cost_usd"] > 0:
                        observed[cell.model].append(rec["cost_usd"])
                    spent += charge(rec)
                    print(f"{cell.model} {cell.prompt_id} {cell.arm} rep{cell.rep}: {rec['outcome']} "
                          f"${rec['cost_usd']:.3f} (counted ${spent:.2f})", flush=True)
                    if rec["outcome"] != "invalid":
                        invalid_streak = 0
                        break
                    invalid_streak += 1
                    if invalid_streak >= MAX_INVALID_STREAK:
                        print(f"stopping: {invalid_streak} invalid sessions in a row (login, usage limit or outage?)")
                        return 1
    return 0


SNIPPET_MARKER = "failing-test step of tdd"
USER_MEMORY_MARKERS = ("scribe", "denis ineshin", "absolute rule", "bash-git-ops")
PROBE_TEXT = ("Without using any tools: first list the name of every skill available to you, exactly as named. "
              "Then quote, word for word, any instructions you were given about writing or changing tests, "
              "or write NONE if there are none.")


def probe_findings(init: dict, with_snippet: str, without_snippet: str) -> list[str]:
    """Problems with the session setup, from a probe answer in a workspace with
    the snippet and one without it. Empty means the setup is clean."""
    found = []
    if "Skill" not in init.get("tools", []):
        found.append("Skill tool missing")
    for skill in trigger.SKILLS:
        if skill not in with_snippet:
            found.append(f"skill not listed: {skill}")
    norm_with, norm_without = (" ".join(t.lower().split()) for t in (with_snippet, without_snippet))
    if SNIPPET_MARKER not in norm_with:
        found.append("snippet not visible with CLAUDE.md")
    if SNIPPET_MARKER in norm_without:
        found.append("snippet visible without CLAUDE.md")
    for marker in USER_MEMORY_MARKERS:
        if marker in norm_with or marker in norm_without:
            found.append(f"user memory visible: {marker}")
    return found


def _init_and_answer(lines: list[str]) -> tuple[dict, str]:
    init, answer = {}, ""
    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "system" and msg.get("subtype") == "init":
            init = msg
        elif msg.get("type") == "result":
            answer = str(msg.get("result", ""))
    return init, answer


def probe(out: Path, model: str = "sonnet") -> int:
    """Check the session setup, then run one should-load prompt to completion to
    measure the turn of the first test write and the cost of a full session."""
    by_id = {p["id"]: p for p in load_prompts()}
    report: list[str] = []
    answers = {}
    for arm in ("current+snippet", "current"):
        with tempfile.TemporaryDirectory(prefix="trig-probe-") as tmp:
            ws = prepare_workspace(by_id["wt-s02"], arm, Path(tmp) / "ws")
            lines, _ = launch(build_command(PROBE_TEXT, model, [PLUGIN], SESSION_BUDGET_USD), ws, lambda _: False,
                              LAUNCH_TIMEOUT_S)
            answers[arm] = _init_and_answer(lines)
            report += [f"## probe answer, {arm}", answers[arm][1], ""]
    init = answers["current+snippet"][0]
    report += [f"init tools: {', '.join(init.get('tools', []))}", f"init model: {init.get('model', '')}", ""]
    with tempfile.TemporaryDirectory(prefix="trig-probe-") as tmp:
        ws = prepare_workspace(by_id["op-s01"], "current", Path(tmp) / "ws")
        lines, _ = launch(build_command("Without using any tools: list the subagent types you can launch.", model,
                                        [PLUGIN], SESSION_BUDGET_USD), ws, lambda _: False, LAUNCH_TIMEOUT_S)
        report += ["## subagent types in the optimizer workspace", _init_and_answer(lines)[1], ""]
    prompt = by_id["wt-s02"]
    with tempfile.TemporaryDirectory(prefix="trig-probe-") as tmp:
        ws = prepare_workspace(prompt, "current", Path(tmp) / "ws")
        skills_dir = str(PLUGIN / "skills")
        lines, _ = launch(build_command(prompt["text"], "opus", [PLUGIN], SESSION_BUDGET_USD), ws, lambda _: False,
                          LAUNCH_TIMEOUT_S)
        events = trigger.parse_events(lines, skills_dir)
        rec = record(Cell(prompt["id"], "current", "opus", 0), prompt, events,
                     trigger.classify(events, prompt["skill"], prompt["kind"], False), _cli_version(),
                     _resolved_model(lines), [])
        kinds = defaultdict(int)
        for e in events:
            kinds[e.kind] += 1
        report += ["## full session, wt-s02, opus, current", json.dumps(rec, sort_keys=True),
                   "event kinds: " + json.dumps(dict(kinds), sort_keys=True),
                   f"assistant turns: {max((e.turn for e in events), default=0)}", ""]
    findings = probe_findings(init, answers["current+snippet"][1], answers["current"][1])
    if not kinds.get("result"):
        findings.append("no result event parsed from a real session")
    report += ["## findings", *(findings or ["CLEAN"])]
    text = "\n".join(report) + "\n"
    text = text.replace(str(Path.home()), "~").replace(tempfile.gettempdir(), "<tmp>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    return 1 if findings else 0


def scrub_problems(path: Path) -> list[str]:
    problems = []
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "/Users/" in line or "/private/" in line:
                problems.append(f"{f}:{n}")
    return problems


def _cli_version() -> str:
    r = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    return r.stdout.split()[0] if r.stdout else ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--phase", type=int, required=True)
    pl.add_argument("--gap", action="append", default=[])
    rn = sub.add_parser("run")
    rn.add_argument("--phase", type=int, required=True)
    rn.add_argument("--cap", type=float, required=True)
    rn.add_argument("--out", type=Path, required=True)
    rn.add_argument("--crowd", type=Path, action="append", default=[])
    rn.add_argument("--gap", action="append", default=[])
    pr = sub.add_parser("probe")
    pr.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    install_stop_handlers()
    if a.cmd == "probe":
        return probe(a.out)
    if a.cmd == "plan":
        cells = matrix(a.phase, load_prompts(), set(a.gap))
        per = defaultdict(int)
        for c in cells:
            per[(c.model, c.arm)] += 1
        for (model, arm), n in sorted(per.items()):
            print(f"{model:7} {arm:18} {n}")
        print(f"{len(cells)} sessions, estimate ${estimate(cells):.2f}")
        return 0
    return run_phase(a.phase, a.cap, a.out, a.crowd, cli_version=_cli_version(), gaps=set(a.gap))


if __name__ == "__main__":
    sys.exit(main())
