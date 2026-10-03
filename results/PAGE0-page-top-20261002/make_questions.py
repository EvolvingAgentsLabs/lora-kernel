"""Writes results/PAGE0-page-top-20261002/questions.jsonl (run from the repo root).

A FRESH frozen set over the real library knowledge/hazwaste-regs (40 CFR Part 262, EPA standards for generators of
hazardous waste, ingested eCFR text), written from the library pages alone — no model answer, no walk, no run log, no
result section and none of the treatment's code was read. Format, helpers and token rules are CITE0's
(results/CITE0-runtime-check-20261002/make_questions.py): every value row grades with `check.cite = "support"` (the
citation must BE the supporting statement), and every check token is a number that occurs in that statement and in no
statement the oracle walk opened before it. No question carries a digit or a section number.

Tokens: a value printed with a thousands comma ("6,000") or a dot ("261.4", "30.200") is checked as the string the
statement prints, ALONE in its row — the grader's hedge test splits it, so it never shares a row with a plain number.

AVOIDED: statements whose text is repeated word for word elsewhere in the library (the SQG/LQG "Sign Item 18c"
paragraphs, the import/export ISO-code paragraphs, the LQG exception-report paragraph that repeats its 60 days for the
e-Manifest system) — nothing tells the two apart, so a strict citation would grade a coin.

SHARED STATEMENTS: no supporting statement is used twice. Two first/middle statements are reused as a route:
262-264§text (start of a two-hop, middle of a three-hop) and 262-83§iii-2-2 (start of a two-hop, middle of a three-hop),
each time leading to a DIFFERENT supporting statement. One value repeats across two supports in different sections:
the National Response Center number (262-265§d-2 is a support; the same number sits unasked in 262-16§b-9-iv-c).
"""
import json
import re
from collections import Counter

P = "hazwaste-regs/wiki/"
LIB = "knowledge/hazwaste-regs/wiki/"
OUT = "results/PAGE0-page-top-20261002/questions.jsonl"
# the start page's search query: its title, as REAL3/REAL5/CITE0 (a bare generic title gets its section number)
Q = {"262-10": "purpose scope and applicability",
     "262-13": "generator category determination",
     "262-14": "conditions for exemption for a very small quantity generator",
     "262-15": "satellite accumulation area regulations for small and large quantity generators",
     "262-16": "conditions for exemption for a small quantity generator that accumulates hazardous waste",
     "262-17": "conditions for exemption for a large quantity generator that accumulates hazardous waste",
     "262-20": "section 262.20 general requirements",
     "262-21": "manifest tracking numbers manifest printing and obtaining manifests",
     "262-24": "use of the electronic manifest",
     "262-41": "biennial report for large quantity generators",
     "262-42": "exception reporting",
     "262-81": "section 262.81 definitions",
     "262-83": "exports of hazardous waste",
     "262-84": "imports of hazardous waste",
     "262-207": "section 262.207 training",
     "262-209": "where and when to make the hazardous waste determination and where to send containers of unwanted "
                "material upon removal from the laboratory",
     "262-210": "making the hazardous waste determination in the laboratory before the unwanted material is removed "
                "from the laboratory",
     "262-214": "laboratory management plan",
     "262-232": "conditions for a generator managing hazardous waste from an episodic event",
     "262-261": "content of contingency plan",
     "262-262": "copies of contingency plan",
     "262-264": "emergency coordinator"}


def walk(start, *hops):
    """start page key; hops = [(page, anchor), ...]: open page, open page§anchor for each."""
    plan = [["search", "wiki", Q[start]]]
    for pg, an in hops:
        plan += [["open", P + pg], ["open", P + pg, an]]
    return plan


rows = []


def add(fam, block, hops, question, plan, answer, tokens, famous=False):
    sup = plan[-1][1:]
    rows.append({"family": fam, "block": block, "hops": hops, "shelf": "wiki", "question": question, "plan": plan,
                 "support": list(sup), "answer": answer, "check": {"kind": "value", "tokens": tokens, "cite": "support"},
                 "famous": famous})


def none(question, query):
    rows.append({"family": "none", "block": "none", "hops": 0, "shelf": "wiki", "question": question,
                 "plan": [["search", "wiki", query]], "support": None, "answer": "Not in my library.",
                 "check": {"kind": "none", "tokens": []}, "famous": False})


