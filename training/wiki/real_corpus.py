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


NONE_TOPICS = ["cargo liability insurance minimums", "customs duties on imported pallets", "payroll tax deposits",
               "workers' compensation premiums", "food label nutrition facts formatting", "hazardous materials placards",
               "trademark registration", "overtime pay rates", "pesticide residue tolerances", "railcar demurrage fees",
               "fuel tax reporting", "forklift dealer warranties", "warehouse property tax", "export licenses",
               "driver union contracts", "refrigerant handling certification"]
ASK_NONE = """Write {n} short questions a person at a trucking company, a food plant or a warehouse might ask about: {topic}.
They must sound like real operational questions with a specific answer (a number, a deadline, an amount). Return only
JSON: a list of objects {{"question": ..., "keywords": [three distinctive words of the question's topic]}}."""


def build_none(per_topic: int = 10) -> list[dict]:
    """Questions the library cannot answer — REAL3 [ran]: a corpus with none taught a member that never refuses (0/4).
    Mechanical check: a question is kept only if none of its topic keywords occurs anywhere in the training library."""
    lib, key, out = Library.load(LIB), _key(), []
    text = " ".join(n.body.lower() + " " + n.title.lower() for n in lib.notes.values())
    for topic in NONE_TOPICS:
        for q in ask(ASK_NONE.format(n=per_topic, topic=topic), key):
            try:
                question, kws = str(q["question"]).strip(), [str(k).lower() for k in q["keywords"]][:3]
            except (KeyError, TypeError):
                continue
            if question.endswith("?") and kws and not any(k in text for k in kws) and not re.search(r"\d", question):
                out.append({"question": question, "answer": "Not in my library.", "hops": 0, "pages": [], "support": None,
                            "tokens": [], "none": True, "keywords": kws})
    print(f"[realcorpus] none: {len(out)} questions · ${_spent['usd']:.2f}", flush=True)
    return out


REPEATED = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s+(hours?|days?|months?|years?|minutes?|feet|inches|pounds|percent|miles|"
                      r"calendar days|working days)\b", re.I)
ASK_REPEATED = """The same value — "{value}" — appears in each of these statements of a regulation. Write ONE question for EACH
statement, asked as a person at a trucking company, a food plant or a warehouse would, that ONLY that statement answers:
describe the situation that statement is about so a reader must pick that statement and not another one with the same
value. Never quote a section number or anchor; never put the value in the question.
Return only JSON: a list of objects {{"question": ..., "anchor": ..., "page": ..., "value": ...}} — `page` and `anchor`
exactly as written before each statement, `value` the exact span from that statement.

{statements}"""


def build_repeated(max_group: int = 12) -> list[dict]:
    """REAL6: questions whose value occurs in several statements, so only the right citation is right — REAL5 [ran] lost
    3 of its 5 citations to another statement holding the same number. Kept only if the value is in the named statement,
    not in the question, AND in at least one OTHER statement of the library (the row must exercise the choice)."""
    from collections import defaultdict
    lib, key, out = Library.load(LIB), _key(), []
    groups = defaultdict(list)
    for n in lib.notes.values():
        if count_tokens(n.body) > MAX_PAGE_TOKENS:
            continue
        for st in statements_of(n.body)[0]:
            for m in REPEATED.finditer(_LABEL.sub(" ", st.text)):
                groups[(m.group(1), m.group(2).lower().rstrip("s"))].append((n, st))
    for (num, unit), members in groups.items():
        uniq = list({(n.id, st.anchor): (n, st) for n, st in members}.values())
        if len(uniq) < 2:
            continue
        random.Random(f"{num}{unit}").shuffle(uniq)
        shown = uniq[:max_group]
        text = "\n\n".join(f"PAGE {n.id} — {n.title}\n§{st.anchor} {re.sub(r'\[\[[^\]]+\]\]', '§', st.text)}" for n, st in shown)
        for q in ask(ASK_REPEATED.format(value=f"{num} {unit}", statements=text), key):
            page = str(q.get("page", "")).strip()
            if page not in lib.notes:
                continue
            v = valid(q, lib.notes[page], lib.notes[page])
            if not v:
                continue
            others = sum(1 for n, st in uniq if (n.id, st.anchor) != (page, v["anchor"]))
            if others:
                out.append({**v, "hops": 1, "pages": [page], "support": [page, v["anchor"]], "repeated": others + 1})
    print(f"[realcorpus] repeated-value questions: {len(out)} · ${_spent['usd']:.2f}", flush=True)
    return out


