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
# H3 (results/H3-tracker-corpus-v2-20260929/BRIEF.md). Training wording widened by two phrasings per turn in every role —
# not only where H2 missed — written before training and without reading a model's output; and a FRESH held-out suite,
# `eval` of suite h3: new worlds and wording that neither the training nor H2's eval uses (gate S5). H2's files and
# wording are untouched, so H2 reproduces from them.
EXTRA_H3 = {
    "developer": [["{key}, please.", "I need the details of {key}."], ["Mark it {to_h}.", "It can go to {to_h} now."],
                  ["{h}h on it, please log it.", "Add {h} hours to its worklog."],
                  ["Who's responsible for its component?", "Find the owner of that issue's component."],
                  ["Comment: {note}", "Please write on it: {note}"]],
    "lead": [["New bug: {summary}", "Log a bug for this: {summary}"], ["{person} should take it.", "Put {person} on it."],
             ["Remind me of the critical-bug rule.", "What's the triage time for a critical bug?"],
             ["Sprint board, please.", "Where does the sprint stand?"], ["Open the bug you filed again.", "Show me that bug again."]],
    "qa": [["{key}, please.", "I'm testing {key} — show it."], ["All checks pass, move it to done.", "Done — transition it."],
           ["Where do tests need to pass for an issue to be done?", "What's the testing requirement in the definition of done?"],
           ["Comment: {note}", "Please write on it: {note}"]],
}
EVAL_H3 = {
    "developer": [["Look up {key} for me.", "Details on {key}?"], ["Transition it to {to_h}.", "Bump it to {to_h}."],
                  ["Book {h} hours on it.", "Track {h}h against it."], ["Who do I ask about its component?", "Its component — who owns it?"],
                  ["Annotate it: {note}", "Drop a comment: {note}"]],
    "lead": [["Raise a bug: {summary}", "Please report a bug — {summary}"], ["Let {person} own it.", "Route it to {person}."],
             ["How do we handle critical bugs?", "Critical bugs — what's the policy?"], ["Board status?", "How is the current sprint going?"],
             ["Bring back the bug you just filed.", "Let me see that bug once more."]],
    "qa": [["Fetch {key}.", "What does {key} look like?"], ["QA passed, it's done.", "Close it out as done."],
           ["Where should tests pass before we call it done?", "Done criteria for tests?"], ["Annotate it: {note}", "Remark on it: {note}"]],
}
SEED0_H3 = {"train": 500_000, "eval": 1_440_000}
OUT_H3 = Path(__file__).parent / "data_sessions_h3"
# H4 (results/H4-tracker-command-notes-20260930/BRIEF.md). A note whose text reads like an order — "ready for QA" — was
# taken as one: tr-s1 tried `issue_transition → qa` instead of commenting [ran] H3. Training keeps H3's wording and adds
# notes that sound like instructions; the fresh eval draws its notes from a DISJOINT pool of the same kind (gate S6) and
# its wording from a fifth set (S5). One unknown: the notes.
CMD_NOTES = {
    "train": ["move to done after the demo", "assign to Bruno next sprint", "close it if nobody objects",
              "reopen if it fails again", "log 2 more hours tomorrow", "set priority to high later",
              "please review before merging", "ready for QA"],
    "eval": ["ready for review", "mark as done once CI is green", "hand it to QA when merged",
             "transition after the release", "bump to in progress on Monday", "needs QA sign-off before done",
             "can be closed next week", "reassign to the lead if blocked"],
}
EVAL_H4 = {
    "developer": [["Can I see {key}?", "Show {key}, please."], ["Advance it to {to_h}.", "Shift it to {to_h}."],
                  ["Add {h} hours of work to it.", "Charge {h}h to it."], ["Who's the component owner for it?", "Who owns that component?"],
                  ["Leave this comment: {note}", "Comment on it with: {note}"]],
    "lead": [["Report this bug: {summary}", "New defect — {summary}"], ["Make {person} the assignee.", "{person} takes it."],
             ["What's the critical bug rule?", "How fast do critical bugs get triaged?"], ["Current sprint board?", "Show the sprint."],
             ["Reopen view of the bug you created.", "Display that new bug again."]],
    "qa": [["Bring up {key}.", "Look at {key} with me."], ["Passed QA, set to done.", "It's verified, done."],
           ["Tests must pass where, for done?", "What does done require for tests?"], ["Leave this comment: {note}", "Comment on it with: {note}"]],
}
SEED0_H4 = {"train": 500_000, "eval": 1_900_000}
OUT_H4 = Path(__file__).parent / "data_sessions_h4"


def wording(kind: str, split: str, suite: str = "h2") -> list[list[str]]:
    if suite == "h4":
        return wording(kind, "train", "h3") if split == "train" else EVAL_H4[kind]
    if suite == "h3":
        return [a + b for a, b in zip(P[kind]["train"], EXTRA_H3[kind])] if split == "train" else EVAL_H3[kind]
    return P[kind][split]


NOTES = ["ready for QA", "verified on staging", "needs a follow-up ticket", "tested with a large account", "looks good to me"]
SUMMARIES = ["Login loops on Safari", "Invoice PDF shows the wrong total", "Search misses accented names",
             "Password reset email never arrives", "Export hangs after 10,000 rows"]


def _pick(conn, org: str, where: str) -> dict | None:
    r = conn.execute(f"select * from issues where org_id=? and {where} order by key", (org,)).fetchall()
    return dict(r[0]) if r else None


