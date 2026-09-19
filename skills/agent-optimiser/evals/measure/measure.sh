#!/usr/bin/env bash
# measure.sh <label> <agent.md> <task-cwd> <task-prompt>
set -u
label="$1"; md="$2"; cwd="$3"; task="$4"
M=${MEASURE_DIR:-$(cd "$(dirname "$0")" && pwd)}
agents="$(python3 $M/md2agent.py "$md")"
name="$(python3 -c "import json,sys; print(list(json.loads(sys.argv[1]).keys())[0])" "$agents")"
mkdir -p "$M/out"
( cd "$cwd" && claude -p "Use the Agent tool to launch the $name agent with exactly this task, verbatim, and then reply with the agent's full result unchanged: $task" \
    --model haiku --agents "$agents" --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
    --dangerously-skip-permissions --max-turns 6 --output-format json < /dev/null \
    > "$M/out/$label.json" 2> "$M/out/$label.err" )
python3 - "$label" "$cwd" <<'PY'
import json, sys, glob, os
label, cwd = sys.argv[1], sys.argv[2]
M="${MEASURE_DIR:-$(cd "$(dirname "$0")" && pwd)}"
d=json.load(open(f"{M}/out/{label}.json"))
res=[m for m in d if m.get("type")=="result"][-1]
sess=res["session_id"]
proj="-"+cwd.strip("/").replace("/","-")
files=glob.glob(os.path.expanduser(f"~/.claude/projects/{proj}/{sess}/subagents/*.jsonl"))
first=None; nreq=0; out_tokens=0
for f in files:
    seen=set()
    for line in open(f):
        m=json.loads(line)
        if m.get("type")=="assistant" and (m.get("message") or {}).get("usage"):
            rid=m.get("requestId") or m["message"].get("id")
            if rid in seen: continue
            seen.add(rid); u=m["message"]["usage"]; nreq+=1
            tot=u["input_tokens"]+u["cache_creation_input_tokens"]+u["cache_read_input_tokens"]
            if first is None: first=tot
            out_tokens+=u.get("output_tokens",0)
summary={"label":label,"first_request_input":first,"subagent_requests":nreq,"subagent_output_tokens":out_tokens,
         "result":res.get("result","")[:4000],"cost_usd":res.get("total_cost_usd"),"session":sess}
json.dump(summary, open(f"{M}/out/{label}.summary.json","w"), indent=1)
print(label, "first_request_input=",first, "requests=",nreq, "out=",out_tokens, "cost=",res.get("total_cost_usd"))
PY