# ---------------- one hop: the value is in the first statement opened
R1 = lambda q, pg, an, a, t, famous=False: add("one-hop", "R1", 1, q, walk(pg, (pg, an)), a, t, famous)
R1("Our resin plant received an export consent letter from EPA years ago and still ships under it. Exporters whose "
   "consent was received before what date stay subject to that approval until it expires?",
   "262-83", "a", "before December 31, 2016", ["31", "2016"])
R1("My logistics team uploads the top copy of each export manifest to the e-Manifest system within thirty days of "
   "getting it from the final domestic transporter. That duty begins on what date?",
   "262-83", "c-4", "beginning on December 1, 2025", ["1", "2025"])
R1("We are shutting down our large quantity generator plant for good. After closing, within how many days must we "
   "notify EPA that we met the closure performance standards?",
   "262-17", "a-8-ii-b", "within 90 days after closing the facility", ["90"])
R1("At our refinery we are closing one waste accumulation unit but keeping the others open. If we place a notice in "
   "the operating record, it is due within how many days after closure?",
   "262-17", "a-8-i-a", "within 30 days after closure", ["30"])
R1("Our small quantity generator paint shop keeps waste in an uncovered tank with no containment structure. How many "
   "centimeters of freeboard must that tank keep?",
   "262-16", "b-3-ii-c", "at least 60 centimeters", ["60"])
R1("As a small quantity generator running a batch-process tank on our plating line, our inventory logs must show the "
   "tank was emptied within how many days of waste first entering it?",
   "262-16", "b-6-ii-c", "within 180 days of first entering the tank", ["180"])
R1("Looking at the paper manifest forms at our shipping desk, which page of the form is marked as the copy the "
   "designated facility sends to the generator?",
   "262-21", "f-6-ii", "Page 2", ["2"])
R1("The customs broker for our warehouse asked about EPA's Acknowledgment of Consent letter for our waste exports. It "
   "meets the definition of an export license in which Census Bureau regulation, by CFR title and section?",
   "262-81", "text-19", "15 CFR 30.1", ["30.1"])
R1("Our very small quantity generator lab is planning a one-off purge of excess chemical inventory. How many calendar "
   "days ahead must we notify EPA, and if an unplanned event hits instead, within how many hours?",
   "262-232", "a-2", "no later than 30 calendar days before; within 72 hours of an unplanned event", ["30", "72"])
R1("A tank cleanout at our small quantity generator plant counts as an episodic event. Within how many calendar days "
   "from its start must we treat that waste on site or ship it off site?",
   "262-232", "b-5", "within 60 calendar days from the start of the episodic event", ["60"])
R1("Our little body shop is a very small quantity generator but has piled up more than a tonne of non-acute waste. "
   "Once that amount is exceeded, for how many days may the waste be held on site?",
   "262-14", "a-4-i", "no more than 180 days, or 270 days if applicable", ["180", "270"])
R1("Our plant in Massachusetts handles Class A recyclable materials under the state program instead of the federal "
   "accumulation conditions. Which section of the state's regulations does the federal rule name?",
   "262-10", "k", "310 C.M.R. 30.200", ["30.200"])
R1("We recently became a large quantity generator and must give the fire department a quick reference guide to our "
   "contingency plan. That applies to generators first subject after what date?",
   "262-262", "b", "after May 30, 2017", ["30", "2017"])
R1("The signed manifest from the disposal facility never came back to our large quantity generator warehouse. Within "
   "how many days of the transporter accepting the waste should we have contacted the transporter or facility?",
   "262-42", "a", "within 45 days", ["45"])

# ---------------- two hops: a statement's link must be followed to the page holding the value
R2 = lambda fam, q, start, an, target, a, t: add(fam, "R2", 2, q, walk(start, (start, an), target), a, t)
# applicability / very small quantity generators → identification numbers
R2("scope-id", "We import spent catalyst into our refinery, so the purpose-and-scope section sends us to the "
   "identification-number rules. Starting in which year must a small quantity generator re-notify EPA every four "
   "years?",
   "262-10", "d", ("262-18", "d"), "starting in 2021", ["2021"])
R2("vsqg-id", "Our dental clinic is a very small quantity generator that briefly held too much acute waste, so it must "
   "notify under the identification-number section. Which EPA form do we use to apply for an identification number?",
   "262-14", "a-3-iii", ("262-18", "b"), "EPA Form 8700-12", ["8700", "12"])
