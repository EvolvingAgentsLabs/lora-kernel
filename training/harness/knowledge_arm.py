"""P61 — weights or harness: the base with a written procedure against the trained expert.

WHY. The service resolves a request locally either with a LoRA (weights) or with
knowledge the harness puts in the context (markdown, retrieved lexically — the version
that won ai-os's memory benchmark). Which one buys the region decides what the
customisation costs: a LoRA is trained once and adds no tokens per request; a
knowledge document is written in an afternoon and is paid on every request, at its
length in tokens. The measurement is the same suite, the same corpus-mode loop, the
same base, three arms in one session:

    base            the system prompt the corpus taught, nothing else   (P55: 0.516, human 0.345)
    base + kb       the same, with `knowledge/<suite>.md` appended to the system prompt
    expert          the QLoRA `email-full`                              (P55: 0.992, human 0.989)

WHAT THE BASE DOES WITHOUT THE DOCUMENT **[ran]** P55: 230 of 351 human messages
answered NOT IMPORTANT with zero tool calls, although the system prompt states the
rule. So the document is a procedure — which call returns which signal, in which
syntax, in which order — and not the rule restated.

THE MATHEMATICS IS THE SIGN TEST ON DISCORDANT PAIRS (FOUNDATIONS §7.3): with $a$ the
cases only the first arm passes and $b$ the cases only the second passes, under
$H_0$ both arms are equal and $a \\sim \\mathrm{Bin}(a+b, 1/2)$; $p$ is the two-sided
tail. Pre-registered, before the run:

    kb_pays                 base+kb > base,   p < 0.05, on all cases
    weights_needed          expert > base+kb, p < 0.05
    harness_replaces_weights   not weights_needed AND human(base+kb) ≥ human(expert) − 0.05
    otherwise               unresolved at this n (the power line says what n would resolve it)

and the price line: tokens the document adds to every request, and tool calls per
case in each arm — the cost side of the same decision.

    python3 -m training.harness.knowledge_arm --base Qwen/Qwen2.5-3B-Instruct \\
        --adapter email-full=adapters/email-full --knowledge knowledge/email-triage.md
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

from training.harness import bar
from training.harness.accept_rank import draft_arm, preflight, serve, stop, wait_ready
from training.harness.suites import load

OUT = Path("session.json")
GAP = 0.05          # human-accuracy gap within which the harness counts as replacing weights


def with_knowledge(suite, text: str):
    """The same suite with the document appended to the system prompt. The tool block,
    the tags, the answer function and the verdict rule are the corpus's, byte for byte."""
    return dataclasses.replace(suite, name=f"{suite.name}+kb",
                               system=suite.system.rstrip() + "\n\n" + text.strip())


def passed(records: list[dict]) -> dict:
    return {r["id"]: bool(r.get("correct")) for r in records if "error" not in r}


def human_acc(records: list[dict]) -> float:
    h = [r for r in records if r.get("human") and "error" not in r]
    return sum(bool(r.get("correct")) for r in h) / len(h) if h else float("nan")


