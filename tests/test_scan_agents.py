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


def test_read_only_declaration_recall_on_common_phrasings(scan, agent_file):
    # Bug caught: a tail that demands a bare noun right after the verb misses "do not write any code".
    fm = "description: Use when x\ntools: Read, Edit, Write\n"
    phrasings = [
        "Do not write any code.", "It does not modify any files.", "Never change existing files.",
        "Don't edit user files.", "Do not write to disk.", "It does not write to the repository.",
        "Never implement fixes yourself.", "You never make changes to the codebase.",
    ]
    for i, body in enumerate(phrasings):
        assert "WRITE_ON_READONLY" in flags_of(scan, agent_file(f"r{i}", fm, body + "\n")), body
    for i, body in enumerate(["Run the tests without changing them first.",
                              "Do not forget to write comprehensive logs.",
                              "Never implement a recommendation without reading the plan."]):
        assert "WRITE_ON_READONLY" not in flags_of(scan, agent_file(f"n{i}", fm, body + "\n")), body


def test_hash_inside_a_tool_specifier_is_not_a_comment(scan, agent_file):
    # Bug caught: stripping from any `#` truncates `Bash(echo "#x")`.
    p = agent_file("a", 'description: Use when x\ntools: Bash(echo "#x"), Read  # trailing comment\n')
    assert scan.parse_agent(p)["tools"] == ['Bash(echo "#x")', "Read"]


def test_task_output_is_dead_not_legacy(scan):
    # Bug caught: listing TaskOutput in both sets makes the catalog and the scanner disagree.
    assert "TaskOutput" in scan.SUBAGENT_DEAD_TOOLS and "TaskOutput" not in scan.LEGACY_TOOL_NAMES


# --- external audit R1/R2/R3/R5 -------------------------------------------

def test_exit_plan_mode_is_allowed_under_plan_permission_mode(scan, agent_file):
    # Bug caught (R1): ignoring permissionMode flags ExitPlanMode on a planner that needs it.
    planner = agent_file("a", "description: Use when x\ntools: Read, ExitPlanMode\npermissionMode: plan\n")
    other = agent_file("b", "description: Use when x\ntools: Read, ExitPlanMode\n")
    assert "DEAD_TOOL_ENTRY" not in flags_of(scan, planner)
    assert "ExitPlanMode" in flags_of(scan, other)["DEAD_TOOL_ENTRY"]["message"]


def test_parameterised_tools_keep_their_arguments(scan, agent_file):
    # Bug caught (R5): splitting on every comma turns Agent(worker, researcher) into two tokens.
    a = agent_file("a", "description: Use when x\ntools: Agent(worker, researcher), Read\n")
    b = agent_file("b", 'description: Use when x\ntools: ["Agent(worker, researcher)", "Read"]\n')
    c = agent_file("c", "description: Use when x\ntools:\n  - Bash(git diff:*, git log:*)\n  - Read\n")
    assert scan.parse_agent(a)["tools"] == ["Agent(worker, researcher)", "Read"]
    assert scan.parse_agent(b)["tools"] == ["Agent(worker, researcher)", "Read"]
    assert scan.parse_agent(c)["tools"] == ["Bash(git diff:*, git log:*)", "Read"]
    assert "NESTED_AGENT_TOOL" in flags_of(scan, a)


def test_quoted_scalars_are_decoded_before_validation(scan, agent_file):
    # Bug caught (R5): validating the raw YAML text flags name: "reviewer" and misses description: "".
    quoted = agent_file("a", 'description: "Use when x"\ntools: Read\n')
    (quoted.parent / "q.md").write_text('---\nname: "reviewer"\ndescription: ""\ntools: Read\n---\nbody\n')
    q = scan.parse_agent(quoted.parent / "q.md")
    assert q["name"] == "reviewer" and q["description"] == ""
    fl = {f["code"] for f in scan.flag_agent(q, scan.DEFAULT_BODY_LINES, scan.DEFAULT_DESC_CHARS)}
    assert "NAME_FORMAT" not in fl and "MISSING_DESCRIPTION" in fl
    assert scan.parse_agent(quoted)["description"] == "Use when x"


def test_omit_claude_md_is_surfaced(scan, agent_file):
    # Bug caught (R2): not parsing omitClaudeMd lets the "re-pasted rules" trim delete the only copy.
    p = agent_file("a", "description: Use when x\ntools: Read\nomitClaudeMd: true\n")
    a = scan.parse_agent(p)
    assert a["omit_claude_md"] is True
    assert flags_of(scan, p)["OMITS_CLAUDE_MD"]["severity"] == "info"
    assert scan.parse_agent(agent_file("b", "description: Use when x\ntools: Read\n"))["omit_claude_md"] is False


def test_readable_report_labels_the_metric_as_definition_text(scan, agent_file):
    # Bug caught (R3): calling the chars/4 sum "tokens/launch" claims a runtime cost it never measures.
    p = agent_file("a", "description: Use when x\ntools: Read\n")
    out = subprocess.run([sys.executable, str(scan.__file__), str(p)],
                         capture_output=True, text=True, check=True).stdout
    assert "definition text" in out and "tokens/launch" not in out


# --- effort (reasoning effort next to the model) ---------------------------

