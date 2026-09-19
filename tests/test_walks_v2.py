"""W5c — corpus v2 and what it stands on, all zero GPU.

THE SHAPE UNDER TEST. A note states a quantity q and a second value of it under a condition c:
    answer(q | c) = cond value      answer(q | ¬c) = plain value
W5 **[ran]**: an adapter whose corpus never showed that shape answered the conditional value 0 of 11
times on the held-out note and the plain one 11 of 12 — it had learned "copy the number". v2 asks each
half equally, so the policy "first number on the page" is worth

    P(first number is the answer) ≈ 1/2          (gate G6: within [0.40, 0.60])

and the shape is met in ≥ 5 notes of BOTH trained procedures (G7). Where the second value comes from:
one real sentence (`source.PROSE`, byte-checked) and sentences a site ADDS — invented example content,
marked as such wherever it lives.
"""
import json
import re
from pathlib import Path

import pytest

from memory import lint
from memory.layers import render, resolve, shown_slots
from memory.notes import Library, Site
from training.nursing import generate_walks as g1
from training.nursing import generate_walks_v2 as g2
from training.nursing import walks_arm as wa
from training.nursing.library import ROOT, SITE_RULES, SUB
from training.nursing.source import PROSE

LIB = Library.load(ROOT)
SETS = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in g2.FILES.items()}
CAP = f"{SUB}/harness/primary-infusion/20-cleanse-cap"


# ---------------------------------------------------------------- the layer: a site ADDS, never rewrites
def test_a_site_adds_a_sentence_with_its_own_slots_and_leaves_the_textbook_line_alone():
    site = LIB.sites["unit-4c"]
    plain, shown = render(LIB[CAP]), render(LIB[CAP], site)
    assert shown.startswith(plain) and shown != plain            # the source's line, then the site's
    assert "30 [site] seconds" in shown                           # the added value is marked as the site's
    assert resolve(LIB[CAP], site)["soiled_seconds"] == (30, "site")
    assert "soiled_seconds" in shown_slots(LIB[CAP], site) and "soiled_seconds" not in LIB[CAP].used_slots()
    # a case's value wins over the site's and is not marked
    assert "for 75 seconds" in render(LIB[CAP], site, {"soiled_seconds": 75})


def test_the_lint_refuses_an_added_sentence_that_is_not_whole(tmp_path):
    def findings(add: str) -> list:
        root = tmp_path / str(abs(hash(add)))
        for p in Path(ROOT).rglob("*.md"):
            q = root / p.relative_to(ROOT); q.parent.mkdir(parents=True, exist_ok=True); q.write_text(p.read_text())
        (root / "site" / "bad.md").write_text(f"---\nsite: bad\noverrides:\nadds:\n  {add}\n---\nx\n")
        return [f for f in lint.lint(root) if f[1] == "bad"]
    assert findings(f'{CAP}: {{text: "Scrub {{{{n}}}} seconds.", n: 9}}') == []
    assert any("gives it no value" in f[2] for f in findings(f'{CAP}: {{text: "Scrub {{{{n}}}} seconds."}}'))
    assert any("reuses the note's own slot" in f[2] for f in findings(f'{CAP}: {{text: "Scrub {{{{seconds}}}} s.", seconds: 9}}'))
    assert any("does not exist" in f[2] for f in findings(f'{SUB}/harness/nope: {{text: "x {{{{n}}}}", n: 1}}'))
    long = " ".join(["word"] * 160)
    assert any("over" in f[2] for f in findings(f'{CAP}: {{text: "{long} {{{{n}}}}", n: 1}}'))


def test_the_shipped_library_lints_clean_and_says_which_of_its_content_is_invented():
    assert lint.lint(ROOT) == []
    site = (Path(ROOT) / "site" / "unit-4c.md").read_text()
    assert "invented for this repository" in site and "nothing here is clinical guidance" in site
    assert "**The `site/` layers are invented.**" in (Path(ROOT) / "README.md").read_text()
    added = {a["text"] for a in LIB.sites["unit-4c"].adds.values()}
    assert added == {text for _, text, _ in SITE_RULES.values()}              # nothing added that the builder does not declare
    assert not LIB.sites["ward-7b"].adds                                      # W1's example site is as it was