def verdict(base: list[dict], kb: list[dict], expert: list[dict] | None, gap: float = GAP) -> dict:
    """The pre-registered reading of three arms. A NaN accuracy or a missing expert arm
    leaves the corresponding claim unresolved rather than decided."""
    out = {"kb_vs_base": bar.compare(passed(kb), passed(base)),
           "human": {"base": human_acc(base), "kb": human_acc(kb)}}
    c = out["kb_vs_base"]
    out["kb_pays"] = bool(c["p_value"] < 0.05 and c["only_a"] > c["only_b"])
    if expert is None:
        out.update(weights_needed=None, harness_replaces_weights=None,
                   reading="no expert arm — the weights side of the question was not measured")
        return out
    e = bar.compare(passed(expert), passed(kb))
    out["expert_vs_kb"] = e
    out["human"]["expert"] = human_acc(expert)
    out["weights_needed"] = bool(e["p_value"] < 0.05 and e["only_a"] > e["only_b"])
    hk, he = out["human"]["kb"], out["human"]["expert"]
    out["harness_replaces_weights"] = bool(not out["weights_needed"] and hk == hk and he == he
                                           and hk >= he - gap)
    if out["weights_needed"]:
        out["reading"] = (f"WEIGHTS NEEDED: the expert beats base+kb {e['only_a']}:{e['only_b']} "
                          f"(p={e['p_value']}); the document {'pays' if out['kb_pays'] else 'does not pay'} "
                          f"against the plain base ({c['only_a']}:{c['only_b']}, p={c['p_value']})")
    elif out["harness_replaces_weights"]:
        out["reading"] = (f"HARNESS REPLACES WEIGHTS on this region: base+kb human {hk:.3f} vs expert "
                          f"{he:.3f}, {e['only_a']}:{e['only_b']} p={e['p_value']}")
    else:
        out["reading"] = (f"UNRESOLVED at this n: expert vs base+kb {e['only_a']}:{e['only_b']} "
                          f"p={e['p_value']}, human gap {he - hk:+.3f}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[], help="name=path; the expert is --expert")
    ap.add_argument("--expert", default="email-full")
    ap.add_argument("--knowledge", default="knowledge/email-triage.md")
    ap.add_argument("--suite", default="email")
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    suite = load(args.suite)
    n, seed = args.n or suite.eval_n, args.seed or suite.eval_seed
    cases = suite.cases(n, seed)
    text = Path(args.knowledge).read_text()
    kb_suite = with_knowledge(suite, text)
    out = Path(args.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=args.base, expert=args.expert, suite=suite.name, n=len(cases), seed=seed,
               knowledge=args.knowledge, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.base)
    rec["kb_tokens"] = len(tok(text)["input_ids"])
    rec["kb_sha"] = __import__("hashlib").sha256(text.encode()).hexdigest()[:16]
    print(f"[kb] {args.knowledge}: {rec['kb_tokens']} tokens on every request", flush=True)
    save()

    adapters = dict(a.split("=", 1) for a in args.adapter)
    extra = ["--max-model-len", str(args.max_model_len), "--gpu-memory-utilization", "0.90"]
    if adapters:
        extra += ["--enable-lora", "--max-lora-rank", "16", "--max-loras", str(len(adapters)),
                  "--lora-modules", *[f"{k}={v}" for k, v in adapters.items()]]
    p = serve(args.base, extra)
    try:
        if not wait_ready(p):
            print("[kb] the server never came up", flush=True); return 1
        rec["preflight"] = preflight(args.base, tok, "draft")
        if not rec["preflight"].get("stop_included", True):
            print(f"[kb] preflight refused: {rec['preflight']}", flush=True); save(); return 1
        arms = [("base", args.base, suite), ("base+kb", args.base, kb_suite)]
        if args.expert in adapters:
            arms.append(("expert", args.expert, suite))
        else:
            print(f"[kb] no --adapter {args.expert}=…: the expert arm is not run", flush=True)
        for name, model, s in arms:
            a = rec["arms"].setdefault(name, {"model": model, "suite": s.name, "records": {}})
            done = a["records"]
            draft_arm(model, tok, s, cases, args.max_tokens, args.concurrency, done, save)
            rs = list(done.values())
            a.update(n=len(rs), errors=sum("error" in r for r in rs),
                     correct=sum(bool(r.get("correct")) for r in rs),
                     calls=sum(r.get("calls", 0) for r in rs), human=human_acc(rs))
            print(f"[kb] arm {name}: {a['correct']}/{a['n']} human {a['human']:.3f} "
                  f"calls {a['calls']} errors {a['errors']}", flush=True)
            save()
    finally:
        stop(p)
    A = rec["arms"]
    rec["verdict"] = verdict(list(A["base"]["records"].values()), list(A["base+kb"]["records"].values()),
                             list(A["expert"]["records"].values()) if "expert" in A else None)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[kb] {rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
