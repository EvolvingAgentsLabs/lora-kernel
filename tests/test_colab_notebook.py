"""The Colab notebook runs against the repository it clones, with the model replaced by the oracle.

`examples/colab/wiki_walk.ipynb` is the one path from a stranger to the released trajectory LoRA; it
imports `memory/`, `training.harness.accept_rank` and `training.wiki.grade` from `main`, so a change
there can break it silently. This runs its cells 3–5 with the oracle's walk (`wiki_arm.oracle_gen`)
standing in for the model — zero GPU — and asserts what the notebook claims to show:

    credit = value_right ∧ citation_verified          (training/wiki/grade.py)

is 1 on every picked question for the oracle and 0 for a model that answers `Not in my library.`;
and after one statement's number is edited in a copy of the library, the same walk returns the new
number with its citation — the claim that a fact changes by editing markdown (docs/MEMORY.md §1.6).
The model itself ran through the notebook on an L4 on 2026-09-26: bare 2/6, adapter 6/6, the edited
note answered right (`examples/colab/README.md`, `run-l4-20260926.log`).
"""
from __future__ import annotations

import json
from pathlib import Path

import memory.runtime as rt
from training.wiki.wiki_arm import oracle_gen

NB = Path(__file__).resolve().parent.parent / "examples" / "colab" / "wiki_walk.ipynb"


def _cells() -> list[str]:
    nb = json.loads(NB.read_text())
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_the_notebook_walks_grades_and_follows_an_edited_note(tmp_path, monkeypatch):
    monkeypatch.chdir(NB.parents[2])
    code = _cells()
    assert len(code) == 5
    g: dict = {"N_QUESTIONS": 6, "tok": None, "model": None}
    exec(code[2], g)                                           # cell 3: gen_for, walk

    made: list = []

    class Spy(rt.Conversation):                                # the oracle needs the walk's own id map
        def __post_init__(self):
            super().__post_init__()
            made.append(self)

    g["Conversation"] = Spy
    g["gen_for"] = lambda question, adapter=True: (
        (lambda prefix: oracle_gen(g["_row"], made[-1])(prefix)) if adapter else (lambda prefix: "Not in my library."))

    walk4 = 'g, text = walk(lib, r, gen_for(r["question"], adapter=on))'
    walk5 = 'g, text = walk(edited, row_new, gen_for(row["question"], adapter=True))'
    assert walk4 in code[3] and walk5 in code[4]
    exec(code[3].replace(walk4, 'globals()["_row"] = r; ' + walk4), g)
    assert g["score"] == {"bare": 0, "adapter": len(g["picked"])} and len(g["picked"]) == 6

    exec(code[4].replace("/tmp/edited-wiki", str(tmp_path / "edited-wiki"))
                .replace(walk5, 'globals()["_row"] = row_new; ' + walk5), g)
    assert g["new"] != g["old"]
    assert g["g"]["state"] == "right", g["g"]
