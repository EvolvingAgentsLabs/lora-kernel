# SPECK0 — the MTP drafter's draft length on the Mac: is the slowdown the length, or the cost of a round? (pre-registered 2026-10-05)

**Why.** The user, 2026-10-05: *"¿por qué el MTP no acelera al 12B, debería, estamos haciendo algo mal?"* MAC2 **[ran]**
measured llama.cpp's MTP on the 12B at 0.66× (base, general, α 0.53) and 0.52× (LoRA, domain, α 0.37), where MLX gave 1.25×
on the base (MAC **[ran]**). MAC2 never set the draft length; llama.cpp build 11146's default `--spec-draft-n-max` is **3**
**[read]** `llama-server --help`. The expected tokens a round yields, with acceptance $\alpha$ and draft length $k$:

$$E(\alpha, k) = \frac{1 - \alpha^{k+1}}{1 - \alpha}, \qquad \text{speed-up} = \frac{E(\alpha,k)}{C(k)}$$

where $C(k)$ is a round's cost in no-speculation decode steps. MAC2's 0.66× at $E(0.53, 3) = 1.96$ implies
$C(3) \approx 3.0$ — a round costs three plain steps. If $C$ is mostly per-token (verification on Metal at 4 bits), shorter
drafts pay; if it is mostly fixed per round (the draft head's own pass, synchronisation), no $k$ pays.

**What.** MAC2's runner and prompts unchanged (`examples.mac.llamacpp_spec_lora`): the 12B Q4_0 with the wiki LoRA GGUF,
per request scale 0/1, 6 domain + 4 general prompts, greedy, 160 tokens. Configs: `nospec`, `mtp_k1`, `mtp_k2`, `mtp`
(k = 3, the default, re-measured in the same sitting). **Model and provider:** local, the user's MacBook Air M4 16 GB,
llama.cpp build 11146, Metal — approved by the user 2026-10-05, ~22 min. No Colab, no API.

**Reported:** per (k, expert, set) speed-up, acceptance, identical outputs, and the implied $C(k) = E(\hat\alpha, k) /
\text{speed-up}$.

**Verdict, written first.**
- **THE LENGTH WAS WRONG** — some $k \in \{1, 2\}$ gives ≥ 1.1× on base/general **and** beats k = 3 there by ≥ 0.15×.
- **THE ROUND COSTS TOO MUCH** — no $k$ reaches 1.0× on base/general: the overhead is per round in this engine, and what
  remains to change is the engine (MLX's 1.25× is the comparison) or an aligned drafter, not a flag.
- In between (some $k$ ≥ 1.0× but < 1.1×): **MARGINAL**, said with the numbers.
- The LoRA/domain rows are read beside, not gated: their ceiling is set by α ≈ 0.37 ($E \le 1/(1-\alpha) = 1.59$ for any $k$).

**Stopping condition.** One sitting, these four configs, nothing added after the first number. Redesign count: 0.

## Result [ran] 2026-10-05 — THE ROUND COSTS TOO MUCH: no draft length pays on this engine

One sitting, ~22 min, `speck0.json`, `run.log`, `server_*.log`. No speculation: 12.8 / 13.3 tok/s (base, domain / general),
12.6 / 12.5 (LoRA). The swap re-checked: on 0.95 ms, off 1.55 ms, base restored exactly; G1 6/6.

| k | expert / set | speed-up | acceptance $\hat\alpha$ | $E(\hat\alpha,k)$ | implied $C(k)$ | identical |
|---|---|--:|--:|--:|--:|--:|
| 1 | base / domain | **0.88×** | 0.97 | 1.97 | 2.24 | 6/6 |
| 1 | base / general | **0.72×** | 0.74 | 1.75 | 2.42 | 4/4 |
| 1 | LoRA / domain | 0.68× | 0.61 | 1.61 | 2.37 | 6/6 |
| 1 | LoRA / general | 0.69× | 0.68 | 1.68 | 2.43 | 4/4 |
| 2 | base / domain | 0.85× | 0.88 | 2.67 | 3.14 | 6/6 |
| 2 | base / general | 0.56× | 0.64 | 2.05 | 3.65 | 4/4 |
| 2 | LoRA / domain | 0.49× | 0.49 | 1.74 | 3.54 | 6/6 |
| 2 | LoRA / general | 0.61× | 0.56 | 1.88 | 3.09 | 2/4 |
| 3 | base / domain | 0.76× | 0.77 | 2.80 | 3.69 | 6/6 |
| 3 | base / general | 0.57× | 0.53 | 1.97 | 3.45 | 4/4 |
| 3 | LoRA / domain | 0.50× | 0.37 | 1.56 | 3.12 | 6/6 |
| 3 | LoRA / general | 0.57× | 0.46 | 1.78 | 3.12 | 4/4 |

**By the table written first: THE ROUND COSTS TOO MUCH.** The best base/general is 0.72× (k = 1), under 1.0×. k = 3 reproduces
MAC2 (0.57× against 0.66×; 0.50× against 0.52× with the LoRA on its domain, same acceptance 0.37).

**Reading.**
1. **The draft length was not what MAC2 got wrong.** Shorter is better, but even k = 1 with 97 % of drafts accepted — the
   best case a drafter can offer — runs at 0.88×: one round that drafts **one** token costs about **2.2–2.4** plain decode
   steps on this engine, and each extra drafted token adds roughly another 0.5–0.7. A round that costs more than two steps
   cannot pay with any drafter, aligned or not, since $E \le k + 1$.
2. **So on this Mac the problem is llama.cpp's MTP path, not the drafter's quality.** MLX ran the same drafter at 1.25× on the
   base (MAC **[ran]**) — the comparison that says a round can be cheap here. Where llama.cpp spends the round (the MTP head's
   own pass, synchronisation between draft and verify, verification at batch k + 1 on Metal at 4 bits) is **not measured**:
   the server's `timings` give totals, not phases.
3. $\hat\alpha$ is the mean acceptance over drafted tokens, not a per-position rate; $E$ with it is an approximation (later
   draft positions are accepted less, which is why $\hat\alpha$ falls as $k$ grows). The conclusion does not rest on it: the
   k = 1 rows need no model.
4. **Output identity** held in 46 of 48 texts; two general texts at k = 2 with the LoRA differ — near-ties flipped by a
   different batch shape in verification (F0c's reading on vLLM). Recorded, not chased.

**What this changes.** Nothing in the serving decision (MAC2 already kept speculative decoding off on the `edge`); the
answer to the user's question is that the slowdown is the engine's cost per round, not a flag. On a 16 GB Mac, speculative
decoding is an MLX question: MLX's 1.25× on the base is the number to beat, and an aligned drafter (trained on the LoRA'd
target) would be measured there — not in llama.cpp.
