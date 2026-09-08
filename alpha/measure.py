"""The acceptance surface, measured without a sampler.

THE IDENTITY THIS RESTS ON
    At temperature 0 the target's distribution is one-hot, so speculative
    decoding's acceptance test — accept the draft token with probability
    min(1, p_target/p_draft) — reduces to equality. The accepted prefix IS the
    longest common prefix between the draft and the target's greedy continuation.
    Greedy decoding is prefix-consistent, so ONE target generation per case
    carries the ground-truth continuation at every position inside it, and any
    number of candidate drafters can be scored against it for free.

WHAT THE PRIMARY NUMBER IS, AND WHY IT NEEDS NO PREFILL
    In Phase B the router picks an expert BEFORE a token exists, so the number
    the architecture actually runs on is agreement from position 0: how far the
    candidate's own answer follows the target's before it first diverges. That
    needs one target generation and one candidate generation per case and works
    on every provider.
WHAT IS MEASURED IN CHARACTERS AND WHY
    A frontier target does not share the base model's vocabulary, so token-level
    acceptance against it is undefined. The instrument therefore measures the
    longest common prefix in CHARACTERS over a window `w`. That is sound as a
    distillation score and unsound as a speedup claim. Do not convert one into
    the other.

THREE WORKSPACE RULES ARE BUILT INTO THIS FILE
    * every case is persisted as it lands, so a killed run keeps what it bought;
    * the run never hides its position — one line per case, unbuffered, to stderr;
    * no metric comes from stdout. Every number in the report is read back from
      the run directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from alpha import cases as suite
from alpha.backends import BackendError, Reply, build

CACHE = Path("results/.answers")


def cached(model, case, max_tokens: int, prompt_kind: str):
    """Greedy answers are deterministic, so the same model on the same prompt is
    asked once and reused across runs.

    This exists for one reason: after S1 failed its headroom gate, the next step
    is a DIFFERENT TARGET on the same cases — and re-generating four local
    candidates for every target is eight minutes of wall clock buying nothing.
    """
    key = f"{model.name}|{prompt_kind}|{suite.prompt_hash(prompt_kind)}|{case.case_id}|{max_tokens}"
    path = CACHE / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")
    if path.exists():
        d = json.loads(path.read_text())
        return Reply(text=d["text"], thinking=d.get("thinking", ""),
                     prompt_tokens=d.get("tokens_in", 0),
                     completion_tokens=d.get("tokens_out", 0),
                     seconds=0.0, truncated=d.get("truncated", False))
    r = answer(model, case, max_tokens)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "key": key, "text": r.text, "thinking": r.thinking,
        "tokens_in": r.prompt_tokens, "tokens_out": r.completion_tokens,
        "truncated": r.truncated}, indent=2))
    return r


def lcp(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n



def answer(model, case, max_tokens: int):
    """One greedy answer to one case.

    Mid-answer draft positions used to live here and were removed: ollama's chat
    renderer ignores an assistant prefill, so they never produced a usable number
    on this machine, and the promotion criterion reads answers rather than
    characters. The finding survives in EXPERIMENT_PLAN.md §3 and C6; the dead
    code does not.
    """
    return model.chat([{"role": "system", "content": suite.SYSTEM},
                       {"role": "user", "content": case.prompt}],
                      max_tokens=max_tokens)



def run(args) -> int:
    run_dir = Path(args.run_dir)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)

    target = build(args.target)
    drafters = [build(t) for t in args.drafters.split(",") if t]

    config = {
        "target": target.name, "drafters": [d.name for d in drafters],
        "split": args.split, "n": args.n, "window_chars": args.window,
 "temperature": 0.0,
        "target_max_tokens": args.target_max_tokens, "max_tokens": args.max_tokens,
        "prompt": args.prompt, "prompt_version": suite.PROMPT_VERSION,
        "prompt_hash": suite.prompt_hash(args.prompt),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "identity": "alpha_char = lcp(draft, target_continuation) / window, greedy target",
        # A declared price, not a scraped one: the bill has to be reconstructible
        # from the run's own record.
        "usd_per_mtok_in": args.usd_per_mtok_in,
        "usd_per_mtok_out": args.usd_per_mtok_out,
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2))

    cs = suite.load(args.split, args.n, prompt=args.prompt)
    print(f"[alpha] target={target.name} drafters={len(drafters)} "
          f"cases={len(cs)} w={args.window} "
          f"-> {run_dir}", file=sys.stderr, flush=True)

    for i, case in enumerate(cs, 1):
        out_path = run_dir / "cases" / f"{case.case_id}.json"
        if out_path.exists() and not args.force:
            print(f"[{i:>3}/{len(cs)}] {case.case_id} — already on disk, kept",
                  file=sys.stderr, flush=True)
            continue

        t0 = time.time()
        try:
            t_reply = cached(target, case, args.target_max_tokens, args.prompt)
            answer = t_reply.text
        except BackendError as e:
            print(f"[{i:>3}/{len(cs)}] {case.case_id} — TARGET FAILED: {e}",
                  file=sys.stderr, flush=True)
            return 2

        target_v = suite.verify(answer, case.truth)
        record = {
            "case_id": case.case_id, "region": case.region,
            "truth": sorted(case.truth),
            "target": {"name": target.name, "answer": answer, "verified": target_v,
                       "thought_chars": len(t_reply.thinking),
                       "truncated": t_reply.truncated,
                       "seconds": round(t_reply.seconds, 2),
                       "tokens_in": t_reply.prompt_tokens,
                       "tokens_out": t_reply.completion_tokens},
            "drafters": {},
        }
        if not answer.strip():
            # An empty answer channel is an instrument failure, not a model
            # failure: the budget was eaten by the reasoning channel. Scoring α
            # against it would measure the harness and call it capability.
            print(f"[{i:>3}/{len(cs)}] {case.case_id} — TARGET EMPTY ANSWER "
                  f"({len(t_reply.thinking)} chars of thinking, "
                  f"truncated={t_reply.truncated}). Raise --max-tokens.",
                  file=sys.stderr, flush=True)
            return 3

        for d in drafters:
            try:
                own_reply = cached(d, case, args.max_tokens, args.prompt)
                own = own_reply.text
                # POSITION 0 — the number Phase B runs on. No prefill involved.
                head = answer[:args.window]
                at0 = lcp(own, head) / len(head) if head else 0.0
                full_lcp = lcp(own, answer)
                # THE PAYLOAD — the same measurement over the part of the stream
                # the answer format does not determine. Both sides start at their
                # own marker, so a markdown fence or a missing space is not
                # allowed to look like a disagreement about the answer.
                t_pay, d_pay = suite.payload(answer), suite.payload(own)
                if t_pay is None or d_pay is None:
                    at0_content, content_agreement = None, None
                else:
                    c_head = t_pay[:args.window]
                    if not t_pay:
                        # "nothing is missing" is a real answer with an empty
                        # payload. Scoring it 0.0 would invent a disagreement
                        # between two models that said the same thing.
                        at0_content = content_agreement = 1.0 if not d_pay else 0.0
                    else:
                        at0_content = lcp(d_pay, c_head) / len(c_head)
                        content_agreement = lcp(d_pay, t_pay) / len(t_pay)
            except BackendError as e:
                print(f"[{i:>3}/{len(cs)}] {case.case_id} — {d.name} FAILED: {e}",
                      file=sys.stderr, flush=True)
                return 2
            record["drafters"][d.name] = {
                "own_answer": own,
                "verified": suite.verify(own, case.truth),
                "thought_chars": len(own_reply.thinking),
                "tokens_in": own_reply.prompt_tokens,
                "tokens_out": own_reply.completion_tokens,
                "truncated": own_reply.truncated,
                "alpha_at_0": round(at0, 4),
                "alpha_at_0_content": None if at0_content is None else round(at0_content, 4),
                "content_agreement": None if content_agreement is None else round(content_agreement, 4),
                "same_answer": suite.payload(own) is not None
                               and suite.payload(own) == suite.payload(answer),
                "agreement_chars": full_lcp,
                "agreement_fraction": round(full_lcp / len(answer), 4) if answer else 0.0,
            }

        out_path.write_text(json.dumps(record, indent=2))
        line = " ".join(
            f"{n.split(':')[-1]}:α0={r['alpha_at_0']:.2f}"
            f"/αc={'  n/a' if r['alpha_at_0_content'] is None else format(r['alpha_at_0_content'], '.2f')}"
            f"/v={int(r['verified']['passed'])}"
            for n, r in record["drafters"].items())
        print(f"[{i:>3}/{len(cs)}] {case.case_id} [{case.region}] "
              f"target_v={int(target_v['passed'])} {line} ({time.time()-t0:.1f}s)",
              file=sys.stderr, flush=True)

    (run_dir / "config.json").write_text(json.dumps(
        {**config, "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    print(f"[alpha] done — {run_dir}/cases", file=sys.stderr, flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True, help="ollama:<tag> or openai:<model>")
    ap.add_argument("--drafters", required=True, help="comma-separated backend tags")
    ap.add_argument("--split", default="held_out")
    ap.add_argument("--prompt", default="canonical", choices=["canonical", "frozen"],
                    help="canonical = the context compiler that produced this "
                         "workspace's published ladder; frozen = ours")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--window", type=int, default=24, help="draft window, characters")
    ap.add_argument("--target-max-tokens", type=int, default=0,
                    help="the target's own budget; defaults to --max-tokens. A "
                         "thinking target emits its reasoning first and returned "
                         "9 of 20 answers truncated at 700 [ran], and giving it a "
                         "separate budget keeps the drafters' cached answers valid")
    ap.add_argument("--max-tokens", type=int, default=700,
                    help="generous on purpose: the reasoning channel is emitted "
                         "first and eats the budget before the answer starts")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--force", action="store_true", help="re-run cases already on disk")
    ap.add_argument("--usd-per-mtok-in", type=float, default=0.0,
                    help="declared target price, written into the run config")
    ap.add_argument("--usd-per-mtok-out", type=float, default=0.0)
    args = ap.parse_args()
    if not args.target_max_tokens:
        args.target_max_tokens = args.max_tokens
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
