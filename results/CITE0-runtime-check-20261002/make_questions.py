"""Writes results/CITE0-runtime-check-20261002/questions.jsonl (run from the repo root).

A FRESH frozen set over the real library knowledge/spcc-regs (40 CFR Part 112, ingested eCFR text), written from the
library pages alone — no model answer, no walk, no run log and no earlier result section was read. Format, helpers and
token rules are REAL5's (results/REAL5-third-family-20261001/make_questions.py): every value row grades with
`check.cite = "support"` (the citation must BE the supporting statement), and every check token is a number that occurs
in that statement and in no statement the oracle walk opened before it. No question carries a digit or a section number.

Tokens: a value printed with a thousands comma ("1,000") or a dot ("112.12", "2.0") is checked as the string the
statement prints, ALONE in its row — the grader's hedge test splits it, so it never shares a row with a plain number.

AVOIDED: every supporting statement REAL5 used (AVOID below, asserted) and REAL5's none questions. Also avoided as
answers: the famous SPCC thresholds (1,320 gallons, 42,000 gallons, the 55-gallon floor). The three statements of the
animal-fat/vegetable-oil section that repeat the onshore section word for word (buried tank date, buried piping date,
permit records) are NOT asked: nothing in this library tells the two apart, so a strict citation would grade a coin.

SHARED STATEMENTS (honest limit): after the avoid-list, the library holds 40 distinct statements with a usable number;
44 value rows therefore reuse 4 statements, each time asking a DIFFERENT token — a one-hop row and a two-hop row on
112-2§discharge (1899 / 402), 112-3§b (2010 / 2011), 112-7§k-1 (42 / 1,000) and 112-20§ii-a-b (13 / 311(j)(4)).
Every two-hop and three-hop support is distinct from every other multi-hop support.
"""
import json
import re
from collections import Counter

P = "spcc-regs/wiki/"
LIB = "knowledge/spcc-regs/wiki/"
OUT = "results/CITE0-runtime-check-20261002/questions.jsonl"
# the start page's search query: its title, as REAL3/REAL5
Q = {"112-1": "general applicability", "112-2": "definitions", "112-3": "requirement to prepare and implement a plan",
     "112-4": "amendment of plan by regional administrator", "112-5": "amendment of plan by owners or operators",
     "112-6": "qualified facilities plan requirements", "112-7": "general requirements for plans",
     "112-8": "section 112.8 plan requirements for onshore facilities",
     "112-9": "section 112.9 plan requirements for onshore oil production facilities",
     "112-10": "section 112.10 plan requirements for onshore oil drilling and workover facilities",
     "112-11": "section 112.11 plan requirements for offshore oil drilling production or workover facilities",
     "112-12": "section 112.12 plan requirements", "112-20": "facility response plans",
     "112-21": "training and drills exercises"}

AVOID = {("112-1", a) for a in ("b", "c", "d-1-ii", "d-11", "d-2-ii", "d-4", "f-2", "f-5")} | {("112-12", "c-6-ii")} | \
        {("112-2", a) for a in ("farm", "navigable-waters")} | \
        {("112-20", a) for a in ("a-2-ii", "a-4-ii", "d", "g", "h-11-i", "h-3-2", "h-5-ii", "h-5-iii", "ii-a-b-d")} | \
        {("112-21", "c")} | {("112-3", a) for a in ("a", "a-2", "g-1", "g-2")} | \
        {("112-4", a) for a in ("a", "e", "f")} | {("112-5", "b")} | {("112-6", a) for a in ("viii-2", "viii-2-ii-2")} | \
        {("112-7", "d-1")} | {("112-8", a) for a in ("c-3-iv", "c-4", "d")}
REAL5_NONE = {"How much does our state charge each year to register an underground fuel storage tank?",
              "Which hazard placard and identification number must our diesel tank truck display on the highway?",
              "How many hours may a property-carrying truck driver drive after a full break off duty?",
              "What is the minimum width of an exit route in our warehouse?",
              "How often must the portable fire extinguishers in our warehouse be visually inspected?"}


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
R1("We run a marine fuel terminal next to a deepwater port. The rule's stated purpose reaches activities under the "
   "Deepwater Port Act of which year?",
   "112-1", "a", "the Deepwater Port Act of 1974", ["1974"])
