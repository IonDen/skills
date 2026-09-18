"""Each test names the one-line bug in scripts/validate_skills.py that would make it fail."""
import importlib.util
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
