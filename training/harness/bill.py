r"""M6 — price the P41/P62 replay both ways, from records already on disk. Zero GPU, nothing re-run.

WHY THIS EXISTS. `docs/PLAN.md` milestone 6's gate is "the local share saves more than it costs, on
real traffic"; its state was `nothing` (`docs/FRAMEWORK.md` §5 row M) before this file. No real
traffic exists here, so this prices the closest thing on disk: the 240-case P41/P62 replay, which
splits cleanly into 150 email-full cases served locally and 90 fluids cases sent to
`google/gemini-3.8-flash` (confirmed in `frontier_fluids.json`'s own `model` field) — the design's
actual routing decision, not a hypothetical one. Full method and sourced rates:
`results/M6-bill-20260921/BRIEF.md`.

    python3 -m training.harness.bill --out results/M6-bill-20260921/bill.json

NOT PRICED HERE: the local GPU's own dollar cost — the rental rate could not be fetched live
(`BRIEF.md` says why, and is explicit that this is not guessed around). Everything this file computes
is stated as [ran] from real records; the one missing input is named, not invented.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# gemini-3.8-flash, paid tier, promotional through 2026-12-31 — ai.google.dev/gemini-api/docs/pricing,
# fetched 2026-09-21. $ per token, not per million, so the arithmetic below stays exact.
INPUT_RATE = 0.75 / 1_000_000
OUTPUT_RATE = 3.75 / 1_000_000


def _encoder():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def _ntok(enc, text: str) -> int:
    return len(enc.encode(text or "", disallowed_special=()))


def price_email(records: list[dict], enc) -> dict:
    """Exact, up to the tokenizer approximation: every assistant turn bills the conversation so far
    as input and its own text as output — the way a chat API actually bills a multi-turn call."""
    total_in = total_out = calls = 0
    for r in records:
        turns = r["transcript"]
        running = []
        for t in turns:
            if t["role"] == "assistant":
                total_in += sum(_ntok(enc, c) for c in running)
                total_out += _ntok(enc, t["content"])
                calls += 1
            running.append(t["content"] or "")
    return {"n": len(records), "assistant_calls": calls, "input_tokens": total_in,
            "output_tokens": total_out,
            "usd": round(total_in * INPUT_RATE + total_out * OUTPUT_RATE, 4)}


def price_fluids(records: list[dict], enc) -> dict:
    """A stated approximation (BRIEF.md): `statement` once as input, the whole `chain` at the output
    rate — biased toward OVERSTATING the frontier's real cost of these cases, never understating it."""
    total_in = total_out = 0
    for r in records:
        total_in += _ntok(enc, r.get("statement", ""))
        total_out += _ntok(enc, r.get("chain", ""))
    return {"n": len(records), "input_tokens": total_in, "output_tokens": total_out,
            "usd": round(total_in * INPUT_RATE + total_out * OUTPUT_RATE, 4),
            "note": "chain priced entirely at the output rate — overstates true cost, never understates"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", default="results/P41-routing-20260915/pool_results.json")
    ap.add_argument("--frontier", default="results/P41-routing-20260915/frontier_fluids.json")
    ap.add_argument("--replay", default="results/P62-route-per-request-20260918/replay.json")
    ap.add_argument("--out", default="results/M6-bill-20260921/bill.json")
    a = ap.parse_args()

    pool = json.loads(Path(a.pool).read_text())
    front = json.loads(Path(a.frontier).read_text())
    replay = json.loads(Path(a.replay).read_text())

    email_recs = pool["arms"]["email-full"]["records"]
    email_recs = email_recs if isinstance(email_recs, list) else list(email_recs.values())
    fluids_front_recs = front["records"]

    assert front["model"] == "google/gemini-3.8-flash", front["model"]  # the rate below is priced for this model, no other
    assert replay["by_request"]["out"] == len(fluids_front_recs) == 90, "the split this file assumes has moved"
    assert len(email_recs) == 150, "the split this file assumes has moved"

    enc = _encoder()
    email = price_email(email_recs, enc)
    fluids_if_frontier = price_fluids(fluids_front_recs, enc)
    # THE CEILING: if the 150 email cases had ALSO gone to the frontier instead of staying local —
    # priced the same exact-billing way, on the SAME transcripts (what the model would have had to
    # produce is not re-run; this reuses the local model's own transcript lengths as a stand-in for
    # what any model answering the same turns would exchange, an approximation stated once here).
    email_if_frontier_usd = round(email["input_tokens"] * INPUT_RATE + email["output_tokens"] * OUTPUT_RATE, 4)

    rec = {
        "started": "2026-09-21", "rates_source": "https://ai.google.dev/gemini-api/docs/pricing",
        "rates_fetched": "2026-09-21", "model_priced": front["model"],
        "input_rate_per_token": INPUT_RATE, "output_rate_per_token": OUTPUT_RATE,
        "tokenizer": "tiktoken cl100k_base (approximation — not the pool's or Gemini's own tokenizer)",
        "email_local_150": email,
        "fluids_frontier_90_actual_bill": fluids_if_frontier,
        "email_if_it_had_gone_to_frontier_too_usd": email_if_frontier_usd,
        "today_actual_frontier_bill_usd": fluids_if_frontier["usd"],
        "ceiling_if_everything_had_gone_to_frontier_usd": round(
            fluids_if_frontier["usd"] + email_if_frontier_usd, 4),
        "frontier_dollars_avoided_by_keeping_email_local_usd": email_if_frontier_usd,
        "local_gpu_dollar_cost": None,
        "local_gpu_dollar_cost_note": (
            "not priced — the Colab rental rate could not be fetched live (BRIEF.md). "
            "local_token_volume_for_rate_substitution below is what a real $/hour or $/token rate "
            "multiplies against."),
        "local_token_volume_for_rate_substitution": {
            "input_tokens": email["input_tokens"], "output_tokens": email["output_tokens"],
            "assistant_calls": email["assistant_calls"]},
        "finished": "2026-09-21",
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    print(f"[bill] today's actual frontier bill (90 fluids cases): ${rec['today_actual_frontier_bill_usd']}")
    print(f"[bill] frontier dollars avoided by keeping 150 email cases local: "
          f"${rec['frontier_dollars_avoided_by_keeping_email_local_usd']}")
    print(f"[bill] ceiling if everything had gone to the frontier: "
          f"${rec['ceiling_if_everything_had_gone_to_frontier_usd']}")
    print("[bill] local GPU dollar cost: NOT PRICED — rate could not be fetched live, see BRIEF.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
