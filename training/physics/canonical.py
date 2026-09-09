"""Chains written by the oracle itself, so every tool call is exact.

WHY NOT THE TEACHER. `gemini-3.8-flash` ignores a prose tool protocol about half
the time: 9 of 18 chains contained no call at all, and `pump_power` averaged
zero even after the instruction was hardened to an "ABSOLUTE RULE" **[ran]**.
That is worth recording on its own — it is direct evidence for the claim
`harness.lora` rests on, that a protocol living in the prompt is unreliable and
belongs in the weights.

WHAT THIS CHANGES, STATED PLAINLY. These chains are not distilled from a frontier
model. They are emitted by the generator, which knows every intermediate value in
closed form. So this arm no longer tests "can a small model absorb a frontier's
reasoning"; it tests "does a tool fix the execution bottleneck", with the
supervision made exact so the answer is not confounded by teacher noise. The
frontier's contribution — proving the gap exists, and supplying the prose chains
of the first corpus — stands where it was measured.

Every number inside a call comes from the problem statement or from a previous
call's result. Nothing is computed in prose.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re

from training.physics.calc import evaluate
from training.physics.generate import G, TRAIN_FAMILIES, _instruction, generate


def _c(expr: str) -> tuple[str, float]:
    """A call and the value it returns — the value is never written by hand."""
    return f"<calc>{expr}</calc>= {evaluate(expr):.6g}", evaluate(expr)


def chain_for(row: dict) -> str | None:
    """The canonical solution for one case, as calls the harness answers."""
    p, w, fam = row["prompt"], row["workings"], row["family"]

    def num(before: str, after: str = " ") -> float:
        return float(p.split(before)[1].split(after)[0])

    lines = []
    if fam == "hydrostatic_force":
        wdt, hgt = num("gate ", " m wide"), num("wide and ", " m tall")
        rho, top = num("density ", " kg"), num("top edge ", " m below")
        s1, hc = _c(f"{top} + {hgt}/2")
        s2, area = _c(f"{wdt} * {hgt}")
        s3, _ = _c(f"{rho} * {G} * {hc:.6g} * {area:.6g}")
        lines = [f"1. Depth of the centroid below the surface: {s1}",
                 f"2. Area of the gate: {s2}",
                 f"3. Resultant force F = rho g h_c A: {s3}"]
    elif fam == "manning_channel":
        b, y = num("bed width ", " m"), num("depth of ", " m")
        slope = num("bed slope is ", " and")
        import re as _re
        n = float(_re.search(r"coefficient is ([\d.]+?)\.\s", p).group(1))
        s1, a = _c(f"{b} * {y}")
        s2, per = _c(f"{b} + 2*{y}")
        s3, r = _c(f"{a:.6g} / {per:.6g}")
        s4, _ = _c(f"(1/{n}) * {a:.6g} * {r:.6g}**(2/3) * sqrt({slope})")
        lines = [f"1. Flow area: {s1}", f"2. Wetted perimeter: {s2}",
                 f"3. Hydraulic radius R = A/P: {s3}",
                 f"4. Discharge Q = (1/n) A R^(2/3) sqrt(S): {s4}"]
    elif fam in ("pipe_head_loss", "pump_power"):
        q = num("at ", " m^3/s")
        d = num("diameter ", " m")
        L = num("length ", " m")
        rho, mu = num("density ", " kg"), num("viscosity ", " Pa")
        eps = num("roughness is ", " m")
        s1, a = _c(f"pi/4 * {d}**2")
        s2, v = _c(f"{q} / {a:.6g}")
        s3, re = _c(f"{rho} * {v:.6g} * {d} / {mu}")
        if re < 2300:
            s4, f = _c(f"64 / {re:.6g}")
            fl = f"4. Laminar (Re < 2300), so f = 64/Re: {s4}"
        else:
            s4, f = _c(f"0.25 / (log10({eps}/(3.7*{d}) + 5.74/{re:.6g}**0.9))**2")
            fl = f"4. Turbulent (Re > 2300), Swamee-Jain: {s4}"
        s5, h = _c(f"{f:.6g} * ({L}/{d}) * {v:.6g}**2 / (2*{G})")
        lines = [f"1. Cross-sectional area: {s1}", f"2. Velocity v = Q/A: {s2}",
                 f"3. Reynolds number: {s3}", fl,
                 f"5. Head loss h = f (L/D) v^2 / (2g): {s5}"]
        if fam == "pump_power":
            eta = num("efficiency ", ",")
            s6, _ = _c(f"{rho} * {G} * {q} * {h:.6g} / {eta}")
            lines.append(f"6. Shaft power P = rho g Q h / eta: {s6}")
    elif fam == "terminal_velocity":
        d = num("diameter ", " m")
        rho_s = num("density ", " kg")
        rho_f = num("fluid of density ", " kg")
        mu = num("viscosity ", " Pa")
        s1, dr = _c(f"{rho_s} - {rho_f}")
        s2, _ = _c(f"{dr:.6g} * {G} * {d}**2 / (18*{mu})")
        lines = [f"1. Density difference: {s1}",
                 f"2. Stokes terminal velocity v = (rho_s - rho_f) g d^2 / (18 mu): {s2}"]
    elif fam == "venturi_flow":
        d1 = num("diameter of ", " m")
        d2 = num("throat\ndiameter of ", " m") if "throat\ndiameter" in p \
            else float(p.split("throat diameter of ")[1].split(" m")[0])
        rho, dp = num("density is ", " kg"), num("drop between inlet and throat is ", " Pa")
        s1, a1 = _c(f"pi/4 * {d1}**2")
        s2, a2 = _c(f"pi/4 * {d2}**2")
        s3, _ = _c(f"{a2:.6g} * sqrt(2*{dp} / ({rho} * (1 - ({a2:.6g}/{a1:.6g})**2)))")
        lines = [f"1. Inlet area: {s1}", f"2. Throat area: {s2}",
                 f"3. Flow rate Q = A2 sqrt(2 dp / (rho (1 - (A2/A1)^2))): {s3}"]
    if not lines:
        return None
    final = evaluate(lines[-1].split("</calc>= ")[1])
    return "\n".join(lines) + f'\n\n{{"answer": {final:.6g}}}'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=770208)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--out", default="training/physics/data_canon/train.jsonl")
    # TWO RENDERINGS OF THE SAME ORACLE CHAIN, so a domain corpus and a kernel
    # corpus can differ in exactly one thing: whether the arithmetic is delegated.
    #   calc   — `<calc>expr</calc>= v`, the protocol. This is P7's corpus.
    #   inline — `expr = v`, the same formulas with the arithmetic done in place.
    # And two prompt contracts: `legacy` reproduces P6/P7 byte for byte; `shared`
    # is the neutral contract of `training/protocol.py`, which says nothing about
    # tools so that the protocol can only come from the weights.
    ap.add_argument("--style", default="calc", choices=["calc", "inline"])
    ap.add_argument("--contract", default="legacy", choices=["legacy", "shared"])
    args = ap.parse_args()

    if args.contract == "shared":
        from training.protocol import SYSTEM
        rows = generate(args.n, args.seed, TRAIN_FAMILIES, style="working")
    else:
        from training.physics.headroom import SYSTEM
        rows = generate(args.n, args.seed, TRAIN_FAMILIES, style="calc")
    kept, bad = [], 0
    for row in rows:
        try:
            chain = chain_for(row)
        except Exception:
            chain = None
        if chain is None:
            bad += 1
            continue
        if args.style == "inline":
            # `<calc>expr</calc>= v` -> `expr = v`. The formulas and the values are
            # the oracle's either way; only the delegation is removed.
            chain = re.sub(r"<calc>(.*?)</calc>=", r"\1 =", chain, flags=re.S)
        got = float(chain.rsplit('"answer": ', 1)[1].rstrip("}\n"))
        # The chain must reach the oracle's own answer, or it is not a solution.
        if abs(got - row["answer"]) > args.rtol * abs(row["answer"]):
            bad += 1
            continue
        kept.append({"case_id": row["case_id"], "family": row["family"],
                     "answer": row["answer"], "unit": row["unit"],
                     "calc_calls": chain.count("<calc>"),
                     "style": args.style, "contract": args.contract,
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": row["prompt"]},
                                  {"role": "assistant", "content": chain}]})
    import pathlib
    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(k) for k in kept) + "\n")
    from collections import Counter
    print(json.dumps({
        "kept": len(kept), "rejected": bad, "of": len(rows),
        "calls_per_example": round(sum(k["calc_calls"] for k in kept) / max(1, len(kept)), 2),
        "by_family": dict(Counter(k["family"] for k in kept)),
        "note": "chains emitted by the oracle, every value from a tool call",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
