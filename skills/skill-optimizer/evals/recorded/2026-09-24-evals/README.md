# 2026-09-24 eval runs

skill-optimizer 1.0.0, a fresh Claude Sonnet agent per run, one run per eval and per baseline. `gate.txt` in each eval folder is a fresh, independent re-run of `verify_rewrite.py` against the committed `frozen.json` and the run's own original and candidate directories, taken after the floor-division fix to the gate's printed percentage: it is the number to trust. Each run's own `report.md` is the unedited text that run produced at the time and may still show the older, rounded percentage; it is kept as written, not corrected, because it is evidence of what the run actually said, not a live figure. The `gate.txt` outputs come from the gate as it was on 2026-09-24, before the last round of gate fixes; the current gate refuses these older `frozen.json` files instead of re-checking them.

- `eval-0/`: nothing-to-cut. `report.md`, `requirements.md`, `frozen.json`, `SKILL.candidate.md` (byte-identical to the original, since nothing was cut), `gate.txt`.
- `eval-1/`: the full shrink, applied. `report.md`, `requirements.md`, `frozen.json`, `SKILL.result.md` (the applied result this run wrote over the target file, not an unapplied candidate), `gate.txt`.
- `eval-2/`: the refused deletion. `report.md`, `requirements.md`, `frozen.json`, `SKILL.candidate.md` (the rejected candidate; never applied), `gate.txt` (shows `REJECTED` with the lost rules and literals named).
- `eval-3/`: report-only. `report.md`, `requirements.md`, `frozen.json`, `SKILL.candidate.md`, `references/troubleshooting.md` (the proposed move, never applied), `gate.txt` (shows `NEEDS_CONFIRMATION`).
- `eval-5/`: description flagged, body applied. `report.md`, `requirements.md`, `frozen.json`, `SKILL.result.md` (the applied result), `gate.txt`.
- `baseline-eval-1/`, `baseline-eval-2/`: the two no-skill comparison runs described in `evals/README.md`, judged by the agent's own reasoning with no gate involved. `report.md` and `SKILL.result.md` (the file each baseline agent produced).

Eval 4 has no folder here. It was run against a real `/skill-doctor` capture taken from the author's own machine, and that capture is not published because it lists that machine's installed skills. The run passed: it named the never-used skills and where the capture said to turn them off, recommended disabling rather than rewriting, changed nothing, and asked which skill, if any, to optimize.

Every local filesystem path that appeared in a copied file has been replaced with the placeholder the skill's own documentation already uses for it: `<work>` for a run's scratch work directory, `<SKILL_DIR>` for the directory holding the skill under test.
