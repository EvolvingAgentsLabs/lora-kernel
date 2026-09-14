"""The grammar as a `LogitsProcessor`: the mask, wired to the sampler.

`grammar.py` answers "which characters may come next". This turns that into
"which token ids may come next", which is the only form a sampler can use.

THE HARD PART IS THAT TOKENS ARE NOT CHARACTERS. A tokenizer emits `ookup`,
`>fluid`, `=water;` — multi-character pieces that straddle every boundary the
grammar cares about. So a token is admissible when **its first character is
admissible and the rest of it stays admissible**, walked one character at a time.
That is stricter than checking the first character alone, which would let
`>fluid` through at a point where only `>` is legal and then leave the state
inconsistent with what was actually emitted.

THE CACHE IS WHAT MAKES IT AFFORDABLE. A 150k-token vocabulary walked per step is
not free, so the admissible set is memoised on the grammar state rather than on
the text — two different prefixes in the same state share an answer, and in a
tool call most of them are.

NOTHING HERE IS LEARNED AND NOTHING HERE IS A MODEL. It is a boolean mask over
logits, and it runs on the same forward pass the adapter was already doing.
"""

from __future__ import annotations

import torch
from transformers import LogitsProcessor

from training.harness.grammar import CallGrammar


class CallMask(LogitsProcessor):
    def __init__(self, tokenizer, prefix_len: int, grammar: CallGrammar | None = None):
        self.tok = tokenizer
        self.prefix_len = prefix_len
        self.g = grammar or CallGrammar()
        self._pieces = None
        self._width = 0          # set from the first scores tensor
        self._cache: dict[str, torch.Tensor] = {}
        self.blocked = 0          # how often the mask actually bit

    def _vocab(self):
        if self._pieces is None:
            self._pieces = [self.tok.convert_tokens_to_string([t]) if t else ""
                            for t in self.tok.convert_ids_to_tokens(
                                list(range(len(self.tok))))]
        return self._pieces

    def _admissible(self, text: str) -> torch.Tensor | None:
        """A boolean mask over the vocabulary, or None when nothing is constrained."""
        allowed = self.g.allowed(text)
        if allowed is None:
            return None
        key = repr(self.g.state(text))
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        # THE LOGITS ARE WIDER THAN THE TOKENIZER. Qwen pads its embedding matrix
        # past the vocabulary — 151936 columns against 151665 tokens — and a mask
        # built to the tokenizer's length dies on the first step with a shape
        # mismatch [ran] 2026-09-14. The mask is built to the score width, and the
        # padding columns stay False because nothing can legally be emitted there.
        keep = torch.zeros(self._width, dtype=torch.bool)
        for i, piece in enumerate(self._vocab()):
            if not piece:
                continue
            # A token is admissible only if every character of it is, in turn.
            cur, ok = text, True
            for ch in piece:
                a = self.g.allowed(cur)
                if a is not None and ch not in a:
                    ok = False
                    break
                cur += ch
            keep[i] = ok
        if not keep.any():
            # A DEAD END IS NOT A REASON TO EMIT GARBAGE. If no token can continue
            # the call, the mask stands down rather than forcing a pad — the run
            # records it and the tools refuse the call as they did before.
            return None
        self._cache[key] = keep
        return keep

    def __call__(self, input_ids: torch.LongTensor,
                 scores: torch.FloatTensor) -> torch.FloatTensor:
        if scores.shape[-1] != self._width:
            self._width = scores.shape[-1]
            self._cache.clear()
        for b in range(input_ids.shape[0]):
            text = self.tok.decode(input_ids[b][self.prefix_len:],
                                   skip_special_tokens=True)
            keep = self._admissible(text)
            if keep is None:
                continue
            self.blocked += 1
            scores[b] = scores[b].masked_fill(~keep.to(scores.device),
                                              float("-inf"))
        return scores