ASK_CROSSLINK = """A reader starts on the FIRST page; its statement §{via} links to the SECOND page. The value "{value}" appears on
BOTH pages — on the first page in the statements marked DECOY, and on the second page in the TARGET statement(s). Write ONE
question for each TARGET statement, as a person at a trucking company, a food plant or a warehouse would ask, that only that
TARGET statement answers: start from the FIRST page's situation (what the linking statement is about) and ask for the detail
that only the SECOND page holds, so a careless reader would stop on the first page and cite the DECOY. Never quote a section
number or anchor; never put the value in the question.
Return only JSON: a list of objects {{"question": ..., "anchor": ..., "value": ...}} — `anchor` of the TARGET statement as
written, `value` the exact span from it.

FIRST {first}
LINKING §{via} {link_text}
DECOY (first page, same value — must NOT be cited):
{decoys}

SECOND {second}
TARGET (second page — the answer):
{targets}"""


_REF = re.compile(r"(§\s*)?\b\d+\.\d+[\w()]*|\bparts?\s+\d+|\[\[[^\]]+\]\]|\(\w{1,4}\)", re.I)


def decoy_numbers(text: str) -> set[str]:
    """Numbers of two digits or more a reader could cite — quantities, dates, amounts — never a section reference, a part
    number, a link or a paragraph label. REAL5's same-value miscitations were days, dates and amounts alike."""
    return {x for x in re.findall(r"\b\d[\d,]{1,}\b", _REF.sub(" ", text)) if len(x.replace(",", "")) >= 2}


def build_crosslink(per_edge: int = 3, roots: tuple = ("knowledge/regs-train", "knowledge/regs-train2"),
                    max_tokens: int = 2000) -> list[dict]:
    """REAL7: two-hop walks whose answer sits at the END of a link while the same quantity also sits at its START — REAL6
    [ran]: the miscitations were multi-hop rows cited at the wrong end of a link, and REAL6's corpus taught one-hop choices.
    Kept only if the value is in the target statement, in a statement of the first page (the decoy), and not in the ask."""
    key, out = _key(), []
    clean = lambda t: re.sub(r"\[\[[^\]]+\]\]", "§", t)
    for root in roots:
      lib = Library.load(root)
      for a in lib.notes.values():
        if count_tokens(a.body) > max_tokens:
            continue
        a_sts = statements_of(a.body)[0]
        for st in a_sts:
            for t in dict.fromkeys(re.findall(r"\[\[([^\]]+)\]\]", st.text)):
                if t not in lib.notes or t == a.id or count_tokens(lib.notes[t].body) > max_tokens:
                    continue
                b = lib.notes[t]
                for value in sorted(set().union(*[decoy_numbers(x.text) for x in a_sts]) & set().union(*[decoy_numbers(x.text) for x in statements_of(b.body)[0]])):
                    decoys = [x for x in a_sts if value in decoy_numbers(x.text)][:3]
                    targets = [x for x in statements_of(b.body)[0] if value in decoy_numbers(x.text)][:per_edge]
                    prompt = ASK_CROSSLINK.format(
                        via=st.anchor, value=value, first=f"PAGE {a.title}", link_text=clean(st.text)[:600],
                        decoys="\n".join(f"§{x.anchor} {clean(x.text)[:400]}" for x in decoys), second=f"PAGE {b.title}",
                        targets="\n".join(f"§{x.anchor} {clean(x.text)[:500]}" for x in targets))
                    for q in ask(prompt, key):
                        v = valid(q, a, b)
                        if v and any(all(_has_num(x.text, tk) for tk in v["tokens"]) for x in decoys):
                            out.append({**v, "hops": 2, "pages": [a.id, b.id], "support": [b.id, v["anchor"]],
                                        "via": [a.id, st.anchor], "decoy": [a.id, decoys[0].anchor], "lib": root})
    seen, kept = set(), []
    for q in out:
        if q["question"].lower() not in seen:
            seen.add(q["question"].lower()); kept.append(q)
    print(f"[realcorpus] cross-link questions: {len(kept)} · ${_spent['usd']:.2f}", flush=True)
    return kept


