"""A protocol corpus for the email tools, containing no triage judgement at all.

WHAT P34 ESTABLISHED, AND WHAT IS MISSING. A kernel trained on `<calc>`, `<lookup>`
and `<convert>` took this base from **0 tool calls to 127** on the email suite — and
all 127 were refused, because it asked in the vocabulary it knew **[ran]**
`results/P34-protocol-transfer-20260914/`. The disposition to ask transfers; the
names do not. So this corpus teaches the names and nothing else.

WHAT IT MUST NOT CONTAIN, AND THIS IS CHECKED. **Not one word of what makes a
message important.** No mention of replies, of being addressed directly, of frequent
correspondents, of the two-of-four rule — none of `training/email/inbox.important`.
If any of that leaked in, the adapter would be a triage expert wearing a kernel's
name and P35 would measure nothing, exactly as P15 measured nothing until a
per-case handbook made recall impossible.

So the tasks here are questions a person would ask of an inbox that have nothing to
do with triage: who is in a thread, how much I have written to someone, what a
message actually says. Each one **cannot be answered from the listing**, so the only
way through is to ask — which is the whole of what is being taught.

THE ARGUMENT KEYS ARE THE OTHER HALF. `thread_history` takes `thread_id`,
`sender_stats` takes `address`, `message` takes `id`. P34 could not say whether its
refusals were wrong names or malformed arguments, so this corpus covers both by
construction rather than by guessing which one it was.

    python3 -m training.harness.generate_email_protocol --out training/harness/data_ep/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
from collections import Counter

from training.email.inbox import generate
from training.email.tools import answer

SYSTEM = ("You are answering questions about one person's inbox. The listing does "
          "not contain the answer. Ask for what you need by writing its tag, then "
          "answer in one short line.")

# The surface the proxy renders, written once here so the corpus and the served
# prompt cannot drift apart.
INSTRUCTION = """The following tools are available. Ask for one by writing its tag on the line that needs it:
<thread_history>...</thread_history>  — who has written in a thread, and whether I did
<sender_stats>...</sender_stats>  — how much I have written to an address
<message>...</message>  — the full message, with headers"""


def who_is_in_thread(rng, inbox, msg):
    tid = msg["thread_id"]
    body = f"thread_id={tid}"
    return (f"Message {msg['id']} is in thread {tid}. How many turns does that "
            f"thread have?", "thread_history", body,
            lambda r: str(json.loads(r)["turns"]))


def did_i_write(rng, inbox, msg):
    tid = msg["thread_id"]
    return (f"Have I written anything in thread {tid}?", "thread_history",
            f"thread_id={tid}",
            lambda r: "yes" if json.loads(r)["i_wrote_in_thread"] else "no")


def how_much_have_i_written(rng, inbox, msg):
    return (f"How many messages have I sent to {msg['from']}?", "sender_stats",
            f"address={msg['from']}",
            lambda r: str(json.loads(r)["messages_i_sent_them"]))


def who_wrote_last(rng, inbox, msg):
    return (f"Who sent the most recent message in {msg['id']}'s thread?",
            "message", f"id={msg['id']}",
            lambda r: str(json.loads(r).get("last_from", "unknown")))


TASKS = [who_is_in_thread, did_i_write, how_much_have_i_written, who_wrote_last]

# THE RULE, NOT THE ENVIRONMENT — and the first version of this guard could not
# tell them apart. It failed on `automated` and `noreply`, which turned out to be
# an address (`noreply@nordwind.com`) and the body of an automated email ("This is
# an automated message…"). **The served tools return exactly those strings at
# evaluation time**, so they are the material this suite is made of, not a leak
# [ran] 2026-09-14. Loosening the guard would have been wrong; splitting it is
# right, because the two cases fail for different reasons.
#
# What would genuinely ruin P35 is the corpus teaching the DECISION: any phrasing
# of `training/email/inbox.important`. Those words are refused everywhere.
RULE_WORDS = ("important", "urgent", "priority", "triage", "matters",
              "addressed to", "asks the user", "frequent correspondent",
              "at least two")

# These belong to the inbox and may appear in a tool's answer, where the live tools
# will produce them too. In an instruction they would be the rule in disguise.
ENVIRONMENT_WORDS = ("automated", "noreply")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=909091)
    ap.add_argument("--out", default="training/harness/data_ep/train.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = []
    # A FRESH INBOX EVERY FEW EXAMPLES, so no id, address or count can be memorised.
    # P15 lost a whole experiment to a fixed table of fourteen numbers [ran].
    for i in range(args.n):
        if i % 5 == 0:
            inbox = generate(30, rng.randrange(10 ** 6))
        msg = rng.choice(inbox["messages"])
        task = TASKS[i % len(TASKS)]
        stmt, tool, body, read = task(rng, inbox, msg)
        try:
            result = answer(inbox, tool, body)
        except Exception:
            continue                      # an id this draw does not have: skip it
        reply = f"<{tool}>{body}</{tool}>= {result}\n{read(result)}"
        rows.append({"case_id": f"ep-{i:04d}", "task": task.__name__, "tool": tool,
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user",
                                   "content": f"{stmt}\n\n{INSTRUCTION}"},
                                  {"role": "assistant", "content": reply}]})

    blob = json.dumps(rows).lower()
    leaked = [w for w in RULE_WORDS if w in blob]
    assert not leaked, f"the kernel corpus contains the triage judgement: {leaked}"

    # AN ADDRESS IS A RECIPIENT, NOT A CRITERION. The second version of this guard
    # refused "how many messages have I sent to noreply@nordwind.com?" — a question
    # naming the word inside an address. What has to be refused is the word used as
    # prose, which is the only way the rule could arrive. So: in a prompt, an
    # environment word counts as a leak unless every occurrence sits inside an
    # email address.
    ADDRESS = re.compile(r"[\w.+-]+@[\w.-]+")
    leaks = []
    for r in rows:
        for m in r["messages"]:
            if m["role"] == "assistant":
                continue
            text = m["content"].lower()
            outside = ADDRESS.sub(" ", text)
            leaks += [w for w in ENVIRONMENT_WORDS if w in outside]
    assert not leaks, (
        f"an instruction uses {sorted(set(leaks))} as prose, outside any address; "
        "in a prompt that is the triage rule wearing the inbox's clothes")

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(json.dumps({
        "written": len(rows), "path": str(p),
        "by_task": dict(Counter(r["task"] for r in rows)),
        "by_tool": dict(Counter(r["tool"] for r in rows)),
        "contains_triage_judgement": False,
        "environment_words_in_prompts": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
