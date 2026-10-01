"""Writes results/REAL3-real-corpus-20260930/questions.jsonl (run from the repo root).

A FRESH frozen set over the same library as REAL0 (knowledge/logistics-regs: 21 CFR 1 Subpart O, 29 CFR 1910.176/.178),
written without seeing the real-corpus training questions. Same row format as REAL0; every value row grades with
`check.cite = "support"` (the citation must BE the supporting statement) and every check token is a number (or a
dotted section number) that occurs in that statement and in no statement the oracle walk opened before it.
No question repeats a REAL0 (support, ask) pair; the rows that reuse a REAL0 support statement ask another value or
the statement's other branch, and are listed in REUSES_REAL0_SUPPORT below.
"""
import json

P = "logistics-regs/wiki/"
Q = {"908": "requirements for transportation operations", "910": "training requirements for carriers",
     "912": "record retention", "900": "who is subject", "904": "what definitions apply", "178": "powered industrial trucks",
     "902": "criteria and definitions apply under the Federal Food Drug and Cosmetic Act",
     "916": "when will we consider whether to waive a requirement",
     "920": "information submitted in a petition requesting a waiver publicly available",
     "924": "what process applies to a petition requesting a waiver"}
PG = {k: P + ("1910-" + k if k in ("176", "178") else "1-" + k) for k in
      ("900", "902", "904", "906", "908", "910", "912", "916", "920", "924", "176", "178")}

# (page, anchor) of the REAL0 support statements these rows reuse, with a different ask
REUSES_REAL0_SUPPORT = {("904", "text-2"), ("904", "non-covered-business"), ("912", "h"), ("912", "a-2"), ("178", "a-2")}


def walk(start, *hops):
    """start page key; hops = [(page, anchor), ...]: open page, open page§anchor for each."""
    plan = [["search", "wiki", Q[start]]]
    for pg, an in hops:
        plan += [["open", PG[pg]], ["open", PG[pg], an]]
    return plan


rows = []


def add(fam, block, hops, question, plan, answer, tokens):
    sup = plan[-1][1:]
    rows.append({"family": fam, "block": block, "hops": hops, "shelf": "wiki", "question": question, "plan": plan,
                 "support": list(sup), "answer": answer, "check": {"kind": "value", "tokens": tokens, "cite": "support"}})


def none(question, query):
    rows.append({"family": "none", "block": "none", "hops": 0, "shelf": "wiki", "question": question,
                 "plan": [["search", "wiki", query]], "support": None, "answer": "Not in my library.",
                 "check": {"kind": "none", "tokens": []}})


# ---------------- one hop: the value is in the first statement opened
R1 = lambda q, pg, an, a, t: add("one-hop", "R1", 1, q, walk(pg, (pg, an)), a, t)
R1("Which NFPA code (the 1969 edition) governs how we store and handle the gasoline and diesel for our lift trucks?",
   "178", "f", "NFPA No. 30, the Flammable and Combustible Liquids Code", ["30"])
R1("Our forklifts run on propane. Which NFPA standard number (1969 edition) governs storing and handling that liquefied petroleum gas?",
   "178", "f-2", "NFPA No. 58", ["58"])
R1("Carbon monoxide from our lift trucks indoors must stay under limits set in which OSHA section?",
   "178", "h-2-i", "the levels specified in § 1910.1000", ["1910.1000"])
R1("Our lift trucks must bear the testing laboratory's approval mark. Which paragraph of ANSI B56.1-1969 provides for that marking?",
   "178", "a-3", "paragraph 405", ["405"])
R1("For forklift approvals, where in OSHA's rules is a nationally recognized testing laboratory defined?",
   "178", "a-7", "§ 1910.7", ["1910.7"])
R1("An approved forklift has to be listed for fire safety. Where in OSHA's rules is the definition of listed?",
   "178", "a-7", "§ 1910.155(c)(3)(iv)(A)", ["1910.155"])
R1("The ANSI design standard that new forklifts must meet is incorporated by reference. In which OSHA section?",
   "178", "a-2", "§ 1910.6", ["1910.6"])
R1("Our driver steps off the forklift to read a label but stays close with the truck in view. Up to what distance must he still lower the forks, neutralize the controls and set the brakes?",
   "178", "m-5-iii", "within 25 ft of the truck", ["25"])
R1("If a carrier ignores the sanitary food transportation rule, which section of the Food, Drug, and Cosmetic Act makes that a prohibited act?",
   "902", "text-2", "section 301(hh)", ["301"])
