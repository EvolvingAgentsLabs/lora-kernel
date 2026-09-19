r"""W5b — composition: the adapter walks, the bare base writes the final line. One unknown: who reads.

W5 did not pass **[ran]** `results/M7-W5-kill-arm-20260919`: `withlib` 35/56 against the untrained base
reading the oracle's notes, 45/56 (6 : 16, $p = 0.052$). Read where it happens, 12 of `withlib`'s 21
headline failures are quantity rows on a CLEAN walk — the right note opened, the guard silent — whose
final line carries the wrong one of the two values the held-out note states; the untrained base is
right on all 12, and no training row ever read a note with two values. The diagnosis: *the adapter
navigates, and stopped reading the condition*. This arm prices that diagnosis without training
anything.

    composed    `withlib`'s RECORDED walk, replayed — not regenerated: vLLM is not deterministic at
                temperature 0 and a fresh walk would be a second unknown — through a fresh referee
                with the case's own seed, and verified result by result against the recorded text.
                The pages that walk opened, in the order it opened them, are then put before the
                BARE base exactly the way `base-reads` is served (`walks_arm.SYSTEM_READS`, the same
                layout, the same budget, no verbs). The base writes the final line.

Graded by the untouched `grade_walks.grade`: the final line is the base's, the WALK EVIDENCE is the
replayed walk's — so `unread` still applies, and a walk the referee cut still earns nothing.

A RECORD KEPT THE LAST 1500 CHARACTERS OF ITS WALK, so 25 of 140 walks lost their head. A lost head
is rebuilt only if it can be PROVEN: a prefix of the oracle's own plan is tried in front of the visible
calls, and accepted only when every visible result replays byte for byte (the ids shown are drawn
from the whole history, so they are a checksum of it) and the call count, the opened count and the
violations equal the record's. Anything else is `unreplayable`, counted, never guessed.

The verdict pairs, on the same 56 headline ids, exact two-sided sign test on discordant pairs
(FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

    composed vs withlib      must be an improvement, or composition buys nothing
    composed vs base-reads   W5's bar, read as W5 read it: the spec says *beats*; a tie is a tie
    composed vs nolib

THIS IS ATTRIBUTION, NOT A SECOND ATTEMPT AT W5. W5's verdict stands as recorded. These 80 cases
have been looked at; a serving design built on this arm needs its own held-out set, written after
its freeze.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory.notes import Library
from memory.runtime import TAG
from training.nursing import generate_walks as gw
from training.nursing import grade_walks as gr
from training.nursing import walks_arm as wa
from training.nursing.library import ROOT

W5 = Path("results/M7-W5-kill-arm-20260919/walks_arm.json")
KEPT = 1500                                   # `walks_arm.run_case` keeps `chain["text"][-1500:]`
PREDICTED_LEFT, FALSIFIED_LEFT = 2, 6         # of withlib's clean-walk quantity failures, fixed in W5's brief
EMPTY = "(the library returned no note for this situation)"


# ------------------------------------------------------------------ the recorded walk, replayed
def visible_calls(text: str, truncated: bool) -> list[tuple[str, str, str]]:
    """(verb, raw, what the record shows after `= `) for every call whose opening tag survived."""
    ms = list(TAG.finditer(text))
    out = []
    for n, m in enumerate(ms):
        after = text[m.end():(ms[n + 1].start() if n + 1 < len(ms) else len(text))]
        if not after.startswith("= "):
            if truncated and n == 0:
                continue
            raise ValueError("a call in the record has no inline result")
        out.append((m.group(1), m.group(2), after[2:]))
    return out


def _plan_call(conv, step) -> tuple[str, str] | None:
    if step[0] == "open":
        shown = conv.opaque.get(step[1])
        return ("open", ">" + shown) if shown else None
    if step[0] == "search":
        return "search", f" shelf={step[1]}>{step[2]}"
    return "calc", ">" + step[1]


def _run(lib: Library, row: dict, head: list, calls: list, rec: dict):
    """Replay `head` (plan steps) then `calls`; None unless every visible result is the record's."""
    conv, page = gw.conversation(lib, gw.case_of(row))
    pages = [page] if page else []
    n = 0
    for step in head:
        c = _plan_call(conv, step)
        if c is None:
            return None
        res = conv.answer(*c); n += 1
        if c[0] != "search" and not res.startswith("ERROR"):
            pages.append(f"<{c[0]}>{c[1][1:]}</{c[0]}>= {res}")
    for verb, raw, shown in calls:
        res = conv.answer(verb, raw); n += 1
        if not shown.startswith(res):
            return None
        if verb != "search" and not res.startswith("ERROR"):
            pages.append(f"<{verb}>{raw.partition('>')[2]}</{verb}>= {res}")
    walk = gr.walk_evidence(conv, len(row["replay"]["carried"]), {"ran_out": rec.get("ran_out")})
    same = (n == rec["calls"] - rec.get("malformed", 0) and len(walk["opened"]) == rec["opened"]
            and walk["violations"] == rec["violations"])
    return (conv, pages, walk) if same else None


