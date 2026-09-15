"""How well calibrated is the confidence this pool ALREADY has?

THIS IS A HEADROOM CHECK AND IT CAN CANCEL WHAT COMES AFTER IT. The typed-adapter
proposal (`docs/analysis/typed-adapters.md`) rests on the claim that a first-token
logprob is *"a poor proxy — biased by format, tokenisation and prompt"* **[read]**.
That claim is testable on our own model, today, without training anything:
`email-full` already answers `IMPORTANT` / `NOT IMPORTANT`, so the probability mass
it puts on that first token **is** a confidence, and it is already on the wire.

If it is already well calibrated and already orders its errors, a typed head has
nothing to add here and the arm is **cancelled, not tied** — the rule this project
adopted after P42 bought an unresolvable arm against a base at 0.815 **[ran]**.

WHAT IS MEASURED, AND WHY IT IS NOT ACCURACY. P43 settled accuracy: 260/351,
p = 0.00036. This asks the different question a router needs — **can a caller trust
the number the model attaches to its own answer**, which P41 found no cheap way to
do: both escalation rules delivered *less* than routing by region, and the one
signal that worked required calling the frontier.

    python3 -m training.harness.confidence --base-url http://127.0.0.1:8001/v1 \\
        --model email-full --n 475
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from pathlib import Path

from training.email.inbox import generate
from training.harness.agent_sim import SYSTEM
from training.harness.bar import calibration

#: The two answers, as the suite's own words. Both are single tokens on this base
#: **[ran]** — see `docs/analysis/typed-adapters.md` Q5.
YES, NO = "IMPORTANT", "NOT IMPORTANT"


def ask(base_url, key, model, prompt, top=20, max_tokens=8, timeout=180):
    """One turn, with the logprobs the confidence is read from."""
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "logprobs": True, "top_logprobs": top,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}]})
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 data=body.encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def confidence_from(out: dict) -> tuple[bool | None, float | None, str]:
    """The verdict and the mass behind it, read off the FIRST generated token.

    `NOT IMPORTANT` and `IMPORTANT` differ at the first token — one starts with
    `NOT`, the other with `IMP` — so the first position carries the whole decision
    and the restricted softmax is over exactly two candidates. **This is the thing
    the typed proposal would replace, measured as it stands.**
    """
    ch = (out.get("choices") or [{}])[0]
    text = (ch.get("message") or {}).get("content") or ""
    said = None if not text else (False if NO in text.upper() else
                                  (True if YES in text.upper() else None))
    lp = ((ch.get("logprobs") or {}).get("content") or [])
    if not lp:
        return said, None, text[:80]
    # mass on "this token begins NOT" versus "this token begins IMPORTANT"
    p_no = p_yes = 0.0
    for alt in lp[0].get("top_logprobs") or []:
        tok = (alt.get("token") or "").strip().upper()
        p = math.exp(alt.get("logprob", -99))
        if tok.startswith("NOT") or tok == "N":
            p_no += p
        elif tok.startswith("IMP") or tok == "I":
            p_yes += p
    tot = p_no + p_yes
    if tot <= 0:
        return said, None, text[:80]
    # the confidence IN THE ANSWER GIVEN, which is what a router would threshold on
    conf = (p_yes if said else p_no) / tot if said is not None else max(p_yes, p_no) / tot
    return said, conf, text[:80]


def listing(msg: dict) -> str:
    return (f"Message {msg['id']} in thread {msg['thread_id']}\n"
            f"From: {msg['from_name']} <{msg['from']}>\n"
            f"Subject: {msg['subject']}\n"
            f"Preview: {msg['preview']}\n\n"
            "Is this important?")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", action="append", default=[],
                    help="repeatable; the base and the expert are both worth reading")
    ap.add_argument("--n", type=int, default=475)
    ap.add_argument("--seed", type=int, default=717171)
    ap.add_argument("--out", default="confidence.json")
    args = ap.parse_args()

    inbox = generate(args.n, args.seed)
    msgs = inbox["messages"]
    human = [m for m in msgs if not m["_facts"]["automated"]]
    print(f"[conf] {len(msgs)} messages, {len(human)} human", flush=True)

    res = {"n": len(msgs), "n_human": len(human), "arms": {}}
    for model in (args.model or ["email-full"]):
        recs, t0 = [], time.time()
        for i, m in enumerate(msgs, 1):
            try:
                out = ask(args.base_url, args.api_key, model, listing(m))
            except Exception as e:
                print(f"[conf] {model} {m['id']}: {e!r}"[:120], flush=True)
                continue
            said, conf, text = confidence_from(out)
            recs.append({"id": m["id"], "human": not m["_facts"]["automated"],
                         "said": said, "truth": m["_truth"],
                         "correct": said is not None and said == m["_truth"],
                         "confidence": conf, "text": text})
            if i % 50 == 0:
                ok = sum(r["correct"] for r in recs)
                print(f"[conf] {model} {i}/{len(msgs)} correct {ok}", flush=True)

        usable = [r for r in recs if r["confidence"] is not None]
        h = [r for r in usable if r["human"]]
        arm = {"model": model, "scored": len(recs),
               "with_a_confidence": len(usable),
               "all": calibration([r["confidence"] for r in usable],
                                  [r["correct"] for r in usable]),
               "human": calibration([r["confidence"] for r in h],
                                    [r["correct"] for r in h]),
               "seconds": round(time.time() - t0, 1), "records": recs}
        res["arms"][model] = arm
        Path(args.out).write_text(json.dumps(res, indent=2))
        d = arm["human"]
        print(f"\n[conf] {model} · human messages n={d['n']} acc={d['accuracy']}"
              f" mean_conf={d['mean_confidence']}", flush=True)
        print(f"[conf]   ECE {d['ece']}  Brier {d['brier']}  "
              f"AURC {d['aurc']} (oracle floor {d['aurc_oracle_floor']}, "
              f"gap {d['aurc_gap']})", flush=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
