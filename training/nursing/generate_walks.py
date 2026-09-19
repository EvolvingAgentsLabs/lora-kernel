r"""W4 — the corpus of the navigation habit: walks the runtime itself rendered (docs/MEMORY.md §4, §10).

    python -m training.nursing.generate_walks                 # write the corpus and the evaluation sets
    python -m training.nursing.generate_walks --check         # exit 1 if the files on disk have drifted
    python -m training.nursing.generate_walks --gate out.json # W4's gate
    python -m training.nursing.generate_walks --tokens Qwen/Qwen3.5-4B   # exact lengths (tokenizer only)

WHAT IS TAUGHT IS THE METHOD OF WORK, NEVER THE DATA. A row is one bounded task and the walk that
solves it, **byte for byte as it will be served**: every observation in the assistant turn was written
by `memory/runtime.py` inside the corpus-mode loop (`accept_rank.run_chain`), the verb block by
`render_tools`, the carried page by `Conversation.resume`. This module composes statements, plans
walks and draws values; it renders nothing a served expert reads, because a copy of a renderer is
what drifted last time — 71 refused calls that looked like physics **[ran]** P38.

THE ORACLE KNOWS WHICH NOTE IT WANTS, NEVER WHICH ID. Ids are re-drawn per conversation; before it
opens a note the driver asserts that note's id is *already visible* in the text an expert would have
read — a search line, a link, a `next`. A note the conversation never offered cannot be opened here
either.

FOUR FAMILIES, EVERY DEPTH THE EXPERT WILL SERVE (a corpus with one difficulty teaches a floor —
over-solved 18/18 below its training depth **[ran]** P45):

    carry      carry a procedure forward m ∈ {1,2,3,5,8} steps — from its start (search → skeleton →
               first step) or from a recorded state in the middle — and report the last step, as read
    quantity   a quantity this unit or this order changed: the step that holds it (state carried), or
               the wiki note, reached directly or through its parent concept
    rate       an order → a number: the step that sets the rate → the formula it `uses` → `<calc>`;
               or the formula alone from the wiki shelf
    none       a situation the library does not hold → `Not in my library.` (a specialist is
               confidently wrong one step outside its region: 30/30 inside, 1/20 outside **[ran]** P14)

LONG WALKS DO NOT FIT AND ARE NOT TRUNCATED. `release_gate.RECIPE` trains at `max_seq` 1536 and a
32-step walk is ~1 300 proxy tokens of notes alone, so a task is a *window*. A window entered in the
middle needs what `strict` needs — the steps already done — so the state is carried: the runtime
resumes from the record and its last page stands in the user turn **[spec]** W4.

VALUES NOBODY CAN MEMORISE. Every case draws the quantities a site or an order may change and
delivers them only through a note's slots — site layer (marked `[site]`), case layer, or the
textbook's own — and draws an order's givens. The gate asserts, per row,

    V(r) ∩ N(r) = ∅          V = values read off a slot or a <calc>, N = numbers in the statement

over a fixed 14-value table a control with **no lookup tool** scored 27/30 **[ran]** P15, P21.

THE HELD-OUT SIBLING. `discontinue-iv` is never walked: `check_not_held_out` RAISES if a corpus walk would open
a note that belongs only to it (`held_out_only`). Its notes stay in the library — shown in a search
result is not opened, and the library a member is served holds its siblings. The evaluation sets are
written by the same machinery AFTER the corpus, from reserved windows, values, orders and topics the
corpus generator refuses.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from memory import prompt
from memory.layers import render
from memory.notes import Library, Site, count_tokens
from memory.runtime import ChainSuite, Conversation, Lexical
from training.harness.accept_rank import run_chain
from training.nursing.library import ROOT, SUB

OUT = Path("training/nursing/data_walks")
FILES = {"train": OUT / "train.jsonl", "train_nolib": OUT / "train_nolib.jsonl",
         "eval_heldout": OUT / "eval_heldout.jsonl", "eval_control": OUT / "eval_control.jsonl"}
H, W = f"{SUB}/harness", f"{SUB}/wiki/iv-therapy"
HELD_OUT = f"{H}/discontinue-iv"
TRAINED = (f"{H}/primary-infusion", f"{H}/secondary-infusion")
MAX_SEQ = 1536
PROXY_LIMIT = 1150          # the word proxy runs ~±20 % under BPE (memory/notes.py); 1150 × 1.3 < 1536
MAX_CALLS = 64
N_ROWS = 600
SEED = 20260919
DEPTHS = (1, 2, 3, 5, 8)
DEAD_END_RATE = 0.20        # of the cases that begin with a search
FIND_PLACE_RATE = 0.60      # of the windows entered in the middle: no carried page, find the step yourself
MIX = (("carry", 0.50), ("quantity", 0.20), ("rate", 0.18), ("none", 0.12))
MAX_SAME_WALK = 3           # rows that may open the same notes in the same order


class HeldOut(RuntimeError):
    """A corpus walk would open a note that belongs only to the held-out procedure."""


class Unreachable(LookupError):
    """No search the oracle may write returns the note it needs. Counted, never silent."""


# ------------------------------------------------------------------ what the statements are made of
# (opening, the query a reader of that opening might write — made of the opening's own words)
OPENINGS = {
    f"{H}/primary-infusion": [
        ("A patient with a working IV site is to start continuous maintenance fluids that a provider ordered",
         "start continuous maintenance fluids a provider ordered, IV site working"),
        ("You are asked to hang a new bag of ordered IV fluids for a patient whose IV is already in place",
         "hang a bag of ordered IV fluids, IV already in place"),
        ("The provider has ordered continuous fluids and the patient already has a peripheral IV",
         "continuous fluids ordered for a patient with a peripheral IV"),
    ],
    f"{H}/secondary-infusion": [
        ("A provider has ordered an IV medication to run as a piggyback into fluids that are already infusing",
         "ordered IV medication as a piggyback into a primary line that is infusing"),
        ("An intermittent IV antibiotic is due and the patient has a primary line running",
         "intermittent IV antibiotic due, primary line running"),
        ("You are to set up a secondary bag of medication on a patient's running primary infusion",
         "set up a secondary medication on a running primary infusion"),
    ],
    HELD_OUT: [
        ("A patient's peripheral IV is no longer needed and is to come out",
         "take out a peripheral IV that is no longer needed"),
        ("The provider has written to take out the patient's peripheral IV catheter",
         "take out a patient's peripheral IV catheter"),
        ("You are asked to remove a peripheral IV before the patient goes home",
         "remove a peripheral IV before the patient goes home"),
    ],
}

# A quantity is ONE FACT that several notes state. A site or an order that changes it changes it in
# every note that states it, or the expert reads two values to reconcile (§5.2).
QUANTITIES = {
    "cap_seconds": {
        "unit": "seconds", "textbook": "5", "held_out": False,
        "notes": [(f"{H}/primary-infusion/20-cleanse-cap", "seconds"),
                  (f"{H}/primary-infusion/23-cleanse-cap-again", "seconds"),
                  (f"{W}/asepsis/scrub-the-hub", "seconds")],
        "draw": (8, 10, 12, 15, 20, 25, 30, 45), "reserved": (18, 40),
        "step_ask": "for how many seconds is the catheter cap cleansed at this step",
        "wiki": f"{W}/asepsis/scrub-the-hub",
        "wiki_ask": ["How long is an IV port's cap scrubbed before anything is attached to it",
                     "For how many seconds must the cap of an IV port be cleansed"],
        "wiki_query": ["how long to scrub the cap of an IV port", "clean an IV port's cap: how long"],
        "parent_query": "keeping a port or an open end of tubing clean before touching it"},
    "flush_ml": {
        "unit": "mL", "textbook": "3 to 5", "held_out": False,
        "notes": [(f"{H}/primary-infusion/21-assess-patency", "flush_ml"),
                  (f"{W}/site-assessment/patency-flush", "flush_ml")],
        "draw": (2, 4, 6, 7, 8, 10), "reserved": (9, 11),
        "step_ask": "how much normal saline is injected to assess patency at this step",
        "wiki": f"{W}/site-assessment/patency-flush",
        "wiki_ask": ["How much saline shows that an IV catheter is open before infusing through it",
                     "What volume of normal saline is used for a patency flush"],
        "wiki_query": ["saline flush to check that an IV catheter is open", "show an IV catheter is open before infusing"],
        "parent_query": "checking a patient's IV site before using it"},
    "hold_minutes": {
        "unit": "minutes", "textbook": "2-3", "held_out": True,
        "notes": [(f"{HELD_OUT}/07-hold-pressure", "minutes"), (f"{W}/removal/pressure-after-removal", "minutes")],
        "draw": (4, 6, 8, 9, 12), "reserved": (),
        "step_ask": "for how many minutes is pressure held on the site of a patient who is not on anticoagulants",
        "wiki": f"{W}/removal/pressure-after-removal",
        "wiki_ask": ["How long is pressure kept on a site after an IV comes out, for a patient not on anticoagulants"],
        "wiki_query": ["how long to press on the site after an IV is taken out", "press on a site after an IV comes out"],
        "parent_query": "principles when a catheter is coming out"},
    "anticoagulant_minutes": {
        "unit": "minutes", "textbook": "5-10", "held_out": True,
        "notes": [(f"{HELD_OUT}/07-hold-pressure", "anticoagulant_minutes"),
                  (f"{W}/removal/pressure-after-removal", "anticoagulant_minutes")],
        "draw": (11, 13, 15, 20, 25), "reserved": (),
        "step_ask": "for how many minutes is pressure held on the site of a patient on anticoagulant medication",
        "wiki": f"{W}/removal/pressure-after-removal",
        "wiki_ask": ["How long is pressure kept on a site after an IV comes out, for a patient on anticoagulant medication"],
        "wiki_query": ["how long to press on the site after an IV is taken out", "press on a site after an IV comes out"],
        "parent_query": "principles when a catheter is coming out"},
}
LAYERS = (("site", 0.5), ("case", 0.3), ("textbook", 0.2))

# an order's givens. The reserved values are the control set's and the corpus never draws them.
GRAVITY = {"volume": (250, 500, 1000), "hours": (2, 3, 4, 6, 8, 12), "drop_factor": (10, 15, 20, 60),
           "reserved_volume": (750,)}
PUMP = {"volume": (50, 100, 250), "minutes": (15, 20, 30, 45, 90), "reserved_volume": (150,)}
RATE_STEPS = {"gravity": [f"{H}/primary-infusion/26-set-rate"],
              "pump": [f"{H}/primary-infusion/26-set-rate", f"{H}/secondary-infusion/19-set-rate"]}
FORMULA = {"gravity": f"{W}/rates/gravity-drip-rate", "pump": f"{W}/rates/pump-rate"}

# situations this library does not hold. The last four are the control set's.
NOT_HELD = [
    ("A patient needs an indwelling urinary catheter inserted", "insert an indwelling urinary catheter"),
    ("A central line dressing is due to be changed", "change a central venous catheter dressing"),
    ("A unit of packed red blood cells has arrived for transfusion", "administer a blood transfusion"),
    ("A patient's blood glucose is high and sliding-scale insulin is ordered", "give subcutaneous insulin by sliding scale"),
    ("A nasogastric tube is to be placed for feeding", "place a nasogastric feeding tube"),
    ("A patient needs a 12-lead electrocardiogram recorded", "record a twelve lead electrocardiogram"),
    ("A surgical wound needs a sterile dressing change", "sterile dressing change of a surgical wound"),
    ("You are asked to collect a sputum specimen for culture", "collect a sputum specimen for culture"),
    ("A tracheostomy needs suctioning", "suction a tracheostomy"),
    ("An oral medication must be crushed for a patient who cannot swallow", "crush an oral tablet for a patient"),
    ("A patient is to be taught how to use an incentive spirometer", "teach incentive spirometer use"),
    ("A new peripheral IV must be started on a patient with no IV access", "insert a new peripheral catheter into a vein"),
    ("A patient-controlled analgesia pump is to be programmed", "program a patient controlled analgesia pump"),
    ("A chest tube drainage system needs to be checked", "check a chest tube drainage system"),
    ("An intramuscular vaccine is due", "give an intramuscular injection"),
    ("A patient's oxygen is to be changed from nasal cannula to a mask", "change oxygen delivery device"),
]
NOT_HELD_RESERVED = 4
NOT_HELD_ASKS = [
    "Carry out the first step of the procedure and report it, word for word as the library states it.",
    "Carry out the first 3 steps of the procedure, in order, and report the last step you carried out, word for word as the library states it.",
    "On this unit and for this order, what does the first step require? Answer as the library states it.",
]


# ------------------------------------------------------------------ the library's split
def held_out_only(lib: Library) -> set[str]:
    """Notes no corpus walk may open: the held-out skeleton, its steps, the wiki only it uses."""
    own = {HELD_OUT, *lib.walk(HELD_OUT)}
    used_by = lambda procs: {u for p in procs for s in lib.walk(p) for u in lib[s].uses}
    only = used_by([HELD_OUT]) - used_by(TRAINED)
    changed = True
    while changed:                          # a concept whose whole branch is the held-out's, and its leaves
        changed = False
        for n in lib.notes.values():
            if n.shelf != "wiki" or n.id in only:
                continue
            if n.parent in only and n.id not in used_by(TRAINED):
                only.add(n.id); changed = True
    return own | only


# ------------------------------------------------------------------ a case
@dataclass
class Case:
    id: str
    family: str
    variant: str
    procedure: str | None
    statement: str                       # the task, in plain words — what BOTH arms read
    carried: list[str]                   # steps the record shows done (state for `resume`)
    plan: list[tuple]                    # ("search", shelf, query) · ("open", note id) · ("calc", expr)
    answer: str
    check: dict                          # how a reply is verified
    givens: list[str] = field(default_factory=list)      # numbers the statement must state
    site: dict | None = None             # note id → {slot: value}
    case: dict | None = None             # note id → {slot: value}
    seed: int = 0
    dead_end: bool = False
    page: bool = True                    # is the carried page shown? If not, the expert finds its place itself
    meta: dict = field(default_factory=dict)

    @property
    def walk(self) -> list[str]:
        """The notes the oracle opens, in order."""
        return [a[1] for a in self.plan if a[0] == "open"]


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _label(note_id: str) -> str:
    n, _, slug = note_id.rsplit("/", 1)[-1].partition("-")
    return f"{n} {slug.replace('-', ' ')}"


def _pick(rng: random.Random, weighted) -> str:
    x, acc = rng.random(), 0.0
    for name, w in weighted:
        acc += w
        if x < acc:
            return name
    return weighted[-1][0]


# ------------------------------------------------------------------ driving the runtime
def conversation(lib: Library, c: Case, searcher=None) -> tuple[Conversation, str]:
    """The conversation a case is served in, and the carried page the runtime wrote for it."""
    site = Site(name="case-site", overrides=c.site) if c.site else None
    conv = Conversation(lib, site=site, case=c.case, mode="strict", seed=c.seed, searcher=searcher,
                        log_content=True)
    return conv, conv.resume(c.carried)


def user_turn(c: Case, page: str) -> str:
    text = c.statement
    if page and c.page:
        text += "\n\nThe walk so far — the last page the library showed you:\n" + page
    return prompt.user_text(text)


def _visible(shown: str, text: str) -> bool:
    return bool(re.search(rf"(?:\[{shown}\]|next {shown}\b|First step: {shown}\b)", text))


def drive(lib: Library, c: Case, searcher=None) -> dict:
    """Run a case's plan through the corpus-mode loop. Returns the served user turn, the assistant
    turn the loop wrote, and the conversation (its log is what the gate reads)."""
    conv, page = conversation(lib, c, searcher)
    user = user_turn(c, page)
    steps = iter(c.plan)

    def gen(prefix: str) -> str:
        step = next(steps, None)
        if step is None:
            return c.answer
        if step[0] == "search":
            return f"<search shelf={step[1]}>{step[2]}</search>"
        if step[0] == "calc":
            return f"<calc>{step[1]}</calc>"
        shown = conv.opaque.get(step[1])
        if shown is None or not _visible(shown, user + prefix):
            raise Unreachable(step[1])
        return f"<open>{shown}</open>"

    suite = ChainSuite(conv)
    chain = run_chain(suite.wrap(gen), {}, max_calls=MAX_CALLS, suite=suite)
    return {"user": user, "assistant": chain["text"], "chain": chain, "conv": conv}


def returned(lib: Library, shelf: str, query: str, searcher=None) -> list[str]:
    return (searcher or Lexical(lib)).search(query, shelf, 3)


def reach(lib: Library, target: str, shelf: str, queries: list[str], searcher=None) -> list[tuple]:
    """The searches that bring `target` into a result: the first query that returns it, preceded by
    the ones that did not — a second, narrower search is a legitimate step of a walk."""
    plan = []
    for q in queries[:2]:
        plan.append(("search", shelf, q))
        if target in returned(lib, shelf, q, searcher):
            return plan
    raise Unreachable(target)


def dead_end(lib: Library, rng: random.Random, shelf: str, query: str, targets: set[str], searcher=None) -> list[tuple]:
    """A hurried search, a wrong note opened and read — the recovery is the search that follows.

    The hurried search is two words of the proper one, chosen among the pairs whose three results do
    NOT hold the note wanted (opening a wrong note while the right one is listed would teach exactly
    the wrong habit). The wrong note is one the referee lets through — nothing it `requires` is
    missing, and it is not the held-out's: a dead end is a detour, never a violation. Which pairs
    qualify depends on the searcher, as a dead end does; none qualifying → no dead end, `[]`.
    """
    from memory.runtime import _words
    words, banned = sorted(_words(query)), held_out_only(lib) | targets
    pairs = [(a, b) for i, a in enumerate(words) for b in words[i + 1:]]
    rng.shuffle(pairs)
    for a, b in pairs:
        got = returned(lib, shelf, f"{a} {b}", searcher)
        wrong = [i for i in got if i not in banned and not lib[i].requires]
        if wrong and not (set(got) & targets):
            return [("search", shelf, f"{a} {b}"), ("open", wrong[0])]
    return []


# ------------------------------------------------------------------ the four families
def _draw_quantities(rng: random.Random, which: str, avoid: set[str], eval_set: str | None) -> tuple[dict, dict, dict]:
    """Every trained quantity is drawn for every case, so any page a walk crosses shows this case's
    value. Returns (site overrides, case values, {quantity: (value, layer)})."""
    site, case, drawn = {}, {}, {}
    layer = _pick(rng, LAYERS)
    if eval_set == "control" and layer == "textbook":
        layer = "site"          # the textbook's value is the corpus's too: a control case draws a reserved one
    for name, q in QUANTITIES.items():
        if q["held_out"] != (which == "heldout"):
            continue
        pool = q["reserved"] if (eval_set == "control" and q["reserved"]) else q["draw"]
        pool = [v for v in pool if str(v) not in avoid]
        # a textbook value the statement happens to state ("the next 5 steps", five seconds) would
        # read as a leak and is one: this case's unit changed it instead.
        mine = "site" if (layer == "textbook" and _numbers(q["textbook"]) & avoid) else layer
        value = rng.choice(pool) if mine != "textbook" else q["textbook"]
        for note, slot in q["notes"]:
            if mine == "site":
                site.setdefault(note, {})[slot] = value
            elif mine == "case":
                case.setdefault(note, {})[slot] = value
        drawn[name] = (str(value), mine)
    return site or None, case or None, drawn


def carry_case(lib, rng, cid, proc, k, m, eval_set=None, searcher=None, dead_rate=DEAD_END_RATE) -> Case:
    steps = lib.walk(proc)
    opening, query = rng.choice(OPENINGS[proc])
    window = steps[k:k + m]
    ask = (f"Carry out the {'first step of the procedure' if m == 1 else f'first {m} steps of the procedure, in order'}"
           if k == 0 else
           f"The record shows steps 1 to {k} done — the last was '{_label(steps[k - 1])}'. "
           f"Carry out the next {'step' if m == 1 else f'{m} steps, in order'}")
    statement = (f"{opening}. {ask}{',' if m > 1 else ''} and report the last step you carried out, word for word "
                 "as the library states it.")
    site, case, drawn = _draw_quantities(rng, "heldout" if proc == HELD_OUT else "trained",
                                         _numbers(statement), eval_set)
    plan, dead = [], False
    if k == 0:
        if rng.random() < dead_rate:
            plan += dead_end(lib, rng, "harness", query, {proc, *window}, searcher)
            dead = bool(plan)
        plan += reach(lib, proc, "harness", [query, query + ", the ordered steps of the procedure"], searcher) + [("open", proc)]
    # FINDING ONE'S PLACE, WITHOUT THE PAGE. The record says where the walk stands; the skeleton
    # says what comes next; a search for that label finds the step. Four moves and two verbs, where
    # following a carried page is one verb repeated — and a protocol with one tool is copying
    # **[ran]** P13. Where no search reaches the step, the page is shown instead (counted).
    variant, page = ("start" if k == 0 else "middle"), True
    if k and rng.random() < FIND_PLACE_RATE:
        label = _label(steps[k]).split(" ", 1)[1]
        try:
            find = (reach(lib, proc, "harness", [query, query + ", the ordered steps of the procedure"], searcher)
                    + [("open", proc)]
                    + reach(lib, steps[k], "harness", [label, f"{label}, {lib[proc].title.lower()}"], searcher))
            plan, variant, page = find, "middle-find", False
        except Unreachable:
            variant = "middle-page-fallback"
    plan += [("open", s) for s in window]
    last = lib[window[-1]]
    body = render(last, Site(name="case-site", overrides=site) if site else None, (case or {}).get(last.id))
    return Case(id=cid, family="carry", variant=variant, procedure=proc, page=page,
                statement=statement, carried=steps[:k], plan=plan, answer=f"Last step carried out: {body}",
                check={"kind": "body", "body": body}, site=site, case=case, seed=rng.randrange(10**9),
                dead_end=dead, meta={"k": k, "m": m, "drawn": drawn})


def quantity_case(lib, rng, cid, name, variant, eval_set=None, searcher=None, dead_rate=DEAD_END_RATE) -> Case:
    q = QUANTITIES[name]
    plan, dead, carried, proc = [], False, [], None
    if variant == "step":
        target = q["notes"][0][0] if name != "cap_seconds" else rng.choice(q["notes"][:2])[0]
        proc = target.rsplit("/", 1)[0]
        steps = lib.walk(proc)
        k = steps.index(target)
        opening = rng.choice(OPENINGS[proc])[0]
        carried = steps[:k]
        statement = (f"{opening}. The record shows steps 1 to {k} done — the last was '{_label(steps[k - 1])}'. "
                     f"On this unit and for this order, {q['step_ask']}? Carry out the step and answer with the "
                     "quantity and its unit.")
        plan = [("open", target)]
    else:
        ask = rng.choice(q["wiki_ask"])
        statement = f"{ask}, on this unit and for this order? Answer with the quantity and its unit."
        target = q["wiki"]
        if rng.random() < dead_rate:
            plan += dead_end(lib, rng, "wiki", q["wiki_query"][0], {target, lib[target].parent}, searcher)
            dead = bool(plan)
        if variant == "wiki-parent":         # through the concept that holds it: two opens
            parent = lib[target].parent
            plan += reach(lib, parent, "wiki", [q["parent_query"], lib[parent].title], searcher)
            plan += [("open", parent), ("open", target)]
        else:
            plan += reach(lib, target, "wiki", q["wiki_query"], searcher) + [("open", target)]
    site, case, drawn = _draw_quantities(rng, "heldout" if q["held_out"] else "trained",
                                         _numbers(statement), eval_set)
    value, layer = drawn[name]
    if _numbers(statement) & _numbers(value):
        raise ValueError(f"{cid}: the statement states the value it asks for")
    return Case(id=cid, family="quantity", variant=variant, procedure=proc, statement=statement,
                carried=carried, plan=plan, answer=f"{value} {q['unit']}",
                check={"kind": "value", "value": value, "unit": q["unit"]}, site=site, case=case,
                seed=rng.randrange(10**9), dead_end=dead, meta={"quantity": name, "layer": layer, "drawn": drawn})


def rate_case(lib, rng, cid, kind, variant, eval_set=None, searcher=None, dead_rate=DEAD_END_RATE) -> Case:
    for _ in range(200):
        target = rng.choice(RATE_STEPS[kind])
        proc_of = target.rsplit("/", 1)[0]
        k = lib.walk(proc_of).index(target)
        if kind == "gravity":
            g = GRAVITY
            vol = rng.choice(g["reserved_volume"] if eval_set == "control" else g["volume"])
            hours, df = rng.choice(g["hours"]), rng.choice(g["drop_factor"])
            expr, exact = f"{vol} * {df} / ({hours} * 60)", vol * df / (hours * 60)
            order = (f"The order is {vol} mL of IV fluid over {hours} hours by gravity, and the tubing's drop factor "
                     f"is {df} gtt/mL")
            unit, givens = "drops per minute", [str(vol), str(hours), str(df)]
        else:
            g = PUMP
            vol = rng.choice(g["reserved_volume"] if eval_set == "control" else g["volume"])
            minutes = rng.choice(g["minutes"])
            expr, exact = f"{vol} * 60 / {minutes}", vol * 60 / minutes
            what = "IV medication" if (variant != "step" or proc_of.endswith("secondary-infusion")) else "IV fluid"
            order = f"The order is {vol} mL of {what} over {minutes} minutes on an infusion pump"
            unit, givens = "mL/hr", [str(vol), str(minutes)]
        shown, answer = f"{exact:.6g}", str(round(exact))
        # THE ANSWER MUST NOT ALREADY BE IN THE STATEMENT: 100 mL over 60 minutes is 100 mL/hr, and
        # "steps 1 to 25" states a 25.
        if not ({shown, answer} & (set(givens) | {"1", str(k)})):
            break
    else:
        raise ValueError(f"{cid}: no order whose rate is not one of its own givens")
    formula = FORMULA[kind]
    plan, dead, carried, proc = [], False, [], None
    site, case, drawn = _draw_quantities(rng, "trained", set(givens) | {"1", str(k), shown, answer}, eval_set)
    if variant == "step":
        proc = target.rsplit("/", 1)[0]
        steps = lib.walk(proc)
        carried = steps[:k]
        statement = (f"{rng.choice(OPENINGS[proc])[0]}. {order}. The record shows steps 1 to {k} done — the last was "
                     f"'{_label(steps[k - 1])}'. Carry out the step that sets the rate: what is set, in {unit}? "
                     "Answer with a whole number and its unit.")
        plan = [("open", target), ("open", formula), ("calc", expr)]
    else:
        statement = f"{order}. What rate is set, in {unit}? Answer with a whole number and its unit."
        parent = lib[formula].parent
        if rng.random() < dead_rate:
            plan += dead_end(lib, rng, "wiki", "rate to set for an infusion by gravity in drops per minute" if kind == "gravity"
                             else "rate to set for an infusion on a pump in mL per hour", {formula, parent}, searcher)
            dead = bool(plan)
        if variant == "wiki-parent":
            plan += reach(lib, parent, "wiki", ["turning an order into a number to set on a pump or a clamp", "infusion rates"], searcher)
            plan += [("open", parent), ("open", formula), ("calc", expr)]
        else:
            qs = (["drops per minute for a gravity infusion", "gravity infusion drops per minute formula"] if kind == "gravity"
                  else ["mL per hour for an infusion on a pump", "pump infusion mL per hour formula"])
            plan += reach(lib, formula, "wiki", qs, searcher) + [("open", formula), ("calc", expr)]
    return Case(id=cid, family="rate", variant=f"{kind}-{variant}", procedure=proc, statement=statement,
                carried=carried, plan=plan, answer=f"{answer} {unit}",
                check={"kind": "value", "value": answer, "unit": unit, "tolerance": 1},
                givens=givens, site=site, case=case, seed=rng.randrange(10**9), dead_end=dead,
                meta={"expr": expr, "calc": shown, "drawn": drawn})


def none_case(lib, rng, cid, topic, searcher=None) -> Case:
    situation, query = topic
    statement = f"{situation}. " + rng.choice(NOT_HELD_ASKS)
    plan = [("search", "harness", query)]
    if rng.random() < 0.5:
        plan.append(("search", "wiki", query))
    return Case(id=cid, family="none", variant=f"{len(plan)}-search", procedure=None, statement=statement,
                carried=[], plan=plan, answer="Not in my library.", check={"kind": "none"},
                seed=rng.randrange(10**9), meta={"topic": query})


# ------------------------------------------------------------------ signatures, the split, the rows
def signature(c: Case) -> str:
    """What a walk IS, for the purpose of saying two cases are the same one: the notes opened in
    order, the values those notes showed, the order's givens. Ids and wording are not part of it."""
    shown = sorted((n, s, str(v)) for layer in (c.site, c.case) for n, slots in (layer or {}).items()
                   for s, v in slots.items() if n in c.walk)
    core = [c.family, c.walk, shown, sorted(c.givens) if c.family == "rate" else [],
            c.meta.get("topic"), c.statement if c.family == "none" else None,
            sum(a[0] == "search" for a in c.plan) if c.family == "none" else None]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def reserved_windows(lib: Library) -> set[tuple[str, int, int]]:
    """Windows of the trained procedures that belong to the control set. Drawn once, by seed."""
    rng = random.Random(SEED + 1)
    every = [(p, k, m) for p in TRAINED for k in range(len(lib.walk(p))) for m in DEPTHS
             if k + m <= len(lib.walk(p))]
    return set(rng.sample(every, 24))


