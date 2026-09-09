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
| M9 | **`held_out_delta` gives the target headroom where `held_out` does not**: `gemma4:12b` **12/20** against **6/20** for both of its drafters. That is where the frontier arm should be bought. | [ran] |
| M10 | In that split, ordering by α matched ordering by verified score **for the wrong reason** at n=12 — the 9B indents like the target — and the agreement vanished at n=20 when the candidates tied exactly. **A one-case difference is not an ordering.** | [ran] |
| M11 | **The promotion criterion is semantic answer agreement, not character acceptance** — decided 2026-09-07 under the plan's own stopping rule, after M7. Character α is reported beside it and ranks nothing; whether `harness.lora` reconciles them is S6's win condition. | decided |
| M12 | Applying that criterion to runs already on disk cost nothing: the case files store both answers, so a metric change re-scores four runs without re-running inference. Persisting the raw answers, not just the metric, is what made that possible. | [ran] |
| M13 | **No Gemini target clears the local 12B on this suite**: `gemini-3.5-flash-lite` 13/20 ($0.003), `gemini-3.8-flash` 13/20 ($0.13), `gemini-3.1-pro-preview` **8/20** ($0.29), against `gemma4:12b` 12/20 free. Paying 100× more scored worse. S1's gate failed three times. | [ran] |
| M14 | **The promotion criterion works: 14 of 15 discriminable pairs ordered correctly across three independent targets** — but the targets are peers of the best candidate, so this validates the criterion's mechanics, not the distillation claim. | [ran] |
| M15 | **Character α's concordance moved 1/5 → 4/5 across targets on identical candidates and cases**, because the pro target pretty-prints and the flash ones do not. Direct evidence that it measures layout. | [ran] |
| M19 | **SPECIALISATION HAPPENS.** A 10.9 M-parameter LoRA (0.58 % of `Qwen/Qwen3.5-2B`), two epochs on 600 generated cases on a free T4: **44/60 against the base's 6/60 on `val`** (+63.3 points) and **12/30 against 6/30** on the inverted-rule split it never saw (+20). Zero unparseable. Even across clinics: 15/20, 15/20, 14/20. | [ran] |
| M20 | **The false-promotion probe came back negative.** An adapter that had memorised the unpublished rule would gain on `val` and collapse on `delta`, where the rule inverts. This one improved there too — it learned to read the case, not to recite the protocol. | [ran] |
| M22 | **Specialisation by region is real and asymmetric.** Expert α: 0.70 on α, 0.40 on β. Expert β: 0.65 on α, 0.75 on β. Own 0.725 vs other 0.525. But on α's cases the two differ by **one case of twenty** — the routing signal exists in one region and not the other. | [ran] |
| M23 | **Match the training budget, not the epoch count.** A region holds a third of the corpus, so the same epochs give a third of the updates: the first α expert hit `train_loss` 1.079 against 0.103 and scored 3/20 on its own region. Comparing an undertrained expert with a trained one measures the budget. | [ran] |
| M21 | **Gradient checkpointing left on during generation corrupts output**, not just speed: the same adapter scored 0/60 with it on and 44/60 with it off. Together with the T4's missing bf16, that is three infrastructure zeros that each read exactly like the step's own falsification condition. | [ran] |
| M24 | **The protocol is separable as a thing to LEARN.** A kernel adapter trained only on receipts, means, compound growth and cone volumes — no physics anywhere in its corpus — calls `<calc>` on **30 of 30** fluid-mechanics cases (5.6 calls/case) and never malforms one. The physics expert, which knows Reynolds and Swamee-Jain, calls it **0** times in 30. `results/P8-harness-lora-20260909/`. | [ran] |
| M25 | ~~It is NOT separable as a thing to serve; two independently trained LoRAs interfere.~~ **WITHDRAWN 2026-09-09, same day: confounded.** Stacked 0/30 and blended 0/30 are real, but the two corpora taught different NOTATIONS — kernel 600/600 with `<calc>` and 0 LaTeX, domain 0/598 with `<calc>` and 433 with LaTeX — and every arm ran under the **domain's** system prompt ("show no working"), which contradicts the kernel's training contract and even the domain corpus's own targets. The corruption is the superposition of two taught surface forms, not evidence about weight-space composition. Composition is **unmeasured**. | [ran] |
| M27 | **Syntax is not the dominant failure**: of the stacked arm's 30 failures, **19 had every call clean** and still got the physics wrong. A grammar or a tag-repair pass addresses at most a third of the gap. | [ran] |
| M28 | **The domain adapter's physics has never been measured.** Under the eval prompt it emits only `{"answer": ...}` with no chain on 30/30 cases, ~2x off. A composition cannot be shown to gain from a half whose contribution was never established. | [ran] |
| M26 | **A timed-out `colab exec` is not a failed command**, and a failing restore must never be fatal. Under `set -e`/`pipefail` a CLI timeout on a git clone, and a 240 MB adapter upload, each killed a healthy L4 that had already restored its state. Verify the runtime's HEAD and retry; never let transport cost a session. | [ran] |
| M16 | **The adapter had never been graded until 2026-09-08.** Six infrastructure failures and three reclaimed free-Colab sessions: parser crash, memory leak, fp32 upcast, unwrappable layer class, old `torchao`, and a T4 without bf16. The base arms on `Qwen/Qwen3.5-2B` are banked at **6/60** (`val`) and **6/30** (`val_delta`). | [ran] |
| M17 | **A T4 has no bf16.** The base generates fine in it; every LoRA generation then dies with "no engine to execute this computation" and the arm reports 0 — which reads exactly like S4's falsification condition. Precision is chosen by `is_bf16_supported()`. | [ran] |
| M18 | Every local model here emits a reasoning channel before the answer; ollama returns the two separately, `think=false` works on qwen and 500s on gemma; and ollama's chat renderer ignores an assistant prefill, so mid-answer draft positions are unavailable locally. | [ran] |

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

