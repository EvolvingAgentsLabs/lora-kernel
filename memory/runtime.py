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

PAGES OF ATOMIC STATEMENTS (§1.6, W9 **[spec]**). `<open>id</open>` on a page shows its title, its
`what:` and its SECTIONS — anchors only, never a statement's text, like Wikipedia's contents: which
section answers the task is the expert's choice. `<open>id§anchor</open>` shows that one statement,
slots filled, each `[[link]]` written `[p7q] Title` so it can be opened. Opened statements are kept
in `statements`, which is what a citation `[id§anchor]` is checked against.

    <open>k3f</open>= Brisk-40 pallet wrap — A stretch film for pallets.
      sections §supplier · §warehouse · §pack
    <open>k3f§supplier</open>= Brisk-40 is supplied by [q7m] Norvale Supplies.

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
from memory.notes import LINK, Library, Note, Site, count_tokens, statements_of

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


@dataclass
class FullText:
    r"""Full-text search: Okapi BM25 over a note's statements (its body), plus a flat bonus per query word in its
    `when`/`what`. Standard parameters, $k_1 = 1.2$, $b = 0.75$, never tuned on a question set.

    WHY (REAL0 [ran]): an ingested real page's `when`/`what` is its section title, and a person's question shares few
    words with a regulation's title — `Lexical` found the page a walk starts on for 5 of 36 questions, the supporting
    page for 10. The words are in the statements: BM25 over them finds the start 34/36 and the support 32/36 (k = 3).
    Deterministic: ties break on the note id.

    $$\mathrm{score}(n\mid q)=\sum_{w\in q} \mathrm{idf}(w)\,\frac{f_{w,n}(k_1+1)}{f_{w,n}+k_1\,(1-b+b\,|n|/\overline{|n|})}
      + 2\,\bigl|q\cap(\mathrm{when}\cup\mathrm{what})\bigr|,\qquad \mathrm{idf}(w)=\ln\!\Bigl(1+\frac{N-\mathrm{df}_w+0.5}{\mathrm{df}_w+0.5}\Bigr)$$
    """
    lib: Library
    k1: float = 1.2
    b: float = 0.75

    def __post_init__(self):
        from collections import Counter
        self._head = {i: _words(n.when) | _words(n.what) for i, n in self.lib.notes.items()}
        self._body = {i: Counter(w for st in statements_of(n.body)[0] for w in _words(st.text)) if n.is_page
                      else Counter(_words(n.body)) for i, n in self.lib.notes.items()}
        self._len = {i: sum(c.values()) or 1 for i, c in self._body.items()}
        self._avg = sum(self._len.values()) / max(1, len(self._len))
        self._df = Counter(w for i in self._body for w in set(self._body[i]) | self._head[i])

    def search(self, query: str, shelf: str | None = None, k: int = K) -> list[str]:
        import math
        q, n_docs, scored = _words(query), len(self._body), []
        for i, note in self.lib.notes.items():
            if shelf and note.shelf != shelf:
                continue
            f, norm = self._body[i], self.k1 * (1 - self.b + self.b * self._len[i] / self._avg)
            s = sum(math.log(1 + (n_docs - self._df[w] + 0.5) / (self._df[w] + 0.5)) * f[w] * (self.k1 + 1) / (f[w] + norm)
                    for w in q if f[w]) + 2.0 * len(q & self._head[i])
            if s > 0:
                scored.append((-s, i))
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
    # THE REFEREE MAY WRITE THE FIRST QUERY. Set, the conversation's first `<search>` runs on this text
    # (the request's own statement) on the shelf the expert named, and the expert's words are logged,
    # not searched. W5d [ran]: on a new wording the adapter wrote a training query for another topic in
    # 9 of 11 misses, where the statement lists the needed note 16 of 16. None: the expert's query, as
    # trained. One unknown, measured in results/M7-W5e-first-search-20260923.
    first_query: str | None = None
    # THE ENTRY IS THE QUESTION'S, ON EVERY SHELF (REAL0 [ran]): on a library it was not trained on, a trajectory
    # member searched the harness shelf with a query memorised from its generated world in 40 of 40 walks, found nothing
    # and never opened a page. `entry_all_shelves` runs `first_query` on every shelf, whatever shelf the model named.
    entry_all_shelves: bool = False
    # AN EMPTY SEARCH SAYS WHERE ELSE TO LOOK. `fallback`: a search on a named shelf that finds nothing is run on every
    # shelf, and the result says so — "0 notes on harness; on every shelf:" — instead of a bare "0 notes".
    fallback: bool = False
    # A PAGE OPENS WITH ITS STATEMENTS' TEXT (REAL2). On a real document the anchors are the paragraphs' own labels —
    # `§a-2`, `§h` — and a contents list of labels gives the model nothing to choose by: with the entry fixed, walks reached
    # the supporting page 17/25 and opened the supporting statement 2–6/25 [ran] REAL1. `page_text` renders every
    # statement under its anchor (links as `[id] Title`); each counts as read for the citation, not against the budget.
    page_text: bool = False
    # A LONG PAGE OPENS WITH THE STATEMENTS THE QUESTION NAMES (LIVE-library [ran]): 29 CFR 1910.178 reads ~6,900 tokens
    # whole, and on the Mac's 12,288-token context 4 of 52 walks overflowed after opening it. With `page_budget` a page
    # whose text exceeds it shows its statements in BM25 order against `first_query` (the question) until the budget,
    # in document order, then the anchors left out — each still openable as `id§anchor`. Only the shown ones count as
    # read. Offline [ran]: at 1,500–3,500 the 8 statements REAL4's walks need on that page are all kept.
    page_budget: int | None = None
    # THE CITATION IS CHECKED BEFORE THE ANSWER LEAVES (LIVE-library2 [ran], offline over its 52 walks): of 15 misses, 9
    # end on a line the referee can reject without knowing the answer — no `[id§section]`, an id never shown, a statement
    # never opened, or a number the cited statement does not hold — and of 37 right answers, none does. With
    # `cite_check`, such a final line is answered once with `= ERROR: citation — …` and the walk goes on; a second final
    # line stands as it is. It cannot catch a statement that holds the number but is not the one asked about.
    cite_check: bool = False
    cite_checks: int = 0
    checked: dict | None = None
    implicit: int = 0

    shown: dict[str, str] = field(default_factory=dict)      # opaque → library id
    opaque: dict[str, str] = field(default_factory=dict)     # library id → opaque
    opened: list[str] = field(default_factory=list)
    statements: list[tuple[str, str]] = field(default_factory=list)   # (library id, anchor), in order
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
        written = None
        if self.first_query is not None and self.searches == 0:
            written, query = query, self.first_query
            if self.entry_all_shelves:
                shelf = None
        if not query:
            return self._error("empty", "an empty search", "search")
        if self.searches >= self.max_searches:
            return self._end("search budget", "search")
        self.searches += 1
        ids = self.searcher.search(query, shelf, K)
        head = None
        if not ids and shelf and self.fallback:
            ids = self.searcher.search(query, None, K)
            head = f"0 notes on {shelf}; on every shelf, {len(ids)} note{'s' if len(ids) != 1 else ''}"
        lines = [head or f"{len(ids)} note{'s' if len(ids) != 1 else ''}"]
        for i in ids:
            n = self.lib[i]
            lines.append(f"  [{self._id(i)}] {n.kind} · {n.title} — when: {n.when}")
        more = {} if written is None else {"substituted": True, "written": written if self.log_content else None}
        self._log("search", query, shelf=shelf, returned=ids, guard="ok", **more)
        return "\n".join(lines)

    def _open(self, shown: str) -> str:
        shown = shown.strip("[] ")
        shown, section, anchor = shown.partition("§")
        if section:
            return self._open_statement(shown.strip(), anchor.strip())
        if shown not in self.shown:
            self.guard.unknown_id(shown)
            return self._violation(f"no note {shown} in this conversation", "unknown_id", shown)
        note = self.lib[self.shown[shown]]
        v = self.guard.check_open(note, set(self.opened))
        if not v.ok:
            first = " ".join(self._id(m) for m in v.missing)
            return self._violation(f"requires {first} first", "requires", shown, note=note.id)
        if len(self.opened) + len(self.statements) - self.implicit >= self.max_opens:
            return self._end("open budget", "open")
        self.opened.append(note.id)
        case = (self.case or {}).get(note.id)
        text = self._render(note, case)
        if self.page_text and note.is_page:
            shown_here = self._page_selection(note)
            for st in note.statements:
                if st.anchor in shown_here and (note.id, st.anchor) not in self.statements:
                    self.statements.append((note.id, st.anchor)); self.implicit += 1
        self._log("open", shown, note=note.id, guard="ok", tokens=count_tokens(text),
                  slots={k: [val, layer] for k, (val, layer) in resolve(note, self.site, case).items()
                         if k in shown_slots(note, self.site)})
        return text

    def _open_statement(self, shown: str, anchor: str) -> str:
        """§1.6: one statement of a page. A wrong section is an observation, not a violation."""
        if shown not in self.shown:
            self.guard.unknown_id(shown)
            return self._violation(f"no note {shown} in this conversation", "unknown_id", shown)
        note = self.lib[self.shown[shown]]
        if not note.is_page:
            return self._error("section", f"{shown} is not a page of sections — open it whole", "open")
        text = self._statement_text(note, anchor)
        if text is None:
            return self._error("section", f"no section §{anchor} on {shown}", "open")
        if len(self.opened) + len(self.statements) - self.implicit >= self.max_opens:
            return self._end("open budget", "open")
        self.statements.append((note.id, anchor))
        self._log("open", f"{shown}§{anchor}", note=note.id, anchor=anchor, guard="ok", tokens=count_tokens(text))
        return text

    def _statement_text(self, note: Note, anchor: str) -> str | None:
        """The statement as the expert reads it — slots filled, links as openable ids — or None."""
        body = render(note, self.site, (self.case or {}).get(note.id))
        st = next((x for x in statements_of(body)[0] if x.anchor == anchor), None)
        if st is None:
            return None
        return LINK.sub(lambda m: f"[{self._id(m.group(1))}] {self.lib[m.group(1)].title}", st.text)

    def _page_selection(self, note: Note) -> set[str]:
        """The anchors a page opens with: all of them, or — over `page_budget` — the question's best by BM25 within the page,
        $k_1 = 1.2$, $b = 0.75$ as `FullText`, taken in score order while the statements and the list of the rest fit."""
        import math
        from collections import Counter
        lines = {st.anchor: f"  §{st.anchor} {self._statement_text(note, st.anchor)}" for st in note.statements}
        if not self.page_budget or count_tokens("\n".join(lines.values())) <= self.page_budget:
            return set(lines)
        docs = {a: Counter(_words(t)) for a, t in lines.items()}
        n, df = len(docs), Counter(w for d in docs.values() for w in d)
        avg = sum(sum(d.values()) for d in docs.values()) / n
        q = _words(self.first_query or "")

        def score(a):
            d = docs[a]; norm = 1.2 * (0.25 + 0.75 * sum(d.values()) / avg)
            return sum(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * d[w] * 2.2 / (d[w] + norm) for w in q if d[w])
        order = sorted(lines, key=lambda a: (-score(a), [st.anchor for st in note.statements].index(a)))
        keep, used = set(), sum(count_tokens(f" · §{a}") for a in lines) + 20       # the list of the rest, at most
        for a in order:
            if used + count_tokens(lines[a]) <= self.page_budget:
                keep.add(a); used += count_tokens(lines[a])
        return keep

    def _render(self, note: Note, case: dict | None) -> str:
        if note.is_page:
            if self.page_text:
                keep = self._page_selection(note)
                body = "\n".join(f"  §{st.anchor} {self._statement_text(note, st.anchor)}" for st in note.statements
                                 if st.anchor in keep)
                rest = [st.anchor for st in note.statements if st.anchor not in keep]
                more = (f"\n  {len(rest)} more sections, not shown — open {self._id(note.id)}§<section> to read one: "
                        + " · ".join(f"§{a}" for a in rest)) if rest else ""
                return f"{note.title} — {note.what}\n{body}{more}"
            anchors = " · ".join(f"§{st.anchor}" for st in note.statements)
            return f"{note.title} — {note.what}\n  sections {anchors}"
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

    def check_final(self, text: str) -> str | None:
        r"""`cite_check`: why a final line cannot be verified, or None. Without the answer key — the referee's own record:
        a line passes iff it is `Not in my library.`, or it cites $[o\S a]$ with $o$ shown, $(\mathrm{id}(o), a)$ opened,
        and $\mathrm{nums}(\text{line}) \subseteq \mathrm{nums}(\text{statement})$ (the citation's own label aside)."""
        if not self.cite_check or self.cite_checks >= 1 or self.ended:
            return None
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        line = lines[-1] if lines else ""
        if "not in my library" in line.lower():
            return None
        self.cite_checks += 1
        self.checked = {"line": line, "statements": list(self.statements)}      # what the line was, as the check saw it
        how = "end with one line: the answer and [id§section] of a statement you opened that holds it — or Not in my library."
        cites = list(_CITE.finditer(line))
        if not line:
            return f"citation — no answer line; {how}"
        if not cites:
            return f"citation — no [id§section] on the answer line; {how}"
        shown, anchor = cites[-1].group(1), cites[-1].group(2)
        if shown not in self.shown:
            return f"citation — {shown} was never shown in this conversation; {how}"
        nid = self.shown[shown]
        if (nid, anchor) not in self.statements:
            return f"citation — {shown}§{anchor} was not opened; {how}"
        text_ = self._statement_text(self.lib[nid], anchor) or ""
        nums = lambda t: {n.lstrip("0") or "0" for n in re.findall(r"\d+", t)}
        missing = sorted(nums(_CITE.sub(" ", line)) - nums(text_))
        if missing:
            return f"citation — {shown}§{anchor} does not hold {', '.join(missing)}; {how}"
        self.cite_checks -= 1                       # a line that passes has not used the one check
        self.checked = None
        return None

    @property
    def answered(self) -> bool:
        return self.ended is None


_CITE = re.compile(r"\[([a-z0-9]{3})§([a-z0-9][a-z0-9-]*)\]")


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

    def check_final(self, text: str) -> str | None:
        return self.conv.check_final(text)

    def wrap(self, gen):
        """A cut walk generates nothing more: the loop sees an empty, tag-less chunk and stops."""
        return lambda prefix: "" if self.conv.ended else gen(prefix)
