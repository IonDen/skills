---
name: skill-optimizer
description: >-
  Use when asked to shrink, trim, compress or optimize an agent skill (a folder
  with a SKILL.md) so it costs fewer tokens, or when a skill feels too long.
  Cuts by deletion and restructuring only, can move rarely needed sections into
  references/ behind a load trigger, and checks that every rule, exception,
  command and threshold survives before anything is applied. Never edits the
  frontmatter; suggests description changes instead. Subagent definitions in
  .claude/agents/ and Codex agents in .codex/agents/ are a different thing,
  handled by subagent-optimizer.
  Triggers: "optimize this skill", "shrink my skill", "this skill is too long",
  "trim SKILL.md", "my skills eat my context", "skill optimizer".
license: MIT
metadata:
  version: "1.1.0"
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
before they approve. A report-only request changes nothing in the user's skill.
A request that already says to apply ("shrink it and apply the result") applies
every cut the gate passes, with no questions.

Run the workflow through to the report without stopping to ask. When you are
not sure a cut or a move is safe, keep the text, carry on, and list the cut in
the report under "Optional further cuts (not applied)". Trimming less is fine;
losing an instruction is not.

## 1. Sanity check with /skill-doctor

Skip this step when the user names a skill that is not installed (a repository
checkout, a copy in a temp directory) or says to skip it.

Otherwise, in Claude Code, run `claude -p "/skill-doctor"` if the shell allows
it. Quote only the rows you act on. For a named skill, do not wait for the
report: proceed, and note its usage data if you have it. Ask the user to run
`/skill-doctor` and paste the table only for a general request, when the
command cannot run.

- Usage data is information only. Show which skills are never invoked or cost
  the most, and never recommend disabling or deleting a skill; the user decides.
- A general request ("my skills eat my context"): list the skills by listing
  cost, each with its usage, and ask which to optimize.
- No report (Codex, an older Claude Code): say that no usage data was available and continue.

Spec compliance, broken links and frontmatter faults belong to other tools:
`agentskills validate` from the `skills-ref` package, or a skill
linter. Mention one if you notice such a fault, and move on.

## 2. Measure and snapshot

```bash
python3 scripts/measure_skills.py "<skill-dir>"
mktemp -d
```

`mktemp -d` prints a new directory. Shell variables do not survive between
commands, so write that path out in full wherever this skill says `<work>`.

```bash
python3 scripts/snapshot.py "<skill-dir>" "<work>/original"
```

The snapshot is real files. It follows the skill itself, a symlinked skill
directory or a SKILL.md linked to another SKILL.md, but never copies or reads
any other link inside the skill. It prints each link it skipped; list them in
the report.

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
whole sentence word for word. In a table each cell is a separate target, so
anchor inside one cell. Do not let an anchor cross a line that ends in a hyphen
(`what-to-` / `read-for-what`): the lines join with a space, and it never
matches.

List plain instructions as well as MUST and NEVER rules: each step and its
order, conditions ("if the build fails, ..."), commands, thresholds, gotchas,
and the reason attached to a rule. Then check the list:

```bash
python3 scripts/extract_requirements.py "<work>/original" --requirements "<work>/requirements.md" --dry-run
```

It prints two groups. The first is every sentence that has no rule word, no
literal and no anchor yet. The second is every sentence with no rule word or
anchor that carries a literal: the gate checks only that literal, so the rest of
the sentence, a condition included, can go unless you anchor it. Anchor each one
that is an instruction, a condition or a reason; what is left is what you may
cut. When the list is right, freeze it, once:

```bash
python3 scripts/extract_requirements.py "<work>/original" --requirements "<work>/requirements.md" -o "<work>/frozen.json"
```

It refuses an anchor that is not in the original, and it refuses to overwrite
an existing freeze. If a requirement turns out wrong after the candidate exists,
say so in the report; do not freeze again.

## 4. Write the candidate

