"""Milestone 7, arm 0: a failure is read where it happens — was what the tool returned used?

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §8.6). A channel is only measurable if it is
needed *and read*. `used` / `ignored` count whether a tool's value reaches a later step;
`invented_steps` counts `<calc>`s holding a number with no source."""

from training.physics import result_use


def _answer(name, body, handbook):
    return eval(body) if name == "calc" else 882.3


def test_a_looked_up_value_that_is_multiplied_is_used():
    got = result_use.read_chain("<lookup>density</lookup>\n<calc>882.3 * 2</calc>", "2 m", None, _answer)
    assert (got["used"], got["ignored"], got["invented_steps"]) == (1, 0, 0)


def test_a_looked_up_value_replaced_by_the_models_own_is_ignored_and_invented():
    got = result_use.read_chain("<lookup>density</lookup>\n<calc>1359.7 * 2</calc>", "2 m", None, _answer)
    assert (got["used"], got["ignored"], got["invented_steps"]) == (0, 1, 1)


def test_the_recorded_run_reads_as_the_record_says():
    import json
    rec = json.load(open("results/M7-knowledge-base-20260919/arm0.json"))
    assert (rec["failed"], rec["failed_with_a_number_from_nowhere"],
            rec["failed_with_a_result_never_used"], rec["tool_errors_while_replaying"]) == (79, 74, 75, 0)


def test_a_tool_that_raises_is_counted_not_skipped():
    """The first replay swallowed every `<lookup>` error and published two wrong counts."""
    def broken(name, body, handbook):
        raise RuntimeError("handbook in the wrong shape")
    got = result_use.read_chain("<lookup>density</lookup>\n<calc>882.3 * 2</calc>", "2 m", None, broken)
    assert got["tool_errors"] == 2
