# Agents

Versioned with the code, and expected to change as the project learns. The lifecycle rule
is in [`../../CLAUDE.md`](../../CLAUDE.md) §5 and the ledger of every creation, edit and
retirement is [`docs/PLAN.md`](../../docs/PLAN.md) §4.

| agent | exists because | its step in the plan |
|---|---|---|
| [`headroom-auditor`](headroom-auditor.md) | a baseline at the ceiling makes every arm tie, and a tie reads as success — and the floor does the mirror | before every milestone; milestone 2's test set and milestone 3's band depend on it |
| [`instrument-skeptic`](instrument-skeptic.md) | twelve instruments produced clean, wrong numbers ([`docs/RECORD.md`](../../docs/RECORD.md) §4) | after anything that produces a metric changes |
| [`colab-runner`](colab-runner.md) | this machine cannot train an adapter, and that limit must not shrink the experiment | milestones 1, 3, 4 |
| [`mirror-keeper`](mirror-keeper.md) | a stale Spanish mirror is worse than an absent one | every document commit |

These load for a session rooted at this repository. A session rooted at the workspace above
sees them through symlinks in `../../../.claude/agents/` **[ran]**.

Retired agents move to [`deprecated/`](deprecated/README.md) with the reason at the top.
Deleting one loses why it existed.
