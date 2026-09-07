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
    Mid-answer positions — the acceptance a serving loop would see — need a
    prefill the provider may silently ignore, which is why `restarted` is
    measured per call and the report refuses those numbers when it fires.

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
import json
import sys
import time
from pathlib import Path

from alpha import cases as suite
from alpha.backends import BackendError, build


def lcp(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def offsets(text: str, positions: int, window: int) -> list[int]:
    """Draft points inside the target's own answer, evenly spaced.

    Position 0 is always included: it is the only one a router could use before
    any token exists, and it is therefore the one Phase B would actually run on.
    """
    usable = max(len(text) - window, 0)
    if positions <= 1 or usable == 0:
        return [0]
    step = usable / (positions - 1)
    return sorted({int(round(i * step)) for i in range(positions)})


def draft_at(model, case, prefix: str, max_tokens: int):
    """Answer the case, optionally continuing from `prefix`.

    A trailing assistant message is a prefill: the model is meant to continue
    that message rather than start a new one. Ollama's chat renderer does NOT
    honour it — a qwen drafter re-opened its own turn and restarted the answer
    [ran] 2026-09-07 — so nothing here assumes it worked. `restarted` measures
    it per call and the report discards mid-answer numbers when it fires.
    """
    messages = [{"role": "system", "content": suite.SYSTEM},
                {"role": "user", "content": case.prompt}]
    if prefix:
        messages.append({"role": "assistant", "content": prefix})
    return model.chat(messages, max_tokens=max_tokens)


def restarted(continuation: str, full_answer: str) -> bool:
    """The prefill failed and the model began the answer again."""
    head = full_answer[:8].strip()
    return bool(head) and continuation.lstrip().startswith(head)


def run(args) -> int:
    run_dir = Path(args.run_dir)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)

    target = build(args.target)
    drafters = [build(t) for t in args.drafters.split(",") if t]

    config = {
        "target": target.name, "drafters": [d.name for d in drafters],
        "split": args.split, "n": args.n, "window_chars": args.window,
        "positions": args.positions, "temperature": 0.0,
        "prompt": args.prompt, "prompt_version": suite.PROMPT_VERSION,
        "prompt_hash": suite.prompt_hash(args.prompt),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "identity": "alpha_char = lcp(draft, target_continuation) / window, greedy target",
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2))

    cs = suite.load(args.split, args.n, prompt=args.prompt)
    print(f"[alpha] target={target.name} drafters={len(drafters)} "
          f"cases={len(cs)} w={args.window} positions={args.positions} "
          f"-> {run_dir}", file=sys.stderr, flush=True)

    for i, case in enumerate(cs, 1):
        out_path = run_dir / "cases" / f"{case.case_id}.json"
        if out_path.exists() and not args.force:
            print(f"[{i:>3}/{len(cs)}] {case.case_id} — already on disk, kept",
                  file=sys.stderr, flush=True)
            continue

        t0 = time.time()
        try:
            t_reply = draft_at(target, case, "", args.max_tokens)
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
                       "seconds": round(t_reply.seconds, 2)},
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

        pts = offsets(answer, args.positions, args.window)[1:]  # 0 is measured below
        for d in drafters:
            try:
                own_reply = draft_at(d, case, "", args.max_tokens)
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
                per_pos = []
                for o in pts:
                    cont = draft_at(d, case, answer[:o], max(8, args.window // 2)).text
                    want = answer[o:o + args.window]
                    acc = lcp(cont, want)
                    per_pos.append({
                        "offset": o, "accepted": acc,
                        "alpha": round(acc / len(want), 4) if want else 0.0,
                        "restarted": restarted(cont, answer),
                    })
            except BackendError as e:
                print(f"[{i:>3}/{len(cs)}] {case.case_id} — {d.name} FAILED: {e}",
                      file=sys.stderr, flush=True)
                return 2
            mid = [p["alpha"] for p in per_pos]
            record["drafters"][d.name] = {
                "own_answer": own,
                "verified": suite.verify(own, case.truth),
                "thought_chars": len(own_reply.thinking),
                "truncated": own_reply.truncated,
                "alpha_at_0": round(at0, 4),
                "alpha_at_0_content": None if at0_content is None else round(at0_content, 4),
                "content_agreement": None if content_agreement is None else round(content_agreement, 4),
                "same_answer": suite.payload(own) is not None
                               and suite.payload(own) == suite.payload(answer),
                "agreement_chars": full_lcp,
                "agreement_fraction": round(full_lcp / len(answer), 4) if answer else 0.0,
                "alpha_mid_mean": round(sum(mid) / len(mid), 4) if mid else None,
                "restarted_fraction": round(
                    sum(p["restarted"] for p in per_pos) / len(per_pos), 3) if per_pos else None,
                "positions": per_pos,
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
    ap.add_argument("--positions", type=int, default=1,
                    help="1 = position 0 only, which needs no prefill; >1 adds "
                         "mid-answer positions whose validity `restarted` decides")
    ap.add_argument("--max-tokens", type=int, default=700,
                    help="generous on purpose: the reasoning channel is emitted "
                         "first and eats the budget before the answer starts")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--force", action="store_true", help="re-run cases already on disk")
    return run(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
