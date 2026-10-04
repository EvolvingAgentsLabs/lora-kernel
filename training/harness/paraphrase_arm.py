r"""P2a — does a pool member answer a PARAPHRASE of its task? (docs/review/moe-distillation-and-spotlight.md, step 2)

WHY. ROUTE0's factored router keeps a request local only when its task paragraph is, verbatim, a task its member was
trained on; a paraphrase leaves for the frontier by design (B3: 0/120 kept local) **[ran]**
results/ROUTE0-factored-router-20261002. That was a bet that the members — each trained on one wording — fail
paraphrases. ROUTE2 (a router that keeps paraphrases local) is worth building only if the bet is wrong. This arm
measures the bet, before any router is built.

THE INSTRUMENT IS THE RELEASE'S, CHANGED IN ONE LINE. The released scores of `email-full@v3` (469/475) and
`desk-commitment@v3` (240/240 shallow, 239/240 deep) were measured by `training.harness.pool_base` (M1b, M1d **[ran]**):

    cases      `suites.load(name).cases(eval_n, eval_seed)` — email 475 (seed 717171), desk:commitment 240 and
               desk:commitment_deep 240 (seed 424242); the case's `user` is the listing, a blank line, the task line
    render     `suite.system` + `suite.user_text(case)` (the user turn, a blank line, the tool block the corpus taught)
               through the base's chat template, thinking off — the member's own prompt, i.e. corpus mode
    loop       `accept_rank.draft_arm` → `run_chain`: generate to a closing tag, answer it for real, continue
    grader     `case.verify(suite.parse(final span))` — email: `said == truth` on IMPORTANT / NOT IMPORTANT; desk:
               `desk.correct`, exactly one date and the right one

Here every case is scored twice by that path, on ONE vLLM serving both adapters: (a) **verbatim**, the released
condition, and (b) **paraphrase** — the same `Case`, with only its final line (the task) replaced, round-robin from a
fixed list (`PARAPHRASES`, ≥ 15 per suite, none in either corpus). `ctx`, `truth`, `verify` are the same objects.

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2). Paired by case id: with $b$ cases only the paraphrase gets right and $c$
only verbatim, $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$ (`release_gate.pair`). Per suite $s$ the drop is
$\Delta_s = \mathrm{acc}_{verbatim} - \mathrm{acc}_{paraphrase}$ in accuracy points.

    MEMBERS ANSWER PARAPHRASES   every suite: Δ ≤ 0.05 and no REGRESSION (p < 0.05 with c > b) → ROUTE2 worth building
    PARAPHRASES COST             any suite of any member: REGRESSION → paraphrases correctly leave; ROUTE2 not built
    UNRESOLVED                   otherwise (Δ > 0.05 without significance) → ROUTE2 not built on this evidence
    VOID                         G1 not applied, a transport error left in any arm, or the verbatim arm a REGRESSION
                                 against the recorded release records (the serving path is not the release's)

    python3 -m training.harness.paraphrase_arm --base google/gemma-4-E4B-it --out p2a.json
    python3 -m training.harness.paraphrase_arm --zero-gpu        # cases, paraphrases, corpus leak check; no server
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

from training.harness import suites

BASE = "google/gemma-4-E4B-it"
OUT = Path("p2a.json")

# THE TWO RELEASED MEMBERS (releases/email-full@v3.json, releases/desk-commitment@v3.json), the directories their
# tarballs unpack to, and the suites their releases were scored on. The served NAME is the release's, as in M1b/M1d.
MEMBERS = {
    "email-full": {"adapter": "adapters/email-full-g4", "sha256": "725ad8ddd2124b753742caf7b0c5d6d5b165f1f41ef6e38d36f4fca9754676b1",
                   "suites": ("email",)},
    "desk-commitment": {"adapter": "adapters/desk-commitment-g4b",
                        "sha256": "dd8e2ba026fe52d21cc259f759876eac548571727745eba5289561a148f1c122",
                        "suites": ("desk:commitment_deep", "desk:commitment")},
}
# the release's own records, per suite: the verbatim arm is paired against them (the substrate check)
RECORDED = {
    "email": ("results/M1b-pool-gemma4-20260925/pool_base.json", "email-full"),
    "desk:commitment": ("results/M1d-desk-both-bands-20260926/shallow.json", "desk-commitment"),
    "desk:commitment_deep": ("results/M1d-desk-both-bands-20260926/deep.json", "desk-commitment"),
}
CORPORA = {"email-full": "training/harness/data_ef/train.jsonl",
           "desk-commitment": "training/harness/data_desk_both/train.jsonl"}

# THE TASK LINE, verbatim — the last line of every case's `user` and the only wording each corpus taught.
TASK = {
    "email": "Is this important?",
    "desk:commitment": "What date did you commit to in this thread?",
    "desk:commitment_deep": "What date did you commit to in this thread? If you committed more than once, "
                            "the latest one counts.",
}

# THE PARAPHRASES. email and desk:commitment are ROUTE0's B3 wordings (results/ROUTE0-factored-router-20261002/
# make_sets.py, written blind to that router), with one email wording dropped: "Can I safely ignore this email?"
# inverts the polarity, so a correct "Yes" carries no IMPORTANT / NOT IMPORTANT and the release grader would score
# phrasing, not the member. desk:commitment_deep's are new: each keeps the band's rule (the most recent promise counts)
# — without it the paraphrase would ask another question, and a member answering it rightly would be graded wrong.
PARAPHRASES = {
    "email": [
        "Should I care about this one?",
        "Does this need my attention?",
        "Is this worth my time?",
        "Do I need to deal with this?",
        "Is this one a priority?",
        "Is this message one I should act on?",
        "Would you flag this as important?",
        "How important is this email?",
        "Is this something I have to look at?",
        "Does this one matter?",
        "Important or not?",
        "Should this go to the top of my inbox?",
        "Is this email significant for me?",
        "Must I respond to this, or is it noise?",
        "Is this a message I shouldn't miss?",
        "Do you think this one is important?",
        "Is this high priority?",
        "Should I bother opening this?",
        "Does this deserve attention today?",
    ],
    "desk:commitment": [
        "When did I promise to deliver?",
        "What deadline did I agree to here?",
        "Which date did I commit to?",
        "What date did I promise in this conversation?",
        "By when did I say I'd have it done?",
        "What delivery date did I give them?",
        "Which day did I promise them?",
        "What date did I agree to in this exchange?",
        "When did I say it would be ready?",
        "What due date did I commit to on this thread?",
        "Remind me what date I promised.",
        "What was the date I committed to?",
        "On what date did I say I'd deliver?",
        "Which deadline did I sign up for in this thread?",
        "What date did I give as my commitment here?",
        "When did I tell them to expect it?",
        "What's the date I promised in this email chain?",
        "Tell me the date I committed to.",
    ],
    "desk:commitment_deep": [
        "When did I promise to deliver? If I promised more than once, give the most recent date.",
        "What deadline did I agree to here? If there were several, the last one I agreed to is the one that counts.",
        "Which date did I commit to? Should I have committed more than once, go with the latest.",
        "What date did I promise in this conversation? If I promised several times, I want the most recent promise.",
        "By when did I say I'd have it done? If I changed it, tell me the final date I gave.",
        "What delivery date did I give them? If I gave more than one, the newest counts.",
        "Which day did I promise them? Only my latest promise matters.",
        "What date did I agree to in this exchange? If I agreed to more than one, use the last.",
        "When did I say it would be ready? Where I said it more than once, take the most recent.",
        "What due date did I commit to on this thread? If it moved, give the last date I committed to.",
        "Remind me what date I promised. If I promised more than once, the latest promise wins.",
        "What was the date I committed to? In case of several commitments, pick the most recent one.",
        "On what date did I say I'd deliver? If I said it more than once, my last word on it counts.",
        "Which deadline did I sign up for in this thread? If there were several, the latest one I signed up for.",
        "What date did I give as my commitment here? If I revised it, give the revised one.",
        "Tell me the date I committed to. If I committed more than once, only the most recent counts.",
    ],
}
MIN_PARAPHRASES = 15
MAX_DROP = 0.05


def paraphrased(case: suites.Case, suite_name: str, k: int) -> suites.Case:
    """The same case with ONLY its task line replaced — `PARAPHRASES[suite][k % n]`, round-robin by position.

    The task is the case's last line and must read exactly `TASK[suite]`; anything else is refused rather than
    guessed, because a replacement that touched the listing would measure another prompt."""
    task, pool = TASK[suite_name], PARAPHRASES[suite_name]
    head, sep, last = case.user.rpartition("\n")
    if not sep or last != task:
        raise ValueError(f"{case.id}: the last line is {last!r}, not the task {task!r}")
    p = pool[k % len(pool)]
    return replace(case, user=head + sep + p, meta={**case.meta, "paraphrase": p, "paraphrase_k": k % len(pool)})


def corpus_leaks(corpora: dict[str, str] = CORPORA) -> dict[str, list[str]]:
    """Every paraphrase found (case-insensitive) in its member's corpus — must be empty, or the 'paraphrase' arm
    measures a wording the member was trained on."""
    out = {}
    for m, spec in MEMBERS.items():
        blob = Path(corpora[m]).read_text().lower()
        hits = [p for s in spec["suites"] for p in PARAPHRASES[s] if p.lower() in blob or json.dumps(p.lower())[1:-1] in blob]
        if hits:
            out[m] = hits
    return out


def load_cases(suite_name: str) -> tuple[suites.Suite, list[suites.Case], list[suites.Case]]:
    s = suites.load(suite_name)
    cases = s.cases(s.eval_n, s.eval_seed)
    return s, cases, [paraphrased(c, suite_name, k) for k, c in enumerate(cases)]


def prompt_sha(tok, suite: suites.Suite, case: suites.Case) -> str:
    """The sha `draft_arm` records for a case — the same render, so verbatim can be checked against the release."""
    text = tok.apply_chat_template([{"role": "system", "content": suite.system},
                                    {"role": "user", "content": suite.user_text(case)}],
                                   tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def arm_key(member: str, suite_name: str, cond: str) -> str:
    return f"{member}|{suite_name}|{cond}"


def _recorded(suite_name: str) -> list[dict] | None:
    path, arm = RECORDED[suite_name]
    if not Path(path).exists():
        return None
    recs = json.loads(Path(path).read_text())["arms"][arm]["records"]
    return recs if isinstance(recs, list) else list(recs.values())


def analyse(rec: dict) -> dict:
    from training.harness.release_gate import pair
    out = {}
    for m, spec in MEMBERS.items():
        for s in spec["suites"]:
            v = list(rec.get("arms", {}).get(arm_key(m, s, "verbatim"), {}).get("records", {}).values())
            p = list(rec.get("arms", {}).get(arm_key(m, s, "paraphrase"), {}).get("records", {}).values())
            if not v or not p:
                continue
            ok_v = [r for r in v if "error" not in r]
            ok_p = [r for r in p if "error" not in r]
            acc_v = sum(r["correct"] for r in ok_v) / len(v)
            acc_p = sum(r["correct"] for r in ok_p) / len(p)
            row = {"member": m, "suite": s, "n": len(v), "verbatim": sum(r["correct"] for r in ok_v),
                   "paraphrase": sum(r["correct"] for r in ok_p), "drop": round(acc_v - acc_p, 4),
                   "errors": (len(v) - len(ok_v)) + (len(p) - len(ok_p)),
                   # A LOSS WITH NO VERDICT WORD IS FORMAT, A LOSS WITH ONE IS CONTENT — read beside, never gated
                   "undecided": {"verbatim": sum(r.get("verdict") is None for r in ok_v),
                                 "paraphrase": sum(r.get("verdict") is None for r in ok_p)},
                   "pair": pair(p, v, "paraphrase vs verbatim")}
            per_k: dict = {}
            for r in ok_p:
                k = per_k.setdefault(r.get("paraphrase", "?"), [0, 0])
                k[0] += bool(r["correct"]); k[1] += 1
            row["by_paraphrase"] = {k: f"{a}/{b}" for k, (a, b) in sorted(per_k.items())}
            if s in {"desk:commitment_deep"}:
                by: dict = {}
                for cond, rs in (("verbatim", ok_v), ("paraphrase", ok_p)):
                    for r in rs:
                        by.setdefault(str(r.get("depth")), {}).setdefault(cond, 0)
                        by[str(r.get("depth"))][cond] += bool(r["correct"])
                row["by_depth"] = by
            old = _recorded(s)
            if old is not None:
                row["vs_release"] = pair(v, old, "verbatim vs recorded release")
                shas = {r["id"]: r.get("prompt_sha") for r in old}
                row["render_matches_release"] = sum(r.get("prompt_sha") == shas.get(r["id"]) for r in ok_v)
            out[f"{m}|{s}"] = row
    return out


def verdict(rec: dict) -> dict:
    rows = rec.get("analysis", {})
    want = [f"{m}|{s}" for m, spec in MEMBERS.items() for s in spec["suites"]]
    g1 = all(rec.get("G1", {}).get(m, {}).get("applied") for m in MEMBERS)
    missing = [k for k in want if k not in rows]
    errors = sum(rows[k]["errors"] for k in rows)
    off_release = [k for k in rows if rows[k].get("vs_release", {}).get("state") == "REGRESSION"]
    out = {"G1": g1, "missing": missing, "errors": errors, "verbatim_off_release": off_release}
    if not g1 or missing or errors or off_release:
        why = ("G1: a member is not applied" if not g1 else f"suites not scored: {missing}" if missing else
               f"{errors} transport errors left in the arms" if errors else
               f"the verbatim arm regresses against the release on {off_release}: not the release's serving path")
        return {**out, "decided": False, "verdict": "VOID", "reading": f"VOID — {why}"}
    cost = [k for k in want if rows[k]["pair"]["state"] == "REGRESSION"]
    wide = [k for k in want if rows[k]["drop"] > MAX_DROP]
    holds = {m: all(k not in cost and k not in wide for k in want if k.startswith(m + "|")) for m in MEMBERS}
    if cost:
        v, why = "PARAPHRASES COST", f"paired loss on {cost} — paraphrases correctly leave; ROUTE2 is not built"
    elif wide:
        v, why = "UNRESOLVED", f"drop > {MAX_DROP:.0%} without a significant pair on {wide} — ROUTE2 not built on this"
    else:
        v, why = "MEMBERS ANSWER PARAPHRASES", "every suite within 5 points and no paired loss — ROUTE2 is worth building"
    return {**out, "members": holds, "decided": True, "verdict": v, "reading": f"{v}: {why}"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored; MEMBERS names them)")
    ap.add_argument("--zero-gpu", action="store_true", help="build the cases and paraphrases, check the corpora; no server")
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {}); rec.setdefault("G1", {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    leaks = corpus_leaks()
    rec["corpus_leaks"] = leaks
    loaded = {s: load_cases(s) for spec in MEMBERS.values() for s in spec["suites"]}
    rec["cases"] = {s: len(c) for s, (_, c, _) in loaded.items()}
    save()
    print(f"[p2a] cases {rec['cases']} · paraphrases {{{', '.join(f'{s}: {len(PARAPHRASES[s])}' for s in TASK)}}} · "
          f"corpus leaks {leaks or 'none'}", flush=True)
    if leaks:
        rec["stopped"] = f"a paraphrase is in its member's corpus: {leaks}"; save()
        print(f"[p2a] STOPPED — {rec['stopped']}", flush=True)
        return 2
    if a.zero_gpu:
        return 0
    lacking = [spec["adapter"] for spec in MEMBERS.values() if not Path(spec["adapter"], "adapter_model.safetensors").exists()]
    if lacking:
        rec["stopped"] = f"adapters not on disk: {lacking}"; save()
        print(f"[p2a] STOPPED — {rec['stopped']}", flush=True)
        return 2
    from training.harness.release_gate import sha256
    rec["adapters"] = {m: {"path": spec["adapter"], "sha256": sha256(Path(spec["adapter"], "adapter_model.safetensors"))}
                       for m, spec in MEMBERS.items()}
    wrong = [m for m, spec in MEMBERS.items() if rec["adapters"][m]["sha256"] != spec["sha256"]]
    if wrong:
        rec["stopped"] = f"not the released adapter (sha256 differs from the manifest): {wrong}"; save()
        print(f"[p2a] STOPPED — {rec['stopped']}", flush=True)
        return 2
    save()

    from transformers import AutoTokenizer
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    # THE RENDER CHECK, ZERO GPU ON THE VM: the verbatim prompt of every case against the sha the release recorded
    rec["render_check"] = {}
    for s, (suite, cases, _) in loaded.items():
        old = _recorded(s)
        if old is not None:
            shas = {r["id"]: r.get("prompt_sha") for r in old}
            rec["render_check"][s] = f"{sum(prompt_sha(tok, suite, c) == shas.get(c.id) for c in cases)}/{len(cases)}"
    print(f"[p2a] verbatim renders the release's prompt: {rec['render_check']}", flush=True)
    save()

    # ONE `--lora-modules` FLAG, EVERY ADAPTER AFTER IT (vLLM 0.30 keeps the last of a repeated flag, W9 [ran])
    srv = ar.serve(a.base, ["--max-model-len", str(a.max_model_len), "--gpu-memory-utilization", "0.90",
                            "--enable-lora", "--max-lora-rank", "16", "--max-loras", str(len(MEMBERS)),
                            "--lora-modules", *[f"{m}={spec['adapter']}" for m, spec in MEMBERS.items()]])
    try:
        if not ar.wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            for m in MEMBERS:
                rec["G1"][m] = identity(a.base, m, tok)
                print(f"[p2a] G1 {m}: {rec['G1'][m]['differs']}/{rec['G1'][m]['probed']} differ → "
                      f"{'applied' if rec['G1'][m]['applied'] else 'NOT APPLIED'}", flush=True)
                save()
            if not all(rec["G1"][m].get("applied") for m in MEMBERS):
                rec["stopped"] = "G1: a member is not applied — nothing after this would measure a member"
            else:
                for m, spec in MEMBERS.items():
                    for s in spec["suites"]:
                        suite, verbatim, para = loaded[s]
                        for cond, cases in (("verbatim", verbatim), ("paraphrase", para)):
                            slot = rec["arms"].setdefault(arm_key(m, s, cond), {"model": m, "records": {}})
                            # an errored case is drafted again; a finished one is never redrafted
                            slot["records"] = {k: r for k, r in slot["records"].items() if "error" not in r}
                            print(f"[p2a] arm {m} · {s} · {cond}", flush=True)
                            recs = ar.draft_arm(m, tok, suite, cases, a.max_tokens, a.concurrency, slot["records"], save)
                            slot.update(ar.summarise(recs))
                            print(f"[p2a] {m} · {s} · {cond}: {slot['correct']}/{slot['n']} errors {slot['errors']} "
                                  f"undecided {slot['undecided']}", flush=True)
                            save()
    finally:
        ar.stop(srv)
    rec["analysis"] = analyse(rec)
    for k, row in rec["analysis"].items():
        pr = row["pair"]
        print(f"[p2a] {k}: verbatim {row['verbatim']}/{row['n']} paraphrase {row['paraphrase']}/{row['n']} "
              f"({pr['only_a']}:{pr['only_b']}, p={pr['p_value']}, {pr['state']})", flush=True)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[p2a] {rec.get('stopped') or rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"].get("decided") else 1


if __name__ == "__main__":
    raise SystemExit(main())
