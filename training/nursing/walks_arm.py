r"""W5 — the kill arm of the memory: does a library extend an expert to a procedure it never trained on?

Four arms on the same cases, `training/nursing/data_walks/eval_heldout.jsonl` (the procedure no
training row ever opened) and `eval_control.jsonl` (the trained band), all served by one vLLM:

    base-reads   the UNTRAINED base, the oracle's notes open in its prompt, no verbs — the control
                 docs/MEMORY.md §4 demands of every arm from W5 on. The notes are rendered by the
                 runtime, by executing the oracle's own plan; nothing is copied.
    base-walks   the untrained base under the member's own prompt and verbs, walking by itself — what
                 navigation costs when nothing taught it.
    nolib        the adapter trained on the same 600 cases with no verbs and no notes.
    withlib      the adapter trained on the walks. Served exactly what its corpus taught: the user
                 turn is asserted byte-equal to the stored one before a token is generated.

BOUGHT IN SEQUENCE. `--arms base-reads,base-walks` needs no adapter and runs first: if the base
already reads its way to the ceiling there is nothing for a trained arm to beat, and that is known
for one short session instead of three.

THE VERDICT (docs/MEMORY.md W5), on the HEADLINE subset — held-out rows at depth ≤ 9 (the deepest
trained walk) whose final line no other procedure states — by CREDIT (`right` or `format`,
`training/nursing/grade_walks.py`), paired by case id with the exact two-sided sign test on
discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

    withlib vs nolib        must be an improvement
    withlib vs base-reads   must be an improvement     — else the memory stops at this model size

Reported beside the headline and never folded into it: the two depth-15 rows (walk-length
generalisation is a second unknown); the rows ending on a shared line; quantity by layer (site/case
against textbook, whose value is common knowledge); control with and without `rate` (its formulas are
nursing-school arithmetic); retrieval misses (the searcher is the LEXICAL one the corpus was
generated with — radar R0 did not pass W3); `context` — the prompt outgrew the window — and `format`
as their own buckets; transport errors, which are never a score.

A SESSION LIVES SIXTY MINUTES: `--train withlib --stop-after-training` and `--train nolib
--stop-after-training` are a session each, the adapter packed and said so; scoring carries both in.
`--floor` needs no GPU: the trivial policy *open result #1, answer the last page* through the real
runtime and the real grader — the floor every arm has to clear.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory import prompt
from memory.notes import Library
from memory.runtime import ChainSuite
from training.harness.accept_rank import run_chain
from training.nursing import generate_walks as gw
from training.nursing import grade_walks as gr
from training.nursing.library import ROOT

BASE = "Qwen/Qwen3.5-4B"
TRAINED = {"withlib": {"corpus": str(gw.FILES["train"]), "adapter": "adapters/nursing-walks-q35"},
           "nolib": {"corpus": str(gw.FILES["train_nolib"]), "adapter": "adapters/nursing-walks-nolib-q35"}}
ARMS = ("base-reads", "base-walks", "nolib", "withlib")
WALKING = ("base-walks", "withlib")
SETS = {"heldout": gw.FILES["eval_heldout"], "control": gw.FILES["eval_control"]}
MAX_TRAINED_DEPTH = 9
MAX_MODEL_LEN = 8192
NO_HEADROOM = 51 / 56       # at ≥ 51 of 56 the control leaves ≤ 5 discordant pairs: 5:0 is p = 0.0625, unbeatable
SYSTEM_READS = ("You are a specialist. The notes you need are open below, in the order a careful walk "
                "through the library would open them. Work only from them. Answer in one line, in the form "
                "the question asks for. If the notes hold nothing for the situation, say so: "
                "`Not in my library.`")


class ContextExhausted(RuntimeError):
    pass


# ------------------------------------------------------------------ what each arm is served
def oracle_pages(lib: Library, row: dict) -> list[str]:
    """The pages the oracle's walk reads, written by the runtime executing the oracle's plan."""
    conv, page = gw.conversation(lib, gw.case_of(row))
    pages = [page] if page else []
    for step in row["replay"]["plan"]:
        if step[0] == "open":
            pages.append(f"<open>{conv.opaque[step[1]]}</open>= " + conv.answer("open", ">" + conv.opaque[step[1]]))
        elif step[0] == "search":
            conv.answer("search", f" shelf={step[1]}>{step[2]}")
        else:
            pages.append(f"<calc>{step[1]}</calc>= " + conv.answer("calc", ">" + step[1]))
    return pages


def served(lib: Library, row: dict, arm: str):
    """(system, user, conversation or None). The walking arms get the member's turn, byte for byte."""
    if arm in WALKING:
        conv, page = gw.conversation(lib, gw.case_of(row))
        user = gw.user_turn(gw.case_of(row), page)
        if user != row["messages"][1]["content"]:
            raise AssertionError(f"{row['case_id']}: the served turn is not the turn the corpus taught")
        return prompt.SYSTEM, user, conv
    if arm == "nolib":
        return prompt.SYSTEM_NO_LIBRARY, row["statement"], None
    notes = "\n\n".join(oracle_pages(lib, row)) or "(the library returned no note for this situation)"
    return SYSTEM_READS, f"{row['statement']}\n\nThe notes:\n{notes}", None


