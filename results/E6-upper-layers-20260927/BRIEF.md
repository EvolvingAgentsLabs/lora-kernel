# E6 — the school member with its LoRA on the upper half of the layers only

*Pre-registered 2026-09-27, before any session started. Phase 1 of the thesis review, approved by the user
([`docs/review/00-thesis-review.md`](../../docs/review/00-thesis-review.md) §5).*

**What.** `school-staff` trained again with M8's recipe and data, changing one thing: the LoRA reaches only decoder layers
$k\ldots N-1$ with $k=\lfloor N/2\rfloor$ (`train_one --layers-from half`; the targets are the same seven projections,
built as an explicit regex, `s4_train.layer_regex`). It is scored against the full member `school-s0` (M8, carried in) on
the same 70 held-out turns and the demo day.

**Why.** If an expert lives only in the upper half, the lower half is the base for every expert. Then three fronts open:
- switching experts within a generation without recomputing the lower KV;
- serving the lower half frozen (flash inference);
- measuring how much less a LoRA moves the activations the MTP drafter reads (C0: domain α 0.79 → 0.34 with the full LoRA).

The run answers none of those three. It answers the precondition: **does an expert survive being confined to the upper half?**

**Model and provider.** `google/gemma-4-E4B-it`, bf16. Colab, two sessions: T trains `upper-s0` on an L4, as M9 did;
S serves both arms with vLLM 0.30 on an L4.

**Headroom [ran] M8.** Bare base 27/70, full member 70/70 on these turns. There is room below the ceiling for the treatment
to lose; the question is non-inferiority.

**The mechanical check**, measured where it happens, in T's process right after training (`train_one.lower_layers_identical`):
- Four training prefixes run with the adapter on, off, and off again.
- *Control:* off against off must be bit-identical (`torch.equal`) in every hidden state. Otherwise the engine is
  nondeterministic here and the identity cannot be read (F0b's lesson).
- *Identity:* the inputs to layers $0\ldots k$ and the KV cache of layers $\lt k$ must be bit-identical between adapter on
  and off.
- *Activity:* layer $k$'s output must differ between on and off, so the adapter was actually active.
- *File:* the saved adapter must contain no tensor for a layer $\lt k$.
- If the KV cache class cannot be read, the identity rests on the inputs to layers $0\ldots k$, which determine that KV.
  This fallback is written here, before the run.

**Verdict — written first (`school_arm.e6`).** Let $\ell$ be the number of turns the full member passes and `upper-s0` fails.

| outcome | reading |
|---|---|
| G1 not applied, control not identical, or layer $k$ unmoved | **VOID** — the instrument, not the hypothesis |
| lower layers not bit-identical, or the file reaches below $k$ | **FALSIFIED** (identity) |
| $\ell\le 3$ and identity holds | **PASSED** |
| $\ell\gt 3$ | **FALSIFIED** (accuracy); the paired sign test is reported beside it |

The demo day is reported beside, never folded in.

**Stopping condition.** One seed, one scoring session. There is no redesign of the gate after a result. A FALSIFIED is
recorded as such; a different $k$ would be a new brief.

**Not in this run.** The second seed; other values of $k$; switching experts mid-generation; the drafter's acceptance under
`upper-s0`. The last is the next arm if E6 passes, and it is cheap: C0's spike with `upper-s0`.

## Result **[ran]** 2026-09-27 — **PASSED: 0 of 70 turns lost, and the layers below 21 are the base's bit for bit**

T (L4): `upper-s0` trained with M8's recipe on layers 21…41 of 42 (`file_layers` read back from the adapter).
S (L4, vLLM 0.30): G1 shows both adapters applied.

| arm | LoRA on | held-out turns | demo day |
|---|---|--:|--:|
| `school-s0` (full, M8, rescored) | layers 0…41 | **70/70** | 15/15 |
| `upper-s0` | layers 21…41 | **70/70** | 15/15 |

Paired on the 70 turns there are 0 discordant pairs: $\ell = 0 \le 3$.

**The mechanical check, in T's process (`lower_identity.json`).**
- Control: adapter off against adapter off is bit-identical.
- The KV cache of the 21 layers below $k$ is bit-identical with the adapter on and off, and so are the inputs to layers
  $0\ldots 21$.
- Layer 21's output moves, so the adapter was active.
- The file has no tensor below 21.

**By the table written first: PASSED.**

**What it means, and what it does not.**
- **The school expert survives being confined to the upper half.** On this suite it loses nothing, at about half the
  adapter's parameters.
- **The lower half is shared, bit for bit, by every expert trained this way.** That is the precondition for switching
  experts mid-generation without recomputing layers 0…20, and for a frozen lower half.
- **The E4B shares KV across layers:** it caches 24 of its 42 layers, and layers 24…41 reuse KV computed by earlier
  layers. The KV those upper layers read comes from layers 21…23, which *are* adapted. A switch keeps layers 0…20 and
  still recomputes 21…23. The `k_proj`/`v_proj` pieces of the LoRA on layers 24…41 probably act on nothing — a recipe
  detail, not measured here.
- **The suite sits at the full member's ceiling (70/70).** It shows the upper-half member is not worse *on this suite*;
  a loss on harder turns would be invisible. The bare base's 27/70 shows the suite does measure the adapter.
- One seed. Not measured: other values of $k$; the switch itself; how much the MTP drafter's acceptance recovers when the
  LoRA leaves the lower half. The last is cheap: C0's spike with `upper-s0`.
