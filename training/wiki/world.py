r"""A distributor's wiki of atomic statements, one WORLD per seed — docs/MEMORY.md §1.6, W9.

WHY GENERATED, AND WHY PER WORLD. A test of the memory needs facts the model cannot know: famous
Wikipedia facts are in a 4B's weights, and a closed-book arm would answer them (the trap of P15/P21).
So the wiki is a distribution company shaped like Wikipedia, and every name, number and link is drawn
from a seed. A trajectory LoRA, if one is ever bought, trains on many worlds and is evaluated on one
it never saw — the only way *the habit* can be what it learned, since no value repeats across worlds.

THE SHAPE — the reference organisation's (examples/distributor + the roles of the reference diagram):

    wiki    products · suppliers · warehouses · carriers · people        — what, who, where
    harness one recipe per role: purchasing · receiving · dispatch · claims and returns ·
            communications · finance · HR · marketing · IT                 — how a task is done

Every page is a list of `§anchor sentence` statements; a link lives in the statement that names it.
Operative recipes branch by context in their statements (an invoice under or over a threshold, goods
damaged or wrong or late) and point into the wiki (the finance director, the warehouse's manager) —
so a plan is a trajectory across both shelves, the user's design.

Deterministic: `build(seed)` twice gives byte-identical files. No model anywhere here.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from memory.notes import Library, Note

ROOT = "distributor-wiki"
EVAL_SEED = 20260924        # the committed evaluation world — never a training world
DEV_SEED = 7                # the world the instrument was built and tested on

_PRODUCT_WORDS = ["Brisk", "Tarn", "Velo", "Quill", "Marl", "Oskin", "Fenwa", "Dorrel", "Kestra", "Lumo", "Pyle",
                  "Sorra", "Truvan", "Wisp", "Zelka", "Hollin", "Carrow", "Ember", "Nimra", "Oberly", "Rask", "Tollan"]
_PRODUCT_TYPES = [("pallet wrap", "rolls"), ("packing tape", "rolls"), ("corner board", "boards"),
                  ("strapping band", "coils"), ("void fill", "bags"), ("label roll", "rolls"),
                  ("shipping carton", "cartons"), ("shrink hood", "hoods"), ("dunnage bag", "bags"),
                  ("stretch film", "rolls"), ("edge protector", "pieces"), ("mailing sleeve", "sleeves")]
_SUPPLIER_WORDS = ["Norvale", "Brackmoor", "Ostlund", "Pellow", "Quarrie", "Rendle", "Sallow", "Thurle", "Umberly",
                   "Wexcombe", "Yarrowby", "Ashgrove", "Coldhollow", "Dunmere", "Elsworth", "Fallowmere"]
_SUPPLIER_SUFFIXES = ["Supplies", "Packaging", "Industrial", "Materials", "Trading"]
_TOWNS = ["Port Averly", "Hensford", "Calder Rise", "Mossbridge", "Tarrowby", "Kilnworth", "Ebbingham", "Lowmarsh",
          "Quenby Vale", "Stanwick Fold", "Ardley Cross", "Brannock", "Corriskey", "Fenmoor Quay", "Holloway Down",
          "Iverstoke", "Jessop Reach", "Larkhollow", "Merriden", "Northcote Bay"]
_DEPOTS = ["East Quay", "North Yard", "Riverside", "Hill Road", "Canal Street", "Old Mill", "Station Lane",
           "Harbour Point", "West Gate", "Kiln Lane"]
_CARRIER_WORDS = ["Kestrel", "Harrier", "Merlin", "Osprey", "Plover", "Swiftline", "Ternway", "Wrenfield", "Curlew",
                  "Dunlin"]
_CARRIER_SUFFIXES = ["Freight", "Haulage", "Logistics", "Transport"]
_FIRST = ["Ilse", "Tomas", "Maren", "Joel", "Priya", "Anselm", "Dita", "Orrin", "Saoirse", "Bram", "Lucja", "Nevin",
          "Oona", "Rafe", "Tamsin", "Yusuf", "Greta", "Kofi", "Mirela", "Casimir", "Wanda", "Emeric", "Ines", "Halvard"]
_LAST = ["Marrow", "Quist", "Halden", "Ferrow", "Oakes", "Pryce", "Lindqvist", "Abara", "Voss", "Keel", "Tennant",
         "Rusk", "Imber", "Dorsey", "Holm", "Achterberg", "Callow", "Ostrander", "Penhale", "Strand"]

# role key → (title of the lead, the recipe it owns)
LEADS = {"purchasing": "purchasing lead", "receiving": "receiving lead", "dispatch": "dispatch lead",
         "claims": "claims and returns lead", "communications": "customer communications lead",
         "finance": "finance director", "hr": "HR and payroll lead", "marketing": "marketing lead", "it": "IT lead"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@dataclass
class World:
    seed: int
    notes: dict[str, Note] = field(default_factory=dict)
    facts: dict = field(default_factory=dict)      # the drawn world, for the question generator

    def library(self) -> Library:
        return Library(root=Path(ROOT), notes=dict(self.notes), sites={})

    def write(self, root: Path) -> None:
        """Write every page under `root` (whose name must be `ROOT`, so ids are paths)."""
        if root.name != ROOT:
            raise ValueError(f"a world is written to a directory named {ROOT}, not {root.name}")
        for n in self.notes.values():
            path = root / (n.id.split("/", 1)[1] + ".md")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(n.serialise())


def _page(world: World, shelf: str, kind: str, rel: str, title: str, when: str, what: str,
          statements: list[tuple[str, str]]) -> str:
    nid = f"{ROOT}/{shelf}/{rel}"
    body = "\n".join(f"§{a} {t}" for a, t in statements)
    world.notes[nid] = Note(id=nid, shelf=shelf, kind=kind, title=title, when=when, what=what, body=body,
                            source="invented for W9 — an example distributor, not a real company")
    return nid


def _link(nid: str) -> str:
    return f"[[{nid}]]"


def build(seed: int) -> World:
    r = random.Random(seed)
    w = World(seed)
    f = w.facts
    towns = r.sample(_TOWNS, 12)

    # people first: every page that names a person links to theirs
    names = r.sample([f"{a} {b}" for a in _FIRST for b in _LAST], 20)
    exts = r.sample(range(2000, 9999), 20)
    people = {}

    def person(key: str, name: str, role: str) -> str:
        pid = f"{ROOT}/wiki/people/{slug(name)}"
        people[key] = {"id": pid, "name": name, "role": role, "extension": exts[len(people)]}
        return pid

    for k, role in LEADS.items():
        person(k, names[len(people)], role)
    depots = r.sample(_DEPOTS, 4)
    for i, d in enumerate(depots):
        person(f"manager:{i}", names[len(people)], f"manager of the {d} depot")
    suppliers_n = [f"{a} {b}" for a, b in zip(r.sample(_SUPPLIER_WORDS, 5), r.choices(_SUPPLIER_SUFFIXES, k=5))]
    for i, s in enumerate(suppliers_n):
        person(f"contact:{i}", names[len(people)], f"account manager at {s}")

    # carriers
    carriers = []
    for i, (cw, cs) in enumerate(zip(r.sample(_CARRIER_WORDS, 3), r.choices(_CARRIER_SUFFIXES, k=3))):
        name = f"{cw} {cs}"
        c = {"name": name, "id": f"{ROOT}/wiki/carriers/{slug(name)}", "cutoff": f"{r.choice([13, 14, 15, 16, 17])}:{r.choice(['00', '30'])}",
             "days": r.randint(1, 4), "line": r.randint(3000, 9899)}
        carriers.append(c)
        _page(w, "wiki", "page", f"carriers/{slug(name)}", name,
              f"You need a fact about the carrier {name}: its pickup cutoff, its delivery time or its dispatch line.",
              f"{name}, a road carrier the distributor books pickups with.",
              [("cutoff", f"A pickup with {name} must be booked before {c['cutoff']}."),
               ("delivery", f"{name} delivers within {c['days']} working days."),
               ("dispatch-line", f"The dispatch line of {name} is {c['line']}.")])

    # warehouses
    warehouses = []
    for i, d in enumerate(depots):
        open_h = r.choice([5, 6, 7, 8]); close_h = open_h + r.choice([7, 8, 9, 10])
        wh = {"name": f"{d} depot", "id": f"{ROOT}/wiki/warehouses/{slug(d)}", "town": towns[i],
              "hours": f"{open_h:02d}:00 to {close_h:02d}:00", "manager": f"manager:{i}", "carrier": carriers[i % 3]}
        warehouses.append(wh)
        m = people[wh["manager"]]
        _page(w, "wiki", "page", f"warehouses/{slug(d)}", wh["name"],
              f"You need a fact about the {d} depot: where it is, who manages it, its dock hours or its carrier.",
              f"The {d} depot, one of the distributor's warehouses.",
              [("town", f"The {d} depot is in {wh['town']}."),
               ("manager", f"The {d} depot is managed by {_link(m['id'])}."),
               ("dock-hours", f"The docks of the {d} depot are open from {wh['hours']}."),
               ("carrier", f"The {d} depot ships with {_link(wh['carrier']['id'])}.")])

    # suppliers
    suppliers = []
    for i, name in enumerate(suppliers_n):
        s = {"name": name, "id": f"{ROOT}/wiki/suppliers/{slug(name)}", "town": towns[4 + i],
             "lead": r.randint(3, 21), "minimum": r.choice([20, 25, 30, 40, 50, 60, 80, 100]), "contact": f"contact:{i}"}
        suppliers.append(s)
        _page(w, "wiki", "page", f"suppliers/{slug(name)}", name,
              f"You need a fact about the supplier {name}: where it is, its lead time, its minimum order or its contact.",
              f"{name}, a supplier of packaging the distributor buys from.",
              [("town", f"{name} is based in {s['town']}."),
               ("lead-time", f"An order from {name} arrives {s['lead']} days after it is placed."),
               ("minimum-order", f"The minimum order at {name} is {s['minimum']} packs."),
               ("contact", f"The contact at {name} is {_link(people[s['contact']]['id'])}.")])

    # products
    products = []
    words = r.sample(_PRODUCT_WORDS, 10)
    types = r.sample(_PRODUCT_TYPES, 10)
    for i, (word, (kind, unit)) in enumerate(zip(words, types)):
        # 310–990: no drawn value lives there (packs ≤ 48, reorder points ≤ 200, days ≤ 90), so a
        # product's name never states an answer a question could copy — corpus gate G4
        name = f"{word}-{r.randrange(310, 1000, 10)} {kind}"
        p = {"name": name, "id": f"{ROOT}/wiki/products/{slug(name)}", "unit": unit, "pack": r.choice([6, 8, 10, 12, 18, 20, 24, 36, 48]),
             "reorder": r.choice([40, 60, 80, 100, 120, 150, 200]), "supplier": suppliers[i % 5], "warehouse": warehouses[r.randrange(4)]}
        products.append(p)
        _page(w, "wiki", "page", f"products/{slug(name)}", name,
              f"You need a fact about the {name}: who supplies it, where it is stocked, its pack or its reorder point.",
              f"The {name}, one of the products the distributor carries.",
              [("supplier", f"The {name} is supplied by {_link(p['supplier']['id'])}."),
               ("warehouse", f"The {name} is stocked at {_link(p['warehouse']['id'])}."),
               ("pack", f"A pack of {name} holds {p['pack']} {unit}."),
               ("reorder-point", f"The {name} is reordered when stock falls below {p['reorder']} packs.")])

    for key, pr in people.items():
        _page(w, "wiki", "page", f"people/{slug(pr['name'])}", pr["name"],
              f"You need to know who {pr['name']} is or how to reach them.",
              f"{pr['name']}, {pr['role']}.",
              [("role", f"{pr['name']} is the {pr['role']}."),
               ("extension", f"{pr['name']} can be reached on extension {pr['extension']}.")])

    # the operative recipes — one per role of the reference organisation; values drawn per world
    L = {k: _link(people[k]["id"]) for k in LEADS}
    v = {"order_limit": r.choice([500, 750, 1000, 1500, 2000, 2500]), "count_h": r.choice([1, 2, 3, 4, 6]),
         "photo_h": r.choice([12, 24, 36, 48, 72]), "return_d": r.choice([5, 7, 10, 14, 21, 30]),
         "late_h": r.choice([2, 4, 6, 8, 12]), "email_h": r.choice([1, 2, 3, 4, 6, 8]),
         "invoice_limit": r.choice([2000, 3000, 5000, 7500, 10000]), "pay_d": r.choice([14, 21, 30, 45, 60, 90]),
         "ot_h": r.choice([4, 6, 8, 10, 12]), "discount": r.choice([10, 15, 20, 25, 30]), "notice_d": r.choice([3, 5, 7, 10, 14]),
         "readonly_d": r.choice([7, 14, 30, 60, 90])}
    recipes = {
        "purchasing": ("reorder", "Reordering stock", "Stock of a product is low and it has to be reordered from its supplier.",
                       [("reorder-point", "A product is reordered when its stock falls below the reorder point on its page."),
                        ("small-order", f"An order under {v['order_limit']} euros is approved by {L['purchasing']}."),
                        ("large-order", f"An order of {v['order_limit']} euros or more is approved by {L['finance']}."),
                        ("arrival", "A reordered product arrives after its supplier's lead time.")]),
        "receiving": ("inbound", "Receiving a delivery", "A supplier's delivery arrives at a depot and has to be received.",
                      [("unload", "A delivery is unloaded only during the depot's dock hours."),
                       ("count", f"Every pallet is counted within {v['count_h']} hours of unloading."),
                       ("short", f"A delivery that is short is reported to {L['receiving']}.")]),
        "dispatch": ("outbound", "Shipping a customer order", "A customer order has to be shipped from a depot.",
                     [("book", "A pickup is booked with the depot's carrier before the carrier's cutoff."),
                      ("missed", f"An order that misses the cutoff ships the next working day and the customer is told by {L['communications']}.")]),
        "claims": ("claims", "Handling a damaged, wrong or late delivery", "Goods arrived damaged, wrong or late and a claim or a return is needed.",
                   [("if-damaged", f"If the goods arrived damaged, photographs are sent to {L['claims']} within {v['photo_h']} hours."),
                    ("if-wrong-item", f"If the wrong item arrived, it is returned within {v['return_d']} days."),
                    ("if-late", f"If a delivery is more than {v['late_h']} hours late, {L['dispatch']} asks the carrier for a new date."),
                    ("credit", f"A credit note for a claim is issued by {L['finance']}.")]),
        "communications": ("delay-notice", "Telling a customer about a delay", "A customer order will be late and the customer has to be told.",
                           [("email", f"A customer is emailed within {v['email_h']} hours of a known delay."),
                            ("urgent", f"For an urgent order the customer is phoned by {L['communications']} instead.")]),
        "finance": ("invoice", "Approving a supplier invoice", "A supplier's invoice has arrived and has to be approved and paid.",
                    [("under-threshold", f"An invoice of up to {v['invoice_limit']} euros is approved by {L['purchasing']}."),
                     ("over-threshold", f"An invoice over {v['invoice_limit']} euros is approved by {L['finance']}."),
                     ("terms", f"Suppliers are paid {v['pay_d']} days after the invoice date.")]),
        "hr": ("overtime", "Approving overtime", "An employee wants overtime approved or paid.",
               [("approval", "Overtime is approved by the manager of the employee's depot."),
                ("limit", f"An employee may work at most {v['ot_h']} hours of overtime a week."),
                ("payroll", f"Approved overtime is paid in the next payroll run by {L['hr']}.")]),
        "marketing": ("promotion", "Running a promotion", "A price promotion is planned for customers.",
                      [("approval", f"A discount above {v['discount']} percent is approved by {L['marketing']}."),
                       ("notice", f"Customers are told about a promotion {v['notice_d']} days before it starts.")]),
        "it": ("access", "Getting access to the stock system", "Someone needs access to the stock system.",
               [("request", f"Access to the stock system is requested from {L['it']}."),
                ("new-staff", f"A new employee has read-only access for the first {v['readonly_d']} days.")]),
    }
    recipe_ids = {}
    for role, (rs, title, when, sts) in recipes.items():
        recipe_ids[role] = _page(w, "harness", "recipe", f"{role}/{rs}", title,
                                 f"{when} The {LEADS[role]}'s procedure.", f"How the distributor handles it: {title.lower()}.", sts)

    f.update(people=people, carriers=carriers, warehouses=warehouses, suppliers=suppliers, products=products,
             values=v, recipes=recipe_ids)
    return w


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="write one world to disk")
    ap.add_argument("--seed", type=int, default=EVAL_SEED)
    ap.add_argument("--out", default=f"knowledge/{ROOT}")
    a = ap.parse_args()
    build(a.seed).write(Path(a.out))
    print(f"[wiki] world {a.seed} written to {a.out}")
