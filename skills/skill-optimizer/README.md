# skill-optimizer: cut a skill's token cost without losing an instruction

A skill optimizer for Claude Code and OpenAI Codex, packaged as an agent skill. It reads a `SKILL.md`, works out what part of it is paid on every turn and what part is paid only when the skill runs, and cuts only what its gate allows, with a reason for each cut, rather than whatever looks long. It is plain Markdown plus five Python scripts, so it runs under both harnesses.

It works on agent skills, the folders with a `SKILL.md`. Subagent definitions in `.claude/agents/` and Codex agents in `.codex/agents/` are a different thing; [subagent-optimizer](../subagent-optimizer/) handles those.

Triggers: "optimize this skill", "shrink my skill", "this skill is too long", "trim SKILL.md", "my skills eat my context", "skill optimizer".

## Why this exists

The Agent Skills spec caps a skill's `description` at 1,024 characters and recommends keeping `SKILL.md` under 500 lines, with its instructions under roughly 5,000 tokens. Claude Code defaults to trimming a skill's listing past 1,536 characters, and Codex is reported to budget at most 2% of the context window for the skill listing, or 8,000 characters when that figure is unknown. `/skill-doctor` (Claude Code v2.1.252+) shows what a skill actually costs and how often it fires. None of that tells you which sentence in your own over-length skill is safe to cut.

A skill's description and any `when_to_use` field are paid on every turn it could trigger, whether or not it does; the body is paid only when the skill actually runs. A skill accumulates the same bloat a hand-tuned prompt does: a rule restated twice, an example that teaches nothing the first one did not, a troubleshooting section every run pays to load and almost never reads. Cutting that by hand risks losing the sentence that mattered. This skill removes only text its gate allows: a sentence with no rule word and no anchor, and only while every literal in it survives somewhere in the skill. Each cut comes with a stated reason, and the model checks after the gate (coverage, a reverse reconstruction, a behaviour run) cover what a script cannot judge. It also looks before it cuts: run against a skill that was already tight, it found almost nothing worth cutting and said so instead of forcing a number.

## What the gate checks

`verify_rewrite.py` is the gate: a deterministic check with no model call, run against a frozen inventory of the original skill. It exits 0 (`pass`, or `unchanged` when the candidate is the original), 1 (`rejected`, and a rejected candidate is never shown as a proposal or applied), 2 (a missing or unreadable input, a candidate `SKILL.md` that is a symlink, an original `SKILL.md` linked to anything but another `SKILL.md`, or a freeze written by an older version) or 3 (`needs_confirmation`).

| Code | What it means |
|---|---|
| `ORIGINAL_CHANGED` | The skill on disk isn't the one that was frozen |
| `FRONTMATTER_CHANGED` | Any byte of the frontmatter differs |
| `FILE_CHANGED` | A file other than `SKILL.md` differs or is missing |
| `UNEXPECTED_FILE` | A new file sits outside `references/*.md`, a file is a symlink, or a new reference takes a path that already exists in the installed skill as a file or link |
| `NEW_TEXT` | A sentence or heading uses words the original never put together. The one exception is the line that points to a new reference, and it may add at most 25 words and no strong rule word |
| `CODE_EDITED` | A surviving code block differs from every block in the original |
| `RULE_LOST` | A sentence or heading with a rule word is gone or was edited |
| `ANCHOR_LOST` | A sentence a requirement anchors is gone or was edited |
| `LITERAL_LOST` | A command, path, flag, URL, version, date or threshold is gone or changed |
| `PROMINENCE_LOST` | A strong rule or a rule heading now has text in front of it that used to sit behind it, or sits deeper than it did. A rule heading the original repeats, such as "Pitfalls to avoid" in two sections, has no single position, but its highest copy may not end up deeper than the highest level it had |
| `TERMINAL_MOVED` | A closing rule no longer closes the body |
| `REFERENCE_UNLINKED` | A new `references/` file exists, but nothing in the body sends the agent to it |
| `NOT_SMALLER` | The candidate body didn't get smaller |
| `MOVED_TO_REFERENCE` | A rule or an anchored sentence now lives only in a new reference file (exit 3, not a rejection) |
| `SECTION_CHANGED` | A rule or an anchored sentence now sits under a different heading (exit 3, not a rejection). A shortened heading still counts as the heading it was cut from, when exactly one original heading fits and that heading is no longer in the body |

