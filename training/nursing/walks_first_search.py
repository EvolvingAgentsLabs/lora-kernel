r"""W5e — the referee writes the first query: one unknown, the text of the walk's first search.

W5d **[ran]** left one thing standing between the answer policy and a pass. Where the adapter's walk
opened the supplying note, the bare base read it right 21 of 21; the other 11 value rows of the headline
were retrieval misses, and in 9 of the 11 the adapter wrote, word for word, a query its corpus holds 68
times for another topic — on the RIGHT shelf (`wiki`), with the WRONG words. The same lexical searcher
given the request's own statement lists the needed note 16 of 16 (zero GPU).

THE TREATMENT (`memory.runtime.Conversation.first_query`). The conversation's first `<search>` runs on
the statement, on the shelf the adapter named; the adapter's words are logged, not searched; every later
search is the adapter's own. Applied to EVERY row — the referee does not know a task's kind — so carry
rows are re-walked under it too, and control is where that is paid for, if it is.

WHERE IT IS READ — W5d's own sets, and that is ATTRIBUTION, never the claim. Those sets were written after
W5d's freeze and are seen by us now: the 11 misses are why this arm exists. A pass here buys the next
step — a set written after THIS freeze — and is never quoted as a result of the design on fresh cases.

THE ADAPTER IS RETRAINED, SO THE BASELINE IS RE-RUN. W5c's `withlib` was never stored outside a scratchpad
that no longer exists; it is retrained from the same corpus and recipe (one A100 session, `walks_arm --data
data_walks_v2 --tag v2 --train withlib`). A retrained adapter is not W5c's bit for bit, so W5d's recorded
`withlib`/`policy` do not pair with it: both are re-run here, in the same session as the treatment, which
also takes vLLM's session-to-session spread out of the pair.

    recorded (copied from W5d, beside only)   base-reads — no adapter in it
    bought here (one L4 session, no training) withlib      the retrained adapter walks, its own queries
                                              withlib-fs   the same adapter under the referee's first query
                                              policy       W5d's frozen policy over `withlib`'s walks
                                              policy-fs    the same policy over `withlib-fs`' walks

THE VERDICT, by CREDIT (`grade_walks`, untouched), paired by case id, exact two-sided sign test on
discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, $p<0.05$:

    headroom    `withlib` (this session) loses fewer than 4 headline value rows to a retrieval miss → NO
                HEADROOM: the retrained adapter does not show the failure, nothing is left to repair
    mechanism   of those rows, the walk under the referee's first query STILL does not open the supplying
                note on at least half  → FALSIFIED: the listing is not enough, the walk itself is memorised
                (W5d's own falsifier was 6 of its 11)
    headline    policy-fs vs policy     must be an IMPROVEMENT
    control     policy-fs vs policy     must NOT be a REGRESSION — the referee's query costs the trained band

Beside, never folded in: policy-fs vs base-reads (W5's bar), withlib-fs vs withlib, right-only pairs, value
rows' retrieval misses (predicted ≤ 2 of 32, from 11), the adapter's written query where it was replaced.
W5d's 11 are reported beside, walked by the retrained adapter with and without the referee.
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory.notes import Library
from memory.runtime import ChainSuite, Lexical
from training.nursing import walks_arm as wa
from training.nursing import walks_policy as wp
from training.nursing.library import ROOT

DATA = Path("training/nursing/data_walks_w5d")
W5D = Path("results/M7-W5d-answer-policy-20260920/walks_policy.json")
RECORDED = ("base-reads", "withlib", "policy")      # W5d's: `base-reads` is paired beside; the other two define the 11
ARMS = ("withlib", "withlib-fs", "policy", "policy-fs")
MIN_MISSES = 4             # below it the retrained adapter does not show the failure: no headroom
MECHANISM_BAR = 6          # W5d's own falsifier, on its 11 — the fixture test holds the scripted walker to it


def still_bar(misses: int) -> int:
    """FALSIFIED at or above: half of the rows the adapter's own query lost, rounded up (6 of W5d's 11)."""
    return (misses + 1) // 2


def load(rec_w5d: dict) -> dict:
    """W5d's claim-stage records, by arm, both sets merged."""
    arms = rec_w5d["claim"]["arms"]
    return {a: {**arms[a]["heldout"]["records"], **arms[a]["control"]["records"]} for a in RECORDED}


