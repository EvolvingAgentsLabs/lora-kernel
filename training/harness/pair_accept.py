r"""Milestone 4 (B4) — does the large half's LoRA raise acceptance of the small half's drafts?

The pair (docs/ARCHITECTURE.md §3): per subdomain a LoRA on a small model drafts and a LoRA on a large one verifies.
Speculative decoding at temperature 0 accepts a drafted token iff it is the verifier's rank-1 token there, so the
number that prices the pair is **acceptance** — `accept_rank.score_span`, the instrument P55 built: the verifier is
asked for `prompt_logprobs` over the draft, and each drafted token is accepted iff it is the verifier's rank-1.

    drafts    the small member's own walks, recorded with their spans (`wiki_arm` records, `spans`): only what
              the MODEL wrote is scored — the referee's results in between are context, not drafts
    arms      the bare large (`--base`) and the large + its LoRA (`--member name=path`), same drafts, same prompts

VERDICT (milestone 4's gate), written before the run (results/B4-gemma4-pair-acceptance-20260926/BRIEF.md): per draft
record, the arm with the higher accepted fraction; exact two-sided sign test on the discordant records,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$: `large+LoRA vs large` must be an improvement. Beside: pooled
α (accepted / drafted tokens) per arm, the longest accepted prefix per span, by question set.
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from training.harness import family


def draft_records(path: str, arm: str) -> list[dict]:
    rec = json.loads(Path(path).read_text())
    return [r for r in rec["arms"][arm].values() if "error" not in r and r.get("spans")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=family.LARGE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--member", required=True, help="name=path of the large half's LoRA")
    ap.add_argument("--drafts", action="append", required=True, help="records.json:arm:rows — e.g. h.json:withlib-s1:eval_hard")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="pair_accept.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, member=a.member, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1))
    from memory import prompt
    from training.harness.accept_rank import score_span, serve, stop, wait_ready
    from training.harness.verify_substrate import identity
    from training.wiki import wiki_arm as wa
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    name, _, path = a.member.partition("=")
    work = []
    for spec in a.drafts:
        f, arm, rows = spec.split(":")
        q = {r["case_id"]: r for r in wa.load_rows(rows)}
        work += [(rows, d, q[d["id"]]) for d in draft_records(f, arm)]
    rec["drafts"] = len(work)
    srv = serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora",
                         "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", a.member])
    try:
        if not wait_ready(srv):
            rec["stopped"] = "the large never came up"
        else:
            rec["G1"] = identity(a.base, name, tok)
            print(f"[pool] G1 {name}: {'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not rec["G1"]["applied"]:
                rec["stopped"] = "G1: the large half's LoRA is not applied"
            for arm, model in (("large", a.base), ("large+lora", name)) if rec["G1"].get("applied") else ():
                slot = rec["arms"].setdefault(arm, {})

                def one(item, model=model):
                    rows, d, row = item
                    head = tok.apply_chat_template([{"role": "system", "content": prompt.SYSTEM_WIKI},
                                                    {"role": "user", "content": prompt.user_text_wiki(row["question"])}],
                                                   tokenize=False, add_generation_prompt=True, enable_thinking=False)
                    spans = [score_span(model, tok, head + d["text"][:s["at"]], s["text"]) for s in d["spans"] if s["text"]]
                    ok = [s for s in spans if "error" not in s]
                    tokens, acc = sum(s["tokens"] for s in ok), sum(s["accepted"] for s in ok)
                    return {"id": d["id"], "rows": rows, "tokens": tokens, "accepted": acc,
                            "alpha": round(acc / tokens, 4) if tokens else None, "errors": len(spans) - len(ok),
                            "lcp": [s["lcp"] for s in ok]}
                todo = [w for w in work if w[1]["id"] not in slot]
                n = 0
                with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
                    for fut in as_completed([ex.submit(one, w) for w in todo]):
                        r = fut.result(); slot[r["id"]] = r; n += 1
                        if n % 20 == 0 or n == len(todo):
                            save()
                            t = sum(x["tokens"] for x in slot.values()); acc = sum(x["accepted"] for x in slot.values())
                            print(f"[pair] {arm} {len(slot)}/{len(work)} alpha {acc / max(1, t):.3f}", flush=True)
    finally:
        stop(srv)
    L, M = rec["arms"].get("large", {}), rec["arms"].get("large+lora", {})
    ids = [i for i in L if i in M and L[i]["alpha"] is not None and M[i]["alpha"] is not None]
    b = sum(M[i]["alpha"] > L[i]["alpha"] for i in ids); c = sum(M[i]["alpha"] < L[i]["alpha"] for i in ids)
    from math import comb
    n = b + c
    p = min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0
    pooled = {k: round(sum(x["accepted"] for x in v.values()) / max(1, sum(x["tokens"] for x in v.values())), 4)
              for k, v in (("large", L), ("large+lora", M))}
    state = "improvement" if (p < 0.05 and b > c) else "REGRESSION" if (p < 0.05 and c > b) else "tie"
    rec["verdict"] = {"pooled_alpha": pooled, "records": len(ids), "lora_higher": b, "bare_higher": c, "p_value": round(p, 5),
                      "state": state, "reading": (f"MILESTONE 4 PASSES: the large half's LoRA raises acceptance ({b}:{c}, p={p:.4f}; "
                                                  f"α {pooled['large']} → {pooled['large+lora']})" if state == "improvement" else
                                                  f"MILESTONE 4 NOT PASSED: large+LoRA vs large is {state} ({b}:{c}, p={p:.4f}; "
                                                  f"α {pooled['large']} → {pooled['large+lora']})")}
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[pair] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
