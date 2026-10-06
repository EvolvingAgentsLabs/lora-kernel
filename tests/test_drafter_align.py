"""DRAFT0's pure pieces: who the drafter's query may read, the k = 1 speed-up $(1+\alpha)/C(1)$, and the verdict table."""
from training.harness.drafter_align import C1, speedup, verdict, visible


def test_a_query_reads_only_the_targets_kv_strictly_before_it():
    assert visible(5, 4, "full_attention") and not visible(5, 5, "full_attention") and not visible(5, 6, "full_attention")
    assert not visible(0, 0, "full_attention")


def test_sliding_layers_see_only_the_window():
    assert visible(2000, 1999, "sliding_attention", window=1024)
    assert visible(2000, 2000 - 1024, "sliding_attention", window=1024)
    assert not visible(2000, 2000 - 1025, "sliding_attention", window=1024)
    assert visible(2000, 0, "full_attention", window=1024)


def test_the_speedup_is_the_measured_round_cost():
    assert abs(C1 - 1.755 / 1.40) < 1e-9
    assert speedup(0.755) == round(1.755 / C1, 3) == 1.4


def _rec(g0=True, g1=True, a0=0.6, a1=0.9):
    return {"gates": {"G0": {"ok": g0}, "G1": {"ok": g1, "alpha": a0}},
            "alpha": {"stock": {"domain": a0}, "aligned": {"domain": a1}}}


def test_the_gates_are_read_before_alpha():
    assert verdict(_rec(g0=False)).startswith("VOID: G0")
    assert verdict(_rec(g1=False)).startswith("VOID: G1")


def test_the_verdict_table():
    assert verdict(_rec(a0=0.6, a1=0.9)).startswith("ALIGNED")
    assert verdict(_rec(a0=0.6, a1=0.84)).startswith("PARTLY")
    assert verdict(_rec(a0=0.75, a1=0.86)).startswith("PARTLY")      # over 0.85 but not +0.15
    assert verdict(_rec(a0=0.6, a1=0.62)).startswith("NOT ALIGNED")


def test_the_general_prompts_are_the_macs():
    """Copied, not imported (the Mac module imports mlx); the copy must not drift from what HOTL0 measured."""
    import ast
    from pathlib import Path
    from training.harness.drafter_align import GENERAL
    src = Path(__file__).parents[1] / "examples" / "mac" / "mlx_spec_lora.py"
    tree = ast.parse(src.read_text())
    mac = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "GENERAL")
    assert GENERAL == mac
