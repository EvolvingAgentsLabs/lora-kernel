"""P61 — the harness arm: the document rides on the system prompt and nothing else moves;
the verdict is the pre-registered one (knowledge_arm.py docstring, FOUNDATIONS §7.3)."""

from pathlib import Path

from training.harness.knowledge_arm import verdict, with_knowledge
from training.harness.suites import load


def _recs(flags, human=None):
    human = human or [True] * len(flags)
    return [{"id": f"m{i}", "correct": f, "human": h} for i, (f, h) in enumerate(zip(flags, human))]


def test_the_document_changes_only_the_system_prompt():
    s = load("email")
    k = with_knowledge(s, Path("knowledge/email-triage.md").read_text())
    assert k.block == s.block and k.tags == s.tags and k.answer is s.answer and k.parse is s.parse
    assert k.system.startswith(s.system) and "Worked example" in k.system
    assert k.user_text(s.cases(3, 1)[0]) == s.user_text(s.cases(3, 1)[0])


def test_the_document_speaks_the_corpus_s_tags_in_the_corpus_s_syntax():
    s = load("email")
    text = Path("knowledge/email-triage.md").read_text()
    calls = s.tag.findall(text)
    assert {t for t, _ in calls} == set(s.tags)
    for tag, body in calls:
        key = s.positional[tag]
        assert body.startswith(f"{key}=") or body.startswith(f"{key}=thr") or key in body, (tag, body)


def test_verdict_reads_the_three_pre_registered_outcomes():
    n = 200
    base = _recs([i % 3 == 0 for i in range(n)])
    kb = _recs([i % 3 != 2 for i in range(n)])          # strictly better than base
    expert = _recs([i != 5 for i in range(n)])          # near-perfect
    v = verdict(base, kb, expert)
    assert v["kb_pays"] and v["weights_needed"] and not v["harness_replaces_weights"]
    assert v["reading"].startswith("WEIGHTS NEEDED")
    tie = verdict(base, kb, _recs([i % 3 != 2 or i == 7 for i in range(n)]))
    assert tie["harness_replaces_weights"] and not tie["weights_needed"]
    assert tie["reading"].startswith("HARNESS REPLACES")
    nothing = verdict(base, base, None)
    assert not nothing["kb_pays"] and nothing["weights_needed"] is None


def test_errors_are_not_folded_into_a_score():
    base = _recs([True] * 10); kb = [{"id": f"m{i}", "error": "boom", "human": True} for i in range(10)]
    v = verdict(base, kb, None)
    assert v["kb_vs_base"]["n_paired"] == 0 and not v["kb_pays"]
