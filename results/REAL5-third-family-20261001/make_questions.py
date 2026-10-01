"""Writes results/REAL5-third-family-20261001/questions.jsonl (run from the repo root).

A FRESH frozen set over a THIRD real library, knowledge/spcc-regs (40 CFR Part 112, EPA's oil spill prevention rule,
ingested verbatim), written from the pages alone — no model answer, no training row, no earlier result was read.
Same row format as REAL3; every value row grades with `check.cite = "support"` (the citation must BE the supporting
statement), and every check token is a number that occurs in that statement and in no statement the oracle walk opened
before it. No question carries a digit.

Tokens: a value printed with a thousands comma ("2,100") is checked as the string the statement prints, ALONE in its
row — the grader's hedge test splits "2,100" into 2 and 100, so a comma value never shares a row with a plain number.

FAMOUS: the three SPCC thresholds a 4B may hold in its weights (1,320 gallons aggregate aboveground, 42,000 gallons
completely buried, the 55-gallon container floor). One row asks one of them; it is marked `famous: true` and is not in
the headline (it is one hop). Every other value is a date, a section, a part, a day count or a gallon figure that is
not one of the three.
"""
import json

P = "spcc-regs/wiki/"
# the start page's search query: its title, as REAL3 — Lexical ranks the page first (checked by the validator)
Q = {"112-1": "general applicability", "112-2": "definitions", "112-3": "requirement to prepare and implement a plan",
     "112-4": "amendment of plan by regional administrator", "112-5": "amendment of plan by owners or operators",
     "112-6": "qualified facilities plan requirements", "112-7": "general requirements for plans",
     "112-8": "section 112.8 plan requirements for onshore facilities",
     "112-12": "section 112.12 plan requirements", "112-20": "facility response plans",
     "112-21": "training and drills exercises"}


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
R1("We run a trucking terminal and fuel our own tank trucks. The rule leaves transportation-related facilities to DOT as "
   "drawn in a memorandum of understanding between the Secretary of Transportation and the EPA Administrator alone. "
   "What is that memorandum's date?",
   "112-1", "d-1-ii", "November 24, 1971", ["24", "1971"])
R1("EPA's regional office made a final determination that our otherwise-exempt warehouse must prepare an SPCC Plan, and "
   "we appealed to the EPA Administrator. Within how many days of receiving the appeal must the Administrator decide?",
   "112-1", "f-5", "within 60 days of receiving the appeal", ["60"])
R1("The Regional Administrator sent us written notice that our small fuel yard must prepare an SPCC Plan although we "
   "thought we were exempt. How many days after receiving it do we have to send information and consult with EPA?",
   "112-1", "f-2", "within 30 days of receipt of the notice", ["30"])
R1("Our warehouse keeps a few drums and one small diesel tank above ground. At or below what aggregate aboveground oil "
   "storage capacity is a facility exempt from the SPCC rule?",
   "112-1", "d-2-ii", "1,320 U.S. gallons", ["1,320"], famous=True)
R1("Our fuel depot is run by a federal agency. Under which section of the Clean Water Act are federal departments "
   "subject to the SPCC rule to the same extent as any person?",
   "112-1", "c", "section 313 of the Clean Water Act", ["313"])
R1("The spill rule keeps referring to the navigable waters near our terminal. Which section of the chapter does its "
   "definition of navigable waters point to?",
   "112-2", "navigable-waters", "§ 120.2 of the chapter", ["120.2"])
R1("The Regional Administrator sent us, by certified mail, a proposed amendment to our terminal's SPCC Plan. How many "
   "days from receipt do we have to submit written information, views and arguments on it?",
   "112-4", "e", "within 30 days from receipt of the notice", ["30"])
R1("Our warehouse fuel tanks have been in service since the nineties. For a facility in operation on or before what date "
   "does the five-year Plan review run from the date the last review was required?",
   "112-5", "b", "August 16, 2002", ["16", "2002"])
R1("We store vegetable oil in elevated, shop-built austenitic stainless steel tanks with no external insulation, which "
   "may get formal visual inspection instead of integrity testing. Which FDA regulation must those tanks be subject to "
   "(title and part of the CFR)?",
   "112-12", "c-6-ii", "21 CFR part 110", ["21", "110"])
R1("We are building a new fuel terminal that must submit a facility response plan before it starts operating. Changes "
   "made during start-up go to the Regional Administrator after an operational trial period of how many days?",
   "112-20", "a-2-ii", "after an operational trial period of 60 days", ["60"])

# ---------------- two hops: a statement's link must be followed to the page holding the value
R2 = lambda fam, q, start, an, target, a, t: add(fam, "R2", 2, q, walk(start, (start, an), target), a, t)
# general requirements → facility response plans (the "unless you have submitted a response plan" statements)
R2("general-frp", "Our trucking terminal's SPCC Plan skips the discharge-reporting procedures because we submitted a "
   "facility response plan instead. That response plan needs a planning scenario for a small discharge: up to how many "
   "gallons?",
   "112-7", "a-4", ("112-20", "h-5-ii"), "a discharge of 2,100 gallons or less", ["2,100"])
