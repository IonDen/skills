#!/usr/bin/env python3
"""Run one eval of writing-tests-that-can-fail in an isolated `claude -p`
session and record the result with its verdict.

    python3 run_eval.py probe
    python3 run_eval.py run --fixture e-shipping-py --arm skill --model haiku --n 1 --out recorded/2026-09-25

The agent works in a fresh temp folder that holds only the files it is meant
to see: the fixture source (and, for the red-test fixture, its given tests);
with --arm skill also skill/SKILL.md and skill/references/. Reference suites,
held-out tests and mutants never enter it. The session loads no user or
project settings or CLAUDE.md, cannot use the Skill tool, has no MCP servers,
and runs in acceptEdits mode with only the test runners, ls and cat allowed
in Bash."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))
import harness  # noqa: E402

ALLOWED = ["Bash(python3 -m pytest:*)", "Bash(pytest:*)", "Bash(node --test:*)", "Bash(ls:*)", "Bash(cat:*)"]
PROBE = ("Without using any tools: list the name of every skill available to you, then quote any "
         "instructions you were given about writing or fixing tests. Reply NONE for each if there are none.")


def _evals() -> dict:
    return json.loads((HERE / "evals.json").read_text(encoding="utf-8"))


def _eval_for(fixture: str) -> dict:
    return next(e for e in _evals()["evals"] if e["fixture"] == fixture)


def prompt_for(fixture: str, arm: str) -> str:
    base = _eval_for(fixture)["prompt"]
    return _evals()["skill_preamble"] + base if arm == "skill" else base


def skill_files() -> list[Path]:
    return [SKILL_DIR / "SKILL.md"] + sorted(p for p in (SKILL_DIR / "references").rglob("*") if p.is_file())


def skill_hash() -> str:
    h = hashlib.sha256()
    for p in skill_files():
        h.update(str(p.relative_to(SKILL_DIR)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def prepare_workspace(fixture: str, arm: str, dest: Path) -> Path:
    fx_dir = FIXTURES / fixture
    meta = json.loads((fx_dir / "fixture.json").read_text(encoding="utf-8"))
    dest.mkdir(parents=True)
    for name in meta["sources"]:
        shutil.copy(fx_dir / name, dest / name)
    for name in meta.get("given", []):
        shutil.copy(fx_dir / "given" / name, dest / name)
    if arm == "skill":
        for p in skill_files():
            target = dest / "skill" / p.relative_to(SKILL_DIR)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, target)
    return dest


def build_command(prompt: str, model: str) -> list[str]:
    return ["claude", "-p", prompt, "--model", model,
            "--setting-sources", "local", "--disallowedTools", "Skill",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED,
            "--max-turns", "40", "--output-format", "json"]


LAUNCH_TIMEOUT_S = 1200


def parse_result(returncode: int, stdout: str, stderr: str) -> dict:
    """The session's final result message, with the exit code; a CLI error
    that printed no JSON raises instead of being recorded as a run."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude exited {returncode} without JSON output: {stderr.strip()[:500]}") from None
    result = data[-1] if isinstance(data, list) else data
    return {**result, "returncode": returncode}


def _launch(prompt: str, model: str, cwd: Path) -> dict:
    r = harness.run_group(build_command(prompt, model), cwd, timeout=LAUNCH_TIMEOUT_S)
    if r is None:
        return {"timed_out": True, "is_error": True, "subtype": "timeout", "returncode": None, "result": ""}
    return parse_result(*r)


def probe() -> int:
    with tempfile.TemporaryDirectory(prefix="wtcf-probe-") as tmp:
        result = _launch(PROBE, "haiku", Path(tmp))
    text = result.get("result", "")
    print(text)
    leaked = [w for w in ("writing-tests-that-can-fail", "test-driven-development", "name the one-line bug")
              if w.lower() in text.lower()]
    print("LEAK:" if leaked else "CLEAN", ", ".join(leaked))
    return 1 if leaked else 0


def run(fixture: str, arm: str, model: str, n: int, out: Path) -> Path:
    ev = _eval_for(fixture)
    run_dir = out / fixture / f"{arm}-{model}-{n}"
    if run_dir.exists():
        raise SystemExit(f"{run_dir} exists; runs are never overwritten")
    # Everything is written to a staging folder and renamed at the end, so a
    # failure never leaves a half-written run that blocks this cell.
    staging = run_dir.with_name(f".staging-{run_dir.name}")
    try:
        with tempfile.TemporaryDirectory(prefix="wtcf-run-") as tmp:
            ws = prepare_workspace(fixture, arm, Path(tmp) / "ws")
            result = _launch(prompt_for(fixture, arm), model, ws)
            staging.mkdir(parents=True)
            if ev["output"] == "workspace":
                shutil.copytree(ws, staging / "workspace",
                                ignore=shutil.ignore_patterns("skill", "__pycache__", ".pytest_cache"))
                verdict = harness.verdict_f(FIXTURES / fixture, staging / "workspace")
            else:
                produced = ws / ev["output"]
                if produced.exists():
                    shutil.copy(produced, staging / ev["output"])
                    verdict = harness.verdict(FIXTURES / fixture, staging / ev["output"])
                else:
                    verdict = {"fixture": fixture, "missing_output": ev["output"]}
        meta = {"fixture": fixture, "arm": arm, "model_alias": model,
                "model_ids": sorted((result.get("modelUsage") or {}).keys()),
                "date": datetime.date.today().isoformat(),
                "skill_hash": skill_hash() if arm == "skill" else None,
                "num_turns": result.get("num_turns"), "cost_usd": result.get("total_cost_usd"),
                "returncode": result.get("returncode"), "is_error": result.get("is_error"),
                "subtype": result.get("subtype"), "timed_out": result.get("timed_out", False),
                "final_message": result.get("result", "")}
        (staging / "run.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
        (staging / "verdict.json").write_text(json.dumps(verdict, indent=1, sort_keys=True) + "\n",
                                              encoding="utf-8")
        staging.rename(run_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return run_dir


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    r = sub.add_parser("run")
    r.add_argument("--fixture", required=True)
    r.add_argument("--arm", choices=["baseline", "skill"], required=True)
    r.add_argument("--model", choices=["haiku", "sonnet"], required=True)
    r.add_argument("--n", type=int, required=True)
    r.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        return probe()
    print(run(a.fixture, a.arm, a.model, a.n, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
