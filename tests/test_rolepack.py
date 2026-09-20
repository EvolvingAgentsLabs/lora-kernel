"""The role pack — results/F3-role-pack-20260920. A pack DECLARES and the linter CHECKS: every line is
held against the artefact it names, and equality is Python `==` on the proxy's own objects — the served
prompt is `openai_proxy.POOL_SYSTEM[member]`, the served block is `prune` + `tools_to_instruction`, the
two calls the proxy makes. A copied string would pass a test and drift in production."""
import json
import shutil
from pathlib import Path

import pytest

import rolepack
from rolepack import gate as G
from rolepack import lint as L


def test_the_three_packs_lint_clean_and_the_cli_says_so(capsys):
    assert L.main(["roles"]) == 0
    out = capsys.readouterr().out
    assert "3 pack(s), 0 finding(s)" in out


def test_the_recorded_gate_is_what_the_gate_computes_today():
    rec = json.loads(Path("results/F3-role-pack-20260920/gate.json").read_text())
    now = json.loads(json.dumps(G.gate()))
    assert now == rec and rec["passed"] is True


@pytest.mark.parametrize("role", G.RELEASED)
def test_a_released_members_prompt_and_block_are_what_the_proxy_serves(role):
    from training.harness import openai_proxy
    p = rolepack.load_all("roles")[role]
    surfaces = openai_proxy._load_surfaces()             # what `--prune` loads at start-up
    assert p.prompt() == openai_proxy.POOL_SYSTEM[p.member]
    assert surfaces[p.member] == p.surface and openai_proxy.POOL_ARGS[p.member] == p.args
    blocks = rolepack.corpus_blocks(p.corpus)
    assert blocks == {p.block()}, "the block the pack renders is not the one in every corpus row"


def test_the_registries_the_code_reads_are_derivable_from_the_packs():
    from training.harness import route
    from training.harness.train_pool import POOL
    packs = rolepack.load_all("roles")
    assert rolepack.pool(packs) == POOL
    reg = rolepack.regions(packs)
    assert set(reg) == {"email-full", "desk-commitment"} and all(reg[m] == route.REGIONS[m] for m in reg)
    assert rolepack.roles(packs) == {r: m for r, m in route.ROLES.items() if m in reg}
    # an unreleased member is declared and derives NOTHING: it is in no registry a server reads
    assert "adapters/nursing-walks-v2-q35" not in rolepack.pool(packs)


@pytest.mark.parametrize("what,clause", [("tampered corpus hash", "hashes"), ("prompt hash drifted", "prompt"),
                                         ("surface re-sorted", "surface"), ("argument keys moved to another tag", "keys"),
                                         ("another member's prompt referenced", "prompt")])
def test_the_linter_can_fail_on_each_clause(what, clause):
    rec = json.loads(Path("results/F3-role-pack-20260920/gate.json").read_text())
    assert clause in rec["G6_the_linter_can_fail"][what]


def test_more_ways_to_break_a_pack(tmp_path):
    def broken(role, a, b):
        root = tmp_path / f"r{abs(hash((role, a))) % 10**6}"
        shutil.copytree("roles", root)
        f = root / role / "role.toml"
        assert a in f.read_text()
        f.write_text(f.read_text().replace(a, b, 1))
        return {c for items in L.lint(root).values() for c, _ in items}
    assert "route" in broken("desk", 'roles = ["desk"]', 'roles = ["triage"]')            # one role, two members
    assert "policy" in broken("triage", 'default = "adapter"', 'default = "oracle"')
    assert "policy" in broken("triage", 'unmeasured = "frontier"', 'unmeasured = "somewhere"')
    assert "policy" in broken("nursing-walks", 'value = "base"', 'value = "adapter"')      # the frozen table is the source
    assert "keys" in broken("nursing-walks", 'search = ["shelf"]', 'search = []')          # a tag attribute the corpus writes
    assert "library" in broken("nursing-walks", 'sites = ["ward-7b", "unit-4c"]', 'sites = ["ward-9z"]')
    assert "hashes" in broken("nursing-walks", 'arm = "withlib"', 'arm = "nolib"')         # evidence of another adapter
    assert "loop" in broken("triage", 'measured = "inline"', 'measured = "guess"')
    assert "hashes" in broken("desk", 'release = "releases/desk-commitment@v2.json"', 'release = "releases/email-full@v2.json"')


def test_a_pack_holds_no_copy_of_a_prompt_or_a_block():
    for f in Path("roles").glob("*/role.toml"):
        t = f.read_text()
        assert "The following tools are available" not in t and "You are" not in t, f