def missed(sets: dict, recorded: dict) -> list[str]:
    """W5d's value rows on the headline that the policy lost to a retrieval miss of the adapter's walk."""
    head = set(wa.slices(sets)["headline"])
    return sorted(i for i, r in recorded["policy"].items()
                  if i in head and r.get("written_by") == "base" and not r["credit"]
                  and recorded["withlib"][i].get("retrieval", {}).get("miss"))


def zero_gpu(lib: Library, sets: dict, gone: list[str]) -> dict:
    """What the referee's query lists, no model: the oracle's first shelf, the statement as the query."""
    lx, rows = Lexical(lib), {r["case_id"]: r for rs in sets.values() for r in rs}
    out = {}
    for name, ids in {**wa.slices(sets), "w5d_missed": gone}.items():
        need = hit = supplying = 0
        for i in ids:
            plan = rows[i]["replay"]["plan"]
            first = next((s for s in plan if s[0] == "search"), None)
            if first is None or not rows[i]["walk"]:
                continue
            need += 1
            listed = set(lx.search(rows[i]["statement"], first[1], 3))
            hit += bool(listed & set(rows[i]["walk"]))
            supplying += rows[i]["walk"][-1] in listed
        out[name] = {"rows": len(ids), "need_a_search": need, "statement_lists_a_walk_note": hit,
                     "statement_lists_the_supplying_note": supplying}
    return out


def analyse(arms: dict, sets: dict, gone: list[str]) -> dict:
    sl = wa.slices(sets)
    out = {"slices": {k: len(v) for k, v in sl.items()},
           "summary": {a: {k: wa.summarise(r, ids) for k, ids in sl.items()} for a, r in arms.items()},
           "pairs": {}, "pairs_right_only": {}}
    duels = (("policy-fs", "policy"), ("policy-fs", "base-reads"), ("withlib-fs", "withlib"), ("policy", "withlib"))
    for k, ids in sl.items():
        live = [(a, b) for a, b in duels if a in arms and b in arms and ids]
        out["pairs"][k] = [wp._pair_on(arms[a], arms[b], ids, f"{a} vs {b}", lambda r: r["credit"]) for a, b in live]
        out["pairs_right_only"][k] = [wp._pair_on(arms[a], arms[b], ids, f"{a} vs {b}", lambda r: r.get("state") == "right")
                                      for a, b in live]
    if "withlib" in arms and "withlib-fs" in arms:
        rows = {r["case_id"]: r for rs in sets.values() for r in rs}
        plain, fs_ = arms["withlib"], arms["withlib-fs"]
        value = [i for i in sl["headline"] if rows[i]["family"] in wa.QUANTITY]
        ok = lambda w, i: i in w and "error" not in w[i]
        reached = lambda w, i: rows[i]["walk"][-1] in (w[i].get("opened_ids") or [])
        lost = [i for i in value if ok(plain, i) and plain[i].get("retrieval", {}).get("miss")]
        still = [i for i in lost if ok(fs_, i) and not reached(fs_, i)]
        out["mechanism"] = {
            "misses": len(lost), "miss_ids": lost, "scored": sum(ok(fs_, i) for i in lost),
            "still_not_opened": len(still), "still_ids": still, "falsified_at": still_bar(len(lost)),
            "value_rows": len(value),
            "value_rows_retrieval_misses": {a: sum(bool(w[i].get("retrieval", {}).get("miss")) for i in value if ok(w, i))
                                            for a, w in (("withlib", plain), ("withlib-fs", fs_))},
            "w5d_missed": {"n": len(gone), **{a: sum(ok(w, i) and reached(w, i) for i in gone)
                                              for a, w in (("withlib", plain), ("withlib-fs", fs_))}}}
    if "policy-fs" in arms:
        by = {}
        for r in arms["policy-fs"].values():
            if "error" not in r:
                w = by.setdefault(r.get("written_by", "?"), {"n": 0, "credit": 0})
                w["n"] += 1; w["credit"] += bool(r["credit"])
        out["policy_fs_by_writer"] = by
    return out


