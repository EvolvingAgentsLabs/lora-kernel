r"""RFT0 — rejection-sampling fine-tuning: the member's own walks, kept only where the strict grader says `right`.

WHY (results/RFT0-rejection-sampling-20261005/BRIEF.md). Two SFT corpus lines aimed at the wrong-statement citation
(REAL6, REAL7) and one at the format (FMT0) changed nothing **[ran]**: every one of them trained the member on the
ORACLE's walks. Reinforcement against a verifier trains on the member's OWN walks, scored; the cheapest falsifiable
version of that is on-policy rejection sampling: sample the served member on its own training questions, keep the walks
the strict grader verifies, train on them span-masked exactly as the oracle's walks were. GRPO only if this shows signal.

THE SAMPLER (session S1, one L4). `real-none-s0` (REAL4's member) served by vLLM under the SERVED runtime — the question's
full-text entry on every shelf, pages opened with their statements, `page_top = 8` (wiki_arm's `+page+top8`), the strict
guard — on EVERY question it was trained on (`real_questions.jsonl` + `real_none_questions.jsonl`, `knowledge/regs-train`),
k = 4 walks each at temperature 0.7, seeds 1…4, each through `run_chain` and graded by `grade.py` (cite="support").

    accepted   a walk graded `right` (an unanswerable question: a right `Not in my library.`) whose rendered turn is under
               the trainer's window (real_corpus.WINDOW); at most MAX_KEEP distinct walks per question, walks with no
               ERROR line first, then seed order
    spans      what the model wrote, as character spans of the assistant turn — `real_corpus.walk_rows`' rule; a span the
               runtime answered with an ERROR is kept out of the loss, as walk_rows keeps FMT0's injected mistake out
    persisted  per question, into `--out`; a rerun resumes every question already done (and retries transport errors)

THE HAND-BACK. The chain (training/harness/chain_serve.sh) fetches `--out` on every poll and at the end, and nothing else
of a run's files but its logs and `adapters_out.tgz`; so the accepted walks travel INSIDE `--out`, and the corpus is
assembled from it — on the VM at the end (into the record's `gate`) and, authoritatively, at zero GPU on this machine:

    python -m training.wiki.rft_sample --base google/gemma-4-E4B-it --member-prefix adapters/real-none-s --out rft_sample.json
    python -m training.wiki.rft_sample --assemble results/RFT0-rejection-sampling-20261005/rft_sample.json
        → training/wiki/data/train_real_rft.jsonl  (train_real_none.jsonl byte for byte, then the accepted self-walks)
        → training/wiki/data/gate_real_rft.json
    python -m training.wiki.rft_sample --verdict results/RFT0-rejection-sampling-20261005/rft0.json   # S2, as fixed

THE CAP (fixed before S1, BRIEF.md): the self-walks never outnumber the oracle's walks (MAX_SELF = 315 = the rows of
train_real_none.jsonl) — T must fit one sixty-minute A100 session. Coverage first: one walk per covered question (in a
fixed shuffled order), then second walks, until the cap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory import prompt
from memory.notes import Library, count_tokens
from training.wiki import grade as gr
from training.wiki import real_corpus as rc
from training.wiki import wiki_arm as wa

LIB = rc.LIB
DATA = rc.DATA
QUESTION_FILES = (DATA / "real_questions.jsonl", DATA / "real_none_questions.jsonl")
BASE_CORPUS = DATA / "train_real_none.jsonl"
OUT_NAME = "train_real_rft"
SEEDS = (1, 2, 3, 4)
TEMPERATURE = 0.7
PAGE_TOP = 8
MAX_KEEP = 2
MAX_SELF = 315
SHUFFLE_SEED = 20261005
SERVED = "member"                      # the LoRA's name in vLLM — a member is asked for by NAME, never by its path

# S2 (the scoring session is wiki_arm; this reads its record as the brief fixed it)
BASE_ARM, TREAT_ARM = "withlib-s0+page+top8", "withlib-s1+page+top8"
EVAL_ROWS = Path("results/PAGE0-page-top-20261002/questions.jsonl")


# ------------------------------------------------------------------ the questions, as walk_rows numbered them
def questions() -> list[dict]:
    """REAL4's training questions in walk_rows' order (`--walks --with-none`: the answerable, then the unanswerable), so
    a question's case id — and with it the conversation's opaque ids — is the one its oracle walk had."""
    return [json.loads(l) for f in QUESTION_FILES for l in f.read_text().splitlines() if l.strip()]


def question_row(q: dict, i: int) -> dict:
    """walk_rows' row for question `i`, without the oracle's plan."""
    if q.get("none"):
        return {"case_id": f"real3-train-none-{i}", "world": 0, "family": "none", "block": "none", "hops": 0,
                "shelf": "wiki", "question": q["question"], "support": None, "answer": "Not in my library.",
                "check": {"kind": "none", "tokens": []}}
    return {"case_id": f"real3-train-{i}", "world": 0, "family": f"real-{q['hops']}hop", "block": "R", "hops": q["hops"],
            "shelf": "wiki", "question": q["question"], "support": q["support"], "answer": q["answer"],
            "check": {"kind": "value", "tokens": q["tokens"], "cite": "support"}}


def served_conversation(lib: Library, ft, row: dict):
    """The runtime the member is served with now — wiki_arm's `+page+top8`, strict guard."""
    conv = wa.conversation(lib, row)
    conv.searcher, conv.first_query, conv.entry_all_shelves, conv.fallback = ft, row["question"], True, True
    conv.page_text, conv.page_top = True, PAGE_TOP
    return conv


