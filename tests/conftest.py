"""Load the subagent-optimizer scripts as modules without installing anything."""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "subagent-optimizer" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _isolated_codex_home(tmp_path_factory, monkeypatch):
    """Point CODEX_HOME at an empty folder so a real ~/.codex/config.toml never
    leaks declared roles or notes into a test (subprocess runs inherit it)."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path_factory.mktemp("codex-home")))


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


@pytest.fixture
def codex_file(tmp_path):
    """Write a Codex custom agent (.toml) and return its path."""
    def _write(name: str, text: str):
        p = tmp_path / f"{name}.toml"
        p.write_text(text, encoding="utf-8")
        return p
    return _write
