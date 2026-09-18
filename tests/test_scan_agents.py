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


# --- fixes from the review wave -------------------------------------------

def test_agent_tool_is_a_question_not_a_dead_entry(scan, agent_file):
    # Bug caught: leaving "Agent" in SUBAGENT_DEAD_TOOLS strips delegation from fan-out agents
    # (nested subagents are on by default per the sub-agents docs).
    p = agent_file("a", "description: Use when x\ntools: Read, Agent\n")
    flags = flags_of(scan, p)
    assert "DEAD_TOOL_ENTRY" not in flags
    assert flags["NESTED_AGENT_TOOL"]["severity"] == "low"


def test_legacy_tool_names_get_a_rename_flag(scan, agent_file):
    # Bug caught: dropping LEGACY_TOOL_NAMES lets `Task`/`LS`/`MultiEdit` pass silently.
    p = agent_file("a", "description: Use when x\ntools: Read, Task, LS, MultiEdit\n")
    msg = flags_of(scan, p)["LEGACY_TOOL_NAME"]["message"]
    assert "Task" in msg and "Agent" in msg and "LS" in msg and "MultiEdit" in msg


def test_background_stripped_tools_are_flagged_low(scan, agent_file):
    # Bug caught: omitting BACKGROUND_STRIPPED_TOOLS lets TaskCreate/LSP pass on a background agent.
    p = agent_file("a", "description: Use when x\ntools: Read, TaskCreate, LSP\n")
    f = flags_of(scan, p)["BACKGROUND_STRIPPED"]
    assert f["severity"] == "low" and "TaskCreate" in f["message"] and "LSP" in f["message"]


def test_tools_tokenizer_handles_flow_lists_quotes_and_comments(scan, agent_file):
    # Bug caught: not stripping `[`, `]`, quotes or `# ...` yields tokens like '[Read' and 'Glob  # x'.
    flow = agent_file("a", "description: Use when x\ntools: [Read, Grep, Glob]\n")
    quoted = agent_file("b", 'description: Use when x\ntools: "Read, Grep"\n')
    commented = agent_file("c", "description: Use when x\ntools:\n  - Read\n  - Task  # legacy, dead\n")
    assert scan.parse_agent(flow)["tools"] == ["Read", "Grep", "Glob"]
    assert scan.parse_agent(quoted)["tools"] == ["Read", "Grep"]
    assert scan.parse_agent(commented)["tools"] == ["Read", "Task"]


def test_empty_tools_list_counts_as_no_tools(scan, agent_file):
    # Bug caught: treating `tools: []` as one tool named "[]" hides NO_TOOLS_FIELD.
    p = agent_file("a", "description: Use when x\ntools: []\n")
    a = scan.parse_agent(p)
    assert a["has_tools"] is False and a["tools"] == []


def test_read_only_declaration_needs_a_code_object(scan, agent_file):
    # Bug caught: a bare "do not ... write" regex flags "Do not forget to write logs" as read-only.
    body_ro = "You are a critic. You do not edit code.\n"
    body_obligation = "Do not forget to write comprehensive logs after every change.\n"
    body_tests = "Run the tests without changing them first, then fix the code.\n"
    fm = "description: Use when x\ntools: Read, Edit, Write\n"
    assert "WRITE_ON_READONLY" in flags_of(scan, agent_file("a", fm, body_ro))
    assert "WRITE_ON_READONLY" not in flags_of(scan, agent_file("b", fm, body_obligation))
    assert "WRITE_ON_READONLY" not in flags_of(scan, agent_file("c", fm, body_tests))
    assert "WRITE_ON_READONLY" in flags_of(scan, agent_file("d", fm, "This agent is read-only.\n"))


def test_memory_false_is_not_memory_enabled(scan, agent_file):
    # Bug caught: `bool(a["memory"])` treats the literal "false" as enabled.
    body = "You are a critic. You do not edit code.\n"
    p = agent_file("a", "description: Use when x\ntools: Read, Edit, Write\nmemory: false\n", body)
    assert "WRITE_ON_READONLY" in flags_of(scan, p)