def _has_num(text: str, token: str) -> bool:
    from training.wiki import grade as gr
    return gr._has(_LABEL.sub(" ", text), token)


def fmt_plan(lib, q: dict, plan: list, page_top: int | None, inject: bool) -> tuple[list, str | None]:
    """FMT0: REAL4's walk for the page form the member is served with. Under `page_top` a page opens with the question's
    best statements; when the statement a walk needs — the link it follows (`via`) or the one it cites — is not among
    them, the walk opens it as `id§section`. With `inject`, the walk first opens the page's own section number as if it
    were an id — the mistake LIVE-library and CITE0 saw (`<open>20</open>`, `<open>1910.7</open>`) — reads the ERROR, and
    goes on; that open is returned so its span can be kept out of the loss (the recovery is taught, not the mistake)."""
    from memory.runtime import Conversation
    view = Conversation(lib, page_text=True, page_top=page_top, first_query=q["question"]) if page_top else None
    hidden = lambda pg, an: view is not None and an not in view._page_selection(lib[pg])
    out, bad = [], None
    for st in plan:
        out.append(st)
        if st[0] == "search" and inject and bad is None and not q.get("none"):
            bad = lib[q["pages"][0]].title.split(" ", 1)[0]
            out.append(["raw", bad])
        if st[0] == "open" and len(st) == 2 and not q.get("none"):
            if q.get("via") and st[1] == q["via"][0] and hidden(*q["via"]):
                out.append(["open", *q["via"]])
            if st[1] == q["support"][0] and hidden(*q["support"]):
                out.append(["open", *q["support"]])
    return out, (f"<open>{bad}</open>" if bad else None)


