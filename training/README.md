# `training/` — the adapters

The rest of this repository measures *which* expert answers. This directory makes
the experts.

## Why it lives here and runs there

A 26B does not fit on the machine this project is developed on, and this project
is adapters — so anything needing a GPU ships as a notebook, committed, with its
data and its grader beside it. Open
[`lora_kernel_colab.ipynb`](lora_kernel_colab.ipynb) in Colab, set the runtime to
GPU, run it top to bottom.

## What is in the box

| file | what it does |
|---|---|
| [`build_dataset.py`](build_dataset.py) | generates the training corpus with the sealed benchmark's own generator at a different seed, and **refuses to write if any training prompt matches a sealed one** |
| [`evaluate.py`](evaluate.py) | the exact verifier — one copy, grading every arm, because a base and an adapter graded by different code are not comparable |
| [`lora_kernel_colab.ipynb`](lora_kernel_colab.ipynb) | baseline → QLoRA → adapter, then two region experts cross-evaluated |
| `data/*.jsonl` | 600 train, 120 val, 60 val_delta, plus per-clinic splits |

Regenerate the data with:

    python3 -m training.build_dataset --n-train 600 --n-val 120

## The two questions, and the probe

1. **Does specialisation happen?** The adapter must beat the base on `val`.
2. **Do experts differ by region?** The α-trained and β-trained adapters must each
   win on their own clinic — otherwise the pool is one expert with three names and
   there is nothing to route between.

And `val_delta` is the clinic where an unpublished rule **inverts**. It is in no
training split. An adapter that memorised the rule scores well on `val` and
collapses here; that gap is the **false-promotion** number and it is reported
beside every gain. A gain without it is not a result.

## Models

`google/gemma-4-E4B-it` on a free T4, `google/gemma-4-26B-A4B-it` on an A100.
`google/gemma-4-12B-it` is the baseline this workspace has already measured at
12/20 on the sealed delta split, so it is the honest thing to beat.

## Running it headlessly, from a terminal

The [Colab CLI](https://github.com/googlecolab/google-colab-cli) runs the same
code on a Colab GPU without a browser, which is what lets an agent execute this
step rather than hand it to a person:

    colab new --gpu T4 -s s4
    colab install -s s4 trl bitsandbytes
    colab exec -s s4        # bootstrap: clone this branch on the runtime
    colab exec -s s4 -f training/s4_train.py
    colab download -s s4 lora-kernel/s4_results.json ./s4_results.json
    colab stop -s s4

### One arm per session, because the free tier does not keep one

Colab reclaimed three sessions inside roughly forty minutes of GPU work each
**[ran]** 2026-09-08. [`chain_colab.sh`](chain_colab.sh) runs the experiment as a
chain instead: each session provisions, **restores the partial results from this
machine**, completes exactly one arm, hands the results back, and stops.

    training/chain_colab.sh        # one arm
    training/chain_colab.sh 3      # three arms, three sessions

The state of the experiment lives here between sessions, not on the runtime. It
is idempotent — an arm already in the results file is skipped — so running it
more times than there are arms left costs one session start and nothing else.

**Two install pins are load-bearing on macOS** — both were failures, not
precautions **[ran]** 2026-09-07:

    uv tool install --force --python 3.12 --with "jupyter-kernel-client<1" google-colab-cli

Python 3.13 loads a `cryptography` wheel whose Rust binding cannot find
`_BIO_ADDR_free`, and `jupyter-kernel-client` 1.x renamed `KernelClient`, which
the CLI still imports. Without both pins every command fails at import.

`--gpu` accepts `T4, L4, G4, H100, A100`; the larger ones need a Colab Pro
entitlement (`colab pay`).
