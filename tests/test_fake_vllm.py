"""The serving path against a fake `vllm serve` — the three bugs W9's scoring paid for, caught on the Mac.

`training/harness/fake_vllm.py` models vLLM 0.30's interface at the edges it was observed at — a
repeated `--lora-modules` keeps the last list, a model it does not serve is a 404, stop strings are
honoured — and nothing of a model. Here the REAL runner (`training.wiki.wiki_arm.main`) runs a scoring
session end to end against it: the command line it writes, G1, both arms, the records it keeps. Each
of the two runner bugs of 2026-09-24/25 is then reintroduced and shown to fail here, not on a card.
"""
import json
import sys
import types
from pathlib import Path

import pytest

from training.harness import fake_vllm as fv

REPO = Path(__file__).resolve().parent.parent


def test_a_repeated_lora_flag_keeps_only_the_last_list_as_vllm_030_does():
    twice = fv.parse_serve(["vllm", "serve", "B", "--enable-lora", "--lora-modules", "a=x", "--lora-modules", "b=y"])
    once = fv.parse_serve(["vllm", "serve", "B", "--enable-lora", "--lora-modules", "a=x", "b=y"])
    assert twice["loras"] == {"b": "y"} and once["loras"] == {"a": "x", "b": "y"}


@pytest.fixture
def scoring_dir(tmp_path, monkeypatch):
    """A working directory the runner can score in: the committed wiki and sets, two stand-in adapters."""
    (tmp_path / "knowledge").symlink_to(REPO / "knowledge")
    (tmp_path / "training").mkdir()
    (tmp_path / "training" / "wiki").symlink_to(REPO / "training" / "wiki")
    for k in (0, 1):
        d = tmp_path / "adapters" / f"wiki-walks-s{k}"
        d.mkdir(parents=True)
        (d / "adapter_model.safetensors").write_bytes(b"stand-in")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    return tmp_path


def _score(monkeypatch, out: str = "scoring.json"):
    from training.wiki import wiki_arm as wa
    monkeypatch.setattr(sys, "argv", ["wiki_arm", "--arms", "withlib-s0,withlib-s1", "--concurrency", "4", "--out", out])
    with fv.patched() as seen:
        wa.main()
    return json.loads(Path(out).read_text()), seen


def test_a_scoring_session_runs_end_to_end_against_the_fake(scoring_dir, monkeypatch):
    rec, seen = _score(monkeypatch)
    assert seen["spec"]["loras"] == {"withlib-s0": "adapters/wiki-walks-s0", "withlib-s1": "adapters/wiki-walks-s1"}
    assert all(rec["G1"][x]["applied"] for x in ("withlib-s0", "withlib-s1"))
    for arm in ("withlib-s0", "withlib-s1"):
        recs = rec["arms"][arm]
        assert len(recs) == 67 and not [r for r in recs.values() if "error" in r]
    assert seen["server"].refused == [] and {"withlib-s0", "withlib-s1"} <= set(seen["server"].served)


def _one_flag_per_adapter(extra: list[str]) -> list[str]:
    """Attempt 1's command line: every adapter behind its own `--lora-modules`."""
    i = extra.index("--lora-modules")
    mods = [x for x in extra[i + 1:] if "=" in x]
    return extra[:i] + extra[i + 1 + len(mods):] + [y for m in mods for y in ("--lora-modules", m)]


def test_the_repeated_flag_bug_fails_here_not_on_a_card(scoring_dir, monkeypatch):
    from training.harness import accept_rank as ar
    from training.wiki import wiki_arm as wa
    monkeypatch.setattr(sys, "argv", ["wiki_arm", "--arms", "withlib-s0,withlib-s1", "--out", "bug1.json"])
    with fv.patched() as seen:
        fake = ar.serve
        ar.serve = lambda m, e: fake(m, _one_flag_per_adapter(e))      # restored by `patched` on exit
        with pytest.raises(Exception) as err:
            wa.main()
    assert seen["spec"]["loras"] == {"withlib-s1": "adapters/wiki-walks-s1"}
    assert "404" in str(err.value)


def test_the_path_for_name_bug_fails_here_not_on_a_card(scoring_dir, monkeypatch):
    from training.wiki import wiki_arm as wa
    monkeypatch.setattr(wa, "served_model", lambda arm, members, base: members.get(arm, base))   # attempt 3's bug
    rec, seen = _score(monkeypatch, "bug3.json")
    errors = [r for r in rec["arms"]["withlib-s0"].values() if "error" in r]
    assert len(errors) == 67 and "404" in errors[0]["error"]
    assert "adapters/wiki-walks-s0" in seen["server"].refused