def check_not_held_out(lib: Library, c: Case) -> None:
    bad = [i for i in c.walk + c.carried if i in held_out_only(lib)]
    if bad:
        raise HeldOut(f"{c.id}: a corpus walk may not open {bad[0]}")


def corpus_cases(lib: Library, n: int = N_ROWS, seed: int = SEED, searcher=None) -> tuple[list[Case], dict]:
    rng = random.Random(seed)
    reserved = reserved_windows(lib)
    topics = NOT_HELD[:-NOT_HELD_RESERVED]
    out, seen, per_walk = [], set(), {}
    dropped = {"unreachable": 0, "duplicate": 0, "walk_cap": 0, "too_long": 0, "drawn": 0}
    while len(out) < n:
        dropped["drawn"] += 1
        if dropped["drawn"] > 40 * n:
            raise RuntimeError(f"cannot fill {n} rows: {dropped}")
        family, cid = _pick(rng, MIX), f"w4-{len(out):04d}"
        try:
            if family == "carry":
                proc = rng.choice(TRAINED)
                steps = lib.walk(proc)
                m = rng.choice(DEPTHS)
                k = 0 if rng.random() < 0.35 else rng.randrange(1, len(steps) - m + 1)
                if (proc, k, m) in reserved:
                    continue
                c = carry_case(lib, rng, cid, proc, k, m, searcher=searcher)
            elif family == "quantity":
                name = rng.choice([q for q, v in QUANTITIES.items() if not v["held_out"]])
                c = quantity_case(lib, rng, cid, name, _pick(rng, (("step", .45), ("wiki", .35), ("wiki-parent", .2))),
                                  searcher=searcher)
            elif family == "rate":
                c = rate_case(lib, rng, cid, rng.choice(("gravity", "pump")),
                              _pick(rng, (("step", .4), ("wiki", .4), ("wiki-parent", .2))), searcher=searcher)
            else:
                c = none_case(lib, rng, cid, rng.choice(topics), searcher=searcher)
        except Unreachable:
            dropped["unreachable"] += 1
            continue
        check_not_held_out(lib, c)
        key = (signature(c), c.statement)
        if key in seen:
            dropped["duplicate"] += 1
            continue
        w = (c.family, tuple(c.walk), tuple(c.givens), c.meta.get("topic"), c.variant if c.family == "none" else None)
        if c.family in ("carry", "none") and per_walk.get(w, 0) >= MAX_SAME_WALK:
            dropped["walk_cap"] += 1
            continue
        seen.add(key); per_walk[w] = per_walk.get(w, 0) + 1
        out.append(c)
    return out, dropped


