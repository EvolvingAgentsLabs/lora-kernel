"""Does a stranger's LoRA join our pool? Headroom first, then the substrate.

WHAT THIS IS FOR. Every pool result so far used adapters trained by one script, at
one rank, on the same seven modules. A LoRA trained by someone we have never met is
the independent test — and **if it does not apply, that is the more valuable
outcome**, because three of our own runs would have been telling us the substrate is
sturdier than it is.

HEADROOM RUNS FIRST AND CAN CANCEL THE ACCURACY ARM. If the base already clears ARC
on its own, an adapter cannot show anything there and the accuracy comparison is
recorded as **cancelled**, not as a tie. The substrate arm does not depend on it and
runs either way. This is the rule this project has paid for twice.

WEIGHTS ARE `safetensors`, CHECKED BEFORE DOWNLOAD. A `.bin` adapter is a pickle and
loading one executes whatever is inside it. The check is not a formality: these are
files from strangers.

    python3 -m training.harness.third_party \\
        --base Qwen/Qwen2.5-3B-Instruct \\
        --ours email-full=adapters/email-full \\
        --theirs arc=sumanthota/qwen2.5-3b-mcq-arc-lora \\
        --n-arc 200
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path("third_party_results.json")


def _wait(url: str, minutes: int, proc=None) -> bool:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            print(f"[3p] {url} exited with {proc.returncode}", flush=True)
            return False
        try:
            urllib.request.urlopen(url, timeout=5).read()
            return True
        except Exception:
            time.sleep(5)
    return False


def _hub_download(repo: str) -> str:
    from huggingface_hub import snapshot_download
    return snapshot_download(repo_id=repo, allow_patterns=[
        "adapter_config.json", "adapter_model.safetensors", "README.md"])


def fetch(repo: str, dest: Path, download=None) -> dict:
    """Download one adapter, refusing anything that is not safetensors.

    `download` is injectable so the refusal logic can be tested without the hub
    library or the network. A test that had to import `huggingface_hub` would not
    run in CI, and the thing worth testing here is what happens to a pickle.
    """
    src = Path((download or _hub_download)(repo))
    if not (src / "adapter_model.safetensors").exists():
        # A `.bin` adapter is a pickle; loading one runs whatever is inside it.
        return {"repo": repo, "refused": "no adapter_model.safetensors — a .bin "
                                         "adapter is a pickle and is not loaded"}
    dest.mkdir(parents=True, exist_ok=True)
    for f in ("adapter_config.json", "adapter_model.safetensors"):
        dest.joinpath(f).write_bytes((src / f).read_bytes())
    cfg = json.loads((dest / "adapter_config.json").read_text())
    return {"repo": repo, "path": str(dest), "r": cfg.get("r"),
            "base": cfg.get("base_model_name_or_path"),
            "targets": sorted(cfg.get("target_modules") or []),
            "bytes": (dest / "adapter_model.safetensors").stat().st_size}


def ask(model: str, prompt: str, port: int = 8000, max_tokens: int = 24) -> str | None:
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]})
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=body.encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return (json.loads(r.read())["choices"][0]["message"].get("content") or "")
    except Exception as e:
        print(f"[3p] {model} failed: {e!r}"[:160], flush=True)
        return None


def score_arc(model: str, items: list[dict], port: int = 8000) -> dict:
    from training.arc.suite import correct, parse, prompt
    ok, said_nothing, recs = 0, 0, []
    for i, it in enumerate(items, 1):
        text = ask(model, prompt(it), port)
        labs = [l for l, _ in it["choices"]]
        said = parse(text or "", labs)
        said_nothing += said is None
        right = correct(said, it["answer"])
        ok += right
        recs.append({"id": it["id"], "said": said, "want": it["answer"],
                     "correct": right, "text": (text or "")[:120]})
        if i % 25 == 0:
            print(f"[3p] {model} {i}/{len(items)} correct {ok}", flush=True)
    return {"model": model, "n": len(items), "correct": ok,
            "accuracy": round(ok / max(len(items), 1), 4),
            "unparseable": said_nothing, "records": recs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--ours", action="append", default=[], help="name=path")
    ap.add_argument("--theirs", action="append", default=[], help="name=hf_repo")
    ap.add_argument("--n-arc", type=int, default=200)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    res: dict = {"base": args.base, "downloaded": {}, "arms": {}}

    pool = dict(a.split("=", 1) for a in args.ours)
    for spec in args.theirs:
        name, repo = spec.split("=", 1)
        info = fetch(repo, Path("adapters") / f"third-{name}")
        res["downloaded"][name] = info
        print(f"[3p] {name}: {info}", flush=True)
        if "path" in info:
            if info.get("base") != args.base:
                print(f"[3p] {name} was trained on {info.get('base')} — not loading "
                      "it onto a different base", flush=True)
                info["refused"] = "base mismatch"
                continue
            pool[name] = info["path"]
    OUT.write_text(json.dumps(res, indent=2))

    from training.arc.suite import load, majority_bar
    items = load(args.n_arc)
    res["arc"] = {"n": len(items), "majority_bar": round(majority_bar(items), 4)}
    print(f"[3p] ARC: {len(items)} items, majority bar "
          f"{res['arc']['majority_bar']:.3f}", flush=True)

    ranks = [i.get("r") for i in res["downloaded"].values() if i.get("r")]
    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16", "--enable-lora",
           "--max-lora-rank", str(max([16] + ranks)),
           "--max-loras", str(max(len(pool), 1)), "--lora-modules",
           *[f"{n}={p}" for n, p in pool.items()]]
    print("[3p] " + " ".join(cmd), flush=True)
    v = subprocess.Popen(cmd, stdout=open("vllm.log", "w"), stderr=subprocess.STDOUT)
    try:
        if not _wait("http://127.0.0.1:8000/health", 20, v):
            res["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(res, indent=2)); return 1
        print("[3p] vllm up", flush=True)

        # HEADROOM FIRST. A base at the ceiling cancels the accuracy arm; it does
        # not tie with it.
        base_arc = score_arc(args.base, items)
        res["arms"]["base on ARC"] = base_arc
        OUT.write_text(json.dumps(res, indent=2))
        # HEADROOM IS POWER, NOT MARGIN — and this line is what taught that. It used
        # to read `cancel if 1 - accuracy < 0.10`; the base scored 0.815, 0.185 was
        # left, the arm was bought, and at n=200 over a 0.815 baseline it could see
        # a +0.05 adapter 55% of the time and the +0.01 that appeared 8% of the
        # time. It was unresolvable before it was purchased **[ran]** 2026-09-15.
        from training.harness.bar import n_for, resolvable
        bar = res["arc"]["majority_bar"]
        rv = resolvable(len(items), base_arc["accuracy"], effect=0.05)
        rv["n_that_would_resolve_it"] = n_for(base_arc["accuracy"], 0.05)
        res["headroom"] = rv
        print(f"[3p] headroom: base {base_arc['accuracy']:.3f} against a bar of "
              f"{bar:.3f} · {rv['why']}", flush=True)
        res["accuracy_arm"] = ("bought" if rv["resolvable"] else
                               f"cancelled: unresolvable at n={rv['n']}; "
                               f"{rv['n_that_would_resolve_it']} cases would resolve it")
        print(f"[3p] accuracy arm: {res['accuracy_arm']}", flush=True)

        # THE SUBSTRATE ARM RUNS EITHER WAY — it does not depend on headroom.
        probe = "In one sentence, what are you?"
        texts = {"base": ask(args.base, probe)}
        for n in pool:
            texts[n] = ask(n, probe)
        gate = {n: {"differs_from_base":
                    None if texts[n] is None
                    else texts[n].strip() != (texts["base"] or "").strip(),
                    "reply": (texts[n] or "")[:120]} for n in pool}
        names = list(pool)
        distinct = len({(texts[n] or "").strip() for n in names}) == len(names)
        for n in names:
            print(f"[3p] gate {n}: "
                  + ("applied" if gate[n]["differs_from_base"]
                     else "IDENTICAL TO BASE — not applied"), flush=True)
        print(f"[3p] members differ from each other: {distinct}", flush=True)
        res["identity_gate"] = gate
        res["members_are_distinct"] = distinct
        OUT.write_text(json.dumps(res, indent=2))

        if res["accuracy_arm"] == "bought":
            for n in pool:
                if n == "email-full":
                    continue          # its suite is email, not ARC
                res["arms"][f"{n} on ARC"] = score_arc(n, items)
                OUT.write_text(json.dumps(res, indent=2))

        res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        OUT.write_text(json.dumps(res, indent=2))
        print("\n[3p] done", flush=True)
    finally:
        v.terminate()
        try:
            v.wait(timeout=30)
        except subprocess.TimeoutExpired:
            v.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
