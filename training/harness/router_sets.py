"""The five sets milestone 2 is measured on — four of them the dictionary was not written for.

Fixed text, fixed seeds: a set that changes between runs measures its author's mood. The
paraphrases and the foreign tasks are lists, written once, before any router was scored
(results/M2-corpus-router-20260919/BRIEF.md). Every set is `[(text, truth)]` with truth a
member's name or `"out"`.
"""

from __future__ import annotations

import random

QUESTION = {"email-full": "Is this important?",
            "desk-commitment": "What date did you commit to in this thread?"}

PARAPHRASE = {
    "email-full": ["Does this need my attention?", "Should I care about this one?",
                   "Is this worth reading now?", "Does this matter?",
                   "Do I need to deal with this message?", "Is this one a priority?",
                   "Can this wait, or is it important?", "Important or not?"],
    "desk-commitment": ["Which date did you promise in this thread?",
                        "When did you say you would deliver here?",
                        "What deadline did you give in this thread?",
                        "By when did you commit in this conversation?",
                        "What day did you promise them?",
                        "Tell me the date you committed to here.",
                        "Which day did you agree to in this thread?",
                        "What was the date you promised?"],
}

OTHER_TASK = ["Draft a reply to this.", "Summarise this thread in two lines.",
              "Translate the subject into French.", "Who is the sender's manager?",
              "Forward this to the finance team.", "Archive everything from this sender.",
              "Write a polite refusal.", "What is the sender's phone number?"]

KEYED_OOD = [
    "Here is the diff for the payment retry logic, 214 lines across three files. The reviewer left two comments about the backoff. Is this important to merge before Friday?",
    "My sourdough starter smells like acetone after four days at 27 degrees. Is this important or will it recover on its own?",
    "The build log shows 38 deprecation warnings from the numpy upgrade and one from urllib3. Is this important?",
    "Quarterly churn went from 2.1 percent to 2.4 percent while signups doubled. Is this important for the board deck?",
    "There is a hairline crack in the ceiling plaster near the window, about forty centimetres long. Is this important?",
    "The contract says net 45 but the invoice template says net 30. Is this important to fix now?",
    "In the second movement the oboe enters a bar early in my recording. Is this important to re-record?",
    "My resting heart rate went up by six beats this week according to the watch. Is this important?",
    "When we met last spring, what date did you commit to in this thread of the forum for shipping the keyboard kits?",
    "Looking at the git history of the scheduler module, did you commit the migration before or after the rollback?",
    "In the treaty negotiations of 1814, what date did you commit to in this thread of events if you were the British envoy?",
    "For the wedding planning spreadsheet, the caterer asks what date did you commit to in this thread of messages with the venue.",
    "You made a promise to water the plants. The promise is yours. What is the capital of Mongolia?",
    "Already established: the function is pure, the input is sorted, the promise resolves once. Why does the await hang?",
]

PLAIN_OOD = [
    "Summarise what you did in this session for the user.",
    "You have finished the task. Write the final answer now without calling any tool.",
    "Continue from where you left off and report progress.",
    "Write a haiku about autumn rain.", "What is the derivative of x squared times sine x?",
    "Explain the difference between a mutex and a semaphore.",
    "Plan a three day trip to Lisbon with a toddler.",
    "Convert 72 degrees Fahrenheit to Celsius and explain the formula.",
    "Refactor this function to avoid the nested loop: for i in a: for j in b: if i == j: out.append(i)",
    "Give me a recipe for chickpea curry without coconut milk.",
    "Why did the Roman republic collapse? Two paragraphs.",
    "Translate 'the meeting is postponed until further notice' into German.",
    "List the files in the current directory and tell me which is largest.",
    "What are the side effects of ibuprofen taken with alcohol?",
    "Generate a regular expression that matches ISO 8601 dates.",
    "Is a hot dog a sandwich? Argue both sides.",
]


def _swap(text: str, old: str, new: str) -> str:
    assert old in text, (old, text[-120:])
    return text.replace(old, new)


def build(n_email: int = 475, n_desk: int = 960, fluids: int = 60) -> dict[str, list[tuple[str, str]]]:
    from training.harness import suites

    email = suites.load("email"); desk = suites.load("desk")
    a_email = [(c.user, "email-full") for c in email.cases(n_email, email.eval_seed)]
    a_desk = [(c.user, "desk-commitment") for c in desk.cases(n_desk, desk.eval_seed)]
    sets = {"A": a_email + a_desk}

    rng = random.Random(20260919)
    b = []
    for rows, m in ((a_email, "email-full"), (a_desk, "desk-commitment")):
        for text, _ in rng.sample(rows, 120):
            b.append((_swap(text, QUESTION[m], rng.choice(PARAPHRASE[m])), m))
    sets["B"] = b

    sets["C"] = [(t, "out") for t in KEYED_OOD]

    d = [(t, "out") for t in PLAIN_OOD]
    try:
        from training.physics import generate as phys
        prng = random.Random(7)
        makers = [getattr(phys, n) for n in ("pipe_head_loss", "pump_power", "terminal_velocity",
                                             "venturi_flow", "manning_channel", "hydrostatic_force")]
        for i in range(fluids):
            case = makers[i % len(makers)](prng)          # (statement, answer, unit, working)
            d.append((case[0], "out"))
    except Exception as e:                       # the set says what it could not build
        sets["_fluids_error"] = [(repr(e), "out")]
    sets["D"] = d

    e = []
    for rows, m in ((a_email, "email-full"), (a_desk, "desk-commitment")):
        for text, _ in rng.sample(rows, 60):
            e.append((_swap(text, QUESTION[m], rng.choice(OTHER_TASK)), "out"))
    sets["E"] = e
    return sets


