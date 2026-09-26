"""Each test names the one-line bug in scripts/validate_skills.py that would make it fail."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATOR = Path(__file__).resolve().parent.parent / "scripts" / "validate_skills.py"


@pytest.fixture(scope="session")
def validate():
    spec = importlib.util.spec_from_file_location("validate_skills", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_skill(root: Path, dirname: str, name: str | None = None, description: str = "Use when x",
               openai: str | None = "interface:\n  display_name: X\n  short_description: Y\n",
               bom: bool = False):
    d = root / "skills" / dirname
    d.mkdir(parents=True)
    text = f"---\nname: {name or dirname}\ndescription: {description}\n---\nbody\n"
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
    (tmp_path / "skills").mkdir()
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


REPO = VALIDATOR.parent.parent
LISTING = " ".join(["word"] * 45)


def make_plugin(root: Path, names: list[str], *, codex_skills=None, claude_skills=None,
                source="./skills", claude_version="0.7.0", codex_version="0.7.0",
                readme=LISTING, license=True):
    for n in names:
        make_skill(root, n)
    sk = root / "skills"
    (sk / ".claude-plugin").mkdir(parents=True)
    (sk / ".codex-plugin").mkdir(parents=True)
    (sk / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "p", "version": claude_version, "skills": claude_skills if claude_skills is not None else ["./"]}))
    (sk / ".codex-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "p", "version": codex_version,
         "skills": codex_skills if codex_skills is not None else [f"./{n}" for n in names]}))
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"name": "m", "plugins": [{"name": "p", "source": source}]}))
    if readme is not None:
        (sk / "README.md").write_text(readme)
    if license:
        (sk / "LICENSE").write_text("MIT")
    return root


def test_check_plugin_accepts_a_correct_layout(validate, tmp_path):
    # Bug caught: check_plugin reporting a problem on a valid tree.
    assert validate.check_plugin(make_plugin(tmp_path, ["a-skill", "b-skill"])) == []


def test_check_plugin_rejects_evals_inside_a_skill_folder(validate, tmp_path):
    # Bug caught: the allowlist check skipped, so evals ship to every user again.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / "skills" / "a-skill" / "evals").mkdir()
    problems = validate.check_plugin(root)
    assert any("evals" in p and "evals/a-skill/" in p for p in problems)


def test_check_plugin_ignores_dotfiles_in_a_skill_folder(validate, tmp_path):
    # Bug caught: an untracked Finder .DS_Store failing local validation.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / "skills" / "a-skill" / ".DS_Store").write_text("")
    assert validate.check_plugin(root) == []


def test_check_plugin_rejects_a_single_dot_path_for_codex(validate, tmp_path):
    # Bug caught: accepting "./", which Codex 0.147 installs but loads no skills from.
    root = make_plugin(tmp_path, ["a-skill"], codex_skills="./")
    assert any("Codex" in p and "./<name>" in p for p in validate.check_plugin(root))


def test_check_plugin_rejects_a_codex_list_missing_a_skill(validate, tmp_path):
    # Bug caught: comparing only list types, not contents, so a new skill never loads in Codex.
    root = make_plugin(tmp_path, ["a-skill", "b-skill"], codex_skills=["./a-skill"])
    assert any("b-skill" in p for p in validate.check_plugin(root))


def test_check_plugin_rejects_claude_skills_other_than_plugin_root(validate, tmp_path):
    # Bug caught: pointing Claude at "./skills/", a folder that does not exist inside the plugin root.
    root = make_plugin(tmp_path, ["a-skill"], claude_skills=["./skills/"])
    assert any(".claude-plugin" in p and "skills" in p for p in validate.check_plugin(root))


def test_check_plugin_rejects_version_drift(validate, tmp_path):
    # Bug caught: bumping one manifest and not the other.
    root = make_plugin(tmp_path, ["a-skill"], codex_version="0.6.0")
    assert any("version" in p for p in validate.check_plugin(root))


def test_check_plugin_rejects_marketplace_source_at_repo_root(validate, tmp_path):
    # Bug caught: marketplace still pointing at "./", which installs the whole repository.
    root = make_plugin(tmp_path, ["a-skill"], source="./")
    assert any("marketplace" in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("stale", [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"])
def test_check_plugin_rejects_a_manifest_at_repo_root(validate, tmp_path, stale):
    # Bug caught: a leftover root manifest making the repo root a plugin again.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / stale).parent.mkdir(exist_ok=True)
    (root / stale).write_text("{}")
    assert any(stale.split("/")[0] in p for p in validate.check_plugin(root))


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
    (root / "skills" / ".codex-plugin" / "plugin.json").write_text("{not json")
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


def test_validate_all_fails_on_a_skill_problem_alone(validate, tmp_path):
    # Bug caught: validate_all returning only the packaging result, so a broken SKILL.md passes CI.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / "skills" / "a-skill" / "SKILL.md").write_text("---\nname: other-name\ndescription: Use when x\n---\nbody\n")
    assert validate.check_plugin(root) == []
    assert validate.validate_all(root) == 1


@pytest.mark.parametrize("rel", [".claude-plugin/marketplace.json", "skills/.claude-plugin/plugin.json", "skills/.codex-plugin/plugin.json"])
def test_check_plugin_reports_a_missing_manifest(validate, tmp_path, rel):
    # Bug caught: the missing-file branch recording nothing, so a tree without that manifest validates clean.
    root = make_plugin(tmp_path, ["a-skill"])
    (root / rel).unlink()
    assert f"{rel}: missing" in validate.check_plugin(root)


@pytest.mark.parametrize("rel", [".claude-plugin/marketplace.json", "skills/.claude-plugin/plugin.json", "skills/.codex-plugin/plugin.json"])
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
    # Bug caught: only folders holding a SKILL.md get checked, so anything else at the top of skills/ ships.
    root = make_plugin(tmp_path, ["a-skill"])
    target = root / "skills" / entry
    target.mkdir() if is_dir else target.write_text("x")
    assert any(p.startswith("skills/: ships") and entry in p for p in validate.check_plugin(root))


@pytest.mark.parametrize("version", [None, ""])
def test_check_plugin_requires_a_version_in_both_manifests(validate, tmp_path, version):
    # Bug caught: comparing the two versions only, so two manifests with no version pass as equal.
    root = make_plugin(tmp_path, ["a-skill"], claude_version=version, codex_version=version)
    problems = validate.check_plugin(root)
    assert any(p.startswith("skills/.claude-plugin/plugin.json:") and "version" in p for p in problems)
    assert any(p.startswith("skills/.codex-plugin/plugin.json:") and "version" in p for p in problems)