def test_the_one_real_two_valued_note_is_the_sources_own_sentence():
    values, where = PROSE["drop factor"]
    note = LIB[f"{SUB}/wiki/iv-therapy/rates/drop-factor"]
    assert render(note) == f"{where} {values}"                                # the textbook layer gives the source back
    assert "10, 15, or 20 drops per milliliter" in values and "60 drops per milliliter" in values
    assert "CC BY 4.0" in note.source and "restating" not in note.source


def test_no_added_sentence_touches_the_held_out_procedure():
    held = g1.held_out_only(LIB)
    for s in LIB.sites.values():
        assert not (set(s.adds) & held)
    for notes, _, _ in SITE_RULES.values():
        assert all("discontinue-iv" not in n and "removal" not in n for n in notes)


# ---------------------------------------------------------------- the files are the generator's, and v1 is untouched
def test_the_v2_files_on_disk_are_what_the_generator_writes_and_v1_has_not_moved():
    assert g2.main(["--check"]) == 0
    assert g1.main(["--check"]) == 0


def test_the_v2_gate_passes_and_is_the_gate_on_disk():
    g = g2.gate(SETS, LIB)
    stored = json.loads(Path("results/M7-W5c-conditional-corpus-20260919/gate.json").read_text())
    assert g["passed"] and stored["passed"]
    for k in ("rows", "G1_value_in_statement", "G3_held_out_opened", "G5_is_a_v1_evaluation_case", "conditional_balance"):
        assert g[k] == stored[k], k
    assert g["redesign_count"] == g1.REDESIGN_COUNT == 2                      # a new arm; the instrument is not redesigned


def test_copying_the_first_number_on_the_page_is_worth_one_half():
    """Computed from the served text itself, not from the generator's own flag."""
    for name in ("train", "eval_heldout", "eval_control"):
        rows = [r for r in SETS[name] if r["family"] == "conditional"]
        hit = 0
        for r in rows:
            page = r["messages"][2]["content"].rsplit("</open>= ", 1)[1].split("\n")[0].replace("[site]", "")
            first = re.findall(r"\d+(?:\.\d+)?", page)[0]
            hit += first in re.findall(r"\d+(?:\.\d+)?", r["check"]["value"])
            assert bool(first in re.findall(r"\d+(?:\.\d+)?", r["check"]["value"])) == r["meta"]["first_number_on_the_page_is_the_answer"]
        assert 0.40 <= hit / len(rows) <= 0.60, (name, hit, len(rows))
        asked = sum(r["meta"]["asked"] == "conditional" for r in rows) / len(rows)
        assert abs(asked - 0.5) <= 0.06, (name, asked)


def test_the_condition_reaches_the_expert_both_ways():
    rows = [r for r in SETS["train"] if r["family"] == "conditional"]
    assert {r["meta"]["phrasing"] for r in rows} == {"explicit", "implicit"}
    for r in SETS["eval_heldout"]:
        if r["family"] == "conditional" and r["meta"]["phrasing"] == "implicit":
            assert re.search(r"The patient takes (no )?anticoagulant medication\.", r["statement"])
            assert "this patient's site" in r["statement"]


# ---------------------------------------------------------------- each clause can fail
def test_G5_fires_on_a_W5_evaluation_case():
    old = json.loads(g1.FILES["eval_heldout"].read_text().splitlines()[0])
    g = g2.gate({**SETS, "eval_heldout": SETS["eval_heldout"] + [old]}, LIB)
    assert old["case_id"] in g["G5_is_a_v1_evaluation_case"] and not g["passed"]


def test_G6_fires_when_only_one_half_is_asked():
    lop = [r for r in SETS["train"] if not (r["family"] == "conditional" and r["meta"]["asked"] == "conditional")]
    g = g2.gate({**SETS, "train": lop, "train_nolib": [g1.nolib_row(r) for r in lop]}, LIB)
    assert "train" in g["G6_copying_the_first_number_is_not_worth_half"] and not g["passed"]


def test_G7_fires_when_one_procedure_never_shows_the_shape():
    lop = [r for r in SETS["train"] if not (r["family"] == "conditional" and "secondary-infusion" in r["walk"][-1])]
    g = g2.gate({**SETS, "train": lop, "train_nolib": [g1.nolib_row(r) for r in lop]}, LIB)
    assert not g["G7_the_shape_is_met_in_several_notes_of_both_procedures"]["ok"] and not g["passed"]


def test_G1_fires_when_a_statement_states_a_value_the_added_sentence_supplies():
    r = json.loads(json.dumps(next(x for x in SETS["train"] if x["family"] == "conditional"
                                   and x["meta"]["quantity"] == "yport_seconds")))
    r["statement"] += f" (Someone said {r['check']['value']}.)"
    assert g1.leaks(r)                                                        # the added sentence's values are READ values


