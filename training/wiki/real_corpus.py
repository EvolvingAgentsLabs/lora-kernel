r"""REAL3's training corpus — walks over REAL documents, a document family the evaluation never sees (M3).

WHY. REAL0–REAL2 **[ran]**: a trajectory member trained on a generator's world never entered a real library (memorised
queries and shelves), and the runtime's entry and page text took the untrained base to 7/25 and the member to 5/25 —
walks now reach the supporting page 24/25, then lose the citation or read the wrong paragraph among a page's many. What
neither model has been shown is **a real page read whole and the one statement cited from it.** This corpus is that.

THE DOCUMENTS (train family, `knowledge/regs-train`, ingested verbatim like REAL0's): 49 CFR 391/395/396 (drivers,
hours of service, vehicle inspection), 21 CFR 117 (food manufacturing practices and records), 29 CFR 1910 Subpart E
(exits, emergency plans). **21 CFR Part 1 and 29 CFR 1910.176/178 — the evaluation library — are absent.**

THE QUESTIONS are written by a model (Claude Haiku) from one page, or from a statement and the page its link leads to
(two hops), as a person at a carrier, a plant or a warehouse would ask; then **checked mechanically**: the anchor exists;
every value token is in the supporting statement and none is in the question (G4); no section number in the question; no
question repeated, and no question opening shared by more than `MAX_SHARE` of the corpus (M2's lesson: REAL0's member
learned five strings). The walks are the oracle's, through **the runtime the member is served with** — the question's
full-text entry on every shelf, pages opened with their statements (`Conversation.page_text`) — graded by the strict
grader. The evaluation questions are written by someone else, never by this generator.

    python -m training.wiki.real_corpus --questions   # model-written, validated → training/wiki/data/real_questions.jsonl
    python -m training.wiki.real_corpus --walks       # oracle walks → training/wiki/data/train_real.jsonl, gate_real.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

from memory.notes import Library, count_tokens, statements_of

LIB = Path("knowledge/regs-train")
DATA = Path("training/wiki/data")
MODEL = "claude-haiku-4-5-20251001"
SPEND_CAP_USD, RATES = 5.0, (1.0, 5.0)              # $ per million input, output tokens
PER_PAGE, MAX_PAGE_TOKENS, WINDOW, MAX_SHARE = 8, 2500, 4096, 0.02
_spent = {"usd": 0.0}

ASK = """You write practice questions about a regulation page, for training an assistant that must find answers in it.

Rules for every question:
- Ask it as a person at a trucking company, a food plant or a warehouse would, in plain words. Never quote a section
  number, paragraph label or the regulation's exact phrasing; never put the answer in the question.
- The answer MUST be a short exact span copied from ONE statement below that contains a number: a quantity, a duration,
  a time, a temperature, a weight, a distance, a count. If the page has fewer such numbers, write fewer questions.
- Return only JSON: a list of objects {{"question": ..., "answer": ..., "anchor": ..., "value": ...}} where `anchor` is
  the statement's anchor (without §) and `value` is the exact span as it appears in that statement.

{task}