# ------------------------------------------------------------------ one case, one arm
def retrieval(conv, row: dict) -> dict:
    searches = [l for l in conv.log if l["verb"] == "search" and "returned" in l]
    wanted = set(row["walk"])
    hit = any(wanted & set(l["returned"]) for l in searches)
    needs = any(a[0] == "search" for a in row["replay"]["plan"]) and bool(wanted)
    return {"searches": len(searches), "needed": needs, "miss": bool(needs and not hit)}


def run_case(lib: Library, row: dict, arm: str, gen_for, max_calls: int = gw.MAX_CALLS) -> dict:
    """`gen_for(system, user, conv)` returns `gen(prefix) -> continuation` — the model, or a scripted
    policy (`conv` is None for an arm with no verbs; the model never looks at it)."""
    system, user, conv = served(lib, row, arm)
    rec = {"id": row["case_id"], "family": row["family"], "variant": row["variant"]}
    try:
        gen = gen_for(system, user, conv)
        if conv is None:
            final, chain = gen(""), None
        else:
            suite = ChainSuite(conv)
            chain = run_chain(suite.wrap(gen), {}, max_calls=max_calls, suite=suite)
            final = chain["spans"][-1]["text"] if chain["spans"] else ""
    except ContextExhausted as e:
        return {**rec, "state": "context", "credit": False, "correct": False, "detail": str(e)[:120]}
    except Exception as e:                                   # transport — never folded into a score
        return {**rec, "error": repr(e)[:160]}
    walk = gr.walk_evidence(conv, len(row["replay"]["carried"]), chain) if conv is not None else None
    g = gr.grade(lib, row, final, walk)
    rec.update(g, correct=g["credit"], final=final[-400:])
    if conv is not None:
        rec.update(calls=chain["calls"], refused=chain["refused"], malformed=chain["malformed"],
                   ran_out=chain["ran_out"], ended=conv.ended, errors=dict(conv.errors),
                   opened=len(walk["opened"]), violations=walk["violations"], retrieval=retrieval(conv, row),
                   # THE WHOLE WALK, AND WHICH NOTES. This kept a count and the last 1500 characters, and
                   # the composition arm then could not prove what 6 of 140 walks had opened: they were
                   # excluded, and the exclusion was not neutral [ran] M7-W5b. A record is what a later
                   # arm replays; `text_full` tells a reader this one has its head. Changes no score.
                   opened_ids=list(walk["opened"]), text=chain["text"], text_full=True)
    return rec


# ------------------------------------------------------------------ the floor, zero GPU
def floor_policy(system: str, user: str, conv=None):
    """Open result #1, follow a skeleton to its first step, answer the last page. No comprehension."""
    carry = "report the last step" in user

    def gen(prefix: str) -> str:
        results = re.findall(r"</(search|open|calc)>= (.*?)(?=\n<(?:search|open|calc)|\Z)", prefix, re.S)
        if not results:
            nxt = re.findall(r"\n  next (\w+)", user.split("\n\nThe following tools")[0])
            if nxt:
                return f"<open>{nxt[-1]}</open>"
            return f"<search shelf=harness>{user.splitlines()[0]}</search>"
        verb, res = results[-1]
        if res.startswith("ERROR"):
            return "Not in my library."
        if verb == "search":
            m = re.search(r"\[(\w+)\]", res)
            return f"<open>{m.group(1)}</open>" if m else "Not in my library."
        first = re.search(r"First step: (\w+)", res)
        if first and prefix.count("<open>") < 3:
            return f"<open>{first.group(1)}</open>"
        line = res.splitlines()[0]
        return f"{gr.CARRY_PREFIX} {line}" if carry else line
    return gen


