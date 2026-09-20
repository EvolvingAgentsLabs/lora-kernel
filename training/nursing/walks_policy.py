r"""W5d — the answer policy, scored: the adapter walks; WHO WRITES the final line depends on the kind of task.

The policy and the rule that decides a task's kind are `training/nursing/answer_policy.py`, frozen
before the sets this runner's CLAIM is read on were written. One unknown: who writes which line.

TWO STAGES, AND ONLY ONE OF THEM IS THE CLAIM.

    claim         NEW held-out and control sets (`data_walks_w5d/`), written after the freeze, never
                  W5's 80 nor W5c's 88/80. Three arms, in the order bought:
                      base-reads   the untrained base, the oracle's notes open — W5's bar, and headroom
                      withlib      the v2 adapter (W5c's, carried in, not retrained) walks the new set
                      policy       `withlib`'s record where the ADAPTER writes (carry · not-in-library ·
                                   rate); where the BASE writes (a value), `withlib`'s walk — replayed
                                   from its own record, never regenerated — and the bare base's final
                                   line over the pages that walk opened, served as `base-reads` is
    attribution   the same policy over W5c's RECORDED `withlib` walks on the v2 sets. Those sets are new
                  to the policy's design (its 47/56 came from W5's first set) and NOT new to us: a first
                  out-of-sample look, reported as that, never as the claim.

Graded by the untouched `grade_walks.grade`; the walk evidence is always `withlib`'s, so `unread`
still applies — a right value whose note the walk never opened earns nothing.

THE VERDICT, on the NEW headline (held-out, depth ≤ 9, final line no other procedure states), by
CREDIT, paired by case id, exact two-sided sign test on discordant pairs (FOUNDATIONS §7.1),
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at $p < 0.05$:

    policy vs withlib       must be an IMPROVEMENT — a tie or worse FALSIFIES the policy
    policy vs base-reads    W5's own bar. The spec says *beats*; a tie is reported as a tie
    control: policy vs withlib   must NOT be a REGRESSION — the failure composition had (W5b, 0 : 19)

`right` alone — the contract: right AND in the taught form — is paired and printed beside credit.
W5's verdict stands whatever this says: a policy that passes is a serving design with one held-out
set under it, not a second reading of W5.
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from memory.notes import Library
from memory.runtime import ChainSuite
from training.nursing import answer_policy as ap
from training.nursing import grade_walks as gr
from training.nursing import walks_arm as wa
from training.nursing import walks_composed as wc
from training.nursing.library import ROOT

ADAPTER = "adapters/nursing-walks-v2-q35"           # W5c's `withlib`, adapter sha256 0f7d872d… — carried in
MEMBER = "withlib"
W5C = Path("results/M7-W5c-conditional-corpus-20260919/walks_arm.json")
DATA = {"claim": Path("training/nursing/data_walks_w5d"), "attribution": Path("training/nursing/data_walks_v2")}
ARMS = ("base-reads", "withlib", "policy")


def load_sets(d: Path) -> dict:
    return {k: [json.loads(l) for l in (d / f"eval_{k}.jsonl").read_text().splitlines()] for k in ("heldout", "control")}


# ------------------------------------------------------------------ one policy record
def policy_case(lib: Library, row: dict, walked: dict, gen_base) -> dict:
    """`walked` is `withlib`'s record of this case. The adapter's own record where the adapter writes;
    its replayed walk plus the base's line where the base does."""
    k = ap.kind(row["statement"])
    if "error" in walked:
        return {"id": row["case_id"], "family": row["family"], "variant": row["variant"], "kind": k,
                "error": "withlib's walk was lost to transport: " + str(walked["error"])[:100]}
    if ap.WRITER[k] == "adapter":
        return {**{f: walked.get(f) for f in ("id", "family", "variant", "state", "credit", "correct", "verbatim", "final")},
                "kind": k, "written_by": "adapter", "opened_ids": walked.get("opened_ids"), "violations": walked.get("violations")}
    return {**wc.run_case(lib, row, walked, gen_base), "kind": k, "written_by": "base"}


