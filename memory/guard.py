"""The conformance guard — docs/MEMORY.md §5.3.

A harness note says `requires: [a, b]`. Opening it while `a` or `b` has never been opened in this
conversation is a violation, and the guard says so **without knowing whether the final answer was
right**: it consults no answer key and the training loop never sees it, which is what any signal
used to accept or reject an answer has to be (precedent: dimensional analysis on a physics chain,
**[ran]** P22).

    violation(n | opened) = { r in requires(n) : r not in opened }  is non-empty

Because every step of a procedure requires the step before it (W1's library), *a step out of order*
is the same violation and needs no second rule. An id the conversation never returned is the
runtime's to refuse (it holds the id map); it reports it here so both kinds are counted in one place.

Two modes **[spec]**: `strict` — the default in 1.0 — the first violation ends the walk as *not
answered*; `recover` — the violation is written inline and the expert may go back. Whether small
experts do recover is an arm, not an assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MODES = ("strict", "recover")


@dataclass
class Verdict:
    ok: bool
    kind: str | None = None                 # "requires" | "unknown_id"
    missing: list[str] = field(default_factory=list)   # library ids — for the log, never shown


@dataclass
class Guard:
    mode: str = "strict"
    violations: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"guard mode `{self.mode}` is not one of {MODES}")

    def check_open(self, note, opened: set[str]) -> Verdict:
        missing = [r for r in note.requires if r not in opened]
        if not missing:
            return Verdict(True)
        return self._record(Verdict(False, "requires", missing), note.id)

    def unknown_id(self, shown: str) -> Verdict:
        return self._record(Verdict(False, "unknown_id"), shown)

    def _record(self, v: Verdict, what: str) -> Verdict:
        self.violations.append({"kind": v.kind, "at": what, "missing": v.missing})
        return v

    @property
    def cuts(self) -> bool:
        """Does a violation end the walk?"""
        return self.mode == "strict"
