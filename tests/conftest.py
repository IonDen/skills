"""Load the skills' scripts as modules without installing anything."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "subagent-optimizer" / "scripts"
OPTIMIZER_SCRIPTS = ROOT / "skills" / "skill-optimizer" / "scripts"


def _load(name: str, scripts: Path = SCRIPTS):
    spec = importlib.util.spec_from_file_location(name, scripts / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def scan():
    return _load("scan_agents")


@pytest.fixture(scope="session")
def bump():
    return _load("bump_version")


@pytest.fixture
def agent_file(tmp_path):
    """Write an agent file and return its path."""
    def _write(name: str, frontmatter: str, body: str = "Do the job.\n"):
        p = tmp_path / f"{name}.md"
        p.write_text(f"---\nname: {name}\n{frontmatter}---\n{body}", encoding="utf-8")
        return p
    return _write


@pytest.fixture(scope="session")
def skillmd():
    return _load("skillmd", OPTIMIZER_SCRIPTS)


@pytest.fixture(scope="session")
def measure():
    return _load("measure_skills", OPTIMIZER_SCRIPTS)


@pytest.fixture(scope="session")
def freezer():
    return _load("extract_requirements", OPTIMIZER_SCRIPTS)


@pytest.fixture(scope="session")
def gate():
    return _load("verify_rewrite", OPTIMIZER_SCRIPTS)


@pytest.fixture
def make_skill(tmp_path):
    """Write a skill directory: SKILL.md with the given body, plus extra files."""
    def _make(body: str, where: str = "original", frontmatter: str = None, files: dict = None):
        d = tmp_path / where
        d.mkdir(parents=True, exist_ok=True)
        fm = frontmatter if frontmatter is not None else "---\nname: demo\ndescription: Use when testing.\n---\n"
        (d / "SKILL.md").write_text(fm + body, encoding="utf-8")
        for rel, text in (files or {}).items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        return d
    return _make