def eval_cases(lib: Library, seed: int = SEED + 7, searcher=None) -> dict[str, list[Case]]:
    """Written after the corpus generator above was frozen. `heldout`: the sibling never walked —
    from its start at every depth, from the middle, its two quantities on both shelves. `control`:
    the trained procedures, from reserved windows, reserved values, reserved orders, reserved topics."""
    rng = random.Random(seed)
    held, steps = [], lib.walk(HELD_OUT)
    for m in (1, 2, 3, 5, 8, len(steps)):
        for _ in range(3):
            held.append(carry_case(lib, rng, f"w5h-{len(held):03d}", HELD_OUT, 0, m, "heldout", searcher, 0.0))
    for k in range(1, len(steps)):
        for m in (1, 2, 3, 5):
            if k + m <= len(steps):
                held.append(carry_case(lib, rng, f"w5h-{len(held):03d}", HELD_OUT, k, m, "heldout", searcher, 0.0))
    for name in ("hold_minutes", "anticoagulant_minutes"):
        for variant in ("step",) * 6 + ("wiki",) * 3 + ("wiki-parent",) * 3:
            held.append(quantity_case(lib, rng, f"w5h-{len(held):03d}", name, variant, "heldout", searcher, 0.0))
    shared = _shared_lines()
    for c in held:
        c.meta["final_is_a_shared_line"] = bool(c.walk) and c.walk[-1] in shared
    control = []
    for p, k, m in sorted(reserved_windows(lib)):
        control.append(carry_case(lib, rng, f"w5c-{len(control):03d}", p, k, m, "control", searcher, 0.0))
    for name in ("cap_seconds", "flush_ml"):
        for variant in ("step",) * 4 + ("wiki",) * 2 + ("wiki-parent",) * 2:
            control.append(quantity_case(lib, rng, f"w5c-{len(control):03d}", name, variant, "control", searcher, 0.0))
    for kind in ("gravity", "pump"):
        for variant in ("step",) * 3 + ("wiki",) * 3 + ("wiki-parent",) * 2:
            control.append(rate_case(lib, rng, f"w5c-{len(control):03d}", kind, variant, "control", searcher, 0.0))
    for topic in NOT_HELD[-NOT_HELD_RESERVED:]:
        for _ in range(2):
            control.append(none_case(lib, rng, f"w5c-{len(control):03d}", topic, searcher))
    # an evaluation oracle takes no deliberate dead end (`dead_rate` 0): it is the shortest walk
    return {"eval_heldout": _dedupe(held), "eval_control": _dedupe(control)}


