"""Does the protocol compose, or does every expert have to re-learn it?

THE ONLY UNTESTED CLAIM LEFT IN THE ARCHITECTURE. `ARCHITECTURE.md` §4 says the
kernel owns how to act and the domain adapter owns what is true, and that merging
them is the cost the design exists to remove. P7 measured the MERGED case —
one adapter that learned fluid mechanics and `<calc>` syntax together — at 40/40
**[ran]**. That is the option `TECHNICAL-REFERENCE.md` §5 lists in order to reject
it. Separation itself has never been measured.

FIVE ARMS, AND EACH ISOLATES ONE THING.

  base + tool             0/40 already, with 53 calls: the tool alone is nothing.
  kernel + tool           a protocol adapter that has never seen physics. It
                          should call correctly and compute the wrong physics.
  domain + tool           the P6 expert: physics in prose, no tags. It knows what
                          to compute and not how to ask.
  KERNEL + DOMAIN + tool  the claim. If the two compose, the protocol lives in
                          weights of its own.
  merged + tool           40/40, P7's adapter, the ceiling this must approach.

FALSIFICATION, WRITTEN BEFORE THE RUN. If the composition does not clearly beat
both halves alone, then a protocol does not compose and §4 is wrong: every expert
must carry the protocol, which is the merged adapter — and that costs a retrain
of every domain adapter whenever the tool surface changes, which is precisely the
price the architecture claims to avoid.

    python3 -m training.harness.compose --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.physics.calc import generate_with_tool
from training.physics.generate import TRAIN_FAMILIES, generate
from training.physics.headroom import SYSTEM, correct, parse_answer

RESULTS = Path("compose_results.json")


def score(step, rows, rtol, label, prev=None, save=None):
    """One arm, checkpointed after every case.

    AN ARM IS NOT AN ATOM. The composition arm reached 20 of 30 and a reclaimed
    session took all of it, because the results file was only written when an
    arm finished [ran] 2026-09-09 — the chain script's own lesson, one level
    down. Every case is banked as it lands, and a resumed arm starts at the
    first case it does not already hold.
    """
    recs = list((prev or {}).get("records") or [])
    done = {r["case_id"] for r in recs}
    passed = sum(r["passed"] for r in recs)
    calls = sum(r["tool_calls"] for r in recs)
    if recs:
        print(f"  [{label}] resuming with {len(recs)} cases already scored",
              flush=True)

    def snapshot(complete):
        return {"label": label, "n": len(rows), "scored": len(recs),
                "passed": passed, "complete": complete,
                "accuracy": round(passed / max(len(recs), 1), 4),
                "tool_calls": calls, "records": recs}

    for i, row in enumerate(rows, 1):
        if row["case_id"] in done:
            continue
        text, used = generate_with_tool(step, SYSTEM, row["prompt"])
        calls += used
        got = parse_answer(text)
        ok = correct(got, row["answer"], rtol)
        passed += ok
        recs.append({"case_id": row["case_id"], "family": row["family"],
                     "want": row["answer"], "got": got, "passed": bool(ok),
                     "tool_calls": used, "raw": text[:400]})
        if save:
            save(snapshot(False))
        if i % 10 == 0:
            print(f"  [{label}] {i}/{len(rows)} passed {passed} calls {calls}",
                  flush=True)
    return snapshot(True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--kernel-corpus", default="training/harness/data/train.jsonl")
    ap.add_argument("--domain-corpus", default="training/physics/data/train.jsonl")
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
    ap.add_argument("--max-new-tokens", type=int, default=900)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true")
    args = ap.parse_args()

    from peft import PeftModel
    from training.physics.train_expert import make_gen_step
    from training.s4_train import free, load_base, train_adapter

    ev = generate(args.n_eval, args.eval_seed, TRAIN_FAMILIES, style="calc")
    kernel_rows = [json.loads(l) for l in open(args.kernel_corpus) if l.strip()]
    domain_rows = [json.loads(l) for l in open(args.domain_corpus) if l.strip()]
    print(f"[corpora] kernel {len(kernel_rows)} (no physics) | "
          f"domain {len(domain_rows)} (no tool syntax) | eval {len(ev)}", flush=True)

    summary = {"base": args.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "kernel_n": len(kernel_rows), "domain_n": len(domain_rows),
               "arms": {}}
    if RESULTS.exists():
        prev = json.loads(RESULTS.read_text())
        if prev.get("base") == args.base:
            summary["arms"] = prev.get("arms", {})
            for k, v in summary["arms"].items():
                state = "" if v.get("complete", True) else \
                    f" (partial, {v.get('scored', 0)} cases)"
                print(f"[resume] {k}{state}", flush=True)

    def save():
        RESULTS.write_text(json.dumps(summary, indent=2))

    # Trained once each, saved, then loaded together. Training them in one
    # process and composing in another would leave the composition untested.
    for name, rows in (("kernel", kernel_rows), ("domain", domain_rows)):
        if not Path(f"adapters/{name}").exists():
            print(f"[train] {name}", flush=True)
            m, _ = train_adapter(args.base, rows, f"adapters/{name}", args)
            m = None
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
            if isinstance(active, list):
                # STACKING GOES THROUGH THE LoraModel, NOT THE PeftModel.
                # PeftModel.set_adapter takes a single name and raises
                # "unhashable type: 'list'" on a list [ran] 2026-09-09; the
                # tuner underneath is the object that can hold several deltas
                # active at once, which is what option 2 of §5 requires.
                peft_model.base_model.set_adapter(active)
            else:
                peft_model.set_adapter(active)
        print(f"[arm] {label} — active adapters: {active}", flush=True)
        step = make_gen_step(peft_model, tok, args.max_new_tokens)

        def bank(partial):
            summary["arms"][label] = partial
            save()

        summary["arms"][label] = score(step, ev, args.rtol, label, prev, bank)
        save()

    run(None, "base + tool")
    run("kernel", "kernel + tool")
    run("domain", "domain + tool")
    # THE CLAIM: both deltas over one base, at once.
    run(["kernel", "domain"], "kernel + domain + tool")

    a = summary["arms"]
    print(f"\n{'arm':<28}{'passed':>10}{'accuracy':>11}{'tool calls':>12}")
    for k, v in a.items():
        print(f"{k:<28}{str(v['passed'])+'/'+str(v['n']):>10}"
              f"{v['accuracy']:>11.3f}{v['tool_calls']:>12}")
    both = a.get("kernel + domain + tool", {}).get("accuracy", 0)
    print(f"\ncomposition {both:.3f} against kernel alone "
          f"{a.get('kernel + tool',{}).get('accuracy',0):.3f} and domain alone "
          f"{a.get('domain + tool',{}).get('accuracy',0):.3f}")
    print("If the composition does not clearly beat both halves, the protocol "
          "does not compose and every expert must carry it.")
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
