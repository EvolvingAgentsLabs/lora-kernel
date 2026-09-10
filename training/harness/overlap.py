"""How much of the same subspace do two adapters occupy?

WHY THIS IS A TEST AND NOT A DIAGNOSTIC. P11 measured that giving each adapter
its own projections — kernel on `q,k,v,o`, domain on the MLP, no matrix in common
— made delegation *worse*, and concluded that the competition is not a collision
in weight space **[ran]** `results/P11-disjoint-20260909/`. That conclusion makes
a prediction about geometry, and this script checks it:

- If the two deltas turn out to be **nearly orthogonal already** and the domain
  still wins the format on 25 of 30 steps, then the collision story is dead twice
  over and P11's reading stands. Orthogonality regularisation and null-space
  projection would then be fixes for a problem that is not there.
- If they turn out to **overlap heavily**, P11's disjoint result needs another
  explanation, and forcing orthogonality inside the shared projections becomes
  worth buying.

Either way the number is bought before the fix, which is the order that keeps a
measurement from becoming a search.

WHAT IS COMPUTED, per target module and adapter pair:

  cosine        <dW_k, dW_d>_F / (||dW_k||_F ||dW_d||_F)  — the deltas as vectors
  col_overlap   mean cos of the principal angles between the column spaces of
                B_k and B_d — where each adapter writes
  row_overlap   the same for the row spaces of A_k and A_d — what each reads

A rank-16 subspace drawn at random in 2048 dimensions has an expected principal
angle cosine near sqrt(r/d) ~ 0.09, so that is the number "unrelated" looks like,
and the report prints it beside the measurement rather than leaving the reader to
guess the scale.

    python3 -m training.harness.overlap adapters/kernel adapters/domain
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict


def _load(path: str) -> dict:
    from safetensors.torch import load_file
    return load_file(f"{path}/adapter_model.safetensors")


def _pairs(sd: dict) -> dict:
    """module name -> (A, B), from peft's `...lora_A.weight` / `...lora_B.weight`."""
    out: dict[str, dict] = defaultdict(dict)
    for k, v in sd.items():
        m = re.match(r".*?\.(?:model\.)?(layers\..*?)\.lora_([AB])\.weight$", k)
        if m:
            out[m.group(1)][m.group(2)] = v
    return {k: (v["A"], v["B"]) for k, v in out.items() if "A" in v and "B" in v}


def _principal(x, y) -> float:
    """Mean cosine of the principal angles between the column spaces of x and y."""
    import torch
    qx, _ = torch.linalg.qr(x.float())
    qy, _ = torch.linalg.qr(y.float())
    s = torch.linalg.svdvals(qx.T @ qy)
    return float(s.clamp(0, 1).mean())


def compare(kernel_path: str, domain_path: str, scale: float = 2.0) -> dict:
    import torch
    ka, da = _pairs(_load(kernel_path)), _pairs(_load(domain_path))
    shared = sorted(set(ka) & set(da))
    rows = []
    for name in shared:
        (Ak, Bk), (Ad, Bd) = ka[name], da[name]
        dWk = (Bk.float() @ Ak.float()) * scale
        dWd = (Bd.float() @ Ad.float()) * scale
        num = float((dWk * dWd).sum())
        den = float(dWk.norm() * dWd.norm()) or 1.0
        rows.append({"module": name, "cosine": num / den,
                     "col_overlap": _principal(Bk, Bd),
                     "row_overlap": _principal(Ak.T, Ad.T)})
    if not rows:
        return {"shared_modules": 0,
                "note": "the two adapters modify no matrix in common"}

    def stat(key):
        v = sorted(r[key] for r in rows)
        return {"mean": sum(v) / len(v), "min": v[0], "max": v[-1],
                "median": v[len(v) // 2]}

    r = ka[shared[0]][0].shape[0]
    d = ka[shared[0]][0].shape[1]
    return {"shared_modules": len(rows), "rank": r,
            "chance_overlap": math.sqrt(r / d),
            "cosine": stat("cosine"), "col_overlap": stat("col_overlap"),
            "row_overlap": stat("row_overlap"), "per_module": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kernel", nargs="?", default="adapters/kernel")
    ap.add_argument("domain", nargs="?", default="adapters/domain")
    ap.add_argument("--scale", type=float, default=2.0, help="alpha / r")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    res = compare(args.kernel, args.domain, args.scale)
    if args.out:
        open(args.out, "w").write(json.dumps(res, indent=2))
    slim = {k: v for k, v in res.items() if k != "per_module"}
    print(json.dumps(slim, indent=2))
    if res.get("shared_modules"):
        print(f"\nUnrelated rank-{res['rank']} subspaces in {res['rank']}/"
              f"{res['chance_overlap']:.3f}-scaled space overlap about "
              f"{res['chance_overlap']:.3f}. Measured column overlap: "
              f"{res['col_overlap']['mean']:.3f}.")
        print("Near chance means the two adapters already write in different "
              "directions and still compete — which is P11's reading, and kills "
              "orthogonality regularisation as a fix. Well above chance means "
              "P11's disjoint result needs another explanation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
