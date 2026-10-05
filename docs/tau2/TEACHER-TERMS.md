# Teacher terms: which models' outputs may train a published adapter

**The decision this informs.** We plan to publish small open adapters (QLoRA on
Gemma 4), trained by distillation, SFT or RL on τ²-bench airline trajectories that
a "teacher" model generates. This document lists which teachers' terms allow using
their outputs that way. It does not choose one. The user decides.

**How it was read.** Every source below was read on **2026-10-05**. A statement
marked **[read]** comes from the URL next to it. **[inferred]** marks my own
arithmetic or reading, such as VRAM estimates or what a clause implies. **[not read]**
marks a source I did not open, such as a provider's API terms. This is a reading of
public terms, not legal advice. Where a clause is ambiguous, this document says so
and leaves it unresolved.

Retrieval notes: openai.com and x.ai return HTTP 403 to direct fetches, so those
pages were read through a text-rendering proxy (`r.jina.ai/<url>`). The quotes are
the providers' own text, but the pages were not read directly. Hugging Face licence
files were downloaded from each repo's `resolve/main/LICENSE`.

---

## 0. Two facts that change the question

1. **The user simulator writes into the trajectories too.** τ²-bench runs an LLM as
   the *user* as well as the agent. The README example is
   `tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1`
   [read, https://github.com/sierra-research/tau2-bench README]. The user turns end
   up in the training data, even when they are masked out of the loss. So the
   user-simulator model's terms matter as much as the teacher's.
   [inferred] The clean setup uses a user simulator whose terms are as permissive as
   the teacher's.
2. **Where you call a model decides which terms apply, not which model it is.** The
   same Gemma 4 weights are Apache 2.0 when self-hosted. Called through the Gemini
   API, they fall under the Gemini API terms and their anti-competition clause (see
   §1.3). Through OpenRouter, the user must also follow each model's "Model Terms"
   [read, https://openrouter.ai/terms, "Last Updated: August 31, 2026"; it also
   prohibits using the service for "reselling API access to Models or otherwise
   developing a competing service"]. [inferred] For open weights, **self-hosting is
   the only route where the model licence is the whole story.**

---

## 1. Frontier APIs

### 1.1 Anthropic (Claude API)

- **Commercial Terms, D.4**, effective June 17, 2025
  [read, https://www.anthropic.com/legal/commercial-terms]:
  > "Customer may not and must not attempt to (a) access the Services to build a
  > competing product or service, including to train competing AI models or resell
  > the Services except as expressly approved by Anthropic; (b) reverse engineer or
  > duplicate the Services; …"
- **Usage Policy**, effective September 15, 2025, under "Do Not Abuse our Platform"
  [read, https://www.anthropic.com/legal/aup]:
  > "Utilization of inputs and outputs to train an AI model (e.g., "model scraping"
  > or "model distillation") without prior authorization from Anthropic"
- Ownership: "Customer (a) retains all rights to its Inputs, and (b) owns its
  Outputs" [read, commercial-terms §B].
- (a) Train another model: **no**, unless Anthropic gives prior authorization. The
  Usage Policy clause has no "competing" qualifier, so any training is covered.
  (b) Owning the outputs does not override the use restriction. (c) Publishing the
  adapter: no without authorization. (d) Tool calling: yes. Prices per MTok, input/output:
  Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 4.5 $1/$5; Batch API halves them
  [read, https://platform.claude.com/docs/en/about-claude/pricing].

### 1.2 OpenAI (API)

- **Services Agreement §3.3(e)**, effective January 1, 2026
  [read via proxy, https://openai.com/policies/services-agreement/]:
  > "Customer will not, and will not permit End Users to: … (e) except for a
  > Permitted Exception, use Output to develop artificial intelligence models that
  > compete with OpenAI's products and services;"
  
  > "'Permitted Exception' means Customer using Output to: (a) develop artificial
  > intelligence models primarily intended to categorize, classify, or organize data
  > (e.g., embeddings or classifiers), if these models are not distributed or made
  > commercially available to third parties; and (b) fine tune or customize models
  > provided as part of OpenAI's fine-tuning or other Services …"
- **Terms of Use** (consumer), effective January 1, 2026, prohibit: "Use Output to
  develop models that compete with OpenAI." [read via proxy,
  https://openai.com/policies/row-terms-of-use/]
- Ownership: "you … own the Output" [read, row-terms-of-use].
- (a) **Ambiguous.** Training is allowed unless the model "compete[s] with OpenAI's
  products and services", and the agreement does not define "compete". A published
  general tool-calling customer-service adapter could plausibly be read as
  competing. Neither Permitted Exception covers our case: (a) is for
  classifiers/embeddings that are *not distributed*, and (b) is OpenAI's own
  fine-tuning. (c) Publishing openly is ambiguous, leaning no. (d) Tool calling: yes.
  Rough prices per MTok via OpenRouter: gpt-5.5 $5/$30, gpt-5.4 $2.50/$15,
  gpt-5.6-sol $2/$10 [read, https://openrouter.ai/api/v1/models; OpenAI's own
  pricing page not read].

### 1.3 Google (Gemini API)

- **Gemini API Additional Terms**. The page shows "Last modified March 23, 2026" and
  the footer says "Last updated 2026-04-28 UTC"
  [read, https://ai.google.dev/gemini-api/terms]:
  > "You may not use the Services to develop models that compete with the Services
  > (e.g., Gemini API or Google AI Studio). You also may not attempt to reverse
  > engineer, extract or replicate any component of the Services, including the
  > underlying data or models (e.g., parameter weights)."
- Ownership: "Google won't claim ownership over that content." [read, same]
- (a) **Ambiguous.** It has the same "compete" shape as OpenAI and no definition.
  "Extract or replicate any component … including the underlying … models" could
  also be read to cover distillation. (c) Ambiguous, leaning no. (d) Tool calling: yes.
  Gemini 3.8 Flash costs $0.75/$3.75 per MTok through 2026-12-31 and $1.50/$7.50
  after that; Gemini 3.1 Pro Preview costs $2/$12
  [read, https://ai.google.dev/gemini-api/docs/pricing, updated 2026-10-01].
  **Gemma 4 is listed there free-tier only.** [inferred] If Gemma 4 runs through the
  Gemini API, this clause applies to it. Self-hosting it avoids that.

### 1.4 xAI (Grok API)

- **Terms of Service — Enterprise, §3.2 "Rights in Input and Output"**. The page
  shows no effective date, and the party is now "SpaceXAI LLC"
  [read via proxy, https://x.ai/legal/terms-of-service-enterprise]:
  > "Customer will not, and will not permit any third party to: (i) use any Output to
  > train any foundation models, large language models, or other artificial
  > intelligence systems except as may be expressly permitted in an Order Form; …"
- Ownership: Customer "owns all right, title, and interest in the Output in
  perpetuity" [read, same].
- (a) **No**, unless an Order Form permits it. The clause has no competition
  qualifier. (c) No. (d) Tool calling: yes. Grok 4.7 costs about $2/$6 per MTok via
  OpenRouter [read, openrouter models API].

### 1.5 Mistral (API / Studio)

- **Commercial Terms of Service**, effective September 25, 2026
  [read, https://legal.mistral.ai/terms/commercial-terms-of-service]:
  > "3.3. Output Restrictions. To the extent permitted by applicable law, Customer may
  > not use image Outputs to develop or train any image generation product that
  > competes with a Mistral AI Product."
  
  Restrictions (d)/(e) in the same document:
  > "(d) attempt to reverse engineer, decompile, or otherwise attempt to discover the
  > source code or underlying components (e.g., algorithms, weights, or systems) of
  > the Mistral AI Products, including using the Output or any modified version of the
  > Output to do any of the foregoing …; (e) use the Output or any modified version of
  > the Output to reverse engineer the Mistral AI Products;"
- Ownership: "Customer … owns all Output." (§3.1) [read]
- The Usage Policy, effective June 11, 2026, has no distillation or training clause
  [read, https://legal.mistral.ai/terms/usage-policy; searched for "distill" and
  "train" and found neither].
- (a) **Yes for text outputs, with a small ambiguity.** The only explicit training
  restriction covers *image* outputs. It is ambiguous whether (d)/(e) ("discover …
  weights … using the Output") reach behavioural distillation. Read literally, they
  target reverse engineering, not imitation. (c) Probably publishable. (d) Tool
  calling: yes. Mistral Medium 3.5 costs about $1.50/$7.50 per MTok via OpenRouter
  [read, openrouter models API].
- Open-weight Mistral models are covered in §2.7.

---

## 2. Open-weight models (self-hosted, so only the licence applies)

### 2.1 Google Gemma 4 (same family as our base)

- Licence: **Apache 2.0**. The HF card for `google/gemma-4-31B-it` says
  `license: apache-2.0` and links to https://ai.google.dev/gemma/docs/gemma_4_license
  [read, https://huggingface.co/google/gemma-4-31B-it]. The licence page is the
  Apache 2.0 text and was last updated 2026-04-01 [read,
  https://ai.google.dev/gemma/docs/gemma_4_license].
- The old **Gemma Terms of Use** now say "For Gemma 4 terms, see the Gemma 4
  license" [read, https://ai.google.dev/gemma/terms, last modified April 1, 2026].
  The old terms defined "Model Derivatives" to include any model "created by transfer
  of patterns of the weights, parameters, operations, or Output of Gemma", which
  explicitly includes distillation. That definition governed Gemma 1–3 and **does not
  govern Gemma 4** [read, same page].
- **Ambiguity:** the Gemma 4 licence page links a "Prohibited use" policy and an
  "Intended use statement" in its navigation. It says nothing about whether they are
  binding on Apache-licensed Gemma 4 [read, gemma_4_license page]. The Prohibited
  Use Policy ("You may not use nor allow others to use Gemma or Model Derivatives
  to: …", last modified February 21, 2024) contains no clause on training other
  models [read, https://ai.google.dev/gemma/prohibited_use_policy].
- (a) **Yes.** Apache 2.0 places no restriction on outputs. (b) Apache §4 notice and
  attribution obligations apply if the adapter is treated as a Derivative Work. Our
  adapter is *already* a derivative of the Gemma 4 base, so the teacher adds no new
  obligation. (c) **Yes**, under the same licence as the base. (d) Sizes are 31B
  dense, 26B-A4B MoE, 12B, E4B and E2B. Official QAT q4_0 and w4a16 builds exist
  [read, HF model list for google/gemma-4-*]. [inferred] The 31B is about 62 GB in
  bf16, so it fits one 80 GB GPU with modest KV cache. On 40 GB it needs the
  official 4-bit QAT build (about 17–20 GB). Native function calling: yes [read, card].
  Via OpenRouter it costs about $0.09/$0.34 per MTok, but OpenRouter's terms then
  apply [read, openrouter models API].
- Headroom note, from the card and not our measurement: the card reports "Tau2
  (average over 3)" of **76.9%** for the 31B, against 68.2% for the 26B-A4B and
  69.0% for the 12B [read, gemma-4-31B-it README]. The averaging is not defined on
  the card and the figure is self-reported. [inferred] The gap between teacher and
  student within the family is about 8 points on that metric. That is the
  maximum effect available from a same-family teacher, before any of our measurements.

### 2.2 OpenAI gpt-oss-120b (open weights)

- Licence: **Apache 2.0** [read, HF API tag `license:apache-2.0`,
  https://huggingface.co/openai/gpt-oss-120b]. The USAGE_POLICY file reads in full:
  "We aim for our tools to be used safely, responsibly, and democratically, while
  maximizing your control over how you use them. By using OpenAI gpt-oss-120b, you
  agree to comply with all applicable law." [read,
  https://huggingface.co/openai/gpt-oss-120b/blob/main/USAGE_POLICY]
- The OpenAI Services Agreement's "compete" clause governs *the Services*, meaning
  the API. Self-hosted gpt-oss weights are not the Services. [inferred]
- (a) **Yes.** (c) Yes, with Apache notice. (d) [inferred] MXFP4 weights of about
  63 GB fit one 80 GB GPU, but not 40 GB. Tool calling: yes. It costs about
  $0.04/$0.17 per MTok via OpenRouter [read, openrouter models API].

### 2.3 DeepSeek (V4 / V4.1)

- Weights: **MIT**. Examples are `DeepSeek-V4-Pro-0813` (about 1.65T params),
  `DeepSeek-V4.1-Flash` (about 763B) and `DeepSeek-V4-Flash-0731` (about 304B)
  [read, HF LICENSE file and HF API]. The V4-Pro README says "This repository and
  the model weights are licensed under the MIT License." [read]
- **The API terms are explicitly permissive.** DeepSeek Open Platform Terms of
  Service, effective April 29, 2026
  [read, https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html]:
  > "You may apply the Inputs and Outputs of the Services to a wide range of use
  > cases, including personal use, academic research, derivative product
  > development, training other models (such as model distillation), etc."
- (a) **Yes, both self-hosted and via the API.** This is the only API that names
  distillation as permitted. (c) Yes. (d) None of these fit on 40/80 GB [inferred].
  The API supports "Tool Calls". deepseek-flash costs $0.15–0.30 input and
  $0.60–1.20 output per MTok, and deepseek-v4-pro costs $0.66–1.32 and $1.98–3.96,
  on off-peak/peak rates [read, https://api-docs.deepseek.com/quick_start/pricing].
  Note: using the API means accepting DeepSeek's data handling and Chinese-law
  provisions in the same terms (not analysed here).

### 2.4 Qwen (Qwen3.8)

- **Qwen3.8-27B: Apache 2.0** [read, HF card `license: apache-2.0`,
  https://huggingface.co/Qwen/Qwen3.8-27B].
- **Qwen3.8-2.4T-A95B: "Qwen3.8-Max License"** [read,
  https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B/blob/main/LICENSE]. It is MIT-like,
  with two conditions:
  > "If the Software (or any derivative works thereof) is Used for any of the
  > licensee's commercial products or services that have more than 100,000,000
  > monthly active users or US$ 20,000,000 … monthly revenue, respective model name
  > must be prominently displayed …"
  
  > "If the licensee or any of its affiliates conducts a Model as a Service or AI
  > Work Assistant business, and the aggregate revenue … exceeds US$50,000,000 …,
  > the licensee shall obtain a separate license from Qwen …"
- **Qwen3.8-Flash-Next (about 180B): "Qwen Community License 1.0"** [read,
  HF LICENSE]. It is the same text, except the MaaS/AI-Work-Assistant condition has
  **no revenue threshold**: "If the licensee … conducts a Model as a Service or AI
  Work Assistant business, the licensee shall obtain a separate license".
- Nothing in these licences mentions outputs or distillation. **Ambiguous:** they
  do not define "derivative works", so it is unclear whether a model trained on
  outputs counts as one. If it does, the conditions travel with the adapter to
  anyone who uses it commercially. For Flash-Next, that includes any MaaS operator
  of any size. [inferred]
- (a) 27B: yes. 2.4T and Flash-Next: probably yes, ambiguous at the derivative
  boundary. (c) 27B: yes. The others are publishable, but downstream conditions may
  attach. (d) [inferred] 27B is about 56 GB in bf16 and fits 80 GB, or 40 GB at 8/4-bit.
  The 2.4T needs an API. OpenRouter prices: qwen3.8-27b $0.42/$2.55, 2.4T $2/$6
  [read, openrouter models API]. Alibaba's own API terms (Qwen Cloud) [not read].

### 2.5 Meta Llama 4

- **Llama 4 Community License**, version date April 5, 2025, §1.b.i
  [read, https://dev.meta.ai/llama/llama4/license/]:
  > "If you use the Llama Materials or any outputs or results of the Llama Materials
  > to create, train, fine tune, or otherwise improve an AI model, which is
  > distributed or made available, you shall also include "Llama" at the beginning
  > of any such AI model name."
  
  The same section requires "Built with Llama" when you redistribute Llama
  Materials or derivatives. §1.b.iv incorporates the Acceptable Use Policy "by
  reference". §2 applies a 700M-MAU threshold [read].
- (a) **Yes, with conditions.** Training on outputs is explicitly contemplated.
  (b) A published adapter would have to be named "Llama-…", which conflicts with a
  Gemma-based adapter's identity, and the Llama AUP binds use. (c) Publishable, but
  only under the naming condition. (d) Maverick is 17B active/128 experts, about
  400B total, so it needs an API [inferred]. It costs about $0.19/$0.65 via
  OpenRouter [read]. [inferred] It is weaker than 2026 alternatives as a teacher.

### 2.6 GLM (Z.AI), Kimi (Moonshot), MiniMax

- **GLM-5.3-Flash (about 321B): MIT** [read, HF LICENSE,
  https://huggingface.co/zai-org/GLM-5.3-Flash]. **GLM-5.3 (about 753B): "GLM-5.3
  License"** [read, HF LICENSE]. It is MIT-like. Its only condition is a security
  review for MaaS operators with more than **US$10 billion** revenue over 12 months.
  Nothing on outputs. Same "derivative works" ambiguity as Qwen. In practice that
  condition can never bind us. API only at these sizes [inferred]. OpenRouter:
  glm-5.3-flash $0.15/$0.50 [read].
- **Kimi K3 (about 2.8T): "Kimi K3 License"** [read,
  https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE]. MaaS businesses
  above US$20M revenue need a separate agreement. Products above 100M MAU or US$20M
  monthly revenue must display "Kimi K3". Both conditions are waived for internal
  use. **Kimi K2.6** is "Modified MIT" with the display condition only [read,
  HF LICENSE page]. Nothing on outputs. "Derivative works" is ambiguous in the same
  way. OpenRouter: kimi-k3 $1.39/$14 [read].
- **MiniMax-M3 (about 427B): "MiniMax Community License"** [read,
  https://huggingface.co/MiniMaxAI/MiniMax-M3/blob/main/LICENSE]. The grant is
  "to deal in the Software **for non-commercial purposes**". Commercial use of the
  Software "or any derivative work thereof" requires displaying "Built with MiniMax
  M3" plus a notice or authorization to MiniMax. The appendix lists prohibited uses,
  including "any military purpose". **Ambiguous, and more restrictive:** if an
  output-trained adapter counts as a derivative work, its downstream commercial users
  inherit these conditions, and our open licence would conflict with them.
  OpenRouter: $0.30/$1.20 [read].

### 2.7 Mistral open weights

- **Mistral-Small-4-119B-2603: Apache 2.0** [read, HF API tag]. **Mistral-Large-3-675B:
  Apache 2.0** [read, HF API tag].
- **Mistral-Medium-3.5-128B: "Modified MIT"** [read, HF LICENSE]:
  > "You are not authorized to exercise any rights under this license if the global
  > consolidated monthly revenue of your company (or that of your employer) exceeds
  > $20 million … This restriction … applies to the Model and any derivatives,
  > modifications, or combined works based on it …"
  
  Whether an output-trained adapter is a "derivative … based on it" is **ambiguous**.
- (d) [inferred] Small-4-119B needs about 120 GB at FP8. The official NVFP4 build
  (about 60–65 GB) fits 80 GB but needs FP4-capable hardware (Blackwell). An A100
  has no native FP4. It does not fit 40 GB.

---

## 3. τ²-bench's own licence and its task data

- Repository licence: **MIT**, "Copyright (c) 2025 Sierra Research". The LICENSE
  file and `pyproject.toml` both say `license = "MIT"` [read,
  https://github.com/sierra-research/tau2-bench, LICENSE and pyproject.toml].
- Task data lives *inside* that repository (`data/tau2/domains/airline/`: `tasks.json`,
  `split_tasks.json`, `policy.md`, `db.json`). No separate data licence was found in
  the repo, and the README states none [read, GitHub contents API]. [inferred] The
  MIT licence of the repository therefore covers the task data. It is not stated
  explicitly for the data.
- The airline domain comes from the original τ-bench, which is also **MIT**
  [read, https://github.com/sierra-research/tau-bench].
- Airline split: **train 30, test 20, base 50** [read, `split_tasks.json`]. The README
  says: "If you are evaluating an agent (not training), use the `base` task split …
  This is the default." [read]. [inferred] `base` = train ∪ test. Any published
  number on `base` or on the leaderboard therefore includes the 30 tasks the adapters
  were trained on. Published adapters should report **test (20) only**, or say why not.
- [inferred, ambiguous] The repo also contains `data/tau2/results/` and
  `data/tau2/user_simulator/` [read, contents listing]. Trajectories that others
  generated with closed models (leaderboard runs) are MIT in the repo. The
  generating provider's output terms bound whoever ran them, not us. Whether
  training on *those* is clean is unresolved, and this document does not resolve it.

---

## 4. Summary table

| Model (route) | Outputs may train a **published** model | Key clause | Tool calling | Cost / serving |
|---|---|---|---|---|
| Claude (Anthropic API) | **No** (without prior authorization) | AUP: "Utilization of inputs and outputs to train an AI model … without prior authorization"; CTOS D.4 | yes | Sonnet 5.5 $2/$10; Opus 5.5 $4/$20 per MTok |
| GPT-5.x (OpenAI API) | **Ambiguous → leaning no** | SA §3.3(e) "use Output to develop artificial intelligence models that compete"; exceptions don't fit | yes | gpt-5.6-sol ~$2/$10; gpt-5.5 ~$5/$30 |
| Gemini (Gemini API) | **Ambiguous → leaning no** | "may not use the Services to develop models that compete with the Services" | yes | 3.8 Flash $0.75/$3.75 (to 2026-12-31) |
| Grok (xAI API) | **No** (unless Order Form) | Ent. ToS §3.2 "use any Output to train any … artificial intelligence systems" | yes | ~$2/$6 |
| Mistral (API) | **Yes** (text); minor ambiguity in (d)/(e) | only image-output training restricted (§3.3) | yes | Medium 3.5 ~$1.5/$7.5 |
| **Gemma 4 31B (self-host)** | **Yes** | Apache 2.0; old "Model Derivatives" terms don't govern Gemma 4 | yes (native) | 80 GB bf16 / 40 GB 4-bit QAT; ~$0.09/$0.34 hosted |
| **gpt-oss-120b (self-host)** | **Yes** | Apache 2.0; usage policy = "comply with all applicable law" | yes | 80 GB (MXFP4), not 40 GB; ~$0.04/$0.17 hosted |
| **DeepSeek V4 / V4.1 (API or weights)** | **Yes (explicit)** | API ToS: "training other models (such as model distillation)"; weights MIT | yes | API only at these sizes; flash $0.15–0.30/$0.60–1.20 |
| Qwen3.8-27B (self-host) | **Yes** | Apache 2.0 | yes | 80 GB bf16 / 40 GB quantized; ~$0.42/$2.55 hosted |
| Qwen3.8-2.4T / Flash-Next | Yes, **ambiguous** at "derivative works" | MaaS/AI-Work-Assistant license condition (Flash-Next: no threshold) | yes | API; 2.4T ~$2/$6 |
| GLM-5.3-Flash / GLM-5.3 | Yes / yes (ambiguous derivative; only >$10B MaaS condition) | MIT / GLM-5.3 License | yes | API; flash ~$0.15/$0.50 |
| Kimi K3 / K2.6 | Yes, **ambiguous** at "derivative works" | MaaS >$20M + display conditions | yes | API; K3 ~$1.39/$14 |
| MiniMax-M3 | **Ambiguous** (non-commercial grant; conditions on derivatives) | "for non-commercial purposes"; "Built with MiniMax M3" | yes | API; ~$0.30/$1.20 |
| Llama 4 Maverick | Yes, **with naming condition** | "include "Llama" at the beginning of any such AI model name" | yes | API; ~$0.19/$0.65 |
| Mistral-Small-4-119B (self-host) | **Yes** | Apache 2.0 | yes | 80 GB only with NVFP4 (Blackwell); not A100/40 GB |

Prices are USD per million tokens, input/output. Unless the row cites the
provider's own page, they come from OpenRouter's public models API on 2026-10-05
and depend on the provider. Calling a model through OpenRouter adds OpenRouter's
terms and the upstream model's terms.

---

## 5. The cleanest options for publication (not a decision)

These are listed in the order the terms make them clean, not by expected quality.
The user chooses.

1. **Gemma 4 31B, self-hosted, as both teacher and user simulator.** The teacher's
   licence is the same Apache 2.0 as the base, so the adapter's provenance is one
   licence end to end. It fits the A100-80GB in bf16, or 40 GB with the official
   4-bit QAT build. The card's own τ² figure gives an available gap of about 8 points
   over the 26B/12B. That ceiling is small, and it is the first thing to measure
   (headroom before treatment). Do not call it through the Gemini API, because that
   adds §1.3.
2. **gpt-oss-120b, self-hosted.** Apache 2.0, a one-line usage policy, and it fits a
   single 80 GB GPU. It is a different family from the student, so it brings
   different behaviour, which may help or hurt. It does not fit the 40 GB tier.
3. **DeepSeek V4/V4.1 via the DeepSeek API.** It is the only *API* whose terms
   name distillation as permitted, and it is cheap. The costs: data goes to a
   provider under Chinese-law terms (not analysed here), and the model is not
   self-hostable on our hardware.

Not recommended for a published adapter without a separate agreement: Claude,
Grok (explicit prohibitions). Also not recommended: GPT, Gemini (an undefined
"compete" clause). MiniMax-M3 and Llama 4 carry conditions that would travel with,
or rename, the adapter. Qwen3.8-27B (Apache 2.0) is as clean as option 2 on terms.
It was left out of the top three only because 1–3 already cover same-family,
single-GPU and API routes.

Whatever the teacher, the user-simulator model must sit under equally clean terms
(§0.1). The adapter card should also report τ² airline **test (20)**, not `base`
(§3).
