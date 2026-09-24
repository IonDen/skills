# skill-optimizer: cut a skill's token cost without losing an instruction

A skill optimizer for Claude Code and OpenAI Codex, packaged as an agent skill. It reads a `SKILL.md`, works out what part of it is paid on every turn and what part is paid only when the skill runs, and cuts what it can prove is redundant, never merely what looks long. It is plain Markdown plus four Python scripts, so it runs under both harnesses.

Triggers: "optimize this skill", "shrink my skill", "this skill is too long", "trim SKILL.md", "my skills eat my context", "skill optimizer".

## Why this exists

The Agent Skills spec caps a skill's `description` at 1,024 characters and recommends keeping `SKILL.md` under 500 lines, with its instructions under roughly 5,000 tokens. Claude Code defaults to trimming a skill's listing past 1,536 characters, and Codex is reported to budget at most 2% of the context window for the skill listing, or 8,000 characters when that figure is unknown. `/skill-doctor` (Claude Code v2.1.252+) shows what a skill actually costs and how often it fires. None of that tells you which sentence in your own over-length skill is safe to cut.

A skill's description and any `when_to_use` field are paid on every turn it could trigger, whether or not it does; the body is paid only when the skill actually runs. A skill accumulates the same bloat a hand-tuned prompt does: a rule restated twice, an example that teaches nothing the first one did not, a troubleshooting section every run pays to load and almost never reads. Cutting that by hand risks losing the sentence that mattered. This skill only removes text a deterministic check can prove is redundant, and it checks first: run against a skill that was already tight, it found almost nothing worth cutting and said so instead of forcing a number.

## What the gate checks

`verify_rewrite.py` is the gate: a deterministic check with no model call, run against a frozen inventory of the original skill. It exits 0 (`pass`, or `unchanged` when the candidate is the original), 1 (`rejected`, and a rejected candidate is never shown as a proposal or applied), 2 (a missing or unreadable input) or 3 (`needs_confirmation`).

| Code | What it means |
|---|---|
| `ORIGINAL_CHANGED` | The skill on disk isn't the one that was frozen |
| `FRONTMATTER_CHANGED` | Any byte of the frontmatter differs |
| `FILE_CHANGED` | A file other than `SKILL.md` differs or is missing |
| `UNEXPECTED_FILE` | A new file sits outside `references/*.md` |
| `NEW_TEXT` | A sentence or heading uses words the original never put together |
| `CODE_EDITED` | A surviving code block differs from every block in the original |
| `RULE_LOST` | A sentence or heading with a rule word is gone or was edited |
| `ANCHOR_LOST` | A sentence a requirement anchors is gone or was edited |
| `LITERAL_LOST` | A command, path, flag, URL, version, date or threshold is gone or changed |
| `PROMINENCE_LOST` | A strong rule now has text in front of it that used to sit behind it, or sits under a deeper heading |
| `TERMINAL_MOVED` | A closing rule no longer closes the body |
| `REFERENCE_UNLINKED` | A new `references/` file exists, but nothing in the body sends the agent to it |
| `NOT_SMALLER` | The candidate body didn't get smaller |
| `MOVED_TO_REFERENCE` | A rule or an anchored sentence now lives only in a new reference file (exit 3, not a rejection) |

The first thirteen codes reject the candidate outright. `MOVED_TO_REFERENCE` works differently: it doesn't reject, it asks, and the report lists each such move for you to confirm or decline before anything is copied over the original. A rule sentence can also be deleted outright rather than moved, but only after you approve that exact sentence: it goes into `approved.txt`, one sentence per line, copied exactly, and the gate is re-run with `--approved approved.txt`. Without that file, deleting a rule sentence is `RULE_LOST` and the candidate is rejected.

## What it never does

- Edit the frontmatter. A shorter `description` is suggested in the report, never applied. The gate rejects any candidate whose frontmatter differs by even one byte.
- Aim for a size. There is no target: a rewrite that drops a rule to hit a number is worse than no rewrite, and a skill with nothing to cut is reported as such and left untouched.
- Paraphrase or shorten a sentence that carries a rule word or an anchor. Such a sentence can be moved into a reference file or deleted outright, but only with your approval, and never reworded.
- Do another tool's job. Spec compliance, broken links and frontmatter faults belong to `agentskills validate` (the `skills-ref` package) or a skill linter; deciding whether a skill nobody invokes should be disabled belongs to `/skill-doctor`, not to a rewrite.

## One real before and after

[subagent-optimizer](../subagent-optimizer/), a real skill in this repository, optimized by skill-optimizer 1.0.0. Body only, one run, approval given in advance for anything the gate would pass:

