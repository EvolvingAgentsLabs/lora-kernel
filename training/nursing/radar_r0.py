r"""Memory W3 — the radar R0 beside a lexical baseline, on queries that do not share the note's words.

RUNS ON COLAB, THROUGH THE CHAIN. The encoder is `training.harness.embed_router.TransformerEncoder`
(`Qwen/Qwen3-Embedding-0.6B` [read], fp16, last-token pooling) under ONE instruction — *represent the
situation this is for* (docs/MEMORY.md §2.2). No model runs on the user's machine: `--lexical-only`
is the one part that runs anywhere, because it loads none. Brief and verdict table:
results/M7-W3-radar-r0-20260919/BRIEF.md.

THE MATHEMATICS (docs/MEMORY.md §2.3; docs/FOUNDATIONS.md §7.1).

    s(n | q) = <e(q), e_when(n)> + beta <e(q), e_what(n)>          rank_q = position of the needed note
    recall@k = |{q : rank_q <= k}| / |Q|                           MRR = mean 1 / rank_q

R0 and the lexical baseline rank the SAME queries, so they are paired on *needed note in the top 3* —
exact two-sided sign test on discordant pairs, p = 2 Σ_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (`bar.compare`).
A query the word-matcher scores zero on every note has no rank: it counts as a miss, and is counted.

EVERY RANK IS PERSISTED AS IT LANDS, per query and per arm — a summary row cannot say whether a miss
sat at rank 4 or rank 60, and that is the difference between a threshold and a representation.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from memory.index import BETA, K, Index
from memory.notes import Library
from memory.runtime import Lexical
from training.harness import bar
from training.nursing import radar_queries
from training.nursing.library import ROOT

INSTRUCTION = ("Instruct: Given a note or a question from one clinical subdomain, represent the situation "
               "it is for, so that a question retrieves the note written for that situation\nQuery: ")
HEADROOM_CEILING = 0.95          # a lexical baseline at or above this leaves the radar no job to show
GATE_SET = "P"
# THE ABSOLUTE STANDARD, BESIDE THE PAIR. On P the word-matcher sits at the floor by construction
# (0.064 [ran], zero GPU: the queries were written not to share the note's words), so "beats lexical"
# alone is close to a formality. *Is this radar sufficient* is gated on its own number: the needed
# note in the top 3 for at least this share of P. Fixed before any R0 number existed.
SUFFICIENT = 0.80


def rank_of(ranking: list[str], target: str) -> int | None:
    return ranking.index(target) + 1 if target in ranking else None


def lexical_ranks(lib: Library, rows: list[dict]) -> list[dict]:
    lex, shelf_of = Lexical(lib), {i: n.shelf for i, n in lib.notes.items()}
    out = []
    for r in rows:
        t = r["target"]
        out.append({"id": r["id"], "rank": rank_of(lex.search(r["query"], None, len(lib.notes)), t),
                    "rank_in_shelf": rank_of(lex.search(r["query"], shelf_of[t], len(lib.notes)), t)})
    return out


def summarise(ranks: list[dict], key: str = "rank") -> dict:
    n = len(ranks)
    hit = lambda k: sum(1 for r in ranks if r[key] is not None and r[key] <= k)
    return {"n": n, "recall@1": round(hit(1) / n, 4), "recall@3": round(hit(K) / n, 4),
            "hits@3": hit(K), "unranked": sum(r[key] is None for r in ranks),
            "mrr": round(sum(1 / r[key] for r in ranks if r[key]) / n, 4)}


def in_top(ranks: list[dict], key: str = "rank") -> dict:
    return {r["id"]: r[key] is not None and r[key] <= K for r in ranks}


def headroom(lexical: dict) -> dict:
    r = lexical[GATE_SET]["recall@3"]
    return {"set": GATE_SET, "lexical_recall@3": r, "ceiling": HEADROOM_CEILING, "go": r < HEADROOM_CEILING,
            "reading": (f"GO: the word-matcher finds {r:.3f} of the needed notes in its top 3 — there is room above it"
                        if r < HEADROOM_CEILING else
                        f"NO-GO: the word-matcher is already at {r:.3f}; no radar can be shown to beat it on this set")}


def verdict(rec: dict) -> dict:
    pr = rec.get("pairs", {}).get(GATE_SET)
    if not rec.get("headroom", {}).get("go"):
        return {"passed": False, "reading": "VOID: no headroom on the gate set — nothing a radar does here can be read"}
    if not pr:
        return {"passed": False, "reading": "NOTHING RANKED: the encoder arm did not run"}
    state = ("tie" if not pr["different"] else "R0" if pr["only_a"] > pr["only_b"] else "lexical")
    r0, lx = rec["summary"]["r0"][GATE_SET]["recall@3"], rec["summary"]["lexical"][GATE_SET]["recall@3"]
    enough = r0 >= SUFFICIENT
    out = {"passed": state == "R0" and enough, "state": state, "sufficient": enough,
           "r0_recall@3": r0, "lexical_recall@3": lx, "standard": SUFFICIENT}
    out["reading"] = {
        "R0": (f"THE RADAR HAS A JOB AND DOES IT: recall@3 {r0} (standard {SUFFICIENT}) against the word-matcher's {lx}, "
               f"paired {pr['only_a']}:{pr['only_b']}" if enough else
               f"R0 BEATS A WORD-MATCHER AND IS NOT ENOUGH: recall@3 {r0} under the standard {SUFFICIENT} "
               f"(lexical {lx}, paired {pr['only_a']}:{pr['only_b']}) — read the misses' ranks; this is the gap R1 is for"),
        "tie": f"NO JOB SHOWN AT THIS LIBRARY SIZE: R0 {r0} against lexical {lx} is a tie ({pr['only_a']}:{pr['only_b']}) — "
               "W5 runs on the lexical searcher and R1 has nothing to compress",
        "lexical": f"THE WORD-MATCHER WINS: lexical {lx} against R0 {r0} ({pr['only_b']}:{pr['only_a']}) — a null, reported as one",
    }[state]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen3-Embedding-0.6B", help="the embedding model")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--beta", type=float, default=BETA)
    ap.add_argument("--lexical-only", action="store_true", help="the zero-GPU half: loads no model")
    ap.add_argument("--index-out", default="radar_r0.index.json")
    ap.add_argument("--out", default="radar_r0.json")
    a = ap.parse_args(argv)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    lib = Library.load(ROOT)
    sets = radar_queries.build(lib)
    rec = {"library": str(ROOT), "notes": len(lib.notes), "k": K, "beta": a.beta,
           "sets": {s: {"n": len(rows), "targets": len({r["target"] for r in rows}),
                        "overlap": radar_queries.overlap_summary(rows)} for s, rows in sets.items()},
           "queries": sets, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "ranks": {}, "summary": {}}

    def save():
        out.write_text(json.dumps(rec, indent=1))

    rec["ranks"]["lexical"] = {s: lexical_ranks(lib, rows) for s, rows in sets.items()}
    rec["summary"]["lexical"] = {s: summarise(v) for s, v in rec["ranks"]["lexical"].items()}
    rec["summary"]["lexical_in_shelf"] = {s: summarise(v, "rank_in_shelf") for s, v in rec["ranks"]["lexical"].items()}
    rec["headroom"] = headroom(rec["summary"]["lexical"])
    save()
    for s, v in rec["summary"]["lexical"].items():
        print(f"[radar] lexical {s}: recall@1 {v['recall@1']} recall@3 {v['recall@3']} mrr {v['mrr']} "
              f"unranked {v['unranked']}/{v['n']} · overlap mean {rec['sets'][s]['overlap']['mean']}", flush=True)
    print(f"[radar] headroom — {rec['headroom']['reading']}", flush=True)
    if a.lexical_only:
        rec["lexical_only"] = True
        save()
        return 0
    if not rec["headroom"]["go"]:
        rec["verdict"] = verdict(rec); rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
        print(f"[radar] {rec['verdict']['reading']}", flush=True)
        return 1

    from training.harness.embed_router import TransformerEncoder, _dot
    enc = TransformerEncoder(a.base, instruction=INSTRUCTION)
    rec["encoder"] = {"model": a.base, "instruction": INSTRUCTION}
    probe = enc.encode(["The line is clamped and still under its dressing.",
                        "Flow is shut off. Which way do I lift the clear film?", "Write a haiku about rain."])
    rec["probe"] = {"paraphrase": round(_dot(probe[0], probe[1]), 4), "unrelated": round(_dot(probe[0], probe[2]), 4)}
    print(f"[radar] probe {rec['probe']} dim {len(probe[0])}", flush=True)
    index = Index.build(lib, enc, encoder_name=a.base, beta=a.beta)
    index.save(a.index_out)
    rec["index"] = {"path": a.index_out, "dim": len(index.when[0]), "fingerprint": index.fingerprint}
    save()
    shelf_of = {i: n.shelf for i, n in lib.notes.items()}
    rec["ranks"]["r0"], rec["ranks"]["r0_when_only"] = {}, {}
    for s, rows in sets.items():
        vecs = enc.encode([r["query"] for r in rows])
        for arm, beta in (("r0", a.beta), ("r0_when_only", 0.0)):
            rec["ranks"][arm][s] = [
                {"id": r["id"], "rank": rank_of(index.rank_vec(v, None, beta), r["target"]),
                 "rank_in_shelf": rank_of(index.rank_vec(v, shelf_of[r["target"]], beta), r["target"])}
                for r, v in zip(rows, vecs)]
            save()                                                    # records before the summary
    for arm in ("r0", "r0_when_only"):
        rec["summary"][arm] = {s: summarise(v) for s, v in rec["ranks"][arm].items()}
        rec["summary"][arm + "_in_shelf"] = {s: summarise(v, "rank_in_shelf") for s, v in rec["ranks"][arm].items()}
        for s, v in rec["summary"][arm].items():
            print(f"[radar] {arm} {s}: recall@1 {v['recall@1']} recall@3 {v['recall@3']} mrr {v['mrr']}", flush=True)
    rec["pairs"] = {s: bar.compare(in_top(rec["ranks"]["r0"][s]), in_top(rec["ranks"]["lexical"][s])) for s in sets}
    rec["pairs_when_only_vs_r0"] = {s: bar.compare(in_top(rec["ranks"]["r0_when_only"][s]), in_top(rec["ranks"]["r0"][s]))
                                    for s in sets}
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for s, pr in rec["pairs"].items():
        print(f"[radar] {s} · R0 vs lexical, needed note in the top {K}: {pr['only_a']}:{pr['only_b']} p={pr['p_value']}", flush=True)
    print(f"[radar] {rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