R1("Food hauled in breach of the sanitary transportation rule is adulterated within the meaning of which section of the Food, Drug, and Cosmetic Act?",
   "902", "text", "section 402(i)", ["402"])
R1("We want the FDA to waive one of the sanitary transport requirements for our class of vehicles. Under which section of the chapter is the petition submitted?",
   "916", "text", "a petition under § 10.30", ["10.30"])
R1("If we petition for a sanitary-transport waiver, the FDA presumes our submission holds nothing exempt from disclosure. Which part of the chapter sets those disclosure exemptions?",
   "920", "text", "part 20", ["20"])
R1("After we file a waiver petition, under which provision does the FDA publish a Federal Register notice asking for information and views?",
   "924", "b", "§ 10.30(h)(3)", ["10.30(h)(3)"])

# ---------------- two hops: a statement's link must be followed to the page holding the value
R2 = lambda fam, q, start, an, target, a, t: add(fam, "R2", 2, q, walk(start, (start, an), target), a, t)
# from who is covered (its exception names the definitions) to the definitions
R2("coverage-defs", "We're checking whether the sanitary food transport rule covers our company, and its exceptions lean on how it counts full-time equivalent staff. In that count, how many hours a week is one full-time employee taken to work?",
   "900", "a", ("904", "text-2"), "40 hours a week", ["40"])
R2("coverage-defs", "To see whether we fall outside the sanitary transport rule we must count our full-time equivalents the rule's way. How many weeks of work in a year does that count assume?",
   "900", "a", ("904", "text-2"), "52 weeks", ["52"])
R2("coverage-defs", "Our family-run produce shipper may be too small for the sanitary transportation rule to apply at all. The revenue test for that is an average taken over how many preceding years?",
   "900", "a", ("904", "non-covered-business"), "the 3-year period preceding the applicable calendar year", ["3"])
R2("coverage-defs", "Once we know the sanitary transport rule covers us we must protect unwrapped food from allergen cross-contact. That definition borrows the meaning of food allergen from which section of the Food, Drug, and Cosmetic Act?",
   "900", "a", ("904", "cross-contact"), "section 201(qq)", ["201"])
R2("coverage-defs", "We truck boxed food contact substances, which stay in scope even fully enclosed. Which section of the Food, Drug, and Cosmetic Act defines the food contact substances the rule keeps in?",
   "900", "a", ("904", "transportation-operations"), "section 409(h)(6)", ["409", "6"])
R2("coverage-defs", "Work done by a farm is outside the rule's transportation operations. Which section of the chapter does the rule take its meaning of farm from?",
   "900", "a", ("904", "farm"), "§ 1.227", ["1.227"])
R2("coverage-defs", "Besides the rule's own list of definitions, terms in the sanitary transport rule take the definitions and interpretations of which section of the Food, Drug, and Cosmetic Act?",
   "900", "a", ("904", "text"), "section 201", ["201"])
# from the small-business definition (it names the businesses covered) to the coverage page
R2("defs-coverage", "We're a small trucking firm; our small-business test refers to the businesses the rule applies to. We haul food imported only for future export. Under which section of the Food, Drug, and Cosmetic Act must that import happen for the rule not to apply?",
   "904", "small-business", ("900", "b-2"), "section 801(d)(3)", ["801", "3"])
R2("defs-coverage", "Our small-business test points to the businesses the rule covers, which leaves out facilities regulated only by USDA. Where in Title 21 of the U.S. Code does the Federal Meat Inspection Act start?",
   "904", "small-business", ("900", "b-3"), "21 U.S.C. 601 et seq.", ["601"])
R2("defs-coverage", "The small-business definition sends us to the provision on who is covered; it exempts plants regulated entirely by USDA. At which section of Title 21 of the U.S. Code does the Poultry Products Inspection Act begin?",
   "904", "small-business", ("900", "b-3"), "21 U.S.C. 451 et seq.", ["451"])
R2("defs-coverage", "We pack eggs at a plant inspected only by USDA. Following the small-business definition to the coverage provision, at which section of Title 21 of the U.S. Code does the Egg Products Inspection Act begin?",
   "904", "small-business", ("900", "b-3"), "21 U.S.C. 1031 et seq.", ["1031"])
R2("defs-coverage", "Our small-business test refers to the businesses the rule applies to, and food in USDA-only facilities is left out. Which section of the chapter defines the food facilities meant there?",
   "904", "small-business", ("900", "b-3"), "§ 1.227", ["1.227"])
R2("defs-coverage", "The small-business definition points to the provision on who the rule applies to. Besides this rule in part 1 of 21 CFR, which other parts does that provision name as also applying to food transport?",
   "904", "small-business", ("900", "a"), "parts 117, 118, 225, 507, and 589", ["117", "118", "225", "507", "589"])