{pages}"""


def _key() -> str:
    for line in Path("~/.config/lora-kernel/frontier.env").expanduser().read_text().splitlines():
        if line.startswith("FRONTIER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("no FRONTIER_API_KEY in ~/.config/lora-kernel/frontier.env")


def ask(prompt: str, key: str) -> list[dict]:
    if _spent["usd"] >= SPEND_CAP_USD:
        raise SystemExit(f"spend cap ${SPEND_CAP_USD} reached")
    body = json.dumps({"model": MODEL, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(4):
        try:
            out = json.loads(urllib.request.urlopen(req, timeout=120).read())
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        return []
    u = out.get("usage", {})
    _spent["usd"] += (u.get("input_tokens", 0) * RATES[0] + u.get("output_tokens", 0) * RATES[1]) / 1e6
    text = "".join(c.get("text", "") for c in out.get("content", []))
    m = re.search(r"\[.*\]", text, re.S)
    try:
        return json.loads(m.group(0)) if m else []
    except ValueError:
        return []


def render(note) -> str:
    sts = statements_of(note.body)[0]
    return f"PAGE: {note.title}\n" + "\n".join(f"§{s.anchor} {re.sub(r'\[\[[^\]]+\]\]', '§', s.text)}" for s in sts)


_NUM = re.compile(r"\d+(?::\d+)?")


_LABEL = re.compile(r"\(\s*[A-Za-z0-9]{1,4}\s*\)")


def tokens_of(value: str) -> list[str]:
    """The check is the value's numbers — what the grader can verify without ambiguity; a value with none is dropped,
    and a paragraph label — `(3)` — is not a number of the answer."""
    return _NUM.findall(_LABEL.sub(" ", value))


def valid(q: dict, note, support_note) -> dict | None:
    """The mechanical check: a model's question enters the corpus only if the statement it names holds the value and
    the question does not."""
    from training.wiki import grade as gr
    try:
        question, anchor, value = str(q["question"]).strip(), str(q["anchor"]).strip().lstrip("§"), str(q["value"]).strip()
        labels = re.findall(r"\(([A-Za-z0-9]{1,4})\)", anchor)
        if labels:                                   # the model wrote the regulation's citation, `391.21(b)(3)` → `b-3`
            anchor = "-".join(x.lower() for x in labels)
    except (KeyError, TypeError):
        return None
    st = next((s for s in statements_of(support_note.body)[0] if s.anchor == anchor), None)
    toks = tokens_of(value)
    if not st or not toks or not question.endswith("?") or len(question) > 220:
        return None
    if not all(gr._has(_LABEL.sub(" ", st.text), t) for t in toks) or any(gr._has(question, t) for t in toks):
        return None
    if re.search(r"§|\b\d+\.\d+\b|\(\w\)\(\d\)", question):
        return None
    return {"question": question, "answer": str(q.get("answer") or value).strip(), "anchor": anchor, "tokens": toks}


def build_questions() -> list[dict]:
    lib, key, out = Library.load(LIB), _key(), []
    pages = [n for n in lib.notes.values() if count_tokens(n.body) <= MAX_PAGE_TOKENS]
    for i, n in enumerate(pages):
        task = f"Write {PER_PAGE} questions, each answered by a different statement of this page."
        for q in ask(ASK.format(task=task, pages=render(n)), key):
            v = valid(q, n, n)
            if v:
                out.append({**v, "hops": 1, "pages": [n.id], "support": [n.id, v["anchor"]]})
        if i % 10 == 0:
            print(f"[realcorpus] one-hop {i + 1}/{len(pages)} pages · {len(out)} valid · ${_spent['usd']:.2f}", flush=True)
    edges = []
    for n in pages:
        for s in statements_of(n.body)[0]:
            for t in re.findall(r"\[\[([^\]]+)\]\]", s.text):
                if t in lib.notes and t != n.id and count_tokens(lib.notes[t].body) <= MAX_PAGE_TOKENS:
                    edges.append((n, s, lib.notes[t]))
    random.Random(3).shuffle(edges)
    for i, (a, s, b) in enumerate(edges[:300]):
        task = (f"Write 2 questions a person reading the FIRST page's statement §{s.anchor} would ask, whose answer is in the "
                f"SECOND page (the page that statement refers to). Describe what they need in their own words; the "
                f"anchor and value must come from the SECOND page.")
        for q in ask(ASK.format(task=task, pages=f"FIRST {render(a)}\n\nSECOND {render(b)}"), key):
            v = valid(q, a, b)
            if v:
                out.append({**v, "hops": 2, "pages": [a.id, b.id], "support": [b.id, v["anchor"]], "via": [a.id, s.anchor]})
        if i % 20 == 0:
            print(f"[realcorpus] two-hop {i + 1}/{min(300, len(edges))} edges · {len(out)} valid · ${_spent['usd']:.2f}", flush=True)
    seen, kept = set(), []
    for q in out:
        k = q["question"].lower()
        if k not in seen:
            seen.add(k); kept.append(q)
    return kept


def walk_rows(questions: list[dict]) -> list[dict]:
    from memory import prompt
    from memory.runtime import FullText
    from training.wiki import grade as gr
    from training.wiki import wiki_arm as wa
    lib = Library.load(LIB)
    ft, rows = FullText(lib), []
    for i, q in enumerate(questions):
        plan = [["search", "wiki", q["question"]]]
        if q["pages"][0] not in ft.search(q["question"], None, 3):
            # the question's entry does not show the page: the walk searches again, for the page by its title — a second
            # search a served walk may write too (the runtime substitutes only the first)
            plan.append(["search", "wiki", lib.notes[q["pages"][0]].title])
        plan += [["open", p] for p in q["pages"]]
        row = {"case_id": f"real3-train-{i}", "world": 0, "family": f"real-{q['hops']}hop", "block": "R",
               "hops": q["hops"], "shelf": "wiki", "question": q["question"], "plan": plan, "support": q["support"],
               "answer": q["answer"], "check": {"kind": "value", "tokens": q["tokens"], "cite": "support"}}
        conv = wa.conversation(lib, row)
        conv.searcher, conv.first_query, conv.entry_all_shelves, conv.fallback, conv.page_text = ft, q["question"], True, True, True
        try:
            final, conv, chain = wa.walk(lib, row, wa.oracle_gen(row, conv), conv)
        except KeyError:                                 # a page no search shows: the walk cannot reach it — dropped
            continue
        g = gr.grade(row, final, conv)
        # WHAT THE MODEL WROTE, as character spans of the assistant turn — the loss goes there and nowhere else
        # (REAL3 attempt 1 [ran]: a loss on the whole walk taught the LoRA to write the regulation pages it was shown)
        rows.append({**row, "grade": g["state"], "refused": chain["refused"],
                     "train_spans": [[sp["at"], sp["at"] + len(sp["text"])] for sp in chain["spans"] if sp["text"]],
                     "messages": [{"role": "system", "content": prompt.SYSTEM_WIKI},
                                  {"role": "user", "content": prompt.user_text_wiki(q["question"])},
                                  {"role": "assistant", "content": chain["text"]}]})
    return rows


def gate(rows: list[dict], eval_files: list[Path]) -> dict:
    from training.wiki import grade as gr
    evals = [json.loads(l) for f in eval_files if f.exists() for l in f.read_text().splitlines() if l.strip()]
    eval_q = {r["question"].lower() for r in evals}
    eval_libs = {r["support"][0].split("/")[0] for r in evals if r.get("support")}
    openers = Counter(" ".join(r["question"].lower().split()[:4]) for r in rows)
    g = {"G1_eval_library_in_corpus": sum(r["support"][0].split("/")[0] in eval_libs for r in rows),
         "G2_eval_question_in_corpus": sum(r["question"].lower() in eval_q for r in rows),
         "G3_not_verified": sum(r["grade"] != "right" or r["refused"] for r in rows),
         "G4_value_in_question": sum(any(gr._has(r["question"], t) for t in r["check"]["tokens"]) for r in rows),
         "G5_over_window": sum(count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) >= WINDOW for r in rows),
         "G6_repeated_opening": sum(c for c in openers.values() if c > max(3, MAX_SHARE * len(rows))),
         "rows": len(rows), "two_hop": sum(r["hops"] == 2 for r in rows),
         "max_tokens": max((count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) for r in rows), default=0),
         "top_openings": openers.most_common(5)}
    g["passed"] = all(v == 0 for k, v in g.items() if k[:1] == "G" and k[1].isdigit())
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", action="store_true")
    ap.add_argument("--walks", action="store_true")
    a = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    if a.questions:
        qs = build_questions()
        (DATA / "real_questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in qs))
        print(f"[realcorpus] {len(qs)} questions ({sum(q['hops'] == 2 for q in qs)} two-hop) · spent ${_spent['usd']:.2f}", flush=True)
    if a.walks:
        qs = [json.loads(l) for l in (DATA / "real_questions.jsonl").read_text().splitlines() if l.strip()]
        rows = [r for r in walk_rows(qs) if r["grade"] == "right" and not r["refused"]
                and count_tokens(r["messages"][1]["content"] + r["messages"][2]["content"]) < WINDOW]
        random.Random(20260930).shuffle(rows)
        # G6 AS A FILTER, NOT A LOOSER BAR: the question-writing model repeats its openings ("how often do we" 23 of 316 in
        # the first draft); a row past the opening's 2 % share is dropped, shuffled order deciding which
        while True:                                      # the cap is 2 % of the corpus that remains: iterate to a fixed point
            cap, seen, kept = max(3, int(MAX_SHARE * len(rows))), Counter(), []
            for r in rows:
                k = " ".join(r["question"].lower().split()[:4])
                if seen[k] < cap:
                    seen[k] += 1; kept.append(r)
            if len(kept) == len(rows) and all(c <= max(3, MAX_SHARE * len(kept)) for c in seen.values()):
                break
            rows = kept
        g = gate(rows, [Path("results/REAL0-real-library-20260930/questions.jsonl"), Path("results/REAL3-real-corpus-20260930/questions.jsonl")])
        (DATA / "train_real.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        (DATA / "gate_real.json").write_text(json.dumps(g, indent=1))
        print(f"[realcorpus] walks {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