# ------------------------------------------------------------------ what can be known with no GPU
def ceiling(lib: Library, sets: dict, walks: dict, reads: dict) -> dict:
    """With `withlib`'s walks and `base-reads`' records in hand (attribution only): what the policy
    reaches if the base reads the walk's pages as well as it read the oracle's."""
    rows = {r["case_id"]: r for rs in sets.values() for r in rs}
    out = {}
    for name, ids in wa.slices(sets).items():
        got = same = unre = to_base = 0
        for i in ids:
            row, w = rows[i], walks[i]
            if ap.writer(row["statement"]) == "adapter":
                got += bool(w["credit"]); continue
            to_base += 1
            pages, walk, _ = wc.replay(lib, row, w)
            if pages is None:
                unre += 1; continue
            got += bool(gr.walk_ok(lib, row, walk) and reads[i]["credit"])
            same += wc.served(lib, row, pages) == wa.served(lib, row, "base-reads")[:2]
        out[name] = {"n": len(ids), "written_by_base": to_base, "unreplayable": unre, "ceiling": got,
                     "withlib": sum(bool(walks[i]["credit"]) for i in ids), "base_reads": sum(bool(reads[i]["credit"]) for i in ids),
                     "prompt_identical_to_base_reads": same}
    return out


def kinds(sets: dict) -> dict:
    out = {}
    for name, rows in sets.items():
        c = {}
        for r in rows:
            k = ap.kind(r["statement"])
            if k != ap.KIND_OF_FAMILY[r["family"]]:
                raise AssertionError(f"{r['case_id']}: kind() reads {k}, the generator wrote a {r['family']}")
            c[k] = c.get(k, 0) + 1
        out[name] = c
    return out


# ------------------------------------------------------------------ slices, pairs, verdict
def _pair_on(a: dict, b: dict, ids: list[str], label: str, key) -> dict:
    from training.harness.release_gate import pair
    keep = [i for i in ids if i in a and i in b and "error" not in a[i] and "error" not in b[i]]
    return pair([{"id": i, "correct": bool(key(a[i]))} for i in keep], [{"id": i, "correct": bool(key(b[i]))} for i in keep], label)


def analyse(stage: dict, sets: dict) -> dict:
    arms = {a: {**v["heldout"]["records"], **v["control"]["records"]} for a, v in stage.get("arms", {}).items()
            if all(s in v for s in ("heldout", "control"))}
    # A WALK THAT CANNOT BE REPLAYED IS NOT A WRONG ANSWER: it leaves every slice, for every arm. Records
    # now keep their whole walk, so this should be empty; it is counted either way.
    gone = sorted(i for i, r in arms.get("policy", {}).items() if r.get("state") == "unreplayable")
    sl = {k: [i for i in ids if i not in gone] for k, ids in wa.slices(sets).items()}
    out = {"excluded_unreplayable": gone, "slices": {k: len(v) for k, v in sl.items()},
           "summary": {a: {k: wa.summarise(r, ids) for k, ids in sl.items()} for a, r in arms.items()},
           "pairs": {}, "pairs_right_only": {}}
    if "policy" in arms:
        for k, ids in sl.items():
            others = [o for o in ("withlib", "base-reads") if o in arms and ids]
            out["pairs"][k] = [_pair_on(arms["policy"], arms[o], ids, f"policy vs {o}", lambda r: r["credit"]) for o in others]
            out["pairs_right_only"][k] = [_pair_on(arms["policy"], arms[o], ids, f"policy vs {o}", lambda r: r.get("state") == "right")
                                          for o in others]
        by = {}
        for r in arms["policy"].values():
            if "error" not in r:
                w = by.setdefault(r.get("written_by", "?"), {"n": 0, "credit": 0})
                w["n"] += 1; w["credit"] += bool(r["credit"])
        out["policy_by_writer"] = by
    return out


