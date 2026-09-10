"""P13 — sequential activation: the two patches take turns instead of competing.

WHY THIS IS THE EXPERIMENT THAT DEFINES THE PROJECT. Everything measured so far
says the two halves exist and are healthy alone, and that they cannot both speak
at once. The kernel calls the tool on 30 of 30 problems and knows no physics; the
expert's formulas are exact on 30 of 30 and it never calls anything; stacked, the
combination calls on 5 of 30 and the expert wins the format at every other step
**[ran]** `results/P9-shared-contract-20260909/`. Giving each patch its own
matrices made it worse and weighting one up deleted the other
**[ran]** `results/P11-disjoint-20260909/`.

`TECHNICAL-REFERENCE.md` §5 names sequential activation as **option 1 and its own
default**, and it has never been measured. It is the only composition mode left
in which the two patches are never asked to produce the same word.

THE DIVISION OF LABOUR, AND WHY IT IS THE ARCHITECTURE'S OWN. §4 gives the expert
*what is true* and the kernel *how to act*. So:

    domain turn   `3. Reynolds number:`                    the PLAN — which
                                                           quantity comes next
    kernel turn   ` <calc>998 * 1.17 * 0.22 / 0.0008</calc>` the EXECUTION — the
                                                           expression and the call
    harness       `= 3.21e6`                                the value

Each turn ends in the format the other patch was trained to continue from, and at
no point are both active. The transcript that results is byte-identical in shape
to what the merged adapter produces — the one configuration already known to
score 40/40.

THE CONTROL THAT KEEPS THIS HONEST. A harness that could reconstruct the kernel's
contribution would make the kernel a channel nobody needs, and the measurement
void however clean it looked. Here it cannot: the domain turn stops at the colon,
so the expression exists nowhere until the kernel writes it. The control arm is
therefore a different thing — the expert generating alone with the harness
repairing its arithmetic exactly, which delegates on 100% of steps by
construction. If that ties the kernel arm, the kernel adapter earns nothing at
the delegation point **in this suite**, and we say so.

    python3 -m training.harness.sequential --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from training.physics.calc import CLOSE, CalcError, evaluate
from training.physics.generate import TRAIN_FAMILIES, generate
from training.physics.headroom import correct, parse_answer
from training.physics.repair import repair
from training.protocol import SYSTEM

RESULTS = Path("sequential_results.json")

# `3. Reynolds number: 998 * 1.17 * 0.22 / 0.0008 = 3.21e6`
#                    ^ the domain turn stops here, before it can write anything
#                      the harness could copy.
LABEL_END = ":"
ANSWER = re.compile(r'\{\s*"answer"')


def _first_line(text: str) -> str:
    return text.split("\n", 1)[0]


def sequential(step, system: str, user: str, max_steps: int = 8,
               kernel_executes: bool = True) -> tuple[str, int, int]:
    """Run one problem with the two patches taking turns.

    `step(adapter, system, user, prefix, stops)` generates from `prefix` with
    `adapter` active, stopping at any of `stops`. Returns
    (transcript, tool calls, steps the evaluator rejected).
    """
    out, calls, rejected = "", 0, 0
    for _ in range(max_steps):
        # ---- DOMAIN TURN: which quantity comes next, and nothing more.
        raw = step("domain", system, user, out, [LABEL_END, "\n\n"])
        # THE FINAL LINE IS CHECKED BEFORE THE FIRST LINE IS TAKEN. The expert
        # opens its answer with a blank line, so `first_line` of it is empty and
        # the loop used to break and drop the answer entirely — the transcript
        # then scored on whatever number happened to be last.
        if ANSWER.search(raw):
            out += raw[:raw.index("}") + 1] if "}" in raw else raw
            break
        head = _first_line(raw)
        if not head.strip():
            break
        if LABEL_END in head:
            head = head[:head.index(LABEL_END) + 1]
        out += head

        # ---- KERNEL TURN: the expression, wrapped in a call.
        if kernel_executes:
            chunk = step("kernel", system, user, out, [CLOSE])
            if CLOSE in chunk:
                chunk = chunk[:chunk.index(CLOSE) + len(CLOSE)]
            out += chunk
        else:
            # The control: the expert writes its own expression and the harness
            # repairs the arithmetic. No kernel weights are ever loaded.
            chunk = _first_line(step("domain", system, user, out, ["=", "\n"]))
            out += chunk if "=" not in chunk else chunk[:chunk.index("=")]

        # ---- HARNESS: answer whatever was just asked for.
        expr = _expression(out, kernel_executes)
        if expr is None:
            out += "\n"
            continue
        calls += 1
        try:
            out += f"= {evaluate(expr):.6g}\n"
        except CalcError as e:
            rejected += 1
            out += f"= ERROR: {e}\n"
    return out, calls, rejected


def _expression(out: str, tagged: bool) -> str | None:
    """The expression the last turn asked to have computed."""
    if tagged:
        m = list(re.finditer(r"<calc>(.*?)</calc>", out, re.S))
        return m[-1].group(1) if m else None
    tail = out.rsplit("\n", 1)[-1]
    body = tail.rpartition(LABEL_END)[2] if LABEL_END in tail else tail
    body = body.strip()
    return body or None


def make_turn_step(peft_model, tok, max_new_tokens: int):
    """Generate with one named patch active. Switching is a pointer, not a load."""
    import torch

    def step(adapter, system, user, prefix, stops):
        peft_model.set_adapter(adapter)
        msgs = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
        text = tok.apply_chat_template(msgs, tokenize=False,
                                       add_generation_prompt=True) + prefix
        ids = tok(text, return_tensors="pt").to(peft_model.device)
        with torch.no_grad():
            out = peft_model.generate(**ids, max_new_tokens=max_new_tokens,
                                      do_sample=False,
                                      pad_token_id=tok.pad_token_id,
                                      stop_strings=list(stops), tokenizer=tok)
        return tok.decode(out[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True)
    return step


def score(step, rows, rtol, label, kernel_executes, prev=None, save=None):
    """One arm, banked after every case — an arm is not an atom [ran] 2026-09-09."""
    recs = list((prev or {}).get("records") or [])
    done = {r["case_id"] for r in recs}
    if recs:
        print(f"  [{label}] resuming with {len(recs)} scored", flush=True)

    def snap(complete):
        n = max(len(recs), 1)
        return {"label": label, "n": len(rows), "scored": len(recs),
                "complete": complete,
                "passed": sum(r["passed"] for r in recs),
                "accuracy": round(sum(r["passed"] for r in recs) / n, 4),
                "repaired_passed": sum(r["repaired_passed"] for r in recs),
                "tool_calls": sum(r["tool_calls"] for r in recs),
                "steps_rejected": sum(r["steps_rejected"] for r in recs),
                "records": recs}

    for i, row in enumerate(rows, 1):
        if row["case_id"] in done:
            continue
        text, calls, rejected = sequential(step, SYSTEM, row["prompt"],
                                           kernel_executes=kernel_executes)
        got = parse_answer(text)
        fixed, _, _ = repair(text)
        recs.append({"case_id": row["case_id"], "family": row["family"],
                     "want": row["answer"], "got": got,
                     "passed": bool(correct(got, row["answer"], rtol)),
                     "repaired": fixed,
                     "repaired_passed": bool(correct(fixed, row["answer"], rtol)),
                     "tool_calls": calls, "steps_rejected": rejected,
                     "raw": text[:700]})
        if save:
            save(snap(False))
        if i % 10 == 0:
            s = snap(False)
            print(f"  [{label}] {i}/{len(rows)} passed {s['passed']} "
                  f"repaired {s['repaired_passed']} calls {s['tool_calls']}",
                  flush=True)
    return snap(True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--kernel-corpus", default="training/harness/data/train.jsonl")
    ap.add_argument("--domain-corpus", default="training/physics/data_inline/train.jsonl")
    ap.add_argument("--n-eval", type=int, default=30)
    ap.add_argument("--eval-seed", type=int, default=515151)
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
    args = ap.parse_args()

    from peft import PeftModel
    from training.s4_train import free, load_base, train_adapter

    ev = generate(args.n_eval, args.eval_seed, TRAIN_FAMILIES, style="working")
    kernel_rows = [json.loads(l) for l in open(args.kernel_corpus) if l.strip()]
    domain_rows = [json.loads(l) for l in open(args.domain_corpus) if l.strip()]
    print(f"[corpora] kernel {len(kernel_rows)} · domain {len(domain_rows)} · "
          f"eval {len(ev)}", flush=True)

    summary = {"base": args.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "arms": {}}
    if RESULTS.exists():
        prev = json.loads(RESULTS.read_text())
        if prev.get("base") == args.base:
            summary["arms"] = prev.get("arms", {})
            for k, v in summary["arms"].items():
                print(f"[resume] {k}" + ("" if v.get("complete", True)
                                         else f" (partial, {v['scored']})"), flush=True)

    def save():
        RESULTS.write_text(json.dumps(summary, indent=2))

    for name, rows in (("kernel", kernel_rows), ("domain", domain_rows)):
        if not Path(f"adapters/{name}").exists():
            print(f"[train] {name}", flush=True)
            train_adapter(args.base, rows, f"adapters/{name}", args)
            free()

    model, tok = load_base(args.base, args.four_bit)
    peft_model = PeftModel.from_pretrained(model, "adapters/kernel",
                                           adapter_name="kernel")
    peft_model.load_adapter("adapters/domain", adapter_name="domain")
    step = make_turn_step(peft_model, tok, args.max_new_tokens)

    def run(label, kernel_executes):
        prev = summary["arms"].get(label)
        if prev and prev.get("complete", True):
            return
        print(f"[arm] {label}", flush=True)

        def bank(partial):
            summary["arms"][label] = partial
            save()

        summary["arms"][label] = score(step, ev, args.rtol, label,
                                       kernel_executes, prev, bank)
        save()

    # The claim first: it is the arm that can kill the hypothesis.
    run("sequential · domain plans, kernel executes", True)
    # Then the control that prices the kernel at the delegation point.
    run("control · domain alone, harness repairs", False)

    a = summary["arms"]
    print(f"\n{'arm':<46}{'passed':>9}{'repaired':>10}{'calls':>8}{'per case':>10}")
    for k, v in a.items():
        n = max(v["scored"], 1)
        print(f"{k:<46}{str(v['passed'])+'/'+str(n):>9}"
              f"{str(v['repaired_passed'])+'/'+str(n):>10}"
              f"{v['tool_calls']:>8}{v['tool_calls'] / n:>10.1f}")
    claim = a.get("sequential · domain plans, kernel executes", {})
    ctrl = a.get("control · domain alone, harness repairs", {})
    print(f"\nP9 stacked, the same 30 cases: 4/30 passed, 0.6 calls per case.")
    print(f"Sequential: {claim.get('accuracy', 0):.3f} at "
          f"{claim.get('tool_calls', 0) / max(claim.get('scored', 1), 1):.1f} "
          f"calls per case. Control without the kernel: {ctrl.get('accuracy', 0):.3f}.")
    print("If the two arms tie, the kernel adapter earns nothing at the "
          "delegation point in this suite, and the modularity it buys has to be "
          "argued somewhere else.")
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