def _page_patterns(lib: Library, row: dict) -> dict[str, "re.Pattern"]:
    """Every note as the runtime renders it for THIS case, with the ids it draws left open: an id
    shown is three characters drawn from the conversation's history, which a lost head took with it."""
    conv, _ = gw.conversation(lib, gw.case_of(row))
    out = {}
    for note in lib.notes.values():
        text = re.escape(conv._render(note, (conv.case or {}).get(note.id)))
        for shown in conv.shown:
            text = text.replace(re.escape(shown), r"\w{3}")
        out[note.id] = re.compile(text)
    return out


def _from_the_tail(lib: Library, row: dict, calls: list, rec: dict):
    """A head lost, and only searches in it: every page the walk opened is still in the record,
    verbatim. The note behind each is identified by its content; the referee's verdict on the walk
    is the record's. Accepted only if the opened count is the record's and `walk_ok` comes out as
    the record says it did — otherwise nothing is claimed."""
    pats = _page_patterns(lib, row)
    _, page = gw.conversation(lib, gw.case_of(row))
    pages, opened, calcs = ([page] if page else []), [], 0
    for verb, raw, shown in calls:
        arg = raw.partition(">")[2]
        if verb == "search" or shown.startswith("ERROR"):
            continue
        if verb == "calc":
            calcs += 1
            pages.append(f"<calc>{arg}</calc>= {shown.splitlines()[0]}")
            continue
        hits = [(i, m) for i, pat in pats.items() if (m := pat.match(shown))]
        longest = max((len(m.group(0)) for _, m in hits), default=0)
        hits = [(i, m) for i, m in hits if len(m.group(0)) == longest]
        if len(hits) != 1:
            return None
        opened.append(hits[0][0])
        pages.append(f"<open>{arg}</open>= {hits[0][1].group(0)}")
    walk = {"opened": opened, "answered": rec.get("ended") is None, "violations": list(rec["violations"]),
            "calcs": calcs, "errors": rec.get("errors", {}), "ended": rec.get("ended"), "ran_out": bool(rec.get("ran_out"))}
    if len(opened) != rec["opened"] or gr.walk_ok(lib, row, walk) != rec["walk_ok"]:
        return None
    return pages, walk


def replay(lib: Library, row: dict, rec: dict):
    """(pages, walk evidence, how) for a recorded walk — or (None, None, why not)."""
    text = rec.get("text")
    if text is None or "error" in rec:
        return None, None, "no recorded walk"
    # A record written since the fix carries its whole walk and says so; W5's own file does not.
    truncated = not rec.get("text_full") and len(text) >= KEPT
    try:
        calls = visible_calls(text, truncated)
    except ValueError as e:
        return None, None, str(e)
    plan = row["replay"]["plan"]
    for j in (range(len(plan) + 1) if truncated else (0,)):
        got = _run(lib, row, plan[:j], calls, rec)
        if got:
            return got[1], got[2], ("exact" if not truncated else f"head rebuilt from {j} oracle step(s), proven by replay")
    got = _from_the_tail(lib, row, calls, rec) if truncated else None
    if got:
        return got[0], got[1], "head lost, every opened page still in the record — pages verbatim, notes identified by content"
    return None, None, "unreplayable: the kept tail does not determine the walk"


def served(lib: Library, row: dict, pages: list[str]) -> tuple[str, str]:
    """`base-reads`' turn, with the walk's pages where the oracle's were. One layout, one place."""
    notes = "\n\n".join(pages) or EMPTY
    return wa.SYSTEM_READS, f"{row['statement']}\n\nThe notes:\n{notes}"


def run_case(lib: Library, row: dict, rec: dict, gen_for) -> dict:
    out = {"id": row["case_id"], "family": row["family"], "variant": row["variant"]}
    pages, walk, how = replay(lib, row, rec)
    if pages is None:
        return {**out, "state": "unreplayable", "credit": False, "correct": False, "detail": how}
    system, user = served(lib, row, pages)
    try:
        final = gen_for(system, user, None)("")
    except wa.ContextExhausted as e:
        return {**out, "state": "context", "credit": False, "correct": False, "detail": str(e)[:120]}
    except Exception as e:                                   # transport — never folded into a score
        return {**out, "error": repr(e)[:160]}
    g = gr.grade(lib, row, final, walk)
    same_as_oracle = (system, user) == wa.served(lib, row, "base-reads")[:2]
    out.update(g, correct=g["credit"], final=final[-400:], replayed=how, pages=len(pages),
               opened=len(walk["opened"]), opened_ids=list(walk["opened"]), violations=walk["violations"],
               opened_the_oracles_notes=set(walk["opened"]) == set(row["walk"]),
               prompt_is_base_reads=same_as_oracle)
    return out