def test_bom_prefixed_agent_is_still_parsed(scan, tmp_path):
    # Bug caught: reading with plain utf-8 leaves the BOM in front of `---` and drops the file.
    p = tmp_path / "a.md"
    p.write_bytes("---\nname: a\ndescription: Use when x\ntools: Read\n---\nbody\n".encode("utf-8-sig"))
    assert scan.parse_agent(p)["name"] == "a"


def test_directory_walk_skips_symlinked_files(scan, tmp_path):
    # Bug caught: rglob follows file symlinks, so a pack can pull outside files into the report.
    outside = tmp_path / "outside.md"
    outside.write_text("---\nname: outside\ndescription: Use when x\n---\nbody\n")
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "real.md").write_text("---\nname: real\ndescription: Use when x\n---\nbody\n")
    (pack / "link.md").symlink_to(outside)
    names = [scan.parse_agent(f)["name"] for f in scan.gather([str(pack)])]
    assert names == ["real"]


def test_weak_trigger_accepts_proactively(scan, agent_file):
    # Bug caught: `proactiv\b` can never match "proactively", so the cue the docs ask for is flagged.
    ok = agent_file("a", "description: Reviews diffs. Use proactively after every commit.\ntools: Read\n")
    weak = agent_file("b", "description: Reviews code.\ntools: Read\n")
    assert "WEAK_TRIGGER" not in flags_of(scan, ok)
    assert flags_of(scan, weak)["WEAK_TRIGGER"]["severity"] == "med"


def test_model_inherit_flag(scan, agent_file):
    # Bug caught: inverting `if not a["model"]` flags pinned agents and misses unpinned ones.
    assert "MODEL_INHERIT" in flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\n"))
    assert "MODEL_INHERIT" not in flags_of(scan, agent_file("b", "description: Use when x\ntools: Read\nmodel: haiku\n"))


def test_long_body_threshold(scan, agent_file):
    # Bug caught: comparing with `>=` or the wrong constant moves the LONG_BODY boundary.
    long_body = "\n".join(f"line {i}" for i in range(scan.DEFAULT_BODY_LINES + 1)) + "\n"
    short_body = "\n".join(f"line {i}" for i in range(scan.DEFAULT_BODY_LINES)) + "\n"
    assert "LONG_BODY" in flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\n", long_body))
    assert "LONG_BODY" not in flags_of(scan, agent_file("b", "description: Use when x\ntools: Read\n", short_body))


def test_memory_boilerplate_severity_depends_on_memory_field(scan, agent_file):
    # Bug caught: swapping the med/low branches for MEMORY_BOILERPLATE.
    body = "## Persistent Agent Memory\nYou have a memory directory.\n"
    with_mem = flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\nmemory: user\n", body))
    without = flags_of(scan, agent_file("b", "description: Use when x\ntools: Read\n", body))
    assert with_mem["MEMORY_BOILERPLATE"]["severity"] == "med"
    assert without["MEMORY_BOILERPLATE"]["severity"] == "low"


def test_name_format_flag(scan, tmp_path):
    # Bug caught: a permissive NAME_FORMAT regex accepts "My_Agent".
    p = tmp_path / "x.md"
    p.write_text("---\nname: My_Agent\ndescription: Use when x\ntools: Read\n---\nbody\n")
    assert "NAME_FORMAT" in flags_of(scan, p)


def test_readable_report_lists_agent_and_flags(scan, agent_file):
    # Bug caught: a broken f-string or sort key in the readable branch crashes main().
    p = agent_file("a", "description: Reviews code.\n")
    out = subprocess.run([sys.executable, str(scan.__file__), str(p)],
                         capture_output=True, text=True, check=True).stdout
    assert "Scanned 1 agent(s)" in out and "NO_TOOLS_FIELD" in out and "WEAK_TRIGGER" in out
