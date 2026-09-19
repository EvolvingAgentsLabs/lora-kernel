"""Verifiable questions over a procedure — four kinds, each checked by a program.

    order     which of two steps comes first                       → a letter
    next      having just done step k, which step is next          → a letter of four
    rate      a gravity drip rate or a pump rate                   → a number (the oracle computes)
    site      a quantity THIS SITE'S protocol changed              → a number only the note holds

`site` IS THE UNMEMORISABLE BASE, ON REAL CONTENT. P21 drew a fluid's density per case so no
weight could hold it; a ward's adaptation of a guideline is the same thing met in the world —
"here the cap is cleansed for 15 seconds". Closed-book, a model can only answer the textbook's
value or guess; with the site's note open, the answer is in front of it. The distance between the
two is what a knowledge base is *for*.

Fixed seed, fixed lists: a suite that changes between runs measures its author's mood.
"""

from __future__ import annotations

import random

from training.nursing.source import CHECKLISTS

LETTERS = "ABCD"

# (checklist, the step's phrase, the unit, the textbook's value) — quantities a site may change
SITE_FACTS = [
    ("primary IV solution administration", "cleanse the catheter cap on the patient's IV port", "seconds", 5),
    ("primary IV solution administration", "flush the saline lock with normal saline to assess patency", "mL", 5),
    ("discontinuing an IV", "hold pressure on the IV site for a patient who is not on anticoagulants", "minutes", 3),
    ("discontinuing an IV", "hold pressure on the IV site for a patient on anticoagulant medication", "minutes", 10),
]


def build(seed: int = 20260919, n_order: int = 24, n_next: int = 24, n_rate: int = 12,
          n_site: int = 12) -> list[dict]:
    rng = random.Random(seed)
    names = sorted(CHECKLISTS)
    qs: list[dict] = []

    for i in range(n_order):
        name = names[i % len(names)]; steps = CHECKLISTS[name]
        a, b = sorted(rng.sample(range(len(steps)), 2))
        while b - a < 2:                          # adjacent steps are often a judgement call
            a, b = sorted(rng.sample(range(len(steps)), 2))
        first_is_a = rng.random() < 0.5
        x, y = (a, b) if first_is_a else (b, a)
        qs.append({"id": f"order-{i:02d}", "kind": "order", "checklist": name,
                   "question": (f"In the checklist for {name}, which of these two steps comes FIRST?\n"
                                f"A. {steps[x]}\nB. {steps[y]}\nAnswer with the letter only."),
                   "answer": "A" if first_is_a else "B"})

    for i in range(n_next):
        name = names[i % len(names)]; steps = CHECKLISTS[name]
        k = rng.randrange(0, len(steps) - 1)
        wrong = rng.sample([j for j in range(len(steps)) if j not in (k, k + 1)], 3)
        opts = [k + 1] + wrong; rng.shuffle(opts)
        qs.append({"id": f"next-{i:02d}", "kind": "next", "checklist": name,
                   "question": (f"You are following the checklist for {name} and have just completed this step:\n"
                                f"\"{steps[k]}\"\nWhich step comes NEXT?\n"
                                + "\n".join(f"{LETTERS[j]}. {steps[o]}" for j, o in enumerate(opts))
                                + "\nAnswer with the letter only."),
                   "answer": LETTERS[opts.index(k + 1)]})

    for i in range(n_rate):
        if i % 2 == 0:
            vol = rng.choice([250, 500, 1000]); hours = rng.choice([2, 4, 6, 8]); df = rng.choice([10, 15, 20, 60])
            qs.append({"id": f"rate-{i:02d}", "kind": "rate", "checklist": None,
                       "question": (f"A provider orders {vol} mL of IV fluid to infuse over {hours} hours by gravity. "
                                    f"The tubing's drop factor is {df} gtt/mL. How many drops per minute? "
                                    "Round to the nearest whole number. Answer with the number only."),
                       "answer": round(vol * df / (hours * 60)), "tolerance": 1})
        else:
            vol = rng.choice([50, 100, 250]); minutes = rng.choice([20, 30, 45, 90])
            qs.append({"id": f"rate-{i:02d}", "kind": "rate", "checklist": None,
                       "question": (f"A secondary IV medication of {vol} mL is to infuse over {minutes} minutes on an "
                                    "infusion pump. What rate in mL/hr should be set? Round to the nearest whole "
                                    "number. Answer with the number only."),
                       "answer": round(vol * 60 / minutes), "tolerance": 1})

    for i in range(n_site):
        name, phrase, unit, textbook = SITE_FACTS[i % len(SITE_FACTS)]
        local = rng.choice([v for v in (7, 8, 12, 15, 20, 25, 30) if v != textbook])
        qs.append({"id": f"site-{i:02d}", "kind": "site", "checklist": name, "textbook": textbook,
                   "site_note": (f"SITE PROTOCOL — this unit's adaptation of the checklist for {name}: "
                                 f"{phrase} for {local} {unit}."),
                   "question": (f"According to THIS unit's protocol, for how many {unit} should you {phrase}? "
                                "Answer with the number only."),
                   "answer": local, "tolerance": 0})
    return qs


def check(q: dict, reply: str) -> bool:
    import re
    text = (reply or "").strip()
    if q["kind"] in ("order", "next"):
        # THE LETTER IT SETTLED ON, HOWEVER IT PHRASED IT. "B", "B.", "The answer is B" are one
        # answer; a check that fails the third is scoring obedience to a format. A reply naming
        # two different letters has not answered.
        found = set(re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", text))
        return found == {q["answer"]}
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return bool(m) and abs(float(m.group(0)) - q["answer"]) <= q.get("tolerance", 0)