# ------------------------------------------------------------------ what can be known with no GPU
def ceiling(lib: Library, sets: dict, w5: dict) -> dict:
    """The most this arm can reach if the base reads the walk's pages as well as it read the oracle's:
    headline cases whose recorded walk is clean (`walk_ok`) AND on which `base-reads` has credit."""
    head = wa.slices(sets)["headline"]
    rows = {r["case_id"]: r for r in sets["heldout"]}
    wl, br = w5["arms"]["withlib"]["heldout"]["records"], w5["arms"]["base-reads"]["heldout"]["records"]
    info = {i: replay(lib, rows[i], wl[i]) for i in head}
    ok = [i for i in head if info[i][0] is not None]
    clean = [i for i in ok if gr.walk_ok(lib, rows[i], info[i][1])]
    same_set = [i for i in ok if set(info[i][1]["opened"]) == set(rows[i]["walk"])]
    same_prompt = [i for i in ok if served(lib, rows[i], info[i][0]) == wa.served(lib, rows[i], "base-reads")[:2]]
    quantity = [i for i in head if rows[i]["family"] == "quantity" and not wl[i]["credit"] and wl[i].get("walk_ok")]
    return {"headline": len(head), "replayable": len(ok),
            "unreplayable": sorted(set(head) - set(ok)),
            "rebuilt_heads": sorted(i for i in ok if info[i][2] != "exact"),
            "walk_clean": len(clean),
            "ceiling_clean_walk_and_base_reads_has_credit": sum(br[i]["credit"] for i in clean),
            "withlib_credit": sum(wl[i]["credit"] for i in head), "base_reads_credit": sum(br[i]["credit"] for i in head),
            "opened_set_equals_oracle_walk": len(same_set), "prompt_identical_to_base_reads": len(same_prompt),
            "withlib_clean_walk_quantity_failures": sorted(quantity)}


def analyse(rec: dict, sets: dict) -> dict:
    arms = {a: {**v["heldout"]["records"], **v["control"]["records"]} for a, v in rec["arms"].items()
            if all(s in v for s in wa.SETS)}
    # A WALK THAT CANNOT BE REPLAYED IS NOT A WRONG ANSWER. It leaves every slice, for every arm, so
    # each pair is read on the same cases; which ones, and why, is in the brief before the run.
    out_ids = sorted(i for i, r in arms.get("composed", {}).items() if r.get("state") == "unreplayable")
    sl = {k: [i for i in ids if i not in out_ids] for k, ids in wa.slices(sets).items()}
    out = {"excluded_unreplayable": out_ids, "slices": {k: len(v) for k, v in sl.items()},
           "summary": {a: {k: wa.summarise(r, ids) for k, ids in sl.items()} for a, r in arms.items()}, "pairs": {}}
    if "composed" in arms:
        for k, ids in sl.items():
            out["pairs"][k] = [wa._pair(arms["composed"], arms[o], ids, f"composed vs {o}")
                               for o in ("withlib", "base-reads", "nolib") if o in arms and ids]
        q = rec["ceiling"]["withlib_clean_walk_quantity_failures"]
        left = [i for i in q if not arms["composed"].get(i, {}).get("credit")]
        out["diagnosis"] = {"withlib_clean_walk_quantity_failures": len(q), "still_without_credit": left}
        same = [i for i, r in arms["composed"].items() if r.get("prompt_is_base_reads") and i in arms.get("base-reads", {})]
        out["same_prompt_agreement"] = {"n": len(same), "same_credit": sum(
            arms["composed"][i]["credit"] == arms["base-reads"][i]["credit"] for i in same)}
    return out


