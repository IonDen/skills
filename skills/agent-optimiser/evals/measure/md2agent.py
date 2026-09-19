"""Convert a .claude/agents/*.md file into the --agents JSON entry."""
import json, re, sys
from pathlib import Path
def load(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    fm, body = m.group(1), m.group(2)
    fields, cur = {}, None
    for line in fm.splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s?(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            cur = km.group(1); fields[cur] = km.group(2)
        elif cur: fields[cur] += "\n" + line
    def scalar(v):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            inner = v[1:-1]
            try: return json.loads('"' + inner + '"') if v[0] == '"' else inner
            except Exception: return inner
        return v
    entry = {"description": scalar(fields.get("description", "")), "prompt": body.strip()}
    if fields.get("model"): entry["model"] = scalar(fields["model"])
    if fields.get("tools"):
        entry["tools"] = [t.strip() for t in re.sub(r"\s*#.*", "", fields["tools"]).replace("\n", ",").split(",") if t.strip().lstrip("-").strip()]
        entry["tools"] = [t.lstrip("-").strip() for t in entry["tools"]]
    return scalar(fields["name"]), entry
if __name__ == "__main__":
    name, entry = load(sys.argv[1]); print(json.dumps({name: entry}))
