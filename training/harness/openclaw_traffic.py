"""Read shapes out of OpenClaw's own trajectory log. No proxy, no credentials.

WHY NOT THE PROXY. The obvious way to measure a deployment is to sit in front of it —
`openai_proxy --passthrough` exists for exactly that. It does not fit here: this
OpenClaw talks to ChatGPT through an OAuth session bound to OpenAI's endpoint, not a
bearer key a proxy could forward, so putting one in the middle would mean taking the
user's credential. **It also would not be necessary**, because OpenClaw already
records every run.

So this reads what is already on disk and emits the same lines
`training.harness.null_arm` consumes.

WHAT IT NEVER RECORDS. Not the prompt, not the assistant's text, not a tool call's
arguments. **The region question is about shapes** — which tools were offered, how
deep the conversation went, whether a call was made — and none of those need the
content. The snapshot it reads contains private conversations; this walks past them.

    python3 -m training.harness.openclaw_traffic --out traffic.jsonl
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DEFAULT_DBS = "~/.openclaw/agents/*/agent/openclaw-agent.sqlite"


def _tool_names(messages: list) -> list[str]:
    """Every tool named in a snapshot, and nothing else from it."""
    out = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        for tc in m.get("tool_calls") or m.get("toolCalls") or []:
            fn = (tc or {}).get("function") or tc or {}
            name = fn.get("name")
            if isinstance(name, str):
                out.append(name)
        # Some runtimes record the result turn with the tool's name on it.
        if m.get("role") in ("tool", "function") and isinstance(m.get("name"), str):
            out.append(m["name"])
    return out


def rows_from(db: Path) -> list[dict]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.execute("select event_json from trajectory_runtime_events")
        blobs = [r[0] for r in cur.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        con.close()

    out = []
    for blob in blobs:
        try:
            e = json.loads(blob)
        except (json.JSONDecodeError, TypeError):
            continue
        if e.get("type") != "model.completed":
            continue
        data = e.get("data") or {}
        msgs = data.get("messagesSnapshot") or []
        names = _tool_names(msgs)
        out.append({
            "model": e.get("modelId"),
            "provider": e.get("provider"),
            "tools": sorted(set(names)),
            "turns": len(msgs),
            # `reply` is what null_arm scans for well-formed calls. OpenClaw's own
            # runtime already parsed them into structure, so the count is passed
            # instead of the text — and the text stays where it is.
            "reply": "",
            "upstream_tool_calls": len(names),
            "session": e.get("sessionId"),
            "ts": e.get("ts"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", action="append", default=[],
                    help=f"repeatable; default {DEFAULT_DBS}")
    ap.add_argument("--out", default="traffic.jsonl")
    args = ap.parse_args()

    dbs = [Path(d).expanduser() for d in args.db] or sorted(
        Path("~/.openclaw/agents").expanduser().glob("*/agent/openclaw-agent.sqlite"))
    rows = []
    for db in dbs:
        if not db.exists():
            print(f"[skip] {db}")
            continue
        got = rows_from(db)
        print(f"[read] {db.parent.parent.name}: {len(got)} completed runs")
        rows += got

    Path(args.out).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    sessions = len({r["session"] for r in rows})
    print(f"\n{len(rows)} runs over {sessions} sessions -> {args.out}")
    if len(rows) < 50:
        # A REGION CANNOT BE SEEN IN A HANDFUL OF RUNS. Saying so here is cheaper
        # than letting null_arm report a confident share of a sample of six.
        print(f"\nThis is too little to answer the region question. The instrument\n"
              f"will run on it and the answer will not mean anything: three shapes\n"
              f"covering 60% of {len(rows)} runs is not evidence of a region.\n"
              f"Use OpenClaw normally for a week or two and run this again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
