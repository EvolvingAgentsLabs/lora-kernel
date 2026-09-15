"""Beating a bar by one case is not beating it, and the arithmetic says so.

WHAT THIS EXISTS TO STOP. P31's gate was written as "the base can do the job if it
beats 0.680 on the human messages". A model that is **exactly at the bar** — that
is, guessing the majority class and nothing more — clears that rule **45% of the
time** on any suite size, because the rule's whole margin is one case
**[ran]** 2026-09-14. The gate would have authorised a day of training on a coin
flip, and raising `n` does not touch it: the threshold is what is wrong, not the
sample.

AND THE OTHER DIRECTION IS WORSE AT SMALL n. With a correct threshold, a suite of
30 messages carries 24 human ones, and a model genuinely using the tools at 0.80
clears it only **26%** of the time. The arm built to kill the phase would have
reported "the base cannot do this" in three runs out of four where it can:

        n     human      bar     pass at    detect 0.80    false alarm
       30        24    0.667       21/24            26%             2%
      100        77    0.701       61/77            63%             5%
      150       113    0.655      83/113            96%             4%

**[ran]** 2026-09-14, exact binomial, 20 000 draws per cell. 150 is where both
errors land near 4%, and that is the size P31 is bought at.

THE TEST IS EXACT, NOT NORMAL. At these counts the normal approximation moves the
threshold by whole cases, and a decision that turns on one case should not also
turn on which approximation was in fashion.
"""

from __future__ import annotations

import math


def sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def threshold(n: int, bar: float, alpha: float = 0.05) -> int:
    """The smallest number of correct cases that is not explainable by the bar."""
    for k in range(n + 1):
        if sf(k, n, bar) <= alpha:
            return k
    return n + 1


def verdict(correct: int, n: int, bar: float, alpha: float = 0.05) -> dict:
    """Decided, not eyeballed. Two numbers side by side invite reading the wrong one."""
    if n == 0:
        return {"decided": False, "why": "no cases were scored"}
    k = threshold(n, bar, alpha)
    p = sf(correct, n, bar)
    return {
        "n": n, "correct": correct, "accuracy": round(correct / n, 4),
        "bar": round(bar, 4), "passes_at": k, "alpha": alpha,
        "p_value": round(p, 5),
        "beats_the_bar": correct >= k,
        # A RUN THAT MERELY EXCEEDS THE BAR IS NOT A RESULT, and saying so in the
        # output is what stops the number being quoted as one later.
        "exceeds_bar_without_clearing_the_gate":
            bool(correct / n > bar and correct < k),
    }


def power(n: int, bar: float, p_true: float, alpha: float = 0.05) -> float:
    """P(a run of n cases clears the gate) when the true accuracy is `p_true`.

    Exact, so the number that sizes the suite does not come from a simulation whose
    seed nobody recorded.
    """
    return sf(threshold(n, bar, alpha), n, p_true)


# ---------------------------------------------------------------------------
# COMPARING TWO ARMS ON THE SAME CASES IS NOT COMPARING TWO BARS.
#
# Every arm in this repository runs the same fixture set, so the cases are
# PAIRED and the only information about a difference lives in the cases where
# the two arms disagree. Reading `10/30 against 7/30` as a win throws that away:
# those two numbers hide **three** disagreements, and three coin flips landing
# the same way is a p of 0.25.
#
# This was not hypothetical. P15's headline read "a learned protocol beats a
# hand-written rule ... 94.8% against 91.7%, 10/30 against 7/30. That reverses
# P13's verdict and locates it." Both metrics are ties — 3:0 and 4:1, p=0.250
# and p=0.375 **[ran]** 2026-09-14. The direction was consistent and the claim
# was not measured.
# ---------------------------------------------------------------------------

def sign_test(a_better: int, b_better: int) -> float:
    """Exact two-sided p for `a` and `b` differing, given only the disagreements.

    Ties between the arms carry no information about which is better and are
    correctly excluded — that is what makes this the paired test and not a
    comparison of two independent proportions.
    """
    n = a_better + b_better
    if n == 0:
        return 1.0
    return min(1.0, 2 * sf(max(a_better, b_better), n, 0.5))


def compare(a: dict, b: dict, alpha: float = 0.05) -> dict:
    """Two arms as {case_id: passed}. Decided on the cases where they disagree."""
    ids = sorted(set(a) & set(b))
    only_a = sum(bool(a[i]) and not b[i] for i in ids)
    only_b = sum(bool(b[i]) and not a[i] for i in ids)
    p = sign_test(only_a, only_b)
    return {
        "n_paired": len(ids),
        "a_total": sum(bool(a[i]) for i in ids),
        "b_total": sum(bool(b[i]) for i in ids),
        "only_a": only_a, "only_b": only_b,
        "discordant": only_a + only_b,
        "p_value": round(p, 5),
        "different": p <= alpha,
        # THE SENTENCE THAT SHOULD BE WRITTEN WHEN IT IS NOT DIFFERENT.
        "reading": ("the arms differ" if p <= alpha else
                    "a tie: the totals differ but the cases behind them do not"),
    }


