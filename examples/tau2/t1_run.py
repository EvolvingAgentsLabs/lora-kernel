"""T1 — τ²-bench airline baselines on one Colab card: the teacher (Gemma 4 31B) and the base (Gemma 4 E4B) as agents.

WHAT IT MEASURES. `results/TAU2-T1-baselines-20261005/BRIEF.md`: on airline's official test split (20 tasks), k = 4
trials, the same simulator for both arms (the 31B), is there a gap worth distilling?

    pass^k(task) = C(c, k) / C(n, k)        n trials, c successes (reward within 1e-6 of 1)
    pass^k       = mean over tasks          τ²'s own definition (agent_metrics.py:113–126, arXiv 2406.12045)
    gap          = pass^1(teacher) − pass^1(base), paired over tasks; 95 % CI by bootstrap over tasks (B = 10 000)

ARMS (both native tool calling through vLLM's `gemma4` tool parser — vLLM 0.30 `vllm/tool_parsers/__init__.py`):
    teacher   agent = simulator = google/gemma-4-31B-it-qat-w4a16-ct (Google's QAT, compressed-tensors W4A16)
    base      agent = google/gemma-4-E4B-it (bf16), simulator = the 31B
Members (T2 onwards) are served through `examples/tau2/shim.py` instead — a later brief, not this runner's T1.

WHAT THE RUNNER DOES, IN ORDER, AND WHAT STOPS IT
    1  installs τ² at the pinned commit (clone + `uv sync --frozen` + websockets, the T0 MANIFEST's recipe)
    2  sizes the card (nvidia-smi); the base arm needs both models resident — ≥ 70 GiB (G4 96 GB, H100 80 GB).
       On a 40 GB A100 only the teacher arm can run, and it says so
    3  serves the 31B (port 8000) and, for the base arm, the E4B (port 8001), thinking off, `--language-model-only`
    4  PREFLIGHT per arm — an arm proves it can reach its tools before it scores (CLAUDE.md §3): a tool-call probe
       and a simulator probe; parser markup left in `content` (`<|tool_call>`…) is a broken wire → STOPPED
    5  `tau2 run --domain airline --task-split-name test --num-trials 4 --max-steps 150 --auto-resume`, streaming a
       `[tau2]` line per finished simulation and persisting the raw τ² results (gzip+base64) into `--out`
       as they land, so a new session resumes where the last one stopped (τ²'s own `--auto-resume`)
    6  when both arms are complete: metrics, the gate, `"decision"` and `"finished"` — read by the chain

    python -m examples.tau2.t1_run --base google/gemma-4-E4B-it --out t1.json      (Colab, via chain_serve.sh)
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TAU2_REPO = "https://github.com/sierra-research/tau2-bench.git"
TAU2_COMMIT = "5bfa7e37b36656b37dc6d022156be6563c1007f3"      # results/TAU2-T0-recon-20261005/MANIFEST
TEACHER = "google/gemma-4-31B-it-qat-w4a16-ct"
TEACHER_REV = "52f3f65bc7a02d555763bc923bd1d9094898219d"
BASE = "google/gemma-4-E4B-it"
BASE_REV = "ee0ef6023621cff504d758262d4e04895a5af4a2"
SIM_NAME, SIM_PORT = "gemma-4-31b", 8000
AGENT_NAME, AGENT_PORT = "gemma-4-e4b", 8001
SHIM_PORT = 8100
BIG_CARD_GIB = 70               # both models resident: 31B W4A16 (~22 GiB of weights) + E4B bf16 (15.2 GiB [ran] B1)
SUCCESS_EPS = 1e-6
MARKUP = re.compile(r"<\|tool_call>|<tool_call>|<\|\"\|>|^call:\w+\{|<\|channel>|<channel\|>", re.M)
FIXTURES = Path(__file__).parent / "fixtures"


def say(msg: str) -> None:
    print(f"[tau2] {msg}", flush=True)


# ------------------------------------------------------------------------------------------- metrics (pure)
def pass_hat_k(n: int, c: int, k: int) -> float | None:
    """τ²'s pass^k for one task: C(c, k) / C(n, k); None when fewer than k trials exist."""
    if n < k:
        return None
    return math.comb(c, k) / math.comb(n, k)


