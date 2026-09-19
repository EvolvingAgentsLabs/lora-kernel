r"""W2's gate: every oracle walk, replayed through the runtime as a scripted generation.

No model runs. `scripted(...)` stands where a model will: `run_chain` calls it with the assistant
text so far and it returns the next chunk, ending at a closing tag. **The script knows which note it
wants, never which id** — it reads the opaque id off what the runtime itself wrote, by title or off
the last `next` line. So a note the runtime never offered cannot be opened by the oracle either,
and that is a finding, not an exception to swallow.

    gate passes  ⇔  ∀ walk ∈ W1's 72:  refused = malformed = 0 ∧ guard silent ∧ answered
                    ∧ site walks show `answer [site]` ∧ rate walks' <calc> = the answer ± tolerance
                    ∧ no library id in any text shown
                    ∧ the three violating walks are cut in `strict` and continue in `recover`

    python -m training.nursing.walks --gate results/M7-W2-runtime-20260919/gate.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from memory.notes import Library, Site
from memory.runtime import ChainSuite, Conversation
from training.harness.accept_rank import run_chain
from training.nursing.library import ROOT, SITE_SLOTS, SUB, oracle_walk
from training.nursing.questions import SITE_FACTS, build as questions

MAX_CALLS = 64            # above the runtime's own budgets (48 opens + 12 searches): the referee's caps decide


class NeverOffered(LookupError):
    """The oracle wants a note the conversation has shown no id for."""


def learn(text: str, lib: Library, opened: str | None, known: dict) -> None:
    """What the last `<open>` taught: the id on its `next` line is the id of the note that follows."""
    if not opened:
        return
    last = text[text.rindex("<open>"):]
    if "= ERROR" in last:
        return
    m = re.findall(r"^  next (\w+)$", last, re.M)
    follows = lib[opened].next or lib[opened].first
    if m and follows:
        known[follows] = m[-1]


def find_id(text: str, lib: Library, want: str, known: dict) -> str:
    """The opaque id of `want`, read off the runtime's output the way an expert would."""
    if want in known:
        return known[want]
    # Steps of different procedures legitimately share a title ("Hand hygiene"); the oracle reaches
    # those along `next`. A title it has to *look up* must name one note, or the lookup is a guess.
    same = [n.id for n in lib.notes.values() if n.title == lib[want].title]
    assert same == [want], f"looked up by title, and {len(same)} notes are titled `{lib[want].title}`"
    m = re.findall(rf"\[(\w+)\] (?:\w+ · )?{re.escape(lib[want].title)}(?: —|$| ·)", text, re.M)
    if not m:
        raise NeverOffered(want)
    return m[-1]


def rate_expression(question: str) -> str:
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", question.split("Round")[0])]
    if "drops per minute" in question:            # volume mL, hours, drop factor
        return f"{n[0]:g} * {n[2]:g} / ({n[1]:g} * 60)"
    return f"{n[0]:g} / ({n[1]:g} / 60)"           # volume mL over minutes, on a pump → mL/hr


def scripted(lib: Library, plan: list[tuple[str, str]]):
    """plan: ("search", "shelf|query") · ("open", note id) · ("open_raw", opaque) · ("calc", expr)."""
    state = {"i": 0, "prev": None, "known": {}}

    def gen(prefix: str) -> str:
        learn(prefix, lib, state["prev"], state["known"])
        state["prev"] = None
        if state["i"] >= len(plan):
            return "Done."
        verb, arg = plan[state["i"]]
        state["i"] += 1
        if verb == "search":
            shelf, query = arg.split("|", 1)
            return f"<search shelf={shelf}>{query}</search>"
        if verb == "open":
            shown = find_id(prefix, lib, arg, state["known"])
            state["prev"] = arg
            return f"<open>{shown}</open>"
        if verb == "open_raw":
            return f"<open>{arg}</open>"
        return f"<calc>{arg}</calc>"
    return gen


def plan_for(q: dict, walk: list[str], lib: Library) -> list[tuple[str, str]]:
    first = lib[walk[0]]
    plan = [("search", f"{first.shelf}|{first.when}")] + [("open", i) for i in walk]
    if q["kind"] == "rate":
        plan.append(("calc", rate_expression(q["question"])))
    return plan


def run(lib: Library, plan, *, site=None, mode="strict", seed=0) -> tuple[dict, Conversation]:
    conv = Conversation(lib, site=site, mode=mode, seed=seed, log_content=True)
    suite = ChainSuite(conv)
    chain = run_chain(suite.wrap(scripted(lib, plan)), {}, max_calls=MAX_CALLS, suite=suite)
    return chain, conv


def violating(lib: Library) -> dict[str, list[tuple[str, str]]]:
    """Three walks that break the library's links. An id has to be *shown* to be opened, so a
    jump is made the way a model would make it: by searching for the later step."""
    proc = f"{SUB}/harness/discontinue-iv"
    steps = lib.walk(proc)
    start = [("search", f"harness|{lib[proc].when}"), ("open", proc)]
    jump = lambda i: [("search", f"harness|{lib[steps[i]].when}"), ("open", steps[i])]
    back = lambda upto: [("open", s) for s in steps[:upto + 1]]
    return {"skipped_requires": start + jump(6) + back(6),
            "unknown_id": start + [("open_raw", "zz9")] + back(1),
            "out_of_order": start + [("open", steps[0])] + jump(2) + [("open", steps[1]), ("open", steps[2])]}


