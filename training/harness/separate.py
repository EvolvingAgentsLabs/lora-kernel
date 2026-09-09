"""P9 — composition, measured under a contract the two halves actually share.

WHY P8 HAS TO BE RE-RUN AND NOT RE-READ. P8 stacked a kernel adapter and a domain
adapter and got 0/30, and I read that as weight-space interference. It could not
be read as anything: the kernel corpus was 600/600 `<calc>` with no LaTeX, the
domain corpus 0/598 `<calc>` with 433 LaTeX, the domain corpus's system prompt
told the model to show no working over 598 targets that all show working, and
every arm ran under that domain prompt **[ran]**. The corruption inside the tags
was the superposition of two taught notations. Composition was never measured.

WHAT IS DIFFERENT HERE, AND IT IS ONLY THIS. Both corpora now import
`training/protocol.py`: same system prompt, same user instruction, same numbered
ASCII chain, same final JSON. The domain corpus is the *oracle's own* chains with
the tags removed and the arithmetic left in place, so its formulas are exact. The
two adapters therefore differ in exactly one thing — whether the arithmetic is
delegated — which is the thing `ARCHITECTURE.md` §4 says is separable.

**The instruction says nothing about `<calc>`.** If the prompt asked for tags the
prompt would be the protocol and the kernel adapter would be decoration.

THE ARMS, IN THE ORDER THEY CAN KILL THE HYPOTHESIS.

  1. domain          Does the expert know the physics AT ALL? P8 never found out:
                     its domain arm emitted a bare JSON number on 30 of 30 cases.
                     Scored twice — raw, and with its arithmetic repaired.
  2. kernel          The protocol under a prompt that does not ask for it.
  3. kernel+domain   The claim.
  4. base            Attribution, bought last because it cannot kill anything.

THE STOPPING CONDITION, WRITTEN BEFORE THE RUN. If the domain adapter's REPAIRED
accuracy is below `--gate` (0.25), it does not know the physics, there is nothing
for a composition to combine, and arms 3 and 4 are not bought. A composition
cannot be shown to gain from a half that contributes nothing, and buying it anyway
is how a flat result gets spent into a grid.

FALSIFICATION. With the contract shared and the domain half verified, if
`kernel+domain` still fails to beat both halves, weight-space composition is
genuinely dead and §4 must be served some other way.

    python3 -m training.harness.separate --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.physics.calc import generate_with_tool
from training.physics.generate import TRAIN_FAMILIES, generate
from training.physics.headroom import correct, parse_answer
from training.physics.repair import repair
from training.protocol import SYSTEM

RESULTS = Path("separate_results.json")


def score(step, rows, rtol, label, prev=None, save=None):
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
                "repaired_accuracy": round(sum(r["repaired_passed"] for r in recs) / n, 4),
                "tool_calls": sum(r["tool_calls"] for r in recs),
                "steps_rejected": sum(r["steps_rejected"] for r in recs),
                "records": recs}

    for i, row in enumerate(rows, 1):
        if row["case_id"] in done:
            continue
        text, used = generate_with_tool(step, SYSTEM, row["prompt"])
        got = parse_answer(text)
        fixed, n_ok, n_bad = repair(text)
        recs.append({
            "case_id": row["case_id"], "family": row["family"],
            "want": row["answer"], "got": got,
            "passed": bool(correct(got, row["answer"], rtol)),
            # The same chain, with every step re-evaluated exactly. It separates
            # "wrong formula" from "right formula, wrong arithmetic", which is the
            # distinction the whole calculator result rests on.
            "repaired": fixed,
            "repaired_passed": bool(correct(fixed, row["answer"], rtol)),
            "steps_ok": n_ok, "steps_rejected": n_bad,
            "tool_calls": used, "raw": text[:600],
        })
        if save:
            save(snap(False))
        if i % 10 == 0:
            s = snap(False)
            print(f"  [{label}] {i}/{len(rows)} passed {s['passed']} "
                  f"repaired {s['repaired_passed']} calls {s['tool_calls']}", flush=True)
    return snap(True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--kernel-corpus", default="training/harness/data/train.jsonl")
    ap.add_argument("--domain-corpus", default="training/physics/data_inline/train.jsonl")
    ap.add_argument("--n-eval", type=int, default=30)
    ap.add_argument("--eval-seed", type=int, default=515151)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--gate", type=float, default=0.25,
                    help="minimum repaired accuracy for the domain arm before the "
                         "composition is bought at all")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--max-new-tokens", type=int, default=900)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true")
    args = ap.parse_args()

    from peft import PeftModel
    from training.physics.train_expert import make_gen_step
    from training.s4_train import free, load_base, train_adapter

    # The eval prompt is the shared contract, not the calc-style one: nothing in
    # it may ask for a tool.
    ev = generate(args.n_eval, args.eval_seed, TRAIN_FAMILIES, style="working")
    kernel_rows = [json.loads(l) for l in open(args.kernel_corpus) if l.strip()]
    domain_rows = [json.loads(l) for l in open(args.domain_corpus) if l.strip()]

    def contract(rows):
        return [m["content"] for m in rows[0]["messages"] if m["role"] == "system"][0]
    assert contract(kernel_rows) == contract(domain_rows) == SYSTEM, \
        "the two corpora disagree about the contract — that is the P8 confound"
    tagged = sum("<calc>" in m["content"] for r in domain_rows
                 for m in r["messages"] if m["role"] == "assistant")
    assert tagged == 0, f"{tagged} domain examples carry the protocol"
    print(f"[corpora] kernel {len(kernel_rows)} · domain {len(domain_rows)} "
          f"(0 tagged) · eval {len(ev)} · one shared contract", flush=True)

    summary = {"base": args.base, "gate": args.gate,
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

    for name, rows in (("kernel", kernel_rows), ("domain", domain_rows)):
        if not Path(f"adapters/{name}").exists():
            print(f"[train] {name}", flush=True)
            train_adapter(args.base, rows, f"adapters/{name}", args)
            free()

    model, tok = load_base(args.base, args.four_bit)
    peft_model = PeftModel.from_pretrained(model, "adapters/kernel",
                                           adapter_name="kernel")
    peft_model.load_adapter("adapters/domain", adapter_name="domain")

    def run(active, label):
        prev = summary["arms"].get(label)
        if prev and prev.get("complete", True):
            return
        if active is None:
            peft_model.disable_adapter_layers()
        else:
            peft_model.enable_adapter_layers()
            (peft_model.base_model if isinstance(active, list)
             else peft_model).set_adapter(active)
        print(f"[arm] {label} — active: {active}", flush=True)
        step = make_gen_step(peft_model, tok, args.max_new_tokens)

        def bank(partial):
            summary["arms"][label] = partial
            save()

        summary["arms"][label] = score(step, ev, args.rtol, label, prev, bank)
        save()

    run("domain", "domain")
    dom = summary["arms"]["domain"]
    print(f"\n[gate] domain repaired accuracy {dom['repaired_accuracy']:.3f} "
          f"against a gate of {args.gate:.2f}", flush=True)
    if dom["repaired_accuracy"] < args.gate:
        print("[gate] STOPPED. The domain adapter does not know the physics, so a "
              "composition has nothing to combine and arms 2-4 are not bought.",
              flush=True)
        summary["stopped_at_gate"] = True
        summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        return 0

    run("kernel", "kernel")
    run(["kernel", "domain"], "kernel + domain")
    run(None, "base")

    a = summary["arms"]
    print(f"\n{'arm':<20}{'passed':>9}{'repaired':>10}{'calls':>8}{'rejected':>10}")
    for k, v in a.items():
        print(f"{k:<20}{str(v['passed'])+'/'+str(v['n']):>9}"
              f"{str(v['repaired_passed'])+'/'+str(v['n']):>10}"
              f"{v['tool_calls']:>8}{v['steps_rejected']:>10}")
    both = a.get("kernel + domain", {}).get("accuracy", 0)
    print(f"\ncomposition {both:.3f} against kernel {a.get('kernel',{}).get('accuracy',0):.3f} "
          f"and domain {a.get('domain',{}).get('accuracy',0):.3f}")
    print("With the contract shared and the domain half verified, a composition "
          "that does not beat both halves kills weight-space composition.")
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
