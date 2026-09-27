r"""W7 — edit one statement after training; the answer must follow the library (docs/MEMORY.md §W7). Pre-registered in
results/W7-edit-after-training-20260927/BRIEF.md.

The released member `distributor-wiki@v2` was trained on walks through 32 worlds (training/wiki/corpus.py). Its own
training questions, in its own training worlds, are where its weights could hold a value: that is where the library has
to win. Per fixture, the world is written to Markdown, **one line of one page is patched** — the supporting statement's
value replaced by a new one of the same shape, as a commit would change it — and the library is reloaded from disk.

    control     the member walks the unedited library         → right means the old value, cited
    edited      the member walks the patched library          → right means the NEW value, cited to the patched
                                                                statement, and the old value nowhere in the line
    closedbook  the member answers with no library at all     → how often its weights still hold the old value

$\mathrm{follows} = \#\lbrace\text{edited right}\rbrace$, $\mathrm{stale} = \#\lbrace\text{old value in the edited line}\rbrace$,
$\mathrm{memory} = \#\lbrace\text{closedbook writes the old value}\rbrace$, all over the same $n$ fixtures.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import tempfile
import time
from pathlib import Path

from training.wiki import grade as gr
from training.wiki import world as wd

CORPUS = Path("training/wiki/data/train_cmp.jsonl")    # distributor-wiki@v2's corpus (releases/distributor-wiki@v2.json)
MEMBER, ADAPTER = "wiki-v2", "adapters/wiki-cmp-walks-s1"
N = 40
EXCLUDED = ("compare-", "none-")                        # a comparison answers a name; a refusal has no value to edit
ARMS = ("control", "edited", "closedbook")


def fixtures(n: int = N) -> list[dict]:
    """`n` training rows, spread across families, whose answer is numbers or times only — deterministic."""
    rows = [json.loads(l) for l in CORPUS.read_text().splitlines() if l.strip()]
    ok = [r for r in rows if not r["family"].startswith(EXCLUDED) and r["check"]["kind"] == "value" and r["grade"] == "right"
          and r["support"] and all(gr._NUM.fullmatch(t) for t in r["check"]["tokens"])]
    fams: dict[str, list[dict]] = {}
    for r in sorted(ok, key=lambda r: hashlib.sha256(r["case_id"].encode()).hexdigest()):
        fams.setdefault(r["family"], []).append(r)
    out, i = [], 0
    while len(out) < n and any(fams.values()):          # round robin over families
        f = sorted(fams)[i % len(fams)]
        if fams[f]:
            out.append(fams[f].pop(0))
        i += 1
    return out


def new_value(tok: str, avoid: set[str], r: random.Random) -> str:
    """A value of the same shape that is not the old one and appears nowhere on the page (normalised as the grader does)."""
    for _ in range(200):
        if ":" in tok:
            h, m = (int(x) for x in tok.split(":"))
            cand = f"{(h + r.choice([-3, -2, 2, 3])) % 24:02d}:{m:02d}"
        else:
            v = int(tok)
            cand = str(max(1, v + r.choice([-1, 1]) * r.randint(max(2, v // 4), max(3, v // 2 + 3))))
            cand = cand.zfill(len(tok)) if tok.startswith("0") else cand
        if gr._norm(cand) not in avoid:
            return cand
    raise ValueError(f"no new value for {tok}")


def patch(row: dict, root: Path) -> dict:
    """Write the row's world under `root/<ROOT>`, replace the supporting statement's value on its line, reload the library.
    Returns the library, the new tokens and the patch as a unified line pair."""
    from memory.notes import Library
    w = wd.build(int(row["world"]))
    base = root / wd.ROOT
    w.write(base)
    nid, anchor = row["support"]
    page = base / (nid.split("/", 1)[1] + ".md")
    text = page.read_text()
    line = next(l for l in text.splitlines() if l.startswith(f"§{anchor} "))
    avoid = {gr._norm(n) for n in gr._NUM.findall(text)}
    r = random.Random(hashlib.sha256(row["case_id"].encode()).hexdigest())
    new_toks, new_line = [], line
    for t in row["check"]["tokens"]:
        nv = new_value(t, avoid, r)
        avoid.add(gr._norm(nv))
        new_line = re.sub(rf"(?<![\d:]){re.escape(t)}(?![\d:])", nv, new_line, count=1)
        new_toks.append(nv)
    if new_line == line:
        raise ValueError(f"{row['case_id']}: the value was not found on its statement line")
    page.write_text(text.replace(line, new_line, 1))
    return {"lib": Library.load(base), "tokens": new_toks, "patch": {"file": str(page.relative_to(root)), "-": line, "+": new_line}}


def edited_row(row: dict, tokens: list[str]) -> dict:
    """The row the grader reads in the edited arm: the new value right, the old one never."""
    answer = row["answer"]
    for o, n in zip(row["check"]["tokens"], tokens):      # the oracle's answer carries the new value too
        answer = re.sub(rf"(?<![\d:]){re.escape(o)}(?![\d:])", n, answer, count=1)
    return {**copy.deepcopy(row), "answer": answer,
            "check": {"kind": "value", "tokens": tokens, "never": list(row["check"]["tokens"])}}


def verdict(rec: dict) -> dict:
    """Written before the run (BRIEF): VOID if G1 fails or the control answers fewer than 32 of 40 — the member must
    first answer its own training questions; PASSED if the edited arm is right on at least 90 % of the fixtures the
    control is right on AND the old value appears in at most 2 edited lines; else FALSIFIED. `memory` is reported
    beside it: at or under 4 the weights held little to overrule, and the pass reads as reading, not as winning."""
    arms = rec.get("arms", {})
    c, e, cb = (arms.get(a, {}) for a in ARMS)
    if not (c and e):
        return {"reading": "NOTHING SCORED"}
    ids = [i for i in c if i in e and "error" not in c[i] and "error" not in e[i]]
    ctrl = [i for i in ids if c[i]["credit"]]
    follows = sum(e[i]["credit"] for i in ctrl)
    stale = sum(e[i].get("stale", False) for i in ids)
    memory = sum(x.get("memory", False) for x in cb.values())
    out = {"n": len(ids), "control": len(ctrl), "follows_on_control_right": follows, "edited_right": sum(e[i]["credit"] for i in ids),
           "stale": stale, "memory": memory, "closedbook_n": len(cb)}
    if not rec.get("G1", {}).get("applied"):
        out["reading"] = "VOID: G1 does not show the member applied"
    elif len(ctrl) < 32:
        out["reading"] = f"VOID: the control answers {len(ctrl)} of {len(ids)} (< 32) — no baseline to follow from"
    elif follows >= 0.9 * len(ctrl) and stale <= 2:
        out["reading"] = (f"PASSED: {follows} of {len(ctrl)} follow the edit, {stale} stale"
                          + (f" — but the weights held the old value on only {memory} (≤ 4): reading, not overruling" if memory <= 4 else ""))
    else:
        out["reading"] = f"FALSIFIED: {follows} of {len(ctrl)} follow the edit (< 90 %), {stale} stale"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="google/gemma-4-E4B-it")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--zero-gpu", action="store_true", help="build every patch and walk the oracle through it — no model")
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--out", default="w7.json")
    a = ap.parse_args()
    from memory import prompt
    from training.wiki import wiki_arm as wa
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    rows = fixtures()
    tmp = Path(tempfile.mkdtemp())
    patched = {}
    for r in rows:
        p = patch(r, tmp / r["case_id"])
        patched[r["case_id"]] = p
    rec["fixtures"] = [{"id": r["case_id"], "family": r["family"], "world": r["world"], "old": r["check"]["tokens"],
                        "new": patched[r["case_id"]]["tokens"], "patch": patched[r["case_id"]]["patch"]} for r in rows]
    save()
    if a.zero_gpu:                                           # the oracle walks every patched library to the NEW value
        ok = 0
        for r in rows:
            p = patched[r["case_id"]]
            er = edited_row(r, p["tokens"])
            conv = wa.conversation(p["lib"], er)
            final, conv, _ = wa.walk(p["lib"], er, wa.oracle_gen(er, conv), conv)
            ok += gr.grade(er, final, conv)["state"] == "right"
        rec["zero_gpu"] = {"n": len(rows), "oracle_follows": ok, "families": sorted({r["family"] for r in rows})}
        save()
        print(f"[w7] zero GPU · {len(rows)} fixtures over {len(rec['zero_gpu']['families'])} families · the oracle follows {ok}/{len(rows)}", flush=True)
        return 0

    from transformers import AutoTokenizer
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    srv = ar.serve(a.base, ["--max-model-len", str(wa.MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90", "--enable-lora",
                            "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{MEMBER}={ADAPTER}"])

    def gen_for(system: str, user: str, walking: bool):
        close = wa.ChainSuite.close if walking else ()
        head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
        return lambda prefix: ar.completion(MEMBER, head + prefix, a.max_tokens if walking else 160, close)

    try:
        if not ar.wait_ready(srv):
            rec["stopped"] = "the base never came up"; save(); return 1
        rec["G1"] = identity(a.base, MEMBER, tok)
        print(f"[w7] G1 {'applied' if rec['G1']['applied'] else 'NOT APPLIED'} ({rec['G1']['differs']}/{rec['G1']['probed']})", flush=True)
        save()
        if not rec["G1"]["applied"]:
            rec["stopped"] = "G1: the member is not applied"
        else:
            for arm in ARMS:
                slot = rec["arms"].setdefault(arm, {})
                for i, r in enumerate(rows, 1):
                    if r["case_id"] in slot and "error" not in slot[r["case_id"]]:
                        continue
                    p = patched[r["case_id"]]
                    if arm == "control":
                        res = wa.run_case(wd.build(int(r["world"])).library(), r, "withlib", gen_for)
                    elif arm == "edited":
                        er = edited_row(r, p["tokens"])
                        res = wa.run_case(p["lib"], er, "withlib", gen_for)
                        if "error" not in res:
                            res["stale"] = any(gr._has(gr.CITE.sub(" ", gr.final_line(res.get("final", ""))), t) for t in r["check"]["tokens"])
                    else:
                        res = wa.run_case(wd.build(int(r["world"])).library(), r, "nolib", gen_for)
                        if "error" not in res:
                            res["memory"] = gr.value_right(r, gr.final_line(res.get("final", "")))
                    slot[r["case_id"]] = res
                    if i % 10 == 0 or i == len(rows):
                        save()
                        print(f"[w7] {arm} {i}/{len(rows)} · credit {sum(x.get('credit', False) for x in slot.values())}"
                              + (f" · stale {sum(x.get('stale', False) for x in slot.values())}" if arm == "edited" else "")
                              + (f" · memory {sum(x.get('memory', False) for x in slot.values())}" if arm == "closedbook" else ""), flush=True)
    finally:
        ar.stop(srv)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[w7] {rec['verdict']['reading']} · {json.dumps({k: v for k, v in rec['verdict'].items() if k != 'reading'})}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
