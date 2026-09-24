# What not to cut

Read before the first edit. Each item says what to keep and why; the gate
checks some of them mechanically, the rest are yours to protect.

## Kept word for word (the gate checks)

- Sentences with a rule word: must, never, always, shall, only, unless,
  except, exception, should, required, forbidden, cannot, not, don't, no, none,
  nothing, without, avoid, prefer, instead, until, even if. Words inside inline
  code do not count. Move such a sentence if the user agrees; never reword,
  shorten or merge it. Small wording changes flip meaning: "never" to "avoid"
  turns a ban into advice, and dropping "unless the user asks" turns an
  exception into a ban. Some of these sentences are only motivation ("so that
  nothing is forgotten"); delete one only after the user approves that sentence.
- Sentences a requirement anchors, word for word, like rule sentences.
- Anything to run or type: inline code, lines of a code fence with no
  language or a shell language, URLs, `--flags`, version pins, versions
  ("Python 3.10", "2.1.252+"), dates, paths.
- Numbers with a unit or a bound: "under 20 GiB", "at most 3 retries",
  "40 seconds". The bound is part of the number.
- Code blocks you keep, exactly. A block may be deleted or moved whole;
  it may not be edited.
- **Your own words.** The only new text allowed is the one line that points to
  a moved section. Everything else must be cut from a sentence of the original.
- The frontmatter, entirely. The description decides when the skill
  triggers, and the user may want it exactly as it is; suggest changes in the
  report instead.
- **Every file other than SKILL.md.** New files may only appear under
  `references/`.
- A closing reminder. A rule repeated at the end of a skill is usually
  there on purpose; it stays at the end.

## Kept in meaning (only you can check)

- **Plain instructions and conditions without a rule word.** "Read the
  conventions before editing" and "If the build fails, ask the maintainer" have
  no MUST in them and are still instructions. The dry run lists them; give each
  one an anchor in `requirements.md`, or nothing protects it.
- Step order. When a skill says to freeze before rewriting, or measure
  before proposing, the order is the instruction.
- Precedence: which rule wins when two apply.
- Gotchas and warnings: often one line, usually earned by a real failure.
- The reason attached to a rule. A rule with its reason is followed more
  reliably and applied more sensibly at the edges; cut long background, keep the
  one clause that says why.
- Dated notes ("changed 2026-05-17 after ...") that record where a rule came from.
- **Which example to keep.** Example fences (markdown, json, yaml, text and
  similar) are not literals, so the gate lets you delete one. Cut a duplicate;
  keep the one that shows a format the skill requires.

## Usually safe to cut

- Definitions of things the model already knows (semantic versioning, what a
  pull request is).
- Motivation that carries no rule: why the skill exists, how important the task is.
- An option menu where one default and one escape hatch would do; keep the
  sentence that states the default, since it usually carries "only" or "should".
- A second example that shows nothing the first did not.
- The same instruction said twice in different words. Keep the version with the
  rule word; the gate will insist on it.