# from a duty to the vehicle requirements it names
R2("duty-vehicles", "Our trucking company's cleaning and inspection procedures must keep trailers sanitary as the vehicle requirements demand. Those requirements say unsuitable equipment makes food adulterated under paragraphs (a)(1), (2) and (4) of a section of the Food, Drug, and Cosmetic Act. Which section?",
   "908", "e-6-i", ("906", "a"), "section 402", ["402"])
# from a duty to the records rules: the definition behind the electronic-records exemption, and its exception
R2("duty-electronic", "We keep our driver sanitary-transport training records electronically, and they are exempt from the electronic-records rules. Which section of the chapter holds the definition of electronic records that exemption uses?",
   "910", "b", ("912", "h"), "§ 11.3(b)(6)", ["11.3"])
R2("duty-electronic", "Our trailer cleaning and inspection procedures are kept as electronic files. Which section of the chapter defines the electronic records that are exempted?",
   "908", "e-6", ("912", "h"), "§ 11.3(b)(6)", ["11.3"])
R2("duty-electronic", "The operating temperatures we give our carriers are logged electronically, and another agency's regulation also requires those logs. Which part of the chapter do they then remain subject to?",
   "908", "b-2", ("912", "h"), "they remain subject to part 11", ["11"])
# the written agreement (not the procedures) under which another party carries out a shipper's measures
R2("duty-agreement", "As a bulk shipper we signed a written agreement letting our tanker carrier carry out the measures against previous-cargo contamination. How long must we keep that agreement after it stops being in use?",
   "908", "b-4", ("912", "a-2"), "12 months beyond when the agreement is in use", ["12"])
R2("duty-agreement", "Our carrier keeps our chilled loads at temperature under a written agreement with us, the shipper. For how long after the agreement is no longer in use must we keep it?",
   "908", "b-5", ("912", "a-2"), "12 months beyond when the agreement is in use", ["12"])

# ---------------- three hops
add("defs-coverage-defs", "R3", 3, "We're a small food hauler. The small-business definition points to the businesses the rule covers, and that provision leaves the tiniest operators out entirely. Over how many years is revenue averaged to decide whether we are one of those left out?",
    walk("904", ("904", "small-business"), ("900", "a"), ("904", "non-covered-business")), "the 3-year period preceding the applicable calendar year", ["3"])
add("defs-coverage-defs", "R3", 3, "We both ship and haul food. The small-business definition points us to the businesses the rule covers, and that provision sends us back to the definitions. When payroll hours are turned into full-time equivalents there, how many hours a week does one full-time worker stand for?",
    walk("904", ("904", "small-business"), ("900", "a"), ("904", "text-2")), "40 hours a week", ["40"])
add("records-duty-vehicles", "R3", 3, "One kind of carrier procedure may never be archived offsite. Those procedures must keep vehicles sanitary as the vehicle requirements demand, and those requirements tie unsuitable equipment to adulteration under paragraphs (a)(1), (2) and (4) of a section of the Food, Drug, and Cosmetic Act. Which section?",
    walk("912", ("912", "i"), ("908", "e-6-i"), ("906", "a")), "section 402", ["402"])
add("defs-duty-records", "R3", 3, "We give carriers an operating temperature as the rule defines it, in writing, and keep those records electronically. They are exempt from the electronic-records rules: which section of the chapter defines the electronic records meant?",
    walk("904", ("904", "operating-temperature"), ("908", "b-2"), ("912", "h")), "§ 11.3(b)(6)", ["11.3"])

# ---------------- not in the library
none("What is the minimum liability insurance a for-hire motor carrier of general freight must carry?", "minimum liability insurance motor carrier")
none("How often must the temperature recorder on a reefer trailer be calibrated?", "reefer temperature recorder calibration")
none("Which class of commercial driver's license does a driver need to drive a refrigerated tractor-trailer?", "commercial driver's license class")
none("Below what declared value can an imported shipment enter duty-free under the customs de minimis rule?", "customs de minimis duty-free value")

for i, r in enumerate(rows):
    r["case_id"] = f"real3-{r['family']}-{i:02d}"
order = ["case_id", "world", "family", "block", "hops", "shelf", "question", "plan", "support", "answer", "check"]
with open("results/REAL3-real-corpus-20260930/questions.jsonl", "w") as f:
    for r in rows:
        r["world"] = "logistics-regs"
        f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")
from collections import Counter
print(len(rows), Counter(r["hops"] for r in rows))
