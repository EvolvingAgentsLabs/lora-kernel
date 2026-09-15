"""Slice a finished run by family, paired against a reference run.

WHY THIS EXISTS. The proposal on 2026-09-15 was to make subdomains narrower and
keep more experts. The cheapest test of it is not a new run: it is to take the
expert that already fails, cut it along the finest partition its suite already
carries, and ask whether some slice is competitive. If one is, a finer router
would have found it. If none is, narrowing has to create its gain by training
rather than reveal one already sitting there.

That answer was on disk the whole time and nobody had asked for it, so this is
the shape of the question rather than a one-off — the same slicing applies to
every domain the pool grows.

PAIRED, BECAUSE THE UNPAIRED VERSION LIES. Two accuracies on "the same suite" can
be computed over different cases when either run dropped one; my own by-case
routing arithmetic silently dropped 21 cases and reported 0.957 where the honest
number was 0.733 **[ran]**. So the pairing is on case id, and `n` is the size of
the intersection — reported, never assumed to be everything.
"""

from __future__ import annotations


def _index(records: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in records}


def slice_by_family(local: list[dict], reference: list[dict]) -> dict:
    """Per-family local and reference accuracy over the cases both ran.

    Returns `families` sorted by local accuracy descending — the best candidate
    for a narrow expert first — plus the `only_local` / `only_reference` split,
    which is what says whether the local expert contributes anything a router
    could keep.
    """
    a, b = _index(local), _index(reference)
    common = sorted(set(a) & set(b))
    fams: dict[str, dict] = {}
    for i in common:
        fam = a[i].get("family", "?")
        row = fams.setdefault(fam, {"family": fam, "n": 0, "local": 0,
                                    "reference": 0, "only_local": 0,
                                    "only_reference": 0})
        L, R = bool(a[i]["passed"]), bool(b[i]["passed"])
        row["n"] += 1
        row["local"] += L
        row["reference"] += R
        if L and not R:
            row["only_local"] += 1
        elif R and not L:
            row["only_reference"] += 1
    for row in fams.values():
        row["local_accuracy"] = round(row["local"] / row["n"], 4)
        row["reference_accuracy"] = round(row["reference"] / row["n"], 4)
        # A family is a candidate for a narrow expert when the local expert is
        # behind — being ahead already means the router has its answer and no
        # training is owed. `dominated` is the interesting case, not the failure.
        row["dominated"] = row["reference_accuracy"] > row["local_accuracy"]
    order = sorted(fams.values(), key=lambda r: -r["local_accuracy"])
    n = sum(r["n"] for r in order)
    return {
        "n": n,
        "dropped_local": len(a) - n,
        "dropped_reference": len(b) - n,
        "families": order,
        "local_accuracy": round(sum(r["local"] for r in order) / n, 4) if n else 0.0,
        "reference_accuracy": round(sum(r["reference"] for r in order) / n, 4) if n else 0.0,
        "only_local": sum(r["only_local"] for r in order),
        "only_reference": sum(r["only_reference"] for r in order),
        # The whole point of the slicing, stated rather than left to the reader:
        # if every family is dominated there is no already-good sub-region.
        "any_family_ahead": any(not r["dominated"] for r in order),
    }


def table(result: dict) -> str:
    lines = [f"{'family':24}{'n':>4}{'local':>8}{'ref':>8}{'only-L':>8}{'only-R':>8}"]
    for r in result["families"]:
        lines.append(f"{r['family']:24}{r['n']:4d}{r['local_accuracy']:8.3f}"
                     f"{r['reference_accuracy']:8.3f}{r['only_local']:8d}"
                     f"{r['only_reference']:8d}")
    lines.append(f"{'ALL':24}{result['n']:4d}{result['local_accuracy']:8.3f}"
                 f"{result['reference_accuracy']:8.3f}{result['only_local']:8d}"
                 f"{result['only_reference']:8d}")
    if result["dropped_local"] or result["dropped_reference"]:
        lines.append(f"unpaired: {result['dropped_local']} local, "
                     f"{result['dropped_reference']} reference — NOT counted above")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local", required=True, help="run json, or arms.<name> inside one")
    p.add_argument("--reference", required=True)
    p.add_argument("--arm", help="pick arms.<ARM>.records out of --local")
    a = p.parse_args(argv)

    loc = json.load(open(a.local))
    if a.arm:
        loc = loc["arms"][a.arm]
    ref = json.load(open(a.reference))
    out = slice_by_family(loc["records"], ref["records"])
    print(table(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
