"""Candidate descriptions for Phase 2: frozen before the run, built on the
shipped text, inside the listing limit and free of words from the prompts."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIG = ROOT / "evals" / "triggering"
CANDS = TRIG / "candidates"
SKILLS = ROOT / "plugins" / "ionden-skills" / "skills"


def candidates():
    return sorted(CANDS.glob("*.md"))


def test_every_candidate_is_frozen_by_hash():
    hashes = json.loads((CANDS / "hashes.json").read_text(encoding="utf-8"))
    assert set(hashes) == {c.stem for c in candidates()} and hashes
    for c in candidates():
        assert hashlib.sha256(c.read_bytes()).hexdigest() == hashes[c.stem], c.stem


def test_candidates_keep_the_shipped_sentences_and_fit_the_limit(trigger_runner):
    for c in candidates():
        shipped = trigger_runner.description_of((SKILLS / c.stem / "SKILL.md").read_text(encoding="utf-8"))
        text = " ".join(c.read_text(encoding="utf-8").split())
        assert len(text) <= 1024, c.stem
        body = shipped.split(" Triggers:")[0]
        assert body in text, c.stem


def test_candidates_avoid_guard_words():
    words = json.loads((TRIG / "prompts.json").read_text(encoding="utf-8"))["guard_words"]
    for c in candidates():
        text = c.read_text(encoding="utf-8").lower()
        assert not [w for w in words if re.search(rf"\b{re.escape(w.lower())}\b", text)], c.stem