## The withdrawal gap closed [ran] 2026-09-08

On multi-step fluid mechanics, `Qwen/Qwen2.5-3B-Instruct` distilled from 600
oracle-written chains and given a calculator scores **40/40 — the teacher's own
score**. The withdrawal gap on that region is **0.000**.

**Neither half works alone**, and that is the finding: base + calculator made 53
tool calls and scored **0/40**; the adapter without the tool scored **4/40**. The
architecture's split between a kernel that acts and an expert that thinks is the
difference between 4/40 and 40/40, measured with each half held out.

**The expert is bounded to its region**: held-out families were at 0/10 when the
session ended — which is why the plan promotes and withdraws per region.

**The clinical suite could never have shown this.** Its difficulty is unpublished
rules, so no frontier can be ahead. The physics domain has a computed oracle, a
+0.975 headroom, and a corpus the oracle itself filters.

## The substrate is unproven [ran] 2026-09-08

**vLLM 0.28.0 accepts a `LoRARequest` and silently serves the base model.** No
error, no warning, byte-identical output; all three adapters scored exactly the
base's 6/60. Adapter files valid, `base_model_name_or_path` matching,
`max_lora_rank` matching `r`, and no V0 to fall back to — `VLLM_USE_V1` is an
unknown variable in 0.28. Open causes: V1 LoRA is documented experimental; the
adapters adapt `q_proj`/`k_proj` under Qwen3 QK-norm; or a 0.28 regression.

**Never accept a serving number without checking that an adapter changes the
output.** The arm that caught this was the redundant-looking one.

## Colab Pro is available on this account [ran] 2026-09-08

**L4** (23 GB, cap 8.9) and **A100-SXM4** (40 GB, cap 8.0), both with real bf16.
This removes session-reclaim, removes the fp16 workaround that produced every
false zero, and makes vLLM possible for the first time.

**And the target does not have to be an API.** A 40 GB card can host a large
Qwen3.5 as the strong reference, and a same-family target **shares the adapters'
tokenizer** — which is exactly what C2/C3 said made true token-level acceptance
unmeasurable. Keep the A100 for the steps that need it (vLLM, the strong target,
the withdrawal gap); everything else runs on the L4.

## Working agreements carried in

- Never push to `main`; everything lands through a PR, documents included.
- Every document has a Spanish mirror, level by section count, in the same commit.
- Brief the experiment — what, why, which model, which provider, what falsifies
  it — **before** the run, not next to the report.
- Respect the architecture as given. Technical facts enter as engineering
  constraints inside it, not as objections to it.
