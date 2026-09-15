"""The test that was missing, and what its absence cost.

`tests/test_email_full_corpus.py` ends with
`test_it_teaches_the_surface_the_proxy_renders`. The equivalent file for fluids was
never written — only `test_fluids_sim.py`, which passes and checks the client. So a
corpus trained on the bare problem statement met a served prompt carrying 388
characters of tool surface it had never seen, listing arguments in **alphabetical**
order where the corpus writes them in the order the tools document.

The adapter then emitted calls missing exactly one key — `property` 40 times,
`value` 30 times — and **71 of its 606 calls were refused for a reason that had
nothing to do with physics** **[ran]** `results/P38-pool-20260915/`. The arm was
void and the run had to be paid for twice.
"""

import json
import subprocess
import sys

import pytest

from training.harness import generate_fluids_full as gen
from training.harness.openai_proxy import render_tools
from training.physics import multitool as mod
from training.physics.tools import SCHEMA, TOOLS


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("ff") / "train.jsonl"
    r = subprocess.run([sys.executable, "-m",
                        "training.harness.generate_fluids_full",
                        "--n", "120", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return [json.loads(l) for l in out.read_text().splitlines() if l.strip()]


def test_the_corpus_teaches_the_prompt_the_model_will_be_served(rows):
    """Not "contains the tool names" — the served prompt, character for character.

    `render_tools` APPENDS UNCONDITIONALLY; it is not idempotent, so the first
    version of this test — re-render the corpus prompt and expect a no-op — got the
    surface twice and failed for its own reason rather than the corpus's. The check
    that means something compares the bare statement's rendering with what the
    corpus stored.
    """
    for r in rows[:20]:
        stored = r["messages"][1]["content"]
        bare = stored.split("\n\nThe following tools")[0]
        served = render_tools([{"role": "user", "content": bare}], SCHEMA)[-1]["content"]
        assert served == stored, "the corpus prompt is not what the proxy would serve"


def test_the_argument_order_the_surface_shows_is_present(rows):
    """The exact drift that voided P38: the surface lists keys alphabetically."""
    surface = render_tools([{"role": "user", "content": "x"}], SCHEMA)[-1]["content"]
    assert "<lookup>T=...; fluid=...; property=...</lookup>" in surface
    for r in rows[:5]:
        assert "<lookup>T=...; fluid=...; property=...</lookup>" in \
            r["messages"][1]["content"]


def test_every_tool_the_expert_needs_is_declared(rows):
    assert {t["function"]["name"] for t in SCHEMA} == set(TOOLS)
    used = {t for r in rows for t in r["tools"]}
    assert used <= set(TOOLS) and used


def test_no_prompt_the_run_will_be_scored_on_is_in_the_corpus(rows):
    held = {c["prompt"] for c in mod.generate(gen.EVAL_N, gen.EVAL_SEED,
                                              mod.FAMILIES)}
    for r in rows:
        # the corpus prompt has the surface appended; the statement is its head
        head = r["messages"][1]["content"].split("\n\nThe following tools")[0]
        assert head not in held


def test_every_family_is_taught(rows):
    from collections import Counter
    seen = Counter(r["family"] for r in rows)
    assert set(seen) == set(mod.FAMILIES), f"missing {set(mod.FAMILIES) - set(seen)}"


def test_the_target_ends_on_an_answer_the_scorer_accepts(rows):
    """Tied to multitool_run's rtol, not to an epsilon chosen here."""
    from training.physics.headroom import correct, parse_answer
    for r in rows[:30]:
        got = parse_answer(r["messages"][-1]["content"])
        assert got is not None
    assert gen.SCORER_RTOL == 0.02
    assert correct(100.0, 101.0, gen.SCORER_RTOL)