def _dedupe(cases: list[Case]) -> list[Case]:
    seen, out = set(), []
    for c in cases:
        key = (signature(c), c.statement)
        if key not in seen:
            seen.add(key); out.append(c)
    return out


def _shared_lines() -> set[str]:
    """Held-out steps whose source line another procedure states almost word for word (≥ 0.8)."""
    import difflib
    from training.nursing.library import PROCEDURES
    from training.nursing.source import CHECKLISTS
    mine = CHECKLISTS[PROCEDURES["discontinue-iv"]["checklist"]]
    others = [l for slug, p in PROCEDURES.items() if slug != "discontinue-iv" for l in CHECKLISTS[p["checklist"]]]
    near = lambda a, b: difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.8
    return {f"{HELD_OUT}/{i:02d}-{s[0]}" for i, (s, line) in
            enumerate(zip(PROCEDURES["discontinue-iv"]["steps"], mine), 1) if any(near(line, o) for o in others)}


def row(lib: Library, c: Case, searcher=None) -> dict:
    d = drive(lib, c, searcher)
    conv, chain = d["conv"], d["chain"]
    values = sorted({str(v) for l in conv.log for v, _ in (l.get("slots") or {}).values()}
                    | set(re.findall(r"</calc>= (\S+)", chain["text"])))
    return {"case_id": c.id, "family": c.family, "variant": c.variant, "procedure": c.procedure,
            "depth": len(conv.opened) - len(c.carried), "calls": chain["calls"], "dead_end": c.dead_end,
            "answer": c.answer, "check": c.check, "signature": signature(c), "statement": c.statement,
            "givens": c.givens, "values_read": values, "walk": c.walk,
            "held_out_shown": sum(1 for l in conv.log for i in (l.get("returned") or []) if i in held_out_only(lib)),
            "replay": {"seed": c.seed, "carried": c.carried, "page": c.page, "site": c.site, "case": c.case,
                       "plan": [list(a) for a in c.plan]},
            "meta": c.meta,
            "messages": [{"role": "system", "content": prompt.SYSTEM},
                         {"role": "user", "content": d["user"]},
                         {"role": "assistant", "content": chain["text"]}]}


