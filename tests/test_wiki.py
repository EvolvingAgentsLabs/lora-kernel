"""W9 — atomic statements: the page format, the referee, the grader, the sets. Zero GPU.

An arm on this wiki measures one unknown only if each of these holds, and each is held here and shown
able to fail: a page is a list of one-sentence statements with its links inside them (lint); the
referee shows a page's sections and never its text, and one statement on `id§anchor`; a citation is
checked against what the walk opened and what the statement says; the oracle's walk, driven through
the real loop, is verified on every row; the corpus shares no world and no wording with the
evaluation. Pairs are exact two-sided sign tests on discordant pairs,
p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1).
"""
import json
from pathlib import Path

import pytest

from memory.lint import lint
from memory.notes import Library
from memory.runtime import Conversation
from training.wiki import corpus as cp
from training.wiki import grade as gr
from training.wiki import questions as qs
from training.wiki import wiki_arm as wa
from training.wiki import world as wd

DEV = wd.build(wd.DEV_SEED)
LIB = DEV.library()
ROWS = qs.rows(DEV, "eval", qs.EVAL_MIX, wd.DEV_SEED)
BY = {r["case_id"]: r for r in ROWS}


def _one(family: str) -> dict:
    return next(r for r in ROWS if r["family"] == family)


# ------------------------------------------------------------------ the world and its lint
def test_a_world_is_deterministic_and_lints_clean(tmp_path):
    a, b = wd.build(11), wd.build(11)
    assert {k: n.serialise() for k, n in a.notes.items()} == {k: n.serialise() for k, n in b.notes.items()}
    root = tmp_path / wd.ROOT
    a.write(root)
    assert lint(root) == []
    assert {n.id for n in Library.load(root).notes.values()} == set(a.notes)


def test_every_lint_rule_for_pages_can_fire(tmp_path):
    root = tmp_path / wd.ROOT
    DEV.write(root)
    page = next(root.glob("wiki/products/*.md"))
    text = page.read_text()
    bad = text.replace("§pack ", "§pack Two sentences here. And another one ") + \
        "a line that is not a statement\n§pack A duplicate anchor.\n§long " + "word " * 45 + "end.\n" + \
        "§dangling Points at [[distributor-wiki/wiki/nowhere]].\n"
    page.write_text(bad.replace("source:", "refs: [distributor-wiki/wiki/nowhere]\nsource:"))
    rules = {f[0] for f in lint(root)}
    assert {"statement-sentence", "statement-line", "statement-anchor", "statement-tokens", "page-refs", "link"} <= rules


# ------------------------------------------------------------------ the referee
def test_a_page_shows_its_sections_and_never_a_statements_text():
    p = DEV.facts["products"][0]
    conv = Conversation(LIB, seed=1)
    conv.answer("search", f" shelf=wiki>{p['name']}")
    page = conv.answer("open", ">" + conv.opaque[p["id"]])
    assert "sections §supplier · §warehouse · §pack · §reorder-point" in page
    assert str(p["pack"]) not in page.split("sections")[1] and "supplied by" not in page


def test_a_statement_opens_on_its_anchor_with_its_links_openable():
    p = DEV.facts["products"][0]
    conv = Conversation(LIB, seed=1)
    conv.answer("search", f" shelf=wiki>{p['name']}")
    st = conv.answer("open", f">{conv.opaque[p['id']]}§supplier")
    sup = p["supplier"]
    assert f"[{conv.opaque[sup['id']]}] {sup['name']}" in st
    assert not conv.answer("open", ">" + conv.opaque[sup["id"]]).startswith("ERROR")
    assert conv.statements == [(p["id"], "supplier")]


def test_a_wrong_section_is_an_observation_and_an_unseen_id_is_a_violation():
    p = DEV.facts["products"][0]
    conv = Conversation(LIB, seed=1)
    conv.answer("search", f" shelf=wiki>{p['name']}")
    assert conv.answer("open", f">{conv.opaque[p['id']]}§colour").startswith("ERROR: no section")
    assert conv.ended is None
    assert conv.answer("open", ">zzz§pack").startswith("ERROR: no note")
    assert conv.ended == "guard: unknown_id"


# ------------------------------------------------------------------ the grader
def _walked(row: dict):
    conv = wa.conversation(LIB, row)
    final, conv, _ = wa.walk(LIB, row, wa.oracle_gen(row, conv), conv)
    return final, conv


def test_the_oracle_walk_through_the_real_loop_is_verified_on_every_row():
    recs = [wa.oracle_record(LIB, r) for r in ROWS]
    assert all(x["credit"] for x in recs) and not any(x["refused"] for x in recs)
    assert sum(qs.headline(r) for r in ROWS) == 40


