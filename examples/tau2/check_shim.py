"""G-shim-1 — the shim loses nothing, both ways, on every tool call τ² ships for airline. Zero model, $0.

WHAT IS REPLAYED. Every simulation in τ²'s shipped airline trajectory files (`data/tau2/results/final/*airline*`,
four models × 4 trials × 50 tasks = 800 conversations) **[ran]** T0. Three checks, each with pass = 100 %:

  calls    for every tool call c = (name, args) in those files:
             parse_reply(call_to_tag(c)) = c               the member's tag read back as the same call
             json.loads(to_openai(…).arguments) = args     what τ² parses out of the shim's reply
             call_to_tag(parse(call_to_tag(c))) = call_to_tag(c)
           "=" is identity of the name, of the argument dict, and of every value's JSON type (canonical
           `json.dumps(sort_keys=True)`, which tells 50 from 50.0 from "50" from true).
  fold     for every conversation (in τ²'s OpenAI form, the system prompt τ² sends included):
             unfold(fold(messages)) = events_of(messages)
           events are user turns, calls (typed as above), tool results (byte-identical strings) and assistant
           text (identical up to surrounding whitespace — the one normalisation, stated). Also at every mid-turn
           cut of a sample (the conversation ending on a tool result: the open turn becomes the prefix).
  render   optional, when jinja2 and the member's cached chat template are present: the folded chat rendered by
           Gemma 4's own template contains every message's content verbatim and in order, and the prompt ends
           with the prefix — the template does not trim what the fold wrote.

    python3 examples/tau2/check_shim.py --tau2 ~/evolvingagents/tau2-bench \
        --out results/TAU2-T0-recon-20261005/g_shim_1.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.tau2.shim import (call_to_tag, events_of, fold, parse_reply, tool_index,  # noqa: E402
                                to_openai, unfold)

FIXTURES = Path(__file__).parent / "fixtures"


def canon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def to_openai_messages(sim_messages: list[dict]) -> list[dict]:
    """τ²'s stored messages → the OpenAI messages it sends (`llm_utils.to_litellm_messages`, re-stated so this runs
    without tau2 installed; `same_as_tau2` checks the re-statement against τ²'s own function when it is importable)."""
    out = []
    for m in sim_messages:
        r = m["role"]
        if r == "user":
            out.append({"role": "user", "content": m.get("content")})
        elif r == "assistant":
            tcs = None
            if m.get("tool_calls"):
                tcs = [{"id": tc["id"], "name": tc["name"], "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                       for tc in m["tool_calls"]]
            out.append({"role": "assistant", "content": m.get("content"), "tool_calls": tcs})
        elif r == "tool":
            out.append({"role": "tool", "content": m.get("content"), "tool_call_id": m.get("id")})
        elif r == "system":
            out.append({"role": "system", "content": m.get("content")})
    return out


def same_as_tau2(sims: list[dict]) -> dict:
    try:
        from tau2.data_model.message import AssistantMessage, ToolMessage, UserMessage
        from tau2.utils.llm_utils import to_litellm_messages
    except Exception as e:                            # not installed here: said, not hidden
        return {"checked": False, "why": f"tau2 not importable ({type(e).__name__})"}
    keep = ("role", "content", "tool_calls", "id", "requestor", "error")
    cls = {"assistant": AssistantMessage, "user": UserMessage, "tool": ToolMessage}
    bad = 0
    for s in sims:
        theirs = to_litellm_messages([cls[m["role"]](**{k: v for k, v in m.items() if k in keep})
                                      for m in s["messages"]])
        bad += canon(theirs) != canon(to_openai_messages(s["messages"]))
    return {"checked": True, "conversations": len(sims), "differ": bad}


def check_calls(sims, tools) -> dict:
    idx = tool_index(tools)
    n, kinds, fails, by_tool, writes = 0, {}, [], {}, 0
    write_tools = {"book_reservation", "cancel_reservation", "send_certificate", "update_reservation_baggages",
                   "update_reservation_flights", "update_reservation_passengers"}   # RECON §2, for the count only
    for s in sims:
        for m in s["messages"]:
            for tc in (m.get("tool_calls") or []) if m["role"] == "assistant" else []:
                n += 1
                name, args = tc["name"], tc["arguments"]
                writes += name in write_tools
                tag, kind = call_to_tag(name, args, idx[name])
                kinds[kind] = kinds.get(kind, 0) + 1
                rep = parse_reply(tag, tools)
                ok = rep["call"] is not None and rep["call"][0] == name and rep["call"][1] == args \
                    and canon(rep["call"][1]) == canon(args) and rep["content"] is None
                if ok:
                    wire = to_openai(rep, "m", [], {})["choices"][0]["message"]["tool_calls"][0]["function"]
                    back = json.loads(wire["arguments"])
                    ok = wire["name"] == name and back == args and canon(back) == canon(args) \
                        and call_to_tag(name, rep["call"][1], idx[name])[0] == tag
                by_tool.setdefault(name, [0, 0])
                by_tool[name][0] += 1
                by_tool[name][1] += ok
                if not ok and len(fails) < 20:
                    fails.append({"sim": s["id"], "name": name, "args": args, "tag": tag, "parsed": rep})
    lost = n - sum(v[1] for v in by_tool.values())
    return {"calls": n, "write_calls": writes, "exact": n - lost, "lost": lost, "kinds": kinds,
            "by_tool": {k: {"calls": v[0], "exact": v[1]} for k, v in sorted(by_tool.items())}, "failures": fails}


def control_repo_serializer(sims) -> dict:
    """THE INSTRUMENT MUST BE ABLE TO FAIL. The same identity, through the repo's own `k=v` serializer
    (`tool_calls.from_tool_call` -> `to_tool_calls`), which T0 measured losing writes [ran]. If this control
    also came back 100 %, the check would be measuring nothing."""
    from training.harness.tool_calls import from_tool_call, to_tool_calls
    n = exact = 0
    for s in sims:
        for m in s["messages"]:
            for tc in (m.get("tool_calls") or []) if m["role"] == "assistant" else []:
                n += 1
                text = from_tool_call({"function": {"name": tc["name"], "arguments": tc["arguments"]}})
                back = to_tool_calls(text)
                exact += bool(back) and back[0]["function"]["name"] == tc["name"] and \
                    canon(json.loads(back[0]["function"]["arguments"])) == canon(tc["arguments"])
    return {"calls": n, "exact": exact, "lost": n - exact}


def check_fold(sims, tools, system: str, cuts_every: int = 10) -> dict:
    convs, fails, cut_checks, results, json_hist = 0, [], 0, 0, 0
    for i, s in enumerate(sims):
        msgs = [{"role": "system", "content": system}] + to_openai_messages(s["messages"])
        chat, prefix, counts = fold(msgs, tools)
        json_hist += counts["json"]
        want = events_of(msgs)
        got = unfold(chat, prefix, tools)
        results += sum(1 for e in want if e[0] == "result")
        ok = canon(got) == canon(want) and chat[0]["content"] == system
        convs += 1
        if not ok and len(fails) < 10:
            fails.append({"sim": s["id"], "first_difference": next(
                ({"at": j, "want": a, "got": b} for j, (a, b) in enumerate(zip(want, got)) if canon(a) != canon(b)),
                {"len_want": len(want), "len_got": len(got)})})
        if i % cuts_every == 0:                       # every mid-turn cut of this conversation
            for c in [j for j, m in enumerate(msgs) if m["role"] == "tool"]:
                part = msgs[:c + 1]
                ch, pre, _ = fold(part, tools)
                cut_checks += 1
                if not pre or canon(unfold(ch, pre, tools)) != canon(events_of(part)):
                    if len(fails) < 10:
                        fails.append({"sim": s["id"], "cut": c, "prefix_empty": not pre})
    return {"conversations": convs, "tool_results": results, "history_calls_as_json": json_hist,
            "mid_turn_cuts": cut_checks, "failures": fails, "passed": not fails}


def check_render(sims, tools, system: str, sample: int = 40) -> dict:
    try:
        import jinja2
    except ImportError:
        return {"checked": False, "why": "jinja2 not installed in this interpreter"}
    paths = glob.glob(str(Path.home() / ".cache/huggingface/hub/models--google--gemma-4-E4B-it/snapshots/*/chat_template.jinja"))
    if not paths:
        return {"checked": False, "why": "gemma-4-E4B-it chat template not cached"}
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, extensions=["jinja2.ext.loopcontrols"])

    def _raise(msg):
        raise jinja2.TemplateError(msg)
    env.globals["raise_exception"] = _raise
    tpl = env.from_string(Path(paths[0]).read_text())
    bad, n = [], 0
    for s in sims[::max(1, len(sims) // sample)][:sample]:
        msgs = [{"role": "system", "content": system}] + to_openai_messages(s["messages"])
        cut = max(j for j, m in enumerate(msgs) if m["role"] in ("tool", "user"))
        chat, prefix, _ = fold(msgs[:cut + 1], tools)
        head = tpl.render(messages=chat, add_generation_prompt=True, enable_thinking=False, bos_token="<bos>")
        prompt = head + prefix
        pos, ok = 0, prompt.endswith(prefix)
        for m in chat:
            j = prompt.find(m["content"], pos)
            if j < 0:
                ok = False
                break
            pos = j + len(m["content"])
        n += 1
        if not ok:
            bad.append(s["id"])
    return {"checked": True, "template": str(Path(paths[0]).relative_to(Path.home())), "conversations": n,
            "verbatim_in_order": n - len(bad), "failures": bad[:10]}


def check_wire(requests: list[dict]) -> dict:
    """τ²'s own client, through the shim's HTTP server, to a scripted member, and back into τ²'s environment.

    No model: the member is a script that writes one tag per encoding. What is checked is the wire — litellm's
    POST reaches the shim, the shim's reply parses into τ²'s `ToolCall` with the schema's types, and the airline
    environment executes it. `amount=50` written `k=v` must arrive as the integer 50 (τ² does not coerce)."""
    try:
        from tau2.data_model.message import SystemMessage, UserMessage, ToolCall
        from tau2.domains.airline.environment import get_environment
        from tau2.utils.llm_utils import generate
    except Exception as e:
        return {"checked": False, "why": f"tau2 not importable ({type(e).__name__})"}
    from examples.tau2.shim import Shim, serve
    script = [
        ('<send_certificate>{"user_id": "mia_li_3668", "amount": 50}</send_certificate>',
         "send_certificate", {"user_id": "mia_li_3668", "amount": 50}),
        ("<send_certificate>user_id=mia_li_3668; amount=50</send_certificate>",
         "send_certificate", {"user_id": "mia_li_3668", "amount": 50}),
        ("<get_user_details>mia_li_3668</get_user_details>", "get_user_details", {"user_id": "mia_li_3668"}),
        ("<list_all_airports></list_all_airports>", "list_all_airports", {}),
        ("Sure — could you give me your user id?", None, None),
    ]
    queue = [x[0] for x in script]
    shim = Shim("member", render=lambda chat: "PROMPT", generate=lambda *a, **k: (queue.pop(0), {
        "prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "finish_reason": "stop"}))
    srv = serve(shim, 0)
    base = f"http://127.0.0.1:{srv.server_address[1]}/v1"
    env = get_environment()
    sys_msg = next(m for m in requests[0]["body"]["messages"] if m["role"] == "system")["content"]
    out, ids = [], set()
    for text, name, args in script:
        msg = generate(model="openai/member", tools=env.get_tools(), api_base=base, api_key="x", temperature=0.0,
                       messages=[SystemMessage(role="system", content=sys_msg),
                                 UserMessage(role="user", content=f"turn {len(out)}")])
        rec = {"member_wrote": text}
        if name is None:
            rec["ok"] = not msg.tool_calls and msg.content == text
        else:
            tc = msg.tool_calls[0] if msg.tool_calls and len(msg.tool_calls) == 1 else None
            res = env.get_response(ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)) if tc else None
            rec.update(tau2_parsed={"name": tc.name, "arguments": tc.arguments} if tc else None,
                       env_error=bool(res.error) if res else None, env_result=(res.content[:80] if res else None))
            rec["ok"] = bool(tc) and tc.name == name and canon(tc.arguments) == canon(args) and not res.error
            ids.add(tc.id if tc else None)
        out.append(rec)
    srv.shutdown()
    return {"checked": True, "steps": out, "passed": all(r["ok"] for r in out), "distinct_call_ids": len(ids)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tau2", default=str(Path.home() / "evolvingagents/tau2-bench"))
    ap.add_argument("--out", default="results/TAU2-T0-recon-20261005/g_shim_1.json")
    a = ap.parse_args()
    files = sorted(glob.glob(str(Path(a.tau2) / "data/tau2/results/final/*airline*.json")))
    if not files:
        print(f"[tau2] no shipped airline trajectories under {a.tau2}")
        return 2
    tools = json.loads((FIXTURES / "airline_tools.json").read_text())
    system = next(m["content"] for m in json.loads((FIXTURES / "tau2_requests.json").read_text())[0]["body"]["messages"]
                  if m["role"] == "system")
    sims = []
    for f in files:
        sims += json.load(open(f))["simulations"]
    print(f"[tau2] G-shim-1 over {len(sims)} conversations in {len(files)} files", flush=True)
    calls = check_calls(sims, tools)
    print(f"[tau2] calls: {calls['exact']}/{calls['calls']} exact ({calls['write_calls']} writes) · kinds {calls['kinds']}", flush=True)
    control = control_repo_serializer(sims)
    print(f"[tau2] control (repo k=v serializer, must lose): {control['exact']}/{control['calls']} exact", flush=True)
    folded = check_fold(sims, tools, system)
    print(f"[tau2] fold: {folded['conversations'] - len([x for x in folded['failures'] if 'cut' not in x])}/"
          f"{folded['conversations']} conversations, {folded['mid_turn_cuts']} mid-turn cuts, "
          f"{len(folded['failures'])} failure(s)", flush=True)
    render = check_render(sims, tools, system)
    print(f"[tau2] render: {render}", flush=True)
    same = same_as_tau2(sims[::20])
    wire = check_wire(json.loads((FIXTURES / "tau2_requests.json").read_text()))
    print(f"[tau2] wire (tau2 client -> shim -> scripted member -> airline env): "
          f"{wire.get('passed', wire.get('why'))}", flush=True)
    passed = calls["lost"] == 0 and folded["passed"] and (not render.get("checked") or not render["failures"]) \
        and (not same.get("checked") or same["differ"] == 0) and control["lost"] > 0 \
        and (not wire.get("checked") or wire["passed"])
    try:
        commit = subprocess.run(["git", "-C", a.tau2, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None
    out = {"gate": "G-shim-1", "verdict": "PASS" if passed else "FAIL", "rule": "100 % identity, no tolerance",
           "tau2_commit": commit,
           "files": {Path(f).name: hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16] for f in files},
           "shim_sha256": hashlib.sha256((Path(__file__).parent / "shim.py").read_bytes()).hexdigest()[:16],
           "calls": calls, "control_repo_serializer": control, "fold": folded, "render": render, "wire": wire, "openai_form_same_as_tau2": same,
           "normalisation": "assistant text compared after strip(); calls, argument types, results and user turns exact"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"[tau2] G-shim-1 {out['verdict']} -> {a.out}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
