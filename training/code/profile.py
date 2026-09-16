"""Let the base and the target say where the completion difficulty is.

THE SAME METHOD AS P51, ON A PREDICATE THAT CONSTRAINS. P51 profiled a desk suite and
came back `usable: false` — three cells of sixteen, all one region. What it also
showed is that the method works: the band fired, and the two regions asking about a
whole inbox turned out unanswerable **for the 32B as well**, which is a suite fault
the profile found rather than a model fault it invented.

WHAT IS DIFFERENT HERE. No tool calls; the answer is a completion and the verifier is
**execution**. So the preflight checks what can go wrong in *this* path — a transport
error, or an empty completion — rather than a missing tool call.

THE BAND IS THE ONE P51 PRE-REGISTERED, UNCHANGED. `0.15 <= base <= 0.70`, and a cell
the target scores under `0.40` is broken rather than hard.

AND THE FLAW P51 FOUND IS REPORTED, NOT FIXED. `commitment@4` was base **0.000**
against target **1.000** and the band dropped it for being on the floor — by a clause
written for *"every arm fails and it reads as the approach not working"*. The target
proved that one doable, so it was the most informative cell there was. Changing the
rule with the result in hand is indistinguishable from moving the band to fit it, so
instead every dropped cell is labelled with **why**, and the ones the target clears
are counted separately. The evidence is visible; the decision stays open.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.code.suite import generate, verify

OUT = Path("code_profile.json")

BAND_LOW, BAND_HIGH = 0.15, 0.70
TARGET_FLOOR = 0.40


class Preflight(RuntimeError):
    pass


def _wait(url: str, minutes: int, proc=None) -> bool:
    for _ in range(minutes * 12):
        if proc is not None and proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception:
            time.sleep(5)
    return False


def complete(base_url: str, model: str, case: dict, max_tokens: int,
             timeout: int = 240) -> dict:
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": case["prompt"]}]})
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 body.encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = json.load(r)["choices"][0]["message"]["content"] or ""
    except Exception as e:
        return {"completion": None, "error": repr(e)[:180]}
    return {"completion": text}


def score_one(base_url: str, model: str, case: dict, max_tokens: int) -> dict:
    out = complete(base_url, model, case, max_tokens)
    if out.get("error"):
        return {**out, "correct": False, "why": "transport"}
    v = verify(case, out["completion"])
    return {"completion": out["completion"][:600], **v}


def preflight(base_url: str, model: str, case: dict, max_tokens: int) -> dict:
    """One case before the other fifty-nine are paid for.

    P51's first attempt returned HTTP 400 on all 240 cases and printed
    `correct 0 calls 0 refused 0`, which is what a floor looks like **[ran]**. Here
    the two things that can be silently wrong are a transport error and an empty
    completion — a model returning nothing scores zero exactly like a model that
    cannot write the code.
    """
    r = complete(base_url, model, case, max_tokens)
    if r.get("error"):
        raise Preflight(f"the serving path rejected a completion: {r['error']}")
    if not (r.get("completion") or "").strip():
        raise Preflight("the model returned an empty completion — an empty arm scores "
                        "zero exactly like an arm that cannot do the task")
    return r


def summarise(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"n": 0}
    cells: dict[str, dict] = {}
    for r in records:
        key = f"{r['algorithm']}@{r['depth']}"
        row = cells.setdefault(key, {"n": 0, "correct": 0})
        row["n"] += 1
        row["correct"] += bool(r["correct"])
    by_lang: dict[str, dict] = {}
    for r in records:
        row = by_lang.setdefault(r["region"], {"n": 0, "correct": 0})
        row["n"] += 1
        row["correct"] += bool(r["correct"])
    for d in (cells, by_lang):
        for row in d.values():
            row["rate"] = round(row["correct"] / row["n"], 4)
    return {"n": n, "correct": sum(r["correct"] for r in records),
            "accuracy": round(sum(r["correct"] for r in records) / n, 4),
            "transport_errors": sum(r.get("why") == "transport" for r in records),
            "did_not_run": sum(bool(r.get("why")) and r.get("why") not in
                               ("", "output differs", "transport") for r in records),
            "wrong_output": sum(r.get("why") == "output differs" for r in records),
            "by_cell": dict(sorted(cells.items())),
            "by_language": dict(sorted(by_lang.items()))}


def band(base: dict, target: dict) -> dict:
    cells, tcells = base.get("by_cell") or {}, target.get("by_cell") or {}
    keep, why, floor_but_target_clears = [], {}, []
    for cell, row in sorted(cells.items()):
        b = row["rate"]
        t = (tcells.get(cell) or {}).get("rate")
        if b > BAND_HIGH:
            why[cell] = f"base at the ceiling ({b:.3f})"
        elif b < BAND_LOW:
            why[cell] = f"base on the floor ({b:.3f})"
            # P51's finding, counted rather than acted on: a cell the base cannot do
            # and the target always can is the largest distance an expert could
            # close, and the floor clause drops it.
            if t is not None and t >= 0.90:
                floor_but_target_clears.append(cell)
                why[cell] += f" — but the target clears it ({t:.3f})"
        elif t is not None and t < TARGET_FLOOR:
            why[cell] = f"the target fails it too ({t:.3f}) — broken, not hard"
        else:
            keep.append(cell)
    return {
        "band": [BAND_LOW, BAND_HIGH], "target_floor": TARGET_FLOOR,
        "kept": keep, "dropped": why,
        "floor_but_target_clears": floor_but_target_clears,
        "kept_algorithms": sorted({c.split("@")[0] for c in keep}),
        "kept_depths": sorted({c.split("@")[1] for c in keep}),
        "usable": len({c.split("@")[0] for c in keep}) >= 2
                  and len({c.split("@")[1] for c in keep}) >= 2,
    }


def serve(model: str, port: int, extra: list[str]) -> subprocess.Popen:
    cmd = ["vllm", "serve", model, "--port", str(port), *extra]
    print(f"[code] {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, stdout=open(f"vllm-{port}.log", "w"),
                            stderr=subprocess.STDOUT)


def run_arm(base_url: str, model: str, cases: list[dict], max_tokens: int,
            out: Path, every: int = 10) -> list[dict]:
    done: dict[str, dict] = {}
    if out.exists():
        try:
            done = {r["id"]: r for r in json.loads(out.read_text()).get("records", [])}
        except Exception as e:
            print(f"[code] could not reuse {out}: {e!r}", flush=True)
    if done:
        print(f"[code] resuming — {len(done)} already scored", flush=True)
    else:
        preflight(base_url, model, cases[0], max_tokens)
        print(f"[code] preflight ok for {model}", flush=True)
    recs: list[dict] = []
    for i, case in enumerate(cases, 1):
        if case["case_id"] in done:
            recs.append(done[case["case_id"]])
            continue
        r = score_one(base_url, model, case, max_tokens)
        r |= {"id": case["case_id"], "region": case["region"],
              "algorithm": case["algorithm"], "depth": case["depth"]}
        recs.append(r)
        if len(recs) % every == 0 or i == len(cases):
            s = summarise(recs)
            out.write_text(json.dumps({**s, "model": model,
                                       "partial": i < len(cases),
                                       "records": recs}, indent=2))
            bad = "" if not s["transport_errors"] else \
                f"  ERRORS {s['transport_errors']}/{i}"
            print(f"[code] {model} {i}/{len(cases)} correct {s['correct']} "
                  f"(did not run {s['did_not_run']}, wrong {s['wrong_output']})"
                  f"{bad}", flush=True)
    return recs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--target", default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    cases = generate()
    results = {"base": args.base, "target": args.target, "n": len(cases),
               "band": [BAND_LOW, BAND_HIGH], "arms": {}}
    OUT.write_text(json.dumps(results, indent=2))

    for arm, model in (("base", args.base), ("target", args.target)):
        p = serve(model, 8000, ["--max-model-len", str(args.max_model_len),
                                "--gpu-memory-utilization", "0.90"])
        try:
            if not _wait("http://127.0.0.1:8000/health", 25, p):
                results["arms"][arm] = {"status": "never came up"}
                OUT.write_text(json.dumps(results, indent=2))
                return 1
            print(f"[code] {arm} up", flush=True)
            recs = run_arm("http://127.0.0.1:8000/v1", model, cases,
                           args.max_tokens, Path(f"arm_{arm}.json"))
            results["arms"][arm] = {**summarise(recs), "records": recs}
            OUT.write_text(json.dumps(results, indent=2))
        finally:
            p.terminate()
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()

    results["verdict"] = band(results["arms"].get("base", {}),
                              results["arms"].get("target", {}))
    v = results["verdict"]
    b = results["arms"].get("base", {}).get("by_cell", {})
    t = results["arms"].get("target", {}).get("by_cell", {})
    print(f"\n{'cell':24}{'base':>8}{'target':>8}")
    for cell in sorted(set(b) | set(t)):
        mark = "keep" if cell in v["kept"] else "drop"
        print(f"{cell:24}{b.get(cell, {}).get('rate', float('nan')):>8.3f}"
              f"{t.get(cell, {}).get('rate', float('nan')):>8.3f}  {mark}")
    print(f"\nkept {len(v['kept'])} cells over {v['kept_algorithms']} "
          f"and depths {v['kept_depths']} — usable: {v['usable']}")
    if v["floor_but_target_clears"]:
        print(f"on the floor for the base but cleared by the target: "
              f"{v['floor_but_target_clears']}")
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT.write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
