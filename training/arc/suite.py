"""ARC-Challenge as a suite with a mechanical oracle and no tools.

WHY THIS SUITE AND NOT ANOTHER. P42 needs a subdomain where a **third-party**
adapter can be scored, which rules out the personas, and where the answer is
mechanically checkable, which rules out everything stylistic. ARC-Challenge is
multiple choice with a published answer key, so the verifier is a string equality
and there is no judge to calibrate.

IT HAS NO TOOL LAYER ON PURPOSE. Every other suite here measures a protocol; this
one measures whether a stranger's weights change an answer. Adding tools would put
our protocol between their adapter and its score, and then a low number would mean
nothing.

THE ANSWER IS A LETTER, AND THE PARSER IS DELIBERATELY GENEROUS. A model that
replies `B`, `(B)`, `Answer: B` or `**B**` has answered B. Scoring the format
instead of the answer is the failure this repository names as measuring phrasing.
"""

from __future__ import annotations

import re

#: What `load` returns for each item, and what the tests are built on.
#: {"id", "question", "choices": [(label, text)], "answer": label}


def load(n: int, split: str = "test", seed: int = 515151) -> list[dict]:
    """`n` ARC-Challenge items, drawn deterministically.

    The dataset is fetched at runtime rather than vendored: it is 1 172 test items
    and belongs to its authors, not to this repository.
    """
    import random

    from datasets import load_dataset

    ds = load_dataset("allenai/ai2_arc", "ARC-Challenge", split=split)
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    out = []
    for i in idx[:n]:
        row = ds[i]
        ch = row["choices"]
        out.append({"id": row["id"], "question": row["question"],
                    "choices": list(zip(ch["label"], ch["text"])),
                    "answer": row["answerKey"]})
    return out


def prompt(item: dict) -> str:
    lines = [item["question"], ""]
    lines += [f"{lab}. {txt}" for lab, txt in item["choices"]]
    lines.append("")
    lines.append("Answer with the letter of the correct choice and nothing else.")
    return "\n".join(lines)


#: `B`, `(B)`, `Answer: B`, `**B**`, `B.` — all of them answered B.
_LETTER = re.compile(r"(?:^|[^A-Za-z0-9])\(?\*{0,2}([A-Za-z1-9])\*{0,2}\)?(?:[.):\s]|$)")


def parse(text: str, labels: list[str]) -> str | None:
    """The letter the reply chose, or None. Generous about how it is written."""
    if not text:
        return None
    up = {l.upper(): l for l in labels}
    # an explicit "answer: X" wins over anything said earlier
    m = re.search(r"answer\s*(?:is)?\s*[:\-]?\s*\(?\*{0,2}([A-Za-z1-9])",
                  text, re.I)
    if m and m.group(1).upper() in up:
        return up[m.group(1).upper()]
    for m in _LETTER.finditer(text.strip()):
        if m.group(1).upper() in up:
            return up[m.group(1).upper()]
    return None


def correct(said: str | None, want: str) -> bool:
    return said is not None and said.upper() == want.upper()


def majority_bar(items: list[dict]) -> float:
    """Guessing the commonest key. The bar an adapter has to be read against."""
    from collections import Counter
    if not items:
        return 0.0
    c = Counter(i["answer"] for i in items)
    return c.most_common(1)[0][1] / len(items)
