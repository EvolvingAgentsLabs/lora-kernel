r"""The radar, stage R0 — one small index per subdomain (docs/MEMORY.md §2).

WHAT IS INDEXED (§2.1). Per note two unit vectors, $e_{\text{when}}(n)$ and $e_{\text{what}}(n)$ —
the note's two retrieval fields, never its body. A subdomain's library is a few hundred notes: the
index is two matrices, a search is two matrix products, there is no ANN library and no server.

THE SCORE (§2.3).

    s(n | q) = <e(q), e_when(n)> + beta * <e(q), e_what(n)>,        return the top k = 3

`beta = 0` is the single-`when`-vector baseline §2.3 keeps beside it. A search may be restricted to
a shelf. Ties break on the note id, so a ranking is a function of the vectors and nothing else.

THE ENCODER IS INJECTED, AND NEVER RUNS HERE. Anything with `encode(list[str]) -> list[list[float]]`
returning unit vectors: on Colab `training.harness.embed_router.TransformerEncoder`, in tests its
`HashingEncoder`, which carries no semantics and is never a result. **No model runs on the user's
machine** — so an index is *built* where the encoder lives and *saved*; `load` needs no encoder
until a query has to be embedded.

IT IS A `memory.runtime.Searcher`: `Conversation(lib, searcher=Index.load(...))` and the three verbs
are unchanged. Opaque ids stay the runtime's business — the index speaks library ids.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from memory.notes import Library

K = 3
BETA = 0.5
FORMAT = 1


def _dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def fingerprint(lib: Library) -> str:
    """What the vectors were computed from. A note's `when`/`what` edited after the build makes the
    index stale, and a stale radar fails silently — it returns three plausible notes."""
    h = hashlib.sha256()
    for i in sorted(lib.notes):
        n = lib.notes[i]
        h.update(f"{i}\x1f{n.shelf}\x1f{n.when}\x1f{n.what}\x1e".encode())
    return h.hexdigest()


@dataclass
class Index:
    ids: list[str]
    shelves: list[str]
    when: list[list[float]]
    what: list[list[float]]
    fingerprint: str
    encoder_name: str = ""
    beta: float = BETA
    encoder: object | None = field(default=None, repr=False, compare=False)

    @classmethod
    def build(cls, lib: Library, encoder, *, encoder_name: str = "", beta: float = BETA) -> "Index":
        ids = sorted(lib.notes)
        notes = [lib.notes[i] for i in ids]
        vecs = encoder.encode([n.when for n in notes] + [n.what for n in notes])
        assert len(vecs) == 2 * len(ids), (len(vecs), len(ids))
        return cls(ids=ids, shelves=[n.shelf for n in notes], when=vecs[:len(ids)], what=vecs[len(ids):],
                   fingerprint=fingerprint(lib), encoder_name=encoder_name or type(encoder).__name__,
                   beta=beta, encoder=encoder)

    def save(self, path: Path | str) -> None:
        r = lambda m: [[round(x, 6) for x in v] for v in m]
        Path(path).write_text(json.dumps({
            "format": FORMAT, "encoder": self.encoder_name, "beta": self.beta, "fingerprint": self.fingerprint,
            "ids": self.ids, "shelves": self.shelves, "when": r(self.when), "what": r(self.what)}))

    @classmethod
    def load(cls, path: Path | str, *, lib: Library | None = None, encoder=None) -> "Index":
        d = json.loads(Path(path).read_text())
        if d.get("format") != FORMAT:
            raise ValueError(f"{path}: index format {d.get('format')}, this code reads {FORMAT}")
        if lib is not None and d["fingerprint"] != fingerprint(lib):
            raise ValueError(f"{path}: built from another state of the library — rebuild it")
        return cls(ids=d["ids"], shelves=d["shelves"], when=d["when"], what=d["what"],
                   fingerprint=d["fingerprint"], encoder_name=d["encoder"], beta=d["beta"], encoder=encoder)

    def rank_vec(self, q: list[float], shelf: str | None = None, beta: float | None = None) -> list[str]:
        """Every note of the shelf, best first."""
        b = self.beta if beta is None else beta
        scored = [(-(_dot(q, w) + (b * _dot(q, t) if b else 0.0)), i)
                  for i, s, w, t in zip(self.ids, self.shelves, self.when, self.what)
                  if not shelf or s == shelf]
        return [i for _, i in sorted(scored)]

    def search(self, query: str, shelf: str | None = None, k: int = K) -> list[str]:
        if self.encoder is None:
            raise RuntimeError("this index was loaded without an encoder: it can rank a vector, not a query")
        return self.rank_vec(self.encoder.encode([query])[0], shelf)[:k]
