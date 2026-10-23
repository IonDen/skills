#!/usr/bin/env python3
"""Apply the pre-registered decision rules (criteria.json) to verdict records.

    python3 decide.py recorded/<date>/verdicts.jsonl

gap: does the current text miss enough held-out prompts to justify a new
description? ship: does a new arm beat an old one on held-out prompts without
loading on near-miss prompts? Only the decision model's runs decide."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = ("writing-tests-that-can-fail", "skill-optimizer", "subagent-optimizer")
SCORED = {"hit", "miss"}


def load_criteria() -> dict:
    return json.loads((HERE / "criteria.json").read_text(encoding="utf-8"))


def load_verdicts(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _should(records: list[dict], skill: str, arm: str, model: str) -> dict[str, list[str]]:
    """Held-out should-load outcomes per prompt, scored runs only."""
    out: dict[str, list[str]] = defaultdict(list)
    for r in records:
        if (r["skill"] == skill and r["arm"] == arm and r["model"] == model and r["half"] == "heldout"
                and r["kind"] in ("should", "delegate") and r["outcome"] in SCORED):
            out[r["prompt_id"]].append(r["outcome"])
    return out


def _near_false(records: list[dict], skill: str, arm: str, model: str | None,
                halves: tuple[str, ...] = ("heldout",)) -> int:
    return sum(1 for r in records
               if r["skill"] == skill and r["arm"] == arm and r["half"] in halves and r["kind"] == "near"
               and r["outcome"] == "false-load" and (model is None or r["model"] == model))


def gap(records: list[dict], skill: str, arm: str = "current", crit: dict | None = None) -> dict:
    crit = crit or load_criteria()
    per = _should(records, skill, arm, crit["decision_model"])
    prompts = sorted(p for p, outs in per.items() if outs.count("miss") >= crit["gap_miss_reps"])
    return {"gap": len(prompts) >= crit["gap_min_prompts"], "prompts": prompts}


def ship(records: list[dict], skill: str, new_arm: str, old_arm: str, crit: dict | None = None,
         relative_near: bool = False, near_halves: tuple[str, ...] = ("heldout",)) -> dict:
    crit = crit or load_criteria()
    model = crit["decision_model"]
    new, old = _should(records, skill, new_arm, model), _should(records, skill, old_arm, model)
    net = pooled = 0
    for p in sorted(set(new) & set(old)):
        n, o = new[p].count("hit"), old[p].count("hit")
        net += (n > o) - (n < o)
        pooled += n - o
    near_opus = _near_false(records, skill, new_arm, model, near_halves)
    near_total = _near_false(records, skill, new_arm, None, near_halves)
    if relative_near:
        near_ok = (near_opus <= _near_false(records, skill, old_arm, model, near_halves)
                   and near_total <= _near_false(records, skill, old_arm, None, near_halves))
    else:
        near_ok = near_opus <= crit["near_false_opus"] and near_total <= crit["near_false_total"]
    ok = net >= crit["ship_net_improved"] and pooled >= crit["ship_pooled_hits"] and near_ok
    return {"ship": ok, "net_improved": net, "pooled_delta": pooled,
            "near_false_opus": near_opus, "near_false_total": near_total}


def report(records: list[dict], crit: dict | None = None) -> dict:
    """Gap per skill, plus a ship verdict for each new arm present in the records:
    candidate descriptions (absolute near rule), the Phase 1 snippet and the
    Phase 2 snippet (both relative to current; snippet2 also counts the fresh
    near-miss prompts)."""
    crit = crit or load_criteria()
    ran = {(r["skill"], r["arm"]) for r in records}
    out = {s: {"gap": gap(records, s, crit=crit)} for s in SKILLS}
    for s in SKILLS:
        if (s, "candidate") in ran:
            out[s]["candidate"] = ship(records, s, "candidate", "current", crit)
    wt = "writing-tests-that-can-fail"
    if (wt, "current+snippet") in ran:
        out[wt]["snippet"] = ship(records, wt, "current+snippet", "current", crit, relative_near=True)
    if (wt, "current+snippet2") in ran:
        out[wt]["snippet2"] = ship(records, wt, "current+snippet2", "current", crit, relative_near=True,
                                   near_halves=("heldout", "fresh"))
    return out


if __name__ == "__main__":
    print(json.dumps(report(load_verdicts(Path(sys.argv[1]))), indent=2, sort_keys=True))
