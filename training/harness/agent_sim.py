"""An OpenClaw-shaped agent doing one person's morning triage, through the proxy.

WHAT THIS EXERCISES THAT NOTHING ELSE HAS. Every measurement in this project has been
a single turn — P27 arm 3 explicitly so — and `docs/SERVING.md` names the multi-turn
loop as *assembled and not measured*. This is the loop: the agent sends `tools=[…]`,
reads `tool_calls`, executes them, sends the results back as `role: "tool"`, and does
it again until the model stops asking. **It is the first time the whole path runs.**

IT IS SHAPED LIKE A CLIENT, NOT LIKE A TEST. It speaks only OpenAI: a base URL, a
model name, `tools`, `tool_calls`, `role: "tool"`. Anything it needed that the
protocol does not provide would be a gap between this project and a real runtime, and
there is one, named below.

THE ONE PLACE THE CLIENT KNOWS ITS OWN TOOLS. P28's arity convention renders a
single-parameter function positionally, so the model writes
`<thread_history>thr-000</thread_history>` and the shim hands back `{"_": "thr-000"}`.
Mapping `_` onto the parameter's real name needs the schema — and **the client owns
its schema**, so it happens here rather than in the converter, which stays domain-free.

    python3 -m training.harness.agent_sim --base-url http://127.0.0.1:8001/v1 \\
        --model kernel --n 12
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request

from pathlib import Path

from training.email.inbox import generate
from training.email.tools import SCHEMA, ToolError, answer

SYSTEM = ("You are triaging one person's inbox. For each message decide whether it "
          "is IMPORTANT. A message is important when at least two of these hold: it "
          "continues a thread the user wrote in; it is addressed to the user "
          "directly; it asks the user for something; the sender is a frequent "
          "correspondent. An automated message is never important. Use the tools to "
          "find out — the listing does not say. When you are sure, answer with one "
          "line: IMPORTANT or NOT IMPORTANT.")


# THE INBOX TOOL BEHIND A RUNTIME'S NAME. OpenClaw offers an MCP tool as
# `lora-inbox__thread_history` **[ran]** P43; the proxy renames it to the member's tag
# on the way in and back to the caller's name on the way out, so what this client
# receives in `tool_calls` is its own prefixed name. The last namespace segment is the
# inbox tool — the same structural rule `tool_calls.prune` applies, keyed on
# punctuation and never on a tool list.
NAMESPACE = re.compile(r"__|[./:]")


def inbox_tool(name: str) -> str:
    return NAMESPACE.split(name)[-1]


def _param_name(tool: str) -> str:
    tool = inbox_tool(tool)
    for t in SCHEMA:
        fn = t["function"]
        if fn["name"] == tool:
            req = (fn["parameters"].get("required") or
                   sorted(fn["parameters"]["properties"]))
            return req[0]
    return "id"


def _body(tool: str, arguments) -> str:
    """`tool_calls` arguments back into the string the tool reads."""
    a = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    if list(a) == ["_"]:
        return f"{_param_name(tool)}={a['_']}"
    return "; ".join(f"{k}={v}" for k, v in a.items())


def chat(base_url: str, key: str | None, payload: dict, timeout: int = 300) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def triage_one(base_url, key, model, inbox, msg, max_turns, max_tokens,
               logprobs: int = 0, tools: list[dict] | None = None):
    """One message, one conversation, as many tool turns as the model asks for.

    `logprobs` > 0 asks the server for that many `top_logprobs` and reads a
    confidence off the FINAL turn — the one where the model stops calling tools and
    answers. P44 measured this quantity in the tool-free configuration; P46 then
    showed that configuration has almost no room in it, because the listing alone
    carries one bit and a constant cannot rank **[ran]**. With the tools every fact
    the definition needs is recoverable, so this is where a confidence can be worth
    something — and it could not be read at all until now.

    THE FIRST TOKEN HAS TO BE THE DECISION, AND IT MIGHT NOT BE. `IMPORTANT` and
    `NOT IMPORTANT` differ at the first token, which is why the mass there is the
    whole verdict — but a model that opens with prose puts a word there instead, and
    reading that as a confidence would measure phrasing. `confidence` comes back
    `None` in that case and `answered_first` says so, so the share is countable and
    a run can be declared void on it rather than quietly averaging it in.
    """
    listing = (f"Message {msg['id']} in thread {msg['thread_id']}\n"
               f"From: {msg['from_name']} <{msg['from']}>\n"
               f"Subject: {msg['subject']}\n"
               f"Preview: {msg['preview']}\n\n"
               "Is this important?")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": listing}]
    calls = refused = 0
    asked: list[dict] = []
    for _ in range(max_turns):
        try:
            payload = {"model": model, "messages": messages,
                       "tools": SCHEMA if tools is None else tools,
                       "temperature": 0, "max_tokens": max_tokens}
            if logprobs:
                payload |= {"logprobs": True, "top_logprobs": logprobs}
            out = chat(base_url, key, payload)
        except urllib.error.HTTPError as e:
            return {"verdict": None, "error": e.read()[:160].decode("utf-8", "replace"),
                    "calls": calls, "refused": refused, "turns": len(messages)}
        except Exception as e:
            return {"verdict": None, "error": repr(e)[:160], "calls": calls,
                    "refused": refused, "turns": len(messages)}

        m = (out.get("choices") or [{}])[0].get("message") or {}
        tcs = m.get("tool_calls") or []
        messages.append({k: v for k, v in m.items()
                         if k in ("role", "content", "tool_calls")} or
                        {"role": "assistant", "content": ""})
        if not tcs:
            text = (m.get("content") or "").upper()
            verdict = (True if "NOT IMPORTANT" not in text and "IMPORTANT" in text
                       else False if "NOT IMPORTANT" in text else None)
            conf = None
            if logprobs:
                from training.harness.confidence import confidence_from
                _said, conf, _why = confidence_from(out)
            return {"verdict": verdict, "calls": calls, "refused": refused,
                    "confidence": conf,
                    # Read where the failure happens, not where it surfaces: a
                    # confidence that is None because the model preambled is a
                    # different fact from one that is None because the server sent
                    # no logprobs, and only the first is about the model.
                    # `said` IS THE WRONG VARIABLE HERE and the test caught it:
                    # `confidence_from` reads the verdict from the TEXT, so
                    # "Based on the thread history, this is IMPORTANT" parses fine
                    # while its first token is `Based`. The confidence is what has
                    # to be None-checked, because it is the thing read at position
                    # zero **[ran]** 2026-09-16.
                    "answered_first": None if not logprobs else conf is not None,
                    "turns": len(messages), "asked": asked,
                    # THE TRANSCRIPT, FOR THE SAME REASON fluids_sim keeps its chain:
                    # a routing decision is made per case, and a record holding only
                    # the last line cannot be routed after the fact [ran] P40.
                    "transcript": [{"role": x.get("role"), "content": x.get("content"),
                                    "tool": x.get("name")} for x in messages],
                    "text": (m.get("content") or "")[:200]}
        for tc in tcs:
            fn = tc["function"]
            calls += 1
            try:
                result = answer(inbox, inbox_tool(fn["name"]),
                                _body(fn["name"], fn["arguments"]))
            except ToolError as e:
                refused += 1
                # WHAT WAS ASKED FOR, NOT ONLY THAT THE ASK FAILED. P34 measured a
                # protocol adapter taking this base from 0 tool calls to 127 with
                # 127 refused — and the record could not say whether it asked for a
                # tool this suite does not have or asked correctly with malformed
                # arguments. Those two call for different training, and the
                # difference was invisible [ran] 2026-09-14.
                asked.append({"name": fn["name"],
                              "args": str(fn.get("arguments"))[:120],
                              "error": str(e)[:120]})
                result = f"ERROR: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.get("id"),
                             "name": fn["name"], "content": result})
    return {"verdict": None, "calls": calls, "refused": refused,
            "turns": len(messages), "asked": asked,
            "text": "(ran out of turns)"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default="kernel")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=717171)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--out", default="triage_results.json")
    # P47. The confidence at the END of a tool chain, which P46 says is where the
    # only remaining room is: the listing carries one bit, but `thread_history` and
    # `sender_stats` carry the two facts the definition needs, so with the tools the
    # ceiling collapses to the oracle floor.
    # THE SURFACE A REAL RUNTIME SENDS, replayed. P43 measured OpenClaw offering 54
    # tools to an expert trained on 3, and the expert calling none; `--tools-json`
    # hands this client that surface (or any other) instead of the inbox three, so
    # the proxy's `--prune` can be bought as an arm rather than assumed.
    ap.add_argument("--tools-json", default=None,
                    help="a JSON list of OpenAI tool schemas to offer instead of the inbox three")
    ap.add_argument("--logprobs", type=int, default=0,
                    help="ask for N top_logprobs and score the calibration too")
    args = ap.parse_args()

    tools = json.loads(Path(args.tools_json).read_text()) if args.tools_json else None
    if tools is not None:
        print(f"[sim] offering {len(tools)} tools from {args.tools_json}", flush=True)
    inbox = generate(args.n, args.seed)
    truth = [m["_truth"] for m in inbox["messages"]]
    # THE MAJORITY-CLASS BAR, PRINTED BEFORE THE RUN. Answering "not important" to
    # everything scores this, and a system below it has learned nothing.
    bar = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    # AND THE BAR THAT MATTERS. Spotting `noreply@` is free and a human does it at a
    # glance, so the whole-inbox number rewards the easy half. The question the tools
    # exist for is which HUMAN message matters, and on that subset the best rule
    # readable from the listing scores exactly the majority class — the tools have
    # all of the remaining margin [ran] `tests/test_email.py`.
    human = [m for m in inbox["messages"] if not m["_facts"]["automated"]]
    ht = [m["_truth"] for m in human]
    hbar = max(sum(ht), len(ht) - sum(ht)) / max(len(ht), 1)
    print(f"[sim] {args.n} messages · {sum(truth)} important · "
          f"majority-class bar {bar:.3f}", flush=True)
    print(f"[sim] of those, {len(human)} are human · bar on them {hbar:.3f} — "
          f"this is where the tools decide", flush=True)

    # RESUMED, NOT RESTARTED. P47 was lost twice: once to a KeyError after all 475
    # cases had been scored, and once to a Colab session that stopped answering at
    # 260 of 475 **[ran]** 2026-09-16. The first fix moved the summary after the
    # write and did not help the second, because this loop still wrote **once, at
    # the end**. CLAUDE.md says to persist every result as it lands; a runner that
    # holds 475 cases in memory and writes at the finish does not.
    done: dict[str, dict] = {}
    if Path(args.out).exists():
        try:
            prev = json.loads(Path(args.out).read_text())
            done = {r["id"]: r for r in prev.get("records", []) if "id" in r}
        except Exception as e:
            print(f"[sim] could not reuse {args.out}: {e!r}", flush=True)
    if done:
        print(f"[sim] resuming — {len(done)} of {args.n} already scored", flush=True)

    recs, t0 = [], time.time()

    def checkpoint():
        """Everything scored so far, in the shape the summary will have."""
        ok_ = sum(r["correct"] for r in recs)
        Path(args.out).write_text(json.dumps(
            {"model": args.model, "n": args.n, "correct": ok_,
             "partial": len(recs) < args.n, "records": recs}, indent=2))

    for i, msg in enumerate(inbox["messages"], 1):
        if msg["id"] in done:
            recs.append(done[msg["id"]])
            continue
        r = triage_one(args.base_url, args.api_key, args.model, inbox, msg,
                       args.max_turns, args.max_tokens, args.logprobs, tools)
        r.update({"id": msg["id"], "truth": msg["_truth"],
                  "correct": r["verdict"] == msg["_truth"]})
        recs.append(r)
        # A DEAD SESSION SHOULD COST MINUTES, NOT THE RUN. 25 is roughly three
        # minutes of scoring at the rate measured in P43.
        if len(recs) % 25 == 0:
            checkpoint()
        if i % 4 == 0:
            ok = sum(x["correct"] for x in recs)
            # ERRORS IN THE PROGRESS LINE. P59's off-arm failed every request on
            # context length and read as `correct 0 calls 0` — a floor — until the
            # records were opened **[ran]** 2026-09-17. The same lesson as P51's 400s.
            print(f"  [sim] {i}/{args.n} correct {ok} calls "
                  f"{sum(x['calls'] for x in recs)} errors "
                  f"{sum(1 for x in recs if x.get('error'))}", flush=True)

    ok = sum(r["correct"] for r in recs)
    undecided = sum(r["verdict"] is None for r in recs)
    calls = sum(r["calls"] for r in recs)
    refused = sum(r["refused"] for r in recs)
    hum_ids = {m["id"] for m in human}
    hrecs = [r for r in recs if r["id"] in hum_ids]
    hok = sum(r["correct"] for r in hrecs)
    summary = {"model": args.model, "n": args.n, "correct": ok,
               "accuracy": round(ok / args.n, 4), "majority_class_bar": round(bar, 4),
               "human_n": len(hrecs), "human_correct": hok,
               "human_accuracy": round(hok / max(len(hrecs), 1), 4),
               "human_majority_class_bar": round(hbar, 4),
               "undecided": undecided, "calls": calls, "refused": refused,
               "errors": sum(1 for r in recs if r.get("error")),
               "seconds": round(time.time() - t0, 1), "records": recs}

    # WRITTEN BEFORE THE SUMMARY MATH, NOT AFTER. The first version computed the
    # calibration block first and a `KeyError` in it threw away 475 cases of rented
    # L4 — the expensive part had finished and the file had not been opened yet
    # **[ran]** 2026-09-16. CLAUDE.md already says to persist every result as it
    # lands; this is the line that makes that true for this runner.
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)

    if args.logprobs:
      try:
        from training.harness.bar import calibration
        from training.harness.ceiling import room
        for label, rs in (("all", recs), ("human", hrecs)):
            # ONLY THE CASES WHERE THE FIRST TOKEN WAS THE DECISION. A model that
            # opens with prose puts a word where the verdict should be, and reading
            # that as a confidence measures phrasing. The share is reported, and the
            # brief voids the run above 20%.
            usable = [r for r in rs if r.get("confidence") is not None]
            read_rate = len(usable) / max(len(rs), 1)
            if not usable:
                summary[f"calibration_{label}"] = {"n": 0, "read_rate": 0.0,
                                                   "void": True}
                continue
            c = calibration([r["confidence"] for r in usable],
                            [bool(r["correct"]) for r in usable])
            # WITH THE TOOLS THE CEILING IS THE ORACLE FLOOR, because every fact the
            # definition needs is recoverable — so the measured gap IS the room, and
            # `room()` is called with a ceiling of 0 rather than left to a reader.
            # `calibration()` returns `aurc_oracle_floor` and `aurc_gap`. The
            # first draft invented `aurc_floor` and recomputed a field that was
            # already there; both mistakes came from writing against a remembered
            # shape instead of the real one.
            c |= {"read_rate": round(read_rate, 4),
                  "void": read_rate < 0.80,
                  "room": room(c["aurc_gap"], 0.0)}
            summary[f"calibration_{label}"] = c
            print(f"[conf] {label:5} n={len(usable)} read={read_rate:.3f} "
                  f"ece={c['ece']:.4f} brier={c['brier']:.4f} "
                  f"aurc={c['aurc']:.4f} floor={c['aurc_oracle_floor']:.4f} "
                  f"gap={c['aurc_gap']:.4f}", flush=True)
        # The gate lives with the run that pre-registered it, not inline here.
        from training.harness.tool_confidence import arm_verdict
        g = (summary.get("calibration_human") or {})
        summary["verdict"] = arm_verdict(g.get("aurc_gap") if g.get("n") else None,
                                         g.get("read_rate", 0.0))
        print(f"[conf] {summary['verdict']}", flush=True)
      except Exception as e:
        # A SUMMARY THAT CANNOT BE COMPUTED IS NOT A RUN THAT DID NOT HAPPEN. The
        # records are already on disk; this says so instead of exiting non-zero and
        # letting the caller record "produced nothing".
        summary["calibration_error"] = repr(e)[:300]
        print(f"[conf] calibration failed, records kept: {e!r}", flush=True)
      with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n{ok}/{args.n} = {ok/args.n:.3f} against a majority-class bar of {bar:.3f}")
    print(f"on the {len(hrecs)} human messages: {hok}/{len(hrecs)} = "
          f"{hok/max(len(hrecs),1):.3f} against {hbar:.3f} — the number that counts")
    print(f"{calls} tool calls, {refused} refused, {undecided} never decided")
    print("A system below the bar has not learned the task; it has learned to guess.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
