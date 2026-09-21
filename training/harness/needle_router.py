r"""Milestone 2, arm 3 — the router as `cactus-compute/needle`'s embedding.

WHY THIS ARM, NAMED BEFORE ANY NUMBER OF IT EXISTS. Arm 2 (`embed_router.py`,
`Qwen/Qwen3-Embedding-0.6B`) was not a size problem: "in this space, changing who writes moves a
request as far as changing what is asked" (`docs/RECORD.md` §2) — whole-request similarity does
not factor task from content, so an unseen sender and a member's own listing followed by another
task land in the same cosine range. Needle is read [read] (`https://github.com/cactus-compute/needle`,
fetched 2026-09-21, Apache-2.0) as a candidate not because it is smaller, but because it ships
the two pieces arm 2 was missing: a calibrated confidence head (a principled abstain, not an
ad hoc percentile-of-cosine τ) and local LoRA fine-tuning from a `query`/`answers` format — the
shape of the contrastive projection arm 2's own writeup named as what is left
(`docs/PLAN.md` milestone 2, `docs/FRAMEWORK.md` §9).

THE SAME GRADER AS ARM 2, NOT A NEW ONE. This file changes exactly one thing —
`embed_router.TransformerEncoder` becomes `NeedleEncoder` — and reuses `EmbedRouter`,
`score_cases`, `verdict` and `router_sets` unchanged, so a difference in the numbers is a
difference in the encoder, never in how the encoder is judged.

WHY THIS RUNS ON COLAB. `../../CLAUDE.md`: "no model runs on the user's machine." Needle ships a
CPU-native engine and does not need a GPU to embed a few hundred short strings — but the rule is
not "no model that needs a GPU", it is "no model", and this file does not carve itself an
exception. `chain_serve.sh` installs vLLM as its own gate regardless of what a module needs
(`docs/FRAMEWORK.md` §9's own note on this); `cactus-needle` installs beside it.

**Headroom, not a verdict.** This is the cheapest possible first look — one probe, one router
pass, the same eight sets arm 1 and arm 2 already ran, nothing frozen or iterated against. It
decides whether Needle is worth a real arm (its own BRIEF, its own falsifier written first), not
whether milestone 2 passes.

    python -m training.harness.needle_router --out needle_router.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.harness.embed_router import EmbedRouter, _dot, corpora_from_pool, score_cases

INSTRUCTION = ""     # Needle has no instruction-prefix convention like the Qwen embedder's;
                     # it is asked to embed the text as given, unmodified.


class NeedleEncoder:
    """`embed_router.TransformerEncoder`'s interface (`.encode(texts) -> list[list[float]]`),
    over `needle.Needle().embed(text)` — one call per text; Needle's C engine embeds one string
    at a time, so there is no batch call to reach for here."""

    def __init__(self, model: str | None = None):
        # NOT IN chain_serve.sh'S TRAINDEPS — that installs peft/trl/etc. for modules that
        # train; this arm trains nothing and needs one package the chain does not know about.
        # Self-installed here, once, printed so a run never reads as silence.
        try:
            import needle
        except ImportError:
            import subprocess
            print("[route] installing cactus-needle (not a TRAINDEPS package)", flush=True)
            subprocess.run(["pip", "install", "-q", "cactus-needle"], check=True)
            import needle
        self._needle = needle.Needle()          # default weights: Needle 3, auto-fetched
        self.model = model or "cactus-compute/needle3"

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._needle.embed(t) for t in texts]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # `--base` IS ALWAYS PASSED. chain_serve.sh's launch line is one shape for every module —
    # `--base $BASE $MARGS --out $RESULTS_NAME` — so a module this repo's own chain can run has
    # to accept the flag even when, as here, there is no vLLM base to name (`docs/FRAMEWORK.md`
    # §9: the chain's vLLM-install gate runs regardless of what a module needs).
    ap.add_argument("--base", default="none", help="unused — this module serves no vLLM base")
    ap.add_argument("--out", default="needle_router.json")
    a = ap.parse_args()
    from training.harness import router_sets

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"encoder": "cactus-compute/needle3", "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out.write_text(json.dumps(rec, indent=1))

    enc = NeedleEncoder()
    probe = enc.encode(["Is this important?", "Does this matter?", "Write a haiku about rain."])
    rec["probe"] = {"paraphrase": round(_dot(probe[0], probe[1]), 4),
                    "unrelated": round(_dot(probe[0], probe[2]), 4), "dim": len(probe[0])}
    print(f"[route] probe {rec['probe']}", flush=True)
    if rec["probe"]["paraphrase"] <= rec["probe"]["unrelated"]:
        rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        rec["verdict"] = {"passes": False, "reading": "ABORT: probe failed — paraphrase cosine "
                          "does not exceed unrelated cosine; the encoder or pooling is broken"}
        out.write_text(json.dumps(rec, indent=1))
        print(f"[route] {rec['verdict']['reading']}", flush=True)
        return 1

    router = EmbedRouter(corpora_from_pool(), enc)
    rec["tau"] = router.tau
    out.write_text(json.dumps(rec, indent=1))
    sets = {**router_sets.build(), **router_sets.build_fresh()}
    rec["sets"] = {k: len(v) for k, v in sets.items() if not k.startswith("_")}

    cases = {}
    for name, rows in sets.items():
        if name.startswith("_"):
            continue
        ex = router.explain_many([t for t, _ in rows])
        cases[name] = [{"truth": truth, "member": e["member"], "nearest": e["nearest"],
                        "scores": {m: round(s["score"], 4) for m, s in e["scores"].items()}}
                       for (_, truth), e in zip(rows, ex)]
        out.write_text(json.dumps({**rec, "cases": cases}, indent=1))     # records before the summary
        print(f"[route] {name}: {len(rows)} cases embedded", flush=True)
    rec["cases"] = cases
    q = lambda v, f: round(v[min(len(v) - 1, int(len(v) * f))], 4)
    rec["held_out_scores"] = {m: {"n": len(v), "min": round(v[0], 4), "p01": q(v, .01), "p05": q(v, .05),
                                  "p50": q(v, .5), "max": round(v[-1], 4)} for m, v in router.held_scores.items()}
    out.write_text(json.dumps(rec, indent=1))
    rec["needle_router"] = score_cases(cases)
    out.write_text(json.dumps(rec, indent=1))
    for k, v in rec["needle_router"].items():
        print(f"[route] {k} n {v['n']} misrouted {v['misrouted_to_local']} lost {v['lost_local']} "
              f"abstained {v['abstained']} right {v['local_right_member']}", flush=True)
    from training.harness.embed_router import verdict as _verdict
    rec["verdict"] = _verdict(rec["needle_router"])
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[route] {rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