R2("general-frp", "We put no secondary containment around the transformers and hydraulic systems in our warehouse, and for "
   "them we rely on our facility response plan instead of a separate contingency plan. That response plan's medium "
   "discharge scenario tops out at how many gallons, unless a share of the largest tank is smaller?",
   "112-7", "k-2-ii", ("112-20", "h-5-iii"), "up to 36,000 gallons, or ten percent of the largest tank if that is less",
   ["36,000"])
R2("general-frp", "Dikes around our bulk tanks are not practicable, so we planned to rely on a facility response plan "
   "rather than a contingency plan. A facility with very large storage must file such a plan if its reportable spill "
   "history includes a discharge of at least how many gallons within the last five years?",
   "112-7", "d", ("112-20", "ii-a-b-d"), "a reportable discharge of 10,000 gallons or more within the last five years",
   ["10,000"])
# training and drills ↔ facility response plans
R2("drills-frp", "We are setting up the response training and drill program that must be described in our facility "
   "response plan. If we disagree with the Regional Administrator's determination about that response plan, how many "
   "days after his notice do we have to request reconsideration?",
   "112-21", "a", ("112-20", "h-11-i"), "within 60 days of receipt of the notice", ["60"])
R2("frp-drills", "Our facility response plan must describe our drill and exercise program as the training-and-drills "
   "section lays it out. A program following the national PREP is deemed satisfactory; which section of appendix E "
   "says where to get it?",
   "112-20", "h-8-ii", ("112-21", "c"), "appendix E, section 13", ["13"])
# definitions → facility response plans
R2("defs-frp", "The definitions measure the maximum extent practicable against the response plan our tank farm must meet. "
   "If we change the type of oil we store in a way that alters the response resources needed, within how many days "
   "must we resubmit the revised portions of that response plan?",
   "112-2", "maximum-extent-practicable", ("112-20", "d"), "within 60 days of the change", ["60"])
# general requirements → amendment by the Regional Administrator / onshore requirements
R2("general-ra", "Our Plan uses alternative methods in place of some requirements, and the Regional Administrator may "
   "make us amend it under his amendment procedures. If we appeal his decision requiring the amendment, within how many "
   "days of the notice must the appeal go to the EPA Administrator?",
   "112-7", "a-2", ("112-4", "f"), "in writing within 30 days of receipt of the notice", ["30"])
R2("general-onshore", "Our Plan may not deviate from the onshore section's secondary containment rules. When we drain "
   "rainwater from a diked area past the treatment system, the event records may be those required by permits under "
   "which section of the chapter?",
   "112-7", "a-2", ("112-8", "c-3-iv"), "permits issued under § 122.41 of the chapter", ["122.41"])
R2("onshore-general", "Our onshore warehouse must meet the general Plan requirements. If dikes around our tanks are "
   "impracticable and we have no response plan, our oil spill contingency plan must follow which part of the chapter?",
   "112-8", "a", ("112-7", "d-1"), "part 109 of the chapter", ["109"])
# preparing the Plan ↔ definitions
R2("prepare-defs", "We keep diesel for our trucks on land where we also raise cattle, so the farm deadline for the Plan may "
   "apply to us. To count as a farm, the land must have produced and sold agricultural products worth at least how "
   "much in a year?",
   "112-3", "a-3", ("112-2", "farm"), "$1,000 or more", ["1,000"])
R2("defs-prepare", "The definitions say the SPCC Plan is the document required by the section on preparing it. Our "
   "onshore terminal must also file a facility response plan and has operated since the nineties. By what date did we "
   "have to amend and implement our Plan?",
   "112-2", "text-9", ("112-3", "a-2"), "no later than November 10, 2010", ["10", "2010"])
# amendments / qualified facilities → preparing the Plan
R2("ra-prepare", "The section on amendments the Regional Administrator can require after spills does not apply to us "
   "until our initial Plan deadline has passed. We are an onshore warehouse (not a farm, no offshore part, no response "
   "plan) that opened after the rule's original cutoff but before its later compliance deadline. By what date did we "
   "have to prepare and implement our Plan?",
   "112-4", "b", ("112-3", "a"), "on or before November 10, 2011", ["10", "2011"])
R2("qualified-prepare", "To complete the Tier I template we certify that our facility meets the Tier I qualification "
   "criteria. Under those criteria, no individual aboveground container may be larger than what capacity?",
   "112-6", "vi", ("112-3", "g-1"), "5,000 U.S. gallons", ["5,000"])
R2("qualified-prepare", "The qualified-facilities section sends Tier II facilities to the Tier II criteria. To qualify, a "
   "facility must not have had a single discharge larger than how many gallons in the three years before "
   "self-certification?",
   "112-6", "text", ("112-3", "g-2"), "1,000 U.S. gallons", ["1,000"])
# preparing / amending the Plan → qualified facilities
R2("prepare-qualified", "A Professional Engineer must certify our Plan unless the qualified-facilities section lets us "
   "self-certify. As a self-certified Tier II facility, above what aggregate aboveground capacity must we switch to an "
   "engineer-certified Plan?",
   "112-3", "d", ("112-6", "viii-2-ii-2"), "more than 10,000 U.S. gallons", ["10,000"])