def nolib_row(r: dict) -> dict:
    """The second arm of W5: the same case, the same answer — no verbs, no notes, no carried page."""
    return {"case_id": r["case_id"], "family": r["family"], "variant": r["variant"], "procedure": r["procedure"],
            "answer": r["answer"], "check": r["check"],
            "messages": [{"role": "system", "content": prompt.SYSTEM_NO_LIBRARY},
                         {"role": "user", "content": r["statement"]},
                         {"role": "assistant", "content": r["answer"]}]}


def row_tokens(r: dict) -> int:
    return sum(count_tokens(m["content"]) for m in r["messages"])


def build(lib: Library | None = None, searcher=None) -> tuple[dict[str, list[dict]], dict]:
    lib = lib or Library.load(ROOT)
    cases, dropped = corpus_cases(lib, searcher=searcher)
    rows = [row(lib, c, searcher) for c in cases]
    sets = {"train": rows, "train_nolib": [nolib_row(r) for r in rows]}
    for name, cs in eval_cases(lib, searcher=searcher).items():
        sets[name] = [row(lib, c, searcher) for c in cs]
    return sets, dropped


# ------------------------------------------------------------------ verifying a reply (W5 reads this)
def verify(check: dict, reply: str) -> bool:
    text = " ".join((reply or "").split())
    if check["kind"] == "none":
        return "not in my library" in text.lower()
    if check["kind"] == "body":
        return " ".join(check["body"].split()).lower() in text.lower()
    nums = re.findall(r"-?\d+(?:\.\d+)?(?:\s*(?:-|to)\s*\d+(?:\.\d+)?)?", text)
    if "tolerance" in check:
        return any(abs(float(re.match(r"-?\d+(?:\.\d+)?", n).group(0)) - float(check["value"])) <= check["tolerance"]
                   for n in nums) and check["unit"].split()[0].lower() in text.lower()
    want = re.sub(r"\s+", "", check["value"])
    return any(re.sub(r"\s+", "", n) == want for n in nums) and check["unit"].lower() in text.lower()


