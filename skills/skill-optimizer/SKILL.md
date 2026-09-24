---
name: skill-optimizer
description: >-
  Use when asked to shrink, trim, compress or optimize a skill (a SKILL.md) so
  it costs fewer tokens, or when a skill feels too long. Cuts by deletion and
  restructuring only, can move rarely needed sections into references/ behind a
  load trigger, and checks that every rule, exception, command and threshold
  survives before anything is applied. Never edits the frontmatter; suggests
  description changes instead. Triggers: "optimize this skill", "shrink my
  skill", "this skill is too long", "trim SKILL.md", "my skills eat my context",
  "skill optimizer".
license: MIT
metadata:
  version: "1.0.0"
  author: IonDen
---

# Skill optimizer

Make a skill cheaper to load without losing an instruction. Any saving counts,
large or small. There is no size target: a rewrite that drops a rule to reach a
number is worse than no rewrite.

All paths below are relative to this skill's directory: in Claude Code that is
`${CLAUDE_SKILL_DIR}`; in Codex it is wherever this SKILL.md was loaded from
(`~/.agents/skills/skill-optimizer/`, a project's `.agents/skills/skill-optimizer/`,
or the older `~/.codex/skills/`). Resolve scripts from that directory, not from
a guessed home path.

Double-quote every path you put into a command, and if a path contains a shell
metacharacter such as `$`, `;`, `|` or a backtick, stop and ask the user first.