# very small quantity generators → the accumulation sections
R2("vsqg-lqg", "Our machine shop is normally a very small quantity generator, but it held more acute waste than "
   "allowed, so the large quantity generator conditions now apply to it. How far from the property line must ignitable "
   "waste containers then be kept, in meters and feet?",
   "262-14", "a-3-ii", ("262-17", "a-1-vi"), "at least 15 meters (50 feet)", ["15", "50"])
R2("vsqg-sqg", "We run a very small quantity generator print shop that stockpiled over a tonne of non-acute waste, "
   "which brings in the small quantity generator conditions. If our disposal site is at least how many miles away, we "
   "may accumulate for up to how many days?",
   "262-14", "a-4-iii", ("262-16", "c"), "200 miles or more; 270 days or less", ["200", "270"])
R2("category-vsqg", "Our category decides which exemption section our foundry must meet, and we are a very small "
   "quantity generator. Accumulating at any time how many kilograms of non-acute waste brings extra conditions?",
   "262-13", "e", ("262-14", "a-4"), "1,000 kilograms or greater", ["1,000"])
# satellite areas ↔ central accumulation
R2("satellite-lqg", "A leaking satellite drum at our large quantity generator plant was moved into our central "
   "accumulation area under the large quantity generator rules. Under those rules, if we need more time to clean close "
   "the facility, within how many days of the closure-notice date must we ask EPA?",
   "262-15", "a-1", ("262-17", "a-8-ii-c"), "within 75 days", ["75"])
R2("satellite-sqg", "Excess waste at our satellite point must come under the central accumulation area rules within "
   "three days, and we are a small quantity generator. Under those rules, how many kilograms of non-acute waste may "
   "we never exceed on site?",
   "262-15", "a-6-i", ("262-16", "b-1"), "6,000 kilograms", ["6,000"])
R2("sqg-satellite", "Waste we scrape off the drip pad at our small quantity generator wood-treating yard sometimes goes "
   "to satellite areas first. How many gallons of non-acute waste may a satellite accumulation area hold?",
   "262-16", "b-4-ii", ("262-15", "a"), "as much as 55 gallons", ["55"])
R2("sqg-lqg", "At our electroplating shop, a small quantity generator, we read that during an episodic event it "
   "accumulates under the episodic rules instead of the large quantity generator section. In that section, how many kilograms of "
   "electroplating wastewater treatment sludge may sit on site at one time for metals recovery?",
   "262-16", "f", ("262-17", "c-3"), "no more than 20,000 kilograms", ["20,000"])
R2("lqg-scope", "Our large quantity generator hub consolidates waste from sister sites and must meet the independent "
   "requirements listed in the purpose-and-scope section. That section says a healthcare facility generating more "
   "than how many kilograms, or pounds, a month must check the pharmaceutical rule?",
   "262-17", "f-3", ("262-10", "n"), "more than 100 kg (220 pounds)", ["100", "220"])
# category / determination
R2("category-cleanout", "Unused chemicals from a lab clean-out at our university are left out of the monthly count "
   "under the clean-out section. Each lab may hold such a clean-out once per how many months?",
   "262-13", "c-7", ("262-213", "a"), "one time per 12 month period", ["12"])
R2("category-determination", "When our factory mixes small quantity generator waste with ordinary trash, the mixture "
   "falls under the hazardous waste determination requirement. In that determination, exclusions from regulation are "
   "checked under which CFR section?",
   "262-13", "iii-2", ("262-11", "b"), "40 CFR 261.4", ["261.4"])
R2("training-determination", "The trained professional at our campus lab makes waste determinations under the "
   "determination section. If a waste is listed, under which CFR sections may we file a delisting petition?",
   "262-207", "d-2", ("262-11", "c"), "40 CFR 260.20 and 260.22", ["260.20"])
R2("lab-category", "Hazardous waste found in our teaching lab is counted toward our generator category under the "
   "category section. Used oil is left out of that count when managed under which CFR part?",
   "262-210", "b-3", ("262-13", "c-4"), "part 279", ["279"])
# manifests
R2("manifest-electronic", "Our shipping dock now prepares electronic manifests, following the electronic manifest "
   "section. Which hazardous materials shipping-paper rule, by CFR section, makes us hand the initial transporter one "
   "printed copy?",
   "262-20", "a-3-i", ("262-24", "d"), "49 CFR 177.817", ["177.817"])
R2("manifest-marking", "Our forklifts carry drums across a public road that splits our own property, where the "
   "manifest subpart and part of the marking section do not apply. Under that marking section, containers of up to how "
   "many gallons need the federal hazardous waste marking?",
   "262-20", "f", ("262-32", "b"), "119 gallons or less", ["119"])
