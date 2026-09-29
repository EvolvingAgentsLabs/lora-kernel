r"""Multi-turn sessions for the distributor — MT0's suite (results/MT0-multiturn-baseline-20260929/BRIEF.md) and, later,
the workflow harness's (docs/review/harness-workflow-kv.md).

WHY. Every demo so far is one turn. A real conversation refers back: "move it to dock 5", "file a return on the same
order", "reorder the one that is lowest". The gateway reads only the last request, so today "it" has no referent. This
suite makes that measurable: sessions of two or three turns by one user in one role, where the right call of a
**dependent** turn can only be written from an earlier turn — an id the user named before, or a value an earlier tool
returned. One session type ends with an **independent** turn, the control.

    dispatch         where is order X?            → and its delivery note?          (→ is it delivered yet?)
    customer_service status of order X?           → file a claim about that order     (the description names X)
    receiving        put order X on dock A         → move it to dock B
    purchasing       show me the stock             → reorder N of whichever is lowest  (the item from the result)
    claims_returns   which returns are open?       → open another on the same order    (the order from the result)
    it               log a ticket at A: D          → list the open tickets             (independent — the control)

Each turn is checked mechanically against the call it must make (tool and arguments), on the session's own synthetic
world (`generate_turns._world`, seeds apart from every corpus). Wording is split train / eval.

    python -m examples.distributor.generate_sessions      # data_sessions/{train,eval}.jsonl, gate.json
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from examples.distributor import generate_turns as gt

OUT = Path(__file__).parent / "data_sessions"
SEED0 = {"train": 400_000, "eval": 960_000}
N = {"train": 300, "eval": 60}
KINDS = ("dispatch", "customer_service", "receiving", "purchasing", "claims_returns", "it")

P = {  # (first turn, follow-ups) per session kind and split; {oid} {d1} {d2} {qty} {reason} {area} {desc}
    "dispatch": {"train": (["Where is order {oid}?", "Status of order {oid}, please."],
                           ["And the delivery note on it?", "What does its delivery note say?"],
                           ["Is it delivered yet?", "Has it arrived?"]),
                 "eval": (["Can you check where order {oid} is?", "Where does order {oid} stand at the moment?"],
                          ["What note did the driver leave on that one?", "Show me its delivery note."],
                          ["So is it delivered now?", "Did that one arrive?"])},
    "customer_service": {"train": (["What's the status of order {oid}?", "Look up order {oid} for me."],
                                   ["The customer says it arrived crushed — file a claim about that order.",
                                    "Open a claim for that order: two boxes are missing."]),
                         "eval": (["Where is order {oid} right now?", "Check order {oid}, please."],
                                  ["That one came damaged, please file a claim for it.",
                                   "The seal on that order was broken — log a claim about it."])},
    "receiving": {"train": (["Put order {oid} on dock {d1}.", "Assign dock {d1} to order {oid}."],
                            ["Move it to dock {d2} instead.", "Actually, switch it to dock {d2}."]),
                  "eval": (["Send order {oid} to dock {d1}, please.", "Order {oid} should unload at dock {d1}."],
                           ["Change that to dock {d2}.", "Put it on dock {d2} instead."])},
    "purchasing": {"train": (["Show me our stock.", "What's our inventory?"],
                             ["Reorder {qty} of whichever item is lowest.", "Top up the lowest one by {qty}."]),
                   "eval": (["How is the stock looking?", "List what we have in stock."],
                            ["Order {qty} more of the item we have least of.", "Restock the smallest one with {qty} units."])},
    "claims_returns": {"train": (["Which returns are open?", "List the returns."],
                                 ["Open another return on the same order: {reason}.", "File a new return for that order — {reason}."]),
                       "eval": (["Show me the returns on file.", "What returns do we have?"],
                                ["Log one more return on that order: {reason}.", "Create another return for the same order: {reason}."])},
    "it": {"train": (["Log a maintenance ticket for {area}: {desc}", "Open a ticket — {area}, {desc}"],
                     ["List the open tickets.", "Which maintenance tickets are open?"]),
           "eval": (["File a maintenance request at {area}: {desc}", "Maintenance needed in {area}: {desc}"],
                    ["Show me the open tickets.", "What maintenance is pending?"])},
}


def _world_facts(conn, org: str) -> dict:
    mine = [r["id"] for r in conn.execute("select id from orders where org_id=?", (org,))]
    stock = [(r["item"], r["qty"]) for r in conn.execute("select item, qty from stock where org_id=?", (org,))]
    ret = conn.execute("select order_id from returns where org_id=?", (org,)).fetchone()
    return {"mine": mine, "stock": stock, "return_order": ret["order_id"] if ret else None}


def session(seed: int, split: str, kind: str) -> dict:
    r = random.Random(seed)
    conn = gt._world(seed)
    org = r.choice(gt.ORGS)
    f = _world_facts(conn, org)
    first, *follows = P[kind][split]
    oid = r.choice(f["mine"])
    d1, d2 = r.sample(range(1, 7), 2)
    qty = r.choice([20, 40, 50, 60, 80, 120])
    reason, area, desc = r.choice(gt.REASONS), r.choice(gt.AREAS), r.choice(gt.PROBLEMS)
    fill = {"oid": oid, "d1": d1, "d2": d2, "qty": qty, "reason": reason, "area": area, "desc": desc}
    lowest = min(f["stock"], key=lambda x: x[1])[0]
    plan = {
        "dispatch": [("order_status", {"order_id": oid}), ("delivery_status", {"order_id": oid}), ("order_status", {"order_id": oid})],
        "customer_service": [("order_status", {"order_id": oid}), ("claim_create", {"description~": str(oid)})],
        "receiving": [("dock_assign", {"order_id": oid, "dock_number": d1}), ("dock_assign", {"order_id": oid, "dock_number": d2})],
        "purchasing": [("stock_read", {}), ("stock_reorder", {"item": lowest, "qty": qty})],
        "claims_returns": [("return_list", {}), ("return_create", {"order_id": f["return_order"], "reason~": reason.split()[0]})],
        "it": [("maintenance_create", {"area": area, "description~": desc.split()[1]}), ("maintenance_list", {})],
    }[kind]
    n_turns = 3 if kind == "dispatch" and r.random() < 0.5 else 2
    phrasings = [first, *follows][:n_turns]
    turns = []
    for i, (options, (tool, args)) in enumerate(zip(phrasings, plan[:n_turns])):
        turns.append({"request": r.choice(options).format(**fill), "tool": tool, "args": args,
                      "depends": i > 0 and kind != "it"})
    return {"session_id": f"{split}-{seed}", "split": split, "kind": kind, "role": kind, "org": org,
            "user_id": f"{kind}-{org}", "world_seed": seed, "turns": turns}


def _norm(v) -> str:
    return str(v).strip().strip("'\"").lower()


def call_matches(call: dict, tool: str, args: dict) -> bool:
    """The call is the one the turn needs: its tool, not refused, and every argument — `key~` means the argument must
    CONTAIN the value (a free-text description naming the order), otherwise equal after normalising."""
    if call.get("tool") != tool or "denied" in call or "error" in call:
        return False
    got = {k: _norm(v) for k, v in (call.get("args") or {}).items()}
    for k, want in args.items():
        if k.endswith("~"):
            if _norm(want) not in got.get(k[:-1], ""):
                return False
        elif got.get(k) != _norm(want):
            return False
    return True


def turn_right(calls: list[dict], turn: dict) -> bool:
    return any(call_matches(c, turn["tool"], turn["args"]) for c in calls)


def build(split: str) -> list[dict]:
    return [session(SEED0[split] + i, split, KINDS[i % len(KINDS)]) for i in range(N[split])]


def oracle_generate(sess: dict):
    """A scripted model that knows the plan: per turn, the gold call, then the result restated (grounded)."""
    state = {"turn": 0}

    def generate(system, user, close, history=None):
        turn = sess["turns"][len([m for m in (history or []) if m["role"] == "user"])]
        args = {k.rstrip("~"): (f"order {v}" if k == "description~" and v.isdigit() else v) for k, v in turn["args"].items()}
        if turn["tool"] == "return_create":
            args["reason"] = next(x for x in gt.REASONS if x.startswith(turn["args"]["reason~"]))
        if turn["tool"] == "maintenance_create":
            args["description"] = next(x for x in gt.PROBLEMS if turn["args"]["description~"] in x)

        def gen(prefix: str) -> str:
            if "</" not in prefix:
                return gt._tag(turn["tool"], args)
            return gt._answer("write" if turn["tool"].endswith(("_create", "_assign", "_reorder")) else "read",
                              prefix.rsplit("= ", 1)[1].strip())
        return gen, lambda: {"prompt_tokens": 0, "completion_tokens": 0}
    return generate


# THE WORKFLOW HARNESS (docs/review/harness-workflow-kv.md): what each first turn stores for later steps, and which key a
# dependent turn fetches — the member learns these from the corpus; the gateway only serves `get` / `put`.
PUTS = {"dispatch": "order", "customer_service": "order", "receiving": "order", "claims_returns": "order",
        "purchasing": "lowest_item"}
WORKFLOWS = Path(__file__).parent / "workflows"


def workflows() -> dict:
    from examples.common.opmemory import Workflow
    return {f.stem: Workflow.load(f) for f in sorted(WORKFLOWS.glob("*.toml"))}


def _stored_value(sess: dict, turn_i: int) -> str | None:
    """What the first turn stores: the order it is about, or the lowest item its stock result shows."""
    t = sess["turns"][0]
    key = PUTS.get(sess["kind"])
    if not key or turn_i != 0:
        return None
    if key == "lowest_item":
        return str(sess["turns"][1]["args"]["item"]) if len(sess["turns"]) > 1 else None
    if sess["kind"] == "claims_returns":
        return str(sess["turns"][1]["args"]["order_id"]) if len(sess["turns"]) > 1 else None
    return str(t["args"]["order_id"])


def complaint(request: str) -> str:
    """What went wrong, out of a claim request: "…crushed — file a claim…" → "…crushed"; "…: two boxes are missing." →
    "two boxes are missing"."""
    text = request.split(": ", 1)[1] if ": " in request else request.split(" — ")[0].split(", please")[0]
    return text.strip().rstrip(".")


def harness_oracle(sess: dict):
    """The oracle's trajectory under the harness: a first turn makes its call and `put`s what a later step needs; a
    dependent turn `get`s it, then makes its call. The answer restates the call's result, as every corpus does."""
    key = PUTS.get(sess["kind"])
    turn_no = {"i": -1}

    def generate(system, user, close, history=None):
        turn_no["i"] += 1
        i = turn_no["i"]
        turn = sess["turns"][i]
        args = {k.rstrip("~"): (f"order {v}" if k == "description~" and str(v).isdigit() else v) for k, v in turn["args"].items()}
        if turn["tool"] == "return_create":
            args["reason"] = next(x for x in gt.REASONS if x.startswith(turn["args"]["reason~"]))
        if turn["tool"] == "maintenance_create":
            args["description"] = next(x for x in gt.PROBLEMS if turn["args"]["description~"] in x)
        if turn["tool"] == "claim_create":                # a claim names the order (from the cache) AND what went wrong
            args["description"] = f"order {turn['args']['description~']}: {complaint(turn['request'])}"
        steps = []
        if turn["depends"] and key:
            steps.append(f"<get>{key}</get>")
        steps.append(gt._tag(turn["tool"], args))
        if (v := _stored_value(sess, i)) is not None:
            steps.append(f"<put>{key}={v}</put>")

        def gen(prefix: str) -> str:
            done = prefix.count("</")
            if done < len(steps):
                return steps[done]
            m = re.search(rf"</{turn['tool']}>= (.*?)(?=\n<|\Z)", prefix, re.S)
            result = m.group(1).strip() if m else ""
            return gt._answer("write" if turn["tool"].endswith(("_create", "_assign", "_reorder")) else "read", result)
        return gen, lambda: {"prompt_tokens": 0, "completion_tokens": 0}
    return generate


