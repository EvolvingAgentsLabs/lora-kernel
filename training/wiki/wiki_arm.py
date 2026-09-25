r"""W9 — atomic statements: does the untrained base walk a wiki of statements, and does a LoRA need to?

One unknown per stage, bought in sequence (docs/MEMORY.md §1.6, results/M7-W9-atomic-statements-20260924):

    headroom   one L4, no training — the bare `Qwen3.5-4B` on the evaluation world, three arms:
                   nolib        the question alone: the wiki's values must NOT be in the weights
                   base-reads   the oracle's statements open, each after its citation — the reading bar
                   base-walks   the verbs, the pages, the sections: the untrained base navigates
    training   ONLY if the headroom verdict says navigation is the gap: a trajectory LoRA on corpus
               worlds (never the evaluation world, never its wording), TWO seeds, one A100 each
    scoring    one L4: `withlib-s<k>` for each trained seed, against `base-walks` on the same rows

THE VERDICT (headroom), on the HEADLINE (two hops or more, a question the wiki answers), by credit
= `right` = value right AND citation verified (`grade.py`), paired by case id, exact two-sided sign
test on discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

    VOID                    nolib value-right > 10 % of the headline: the values are in the weights
    THE RUNTIME IS ENOUGH   base-walks >= 85 % — no trajectory LoRA is bought for this shape
    NAVIGATION IS THE GAP   base-reads >= 70 % and base-reads beats base-walks (improvement) → train
    READING IS THE GAP      base-reads < 70 % — a navigation LoRA would not close it: not bought
    NO ATTRIBUTABLE GAP     otherwise — not bought

THE VERDICT (scoring), per seed: `withlib-s<k> vs base-walks` on the headline must be an improvement.
Both seeds → PASSED; one → DRAW-DEPENDENT (W5e: two draws of one recipe disagreed on 25 of 67); none
→ FALSIFIED. Against `base-reads` beside, never folded in.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory import prompt
from memory.notes import Library
from memory.runtime import ChainSuite, Conversation
from training.harness.accept_rank import run_chain
from training.wiki import grade as gr
from training.wiki import questions as qs
from training.wiki import world as wd

BASE = "Qwen/Qwen3.5-4B"
LIBRARY = Path("knowledge") / wd.ROOT
DATA = Path("training/wiki/data")
MAX_CALLS = 24
MAX_MODEL_LEN = 8192
NOLIB_BAR, ENOUGH, READS_BAR = 0.10, 0.85, 0.70
SEEDS = (0, 1)
ARMS = ("nolib", "base-reads", "base-walks")


class ContextExhausted(RuntimeError):
    pass


def load_rows(name: str = "eval") -> list[dict]:
    return [json.loads(l) for l in (DATA / f"{name}.jsonl").read_text().splitlines() if l.strip()]


def conversation(lib: Library, row: dict) -> Conversation:
    """One case's referee — ids re-drawn per case, deterministically."""
    return Conversation(lib, seed=zlib.crc32(row["case_id"].encode()), mode="strict", log_content=True, max_opens=24)


# ------------------------------------------------------------------ the oracle, through the real loop
def oracle_gen(row: dict, conv: Conversation):
    """The oracle's walk as a scripted model: one tag per turn, the final line last. Driven through
    `run_chain`, so what a corpus holds is byte for byte what serving produces."""
    plan = row["plan"]

    def gen(prefix: str) -> str:
        done = prefix.count("</search>") + prefix.count("</open>")
        if done < len(plan):
            st = plan[done]
            if st[0] == "search":
                return f"<search shelf={st[1]}>{st[2]}</search>"
            o = conv.opaque[st[1]]
            return f"<open>{o}§{st[2]}</open>" if len(st) == 3 else f"<open>{o}</open>"
        if row["check"]["kind"] == "none":
            return row["answer"]
        nid, anchor = row["support"]
        return f"{row['answer']} [{conv.opaque[nid]}§{anchor}]"
    return gen


def walk(lib: Library, row: dict, gen, conv: Conversation | None = None) -> tuple[str, Conversation, dict]:
    conv = conv or conversation(lib, row)
    suite = ChainSuite(conv)
    chain = run_chain(suite.wrap(gen), {}, max_calls=MAX_CALLS, suite=suite)
    final = chain["spans"][-1]["text"] if chain["spans"] else ""
    return final, conv, chain