R2("electronic-manifest", "Electronic manifests at our recycling yard count as legal equivalents when transmitted per "
   "the manifest general requirements. Those requirements exempt contract-reclaimed waste from generators producing "
   "between how many and how many kilograms a month?",
   "262-24", "a", ("262-20", "e"), "greater than 100 kg but less than 1000 kg", ["100", "1000"])
R2("export-printing", "For our export shipments we get manifests from any EPA-approved printer under the manifest "
   "printing section. In which numbered item of the manifest is the unique tracking number pre-printed?",
   "262-83", "c-3", ("262-21", "f-2"), "Item 4", ["4"])
# transboundary
R2("biennial-export", "Our plant's exports of spent catalyst are left off the Biennial Report and reported yearly "
   "under the export section. How many days before the first shipment must the export notification reach EPA?",
   "262-41", "c", ("262-83", "b"), "at least 60 days before the first shipment", ["60"])
R2("defs-export", "As the exporter named in the subpart's definitions, our warehouse originates the movement document "
   "under the export section. If the transporter-signed manifest showing the departure point has not come back within "
   "how many days, within how many more days is the exception report due?",
   "262-81", "text-20", ("262-83", "i-3"), "within 45 days; then within the next 30 days", ["45", "30"])
R2("export-conditions", "Before electronic reporting began, our chemical distributor mailed its export exception "
   "reports to the addresses in the transboundary general conditions. What ZIP code does the postal mail address "
   "carry?",
   "262-83", "iii-2-2", ("262-82", "e-1"), "Washington, DC 20460", ["20460"])
R2("import-conditions", "Our contract lab imports waste samples, and the import notification rules point to the "
   "general conditions section. Up to how many kilograms may a sample weigh for the laboratory analysis exemption?",
   "262-84", "b-1", ("262-82", "d"), "25 kg", ["25"])
R2("import-export", "Our import contract says the receiving facility gives the re-export notice the export section "
   "requires. If a foreign facility tells an exporter a shipment must come back, the exception report is due within "
   "how many days of notice, or how many days before the return starts?",
   "262-84", "f-5", ("262-83", "iii-2"), "within 30 days of notification, or 1 day prior to the return, whichever is "
   "sooner", ["30", "1"])
# episodic events / preparedness
R2("episodic-petition", "Having already held its planned episodic event this year, our very small quantity generator "
   "workshop may hold another only by petition. Within how many hours of an unplanned event must we petition?",
   "262-232", "a-1", ("262-233", "a-1"), "within 72 hours of the unplanned event", ["72"])
R2("contingency-arrangements", "Our contingency plan must describe the arrangements made under the local-authorities "
   "section. A facility with response capabilities around the clock for how many hours may seek a waiver from the "
   "fire code authority?",
   "262-261", "c", ("262-256", "c"), "24-hour response capabilities", ["24"])
R2("coordinator-procedures", "Our warehouse's emergency coordinator carries out the emergency procedures section. "
   "After an incident that needed the contingency plan, within how many days is the written report to the Regional "
   "Administrator due?",
   "262-264", "text", ("262-265", "h-2-i"), "within 15 days after the incident", ["15"])

# ---------------- three hops
R3 = lambda fam, q, start, an, mid, target, a, t: add(fam, "R3", 3, q, walk(start, (start, an), mid, target), a, t)
R3("lmp-cleanout-removal", "Our college's laboratory management plan covers clean-out procedures under the clean-out "
   "section, and other clean-outs that year still follow the removal section. Under that removal section, a regular "
   "interval for removing all containers may not exceed how many months?",
   "262-214", "b-6-i", ("262-213", "b-1"), ("262-208", "a-1"), "not to exceed 12 months", ["12"])
R3("plan-coordinator-procedures", "Our contingency plan names our emergency coordinators per the coordinator section, "
   "which ties them to the emergency procedures. When a release threatens people outside the plant, which toll-free "
   "number must the coordinator call for the National Response Center?",
   "262-261", "d", ("262-264", "text"), ("262-265", "d-2"), "800/424-8802", ["800", "424", "8802"])
R3("import-export-conditions", "Our import contract makes the named party give re-export notice under the export "
   "section, whose exception reports once went to the general conditions addresses. What ZIP code is used there for "
   "hand delivery?",
   "262-84", "f-4-ii", ("262-83", "iii-2-2"), ("262-82", "e-2"), "Washington, DC 20004", ["20004"])
