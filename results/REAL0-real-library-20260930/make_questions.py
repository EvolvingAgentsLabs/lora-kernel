"""Writes results/REAL0-real-library-20260930/questions.jsonl (run from the repo root)."""
import json
P = "logistics-regs/wiki/"
Q = {"908": "requirements for transportation operations", "910": "training requirements for carriers",
     "912": "record retention", "900": "who is subject", "904": "what definitions apply", "178": "powered industrial trucks"}
PG = {"908": P + "1-908", "910": P + "1-910", "912": P + "1-912", "900": P + "1-900", "904": P + "1-904",
      "906": P + "1-906", "178": P + "1910-178"}

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
R1("When does a forklift count as unattended if the driver can still see it?", "178", "m-5-ii", "when the operator is 25 ft or more away", ["25"])
R1("How close to the center of a railroad track may a forklift be parked?", "178", "n-5", "no closer than 8 feet", ["8"])
R1("On a ramp steeper than what grade must a loaded forklift be driven with the load upgrade?", "178", "n-7-i", "grades in excess of 10 percent", ["10"])
R1("Below what level of general lighting must a forklift carry its own auxiliary directional lights?", "178", "h-2", "less than 2 lumens per square foot", ["2"])
R1("A lift truck has a water muffler. Below what share of its filled capacity must the water never be allowed to drop?", "178", "q-8", "75 percent of the filled capacity", ["75"])
R1("When cleaning our lift trucks, what flash point marks a solvent as too dangerous to use?", "178", "q-10", "below 100 °F (low flash point)", ["100"])
R1("Which ANSI standard sets the design and construction requirements that new powered industrial trucks must meet?", "178", "a-2", "ANSI B56.1-1969", ["B56.1"])
R1("How often must our lift trucks be examined for safety before being put into service?", "178", "q-7", "at least daily", ["daily"])
R1("To count full-time equivalent employees under the food transport rule, how many hours of work make up one year?", "904", "text-2", "2,080 hours", ["2,080"])
R1("Below how many full-time equivalent employees is a shipper or receiver a small business under the sanitary transportation rule?", "904", "small-business", "fewer than 500 full-time equivalent employees", ["500"])
R1("For a trucking company that is not also a shipper or receiver, what annual receipts make it a small business under the sanitary transportation rule?", "904", "small-business", "less than $27,500,000 in annual receipts", ["27,500,000"])

# ---------------- two hops: a statement's link must be followed to the page holding the value
R2 = lambda fam, q, start, an, target, a, t: add(fam, "R2", 2, q, walk(start, (start, an), target), a, t)
# into the records page, from the duty that creates the record
R2("duty-retention", "If we hand our sanitary-transport responsibilities to another company in a written agreement, how long after the agreement ends must we keep it?",
   "908", "a", ("912", "d"), "12 months beyond the termination of the agreement", ["12"])
R2("duty-retention", "Our shipping, loading and trucking arms all belong to one company and follow one common set of written procedures. How long must we keep those procedures after we stop using them?",
   "908", "a-5", ("912", "e"), "12 months beyond when the procedures are in use", ["12"])
R2("duty-retention", "We tell our carriers in writing how their trailers must be designed and cleaned. How long must we keep proof of that after the agreement with a carrier ends?",
   "908", "b", ("912", "a-1"), "12 months beyond the termination of the agreements with the carriers", ["12"])
R2("duty-retention", "We ship chilled food and give our carriers an operating temperature in writing. For how long after a carrier agreement ends must we keep those records?",
   "908", "b-2", ("912", "a-1"), "12 months beyond the termination of the agreements with the carriers", ["12"])
R2("duty-retention", "As a shipper we have written procedures to make sure the trucks we use are sanitary. How long must they be kept once we no longer use them?",
   "908", "b-3", ("912", "a-2"), "12 months beyond when the procedures are in use", ["12"])
R2("duty-retention", "We ship food in bulk tankers and keep written procedures so the previous load cannot contaminate it. How long must those procedures be retained after they go out of use?",
   "908", "b-4", ("912", "a-2"), "12 months beyond when the procedures are in use", ["12"])
R2("duty-retention", "We ship food that needs temperature control and have written procedures for keeping it cold in transit. How long must we keep them after we stop using them?",
   "908", "b-5", ("912", "a-2"), "12 months beyond when the procedures are in use", ["12"])
R2("duty-retention", "Our trucking company has written procedures for cleaning and inspecting the trailers we provide. How long after they stop being used must we keep them?",
   "908", "e-6", ("912", "b"), "12 months beyond when the procedures are in use", ["12"])
R2("duty-retention", "A driver we trained on sanitary transport quits. How long must we keep the record of that training?",
   "910", "b", ("912", "c"), "12 months beyond when the person stops performing those duties", ["12"])
