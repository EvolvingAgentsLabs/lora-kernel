# S4 — the first adapters

**Question, in two parts.**
1. **Does specialisation happen at all?** Does a QLoRA adapter over
   `google/gemma-4-E4B-it` beat that same base on cases neither of them was
   trained on?
2. **Do experts differ by region?** Does an adapter trained on clinic `alpha`
   beat one trained on `beta` **on alpha's cases**, and the reverse?

**Falsification, written before the run.**
- Question 1 fails if the adapter does not beat the base on `val`. Then
  specialisation did not happen and no routing scheme rescues it.
- Question 2 fails if the region experts do not each win on their own region.
  Then the pool is one expert wearing three names, **there is nothing for
  acceptance to route between**, and the architecture's central claim is over —
  for the price of a free T4.
- Either way the delta probe travels with the number: `val_delta` is the clinic
  where an unpublished rule **inverts** and it is in no training split. Gain on
  `val` with a collapse on `val_delta` is a memorised rule, not an expert, and
  both numbers are published together.

**Arms.** Four adapters' worth of compute, but only one hypothesis each: base
(no adapter), all-clinics adapter, alpha-only adapter, beta-only adapter. No
frontier is involved and none is needed — S1 established there is no frontier
advantage to distil on this task.

**Data.** 600 generated training cases from clinics alpha/beta/gamma, generated
with the sealed benchmark's own generator at seed 20260907, leak-checked against
the sealed splits. Evaluation on 120 `val` and 60 `val_delta` cases, and 40 per
cell for the region matrix. Nothing evaluated was trained on.

**Model.** `google/gemma-4-E4B-it`, 4-bit NF4, LoRA r=16 α=32 on all attention
and MLP projections, 3 epochs, lr 2e-4, effective batch 16, greedy decoding at
64 new tokens. `gemma-4-26B-A4B-it` is the same script on an A100 and is the next
run, not this one.

**Where it runs.** A Colab T4 driven by the Colab CLI from this machine — the
adapter step is executed here, not handed to a person with a browser.

**Cost.** Free tier. Wall clock is the budget: roughly an hour for four arms.

**Abort rule.** Results are written after **each** arm. If the session is
reclaimed, whatever landed is kept and the run resumes from the next arm rather
than from the beginning.

**Redesign count.** 0. Nothing about the instrument changes for this run.
