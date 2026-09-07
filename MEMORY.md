# Project memory — lora-kernel

What a session needs to know before it starts, and what it must not re-derive.
The live position of the work is [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md);
this file holds the facts that outlive any single step.

## The thesis, in one paragraph

The whole agentic system is a pool of QLoRA adapters over one resident base
model. The **target that verifies the drafts is a frontier model**, so acceptance
stops being a speed statistic and becomes a per-region distillation score. When a
region's score crosses a threshold, the expert is promoted from drafter to
generator and **the frontier is withdrawn**. The number that decides the project
is the **withdrawal gap**: verified score after the frontier leaves, minus the
score it had while it was there.

## Facts established in this repository

| # | fact | marker |
|---|---|---|
| M1 | Rejection sampling emits the *target's* distribution, so α measures agreement **with whatever verifies**. Against the shared base it is anti-correlated with expertise; against a frontier model it is a distillation score. | [read] |
| M2 | vLLM: multi-LoRA over one target and tree-structured verification ship; **LoRA-as-drafter is an open RFC** ([vllm#52038](https://github.com/vllm-project/vllm/issues/52038), 2026-08-12), r=64 ≈ 28× smaller than the 0.8B drafter it replaces, drafting quality within ~2%. | [read] |
| M3 | Cross-adapter KV cache is the open engineering problem. Prefix sharing is standard; cross-adapter branch sharing is not. | [read] |
| M4 | **At T=0 the accepted prefix is exactly the longest common prefix** between the draft and the target's greedy continuation, and greedy is prefix-consistent — so one frontier generation per task yields the ground-truth continuation at every position. The α surface is measurable today with no GPU, no vLLM and no RFC. | [read] |
| M5 | **A frontier target has a different tokenizer than the base**, so token-level acceptance against it is undefined. α against a foreign target is a *text*-agreement measure. This is sound for the distillation score and unsound for any speedup claim. | [read] |
| M6 | Frontier chat APIs do not expose logprobs of a forced continuation, so true rejection sampling against a frontier API is not implementable — which is why M4 is the instrument. | [read] |
| M7 | **Character-prefix agreement measures layout, not agreement.** Identical answers score 0.00 across formats (fenced/pretty vs compact); different answers score 0.44 within one format. In `results/S0c-canonical-20260907` the 4B gave the correct answer and scored 0.00 while an indented copy of the same answer scored 1.00. | [ran] |
| M8 | On `clinical_learning` held-out, **single-shot**, `gemma4:12b` scores 4/12 and its own 4B and 9B drafters score 3/12 — no separation and no headroom. The published 38–41/50 belongs to the **runtime**, not to raw generation. | [ran] |
| M9 | **`held_out_delta` separates the models where `held_out` does not**: `gemma4:12b` 8/12 against 3/12 and 4/12 for its own drafters. Headroom exists — on the split whose planted rule inverts, not on the plain held-out set. | [ran] |
| M10 | In that same run, ordering by α matched ordering by verified score **for the wrong reason** — the 9B indents like the target and the 4B does not. A confirmation of the central claim arriving by accident of formatting. | [ran] |
| M11 | **The promotion criterion is semantic answer agreement, not character acceptance** — decided 2026-09-07 under the plan's own stopping rule, after M7. Character α is reported beside it and ranks nothing; whether `harness.lora` reconciles them is S6's win condition. | decided |
| M12 | Applying that criterion to runs already on disk cost nothing: the case files store both answers, so a metric change re-scores four runs without re-running inference. Persisting the raw answers, not just the metric, is what made that possible. | [ran] |
| M13 | Every local model here emits a reasoning channel before the answer; ollama returns the two separately, `think=false` works on qwen and 500s on gemma; and ollama's chat renderer ignores an assistant prefill, so mid-answer draft positions are unavailable locally. | [ran] |

## What this workspace already measured, and must not be re-learned

| fact | why it binds this project |
|---|---|
| `gemma4:12b` scored **38–41/50** on `clinical_learning` held-out; `qwen3.5:4b` 28–38; `qwen3.5:9b` 19–33. Non-monotonic in size. | The headroom risk is real: a frontier arm may have almost nothing to be better at. Step S1 exists for this. |
| A **feedback message** moved one model +30 points with the information held constant. | Contract/phrasing is a confound as strong as the model. Freeze the prompt and hash it. |
| The strongest legal retriever scored **+0** over raw (p = 1.0000). | Do not assume an obvious mechanism works because it is obvious. |
| The same procedure was *interface compensation* on a 4B and *persistent gain* on a 12B. | Whether an expert is real is a property of the **pair**, not the expert. Fitness `w₁` must come from a verifier the loop cannot see. |
| `gemma4nanoloop` cut peak schema overhead 5,548 → 817 tokens (−85%) **with no training**. | That is the baseline `harness.lora` has to beat, not "big JSON in the prompt". |
| `token-trie` made invalid syntax *impossible* via logit masking, and was archived because **masking needs the sampler, which an API does not expose**. | Owning the runtime is what makes the kernel adapter available at all. |
| `ai-storage`: a memory hierarchy lost to plain lexical search. | Any routing claim needs the cheap lexical/embedding router as its attribution arm. |

## The environment as it is [ran] 2026-09-07

- macOS `arm64`, 16 GB. **`vllm` is not installed and cannot serve here** — every
  vLLM-dependent step is rented GPU, and that is why they are late in the plan.
- `ollama`: `gemma4:12b-mlx`, `gemma4:12b`, `gemma4:e4b`, `qwen3.5:9b`,
  `qwen3.5:4b`, `embeddinggemma`.
- **No `OPENROUTER_API_KEY` in the environment or on disk.** It is the only
  blocker on the frontier arm (S1/S2-frontier).
- `alpha/` is built and tested here: 18 checks, three persisted runs under
  `results/`, reports regenerable. The instrument's design is **frozen at three
  redesigns** pending the decision in [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) §11.
- Agents load for a session rooted at this repository; they are symlinked into
  the workspace's `.claude/agents/` so a session rooted above can address them.
- `../verified-runtime` is the instrument being reused: `clinical_learning`
  held-out (n=50) with an **exact** verifier, an OpenAI-compatible backend at
  `temperature=0.0`, and `evaluation/frontier_gap.py`.

## Working agreements carried in

- Never push to `main`; everything lands through a PR, documents included.
- Every document has a Spanish mirror, level by section count, in the same commit.
- Brief the experiment — what, why, which model, which provider, what falsifies
  it — **before** the run, not next to the report.
- Respect the architecture as given. Technical facts enter as engineering
  constraints inside it, not as objections to it.