# ------------------------------------------------------------------ the gate
def replay(lib: Library, r: dict, searcher=None) -> list[str]:
    """Why a stored row is NOT a walk the referee accepts today. Empty = it is."""
    p = r["replay"]
    c = Case(id=r["case_id"], family=r["family"], variant=r["variant"], procedure=r["procedure"],
             statement=r["statement"], carried=p["carried"], plan=[tuple(a) for a in p["plan"]],
             answer=r["answer"], check=r["check"], givens=r["givens"], site=p["site"], case=p["case"], seed=p["seed"],
             page=p.get("page", True))
    try:
        d = drive(lib, c, searcher)
    except Unreachable as e:
        return [f"never offered an id for {e}"]
    chain, conv, why = d["chain"], d["conv"], []
    if chain["refused"] or chain["malformed"] or conv.errors:
        why.append(f"refused {chain['refused']} malformed {chain['malformed']} errors {conv.errors}")
    if conv.guard.violations:
        why.append(f"the guard spoke: {conv.guard.violations[0]['kind']}")
    if not conv.answered or chain["ran_out"] or chain["verdict"] is None:
        why.append("not answered")
    if d["user"] != r["messages"][1]["content"]:
        why.append("the user turn is not what the runtime renders today")
    if chain["text"] != r["messages"][2]["content"]:
        why.append("the assistant turn is not what the runtime renders today")
    if conv.opened[len(p["carried"]):] != r["walk"]:
        why.append("the notes opened are not the row's walk")
    if not verify(r["check"], chain["spans"][-1]["text"]):
        why.append("the row's own answer fails its own check")
    if f"{SUB}/" in d["user"] + chain["text"]:
        why.append("a library id reached the expert's text")
    return why


