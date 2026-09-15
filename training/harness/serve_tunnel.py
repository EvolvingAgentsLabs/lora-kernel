"""Serve the pool on a rented card and hand back a URL the user's machine can reach.

WHY A TUNNEL AT ALL. The user's machine is a 16 GB arm64 Mac and cannot serve vLLM,
so the pool lives on Colab and the proxy lives with the user — which is the split
that keeps **their** credential on **their** machine. The tunnel is the only piece
that makes those two halves meet.

WHAT TRAVELS, SAID RATHER THAN DISCOVERED. Everything the pool serves crosses this
tunnel to a rented VM. For a synthetic suite that is nothing; for real
correspondence it is the message. `docs/OPENCLAW.md` says the same thing before its
first command.

THE URL IS PRINTED ON ONE LINE WITH A MARKER, so a chain watching the log can find
it without a human reading scrollback:

    [tunnel] URL https://something.trycloudflare.com

    python3 -m training.harness.serve_tunnel --base Qwen/Qwen2.5-3B-Instruct \\
        --adapter email-full=adapters/email-full --hours 3
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path("tunnel.json")


def _wait_http(url: str, minutes: int, proc=None) -> bool:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            print(f"[tunnel] {url} exited with {proc.returncode}", flush=True)
            return False
        try:
            urllib.request.urlopen(url, timeout=5).read()
            return True
        except Exception:
            time.sleep(5)
    return False


def start_tunnel(port: int, minutes: int = 3) -> tuple[subprocess.Popen, str | None]:
    """cloudflared, because it needs no account and no token to hand back a URL."""
    subprocess.run("which cloudflared >/dev/null 2>&1 || "
                   "(wget -q -O /usr/local/bin/cloudflared "
                   "https://github.com/cloudflare/cloudflared/releases/latest/download/"
                   "cloudflared-linux-amd64 && chmod +x /usr/local/bin/cloudflared)",
                   shell=True)
    log = open("cloudflared.log", "w+")
    p = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate",
                          "--url", f"http://127.0.0.1:{port}"],
                         stdout=log, stderr=subprocess.STDOUT)
    deadline = time.time() + minutes * 60
    pat = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    while time.time() < deadline:
        text = Path("cloudflared.log").read_text(errors="replace")
        m = pat.search(text)
        if m:
            return p, m.group(0)
        if p.poll() is not None:
            return p, None
        time.sleep(3)
    return p, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[], help="name=path")
    ap.add_argument("--hours", type=float, default=3.0,
                    help="how long to hold the tunnel open before shutting down")
    ap.add_argument("--score", default=None, metavar="MODEL:N",
                    help="once the tunnel is up, run the email suite against MODEL "
                         "for N cases ON THIS VM, so the work survives the user's "
                         "machine being switched off")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    pool = dict(a.split("=", 1) for a in args.adapter)
    missing = [n for n, p in pool.items()
               if not (Path(p) / "adapter_model.safetensors").exists()]
    if missing:
        print(f"[tunnel] no weights for {missing}")
        return 1

    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16"]
    if pool:
        cmd += ["--enable-lora", "--max-lora-rank", "16",
                "--max-loras", str(len(pool)), "--lora-modules",
                *[f"{n}={p}" for n, p in pool.items()]]
    print("[tunnel] " + " ".join(cmd), flush=True)
    v = subprocess.Popen(cmd, stdout=open("vllm.log", "w"), stderr=subprocess.STDOUT)
    tun = None
    res = {"base": args.base, "pool": list(pool)}
    try:
        if not _wait_http("http://127.0.0.1:8000/health", 20, v):
            res["status"] = "vllm never came up"
            OUT.write_text(json.dumps(res, indent=2)); return 1
        print("[tunnel] vllm up", flush=True)

        tun, url = start_tunnel(8000)
        if not url:
            res["status"] = "no tunnel url"
            OUT.write_text(json.dumps(res, indent=2)); return 1
        res["url"] = url
        # THE MARKER IS THE POINT: a chain greps for it rather than a human reading
        # scrollback, and the URL changes on every start.
        print(f"[tunnel] URL {url}", flush=True)
        print(f"[tunnel] EVERYTHING THE POOL SERVES CROSSES THIS TUNNEL to a rented "
              f"VM. Synthetic suites cost nothing; real correspondence is the "
              f"message.", flush=True)
        res["holds_until"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + args.hours * 3600))
        OUT.write_text(json.dumps(res, indent=2))

        # THE LONG WORK RUNS HERE, NOT ON THE USER'S LAPTOP. On 2026-09-15 a
        # 475-case scoring run was killed by the user pausing their machine, and it
        # could not be moved onto the VM afterwards: once the chain exits it takes
        # the session NAME with it, and `colab exec` addresses sessions by name.
        # The tunnel stayed reachable over HTTP and the VM stayed unreachable for
        # anything else **[ran]**. So the VM carries its own proxy and its own
        # scoring, and the tunnel is for interactive use rather than for the run.
        scorer = None
        if args.score:
            model, _, n = args.score.partition(":")
            subprocess.Popen([sys.executable, "-u", "-m",
                              "training.harness.openai_proxy",
                              "--upstream", "http://127.0.0.1:8000", "--port", "8001"],
                             stdout=open("proxy.log", "w"), stderr=subprocess.STDOUT)
            if _wait_http("http://127.0.0.1:8001/v1/models", 3):
                print(f"[tunnel] scoring {model} on {n} cases, on this VM",
                      flush=True)
                scorer = subprocess.Popen(
                    [sys.executable, "-u", "-m", "training.harness.agent_sim",
                     "--base-url", "http://127.0.0.1:8001/v1", "--model", model,
                     "--n", n or "150", "--seed", "717171",
                     "--out", f"arm_{model}_{n}.json"],
                    stdout=open("score.log", "w"), stderr=subprocess.STDOUT)
            else:
                print("[tunnel] the local proxy never came up; not scoring",
                      flush=True)

        deadline = time.time() + args.hours * 3600
        while time.time() < deadline:
            if v.poll() is not None or tun.poll() is not None:
                print("[tunnel] a process exited; shutting down", flush=True)
                break
            if scorer is not None and scorer.poll() is not None:
                tail = Path("score.log").read_text(errors="replace").strip().splitlines()
                for line in tail[-4:]:
                    print(f"[tunnel] score: {line}", flush=True)
                res["scored"] = tail[-1] if tail else None
                OUT.write_text(json.dumps(res, indent=2))
                scorer = None
            time.sleep(30)
        res["status"] = "closed"
        OUT.write_text(json.dumps(res, indent=2))
    finally:
        for p_ in (tun, v):
            if p_ is None:
                continue
            p_.terminate()
            try:
                p_.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p_.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