def verdict(rec: dict) -> dict:
    a = rec.get("claim", {}).get("analysis", {})
    head = {p["pair"]: p for p in a.get("pairs", {}).get("headline", [])}
    ctrl = {p["pair"]: p for p in a.get("pairs", {}).get("control", [])}
    s = a.get("summary", {})
    if "policy vs withlib" not in head:
        return {"decided": False, "reading": "NOTHING SCORED ON THE CLAIM"}
    show = lambda p: f"{p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})"
    lost = sum(s[x]["headline"]["errors"] + s[x]["headline"]["missing"] for x in s)
    base = s["base-reads"]["headline"]
    out = {"G1": bool(rec.get("G1", {}).get(MEMBER, {}).get("applied")),
           "headline": {x: f"{s[x]['headline']['credit']}/{s[x]['headline']['scored']}" for x in s},
           "headline_right_only": {x: f"{s[x]['headline']['right']}/{s[x]['headline']['scored']}" for x in s},
           "control": {x: f"{s[x]['control']['credit']}/{s[x]['control']['scored']}" for x in s},
           "pairs": {k: show(p) for k, p in head.items()},
           "pairs_right_only": {p["pair"]: show(p) for p in a["pairs_right_only"].get("headline", [])},
           "control_pairs": {k: show(p) for k, p in ctrl.items()},
           "excluded_unreplayable": len(a["excluded_unreplayable"]),
           # the bar's headroom, W5's rule: credit ≥ n − 5 leaves at most five discordant pairs
           "no_headroom_for_the_bar": base["credit"] >= base["scored"] - wa.UNBEATABLE_MARGIN}
    if not out["G1"]:
        return {**out, "decided": False, "passed": False, "reading": "VOID: the adapter is not applied — no walk here is the member's"}
    if lost:
        return {**out, "decided": False, "passed": False, "reading": f"VOID: {lost} headline records missing or lost to transport"}
    buys = head["policy vs withlib"]["state"] == "improvement"
    keeps = ctrl.get("policy vs withlib", {}).get("state") != "REGRESSION"
    bar = head["policy vs base-reads"]["state"]
    out.update(decided=True, policy_buys_something=buys, control_holds=keeps, against_the_bar=bar,
               passed=bool(buys and keeps and bar == "improvement"))
    if not buys:
        out["reading"] = ("FALSIFIED: on a set written after the freeze the policy does not beat the adapter alone — "
                          f"policy vs withlib is {show(head['policy vs withlib'])}")
    elif not keeps:
        out["reading"] = ("NOT A SERVING DESIGN: the policy beats the adapter on the held-out procedure and gives the "
                          f"trained band back — control {show(ctrl['policy vs withlib'])}")
    else:
        out["reading"] = (f"THE POLICY BUYS SOMETHING AND KEEPS THE TRAINED BAND: vs withlib {show(head['policy vs withlib'])}, "
                          f"control {show(ctrl['policy vs withlib'])} · against W5's bar (base-reads, the oracle's navigation "
                          f"for free): {show(head['policy vs base-reads'])}"
                          + (" — BEATS it" if bar == "improvement" else
                             " — a TIE: learned navigation plus the base's reading reaches what oracle navigation plus the "
                             "base's reading reaches; the spec says *beats*, so W5's bar is not cleared" if bar == "tie" else
                             " — LOSES to it"))
    return out


