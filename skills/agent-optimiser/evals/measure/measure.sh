#!/usr/bin/env bash
# Measure what one agent definition costs to launch.
#
#   ./measure.sh <label> <agent.md> <task-dir> <task-prompt>
#
# It launches the agent once on the given task through `claude -p`, then reads
# the subagent's first API request out of the session transcript and writes
# out/<label>.summary.json. The first request is the launch cost: system prompt,
# tool schemas, CLAUDE.md, the agent body and the task.
#
# This runs an agent that can edit files inside <task-dir>, so point it at a
# throwaway copy of a workspace, never at real work. It uses the acceptEdits
# permission mode so a non-interactive run is not blocked on prompts; it does
# not bypass permissions. Override the output location with MEASURE_DIR.
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "usage: $0 <label> <agent.md> <task-dir> <task-prompt>" >&2
    exit 2
fi
label="$1"; md="$2"; cwd="$3"; task="$4"

# The label names output files, so keep it to characters that cannot traverse.
case "$label" in
    *[!A-Za-z0-9._-]* | "" | .* )
        echo "measure.sh: label must be non-empty, start with a letter, digit or _, and contain only A-Za-z0-9._-" >&2
        exit 2 ;;
esac
[ -f "$md" ] || { echo "measure.sh: no such agent file: $md" >&2; exit 2; }
[ -d "$cwd" ] || { echo "measure.sh: no such task directory: $cwd" >&2; exit 2; }

here="$(cd "$(dirname "$0")" && pwd)"
M="${MEASURE_DIR:-$here}"
cwd="$(cd "$cwd" && pwd)"
mkdir -p "$M/out"

agents="$(python3 "$here/md2agent.py" "$md")"
name="$(python3 -c 'import json,sys; print(next(iter(json.loads(sys.argv[1]))))' "$agents")"

( cd "$cwd" && claude -p "Use the Agent tool to launch the $name agent with exactly this task, verbatim, and then reply with the agent's full result unchanged: $task" \
    --model haiku --agents "$agents" --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
    --permission-mode acceptEdits --max-turns 6 --output-format json < /dev/null \
    > "$M/out/$label.json" 2> "$M/out/$label.err" )

python3 - "$label" "$cwd" "$M" <<'PY'
"""Read the subagent's first request out of the session transcript."""
import glob, json, os, sys

label, cwd, measure_dir = sys.argv[1], sys.argv[2], sys.argv[3]
transcript = json.load(open(f"{measure_dir}/out/{label}.json"))
result = [m for m in transcript if m.get("type") == "result"][-1]
session = result["session_id"]
project = "-" + cwd.strip("/").replace("/", "-")

first = None
requests = output_tokens = 0
for path in glob.glob(os.path.expanduser(f"~/.claude/projects/{project}/{session}/subagents/*.jsonl")):
    seen = set()
    for line in open(path):
        m = json.loads(line)
        usage = (m.get("message") or {}).get("usage") if m.get("type") == "assistant" else None
        if not usage:
            continue
        rid = m.get("requestId") or m["message"].get("id")
        if rid in seen:
            continue
        seen.add(rid)
        requests += 1
        output_tokens += usage.get("output_tokens", 0)
        total = usage["input_tokens"] + usage["cache_creation_input_tokens"] + usage["cache_read_input_tokens"]
        if first is None:
            first = total

summary = {"label": label, "first_request_input": first, "subagent_requests": requests,
           "subagent_output_tokens": output_tokens, "result": result.get("result", "")[:4000],
           "cost_usd": result.get("total_cost_usd"), "session": session}
with open(f"{measure_dir}/out/{label}.summary.json", "w") as fh:
    json.dump(summary, fh, indent=1)
print(f"{label} first_request_input={first} requests={requests} "
      f"out={output_tokens} cost={result.get('total_cost_usd')}")
PY
