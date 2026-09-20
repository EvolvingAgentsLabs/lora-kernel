r"""W5c — corpus v2: the same habit, plus the one SHAPE the first corpus never showed (docs/MEMORY.md §10).

    python -m training.nursing.generate_walks_v2                 # write the corpus and the NEW evaluation sets
    python -m training.nursing.generate_walks_v2 --check         # exit 1 if the files on disk have drifted
    python -m training.nursing.generate_walks_v2 --gate out.json # the v2 gate

WHY A SECOND CORPUS. W5 **[ran]**: the library arm walked cleanly to the right held-out note and then
wrote the wrong one of the note's TWO values — `anticoagulant_minutes` 0 of 11, `hold_minutes` 11 of
12 — while the untrained base read all of them right. W5b **[ran]** attributed it: with the bare base
writing the last line, 0 of those 12 failures remain. Of the corpus's 108 quantity rows not one read a
note that states two values of one quantity: *a corpus with one difficulty teaches a floor*, and the
floor it taught was "copy the number".

WHAT v2 ADDS — A FAMILY, `conditional`. A note states a quantity and a second value of it under a
condition; the task asks for ONE of the two, the plain or the conditional, in equal shares, so that
"copy the first number on the page" is worth one half. The condition reaches the expert either in the
question (*explicit*) or as a fact of the situation stated before it (*implicit*). Where such notes
come from:

    A   one REAL note — `wiki/…/rates/drop-factor`, the chapter's own sentence (macro-drip against
        micro-drip sets), byte-checked in `source.PROSE`
    B   sentences a site ADDS to trained notes (`Site.adds`, `library.SITE_RULES`) — **invented example
        content**, approved as such by the user; the wording of the condition is fixed, every number
        is drawn per case

Everything else is W4's, by import and not by copy: rows are rendered by the runtime inside the
corpus-mode loop, ids are re-drawn per conversation, values are drawn per case, dead ends and the
depth mix are W4's, and `check_not_held_out` still RAISES if a walk would open a note that belongs
only to `discontinue-iv`. v1's files are never touched (`generate_walks --check` still holds).

THE EVALUATION SETS ARE NEW AND WERE WRITTEN AFTER THIS GENERATOR WAS FROZEN. Still on
`discontinue-iv`, never on the 80 rows W5 scored: new openings, new value pools, new windows, the
condition asked both ways and stated both ways. The v2 gate asserts that no v2 evaluation case is a
v1 evaluation case. W5's sets stay on disk as a regression check and are never evidence again.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from memory.layers import render
from memory.notes import Library
from training.nursing import generate_walks as g1
from training.nursing.generate_walks import H, HELD_OUT, TRAINED, W, Case, Unreachable, _label, _numbers, _pick
from training.nursing.library import ROOT, SITE_RULES, SUB

OUT = Path("training/nursing/data_walks_v2")
FILES = {"train": OUT / "train.jsonl", "train_nolib": OUT / "train_nolib.jsonl",
         "eval_heldout": OUT / "eval_heldout.jsonl", "eval_control": OUT / "eval_control.jsonl"}
SEED = 20260920
N_ROWS = 600
MIX = (("carry", 0.42), ("conditional", 0.22), ("quantity", 0.08), ("rate", 0.16), ("none", 0.12))
DEAD_RATE = 0.40            # of the cases that begin with a search — fewer v2 cases do, so the share of rows holds
NO_RULES_RATE = 0.25        # of the cases: a unit with no added rule — the single-valued page survives
PHRASING = ("explicit", "implicit")


def _rule(name: str) -> tuple[list[str], str]:
    notes, text, _ = SITE_RULES[name]
    return [f"{SUB}/{n}" for n in notes], text


# ------------------------------------------------------------------ the conditional quantities
# plain / cond: (slot, pool, reserved pool). `plain_of`: the plain value is a W4 quantity (drawn by W4's
# own machinery, in whichever layer it picks). `rule`: the sentence comes from `library.SITE_RULES`.
# ask[asked][phrasing] = (a fact of the situation or "", the question). Invented wording throughout B.
CONDITIONALS = {
    "cap_seconds": {
        "unit": "seconds", "rule": "cap_soiled_seconds", "plain_of": "cap_seconds", "held_out": False,
        "cond": ("soiled_seconds", (50, 55, 70, 75, 90), (65, 80)),
        "steps": [f"{H}/primary-infusion/20-cleanse-cap", f"{H}/primary-infusion/23-cleanse-cap-again"],
        "wiki": f"{W}/asepsis/scrub-the-hub",
        "wiki_query": ["how long to scrub the cap of an IV port", "clean an IV port's cap: how long"],
        "parent_query": "keeping a port or an open end of tubing clean before touching it",
        "ask": {"plain": {"explicit": ("", "for how many seconds is a catheter cap that is not visibly soiled cleansed"),
                          "implicit": ("The catheter cap looks clean.", "for how many seconds is this cap cleansed")},
                "cond": {"explicit": ("", "for how many seconds is a catheter cap that is visibly soiled cleansed"),
                         "implicit": ("The catheter cap is visibly soiled.", "for how many seconds is this cap cleansed")}}},
    "flush_ml": {
        "unit": "mL", "rule": "flush_idle_ml", "plain_of": "flush_ml", "held_out": False,
        "cond": ("idle_ml", (12, 14, 15, 16, 20), (13, 18)),
        "steps": [f"{H}/primary-infusion/21-assess-patency"],
        "wiki": f"{W}/site-assessment/patency-flush",
        "wiki_query": ["saline flush to check that an IV catheter is open", "show an IV catheter is open before infusing"],
        "parent_query": "checking a patient's IV site before using it",
        "ask": {"plain": {"explicit": ("", "how much normal saline is injected to assess the patency of a catheter that was used during the previous shift"),
                          "implicit": ("The catheter was last used two hours ago.", "how much normal saline is injected to assess this catheter's patency")},
                "cond": {"explicit": ("", "how much normal saline is injected to assess the patency of a catheter that has not been used since the previous shift"),
                         "implicit": ("The catheter has not been used since the previous shift.", "how much normal saline is injected to assess this catheter's patency")}}},
    "yport_seconds": {
        "unit": "seconds", "rule": "yport_seconds", "held_out": False,
        "plain": ("yport_seconds", (10, 15, 20, 25), (12, 22)),
        "cond": ("yport_shared_seconds", (30, 40, 45, 50), (35, 55)),
        "steps": [f"{H}/secondary-infusion/16-back-prime"], "wiki": None,
        "ask": {"plain": {"explicit": ("", "for how many seconds is the y-port cleansed when the line is not shared with another infusion"),
                          "implicit": ("The primary line carries no other infusion.", "for how many seconds is the y-port cleansed")},
                "cond": {"explicit": ("", "for how many seconds is the y-port cleansed when the line is shared with another infusion"),
                         "implicit": ("The primary line is shared with another infusion.", "for how many seconds is the y-port cleansed")}}},
    "recheck_minutes": {
        "unit": "minutes", "rule": "recheck_minutes", "held_out": False,
        "plain": ("recheck_minutes", (20, 25, 30, 40, 45), (35, 50)),
        "cond": ("recheck_irritant_minutes", (5, 10, 15), (8, 12)),
        "steps": [f"{H}/secondary-infusion/20-assess-site-after"], "wiki": None,
        "ask": {"plain": {"explicit": ("", "how many minutes after the infusion begins is the site assessed again, for a medication the pharmacy does not label an irritant"),
                          "implicit": ("The pharmacy label carries no irritant warning.", "how many minutes after the infusion begins is the site assessed again")},
                "cond": {"explicit": ("", "how many minutes after the infusion begins is the site assessed again, for a medication the pharmacy labels an irritant"),
                         "implicit": ("The pharmacy labels this medication an irritant.", "how many minutes after the infusion begins is the site assessed again")}}},
    # A — the real note. No added sentence: both values are the note's own slots. The micro-drip value is
    # a constant of the equipment and stays the textbook's; the macro-drip set is whichever a unit stocks.
    "drop_factor": {
        "unit": "drops per milliliter", "rule": None, "held_out": False,
        "plain": ("macrodrip_gtt", (10, 15), (20,)), "cond": ("microdrip_gtt", (), ()),   # 20 is the control's
        "fixed_cond": "60", "steps": [], "wiki": f"{W}/rates/drop-factor", "notes": [f"{W}/rates/drop-factor"],
        "wiki_query": ["drop factor of a tubing set", "the drop factor of this tubing set"],
        "parent_query": "turning an order into a number to set on a pump or a clamp",
        "ask": {"plain": {"explicit": ("", "What is the drop factor of the macro-drip sets"),
                          "implicit": ("Routine adult maintenance fluids are to run by gravity through a macro-drip set.", "What is this set's drop factor")},
                "cond": {"explicit": ("", "What is the drop factor of a micro-drip set"),
                         "implicit": ("A small volume is to run slowly by gravity through a micro-drip set.", "What is this set's drop factor")}}},
    # the held-out two-valued notes — evaluation only. Pools are NEW: W5's were (4,6,8,9,12) / (11,13,15,20,25).
    "hold_pressure": {
        "unit": "minutes", "rule": None, "held_out": True,
        "plain": ("minutes", (3, 5, 7, 10), ()), "cond": ("anticoagulant_minutes", (14, 16, 18, 22, 30), ()),
        "textbook": {"minutes": "2-3", "anticoagulant_minutes": "5-10"},
        "steps": [f"{HELD_OUT}/07-hold-pressure"], "wiki": f"{W}/removal/pressure-after-removal",
        "notes": [f"{HELD_OUT}/07-hold-pressure", f"{W}/removal/pressure-after-removal"],
        "wiki_query": ["how long to press on the site after an IV is taken out", "press on a site after an IV comes out"],
        "parent_query": "principles when a catheter is coming out",
        "ask": {"plain": {"explicit": ("", "for how long, in minutes, is pressure kept on the site when the patient takes no anticoagulant medication"),
                          "implicit": ("The patient takes no anticoagulant medication.", "for how long, in minutes, is pressure kept on this patient's site")},
                "cond": {"explicit": ("", "for how long, in minutes, is pressure kept on the site when the patient takes anticoagulant medication"),
                         "implicit": ("The patient takes anticoagulant medication.", "for how long, in minutes, is pressure kept on this patient's site")}}},
}
TRAINED_CONDITIONALS = [k for k, v in CONDITIONALS.items() if not v["held_out"]]

# NEW openings — W5's evaluation used `generate_walks.OPENINGS`; none of these sentences is in it.
OPENINGS_V2 = {
    **g1.OPENINGS,
    HELD_OUT: [
        ("The infusion therapy is finished and the peripheral catheter in the patient's arm is to be removed",
         "remove a peripheral catheter, therapy finished"),
        ("A peripheral IV has been ordered out because the patient no longer needs IV access",
         "peripheral IV ordered out, IV access no longer needed"),
        ("Before transfer, the patient's peripheral IV line is to be discontinued",
         "discontinue a patient's peripheral IV line"),
    ],
}
NOT_HELD_V2 = [      # the v2 control's topics — in neither W4's corpus list nor W5's control
    ("A patient needs a capillary blood glucose reading before a meal", "take a capillary blood glucose reading"),
    ("A pressure injury on the heel needs staging and a dressing", "stage and dress a pressure injury"),
    ("A patient is to be fitted with sequential compression devices", "apply sequential compression devices"),
    ("An ostomy pouch is leaking and must be changed", "change an ostomy pouch"),
]


def _notes_of(spec: dict) -> list[str]:
    return spec.get("notes") or _rule(spec["rule"])[0]


# ------------------------------------------------------------------ drawing a case's conditional world
def draw_rules(rng: random.Random, avoid: set[str], plain_drawn: dict, eval_set: str | None,
               rules: bool = True) -> tuple[dict, dict, dict, dict]:
    """Every trained conditional is drawn for every case, so any page a walk crosses shows this
    case's values. Returns (site overrides, case values, site adds, {name: {plain, cond, layer}})."""
    over, case, adds, drawn = {}, {}, {}, {}
    for name in TRAINED_CONDITIONALS:
        spec = CONDITIONALS[name]
        if spec["rule"] and not rules:
            continue
        layer = "site" if rng.random() < 0.6 else "case"
        vals = {}
        taken = set(avoid)
        if spec.get("plain_of"):
            taken |= _numbers(plain_drawn[spec["plain_of"]][0])
        for role in ("plain", "cond"):
            if role not in spec or (role == "plain" and spec.get("plain_of")):
                continue
            slot, pool, reserved = spec[role]
            if role == "cond" and spec.get("fixed_cond"):
                vals[slot] = None                     # the textbook's own value stays
                continue
            pick = [v for v in (reserved if (eval_set == "control" and reserved) else pool) if str(v) not in taken]
            # a control case whose statement states every reserved value falls back to the corpus's pool:
            # G2 (the walk WITH its values is not in the corpus) still decides whether it is a new case
            pick = pick or [v for v in pool if str(v) not in taken]
            if not pick:
                raise ValueError(f"no free value for {name}.{slot} given {sorted(taken)}")
            vals[slot] = rng.choice(pick)
            taken.add(str(vals[slot]))
        for note in _notes_of(spec):
            if spec["rule"]:
                add = adds.setdefault(note, {"text": _rule(spec["rule"])[1]})
                for slot, v in vals.items():
                    add[slot] = v if layer == "site" else SITE_RULES[spec["rule"]][2][slot]
                    if layer == "case":
                        case.setdefault(note, {})[slot] = v
            else:
                for slot, v in vals.items():
                    if v is not None:
                        (over if layer == "site" else case).setdefault(note, {})[slot] = v
        drawn[name] = {"layer": layer, **{s: (str(v) if v is not None else spec.get("fixed_cond")) for s, v in vals.items()}}
    return over, case, adds, drawn