def oracle_sections(lib: Library, row: dict) -> tuple[str, Conversation]:
    """`base-reads`' turn: the oracle's statements, each after the citation it would be cited by."""
    conv = conversation(lib, row)
    lines = []
    for st in row["plan"]:
        if st[0] == "search":
            conv.answer("search", f" shelf={st[1]}>{st[2]}")
        elif len(st) == 2:
            conv.answer("open", ">" + conv.opaque[st[1]])
        else:
            text = conv.answer("open", f">{conv.opaque[st[1]]}§{st[2]}")
            lines.append(f"[{conv.opaque[st[1]]}§{st[2]}] {text}")
    body = "\n".join(lines) or "(the wiki returned no section for this question)"
    return f"{row['question']}\n\nThe sections:\n{body}", conv


# ------------------------------------------------------------------ one case, one arm
def run_case(lib: Library, row: dict, arm: str, gen_for) -> dict:
    """`gen_for(system, user, walking)` returns `gen(prefix)` — the model, or a scripted policy."""
    rec = {"id": row["case_id"], "family": row["family"], "block": row["block"], "hops": row["hops"]}
    try:
        if arm == "nolib":
            final, conv, chain = gen_for(prompt.SYSTEM_NO_LIBRARY, row["question"], False)(""), None, None
        elif arm == "base-reads":
            user, conv = oracle_sections(lib, row)
            final, chain = gen_for(prompt.SYSTEM_WIKI_READS, user, False)(""), None
        else:
            conv = conversation(lib, row)
            final, conv, chain = walk(lib, row, gen_for(prompt.SYSTEM_WIKI, prompt.user_text_wiki(row["question"]), True), conv)
    except ContextExhausted as e:
        return {**rec, "state": "context", "credit": False, "value_right": False, "detail": str(e)[:120]}
    except Exception as e:                                   # transport — never folded into a score
        return {**rec, "error": repr(e)[:160]}
    g = gr.grade(row, final, conv)
    rec.update(g, credit=g["state"] == "right", final=final[-300:])
    if chain is not None:
        rec.update(calls=chain["calls"], refused=chain["refused"], malformed=chain["malformed"], ran_out=chain["ran_out"],
                   ended=conv.ended, errors=dict(conv.errors), opened_pages=len(conv.opened),
                   opened_statements=[list(s) for s in conv.statements], text=chain["text"])
    return rec


# ------------------------------------------------------------------ zero GPU
def scripted(policy):
    return lambda system, user, walking: policy(user, walking)


def floor_policy(user: str, walking: bool):
    """Search the question, open the first page, open its first section, cite it. No comprehension."""
    def gen(prefix: str) -> str:
        if not walking:
            return "Not in my library."
        import re
        if "</search>" not in prefix:
            return f"<search shelf=wiki>{user.split(chr(10))[0]}</search>"
        found = re.findall(r"\[(\w{3})\]", prefix)
        if not found:
            return "Not in my library."
        page = found[0]
        if f"<open>{page}</open>" not in prefix:
            return f"<open>{page}</open>"
        sec = re.search(r"sections (§[a-z0-9-]+)", prefix)
        if not sec:
            return "Not in my library."
        cite = f"{page}{sec.group(1)}"
        if f"<open>{cite}</open>" not in prefix:
            return f"<open>{cite}</open>"
        stmt = prefix.rsplit("</open>= ", 1)[1].strip().splitlines()[0]
        return f"{stmt} [{cite}]"
    return gen


def oracle_record(lib: Library, row: dict) -> dict:
    """The oracle walked through the real loop and graded by the real grader."""
    conv = conversation(lib, row)
    final, conv, chain = walk(lib, row, oracle_gen(row, conv), conv)
    g = gr.grade(row, final, conv)
    return {"id": row["case_id"], **g, "credit": g["state"] == "right", "text": chain["text"], "calls": chain["calls"],
            "refused": chain["refused"]}


# ------------------------------------------------------------------ slices, pairs, verdicts
def slices(rows: list[dict]) -> dict[str, list[str]]:
    by = lambda pred: [r["case_id"] for r in rows if pred(r)]
    out = {"headline": by(qs.headline), "all": by(lambda r: True), "none": by(lambda r: r["check"]["kind"] == "none")}
    for h in (1, 2, 3):
        out[f"hops-{h}"] = by(lambda r, h=h: r["hops"] == h and r["check"]["kind"] == "value")
    for b in ("E1", "E2", "E3", "O1", "O2", "O3"):
        out[f"block-{b}"] = by(lambda r, b=b: r["block"] == b)
    return out


