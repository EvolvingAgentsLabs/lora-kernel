"""P45 — where does a small expert stop being sufficient? A headroom sweep.

WHY THIS RUNS BEFORE ANY TRAINING. Every number this project has about the fluids
expert was measured on a suite whose oracle solutions are 6, 7 or 9 steps long, with
no case below six and each family pinned at one depth **[ran]** 2026-09-15. So
`this expert is too weak` and `this suite is too hard` were the same number, 0.122,
and no amount of training could have told them apart. `training/physics/ladder.py`
adds rungs at 1-4; this measures them.

THE ARMS, IN THE ORDER THAT CAN KILL THE QUESTION SOONEST.

1. **The bare base, no adapter.** The ordinary ceiling check, asked of every rung
   rather than of the suite as a whole. A rung the base already passes cannot show
   an adapter anything, so this decides which rungs are worth training for. It is
   also the cheapest arm and it runs first.
2. **The existing expert, unchanged.** It is already trained; this costs inference
   only, and its curve against depth IS the question — where does a small expert
   stop being sufficient. Nothing new is trained to obtain it.

The frontier is NOT an arm here. It is run separately as a ceiling check on the
ladder — a rung the frontier fails is a broken rung, not a hard one — and it is
never the gate. A gate copied from the frontier answers `can the frontier be
withdrawn here`, which is a different question from `is this sufficient`.

THE GATE IS ABSOLUTE AND PRE-REGISTERED AT 0.90. At 0.80 one answer in five is
wrong and every answer has to be checked by hand, which removes the reason to have
the expert. The number is written here, before the run, rather than chosen from the
curve afterwards.

FALSIFICATION, ALSO WRITTEN BEFORE THE RUN. If the expert's curve is flat — if it
fails a one-step lookup at roughly the rate it fails a nine-step chain — then
difficulty is not what blocks it, the analysis that bought this run is wrong, and
the failure is something the ladder does not measure. `verdict_of()` computes that
from the data rather than leaving it to a reading.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path("ladder_sweep.json")

SUFFICIENCY_GATE = 0.90
# A curve is flat when the easy end is no better than the hard end by more than
# this. Written before the run; it is the falsification condition, not a knob.
FLAT_WITHIN = 0.15


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


def _probe(model: str, port: int = 8001) -> str | None:
    body = json.dumps({"model": model, "max_tokens": 24, "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": "Reply with one short sentence "
                                                "about water."}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    except Exception:
        return None


def verdict_of(arms: dict) -> dict:
    """Read the curve, and say what it means, from the numbers rather than by eye."""
    expert = arms.get("expert", {}).get("by_steps") or {}
    base = arms.get("base", {}).get("by_steps") or {}
    depths = sorted(int(d) for d in expert if d.isdigit())
    if not depths:
        return {"readable": False, "why": "the expert arm produced no depths"}

    easy = [d for d in depths if d <= 4]
    hard = [d for d in depths if d >= 6]

    def acc(rows, ds):
        # A DEPTH THE OTHER ARM DID NOT REACH IS ZERO CASES, NOT A CRASH. The
        # depths come from the expert's run; the base's can be missing one because
        # it ran out of turns on every case at that rung, and that is a result
        # rather than an error.
        got = [rows.get(str(d), {"n": 0, "passed": 0}) for d in ds]
        n = sum(r["n"] for r in got)
        k = sum(r["passed"] for r in got)
        return (round(k / n, 4) if n else None), n

    e_easy, n_easy = acc(expert, easy)
    e_hard, n_hard = acc(expert, hard)
    b_easy, _ = acc(base, easy) if base else (None, 0)

    # THE SUFFICIENCY CLAIM IS PER RUNG, not for the ladder as a whole. An expert
    # that clears 0.90 at one step and 0.40 at four is a useful expert with a known
    # edge, and reporting one average would hide exactly the edge we are buying.
    sufficient = [d for d in depths
                  if expert[str(d)]["n"] and
                  expert[str(d)]["passed"] / expert[str(d)]["n"] >= SUFFICIENCY_GATE]
    # A rung the base already clears cannot show an adapter anything — the ordinary
    # ceiling check, asked per rung.
    no_headroom = [d for d in depths
                   if base.get(str(d), {}).get("n") and
                   base[str(d)]["passed"] / base[str(d)]["n"] >= SUFFICIENCY_GATE]

    flat = (e_easy is not None and e_hard is not None
            and (e_easy - e_hard) <= FLAT_WITHIN)
    return {
        "readable": True,
        "expert_easy": e_easy, "n_easy": n_easy,
        "expert_hard": e_hard, "n_hard": n_hard,
        "base_easy": b_easy,
        "gate": SUFFICIENCY_GATE,
        "sufficient_at_depths": sufficient,
        "base_already_clears": no_headroom,
        "curve_is_flat": flat,
        "reading": (
            "FALSIFIED: the curve is flat, so difficulty is not what blocks this "
            "expert and the analysis that bought this run is wrong"
            if flat else
            f"sufficient at depth {sufficient}" if sufficient else
            "the expert clears the absolute gate at no depth on this ladder"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", default="fluids-full=adapters/fluids-full")
    ap.add_argument("--n", type=int, default=140)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--seed", type=int, default=454545)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    name, path = args.adapter.split("=", 1)
    if not (Path(path) / "adapter_model.safetensors").exists():
        print(f"[sweep] no weights at {path}")
        return 1

    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16", "--enable-lora",
           "--max-lora-rank", "16", "--max-loras", "1",
           "--lora-modules", f"{name}={path}"]
    print("[sweep] " + " ".join(cmd), flush=True)
    v = subprocess.Popen(cmd, stdout=open("vllm.log", "w"),
                         stderr=subprocess.STDOUT)
    px = None
    results = {"base": args.base, "adapter": name, "n": args.n,
               "seed": args.seed, "gate": SUFFICIENCY_GATE,
               "families": "full", "arms": {}}

    def save():
        OUT.write_text(json.dumps(results, indent=2))

    try:
        if not _wait("http://127.0.0.1:8000/health", 20, v):
            results["arms"]["server"] = {"status": "never came up"}
            save(); return 1
        print("[sweep] vllm up", flush=True)
        px = subprocess.Popen([sys.executable, "-u", "-m",
                               "training.harness.openai_proxy",
                               "--upstream", "http://127.0.0.1:8000",
                               "--port", "8001"],
                              stdout=open("proxy.log", "w"),
                              stderr=subprocess.STDOUT)
        if not _wait("http://127.0.0.1:8001/v1/models", 3, px):
            results["arms"]["proxy"] = {"status": "never came up"}
            save(); return 1
        print("[sweep] proxy up", flush=True)

        # C18. An adapter vLLM logs as loaded and then does not apply makes the two
        # arms the same model, and the sweep would report the base's curve twice
        # while calling one of them an expert.
        base_text, exp_text = _probe(args.base), _probe(name)
        applied = (exp_text is not None and base_text is not None
                   and exp_text.strip() != base_text.strip())
        results["identity_gate"] = {"differs_from_base": applied}
        print(f"[sweep] gate {name}: "
              + ("applied" if applied else "IDENTICAL TO BASE — not applied"),
              flush=True)
        save()
        if not applied:
            print("[sweep] STOPPED. Both arms would be the base.", flush=True)
            results["stopped_at_gate"] = True
            save(); return 1

        # THE BASE FIRST. It is the ceiling check and it is the arm that can make
        # the second one unnecessary, so it is bought first — never as a grid.
        for arm, model in (("base", args.base), ("expert", name)):
            print(f"[sweep] arm {arm} · model {model}", flush=True)
            r = subprocess.run([sys.executable, "-u", "-m",
                                "training.harness.fluids_sim",
                                "--base-url", "http://127.0.0.1:8001/v1",
                                "--model", model, "--families", "full",
                                "--n", str(args.n), "--seed", str(args.seed),
                                "--max-tokens", str(args.max_tokens),
                                "--out", f"arm_{arm}.json"],
                               capture_output=True, text=True)
            print(r.stdout[-1200:], flush=True)
            p = Path(f"arm_{arm}.json")
            results["arms"][arm] = (json.loads(p.read_text()) if p.exists()
                                    else {"status": "produced nothing",
                                          "stderr": r.stderr[-400:]})
            save()      # persisted before the next arm starts, always

        results["verdict"] = verdict_of(results["arms"])
        print(f"\n{'depth':>6}{'base':>10}{'expert':>10}{'n':>6}")
        b = results["arms"].get("base", {}).get("by_steps", {})
        e = results["arms"].get("expert", {}).get("by_steps", {})
        for d in sorted(set(b) | set(e), key=lambda x: (not x.isdigit(), x)):
            print(f"{d:>6}{b.get(d, {}).get('accuracy', float('nan')):>10.3f}"
                  f"{e.get(d, {}).get('accuracy', float('nan')):>10.3f}"
                  f"{e.get(d, {}).get('n', 0):>6}")
        print("\n" + results["verdict"]["reading"], flush=True)
        results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
    finally:
        for p_ in (px, v):
            if p_ is None:
                continue
            p_.terminate()
            try:
                p_.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p_.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
