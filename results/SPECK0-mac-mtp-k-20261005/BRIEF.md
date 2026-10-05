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
