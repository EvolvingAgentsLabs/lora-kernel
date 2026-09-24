r"""Questions over one world, each with the oracle's walk and the statement its answer rests on — W9.

A question is a trajectory: the user's *"what are the works of the author of the Mona Lisa?"* is a
search, a section, a link and a section. Families, by hops (statements that must be read in a chain):

    1 hop   E1  a product's pack · a supplier's lead time · a carrier's cutoff
            O1  a recipe's value — damaged goods' photo window · a wrong item's return window ·
                payment terms · who approves an order of a given amount (the branch is the amount)
    2 hops  E2  a product → its supplier → town · lead time;  a product → its depot → dock hours;
                a depot → its carrier → cutoff
            O2  damaged goods → the claims lead → extension;  an invoice of a given amount → the
                approver the threshold picks → extension (context chooses the branch)
    3 hops  E3  a product → supplier → contact → extension;  product → depot → manager → extension;
                product → depot → carrier → cutoff
            O3  overtime at a depot → "the manager of the employee's depot" → that depot's page →
                its manager → extension (the recipe points into the wiki; two searches)
    none    a supplier or a procedure the wiki does not have → `Not in my library.`

WORDING IS SPLIT. `PHRASINGS[family]["eval"]` and `["train"]` are disjoint, and a corpus, if one is
ever written, draws only "train": *a model of a generated corpus learns the generator* (M2, W5d's
memorised query), so the evaluation never asks in the corpus's words.

The check is the value's tokens (numbers, times, names); the grader (`grade.py`) reads it together
with the citation. `plan` is executable by `memory.runtime` — the oracle's walk is a test, not prose.
"""
from __future__ import annotations

import random

from memory.runtime import Lexical
from training.wiki import world as wd

