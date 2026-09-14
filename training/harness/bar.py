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
