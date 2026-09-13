# P26 — the pool behind an OpenAI-compatible endpoint

**Pre-registered 2026-09-13, before anything was served.**

## Why now

The architecture's layer 1 is "one resident base, adapters swapped per request".
Everything measured so far has been `transformers` loading one adapter at a time,
or vLLM's **offline** `LLM` class. An agent runtime — OpenClaw, Hermes, anything
that speaks OpenAI — cannot call either of those. It calls
`POST /v1/chat/completions` with a `model` name.

vLLM's server registers each adapter as its own model name, which is exactly that
shape. **Nobody has run it.** This step runs it, and buys a second thing with the
same session: the mixed-batch cost, which P3 explicitly voided because the serial
loop it used measured round-trips instead of batching. Concurrent clients against
one server are what that measurement needed.

## The gate that comes first, and it is not throughput

**C18: vLLM 0.28.0 accepted a valid `LoRARequest` and served the base model — no
error, no warning, byte-identical output [ran]** `results/P3-vllm-20260908/`. Had
that step measured only throughput it would have reported three adapters served at
90 prompts/s and called the substrate proven.

So before any number is recorded:

1. `/v1/models` lists each adapter as its own model name.
2. **The same prompt to the base and to an adapter must produce different text.**
   Identical output means the adapter is not applied, and the run stops there and
   reports that rather than measuring anything.
3. The adapter's accuracy through the API must match what `transformers` measured
   on the same cases. A different number means one of the two stacks is wrong, and
   every earlier result is in question.

## The arms, in order, killing arm first

| # | arm | what it answers |
|--:|---|---|
| 1 | **serving identity** | does an adapter change the output at all — the C18 gate |
| 2 | **accuracy through the API** | do the numbers survive the serving stack |
| 3 | **pure vs mixed concurrency** | what holding a pool costs, measured inside one scheduling pass |

Arm 3 is bought only if 1 and 2 pass. A throughput number from a server that is
quietly ignoring its adapters is the exact failure C18 exists to prevent.

## Falsification

- **The substrate is unproven** if the base and adapter outputs are identical, as on
  `Qwen3.5-2B`. This is a real possible outcome and it stops the step.
- **The serving stack is wrong** if accuracy through the API differs materially from
  `transformers` on the same cases.
- **Per-request swapping is not a serving strategy** if a mixed batch costs so much
  more than a pure one that a pool has to be partitioned by model anyway.

## What this step does NOT do, said plainly

It does **not** give an agent runtime a working tool loop. The adapters emit
`<lookup>…</lookup>` in the message body; OpenAI clients expect `tool_calls`. An
agent pointed at this endpoint would receive prose containing tags and see no tools
at all.

**Bridging that is a separate question and it is not only plumbing**: the protocol
this project put into weights is a text protocol, and a translation layer that
converts it to `tool_calls` reintroduces the hand-written harness the weights were
meant to replace. **P26 serves the pool. Whether `harness.lora` survives contact
with function-calling is the next brief, not this one.**

---

## Attempt 1 — the boot gate refused three sessions (2026-09-13) [ran]

    boot vllm: rc=1 RuntimeError: Detected that PyTorch and TorchAudio were
    compiled with different CUDA versions. PyTorch has CUDA version 13.0
    whereas TorchAudio has CUDA version ...
    boot attempt 3 did not take: NO VLLM

Colab ships `torchaudio` and `torchvision` built against its own CUDA. Installing
vLLM resolves a different `torch` and leaves those two behind pointing at the old
one, and the mismatch raises on **import** — so `vllm` never starts at all.

**Neither is needed to serve a text model**, so both are removed before vLLM
arrives rather than pinned around. And the version check now imports the package
rather than shelling out to `vllm --version`, because importing is the thing that
was failing.

**Nothing was measured and that is the point.** The boot gate was added because a
serving experiment that reports throughput from a stack it never verified is the
C18 failure with a new face. It refused three sessions and cost nothing but their
provisioning.

---

## Attempt 2 — training does not belong in a serving session (2026-09-13) [ran]

vLLM 0.29.0 installed and imported once `torchaudio` and `torchvision` were removed
first. Then:

    ModuleNotFoundError: No module named 'trl'

The pool trainer had been wired into the serving chain to fill whatever the carried
tarball was short of. **A serving session has no `trl` because it has no reason to**
— and this brief already said retraining inside a serving run puts forty minutes and
a second source of variance into a question about HTTP. The smaller version of that
warning arrived as an import error.