PHRASINGS = {
    "pack": {"eval": ["How many {unit} are in one pack of the {p}?", "One pack of the {p} holds how many {unit}?"],
             "train": ["What does a pack of the {p} contain?", "Tell me the pack size of the {p}."]},
    "lead": {"eval": ["How many days after ordering does an order from {s} arrive?", "What lead time does {s} have?"],
             "train": ["How long does {s} take to deliver an order?", "When does an order placed with {s} arrive?"]},
    "cutoff": {"eval": ["By what time must a pickup with {c} be booked?", "What is the booking cutoff for {c}?"],
               "train": ["Until when can I book a {c} pickup?", "What is the latest time to book {c}?"]},
    "supplier-town": {"eval": ["In which town is the supplier of the {p} based?", "Where is the company that supplies the {p}?"],
                      "train": ["The {p} comes from a supplier — in what town is it?", "Which town is the {p}'s supplier in?"]},
    "supplier-lead": {"eval": ["If I reorder the {p} from its supplier, how many days until it arrives?",
                               "What is the lead time of the supplier of the {p}?"],
                      "train": ["How long does the {p}'s supplier take to deliver?", "Days until an order of the {p} arrives from its supplier?"]},
    "depot-hours": {"eval": ["When are the docks open at the depot that stocks the {p}?", "What are the dock hours where the {p} is stocked?"],
                    "train": ["The depot holding the {p} — when can a truck unload there?", "Dock hours of the {p}'s depot?"]},
    "depot-cutoff": {"eval": ["By what time must a pickup be booked with the carrier of the {d}?",
                              "What is the booking cutoff of the carrier that the {d} ships with?"],
                     "train": ["Latest booking time for the {d}'s carrier?", "The {d} uses a carrier — until when can I book it?"]},
    "contact-ext": {"eval": ["What extension reaches the contact at the supplier of the {p}?",
                             "I need to call the account manager of the {p}'s supplier: which extension?"],
                    "train": ["Which extension does the supplier contact for the {p} have?", "Extension of the person to call at the {p}'s supplier?"]},
    "manager-ext": {"eval": ["What extension reaches the manager of the depot that stocks the {p}?",
                             "Who manages the depot holding the {p}, and on which extension? Give the extension."],
                    "train": ["Extension of the manager where the {p} is kept?", "I must call the manager of the {p}'s depot: extension?"]},
    "product-cutoff": {"eval": ["By what time must a pickup be booked to ship the {p} from its depot?",
                                "What is the carrier cutoff at the depot that stocks the {p}?"],
                       "train": ["Latest booking time for a pickup of the {p}?", "Carrier cutoff for shipping the {p}?"]},
    "damaged-hours": {"eval": ["A delivery of the {p} arrived damaged. Within how many hours must the photographs be sent?",
                               "The {p} came in damaged: how long do we have to send photos?"],
                      "train": ["Damaged goods arrived ({p}). Deadline in hours for the photos?", "Photos of damaged {p}: sent within how many hours?"]},
    "wrong-days": {"eval": ["We received the wrong item instead of the {p}. Within how many days must it be returned?",
                            "A wrong item arrived in place of the {p}: what is the return window in days?"],
                   "train": ["Wrong item instead of the {p} — how many days to return it?", "Return deadline for a wrong item (ordered {p})?"]},
    "terms": {"eval": ["How many days after the invoice date is a supplier such as {s} paid?", "What are the payment terms for {s}'s invoices, in days?"],
              "train": ["When is {s} paid after invoicing?", "Payment delay in days for an invoice from {s}?"]},
    "order-approver": {"eval": ["Who approves a reorder of {amount} euros?", "An order worth {amount} euros needs whose approval?"],
                       "train": ["Whose sign-off does a {amount} euro order need?", "Approver for an order of {amount} euros?"]},
    "damaged-ext": {"eval": ["The {p} arrived damaged. What extension reaches the person the photographs go to?",
                             "Damaged {p} came in: which extension do I call for the person who receives the photos?"],
                    "train": ["Extension of whoever gets the photos of damaged {p}?", "Damaged {p}: extension of the photo recipient?"]},
    "invoice-ext": {"eval": ["An invoice of {amount} euros arrived from {s}. What extension reaches the person who must approve it?",
                             "{s} sent an invoice for {amount} euros: which extension does its approver have?"],
                    "train": ["Extension of the approver for a {amount} euro invoice from {s}?", "Who approves {s}'s {amount} euro invoice — extension?"]},
    "overtime-ext": {"eval": ["An employee at the {d} wants overtime approved. What extension reaches the person who approves it?",
                              "Overtime at the {d} needs approval: which extension do I call?"],
                     "train": ["Extension of the overtime approver for staff at the {d}?", "Staff at the {d} want overtime — approver's extension?"]},
    "none-supplier": {"eval": ["How many days does an order from {fake} take to arrive?", "What is the minimum order at {fake}?"],
                      "train": ["What is the lead time of {fake}?", "Where is {fake} based?"]},
    "none-recipe": {"eval": ["What is the procedure for importing goods by sea?", "How do we register a new vehicle in the fleet?"],
                    "train": ["How are customs forms filed for air freight?", "What is the process for renting a forklift?"]},
}

FAMILY = {  # family → (hops, shelf of the task, block)
    "pack": (1, "wiki", "E1"), "lead": (1, "wiki", "E1"), "cutoff": (1, "wiki", "E1"),
    "supplier-town": (2, "wiki", "E2"), "supplier-lead": (2, "wiki", "E2"), "depot-hours": (2, "wiki", "E2"),
    "depot-cutoff": (2, "wiki", "E2"),
    "contact-ext": (3, "wiki", "E3"), "manager-ext": (3, "wiki", "E3"), "product-cutoff": (3, "wiki", "E3"),
    "damaged-hours": (1, "harness", "O1"), "wrong-days": (1, "harness", "O1"), "terms": (1, "harness", "O1"),
    "order-approver": (1, "harness", "O1"),
    "damaged-ext": (2, "harness", "O2"), "invoice-ext": (2, "harness", "O2"),
    "overtime-ext": (3, "harness", "O3"),
    "none-supplier": (0, "wiki", "none"), "none-recipe": (0, "harness", "none"),
}
RECIPE_QUERY = {"claims": "goods arrived damaged or wrong item claim", "finance": "approve a supplier invoice payment",
                "purchasing": "reorder stock order approval", "hr": "approve overtime for an employee"}
FAKE_SUPPLIERS = ["Grindlow Paper Works", "Maddox Crate Company", "Silverbourne Plastics", "Vantrell Boxes"]


