"""Each test names the one-line bug in scripts/validate_skills.py that would make it fail."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATOR = Path(__file__).resolve().parent.parent / "scripts" / "validate_skills.py"
PLUGIN = "plugins/ionden-skills"


@pytest.fixture(scope="session")
def validate():
    spec = importlib.util.spec_from_file_location("validate_skills", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_skill(root: Path, dirname: str, name: str | None = None, description: str = "Use when x",
               openai: str | None = "interface:\n  display_name: X\n  short_description: Y\n",
               bom: bool = False, body: str = "body"):
    d = root / PLUGIN / "skills" / dirname
    d.mkdir(parents=True)
    text = f"---\nname: {name or dirname}\ndescription: {description}\n---\n{body}\n"
    (d / "SKILL.md").write_bytes(text.encode("utf-8-sig" if bom else "utf-8"))
    if openai is not None:
        (d / "agents").mkdir()
        (d / "agents" / "openai.yaml").write_text(openai)
    return d


def test_valid_skill_passes(validate, tmp_path):
    # Bug caught: main() returning 1 unconditionally.
    make_skill(tmp_path, "good-skill")
    assert validate.main(tmp_path) == 0


def test_name_must_match_directory(validate, tmp_path):
    # Bug caught: comparing name to the wrong thing (or not at all).
    make_skill(tmp_path, "good-skill", name="other-name")
    assert validate.main(tmp_path) == 1


def test_missing_description_fails(validate, tmp_path):
    # Bug caught: checking `"description" in fm` instead of a non-empty value.
    make_skill(tmp_path, "good-skill", description=" ")
    assert validate.main(tmp_path) == 1


def test_openai_yaml_needs_both_interface_fields(validate, tmp_path):
    # Bug caught: only checking display_name.
    make_skill(tmp_path, "good-skill", openai="interface:\n  display_name: X\n")
    assert validate.main(tmp_path) == 1


def test_bom_is_tolerated(validate, tmp_path):
    # Bug caught: reading with plain utf-8 so `^---` never matches a BOM-prefixed file.
    make_skill(tmp_path, "good-skill", bom=True)
    assert validate.main(tmp_path) == 0


def test_spec_length_limits(validate, tmp_path):
    # Bug caught: dropping the 64-char name / 1024-char description checks from the spec.
    make_skill(tmp_path, "a" * 65)
    assert validate.main(tmp_path) == 1
    long_desc_root = tmp_path / "second"
    make_skill(long_desc_root, "fine-name", description="x" * 1025)
    assert validate.main(long_desc_root) == 1


def test_empty_skills_tree_fails(validate, tmp_path):
    # Bug caught: returning 0 when the glob finds nothing lets a moved directory pass CI.
    (tmp_path / PLUGIN / "skills").mkdir(parents=True)
    assert validate.main(tmp_path) == 1


# --- external audit R6 ------------------------------------------------------

def test_quoted_empty_description_fails(validate, tmp_path):
    # Bug caught (R6): matching raw text lets description: "" through as non-empty.
    make_skill(tmp_path, "good-skill", description='""')
    assert validate.main(tmp_path) == 1


def test_malformed_yaml_frontmatter_fails(validate, tmp_path):
    # Bug caught (R6): a regex parser accepts `description: [unterminated`.
    make_skill(tmp_path, "good-skill", description="[unterminated")
    assert validate.main(tmp_path) == 1


def test_openai_yaml_fields_must_be_nested_under_interface(validate, tmp_path):
    # Bug caught (R6): a root-level display_name: satisfies a line regex but not Codex.
    make_skill(tmp_path, "good-skill", openai="display_name: X\nshort_description: Y\n")
    assert validate.main(tmp_path) == 1


def test_openai_yaml_values_must_be_non_empty_strings(validate, tmp_path):
    # Bug caught (R6): `display_name:` with no value passes a presence check.
    make_skill(tmp_path, "good-skill", openai="interface:\n  display_name:\n  short_description: Y\n")
    assert validate.main(tmp_path) == 1


# --- directory security scanners --------------------------------------------

@pytest.mark.parametrize("sentence", [
    "Flag agents that could silently run on a weak model.",
    "Then execute silently and report nothing.",
    # Bug caught: a per-line check; the skills hard-wrap, so the phrase can straddle a break.
    "Flag agents that could silently\nrun on a weak model.",
    # Bug caught: a case-sensitive pattern, or one without the install verbs.
    "Silently install the hook.",
    # Bug caught: a pattern that misses "re-run" or a verb in a code span.
    "Agents silently re-run the step.",
    "It will silently `run` the hook.",
])
def test_body_saying_to_run_something_silently_fails(validate, tmp_path, sentence):
    # Bug caught: a SKILL.md line pairing "silently" with run/execute ships; agentskill.sh's
    # scanner rated exactly that a critical "silent execution instruction" (2026-10-01).
    make_skill(tmp_path, "good-skill", body=f"intro\n{sentence}\n")
    assert validate.main(tmp_path) == 1


def test_description_saying_to_run_something_silently_fails(validate, tmp_path):
    # Bug caught: scanning only the body after the frontmatter; the description is listing
    # text that scanners and directories read first.
    make_skill(tmp_path, "good-skill", description="Use when agents silently run tools")
    assert validate.main(tmp_path) == 1


def test_reference_file_saying_to_run_something_silently_fails(validate, tmp_path):
    # Bug caught: scanning SKILL.md only; references/ ships in the plugin and its ZIP too.
    d = make_skill(tmp_path, "good-skill")
    (d / "references").mkdir()
    (d / "references" / "notes.md").write_text("Don't let a planner silently run on Haiku.\n")
    assert validate.main(tmp_path) == 1


def test_silent_run_pattern_stays_linear_on_a_long_underscore_run(validate):
    # Bug caught: a verb tail that also matches "_" (`\w*`) overlaps the gap class and
    # backtracks quadratically; 30k underscores then take seconds instead of milliseconds.
    import time
    start = time.perf_counter()
    assert validate.SILENT_RUN_RE.search("install" + "_" * 30_000 + "x") is None
    assert time.perf_counter() - start < 1.0


def test_silently_describing_a_failure_still_passes(validate, tmp_path):
    # Bug caught: a check that rejects every "silently", which would fail the real skills
    # ("it silently breaks memory upkeep" warns about a failure, it instructs nothing).
    make_skill(tmp_path, "good-skill", body="Stripping it silently breaks memory upkeep.\n")
    assert validate.main(tmp_path) == 0


# --- absolute links that raw-text readers break ------------------------------

BARE = "bare absolute URL"


@pytest.mark.parametrize("body, line", [
    # Bug caught: a shipped `[x](https://…).` link; tools that pull URLs out of the raw Markdown
    # keep the `).` and send visitors to a 404 (seen in the repo traffic, 2026-10-07).
    ("See [the evals](https://example.com/evals/).", 5),
    # Bug caught: a case-sensitive pattern lets an uppercase scheme through.
    ("See [the evals](HTTPS://example.com/evals/).", 5),
    # Bug caught: a per-line check; a hard-wrapped link can break right after `(`.
    ("See [the evals](\nhttps://example.com/evals/).", 5),
])
def test_bare_absolute_link_in_a_skill_body_fails(validate, tmp_path, body, line):
    d = make_skill(tmp_path, "good-skill", body=body)
    assert any(BARE in p and f"SKILL.md line {line} " in p for p in validate.check_skill(d / "SKILL.md"))


def test_bare_absolute_link_in_a_reference_file_fails(validate, tmp_path):
    # Bug caught: checking SKILL.md only, or only links followed by punctuation; the closing
    # `)` alone already ends up in the extracted URL.
    d = make_skill(tmp_path, "good-skill")
    (d / "references").mkdir()
    (d / "references" / "notes.md").write_text("Results: [runs](https://example.com/runs/) here\n")
    assert any(BARE in p and "references/notes.md line 1 " in p
               for p in validate.check_skill(d / "SKILL.md"))


def test_angle_bracket_and_relative_links_pass(validate, tmp_path):
    # Bug caught: a check that flags every link instead of only bare absolute destinations.
    make_skill(tmp_path, "good-skill",
               body="See [the evals](<https://example.com/evals/>). Also [notes](references/a.md).\n")
    assert validate.main(tmp_path) == 0


@pytest.mark.parametrize("line", [
    "Source: [repo](https://example.com/repo).",
    "[![badge](https://img.example.com/b.svg)](<https://example.com/>)",
])
def test_bare_absolute_link_in_the_plugin_readme_fails(validate, tmp_path, line):
    # Bug caught: the plugin README (the directory listing text) left out of the check,
    # or a badge image URL not counted as a link destination.
    root = make_plugin(tmp_path, ["a-skill"], readme=LISTING + "\n\n" + line + "\n")
    assert any(p.startswith(f"{PLUGIN}/README.md line 3 ") and BARE in p
               for p in validate.check_plugin(root))


def test_bare_absolute_link_in_the_root_readme_fails(validate, tmp_path):
    # Bug caught: the repository landing page, the README browsing agents read first, left out.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / "README.md").write_text("Listed at [skills.sh](https://skills.sh/x/y):\n")
    assert any(p.startswith("README.md line 1 ") and BARE in p for p in validate.check_plugin(root))
    (root / "README.md").write_text("Listed at [skills.sh](<https://skills.sh/x/y>):\n")
    assert validate.check_plugin(root) == []


def test_bare_absolute_link_in_a_repo_doc_fails(validate, tmp_path):
    # Bug caught: docs/ left out; the root README links its pages, so readers follow them too.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / "docs").mkdir()
    (root / "docs" / "publishing.md").write_text("Intro\n\nSee [the portal](https://example.com/p).\n")
    assert any(p.startswith("docs/publishing.md line 3 ") and BARE in p
               for p in validate.check_plugin(root))


REPO = VALIDATOR.parent.parent
LISTING = " ".join(["word"] * 45)
OMIT = object()
ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128"/></svg>'


def make_plugin(root: Path, names: list[str], *, codex_skills="./skills/", claude_skills=OMIT,
                source=f"./{PLUGIN}", claude_version="0.8.0", codex_version="0.8.0",
                readme=LISTING, license=True, icon=ICON):
    """A valid plugin at PLUGIN. claude_skills=OMIT leaves the Claude `skills` key out (the valid
    form; None writes an explicit null); codex_skills=None leaves the Codex `skills` key out."""
    for n in names:
        make_skill(root, n)
    sk = root / PLUGIN
    (sk / ".claude-plugin").mkdir(parents=True)
    (sk / ".codex-plugin").mkdir(parents=True)
    claude = {"name": "p", "version": claude_version}
    if claude_skills is not OMIT:
        claude["skills"] = claude_skills
    codex = {"name": "p", "version": codex_version}
    if codex_skills is not None:
        codex["skills"] = codex_skills
    (sk / ".claude-plugin" / "plugin.json").write_text(json.dumps(claude))
    (sk / ".codex-plugin" / "plugin.json").write_text(json.dumps(codex))
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"name": "m", "plugins": [{"name": "p", "source": source}]}))
    if readme is not None:
        (sk / "README.md").write_text(readme)
    if license:
        (sk / "LICENSE").write_text("MIT")
    if icon is not None:
        (sk / ".claude-plugin" / "icon.svg").write_text(icon)
    return root


def test_check_plugin_accepts_a_correct_layout(validate, tmp_path):
    # Bug caught: check_plugin reporting a problem on a valid tree.
    assert validate.check_plugin(make_plugin(tmp_path, ["a-skill", "b-skill"])) == []


def test_check_plugin_rejects_evals_inside_a_skill_folder(validate, tmp_path):
    # Bug caught: the allowlist check skipped, so evals ship to every user again.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / "skills" / "a-skill" / "evals").mkdir()
    problems = validate.check_plugin(root)
    assert any("evals" in p and "evals/a-skill/" in p for p in problems)


def test_check_plugin_ignores_dotfiles_in_a_skill_folder(validate, tmp_path):
    # Bug caught: an untracked Finder .DS_Store failing local validation.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / "skills" / "a-skill" / ".DS_Store").write_text("")
    assert validate.check_plugin(root) == []


@pytest.mark.parametrize("codex_skills", ["./", ["./skills/"], ["./a-skill"], "./skills", None])
def test_check_plugin_wants_codex_skills_to_be_the_skills_folder(validate, tmp_path, codex_skills):
    # Bug caught: accepting another Codex skills form; a bare "./" installs but loads no skills (Codex 0.147).
    root = make_plugin(tmp_path, ["a-skill"], codex_skills=codex_skills)
    assert any(p.startswith(f'{PLUGIN}/.codex-plugin/plugin.json: skills must be "./skills/"')
               for p in validate.check_plugin(root))


@pytest.mark.parametrize("claude_skills", [["./"], ["./skills/"], "./skills/", ["./a-skill"], [], None])
def test_check_plugin_rejects_a_custom_claude_skills_path(validate, tmp_path, claude_skills):
    # Bug caught: allowing a custom skills path, which only Claude Code honours; the directory then lists no skills.
    root = make_plugin(tmp_path, ["a-skill"], claude_skills=claude_skills)
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/plugin.json: remove the skills key")
               for p in validate.check_plugin(root))


def test_check_plugin_rejects_version_drift(validate, tmp_path):
    # Bug caught: bumping one manifest and not the other.
    root = make_plugin(tmp_path, ["a-skill"], codex_version="0.6.0")
    assert any("version" in p for p in validate.check_plugin(root))


def test_check_plugin_rejects_marketplace_source_at_repo_root(validate, tmp_path):
    # Bug caught: marketplace still pointing at "./", which installs the whole repository.
    root = make_plugin(tmp_path, ["a-skill"], source="./")
    assert any("marketplace" in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("stale", [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "skills/README.md"])
def test_check_plugin_rejects_old_layout_leftovers(validate, tmp_path, stale):
    # Bug caught: a leftover root manifest or root skills/ folder from an earlier layout staying unnoticed.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / stale).parent.mkdir(parents=True, exist_ok=True)
    (root / stale).write_text("{}")
    assert any(p.startswith(stale.split("/")[0]) and "left over" in p for p in validate.check_plugin(root))


def test_check_plugin_counts_listing_words_outside_code_blocks(validate, tmp_path):
    # Bug caught: counting words inside ``` fences, which the Anthropic directory does not.
    readme = "Short intro here.\n\n```\n" + " ".join(["code"] * 60) + "\n```\n"
    root = make_plugin(tmp_path, ["a-skill"], readme=readme)
    assert any("README.md" in p and "40" in p for p in validate.check_plugin(root))


def test_check_plugin_requires_listing_readme_and_license(validate, tmp_path):
    # Bug caught: missing-file checks dropped; the directory blocks both.
    root = make_plugin(tmp_path, ["a-skill"], readme=None, license=False)
    problems = validate.check_plugin(root)
    assert any("README.md" in p for p in problems) and any("LICENSE" in p for p in problems)


def test_check_plugin_reports_unparseable_manifest(validate, tmp_path):
    # Bug caught: a JSON error crashing the validator instead of a FAIL line.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / ".codex-plugin" / "plugin.json").write_text("{not json")
    assert any("not valid JSON" in p for p in validate.check_plugin(root))


def test_validate_all_fails_on_a_packaging_problem_alone(validate, tmp_path):
    # Bug caught: __main__ still calling main() only, so CI never runs the packaging checks.
    root = make_plugin(tmp_path, ["a-skill"], source="./")
    assert validate.main(root) == 0
    assert validate.validate_all(root) == 1


def test_the_real_repository_passes_every_check(validate):
    # Bug caught: the repo drifting from its own packaging rules (e.g. a manifest moved back to the root).
    assert validate.validate_all(REPO) == 0


def test_script_entry_point_runs_the_packaging_checks(tmp_path):
    # Bug caught: __main__ calling main() instead of validate_all(), so CI skips every packaging check.
    root = make_plugin(tmp_path, ["a-skill"], source="./")
    r = subprocess.run([sys.executable, str(VALIDATOR), str(root)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "marketplace" in r.stdout


def test_validate_all_fails_on_a_skill_problem_alone(validate, tmp_path, capsys):
    # Bug caught: validate_all returning only the packaging result, so a broken SKILL.md passes CI.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / "skills" / "a-skill" / "SKILL.md").write_text("---\nname: other-name\ndescription: Use when x\n---\nbody\n")
    assert validate.check_plugin(root) == []
    assert validate.validate_all(root) == 1
    assert "a-skill: frontmatter name 'other-name' != directory name" in capsys.readouterr().out


@pytest.mark.parametrize("rel", [".claude-plugin/marketplace.json", f"{PLUGIN}/.claude-plugin/plugin.json", f"{PLUGIN}/.codex-plugin/plugin.json"])
def test_check_plugin_reports_a_missing_manifest(validate, tmp_path, rel):
    # Bug caught: the missing-file branch recording nothing, so a tree without that manifest validates clean.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / rel).unlink()
    assert f"{rel}: missing" in validate.check_plugin(root)


@pytest.mark.parametrize("rel", [".claude-plugin/marketplace.json", f"{PLUGIN}/.claude-plugin/plugin.json", f"{PLUGIN}/.codex-plugin/plugin.json"])
def test_check_plugin_rejects_a_manifest_that_is_not_an_object(validate, tmp_path, rel):
    # Bug caught: the dict guards skipping every check on a list-valued manifest, so `[]` passes.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / rel).write_text("[]")
    assert any(p.startswith(f"{rel}:") and "object" in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("words, accepted", [(39, False), (40, True), (41, True)])
def test_check_plugin_listing_word_boundary(validate, tmp_path, words, accepted):
    # Bug caught: `<` flipped to `<=`, or the threshold moved off the directory's 40-word minimum.
    root = make_plugin(tmp_path, ["a-skill"], readme=" ".join(["word"] * words))
    assert (validate.check_plugin(root) == []) is accepted


@pytest.mark.parametrize("entry, is_dir", [("evals", True), ("notes.md", False)])
def test_check_plugin_rejects_stray_entries_at_the_plugin_root(validate, tmp_path, entry, is_dir):
    # Bug caught: only folders holding a SKILL.md get checked, so anything else in the plugin folder ships.
    root = make_plugin(tmp_path, ["a-skill"])
    target = root / PLUGIN / entry
    target.mkdir() if is_dir else target.write_text("x")
    assert any(p.startswith(f"{PLUGIN}/: ships") and entry in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("entry, is_dir", [("notes", True), ("notes.md", False)])
def test_check_plugin_rejects_stray_entries_in_the_skills_folder(validate, tmp_path, entry, is_dir):
    # Bug caught: not checking skills/ itself, so a folder without a SKILL.md or a loose file ships to users.
    root = make_plugin(tmp_path, ["a-skill"])
    target = root / PLUGIN / "skills" / entry
    target.mkdir() if is_dir else target.write_text("x")
    assert any(p.startswith(f"{PLUGIN}/skills/: ships") and entry in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("version", [None, ""])
def test_check_plugin_requires_a_version_in_both_manifests(validate, tmp_path, version):
    # Bug caught: comparing the two versions only, so two manifests with no version pass as equal.
    root = make_plugin(tmp_path, ["a-skill"], claude_version=version, codex_version=version)
    problems = validate.check_plugin(root)
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/plugin.json:") and "version" in p for p in problems)
    assert any(p.startswith(f"{PLUGIN}/.codex-plugin/plugin.json:") and "version" in p for p in problems)


def test_check_plugin_requires_the_listing_icon(validate, tmp_path):
    # Bug caught: no icon check, so a deleted icon falls back to the GitHub avatar in the directory unnoticed.
    root = make_plugin(tmp_path, ["a-skill"], icon=None)
    assert f"{PLUGIN}/.claude-plugin/icon.svg: missing" in validate.check_plugin(root)


@pytest.mark.parametrize("view_box, accepted", [
    ("0 0 128 128", True),
    ("0 0 256 256", True),
    ("0 0 127 127", False),
    ("0 0 128 96", False),
    ("0 0 256 128", False),
    ("0 0 128 256", False),
])
def test_check_plugin_wants_a_square_icon_of_at_least_128(validate, tmp_path, view_box, accepted):
    # Bug caught: accepting a non-square or sub-128 icon, which the directory asks to be square and 128 px or more.
    # 256x128 and 128x256 clear the size bar on both sides, so only the squareness check can reject them.
    icon = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}"></svg>'
    root = make_plugin(tmp_path, ["a-skill"], icon=icon)
    problems = validate.check_plugin(root)
    if accepted:
        assert problems == []
    else:
        w, h = view_box.split()[2:]
        assert f"{PLUGIN}/.claude-plugin/icon.svg: viewBox is {w}x{h}; the listing icon must be square and at least 128 px" in problems


def test_check_plugin_rejects_an_icon_without_a_view_box(validate, tmp_path):
    # Bug caught: treating a missing viewBox as fine, so the size can't be checked at all.
    root = make_plugin(tmp_path, ["a-skill"], icon='<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/icon.svg:") for p in validate.check_plugin(root))


@pytest.mark.parametrize("attr", ["viewBox='0 0 128 128'", 'viewBox = "0 0 128 128"', 'viewBox="0,0,128,128"',
                                  'viewBox="-64 -64 128 128"'])
def test_check_plugin_reads_other_valid_viewbox_spellings(validate, tmp_path, attr):
    # Bug caught: a pattern that only knows double quotes and spaces, failing a valid icon as "no viewBox".
    root = make_plugin(tmp_path, ["a-skill"], icon=f'<svg xmlns="http://www.w3.org/2000/svg" {attr}></svg>')
    assert validate.check_plugin(root) == []


def test_check_plugin_reports_a_malformed_viewbox_instead_of_crashing(validate, tmp_path):
    # Bug caught: float() on a matched but malformed number raising ValueError out of the validator.
    root = make_plugin(tmp_path, ["a-skill"], icon='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 . ."></svg>')
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/icon.svg:") for p in validate.check_plugin(root))


@pytest.mark.parametrize("icon", [
    '<!-- viewBox="0 0 512 512" --><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><symbol viewBox="0 0 128 128"/></svg>',
])
def test_check_plugin_reads_the_root_svg_viewbox_only(validate, tmp_path, icon):
    # Bug caught: taking the first viewBox anywhere in the file, so a comment or a nested element vouches for a small icon.
    root = make_plugin(tmp_path, ["a-skill"], icon=icon)
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/icon.svg:") for p in validate.check_plugin(root))


@pytest.mark.parametrize("view_box", ["0 0 128", "0 0 128 128 9"])
def test_check_plugin_wants_exactly_four_viewbox_numbers(validate, tmp_path, view_box):
    # Bug caught: accepting a viewBox with a missing or extra number instead of reporting it unreadable.
    root = make_plugin(tmp_path, ["a-skill"], icon=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}"></svg>')
    assert any(p.startswith(f"{PLUGIN}/.claude-plugin/icon.svg: no readable viewBox") for p in validate.check_plugin(root))


@pytest.mark.parametrize("entry, is_dir", [(".evals", True), (".mcp.json", False)])
def test_check_plugin_rejects_hidden_entries_at_the_plugin_root(validate, tmp_path, entry, is_dir):
    # Bug caught: skipping every dot-entry, so a hidden folder or a live .mcp.json ships to users unnoticed.
    root = make_plugin(tmp_path, ["a-skill"])
    target = root / PLUGIN / entry
    target.mkdir() if is_dir else target.write_text("{}")
    assert any(p.startswith(f"{PLUGIN}/: ships") and entry in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("folder, entry", [(".claude-plugin", "notes.md"), (".codex-plugin", "icon.svg")])
def test_check_plugin_rejects_extra_files_in_the_manifest_folders(validate, tmp_path, folder, entry):
    # Bug caught: never looking inside the manifest folders, so anything dropped there ships.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / folder / entry).write_text("x")
    assert any(p.startswith(f"{PLUGIN}/{folder}/: ships") and entry in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("where", ["", "skills", "skills/a-skill", ".claude-plugin", ".codex-plugin"])
def test_check_plugin_ignores_finder_junk_everywhere(validate, tmp_path, where):
    # Bug caught: counting a local .DS_Store as a stray, so validation fails on a Mac for nothing.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / where / ".DS_Store").write_text("")
    assert validate.check_plugin(root) == []


def test_check_plugin_rejects_a_hidden_file_in_a_skill_folder(validate, tmp_path):
    # Bug caught: skipping dot-entries inside a skill folder, so a hidden eval file ships with the skill.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / PLUGIN / "skills" / "a-skill" / ".evals.json").write_text("{}")
    assert any(p.startswith("a-skill: ships") and ".evals.json" in p for p in validate.check_plugin(root))


def test_check_plugin_reports_a_manifest_it_cannot_read(validate, tmp_path):
    # Bug caught: catching only a missing file, so a manifest path that is a folder crashes with a traceback.
    root = make_plugin(tmp_path, ["a-skill"])
    manifest = root / PLUGIN / ".codex-plugin" / "plugin.json"
    manifest.unlink()
    manifest.mkdir()
    assert any(p.startswith(f"{PLUGIN}/.codex-plugin/plugin.json: cannot be read") for p in validate.check_plugin(root))
