# D2 — the C18 mechanism: is it only the tensors' names? (pre-registered 2026-09-18)

**Question (one unknown).** P33 **[ran]**: vLLM 0.29.0 loads a LoRA on `Qwen/Qwen3.5-4B`,
logs `Loaded new LoRA adapter`, and serves the base. Is that a **naming mismatch** between
the adapter's tensors and the module tree vLLM activates by — so that the *same weights,
renamed*, are applied?

**Why now, and why it is cheap.** D2 is *the C18 mechanism, read with the log in hand*. It
was read today, zero GPU, in vLLM v0.29.0's source and P33's own log **[read]**:

- `Qwen3.5-4B` declares `Qwen3_5ForConditionalGeneration`; its checkpoint names the text
  stack `model.language_model.layers.N…`; vLLM's mapper rewrites exactly that prefix to
  `language_model.model.` (`models/qwen3_vl.py`).
- `tiny_adapter` loads through `AutoModelForCausalLM`, so PEFT writes
  `base_model.model.model.layers.N…` — no mapper prefix matches.
- Loading validates the **last component** only (`q_proj` is expected → *Loaded*).
  Activation looks up the **full name**, finds nothing, and calls `reset_lora` behind a
  `logger.debug` (`lora/model_manager.py`). P33's log shows the LoRA kernel JIT-compiling at
  inference: the slot was live, on zeros.

With $K$ the tensor names, $m$ the mapper, $M$ the served module names:
$\text{applied}(K)=\{k\in K: m(k)\in M\}$; as trained $|\cdot|=0$, renamed by $\rho$
(`training/harness/rekey.py`) predicted $|\text{applied}(\rho(K))|=|K|$.

**Set-up.** Colab **L4**, one session, `MODULE=training.harness.lora_matrix --rekey`,
`BASE=Qwen/Qwen3.5-4B`. No API provider, no frontier call. P33's procedure unchanged:
control `Qwen2.5-3B-Instruct` G1→G2; subject G1→G2. **Only if the subject's G2 fails**, the
subject's adapter is renamed — not retrained — and asked again (G2r). Subject serves run
with `VLLM_LOGGING_LEVEL=DEBUG` and the activation lines are counted per arm: the failure
measured where it happens, the served text being only where it surfaces.

**The verdict table, written before the run.**

| control | subject G2 | renamed G2r | reading | what we do |
|---|---|---|---|---|
| ✗ | any | any | **VOID** — the procedure broke | nothing is learned |
| ✓ | ✓ | not bought | C18 is gone under this install | record it; D2 closed by upstream |
| ✓ | ✗ | **✓** | **C18 is a naming mismatch** | a Qwen3.5 adapter is servable as a pool member: train through the served class, or rekey at release. D2 closed; D4 stays blocked on M2 |
| ✓ | ✗ | ✗, `modules_with_weights` > 0 | the weights land and are dropped downstream | Qwen2.5 stays; **stop** — no second arm this session |
| ✓ | ✗ | ✗, `modules_with_weights` = 0 | my reading of the mapper is wrong | read the DEBUG module names, zero GPU; Qwen2.5 stays |

**Falsified by:** G2r `not applied`. **Consistency check on the instrument:** the as-trained
subject should show `modules_with_weights = 0`; if it shows > 0 and still serves the base,
the naming reading is wrong even before G2r.

**What it does not measure.** Quality of a Qwen3.5 expert; the linear-attention projections
separately from the full-attention ones (the toy adapter targets all of them at once); the
27B. The S2L-derived `q_proj,v_proj`-only arm (plan, 2026-09-18) is **superseded** by this
one: the reading explains P33 without reference to which modules were targeted.

**Redesign counter for D2: 0.** This is its first arm.

**Guard added before launch.** If the renaming moves no tensor (`rekey.moved = 0`), PEFT did
not write the names this brief assumed; G2r is **not asked** and the run reads **VOID for
D2**, not falsified.