So the two are separated:

- **`chain_serve.sh` no longer trains anything.** If the adapters are not on disk it
  prints the command that builds them and exits, rather than serving a pool of one
  and calling it a pool.
- **`train_pool` writes `pool.json`** when it finishes, because a chain cannot watch
  for a job that writes nothing — `chain_separate.sh` polls a results file, and
  without one it would have spent its whole session allowance on a job that finished
  in twenty minutes.

**A note that has to travel with whatever comes next.** P3's silent failure was on
vLLM **0.28.0** and this runs **0.29.0**, on a different base. If the identity gate
passes here, **two things changed at once** and the pass cannot be attributed to the
dense base alone.

---

## Attempt 3 — the adapter cache never worked, and the reason is a size limit (2026-09-13) [ran]

Both training sessions died at roughly sixty minutes with the adapters at forty
minutes of training each, and neither could resume, because the cache that exists to
carry them has never once succeeded:

    WARNING: adapters did not upload

**Measured against a live session rather than guessed:**

| size | `colab upload` |
|--:|---|
| 4, 16, 32, 48, 64 MB | ok |
| **80 MB** | **500 Internal Server Error, in 1.5 seconds** |

The tarball is **106 MB**. This is not a timeout — it fails immediately — so the
first repair anyone reaches for, raising the timeout, would have been time spent
chasing the wrong cause. The upload is now **split into 48 MB chunks and
reassembled on the far side**.

**Three runs today paid full retraining for this**, and each time the missing cache
looked like bad luck with session lifetimes rather than a bug that had never worked.
A component that has never succeeded and only ever logs a warning is indistinguishable
from one that works and is unlucky.

Also fixed here: the `_srun.py` heredoc in `chain_separate.sh` is unquoted so that
`$MODULE` interpolates, which means bash expanded a prose comment containing
backticks and printed `adapters/domain-mt: No such file or directory` into every run
log. The same bug was fixed in `chain_ollama.sh` this morning and not looked for
here.

---

## Attempt 4 — two sessions spent on a shell default and a capital letter (2026-09-13) [ran]

Both sessions of the retry ran for over an hour and produced nothing. The reason was
one line in the VM's own log, which no watcher ever passed through:

    train_pool.py: error: unrecognized arguments: --n-eval 30

**Two bugs, and the second is what made the first cost two hours.**

1. `ARGS="${ARGS:---n-eval 30 --epochs 3}"`. **`:-` substitutes on an empty string,
   not only on an unset one**, so passing `ARGS=""` to run a module that takes no
   arguments handed it another module's flags. `train_pool` died on argparse in its
   first second.
2. **The peek filter greps `Traceback|Error`, with a capital E.** argparse writes
   `error:` in lower case. The failure was in the log from the start and *nothing let
   it through*, so a session that had been dead since second one looked busy for
   seventy-seven minutes.

Both are fixed: `${ARGS-…}` substitutes only when unset, and the filter matches
`[Ee]rror` and `[pool]`.

**This is the same shape as the upload that never worked**: a component failing
silently while its supervisor watched for the wrong thing. The repair that matters is
not either line — it is that **the watcher and the runner have to share a
vocabulary**, or every module added later inherits the blindness.

**What survived attempt 4**: the chunked upload worked in both sessions —
`carried the adapters in (3 chunks)` — and the kernel adapter was on the VM's disk
each time. The cache is fixed; it was simply carrying weights to a job that had
already exited.

---

## Attempt 5 — the pool came home, and the server exited on a flag (2026-09-13) [ran]

**The infrastructure finally did the whole round trip.** Both adapters trained
(114/114 steps, loss 0.328), the tarball came back at 211 MB carrying two
`adapter_model.safetensors`, the serving chain's own guard confirmed there were two
before it would start, and vLLM 0.29.0 installed and imported on an A100.

Then:

    [serve] the server exited with 2 before it answered /health
    vllm: error: unrecognized arguments: --disable-log-requests

**Exit 2 is argparse.** The flag was removed in 0.29.0 and the server died before a
single weight was loaded. Quieter logs are not worth a flag that pins a version, so
it is gone rather than version-guarded.

Also raised: the boot timeout, from 900s to 1800s. Installing vLLM ran past fifteen
minutes once and the check that followed found nothing — which surfaces as
`boot attempt 1 did not take: silence`, indistinguishable from a dead channel.