def per_task(sims: list[dict]) -> dict[str, dict]:
    """{task_id: {"n", "c"}} over simulations that count (infrastructure errors are not trials)."""
    out: dict[str, dict] = {}
    for s in sims:
        if s["termination"] == "infrastructure_error":
            continue
        t = out.setdefault(s["task_id"], {"n": 0, "c": 0})
        t["n"] += 1
        t["c"] += s["reward"] is not None and s["reward"] >= 1 - SUCCESS_EPS
    return out


def pass_k(tasks: dict[str, dict], k: int) -> float | None:
    vals = [pass_hat_k(v["n"], v["c"], k) for v in tasks.values()]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def bootstrap(values: list[float], b: int = 10_000, seed: int = 0) -> tuple[float, float]:
    """95 % percentile CI of the mean, resampling the units (tasks) with replacement."""
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(b))
    return means[int(0.025 * b)], means[int(0.975 * b) - 1]


def arm_metrics(sims: list[dict], k: int) -> dict:
    tasks = per_task(sims)
    out = {"simulations": len(sims), "tasks": len(tasks)}
    for j in range(1, k + 1):
        vals = [pass_hat_k(v["n"], v["c"], j) for v in tasks.values()]
        vals = [v for v in vals if v is not None]
        out[f"pass^{j}"] = round(sum(vals) / len(vals), 4) if vals else None
        if j in (1, k) and vals:
            out[f"pass^{j}_ci95"] = [round(x, 4) for x in bootstrap(vals)]
    term: dict[str, int] = {}
    for s in sims:
        term[s["termination"]] = term.get(s["termination"], 0) + 1
    n = max(1, len(sims))
    out.update({
        "termination": term,
        "tool_calls_per_sim": round(sum(s["tool_calls"] for s in sims) / n, 2),
        "tool_errors_per_sim": round(sum(s["tool_errors"] for s in sims) / n, 2),
        "malformed_calls": sum(s["malformed"] for s in sims),
        "agent_prompt_tokens_per_sim": round(sum(s["agent_prompt_tokens"] for s in sims) / n),
        "agent_completion_tokens_per_sim": round(sum(s["agent_completion_tokens"] for s in sims) / n),
        "user_tokens_per_sim": round(sum(s["user_tokens"] for s in sims) / n),
        "agent_latency_s_per_call": round(sum(s["agent_gen_s"] for s in sims) / max(1, sum(s["agent_turns"] for s in sims)), 3),
        "sim_duration_s_mean": round(sum(s["duration"] for s in sims) / n, 1),
        "api_usd": 0.0,
    })
    return out


def gap(sims_t: list[dict], sims_b: list[dict], k: int = 1) -> dict:
    """pass^k(teacher) − pass^k(base), paired over the tasks both arms completed, with a bootstrap CI over tasks."""
    a, b = per_task(sims_t), per_task(sims_b)
    common = sorted(set(a) & set(b), key=lambda x: (len(x), x))
    d = [pass_hat_k(a[t]["n"], a[t]["c"], k) - pass_hat_k(b[t]["n"], b[t]["c"], k) for t in common
         if a[t]["n"] >= k and b[t]["n"] >= k]
    if not d:
        return {"tasks": 0}
    lo, hi = bootstrap(d)
    return {"tasks": len(d), "gap": round(sum(d) / len(d), 4), "ci95": [round(lo, 4), round(hi, 4)],
            "teacher_better_tasks": sum(x > 0 for x in d), "base_better_tasks": sum(x < 0 for x in d)}


