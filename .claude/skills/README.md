# Skills

Project skills, versioned with the code. The lifecycle rule is in
[`../../CLAUDE.md`](../../CLAUDE.md) §5; the ledger is
[`docs/EXPERIMENT_PLAN.md`](../../docs/EXPERIMENT_PLAN.md) §9.

| skill | what it is for |
|---|---|
| [`experiment-brief`](experiment-brief/SKILL.md) | pre-register a run before it starts |
| [`alpha-surface`](alpha-surface/SKILL.md) | measure and report the acceptance surface |

## Searched and not installed

Both marketplaces were searched for evaluation and benchmarking skills
(`huggingface-evaluation`, `wshobson/agents@llm-evaluation`,
`arize-ai/phoenix@phoenix-evals` and others). All of them are built around
LLM-as-judge scoring and tracing. This project's verifier is **exact** and its
metric is acceptance against a target, so none of them removes work here — and
installing one would add surface area that has to be maintained. **[ran]**
2026-09-07.

## Declared, not built

`withdrawal-gap` (S5, needs the non-inferiority margin the step will
pre-register) and `adapter-training` (S4, needs a training environment that does
not exist yet).
