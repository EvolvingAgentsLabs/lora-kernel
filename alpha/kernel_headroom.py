"""S6's headroom check, computed from runs that already exist.

`harness.lora` claims two things: fewer protocol tokens, and fewer malformed
calls. Both have a baseline in this workspace and neither is allowed to be
compared against a flattering strawman:

  * TOKENS — `gemma4nanoloop` bound tools per phase and took peak schema overhead
    from 5,548 to 817, −85 %, with NO TRAINING AT ALL. That is the bar. **[read]**
  * MALFORMED CALLS — the incumbent is constrained decoding, which makes invalid
    syntax impossible rather than unlikely. **[read]**

Before either can be improved, this asks whether there is anything to improve on
the distribution we actually have. If the base model already emits a well-formed
call every time and the protocol already costs a few dozen tokens, then the
kernel adapter cannot be shown to help HERE, and the finding is that S6 needs a
harder tool distribution — not that the adapter is worthless.

    python3 -m alpha.kernel_headroom

Token counts are characters ÷ 4, stated as the approximation it is: no tokenizer
is loaded, and the comparison it feeds is a ratio within one prompt.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from alpha import cases as suite

RESULTS = Path("results")
PROTOCOL_HEADER = "AVAILABLE ACTIONS"


def protocol_overhead(case_id: str = "held_out-000") -> dict:
    prompt = suite.canonical_prompt(case_id)
    i = prompt.find(PROTOCOL_HEADER)
    protocol = prompt[i:] if i >= 0 else ""
    return {
        "prompt_chars": len(prompt),
        "protocol_chars": len(protocol),
        "prompt_tokens_approx": round(len(prompt) / 4),
        "protocol_tokens_approx": round(len(protocol) / 4),
        "protocol_share": round(len(protocol) / len(prompt), 3) if prompt else 0.0,
    }


def malformed_rates() -> dict:
    """One row per model per run: how often the declared shape did not come out."""
    rows: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for run in sorted(RESULTS.glob("*/cases")):
        for f in sorted(run.glob("*.json")):
            rec = json.loads(f.read_text())
            t = rec["target"]
            rows[(run.parent.name, t["name"])].append(
                suite.parse_answer(t["answer"]) is None)
            for name, d in rec["drafters"].items():
                rows[(run.parent.name, name)].append(
                    suite.parse_answer(d["own_answer"]) is None)
    return {f"{r}|{m}": {"n": len(v), "malformed": sum(v),
                         "rate": round(sum(v) / len(v), 3)}
            for (r, m), v in rows.items()}


def main() -> int:
    o = protocol_overhead()
    print("protocol overhead in the canonical prompt (chars ÷ 4, approximate)")
    print(f"  prompt   ~{o['prompt_tokens_approx']} tokens ({o['prompt_chars']} chars)")
    print(f"  protocol ~{o['protocol_tokens_approx']} tokens "
          f"({o['protocol_share'] * 100:.0f}% of the prompt)")
    print(f"  the bar to beat is gemma4nanoloop's 817, reached with no training\n")
    print("malformed-call rate — the declared shape did not come out")
    for k, v in sorted(malformed_rates().items()):
        run, model = k.split("|")
        print(f"  {run:<28}{model:<26}{v['malformed']:>3}/{v['n']:<3} {v['rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