def verdict(arms: dict, k: int, n_tasks: int, threshold_pp: float) -> dict:
    """Gate T1 (BRIEF.md). VOID and INCOMPLETE are checked per arm before the gap is read."""
    for name, arm in arms.items():
        m = arm.get("metrics") or {}
        infra = (m.get("termination") or {}).get("infrastructure_error", 0) + \
            (m.get("termination") or {}).get("unexpected_error", 0)
        if arm.get("preflight", {}).get("ok") is False:
            return {"decision": "VOID", "why": f"{name}: preflight failed — the arm never reached its tools"}
        if m.get("simulations") and infra / m["simulations"] > 0.05:
            return {"decision": "VOID", "why": f"{name}: {infra} infrastructure/unexpected errors (> 5 %)"}
        if (m.get("termination") or {}).get("user_error", 0) / max(1, m.get("simulations", 0)) > 0.05:
            return {"decision": "VOID", "why": f"{name}: the simulator failed in > 5 % of simulations"}
        tasks = per_task(arm.get("sims") or [])
        if len(tasks) < n_tasks or any(v["n"] < k for v in tasks.values()):
            return {"decision": "INCOMPLETE", "why": f"{name}: {len(tasks)} tasks, need {n_tasks} × {k} trials"}
    g1 = gap(arms["teacher"]["sims"], arms["base"]["sims"], 1)
    gk = gap(arms["teacher"]["sims"], arms["base"]["sims"], k)
    distil = g1["gap"] * 100 >= threshold_pp and g1["ci95"][0] > 0
    return {"decision": "DISTIL HERE" if distil else "NO NEED TO DISTIL HERE",
            "rule": f"gap pass^1 >= {threshold_pp} pp AND the 95 % bootstrap CI over tasks excludes 0",
            f"gap_pass^1": g1, f"gap_pass^{k}": gk}


# ------------------------------------------------------------------------------------------- reading τ²'s results
def sim_record(s: dict) -> dict:
    """One simulation, compact: what the metrics read, nothing of the conversation's text."""
    calls = errors = malformed = turns = 0
    ap = ac = ut = 0
    gen = 0.0
    for m in s.get("messages") or []:
        u = m.get("usage") or {}
        if m["role"] == "assistant":
            turns += 1
            calls += len(m.get("tool_calls") or [])
            malformed += bool(MARKUP.search(m.get("content") or ""))
            ap += u.get("prompt_tokens") or 0
            ac += u.get("completion_tokens") or 0
            gen += m.get("generation_time_seconds") or 0.0
        elif m["role"] == "user":
            ut += (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0)
        elif m["role"] == "tool":
            errors += bool(m.get("error"))
    ri = s.get("reward_info") or {}
    term = s.get("termination_reason")
    return {"task_id": s["task_id"], "trial": s.get("trial"), "reward": ri.get("reward"),
            "termination": term.value if hasattr(term, "value") else term, "duration": s.get("duration") or 0.0,
            "messages": len(s.get("messages") or []), "tool_calls": calls, "tool_errors": errors,
            "malformed": malformed, "agent_turns": turns, "agent_prompt_tokens": ap, "agent_completion_tokens": ac,
            "user_tokens": ut, "agent_gen_s": round(gen, 3)}


def pack(raw: bytes) -> str:
    """The raw τ² results inside our JSON without a string the chain greps for (`"finished"`, `"decision"`)."""
    return base64.b64encode(gzip.compress(raw)).decode()


def unpack(s: str) -> bytes:
    return gzip.decompress(base64.b64decode(s))


# ------------------------------------------------------------------------------------------- Colab plumbing
def sh(cmd: str, cwd: str | None = None, check: bool = True) -> str:
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd[:80]} -> rc {r.returncode}: {(r.stdout + r.stderr)[-600:]}")
    return r.stdout.strip()