def leaks(r: dict) -> list[str]:
    """G1. A value read off a slot or a <calc> that the statement already states."""
    stated = _numbers(r["statement"])
    read = {n for v in r["values_read"] for n in _numbers(v)}
    # 60 minutes per hour is a constant of arithmetic, not a quantity a site sets; it is exempt only
    # as a GIVEN the order states ("over 60 minutes"), never as an answer.
    hit = (read - {"60"}) & stated
    out = [f"the statement states {sorted(hit)}, which the walk reads off the library"] if hit else []
    if r["check"]["kind"] == "value" and _numbers(r["check"]["value"]) & stated:
        out.append("the statement states its own answer")
    return out


def gate(sets: dict[str, list[dict]] | None = None, lib: Library | None = None, dropped: dict | None = None,
         searcher=None) -> dict:
    lib = lib or Library.load(ROOT)
    if sets is None:
        sets = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in FILES.items()}
    train, held, control = sets["train"], sets["eval_heldout"], sets["eval_control"]
    H_only = held_out_only(lib)
    g1 = {r["case_id"]: w for r in train + held + control if (w := leaks(r))}
    # A CASE IS ITS STATEMENT AND ITS WORLD. A quantity's statement states no number on purpose, so
    # two cases may share every word and differ in what the notes say; the pair is what must be new.
    world = lambda r: (r["statement"], tuple(r["values_read"]))
    sigs, cases = {r["signature"] for r in train}, {world(r) for r in train}
    g2 = {r["case_id"]: "its walk, with its values, is in the corpus" if r["signature"] in sigs
          else "its statement, with the values its notes show, is in the corpus" for r in held + control
          if r["signature"] in sigs or world(r) in cases}
    g3 = {r["case_id"]: [i for i in r["walk"] + r["replay"]["carried"] if i in H_only][0] for r in train
          if any(i in H_only for i in r["walk"] + r["replay"]["carried"])}
    g4 = {r["case_id"]: w for r in train + held + control if (w := replay(lib, r, searcher))}
    nolib = sets["train_nolib"]
    paired = ([r["case_id"] for r in train] == [r["case_id"] for r in nolib]
              and all(a["answer"] == b["answer"] and b["messages"][1]["content"] == a["statement"]
                      and "<" not in b["messages"][2]["content"] for a, b in zip(train, nolib)))
    shown_held = sum(1 for r in train if r.get("held_out_shown"))
    depth = {}
    for r in train:
        depth[r["depth"]] = depth.get(r["depth"], 0) + 1
    tok = sorted(row_tokens(r) for r in train + held + control)
    families = {}
    for r in train:
        families[r["family"]] = families.get(r["family"], 0) + 1
    variants, eval_variants = {}, {}
    for r in train:
        variants[f"{r['family']}/{r['variant']}"] = variants.get(f"{r['family']}/{r['variant']}", 0) + 1
    for name in ("eval_heldout", "eval_control"):
        for r in sets[name]:
            k = f"{name}: {r['family']}/{r['variant'].replace('-page-fallback', '')}"
            eval_variants[k] = eval_variants.get(k, 0) + 1
    too_long = [r["case_id"] for r in train + held + control if row_tokens(r) > PROXY_LIMIT]
    from training import suite_gates
    report = suite_gates.inspect(
        "nursing-walks", train, region_of=lambda r: r["family"], prompt_of=lambda r: r["statement"],
        depth_of=lambda r: r["depth"], tools_of=lambda r: [a[0] for a in r["replay"]["plan"]],
        waive={"depth_is_not_the_region": "`none` is the family whose right walk opens nothing: depth 0 is its "
                                          "definition, not a shortcut to it — the other three span 1 to 10 opens"})
    suite = [{"gate": f.gate, "passed": f.passed, "waived_for": f.waived_for, "detail": f.detail}
             for f in report.findings]
    suite_ok = all(f["passed"] is not False or f["waived_for"] for f in suite)
    drawn = (dropped or {}).get("drawn", 0)
    unreachable = (dropped or {}).get("unreachable", 0)
    passed = (not (g1 or g2 or g3 or g4 or too_long) and paired and suite_ok
              and (not drawn or unreachable / drawn <= 0.10))
    return {"library": str(ROOT), "held_out": HELD_OUT, "held_out_only_notes": len(H_only),
            "rows": {k: len(v) for k, v in sets.items()},
            "G1_value_in_statement": g1, "G2_evaluated_walk_in_corpus": g2, "G3_held_out_opened": g3,
            "G4_not_accepted_by_the_referee": g4, "no_library_arm_is_the_same_cases": paired,
            "suite_gates": suite, "variants": variants, "eval_variants": eval_variants,
            "families": families, "depth_mix_opens": dict(sorted(depth.items())),
            "dead_ends": sum(r["dead_end"] for r in train),
            "rows_with_more_than_one_search": sum(1 for r in train if r["family"] != "none" and not r["dead_end"]
                                   and sum(a[0] == "search" for a in r["replay"]["plan"]) > 1),
            "not_in_my_library": families.get("none", 0),
            "held_out_note_shown_in_a_result": shown_held,
            "layers": {l: sum(1 for r in train if r["meta"].get("layer") == l) for l, _ in LAYERS},
            "dropped": dropped, "unreachable_share": round(unreachable / drawn, 4) if drawn else None,
            "tokens_proxy": {"min": tok[0], "median": tok[len(tok) // 2], "max": tok[-1],
                             "limit": PROXY_LIMIT, "max_seq": MAX_SEQ, "over": too_long},
            "passed": passed}


def exact_tokens(name: str) -> dict:
    """Row lengths under the base's own tokenizer — files only, no model. Needs `tokenizers`."""
    from tokenizers import Tokenizer
    tok = Tokenizer.from_pretrained(name)
    out = {}
    for k, p in FILES.items():
        n = sorted(sum(len(tok.encode(m["content"]).ids) + 8 for m in json.loads(l)["messages"])
                   for l in p.read_text().splitlines())
        out[k] = {"min": n[0], "median": n[len(n) // 2], "p95": n[int(len(n) * .95)], "max": n[-1],
                  "over_max_seq": sum(x > MAX_SEQ for x in n)}
    return {"tokenizer": name, "max_seq": MAX_SEQ, "per_message_overhead": 8, "sets": out}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    lib = Library.load(ROOT)
    if "--tokens" in argv:
        print(json.dumps(exact_tokens(argv[argv.index("--tokens") + 1]), indent=2))
        return 0
    sets, dropped = build(lib)
    text = {k: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in v) for k, v in sets.items()}
    if "--check" in argv:
        drift = [str(FILES[k]) for k in FILES if not FILES[k].exists() or FILES[k].read_text() != text[k]]
        print(f"[walks] {'drifted: ' + ', '.join(drift) if drift else 'the files on disk are what the generator writes'}", flush=True)
        return 1 if drift else 0
    if "--gate" not in argv:
        OUT.mkdir(parents=True, exist_ok=True)
        for k in FILES:
            FILES[k].write_text(text[k])
    g = gate(sets, lib, dropped)
    if "--gate" in argv and len(argv) > argv.index("--gate") + 1:
        out = Path(argv[argv.index("--gate") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(g, indent=2, ensure_ascii=False))
    print(f"[walks] W4 gate: rows {g['rows']} · G1 {len(g['G1_value_in_statement'])} G2 "
          f"{len(g['G2_evaluated_walk_in_corpus'])} G3 {len(g['G3_held_out_opened'])} G4 "
          f"{len(g['G4_not_accepted_by_the_referee'])} · dead ends {g['dead_ends']} · dropped {g['dropped']} · "
          f"{'PASSED' if g['passed'] else 'FAILED'}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