def test_effort_is_parsed_like_model(scan, agent_file):
    # Bug caught: reading `effort` without `_scalar` keeps the quotes, so "high" never validates.
    quoted = agent_file("a", 'description: Use when x\ntools: Read\neffort: "high"\n')
    missing = agent_file("b", "description: Use when x\ntools: Read\n")
    assert scan.parse_agent(quoted)["effort"] == "high"
    assert scan.parse_agent(missing)["effort"] == ""


def test_effort_invalid_flags_values_outside_the_documented_five(scan, agent_file):
    # Bug caught: leaving `xhigh` (or any documented level) out of the valid set flags a legal value.
    for i, level in enumerate(["low", "medium", "high", "xhigh", "max"]):
        p = agent_file(f"ok{i}", f"description: Use when x\ntools: Read\neffort: {level}\n")
        assert "EFFORT_INVALID" not in flags_of(scan, p), level
    bad = flags_of(scan, agent_file("bad", "description: Use when x\ntools: Read\neffort: extreme\n"))
    assert bad["EFFORT_INVALID"]["severity"] == "med" and "extreme" in bad["EFFORT_INVALID"]["message"]
    assert "EFFORT_INHERIT" not in bad


def test_effort_inherit_flag(scan, agent_file):
    # Bug caught: inverting `if not a["effort"]` flags agents that set effort and misses the rest.
    unset = flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\n"))
    assert unset["EFFORT_INHERIT"]["severity"] == "low"
    assert "session" in unset["EFFORT_INHERIT"]["message"]
    assert "EFFORT_INHERIT" not in flags_of(scan, agent_file("b", "description: Use when x\ntools: Read\neffort: low\n"))


def test_high_effort_on_a_read_only_agent_is_questioned(scan, agent_file):
    # Bug caught: testing only `max` (or only `xhigh`) misses the other top level on a read-only agent.
    for level in ("xhigh", "max"):
        ro = agent_file(f"ro-{level}", f"description: Use when x\ntools: Read, Grep, Glob\neffort: {level}\n")
        assert flags_of(scan, ro)["HIGH_EFFORT_READONLY"]["severity"] == "low", level
    assert "HIGH_EFFORT_READONLY" not in flags_of(
        scan, agent_file("hi", "description: Use when x\ntools: Read, Grep\neffort: high\n"))


def test_high_effort_readonly_needs_a_read_only_tool_list(scan, agent_file):
    # Bug caught: checking only Edit/Write treats a Bash or inherit-all agent as read-only.
    for i, tools in enumerate(["Read, Edit", "Read, Write", "Read, NotebookEdit",
                               "Read, Bash", "Read, Bash(git diff:*)"]):
        p = agent_file(f"w{i}", f"description: Use when x\ntools: {tools}\neffort: max\n")
        assert "HIGH_EFFORT_READONLY" not in flags_of(scan, p), tools
    inherit_all = agent_file("all", "description: Use when x\neffort: max\n")
    assert "HIGH_EFFORT_READONLY" not in flags_of(scan, inherit_all)


def test_reports_show_effort_next_to_the_model(scan, agent_file):
    # Bug caught: parsing effort but never printing it leaves the report blind to the setting.
    p = agent_file("a", "description: Use when x\ntools: Read\nmodel: sonnet\neffort: max\n")
    q = agent_file("b", "description: Use when x\ntools: Read\n")
    text = subprocess.run([sys.executable, str(scan.__file__), str(p), str(q)],
                          capture_output=True, text=True, check=True).stdout
    assert "[sonnet, effort max]" in text
    assert "[inherit (default), effort inherit (session)]" in text
    data = json.loads(subprocess.run([sys.executable, str(scan.__file__), str(p), "--json"],
                                     capture_output=True, text=True, check=True).stdout)
    assert data["agents"][0]["effort"] == "max"


def test_haiku_does_not_get_effort_inherit(scan, agent_file):
    # Bug caught: checking EFFORT_INHERIT before the model asks a haiku agent to pin a level it ignores.
    haiku = flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\nmodel: haiku\n"))
    assert "EFFORT_INHERIT" not in haiku and "EFFORT_UNSUPPORTED" not in haiku
    for model in ("inherit", "sonnet", "claude-opus-5-5"):
        other = flags_of(scan, agent_file(f"m-{model}", f"description: Use when x\ntools: Read\nmodel: {model}\n"))
        assert "EFFORT_INHERIT" in other, model


def test_effort_set_on_haiku_is_unsupported(scan, agent_file):
    # Bug caught: validating effort without looking at the model lets `effort: max` on haiku pass as HIGH_EFFORT_READONLY.
    p = agent_file("a", "description: Use when x\ntools: Read, Grep\nmodel: haiku\neffort: max\n")
    flags = flags_of(scan, p)
    assert flags["EFFORT_UNSUPPORTED"]["severity"] == "low"
    assert "ignores effort" in flags["EFFORT_UNSUPPORTED"]["message"]
    assert "HIGH_EFFORT_READONLY" not in flags
    sonnet = flags_of(scan, agent_file("b", "description: Use when x\ntools: Read, Grep\nmodel: sonnet\neffort: max\n"))
    assert "EFFORT_UNSUPPORTED" not in sonnet and "HIGH_EFFORT_READONLY" in sonnet