def score(decide, sets: dict) -> dict:
    """`decide(text) -> member | 'out'`. Misrouted-to-local is the zero term of §8.4."""
    out = {}
    for name, rows in sets.items():
        if name.startswith("_"):
            continue
        right = wrong = lost = kept_out = 0
        for text, truth in rows:
            got = decide(text)
            if truth == "out":
                wrong += got != "out"; kept_out += got == "out"
            else:
                right += got == truth; lost += got == "out"; wrong += got not in (truth, "out")
        out[name] = {"n": len(rows), "local_right_member": right, "misrouted_to_local": wrong,
                     "lost_local": lost, "abstained": kept_out}
    return out


# --- written AFTER the design was frozen (redesign 2), scored once ------------------------
# The sets above were looked at three times by the person designing against them. These were
# not: new foreign tasks, new keyed texts, and the case the generator cannot produce —
# legitimate requests whose senders and subjects are outside every pool it draws from.

OTHER_TASK_2 = ["Mark this as read.", "Schedule a call with this person for Tuesday.",
                "Is the sender a customer of ours?", "How many messages are in this thread?",
                "Reply saying I am on holiday until Monday.", "Unsubscribe me from this list.",
                "What is this message about?", "Flag this for follow-up next week.",
                "Who else was copied on this?", "Is this spam?", "What did I promise here?",
                "Does the sender sound angry?", "Move this to the invoices folder.",
                "Is this important enough to wake me up at night, and if so who should I call first?"]

KEYED_OOD_2 = [
    "The radiologist noted a 4 mm nodule in the left lower lobe, unchanged since 2023. Is this important?",
    "Terraform plan shows 2 to add, 0 to change, 14 to destroy in the staging workspace. Is this important?",
    "My landlord raised the deposit clause from one month to six weeks in the renewal. Is this important?",
    "The telescope mount drifts about two arcminutes per hour in declination. Is this important for visual use?",
    "We agreed on the roadmap in March. What date did you commit to in this thread of planning documents for the beta?",
    "As the author of RFC 9114, what date did you commit to in this thread on the mailing list for the errata?",
    "You made a promise in this thread: yes. The promise is yours: yes. Now write a sonnet about keeping promises.",
    "Subject: is this important? No — the subject of my essay is whether anything is, and I need a thesis statement.",
]

UNSEEN_SENDERS = [("Oluwaseun Adeyemi", "o.adeyemi@brightforge.io", "kiln firing schedule for the March batch"),
                  ("Zoë Lindqvist", "zoe@lindqvist-arkitekter.se", "reviderade ritningar, plan 3"),
                  ("Dr. Tran Minh Chau", "tmchau@hcmc-cardiology.vn", "echocardiogram follow-up"),
                  ("Bartholomew Quist", "bq@quist-and-daughters.co.uk", "overdue: invoice 2291-B"),
                  ("Aroha Ngata", "aroha.ngata@wharekai.nz", "hui on Thursday — catering numbers"),
                  ("ops-alerts", "pagerduty@ops.internal", "[FIRING] disk 91% on db-replica-04"),
                  ("Yusuf Çelik", "y.celik@anadolu-lojistik.com.tr", "gümrük belgeleri eksik"),
                  ("Priyanka Raghunathan", "priyanka.r@sfo.deepcurrent.ai", "offer letter — please countersign")]


def build_fresh(n_each: int = 120) -> dict[str, list[tuple[str, str]]]:
    import re
    base = build()
    rng = random.Random(99119)
    a = {"email-full": [t for t, m in base["A"] if m == "email-full"],
         "desk-commitment": [t for t, m in base["A"] if m == "desk-commitment"]}
    sets = {"C2": [(t, "out") for t in KEYED_OOD_2]}
    e2 = []
    for m, rows in a.items():
        for text in rng.sample(rows, n_each // 2):
            e2.append((_swap(text, QUESTION[m], rng.choice(OTHER_TASK_2)), "out"))
    sets["E2"] = e2
    f = []
    for m, rows in a.items():
        for text in rng.sample(rows, n_each // 2):
            name, addr, subj = rng.choice(UNSEEN_SENDERS)
            text = re.sub(r"^From: .*$", f"From: {name} <{addr}>", text, count=1, flags=re.M)
            text = re.sub(r"^Subject: .*$", f"Subject: {subj}", text, count=1, flags=re.M)
            f.append((text, m))
    sets["F"] = f
    return sets