**The identity gate has still not been evaluated.** Nothing in this brief's table has
a number in it, and after five attempts that is worth stating plainly rather than
letting the narrative imply progress: **the substrate question P3 opened is still
open.**

---

## Attempt 6 — the probe crashed at the moment the server became healthy (2026-09-13) [ran]

    json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

**vLLM's `/health` answers 200 with an empty body.** The readiness helper parsed
every response as JSON, and `JSONDecodeError` was not among the exceptions the
waiting loop caught — so the run crashed **at the exact moment the server came up**,
which is the one moment that looks like the server failing.

Two lines. The helper returns `{}` for an empty body, and the readiness loop catches
everything: **a readiness probe that is choosy about how it fails reports the wrong
thing.** Reproduced locally without a GPU before relaunching.

**The good news is inside the crash.** The server started, loaded the base and both
adapters, and answered. Every earlier attempt died before that: CUDA, a missing
package, a removed flag. This one died *after* success, on the client.

**Still no number.** Six attempts, and the identity gate is still unevaluated.

---

## Outcome (2026-09-13) [ran]

    /v1/models -> ['Qwen/Qwen2.5-3B-Instruct', 'kernel', 'domain']

### Arm 1 — the gate passes, and this is the result

| model | differs from base |
|---|---|
| `kernel` | **yes** |
| `domain` | **yes** |

They differ in the way they were trained to:

| | first words on the same prompt |
|---|---|
| base | `Let's solve this step-by-step:\n\n1. **Convert dimensions to meters:**` |
| **kernel** | `1. Area of the gate: <calc>1844.2 * 723.6</calc>= 133590.6` |
| **domain** | `1. Gate width: 1.8442\n2. Gate height: 0.7236\n3. Density of the fluid: 1395.2` |

The kernel writes the protocol and delegates the arithmetic; the domain writes the
physics in numbered steps and never emits a tag. **Two personalities over one
resident base, selected by the `model` field of an HTTP request.** This is the
question P3 left open on 2026-09-08 and it is answered.

**The caveat travels with it.** P3's silent failure was vLLM **0.28.0** on a hybrid
multimodal base; this is **0.29.0** on a dense one. **Two things changed**, so the
pass cannot be attributed to the dense base alone.

### Arm 2 does not test what it was built to test

| | |
|---|--:|
| `served · kernel` | **0/30** |
| `served · domain` | **0/30** |

Both zeros are expected and neither is about vLLM. **The kernel delegates**: it emits
`<calc>…</calc>` and waits for an answer that a single-turn `/v1/chat/completions`
never provides, so there is no final value to score. **The domain cannot do
arithmetic**: already measured at 1/30 raw against 30/30 when its own expressions are
re-evaluated exactly.

So the arm's stated job — *do the numbers survive the serving stack* — **cannot be
done this way.** That comparison needs the same **harness**, not merely the same
cases, and no earlier arm scored raw single-turn output. **This is a defect in the
instrument, named rather than dressed up**: the zeros say nothing about serving
fidelity in either direction, and the fidelity question is still unanswered.

### Arm 3 — the pool costs nothing measurable, and the measurement is weak

| | seconds | prompts/s |
|---|--:|--:|
| concurrency · pure | 11.14 | 2.69 |
| concurrency · mixed | 9.97 | **3.01** |

The mixed batch came out **faster**, which is not a result anyone should publish as
"a pool is free and then some". **The two bursts run in a fixed order, pure first**,
so the first one pays whatever warm-up exists and the second does not. A −11.9%
"cost" is the size of that confound, not a finding.

**What it does support**: the catastrophic version is ruled out. P3's voided arm
reported a **20×** penalty for holding a pool, measured by a serial loop that was
counting round-trips. Inside one scheduling pass, two adapters interleaved are within
noise of one — **per-request swapping is not disqualified as a serving strategy**,
which is what the arm was bought to find out. **Ordering it properly, with a warm-up
burst and repeats, is unbought.**

## What P26 delivers, and what it does not

**Delivers**: an OpenAI-compatible endpoint where each adapter is its own model name,
verified to actually apply, on a base this project already uses. An agent runtime can
point at it today.

**Does not deliver**: a working agent. The adapters emit `<calc>` and `<lookup>` in
the message body; OpenAI clients expect `tool_calls`. **An agent pointed here sees
prose containing tags and no tools at all** — as this brief said before the run, and
the transcripts above are the evidence rather than the prediction.