```bash
python3 scripts/snapshot.py "<work>/original" "<work>/candidate"
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
  whether a section is needed on every run, keep it in the body and list the
  move as an optional cut.

Add no words of your own except that one line per moved section. Never
paraphrase or shorten a sentence that carries a rule word or an anchor, never
change a command, path, flag, URL or threshold, and never edit the frontmatter
or an existing file other than SKILL.md. A sentence with a rule word that reads
as pure motivation ("so that nothing important is forgotten") stays in the
body: list it as an optional cut. It goes only if the user approves that exact
sentence.

## 5. Gate the candidate

```bash
python3 scripts/verify_rewrite.py --frozen "<work>/frozen.json" --original "<skill-dir>" --candidate "<work>/candidate"
```

| Exit | Status | Next |
|---|---|---|
| 0 | `pass` | Go to step 6. |
| 0 | `unchanged` | Nothing could be cut without loss. Report that and stop. |
| 1 | `rejected` | Fix each finding and gate again. A rejected candidate is never shown as a proposal or applied. |
| 2 | input error | Fix the paths. |
| 3 | `needs_confirmation` | A rule or anchored sentence moved into a reference or under another heading, or lost its bold or italic. Put each listed item back as it was, gate again, and list the change as an optional cut. A change stays only if the user's request already approved that specific item. |

Use `--approved` only after the user answers the optional-cuts list. Write the
sentences they approve deleting to `<work>/approved.txt`, one per line, copied
exactly, and add `--approved "<work>/approved.txt"` to the gate command. Only the
user's answer to a sentence you listed counts as approval. A request to delete
a section, or to apply everything, does not approve the rule sentences in it.
Never write approved.txt before the user answers.

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

## 7. Report, then apply what is approved

```text
## <skill-name>
Body: <before> -> <after> chars (<-n%>), <before> -> <after> lines
Moved to references: <n> chars, read only when <condition>
Listing: <n> chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: <path>, ... | none

Cuts
- <what was cut>: <why it does not earn its tokens>

Moved
- <section> -> references/<file>.md, loaded by: "<the line left in the body>"

Optional further cuts (not applied)
- Move <section> to references/<file>.md: saves <n> chars; you agree it is needed only when <condition>
- Move <rule sentence> to references/<file>.md: saves <n> chars; you agree an agent reads it only after following the load line
- Delete <rule sentence>: saves <n> chars; you agree it is motivation, not an instruction
- Put <rule sentence> under "<heading>": you agree it applies there, not under "<heading>"

Deleted with your approval: <sentence>

Gate: pass | needs confirmation (changes you approved)    Requirements: <n> (<n> sentences left unprotected on purpose)
Coverage: <n>/<n>    Reverse reconstruction: <n>/<n> | skipped: <why>
Behaviour: <n>/<n> clauses unchanged | skipped: <why>

Description suggestions (not applied)
- <suggestion>: <why>
```

Every cut needs a reason in that list, and every optional cut its saving. Fill
"Deleted with your approval" from the gate's "deleted with the user's approval"
lines, one line each, or leave it out. Put description ideas under "Description
suggestions": when the description passes a limit `measure_skills.py` notes, or
says what the skill does but not when to use it. Never apply them; the user may
want the triggers as they are.

Apply when the request approved applying, or after the user approves. Optional
cuts stay unapplied until the user picks them; then make those cuts, add any
approved sentences to approved.txt, and gate again. If the user declines a cut,
put that text back in the candidate and gate again. Right before copying, gate
once more; it must exit 0, or 3 when the user approved every item it lists.
Then run `mkdir -p "<skill-dir>/references"` if the candidate has references,
and copy `"<work>/candidate/SKILL.md"` over the skill's SKILL.md. Copy each new
reference file only if that path does not exist in the skill; never overwrite a
file. If the skill lives in a plugin cache or a directory an installer manages,
say that an update will overwrite the change and that the lasting fix belongs
in its source.
