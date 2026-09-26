# Moving a section into references/

Moving is the largest saving available and the easiest way to lose an
instruction: a moved section is read only when the line left behind sends the
agent to it. Move a section only when you can say, in one line, the condition
under which it is needed, and that condition does not hold on most runs.

## Good candidates

- Troubleshooting: what to do when a named step fails.
- A mode most runs do not use: publishing, a second platform, a migration path.
- Long reference material consulted for one step: a table of flags, error
  codes, a field-by-field schema.
- Worked examples beyond the first.

## Keep in the body

- The workflow itself, every step of it, and anything used on every run.
- Rules that apply throughout the skill.
- Anything the agent needs in order to recognise that it should open a
  reference: the reference cannot tell the agent when to read itself.

## When unsure, keep it and list it

If you cannot tell whether a section is needed on every run, keep it in the
body and list the move in the report under "Optional further cuts (not
applied)": what the section contains, the condition you would use, and what the
move would save. The gate asks about every sentence with a rule word that ends
up only in a reference; put each one back and list it the same way, unless the
user's request already approved moving that sentence.

## The line left behind

Write it where the section was, naming the file and the condition:

```text
Read `references/troubleshooting.md` when a release step fails.
```

The condition must be something the agent can observe at that moment ("when
the build fails", "when publishing to PyPI"), not a judgement ("when it seems
useful"). Keep the line to at most 25 words besides the path, with no must,
never, always, shall, required, forbidden, cannot or "do not" in it: the gate
treats a longer or stronger line as new text. One reference per topic; do not move text into an existing reference
file, since the gate freezes every file except SKILL.md.

After moving, reverse reconstruction (step 6) is the check that matters: a
fresh agent reading only the candidate must still find the moved instructions
by following the line you left.
