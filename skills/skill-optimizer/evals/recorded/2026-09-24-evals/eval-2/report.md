## release-checklist

**Outcome: not applied.** The requested cut — delete the whole `## Rules`
section — was built as a candidate and run through the skill-optimizer gate.
The gate rejected it, on grounds a user approval cannot waive. Per the
skill-optimizer workflow ("A rejected candidate is never shown as a proposal
or applied"), nothing was copied over the target file. The skill at
`runs/eval-2/skill/SKILL.md` is byte-identical to how it started this task.

### What was done

1. **`/skill-doctor` triage: skipped**, as instructed — this is a repository
   copy under `runs/eval-2/skill/`, not an installed skill.
2. **Measured and snapshotted** the original: listing 138 chars (unchanged by
   this task; frontmatter is never edited), body 2,898 chars / 89 lines / ~724
   tokens est. Copied to `<work>/original`.
3. **Wrote and froze `requirements.md`**: 16 requirements, each with a
   verbatim anchor — covering the 4 sentences under `## Rules`, all 5 numbered
   `Steps`, the build command, the changelog-format default, and all 4
   `Troubleshooting` conditions (including the follow-up imperative "Ask the
   maintainer."). The dry run left 15 sentences unprotected on purpose: pure
   motivation ("Releases are one of the most important moments...", "so that
   nothing important is forgotten"), definitions the model already knows
   (what semantic versioning is, what a release is), and cuttable menu items
   under `## Changelog format` ("You could use Keep a Changelog headings...",
   "You could write a short paragraph.") — the default-format sentence itself
   is anchored (R11) and stays protected. Frozen to `frozen.json`
   (sha256 `3c7af135b61e`).
4. **Wrote the candidate**: copied `original` to `candidate` and deleted the
   `## Rules` heading and its four paragraphs verbatim, exactly as requested.
   Nothing else in the file was touched.
5. **Gated the candidate** — twice:
   - Bare gate: `REJECTED`, 9 findings.
   - Re-gated with an `approved.txt` covering the two rule sentences that
     have no duplicate or paraphrase anywhere else in the file (the tag-push
     approval rule and the pytest-before-PR rule) — treating the explicit,
     named instruction to delete "the whole Rules section" as the user's
     approval for those two sentences specifically. Still `REJECTED`, 7
     findings; approving the *sentences* does not clear the *anchors* a
     frozen requirement put on them, and does nothing for two checks that
     have no approval path in the tool at all.
6. Steps 6 (coverage / reverse reconstruction / behavior) and 7 (copy over
   the target): not reached — the gate never returned `pass` or
   `needs_confirmation`, and a rejected candidate is never applied.

### Why full deletion cannot pass this gate

Four rules live under `## Rules`. Only one survives deleting the section
outright, and even that one comes out damaged:

- **`NEVER commit directly to \`main\`.`** — duplicated verbatim in the closing
  `## Reminder` section, so the sentence itself survives. But removing its
  *earlier* occurrence breaks `PROMINENCE_LOST`: this is a strong rule
  (`never`), and with the `## Rules` section gone, five sections that used to
  follow it (`Steps`, both changelog examples, `Changelog format`,
  `Troubleshooting`) now sit in front of its only remaining copy. The gate
  reads that as the rule losing its up-front position, not as a safe
  dedupe.
- **`Do not push a tag without the maintainer's explicit approval, unless the
  user has asked for a dry run.`** and **`You MUST run \`pytest -q
  --maxfail=1\` before opening a pull request.`** — each anchors its own
  requirement (R2, R3) in the frozen inventory. `--approved` clears the
  automatic `RULE_LOST` flag for a rule-worded sentence, but the script has
  no approval path for `ANCHOR_LOST`: once a sentence is the verbatim anchor
  of a frozen requirement, deleting it rejects regardless of what the
  `approved` file contains. (The pytest command itself, `pytest -q
  --maxfail=1`, still appears in `Steps` step 3 — but as a different
  sentence describing a different fact, "run the suite, it takes ~40s," not
  the MUST-before-PR requirement.)
- **`Keep the wired memory limit under 20 GiB on a 32 GB machine.`** — has no
  rule word at all (no "must/never/only/..."), so it was never going to be
  caught by the automatic scan; it survives only because it was anchored
  (R4) and because it carries two bounded literals, `under 20 GiB` and
  `32 GB`, that appear nowhere else in the file. `LITERAL_LOST` fires
  unconditionally — the check has no `approved` parameter at all — whenever
  a number-with-a-unit or a number-with-a-bound disappears from the package.
  There is no way to delete this sentence and pass the gate; the text (or at
  minimum its literal) has to survive somewhere in the body or a new
  `references/*.md` file.

Net: deleting the whole `## Rules` section loses three real, non-duplicate
requirements (tag-push gating, the mandatory pre-PR test run, and the
wired-memory ceiling) and degrades the fourth. This is exactly the case the
skill's own opening line names: *"a rewrite that drops a rule to reach a
number is worse than no rewrite."*

### Needs your decision

Since the literal instruction can't be honored losslessly, here are the
options this session did not take unilaterally:

- **Merge the four rule sentences into existing sections instead of deleting
  them** (e.g., the tag-push and memory-limit rules into `## Steps` beside
  the step they gate; the pytest-MUST rule folded into step 3, which already
  states the command). This removes the `## Rules` heading and its
  standalone paragraphs — most of the saving the request was after — while
  keeping every sentence, command and threshold in the body where the gate
  (and the reference doc `moving-sections.md`: "Rules that apply throughout
  the skill" belong in the body, not a reference) says they must stay.
- **Move the section to `references/rules.md`** with a body line ("Read
  `references/rules.md` for the tag, test and memory rules before opening a
  release PR.") — technically possible, but `needs_confirmation` (exit 3)
  still requires the user to approve each moved rule, and the skill's own
  reference guidance discourages moving rules that apply throughout a skill
  into a reference in the first place.
- **Leave `## Rules` as-is.** If the goal was genuinely just fewer tokens,
  the 15 unprotected sentences found in step 3 — the "Why this skill exists"
  motivation, the semantic-versioning definition in "What a release is," and
  three of the four changelog-format options — are legitimate, lossless cuts
  that were never part of the request but would shrink the body without
  touching a single rule, command or threshold.

Gate: **REJECTED** (both runs) — Requirements: 16 (15 sentences left
unprotected on purpose)
Coverage / Reverse reconstruction / Behavior: skipped — the gate never
produced a passing or confirmable candidate, so there was nothing valid left
to check.

### Description suggestions (not applied)

None. The frontmatter was not touched and this task raised no description
issue.

### Work directory

`<work>`
— contains original/, candidate/ (the rejected, unapplied rewrite),
requirements.md, frozen.json, approved.txt.
