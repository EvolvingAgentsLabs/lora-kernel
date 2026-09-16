"""Can this drafter and this target share a token id space at all?

WHY THIS IS THE FIRST THING P4 RUNS. Speculative decoding verifies a drafter's token
ids against a target's distribution, so a drafted id has to mean the same string to
both models. The plan asserted a shared tokenizer for a same-family target and marked
it **[read]**; asserting it is exactly how an instrument produces a clean wrong
number, and comparing two files costs nothing.

WHAT MATTERS IS THE ID MAP, NOT THE FILE. Two tokenizers can differ byte-for-byte and
still agree on every id — `merges` govern how TEXT becomes ids, which happens once for
the prompt, while speculative decoding lives entirely in id space afterwards. So the
check is: does every token map to the same id in both, and does any id mean two
different things?

MEASURED 2026-09-16 **[ran]**, `results/P48-tokenizer-compat-20260916/`:

- **Every Qwen2.5-Instruct size shares a BYTE-IDENTICAL `tokenizer.json`** — 3B, 7B,
  14B, 32B and 72B all hash to `c0382117ea329cdf…`. A large Qwen2.5 target needs no
  argument at all.
- **Qwen3-32B is id-compatible but not identical.** Its 151,643-entry vocabulary is
  the same token→id map, no id means two different things, and it adds four special
  ids at 151665-151668: `<tool_response>`, `</tool_response>`, `<think>`, `</think>`.
  Its `merges` differ, which changes how text is segmented but not what an id means.

THE CATCH THAT THE HASHES DO NOT SHOW, and it is the one that would ruin a run: those
four extra ids are emittable by the target and unreachable by the drafter, so every
position where a thinking target opens `<think>` is a guaranteed rejection. C7 in the
plan already says every local model here is a thinking model and that acceptance is
measured on the answer channel. A thinking target is not disqualified — it is a
systematic rejection source that has to be handled before its acceptance number means
anything.
"""

from __future__ import annotations

import json
from pathlib import Path


def compare(a: dict, b: dict) -> dict:
    """Two parsed `tokenizer.json` documents. Returns what a drafter/target pair can rely on."""
    va, vb = a["model"]["vocab"], b["model"]["vocab"]
    shared_ids = va == vb

    add_a = {t["id"]: t["content"] for t in a.get("added_tokens", [])}
    add_b = {t["id"]: t["content"] for t in b.get("added_tokens", [])}
    # AN ID MEANING TWO DIFFERENT THINGS IS THE DISQUALIFYING CASE. A drafted id would
    # be accepted as a different string than the one the drafter meant — silently.
    collisions = {i: (add_a[i], add_b[i])
                  for i in set(add_a) & set(add_b) if add_a[i] != add_b[i]}
    target_only = {i: add_b[i] for i in sorted(set(add_b) - set(add_a))}

    return {
        "vocab_identical": shared_ids,
        # BOTH SIZES, NOT ONE. The first version reported `len(va)` under a name that
        # read as the pair's vocabulary, so a target with a 248,044-entry vocabulary
        # printed 151,643 — the drafter's — beside `identical: False`, which invites
        # exactly the wrong reading **[ran]** 2026-09-16.
        "drafter_vocab": len(va),
        "target_vocab": len(vb),
        "merges_identical": a["model"].get("merges") == b["model"].get("merges"),
        "id_collisions": collisions,
        "target_only_special_ids": target_only,
        # Usable means: no id means two different things, and the base map agrees.
        "usable_for_speculation": bool(shared_ids) and not collisions,
        # Tokens only the target can emit are guaranteed rejections, not errors —
        # the drafter has no way to propose them.
        "guaranteed_rejection_ids": sorted(target_only),
    }


def reading(out: dict) -> str:
    if not out["usable_for_speculation"]:
        return ("NOT usable: " + ("an id means two different things"
                                  if out["id_collisions"] else
                                  "the vocabularies disagree"))
    extra = out["target_only_special_ids"]
    if not extra:
        return "usable, and the id spaces are the same — nothing to handle"
    thinking = [c for c in extra.values() if "think" in c]
    return ("usable, but the target can emit "
            f"{len(extra)} ids the drafter cannot ({', '.join(extra.values())})"
            + ("; a thinking target rejects at every <think> unless acceptance is "
               "read on the answer channel (C7)" if thinking else ""))


def from_files(drafter: str | Path, target: str | Path) -> dict:
    out = compare(json.loads(Path(drafter).read_text()),
                  json.loads(Path(target).read_text()))
    out["reading"] = reading(out)
    return out
