r"""MAC2 — the Mac track on llama.cpp: does the E4B load, does the LoRA act, which drafter pays with the LoRA on, is the
swap hot. Pre-registered in results/MAC2-llamacpp-20260927/BRIEF.md; MLX's numbers (MAC) are the baseline it answers.

    python -m examples.mac.llamacpp_spec_lora --models ~/lora-kernel-models/gguf --out results/MAC2-llamacpp-20260927/mac2.json

One `llama-server` per configuration, one at a time (16 GB): the 12B Q4_0 with the expert's LoRA GGUF loaded, applied
per request (`"lora": [{"id": 0, "scale": s}]`, $s\in\lbrace 0,1\rbrace$ — $y = Wx + s\,\tfrac{\alpha}{r}B(Ax)$), and
    nospec   no speculation
    mtp      `--spec-type draft-mtp`, Gemma 4's MTP heads (`mtp-gemma-4-12b-it.gguf`)
    pair     `--spec-type draft-simple`, the E4B with the wiki LoRA merged into its weights (llama.cpp puts no LoRA on a
             draft model [read] `llama-server --help`, build 11146)
Speed-up per (expert, set) is $\mathrm{tps}_{spec}/\mathrm{tps}_{nospec}$ from the server's own `timings`; acceptance is
$\mathrm{draft\_n\_accepted}/\mathrm{draft\_n}$. Every result is written as it lands.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

GENERAL = ["Explain in a short paragraph how a refrigerator keeps food cold.",
           "Write three sentences about the history of the printing press.",
           "Give a short recipe for a tomato sauce.",
           "Describe what a compiler does, for a beginner."]
PORT = 8791
FILES = {"target": "gemma-4-12b-it-Q4_0.gguf", "mtp": "mtp-gemma-4-12b-it.gguf", "e4b": "gemma-4-E4B-it-Q4_0.gguf",
         "lora": "lora-wiki12b-f16.gguf", "pair": "wiki-e4b-merged-Q4_0.gguf"}
CONFIGS = {"nospec": [], "mtp": ["--spec-type", "draft-mtp", "-md", "{mtp}"],
           "pair": ["--spec-type", "draft-simple", "-md", "{pair}", "--spec-draft-n-max", "4"],
           # REDESIGN 1, after the registered verdict [ran] results/MAC2-llamacpp-20260927: the pair ran out of Metal memory
           # at Q4_0 and Q3_K_M; 2.31 of the draft's 4.83 GB is `per_layer_token_embd`, a lookup table (get_rows, no matmul),
           # so it goes to the CPU and the rest of the draft stays on the GPU. An extra arm; the verdict stands as recorded.
           "pair_ple_cpu": ["--spec-type", "draft-simple", "-md", "{pair}", "--spec-draft-n-max", "4",
                            "--spec-draft-override-tensor", "per_layer_token_embd=CPU"]}


def prompt_sets(n_domain: int = 6) -> dict[str, list[list[dict]]]:
    """MAC's exact sets: 3 `eval` + 3 `eval_hard` wiki questions under the wiki system prompt, and 4 general ones."""
    from memory import prompt
    from training.wiki import wiki_arm as wa
    rows = wa.load_rows("eval")[:n_domain // 2] + wa.load_rows("eval_hard")[:n_domain - n_domain // 2]
    return {"domain": [[{"role": "system", "content": prompt.SYSTEM_WIKI},
                        {"role": "user", "content": prompt.user_text_wiki(r["question"])}] for r in rows],
            "general": [[{"role": "user", "content": g}] for g in GENERAL]}


def server_cmd(model: str, cfg: str, files: dict[str, str], lora: str | None, ctx: int = 4096) -> list[str]:
    extra = [x.format(**files) for x in CONFIGS[cfg]]
    return ["llama-server", "-m", model, "--port", str(PORT), "-c", str(ctx), "-ngl", "99", "--no-webui",
            *(["--lora", lora, "--lora-init-without-apply"] if lora else []), *extra]


def _post(path: str, body: dict, timeout: float = 600) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_ready(proc, timeout: float = 300) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def chat(messages: list[dict], scale: float | None, max_tokens: int) -> dict:
    body = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.0, "seed": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    if scale is not None:
        body["lora"] = [{"id": 0, "scale": scale}]
    t0 = time.perf_counter()
    r = _post("/v1/chat/completions", body)
    tm = r.get("timings", {})
    out = {"text": r["choices"][0]["message"].get("content") or "", "tokens": tm.get("predicted_n"),
           "tps": round(tm.get("predicted_per_second") or 0, 2), "wall_s": round(time.perf_counter() - t0, 2)}
    if tm.get("draft_n"):
        out.update(draft_n=tm["draft_n"], draft_accepted=tm.get("draft_n_accepted"))
    return out


def tps(rs: list[dict]) -> float:
    """Tokens over time, pooled — not a mean of rates."""
    return sum(x["tokens"] for x in rs) / max(1e-9, sum(x["tokens"] / x["tps"] for x in rs if x["tps"]))


def summarise(rec: dict) -> dict:
    runs, out = rec.get("runs", {}), {}
    for key, rs in runs.items():
        cfg, expert, sset = key.split("/")
        if cfg == "nospec" or not rs:
            continue
        base = runs.get(f"nospec/{expert}/{sset}")
        if not base:
            continue
        dn = sum(x.get("draft_n", 0) for x in rs)
        out[key] = {"tps": round(tps(rs), 2), "tps_nospec": round(tps(base), 2), "speedup": round(tps(rs) / tps(base), 2),
                    "acceptance": round(sum(x.get("draft_accepted", 0) for x in rs) / dn, 3) if dn else None,
                    "identical": f"{sum(a['text'] == b['text'] for a, b in zip(rs, base))}/{len(base)}"}
    e, b = runs.get("nospec/lora/domain", []), runs.get("nospec/base/domain", [])
    if e and b:
        out["G1"] = f"{sum(x['text'] != y['text'] for x, y in zip(e, b))}/{len(b)} domain texts differ from the base"
    return out


def verdict(rec: dict, bar: float = 1.3) -> str:
    """BRIEF's verdict, written first: llama.cpp becomes `edge` iff the LoRA acts (≥4/6), the swap is hot and exact, and some
    drafter gives ≥ 1.3× with the LoRA on, on the expert's domain."""
    s = rec.get("summary", {})
    g1 = int(s.get("G1", "0/").split("/")[0] or 0) if "G1" in s else 0
    sw = rec.get("swap", {})
    best = max([v["speedup"] for k, v in s.items() if k.endswith("/lora/domain")] or [0])
    if g1 < 4:
        return f"VOID for the LoRA: G1 {s.get('G1')} — the conversion or its application is wrong"
    if not (sw.get("base_restored") and sw.get("expert_differs")):
        return f"NOT the edge engine: the swap is not clean ({sw})"
    return (f"llama.cpp becomes the edge engine: best drafter {best}× with the LoRA on its domain (≥ {bar})" if best >= bar else
            f"MLX stays the edge engine: best drafter with the LoRA on its domain is {best}× (< {bar})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default=os.path.expanduser("~/lora-kernel-models/gguf"))
    ap.add_argument("--configs", default="nospec,mtp,pair")
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--step1-only", action="store_true", help="does the E4B GGUF load and answer")
    ap.add_argument("--pair-file", default=None, help="the merged E4B draft (BRIEF's fallback: Q3_K_M when Q4_0 does not fit)")
    ap.add_argument("--out", default="mac2.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    files = {k: str(Path(a.models, v)) for k, v in {**FILES, **({"pair": a.pair_file} if a.pair_file else {})}.items()}
    rec.setdefault("draft_files", {})[a.configs] = files["pair"]
    rec["build"] = subprocess.run(["llama-server", "--version"], capture_output=True, text=True).stderr.strip().splitlines()[0]
    sets = prompt_sets()

    def serve(model: str, cfg: str, lora: str | None):
        log = open(out.with_name(f"server_{cfg}{'_e4b' if model == files['e4b'] else ''}.log"), "w")
        p = subprocess.Popen(server_cmd(model, cfg, files, lora), stdout=log, stderr=subprocess.STDOUT)
        return p, wait_ready(p)

    if "step1" not in rec:                                   # does the E4B load on this build?
        p, ok = serve(files["e4b"], "nospec", None)
        try:
            rec["step1"] = {"loads": ok, **({"reply": chat(sets["general"][0], None, 40)} if ok else {})}
        except Exception as e:
            rec["step1"] = {"loads": ok, "error": repr(e)[:300]}
        finally:
            p.terminate(); p.wait()
        save()
        print(f"[mac2] step 1 — E4B loads: {rec['step1']}", flush=True)
    if a.step1_only:
        return 0

    rec.setdefault("runs", {})
    for cfg in [c for c in a.configs.split(",") if c]:
        if cfg.startswith("pair") and not Path(files["pair"]).exists():
            rec.setdefault("skipped", {})[cfg] = "no merged E4B draft on disk"; save(); continue
        if all(f"{cfg}/{e}/{s}" in rec["runs"] for e in ("base", "lora") for s in sets):
            continue
        p, ok = serve(files["target"], cfg, files["lora"])
        try:
            if not ok:
                rec.setdefault("failed", {})[cfg] = "server did not come up — see its log"; save()
                print(f"[mac2] {cfg}: server did not come up", flush=True)
                continue
            for expert, scale in (("base", 0.0), ("lora", 1.0)):
                for sname, msgs in sets.items():
                    key = f"{cfg}/{expert}/{sname}"
                    if key in rec["runs"]:
                        continue
                    try:
                        rec["runs"][key] = [chat(m, scale, a.max_tokens) for m in msgs]
                    except Exception as e:                   # Metal out of memory answers 500 — a result, not a crash
                        rec.setdefault("failed", {})[cfg] = f"{key}: {repr(e)[:200]} — see server_{cfg}.log"
                        save(); print(f"[mac2] {cfg}: FAILED at {key} ({e})", flush=True)
                        break
                    save()
                    rs = rec["runs"][key]
                    dn = sum(x.get("draft_n", 0) for x in rs)
                    print(f"[mac2] {key}: {tps(rs):.1f} tok/s"
                          + (f" · acceptance {sum(x.get('draft_accepted', 0) for x in rs) / dn:.2f}" if dn else ""), flush=True)
            if cfg == "nospec":                              # step 4: the swap, timed and checked, on the no-spec server
                probe = sets["domain"][0]
                t0 = time.perf_counter(); _post("/lora-adapters", [{"id": 0, "scale": 1.0}]); t_on = time.perf_counter() - t0
                e_text = chat(probe, None, a.max_tokens)["text"]
                t0 = time.perf_counter(); _post("/lora-adapters", [{"id": 0, "scale": 0.0}]); t_off = time.perf_counter() - t0
                b_text = chat(probe, None, a.max_tokens)["text"]
                rec["swap"] = {"on_ms": round(t_on * 1e3, 2), "off_ms": round(t_off * 1e3, 2),
                               "expert_differs": e_text != b_text,
                               "base_restored": b_text == rec["runs"]["nospec/base/domain"][0]["text"],
                               "expert_matches_per_request": e_text == rec["runs"]["nospec/lora/domain"][0]["text"]}
                save()
                print(f"[mac2] swap: {rec['swap']}", flush=True)
        finally:
            p.terminate(); p.wait()
    rec["summary"] = summarise(rec)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[mac2] {json.dumps(rec['summary'])}\n[mac2] {rec['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
