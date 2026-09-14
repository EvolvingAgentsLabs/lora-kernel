# P33 — one procedure, two bases, and a control that makes the answer readable

**Pre-registered 2026-09-14. This is urgent and it is designed to be decided in one
session.**

## Why every run today was unreadable

Four runs asked "does vLLM apply a LoRA to Qwen3.5?" and four came back
`IDENTICAL TO BASE`. Not one of them could distinguish:

    the model class does not apply LoRA
    the adapter was never trained properly
    the adapter changes nothing
    my own check was wrong          <- it was, twice

**There was no arm where the answer was already known.** Two of my diagnoses were
withdrawn — "the adapter touched only MLPs" (the loaded module tree does carry
`q_proj`) and "Qwen3.5 does not serve LoRA" (measured through a broken self-check).
Both were readings of an ambiguous result, and the ambiguity was the design's fault,
not the model's.

## The design: the same procedure, run on a base whose answer we have

| base | role | what we already know |
|---|---|---|
| `Qwen2.5-3B-Instruct` | **positive control** | vLLM applies a LoRA to it — P26 measured base 0/60 against adapter 20/60 **[ran]** |
| `Qwen3.5-4B` | subject | unknown |

**Both in the same session**, so the environment cannot be the difference. Three gates
per base, each conclusive on its own:

```
G1  train a tiny adapter, then in-process:   lora_B moved   AND   output changed
G2  serve it through vLLM:                   served text differs from the base
G3  only if G2 fails: merge and serve:       merged text differs from the base
```

G1 uses PEFT's own `disable_adapter` context around the **base** generation — the
idiom the first version of this check got backwards, generating twice through the
adapter and calling them identical.

## The verdict table, written before the run

| control (2.5) | subject (3.5) | reading | what we do |
|---|---|---|---|
| G1 ✓ G2 ✓ | G1 ✓ G2 ✓ | **Qwen3.5 is usable** | decide on merit: retrain on the stronger family, or stay |
| G1 ✓ G2 ✓ | G1 ✓ G2 ✗ | **vLLM does not apply LoRA to this class** | **Qwen2.5**, and G3 says whether merging is a fallback |
| G1 ✓ G2 ✓ | G1 ✗ | **it is a training problem, not a serving one** | Qwen2.5 now; unsloth's path is the open question |
| G1 ✗ | anything | **the procedure is broken** | nothing is learned about any model, and the run is void |

**That last row is the whole point.** It is the only way to tell "the subject is bad"
from "my code is bad", and it is the distinction every run today failed to make.

## What G3 buys, and what it costs

Merging writes the delta into the weights and serves an ordinary model. Unsloth's own
guide recommends exactly that for vLLM. **It works and it is not a pool**: one full
copy of the weights per expert, no shared base, no per-request swapping — which is
the thing this architecture exists to avoid. G3 is bought only to know whether a
fallback exists, and its cost is stated rather than discovered later.

## Falsification

- **The run is void** if the control fails G1 or G2. No claim about Qwen3.5 survives
  a broken procedure, and this brief will say so rather than reporting the subject's
  number.
- **The subject's G1 failing is a finding, not an error** — it means the adapter
  cannot be trained this way on this architecture, which is about the model.
- **A pass on both is not permission to switch.** It says the family is available;
  whether to pay for retraining is a separate decision with its own arithmetic.
