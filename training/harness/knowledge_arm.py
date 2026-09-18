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


def verdict(base: list[dict], kb: list[dict], expert: list[dict] | None, gap: float = GAP,
            majority: float | None = None) -> dict:
    """The pre-registered reading of three arms. A NaN accuracy or a missing expert arm
    leaves the corresponding claim unresolved rather than decided.

    THE MAJORITY BAR IS A GUARD ADDED AFTER THE FIRST RUN, AND THE NUMBER IT GUARDS
    STANDS. P61 **[ran]** 2026-09-18: base+kb beat the base 164 : 74, $p = 0$, with
    **zero tool calls on 351 of 351** human messages — the document had flipped the
    base's default answer from NOT IMPORTANT (0.345) towards IMPORTANT (0.601), still
    under the always-IMPORTANT bar of 0.655. A sign test against a base that answers
    one word cannot tell a procedure followed from a default flipped; the bar can.
    `kb_pays` therefore also requires human(base+kb) > majority."""
    out = {"kb_vs_base": bar.compare(passed(kb), passed(base)),
           "human": {"base": human_acc(base), "kb": human_acc(kb)}, "majority": majority,
           "kb_calls": sum(r.get("calls", 0) for r in kb if r.get("human"))}
    c = out["kb_vs_base"]
    better = bool(c["p_value"] < 0.05 and c["only_a"] > c["only_b"])
    out["kb_above_bar"] = None if majority is None else bool(out["human"]["kb"] > majority)
    out["kb_pays"] = better and out["kb_above_bar"] is not False
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
        doc = ("pays" if out["kb_pays"] else
               f"does not pay — {c['only_a']}:{c['only_b']} over the base but human {hk:.3f} is under the "
               f"majority bar {majority:.3f}" if out["kb_above_bar"] is False else "does not pay")
        out["reading"] = (f"WEIGHTS NEEDED: the expert beats base+kb {e['only_a']}:{e['only_b']} "
                          f"(p={e['p_value']}); the document {doc} against the plain base "
                          f"({c['only_a']}:{c['only_b']}, p={c['p_value']}); base+kb made "
                          f"{out['kb_calls']} tool calls on human messages")
    elif out["harness_replaces_weights"]:
        out["reading"] = (f"HARNESS REPLACES WEIGHTS on this region: base+kb human {hk:.3f} vs expert "
                          f"{he:.3f}, {e['only_a']}:{e['only_b']} p={e['p_value']}")
    else:
        out["reading"] = (f"UNRESOLVED at this n: expert vs base+kb {e['only_a']}:{e['only_b']} "
                          f"p={e['p_value']}, human gap {he - hk:+.3f}")
    return out


def reread(path: Path, suite) -> dict:
    """Re-read a finished session's verdict with the majority bar; the arms are untouched."""
    rec = json.loads(path.read_text()); A = rec["arms"]
    cases = suite.cases(rec["n"], rec["seed"])
    rec["verdict"] = verdict(list(A["base"]["records"].values()), list(A["base+kb"]["records"].values()),
                             list(A["expert"]["records"].values()) if "expert" in A else None,
                             majority=suite.bar(cases))
    rec["reread"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    path.write_text(json.dumps(rec, indent=1))
    return rec["verdict"]


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
    ap.add_argument("--reread", action="store_true", help="re-read --out's verdict with the majority bar")
    args = ap.parse_args()

    suite = load(args.suite)
    if args.reread:
        v = reread(Path(args.out), suite)
        print(f"[kb] {v['reading']}", flush=True)
        return 0
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
                             list(A["expert"]["records"].values()) if "expert" in A else None,
                             majority=suite.bar(cases))
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[kb] {rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
