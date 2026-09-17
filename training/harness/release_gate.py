"""Phase 1 — a reproducible release of an expert, or the training chain is broken.

WHAT A RELEASE IS. An adapter is a number from one run until it is shown to come
back: **re-served**, the recorded score must be a tie by the paired test; and
**re-trained** from the same corpus with the same recipe, the new adapter must tie
the released one on the same cases. The first tests the serving substrate holds
(Phase 0 says it does); the second tests the *training* chain — corpus, recipe, seed —
and is the number this project has never had: how much variance the instrument
itself carries between two trainings.

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2). Two arms scored on the same cases are
compared only on the cases where they disagree: with u favouring A and d favouring B,
p = min(1, 2·Pr[Bin(u+d, ½) ≥ max(u, d)]). A release **reproduces** when both pairs
— (re-served, recorded) and (re-trained, re-served) — come back *not different* at
p ≤ 0.05. A regression is a pair that is different with the new arm on the losing
side; an improvement is reported too, because a training chain that silently got
better is as unreproducible as one that got worse.

THE MANIFEST. `releases/<name>@v1.json` records the adapter's `safetensors` sha256,
the corpus sha256, the prompt sha the drafts were served under, the recipe, and the
recorded scores. `tests/test_release.py` re-hashes the files it names.

    python3 -m training.harness.release_gate --name email-full \\
        --released adapters/email-full --corpus training/harness/data_ef/train.jsonl \\
        --recorded results/P55-graded-ranking-20260916/session_a.json --retrain \\
        --out results/P57-release-20260917/release.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from training.harness import bar, suites
from training.harness.accept_rank import applied, draft_arm, serve, stop, summarise, wait_ready

OUT = Path("release.json")
RECIPE = {"r": 16, "lora_alpha": 32, "epochs": 3, "lr": 2e-4, "batch": 2, "accum": 8,
          "max_seq": 1536, "seed": 0,
          "targets": "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _map(records) -> dict:
    return {r["id"]: bool(r["correct"]) for r in records if "correct" in r and "error" not in r}


def pair(new: list[dict], ref: list[dict], label: str) -> dict:
    """The paired verdict between a new arm and its reference."""
    c = bar.compare(_map(new), _map(ref))
    state = ("tie" if not c["different"] else
             "REGRESSION" if c["only_b"] > c["only_a"] else "improvement")
    return {"pair": label, **c, "state": state}


def verdict(pairs: list[dict]) -> dict:
    bad = [p["pair"] for p in pairs if p["state"] != "tie"]
    return {"reproduces": not bad and bool(pairs), "not_tied": bad,
            "reading": ("RELEASE REPRODUCES — every pair a tie" if not bad and pairs else
                        "RELEASE DOES NOT REPRODUCE: " + ", ".join(
                            f"{p['pair']} {p['state']} ({p['only_a']}:{p['only_b']}, p={p['p_value']})"
                            for p in pairs if p["state"] != "tie") if bad else
                        "NOTHING COMPARED")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", default="email-full")
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--released", default="adapters/email-full")
    ap.add_argument("--corpus", default="training/harness/data_ef/train.jsonl")
    ap.add_argument("--recorded", default="results/P55-graded-ranking-20260916/session_a.json",
                    help="the run whose records the re-serve must tie")
    ap.add_argument("--retrain", action="store_true",
                    help="also re-train from the corpus in a subprocess and pair it")
    ap.add_argument("--suite", default="email")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.base)
    suite = suites.load(args.suite)
    cases = suite.cases(args.n or suite.eval_n, args.seed or suite.eval_seed)

    rec = json.loads(Path(args.recorded).read_text())
    recorded = list(rec["arms"][args.name]["records"].values())

    result = {"name": args.name, "base": args.base, "recipe": RECIPE,
              "corpus": args.corpus, "corpus_sha256": sha256(Path(args.corpus)),
              "released": args.released,
              "released_sha256": sha256(Path(args.released, "adapter_model.safetensors")),
              "recorded": {"path": args.recorded, "n": len(recorded),
                           "correct": sum(r["correct"] for r in recorded)},
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "arms": {}, "pairs": []}

    def save():
        out.write_text(json.dumps(result, indent=2))

    save()
    adapters = {args.name: args.released}
    if args.retrain:
        retrained = f"adapters/{args.name}-retrained"
        if not Path(retrained, "adapter_model.safetensors").exists():
            print(f"[release] retraining {args.name} from {args.corpus}", flush=True)
            rc = subprocess.call([sys.executable, "-m", "training.code.train_one",
                                  "--base", args.base, "--train", args.corpus,
                                  "--out-dir", retrained, "--epochs", str(RECIPE["epochs"]),
                                  "--r", str(RECIPE["r"]), "--alpha", str(RECIPE["lora_alpha"]),
                                  "--lr", str(RECIPE["lr"])])
            if rc != 0:
                result["stopped"] = f"retraining failed rc={rc}"; save(); return 1
        result["retrained_sha256"] = sha256(Path(retrained, "adapter_model.safetensors"))
        adapters[f"{args.name}-retrained"] = retrained

    extra = ["--max-model-len", "4096", "--gpu-memory-utilization", "0.90",
             "--enable-lora", "--max-lora-rank", "16", "--max-loras", str(len(adapters)),
             "--lora-modules", *[f"{k}={v}" for k, v in adapters.items()]]
    p = serve(args.base, extra)
    try:
        if not wait_ready(p):
            result["stopped"] = "the base never came up"; save(); return 1
        for name, model in [("base", args.base)] + [(k, k) for k in adapters]:
            arm = result["arms"].setdefault(name, {"model": model, "records": {}})
            recs = draft_arm(model, tok, suite, cases, args.max_tokens, args.concurrency,
                             arm["records"], save)
            arm.update(summarise(recs))
            if name != "base":
                arm["applied"] = applied(list(result["arms"]["base"]["records"].values()), recs)
                print(f"[release] gate {name}: {arm['applied']['verdict']}", flush=True)
            save()
    finally:
        stop(p)

    served = list(result["arms"][args.name]["records"].values())
    result["pairs"].append(pair(served, recorded, "re-served vs recorded"))
    if args.retrain:
        new = list(result["arms"][f"{args.name}-retrained"]["records"].values())
        result["pairs"].append(pair(new, served, "re-trained vs re-served"))
    save()
    try:
        result["verdict"] = verdict(result["pairs"])
    except Exception as e:
        result["verdict"] = {"reproduces": False, "reading": repr(e)[:160]}
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    for pr in result["pairs"]:
        print(f"[release] {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})",
              flush=True)
    print(f"[release] {result['verdict']['reading']}", flush=True)

    if result["verdict"]["reproduces"]:
        man = Path("releases") / f"{args.name}@v1.json"
        man.parent.mkdir(exist_ok=True)
        man.write_text(json.dumps({
            "name": args.name, "version": 1, "base": args.base, "recipe": RECIPE,
            "corpus": args.corpus, "corpus_sha256": result["corpus_sha256"],
            "adapter_sha256": result["released_sha256"],
            "prompt_sha": (served[0].get("prompt_sha") if served else None),
            "suite": suite.name, "n": len(cases),
            "score": {"correct": result["arms"][args.name]["correct"],
                      "human_correct": result["arms"][args.name]["human_correct"]},
            "pairs": result["pairs"], "run": str(out)}, indent=2))
        print(f"[release] manifest written: {man}", flush=True)
    return 0 if result["verdict"]["reproduces"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
