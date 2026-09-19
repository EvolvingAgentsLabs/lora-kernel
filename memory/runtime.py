r"""The runtime — the software referee. Three verbs, ids, budgets, the walk log — docs/MEMORY.md §3, §5.

Pure Python, no model. It is an *answer function with state per conversation* for the corpus-mode
loop the pool already runs (`training/harness/accept_rank.py::run_chain`, unchanged): generation
stops at a closing tag, the result is written inline as `= result`, generation continues.

    <search shelf=harness>situation</search>= 3 notes
      [k3f] procedure · Primary IV solution administration — when: a provider orders IV fluids
    <open>k3f</open>= Primary IV solution administration — 32 steps. First step: a01 …
      next a01
    <calc>500 * 20 / (4 * 60)</calc>= 41.6667

WHAT THE EXPERT CAN NEVER SEE: a library id. Ids shown are three opaque characters, **re-drawn per
conversation**, and the map lives here. An id exists in a conversation only once a result has shown
it — so `<open>` on anything else is `ERROR: no note … in this conversation`, and navigation by
rote is impossible by construction rather than by training.

WHAT HAPPENS BEFORE A NOTE IS SHOWN: its slots are resolved case → site → textbook
(`memory/layers.py`) and the guard has agreed (`memory/guard.py`). The model reads the rule already
resolved.

SEARCH IN W2 IS LEXICAL **[spec]**. The radar is W3. `Lexical` scores §2.3's formula with token
overlap standing in for the inner product,

    s(n | q) = overlap(q, when(n)) + beta * overlap(q, what(n)),   top k = 3,

behind `Searcher` — the one method W3's index implements. §2.3 keeps lexical search as a reported
baseline whatever the radar does, so this class outlives W2.

ERRORS ARE OBSERVATIONS, AND THEY ARE COUNTED. Nothing here swallows an exception: a bad call
becomes an `ERROR:` line the expert reads and an entry in `errors`; a bug raises.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Protocol

from memory.guard import Guard
from memory.layers import render, resolve, shown_slots
from memory.notes import Library, Note, Site, count_tokens

VERBS = ("search", "open", "calc")
GRAMMAR = "verbs-en-1"                       # frozen with a release (§3, §8)
# One group for the verb, one for everything up to the closing tag — the two groups `run_chain`
# reads. The second holds ` shelf=harness>query` or `>query`; `split_call` takes it apart.
TAG = re.compile(r"<(search|open|calc)((?: shelf=[a-z]+)?>[^<]*)</\1>")
K = 3
# §3 said 24 opens. The first library's longest procedure is 32 steps, and a cap below the corpus's
# own depth scores the cap (the fluids suite paid for that: `suites.Suite.max_calls`). 48 [spec] W2.
MAX_OPENS, MAX_SEARCHES = 48, 12
_ALPHABET = "abcdefghijkmnpqrstuvwxyz0123456789"      # no l, no o: they read as 1 and 0
_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("a an the of to for and or is are in on at by you your be it its this that with as "
                  "have has must about".split())


class Searcher(Protocol):
    def search(self, query: str, shelf: str | None, k: int) -> list[str]: ...


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


@dataclass
class Lexical:
    """The W2 searcher and W3's baseline: token overlap on `when`, plus beta on `what`."""
    lib: Library
    beta: float = 0.5

    def search(self, query: str, shelf: str | None = None, k: int = K) -> list[str]:
        q = _words(query)
        scored = []
        for n in self.lib.notes.values():
            if shelf and n.shelf != shelf:
                continue
            s = len(q & _words(n.when)) + self.beta * len(q & _words(n.what))
            if s > 0:
                scored.append((-s, n.id))
        return [i for _, i in sorted(scored)[:k]]


def split_call(raw: str) -> tuple[str | None, str]:
    """` shelf=wiki>drip rate` → ("wiki", "drip rate");  `>k3f` → (None, "k3f")."""
    head, _, body = raw.partition(">")
    shelf = head.strip().removeprefix("shelf=") or None
    return shelf, body.strip()