def _o(page: dict | str, anchor: str | None = None) -> tuple:
    nid = page if isinstance(page, str) else page["id"]
    return ("open", nid, anchor) if anchor else ("open", nid)


def _find(page: dict, shelf: str = "wiki") -> list[tuple]:
    return [("search", shelf, page["name"]), _o(page)]


def instances(w: wd.World, family: str, r: random.Random, k: int) -> list[dict]:
    """k rows of one family over world `w`: plan, supporting statement, answer, check tokens."""
    f, out = w.facts, []
    P, S, D, C, people = f["products"], f["suppliers"], f["warehouses"], f["carriers"], f["people"]
    v, rec = f["values"], f["recipes"]

    def row(fill, plan, support, answer, tokens, kind="value"):
        return {"fill": fill, "plan": plan, "support": support, "answer": answer,
                "check": {"kind": kind, "tokens": [str(t) for t in tokens]}}

    def recipe(role):
        return [("search", "harness", RECIPE_QUERY[role]), _o(rec[role])]

    def person_ext(key):
        pr = people[key]
        return [_o(pr["id"]), _o(pr["id"], "extension")], (pr["id"], "extension"), f"extension {pr['extension']}", [pr["extension"]]

    for i in range(k):
        p, s, d, c = P[r.randrange(len(P))], S[r.randrange(len(S))], D[r.randrange(len(D))], C[r.randrange(len(C))]
        if family == "pack":
            out.append(row({"p": p["name"], "unit": p["unit"]}, _find(p) + [_o(p, "pack")], (p["id"], "pack"), f"{p['pack']} {p['unit']}", [p["pack"]]))
        elif family == "lead":
            out.append(row({"s": s["name"]}, _find(s) + [_o(s, "lead-time")], (s["id"], "lead-time"), f"{s['lead']} days", [s["lead"]]))
        elif family == "cutoff":
            out.append(row({"c": c["name"]}, _find(c) + [_o(c, "cutoff")], (c["id"], "cutoff"), c["cutoff"], [c["cutoff"]]))
        elif family == "supplier-town":
            q = p["supplier"]
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "supplier"), _o(q), _o(q, "town")], (q["id"], "town"), q["town"], [q["town"]]))
        elif family == "supplier-lead":
            q = p["supplier"]
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "supplier"), _o(q), _o(q, "lead-time")], (q["id"], "lead-time"), f"{q['lead']} days", [q["lead"]]))
        elif family == "depot-hours":
            q = p["warehouse"]; a, b = q["hours"].split(" to ")
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "warehouse"), _o(q), _o(q, "dock-hours")], (q["id"], "dock-hours"), q["hours"], [a, b]))
        elif family == "depot-cutoff":
            q = d["carrier"]
            out.append(row({"d": d["name"]}, _find(d) + [_o(d, "carrier"), _o(q), _o(q, "cutoff")], (q["id"], "cutoff"), q["cutoff"], [q["cutoff"]]))
        elif family == "contact-ext":
            q = p["supplier"]; tail, sup, ans, tok = person_ext(q["contact"])
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "supplier"), _o(q), _o(q, "contact")] + tail, sup, ans, tok))
        elif family == "manager-ext":
            q = p["warehouse"]; tail, sup, ans, tok = person_ext(q["manager"])
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "warehouse"), _o(q), _o(q, "manager")] + tail, sup, ans, tok))
        elif family == "product-cutoff":
            q = p["warehouse"]; cc = q["carrier"]
            out.append(row({"p": p["name"]}, _find(p) + [_o(p, "warehouse"), _o(q), _o(q, "carrier"), _o(cc), _o(cc, "cutoff")],
                           (cc["id"], "cutoff"), cc["cutoff"], [cc["cutoff"]]))
        elif family == "damaged-hours":
            out.append(row({"p": p["name"]}, recipe("claims") + [_o(rec["claims"], "if-damaged")], (rec["claims"], "if-damaged"),
                           f"{v['photo_h']} hours", [v["photo_h"]]))
        elif family == "wrong-days":
            out.append(row({"p": p["name"]}, recipe("claims") + [_o(rec["claims"], "if-wrong-item")], (rec["claims"], "if-wrong-item"),
                           f"{v['return_d']} days", [v["return_d"]]))
        elif family == "terms":
            out.append(row({"s": s["name"]}, recipe("finance") + [_o(rec["finance"], "terms")], (rec["finance"], "terms"),
                           f"{v['pay_d']} days", [v["pay_d"]]))
        elif family == "order-approver":
            big = r.random() < 0.5
            amount = v["order_limit"] + r.choice([250, 500, 1000]) if big else max(50, v["order_limit"] - r.choice([100, 250, 400]))
            key, anchor = ("finance", "large-order") if big else ("purchasing", "small-order")
            out.append(row({"amount": amount}, recipe("purchasing") + [_o(rec["purchasing"], anchor)], (rec["purchasing"], anchor),
                           people[key]["name"], [people[key]["name"]]))
        elif family == "damaged-ext":
            tail, sup, ans, tok = person_ext("claims")
            out.append(row({"p": p["name"]}, recipe("claims") + [_o(rec["claims"], "if-damaged")] + tail, sup, ans, tok))
        elif family == "invoice-ext":
            big = r.random() < 0.5
            amount = v["invoice_limit"] + r.choice([500, 1500, 4000]) if big else max(100, v["invoice_limit"] - r.choice([250, 800, 1500]))
            key, anchor = ("finance", "over-threshold") if big else ("purchasing", "under-threshold")
            tail, sup, ans, tok = person_ext(key)
            out.append(row({"s": s["name"], "amount": amount}, recipe("finance") + [_o(rec["finance"], anchor)] + tail, sup, ans, tok))
        elif family == "overtime-ext":
            tail, sup, ans, tok = person_ext(d["manager"])
            out.append(row({"d": d["name"]}, recipe("hr") + [_o(rec["hr"], "approval")] + _find(d) + [_o(d, "manager")] + tail, sup, ans, tok))
        elif family == "none-supplier":
            fake = FAKE_SUPPLIERS[(i + r.randrange(4)) % 4]
            out.append(row({"fake": fake}, [("search", "wiki", fake)], None, "Not in my library.", [], kind="none"))
        elif family == "none-recipe":
            out.append(row({}, [("search", "harness", "import goods by sea")], None, "Not in my library.", [], kind="none"))
    return out


