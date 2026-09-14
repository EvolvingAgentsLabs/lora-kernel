
---

## The gate on `Qwen3.5-4B`, and why it is not yet an answer (2026-09-14) [ran]

    [serve] /v1/models -> ['Qwen/Qwen3.5-4B', 'kernel']
    [gate] kernel: IDENTICAL TO BASE — not applied

vLLM accepted the adapter, listed it as a model, and served **byte-identical text**.
That is C18 reproduced on a newer vLLM and a newer model — and it is **ambiguous**,
because the adapter handed to it was built for `Qwen2.5-3B`: different tokenizer
(151 665 against 248 077), different shapes.

    the class does not apply LoRA
    vLLM silently ignores a mismatched adapter

**The second would be the worse finding.** It would mean the identity gate cannot
tell a wrong adapter from an unsupported class, and a deployment could serve the base
while believing it serves an expert. This brief pre-registered an *explicit refusal*
as inconclusive; it did not anticipate **silent identity with a foreign adapter**, and
that is a gap in the pre-registration rather than in the result.

**So a native adapter is trained and the gate is asked again.** It does not have to be
good — a few hundred steps on any text — because the question is whether the stack
applies a delta, not whether the delta helps. Its target modules are **discovered from
the model** rather than listed, since a hardcoded list is a list for one architecture
and this is a base nobody here has adapted.

| the native adapter | reading |
|---|---|
| changes the output | the class applies LoRA; the earlier result was the foreign adapter, and **the stronger family is available** |
| does not | the class does not apply LoRA, and P32 runs on Qwen2.5 as planned |

Either way the instrument gains a correction that outlives this step: **the identity
gate is only conclusive with a native adapter**, and every earlier use of it — P26,
P29 — should be read with that in mind. P26's was native and stands; **P29's Gemma 4
result was an exit-1 before any weight loaded**, which is a different failure and is
unaffected.
