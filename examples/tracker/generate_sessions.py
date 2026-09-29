r"""Long sessions for the team tracker — H2's suite: four and five turns by one user in one role, where most turns need an
earlier one. It is the case the workflow harness exists for: over five turns a conversation carried in the prompt grows,
and a key carried in the operational memory does not.

    developer  show me RD-169 → move it to review → log 2 hours on it → who owns its component? → comment that it's ready
    lead       create a bug: … → assign it to Ana → what does the bug policy say about critical ones? → show me the board
               → show me the one you just created
    qa         open RD-88 → it passes, move it to done → what does the definition of done say about tests? → comment that
               it's verified

A dependent turn's argument is an issue key the user named earlier, a key an earlier tool CREATED (the lead's new bug), or
a value an earlier result showed (the issue's component, whose owner a page states). Every turn is checked mechanically
(tool and arguments), on the session's own world (`db.world(seed)`, seeds apart from anything else). Wording is split
train / eval.

    python -m examples.tracker.generate_sessions                    # data_sessions/{train,eval}.jsonl, gate.json
    python -m examples.tracker.generate_sessions --harness-corpus   # + data_sessions/train_harness.jsonl, gate_harness.json
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from examples.distributor.generate_sessions import call_matches
from examples.tracker import db, tools

OUT = Path(__file__).parent / "data_sessions"
WORKFLOWS = Path(__file__).parent / "workflows"
SEED0 = {"train": 500_000, "eval": 970_000}
N = {"train": 300, "eval": 60}
KINDS = ("developer", "lead", "qa")
NEXT = {"todo": "in_progress", "in_progress": "in_review"}

P = {
    "developer": {
        "train": [["Show me {key}.", "Open {key} for me."], ["Move it to {to_h}.", "Set it to {to_h}."],
                  ["Log {h} hours on it.", "Put {h}h of work on it."], ["Who owns its component?", "Which person owns the component of that one?"],
                  ["Add a comment to it: {note}", "Comment on it: {note}"]],
        "eval": [["Can you pull up {key}?", "What's the state of {key}?"], ["Now move it to {to_h}.", "Please change it to {to_h}."],
                 ["Record {h} hours against it.", "I spent {h} hours on it, log that."], ["Who is the owner of its component?", "Whose component is that?"],
                 ["Leave a note on it: {note}", "Write this on it: {note}"]]},
    "lead": {
        "train": [["Create a bug: {summary}", "Open a new bug — {summary}"], ["Assign it to {person}.", "Give it to {person}."],
                  ["What does the bug policy say about critical ones?", "How fast must a critical bug be triaged?"],
                  ["Show me the board.", "How does the sprint look?"], ["Show me the one you just created.", "Open that new bug again."]],
        "eval": [["File a bug: {summary}", "We have a new bug: {summary}"], ["Hand it to {person}.", "Assign that one to {person}."],
                 ["What's our rule for critical bugs?", "What does the policy say about critical bugs?"],
                 ["What's on the sprint board?", "Give me the sprint status."], ["Pull up the bug you created.", "Show the new bug again."]]},
    "qa": {
        "train": [["Open {key}.", "Show me {key}."], ["It passes — move it to done.", "Verified, set it to done."],
                  ["What does the definition of done say about tests?", "Where must the tests pass for done?"],
                  ["Comment on it: {note}", "Add a note to it: {note}"]],
        "eval": [["Let me see {key}.", "Pull up {key}."], ["Looks good, close it as done.", "It works — mark it done."],
                 ["What's the done rule for tests?", "Where do tests have to pass before done?"],
                 ["Put a comment on it: {note}", "Note on it: {note}"]]},
}
NOTES = ["ready for QA", "verified on staging", "needs a follow-up ticket", "tested with a large account", "looks good to me"]
SUMMARIES = ["Login loops on Safari", "Invoice PDF shows the wrong total", "Search misses accented names",
             "Password reset email never arrives", "Export hangs after 10,000 rows"]


def _pick(conn, org: str, where: str) -> dict | None:
    r = conn.execute(f"select * from issues where org_id=? and {where} order by key", (org,)).fetchall()
    return dict(r[0]) if r else None


def session(seed: int, split: str, kind: str) -> dict | None:
    r = random.Random(seed)
    conn = db.world(seed)
    org = r.choice([o for o, _, _ in db.ORGS])
    fill = {"h": r.choice([1, 2, 3, 4]), "note": r.choice(NOTES), "summary": r.choice(SUMMARIES)}
    plan: list[tuple[str, dict, bool]]
    if kind == "developer":
        iss = _pick(conn, org, "status in ('todo','in_progress')")
        if iss is None:
            return None
        to = NEXT[iss["status"]]
        fill.update(key=iss["key"], to_h=to.replace("_", " "))
        plan = [("issue_get", {"key": iss["key"]}, False), ("issue_transition", {"key": iss["key"], "status": to}, True),
                ("worklog_add", {"key": iss["key"], "hours": fill["h"]}, True),
                ("page_read", {"ref": f"components#{iss['component']}"}, True), ("issue_comment", {"key": iss["key"], "text~": fill["note"]}, True)]
    elif kind == "lead":
        person = conn.execute("select name from people where org_id=? and role='developer' order by name", (org,)).fetchone()["name"]
        prefix = dict((o, p) for o, _, p in db.ORGS)[org]
        n = 1 + max(int(x["key"].split("-")[1]) for x in conn.execute("select key from issues where org_id=?", (org,)))
        new = f"{prefix}-{n}"
        fill.update(person=person.split()[0])
        plan = [("issue_create", {"type": "bug", "summary~": fill["summary"].split()[0]}, False),
                ("issue_assign", {"key": new, "person~": person.split()[0].lower()}, True),
                ("page_read", {"ref": "bug-policy#critical"}, False), ("sprint_board", {}, False), ("issue_get", {"key": new}, True)]
    else:
        iss = _pick(conn, org, "type='story' and status='qa'")
        if iss is None:
            return None
        fill.update(key=iss["key"])
        plan = [("issue_get", {"key": iss["key"]}, False), ("issue_transition", {"key": iss["key"], "status": "done"}, True),
                ("page_read", {"ref": "definition-of-done#tests"}, False), ("issue_comment", {"key": iss["key"], "text~": fill["note"]}, True)]
    turns = [{"request": r.choice(options).format(**fill), "tool": tool, "args": args, "depends": dep}
             for options, (tool, args, dep) in zip(P[kind][split], plan)]
    return {"session_id": f"tr-{split}-{seed}", "split": split, "kind": kind, "role": kind, "org": org,
            "user_id": f"{kind}-{org}", "world_seed": seed, "turns": turns}


def build(split: str) -> list[dict]:
    out, i = [], 0
    while len(out) < N[split]:
        s = session(SEED0[split] + i, split, KINDS[len(out) % len(KINDS)])
        i += 1
        if s:
            out.append(s)
    return out


def turn_right(calls: list[dict], turn: dict) -> bool:
    want = {k: (tools._key(v) if k == "key" else v) for k, v in turn["args"].items()}
    norm = [{**c, "args": {k: (v.upper() if k == "key" else re.sub(r"\.0$", "", str(v)).replace(" ", "_") if k == "status" else
                               re.sub(r"\.0$|h$", "", str(v).strip()) if k == "hours" else v) for k, v in (c.get("args") or {}).items()}}
            for c in calls]
    return any(call_matches(c, turn["tool"], {k: (str(v) if k != "status" else v) for k, v in want.items()}) for c in norm)


# ----------------------------------------------------------------------------------------------- the harness
PUTS = {"developer": ("issue", "component"), "lead": ("issue",), "qa": ("issue",)}


def workflows() -> dict:
    from examples.common.opmemory import Workflow
    return {f.stem: Workflow.load(f) for f in sorted(WORKFLOWS.glob("*.toml"))}


def _args(turn: dict) -> dict:
    return {k.rstrip("~"): v for k, v in turn["args"].items()}


def harness_oracle(sess: dict):
    """A first turn makes its call and `put`s what later turns need (the issue's key — for the lead, the key the tool
    CREATED — and, for the developer, its component); a dependent turn `get`s what it needs, then calls."""
    i_turn = {"i": -1}

    def generate(system, user, close, history=None):
        i_turn["i"] += 1
        i, turn = i_turn["i"], sess["turns"][i_turn["i"]]
        args = _args(turn)
        if turn["tool"] == "issue_create":
            args["summary"] = next(s for s in SUMMARIES if s.startswith(args["summary"]))
        if turn["tool"] == "issue_assign":
            args["person"] = args["person"].title()
        if turn["tool"] == "issue_comment":
            args["text"] = args["text"]
        needs = []
        if turn["depends"]:
            needs = ["component"] if turn["tool"] == "page_read" else ["issue"]
        steps = [f"<get>{k}</get>" for k in needs]
        steps.append(_tag(turn["tool"], args))

        def gen(prefix: str) -> str:
            done = prefix.count("</")
            if done < len(steps):
                return steps[done]
            if i == 0 and done == len(steps):
                res = _result(prefix, turn["tool"])
                if turn["tool"] == "issue_create":
                    return f"<put>issue={res.split()[1]}</put>"
                if sess["kind"] == "developer":
                    return f"<put>issue={args['key']}</put>"
                return f"<put>issue={args['key']}</put>"
            if i == 0 and sess["kind"] == "developer" and done == len(steps) + 1:
                comp = re.search(r"· (\w+)$", _result(prefix, turn["tool"]).splitlines()[0])
                return f"<put>component={comp.group(1)}</put>"
            return _answer(_result(prefix, turn["tool"]))
        return gen, lambda: {"prompt_tokens": 0, "completion_tokens": 0}
    return generate


def _tag(tool: str, args: dict) -> str:
    if not args:
        return f"<{tool}></{tool}>"
    body = str(next(iter(args.values()))) if len(args) == 1 else "; ".join(f"{k}={v}" for k, v in args.items())
    return f"<{tool}>{body}</{tool}>"


def _result(prefix: str, tool: str) -> str:
    m = re.search(rf"</{tool}>= (.*?)(?=\n<|\Z)", prefix, re.S)
    return m.group(1).strip() if m else ""


def _answer(result: str) -> str:
    from examples.common import grounding
    body = "; ".join(l.strip("- ").strip() for l in grounding.redact(result).splitlines() if l.strip()).rstrip(".")
    return f"According to the tracker: {body}."


def play(sess: dict, generate, history: bool = False, harness: bool = False, tool_block: bool = True,
         capture: list | None = None) -> list[dict]:
    """One session through the gateway (`--org tracker`), as examples/distributor/generate_sessions.play."""
    from examples.common import tokens
    from examples.common.opmemory import OpMemory
    from examples.school.gateway import Gateway
    from examples.tracker import users
    users.register_all()
    served = {}

    def spy(system, user, close, history=None):
        served.update(system=system, user=user)
        return generate(system, user, close, history) if history else generate(system, user, close)
    gw = Gateway(db.world(sess["world_seed"]), spy, org="tracker", history=history, memory=OpMemory() if harness else None,
                 workflows=workflows() if harness else None, tool_block=tool_block, max_calls=6)
    token = tokens.issue(sess["user_id"], sess["role"], sess["org"])
    messages, out = [], []
    for t in sess["turns"]:
        messages.append({"role": "user", "content": t["request"]})
        try:
            r = gw.turn(token, messages, session=sess["session_id"])
        except Exception as e:                                   # transport — never folded into a score
            out.append({"request": t["request"], "error": repr(e)[:160]})
            messages.append({"role": "assistant", "content": ""})
            continue
        ev = r["event"]
        out.append({"request": t["request"], "tool": t["tool"], "depends": t["depends"], "right": turn_right(ev["calls"], t),
                    "calls": ev["calls"], "route": r["route"], "reply": r["reply"][:300], "walk": r["walk"][-500:],
                    "prompt_tokens": ev.get("prompt_tokens", 0), "completion_tokens": ev.get("completion_tokens", 0)})
        if capture is not None:
            capture.append({"system": served["system"], "user": served["user"], "walk": r["walk"]})
        messages.append({"role": "assistant", "content": r["reply"]})
    return out


def gate(train: list[dict], evals: list[dict]) -> dict:
    """S1 no eval wording in train · S2 no shared world · S3 the harness oracle gets every turn right through the gateway
    · S4 no dependent turn carries its own argument (the key it needs is not in its request)."""
    ev_text = {t["request"] for s in evals for t in s["turns"]}
    bad = sum(not all(x.get("right") for x in play(s, harness_oracle(s), harness=True)) for s in train + evals)

    def self_contained(t):
        k = t["args"].get("key")
        return bool(k) and str(k).lower() in t["request"].lower()
    g = {"S1_eval_wording_in_train": sum(t["request"] in ev_text for s in train for t in s["turns"]),
         "S2_shared_world": len({s["world_seed"] for s in train} & {s["world_seed"] for s in evals}),
         "S3_oracle_fails_a_turn": bad,
         "S4_dependent_turn_self_contained": sum(self_contained(t) for s in train + evals for t in s["turns"] if t["depends"]),
         "sessions": {"train": len(train), "eval": len(evals)},
         "turns": {"eval": sum(len(s["turns"]) for s in evals), "eval_dependent": sum(t["depends"] for s in evals for t in s["turns"])}}
    g["passed"] = all(v == 0 for k, v in g.items() if k[:1] == "S" and k[1].isdigit())
    return g


def main() -> int:
    import sys
    OUT.mkdir(exist_ok=True)
    if "--harness-corpus" in sys.argv[1:]:
        train = [json.loads(l) for l in (OUT / "train.jsonl").read_text().splitlines() if l.strip()]
        rows = []
        # H1's lesson [ran]: a member trained only on prompts that carry the tool block calls no tool without it (0/60).
        # A third of the sessions are rendered WITHOUT the block, so the member learns its tools by name, not by reading.
        for j, s in enumerate(train):
            cap: list = []
            play(s, harness_oracle(s), harness=True, tool_block=(j % 3 != 2), capture=cap)
            rows += [{"case_id": f"{s['session_id']}-t{i}", "kind": s["kind"], "turn": i, "depends": s["turns"][i]["depends"],
                      "messages": [{"role": "system", "content": c["system"]}, {"role": "user", "content": c["user"]},
                                   {"role": "assistant", "content": c["walk"]}]} for i, c in enumerate(cap)]
        (OUT / "train_harness.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        g = {"rows": len(rows), "rows_without_tool_block": sum("The following tools are available" not in r["messages"][1]["content"] for r in rows),
             "rows_with_get": sum("<get>" in r["messages"][2]["content"] for r in rows),
             "rows_with_put": sum("<put>" in r["messages"][2]["content"] for r in rows)}
        (OUT / "gate_harness.json").write_text(json.dumps(g, indent=1))
        print(f"[tracker] harness corpus {g}", flush=True)
        return 0
    train, evals = build("train"), build("eval")
    g = gate(train, evals)
    for name, rows in (("train", train), ("eval", evals)):
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (OUT / "gate.json").write_text(json.dumps(g, indent=1))
    print(f"[tracker] sessions gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