def _merge(a: dict | None, b: dict | None) -> dict | None:
    out = {k: dict(v) for k, v in (a or {}).items()}
    for k, v in (b or {}).items():
        out.setdefault(k, {}).update(v)
    return out or None


def with_rules(lib: Library, c: Case, rng: random.Random, eval_set: str | None, rules: bool) -> Case:
    """A W4 case, in a world that also has the conditional rules. The last step's body is rendered
    again: a sentence the site added to it is part of what 'as the library states it' means."""
    avoid = _numbers(c.statement) | set(c.givens) | _numbers(c.answer if c.family != "carry" else "") \
        | _numbers(str(c.meta.get("calc", "")))
    plain = {k: v for k, v in (c.meta.get("drawn") or {}).items()}
    over, case, adds, drawn = draw_rules(rng, avoid, plain, eval_set, rules)
    c.site, c.case, c.adds = _merge(c.site, over), _merge(c.case, case), (adds or None)
    c.meta["rules"] = drawn
    if c.family == "carry":
        last = lib[c.walk[-1]]
        body = render(last, g1.site_of(c.site, c.adds), (c.case or {}).get(last.id))
        c.answer, c.check = f"Last step carried out: {body}", {"kind": "body", "body": body}
    return c


# ------------------------------------------------------------------ the new family
def conditional_case(lib, rng, cid, name, asked, variant, phrasing, eval_set=None, searcher=None,
                     dead_rate=g1.DEAD_END_RATE, specs=None, openings=None) -> Case:
    """`specs` / `openings`: a later evaluation set asks the same quantities in NEW words, from NEW value
    pools, under NEW openings (W5d). Left out, this is W5c's generator byte for byte."""
    spec = (specs or CONDITIONALS)[name]
    fact, ask = spec["ask"][asked][phrasing]
    plan, dead, carried, proc = [], False, [], None
    if variant == "step":
        target = rng.choice(spec["steps"])
        proc = target.rsplit("/", 1)[0]
        steps = lib.walk(proc)
        k = steps.index(target)
        opening = rng.choice((openings or OPENINGS_V2)[proc])[0]
        carried = steps[:k]
        statement = (f"{opening}. {fact + ' ' if fact else ''}The record shows steps 1 to {k} done — the last was "
                     f"'{_label(steps[k - 1])}'. On this unit and for this order, {ask}? Carry out the step and answer "
                     "with the quantity and its unit.")
        plan = [("open", target)]
    else:
        target = spec["wiki"]
        statement = f"{fact + ' ' if fact else ''}{ask}, on this unit? Answer with the quantity and its unit."
        if rng.random() < dead_rate:
            plan += g1.dead_end(lib, rng, "wiki", spec["wiki_query"][0], {target, lib[target].parent}, searcher)
            dead = bool(plan)
        if variant == "wiki-parent":
            parent = lib[target].parent
            plan += g1.reach(lib, parent, "wiki", [spec["parent_query"], lib[parent].title], searcher)
            plan += [("open", parent), ("open", target)]
        else:
            plan += g1.reach(lib, target, "wiki", spec["wiki_query"], searcher) + [("open", target)]
    avoid = _numbers(statement)
    which = "heldout" if spec["held_out"] else "trained"
    site, case, plain_drawn = g1._draw_quantities(rng, which, avoid, eval_set) if not spec["held_out"] else (None, None, {})
    adds = None
    if spec["held_out"]:
        layer = _pick(rng, g1.LAYERS)
        vals = {}
        for role in ("plain", "cond"):
            slot, pool, _ = spec[role]
            vals[slot] = spec["textbook"][slot] if layer == "textbook" else rng.choice([v for v in pool if str(v) not in avoid])
        if layer != "textbook":
            dest = {n: dict(vals) for n in spec["notes"]}
            site, case = (dest, None) if layer == "site" else (None, dest)
        rules = {name: {"layer": layer, **{s: str(v) for s, v in vals.items()}}}
    else:
        over, case2, adds, rules = draw_rules(rng, avoid, plain_drawn, eval_set, True)
        site, case = _merge(site, over), _merge(case, case2)
    if asked == "plain" and spec.get("plain_of"):
        value, layer = plain_drawn[spec["plain_of"]]
    else:
        value, layer = rules[name][spec["plain" if asked == "plain" else "cond"][0]], rules[name]["layer"]
    if _numbers(statement) & _numbers(value):
        raise ValueError(f"{cid}: the statement states the value it asks for")
    page = render(lib[target], g1.site_of(site, adds), (case or {}).get(target), mark=False)
    shown = [n for n in g1.re.findall(r"\d+(?:\.\d+)?", page)]
    return Case(id=cid, family="conditional", variant=variant, procedure=proc, statement=statement,
                carried=carried, plan=plan, answer=f"{value} {spec['unit']}",
                check={"kind": "value", "value": value, "unit": spec["unit"]}, site=site, case=case, adds=adds or None,
                seed=rng.randrange(10**9), dead_end=dead,
                meta={"quantity": name, "asked": "conditional" if asked == "cond" else "plain", "phrasing": phrasing,
                      "layer": layer, "rules": rules, "drawn": plain_drawn,
                      "first_number_on_the_page_is_the_answer": bool(shown) and shown[0] in _numbers(value)})