def install_tau2(where: Path) -> dict:
    tau2 = where / ".venv/bin/tau2"
    if not (where / ".git").exists():
        say(f"install: cloning τ² at {TAU2_COMMIT[:9]}")
        sh(f"git clone -q {TAU2_REPO} {where}")
    sh(f"git -C {where} checkout -q {TAU2_COMMIT}")
    head = sh(f"git -C {where} rev-parse HEAD")
    if head != TAU2_COMMIT:
        raise RuntimeError(f"τ² is at {head}, not the pinned {TAU2_COMMIT}")
    if not tau2.exists():
        if not shutil.which("uv"):
            sh(f"{sys.executable} -m pip -q install uv")
        say("install: uv sync --frozen (τ²'s own lock) + websockets (the T0 gap)")
        sh("uv sync --frozen --python 3.12", cwd=str(where))
        sh("uv pip install -q --python .venv/bin/python websockets", cwd=str(where))
    version = sh(f"{where}/.venv/bin/python -c 'import tau2, importlib.metadata as m; print(m.version(\"tau2\"))'")
    say(f"install: τ² {version} at {head[:9]}")
    return {"commit": head, "version": version}


def card() -> dict:
    try:
        out = sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits")
        name, mib = [x.strip() for x in out.splitlines()[0].split(",")]
        return {"name": name, "gib": round(int(mib) / 1024, 1)}
    except Exception as e:
        return {"name": None, "gib": 0.0, "error": repr(e)}


def vllm_serve(model: str, rev: str, name: str, port: int, util: float, max_len: int, log: str,
               extra: list[str] | None = None) -> subprocess.Popen:
    cmd = ["vllm", "serve", model, "--revision", rev, "--served-model-name", name, "--port", str(port),
           "--max-model-len", str(max_len), "--gpu-memory-utilization", str(util), "--language-model-only",
           "--enable-auto-tool-choice", "--tool-call-parser", "gemma4", "--reasoning-parser", "gemma4", *(extra or [])]
    say(f"serve: {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=open(log, "a"), stderr=subprocess.STDOUT)


def wait_up(proc: subprocess.Popen, port: int, log: str, minutes: int = 30) -> bool:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc.poll() is not None:
            say(f"serve: :{port} exited rc={proc.returncode}; the last lines of {log}:")
            print("".join(open(log).readlines()[-30:]), flush=True)
            return False
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5).read()
            return True
        except Exception:
            time.sleep(10)
    say(f"serve: :{port} never answered /health in {minutes} min")
    return False


