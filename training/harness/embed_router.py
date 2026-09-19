"""Milestone 2, arm 2 — the router as an embedding model of the members' corpora.

WHY THIS ARM. Arm 1, an n-gram model of each corpus, was safe on foreign text and lost every
legitimate request from an unseen sender — it learned the generator's `.com` — and recovered no
paraphrase, because to a lexical model a paraphrase of the member's question and a different task
are one thing **[ran]** M2. Telling those apart is semantics.

WHAT IT IS (docs/FOUNDATIONS.md §8.5). Each released member's corpus requests — as the router sees
them, the proxy's tool block cut off — are embedded once. A request $x$ is scored against member
$m$ by the mean cosine to its $k$ nearest corpus requests,

    s_m(x) = (1/k) Σ_{j ∈ kNN_m(x)} ⟨e(x), e(c_j)⟩ ,       m̂ = argmax_m s_m(x),

and it is served by $m̂$ iff $s_{m̂}(x) ≥ τ_{m̂}$, with $τ_m$ the 1st percentile of the same score
over a 20 % split of $m$'s corpus held out of the index. Otherwise: out, to the frontier.

THE TASK, NOT THE CONTENT. Both released members read one inbox; most of every request is a listing
both corpora are full of, and a plain embedding of it says "this is about an email". The encoder is
an instruction-following one, and every text — corpus and request alike — is embedded under one
instruction: *what task is being asked*. That is the design's one bet, fixed before any number.

NO MODEL RUNS ON THE USER'S MACHINE. The encoder is served on Colab through the chain; what runs in
tests is the decision rule over a deterministic stand-in encoder.

WHAT IT DOES NOT DECIDE: whether a recognised region is served locally — `route.REGIONS`' measured
`serve: local | out` still does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

K = 5                 # neighbours                       } fixed in the brief before any number:
PERCENTILE = 1.0      # τ = this percentile, held out    } results/M2b-embed-router-20260919/BRIEF.md
HELD_OUT = 0.2
INSTRUCTION = ("Instruct: Given a request sent to an assistant, represent the task the user is asking "
               "to be performed, not the content it is about\nQuery: ")


def _dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def _unit(v):
    n = math.sqrt(_dot(v, v)) or 1.0
    return [x / n for x in v]


class HashingEncoder:
    """A deterministic stand-in for tests: hashed word counts. `blake2b`, never Python's `hash()`,
    which is randomised per process — the bug that fails `evolving-memory`'s central test on 6 of
    30 seeds **[ran]**. It carries no semantics and is never a result."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in t.lower().split():
                v[int(hashlib.blake2b(w.encode(), digest_size=8).hexdigest(), 16) % self.dim] += 1.0
            out.append(_unit(v))
        return out


class TransformerEncoder:
    """Last-token pooling over an instruction-following embedding model, on the GPU it is given."""

    def __init__(self, model: str, batch: int = 32, max_len: int = 512):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch, self.batch, self.max_len = torch, batch, max_len
        self.tok = AutoTokenizer.from_pretrained(model, padding_side="left")
        self.model = AutoModel.from_pretrained(model, torch_dtype=torch.float16).cuda().eval()

    def encode(self, texts: list[str]) -> list[list[float]]:
        torch, out = self.torch, []
        for i in range(0, len(texts), self.batch):
            enc = self.tok([INSTRUCTION + t for t in texts[i:i + self.batch]], padding=True, truncation=True,
                           max_length=self.max_len, return_tensors="pt").to("cuda")
            with torch.no_grad():
                h = self.model(**enc).last_hidden_state[:, -1]          # left-padded: last is the end
            out += torch.nn.functional.normalize(h.float(), dim=-1).cpu().tolist()
        return out


class EmbedRouter:
    def __init__(self, corpora: dict[str, list[str]], encoder, seed: int = 0):
        rng = random.Random(seed)
        self.encoder, self.index, self.tau = encoder, {}, {}
        for name, texts in sorted(corpora.items()):
            texts = sorted(set(texts)); rng.shuffle(texts)
            cut = max(1, int(len(texts) * HELD_OUT))
            held, kept = texts[:cut], texts[cut:]
            self.index[name] = encoder.encode(kept)
            scores = sorted(self._score(name, v) for v in encoder.encode(held))
            self.tau[name] = scores[min(len(scores) - 1, int(len(scores) * PERCENTILE / 100))]
            self.held_scores = getattr(self, "held_scores", {})
            self.held_scores[name] = scores

    def _score(self, name: str, v) -> float:
        sims = sorted((_dot(v, c) for c in self.index[name]), reverse=True)[:K]
        return sum(sims) / len(sims)

    def explain_vec(self, v) -> dict:
        per = {m: {"score": self._score(m, v), "tau": self.tau[m]} for m in self.index}
        best = max(per, key=lambda m: per[m]["score"])
        return {"member": best if per[best]["score"] >= per[best]["tau"] else None, "nearest": best, "scores": per}

    def decide_many(self, texts: list[str]) -> list[str]:
        return [self.explain_vec(v)["member"] or "out" for v in self.encoder.encode(texts)]

    def explain_many(self, texts: list[str]) -> list[dict]:
        return [self.explain_vec(v) for v in self.encoder.encode(texts)]