def resolvable(n: int, baseline: float, effect: float = 0.05,
               alpha: float = 0.05, want: float = 0.80) -> dict:
    """Can a run of `n` cases tell an `effect`-sized improvement from nothing?

    HEADROOM IS A QUESTION ABOUT POWER, NOT ABOUT MARGIN, and P42 is what taught
    that. Its rule was *cancel the arm if less than 0.10 of accuracy is left above
    the baseline*. The base scored **0.815** on ARC, 0.185 was left, so the arm was
    **bought** — and at n=200 over a 0.815 baseline the power to see a +0.05 adapter
    is **55%**, and to see the +0.01 that actually appeared, **8%**. The arm was
    unresolvable before it was purchased **[ran]** 2026-09-15.

    Margin is the wrong quantity because the same margin buys very different
    resolution depending on where the baseline sits: near 0.5 the variance is
    largest and near 1.0 it collapses. Power asks the question the buyer has.
    """
    k = threshold(n, baseline, alpha)
    got = sf(k, n, min(baseline + effect, 1.0))
    return {"n": n, "baseline": round(baseline, 4), "effect": effect,
            "passes_at": k, "power": round(got, 4), "want": want,
            "resolvable": got >= want,
            "why": (f"a +{effect:g} improvement would be seen {got:.0%} of the time; "
                    f"buy the arm only above {want:.0%}")}


def n_for(baseline: float, effect: float = 0.05, alpha: float = 0.05,
          want: float = 0.80, cap: int = 5000) -> int | None:
    """The smallest suite that could resolve `effect`. `None` if `cap` cannot."""
    n = 10
    while n <= cap:
        if resolvable(n, baseline, effect, alpha, want)["resolvable"]:
            return n
        n = int(n * 1.3) + 1
    return None


# ---------------------------------------------------------------------------
# CALIBRATION — is a confidence worth reading?
#
# The gate vocabulary above answers *is this better than guessing*. These answer
# *can a caller trust the number the model attaches to its own answer*, which is a
# different question and the one a router needs: P41 measured per-case escalation
# delivering LESS than routing by region, because the only signal that separated a
# right local answer from a wrong one was agreement with the frontier — and that
# costs a frontier call **[ran]**.
#
# A confidence is useful when three things hold, and they are not the same thing:
#   ECE   the number means what it says       (0.8 happens 80% of the time)
#   Brier the number is sharp as well as true (always saying 0.5 is calibrated
#                                              and useless)
#   AURC  the number ORDERS the errors        (the only one a router uses)
#
# **AURC is the one to read first.** A router does not need a calibrated number, it
# needs the wrong answers to sit at the bottom of the ranking. A model can be badly
# calibrated and perfectly rankable, and that model routes fine.
# ---------------------------------------------------------------------------

def ece(probs: list[float], correct: list[bool], bins: int = 10) -> float:
    """Expected calibration error: |confidence − accuracy|, averaged over bins.

    Equal-width bins, weighted by occupancy. Empty bins contribute nothing rather
    than counting as perfect, which is how a sparse histogram flatters itself.
    """
    if not probs:
        return 0.0
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs)
               if (p > lo or (b == 0 and p >= 0)) and p <= hi]
        if not idx:
            continue
        conf = sum(probs[i] for i in idx) / len(idx)
        acc = sum(bool(correct[i]) for i in idx) / len(idx)
        total += (len(idx) / len(probs)) * abs(conf - acc)
    return total


def brier(probs: list[float], correct: list[bool]) -> float:
    """Mean squared error of the probability. Rewards being right AND sharp."""
    if not probs:
        return 0.0
    return sum((p - float(bool(c))) ** 2 for p, c in zip(probs, correct)) / len(probs)


def aurc(probs: list[float], correct: list[bool]) -> float:
    """Area under the risk–coverage curve: does the confidence ORDER the errors?

    Sort by confidence descending; at each coverage, the risk is the error rate of
    what has been accepted so far. Lower is better, and **this is the number a
    router reads**: it says nothing about whether 0.8 means 0.8, only about whether
    the wrong answers are at the bottom.

    TIES ARE AVERAGED, NOT RESOLVED BY POSITION. `sorted` is stable, so equal
    confidences would break by their index — and the first check written for this
    function reported a model that always says 0.9 as having a **perfect** ordering,
    purely because the correct cases came first in the list. Reordering the same
    data moved the answer from 0.094 to 0.766 **[ran]** 2026-09-15. A measurement
    whose answer depends on case order is the same failure as one that depends on
    the scheduler, in a new costume. Within a tied group the risk is the
    expectation over random orderings, which is exact and costs nothing.
    """
    if not probs:
        return 0.0
    order = sorted(range(len(probs)), key=lambda i: -probs[i])
    total = 0.0
    wrong = 0.0
    k = 0
    i = 0
    while i < len(order):
        j = i
        while j < len(order) and probs[order[j]] == probs[order[i]]:
            j += 1
        group = order[i:j]
        rate = sum(not bool(correct[x]) for x in group) / len(group)
        for _ in group:
            k += 1
            wrong += rate
            total += wrong / k
        i = j
    return total / len(order)


def aurc_floor(correct: list[bool]) -> float:
    """The AURC an ORACLE ranking would reach — the best any confidence can do.

    WHY THIS EXISTS. An AURC is unreadable alone: on an easy suite a useless
    confidence still scores well, and on a hard one a good confidence scores badly.
    The floor is what a perfect ordering gets on THIS suite, and the gap between a
    model's AURC and the floor is the part that is about the model.
    """
    return aurc([1.0 if c else 0.0 for c in correct], correct)


def calibration(probs: list[float], correct: list[bool], bins: int = 10) -> dict:
    """All three, with the floor beside the AURC so it can be read at all."""
    floor = aurc_floor(correct)
    got = aurc(probs, correct)
    return {"n": len(probs),
            "accuracy": round(sum(map(bool, correct)) / max(len(correct), 1), 4),
            "mean_confidence": round(sum(probs) / max(len(probs), 1), 4),
            "ece": round(ece(probs, correct, bins), 4),
            "brier": round(brier(probs, correct), 4),
            "aurc": round(got, 4),
            "aurc_oracle_floor": round(floor, 4),
            "aurc_gap": round(got - floor, 4)}