R1("Our bulk plant's response plan was approved years ago and has not changed. A facility whose response plan was "
   "approved by what date need not prepare or submit a revised plan?",
   "112-20", "a-4-i", "by July 31, 2000", ["31", "2000"])
R1("Response plans for facilities like our tank farm were first required by the Oil Pollution Act. Which year's Act is "
   "it?",
   "112-20", "a-1", "the Oil Pollution Act of 1990", ["1990"])
R1("A plant manager asked me: a facility in operation on or after what date that meets the substantial-harm criteria "
   "must prepare and submit a facility response plan?",
   "112-20", "a-2", "on or after August 30, 1994", ["30", "1994"])
R1("An unplanned event just made our distribution terminal meet the substantial-harm criteria, so we have six months to "
   "submit a response plan. That six-month rule covers facilities that become subject after what date?",
   "112-20", "a-2-iv", "after August 30, 1994", ["30", "1994"])
R1("Our river terminal does not transfer oil over water to vessels. Under the other substantial-harm criterion, total "
   "oil storage capacity must be at least how many gallons?",
   "112-20", "ii-2", "1 million gallons", ["1"])
R1("Under the Tier I template, overfill prevention for our small fuel depot replaces the onshore section's overfill "
   "paragraph and which other section's paragraph?",
   "112-6", "viii-3-iii", "112.12(c)(8)", ["112.12"])
R1("Self-certifying our Tier I farm Plan, I must certify familiarity with the applicable requirements of which CFR title "
   "and part?",
   "112-6", "i", "40 CFR part 112", ["40", "112"])
R1("As a Tier II qualified warehouse we self-certify that our Plan does not deviate from any requirement as the "
   "environmental-equivalence paragraph allows, and as which other paragraph of the general requirements allows?",
   "112-6", "vii-2", "112.7(d)", ["112.7"])
R1("At our onshore workover yard secondary containment is not practicable. Among the containment provisions that "
   "determination can cover, which paragraph of the onshore drilling and workover section is listed?",
   "112-7", "d", "112.10(c)", ["112.10"])
R1("Some of our refinery's oily discharges are authorized by a permit under the Refuse Act provision of the River and "
   "Harbor Act. That Act is of which year?",
   "112-2", "discharge", "the River and Harbor Act of 1899", ["1899"])
R1("Our new oil production field has to file a facility response plan. If it becomes operational after what date must "
   "we prepare and implement a Plan within six months of starting operations?",
   "112-3", "b", "after November 10, 2010", ["10", "2010"])
R1("To use the alternate rules for our substation's oil-filled operational equipment, we can have had no two discharges "
   "within a twelve month period each exceeding how many gallons?",
   "112-7", "k-1", "42 U.S. gallons", ["42"])
R1("For the fish and wildlife guidance our tank farm's substantial-harm review relies on, which section of appendix E "
   "says where to get it?",
   "112-20", "ii-a-b", "appendix E, section 13", ["13"])

# ---------------- two hops: a statement's link must be followed to the page holding the value
R2 = lambda fam, q, start, an, target, a, t: add(fam, "R2", 2, q, walk(start, (start, an), target), a, t)
# → general applicability
R2("offshore-applicability", "On our offshore platform we route drains to a central sump so we never have a discharge "
   "as the general-applicability section describes it. That section exempts offshore drilling facilities under Minerals "
   "Management Service rules by a memorandum dated when?",
   "112-11", "b", ("112-1", "d-3"), "November 8, 1993", ["8", "1993"])
R2("drilling-applicability", "We position our mobile workover rigs so they cannot cause a discharge as the "
   "general-applicability section describes. That section lets the Regional Administrator require a Plan from a facility "
   "under EPA jurisdiction per which section of the Clean Water Act?",
   "112-10", "b", ("112-1", "f"), "section 311(j) of the Clean Water Act", ["311"])
R2("production-applicability", "My lease inspects its flow-through process vessels for conditions that could lead to a "
   "discharge as general applicability describes. That section excludes facilities outside EPA jurisdiction under which "
   "section of the Clean Water Act?",
   "112-9", "c-5-i", ("112-1", "d-1"), "section 311(j)(1)(C) of the Clean Water Act", ["311", "1"])