Default mode is report, then apply on approval. Do not change the user's skill
before they approve. A request that already says to apply ("shrink it and apply
the result") approves the cuts the gate passes; anything the gate or this
workflow says to ask about still needs an answer.

## 1. Sanity check with /skill-doctor

Skip this step when the user names a skill that is not installed (a repository
checkout, a copy in a temp directory) or says to skip it.

Otherwise, in Claude Code, get the `/skill-doctor` report: run
`claude -p "/skill-doctor"` if the shell allows it, or ask the user to run
`/skill-doctor` and paste the table. Quote only the rows you act on.

- A general request ("my skills eat my context"): the report is most of the
  answer. A skill that is never invoked should be disabled, not optimized. Say
  so, quote where the report says to turn it off, and ask which skill to optimize.
- The named skill was never invoked: say so, and ask whether to optimize it anyway or disable it.
- No report (Codex, an older Claude Code): say that no usage data was available and continue.

Spec compliance, broken links and frontmatter faults belong to other tools:
`agentskills validate` from the `skills-ref` package, or a skill
linter. Mention one if you notice such a fault, and move on.

## 2. Measure and snapshot

```bash
python3 scripts/measure_skills.py <skill-dir>
mktemp -d
```

`mktemp -d` prints a new directory. Shell variables do not survive between
commands, so write that path out in full wherever this skill says `<work>`.

```bash
cp -RL <skill-dir> <work>/original
```

The snapshot must be real files, so a symlinked install is copied with its
links resolved.

The listing (description plus `when_to_use`) is paid on every turn; the body is
paid when the skill runs. This skill rewrites the body only.

## 3. Write the requirement list, then freeze it

Before any rewrite exists, read the whole skill and write `<work>/requirements.md`:
every instruction the skill gives, one entry each, with an anchor copied
verbatim from one sentence of the original.

```text
R1: Never commit directly to main.
  anchor: NEVER commit directly to `main`.
R2: Read the repository conventions before starting.
  anchor: Read the repository conventions before starting work
```

An anchor has at least three words, sits inside one sentence, and protects that
whole sentence word for word. List plain instructions as well as MUST and NEVER
rules: each step and its order, conditions ("if the build fails, ..."),
commands, thresholds, gotchas, and the reason attached to a rule. Then check the
list:

```bash
python3 scripts/extract_requirements.py <work>/original --requirements <work>/requirements.md --dry-run
```

It prints two groups. The first is every sentence that has no rule word, no
literal and no anchor yet. The second is every sentence with no rule word or
anchor that carries a literal: the gate checks only that literal, so the rest of
the sentence, a condition included, can go unless you anchor it. Anchor each one
that is an instruction, a condition or a reason; what is left is what you may
cut. When the list is right, freeze it, once:

```bash
python3 scripts/extract_requirements.py <work>/original --requirements <work>/requirements.md -o <work>/frozen.json
```

It refuses an anchor that is not in the original, and it refuses to overwrite
an existing freeze. If a requirement turns out wrong after the candidate exists,
say so in the report; do not freeze again.

## 4. Write the candidate

```bash
cp -RL <work>/original <work>/candidate
```

Edit only `<work>/candidate/SKILL.md`, and add new files only under
`<work>/candidate/references/`. Read `references/what-not-to-cut.md` before the
first edit.

- Delete what does not earn its tokens: definitions the model already knows,
  motivation that carries no rule, a menu of options where one default and an
  escape hatch will do, a second example that teaches nothing the first did not.
- Restructure: merge duplicate passages, reorder within a section, turn prose
  into a list. Never change the order of steps or move a rule to another
  section; the gate asks when a rule changes section.
- Move a section the skill needs only sometimes into a new
  `references/<topic>.md`, leaving one line in the body that says when to read
  it. Read `references/moving-sections.md` before moving anything. When unsure
  whether a section is needed on every run, ask the user.

Add no words of your own except that one line per moved section. Never
paraphrase or shorten a sentence that carries a rule word or an anchor, never
change a command, path, flag, URL or threshold, and never edit the frontmatter
or an existing file other than SKILL.md. A sentence with a rule word that reads
as pure motivation ("so that nothing important is forgotten") may be deleted
only if the user approves that exact sentence; list it under "Needs your decision".

## 5. Gate the candidate

```bash
python3 scripts/verify_rewrite.py --frozen <work>/frozen.json --original <skill-dir> --candidate <work>/candidate
```

| Exit | Status | Next |
|---|---|---|
| 0 | `pass` | Go to step 6. |
| 0 | `unchanged` | Nothing could be cut without loss. Report that and stop. |
| 1 | `rejected` | Fix each finding and gate again. A rejected candidate is never shown as a proposal or applied. |
| 2 | input error | Fix the paths. |
| 3 | `needs_confirmation` | A rule or anchored sentence moved into a reference or under another heading. Go to step 6, and ask about each one in the report. |

Once the user approves deleting specific sentences, write them to
`<work>/approved.txt`, one per line, copied exactly, and add
`--approved <work>/approved.txt` to the gate command. Only the user's answer to
a sentence you listed counts as approval. A request to delete a section, or to
apply everything, does not approve the rule sentences in it. Never write
approved.txt before asking.

## 6. Check what a script cannot

1. Coverage. For each entry in `requirements.md`, one at a time, confirm the
   candidate still carries it where an agent will find it.
2. Reverse reconstruction. Give a fresh agent the candidate SKILL.md alone,
   tell it to open a reference file only where the candidate says to, and ask
   it to list every instruction it finds. Compare with `requirements.md`. An
   instruction it cannot find has become unfindable, even if its text is still
   in a reference file.
3. Behaviour. If the skill ships `evals/evals.json`, or the user gave test
   prompts, run each one twice: once with the original skill and once with the
   candidate, a fresh agent and fresh copies of any fixtures each time. Score
   every clause of each expected outcome for both. If a clause the original met
   fails with the candidate, run that eval once more per version; if it still
   differs, the candidate changed behaviour: find the cut that caused it and
   restore it. Keep every assertion that passes on both; that is the point.

Without a way to start a fresh agent, say which of 2 and 3 were skipped and why.

## 7. Report, then wait

```text
## <skill-name>
Body: <before> -> <after> chars (<-n%>), <before> -> <after> lines
Moved to references: <n> chars, read only when <condition>
Listing: <n> chars, unchanged (the frontmatter is never edited)

Cuts
- <what was cut>: <why it does not earn its tokens>

Moved
- <section> -> references/<file>.md, loaded by: "<the line left in the body>"

Needs your decision
- <rule sentence> would move to references/<file>.md. Move it, or keep it in the body?
- <rule sentence> reads as motivation. Delete it, or keep it?
- <rule sentence> now sits under "<heading>", not "<heading>". Keep the move, or put it back?

Deleted with your approval: <sentence>

Gate: pass | needs confirmation    Requirements: <n> (<n> sentences left unprotected on purpose)
Coverage: <n>/<n>    Reverse reconstruction: <n>/<n> | skipped: <why>
Behaviour: <n>/<n> clauses unchanged | skipped: <why>

Description suggestions (not applied)
- <suggestion>: <why>
```

Every cut needs a reason in that list. Fill "Deleted with your approval" from
the gate's "deleted with the user's approval" lines, one line each, or leave it
out. Put description ideas under "Description suggestions": when the description
passes a limit `measure_skills.py` notes, or says what the skill does but not
when to use it.
Never apply them; the user may want the triggers as they are.

Apply only after approval. If the user declines a cut or a move, put that text
back in the candidate and gate again. Right before copying, gate once more; it
must exit 0, or 3 when the user approved every move it lists. Then run
`mkdir -p <skill-dir>/references` if the candidate has references, and copy
`<work>/candidate/SKILL.md` and each new reference file over the skill. If the
skill lives in a plugin cache or a directory an installer manages, say that an
update will overwrite the change and that the lasting fix belongs in its source.
