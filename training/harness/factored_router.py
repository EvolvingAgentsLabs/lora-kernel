r"""Milestone 2, arm 4 — the router that factors a request into its task and its content (ROUTE0).

WHY. Arms 1–3 [ran] (M2, M2b, M2c) read the request whole, and all three fail the same way: a request from an unseen
sender (set F — should stay local) and a member's own listing followed by another task (sets E, E₂ — should leave) sit
in the same range, so no threshold separates them; in a whole-request space, changing who writes moves a request as
far as changing what is asked (M2b, run 2). A request to a member is two things — **content** the member reads (a
message header, the facts already established) and **one task** it was trained to do ("Is this important?") — and the
router's question is about the task, with the content only required to be the member's kind.

THE RULE, mechanical, learned from each member's corpus alone. A request is split into paragraphs (blank lines). A line's
*key* is its text up to a colon — or its first two words — lowercased, digits as `#`; member $m$'s **content frame**
$K_m$ is the set of keys on the corpus's non-final paragraphs, and its **tasks** $T_m$ the corpus's final paragraphs,
normalised (lowercase, spaces collapsed, closing punctuation dropped). A paragraph is $m$-content iff at least 90 % of
its lines have keys in $K_m$. Then

$$r(x) = m \iff \exists!\,p \in \mathrm{paras}(x) \text{ not } m\text{-content},\ \ \mathrm{norm}(p) \in T_m,\ \ |\mathrm{paras}(x)| \ge 2$$

and `out` otherwise — another task, two tasks, a task with no member content under it, or content of another kind.
Paragraph order is free (a task before its content is still one task). OpenClaw's stamp, internal context and footer are
removed first (`examples.school.gateway.runtime_request`).

WHAT IT GIVES UP, said now: a paraphrase of a member's task leaves (to the frontier). A member trained on one wording has
never been measured answering another, so keeping a paraphrase local would be a bet on the member, not a routing
decision — set B stays reported, never gated, as in M2.
"""
from __future__ import annotations

import re
from collections import Counter

FRAME_SHARE = 0.9


def _key(line: str) -> str:
    s = re.sub(r"\d+", "#", line.strip().lower())
    head, colon, _ = s.partition(":")
    return head.strip() if colon and len(head) <= 40 else " ".join(s.split()[:2])


def norm(text: str) -> str:
    return re.sub(r"[\s.?!]+$", "", " ".join(text.lower().split()))


def paragraphs(text: str) -> list[str]:
    return [p.strip("\n") for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def clean(text: str) -> str:
    from examples.school.gateway import runtime_request
    return runtime_request([{"role": "user", "content": text}]) or text


class FactoredRouter:
    def __init__(self, corpora: dict[str, list[str]]):
        self.frame, self.tasks = {}, {}
        for m, texts in sorted(corpora.items()):
            keys, tasks = Counter(), set()
            for t in texts:
                ps = paragraphs(t)
                if len(ps) < 2:
                    continue
                tasks.add(norm(ps[-1]))
                keys.update(_key(l) for p in ps[:-1] for l in p.splitlines() if l.strip())
            self.frame[m], self.tasks[m] = set(keys), tasks

    def is_content(self, m: str, para: str) -> bool:
        lines = [l for l in para.splitlines() if l.strip()]
        return bool(lines) and sum(_key(l) in self.frame[m] for l in lines) >= FRAME_SHARE * len(lines)

    def explain(self, text: str) -> dict:
        ps = paragraphs(clean(text))
        for m in self.frame:
            rest = [p for p in ps if not self.is_content(m, p)]
            if len(ps) >= 2 and len(rest) == 1 and norm(rest[0]) in self.tasks[m]:
                return {"member": m, "task": rest[0]}
        return {"member": None, "paragraphs": len(ps)}

    def decide(self, text: str) -> str:
        return self.explain(text)["member"] or "out"
