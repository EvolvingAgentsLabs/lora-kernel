from training.harness.by_family import slice_by_family, table


def rec(i, fam, passed):
    return {"id": i, "family": fam, "passed": passed}


def test_pairs_on_id_and_reports_what_it_dropped():
    local = [rec("a", "x", True), rec("b", "x", False), rec("c", "y", False)]
    ref = [rec("a", "x", True), rec("b", "x", True)]
    out = slice_by_family(local, ref)
    # 'c' has no reference, so it is outside the comparison AND said so.
    assert out["n"] == 2
    assert out["dropped_local"] == 1
    assert out["dropped_reference"] == 0
    assert "NOT counted" in table(out)


def test_only_local_counts_the_cases_a_router_would_keep():
    local = [rec("a", "x", True), rec("b", "x", False)]
    ref = [rec("a", "x", False), rec("b", "x", True)]
    out = slice_by_family(local, ref)
    assert out["only_local"] == 1
    assert out["only_reference"] == 1


def test_any_family_ahead_is_false_when_every_slice_is_dominated():
    local = [rec("a", "x", False), rec("b", "y", False)]
    ref = [rec("a", "x", True), rec("b", "y", True)]
    out = slice_by_family(local, ref)
    assert out["any_family_ahead"] is False
    assert all(r["dominated"] for r in out["families"])


def test_a_family_the_local_expert_wins_is_reported_ahead():
    local = [rec("a", "x", True), rec("b", "y", False)]
    ref = [rec("a", "x", False), rec("b", "y", True)]
    out = slice_by_family(local, ref)
    assert out["any_family_ahead"] is True
    # and the best candidate sorts first
    assert out["families"][0]["family"] == "x"


def test_reproduces_the_p41_numbers_in_the_plan():
    # The shape of P41's fluids arm, families in the proportions measured, so a
    # change to the arithmetic breaks here rather than in a document nobody runs.
    local, ref = [], []
    counts = {"manning_channel": (23, 7, 19), "venturi_flow": (22, 3, 15),
              "hydrostatic_force": (23, 1, 14), "pipe_head_loss": (22, 0, 18)}
    for fam, (n, kl, kr) in counts.items():
        for j in range(n):
            local.append(rec(f"{fam}-{j}", fam, j < kl))
            ref.append(rec(f"{fam}-{j}", fam, j >= n - kr))
    out = slice_by_family(local, ref)
    assert out["n"] == 90
    assert out["local_accuracy"] == 0.1222
    assert out["reference_accuracy"] == 0.7333
    assert out["any_family_ahead"] is False
