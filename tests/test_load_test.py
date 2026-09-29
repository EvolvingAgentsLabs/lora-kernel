r"""C1's instrument (training/harness/load_test.py): cells spread sessions over adapters, errors are counted and never
raised, percentiles are nearest-rank, and the reading is the one written first — $r_A = \mathrm{tps}_4/\mathrm{tps}_1$ at
K = 16, $r_A \ge 0.8$ no material contention."""
from training.harness import load_test as lt


def test_percentiles_are_nearest_rank():
    xs = [float(i) for i in range(1, 21)]
    assert lt.pct(xs, 50) == 10.0 and lt.pct(xs, 95) == 19.0 and lt.pct([], 95) == 0.0


def test_a_cell_spreads_sessions_over_adapters_and_counts_errors():
    seen = []

    def stream(m, p):
        seen.append(m)
        return {"error": "boom"} if p == "bad" else {"ttft_s": 0.1, "total_s": 0.5, "tokens": 10}
    prompts = {m: ["p", "bad"] for m in lt.MEMBERS}
    c = lt.run_cell(4, 4, prompts, stream)
    assert sorted(set(seen)) == sorted(lt.MEMBERS) and c["requests"] == 4 * lt.R and c["errors"] == 2 * 4
    assert c["ttft_p95_s"] == 0.1


def test_the_reading_written_first():
    cell = lambda k, a, tps, p95=1.0, err=0: {"k": k, "adapters": a, "tps": tps, "ttft_p95_s": p95, "errors": err}
    r = lt.reading([cell(16, 1, 200), cell(16, 4, 170), cell(8, 4, 100, 0.5), cell(32, 4, 250, 2.5)])
    assert r["contention"] == {"ratio_4_over_1_at_16": 0.85, "reading": "NO MATERIAL CONTENTION"}
    assert r["capacity"]["largest_k_four_adapters_p95_ttft_under_2s"] == 16
    assert lt.reading([cell(16, 1, 200), cell(16, 4, 150)])["contention"]["reading"] == "CONTENTION"