def test_a_right_number_is_not_credit_unless_its_citation_holds():
    row = _one("supplier-lead")
    final, conv = _walked(row)
    assert gr.grade(row, final, conv)["state"] == "right"
    value = final.split(" [")[0]
    assert gr.grade(row, value, conv)["state"] == "unverified"                       # no citation
    nid, _ = row["support"]
    assert gr.grade(row, f"{value} [{conv.opaque[nid]}§town]", conv)["state"] == "unverified"   # not opened
    p_id = row["plan"][1][1]
    assert gr.grade(row, f"{value} [{conv.opaque[p_id]}§supplier]", conv)["why"] == "the cited statement does not hold the value"
    assert gr.grade(row, f"{value} or 99 days [{conv.opaque[nid]}§lead-time]", conv)["state"] == "wrong"   # hedged
    assert gr.grade(row, value, None)["value_right"] is True                          # what the closed-book gate reads


def test_not_in_my_library_is_right_only_where_the_wiki_has_nothing():
    none, some = _one("none-supplier"), _one("lead")
    assert gr.grade(none, "Not in my library.")["state"] == "right"
    assert gr.grade(some, "Not in my library.")["state"] == "wrong"


def test_the_trivial_floor_scores_nothing_on_the_headline():
    head = [r for r in ROWS if qs.headline(r)]
    assert sum(wa.run_case(LIB, r, "base-walks", wa.scripted(wa.floor_policy))["credit"] for r in head) == 0


def test_base_reads_is_handed_the_oracles_statements_with_their_citations():
    row = _one("contact-ext")
    user, conv = wa.oracle_sections(LIB, row)
    assert user.count("§") == 3 and len(conv.statements) == 3
    final = f"{row['answer']} [{conv.opaque[row['support'][0]]}§extension]"
    assert gr.grade(row, final, conv)["state"] == "right"


# ------------------------------------------------------------------ the verdict can say each reading
def _rec(nolib: int, reads: int, walks: int, pair_state: str) -> dict:
    s = lambda c, v=None: {"headline": {"n": 40, "scored": 40, "errors": 0, "missing": 0, "credit": c, "value_right": c if v is None else v}}
    return {"analysis": {"summary": {"nolib": s(0, nolib), "base-reads": s(reads), "base-walks": s(walks)},
                         "pairs": {"headline": [{"pair": "base-reads vs base-walks", "state": pair_state, "only_a": 9, "only_b": 1, "p_value": 0.02}]}}}


@pytest.mark.parametrize("args,stage", [((10, 38, 20, "improvement"), "VOID"), ((0, 38, 35, "tie"), "THE RUNTIME IS ENOUGH"),
                                        ((0, 20, 10, "improvement"), "READING IS THE GAP"),
                                        ((0, 38, 20, "improvement"), "NAVIGATION IS THE GAP"), ((0, 30, 27, "tie"), "NO ATTRIBUTABLE GAP")])
def test_the_headroom_verdict_can_say_each_of_its_readings(args, stage):
    v = wa.verdict(_rec(*args))
    assert v["stage"] == stage and v["train"] == (stage == "NAVIGATION IS THE GAP")


# ------------------------------------------------------------------ the sets
def test_the_corpus_gate_passes_and_each_clause_can_fail():
    train, evals = cp.train_rows(), cp.eval_rows()
    assert cp.gate(train, evals)["passed"]
    bad = [dict(r) for r in train[:3]]
    bad[0]["world"] = wd.EVAL_SEED
    bad[1]["question"] = evals[0]["question"]
    bad[2]["grade"] = "wrong"
    g = cp.gate(bad + train[3:], evals)
    assert g["G1_eval_world_in_corpus"] == 1 and g["G2_eval_question_in_corpus"] == 1 and g["G3_not_verified"] == 1
    leak = dict(evals[0]); leak["question"] += f" ({evals[0]['check']['tokens'][0]})"
    assert cp.gate(train, [leak] + evals[1:])["G4_value_in_question"] >= 1


def test_the_evaluation_world_on_disk_is_the_frozen_generators():
    if not wa.LIBRARY.exists():
        pytest.skip("written after the freeze")
    disk = Library.load(wa.LIBRARY)
    assert {k: n.serialise() for k, n in disk.notes.items()} == \
        {k: n.serialise() for k, n in wd.build(wd.EVAL_SEED).notes.items()}
    assert lint(wa.LIBRARY) == []
    rows = wa.load_rows("eval")
    assert rows == json.loads(json.dumps(cp.eval_rows()))


def test_the_nursing_members_prompt_is_untouched_by_the_wiki_member():
    from memory import prompt
    assert "id§section" not in prompt.SYSTEM and "open id§section" in prompt.SCHEMA_WIKI[1]["function"]["description"]
