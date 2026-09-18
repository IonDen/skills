"""Each test names the one-line bug in scan_agents.py that would make it fail."""
import json
import subprocess
import sys


def flags_of(scan, path):
    a = scan.parse_agent(path)
    return {f["code"]: f for f in scan.flag_agent(a, scan.DEFAULT_BODY_LINES, scan.DEFAULT_DESC_CHARS)}


def test_tools_parsed_from_inline_list_and_yaml_list(scan, agent_file):
    # Bug caught: dropping the `.lstrip("-")` in the tools tokenizer leaves "- Read" entries.
    inline = agent_file("a", "description: Use when x\ntools: Read, Grep, Glob\n")
    yaml = agent_file("b", "description: Use when x\ntools:\n  - Read\n  - Bash\n")
    assert scan.parse_agent(inline)["tools"] == ["Read", "Grep", "Glob"]
    assert scan.parse_agent(yaml)["tools"] == ["Read", "Bash"]


def test_missing_tools_field_raises_high_flag(scan, agent_file):
    # Bug caught: inverting `if not a["has_tools"]` flags the wrong agents.
    p = agent_file("a", "description: Use when x\n")
    assert flags_of(scan, p)["NO_TOOLS_FIELD"]["severity"] == "high"
    q = agent_file("b", "description: Use when x\ntools: Read\n")
    assert "NO_TOOLS_FIELD" not in flags_of(scan, q)


def test_write_on_readonly_keeps_edit_write_for_memory_agents(scan, agent_file):
    # Bug caught: emptying the `justified` set for memory agents flags Edit/Write they need.
    body = "You are a critic. You do not edit code.\n"
    no_mem = agent_file("a", "description: Use when x\ntools: Read, Edit, Write\n", body)
    assert "WRITE_ON_READONLY" in flags_of(scan, no_mem)
    mem = agent_file("b", "description: Use when x\ntools: Read, Edit, Write\nmemory: user\n", body)
    assert "WRITE_ON_READONLY" not in flags_of(scan, mem)
    mem_nb = agent_file("c", "description: Use when x\ntools: Read, Edit, Write, NotebookEdit\nmemory: user\n", body)
    msg = flags_of(scan, mem_nb)["WRITE_ON_READONLY"]["message"]
    assert "NotebookEdit" in msg and "Edit/Write kept" in msg


def test_dead_tool_entry_covers_documented_blacklist(scan, agent_file):
    # Bug caught: leaving Workflow / TaskOutput / EndConversation out of SUBAGENT_DEAD_TOOLS.
    p = agent_file("a", "description: Use when x\ntools: Read, Workflow, TaskOutput, EndConversation, AskUserQuestion\n")
    msg = flags_of(scan, p)["DEAD_TOOL_ENTRY"]["message"]
    for dead in ("Workflow", "TaskOutput", "EndConversation", "AskUserQuestion"):
        assert dead in msg


def test_skill_md_files_are_not_scanned_as_agents(scan, tmp_path):
    # Bug caught: gather() treating every frontmatter .md with `name` as an agent.
    (tmp_path / "agent.md").write_text("---\nname: agent\ndescription: Use when x\n---\nbody\n")
    skill_dir = tmp_path / "some-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: some-skill\ndescription: Use when y\n---\nbody\n")
    files = scan.gather([str(tmp_path)])
    names = [scan.parse_agent(f)["name"] for f in files if scan.parse_agent(f)]
    assert names == ["agent"]


def test_duplicate_blocks_need_two_agents(scan, agent_file):
    # Bug caught: changing `len(names) >= 2` to `> 2` hides pairwise duplication.
    para = "Persistent memory: " + "x" * 130 + "\n"
    a = scan.parse_agent(agent_file("a", "description: Use when x\n", para + "\nrole a\n"))
    b = scan.parse_agent(agent_file("b", "description: Use when x\n", para + "\nrole b\n"))
    dups = scan.find_duplicate_blocks([a, b])
    assert len(dups) == 1 and dups[0]["agents"] == ["a", "b"]
    assert scan.find_duplicate_blocks([a]) == []


def test_missing_description_is_high(scan, agent_file):
    # Bug caught: guarding the MISSING_DESCRIPTION branch on `if a["description"]` instead of `.strip()`.
    p = agent_file("a", "description:   \ntools: Read\n")
    assert flags_of(scan, p)["MISSING_DESCRIPTION"]["severity"] == "high"


def test_json_output_omits_bodies(scan, agent_file):
    # Bug caught: forgetting `a.pop("body")` leaks whole prompts into the JSON report.
    p = agent_file("a", "description: Use when x\ntools: Read\n", "secret body text\n")
    out = subprocess.run([sys.executable, str(scan.__file__), str(p), "--json"],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    assert data["count"] == 1
    assert "body" not in data["agents"][0]
    assert "secret body text" not in out