def summarise(records: dict, ids: list[str]) -> dict:
    got = [records[i] for i in ids if i in records]
    ok = [x for x in got if "error" not in x]
    count = lambda st: sum(x.get("state") == st for x in ok)
    return {"n": len(ids), "scored": len(ok), "errors": len(got) - len(ok), "missing": len(ids) - len(got),
            "credit": sum(bool(x["credit"]) for x in ok), "value_right": sum(bool(x.get("value_right")) for x in ok),
            "right": count("right"), "unverified": count("unverified"), "wrong": count("wrong"), "context": count("context")}


def pair(a: dict, b: dict, ids: list[str], label: str) -> dict:
    from training.harness.release_gate import pair as _pair
    keep = [i for i in ids if i in a and i in b and "error" not in a[i] and "error" not in b[i]]
    return _pair([{"id": i, "correct": bool(a[i]["credit"])} for i in keep],
                 [{"id": i, "correct": bool(b[i]["credit"])} for i in keep], label)


def analyse(arms: dict, rows: list[dict]) -> dict:
    sl = slices(rows)
    out = {"slices": {k: len(v) for k, v in sl.items()},
           "summary": {a: {k: summarise(r, ids) for k, ids in sl.items()} for a, r in arms.items()}, "pairs": {}}
    duels = [("base-reads", "base-walks")] + [(a, "base-walks") for a in arms if a.startswith("withlib")] \
        + [(a, "base-reads") for a in arms if a.startswith("withlib")]
    for k in ("headline", "all", "hops-2", "hops-3"):
        out["pairs"][k] = [pair(arms[a], arms[b], sl[k], f"{a} vs {b}") for a, b in duels if a in arms and b in arms]
    return out


def verdict(rec: dict) -> dict:
    a = rec.get("analysis", {})
    s = a.get("summary", {})
    if not all(x in s for x in ARMS):
        return {"decided": False, "reading": "NOTHING SCORED"}
    h = {x: s[x]["headline"] for x in s}
    n = h["base-walks"]["n"]
    lost = sum(h[x]["errors"] + h[x]["missing"] for x in ARMS)
    heads = {p["pair"]: p for p in a["pairs"]["headline"]}
    show = lambda p: f"{p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})"
    out = {"headline": {x: f"{h[x]['credit']}/{h[x]['scored']}" for x in h},
           "headline_value_right": {x: f"{h[x]['value_right']}/{h[x]['scored']}" for x in h},
           "pairs": {k: show(p) for k, p in heads.items()}}
    if lost:
        return {**out, "decided": False, "reading": f"VOID: {lost} headline records missing or lost to transport"}
    nolib = h["nolib"]["value_right"] / max(1, h["nolib"]["scored"])
    walks, reads = h["base-walks"]["credit"] / n, h["base-reads"]["credit"] / n
    rw = heads["base-reads vs base-walks"]["state"]
    out.update(decided=True, nolib_value_right=round(nolib, 3), base_walks=round(walks, 3), base_reads=round(reads, 3))
    if nolib > NOLIB_BAR:
        out.update(stage="VOID", train=False, reading=f"VOID: the closed-book base gets {nolib:.0%} of the headline — the values are in the weights")
    elif walks >= ENOUGH:
        out.update(stage="THE RUNTIME IS ENOUGH", train=False,
                   reading=f"THE RUNTIME IS ENOUGH: the untrained base walks {walks:.0%} of the headline, verified — no trajectory LoRA for this shape")
    elif reads < READS_BAR:
        out.update(stage="READING IS THE GAP", train=False,
                   reading=f"READING IS THE GAP: handed the oracle's statements the base is verified on {reads:.0%} — a navigation LoRA would not close it")
    elif rw == "improvement":
        out.update(stage="NAVIGATION IS THE GAP", train=True,
                   reading=f"NAVIGATION IS THE GAP: base-reads {reads:.0%} vs base-walks {walks:.0%}, {show(heads['base-reads vs base-walks'])} — train the trajectory LoRA, {len(SEEDS)} seeds")
    else:
        out.update(stage="NO ATTRIBUTABLE GAP", train=False,
                   reading=f"NO ATTRIBUTABLE GAP: base-walks {walks:.0%}, base-reads {reads:.0%}, {show(heads['base-reads vs base-walks'])}")
    seeds = sorted(x for x in s if x.startswith("withlib-s"))
    if seeds:
        wins = [x for x in seeds if heads.get(f"{x} vs base-walks", {}).get("state") == "improvement"]
        out["scoring"] = {x: show(heads[f"{x} vs base-walks"]) for x in seeds if f"{x} vs base-walks" in heads}
        unapplied = [x for x in seeds if not rec.get("G1", {}).get(x, {}).get("applied")]
        out["scoring_reading"] = (f"VOID: G1 does not show {unapplied} applied — no walk there is the member's" if unapplied else
                                  "PASSED: every seed beats the untrained walk" if len(wins) == len(seeds) else
                                  f"DRAW-DEPENDENT: {len(wins)} of {len(seeds)} seeds beat the untrained walk" if wins else
                                  "FALSIFIED: no seed beats the untrained walk")
    return out