def train_spans(chain: dict) -> tuple[list[list[int]], int]:
    """walk_rows' spans: every non-empty span the model wrote; one the runtime answered with an ERROR stays out of the loss
    (the recovery may be taught, never the mistake). Returns the spans and how many were masked."""
    text, out, masked = chain["text"], [], 0
    for sp in chain["spans"]:
        if not sp["text"]:
            continue
        end = sp["at"] + len(sp["text"])
        if text[end:].lstrip("\n").startswith("= ERROR"):
            masked += 1
            continue
        out.append([sp["at"], end])
    return out, masked


def training_row(row: dict, chain: dict, g: dict, seed: int) -> dict:
    spans, masked = train_spans(chain)
    return {**row, "case_id": f"{row['case_id']}-rft-s{seed}", "source": "rft", "seed": seed, "of": row["case_id"],
            "grade": g["state"], "refused": chain["refused"], "masked_error_spans": masked,
            "train_spans": spans,
            "messages": [{"role": "system", "content": prompt.SYSTEM_WIKI},
                         {"role": "user", "content": prompt.user_text_wiki(row["question"])},
                         {"role": "assistant", "content": chain["text"]}]}


def same_page_wrong(row: dict, g: dict) -> bool:
    """The failure RFT0 targets: the walk reached the supporting page and cited another statement on it."""
    return (g["state"] != "right" and bool(row.get("support")) and isinstance(g.get("cited"), list)
            and g["cited"][0] == row["support"][0] and g["cited"] != list(row["support"]))


# ------------------------------------------------------------------ one question, k walks
def sample_question(lib: Library, ft, q: dict, i: int, gen_for, seeds=SEEDS, temperature: float = TEMPERATURE,
                    max_keep: int = MAX_KEEP) -> dict:
    """`gen_for(system, user, walking, temperature=, seed=)` returns `gen(prefix)` — the served member, or a script."""
    row = question_row(q, i)
    rec = {"id": row["case_id"], "kind": row["check"]["kind"], "hops": row["hops"], "walks": [], "accepted": []}
    candidates = []
    for seed in seeds:
        try:
            final, conv, chain = wa.walk(lib, row, gen_for(prompt.SYSTEM_WIKI, prompt.user_text_wiki(row["question"]), True,
                                                           temperature=temperature, seed=seed),
                                         served_conversation(lib, ft, row))
        except wa.ContextExhausted:
            rec["walks"].append({"seed": seed, "state": "context"})
            continue
        except KeyError:                                      # a page no search shows: walk_rows drops these too
            rec["walks"].append({"seed": seed, "state": "unreachable"})
            continue
        except Exception as e:                                # transport — the question is retried, never scored
            return {**rec, "error": repr(e)[:160]}
        g = gr.grade(row, final, conv)
        tr = training_row(row, chain, g, seed)
        tokens = count_tokens(tr["messages"][1]["content"] + tr["messages"][2]["content"])
        w = {"seed": seed, "state": g["state"], "line": g["line"], "cited": g.get("cited"), "why": g.get("why"),
             "same_page_wrong": same_page_wrong(row, g), "refused": chain["refused"], "calls": chain["calls"],
             "ran_out": chain["ran_out"], "tokens": tokens, "over_window": tokens >= rc.WINDOW}
        rec["walks"].append(w)
        if g["state"] == "right" and not w["over_window"]:
            candidates.append(tr)
    seen, kept = set(), []
    # walks with no ERROR line first, then seed order (sorted is stable)
    for tr in sorted(candidates, key=lambda r: r["refused"] > 0):
        text = tr["messages"][2]["content"]
        if text in seen:
            continue
        seen.add(text)
        kept.append(tr)
        if len(kept) == max_keep:
            break
    rec["accepted"] = kept
    return rec