def verdict(rec: dict) -> dict:
    a = rec.get("analysis", {})
    head = {p["pair"]: p for p in a.get("pairs", {}).get("headline", [])}
    s = a.get("summary", {}).get("composed", {}).get("headline")
    if not s or not head:
        return {"decided": False, "reading": "NOTHING SCORED"}
    lost = s["errors"] + s["missing"]
    left = len(a["diagnosis"]["still_without_credit"]); of = a["diagnosis"]["withlib_clean_walk_quantity_failures"]
    out = {"decided": not lost, "headline": f"{s['credit']}/{s['scored']}", "unreplayable": s["states"].get("unreplayable", 0),
           "pairs": {k: f"{p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})" for k, p in head.items()},
           "quantity_failures_left": f"{left}/{of}",
           "diagnosis": ("HOLDS" if left <= PREDICTED_LEFT else "FALSIFIED" if left >= FALSIFIED_LEFT else "UNDECIDED")}
    if lost:
        out["reading"] = f"VOID: {lost} headline records missing or lost to transport"
        return out
    vs = {k: p["state"] for k, p in head.items()}
    out["reading"] = (
        f"diagnosis {out['diagnosis']}: {left} of withlib's {of} clean-walk quantity failures remain when the base "
        f"writes the line · composed {out['headline']} · vs withlib {vs.get('composed vs withlib')} · vs base-reads "
        f"{vs.get('composed vs base-reads')} · vs nolib {vs.get('composed vs nolib')} — W5's verdict stands; this is "
        "attribution")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=wa.BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--w5", default=str(W5))
    ap.add_argument("--ceiling", action="store_true", help="zero GPU: replay every walk, print what this arm can reach")
    ap.add_argument("--max-tokens-plain", type=int, default=320, help="base-reads' budget, unchanged")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="walks_composed.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    w5 = json.loads(Path(a.w5).read_text())
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"),
               grader="training.nursing.grade_walks", walks_from=a.w5, w5_verdict=w5["verdict"]["reading"])
    # THE FOUR RECORDED ARMS ARE COPIED IN, NEVER RE-RUN, and the W5 file is never written to.
    rec.setdefault("arms", {})
    for arm in wa.ARMS:
        rec["arms"][arm] = w5["arms"][arm]
    lib = Library.load(ROOT)
    sets = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in wa.SETS.items()}
    rec["ceiling"] = ceiling(lib, sets, w5)

    def save():
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    save()
    c = rec["ceiling"]
    print(f"[arm] composed, zero GPU: {c['replayable']}/{c['headline']} headline walks replay · ceiling "
          f"{c['ceiling_clean_walk_and_base_reads_has_credit']}/{c['headline']} (withlib {c['withlib_credit']}, "
          f"base-reads {c['base_reads_credit']}) · prompt identical to base-reads on {c['prompt_identical_to_base_reads']}",
          flush=True)
    if a.ceiling:
        return 0

    from transformers import AutoTokenizer
    from training.harness.accept_rank import completion, serve, stop, wait_ready
    tok = AutoTokenizer.from_pretrained(a.base)

    def gen_for(system: str, user: str, conv=None):
        head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)

        def gen(prefix: str) -> str:
            n = len(tok(head + prefix)["input_ids"])
            if n + a.max_tokens_plain > wa.MAX_MODEL_LEN:
                raise wa.ContextExhausted(f"{n} prompt tokens + {a.max_tokens_plain} > {wa.MAX_MODEL_LEN}")
            return completion(a.base, head + prefix, a.max_tokens_plain, ())
        return gen

    p = serve(a.base, ["--max-model-len", str(wa.MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90"])
    try:
        if not wait_ready(p):
            rec["stopped"] = "the base never came up"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            print(f"[arm] {rec['stopped']}", flush=True)
            return 1
        for name, rows in sets.items():
            walks = w5["arms"]["withlib"][name]["records"]
            slot = rec["arms"].setdefault("composed", {}).setdefault(name, {"records": {}})
            todo = [r for r in rows if r["case_id"] not in slot["records"] or "error" in slot["records"][r["case_id"]]]
            print(f"[arm] composed · {name}: {len(todo)} to run, {len(rows) - len(todo)} resumed", flush=True)
            t0, n = time.time(), 0
            with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
                for f in as_completed([ex.submit(run_case, lib, r, walks[r["case_id"]], gen_for) for r in todo]):
                    r = f.result(); slot["records"][r["id"]] = r; n += 1
                    if n % 20 == 0 or n == len(todo):
                        save()
                        done = [x for x in slot["records"].values() if "error" not in x]
                        print(f"[arm] composed · {name} {len(slot['records'])}/{len(rows)} credit "
                              f"{sum(x['credit'] for x in done)} errors {len(slot['records']) - len(done)} "
                              f"{time.time() - t0:.0f}s", flush=True)
            save()
    finally:
        stop(p)
    rec["analysis"] = analyse(rec, sets)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for pr in rec["analysis"]["pairs"].get("headline", []):
        print(f"[arm] headline · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})", flush=True)
    print(f"[arm] {rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("decided") else 1


if __name__ == "__main__":
    raise SystemExit(main())