def floor(lib: Library, sets: dict) -> dict:
    out = {}
    for name, rows in sets.items():
        recs = [run_case(lib, r, "withlib", floor_policy) for r in rows]
        out[name] = {"records": {r["id"]: r for r in recs}}
    return out


# ------------------------------------------------------------------ slices, pairs, verdict
def slices(sets: dict) -> dict[str, list[str]]:
    h, c = sets["heldout"], sets["control"]
    shared = lambda r: bool(r["meta"].get("final_is_a_shared_line"))
    ids = lambda rows: [r["case_id"] for r in rows]
    return {
        "headline": ids(r for r in h if r["depth"] <= MAX_TRAINED_DEPTH and not shared(r)),
        "heldout_deeper_than_trained": ids(r for r in h if r["depth"] > MAX_TRAINED_DEPTH),
        "heldout_shared_line": ids(r for r in h if shared(r) and r["depth"] <= MAX_TRAINED_DEPTH),
        "heldout_carry": ids(r for r in h if r["family"] == "carry" and r["depth"] <= MAX_TRAINED_DEPTH and not shared(r)),
        "heldout_quantity_site_or_case": ids(r for r in h if r["family"] == "quantity" and r["meta"].get("layer") in ("site", "case")),
        "heldout_quantity_textbook": ids(r for r in h if r["family"] == "quantity" and r["meta"].get("layer") == "textbook"),
        "control": ids(c),
        "control_without_rate": ids(r for r in c if r["family"] != "rate"),
        "control_rate": ids(r for r in c if r["family"] == "rate"),
    }


def summarise(records: dict, ids: list[str]) -> dict:
    recs = [records[i] for i in ids if i in records]
    scored = [r for r in recs if "error" not in r]
    states = {}
    for r in scored:
        states[r["state"]] = states.get(r["state"], 0) + 1
    walked = [r for r in scored if "retrieval" in r]
    miss = [r for r in walked if r["retrieval"]["miss"]]
    return {"n": len(ids), "scored": len(scored), "errors": len(recs) - len(scored), "missing": len(ids) - len(recs),
            "credit": sum(r["credit"] for r in scored), "right": states.get("right", 0), "states": states,
            "verbatim": sum(bool(r.get("verbatim")) for r in scored),
            "retrieval_misses": len(miss),
            "credit_where_retrieval_hit": sum(r["credit"] for r in walked if not r["retrieval"]["miss"]),
            "n_where_retrieval_hit": len(walked) - len(miss)}


def _pair(a: dict, b: dict, ids: list[str], label: str) -> dict:
    from training.harness.release_gate import pair
    keep = [i for i in ids if i in a and i in b and "error" not in a[i] and "error" not in b[i]]
    return pair([{"id": i, "correct": a[i]["credit"]} for i in keep],
                [{"id": i, "correct": b[i]["credit"]} for i in keep], label)


def analyse(rec: dict, sets: dict) -> dict:
    sl = slices(sets)
    arms = {a: {**rec["arms"][a]["heldout"]["records"], **rec["arms"][a]["control"]["records"]}
            for a in rec.get("arms", {}) if all(s in rec["arms"][a] for s in SETS)}
    out = {"slices": {k: len(v) for k, v in sl.items()},
           "summary": {a: {k: summarise(r, ids) for k, ids in sl.items()} for a, r in arms.items()}, "pairs": {}}
    for k, ids in sl.items():
        out["pairs"][k] = [_pair(arms["withlib"], arms[o], ids, f"withlib vs {o}")
                           for o in ("nolib", "base-reads", "base-walks") if "withlib" in arms and o in arms and ids]
    return out


