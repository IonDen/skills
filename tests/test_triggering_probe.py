"""The probe's isolation checks, run before any recorded session."""
WT = "writing-tests-that-can-fail"
LISTING = "Skills: ionden-skills:skill-optimizer, ionden-skills:subagent-optimizer, ionden-skills:writing-tests-that-can-fail."
QUOTED = LISTING + " Instructions: 'When you write, change or review tests, including the failing-test step of TDD, use the skill.'"
INIT = {"type": "system", "subtype": "init", "tools": ["Bash", "Read", "Skill"], "model": "claude-sonnet-5-5"}


def test_clean_probe_has_no_findings(trigger_runner):
    assert trigger_runner.probe_findings(INIT, QUOTED, LISTING + " Instructions: NONE") == []


def test_missing_skill_tool_is_a_finding(trigger_runner):
    init = dict(INIT, tools=["Bash", "Read"])
    assert trigger_runner.probe_findings(init, QUOTED, LISTING) == ["Skill tool missing"]


def test_unlisted_skill_is_a_finding(trigger_runner):
    text = QUOTED.replace("ionden-skills:subagent-optimizer, ", "")
    assert trigger_runner.probe_findings(INIT, text, LISTING) == ["skill not listed: subagent-optimizer"]


def test_snippet_not_seen_is_a_finding(trigger_runner):
    assert trigger_runner.probe_findings(INIT, LISTING, LISTING) == ["snippet not visible with CLAUDE.md"]


def test_snippet_seen_without_claude_md_is_a_finding(trigger_runner):
    assert trigger_runner.probe_findings(INIT, QUOTED, QUOTED) == ["snippet visible without CLAUDE.md"]


def test_snippet_match_ignores_case_and_line_breaks(trigger_runner):
    text = LISTING + " INCLUDING THE\nFAILING-TEST STEP OF TDD"
    assert trigger_runner.probe_findings(INIT, text, LISTING) == []


def test_user_memory_leak_is_a_finding(trigger_runner):
    leaked = LISTING + " Also: delegate git work to the scribe agent."
    assert trigger_runner.probe_findings(INIT, QUOTED, leaked) == ["user memory visible: scribe"]
