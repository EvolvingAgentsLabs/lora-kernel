r"""H5 — the span-masked loss on a member whose tool results are short: does training only what the model writes cost
anything where the whole-text loss never visibly failed? `tr-s3` = `tr-s1`'s corpus and recipe, loss on the model's spans
(`s4_train.span_labels`); against `tr-s1`, both block-less with the memory and key capture, on H4's fresh suite.
Pre-registered in results/H5-span-loss-tracker-20261001/BRIEF.md.

    python -m examples.tracker.h5_arm --train-seed 0 --out train_tr_s3.json      # one A100
    python -m examples.tracker.h5_arm --arms s1-noblock,s3-noblock --out h5.json  # one L4
"""
from __future__ import annotations

from pathlib import Path

from examples.tracker import h3_arm
from examples.tracker.session_arm import summarise

DATA = Path("examples/tracker/data_sessions_h4")
MEMBERS = {"tr-s1": "adapters/tracker-wf-s1", "tr-s3": "adapters/tracker-wf-s3"}
ARM_SPEC = {"s1-noblock": ("tr-s1", {"harness": True, "tool_block": False}),
            "s3-noblock": ("tr-s3", {"harness": True, "tool_block": False}),
            # H5's attribution arms (after its VOID): the same members WITH the tool block
            "s1-harness": ("tr-s1", {"harness": True}), "s3-harness": ("tr-s3", {"harness": True})}
TIE_BAND = 3


def reading(rec: dict) -> dict:
    r"""Written first (BRIEF). Both arms trained members: first turns under 90 % → that arm VOID. On the dependent turns,
    paired: **EQUIVALENT** if the exact sign test finds no difference and the totals differ by ≤ 3 — the span-masked loss
    becomes the default recipe (REAL3 showed the whole-text loss fails on long results); **BETTER** if an improvement
    ($p \lt 0.05$); **WORSE** if a regression — then the whole-text loss stays for short-result members."""
    from training.harness.release_gate import pair
    arms = rec.get("arms", {})
    s = {a: summarise(list(v.values())) for a, v in arms.items()}
    num = lambda x: tuple(int(v) for v in x.split("/"))
    void = sorted(a for a in s if num(s[a]["first"])[1] == 0 or num(s[a]["first"])[0] < 0.9 * num(s[a]["first"])[1])
    out = {"summary": s, "void_arms": void}
    if not {"s1-noblock", "s3-noblock"} <= arms.keys() or void:
        out["reading"] = "VOID: an arm is void or missing"
        return out

    def dep(a):
        return {(sid, i): t for sid, x in arms[a].items() for i, t in enumerate(x["turns"]) if i > 0 and t.get("depends") and "error" not in t}
    A, B = dep("s1-noblock"), dep("s3-noblock")
    ids = sorted(A.keys() & B.keys())
    p = pair([{"id": str(i), "correct": B[i]["right"]} for i in ids], [{"id": str(i), "correct": A[i]["right"]} for i in ids],
             "tr-s3 vs tr-s1")
    r1, r3 = sum(A[i]["right"] for i in ids), sum(B[i]["right"] for i in ids)
    state = ("BETTER" if p["state"] == "improvement" else "WORSE" if p["state"] == "REGRESSION"
             else "EQUIVALENT" if abs(r3 - r1) <= TIE_BAND else "UNDECIDED")
    out.update(pair=p, s1_dependent=f"{r1}/{len(ids)}", s3_dependent=f"{r3}/{len(ids)}",
               reading=f"{state}: tr-s3 {r3}/{len(ids)} against tr-s1 {r1}/{len(ids)} ({p['only_a']}:{p['only_b']}, p={p['p_value']})")
    return out


def main(argv=None) -> int:
    return h3_arm.main(argv, doc=__doc__, data=Path("examples/tracker/data_sessions_h3"), members=MEMBERS, arm_spec=ARM_SPEC,
                       read=reading, train_member="tr-s3", default_arms="s1-noblock,s3-noblock", default_out="h5.json",
                       tag="tracker5", corpus_file="train_harness_spans.jsonl", eval_data=DATA)


if __name__ == "__main__":
    raise SystemExit(main())