def gate(root: Path = ROOT) -> dict:
    lib = Library.load(root)
    failures, per_kind, ranks, totals = {}, {}, [], {"calls": 0, "refused": 0, "malformed": 0, "opens": 0,
                                                     "searches": 0, "calcs": 0, "log_lines": 0}
    for n, q in enumerate(questions()):
        walk = oracle_walk(q, lib)
        site = None
        if q["kind"] == "site":
            fact = next(f for f in SITE_FACTS if f[1] in q["question"])
            target, slot = SITE_SLOTS[SITE_FACTS.index(fact)]
            site = Site(name="case-site", overrides={target: {slot: q["answer"]}})
        why = []
        try:
            chain, conv = run(lib, plan_for(q, walk, lib), site=site, seed=n)
        except NeverOffered as e:
            failures[q["id"]] = [f"never offered an id for {e}"]
            continue
        text = chain["text"]
        if chain["refused"] or chain["malformed"] or conv.errors:
            why.append(f"refused {chain['refused']} malformed {chain['malformed']} errors {conv.errors}")
        if conv.guard.violations:
            why.append(f"guard spoke: {conv.guard.violations}")
        if not conv.answered or chain["ran_out"] or chain["verdict"] is None:
            why.append(f"not answered: ended={conv.ended} ran_out={chain['ran_out']}")
        if conv.opened != walk:
            why.append("the notes opened are not the oracle's walk")
        if f"{SUB}/" in text:
            why.append("a library id reached the expert's text")
        if q["kind"] == "site" and f"{q['answer']} [site]" not in text:
            why.append("the site's value is not in the text, marked")
        if q["kind"] == "rate":
            got = float(re.findall(r"</calc>= (\S+)", text)[-1])
            if abs(got - q["answer"]) > q["tolerance"]:
                why.append(f"calc {got} is not {q['answer']} ± {q['tolerance']}")
        returned = next(l for l in conv.log if l["verb"] == "search")["returned"]
        ranks.append(returned.index(walk[0]) + 1)
        k = per_kind.setdefault(q["kind"], {"n": 0, "passed": 0})
        k["n"] += 1; k["passed"] += not why
        totals["calls"] += chain["calls"]; totals["refused"] += chain["refused"]
        totals["malformed"] += chain["malformed"]; totals["opens"] += len(conv.opened)
        totals["searches"] += conv.searches; totals["log_lines"] += len(conv.log)
        totals["calcs"] += sum(1 for l in conv.log if l["verb"] == "calc")
        if why:
            failures[q["id"]] = why

    cuts = {}
    for name, plan in violating(lib).items():
        try:
            strict, cs = run(lib, plan, mode="strict")
            recover, cr = run(lib, plan, mode="recover")
        except NeverOffered as e:          # a library whose own links are broken cannot host the check
            cuts[name] = {"unrunnable": f"never offered an id for {e}"}
            continue
        planned = sum(1 for v, _ in plan if v != "search") + sum(1 for v, _ in plan if v == "search")
        cuts[name] = {"strict": {"cut": cs.ended is not None, "ended": cs.ended, "verdict": strict["verdict"],
                                 "calls_made": strict["calls"], "calls_planned": planned,
                                 "reported": re.findall(r"= (ERROR: [^\n]+)", strict["text"])},
                      "recover": {"continued": cr.ended is None and recover["calls"] == planned,
                                  "violations": len(cr.guard.violations), "answered": recover["verdict"] is not None,
                                  "reported": re.findall(r"= (ERROR: [^\n]+)", recover["text"])}}
    cut_ok = all("unrunnable" not in c and c["strict"]["cut"] and c["strict"]["verdict"] is None and c["strict"]["reported"]
                 and c["strict"]["calls_made"] < c["strict"]["calls_planned"]
                 and c["recover"]["continued"] and c["recover"]["violations"] == 1 and c["recover"]["answered"]
                 for c in cuts.values())
    n_q = len(questions())
    return {"library": str(root), "walks": n_q, "passed_walks": n_q - len(failures), "failures": failures,
            "per_kind": per_kind, "totals": totals,
            "search": {"what": "lexical (W2); the procedure or concept the walk starts at, by its own `when`",
                       "rank_1": sum(r == 1 for r in ranks), "rank_le_3": len(ranks), "n": n_q},
            "violating_walks": cuts, "violating_walks_ok": cut_ok,
            "budgets": {"max_opens": 48, "max_searches": 12, "k": 3, "loop_max_calls": MAX_CALLS},
            "passed": not failures and cut_ok}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    g = gate()
    if "--gate" in argv and len(argv) > argv.index("--gate") + 1:
        out = Path(argv[argv.index("--gate") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(g, indent=2, ensure_ascii=False))
    print(f"[runtime] W2 gate: {g['passed_walks']}/{g['walks']} oracle walks through the runtime, "
          f"refused {g['totals']['refused']}, malformed {g['totals']['malformed']}; "
          f"violating walks {'cut' if g['violating_walks_ok'] else 'NOT CUT'}; "
          f"{'PASSED' if g['passed'] else 'FAILED'}", flush=True)
    for k, v in g["failures"].items():
        print(f"[runtime]   {k}: {v}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