def verdict(rec: dict) -> dict:
    a = rec.get("analysis", {})
    head = {p["pair"]: p for p in a.get("pairs", {}).get("headline", [])}
    ctrl = {p["pair"]: p for p in a.get("pairs", {}).get("control", [])}
    m = a.get("mechanism")
    if "policy-fs vs policy" not in head or not m:
        return {"decided": False, "reading": "NOTHING SCORED"}
    show = lambda p: f"{p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})"
    s = a["summary"]
    lost = sum(s[x]["headline"]["errors"] + s[x]["headline"]["missing"] for x in ARMS if x in s)
    out = {"G1": bool(rec.get("G1", {}).get(wp.MEMBER, {}).get("applied")),
           "headline": {x: f"{s[x]['headline']['credit']}/{s[x]['headline']['scored']}" for x in s},
           "control": {x: f"{s[x]['control']['credit']}/{s[x]['control']['scored']}" for x in s},
           "pairs": {k: show(p) for k, p in head.items()},
           "pairs_right_only": {p["pair"]: show(p) for p in a["pairs_right_only"].get("headline", [])},
           "control_pairs": {k: show(p) for k, p in ctrl.items()},
           "mechanism": f"{m['still_not_opened']} of {m['misses']} still not opened (falsified at ≥ {m['falsified_at']})",
           "stage": "ATTRIBUTION on W5d's sets — seen; never the claim"}
    if not out["G1"]:
        return {**out, "decided": False, "passed": False, "reading": "VOID: the adapter is not applied"}
    if lost or m["scored"] < m["misses"]:
        return {**out, "decided": False, "passed": False, "reading": f"VOID: {lost} headline records missing or lost to transport"}
    if m["misses"] < MIN_MISSES:
        return {**out, "decided": True, "passed": False, "reading":
                f"NO HEADROOM: the retrained adapter loses only {m['misses']} value rows to its own query — nothing to repair"}
    listing = m["still_not_opened"] < m["falsified_at"]
    buys = head["policy-fs vs policy"]["state"] == "improvement"
    keeps = ctrl.get("policy-fs vs policy", {}).get("state") != "REGRESSION"
    out.update(decided=True, listing_is_enough=listing, buys_something=buys, control_holds=keeps,
               passed=bool(listing and buys and keeps))
    if not listing:
        out["reading"] = (f"FALSIFIED: shown the statement's listing, the walk still missed the supplying note on "
                          f"{m['still_not_opened']} of {m['misses']} — the walk itself is memorised, not only its query")
    elif not buys:
        out["reading"] = f"NOT BOUGHT: the listing reaches the note, and policy-fs vs policy is {show(head['policy-fs vs policy'])}"
    elif not keeps:
        out["reading"] = (f"NOT A SERVING DESIGN: the referee's query repairs the held-out procedure and costs the trained band — "
                          f"control {show(ctrl['policy-fs vs policy'])}")
    else:
        out["reading"] = (f"THE REFEREE'S QUERY REPAIRS THE MISS — on a seen set: policy-fs vs policy {show(head['policy-fs vs policy'])}, "
                          f"control {show(ctrl['policy-fs vs policy'])}, against W5's bar {show(head['policy-fs vs base-reads'])}. "
                          "Next is a set written after this freeze; this is attribution, not the claim")
    return out


