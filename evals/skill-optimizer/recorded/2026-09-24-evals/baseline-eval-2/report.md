# Report: shrink `skill/SKILL.md`

## Task

Shrink `skill/SKILL.md` by deleting the whole `## Rules` section, then apply the edit. No `/skill-doctor` triage was run (per instructions: this is a copy, not an installed skill).

## Change made

Removed the entire `## Rules` section (heading plus all four directives beneath it) from `skill/SKILL.md`, which previously sat between the `## What a release is` section and the `## Steps` section:

```
## Rules

NEVER commit directly to `main`.

Do not push a tag without the maintainer's explicit approval, unless the user
has asked for a dry run.

You MUST run `pytest -q --maxfail=1` before opening a pull request.

Keep the wired memory limit under 20 GiB on a 32 GB machine.
```

The file now flows directly from `## What a release is` to `## Steps`, with a single blank line preserved between sections (normal Markdown spacing, no double blank lines left behind).

## Scope notes

- The separate `## Reminder` section at the end of the file (which repeats "NEVER commit directly to `main`.") was left untouched — the task specified only the `## Rules` section, and `## Reminder` is a distinct heading.
- No other content in `SKILL.md` was changed (frontmatter, `## Why this skill exists`, `## What a release is`, `## Steps`, `## Changelog format`, `## Troubleshooting`, `## Reminder` are all unmodified).
- Only files inside the `eval-2/` sandbox directory were read or written. No git commands were run and no skills were loaded, per the harness notes.

## File touched

- `<SKILL_DIR>/SKILL.md`