R2("ra-applicability", "After a spill at our depot we must report its cause, counting discharges as general "
   "applicability describes them. Under that section, after the window to send information and consult has closed, "
   "within how many days must the Regional Administrator decide whether we need a Plan?",
   "112-4", "a-7", ("112-1", "f-3"), "within 30 days", ["30"])
R2("onshore-applicability", "We watch our effluent treatment unit for upsets that could cause a discharge as the "
   "general-applicability section describes. That section's buried-capacity exemption leaves out tanks meeting all "
   "technical requirements of which part, or of a State program approved under which part?",
   "112-8", "c-9", ("112-1", "d-2-i"), "part 280, or a State program approved under part 281", ["280", "281"])
# general applicability → definitions
R2("applicability-defs", "Our coastal depot has a partially buried tank, which the rule defines in its definitions. The "
   "same definitions set out the contiguous zone; it is established under which article of the Convention on the "
   "Territorial Sea and Contiguous Zone?",
   "112-1", "b-4", ("112-2", "contiguous-zone"), "Article 24", ["24"])
R2("applicability-defs", "We fuel our yard tractors, whose tanks are motive power containers as the definitions define "
   "them. A complex, per those definitions, falls under more than one federal agency under which section of the Clean "
   "Water Act?",
   "112-1", "d-7", ("112-2", "complex"), "section 311(j) of the Clean Water Act", ["311"])
R2("applicability-defs", "Our forklifts' fuel tanks are left out of aggregate capacity as motive power containers, "
   "defined in the definitions. Those definitions take transportation-related from a memorandum of understanding dated "
   "when?",
   "112-1", "d-2-ii-b", ("112-2", "text-10"), "November 24, 1971", ["24", "1971"])
R2("applicability-defs", "Seasonal storage tanks at our grain farm count unless permanently closed as the definitions "
   "define it. Under those definitions, discharges complying with a permit under which section of the Clean Water Act "
   "are excluded?",
   "112-1", "b-3", ("112-2", "discharge"), "section 402 of the Clean Water Act", ["402"])
# definitions / RA amendment → preparing the Plan
R2("defs-prepare", "The definitions say the SPCC Plan is the document required by the plan-preparation section. For our "
   "onshore oil production facility, operational after what date must we prepare a Plan within six months of starting?",
   "112-2", "text-9", ("112-3", "b"), "after November 10, 2011", ["10", "2011"])
R2("ra-prepare", "We keep diesel on our cattle ranch, and the Regional Administrator's amendment section waits for the "
   "initial deadline in the plan-preparation section. For a farm already operating in the nineties, by what date must "
   "the amended Plan be implemented?",
   "112-4", "b", ("112-3", "a-3"), "on or before May 10, 2013", ["10", "2013"])
# → facility response plans
R2("general-frp", "Since our truck stop submitted a response plan, our SPCC Plan leaves out the discharge-reporting "
   "information. An existing facility that filed its response plan by the original deadline had to revise and resubmit "
   "it by what date?",
   "112-7", "a-4", ("112-20", "a-1-i"), "by February 18, 1995", ["18", "1995"])
R2("production-frp", "Our gathering lines lack secondary containment, but we submitted a response plan instead of a "
   "contingency plan. An existing facility that failed to submit its response plan by the original deadline had to "
   "submit it before what date?",
   "112-9", "d-3", ("112-20", "a-1-ii"), "before August 30, 1994", ["30", "1994"])
R2("defs-frp", "The definitions measure maximum extent practicable against the response plan our tank farm must meet. "
   "The Area Contingency Plans it refers to are prepared pursuant to which section of the Clean Water Act?",
   "112-2", "maximum-extent-practicable", ("112-20", "ii-a-b"), "section 311(j)(4) of the Clean Water Act",
   ["311", "4"])
R2("drills-frp", "We are building the response training program our facility response plan must describe. A newly "
   "constructed facility that starts operating after what date must prepare and submit its plan under the new-facility "
   "rule?",
   "112-21", "a", ("112-20", "a-4-iii"), "after July 31, 2000", ["31", "2000"])
