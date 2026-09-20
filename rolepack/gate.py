"""The role pack's gate — results/F3-role-pack-20260920/BRIEF.md, clauses G1–G6, zero GPU.

    python -m rolepack.gate            # writes results/F3-role-pack-20260920/gate.json
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import rolepack
from rolepack import lint as L

RELEASED = ("triage", "desk")


def tampered(edit) -> list[str]:
    """Lint a copy of `roles/` after `edit(text of roles/triage/role.toml) -> text`; the clauses found."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "roles"
        shutil.copytree("roles", root)
        f = root / "triage" / "role.toml"
        f.write_text(edit(f.read_text()))
        return sorted({c for c, _ in L.lint(root).get("triage", [])})


def gate() -> dict:
    from training.harness import openai_proxy, route
    from training.harness.train_pool import POOL
    packs = rolepack.load_all("roles")
    openai_proxy._load_surfaces()
    g = {"packs": sorted(packs), "lint_findings": {k: v for k, v in L.lint("roles").items() if v}}
    g["G1_served_prompt_is_the_proxys"] = {r: packs[r].prompt() == openai_proxy.POOL_SYSTEM[packs[r].member] for r in RELEASED}
    g["G2_block_byte_identical_in_every_row"] = {
        r: rolepack.corpus_blocks(packs[r].corpus) == {packs[r].block()} for r in RELEASED}
    g["G2_rows"] = {r: sum(1 for _ in open(packs[r].corpus)) for r in RELEASED}
    g["G3_surface_and_keys_are_the_corpus"] = {
        r: rolepack.corpus_surface(packs[r].corpus) == packs[r].surface
           and {t: k for t, k in rolepack.corpus_keys(packs[r].corpus).items() if t in packs[r].surface} == packs[r].args
        for r in RELEASED}
    g["G4_hashes_agree_with_the_manifest"] = {
        r: json.loads(Path(packs[r].release).read_text())["corpus_sha256"] == rolepack.sha_file(packs[r].corpus)
           == packs[r].raw["corpus"]["sha256"] for r in RELEASED}
    reg = rolepack.regions(packs)
    g["G5_derivation"] = {"POOL": rolepack.pool(packs) == POOL,
                          "REGIONS": all(reg[m] == route.REGIONS[m] for m in reg) and len(reg) == 2,
                          "ROLES": rolepack.roles(packs) == {r: m for r, m in route.ROLES.items() if m in reg}}
    swap = lambda a, b: (lambda t: t.replace(a, b, 1))
    g["G6_the_linter_can_fail"] = {
        "tampered corpus hash": tampered(lambda t: re.sub(r'(\[corpus\]\npath = "[^"]+"\nsha256 = ")[0-9a-f]{4}', r"\g<1>0000", t)),
        "argument keys moved to another tag": tampered(swap('thread_history = ["thread_id"]', 'thread_history = ["id"]')),
        "prompt hash drifted": tampered(lambda t: re.sub(r'(\[prompt\][^\[]*sha256 = ")[0-9a-f]{4}', r"\g<1>0000", t, flags=re.S)),
        "surface re-sorted": tampered(swap('surface = ["thread_history", "sender_stats", "message"]',
                                           'surface = ["message", "sender_stats", "thread_history"]')),
        "another member's prompt referenced": tampered(swap("training.harness.agent_sim:SYSTEM", "training.harness.desk_sim:SYSTEM")),
    }
    want = {"tampered corpus hash": "hashes", "argument keys moved to another tag": "keys", "prompt hash drifted": "prompt",
            "surface re-sorted": "surface", "another member's prompt referenced": "prompt"}
    ok6 = all(want[k] in v for k, v in g["G6_the_linter_can_fail"].items())
    g["third_pack"] = {"id": "nursing-walks", "status": packs["nursing-walks"].status, "lint": not L.lint_pack(packs["nursing-walks"]),
                       "block_byte_identical_in_every_row": rolepack.corpus_blocks(packs["nursing-walks"].corpus)
                                                            == {packs["nursing-walks"].block("library")}}
    g["passed"] = bool(not g["lint_findings"] and all(all(v.values()) for k, v in g.items()
                                                      if k.startswith(("G1", "G2_block", "G3", "G4", "G5"))) and ok6)
    return g


def main() -> int:
    g = gate()
    out = Path("results/F3-role-pack-20260920/gate.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(g, indent=1))
    print(f"[pack] gate {'PASSED' if g['passed'] else 'FAILED'} · " + " · ".join(
        f"{k.split('_')[0]}={v}" for k, v in g.items() if k.startswith("G") and k != "G2_rows"))
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