# into the records page, to its other rules (offsite storage, electronic records, disclosure)
R2("duty-offsite", "Our shipper procedures for keeping chilled food at temperature are archived at head office. If the FDA asks for them, how quickly must we produce them on site?",
   "908", "b-5", ("912", "i"), "within 24 hours of the request", ["24"])
R2("duty-offsite", "Our shipper procedures for making sure the trucks we use are sanitary are archived offsite. How fast must they be brought on site for an official review?",
   "908", "b-3", ("912", "i"), "within 24 hours of the request", ["24"])
R2("duty-offsite", "We keep our carrier procedures for bulk tankers (previous cargo and last cleaning) in an offsite archive. Within how many hours must they be retrievable on site when inspectors ask?",
   "908", "e-6", ("912", "i"), "within 24 hours of the request", ["24"])
R2("duty-offsite", "Can our driver sanitary-transport training records sit in an offsite archive, and if so, how fast must we produce them on site?",
   "910", "b", ("912", "i"), "yes, if they can be provided onsite within 24 hours of request", ["24"])
R2("duty-offsite", "The written agreements in which we reassigned our sanitary-transport duties to another party are in offsite storage. How quickly must we be able to produce them on site?",
   "908", "a", ("912", "i"), "within 24 hours of the request", ["24"])
R2("duty-electronic", "We keep our carrier training records electronically. Which part of the chapter's electronic-records rules are they exempt from?",
   "910", "b", ("912", "h"), "exempt from part 11", ["11"])
R2("duty-electronic", "The operating temperatures we send carriers are stored as electronic records. Which part of the chapter are those records exempt from?",
   "908", "b-2", ("912", "h"), "exempt from part 11", ["11"])
R2("duty-electronic", "Our carrier's cleaning and inspection procedures are kept electronically. Are they subject to the part on electronic records, and which part is it?",
   "908", "e-6", ("912", "h"), "exempt from part 11", ["11"])
R2("duty-disclosure", "Could the written agreement in which we reassigned our sanitary-transport duties be disclosed to the public? Under which part of the chapter?",
   "908", "a", ("912", "j"), "subject to the disclosure requirements of part 20", ["20"])
R2("duty-disclosure", "Our single-company common transport procedures are records under this rule. Which part of the chapter governs whether they can be publicly disclosed?",
   "908", "a-5", ("912", "j"), "the disclosure requirements under part 20", ["20"])
# from the records page to the duty it names
R2("record-duty", "One kind of carrier procedure may not be stored offsite at all. What do those procedures cover?",
   "912", "i", ("908", "e-6-i"), "cleaning, sanitizing if necessary, and inspecting vehicles and transportation equipment", ["cleaning"])
R2("record-duty", "Carriers keep training records for 12 months after the trainee stops those duties. What must each training record show?",
   "912", "c", ("910", "b"), "the date of the training, the type of training, and the person(s) trained", ["date", "type"])
# from who is covered to the definition that excludes
R2("coverage", "Very small food businesses are left out of the sanitary transportation rule. Below what average annual revenue is a business not covered?",
   "900", "a", ("904", "non-covered-business"), "less than $500,000, adjusted for inflation", ["$500,000"])
R2("coverage", "The revenue cutoff that leaves small businesses out of the sanitary transport rule is adjusted for inflation. What is the baseline year for that adjustment?",
   "900", "a", ("904", "non-covered-business"), "2011", ["2011"])
R2("duty-offsite", "Our written procedures as a bulk shipper, meant to stop a previous cargo from contaminating the food, are archived offsite. Within how many hours must they be produced on site when the FDA asks?",
   "908", "b-4", ("912", "i"), "within 24 hours of the request", ["24"])

# ---------------- three hops
add("coverage", "R3", 3, "We only haul food by truck. Our small-business test points to the businesses this rule covers, and that rule leaves the smallest ones out entirely. The revenue cutoff that leaves the smallest ones out is adjusted for inflation from which baseline year?",
    walk("904", ("904", "small-business"), ("900", "a"), ("904", "non-covered-business")), "2011", ["2011"])

# ---------------- not in the library
none("How many hours may a truck driver drive before a mandatory rest break?", "truck driver hours of service rest break")
none("At what temperature must frozen food be held during transport?", "frozen food transport temperature")
none("How often must the fire extinguishers in our warehouse be inspected?", "fire extinguisher inspection")
none("What is the maximum gross weight allowed for a tractor-trailer on the interstate?", "maximum gross vehicle weight")

for i, r in enumerate(rows):
    r["case_id"] = f"real0-{r['family']}-{i:02d}"
order = ["case_id", "world", "family", "block", "hops", "shelf", "question", "plan", "support", "answer", "check"]
with open("results/REAL0-real-library-20260930/questions.jsonl", "w") as f:
    for r in rows:
        r["world"] = "logistics-regs"
        f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")
from collections import Counter
print(len(rows), Counter(r["hops"] for r in rows))