# ------------------------------------------------------------------ the session
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=wa.BASE)
    p.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    p.add_argument("--zero-gpu", action="store_true", help="kinds, the floor on the new sets, the attribution ceiling — no model")
    p.add_argument("--max-tokens", type=int, default=160, help="per step, for the arm that walks")
    p.add_argument("--max-tokens-plain", type=int, default=320, help="the whole reply, for an arm with no verbs")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--out", default="walks_policy.json")
    a = p.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"), grader="training.nursing.grade_walks",
               policy={"writer": ap.WRITER, "decided_by": "kind(statement) in training.nursing.answer_policy"},
               adapter=ADAPTER, walks_recorded_in=str(W5C))
    lib = Library.load(ROOT)
    sets = {stage: load_sets(d) for stage, d in DATA.items()}
    w5c = json.loads(W5C.read_text())
    for stage in DATA:
        rec.setdefault(stage, {}).setdefault("arms", {})
    # ATTRIBUTION'S TWO RECORDED ARMS ARE COPIED IN, NEVER RE-RUN; the W5c file is read and never written.
    for arm in ("base-reads", "withlib"):
        rec["attribution"]["arms"][arm] = w5c["arms"][arm]
    rec["kinds"] = {stage: kinds(s) for stage, s in sets.items()}

    def save():
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    if a.zero_gpu:
        f = wa.floor(lib, sets["claim"])
        both = {**f["heldout"]["records"], **f["control"]["records"]}
        rec["floor_claim"] = {k: wa.summarise(both, ids) for k, ids in wa.slices(sets["claim"]).items()}
        walks = {**w5c["arms"]["withlib"]["heldout"]["records"], **w5c["arms"]["withlib"]["control"]["records"]}
        reads = {**w5c["arms"]["base-reads"]["heldout"]["records"], **w5c["arms"]["base-reads"]["control"]["records"]}
        rec["ceiling_attribution"] = ceiling(lib, sets["attribution"], walks, reads)
        # ONLY WHAT NO MODEL WAS NEEDED FOR, and never into the run's own results file: the chain carries
        # that file into the session, and 1 MB of copied records is not a zero-GPU number.
        small = {k: rec[k] for k in ("policy", "adapter", "kinds", "floor_claim", "ceiling_attribution")}
        small["slices_claim"] = {k: len(v) for k, v in wa.slices(sets["claim"]).items()}
        out.write_text(json.dumps(small, indent=1, ensure_ascii=False))
        c, fl = rec["ceiling_attribution"], rec["floor_claim"]
        print(f"[arm] policy, zero GPU · attribution ceiling: headline {c['headline']['ceiling']}/{c['headline']['n']} "
              f"(withlib {c['headline']['withlib']}, base-reads {c['headline']['base_reads']}) · control "
              f"{c['control']['ceiling']}/{c['control']['n']} (withlib {c['control']['withlib']}) · floor on the new sets: "
              f"headline {fl['headline']['credit']}/{fl['headline']['n']}, control {fl['control']['credit']}/{fl['control']['n']}",
              flush=True)
        return 0

    if not Path(ADAPTER, "adapter_model.safetensors").exists():
        print(f"[arm] cannot score: {ADAPTER} is not on disk — carry W5c's adapters.tgz into this run directory", flush=True)
        return 2
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

    def run(stage: str, arm: str, name: str, rows: list, one) -> None:
        slot = rec[stage]["arms"].setdefault(arm, {}).setdefault(name, {"records": {}})
        todo = [r for r in rows if r["case_id"] not in slot["records"] or "error" in slot["records"][r["case_id"]]]
        print(f"[arm] {stage} · {arm} · {name}: {len(todo)} to run, {len(rows) - len(todo)} resumed", flush=True)
        t0, n = time.time(), 0
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            for f in as_completed([ex.submit(one, r) for r in todo]):
                r = f.result(); slot["records"][r["id"]] = r; n += 1
                if n % 20 == 0 or n == len(todo):
                    save()
                    done = [x for x in slot["records"].values() if "error" not in x]
                    print(f"[arm] {stage} · {arm} · {name} {len(slot['records'])}/{len(rows)} credit "
                          f"{sum(bool(x['credit']) for x in done)} errors {len(slot['records']) - len(done)} {time.time() - t0:.0f}s",
                          flush=True)
        save()

    srv = serve(a.base, ["--max-model-len", str(wa.MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90", "--enable-lora",
                         "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{MEMBER}={ADAPTER}"])
    try:
        if not wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            rec.setdefault("G1", {})[MEMBER] = identity(a.base, MEMBER, tok)
            print(f"[pool] G1 {MEMBER}: {'applied' if rec['G1'][MEMBER]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not rec["G1"][MEMBER]["applied"]:
                rec["stopped"] = "G1: the adapter is not applied"
            else:
                base, member = gen_for_model(a.base), gen_for_model(MEMBER)
                # THE CLAIM FIRST — a session lives sixty minutes and this is the stage that counts.
                for arm, gen in (("base-reads", base), ("withlib", member)):          # the bar, then the walks
                    for name, rows in sets["claim"].items():
                        run("claim", arm, name, rows, lambda r, arm=arm, gen=gen: wa.run_case(lib, r, arm, gen))
                for stage in ("claim", "attribution"):
                    for name, rows in sets[stage].items():
                        walked = rec[stage]["arms"]["withlib"][name]["records"]
                        run(stage, "policy", name, rows, lambda r, w=walked: policy_case(lib, r, w[r["case_id"]], base))
    finally:
        stop(srv)
    for stage in DATA:
        rec[stage]["analysis"] = analyse(rec[stage], sets[stage])
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for stage in DATA:
        for pr in rec[stage]["analysis"]["pairs"].get("headline", []):
            print(f"[arm] {stage} · headline · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})", flush=True)
    print(f"[arm] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("decided") else 1


if __name__ == "__main__":
    raise SystemExit(main())