def play(sess: dict, generate, history: bool = False, harness: bool = False, tool_block: bool = True,
         capture: list | None = None) -> list[dict]:
    """One session through the gateway: each turn appended to the conversation, the reply shown appended after it.
    `harness=True` serves the operational memory and the role's workflow instead of the conversation; `capture` collects
    what the model was served per turn (system, user) and the walk it wrote — a corpus row."""
    from examples.common import tokens
    from examples.common.opmemory import OpMemory
    from examples.distributor import users
    from examples.school.gateway import Gateway
    users.register_all()
    served = {}

    def spy(system, user, close, history=None):
        served.update(system=system, user=user)
        return generate(system, user, close, history) if history else generate(system, user, close)
    gw = Gateway(gt._world(sess["world_seed"]), spy, org="distributor", history=history,
                 memory=OpMemory() if harness else None, workflows=workflows() if harness else None, tool_block=tool_block)
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
                    "calls": ev["calls"], "route": r["route"], "reply": r["reply"][:300], "walk": r["walk"][-400:],
                    "prompt_tokens": ev.get("prompt_tokens", 0), "completion_tokens": ev.get("completion_tokens", 0)})
        if capture is not None:
            capture.append({"system": served["system"], "user": served["user"], "walk": r["walk"]})
        messages.append({"role": "assistant", "content": r["reply"]})
    return out