| Metric | Before | After | Change |
|---|---|---|---|
| Body chars | 8,863 | 8,758 | -105 (-1.2%) |
| Body lines | 176 | 175 | -1 |
| Chars moved to references | - | 0 | nothing moved |

Gate: pass, re-run independently against the frozen original. Two sentences were cut, both plain restatements with no rule word and no anchor: one cheered for a conclusion the sentence right before it already reached, the other restated the heading that followed it. Two more sentences that carry a rule word ("must", "isn't") were left in place and flagged as decisions instead, because the agent read both as the stated reason behind a rule rather than filler. Requirements extracted: 28 (16 sentences left unprotected on purpose: short bold lead-in labels, none of them cut). Coverage: 28/28. A separate fresh agent, given only the optimized `SKILL.md` and asked to reconstruct every instruction it could find, returned 81 items; every one of the 28 requirements mapped onto at least one, and neither cut sentence appeared.

The skill was already tight. Run against a real document instead of a synthetic fixture, the optimizer found almost nothing it could cut without loss, and said so rather than forcing a number. (One of the evals' own fixtures is a deliberately padded test skill built to shrink by 37% under the same gate, see `evals/README.md`, so the small real-skill number reflects the input, not a ceiling on what the skill will cut.)

Behaviour check: subagent-optimizer's own eval 1 and eval 3, each run once against the original `SKILL.md` and once against the optimized copy, each by a fresh agent on a fresh copy of the fixtures. All 13 of 13 expected clauses were met by both versions; none differed. One of the four runs noted, in its own report, that its target agent file matched a fixture behind one of this skill's own recorded eval records. That is a fact about that run's independence, not about any behaviour difference traceable to the two deleted sentences.

Full method and report: [`evals/recorded/2026-09-24-subagent-optimizer/`](evals/recorded/2026-09-24-subagent-optimizer/).

## Install

```bash
npx skills add IonDen/skills --skill skill-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill skill-optimizer -g -a codex -y   # --copy for real files
```

The `-a claude-code` matters: most agents share `.agents/skills` and the CLI installs there by default, while Claude Code reads `.claude/skills` and is not pre-selected in the interactive picker.

As a plugin, which also keeps it updated:

```text
/plugin marketplace add IonDen/skills        # Claude Code
codex plugin marketplace add IonDen/skills   # Codex
```

By hand: copy this folder into `~/.claude/skills/` or `~/.agents/skills/`.

## Use

- "Shrink this skill" or "optimize this skill": scope is whichever `SKILL.md` you point at.
- "My skills eat my context, fix it": runs `/skill-doctor` first and triages against real usage, rather than rewriting a skill nobody invokes.
- "Look at this skill and tell me how you'd make it cheaper, I haven't decided anything yet": report only, nothing changes on disk.

It reports first and stops. Nothing is edited until you approve each cut.

## What ships

```text
skill-optimizer/
├── SKILL.md                       the workflow: sanity check, measure, freeze requirements, rewrite, gate, verify, report
├── agents/openai.yaml             Codex and ChatGPT metadata
├── references/
│   ├── moving-sections.md         when a section belongs in references/, and how to move it
│   └── what-not-to-cut.md         what looks safe to cut but isn't
├── scripts/
│   ├── measure_skills.py          listing vs. body size for a skill, in characters
│   ├── extract_requirements.py    turns requirements.md into the frozen inventory the gate checks against
│   ├── verify_rewrite.py          the gate: exit 0 pass/unchanged, 1 rejected, 2 input error, 3 needs confirmation
│   └── skillmd.py                 shared SKILL.md parsing the other scripts use
└── evals/
    ├── evals.json                 six prompts with expected outcomes
    ├── fixtures/                  the three SKILL.md files they run against
    ├── README.md                  what each eval checks, and the recorded results
    └── recorded/                  measured runs, including a real skill's before and after
```

## Sources

- [Agent Skills specification](https://agentskills.io/specification): the 1,024-character description limit, the under-500-line guidance for `SKILL.md`, and the under-5,000-token guidance for instructions. `when_to_use` is not part of the spec.
- [Claude Code skills docs](https://code.claude.com/docs/en/skills): `/skill-doctor` needs Claude Code v2.1.252+.
- [anthropics/claude-code#47627](https://github.com/anthropics/claude-code/issues/47627): the 1,536-character per-skill listing cap, a default and configurable, not stated in Anthropic's own docs.
- [openai/codex#24299](https://github.com/openai/codex/issues/24299): Codex's skill listing reported to use at most 2% of the context window, or 8,000 characters when that figure is unknown.

## Version history

**1.0.0**: First public release.

## Author and license

By [Denis Ineshin](https://github.com/IonDen). MIT.