def verdict(rec: dict) -> dict:
    a = rec.get("analysis", {})
    head = {p["pair"]: p["state"] for p in a.get("pairs", {}).get("headline", [])}
    g1 = rec.get("G1", {})
    applied = all(g1.get(m, {}).get("applied") for m in TRAINED) if g1 else False
    errors = sum(s["headline"]["errors"] + s["headline"]["missing"] for s in a.get("summary", {}).values())
    base = a.get("summary", {}).get("base-reads", {}).get("headline")
    out = {"G1": applied, "headline_pairs": head, "headline_errors_or_missing": errors,
           "base_reads_headline": base and f"{base['credit']}/{base['scored']}"}
    out["no_headroom"] = bool(base and base["scored"] and base["credit"] / base["scored"] >= NO_HEADROOM)
    if "withlib vs nolib" not in head:
        out["passed"] = False
        if not base:
            out["reading"] = "NOTHING SCORED"
        elif out["no_headroom"]:
            out["reading"] = (f"NO HEADROOM: the untrained base reads its way to {out['base_reads_headline']} on the "
                              "headline — no trained arm can beat that by a sign test on this n. Stop before "
                              "training; the decision is the user's")
        else:
            out["reading"] = (f"HEADROOM: the untrained base reads its way to {out['base_reads_headline']} on the "
                              "headline — there is room; buy the trained arms")
        return out
    if not applied:
        out.update(passed=False, reading="VOID: an adapter is not applied — nothing here is about an expert")
    elif errors:
        out.update(passed=False, reading=f"VOID: {errors} headline records missing or lost to transport")
    else:
        ok = head.get("withlib vs nolib") == "improvement" and head.get("withlib vs base-reads") == "improvement"
        out["passed"] = ok
        out["reading"] = ("EXTENDS: on a procedure it never trained on, the library arm beats the arm without "
                          "one and beats the untrained base reading the same notes" if ok else
                          "DOES NOT PASS W5 AS WRITTEN: " + ", ".join(f"{k} is {v}" for k, v in head.items()
                                                                        if k != "withlib vs base-walks" and v != "improvement"))
    return out