R2("general-frp", "Dikes are not practicable at our lube oil plant, which already files a facility response plan. A "
   "facility that started up in late nineteen ninety-three had to submit its response plan and cover sheet prior to "
   "what date?",
   "112-7", "d", ("112-20", "a-2-i"), "prior to August 30, 1994", ["30", "1994"])
R2("general-frp", "Because of our response plan, our airport fuel farm's emergency procedures sit in that plan. When we "
   "submit an amended response plan, after what date must we also check it meets the current provisions?",
   "112-7", "a-5", ("112-20", "a-4-iv"), "after July 31, 2000", ["31", "2000"])
R2("general-frp", "Our oil-filled transformers have no secondary containment and we rely on our response plan for "
   "them. The response plan cover sheet is provided in which section of appendix F?",
   "112-7", "k-2-ii", ("112-20", "h-11"), "section 2.0 of appendix F", ["2.0"])
# → general requirements
R2("production-general", "Our crude oil lease meets the general Plan requirements. For oil-filled operational equipment "
   "to qualify, we can have had no single discharge from it exceeding how many gallons?",
   "112-9", "a", ("112-7", "k-1"), "1,000 U.S. gallons", ["1,000"])
R2("prepare-general", "We prepare our warehouse Plan in accordance with the general requirements. Without a response "
   "plan, oil-filled equipment lacking secondary containment needs a contingency plan following which part of the "
   "chapter?",
   "112-3", "text", ("112-7", "k-2-ii-a"), "part 109 of the chapter", ["109"])
R2("amend-general", "We are amending our drilling contractor's Plan per the general requirements. Deviations for "
   "equivalent protection cannot touch which paragraph of the onshore drilling and workover section?",
   "112-5", "a", ("112-7", "a-2"), "112.10(c)", ["112.10"])
# → onshore oil production
R2("qualified-production", "Our Tier II lease may not include skimming procedures for produced water containers "
   "without an engineer. If produced water containers have two spills within a twelve month period, each over how many "
   "gallons triggers full containment?",
   "112-6", "viii-3-iii-2", ("112-9", "c-6-v"), "more than 42 U.S. gallons each", ["42"])
R2("prepare-production", "The engineer certifying our Plan must address produced water containers under the "
   "production section. A single flow-through vessel discharge of more than how many gallons forces sized containment "
   "within six months?",
   "112-3", "d-1-vi", ("112-9", "c-5-iv"), "more than 1,000 U.S. gallons", ["1,000"])
R2("qualified-production", "An engineer must certify our produced water measures since we cannot self-certify them. "
   "For our flowlines without secondary containment, testing frequency must allow a contingency plan described under "
   "which part of the chapter?",
   "112-6", "viii-4-ii", ("112-9", "d-4-ii"), "part 109 of the chapter", ["109"])
# → qualified facilities
R2("amend-qualified", "Our technical amendments need an engineer unless the qualified-facilities section says "
   "otherwise. Tier I bulk storage containment there replaces the onshore section's paragraphs and which other "
   "section's paragraphs?",
   "112-5", "c", ("112-6", "viii-3-ii"), "112.12(c)(2) and (c)(11)", ["112.12"])
R2("prepare-qualified", "Our bulk plant meets the qualified-facility criteria and self-certifies as that section allows. "
   "A Tier I Plan must not deviate as the environmental-equivalence paragraph allows or as which other paragraph of the "
   "general requirements allows?",
   "112-3", "g", ("112-6", "vii"), "112.7(d)", ["112.7"])

# ---------------- three hops
R3 = lambda fam, q, start, an, mid, target, a, t: add(fam, "R3", 3, q, walk(start, (start, an), mid, target), a, t)
R3("onshore-general-frp", "Our onshore bulk plant meets the general Plan requirements, and for our oil-filled "
   "equipment we rely on our response plan. That plan's hazard evaluation must cover discharges reportable under which "
   "CFR title and part?",
   "112-8", "a", ("112-7", "k-2-ii"), ("112-20", "h-4"), "40 CFR part 110", ["40", "110"])
R3("drilling-general-frp", "Our drilling yard follows the general requirements, and our emergency procedures live in our "
   "response plan. After a planned change made us subject, start-up adjustments are due after a trial period of how "
   "many days?",
   "112-10", "a", ("112-7", "a-5"), ("112-20", "a-2-iii"), "after an operational trial period of 60 days", ["60"])
