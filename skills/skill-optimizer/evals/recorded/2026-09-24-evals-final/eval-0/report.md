Skill: `<SKILL_DIR>` (name: `lean`)
Work directory: `<work>`

Step 1 (`/skill-doctor` sanity check) skipped: the target is a copy in a temp
directory, not an installed skill, and the request said to skip it.

## lean
Body: 91 -> 91 chars (+0.0%), 2 -> 2 lines
Moved to references: 0 chars
Listing: 66 chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: none

Cuts
- none. The body is two sentences: "Run `make test-fast` before committing."
  and "If it fails, fix the failure before you continue." Both are anchored
  instructions (R1, R2 in requirements.md), and the first also carries a
  literal (the command `make test-fast`, which the gate protects on its own).
  There is no definition, no motivation without a rule, no option menu, no
  duplicate instruction, and no section long enough to move to a reference.
  Nothing is left that doesn't earn its tokens.

Moved
- none

Optional further cuts (not applied)
- none

Deleted with your approval: none

Gate: unchanged    Requirements: 2 (0 sentences left unprotected on purpose)
Coverage: 2/2 (both requirements found in the candidate, which is byte-identical to the original)
Reverse reconstruction: skipped: the gate returned `unchanged` (candidate identical to the original), so there is no rewrite to reconstruct from
Behaviour: skipped: this skill copy ships no `evals/evals.json` and no test prompts were given, and there is no rewrite to compare against

Description suggestions (not applied)
- none: the description is 66 characters, well under the 1,024-char spec
  limit and the 1,536-char listing cap (`measure_skills.py` raised no note),
  and it already states both what the skill does and when to use it.

## Verification

    $ python3 scripts/verify_rewrite.py --frozen <work>/frozen.json \
        --original <skill-dir> --candidate <work>/candidate
    UNCHANGED  body 91 -> 91 chars (+0.0%), 0 chars moved to new references;
    2 requirements, 0 unprotected sentences; frozen 57b84b934a0b

`<skill-dir>/SKILL.md` SHA-256 before and after: both
`c7292dd20f081728bcfacb83b8ccbd47e4568e02ac7b5802715d9cdee164377a` -- the file
was never touched.

## Conclusion

Nothing can be cut from this skill without losing an instruction. Every
sentence in the body is either an anchored instruction or protected by a
literal it carries, and the gate confirms the only possible candidate is
identical to the original (`unchanged`, exit 0). No changes were applied.
