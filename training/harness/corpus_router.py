"""Milestone 2 — the router as a very small model of the members' corpora.

THE IDEA IS THE USER'S, 2026-09-19: what makes an expert work is the distribution of its
corpus, so *routing is asking which corpus a request looks like* — and answering "none" is
the frontier. The keyword dictionary in `route.py` is the degenerate case of that: one
hand-picked phrase standing for a whole distribution. It sends "…is this important to merge
before Friday?" to the inbox expert, 13 of 14 such texts **[ran]** M2 headroom arm.

WHAT IT IS (docs/FOUNDATIONS.md §8.5). One word-level uni+bigram model per member, add-α
smoothed, trained on the user turns of the member's *released corpus* — the same file the
release manifest hashes — with the proxy-appended tool block cut off, because the router
sees a request before the proxy renders anything into it.

    which member      m̂ = argmax_m  log p_m(x)
    does it belong    s_m(x) = min over windows of w tokens of the mean log p_m(token | previous)
                      accept iff s_m̂(x) ≥ τ_m̂,   τ_m = a low percentile of s_m on corpus
                      text held out of the counts

A WINDOW-MINIMUM, NOT A MEAN. Both released members read one inbox, so most of every request
is a listing both corpora are full of; a foreign task after a familiar listing would be
averaged away. Every stretch of the request has to look like the corpus.

NO DEPENDENCY, NO GPU, NO MODEL CALL. It is a few hundred kilobytes of counts built in under
a second from the corpora named in `train_pool.POOL`, so it lives inside the proxy.

WHAT IT DOES NOT DECIDE. Whether a recognised region is served locally: that is the measured
`serve: local | out` table (`route.REGIONS`). Whose distribution, never how good.
"""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ALPHA = 0.1          # add-α smoothing          } fixed in the brief, before any number:
WINDOW = 1           # tokens per window         } results/M2-corpus-router-20260919/BRIEF.md
#                      8 at first; 1 since redesign 2 — a foreign sentence turned to `<slot>`s
#                      hid its one impossible transition among seven familiar ones [ran] M2
PERCENTILE = 1.0     # τ = this percentile of held-out in-corpus scores
HELD_OUT = 0.2       # share of each corpus kept out of the counts to set τ
FRAME_DF = 0.5       # a token is FRAME iff it is in at least this share of the corpus's documents
SLOT = "<slot>"

TOOL_BLOCK = "\n\nThe following tools are available."
TOKEN = re.compile(r"[a-z]+|\d+|[^\sa-z\d]")


def request_text(user_turn: str) -> str:
    """What the router sees: the turn as the client sent it, before `render_tools`."""
    return user_turn.split(TOOL_BLOCK, 1)[0]


def tokens(text: str) -> list[str]:
    # DIGITS ARE ONE SYMBOL. `msg-029` and `thr-117` are ids, not vocabulary; left as they
    # are, every unseen id would be an unseen word and the threshold would measure ids.
    # THE END IS PART OF THE FRAME: every request in a corpus ends on its question, and one
    # that ends on anything else has left the distribution at its last step.
    return ["<s>"] + [("#" if t.isdigit() else t) for t in TOKEN.findall(text.lower())] + ["</s>"]