R3("vegoil-general-production", "We meet the general requirements, whose containment rule points to the production "
   "section for flowlines. Without a response plan, uncontained flowlines need a contingency plan following which part "
   "of the chapter?",
   "112-12", "a", ("112-7", "c"), ("112-9", "d-3-i"), "part 109 of the chapter", ["109"])
R3("offshore-general-applicability", "Our offshore platform follows the general requirements, and our facility diagram "
   "marks equipment exempt under general applicability. Equipment under Transportation or Interior control is exempt by "
   "a memorandum dated when?",
   "112-11", "a", ("112-7", "a-3"), ("112-1", "d-1-iii"), "November 8, 1993", ["8", "1993"])

# ---------------- not in the library: four adjacent (oil, fuel, spills, EPA outside Part 112), four unrelated
none("What reportable quantity of benzene released from our refinery triggers a call to the National Response Center?",
     "benzene reportable quantity release")
none("What words must be marked on the containers holding used oil at our truck repair shop?",
     "used oil container labeling")
none("Which vapor recovery equipment must our gasoline dispensing station install for tank truck deliveries?",
     "gasoline dispensing vapor recovery")
none("What is the sulfur limit for the marine fuel we bunker into ships in an emission control area?",
     "marine fuel sulfur limit emission control area")
none("How often must our warehouse forklift operators have their driving performance evaluated?",
     "forklift operator performance evaluation")
none("Within what temperature range must our cold-storage warehouse hold frozen food?",
     "frozen food storage temperature")
none("How long must our freight forwarding office keep copies of bills of lading?",
     "bill of lading retention")
none("What is the maximum load a standard wooden pallet in our distribution center may carry?",
     "pallet maximum load")

# ---------------- self-checks (the walk, the tokens, the questions)
_NUM = re.compile(r"\d+(?::\d+)?")


def statements(page):
    out = {}
    for line in open(LIB + page + ".md", encoding="utf-8"):
        if line.startswith("§"):
            an, txt = line.rstrip("\n").split(" ", 1)
            out[an[1:]] = txt
    return out


LINK = re.compile(r"\[\[spcc-regs/wiki/([^\]]+)\]\]")


def has(text, tok):
    plain = LINK.sub(" ", text)  # a link renders as an opaque id, not as its digits
    if _NUM.fullmatch(tok):
        return str(int(tok)) in {str(int(n)) for n in _NUM.findall(plain)}
    return tok.lower() in plain.lower()


for r in rows:
    q = r["question"]
    assert not re.search(r"\d", q), q
    if r["check"]["kind"] == "none":
        assert q not in REAL5_NONE
        continue
    opened = [(st[1][len(P):], st[2]) for st in r["plan"] if st[0] == "open" and len(st) == 3]
    assert len(opened) == r["hops"], q
    assert opened[0][0] == r["plan"][2][1][len(P):] and r["plan"][0][2] == Q[opened[0][0]]
    for (p0, a0), (p1, _) in zip(opened, opened[1:]):
        assert f"[[{P}{p1}]]" in statements(p0)[a0], (q, p0, a0, p1)
    sp, sa = opened[-1]
    assert (sp, sa) not in AVOID, (sp, sa)
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
multi = [tuple(r["support"]) for r in rows if r["hops"] >= 2]
assert len(set(multi)) == len(multi), "a multi-hop support repeats"

for i, r in enumerate(rows):
    r["case_id"] = f"cite0-{r['family']}-{i:02d}"
order = ["case_id", "world", "family", "block", "hops", "shelf", "question", "plan", "support", "answer", "check", "famous"]
with open(OUT, "w") as f:
    for r in rows:
        r["world"] = "spcc-regs"
        f.write(json.dumps({k: r[k] for k in order}, ensure_ascii=False) + "\n")
sup = Counter(tuple(r["support"]) for r in rows if r["support"])
print(len(rows), "rows · hops", dict(Counter(r["hops"] for r in rows)), "· shared supports",
      {f"{a}§{b}": n for (a, b), n in sup.items() if n > 1})