The first thirteen codes reject the candidate outright. `MOVED_TO_REFERENCE` and `SECTION_CHANGED` don't reject. The workflow puts each such rule back where it was and lists the move under "Optional further cuts (not applied)", unless your request already approved moving that item. A rule sentence, a rule heading or an anchored sentence can also be deleted outright, but only after you approve that exact text: it goes into `approved.txt`, one sentence per line, copied exactly, and the gate is re-run with `--approved approved.txt`. The text has to be gone whole. If a candidate sentence keeps some of its words in order ("Deploy on Fridays." left from "Deploy on Fridays only when the lead signs off."), the gate reads it as trimmed, not deleted, names the sentence left over, and still rejects it. A literal that appeared only in sentences you approved and that were deleted whole goes with them. Without that file, deleting a rule sentence is `RULE_LOST` and the candidate is rejected.

A sentence with no rule word and no anchor is protected only through the literals it carries, if any. Before the freeze, a dry run lists those sentences in two groups, the ones nothing protects and the ones protected only through a literal, so the instructions and conditions among them can be anchored first.

## What it never does

- Edit the frontmatter. A shorter `description` is suggested in the report, never applied. The gate rejects any candidate whose frontmatter differs by even one byte.
- Aim for a size. There is no target: a rewrite that drops a rule to hit a number is worse than no rewrite, and a skill with nothing to cut is reported as such and left untouched.
- Paraphrase or shorten a sentence that carries a rule word or an anchor. Such a sentence can be moved into a reference file or deleted outright, but only with your approval, and never reworded.
- Copy or read a link other than the skill's own. The snapshot resolves the skill's directory and its `SKILL.md` when either is a symlink (a symlinked install, or a per-file install such as stow or home-manager), and never copies or reads any other link inside the skill. It lists each link it skipped, the freeze leaves links out, and the gate rejects a link in the candidate.
- Recommend disabling or deleting a skill. Usage data from `/skill-doctor` (which skills are never invoked, which cost the most) is shown as information only; what to keep is your call.
- Do another tool's job. Spec compliance, broken links and frontmatter faults belong to `agentskills validate` (the `skills-ref` package) or a skill linter.

## One real before and after

[subagent-optimizer](../subagent-optimizer/), a real skill in this repository, optimized by skill-optimizer 1.0.0. Body only, one run, approval given in advance for anything the gate would pass:

| Metric | Before | After | Change |
|---|---|---|---|
| Body chars | 8,863 | 8,758 | -105 (-1.2%) |
| Body lines | 176 | 175 | -1 |
| Chars moved to references | - | 0 | nothing moved |

Gate: pass, re-run independently against the frozen original. Two sentences were cut, both plain restatements with no rule word and no anchor: one cheered for a conclusion the sentence right before it already reached, the other restated the heading that followed it. Two more sentences that carry a rule word ("must", "isn't") were left in place and flagged as decisions instead, because the agent read both as the stated reason behind a rule rather than filler. Requirements extracted: 28 (16 sentences left unprotected on purpose: short bold lead-in labels, none of them cut). Coverage: 28/28. A separate fresh agent, given only the optimized `SKILL.md` and asked to reconstruct every instruction it could find, returned 81 items; every one of the 28 requirements mapped onto at least one, and neither cut sentence appeared.

The skill was already tight. Run against a real document instead of a synthetic fixture, the optimizer found almost nothing it could cut without loss, and said so rather than forcing a number. (One of the evals' own fixtures is a deliberately padded test skill built to shrink by 29.7% (2,898 to 2,036 characters) under the same gate, keeping and listing every further cut it wasn't sure was safe instead of applying it; see `evals/README.md`. So the small real-skill number reflects the input, not a ceiling on what the skill will cut.)

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
- "My skills eat my context, fix it": runs `/skill-doctor` first, lists your skills by what their listing costs, with each one's usage, and asks which to optimize.
- "Look at this skill and tell me how you'd make it cheaper, I haven't decided anything yet": report only, nothing changes on disk.

It runs through to the report without stopping to ask questions, and nothing is edited until you approve. Saying up front "shrink it and apply the result" applies every cut the gate passes. When it isn't sure a cut is safe (deleting a rule sentence that reads as motivation, moving a rule into a reference or under another heading, moving a section that might be needed on every run), it keeps the text and lists the cut under "Optional further cuts (not applied)" with what it would save. You can approve any of them later. It would rather trim less than drop an instruction.

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
│   ├── snapshot.py                copies a skill into a work directory without following inner links
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

**1.0.1**: A version, date or number written inside a longer name, such as `rust-v0.156.1` or `python-3.12`, is now frozen as the whole name. Before, the freeze kept only `v0.156.1`, which the gate then could not find on its own, so a skill that mentioned such a name was rejected even when nothing in it had changed.

**1.0.0**: First public release.

## Author and license

By [Denis Ineshin](https://github.com/IonDen). MIT.
