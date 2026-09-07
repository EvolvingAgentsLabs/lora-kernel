# Agents

Versioned with the code, and expected to change as the project learns. The
lifecycle rule is in [`../../CLAUDE.md`](../../CLAUDE.md) §5 and the ledger of
every creation, edit and retirement is
[`docs/EXPERIMENT_PLAN.md`](../../docs/EXPERIMENT_PLAN.md) §9.

| agent | exists because | first used at |
|---|---|---|
| [`headroom-auditor`](headroom-auditor.md) | a baseline at the ceiling makes every arm tie, and a tie reads as success | S1 |
| [`instrument-skeptic`](instrument-skeptic.md) | four instruments produced clean, wrong numbers in one day | S0 |
| [`alpha-runner`](alpha-runner.md) | α runs have to stream, persist per case, and be abortable | S0 |
| [`mirror-keeper`](mirror-keeper.md) | a stale Spanish mirror is worse than an absent one | every document commit |

These load for a session rooted at this repository. A session rooted at the
workspace above sees them through symlinks in `../../../.claude/agents/` **[ran]**
— created 2026-09-07, when `instrument-skeptic` could not be addressed from
there.

Retired agents move to [`deprecated/`](deprecated/README.md) with the reason at
the top. Deleting one loses why it existed.

## Declared, not built

Justified by a step that does not exist yet, and therefore not written:
`adapter-trainer` (S4), `kernel-bench` (S6), `tournament-referee` (S7).
