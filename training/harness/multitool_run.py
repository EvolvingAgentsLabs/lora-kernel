"""P15 — three tool layers over one expert, and the rule is the one to beat.

THE QUESTION. P13 measured a learned protocol losing to a regular expression on a
suite where the call was a copy. This suite removes the copying: statements name
their fluid instead of handing over a density, quantities arrive in litres per
second and millimetres, and one family needs no lookup at all. Asking for a tool
now means choosing between three of them and building keyed arguments out of
prose.

THE ARMS, differing only in who writes the `convert` and `lookup` calls:

  kernel   the learned protocol adapter, from the statement and the step label
  rule     `rule_tools.call_for` — **92.9%** on the oracle's tool steps [ran]
  none     no tool layer: the expert answers from memory, arithmetic repaired

`calc` steps are the expert's in every arm, so nothing here compares physics.

THE BAR IS PUBLISHED BEFORE THE TREATMENT RUNS. Below the rule and a learned
protocol is not worth its weights even where the call is not a copy.

THE KERNEL DECLINES BY CHOOSING `calc`. Both tool layers are asked for a call and
both may decline: the rule by returning None, the kernel by emitting `<calc>`,
which says the step needs an expression rather than a query. Declining hands the
step to the expert, identically in both arms — so the kernel's choice of tool is
measured rather than assumed.

    python3 -m training.harness.multitool_run --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from training.harness.failure_mode import tally
from training.harness.rule_tools import call_for
from training.physics.multitool import FAMILIES, generate
from training.physics.repair import repair
from training.physics.tools import CALL, ToolError, answer
from training.protocol import SYSTEM

RESULTS = Path("multitool_results.json")   # per run dir; P15 and P21 never share one
LABEL_END = ":"
ANSWER = re.compile(r'\{\s*"answer"')
QUERIES = ("convert", "lookup")


def _first_line(t: str) -> str:
    return t.split("\n", 1)[0]


def _statement(prompt: str) -> str:
    return prompt.split("\n\n")[0]


def run_case(step, prompt: str, layer: str, handbook=None, max_steps: int = 10):
    """One problem. Returns (transcript, queries, rejected, declined)."""
    out, queries, rejected, declined = "", 0, 0, 0
    stmt = _statement(prompt)
    for _ in range(max_steps):
        raw = step("domain", prompt, out, [LABEL_END, "\n\n"])
        if ANSWER.search(raw):
            out += raw[:raw.index("}") + 1] if "}" in raw else raw
            break
        head = _first_line(raw)
        if not head.strip():
            break
        if LABEL_END in head:
            head = head[:head.index(LABEL_END) + 1]
        out += head
        label = head.rsplit(".", 1)[-1].strip(" :")

        call = None
        if layer == "kernel":
            chunk = step("kernel", prompt, out, ["</calc>", "</convert>", "</lookup>"])
            m = CALL.search(chunk)
            if m and m.group(1) in QUERIES:
                call = m.group(0)
            else:
                declined += 1
        elif layer == "rule":
            call = call_for(stmt, label)
            declined += call is None

        if call is not None:
            m = CALL.search(call)
            out += " " + call
            queries += 1
            try:
                out += f"= {answer(m.group(1), m.group(2), handbook):.6g}\n"
            except ToolError as e:
                rejected += 1
                out += f"= ERROR: {e}\n"
            continue

        # No query: the expert writes this step itself, and the harness computes
        # whatever expression it produced rather than trusting its arithmetic.
        body = _first_line(step("domain", prompt, out, ["\n"]))
        expr = body[:body.index("=")] if "=" in body else body
        out += expr
        value, _, _ = repair(f"1. x: {expr.strip()}")
        out += f"= {value:.6g}\n" if value is not None else "\n"
    return out, queries, rejected, declined


def make_step(peft_model, tok, max_new_tokens: int):
    import torch

    def step(adapter, user, prefix, stops):
        peft_model.set_adapter(adapter)
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        text = tok.apply_chat_template(msgs, tokenize=False,
                                       add_generation_prompt=True) + prefix
        ids = tok(text, return_tensors="pt").to(peft_model.device)
        with torch.no_grad():
            o = peft_model.generate(**ids, max_new_tokens=max_new_tokens,
                                    do_sample=False, pad_token_id=tok.pad_token_id,
                                    stop_strings=list(stops), tokenizer=tok)
        return tok.decode(o[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    return step


def oracle_tool_values(row) -> list[float]:
    book = _book(row)
    return [answer(t, b, book) for _, t, b in row["chain"] if t in QUERIES]


def _book(row) -> dict:
    """The handbook this problem carries. It lives in the tool, never in the
    prompt — a printed handbook can be copied, and P15 died of a table that
    could be remembered [ran]."""
    return {tuple(k): v for k, v in row.get("handbook", [])}


def score(step, rows, rtol, label, layer, prev=None, save=None):
    from training.physics.headroom import correct, parse_answer
    recs = list((prev or {}).get("records") or [])
    done = {r["case_id"] for r in recs}
    if recs:
        print(f"  [{label}] resuming with {len(recs)} scored", flush=True)

    def snap(complete):
        n = max(len(recs), 1)
        return {"label": label, "layer": layer, "n": len(rows), "scored": len(recs),
                "complete": complete,
                "passed": sum(r["passed"] for r in recs),
                "accuracy": round(sum(r["passed"] for r in recs) / n, 4),
                "queries": sum(r["queries"] for r in recs),
                "rejected": sum(r["rejected"] for r in recs),
                "declined": sum(r["declined"] for r in recs),
                "tool_values_matched": sum(r["matched"] for r in recs),
                "tool_values_wanted": sum(r["wanted"] for r in recs),
                # WHICH HALF FAILED. Accuracy folds the tool layer and the physics
                # together; P21's rule wrote 93 of 96 calls and still scored 5/30,
                # so the number alone pointed at the wrong next step [ran].
                "failure_modes": tally(recs),
                "records": recs}

    for i, row in enumerate(rows, 1):
        if row["case_id"] in done:
            continue
        text, q, rej, dec = run_case(step, row["prompt"], layer, _book(row))
        got = parse_answer(text)
        # HOW MANY OF THE ORACLE'S QUERIES DID THIS ARM ACTUALLY REPRODUCE? The
        # final answer folds tool errors and physics errors together; this does
        # not, and it is the number the 92.9% bar is stated in.
        want_vals = oracle_tool_values(row)
        got_vals = []
        book = _book(row)
        for m in CALL.finditer(text):
            if m.group(1) in QUERIES:
                try:
                    got_vals.append(answer(m.group(1), m.group(2), book))
                except ToolError:
                    pass
        pool = list(want_vals)
        matched = 0
        for v in got_vals:
            hit = next((w for w in pool if abs(v - w) <= 1e-6 * max(abs(w), 1)), None)
            if hit is not None:
                pool.remove(hit)
                matched += 1
        recs.append({"case_id": row["case_id"], "family": row["family"],
                     "want": row["answer"], "got": got,
                     "passed": bool(correct(got, row["answer"], rtol)),
                     "queries": q, "rejected": rej, "declined": dec,
                     "matched": matched, "wanted": len(want_vals),
                     "raw": text[:700]})
        if save:
            save(snap(False))
        if i % 10 == 0:
            s = snap(False)
            print(f"  [{label}] {i}/{len(rows)} passed {s['passed']} "
                  f"tools {s['tool_values_matched']}/{s['tool_values_wanted']} "
                  f"queries {s['queries']} rejected {s['rejected']}", flush=True)
    return snap(True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--kernel-corpus", default="training/harness/data_mt/train.jsonl")
    ap.add_argument("--domain-corpus", default="training/physics/data_mt/train.jsonl")
    ap.add_argument("--n-eval", type=int, default=30)
    ap.add_argument("--eval-seed", type=int, default=616161)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true")
    ap.add_argument("--gate", type=float, default=0.35,
                    help="if the no-tool arm reaches this, the material is still "
                         "memorisable and the other arms are not bought")
    args = ap.parse_args()

    from peft import PeftModel
    from training.s4_train import free, load_base, train_adapter

    ev = generate(args.n_eval, args.eval_seed, FAMILIES)
    kernel_rows = [json.loads(l) for l in open(args.kernel_corpus) if l.strip()]
    domain_rows = [json.loads(l) for l in open(args.domain_corpus) if l.strip()]
    tagged = sum("<" in m["content"] for r in domain_rows
                 for m in r["messages"] if m["role"] == "assistant")
    assert tagged == 0, f"{tagged} expert examples carry the protocol"
    print(f"[corpora] kernel {len(kernel_rows)} (3 tools, no evaluation domain) · "
          f"domain {len(domain_rows)} (0 tagged) · eval {len(ev)}", flush=True)

    summary = {"base": args.base, "rule_bar": 0.929,
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "arms": {}}
    if RESULTS.exists():
        prev = json.loads(RESULTS.read_text())
        if prev.get("base") == args.base:
            summary["arms"] = prev.get("arms", {})
            for k, v in summary["arms"].items():
                print(f"[resume] {k}" + ("" if v.get("complete", True)
                                         else f" (partial, {v['scored']})"), flush=True)

    def save():
        RESULTS.write_text(json.dumps(summary, indent=2))

    # AN ADAPTER IS ITS WEIGHTS, NOT ITS DIRECTORY. This check used to be
    # `Path(path).exists()`, and a session-carrying tarball shipped an EMPTY
    # `adapters/domain-mt` — the directory trl creates before it has written
    # anything [ran] 2026-09-12. That would have skipped training and scored the
    # base model wearing an adapter's name, silently, with every other number in
    # the run looking normal. Keying on the weights file makes the failure loud.
    for name, rows, path in (("kernel", kernel_rows, "adapters/kernel-mt"),
                             ("domain", domain_rows, "adapters/domain-mt")):
        if not (Path(path) / "adapter_model.safetensors").exists():
            if Path(path).exists():
                print(f"[train] {name} — directory present but no weights in it",
                      flush=True)
            else:
                print(f"[train] {name}", flush=True)
            train_adapter(args.base, rows, path, args)
            free()

    model, tok = load_base(args.base, args.four_bit)
    peft_model = PeftModel.from_pretrained(model, "adapters/kernel-mt",
                                           adapter_name="kernel")
    peft_model.load_adapter("adapters/domain-mt", adapter_name="domain")
    step = make_step(peft_model, tok, args.max_new_tokens)

    def run(label, layer):
        prev = summary["arms"].get(label)
        if prev and prev.get("complete", True):
            return
        print(f"[arm] {label}", flush=True)

        def bank(p):
            summary["arms"][label] = p
            save()

        summary["arms"][label] = score(step, ev, args.rtol, label, layer, prev, bank)
        save()

    # THE KILLING ARM IS BOUGHT FIRST. P15 ordered this last and paid for two arms
    # before learning its material could be answered from memory [ran]. If the
    # expert still scores well with no tool layer, the handbook did not work and
    # the other two arms are not bought.
    run("no tool layer at all", "none")
    if summary["arms"]["no tool layer at all"]["accuracy"] >= args.gate:
        print(f"[gate] STOPPED. With no tool layer the expert scores "
              f"{summary['arms']['no tool layer at all']['accuracy']:.3f}, at or "
              f"above the gate of {args.gate:.2f}: the material is still "
              "answerable without the tools and the other arms measure nothing.",
              flush=True)
        summary["stopped_at_gate"] = True
        summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        return 0
    run("hand-written rule writes the calls", "rule")   # the bar
    run("kernel adapter writes the calls", "kernel")    # the claim

    a = summary["arms"]
    print(f"\n{'arm':<40}{'passed':>9}{'tool steps':>13}{'queries':>9}{'rejected':>10}")
    for k, v in a.items():
        n = max(v["scored"], 1)
        tools = f"{v['tool_values_matched']}/{v['tool_values_wanted']}"
        print(f"{k:<40}{str(v['passed']) + '/' + str(n):>9}{tools:>13}"
              f"{v['queries']:>9}{v['rejected']:>10}")
        f = v.get("failure_modes") or tally(v["records"])
        print(f"{'':<40}of {f['failed']} failures: protocol {f['protocol']}, "
              f"physics {f['physics']}  "
              + ", ".join(f"{m} {c}" for m, c in f["by_mode"].items() if c))
    ker = a.get("kernel adapter writes the calls", {})
    got = ker.get("tool_values_matched", 0) / max(ker.get("tool_values_wanted", 1), 1)
    print(f"\nThe bar is the hand-written rule at 0.929 on the oracle's tool steps.")
    print(f"The kernel adapter reproduced {got:.3f}.")
    print("Below the bar, a learned protocol is not worth its weights even where "
          "the call is not a copy, and harness.lora should be replaced by a rule "
          "in the architecture rather than defended.")
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