def test_the_held_out_notes_are_never_opened_and_the_generator_refuses_to():
    held = g1.held_out_only(LIB)
    assert not any(i in held for r in SETS["train"] for i in r["walk"] + r["replay"]["carried"])
    import random
    c = g2.conditional_case(LIB, random.Random(1), "x", "hold_pressure", "cond", "step", "explicit", "heldout", None, 0.0)
    with pytest.raises(g1.HeldOut):
        g1.check_not_held_out(LIB, c)


def test_every_v2_held_out_case_is_inside_the_trained_depth_and_new():
    v1 = {json.loads(l)["statement"] for k in ("eval_heldout", "eval_control") for l in g1.FILES[k].read_text().splitlines()}
    assert all(r["depth"] <= wa.MAX_TRAINED_DEPTH for r in SETS["eval_heldout"])
    assert not ({r["statement"] for k in ("eval_heldout", "eval_control") for r in SETS[k]} & v1)
    assert all(r["procedure"] in (None, g1.HELD_OUT) for r in SETS["eval_heldout"])


# ---------------------------------------------------------------- the runner, pointed at v2
def test_the_runner_is_parameterised_not_copied_and_W5_is_as_it_ran():
    before = (dict(wa.TRAINED), dict(wa.SETS))
    try:
        wa.configure("training/nursing/data_walks_v2", "v2")
        assert wa.TRAINED["withlib"] == {"corpus": "training/nursing/data_walks_v2/train.jsonl",
                                         "adapter": "adapters/nursing-walks-v2-q35"}
        assert wa.TRAINED["nolib"]["adapter"] == "adapters/nursing-walks-nolib-v2-q35"
        assert wa.SETS["heldout"] == g2.FILES["eval_heldout"]
    finally:
        wa.configure()
    assert (wa.TRAINED, wa.SETS) == before


def test_the_slices_and_the_floor_the_brief_quotes():
    sets = {"heldout": SETS["eval_heldout"], "control": SETS["eval_control"]}
    sl = wa.slices(sets)
    assert (len(sl["headline"]), len(sl["heldout_shared_line"]), len(sl["heldout_deeper_than_trained"])) == (66, 22, 0)
    assert (len(sl["heldout_quantity_conditional"]), len(sl["heldout_quantity_plain"])) == (15, 16)
    stored = json.loads(Path("results/M7-W5c-conditional-corpus-20260919/floor.json").read_text())["floor"]
    f = wa.floor(LIB, sets)
    both = {**f["heldout"]["records"], **f["control"]["records"]}
    for k, ids in sl.items():
        assert wa.summarise(both, ids)["credit"] == stored[k]["credit"], k
    brief = Path("results/M7-W5c-conditional-corpus-20260919/BRIEF.md").read_text()
    assert f"headline {stored['headline']['credit']} / 66" in brief and "61 of 66" in brief


def test_the_headroom_rule_is_W5s_at_56_and_scales_with_n():
    def v(credit, n):
        return wa.verdict({"analysis": {"summary": {"base-reads": {"headline": {"credit": credit, "scored": n, "errors": 0, "missing": 0}}},
                                        "pairs": {}}})["no_headroom"]
    assert v(51, 56) and not v(50, 56)            # W5: 45/56 → there was room
    assert v(61, 66) and not v(60, 66)


def test_the_W5_quantity_rows_say_which_value_they_asked():
    old = [json.loads(l) for l in g1.FILES["eval_heldout"].read_text().splitlines()]
    n = sum(wa.asked(r) == "conditional" for r in old if r["family"] == "quantity")
    assert n == sum(r["meta"].get("quantity") == "anticoagulant_minutes" for r in old) > 0


def test_the_falsifier_is_an_exact_test_decided_before_the_run():
    """Fisher, one-sided, against the first corpus's 0 of 11: p(4/15) = C(15,4)/C(26,4) = 0.0913."""
    r = wa.conditional_reading
    assert r(4, 15)["state"] == "FALSIFIED" and r(4, 15)["p_fisher_one_sided"] == 0.0913
    assert r(5, 15)["state"] == "PARTIAL" and r(11, 15)["state"] == "PARTIAL"
    assert r(12, 15)["state"] == "RECOVERS"
    assert r(0, 11)["state"] == "FALSIFIED"            # the first corpus against itself