# ------------------------------------------------------------------ the session
def sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--train", choices=sorted(TRAINED), help="train this adapter in this session")
    ap.add_argument("--stop-after-training", dest="train_only", action="store_true")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--floor", action="store_true", help="zero GPU: the trivial policy through the runtime")
    ap.add_argument("--max-tokens", type=int, default=160, help="per step, for an arm that walks")
    ap.add_argument("--max-tokens-plain", type=int, default=320, help="the whole reply, for an arm with no verbs")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="walks_arm.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.pop("trained_only", None)
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"),
               grader="training.nursing.grade_walks", searcher="lexical (memory.runtime.Lexical) — R0 did not pass W3")
    for k in ("arms", "G1", "members"):
        rec.setdefault(k, {})
    lib = Library.load(ROOT)
    sets = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in SETS.items()}

    def save():
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    if a.floor:
        f = floor(lib, sets)
        both = {**f["heldout"]["records"], **f["control"]["records"]}
        rec["floor"] = {k: summarise(both, ids) for k, ids in slices(sets).items()}
        save()
        print(f"[arm] floor, headline: {rec['floor']['headline']['credit']}/{rec['floor']['headline']['n']} · "
              f"control: {rec['floor']['control']['credit']}/{rec['floor']['control']['n']}", flush=True)
        return 0

    save()
    if a.train:
        from training.harness.release_gate import RECIPE
        spec = TRAINED[a.train]
        if not Path(spec["adapter"], "adapter_model.safetensors").exists():
            print(f"[pool] training {a.train} on {a.base} from {spec['corpus']}", flush=True)
            rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base,
                                  "--train", spec["corpus"], "--out-dir", spec["adapter"],
                                  "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                                  "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"])])
            if rc != 0:
                rec["stopped"] = f"training {a.train} failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
                print(f"[pool] {rec['stopped']}", flush=True)
                return 1
        rec["recipe"] = RECIPE
    have = {m: s for m, s in TRAINED.items() if Path(s["adapter"], "adapter_model.safetensors").exists()}
    for m, s in have.items():
        note = Path(s["adapter"], "rekey.json")
        rec["members"][m] = {"adapter": s["adapter"], "corpus": s["corpus"], "corpus_sha256": sha256(Path(s["corpus"])),
                             "adapter_sha256": sha256(Path(s["adapter"], "adapter_model.safetensors")),
                             "named_for_serving": json.loads(note.read_text()) if note.exists() else None}
    if have:
        subprocess.call(["tar", "czf", "adapters_out.tgz", *[s["adapter"] for s in have.values()]])
        rec["packed"] = len(have)
        save()
    if a.train_only:
        rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print(f"[pool] trained and packed {rec.get('packed')} — stopping before serving, as asked", flush=True)
        return 0

    arms = [x for x in a.arms.split(",") if x]
    unknown = [x for x in arms if x not in ARMS]
    lacking = [x for x in arms if x in TRAINED and x not in have]
    if unknown or lacking:
        print(f"[arm] cannot score: unknown {unknown}, adapters not on disk {lacking}", flush=True)
        return 2

    from transformers import AutoTokenizer
    from training.harness.accept_rank import completion, serve, stop, wait_ready
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    lora = [x for x in arms if x in TRAINED]
    extra = ["--max-model-len", str(MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90"]
    if lora:
        extra += ["--enable-lora", "--max-lora-rank", "16", "--max-loras", str(len(lora)),
                  "--lora-modules", *[f"{m}={TRAINED[m]['adapter']}" for m in lora]]

    def gen_for_model(model: str):
        def gen_for(system: str, user: str, conv=None):
            # AN ARM WITH NO VERBS HAS NO TAG TO STOP AT, and is given room to say it its own way.
            close, budget = (ChainSuite.close, a.max_tokens) if conv is not None else ((), a.max_tokens_plain)
            head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                           tokenize=False, add_generation_prompt=True, enable_thinking=False)

            def gen(prefix: str) -> str:
                n = len(tok(head + prefix)["input_ids"])
                if n + budget > MAX_MODEL_LEN:
                    raise ContextExhausted(f"{n} prompt tokens + {budget} > {MAX_MODEL_LEN}")
                return completion(model, head + prefix, budget, close)
            return gen
        return gen_for

    p = serve(a.base, extra)
    try:
        if not wait_ready(p):
            rec["stopped"] = "the base never came up"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            print(f"[arm] {rec['stopped']}", flush=True)
            return 1
        for m in lora:
            rec["G1"][m] = identity(a.base, m, tok)
            print(f"[pool] G1 {m}: {'applied' if rec['G1'][m]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
        if not all(rec["G1"][m]["applied"] for m in lora):
            rec["stopped"] = "G1: an adapter is not applied"
        else:
            for arm in arms:                                  # ARMS order: the controls first
                model = arm if arm in TRAINED else a.base
                for name, rows in sets.items():
                    slot = rec["arms"].setdefault(arm, {}).setdefault(name, {"records": {}})
                    todo = [r for r in rows if r["case_id"] not in slot["records"]
                            or "error" in slot["records"][r["case_id"]]]
                    print(f"[arm] {arm} · {name}: {len(todo)} to run, {len(rows) - len(todo)} resumed", flush=True)
                    t0, n = time.time(), 0
                    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
                        for f in as_completed([ex.submit(run_case, lib, r, arm, gen_for_model(model)) for r in todo]):
                            r = f.result(); slot["records"][r["id"]] = r; n += 1
                            if n % 20 == 0 or n == len(todo):
                                save()
                                done = [x for x in slot["records"].values() if "error" not in x]
                                print(f"[arm] {arm} · {name} {len(slot['records'])}/{len(rows)} credit "
                                      f"{sum(x['credit'] for x in done)} errors {len(slot['records']) - len(done)} "
                                      f"{time.time() - t0:.0f}s", flush=True)
                    save()
    finally:
        stop(p)
    rec["analysis"] = analyse(rec, sets)
    rec["verdict"] = verdict(rec)
    # WHICH MARKER ENDS THIS SESSION. The chain reads `"finished"` as *the run is decided — no further
    # sessions, and do not carry this file in*; it reads `"trained_only"` as *this session is over, the
    # run is not* and strips it on the way into the next one. A headroom session that found room is
    # the second kind, whatever the marker is called: its records are what the scoring session resumes.
    decided = "withlib" in arms or rec["verdict"].get("no_headroom") or bool(rec.get("stopped"))
    rec["finished" if decided else "trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for pr in rec["analysis"]["pairs"].get("headline", []):
        print(f"[arm] headline · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})", flush=True)
    print(f"[arm] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("passed") or not decided else 1

if __name__ == "__main__":
    raise SystemExit(main())