@dataclass
class Conversation:
    """One task's state: the id map, what has been opened, the budgets, the log."""
    lib: Library
    site: Site | None = None
    case: dict | None = None              # note id → {slot: value}; training and evaluation only
    mode: str = "strict"
    seed: int = 0
    searcher: Searcher | None = None
    max_opens: int = MAX_OPENS
    max_searches: int = MAX_SEARCHES
    log_content: bool = False             # §5.4: shapes by default, content is a setting

    shown: dict[str, str] = field(default_factory=dict)      # opaque → library id
    opaque: dict[str, str] = field(default_factory=dict)     # library id → opaque
    opened: list[str] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)
    ended: str | None = None              # why the walk is *not answered*, if it is
    searches: int = 0

    def __post_init__(self):
        self.guard = Guard(self.mode)
        self.searcher = self.searcher or Lexical(self.lib)
        self._rng = random.Random(self.seed)

    # ---- ids -------------------------------------------------------------------------------
    def _id(self, note_id: str) -> str:
        if note_id not in self.opaque:
            while True:
                o = "".join(self._rng.choice(_ALPHABET) for _ in range(3))
                if o not in self.shown:
                    break
            self.opaque[note_id], self.shown[o] = o, note_id
        return self.opaque[note_id]

    # ---- a walk carried over from an earlier turn ------------------------------------------
    def resume(self, done: list[str]) -> str:
        """Carry a walk over: `done` were opened before this conversation, in that order.

        A WINDOW ENTERED IN THE MIDDLE NEEDS WHAT `strict` NEEDS — the steps already done — and an
        id to go on from, which exists only once a result has shown it. So the referee resumes from
        its own record (§5.4): the steps count as opened, and the LAST PAGE is rendered again, ids
        re-drawn for this conversation, to stand in the turn that continues the walk. Returned
        exactly as the loop would have written it, `<open>id</open>= page`, so a corpus that shows a
        carried page calls this and imitates nothing **[spec]** W4. Nothing is carried: `""`.
        """
        if self.opened or self.log:
            raise RuntimeError("resume() starts a conversation; this one has already begun")
        for i in done:
            self.lib[i]                                    # a record naming no note is a bug: raise
        self.opened = list(done)
        if not done:
            return ""
        last = self.lib[done[-1]]
        page = self._render(last, (self.case or {}).get(last.id))
        self._log("resume", "", note=last.id, guard="ok", carried=len(done), tokens=count_tokens(page))
        return f"<open>{self._id(last.id)}</open>= {page}"

    # ---- the verbs -------------------------------------------------------------------------
    def answer(self, verb: str, raw: str) -> str:
        """The text written after `= `. Never raises for something the expert did."""
        if self.ended:
            return self._error("ended", f"this task has ended ({self.ended})", verb)
        shelf, arg = split_call(raw)
        if verb == "search":
            return self._search(arg, shelf)
        if verb == "open":
            return self._open(arg)
        if verb == "calc":
            return self._calc(arg)
        return self._error("verb", f"no verb `{verb}` — the verbs are {', '.join(VERBS)}", verb)

    def _search(self, query: str, shelf: str | None) -> str:
        if shelf and shelf not in ("harness", "wiki"):
            return self._error("shelf", f"no shelf `{shelf}` — harness or wiki", "search")
        if not query:
            return self._error("empty", "an empty search", "search")
        if self.searches >= self.max_searches:
            return self._end("search budget", "search")
        self.searches += 1
        ids = self.searcher.search(query, shelf, K)
        lines = [f"{len(ids)} note{'s' if len(ids) != 1 else ''}"]
        for i in ids:
            n = self.lib[i]
            lines.append(f"  [{self._id(i)}] {n.kind} · {n.title} — when: {n.when}")
        self._log("search", query, shelf=shelf, returned=ids, guard="ok")
        return "\n".join(lines)

    def _open(self, shown: str) -> str:
        shown = shown.strip("[] ")
        if shown not in self.shown:
            self.guard.unknown_id(shown)
            return self._violation(f"no note {shown} in this conversation", "unknown_id", shown)
        note = self.lib[self.shown[shown]]
        v = self.guard.check_open(note, set(self.opened))
        if not v.ok:
            first = " ".join(self._id(m) for m in v.missing)
            return self._violation(f"requires {first} first", "requires", shown, note=note.id)
        if len(self.opened) >= self.max_opens:
            return self._end("open budget", "open")
        self.opened.append(note.id)
        case = (self.case or {}).get(note.id)
        text = self._render(note, case)
        self._log("open", shown, note=note.id, guard="ok", tokens=count_tokens(text),
                  slots={k: [val, layer] for k, (val, layer) in resolve(note, self.site, case).items()
                         if k in shown_slots(note, self.site)})
        return text

    def _render(self, note: Note, case: dict | None) -> str:
        body = render(note, self.site, case)
        if note.kind == "procedure":
            head = f"{note.title} — {len(note.steps)} steps. First step: {self._id(note.first)}"
            lines = [head, *body.splitlines(), f"  next {self._id(note.first)}"]
            return "\n".join(lines)
        lines = body.splitlines() or [""]
        if note.next:
            lines.append(f"  next {self._id(note.next)}")
        for label, ids in (("requires", note.requires), ("uses", note.uses),
                           ("parent", [note.parent] if note.parent else []), ("children", note.children)):
            if ids:
                lines.append(f"  {label} " + " · ".join(f"[{self._id(i)}] {self.lib[i].title}" for i in ids))
        return "\n".join(lines)

    def _calc(self, expr: str) -> str:
        from training.physics.calc import CalcError, evaluate
        try:
            value = evaluate(expr)
        except CalcError as e:
            return self._error("calc", str(e), "calc")
        self._log("calc", expr, guard="ok")
        return f"{value:.6g}"

    # ---- errors, violations, endings -------------------------------------------------------
    def _error(self, kind: str, message: str, verb: str) -> str:
        self.errors[kind] = self.errors.get(kind, 0) + 1
        self._log(verb, "", guard="ok", error=kind)
        return f"ERROR: {message}"

    def _violation(self, message: str, kind: str, shown: str, note: str | None = None) -> str:
        self.errors[kind] = self.errors.get(kind, 0) + 1
        if self.guard.cuts:
            self.ended = f"guard: {kind}"
        self._log("open", shown, note=note, guard=kind, cut=self.guard.cuts)
        return f"ERROR: {message}"

    def _end(self, why: str, verb: str) -> str:
        self.errors["budget"] = self.errors.get("budget", 0) + 1
        self.ended = why
        self._log(verb, "", guard="ok", error="budget")
        return f"ERROR: {why} reached — this task is not answered"

    def _log(self, verb: str, arg: str, **more) -> None:
        line = {"n": len(self.log), "verb": verb, "arg_tokens": count_tokens(arg), **more}
        if self.log_content:
            line["arg"] = arg
        self.log.append(line)

    def log_lines(self) -> str:
        """§5.4: one JSON line per command."""
        return "\n".join(json.dumps(l, ensure_ascii=False) for l in self.log)

    @property
    def answered(self) -> bool:
        return self.ended is None


class ChainSuite:
    """What `run_chain(gen, inbox, max_calls, suite)` reads off a suite — for one conversation.

    `run_chain` counts a call as *refused* when the tool raises `ToolError`, and writes the message
    inline as `= ERROR: …` itself; so an `ERROR:` answer is raised here rather than returned, and
    the loop's own counter agrees with `Conversation.errors`.
    """
    close = tuple(f"</{v}>" for v in VERBS)
    tag = TAG
    positional: dict = {}

    def __init__(self, conv: Conversation):
        self.conv = conv

    def answer(self, _inbox, verb: str, raw: str) -> str:
        from training.email.tools import ToolError
        res = self.conv.answer(verb, raw)
        if res.startswith("ERROR: "):
            raise ToolError(res[len("ERROR: "):])
        return res

    def parse(self, text: str):
        """The final span is the answer — unless the referee ended the task: then *not answered*."""
        return text.strip() if self.conv.answered and text.strip() else None

    def wrap(self, gen):
        """A cut walk generates nothing more: the loop sees an empty, tag-less chunk and stops."""
        return lambda prefix: "" if self.conv.ended else gen(prefix)
