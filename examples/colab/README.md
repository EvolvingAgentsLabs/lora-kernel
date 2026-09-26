# Colab: a LoRA that walks a library instead of memorising it

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EvolvingAgentsLabs/lora-kernel/blob/main/examples/colab/wiki_walk.ipynb)

[`wiki_walk.ipynb`](wiki_walk.ipynb) loads `gemma-4-E4B-it` in bf16 with the released
[`distributor-wiki@v2`](https://huggingface.co/Matias/lora-kernel-distributor-wiki-gemma4-e4b) adapter. It asks six
two-hop questions from W9's evaluation world, first to the bare model and then to the adapter. Then it edits one number
in one markdown page and asks again. It needs a bf16 GPU (L4 or A100) and no Hugging Face login.

The grade is the repository's own (`training/wiki/grade.py`):

    credit = value_right ∧ citation_verified

A citation is verified when the cited section was opened in this walk *and* holds the value, so an answer can't
earn credit by quoting a number the page no longer says.

## What it printed **[ran]** 2026-09-26, L4, Colab — [`run-l4-20260926.log`](run-l4-20260926.log)

| | credit on 6 two-hop questions |
|---|---|
| bare `gemma-4-E4B-it`, same runtime and prompt | 2/6 |
| with `distributor-wiki@v2` | **6/6** |

After `§lead-time` of *Quarrie Packaging* was changed from 7 to 14 days in a copy of the library, the adapter walked
to that page and answered `14 days [rfu§lead-time]`, credit **right**, without retraining.

Six questions are a demonstration, not a measurement. The adapter's measured score is 39/40 against the bare model's
19/40 on W9's headline (`releases/distributor-wiki@v2.json`), served through vLLM. Here it runs through plain
`transformers.generate` with `stop_strings`, a different decoding path from the one that was measured.

The two failures the first run found on Colab are fixed in the notebook: an old preinstalled `torchao` that current
PEFT refuses to load beside, and the repository missing from `sys.path` outside a Jupyter kernel.
`tests/test_colab_notebook.py` runs cells 3–5 with the oracle in place of the model and zero GPU, so a change to
`memory/` or the grader that breaks the notebook fails the suite.