R3("lab-central-category", "At our university the trained professional checks unwanted lab material at the central "
   "accumulation area under its own section, and that waste is then counted under the category section. Universal "
   "waste is left out of the count when managed under which CFR part?",
   "262-209", "a-2", ("262-211", "e-3"), ("262-13", "c-6"), "part 273", ["273"])

# ---------------- not in the library: four adjacent (transport, oil, air, water — outside Part 262), four unrelated
none("How often must the hazmat employees who load our trucks repeat their DOT hazardous materials training?",
     "hazmat employee training recurrent")
none("Under the oil spill prevention rule, how often must the dikes around our heating oil tanks be inspected?",
     "oil tank dike inspection frequency")
none("What opacity limit applies to the smoke from our boiler stack?", "boiler stack opacity limit")
none("What concentration of oil and grease may our plant discharge to the city sewer under the pretreatment rules?",
     "sewer pretreatment oil and grease limit")
none("What clearance must we keep between stored pallets and the sprinkler heads in our warehouse?",
     "warehouse sprinkler clearance storage")
none("How long can a truck sit at our loading dock before detention charges start?", "truck detention charges dock")
none("What is the heaviest box one worker should lift by hand in our distribution center?",
     "manual lifting weight limit")
none("How often should we cycle count the fast-moving items in our warehouse?", "warehouse cycle count frequency")

# ---------------- self-checks (the walk, the tokens, the questions)
_NUM = re.compile(r"\d+(?::\d+)?")


def statements(page):
    out = {}
    for line in open(LIB + page + ".md", encoding="utf-8"):
        if line.startswith("§"):
            an, txt = line.rstrip("\n").split(" ", 1)
            out[an[1:]] = txt
    return out


LINK = re.compile(r"\[\[hazwaste-regs/wiki/([^\]]+)\]\]")


def has(text, tok):
    plain = LINK.sub(" ", text)  # a link renders as an opaque id, not as its digits
    if _NUM.fullmatch(tok):
        return str(int(tok)) in {str(int(n)) for n in _NUM.findall(plain)}
    return tok.lower() in plain.lower()


for r in rows:
    q = r["question"]
    assert not re.search(r"\d", q), q
    if r["check"]["kind"] == "none":
        continue
    opened = [(st[1][len(P):], st[2]) for st in r["plan"] if st[0] == "open" and len(st) == 3]
    assert len(opened) == r["hops"], q
    assert opened[0][0] == r["plan"][2][1][len(P):] and r["plan"][0][2] == Q[opened[0][0]]
    for (p0, a0), (p1, _) in zip(opened, opened[1:]):
        assert f"[[{P}{p1}]]" in statements(p0)[a0], (q, p0, a0, p1)   # every hop is a real link
        assert p1 != opened[0][0] or r["hops"] == 1, (q, p1)            # the value is never on the start page
    if r["hops"] >= 2:
        assert opened[-1][0] != opened[0][0], q
    sp, sa = opened[-1]
    toks = r["check"]["tokens"]
    for t in toks:
        assert has(statements(sp)[sa], t), (sp, sa, t)
        for p, a in opened[:-1]:
            assert not has(statements(p)[a], t), (q, p, a, t)
    if any(not _NUM.fullmatch(t) for t in toks):
        assert len(toks) == 1, toks  # a comma/dot value stands alone in its row
    else:  # the oracle's answer line must not hedge
        assert {str(int(n)) for n in _NUM.findall(r["answer"])} == {str(int(t)) for t in toks}, r["answer"]
qs = [r["question"] for r in rows]
assert len(set(qs)) == len(qs), "duplicated question"
first4 = Counter(" ".join(q.lower().split()[:4]) for q in qs)
assert max(first4.values()) == 1, [k for k, v in first4.items() if v > 1]
sups = [tuple(r["support"]) for r in rows if r["support"]]
assert len(set(sups)) == len(sups), "a supporting statement repeats"

for i, r in enumerate(rows):
    r["case_id"] = f"page0-{r['family']}-{i:02d}"
order = ["case_id", "world", "family", "block", "hops", "shelf", "question", "plan", "support", "answer", "check", "famous"]
with open(OUT, "w") as f:
    for r in rows:
        r["world"] = "hazwaste-regs"
        f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")
print(len(rows), "rows · hops", dict(Counter(r["hops"] for r in rows)), "· supports all distinct:",
      len(set(sups)) == len(sups))