def corpora_from_pool() -> dict[str, list[str]]:
    from training.harness.corpus_router import request_text
    from training.harness.train_pool import POOL
    out = {}
    for path, record in POOL.items():
        rows = [json.loads(line) for line in open(record["corpus"]) if line.strip()]
        out[Path(path).name] = [request_text(next(m["content"] for m in r["messages"] if m["role"] == "user"))
                                for r in rows]
    return out


def score_sets(decide_many, sets: dict) -> dict:
    out = {}
    for name, rows in sets.items():
        if name.startswith("_"):
            continue
        got = decide_many([t for t, _ in rows])
        right = wrong = lost = kept = 0
        for (_, truth), g in zip(rows, got):
            if truth == "out":
                wrong += g != "out"; kept += g == "out"
            else:
                right += g == truth; lost += g == "out"; wrong += g not in (truth, "out")
        out[name] = {"n": len(rows), "local_right_member": right, "misrouted_to_local": wrong,
                     "lost_local": lost, "abstained": kept}
    return out


def score_cases(cases: dict) -> dict:
    """The same table as `score_sets`, computed from the stored per-case decisions — so the summary
    can never disagree with the records it sits beside."""
    out = {}
    for name, rows in cases.items():
        right = wrong = lost = kept = 0
        for c in rows:
            g, truth = c["member"] or "out", c["truth"]
            if truth == "out":
                wrong += g != "out"; kept += g == "out"
            else:
                right += g == truth; lost += g == "out"; wrong += g not in (truth, "out")
        out[name] = {"n": len(rows), "local_right_member": right, "misrouted_to_local": wrong,
                     "lost_local": lost, "abstained": kept}
    return out


def verdict(res: dict) -> dict:
    foreign = ["C", "D", "E", "C2", "E2"]
    mis_foreign = sum(res[s]["misrouted_to_local"] for s in foreign)
    n_foreign = sum(res[s]["n"] for s in foreign)
    a, f, b = res["A"], res["F"], res["B"]
    safe = mis_foreign <= 60 and (n_foreign - mis_foreign) / n_foreign >= 0.95 and a["misrouted_to_local"] == 0
    keeps = a["lost_local"] <= 0.01 * a["n"] and f["lost_local"] <= 0.05 * f["n"]
    out = {"misrouted_foreign": mis_foreign, "of": n_foreign, "lost_A": a["lost_local"], "lost_F": f["lost_local"],
           "recovered_B": b["local_right_member"], "safe": safe, "keeps_real_looking_traffic": keeps,
           "passes": bool(safe and keeps)}
    out["reading"] = ("PASSES: safe on foreign text and keeps requests from unseen senders" if out["passes"] else
                      "NOT SAFE: serves foreign text locally" if not safe else
                      "SAFE AND LOSES REAL-LOOKING TRAFFIC: the same wall arm 1 hit")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen3-Embedding-0.6B", help="the embedding model")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--out", default="embed_router.json")
    a = ap.parse_args()
    from training.harness import router_sets
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"encoder": a.base, "params": {"k": K, "percentile": PERCENTILE, "held_out": HELD_OUT,
                                         "instruction": INSTRUCTION}, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out.write_text(json.dumps(rec, indent=1))
    enc = TransformerEncoder(a.base)
    probe = enc.encode(["Is this important?", "Does this matter?", "Write a haiku about rain."])
    rec["probe"] = {"paraphrase": round(_dot(probe[0], probe[1]), 4), "unrelated": round(_dot(probe[0], probe[2]), 4)}
    print(f"[route] probe {rec['probe']}", flush=True)
    router = EmbedRouter(corpora_from_pool(), enc)
    rec["tau"] = router.tau
    out.write_text(json.dumps(rec, indent=1))
    sets = {**router_sets.build(), **router_sets.build_fresh()}
    rec["sets"] = {k: len(v) for k, v in sets.items() if not k.startswith("_")}
    # KEEP THE SCORES, NOT THE VERDICTS. The first run of this arm stored one summary row per set;
    # it lost 120 of 120 on F and nothing on disk could say whether F sits a hair under τ (a
    # calibration problem) or far below it (a representation problem) [ran] 2026-09-19. A decision
    # is made per case and the record has to hold what it was made from.
    cases = {}
    for name, rows in sets.items():
        if name.startswith("_"):
            continue
        ex = router.explain_many([t for t, _ in rows])
        cases[name] = [{"truth": truth, "member": e["member"], "nearest": e["nearest"],
                        "scores": {m: round(s["score"], 4) for m, s in e["scores"].items()}}
                       for (_, truth), e in zip(rows, ex)]
    rec["cases"] = cases
    q = lambda v, f: round(v[min(len(v) - 1, int(len(v) * f))], 4)
    rec["held_out_scores"] = {m: {"n": len(v), "min": round(v[0], 4), "p01": q(v, .01), "p05": q(v, .05),
                                  "p50": q(v, .5), "max": round(v[-1], 4)} for m, v in router.held_scores.items()}
    out.write_text(json.dumps(rec, indent=1))                       # records before the summary
    rec["embed_router"] = score_cases(cases)
    out.write_text(json.dumps(rec, indent=1))
    for k, v in rec["embed_router"].items():
        print(f"[route] {k} n {v['n']} misrouted {v['misrouted_to_local']} lost {v['lost_local']} "
              f"abstained {v['abstained']} right {v['local_right_member']}", flush=True)
    rec["verdict"] = verdict(rec["embed_router"])
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[route] {rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