# ------------------------------------------------------------------ the corpus, from the record
def select(records: dict, max_self: int | None = MAX_SELF) -> tuple[list[dict], int]:
    """Coverage first: one walk of every covered question (fixed shuffled order), then second walks, until `max_self`."""
    order = sorted(records)
    random.Random(SHUFFLE_SEED).shuffle(order)
    tiers = [[records[k]["accepted"][t] for k in order if len(records[k].get("accepted", [])) > t] for t in range(MAX_KEEP)]
    flat = [r for tier in tiers for r in tier]
    if max_self is None or max_self <= 0:
        return flat, 0
    return flat[:max_self], max(0, len(flat) - max_self)


def assemble(rec: dict, base: Path = BASE_CORPUS, max_self: int | None = MAX_SELF) -> tuple[str, dict]:
    """The corpus text (the base corpus byte for byte, then the self-walks) and its gate."""
    base_text = base.read_text()
    if base_text and not base_text.endswith("\n"):
        base_text += "\n"
    base_rows = [json.loads(l) for l in base_text.splitlines() if l.strip()]
    records = {k: v for k, v in rec.get("questions", {}).items() if "error" not in v}
    chosen, capped = select(records, max_self)
    text = base_text + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen)
    g = rc.gate(base_rows + chosen, rc.EVAL_FILES)
    # G3 READS THE GRADE ONLY: a self-walk is kept with an ERROR line it recovered from (its span out of the loss), which
    # real_corpus' G3 would count as `refused`; it is reported apart
    g["G3_not_verified"] = sum(r["grade"] != "right" for r in base_rows + chosen)
    # G6 IS REPORTED, NOT GATED: the self-walks repeat REAL4's questions by design, whose openings passed G6 already
    g["G6_repeated_opening_info"] = g.pop("G6_repeated_opening")
    walks = [w for v in records.values() for w in v["walks"]]
    kinds = lambda rows: Counter("none" if r["check"]["kind"] == "none" else f"{r['hops']}-hop" for r in rows)
    by_kind = {}
    for kind, pred in (("one_hop", lambda v: v["kind"] == "value" and v["hops"] == 1),
                       ("multi_hop", lambda v: v["kind"] == "value" and v["hops"] >= 2),
                       ("none", lambda v: v["kind"] == "none")):
        vs = [v for v in records.values() if pred(v)]
        ws = [w for v in vs for w in v["walks"]]
        by_kind[kind] = {"questions": len(vs), "covered": sum(bool(v["accepted"]) for v in vs),
                         "walks": len(ws), "right": sum(w["state"] == "right" for w in ws),
                         "accepted": sum(len(v["accepted"]) for v in vs)}
    g.update({
        "base_rows": len(base_rows), "base_sha256": hashlib.sha256(base_text.encode()).hexdigest(),
        "self_rows": len(chosen), "self_by_kind": dict(kinds(chosen)), "capped": capped, "max_self": max_self,
        "questions": len(questions()), "questions_sampled": len(records),
        "questions_errored": sum("error" in v for v in rec.get("questions", {}).values()),
        "per_question_accepted": dict(sorted(Counter(len(v["accepted"]) for v in records.values()).items())),
        "by_kind": by_kind,
        "walks": len(walks), "walks_right": sum(w["state"] == "right" for w in walks),
        "acceptance_rate": round(sum(w["state"] == "right" for w in walks) / max(1, len(walks)), 4),
        "walks_same_page_wrong": sum(bool(w.get("same_page_wrong")) for w in walks),
        "walks_context": sum(w["state"] == "context" for w in walks),
        "walks_over_window": sum(bool(w.get("over_window")) for w in walks),
        "self_with_error_line": sum(r["refused"] > 0 for r in chosen),
        "self_not_right": sum(r["grade"] != "right" for r in chosen),
    })
    g["passed"] = all(v == 0 for k, v in g.items() if k[:1] == "G" and k[1].isdigit() and not k.endswith("_info")) \
        and g["self_not_right"] == 0 and g["questions_sampled"] == g["questions"] and g["self_rows"] > 0
    return text, g


