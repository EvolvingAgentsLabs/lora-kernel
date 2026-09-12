"""S2, re-scored against a target that is actually ahead.

THE QUESTION, unchanged since §5: does **agreement with the target** order
candidates the way verified quality does? It is the project's promotion criterion,
so every later step assumes it. It passed 14 of 15 pairs — against targets that
were peers of the strongest candidate, which tests the criterion's mechanics and
not the architecture's claim **[ran]** §5.

THE TARGET'S ANSWERS ARE ALREADY PAID FOR. P10 ran `gemini-3.8-flash` on these
exact 30 cases at seed 515151 under the shared contract, twice at two token
budgets. Nothing here calls an API.

AND THE TRAP IS THE POINT. At the 6k budget the target scores **30/30**, where
agreeing with it is simply being right and the ordering test passes for no reason
at all. The same model at the smaller budget scores **17/30** and is wrong on 13 of
them — those 13 are the only cases where agreement and correctness can disagree, so
that is the arm the verdict is read from. The 30/30 arm is printed beside it and
labelled as the tautology it is.

    python3 -m training.harness.ranking
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

RTOL = 0.02
P10 = Path("results/P10-baseline-recheck-20260909")
P23 = Path("results/P23-ranking-20260912")

# THE FIRST FALLIBLE TARGET WAS NOT FALLIBLE, IT WAS TRUNCATED. `gemini-3.8-flash`
# at a smaller budget scores 17/30, and all 13 of those failures turned out to be
# derivations cut off mid-page whose "answer" was a pipe area — at the full budget
# the same model answers 13 of 13 correctly [ran]. Its row is gone from here
# because it is struck at length in the brief, which is where history lives.
TARGETS = [
    ("gemini-3.5-flash-lite @6k — naturally weaker (21/30, 9 of 9 failures complete)",
     P23 / "target-flash-lite/headroom.json",
     "openai:google/gemini-3.5-flash-lite", True),
    ("gemini-3.8-flash @6k — the tautology control (30/30)",
     P10 / "shared6k/headroom.json", "openai:google/gemini-3.8-flash", False),
]

# ALL FOUR ARE RE-RUN ON THE SAME MACHINE, the 4b included even though P10 already
# published 14/30 for it. That number came out of ollama on an arm64 Mac and these
# come out of ollama on a rented Linux card; reusing it would put the build inside
# the ordering test. The published 14/30 stays where it is and is not overwritten.
CANDIDATES = [
    ("qwen3.5:2b", P23 / "qwen3-5-2b/headroom.json", "ollama:qwen3.5:2b"),
    ("qwen3.5:4b", P23 / "qwen3-5-4b/headroom.json", "ollama:qwen3.5:4b"),
    ("qwen3.5:9b", P23 / "qwen3-5-9b/headroom.json", "ollama:qwen3.5:9b"),
    ("gemma4:12b", P23 / "gemma4-12b/headroom.json", "ollama:gemma4:12b"),
]


def load(path: Path, arm: str) -> dict | None:
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    a = d["arms"].get(arm)
    return {r["case_id"]: r for r in a["records"]} if a else None


def close(a, b) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= RTOL * max(abs(a), abs(b), 1e-12)


def agreement(cand: dict, targ: dict) -> tuple[float, float, int]:
    """Semantic agreement, character agreement, and the shared case count.

    CHARACTER AGREEMENT IS CARRIED AS THE CONTROL THAT ALREADY FAILED. §11 settled
    the criterion on semantics because character α scored 1/5 with one target and
    4/5 with another on the same candidates — it measures whether the target
    indents like the candidate. It is printed so that stays visible.
    """
    ids = sorted(set(cand) & set(targ))
    sem = sum(close(cand[i].get("got"), targ[i].get("got")) for i in ids)
    chr_ = sum((cand[i].get("raw") or "").strip() == (targ[i].get("raw") or "").strip()
               for i in ids)
    n = max(len(ids), 1)
    return sem / n, chr_ / n, len(ids)


def main() -> int:
    cands = []
    for name, path, arm in CANDIDATES:
        recs = load(path, arm)
        if recs is None:
            print(f"[missing] {name} — {path}")
            continue
        verified = sum(r["passed"] for r in recs.values()) / len(recs)
        cands.append({"name": name, "recs": recs, "verified": verified})
    if len(cands) < 3:
        print("fewer than three candidates on disk; nothing to order yet")
        return 0

    report = {}
    for label, path, arm, decisive in TARGETS:
        targ = load(path, arm)
        if targ is None:
            continue
        print(f"\n=== {label}")
        rows = []
        for c in cands:
            sem, chr_, n = agreement(c["recs"], targ)
            rows.append({**{k: c[k] for k in ("name", "verified")},
                         "agreement": round(sem, 3), "character": round(chr_, 3),
                         "shared_cases": n})
        print(f"{'candidate':<16}{'verified':>10}{'agreement':>11}{'character α':>13}")
        for r in rows:
            print(f"{r['name']:<16}{r['verified']:>10.3f}{r['agreement']:>11.3f}"
                  f"{r['character']:>13.3f}")

        # THE ORDERING TEST, over pairs whose VERIFIED scores differ. A pair that
        # ties on quality has no ordering to reproduce, and S2a already published
        # a passing row built on one case of difference [ran] — struck, not deleted.
        pairs, right = 0, 0
        inversions = []
        for a, b in itertools.combinations(rows, 2):
            if a["verified"] == b["verified"]:
                continue
            pairs += 1
            better = a if a["verified"] > b["verified"] else b
            worse = b if better is a else a
            if better["agreement"] > worse["agreement"]:
                right += 1
            else:
                inversions.append(f"{better['name']} ({better['verified']:.2f} "
                                  f"verified, {better['agreement']:.2f} agreement) "
                                  f"ranked at or below {worse['name']} "
                                  f"({worse['verified']:.2f}, {worse['agreement']:.2f})")
        # AND THE VOIDING CONDITION, checked rather than assumed: if agreement just
        # equals verified accuracy, the fallible target did not separate anything
        # and this arm has collapsed into the tautology it was bought to avoid.
        collapsed = all(abs(r["agreement"] - r["verified"]) < 1e-9 for r in rows)
        print(f"ordering: {right}/{pairs} discriminable pairs")
        for inv in inversions:
            print(f"  INVERTED: {inv}")
        if pairs < 3:
            print("  VOID — fewer than three discriminable pairs, as pre-registered")
        if collapsed:
            print("  VOID — agreement equals verified accuracy exactly: this target "
                  "separated nothing and the arm is the tautology again")
        if decisive:
            print("  ^ this is the arm the verdict is read from")
        report[label] = {"rows": rows, "pairs": pairs, "right": right,
                         "inversions": inversions, "collapsed": collapsed,
                         "decisive": decisive}

    (P23 / "ranking.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
