import sys

from training.harness.stream import run_streaming


def test_output_is_returned_and_the_returncode_comes_back():
    rc, out = run_streaming([sys.executable, "-c",
                             "print('a'); print('b')"])
    assert rc == 0
    assert out.splitlines() == ["a", "b"]


def test_a_failing_child_reports_its_code_rather_than_raising():
    rc, out = run_streaming([sys.executable, "-c",
                             "import sys; print('before'); sys.exit(3)"])
    assert rc == 3
    assert "before" in out


def test_stderr_is_merged_so_a_traceback_is_not_lost():
    rc, out = run_streaming([sys.executable, "-c",
                             "raise SystemExit('gone wrong')"])
    assert rc != 0
    assert "gone wrong" in out


def test_only_the_tail_is_kept_so_a_long_run_does_not_return_megabytes():
    rc, out = run_streaming([sys.executable, "-c",
                             "[print(i) for i in range(50)]"], keep=5)
    assert rc == 0
    got = out.splitlines()
    assert len(got) <= 6           # `keep` trims as it goes, never below the last few
    assert got[-1] == "49"         # and it keeps the END, which is where a result is
