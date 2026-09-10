# P12 (F1) — a domain corpus that states the formula and produces no value

**The problem this targets, measured.** P9's composition delegated on **5 of 30**
cases while the kernel alone delegates on all 30, and it passed **3 of those 5**
against **1 of the other 25** **[ran]**. The mechanism is intact; it rarely fires.
At every step two taught behaviours compete — the kernel's *"write a call"* and
the domain's *"write the number here"* — and the domain wins.

**The fix, and why it is the architecture's own.** `ARCHITECTURE.md` §4 gives the
expert *what is true* and leaves *how to act* to the kernel. It never asked the
expert for the number. The inline corpus gave it both, which is what the two
deltas had to fight over. `--style formula` rewrites each step so it stands on its
own numbers and stops before any value:

    3. Resultant force F = rho g h_c A: 880.0 * 9.80665 * (2.58 + 1.32/2) * (0.7 * 1.32)

600 of 600 chains kept, balanced across all six families, and every final formula
reaches the oracle's answer within 2% **[ran]**.

**The metric that decides it is delegation, not accuracy.** P9 plain: **0.6**
calls per case composed, against **7.7** for the kernel alone. Accuracy moved by
three cases and could move by three again for reasons unrelated to the mechanism;
calls per case is what this corpus is built to change.

**Falsification, written before the run.** If the composition's calls per case
does not rise materially toward the kernel's, then removing the value from the
expert's corpus was not what suppressed delegation, and the competition is not
about what the expert was taught to produce.

**A cost that must be reported, not hidden.** The domain adapter alone can no
longer answer: its corpus ends at a formula and never writes `{"answer": ...}`.
Its raw score will be near zero **by construction**, and the gate reads the
repaired score, which is the number that says whether its physics survived.
