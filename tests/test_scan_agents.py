"""Each test names the one-line bug in scan_agents.py that would make it fail."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


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


def test_haiku_full_model_id_is_treated_like_the_alias(scan, agent_file):
    # Bug caught: matching only the exact alias `haiku` misses `claude-haiku-4-5`, which has no effort either.
    unset = flags_of(scan, agent_file("a", "description: Use when x\ntools: Read\nmodel: claude-haiku-4-5\n"))
    assert "EFFORT_INHERIT" not in unset
    pinned = flags_of(scan, agent_file("b", "description: Use when x\ntools: Read\nmodel: claude-haiku-4-5\neffort: low\n"))
    assert pinned["EFFORT_UNSUPPORTED"]["severity"] == "low"


# --- Codex custom agents (.codex/agents/*.toml) ----------------------------

needs_toml = pytest.mark.skipif(sys.version_info < (3, 11),
                                reason="tomllib is in the standard library from Python 3.11")

CODEX_OK = '''name = "log_reader"
description = "Finds error lines in logs."
model = "gpt-6-luna"
model_reasoning_effort = "high"
developer_instructions = """
Find the error lines and report them as path:line with a quote.
"""
'''


def cflags(scan, path):
    return flags_of(scan, path)


@needs_toml
def test_codex_agent_is_normalised_into_the_shared_dict(scan, codex_file):
    # Bug caught: reading effort from `effort` instead of `model_reasoning_effort` loses the Codex setting.
    a = scan.parse_agent(codex_file("log_reader", CODEX_OK))
    assert a["format"] == "codex" and a["name"] == "log_reader"
    assert a["model"] == "gpt-6-luna" and a["effort"] == "high"
    assert "path:line" in a["body"] and a["description"] == "Finds error lines in logs."
    assert a["tools"] == [] and a["has_tools"] is False


def test_claude_agents_are_labelled_claude(scan, agent_file):
    # Bug caught: leaving `format` off Claude agents makes the shared report unable to tell them apart.
    assert scan.parse_agent(agent_file("a", "description: Use when x\ntools: Read\n"))["format"] == "claude"


@needs_toml
def test_codex_agent_gets_no_claude_only_flags(scan, codex_file):
    # Bug caught: running the Claude checks on a Codex agent reports a missing `tools` field Codex has no use for.
    text = CODEX_OK.replace('model = "gpt-6-luna"\nmodel_reasoning_effort = "high"\n', "")
    flags = cflags(scan, codex_file("log_reader", text))
    for code in ("NO_TOOLS_FIELD", "MODEL_INHERIT", "EFFORT_INHERIT", "NAME_FORMAT", "WEAK_TRIGGER"):
        assert code not in flags, code


@needs_toml
def test_codex_missing_or_blank_required_keys(scan, codex_file):
    # Bug caught: testing only `key in data` lets a blank developer_instructions through, which Codex refuses.
    p = codex_file("x", 'name = "x"\ndeveloper_instructions = "   "\n')
    f = cflags(scan, p)["CODEX_MISSING_REQUIRED"]
    assert f["severity"] == "high"
    assert f["message"].startswith("Missing or blank: description, developer_instructions.")
    assert "CODEX_MISSING_REQUIRED" not in cflags(scan, codex_file("ok", CODEX_OK))


@needs_toml
def test_codex_claude_style_keys_are_high(scan, codex_file):
    # Bug caught: flagging `skills` whatever its type flags Codex's own `[[skills.config]]` table.
    text = CODEX_OK + 'tools = ["Read", "Grep"]\neffort = "high"\npermissionMode = "plan"\nskills = ["a"]\n'
    f = cflags(scan, codex_file("claude_keys", text))["CODEX_CLAUDE_KEY"]
    assert f["severity"] == "high"
    for key in ("tools", "effort", "permissionMode", "skills"):
        assert key in f["message"], key
    assert "model_reasoning_effort" in f["message"]
    codex_skills = CODEX_OK + '\n[[skills.config]]\npath = "/x/SKILL.md"\nenabled = false\n'
    assert "CODEX_CLAUDE_KEY" not in cflags(scan, codex_file("codex_skills", codex_skills))


@needs_toml
def test_codex_effort_values_outside_the_documented_six_are_invalid(scan, codex_file):
    # Bug caught: a valid set without `ultra` (Claude's five) flags a legal Codex level.
    def with_effort(name, effort):
        return codex_file(name, CODEX_OK.replace('"gpt-6-luna"', '"my-model"')
                          .replace('effort = "high"', f'effort = "{effort}"'))
    for level in ("low", "medium", "high", "xhigh", "max", "ultra"):
        assert "CODEX_EFFORT_INVALID" not in cflags(scan, with_effort(f"ok_{level}", level)), level
    bad = cflags(scan, with_effort("bad", "extreme"))["CODEX_EFFORT_INVALID"]
    assert bad["severity"] == "med" and "extreme" in bad["message"]
    minimal = cflags(scan, with_effort("minimal", "minimal"))["CODEX_EFFORT_INVALID"]
    assert "not offered" in minimal["message"]


@needs_toml
def test_codex_effort_must_be_one_the_model_offers(scan, codex_file):
    # Bug caught: checking effort against the global set instead of the model's table misses ultra on Luna.
    def agent(name, model, effort):
        return codex_file(name, CODEX_OK.replace('"gpt-6-luna"', f'"{model}"')
                          .replace('effort = "high"', f'effort = "{effort}"'))
    luna_ultra = cflags(scan, agent("a", "gpt-6-luna", "ultra"))["CODEX_EFFORT_UNSUPPORTED"]
    assert luna_ultra["severity"] == "med" and "gpt-6-luna" in luna_ultra["message"]
    assert "CODEX_EFFORT_UNSUPPORTED" in cflags(scan, agent("b", "gpt-5.5", "max"))
    assert "CODEX_EFFORT_UNSUPPORTED" in cflags(scan, agent("c", "gpt-5.6-luna", "ultra"))
    assert "CODEX_EFFORT_UNSUPPORTED" not in cflags(scan, agent("d", "gpt-6-luna", "max"))
    assert "CODEX_EFFORT_UNSUPPORTED" not in cflags(scan, agent("e", "gpt-6-sol", "ultra"))
    assert "CODEX_EFFORT_UNSUPPORTED" not in cflags(scan, agent("f", "someone-elses-model", "ultra"))


@needs_toml
def test_codex_retired_models_are_flagged_with_the_date(scan, codex_file):
    # Bug caught: dropping gpt-5.4-mini from the retired table lets a dead slug through.
    for model in ("gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.2", "gpt-5.3-codex"):
        p = codex_file(f"m{model}", CODEX_OK.replace('"gpt-6-luna"', f'"{model}"')
                       .replace('effort = "high"', 'effort = "low"'))
        f = cflags(scan, p)["CODEX_MODEL_RETIRED"]
        assert f["severity"] == "med" and "ChatGPT sign-in, as of 2026-09-24" in f["message"], model
    assert "CODEX_MODEL_RETIRED" not in cflags(scan, codex_file("sol", CODEX_OK.replace("gpt-6-luna", "gpt-6-sol")))


@needs_toml
def test_codex_model_pinned_without_effort(scan, codex_file):
    # Bug caught: inverting the check flags agents that pin both and misses the ones that pin only the model.
    only_model = CODEX_OK.replace('model_reasoning_effort = "high"\n', "")
    assert cflags(scan, codex_file("a", only_model))["CODEX_MODEL_WITHOUT_EFFORT"]["severity"] == "low"
    assert "CODEX_MODEL_WITHOUT_EFFORT" not in cflags(scan, codex_file("b", CODEX_OK))
    neither = only_model.replace('model = "gpt-6-luna"\n', "")
    assert "CODEX_MODEL_WITHOUT_EFFORT" not in cflags(scan, codex_file("c", neither))


@needs_toml
def test_codex_agents_reuse_the_length_checks_and_duplicate_blocks(scan, codex_file, agent_file):
    # Bug caught: a Codex dict without body_lines/_paragraphs skips LONG_BODY and duplicate detection.
    long_body = "\n".join(f"line {i}" for i in range(scan.DEFAULT_BODY_LINES + 1))
    p = codex_file("long", f'name = "long"\ndescription = "d"\ndeveloper_instructions = """\n{long_body}\n"""\n')
    assert "LONG_BODY" in cflags(scan, p)
    para = "Shared rule: " + "x" * 130
    c = scan.parse_agent(codex_file("c", f'name = "c"\ndescription = "d"\ndeveloper_instructions = """\n{para}\n"""\n'))
    m = scan.parse_agent(agent_file("m", "description: Use when x\ntools: Read\n", para + "\n"))
    assert scan.find_duplicate_blocks([c, m])[0]["agents"] == ["c", "m"]


@needs_toml
def test_toml_without_agent_keys_is_not_an_agent(scan, tmp_path):
    # Bug caught: treating every .toml as an agent puts pyproject.toml in the report.
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "pkg"\nversion = "1"\n')
    assert scan.parse_agent(p) is None


@needs_toml
def test_malformed_toml_is_reported_not_fatal(scan, tmp_path, agent_file):
    # Bug caught: letting TOMLDecodeError escape aborts the whole scan on one broken file.
    bad = tmp_path / "bad.toml"
    bad.write_text('name = "bad\n')
    agent_file("good", "description: Use when x\ntools: Read\n")
    agents, skipped = scan.scan_paths([str(tmp_path)])
    assert [a["name"] for a in agents] == ["good"]
    assert skipped[0]["path"].endswith("bad.toml") and "TOML" in skipped[0]["reason"]


def test_directory_walk_finds_toml_and_notes_symlinked_toml(scan, tmp_path):
    # Bug caught: a walk over `*.md` only never sees Codex agents; a silent symlink skip hides why one is missing.
    (tmp_path / "a.md").write_text("---\nname: a\ndescription: Use when x\n---\nbody\n")
    (tmp_path / "b.toml").write_text(CODEX_OK)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.toml"
    outside.write_text(CODEX_OK)
    (tmp_path / "link.toml").symlink_to(outside)
    notes = []
    files = scan.gather([str(tmp_path)], notes)
    assert sorted(f.name for f in files) == ["a.md", "b.toml"]
    assert notes[0]["path"].endswith("link.toml") and "symlink" in notes[0]["reason"]


def test_without_tomllib_codex_files_are_not_scanned_but_claude_files_are(scan, tmp_path, monkeypatch):
    # Bug caught: calling tomllib unguarded crashes the whole scan on Python 3.10.
    monkeypatch.setattr(scan, "tomllib", None)
    (tmp_path / "a.md").write_text("---\nname: a\ndescription: Use when x\n---\nbody\n")
    (tmp_path / "b.toml").write_text(CODEX_OK)
    agents, skipped = scan.scan_paths([str(tmp_path)])
    assert [a["name"] for a in agents] == ["a"]
    assert skipped == [{"path": str(tmp_path / "b.toml"), "reason": "not scanned: needs Python 3.11+"}]


def test_default_targets_include_codex_agent_folders(scan):
    # Bug caught: scanning only .claude/agents by default never finds personal Codex agents.
    targets = scan.default_targets()
    assert str(Path.home() / ".claude/agents") in targets
    assert str(Path.home() / ".codex/agents") in targets


@needs_toml
def test_codex_reports_show_format_model_and_effort(scan, codex_file):
    # Bug caught: printing the Claude tools summary for a Codex agent claims a tools field it cannot have.
    p = codex_file("log_reader", CODEX_OK)
    text = subprocess.run([sys.executable, str(scan.__file__), str(p)],
                          capture_output=True, text=True, check=True).stdout
    assert "[gpt-6-luna, effort high]  Codex agent (no per-agent tool list)" in text
    data = json.loads(subprocess.run([sys.executable, str(scan.__file__), str(p), "--json"],
                                     capture_output=True, text=True, check=True).stdout)
    a = data["agents"][0]
    assert a["format"] == "codex" and "body" not in a and "_keys" not in a
    assert data["skipped"] == []


# --- PR 11 fixes: declared roles, new Codex flags, robustness ---------------

def test_duplicate_blocks_keep_same_named_files_apart(scan, tmp_path):
    # Bug caught: keying duplicate detection by `name` collapses a Claude agent and its
    # same-named port (or user and project scope copies) into one, hiding the duplication.
    para = "Shared rule: " + "x" * 130
    user = tmp_path / "user"
    proj = tmp_path / "proj"
    user.mkdir()
    proj.mkdir()
    (user / "reviewer.md").write_text(f"---\nname: reviewer\ndescription: Use when x\ntools: Read\n---\n{para}\n")
    (proj / "reviewer.md").write_text(f"---\nname: reviewer\ndescription: Use when x\ntools: Read\n---\n{para}\n")
    agents, _ = scan.scan_paths([str(user), str(proj)])
    dups = scan.find_duplicate_blocks(agents)
    assert len(dups) == 1
    assert dups[0]["files"] == [str(proj / "reviewer.md"), str(user / "reviewer.md")]
    text = subprocess.run([sys.executable, str(scan.__file__), str(user), str(proj)],
                          capture_output=True, text=True, check=True).stdout
    assert "DUPLICATED BLOCKS" in text
    assert f"reviewer ({user / 'reviewer.md'})" in text and f"reviewer ({proj / 'reviewer.md'})" in text


# Keys Codex 0.149+ parses but does not apply to a custom agent (rust-v0.156.1,
# core/src/agent/role.rs AgentRoleOverrides). Written out, not read from the scanner,
# so dropping one from CODEX_IGNORED_KEYS turns its case red.
IGNORED_KEY_SNIPPETS = {
    "sandbox_mode": 'sandbox_mode = "read-only"\n',
    "approval_policy": 'approval_policy = "never"\n',
    "model_provider": 'model_provider = "openai"\n',
    "notify": 'notify = ["notify-send"]\n',
    "openai_base_url": 'openai_base_url = "https://example.com"\n',
    "chatgpt_base_url": 'chatgpt_base_url = "https://example.com"\n',
    "mcp_servers": '[mcp_servers.docs]\nurl = "https://example.com/mcp"\n',
    "apps": '[apps]\nenabled = false\n',
    "hooks": '[[hooks.PreToolUse]]\nmatcher = "shell"\n',
}


@needs_toml
@pytest.mark.parametrize("key", sorted(IGNORED_KEY_SNIPPETS))
def test_codex_ignored_keys_are_low_and_kept(scan, codex_file, key):
    # Bug caught: a key missing from CODEX_IGNORED_KEYS (or `hooks` left in the Claude list)
    # is either reported as effective or told to be removed, though older Codex still applies it.
    flags = cflags(scan, codex_file(f"ign_{key}", CODEX_OK + "\n" + IGNORED_KEY_SNIPPETS[key]))
    f = flags["CODEX_IGNORED_KEY"]
    assert f["severity"] == "low" and key in f["message"]
    assert "0.149" in f["message"] and "older" in f["message"]
    assert "remove" not in f["message"].lower()
    assert "CODEX_CLAUDE_KEY" not in flags and "CODEX_UNKNOWN_KEY" not in flags


@needs_toml
def test_service_tier_is_applied_so_not_ignored(scan, codex_file):
    # Bug caught: listing service_tier as ignored, though rust-v0.156.1 applies it to the child.
    flags = cflags(scan, codex_file("tier", 'service_tier = "flex"\n' + CODEX_OK))
    assert "CODEX_IGNORED_KEY" not in flags and "CODEX_UNKNOWN_KEY" not in flags


@needs_toml
@pytest.mark.parametrize("model", ["sonnet", "Opus", "HAIKU", "fable", "inherit",
                                   "claude-opus-5-5", "Claude-Sonnet-4-6"])
def test_codex_claude_model_is_high(scan, codex_file, model):
    # Bug caught: a case-sensitive alias match, or no `claude-` prefix check, lets a Claude model
    # through that Codex cannot resolve.
    text = CODEX_OK.replace('"gpt-6-luna"', f'"{model}"')
    f = cflags(scan, codex_file("cm", text))["CODEX_CLAUDE_MODEL"]
    assert f["severity"] == "high" and model in f["message"]


@needs_toml
@pytest.mark.parametrize("model", ["gpt-6-sol", "someone-elses-model", "my-claude-proxy"])
def test_codex_model_that_is_not_claude_is_not_flagged(scan, codex_file, model):
    # Bug caught: a substring match on "claude" flags a Codex model whose slug merely contains it.
    text = CODEX_OK.replace('"gpt-6-luna"', f'"{model}"').replace('effort = "high"', 'effort = "low"')
    assert "CODEX_CLAUDE_MODEL" not in cflags(scan, codex_file("ok", text))


@needs_toml
def test_codex_unknown_top_level_key_is_high(scan, codex_file):
    # Bug caught: without a known-key list, `prompt` and `version` pass silently while Codex
    # skips the whole agent.
    f = cflags(scan, codex_file("unk", 'prompt = "x"\nversion = 2\n' + CODEX_OK))["CODEX_UNKNOWN_KEY"]
    assert f["severity"] == "high"
    assert "prompt" in f["message"] and "version" in f["message"] and "skips" in f["message"]


@needs_toml
def test_codex_known_keys_are_not_unknown(scan, codex_file):
    # Bug caught: a known-key list missing Codex's own keys (nickname_candidates, personality,
    # [features], [[skills.config]], [tools]) flags a valid agent as one Codex will skip.
    text = ('nickname_candidates = ["Ada"]\npersonality = "pragmatic"\nmodel_verbosity = "low"\n'
            'model_reasoning_summary = "concise"\n' + CODEX_OK
            + '\n[features]\nshell_tool = false\n\n[[skills.config]]\npath = "/x/SKILL.md"\nenabled = false\n'
            '\n[tools]\nweb_search = false\n')
    flags = cflags(scan, codex_file("known", text))
    assert "CODEX_UNKNOWN_KEY" not in flags and "CODEX_CLAUDE_KEY" not in flags


@needs_toml
def test_claude_keys_are_not_also_reported_as_unknown(scan, codex_file):
    # Bug caught: checking unknown keys without excluding Claude keys reports `color` twice.
    flags = cflags(scan, codex_file("ck", CODEX_OK + 'color = "blue"\n'))
    assert "color" in flags["CODEX_CLAUDE_KEY"]["message"] and "CODEX_UNKNOWN_KEY" not in flags