# ------------------------------------------------------------------ the corpus
def reserved_windows(lib: Library) -> set[tuple[str, int, int]]:
    rng = random.Random(SEED + 1)
    every = [(p, k, m) for p in TRAINED for k in range(len(lib.walk(p))) for m in g1.DEPTHS if k + m <= len(lib.walk(p))]
    return set(rng.sample(every, 24))


def _variants(spec: dict):
    return (("step", .5), ("wiki", .3), ("wiki-parent", .2)) if (spec["steps"] and spec["wiki"]) else \
        ((("step", 1.0),) if spec["steps"] else (("wiki", .6), ("wiki-parent", .4)))


def corpus_cases(lib: Library, n: int = N_ROWS, seed: int = SEED, searcher=None) -> tuple[list[Case], dict]:
    rng = random.Random(seed)
    reserved = reserved_windows(lib)
    topics = g1.NOT_HELD[:-g1.NOT_HELD_RESERVED]
    out, seen, per_walk, turn = [], set(), {}, 0
    dropped = {"unreachable": 0, "duplicate": 0, "walk_cap": 0, "too_long": 0, "value_clash": 0, "drawn": 0}
    while len(out) < n:
        dropped["drawn"] += 1
        if dropped["drawn"] > 40 * n:
            raise RuntimeError(f"cannot fill {n} rows: {dropped}")
        family, cid = _pick(rng, MIX), f"w5c-t{len(out):04d}"
        rules = rng.random() >= NO_RULES_RATE
        try:
            if family == "carry":
                proc = rng.choice(TRAINED)
                steps = lib.walk(proc)
                m = rng.choice(g1.DEPTHS)
                k = 0 if rng.random() < 0.35 else rng.randrange(1, len(steps) - m + 1)
                if (proc, k, m) in reserved:
                    continue
                c = with_rules(lib, g1.carry_case(lib, rng, cid, proc, k, m, searcher=searcher, dead_rate=DEAD_RATE), rng, None, rules)
            elif family == "conditional":
                name = TRAINED_CONDITIONALS[turn % len(TRAINED_CONDITIONALS)]
                asked, phrasing = ("plain", "cond")[(turn // len(TRAINED_CONDITIONALS)) % 2], PHRASING[(turn // 2) % 2]
                turn += 1
                c = conditional_case(lib, rng, cid, name, asked, _pick(rng, _variants(CONDITIONALS[name])), phrasing,
                                     searcher=searcher, dead_rate=DEAD_RATE)
            elif family == "quantity":          # the single-valued page, in a unit with no added rule
                name = rng.choice([q for q, v in g1.QUANTITIES.items() if not v["held_out"]])
                c = g1.quantity_case(lib, rng, cid, name, _pick(rng, (("step", .45), ("wiki", .35), ("wiki-parent", .2))),
                                     searcher=searcher, dead_rate=DEAD_RATE)
                c = with_rules(lib, c, rng, None, False)
            elif family == "rate":
                c = g1.rate_case(lib, rng, cid, rng.choice(("gravity", "pump")),
                                 _pick(rng, (("step", .4), ("wiki", .4), ("wiki-parent", .2))), searcher=searcher,
                                 dead_rate=DEAD_RATE)
                c = with_rules(lib, c, rng, None, rules)
            else:
                c = g1.none_case(lib, rng, cid, rng.choice(topics), searcher=searcher)
        except Unreachable:
            dropped["unreachable"] += 1
            continue
        except ValueError:                  # every free value of a pool is a number the statement states
            dropped["value_clash"] += 1
            continue
        g1.check_not_held_out(lib, c)
        key = (g1.signature(c), c.statement, json.dumps(c.adds, sort_keys=True))
        if key in seen:
            dropped["duplicate"] += 1
            continue
        w = (c.family, tuple(c.walk), tuple(c.givens), c.meta.get("topic"), c.variant if c.family == "none" else None)
        if c.family in ("carry", "none") and per_walk.get(w, 0) >= g1.MAX_SAME_WALK:
            dropped["walk_cap"] += 1
            continue
        seen.add(key); per_walk[w] = per_walk.get(w, 0) + 1
        out.append(c)
    return out, dropped


# ------------------------------------------------------------------ the NEW evaluation sets
def eval_cases(lib: Library, seed: int = SEED + 7, searcher=None) -> dict[str, list[Case]]:
    """Written after `corpus_cases` above was frozen. Every held-out row is within the trained depth
    (W5 kept two deeper rows aside as a second unknown; v2 does not draw them at all)."""
    rng = random.Random(seed)
    held, steps = [], lib.walk(HELD_OUT)
    hid = lambda: f"w5ch-{len(held):03d}"
    for m in (1, 2, 3, 5, 8):
        for _ in range(3):
            held.append(g1.carry_case(lib, rng, hid(), HELD_OUT, 0, m, "heldout", searcher, 0.0, openings=OPENINGS_V2))
    for k in range(1, len(steps)):
        for m in (1, 2, 3, 4):
            if k + m <= len(steps):
                held.append(g1.carry_case(lib, rng, hid(), HELD_OUT, k, m, "heldout", searcher, 0.0, openings=OPENINGS_V2))
    i = 0
    for asked in ("plain", "cond"):
        for variant in ("step",) * 8 + ("wiki",) * 4 + ("wiki-parent",) * 4:
            held.append(conditional_case(lib, rng, hid(), "hold_pressure", asked, variant, PHRASING[i % 2],
                                         "heldout", searcher, 0.0))
            i += 1
    shared = g1._shared_lines()
    for c in held:
        c.meta["final_is_a_shared_line"] = bool(c.walk) and c.walk[-1] in shared
    control = []
    cid = lambda: f"w5cc-{len(control):03d}"
    for p, k, m in sorted(reserved_windows(lib)):
        control.append(with_rules(lib, g1.carry_case(lib, rng, cid(), p, k, m, "control", searcher, 0.0), rng, "control", True))
    i = 0
    for name in TRAINED_CONDITIONALS:
        spec = CONDITIONALS[name]
        kinds = [v for v, _ in _variants(spec)]
        for asked in ("plain", "cond"):
            for j in range(4):
                control.append(conditional_case(lib, rng, cid(), name, asked, kinds[j % len(kinds)], PHRASING[i % 2],
                                                "control", searcher, 0.0))
                i += 1
    for kind in ("gravity", "pump"):
        for variant in ("step",) * 3 + ("wiki",) * 3 + ("wiki-parent",) * 2:
            control.append(with_rules(lib, g1.rate_case(lib, rng, cid(), kind, variant, "control", searcher, 0.0),
                                      rng, "control", True))
    for topic in NOT_HELD_V2:
        for _ in range(2):
            control.append(g1.none_case(lib, rng, cid(), topic, searcher))
    return {"eval_heldout": g1._dedupe(held), "eval_control": g1._dedupe(control)}


def build(lib: Library | None = None, searcher=None) -> tuple[dict[str, list[dict]], dict]:
    lib = lib or Library.load(ROOT)
    cases, dropped = corpus_cases(lib, searcher=searcher)
    rows = [g1.row(lib, c, searcher) for c in cases]
    sets = {"train": rows, "train_nolib": [g1.nolib_row(r) for r in rows]}
    v1 = _v1_eval_worlds()
    for name, cs in eval_cases(lib, searcher=searcher).items():
        rs = [g1.row(lib, c, searcher) for c in cs]
        sets[name] = [r for r in rs if r["statement"] not in v1["statements"] and _world(r) not in v1["worlds"]]
        dropped[f"{name}_was_a_v1_case"] = len(rs) - len(sets[name])
    return sets, dropped


# ------------------------------------------------------------------ the v2 gate
def _world(r: dict) -> tuple:
    return (r["statement"], tuple(r["values_read"]))


def _v1_eval_worlds() -> dict:
    rows = [json.loads(l) for k in ("eval_heldout", "eval_control") for l in g1.FILES[k].read_text().splitlines()]
    return {"worlds": {_world(r) for r in rows}, "signatures": {r["signature"] for r in rows},
            "statements": {r["statement"] for r in rows}}


def balance(rows: list[dict]) -> dict:
    """How much 'copy the first number on the page' is worth on the conditional rows."""
    rs = [r for r in rows if r["family"] == "conditional"]
    n = len(rs) or 1
    return {"n": len(rs), "asked_conditional": sum(r["meta"]["asked"] == "conditional" for r in rs),
            "first_number_is_the_answer": sum(bool(r["meta"]["first_number_on_the_page_is_the_answer"]) for r in rs),
            "share_first_number": round(sum(bool(r["meta"]["first_number_on_the_page_is_the_answer"]) for r in rs) / n, 3),
            "implicit": sum(r["meta"]["phrasing"] == "implicit" for r in rs),
            "notes": sorted({r["walk"][-1].replace(f"{SUB}/", "") for r in rs}),
            "by_quantity": {q: sum(r["meta"]["quantity"] == q for r in rs) for q in sorted({r["meta"]["quantity"] for r in rs})}}


def gate(sets: dict | None = None, lib: Library | None = None, dropped: dict | None = None, searcher=None) -> dict:
    lib = lib or Library.load(ROOT)
    if sets is None:
        sets = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in FILES.items()}
    g = g1.gate(sets, lib, dropped, searcher)               # W4's clauses G1–G4, the twin, the suite gates
    v1 = _v1_eval_worlds()
    # A 14-step procedure has finitely many windows and W5 walked most of them: what makes a v2 case NEW
    # is its statement (new openings, new asks) and its world (new value pools) — never the window alone.
    g5 = {r["case_id"]: "a W5 (v1) evaluation case" for k in ("eval_heldout", "eval_control") for r in sets[k]
          if _world(r) in v1["worlds"] or r["statement"] in v1["statements"]}
    bal = {k: balance(sets[k]) for k in ("train", "eval_heldout", "eval_control")}
    half = lambda b: b["n"] and abs(b["asked_conditional"] / b["n"] - .5) <= .06 and .40 <= b["share_first_number"] <= .60
    trained_notes = bal["train"]["notes"]
    g6 = {k: b for k, b in bal.items() if not half(b)}
    g7_ok = (len(trained_notes) >= 5 and any("primary-infusion" in n for n in trained_notes)
             and any("secondary-infusion" in n for n in trained_notes) and any(n.startswith("wiki/") for n in trained_notes))
    real = sum(r["meta"]["quantity"] == "drop_factor" for r in sets["train"] if r["family"] == "conditional")
    g["G5_is_a_v1_evaluation_case"] = g5
    g["G6_copying_the_first_number_is_not_worth_half"] = g6
    g["G7_the_shape_is_met_in_several_notes_of_both_procedures"] = {"ok": g7_ok, "notes": trained_notes}
    g["conditional_balance"] = bal
    g["conditional_rows_on_the_real_note"] = real
    g["conditional_rows_on_invented_site_rules"] = bal["train"]["n"] - real
    g["rows_in_a_unit_with_no_added_rule"] = sum(1 for r in sets["train"] if not r["replay"].get("adds"))
    g["redesign_count"] = g1.REDESIGN_COUNT
    g["redesign_note"] = ("carried from W4/W5 unchanged: v2 is a new ARM of the experiment (a corpus and a held-out "
                          "set), not a redesign of the grader, the verdict or the instrument")
    g["passed"] = bool(g["passed"] and not g5 and not g6 and g7_ok)
    return g


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    lib = Library.load(ROOT)
    sets, dropped = build(lib)
    text = {k: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in v) for k, v in sets.items()}
    if "--check" in argv:
        drift = [str(FILES[k]) for k in FILES if not FILES[k].exists() or FILES[k].read_text() != text[k]]
        print(f"[walks] v2 {'drifted: ' + ', '.join(drift) if drift else 'files on disk are what the generator writes'}", flush=True)
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
    b = g["conditional_balance"]["train"]
    print(f"[walks] v2 gate: rows {g['rows']} · G1 {len(g['G1_value_in_statement'])} G2 "
          f"{len(g['G2_evaluated_walk_in_corpus'])} G3 {len(g['G3_held_out_opened'])} G4 "
          f"{len(g['G4_not_accepted_by_the_referee'])} G5 {len(g['G5_is_a_v1_evaluation_case'])} · conditional "
          f"{b['n']} rows, first-number share {b['share_first_number']} · {'PASSED' if g['passed'] else 'FAILED'}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