def gate(train: list[dict], evals: list[dict]) -> dict:
    """S1 no eval wording in train · S2 no world shared with each other or with any corpus · S3 every turn solvable: the
    oracle, played through the gateway WITH history, gets every turn right · S4 the dependent turn cannot be read off
    its own request (the id or item it needs is not in it)."""
    from examples.distributor.generate_turns import EVAL_SEED0, TRAIN_SEED0
    ev_text = {t["request"] for s in evals for t in s["turns"]}
    corpus = set(range(TRAIN_SEED0, TRAIN_SEED0 + 700)) | set(range(EVAL_SEED0, EVAL_SEED0 + 70))
    seeds_t, seeds_e = {s["world_seed"] for s in train}, {s["world_seed"] for s in evals}
    bad_oracle = sum(not all(x.get("right") for x in play(s, oracle_generate(s), history=True)) for s in train + evals)

    def self_contained(t):
        need = [str(v) for k, v in t["args"].items() if not k.endswith("~") and k in ("order_id", "item")]
        return bool(need) and all(n.lower() in t["request"].lower() for n in need)
    g = {"S1_eval_wording_in_train": sum(t["request"] in ev_text for s in train for t in s["turns"]),
         "S2_shared_world": len(seeds_t & seeds_e) + len((seeds_t | seeds_e) & corpus),
         "S3_oracle_fails_a_turn": bad_oracle,
         "S4_dependent_turn_self_contained": sum(self_contained(t) for s in train + evals for t in s["turns"] if t["depends"]),
         "sessions": {"train": len(train), "eval": len(evals)},
         "turns": {"eval": sum(len(s["turns"]) for s in evals), "eval_dependent": sum(t["depends"] for s in evals for t in s["turns"])}}
    g["passed"] = all(v == 0 for k, v in g.items() if k[:1] == "S" and k[1].isdigit())
    return g