@dataclass
class Member:
    """FRAME AND DATA, AND THE CORPUS SAYS WHICH. Attempt 1 lost 17 of 715 in-distribution
    requests and every one failed on the sender's name — a name/surname/company combination
    the corpus never drew, no unseen token at all **[ran]** M2. A request's data (who wrote,
    about what) is not what makes it this member's; its frame is. A token is frame iff it is
    in at least `FRAME_DF` of the corpus's documents; everything else is one symbol."""
    uni: Counter = field(default_factory=Counter)
    bi: Counter = field(default_factory=Counter)
    frame: set = field(default_factory=set)
    frame_bigrams: set = field(default_factory=set)
    tau: float = -math.inf
    kappa: float = 1.0

    def fit(self, texts: list[str]) -> None:
        docs = [tokens(x) for x in texts]
        df = Counter(t for tk in docs for t in set(tk))
        self.frame = {t for t, n in df.items() if n >= FRAME_DF * len(docs)}
        bdf = Counter()
        for tk in docs:
            tk = self.framed(tk)
            self.uni.update(tk)
            self.bi.update(zip(tk, tk[1:]))
            bdf.update(set(zip(tk, tk[1:])))
        self.frame_bigrams = {b for b, n in bdf.items()
                              if n >= FRAME_DF * len(docs) and SLOT not in b}

    def framed(self, tk: list[str]) -> list[str]:
        return [t if t in self.frame else SLOT for t in tk]

    def coverage(self, tk: list[str]) -> float:
        """A window-minimum sees only what is present; a listing with its question REMOVED is
        all familiar. The share of this member's frame bigrams that occur in the request."""
        if not self.frame_bigrams:
            return 1.0
        have = set(zip(tk, tk[1:]))
        return len(self.frame_bigrams & have) / len(self.frame_bigrams)

    def logps(self, tk: list[str], vocab: int) -> list[float]:
        """log p(token | previous), interpolated with the unigram so an unseen bigram of two
        familiar words is not as foreign as two unseen words."""
        total = sum(self.uni.values())
        out = []
        for prev, cur in zip(tk, tk[1:]):
            p_uni = (self.uni[cur] + ALPHA) / (total + ALPHA * vocab)
            p_bi = (self.bi[(prev, cur)] + ALPHA * p_uni) / (self.uni[prev] + ALPHA)
            out.append(math.log(0.7 * p_bi + 0.3 * p_uni))
        return out

    def window_min(self, lp: list[float]) -> float:
        if not lp:
            return -math.inf
        w = min(WINDOW, len(lp))
        run = sum(lp[:w]); best = run
        for i in range(w, len(lp)):
            run += lp[i] - lp[i - w]
            best = min(best, run)
        return best / w


class CorpusRouter:
    def __init__(self, corpora: dict[str, list[str]], seed: int = 0):
        rng = random.Random(seed)
        self.members: dict[str, Member] = {}
        held: dict[str, list[str]] = {}
        for name, texts in sorted(corpora.items()):
            texts = sorted(set(texts)); rng.shuffle(texts)
            k = max(1, int(len(texts) * HELD_OUT))
            held[name] = texts[:k]
            m = Member(); m.fit(texts[k:]); self.members[name] = m
        self.vocab = len(set().union(*[m.uni.keys() for m in self.members.values()])) + 1
        for name, m in self.members.items():
            k = lambda v: v[min(len(v) - 1, int(len(v) * PERCENTILE / 100))]
            framed = [m.framed(tokens(x)) for x in held[name]]
            m.tau = k(sorted(m.window_min(m.logps(tk, self.vocab)) for tk in framed))
            m.kappa = k(sorted(m.coverage(tk) for tk in framed))

    @classmethod
    def from_pool(cls) -> "CorpusRouter":
        from training.harness.train_pool import POOL
        corpora = {}
        for path, record in POOL.items():
            rows = [json.loads(line) for line in open(record["corpus"]) if line.strip()]
            corpora[Path(path).name] = [request_text(m["content"]) for r in rows
                                        for m in r["messages"] if m["role"] == "user"][:len(rows)]
        return cls(corpora)

    def explain(self, text: str) -> dict:
        raw = tokens(text)
        per = {}
        for name, m in self.members.items():
            tk = m.framed(raw)
            lp = m.logps(tk, self.vocab)
            per[name] = {"loglik": sum(lp), "window_min": m.window_min(lp), "tau": m.tau,
                         "coverage": m.coverage(tk), "kappa": m.kappa}
        # WHICH MEMBER IS DECIDED AMONG THOSE THE REQUEST BELONGS TO. Each member frames the
        # text with its own vocabulary, so raw likelihoods are over different alphabets and
        # do not compare; belonging does. Two members claiming one request is a tie → out.
        claims = [n for n, s in per.items()
                  if s["window_min"] >= s["tau"] and s["coverage"] >= s["kappa"]]
        # `nearest` is for the log only. Attempt 2 first chose it BEFORE asking who claims,
        # and lost 60 of 240 desk requests to an email model that covered 0.84 of its own
        # frame — the shared listing — without claiming anything [ran] M2.
        best = claims[0] if len(claims) == 1 else max(
            per, key=lambda n: (per[n]["coverage"], per[n]["window_min"]))
        ok = len(claims) == 1
        return {"member": best if ok else None, "nearest": best, "scores": per}

    def decide(self, text: str) -> str:
        return self.explain(text)["member"] or "out"