# ------------------------------------------------------------------ the session
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--zero-gpu", action="store_true")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--train-seed", type=int, default=None, help="train adapters/wiki-walks-s<seed> and stop")
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--max-tokens-plain", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="wiki_arm.json")
    ap.add_argument("--combine", default=None, help="zero GPU: add this file's scored arms to --out's and re-read the verdict")
    a = ap.parse_args()
    if a.combine:
        # THE SCORING SESSION'S ARMS BESIDE STAGE 1'S, READ BY THE SAME `analyse` AND `verdict`. The
        # bare base was scored in stage 1's session; pairing across sessions carries vLLM's spread,
        # which the brief states — and base-walks sat at 0/40, where no spread can move a pair.
        rec = json.loads(Path(a.out).read_text())
        more = json.loads(Path(a.combine).read_text())
        rec["arms"].update({k: v for k, v in more["arms"].items() if k.startswith("withlib-s")})
        rec["G1"] = {**rec.get("G1", {}), **more.get("G1", {})}
        rec["scoring_from"] = a.combine
        rec["analysis"] = analyse(rec["arms"], load_rows("eval"))
        rec["verdict"] = verdict(rec)
        Path(a.out).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        for p in rec["analysis"]["pairs"]["headline"]:
            print(f"[wiki] headline · {p['pair']}: {p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})", flush=True)
        print(f"[wiki] {rec['verdict'].get('scoring_reading', rec['verdict']['reading'])}", flush=True)
        return 0
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"), grader="training.wiki.grade",
               library=str(LIBRARY), eval_world=wd.EVAL_SEED)
    rec.setdefault("arms", {})
    lib = Library.load(LIBRARY)
    rows = load_rows("eval")

    def save():
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    if a.zero_gpu:
        oracle = [oracle_record(lib, r) for r in rows]
        head = {r["case_id"] for r in rows if qs.headline(r)}
        floor = {r["case_id"]: run_case(lib, r, "base-walks", scripted(floor_policy)) for r in rows}
        rec["zero_gpu"] = {"n": len(rows), "headline": len(head),
                           "oracle_credit": sum(o["credit"] for o in oracle), "oracle_refused": sum(o["refused"] for o in oracle),
                           "floor_headline": sum(floor[i]["credit"] for i in head), "floor_all": sum(x["credit"] for x in floor.values()),
                           "slices": {k: len(v) for k, v in slices(rows).items()}}
        save()
        z = rec["zero_gpu"]
        print(f"[wiki] zero GPU · oracle {z['oracle_credit']}/{z['n']} verified, {z['oracle_refused']} refused · "
              f"floor headline {z['floor_headline']}/{z['headline']}", flush=True)
        return 0

    if a.train_seed is not None:
        spec = f"adapters/wiki-walks-s{a.train_seed}"
        from training.harness.release_gate import RECIPE
        if not Path(spec, "adapter_model.safetensors").exists():
            print(f"[pool] training {spec} on {a.base} from {DATA / 'train.jsonl'}", flush=True)
            rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base, "--train", str(DATA / "train.jsonl"),
                                  "--out-dir", spec, "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                                  "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"]), "--seed", str(a.train_seed)])
            if rc != 0:
                rec["stopped"] = f"training {spec} failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
                print(f"[pool] {rec['stopped']}", flush=True)
                return 1
        import hashlib
        rec.setdefault("members", {})[f"withlib-s{a.train_seed}"] = {
            "adapter": spec, "seed": a.train_seed, "recipe": RECIPE,
            "adapter_sha256": hashlib.sha256(Path(spec, "adapter_model.safetensors").read_bytes()).hexdigest(),
            "corpus_sha256": hashlib.sha256((DATA / "train.jsonl").read_bytes()).hexdigest()}
        have = sorted(str(p.parent) for p in Path("adapters").glob("wiki-walks-s*/adapter_model.safetensors"))
        subprocess.call(["tar", "czf", "adapters_out.tgz", *have])
        rec["packed"] = len(have); rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print(f"[pool] trained and packed {len(have)} — stopping before serving, as asked", flush=True)
        return 0

    arms = [x for x in a.arms.split(",") if x]
    members = {x: f"adapters/wiki-walks-s{x.removeprefix('withlib-s')}" for x in arms if x.startswith("withlib-s")}
    lacking = [x for x, d in members.items() if not Path(d, "adapter_model.safetensors").exists()]
    if lacking:
        print(f"[wiki] cannot score: adapters not on disk {lacking}", flush=True)
        return 2
    save()
    from transformers import AutoTokenizer
    from training.harness.accept_rank import completion, serve, stop, wait_ready
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)

    def gen_for_model(model: str):
        def gen_for(system: str, user: str, walking: bool):
            close, budget = (ChainSuite.close, a.max_tokens) if walking else ((), a.max_tokens_plain)
            head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                           tokenize=False, add_generation_prompt=True, enable_thinking=False)

            def gen(prefix: str) -> str:
                n = len(tok(head + prefix)["input_ids"])
                if n + budget > MAX_MODEL_LEN:
                    raise ContextExhausted(f"{n} prompt tokens + {budget} > {MAX_MODEL_LEN}")
                return completion(model, head + prefix, budget, close)
            return gen
        return gen_for

    def run(arm: str, model: str) -> None:
        slot = rec["arms"].setdefault(arm, {})
        todo = [r for r in rows if r["case_id"] not in slot or "error" in slot[r["case_id"]]]
        print(f"[wiki] {arm}: {len(todo)} to run, {len(rows) - len(todo)} resumed", flush=True)
        gen_for, t0, n = gen_for_model(model), time.time(), 0
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            for f in as_completed([ex.submit(run_case, lib, r, "base-walks" if arm.startswith("withlib") else arm, gen_for) for r in todo]):
                x = f.result(); slot[x["id"]] = x; n += 1
                if n % 10 == 0 or n == len(todo):
                    save()
                    done = [y for y in slot.values() if "error" not in y]
                    print(f"[wiki] {arm} {len(slot)}/{len(rows)} credit {sum(bool(y['credit']) for y in done)} "
                          f"value-right {sum(bool(y.get('value_right')) for y in done)} errors {len(slot) - len(done)} {time.time() - t0:.0f}s", flush=True)
        save()

    # ONE `--lora-modules` FLAG, EVERY ADAPTER AFTER IT. vLLM 0.30 reads a repeated flag as a
    # duplicate key and keeps the last: W9's first scoring loaded only `withlib-s1`, and G1 on
    # `withlib-s0` got a 404 [ran] 2026-09-24 (S2_vllm.log: "Found duplicate keys --lora-modules").
    lora = ["--lora-modules", *[f"{x}={d}" for x, d in members.items()]] if members else []
    extra = ["--enable-lora", "--max-lora-rank", "16", "--max-loras", str(max(1, len(members)))] + lora if members else []
    srv = serve(a.base, ["--max-model-len", str(MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90", *extra])
    try:
        if not wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            for x in members:
                rec.setdefault("G1", {})[x] = identity(a.base, x, tok)
                print(f"[pool] G1 {x}: {'applied' if rec['G1'][x]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if any(not rec["G1"][x]["applied"] for x in members):
                rec["stopped"] = "G1: an adapter is not applied"
            else:
                for arm in arms:               # nolib FIRST: it is the gate on the whole set
                    run(arm, members.get(arm, a.base))
    finally:
        stop(srv)
    scored = {x: v for x, v in rec["arms"].items()}
    rec["analysis"] = analyse(scored, rows)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for p in rec["analysis"]["pairs"].get("headline", []):
        print(f"[wiki] headline · {p['pair']}: {p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})", flush=True)
    print(f"[wiki] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("decided") else 1


if __name__ == "__main__":
    raise SystemExit(main())