def session(seed: int, split: str, kind: str, suite: str = "h2") -> dict | None:
    r = random.Random(seed)
    conn = db.world(seed)
    org = r.choice([o for o, _, _ in db.ORGS])
    notes = (NOTES + CMD_NOTES["train"] if split == "train" else CMD_NOTES["eval"]) if suite == "h4" else NOTES
    fill = {"h": r.choice([1, 2, 3, 4]), "note": r.choice(notes), "summary": r.choice(SUMMARIES)}
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
             for options, (tool, args, dep) in zip(wording(kind, split, suite), plan)]
    return {"session_id": f"tr-{split}-{seed}", "split": split, "kind": kind, "role": kind, "org": org,
            "user_id": f"{kind}-{org}", "world_seed": seed, "turns": turns}


def build(split: str, suite: str = "h2") -> list[dict]:
    out, i = [], 0
    while len(out) < N[split]:
        s = session({"h3": SEED0_H3, "h4": SEED0_H4}.get(suite, SEED0)[split] + i, split, KINDS[len(out) % len(KINDS)], suite)
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


def turn_right_h3(calls: list[dict], turn: dict) -> bool:
    """H3's scorer, fixed in its brief before the run. As `turn_right`, except a turn that needs one statement of a page
    (`page#anchor`) is right when a page read RETURNED that statement: H2 scored reading the whole page as a miss while the
    statement sat in what was read — a check that could fail while the capability worked [ran] H2."""
    ref = str(turn["args"].get("ref", ""))
    if turn["tool"] == "page_read" and "#" in ref:
        return any(c.get("tool") == "page_read" and "error" not in c and "denied" not in c
                   and f"[{ref.lower()}]" in str(c.get("result", "")).lower() for c in calls)
    return turn_right(calls, turn)


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
         capture: list | None = None, scorer=None) -> list[dict]:
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
        out.append({"request": t["request"], "tool": t["tool"], "depends": t["depends"], "right": (scorer or turn_right)(ev["calls"], t),
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


def _templates(kind_split) -> set[str]:
    return {o for opts in kind_split for o in opts}


def main() -> int:
    import sys
    argv = sys.argv[1:]
    suite = argv[argv.index("--suite") + 1] if "--suite" in argv else "h2"
    out = {"h3": OUT_H3, "h4": OUT_H4}.get(suite, OUT)
    out.mkdir(exist_ok=True)
    if "--harness-corpus" in argv:
        train = [json.loads(l) for l in (out / "train.jsonl").read_text().splitlines() if l.strip()]
        rows = []
        # H1's lesson [ran]: a member trained only on prompts that carry the tool block calls no tool without it (0/60).
        # A third of the sessions are rendered WITHOUT the block, so the member learns its tools by name, not by reading.
        # H2 chose that third by `j % 3`, which is also how the roles rotate: every block-less row was QA's (400 of 400),
        # and the member learned block-less exactly the role it was shown [ran] H2. H3 takes a third of EACH role.
        noblock = (lambda j: (j // len(KINDS)) % 3 == 2) if suite in ("h3", "h4") else (lambda j: j % 3 == 2)
        for j, s in enumerate(train):
            cap: list = []
            play(s, harness_oracle(s), harness=True, tool_block=not noblock(j), capture=cap)
            rows += [{"case_id": f"{s['session_id']}-t{i}", "kind": s["kind"], "turn": i, "depends": s["turns"][i]["depends"],
                      "messages": [{"role": "system", "content": c["system"]}, {"role": "user", "content": c["user"]},
                                   {"role": "assistant", "content": c["walk"]}]} for i, c in enumerate(cap)]
        (out / "train_harness.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        bare = [r for r in rows if "The following tools are available" not in r["messages"][1]["content"]]
        g = {"rows": len(rows), "rows_without_tool_block": len(bare),
             "rows_without_tool_block_by_kind": {k: sum(r["kind"] == k for r in bare) for k in KINDS},
             "rows_with_get": sum("<get>" in r["messages"][2]["content"] for r in rows),
             "rows_with_put": sum("<put>" in r["messages"][2]["content"] for r in rows)}
        (out / "gate_harness.json").write_text(json.dumps(g, indent=1))
        print(f"[tracker] harness corpus {g}", flush=True)
        return 0
    train, evals = build("train", suite), build("eval", suite)
    g = gate(train, evals)
    if suite in ("h3", "h4"):
        # S5: the fresh suite shares no wording with the training, nor with an earlier eval (it is not a set re-asked)
        ev = _templates(o for k in KINDS for o in (EVAL_H3 if suite == "h3" else EVAL_H4)[k])
        seen = _templates(o for k in KINDS for o in wording(k, "train", suite)) | _templates(o for k in KINDS for o in P[k]["eval"])
        if suite == "h4":
            seen |= _templates(o for k in KINDS for o in EVAL_H3[k])
        g["S5_eval_wording_not_fresh"] = len(ev & seen)
        g["passed"] = g["passed"] and not g["S5_eval_wording_not_fresh"]
    if suite == "h4":
        # S6: no eval note is a training note — the member must comment a note it has never seen, of the kind it has
        g["S6_eval_note_in_train"] = len(set(CMD_NOTES["eval"]) & (set(NOTES) | set(CMD_NOTES["train"])))
        g["eval_comment_turns"] = sum(t["tool"] == "issue_comment" for s in evals for t in s["turns"])
        g["passed"] = g["passed"] and not g["S6_eval_note_in_train"]
    for name, rows in (("train", train), ("eval", evals)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (out / "gate.json").write_text(json.dumps(g, indent=1))
    print(f"[tracker] sessions gate ({suite}) {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