# ------------------------------------------------------------------ the session
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=wa.BASE)
    p.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    p.add_argument("--zero-gpu", action="store_true", help="what the referee's query lists, and W5d's missed ids — no model")
    p.add_argument("--max-tokens", type=int, default=160, help="per step, for the arm that walks")
    p.add_argument("--max-tokens-plain", type=int, default=320, help="the whole reply, for an arm with no verbs")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--out", default="walks_first_search.json")
    a = p.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    lib = Library.load(ROOT)
    sets = wp.load_sets(DATA)
    recorded = load(json.loads(W5D.read_text()))
    gone = missed(sets, recorded)
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"), grader="training.nursing.grade_walks",
               adapter=wp.ADAPTER, sets=str(DATA), recorded_in=str(W5D), treatment="Conversation.first_query = statement",
               w5d_missed=gone, zero_gpu=zero_gpu(lib, sets, gone))
    rec.setdefault("arms", {})

    def save():
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    if a.zero_gpu:
        save()
        z = rec["zero_gpu"]
        print(f"[arm] first-search, zero GPU · W5d missed {len(gone)} · the statement lists the supplying note on "
              f"{z['w5d_missed']['statement_lists_the_supplying_note']}/{z['w5d_missed']['need_a_search']} of them · headline "
              f"{z['headline']['statement_lists_a_walk_note']}/{z['headline']['need_a_search']} list a walk note · control "
              f"{z['control']['statement_lists_a_walk_note']}/{z['control']['need_a_search']}", flush=True)
        return 0

    if not Path(wp.ADAPTER, "adapter_model.safetensors").exists():
        print(f"[arm] cannot score: {wp.ADAPTER} is not on disk — carry W5c's adapters.tgz into this run directory", flush=True)
        return 2
    rec["adapter_sha256"] = wa.sha256(Path(wp.ADAPTER, "adapter_model.safetensors"))   # retrained: not W5c's 0f7d872d…
    save()
    from transformers import AutoTokenizer
    from training.harness.accept_rank import completion, serve, stop, wait_ready
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)

    def gen_for_model(model: str):
        def gen_for(system: str, user: str, conv=None):
            close, budget = (ChainSuite.close, a.max_tokens) if conv is not None else ((), a.max_tokens_plain)
            head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                           tokenize=False, add_generation_prompt=True, enable_thinking=False)

            def gen(prefix: str) -> str:
                n = len(tok(head + prefix)["input_ids"])
                if n + budget > wa.MAX_MODEL_LEN:
                    raise wa.ContextExhausted(f"{n} prompt tokens + {budget} > {wa.MAX_MODEL_LEN}")
                return completion(model, head + prefix, budget, close)
            return gen
        return gen_for

    def run(arm: str, name: str, rows: list, one) -> None:
        slot = rec["arms"].setdefault(arm, {}).setdefault(name, {"records": {}})
        todo = [r for r in rows if r["case_id"] not in slot["records"] or "error" in slot["records"][r["case_id"]]]
        print(f"[arm] {arm} · {name}: {len(todo)} to run, {len(rows) - len(todo)} resumed", flush=True)
        t0, n = time.time(), 0
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            for f in as_completed([ex.submit(one, r) for r in todo]):
                r = f.result(); slot["records"][r["id"]] = r; n += 1
                if n % 20 == 0 or n == len(todo):
                    save()
                    done = [x for x in slot["records"].values() if "error" not in x]
                    print(f"[arm] {arm} · {name} {len(slot['records'])}/{len(rows)} credit "
                          f"{sum(bool(x['credit']) for x in done)} errors {len(slot['records']) - len(done)} {time.time() - t0:.0f}s",
                          flush=True)
        save()

    srv = serve(a.base, ["--max-model-len", str(wa.MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90", "--enable-lora",
                         "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{wp.MEMBER}={wp.ADAPTER}"])
    try:
        if not wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            rec.setdefault("G1", {})[wp.MEMBER] = identity(a.base, wp.MEMBER, tok)
            print(f"[pool] G1 {wp.MEMBER}: {'applied' if rec['G1'][wp.MEMBER]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not rec["G1"][wp.MEMBER]["applied"]:
                rec["stopped"] = "G1: the adapter is not applied"
            else:
                base, member = gen_for_model(a.base), gen_for_model(wp.MEMBER)
                # THE BASELINE FIRST: it is the headroom — if its own query does not miss, nothing is left to repair.
                for arm, fq in (("withlib", False), ("withlib-fs", True)):
                    for name, rows in sets.items():
                        run(arm, name, rows, lambda r, fq=fq: wa.run_case(lib, r, "withlib", member, first_query=fq))
                for arm, walks in (("policy", "withlib"), ("policy-fs", "withlib-fs")):
                    for name, rows in sets.items():
                        walked = rec["arms"][walks][name]["records"]
                        run(arm, name, rows, lambda r, w=walked: wp.policy_case(lib, r, w[r["case_id"]], base))
    finally:
        stop(srv)
    arms = {"base-reads": recorded["base-reads"], **{x: {**v["heldout"]["records"], **v["control"]["records"]} for x, v in rec["arms"].items()
                           if all(s in v for s in ("heldout", "control"))}}
    rec["analysis"] = analyse(arms, sets, gone)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for pr in rec["analysis"]["pairs"].get("headline", []):
        print(f"[arm] headline · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})", flush=True)
    print(f"[arm] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("decided") else 1


if __name__ == "__main__":
    raise SystemExit(main())