R2("amend-qualified", "We are amending our self-certified Plan for a technical change, and the amendment rule sends "
   "qualified facilities to their own section instead of a Professional Engineer. We are Tier I: installing a container "
   "larger than what capacity takes us out of Tier I?",
   "112-5", "c", ("112-6", "viii-2"), "5,000 U.S. gallons", ["5,000"])
# qualified facilities → onshore requirements
R2("qualified-onshore", "As a Tier I warehouse our overfill rule stands in for the one in the onshore-facility section. "
   "That onshore section requires corrosion protection for completely buried metallic tanks installed on or after "
   "what date?",
   "112-6", "viii-3-iii", ("112-8", "c-4"), "January 10, 1974", ["10", "1974"])
R2("qualified-onshore", "Our Tier I containment rule replaces the bulk-storage containment paragraphs of the onshore-facility "
   "section. In that onshore section, buried piping installed or replaced on or after what date needs a protective "
   "wrapping and coating?",
   "112-6", "viii-3-ii", ("112-8", "d"), "August 16, 2002", ["16", "2002"])
# amendment by the Regional Administrator → general applicability
R2("ra-applicability", "After two spills within a year at our terminal we must report to the Regional Administrator, "
   "counting only discharges as described in the general-applicability section. Harmful quantities there are as "
   "described in which part of the chapter?",
   "112-4", "a", ("112-1", "b"), "part 110 of the chapter", ["110"])

# ---------------- three hops
R3 = lambda fam, q, start, an, mid, target, a, t: add(fam, "R3", 3, q, walk(start, (start, an), mid, target), a, t)
R3("onshore-general-frp", "Our onshore warehouse must meet the general Plan requirements, and its discharge-reporting "
   "procedures are covered by the facility response plan we submitted instead. If the Regional Administrator denies our "
   "request to reconsider a decision about that response plan, within how many days must we appeal to the EPA "
   "Administrator?",
   "112-8", "a", ("112-7", "a-4"), ("112-20", "h-3-2"), "in writing within 60 days of receipt of the denial", ["60"])
R3("vegoil-general-frp", "We store vegetable oil in bulk and must meet the general Plan requirements, with our emergency "
   "procedures handled by our facility response plan. For animal fat and vegetable oil facilities whose submitted but "
   "unapproved response plan fell short of the revised rules, by what date was a new plan due?",
   "112-12", "a", ("112-7", "a-5"), ("112-20", "a-4-ii"), "by September 28, 2000", ["28", "2000"])
R3("prepare-general-frp", "Our Plan follows the general requirements, and since dikes are not practicable around our "
   "tanks we rely on our facility response plan. That response plan should be coordinated with the local emergency plan "
   "developed under which section of Title III of the Superfund Amendments and Reauthorization Act?",
   "112-3", "text", ("112-7", "d"), ("112-20", "g"), "section 303", ["303"])
R3("qualified-general-ra", "Our Tier I Plan follows the general Plan requirements, and EPA can make us amend it under the "
   "Regional Administrator's amendment procedures. Once a large spill makes that section apply, within how many days "
   "must we send the Regional Administrator our facility information?",
   "112-6", "a", ("112-7", "a-2"), ("112-4", "a"), "within 60 days", ["60"])
R3("amend-general-applicability", "We are amending our Plan under the general requirements, and our facility diagram must "
   "mark our underground diesel tank as exempt. That tank is exempt when it meets all the technical requirements of "
   "which part of the chapter, or of a State program approved under which part?",
   "112-5", "a", ("112-7", "a-3"), ("112-1", "d-4"), "part 280, or a State program approved under part 281",
   ["280", "281"])
R3("prepare-general-applicability", "Our Plan follows the general requirements, and our facility diagram has to show "
   "certain pipelines marked as exempt. Intra-facility gathering lines are exempt when subject to which DOT pipeline "
   "regulations (CFR title and parts)?",
   "112-3", "text", ("112-7", "a-3"), ("112-1", "d-11"), "49 CFR part 192 or 195", ["49", "192", "195"])

# ---------------- not in the library: two adjacent (oil and fuel, outside Part 112), three unrelated
none("How much does our state charge each year to register an underground fuel storage tank?",
     "state underground storage tank registration fee")
none("Which hazard placard and identification number must our diesel tank truck display on the highway?",
     "tank truck placard diesel hazardous materials")
none("How many hours may a property-carrying truck driver drive after a full break off duty?", "truck driver hours of service")
none("What is the minimum width of an exit route in our warehouse?", "warehouse exit route width")
none("How often must the portable fire extinguishers in our warehouse be visually inspected?",
     "portable fire extinguisher inspection")

for i, r in enumerate(rows):
    r["case_id"] = f"real5-{r['family']}-{i:02d}"
order = ["case_id", "world", "family", "block", "hops", "shelf", "question", "plan", "support", "answer", "check", "famous"]
with open("results/REAL5-third-family-20261001/questions.jsonl", "w") as f:
    for r in rows:
        r["world"] = "spcc-regs"
        f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")
from collections import Counter
print(len(rows), Counter(r["hops"] for r in rows))