def walk_rows(questions: list[dict], page_top: int | None = None, inject_every: int = 0) -> list[dict]:
    from memory import prompt
    from memory.runtime import FullText
    from training.wiki import grade as gr
    from training.wiki import wiki_arm as wa
    libs: dict = {}

    def lib_of(root):
        if root not in libs:
            L = Library.load(root); libs[root] = (L, FullText(L))
        return libs[root]
    rows = []
    for i, q in enumerate(questions):
        lib, ft = lib_of(q.get("lib", str(LIB)))
        plan = [["search", "wiki", q["question"]]]
        if q.get("none"):
            # read the best page the entry shows, find nothing, refuse — a refusal is a reading, not a reflex
            top = ft.search(q["question"], None, 3)
            if not top:
                continue
            plan.append(["open", top[0]])
            row = {"case_id": f"real3-train-none-{i}", "world": 0, "family": "none", "block": "none", "hops": 0,
                   "shelf": "wiki", "question": q["question"], "plan": plan, "support": None, "answer": "Not in my library.",
                   "check": {"kind": "none", "tokens": []}}
        elif q["pages"][0] not in ft.search(q["question"], None, 3):
            # the question's entry does not show the page: the walk searches again, for the page by its title — a second
            # search a served walk may write too (the runtime substitutes only the first)
            plan.append(["search", "wiki", lib.notes[q["pages"][0]].title])
        if not q.get("none"):
          plan += [["open", p] for p in q["pages"]]
          row = {"case_id": f"real3-train-{i}", "world": 0, "family": f"real-{q['hops']}hop", "block": "R",
               "hops": q["hops"], "shelf": "wiki", "question": q["question"], "plan": plan, "support": q["support"],
               "answer": q["answer"], "check": {"kind": "value", "tokens": q["tokens"], "cite": "support"}}
        bad = None
        if page_top or inject_every:
            row["plan"], bad = fmt_plan(lib, q, row["plan"], page_top, bool(inject_every) and i % inject_every == 0)
        conv = wa.conversation(lib, row)
        conv.searcher, conv.first_query, conv.entry_all_shelves, conv.fallback, conv.page_text = ft, q["question"], True, True, True
        conv.page_top = page_top
        if bad is not None:
            # the guard's `recover` mode (docs/MEMORY.md §5.3): the violation is written inline and the walk goes on —
            # `strict` ends it, which is what LIVE-library's "no line after an ERROR" walks were [ran] (FMT0's diagnosis)
            conv.guard.mode = "recover"
        try:
            final, conv, chain = wa.walk(lib, row, wa.oracle_gen(row, conv), conv)
        except KeyError:                                 # a page no search shows: the walk cannot reach it — dropped
            continue
        g = gr.grade(row, final, conv)
        # WHAT THE MODEL WROTE, as character spans of the assistant turn — the loss goes there and nowhere else
        # (REAL3 attempt 1 [ran]: a loss on the whole walk taught the LoRA to write the regulation pages it was shown)
        rows.append({**row, "grade": g["state"], "refused": chain["refused"] - (bad is not None), "injected": bad,
                     "train_spans": [[sp["at"], sp["at"] + len(sp["text"])] for sp in chain["spans"]
                                     if sp["text"] and sp["text"] != bad],
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
    g = {"G1_eval_library_in_corpus": sum(bool(r.get("support")) and r["support"][0].split("/")[0] in eval_libs for r in rows),
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
    ap.add_argument("--with-none", action="store_true", help="REAL4: add unanswerable questions → train_real_none.jsonl")
    ap.add_argument("--with-repeated", action="store_true", help="REAL6: also add repeated-value questions → train_real_cite.jsonl")
    ap.add_argument("--with-format", action="store_true",
                    help="FMT0: REAL4's corpus walked under page_top=8 (hidden statements opened as id§section) and one walk "
                         "in three recovering from a mistaken open → train_real_fmt.jsonl")
    ap.add_argument("--with-crosslink", action="store_true", help="REAL7: REAL4's corpus + cross-link decoy walks → train_real_link.jsonl")
    a = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    if a.questions:
        qs = build_questions()
        (DATA / "real_questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in qs))
        print(f"[realcorpus] {len(qs)} questions ({sum(q['hops'] == 2 for q in qs)} two-hop) · spent ${_spent['usd']:.2f}", flush=True)
    if a.walks:
        qs = [json.loads(l) for l in (DATA / "real_questions.jsonl").read_text().splitlines() if l.strip()]
        name = "train_real"
        if a.with_none:
            nf = DATA / "real_none_questions.jsonl"
            if not nf.exists():
                nf.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in build_none()))
            qs, name = qs + [json.loads(l) for l in nf.read_text().splitlines() if l.strip()], "train_real_none"
        if a.with_crosslink:
            cf = DATA / "real_crosslink_questions.jsonl"
            if not cf.exists():
                cf.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in build_crosslink()))
            qs, name = qs + [json.loads(l) for l in cf.read_text().splitlines() if l.strip()], "train_real_link"
        if a.with_repeated:
            rf = DATA / "real_repeated_questions.jsonl"
            if not rf.exists():
                rf.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in build_repeated()))
            qs, name = qs + [json.loads(l) for l in rf.read_text().splitlines() if l.strip()], "train_real_cite"
        if a.with_format:
            name = "train_real_fmt"
        rows = [r for r in walk_rows(qs, *((8, 3) if a.with_format else ())) if r["grade"] == "right" and not r["refused"]
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
        g = gate(rows, [Path("results/REAL0-real-library-20260930/questions.jsonl"), Path("results/REAL3-real-corpus-20260930/questions.jsonl"),
                        # every set measured since — G1/G2 keep their libraries and questions out (FMT0 is scored on PAGE0's)
                        Path("results/REAL4-refusal-20260930/questions.jsonl"), Path("results/REAL5-third-family-20261001/questions.jsonl"),
                        Path("results/CITE0-runtime-check-20261002/questions.jsonl"), Path("results/PAGE0-page-top-20261002/questions.jsonl")])
        if a.with_format:
            g["FMT_injected"] = sum(bool(r.get("injected")) for r in rows)
            g["FMT_section_opens"] = sum(r["messages"][2]["content"].count("§") and "<open>" in r["messages"][2]["content"]
                                         and bool(__import__("re").search(r"<open>[a-z0-9]{3}§", r["messages"][2]["content"])) for r in rows)
        (DATA / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        (DATA / f"gate_{name.removeprefix('train_')}.json").write_text(json.dumps(g, indent=1))
        print(f"[realcorpus] walks {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
        return 0 if g["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