def harness_rows(sessions: list[dict]) -> tuple[list[dict], int]:
    """Every turn of every session, as the harness serves it, with the oracle's walk: (corpus rows, sessions not right)."""
    rows, bad = [], 0
    for s in sessions:
        cap: list = []
        res = play(s, harness_oracle(s), harness=True, capture=cap)
        ok = all(x.get("right") for x in res) and all(
            any(c["tool"] == "get" and "result" in c for c in x["calls"]) for x in res if x.get("depends") and PUTS.get(s["kind"]))
        bad += not ok
        rows += [{"case_id": f"{s['session_id']}-t{i}", "kind": s["kind"], "turn": i, "depends": s["turns"][i]["depends"],
                  "messages": [{"role": "system", "content": c["system"]}, {"role": "user", "content": c["user"]},
                               {"role": "assistant", "content": c["walk"]}]} for i, c in enumerate(cap)]
    return rows, bad


def write_harness_corpus() -> dict:
    """data_turns/train_harness.jsonl = M10's train_out.jsonl BYTE FOR BYTE + every turn of the 300 training sessions as
    the harness serves them. Gate H1: every oracle session right through the memory, every dependent turn fetched by key."""
    train = [json.loads(l) for l in (OUT / "train.jsonl").read_text().splitlines() if l.strip()]
    evals = [json.loads(l) for l in (OUT / "eval.jsonl").read_text().splitlines() if l.strip()]
    rows, bad_t = harness_rows(train)
    _, bad_e = harness_rows(evals)
    turns_dir = Path(__file__).parent / "data_turns"
    base = (turns_dir / "train_out.jsonl").read_bytes()
    (turns_dir / "train_harness.jsonl").write_bytes(base + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())
    g = {"H1_oracle_train_sessions_not_right": bad_t, "H2_oracle_eval_sessions_not_right": bad_e,
         "harness_rows": len(rows), "base_rows": base.count(b"\n"),
         "rows_with_get": sum("<get>" in r["messages"][2]["content"] for r in rows),
         "rows_with_put": sum("<put>" in r["messages"][2]["content"] for r in rows)}
    g["passed"] = g["H1_oracle_train_sessions_not_right"] == 0 and g["H2_oracle_eval_sessions_not_right"] == 0
    (OUT / "gate_harness.json").write_text(json.dumps(g, indent=1))
    return g


def main() -> int:
    import sys
    if "--harness-corpus" in sys.argv[1:]:
        g = write_harness_corpus()
        print(f"[sessions] harness corpus · gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    OUT.mkdir(exist_ok=True)
    train, evals = build("train"), build("eval")
    g = gate(train, evals)
    for name, rows in (("train", train), ("eval", evals)):
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (OUT / "gate.json").write_text(json.dumps(g, indent=1))
    print(f"[sessions] gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