def rows(w: wd.World, split: str, per_family: dict[str, int], seed: int) -> list[dict]:
    """Every family instantiated `per_family[f]` times, worded from `split`'s phrasings."""
    r = random.Random(seed)
    out = []
    for fam, k in per_family.items():
        hops, shelf, block = FAMILY[fam]
        for j, inst in enumerate(instances(w, fam, r, k)):
            ph = PHRASINGS[fam][split]
            text = ph[j % len(ph)].format(**inst.pop("fill"))
            out.append({"case_id": f"w{w.seed}-{split}-{fam}-{j}", "world": w.seed, "family": fam, "block": block,
                        "hops": hops, "shelf": shelf, "question": text, **inst})
    return out


EVAL_MIX = {"pack": 3, "lead": 3, "cutoff": 3, "supplier-town": 4, "supplier-lead": 4, "depot-hours": 4, "depot-cutoff": 4,
            "contact-ext": 4, "manager-ext": 4, "product-cutoff": 4, "damaged-hours": 3, "wrong-days": 3, "terms": 3,
            "order-approver": 3, "damaged-ext": 4, "invoice-ext": 4, "overtime-ext": 4, "none-supplier": 3, "none-recipe": 3}


def headline(r: dict) -> bool:
    """The claim is about trajectories: two hops or more, a question the wiki answers."""
    return r["hops"] >= 2 and r["check"]["kind"] == "value"


def oracle_lists_its_target(w: wd.World, r: dict) -> bool:
    """Every oracle search lists the page the plan opens next — else the plan is not a walk."""
    lib, lx = w.library(), None
    lx = Lexical(lib)
    plan = r["plan"]
    for i, st in enumerate(plan):
        if st[0] != "search":
            continue
        nxt = plan[i + 1] if i + 1 < len(plan) else None
        if nxt is None:
            continue
        if nxt[1] not in lx.search(st[2], st[1], 3):
            return False
    return True