def write_corpus(rec: dict, data: Path = DATA, max_self: int | None = MAX_SELF) -> dict:
    text, g = assemble(rec, max_self=max_self)
    (data / f"{OUT_NAME}.jsonl").write_text(text)
    g["corpus_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (data / f"gate_{OUT_NAME.removeprefix('train_')}.json").write_text(json.dumps(g, indent=1))
    return g


# ------------------------------------------------------------------ S2's verdict, as the brief fixed it
def sign_p(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def verdict(rec: dict, rows: list[dict]) -> dict:
    """RFT WORKS iff real-rft-s0 beats real-none-s0 on the answerable rows, paired, exact sign test p < 0.05, and refusals
    do not drop by more than one; RFT HELPS iff wins > losses otherwise; FALSIFIED iff wins ≤ losses. VOID on an
    unapplied member or more than 3 rows lost to transport."""
    rows = {r["case_id"]: r for r in rows}
    arms = rec.get("arms", {})
    if BASE_ARM not in arms or TREAT_ARM not in arms:
        return {"reading": "NOTHING SCORED"}
    b, t = arms[BASE_ARM], arms[TREAT_ARM]
    unapplied = [x for x in ("withlib-s0", "withlib-s1") if not rec.get("G1", {}).get(x, {}).get("applied")]
    ok = lambda x: "error" not in x
    lost = [i for i in rows if i not in b or i not in t or not ok(b[i]) or not ok(t[i])]
    keep = [i for i in rows if i not in lost]
    ans = [i for i in keep if rows[i]["check"]["kind"] != "none"]
    none = [i for i in keep if rows[i]["check"]["kind"] == "none"]
    wins = sum(bool(t[i]["credit"]) and not b[i]["credit"] for i in ans)
    losses = sum(bool(b[i]["credit"]) and not t[i]["credit"] for i in ans)
    p = sign_p(wins, losses)
    cnt = lambda arm, ids: sum(bool(arm[i]["credit"]) for i in ids)
    spw = lambda arm: sum(1 for i in ans if not arm[i]["credit"] and isinstance(arm[i].get("cited"), list)
                          and arm[i]["cited"][0] == rows[i]["support"][0] and arm[i]["cited"] != list(rows[i]["support"]))
    drop = cnt(b, none) - cnt(t, none)
    if unapplied:
        reading = f"VOID: G1 does not show {unapplied} applied"
    elif len(lost) > 3:
        reading = f"VOID: {len(lost)} rows lost to transport"
    elif wins > losses and p < 0.05 and drop <= 1:
        reading = "RFT WORKS"
    elif wins > losses:
        reading = "RFT HELPS"
    else:
        reading = "FALSIFIED"
    multi = [i for i in ans if rows[i]["hops"] > 1]
    one = [i for i in ans if rows[i]["hops"] == 1]
    both = lambda ids: {BASE_ARM: f"{cnt(b, ids)}/{len(ids)}", TREAT_ARM: f"{cnt(t, ids)}/{len(ids)}"}
    return {"reading": reading, "paired": f"{wins}:{losses}", "p": round(p, 4), "lost": lost,
            "answerable": both(ans), "multi_hop": both(multi), "one_hop": both(one), "refusals": both(none),
            "refusal_drop": drop, "same_page_wrong_statement": {BASE_ARM: spw(b), TREAT_ARM: spw(t)}}


# ------------------------------------------------------------------ the session
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=wa.BASE)
    ap.add_argument("--member-prefix", default="adapters/real-none-s", help="the member served is <prefix><seed>")
    ap.add_argument("--member-seed", type=int, default=0)
    ap.add_argument("--library", default=str(LIB))
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--max-model-len", type=int, default=16384)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="only the first n questions (a smoke run, never the measurement)")
    ap.add_argument("--max-self", type=int, default=MAX_SELF, help="cap on self-walks in the corpus; 0 = no cap")
    ap.add_argument("--assemble", default=None, help="zero GPU: a sampler record → train_real_rft.jsonl + gate_real_rft.json")
    ap.add_argument("--verdict", default=None, help="zero GPU: S2's wiki_arm record → its verdict, as the brief fixed it")
    ap.add_argument("--rows", default=str(EVAL_ROWS))
    ap.add_argument("--out", default="rft_sample.json")
    a = ap.parse_args()
    if a.assemble:
        g = write_corpus(json.loads(Path(a.assemble).read_text()), max_self=a.max_self)
        print(f"[rft] corpus {'PASSED' if g['passed'] else 'FAILED'} · {g['base_rows']} + {g['self_rows']} self-walks "
              f"(capped {g['capped']}) · acceptance {g['acceptance_rate']} · {json.dumps(g['by_kind'])}", flush=True)
        return 0 if g["passed"] else 1
    if a.verdict:
        v = verdict(json.loads(Path(a.verdict).read_text()), wa.load_rows(a.rows))
        Path(a.verdict).with_name("verdict.json").write_text(json.dumps(v, indent=1))
        print(f"[rft] {v['reading']} · {json.dumps(v)}", flush=True)
        return 0

    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"), grader="training.wiki.grade",
               library=a.library, seeds=list(SEEDS), temperature=TEMPERATURE, page_top=PAGE_TOP, max_keep=MAX_KEEP)
    rec.setdefault("questions", {})
    spec = f"{a.member_prefix}{a.member_seed}"
    adapter = Path(spec, "adapter_model.safetensors")
    if not adapter.exists():
        print(f"[rft] cannot sample: {spec} not on disk", flush=True)
        return 2
    rec["member"] = {"adapter": spec, "adapter_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest()}

    def save():
        out.write_text(json.dumps(rec, ensure_ascii=False))

    save()
    from memory.runtime import ChainSuite, FullText
    from transformers import AutoTokenizer
    from training.harness.accept_rank import completion, serve, stop, wait_ready
    from training.harness.verify_substrate import identity
    lib = Library.load(a.library)
    ft = FullText(lib)
    qs = questions()[:a.limit] if a.limit else questions()
    tok = AutoTokenizer.from_pretrained(a.base)

    def gen_for(system: str, user: str, walking: bool, temperature: float = 0.0, seed: int | None = None):
        head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)

        def gen(prefix: str) -> str:
            n = len(tok(head + prefix)["input_ids"])
            if n + a.max_tokens > a.max_model_len:
                raise wa.ContextExhausted(f"{n} prompt tokens + {a.max_tokens} > {a.max_model_len}")
            return completion(SERVED, head + prefix, a.max_tokens, ChainSuite.close, temperature, seed)
        return gen

    srv = serve(a.base, ["--max-model-len", str(a.max_model_len), "--gpu-memory-utilization", "0.90", "--enable-lora",
                         "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{SERVED}={spec}"])
    try:
        if not wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            g1 = identity(a.base, SERVED, tok)
            if not g1["applied"]:
                # wiki_arm's rule: a narrow LoRA can leave generic probes untouched — the domain probes decide
                dom = identity(a.base, SERVED, tok, probes=[prompt.user_text_wiki(q["question"]) for q in qs[:3]])
                g1 = {"generic": g1, "domain": dom, "applied": dom["applied"]}
            rec["G1"] = g1
            print(f"[rft] G1 {spec}: {'applied' if g1['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not g1["applied"]:
                rec["stopped"] = "G1: the member is not applied"
            else:
                for attempt in (1, 2):                      # a second pass retries transport errors, once
                    todo = [(i, q) for i, q in enumerate(qs)
                            if question_row(q, i)["case_id"] not in rec["questions"]
                            or "error" in rec["questions"][question_row(q, i)["case_id"]]]
                    print(f"[rft] pass {attempt}: {len(todo)} questions to sample, {len(qs) - len(todo)} resumed", flush=True)
                    if not todo:
                        break
                    t0, n = time.time(), 0
                    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
                        for f in as_completed([ex.submit(sample_question, lib, ft, q, i, gen_for) for i, q in todo]):
                            x = f.result()
                            rec["questions"][x["id"]] = x
                            n += 1
                            save()                          # persisted per question: the chain fetches it every poll
                            if n % 10 == 0 or n == len(todo):
                                done = [v for v in rec["questions"].values() if "error" not in v]
                                ws = [w for v in done for w in v["walks"]]
                                print(f"[rft] {len(rec['questions'])}/{len(qs)} questions · right {sum(w['state'] == 'right' for w in ws)}"
                                      f"/{len(ws)} walks · accepted {sum(len(v['accepted']) for v in done)} walks over "
                                      f"{sum(bool(v['accepted']) for v in done)} questions · errors "
                                      f"{len(rec['questions']) - len(done)} · {time.time() - t0:.0f}s", flush=True)
    finally:
        stop(srv)
    if "stopped" not in rec:
        _, g = assemble(rec, max_self=a.max_self)
        rec["gate"] = g
        print(f"[rft] corpus {'PASSED' if g['passed'] else 'FAILED'} · {g['base_rows']} + {g['self_rows']} self-walks · "
              f"acceptance {g['acceptance_rate']} · same-page-wrong walks {g['walks_same_page_wrong']}", flush=True)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[rft] {rec.get('stopped') or 'sampled — assemble the corpus at zero GPU from ' + str(out)}", flush=True)
    return 0 if "stopped" not in rec else 1


if __name__ == "__main__":
    raise SystemExit(main())
