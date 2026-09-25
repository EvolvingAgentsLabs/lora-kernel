r"""W9's sets: the evaluation world and its questions, and a training corpus that never touches either.

    python -m training.wiki.corpus --eval     knowledge/distributor-wiki/ (world EVAL_SEED) and
                                              training/wiki/data/eval.jsonl (the "eval" wording)
    python -m training.wiki.corpus --train    training/wiki/data/train.jsonl — oracle walks over
                                              TRAIN_WORLDS, the "train" wording, rendered by the real loop

A CORPUS ROW IS WHAT SERVING PRODUCES. The oracle is a scripted model driven through `run_chain` with
the member's own referee (`wiki_arm.oracle_gen`), so the assistant turn — tags, `= result` lines, the
cited final line — is byte for byte what a served walk writes. System and user turn are the member's
(`memory.prompt.SYSTEM_WIKI`, `user_text_wiki`): a corpus must teach the prompt it will be served.

THE GATE (`gate`), each clause shown able to fail in tests/test_wiki.py:
    G1  no training world is the evaluation world
    G2  no training question is worded like an evaluation one (the two phrasing sets are disjoint, and
        no training question string occurs in the evaluation set)
    G3  every training row's walk is the oracle's and is verified by the grader — the corpus teaches
        only walks that cite a statement holding the answer
    G4  no value is in a question: the answer is read, never copied from the ask
    G5  every row fits the trainer's window (a word-and-mark proxy, `count_tokens`, under 1536)
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from memory import prompt
from memory.notes import count_tokens
from training.wiki import grade as gr
from training.wiki import questions as qs
from training.wiki import wiki_arm as wa
from training.wiki import world as wd

TRAIN_WORLDS = range(1000, 1032)
TRAIN_MIX = {f: 1 for f in qs.FAMILY}
TRAIN_ROWS = 600
WINDOW = 1536


def eval_rows() -> list[dict]:
    return qs.rows(wd.build(wd.EVAL_SEED), "eval", qs.EVAL_MIX, wd.EVAL_SEED)


def train_rows() -> list[dict]:
    out = []
    for seed in TRAIN_WORLDS:
        w = wd.build(seed)
        lib = w.library()
        for r in qs.rows(w, "train", TRAIN_MIX, seed):
            conv = wa.conversation(lib, r)
            final, conv, chain = wa.walk(lib, r, wa.oracle_gen(r, conv), conv)
            g = gr.grade(r, final, conv)
            out.append({**r, "grade": g["state"], "refused": chain["refused"],
                        "messages": [{"role": "system", "content": prompt.SYSTEM_WIKI},
                                     {"role": "user", "content": prompt.user_text_wiki(r["question"])},
                                     {"role": "assistant", "content": chain["text"]}]})
    random.Random(20260924).shuffle(out)
    return out[:TRAIN_ROWS]


def gate(train: list[dict], evals: list[dict]) -> dict:
    eval_q = {r["question"] for r in evals}
    eval_ph = {p for f in qs.PHRASINGS.values() for p in f["eval"]}
    train_ph = {p for f in qs.PHRASINGS.values() for p in f["train"]}
    g = {"G1_eval_world_in_corpus": sum(r["world"] == wd.EVAL_SEED for r in train),
         "G2_shared_phrasing_templates": len(eval_ph & train_ph),
         "G2_eval_question_in_corpus": sum(r["question"] in eval_q for r in train),
         "G3_not_verified": sum(r["grade"] != "right" or r["refused"] for r in train),
         "G4_value_in_question": sum(any(gr._has(r["question"], t) for t in r["check"]["tokens"]) for r in train + evals),
         "G5_over_window": sum(count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) >= WINDOW for r in train),
         "max_tokens": max(count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) for r in train),
         "rows": len(train), "families": sorted({r["family"] for r in train})}
    g["passed"] = all(v == 0 for k, v in g.items() if k.startswith("G"))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--train", action="store_true")
    a = ap.parse_args()
    wa.DATA.mkdir(parents=True, exist_ok=True)
    if a.eval:
        wd.build(wd.EVAL_SEED).write(wa.LIBRARY)
        rows = eval_rows()
        (wa.DATA / "eval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"[wiki] evaluation world {wd.EVAL_SEED} → {wa.LIBRARY}, {len(rows)} questions, "
              f"headline {sum(qs.headline(r) for r in rows)}", flush=True)
    if a.train:
        train = train_rows()
        g = gate(train, eval_rows())
        (wa.DATA / "train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train))
        (wa.DATA / "gate.json").write_text(json.dumps(g, indent=1))
        print(f"[wiki] corpus {len(train)} rows from {len(TRAIN_WORLDS)} worlds · gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
