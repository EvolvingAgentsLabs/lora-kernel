r"""W5d — the evaluation sets the answer policy's CLAIM is read on. Written AFTER the policy was frozen.

    python -m training.nursing.generate_walks_w5d                  # write the two sets
    python -m training.nursing.generate_walks_w5d --check          # exit 1 if the files on disk have drifted
    python -m training.nursing.generate_walks_w5d --gate out.json  # the gate

THE ORDER IS THE POINT. `answer_policy.WRITER` and `answer_policy.kind` were committed first (the brief
cites the hash); these cases were drawn afterwards, and nothing here was iterated against a model — no
model has seen them. *A set the designer has iterated against is a training set.*

NOTHING IS TRAINED ON THIS: there is no `train.jsonl` here. The adapter that walks these cases is
W5c's, trained on `data_walks_v2/train.jsonl`; the gate below checks the new cases against THAT corpus.

WHAT MAKES A CASE NEW. The held-out procedure has fourteen steps and W5 and W5c walked most of its
windows, so a window cannot be new. A case is its STATEMENT and its WORLD (`generate_walks.gate`): here
every opening sentence is new (all three procedures), every conditional quantity is asked in new words
both ways and stated both ways, the held-out note's two values come from pools neither W5
(4,6,8,9,12 / 11,13,15,20,25) nor W5c (3,5,7,10 / 14,16,18,22,30) drew from, the not-in-library topics
are new, and the seed is new. Any row whose statement or world W5 or W5c evaluated is DROPPED and
counted, and the gate asserts none is left. The machinery is W5c's by import, not by copy: rows are
rendered by the runtime inside the corpus-mode loop, ids are re-drawn per conversation.

THE ASKS STILL CLOSE ON THE GENERATOR'S OWN SENTENCE ("Answer with the quantity and its unit."), which
is what `answer_policy.kind` reads. That is the caveat the brief states about the classifier, and it is
asserted here rather than hidden: `kind()` must agree with `family` on every row, or the gate fails.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

from memory.notes import Library
from training.nursing import answer_policy as ap
from training.nursing import generate_walks as g1
from training.nursing import generate_walks_v2 as g2
from training.nursing.generate_walks import H, HELD_OUT
from training.nursing.library import ROOT

OUT = Path("training/nursing/data_walks_w5d")
FILES = {"eval_heldout": OUT / "eval_heldout.jsonl", "eval_control": OUT / "eval_control.jsonl"}
SEED = 20260921
PRIOR_EVAL = [g1.FILES["eval_heldout"], g1.FILES["eval_control"], g2.FILES["eval_heldout"], g2.FILES["eval_control"]]
PRIOR_TRAIN = [g1.FILES["train"], g2.FILES["train"]]

OPENINGS = {
    f"{H}/primary-infusion": [
        ("Maintenance IV fluids have been ordered and the patient's peripheral IV is patent and ready",
         "start ordered maintenance IV fluids through a patent peripheral IV"),
        ("A new order for continuous IV fluids is to be started on a patient who already has IV access",
         "start a new order of continuous IV fluids, IV access in place"),
        ("The patient's ordered bag of primary IV fluids is ready to be hung and started",
         "hang and start a primary bag of ordered IV fluids"),
    ],
    f"{H}/secondary-infusion": [
        ("A piggyback dose of IV medication is due for a patient whose primary fluids are running",
         "piggyback IV medication dose due, primary fluids running"),
        ("The pharmacy has sent up a secondary bag of medication to run through the patient's existing primary line",
         "run a secondary bag of medication through an existing primary line"),
        ("An ordered IV medication is to be given as a secondary infusion on the running primary tubing",
         "give an ordered IV medication as a secondary infusion"),
    ],
    HELD_OUT: [
        ("The patient is being discharged today and the peripheral IV has to be taken out first",
         "take out a peripheral IV before discharge"),
        ("The order says to discontinue the peripheral IV now that the patient is on oral medication",
         "discontinue a peripheral IV, patient on oral medication"),
        ("The peripheral catheter is no longer in use and is to be removed this shift",
         "remove a peripheral catheter that is no longer in use"),
    ],
}
NOT_HELD = [      # in neither corpus's topic list, nor W5's control, nor W5c's
    ("A patient needs a bladder scan after voiding", "perform a bladder scan"),
    ("A patient in a cast needs a neurovascular check of the limb", "neurovascular check of a casted limb"),
    ("An enteral feeding has been stopped and must be restarted through the pump", "restart an enteral tube feeding"),
    ("A patient needs help measuring peak expiratory flow", "measure peak expiratory flow"),
]

# The same six quantities, asked in NEW words. ask[asked][phrasing] = (a fact of the situation or "", the question).
ASKS = {
    "cap_seconds": {
        "plain": {"explicit": ("", "how many seconds of cleansing does a catheter cap with no visible soiling get"),
                  "implicit": ("Nothing can be seen on the catheter cap.", "how many seconds of cleansing does this cap get")},
        "cond": {"explicit": ("", "how many seconds of cleansing does a catheter cap with visible soiling get"),
                 "implicit": ("The catheter cap has visible soiling on it.", "how many seconds of cleansing does this cap get")}},
    "flush_ml": {
        "plain": {"explicit": ("", "what volume of normal saline checks the patency of a catheter that was in use earlier this shift"),
                  "implicit": ("The catheter was in use an hour ago.", "what volume of normal saline checks this catheter's patency")},
        "cond": {"explicit": ("", "what volume of normal saline checks the patency of a catheter nobody has used since the previous shift"),
                 "implicit": ("Nobody has used the catheter since the previous shift.", "what volume of normal saline checks this catheter's patency")}},
    "yport_seconds": {
        "plain": {"explicit": ("", "how many seconds is the y-port scrubbed when no other infusion shares the line"),
                  "implicit": ("No other infusion runs through the primary line.", "how many seconds is the y-port scrubbed")},
        "cond": {"explicit": ("", "how many seconds is the y-port scrubbed when another infusion shares the line"),
                 "implicit": ("Another infusion shares the primary line.", "how many seconds is the y-port scrubbed")}},
    "recheck_minutes": {
        "plain": {"explicit": ("", "after how many minutes of infusion is the site checked again, when the pharmacy label has no irritant warning"),
                  "implicit": ("There is no irritant warning on the pharmacy label.", "after how many minutes of infusion is the site checked again")},
        "cond": {"explicit": ("", "after how many minutes of infusion is the site checked again, when the pharmacy label warns that the medication is an irritant"),
                 "implicit": ("The pharmacy label warns that this medication is an irritant.", "after how many minutes of infusion is the site checked again")}},
    "drop_factor": {
        "plain": {"explicit": ("", "What drop factor do the macro-drip sets have"),
                  "implicit": ("Maintenance fluids for an adult are to run by gravity through a macro-drip set.", "What drop factor does this set have")},
        "cond": {"explicit": ("", "What drop factor does a micro-drip set have"),
                 "implicit": ("A small volume is to be given slowly by gravity through a micro-drip set.", "What drop factor does this set have")}},
    "hold_pressure": {
        "plain": {"explicit": ("", "how many minutes of pressure does the site get when the patient is not on an anticoagulant"),
                  "implicit": ("The patient is not on any anticoagulant.", "how many minutes of pressure does this patient's site get")},
        "cond": {"explicit": ("", "how many minutes of pressure does the site get when the patient is on an anticoagulant"),
                 "implicit": ("The patient is on an anticoagulant.", "how many minutes of pressure does this patient's site get")}},
}
HOLD_POOLS = {"plain": (1, 2, 17, 19), "cond": (21, 23, 24, 26, 27, 28, 35)}     # in neither W5's pools nor W5c's


def specs() -> dict:
    s = copy.deepcopy(g2.CONDITIONALS)
    for name, ask in ASKS.items():
        s[name]["ask"] = ask
    for role, pool in HOLD_POOLS.items():
        slot, _, reserved = s["hold_pressure"][role]
        s["hold_pressure"][role] = (slot, pool, reserved)
    return s


def eval_cases(lib: Library, seed: int = SEED, searcher=None) -> dict[str, list]:
    rng, sp = random.Random(seed), specs()
    held, steps = [], lib.walk(HELD_OUT)
    hid = lambda: f"w5dh-{len(held):03d}"
    for m in (1, 2, 3, 5, 8):
        for _ in range(3):
            held.append(g1.carry_case(lib, rng, hid(), HELD_OUT, 0, m, "heldout", searcher, 0.0, openings=OPENINGS))
    for k in range(1, len(steps)):
        for m in (1, 2, 3, 4):
            if k + m <= len(steps):
                held.append(g1.carry_case(lib, rng, hid(), HELD_OUT, k, m, "heldout", searcher, 0.0, openings=OPENINGS))
    i = 0
    for asked in ("plain", "cond"):
        for variant in ("step",) * 8 + ("wiki",) * 4 + ("wiki-parent",) * 4:
            held.append(g2.conditional_case(lib, rng, hid(), "hold_pressure", asked, variant, g2.PHRASING[i % 2],
                                            "heldout", searcher, 0.0, specs=sp, openings=OPENINGS))
            i += 1
    shared = g1._shared_lines()
    for c in held:
        c.meta["final_is_a_shared_line"] = bool(c.walk) and c.walk[-1] in shared
    control = []
    cid = lambda: f"w5dc-{len(control):03d}"
    for p, k, m in sorted(g2.reserved_windows(lib)):          # the windows W5c's corpus never walked
        control.append(g2.with_rules(lib, g1.carry_case(lib, rng, cid(), p, k, m, "control", searcher, 0.0, openings=OPENINGS),
                                     rng, "control", True))
    i = 0
    for name in g2.TRAINED_CONDITIONALS:
        kinds = [v for v, _ in g2._variants(sp[name])]
        for asked in ("plain", "cond"):
            for j in range(4):
                control.append(g2.conditional_case(lib, rng, cid(), name, asked, kinds[j % len(kinds)], g2.PHRASING[i % 2],
                                                   "control", searcher, 0.0, specs=sp, openings=OPENINGS))
                i += 1
    for kind in ("gravity", "pump"):
        for variant in ("step",) * 3 + ("wiki",) * 3 + ("wiki-parent",) * 2:
            control.append(g2.with_rules(lib, g1.rate_case(lib, rng, cid(), kind, variant, "control", searcher, 0.0, openings=OPENINGS),
                                         rng, "control", True))
    for topic in NOT_HELD:
        for _ in range(2):
            control.append(g1.none_case(lib, rng, cid(), topic, searcher))
    return {"eval_heldout": g1._dedupe(held), "eval_control": g1._dedupe(control)}


def _world(r: dict) -> tuple:
    return (r["statement"], tuple(r["values_read"]))


def _prior() -> dict:
    ev = [json.loads(l) for p in PRIOR_EVAL for l in p.read_text().splitlines()]
    tr = [json.loads(l) for p in PRIOR_TRAIN for l in p.read_text().splitlines()]
    return {"eval_statements": {r["statement"] for r in ev}, "eval_worlds": {_world(r) for r in ev},
            "train_statements": {r["statement"] for r in tr}, "train_worlds": {_world(r) for r in tr}}


def _seen(r: dict, prior: dict) -> str | None:
    if r["statement"] in prior["eval_statements"] or _world(r) in prior["eval_worlds"]:
        return "a case W5 or W5c evaluated"
    if _world(r) in prior["train_worlds"]:
        return "its statement, with the values its notes show, is in a training corpus"
    return None


def build(lib: Library | None = None, searcher=None) -> tuple[dict[str, list[dict]], dict]:
    lib = lib or Library.load(ROOT)
    prior, sets, dropped = _prior(), {}, {}
    for name, cs in eval_cases(lib, searcher=searcher).items():
        rows = [g1.row(lib, c, searcher) for c in cs]
        sets[name] = [r for r in rows if not _seen(r, prior)]
        dropped[f"{name}_seen_before"] = len(rows) - len(sets[name])
    return sets, dropped


def gate(sets: dict | None = None, lib: Library | None = None, dropped: dict | None = None, searcher=None) -> dict:
    lib = lib or Library.load(ROOT)
    if sets is None:
        sets = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in FILES.items()}
    v2 = {k: [json.loads(l) for l in g2.FILES[k].read_text().splitlines()] for k in ("train", "train_nolib")}
    # W4's clauses, against the corpus the walking adapter WAS trained on: no value in a statement (G1),
    # no evaluated walk or world in the corpus (G2), every row accepted by the referee in strict (G4).
    g = g1.gate({**v2, **sets}, lib, dropped, searcher)
    prior = _prior()
    g5 = {r["case_id"]: w for rs in sets.values() for r in rs if (w := _seen(r, prior))}
    openings = {s for v in (*g1.OPENINGS.values(), *g2.OPENINGS_V2.values()) for s, _ in v}
    g8 = [r["case_id"] for rs in sets.values() for r in rs if any(r["statement"].startswith(o) for o in openings)]
    kinds, g9 = {}, []
    for name, rs in sets.items():
        kinds[name] = {}
        for r in rs:
            k = ap.kind(r["statement"])
            kinds[name][k] = kinds[name].get(k, 0) + 1
            if k != ap.KIND_OF_FAMILY[r["family"]]:
                g9.append(r["case_id"])
    bal = {k: g2.balance(sets[k]) for k in sets}
    half = lambda b: b["n"] and abs(b["asked_conditional"] / b["n"] - .5) <= .06 and .40 <= b["share_first_number"] <= .60
    g6 = {k: b for k, b in bal.items() if not half(b)}
    held_values = sorted({v for r in sets["eval_heldout"] if r["family"] == "conditional" and r["meta"]["layer"] != "textbook"
                          for v in r["meta"]["rules"]["hold_pressure"].values() if str(v).isdigit()}, key=int)
    old_pools = {"4", "6", "8", "9", "12", "11", "13", "15", "20", "25", "3", "5", "7", "10", "14", "16", "18", "22", "30"}
    g["G5_seen_before_by_W5_or_W5c"] = g5
    g["G6_copying_the_first_number_is_not_worth_half"] = g6
    g["G8_opens_with_a_sentence_an_earlier_set_used"] = g8
    g["G9_kind_disagrees_with_the_generators_family"] = g9
    g["G10_held_out_values_from_an_earlier_pool"] = sorted(set(held_values) & old_pools)
    g["kinds_by_the_frozen_rule"] = kinds
    g["conditional_balance"] = bal
    g["held_out_values_drawn"] = held_values
    g["sizes"] = {k: len(v) for k, v in sets.items()}
    g["corpus_checked_against"] = str(g2.FILES["train"])
    g["redesign_count"] = g1.REDESIGN_COUNT
    g["redesign_note"] = "the instrument's count, carried unchanged: W5d is a new arm and a new set, the grader is untouched"
    g["passed"] = bool(g["passed"] and not g5 and not g6 and not g8 and not g9 and not g["G10_held_out_values_from_an_earlier_pool"])
    return g


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    lib = Library.load(ROOT)
    sets, dropped = build(lib)
    text = {k: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in v) for k, v in sets.items()}
    if "--check" in argv:
        drift = [str(FILES[k]) for k in FILES if not FILES[k].exists() or FILES[k].read_text() != text[k]]
        print(f"[walks] w5d {'drifted: ' + ', '.join(drift) if drift else 'files on disk are what the generator writes'}", flush=True)
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
    print(f"[walks] w5d gate: {g['sizes']} · G1 {len(g['G1_value_in_statement'])} G2 {len(g['G2_evaluated_walk_in_corpus'])} "
          f"G4 {len(g['G4_not_accepted_by_the_referee'])} G5 {len(g['G5_seen_before_by_W5_or_W5c'])} G8 "
          f"{len(g['G8_opens_with_a_sentence_an_earlier_set_used'])} G9 {len(g['G9_kind_disagrees_with_the_generators_family'])} · "
          f"{'PASSED' if g['passed'] else 'FAILED'}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
