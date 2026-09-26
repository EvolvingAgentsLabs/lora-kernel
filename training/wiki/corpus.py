r"""W9's sets: the evaluation world and its questions, and a training corpus that never touches either.

    python -m training.wiki.corpus --eval     knowledge/distributor-wiki/ (world EVAL_SEED) and
                                              training/wiki/data/eval.jsonl (the "eval" wording)
    python -m training.wiki.corpus --train    training/wiki/data/train.jsonl — oracle walks over
                                              TRAIN_WORLDS, the "train" wording, rendered by the real loop
    python -m training.wiki.corpus --comparisons  training/wiki/data/train_cmp.jsonl — B5: W9's corpus row for
                                              row, plus CMP_MIX comparison walks per training world; gated
                                              against eval.jsonl AND eval_hard.jsonl

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
    G4  no value is in a question: the answer is read, never copied from the ask. A CHOICE (a row with
        `check.never`, B3's comparisons) offers both names by design, so what must not be in the ask is
        what decides it: every number of the deciding statements, the offered names struck from them
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
TRAIN_MIX = {f: 1 for f, (_, _, block) in qs.FAMILY.items() if block != "C"}   # W9's corpus, frozen: B3's comparisons are evaluation only
TRAIN_ROWS = 600
CMP_MIX = {"compare-lead": 2, "compare-pack": 2}   # B5: 128 comparison walks on top of W9's 600 — one unknown, the comparisons
WINDOW = 1536


def eval_rows() -> list[dict]:
    return qs.rows(wd.build(wd.EVAL_SEED), "eval", qs.EVAL_MIX, wd.EVAL_SEED)


def hard_rows() -> list[dict]:
    return qs.rows(wd.build(wd.EVAL_SEED), "eval", qs.HARD_MIX, wd.EVAL_SEED + 1)


def walks(mix: dict[str, int], salt: int = 0) -> list[dict]:
    out = []
    for seed in TRAIN_WORLDS:
        w = wd.build(seed)
        lib = w.library()
        for r in qs.rows(w, "train", mix, seed + salt):
            conv = wa.conversation(lib, r)
            final, conv, chain = wa.walk(lib, r, wa.oracle_gen(r, conv), conv)
            g = gr.grade(r, final, conv)
            out.append({**r, "grade": g["state"], "refused": chain["refused"],
                        "messages": [{"role": "system", "content": prompt.SYSTEM_WIKI},
                                     {"role": "user", "content": prompt.user_text_wiki(r["question"])},
                                     {"role": "assistant", "content": chain["text"]}]})
    return out


def train_rows() -> list[dict]:
    out = walks(TRAIN_MIX)
    random.Random(20260924).shuffle(out)
    return out[:TRAIN_ROWS]


def cmp_rows() -> list[dict]:
    """W9's corpus unchanged, then comparison walks (a different draw per world: `salt`), shuffled together."""
    out = train_rows() + [{**r, "case_id": r["case_id"].replace("-train-", "-traincmp-")} for r in walks(CMP_MIX, salt=500_000)]
    random.Random(20260926).shuffle(out)
    return out


_LIBS: dict = {}


def asked(r: dict) -> list[str]:
    """What G4 forbids in the question: the answer's tokens, or — for a choice — the values that decide it."""
    names = r["check"]["tokens"] + r["check"].get("never", [])
    if not r["check"].get("never") or not all(gr._has(r["question"], n) for n in names):
        return r["check"]["tokens"]
    lib = _LIBS.setdefault(r["world"], wd.build(r["world"]).library())
    anchor, out = r["support"][1], []
    for st in r["plan"]:
        if st[0] == "open" and len(st) == 3 and st[2] == anchor:
            text = lib[st[1]].statement(anchor).text
            for n in names:
                text = text.replace(n, "")
            out += gr._NUM.findall(text)
    assert out, f"{r['case_id']}: a choice with no deciding value"
    return out


def gate(train: list[dict], evals: list[dict]) -> dict:
    eval_q = {r["question"] for r in evals}
    eval_ph = {p for f in qs.PHRASINGS.values() for p in f["eval"]}
    train_ph = {p for f in qs.PHRASINGS.values() for p in f["train"]}
    g = {"G1_eval_world_in_corpus": sum(r["world"] == wd.EVAL_SEED for r in train),
         "G2_shared_phrasing_templates": len(eval_ph & train_ph),
         "G2_eval_question_in_corpus": sum(r["question"] in eval_q for r in train),
         "G3_not_verified": sum(r["grade"] != "right" or r["refused"] for r in train),
         "G4_value_in_question": sum(any(gr._has(r["question"], t) for t in asked(r)) for r in train + evals),
         "G5_over_window": sum(count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) >= WINDOW for r in train),
         "max_tokens": max(count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) for r in train),
         "rows": len(train), "families": sorted({r["family"] for r in train})}
    g["passed"] = all(v == 0 for k, v in g.items() if k.startswith("G"))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--hard", action="store_true", help="data/eval_hard.jsonl: B3's comparison band on the evaluation world")
    ap.add_argument("--comparisons", action="store_true", help="data/train_cmp.jsonl: B5's corpus, W9's plus comparisons")
    a = ap.parse_args()
    wa.DATA.mkdir(parents=True, exist_ok=True)
    if a.eval:
        wd.build(wd.EVAL_SEED).write(wa.LIBRARY)
        rows = eval_rows()
        (wa.DATA / "eval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"[wiki] evaluation world {wd.EVAL_SEED} → {wa.LIBRARY}, {len(rows)} questions, "
              f"headline {sum(qs.headline(r) for r in rows)}", flush=True)
    if a.hard:
        rows = hard_rows()
        (wa.DATA / "eval_hard.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"[wiki] hard band: {len(rows)} comparison questions on world {wd.EVAL_SEED}", flush=True)
    if a.train:
        train = train_rows()
        g = gate(train, eval_rows())
        (wa.DATA / "train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train))
        (wa.DATA / "gate.json").write_text(json.dumps(g, indent=1))
        print(f"[wiki] corpus {len(train)} rows from {len(TRAIN_WORLDS)} worlds · gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    if a.comparisons:
        train = cmp_rows()
        g = gate(train, eval_rows() + hard_rows())
        (wa.DATA / "train_cmp.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train))
        (wa.DATA / "gate_cmp.json").write_text(json.dumps(g, indent=1))
        print(f"[wiki] comparison corpus {len(train)} rows · gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