def chat(port: int, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", method="POST",
                                 data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


NO_THINK = {"chat_template_kwargs": {"enable_thinking": False}}


def preflight(agent_port: int, agent_name: str, must_call: bool) -> dict:
    """Does the agent's wire carry tool calls, and does the simulator answer as plain text? Not a score."""
    req0 = json.loads((FIXTURES / "tau2_requests.json").read_text())[0]["body"]
    system = next(m for m in req0["messages"] if m["role"] == "system")
    probes = ["Hi, my user id is mia_li_3668. Please look up my profile.",
              "Can you get the details of reservation NO6JO3?",
              "What is the status of flight HAT170 on 2024-05-15?"]
    seen = []
    for p in probes:
        r = chat(agent_port, {"model": agent_name, "temperature": 0.0, "max_tokens": 512, "tools": req0["tools"],
                              "tool_choice": "auto", "messages": [system, {"role": "user", "content": p}], **NO_THINK})
        m = r["choices"][0]["message"]
        seen.append({"probe": p, "tool_calls": [(tc["function"]["name"], tc["function"]["arguments"])
                                                 for tc in m.get("tool_calls") or []],
                     "content": (m.get("content") or "")[:200], "markup_leak": bool(MARKUP.search(m.get("content") or ""))})
    sim = chat(SIM_PORT, {"model": SIM_NAME, "temperature": 0.0, "max_tokens": 128, **NO_THINK, "messages": [
        {"role": "system", "content": "You are a customer calling an airline. Reply in one sentence."},
        {"role": "user", "content": "Hi! How can I help you today?"}]})["choices"][0]["message"]
    sim_text = sim.get("content") or ""
    calls = sum(bool(s["tool_calls"]) for s in seen)
    leak = any(s["markup_leak"] for s in seen) or bool(MARKUP.search(sim_text))
    ok = not leak and bool(sim_text.strip()) and (calls > 0 or not must_call)
    why = None if ok else ("parser markup left in content" if leak else "simulator returned nothing"
                           if not sim_text.strip() else "the agent made no tool call in 3 probes")
    return {"ok": ok, "why": why, "probes": seen, "calls": calls, "simulator": sim_text[:200]}


def litellm_probe(tau2_dir: Path, agent: str, port: int) -> dict:
    """The path τ² itself takes — litellm, `openai/<name>`, `api_base`, `extra_body` — one call, in τ²'s venv."""
    req0 = json.loads((FIXTURES / "tau2_requests.json").read_text())[0]["body"]
    code = ("import json,sys,litellm\n"
            "a=json.loads(sys.argv[1]); r=litellm.completion(model=a['model'], messages=a['messages'], "
            "tools=a['tools'], tool_choice='auto', **a['args'])\n"
            "m=r.choices[0].message\n"
            "print(json.dumps({'content': m.content, 'tool_calls': [[t.function.name, t.function.arguments] "
            "for t in (m.tool_calls or [])]}))\n")
    arg = json.dumps({"model": f"openai/{agent}", "tools": req0["tools"], "args": llm_args(port, 512),
                      "messages": [next(m for m in req0["messages"] if m["role"] == "system"),
                                   {"role": "user", "content": "Hi, my user id is mia_li_3668. Please look up my profile."}]})
    r = subprocess.run([str(tau2_dir / ".venv/bin/python"), "-c", code, arg], capture_output=True, text=True,
                       timeout=600, env={**os.environ, "OPENAI_API_KEY": "EMPTY"})
    if r.returncode != 0:
        return {"ok": False, "why": (r.stderr or r.stdout)[-400:]}
    got = json.loads(r.stdout.strip().splitlines()[-1])
    return {"ok": not MARKUP.search(got.get("content") or ""), **got}


def llm_args(port: int, max_tokens: int) -> dict:
    return {"temperature": 0.0, "api_base": f"http://127.0.0.1:{port}/v1", "api_key": "EMPTY",
            "max_tokens": max_tokens, "extra_body": NO_THINK}


def run_arm(name: str, agent: str, agent_port: int, a, tau2_dir: Path, results: dict, save) -> None:
    arm = results["arms"][name]
    save_to = f"t1_{name}"
    path = tau2_dir / "data/simulations" / save_to / "results.json"
    if arm.get("tau2_raw") and not path.exists():               # a new session: put the last one's work back
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(unpack(arm["tau2_raw"]))
        say(f"{name}: resumed {len(arm.get('sims') or [])} simulation(s) from the carried results")
    cmd = [str(tau2_dir / ".venv/bin/tau2"), "run", "--domain", "airline", "--task-split-name", a.split,
           "--agent-llm", f"openai/{agent}", "--agent-llm-args", json.dumps(llm_args(agent_port, 2048)),
           "--user-llm", f"openai/{SIM_NAME}", "--user-llm-args", json.dumps(llm_args(SIM_PORT, 1024)),
           "--num-trials", str(a.trials), "--max-steps", str(a.max_steps), "--max-concurrency", str(a.concurrency),
           "--timeout", str(a.sim_timeout), "--save-to", save_to, "--auto-resume", "--log-level", "WARNING"]
    arm["command"] = " ".join(cmd)
    say(f"{name}: tau2 run … --agent-llm openai/{agent} --user-llm openai/{SIM_NAME} --num-trials {a.trials} "
        f"--max-steps {a.max_steps} --max-concurrency {a.concurrency}")
    t0 = time.time()
    log = open(f"tau2_{name}.log", "a")
    proc = subprocess.Popen(cmd, cwd=str(tau2_dir), stdout=log, stderr=subprocess.STDOUT,
                            env={**os.environ, "OPENAI_API_KEY": "EMPTY"})
    done_ids: set = {(s["task_id"], s["trial"]) for s in arm.get("sims") or []}
    want = a.tasks * a.trials

    def harvest() -> None:
        try:
            raw = path.read_bytes()
            sims = json.loads(raw).get("simulations") or []
        except Exception:
            return                                   # mid-write: the next poll reads it
        new = [sim_record(s) for s in sims if (s["task_id"], s.get("trial")) not in done_ids]
        if not new:
            return
        recs = {(r["task_id"], r["trial"]): r for r in (arm.get("sims") or [])}
        for r in new:
            recs[(r["task_id"], r["trial"])] = r
            done_ids.add((r["task_id"], r["trial"]))
            say(f"{name}: {len(done_ids)}/{want} · task {r['task_id']} trial {r['trial']} reward {r['reward']} "
                f"· {r['termination']} · {r['tool_calls']} calls · {r['malformed']} malformed · {r['duration']:.0f}s")
        arm["sims"] = sorted(recs.values(), key=lambda r: (int(r["task_id"]) if str(r["task_id"]).isdigit() else 0,
                                                           r["trial"] or 0))
        arm["tau2_raw"] = pack(raw)
        tasks = per_task(arm["sims"])
        say(f"{name}: running pass^1 {pass_k(tasks, 1):.3f} over {len(tasks)} task(s)")
        save()

    while proc.poll() is None:
        time.sleep(30)
        harvest()
    harvest()
    arm["wall_s"] = round((arm.get("wall_s") or 0) + time.time() - t0, 1)
    arm["tau2_rc"] = proc.returncode
    if proc.returncode != 0:
        say(f"{name}: tau2 exited rc={proc.returncode}; the last lines of tau2_{name}.log:")
        print("".join(open(f"tau2_{name}.log").readlines()[-25:]), flush=True)
    if len(done_ids) >= want:
        arm["complete"] = True
        arm["metrics"] = arm_metrics(arm["sims"], a.trials)
        m = arm["metrics"]
        say(f"{name}: COMPLETE pass^1 {m['pass^1']} {m.get('pass^1_ci95')} · pass^{a.trials} {m.get(f'pass^{a.trials}')} "
            f"· {m['tool_calls_per_sim']} calls/sim · {m['malformed_calls']} malformed · {m['termination']}")
    save()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE, help="the agent under test in the base arm (the chain's BASE)")
    ap.add_argument("--base-rev", default=BASE_REV, help="the base's pinned revision (T1b: the 12B's)")
    ap.add_argument("--teacher", default=TEACHER)
    ap.add_argument("--arms", default="teacher,base")
    ap.add_argument("--split", default="test")
    ap.add_argument("--tasks", type=int, default=20, help="tasks in the split (airline test = 20)")
    ap.add_argument("--trials", type=int, default=4)
    ap.add_argument("--max-steps", type=int, default=150, help="above the longest shipped airline run (104 messages)")
    ap.add_argument("--sim-timeout", type=int, default=1200)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--threshold-pp", type=float, default=15.0)
    ap.add_argument("--tau2-dir", default="/content/tau2-bench")
    ap.add_argument("--out", default="t1.json")
    a = ap.parse_args()

    out = Path(a.out)
    results = json.loads(out.read_text()) if out.exists() else {}
    results.pop("stopped_at_gate", None)
    results.setdefault("run", "TAU2-T1-baselines")
    results.setdefault("arms", {})
    results.setdefault("sessions", [])
    session = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "card": card()}
    results["sessions"].append(session)
    t_session = time.time()

    def save() -> None:
        session["seconds"] = round(time.time() - t_session, 1)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(results, indent=1))
        tmp.replace(out)

    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    for n in arms:
        results["arms"].setdefault(n, {})
    results["config"] = {"teacher": a.teacher, "teacher_revision": TEACHER_REV, "base": a.base, "base_revision": a.base_rev,
                         "simulator": a.teacher, "split": a.split, "trials": a.trials, "max_steps": a.max_steps,
                         "sim_timeout": a.sim_timeout, "concurrency": a.concurrency, "max_model_len": a.max_model_len,
                         "temperature": 0.0, "thinking": "off", "threshold_pp": a.threshold_pp}
    save()
    say(f"T1 · arms {arms} · card {session['card']} · split {a.split} · k {a.trials}")

    try:
        import vllm
        session["vllm"] = vllm.__version__
    except Exception:
        session["vllm"] = None
    results["tau2"] = install_tau2(Path(a.tau2_dir))
    save()

    todo = [n for n in arms if not results["arms"][n].get("complete")]
    big = session["card"]["gib"] >= BIG_CARD_GIB
    skipped = "base" in todo and not big
    if skipped:
        say(f"note: the base arm needs both models resident (>= {BIG_CARD_GIB} GiB); this card has "
            f"{session['card']['gib']} GiB. Run it on GPU=G4 (96 GB) or H100; the teacher arm runs here.")
        todo = [n for n in todo if n != "base"]
        results["arms"]["base"]["skipped_on"] = session["card"]
    procs = []
    if todo:
        util_sim = 0.45 if "base" in todo else 0.90
        p = vllm_serve(a.teacher, TEACHER_REV, SIM_NAME, SIM_PORT, util_sim, a.max_model_len, "vllm.log")
        procs.append(p)
        if not wait_up(p, SIM_PORT, "vllm.log"):
            results["stopped"] = "the 31B never came up (vllm.log)"
            save()
            say("STOPPED: the 31B never came up")
            return 1
        if "base" in todo:
            p = vllm_serve(a.base, a.base_rev, AGENT_NAME, AGENT_PORT, 0.40, a.max_model_len, "vllm_e4b.log")
            procs.append(p)
            if not wait_up(p, AGENT_PORT, "vllm_e4b.log"):
                results["stopped"] = "the E4B never came up (vllm_e4b.log)"
                save()
                say("STOPPED: the E4B never came up")
                return 1
    try:
        for name in todo:
            agent, port = (SIM_NAME, SIM_PORT) if name == "teacher" else (AGENT_NAME, AGENT_PORT)
            pf = preflight(port, agent, must_call=(name == "teacher"))
            results["arms"][name]["preflight"] = pf
            save()
            say(f"{name}: preflight {'ok' if pf['ok'] else 'FAILED'} · {pf['calls']}/3 probes called a tool · "
                f"simulator said {pf['simulator'][:60]!r}")
            if pf["ok"]:
                pf["litellm"] = litellm_probe(Path(a.tau2_dir), agent, port)
                pf["ok"] = pf["litellm"]["ok"]
                pf["why"] = None if pf["ok"] else f"τ²'s litellm path failed: {pf['litellm'].get('why') or 'markup'}"
                save()
                say(f"{name}: litellm path {'ok' if pf['ok'] else 'FAILED'} · {pf['litellm'].get('tool_calls')}")
            if not pf["ok"]:
                say(f"STOPPED: {name} preflight — {pf['why']}")
                return 1
            run_arm(name, agent, port, a, Path(a.tau2_dir), results, save)
    finally:
        for p in procs:
            p.terminate()

    if all(results["arms"].get(n, {}).get("complete") for n in ("teacher", "base")):
        v = verdict(results["arms"], a.trials, a.tasks, a.threshold_pp)
        results["gate"] = v
        results["decision"] = v["decision"]
        results["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save()
        say(f"decision: {v['decision']} · {json.dumps({k: v[k] for k in v if k.startswith('gap')})}")
    elif all(results["arms"][n].get("complete") for n in arms if not (n == "base" and skipped)):
        # EVERYTHING THIS CARD CAN RUN IS DONE: stop the chain rather than buy another session of the same card.
        # A later chain for the remaining arm drops this key from its local copy first (BRIEF.md, chain commands).
        results["stopped_at_gate"] = (f"requested arms complete ({', '.join(n for n in arms if results['arms'][n].get('complete'))}); "
                                      "the gate needs teacher and base")
        save()
        say(f"STOPPED: {results['stopped_at_gate']}")
    else:
        save()
        say("session over without both arms complete — the next session resumes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
