"""Build `knowledge/nursing-iv/` — the first library of the memory (docs/MEMORY.md §10, W1).

    python3 -m training.nursing.library            # write the library
    python3 -m training.nursing.library --check    # exit 1 if the files on disk have drifted
    python3 -m training.nursing.library --gate [out.json]   # W1's gate

WHAT COMES FROM WHERE. Every step's BODY is the Open RN checklist line from `source.py`, unchanged
except that the quantities a site may adapt become `{{slots}}` (§1.4) — so the order of steps and
the wording are the source's, CC BY 4.0, attributed in every note. What is written HERE, and is
therefore this repository's and not Open RN's: the titles, the `when:` / `what:` lines the radar
will index, the typed links, and the small wiki shelf. The wiki restates what the checklists
already say and adds two arithmetic identities; it is a student's index card, not clinical
guidance. **Nothing here advises a patient.**

LINKS. `next` is the checklist's order. `requires` is the step before — the conformance guard of
W2 then refuses a skipped step — plus the named guards in `GUARDS`, which are the ones a ward
would actually audit (the cap is cleansed before anything is attached to it).

WHY A BUILDER AND NOT SEVENTY HAND-EDITED FILES. The files are the artifact and are committed;
this module is what makes them reproducible, and `tests/test_memory_library.py` asserts the two
agree. Edit a note by editing the table below and rebuilding.
"""

from __future__ import annotations

import sys
from pathlib import Path

from memory.notes import Note
from training.nursing.source import ATTRIBUTION, CHECKLISTS

SUB = "nursing-iv"
ROOT = Path("knowledge") / SUB
SOURCE = "Nursing Skills (Open RN), ch. 23 IV Therapy Management, NBK596734 — CC BY 4.0"
OWN = "lora-kernel, restating Open RN ch. 23 (CC BY 4.0) — a study card, not clinical guidance"

W = f"{SUB}/wiki"

# slug, title, when, what, uses (wiki ids, relative to the wiki shelf)
PROCEDURES = {
    "primary-infusion": {
        "checklist": "primary IV solution administration",
        "title": "Administer a primary IV solution",
        "when": "A provider has ordered continuous IV fluids and the patient already has an IV site.",
        "what": "The ordered steps for hanging and starting a primary IV solution.",
        "steps": [
            ("gather-supplies", "Gather supplies for a primary infusion", "You are about to start a primary IV infusion and have nothing in hand yet.", "The supplies a primary IV infusion needs.", []),
            ("verify-order", "Verify the provider order", "You have the primary infusion supplies and have not yet checked the order.", "Matching the provider order against the medication administration record.", ["medication-safety"]),
            ("first-check", "First check of the six rights", "You are withdrawing primary IV fluids from the dispensing unit.", "The first of three medication checks, with expiration date and allergies.", ["medication-safety/six-rights", "medication-safety/three-checks"]),
            ("inspect-bag", "Inspect the IV bag for leaks", "You have taken a primary IV solution out of its packaging.", "Checking an IV bag for tears or leaks under gentle pressure.", []),
            ("check-solution", "Check color and clarity", "The primary IV bag is intact and you have not looked at the fluid itself.", "Visual inspection of an IV solution.", []),
            ("second-check", "Second check of the six rights", "The primary IV solution has been inspected and you are still outside the patient room.", "The second of three medication checks.", ["medication-safety/three-checks"]),
            ("enter-room", "Enter the room and greet the patient", "A primary IV solution has passed two checks and you are at the patient's door.", "Entering and greeting before a primary infusion.", []),
            ("safety-steps", "Safety steps and patient identification", "You have greeted a patient who is to receive a primary infusion.", "Hand hygiene and two patient identifiers before a primary infusion.", ["asepsis/hand-hygiene", "medication-safety/two-identifiers"]),
            ("third-check", "Third check at the bedside", "The patient receiving a primary infusion has been identified.", "The third medication check, done at the bedside.", ["medication-safety/three-checks"]),
            ("unpack-tubing", "Unpack primary tubing and note the drip factor", "You are at the bedside with primary IV tubing still in its package.", "Reading the drip factor off the tubing package for a gravity infusion.", ["rates/gravity-drip-rate", "rates/drop-factor"]),
            ("clamp-roller", "Clamp the roller clamp", "Primary tubing is out of its package and unclamped.", "Positioning and closing the roller clamp before spiking a bag.", []),
            ("uncover-port", "Uncover the bag's tubing port", "Primary tubing is clamped and the bag's port is still covered.", "Removing the cover from an IV bag's tubing port.", []),
            ("spike-bag", "Spike the bag", "The primary bag's port is uncovered and the tubing spike is capped.", "Inserting the tubing spike into the IV bag while maintaining sterility.", ["asepsis"]),
            ("fill-drip-chamber", "Fill the drip chamber", "The primary bag is spiked and the drip chamber is empty.", "Squeezing the drip chamber to fill it halfway.", ["priming"]),
            ("prime-tubing", "Prime the primary tubing", "The drip chamber of the primary tubing is half full and the line is full of air.", "Priming primary IV tubing over the sink.", ["priming"]),
            ("check-air", "Check the tubing for air", "Primary tubing has just been primed.", "Clamping and inspecting the whole length of tubing for air bubbles.", ["priming/air-in-line"]),
            ("cap-tubing", "Replace the tubing cap", "Primed primary tubing is free of air and its end is loose.", "Keeping the end of primed tubing capped and sterile.", ["asepsis"]),
            ("label", "Label the bag and the tubing", "A primary bag and tubing are primed and unlabeled.", "Dating the bag and placing the tubing change label.", []),
            ("assess-site-before", "Assess the venipuncture site before connecting", "A primed, labeled primary infusion is ready and the patient's IV site has not been looked at.", "Looking for vein irritation or infiltration before fluids are connected.", ["site-assessment/infiltration-and-irritation"]),
            ("cleanse-cap", "Cleanse the catheter cap before the flush", "You are about to attach a saline syringe to the patient's IV port.", "Disinfection of the IV port's cap with an alcohol pad or scrub hub.", ["asepsis/scrub-the-hub"]),
            ("assess-patency", "Assess patency with a saline flush", "The catheter cap is clean and dry and you hold a prefilled saline syringe.", "The turbulent stop-start saline flush that shows an IV site is patent.", ["site-assessment/patency-flush"]),
            ("remove-syringe", "Remove the syringe and clamp", "The saline flush went in without resistance.", "Removing the flush syringe and clamping the extension tubing.", []),
            ("cleanse-cap-again", "Cleanse the catheter cap before the tubing", "The flush syringe is off and you are about to connect primary tubing to the IV port.", "A second disinfection of the IV port's cap, before tubing is attached.", ["asepsis/scrub-the-hub"]),
            ("attach-tubing", "Attach the primary tubing", "The catheter cap has been cleansed a second time and is dry.", "Connecting primary tubing to the IV port while maintaining sterility.", ["asepsis"]),
            ("open-slide-clamp", "Open the saline lock's slide clamp", "Primary tubing is attached and the saline lock is still clamped.", "Opening the slide clamp on the saline lock.", []),
            ("set-rate", "Set the primary infusion rate", "Primary tubing is connected and open and no rate is set.", "Setting a pump in mL/hr or a gravity line in drops per minute, per the order.", ["rates/gravity-drip-rate", "rates/pump-rate"]),
            ("assess-site-after", "Assess the site once the primary infusion runs", "A primary infusion has just started flowing.", "Rechecking the IV site for irritation or infiltration after flow begins.", ["site-assessment/infiltration-and-irritation"]),
            ("secure-tubing", "Secure the tubing", "A primary infusion is running and the tubing hangs free.", "Securing IV tubing to the patient's arm.", []),
            ("comfort", "Comfort and questions", "A primary infusion is running and secured.", "Positioning the patient and inviting questions after starting a primary infusion.", []),
            ("leave-safely", "Safety measures on leaving", "You are about to leave a patient on a primary infusion.", "Call light, bed low and locked, rails, table, fall risks — after a primary infusion.", []),
            ("hand-hygiene", "Hand hygiene", "You have left the bedside of a patient on a primary infusion.", "Hand hygiene that closes the primary infusion procedure.", ["asepsis/hand-hygiene"]),
            ("document", "Document the primary infusion", "A primary infusion is running and nothing is charted yet.", "Charting the procedure, the assessment and the fluids as intake.", []),
        ],
        "guards": {"attach-tubing": ["cleanse-cap-again"], "assess-patency": ["cleanse-cap"],
                   "set-rate": ["verify-order"], "third-check": ["safety-steps"]},
        "slots": {"cleanse-cap": {"at least five seconds": ("seconds", 5)},
                  "cleanse-cap-again": {"at least five seconds": ("seconds", 5)},
                  "assess-patency": {"3 to 5 mL": ("flush_ml", "3 to 5")}},
    },
    "secondary-infusion": {
        "checklist": "secondary IV solution administration",
        "title": "Administer a secondary IV solution",
        "when": "A provider has ordered an intermittent IV medication for a patient with a primary line running.",
        "what": "The ordered steps for hanging a secondary (piggyback) IV solution.",
        "steps": [
            ("gather-supplies", "Gather supplies for a secondary infusion", "You are about to hang a secondary IV medication and have nothing in hand yet.", "The supplies a secondary IV infusion needs.", []),
            ("verify-order", "Verify the order for the secondary medication", "You have the secondary infusion supplies and have not yet checked the order.", "Matching the secondary medication order against the administration record.", ["medication-safety"]),
            ("first-check", "First check for the secondary medication", "You are withdrawing a secondary IV medication and tubing from the dispensing unit.", "The first of three checks for a secondary medication, with expiration and allergies.", ["medication-safety/six-rights", "medication-safety/three-checks"]),
            ("verify-compatibility", "Verify compatibility with running fluids", "A secondary medication has passed its first check and the patient has other IV fluids running.", "Compatibility of a secondary solution with the fluids already infusing.", ["medication-safety/compatibility"]),
            ("inspect-bag", "Inspect the secondary bag and solution", "You have taken a secondary IV solution out of its packaging.", "Leaks, color and clarity of a secondary solution.", []),
            ("second-check", "Second check for the secondary medication", "The secondary solution has been inspected and you are still outside the patient room.", "The second of three checks for a secondary medication.", ["medication-safety/three-checks"]),
            ("enter-room", "Enter the room and greet the patient", "A secondary medication has passed two checks and you are at the patient's door.", "Entering and greeting before a secondary infusion.", []),
            ("safety-steps", "Safety steps and patient identification", "You have greeted a patient who is to receive a secondary medication.", "Hand hygiene and two patient identifiers before a secondary infusion.", ["asepsis/hand-hygiene", "medication-safety/two-identifiers"]),
            ("third-check", "Third check at the bedside", "The patient receiving a secondary medication has been identified.", "The third check for a secondary medication, at the bedside.", ["medication-safety/three-checks"]),
            ("teach-first-dose", "Teach about a first dose", "The patient is receiving this IV medication for the first time.", "Teaching patient and family about adverse reactions before a first dose.", []),
            ("unpack-tubing", "Unpack the secondary tubing", "You are at the bedside with secondary tubing still in its package.", "Removing secondary IV tubing from its packaging.", []),
            ("clamp-roller", "Close the secondary roller clamp", "Secondary tubing is out of its package and unclamped.", "Setting the secondary roller clamp to off before spiking.", []),
            ("uncover-spike-and-port", "Uncover the spike and the port", "Secondary tubing is clamped and both the spike and the bag's port are covered.", "Removing the spike's sheath and the port's cover on a secondary set.", []),
            ("spike-bag", "Spike the secondary bag", "The secondary spike and port are uncovered.", "Spiking a secondary bag while maintaining sterility.", ["asepsis"]),
            ("fill-drip-chamber", "Fill the secondary drip chamber", "The secondary bag is spiked and its drip chamber is empty.", "Compressing and releasing the secondary drip chamber to fill it halfway.", ["priming"]),
            ("back-prime", "Back prime the secondary tubing", "The secondary drip chamber is half full and the secondary line is full of air.", "Priming secondary tubing from the primary line through the upper y-port.", ["priming/back-priming", "asepsis/scrub-the-hub"]),
            ("hang-bags", "Hang the secondary above the primary", "Secondary tubing is primed and the bag is not yet on the pole.", "Relative height of primary and secondary bags on the pole.", ["priming/back-priming"]),
            ("label", "Label the secondary tubing", "A secondary bag hangs primed and its tubing is unlabeled.", "Labeling secondary tubing near the drip chamber.", []),
            ("set-rate", "Set the secondary infusion rate", "A secondary medication hangs primed and labeled and no rate is set.", "Setting a secondary rate on a pump in mL/hr or by roller clamp in drops per minute.", ["rates/pump-rate", "rates/gravity-drip-rate"]),
            ("assess-site-after", "Assess the site once the secondary infusion runs", "A secondary infusion has just started flowing.", "Checking the IV site for irritation or infiltration after a secondary infusion begins.", ["site-assessment/infiltration-and-irritation"]),
            ("comfort", "Comfort and questions", "A secondary infusion is running.", "Positioning the patient and inviting questions after starting a secondary infusion.", []),
            ("leave-safely", "Safety measures on leaving", "You are about to leave a patient on a secondary infusion.", "Call light, bed low and locked, rails, table, fall risks — after a secondary infusion.", []),
            ("hand-hygiene", "Hand hygiene", "You have left the bedside of a patient on a secondary infusion.", "Hand hygiene that closes the secondary infusion procedure.", ["asepsis/hand-hygiene"]),
            ("document", "Document the secondary infusion", "A secondary infusion is running and nothing is charted yet.", "Charting a secondary infusion and reporting concerns per agency policy.", []),
        ],
        "guards": {"set-rate": ["verify-order", "verify-compatibility"], "third-check": ["safety-steps"]},
        "slots": {},
    },
    "discontinue-iv": {
        "checklist": "discontinuing an IV",
        "title": "Discontinue a peripheral IV",
        "when": "A patient's peripheral IV is to be removed.",
        "what": "The ordered steps for taking out a peripheral IV catheter.",
        "steps": [
            ("gather-supplies", "Gather supplies for IV removal", "You are about to remove a peripheral IV and have nothing in hand yet.", "The supplies IV removal needs.", []),
            ("safety-steps", "Safety steps and patient identification", "You have the supplies to remove an IV and are with the patient.", "Hand hygiene and two patient identifiers before IV removal.", ["asepsis/hand-hygiene", "medication-safety/two-identifiers"]),
            ("prepare-gauze", "Prepare gauze and tape", "The patient whose IV is coming out has been identified.", "Having gauze and tape ready before the catheter is touched.", []),
            ("clamp-iv", "Clamp the IV", "Gauze and tape are ready and the IV is still open.", "Setting the IV clamp to off before removal.", []),
            ("loosen-dressing", "Loosen the dressing", "The IV is clamped and still under its transparent dressing.", "Peeling dressing and tape toward the IV site.", []),
            ("withdraw-catheter", "Withdraw the catheter", "The dressing is loose and the catheter is still in the vein.", "Pulling the catheter out parallel to the skin under a gauze pad.", ["removal"]),
            ("hold-pressure", "Hold pressure on the site", "The catheter has just come out.", "How long to hold pressure, and longer for a patient on anticoagulants.", ["removal/pressure-after-removal"]),
            ("inspect-catheter", "Inspect and dispose of the catheter", "Pressure has been held and the removed catheter is in your hand.", "Confirming a removed catheter is intact.", ["removal"]),
            ("assess-site", "Assess the site once bleeding stops", "Bleeding at the old IV site has stopped.", "Looking for signs of infection at a site after removal.", ["site-assessment/infiltration-and-irritation"]),
            ("dress-site", "Dress the site", "The old IV site is dry and shows no infection.", "Taping gauze or a Band-Aid over the site.", []),
            ("comfort", "Comfort and questions", "An IV has been removed and the site is dressed.", "Positioning the patient and inviting questions after IV removal.", []),
            ("leave-safely", "Safety measures on leaving", "You are about to leave a patient whose IV was removed.", "Call light, bed low and locked, rails, table, fall risks — after IV removal.", []),
            ("hand-hygiene", "Hand hygiene", "You have left the bedside of a patient whose IV was removed.", "Hand hygiene that closes the IV removal procedure.", ["asepsis/hand-hygiene"]),
            ("document", "Document the IV removal", "An IV has been removed and nothing is charted yet.", "Charting IV removal and reporting concerns per agency policy.", []),
        ],
        "guards": {"withdraw-catheter": ["clamp-iv"], "dress-site": ["hold-pressure"]},
        "slots": {"hold-pressure": {"2-3 minutes": ("minutes", "2-3"), "5-10 minutes": ("anticoagulant_minutes", "5-10")}},
    },
}

# id (relative to wiki/), kind, title, when, what, body, slots — parent is the path above it
# THE ONE REAL TWO-VALUED NOTE OUTSIDE THE HELD-OUT PROCEDURE. Its body is the source's own two
# sentences (`source.PROSE`, byte-checked), location first, with the two drop factors turned into
# slots: ONE quantity — a set's drop factor — TWO values, ONE condition — which kind of set. The
# macro-drip value is a list in the textbook ("10, 15, or 20"); a unit stocks one macro-drip set, so
# a site or a case names the one it stocks and the textbook keeps the source's list.
def _drop_factor_body() -> str:
    from training.nursing.source import PROSE
    values, where = PROSE["drop factor"]
    for phrase, slot in (("10, 15, or 20", "{{macrodrip_gtt}}"), ("60", "{{microdrip_gtt}}")):
        assert phrase in values, phrase
        values = values.replace(phrase, slot, 1)
    return f"{where} {values}"


DROP_FACTOR_BODY = _drop_factor_body()

WIKI = [
    ("iv-therapy", "concept", "IV therapy management", "You need to place an IV therapy question before looking anything up.",
     "The branches of this wiki: asepsis, medication safety, rates, site assessment, priming, removal.",
     "IV therapy notes are filed under six branches. Asepsis: keeping ports and hands clean. Medication safety: the rights, the checks, identification, compatibility. Rates: drops per minute and mL per hour. Site assessment: patency and signs of trouble. Priming: filling tubing without air. Removal: taking a catheter out.", {}),
    ("iv-therapy/asepsis", "concept", "Asepsis around an IV line", "You are about to touch a port, a spike or an open end of tubing.",
     "Why connections are kept sterile and which notes say how.",
     "Every connection into a vein is a route for infection. Spikes and tubing ends stay capped until the moment they are connected; ports are scrubbed and left to dry; hands are cleaned before and after.", {}),
    ("iv-therapy/asepsis/scrub-the-hub", "concept", "Scrub the hub", "You need to know how long and how hard to clean an IV port's cap.",
     "The scrub time for a catheter cap and why it must dry.",
     "Cleanse the cap vigorously with an alcohol pad or scrub hub for at least {{seconds}} seconds, then let it dry: friction removes organisms and the drying time is part of the disinfection. Repeat before every new connection.", {"seconds": 5}),
    ("iv-therapy/asepsis/hand-hygiene", "concept", "Hand hygiene", "You are entering or leaving a patient contact.",
     "When hand hygiene falls in a bedside procedure.",
     "Hand hygiene is part of the safety steps on entering and is performed again after leaving the bedside, before documenting.", {}),
    ("iv-therapy/medication-safety", "concept", "Medication safety for IV fluids", "You are handling an IV fluid or medication that a provider ordered.",
     "IV fluids are medications: order, rights, checks, identity, compatibility.",
     "An IV solution is verified against the provider order in the administration record, checked three times against the six rights, given only to an identified patient, and, if secondary, confirmed compatible with what is already running.", {}),
    ("iv-therapy/medication-safety/six-rights", "concept", "The six rights", "You need to list what a medication check compares.",
     "The six rights of medication administration.",
     "Right patient, right medication, right dose, right route, right time, right documentation.", {}),
    ("iv-therapy/medication-safety/three-checks", "concept", "The three checks", "You need to know where each of the three medication checks happens.",
     "Where the first, second and third medication checks fall.",
     "First: while withdrawing the item from the dispensing unit, with expiration date and allergies. Second: after inspecting the solution, before entering the room. Third: at the bedside, after the patient is identified.", {}),
    ("iv-therapy/medication-safety/two-identifiers", "concept", "Two patient identifiers", "You need to confirm who the patient is.",
     "Patient identification with two identifiers.",
     "Confirm identity with two patient identifiers as part of the safety steps, before the bedside check.", {}),
    ("iv-therapy/medication-safety/compatibility", "concept", "Compatibility of a secondary solution", "A secondary medication will share a line with fluids already infusing.",
     "Why and when compatibility is verified.",
     "A secondary solution back-primes from, and runs through, the primary line. Verify it is compatible with every IV fluid the patient is receiving before it leaves the medication room.", {}),
    ("iv-therapy/rates", "concept", "Infusion rates", "You must turn an order into a number to set on a pump or a roller clamp.",
     "Which rate formula applies: gravity or pump.",
     "By gravity the rate is counted in drops per minute and depends on the tubing's drop factor. On a pump the rate is entered in mL per hour and the drop factor plays no part.", {}),
    ("iv-therapy/rates/gravity-drip-rate", "formula", "Gravity drip rate", "An infusion runs by gravity and you need drops per minute.",
     "Drops per minute from volume, time and drop factor.",
     "gtt/min = volume_mL × drop_factor_gtt_per_mL / ( hours × {{minutes_per_hour}} ). Round to a whole drop.", {"minutes_per_hour": 60}),
    ("iv-therapy/rates/pump-rate", "formula", "Pump rate", "An infusion runs on a pump and you need mL per hour.",
     "mL per hour from volume and minutes.",
     "mL/hr = volume_mL × {{minutes_per_hour}} / minutes. Enter the volume to be infused alongside the rate.", {"minutes_per_hour": 60}),
    ("iv-therapy/rates/drop-factor", "table", "Drop factors", "You need the drop factor of a tubing set.",
     "Where the drop factor is read and its usual values.",
     DROP_FACTOR_BODY, {"macrodrip_gtt": "10, 15, or 20", "microdrip_gtt": 60}),
    ("iv-therapy/site-assessment", "concept", "Assessing an IV site", "You are about to use, or have just used, a patient's IV site.",
     "What is assessed at a site and when.",
     "A site is assessed before fluids are connected, again once flow begins, and after a catheter is removed. Patency is shown by a flush; trouble is shown by the tissue.", {}),
    ("iv-therapy/site-assessment/patency-flush", "concept", "Patency flush", "You need to show that an IV catheter is open before infusing through it.",
     "The saline flush, its volume and its technique.",
     "Attach a prefilled normal saline syringe purged of air, open the clamp and inject {{flush_ml}} mL with a turbulent stop-start technique. If resistance is felt, do not force the flush.", {"flush_ml": "3 to 5"}),
    ("iv-therapy/site-assessment/infiltration-and-irritation", "concept", "Infiltration and vein irritation", "An IV site looks or feels wrong.",
     "What stops an infusion at a site.",
     "Signs of vein irritation or infiltration at the venipuncture site are a reason not to proceed with fluids there. Reassess after the infusion begins, and look for infection after removal.", {}),
    ("iv-therapy/priming", "concept", "Priming tubing", "New tubing is full of air and must be filled before it is connected.",
     "Filling a drip chamber and a line.",
     "Clamp, spike, fill the drip chamber halfway, then open the clamp to run fluid to the end of the tubing. A primary line is primed over the sink; a secondary line is back primed.", {}),
    ("iv-therapy/priming/back-priming", "concept", "Back priming", "Secondary tubing must be primed without wasting medication.",
     "Priming a secondary set from the primary line.",
     "Cleanse the y-port closest to the primary drip chamber, connect the secondary tubing, lower the secondary bag below the primary until its tubing fills, then raise it. It then hangs higher than the primary bag.", {}),
    ("iv-therapy/priming/air-in-line", "concept", "Air in the line", "You see or suspect bubbles in primed tubing.",
     "Finding and removing air bubbles.",
     "With the tubing clamped, check its entire length. Tap the tubing gently to move bubbles up into the drip chamber.", {}),
    ("iv-therapy/removal", "concept", "Removing a peripheral catheter", "A catheter is coming out and you need the principles, not the steps.",
     "Direction of pull, integrity, and bleeding.",
     "Withdraw parallel to the skin, slowly and steadily, under gauze. Inspect the catheter to confirm it is intact. Control bleeding with pressure before dressing.", {}),
    ("iv-therapy/removal/pressure-after-removal", "concept", "Pressure after removal", "You need to know how long to press on a site after an IV comes out.",
     "Pressure times, with and without anticoagulants.",
     "Hold pressure for {{minutes}} minutes. For a patient on anticoagulant medication, {{anticoagulant_minutes}} minutes may be needed.", {"minutes": "2-3", "anticoagulant_minutes": "5-10"}),
]

# SITE RULES THE SOURCE DOES NOT HAVE — **INVENTED EXAMPLE CONTENT**, approved as such by the user on
# 2026-09-19 (W5c). Each is one sentence a site ADDS to a note (`Site.adds`), stating a quantity under
# a condition; the textbook's line is never rewritten. They exist so that a corpus can show the SHAPE
# W5 found missing — two values of one quantity, one condition — in several notes of both trained
# procedures. The numbers here are placeholders: every case draws its own. Nothing here is a real
# unit's protocol and nothing here is clinical guidance.
SITE_RULES = {
    # quantity → (notes it lands in, the sentence, {slot: placeholder})
    "cap_soiled_seconds": (
        ["harness/primary-infusion/20-cleanse-cap", "harness/primary-infusion/23-cleanse-cap-again",
         "wiki/iv-therapy/asepsis/scrub-the-hub"],
        "On this unit, a cap that is visibly soiled is cleansed for {{soiled_seconds}} seconds.",
        {"soiled_seconds": 30}),
    "flush_idle_ml": (
        ["harness/primary-infusion/21-assess-patency", "wiki/iv-therapy/site-assessment/patency-flush"],
        "On this unit, a catheter that has not been used since the previous shift is flushed with {{idle_ml}} mL.",
        {"idle_ml": 12}),
    "yport_seconds": (
        ["harness/secondary-infusion/16-back-prime"],
        "On this unit the y-port is cleansed for {{yport_seconds}} seconds, or for {{yport_shared_seconds}} "
        "seconds when the line is shared with another infusion.",
        {"yport_seconds": 15, "yport_shared_seconds": 30}),
    "recheck_minutes": (
        ["harness/secondary-infusion/20-assess-site-after"],
        "On this unit the site is assessed again {{recheck_minutes}} minutes after the infusion begins, or "
        "{{recheck_irritant_minutes}} minutes after for a medication the pharmacy labels an irritant.",
        {"recheck_minutes": 30, "recheck_irritant_minutes": 10}),
}


def _site_rules_file() -> str:
    lines = ["---", "site: unit-4c", "overrides:",
             f"  {SUB}/wiki/iv-therapy/rates/drop-factor: {{macrodrip_gtt: 15}}", "adds:"]
    for notes, text, values in SITE_RULES.values():
        assert '"' not in text
        vals = ", ".join(f"{k}: {v}" for k, v in values.items())
        lines += [f'  {SUB}/{n}: {{text: "{text}", {vals}}}' for n in notes]
    return "\n".join(lines) + """
---
Unit 4C — an EXAMPLE site layer, **invented for this repository**. Every sentence it adds to a note
is a made-up rule in the shape "a quantity, and another value of it under a condition" (docs/MEMORY.md
§5.2, W5c); the numbers are placeholders and each training or evaluation case draws its own. No real
unit's protocol is represented here, and nothing here is clinical guidance.
"""


SITE = """---
site: ward-7b
overrides:
  nursing-iv/harness/primary-infusion/20-cleanse-cap: {seconds: 15}
  nursing-iv/harness/primary-infusion/23-cleanse-cap-again: {seconds: 15}
  nursing-iv/wiki/iv-therapy/asepsis/scrub-the-hub: {seconds: 15}
  nursing-iv/harness/discontinue-iv/07-hold-pressure: {minutes: 5}
---
Ward 7B — an EXAMPLE site layer, invented for this repository. It adapts quantities only; the
runtime substitutes them before a note reaches the expert and marks them `[site]` (docs/MEMORY.md
§5.2). No real ward's protocol is represented here.
"""

README = f"""# nursing-iv — the first library

IV therapy management as a library of notes: three procedures on the `harness/` shelf, each a
skeleton plus one note per step; a small `wiki/` tree; two example `site/` layers. Format and rules:
[`docs/MEMORY.md`](../../docs/MEMORY.md) §1. Built by `python3 -m training.nursing.library`; checked
by `python3 -m memory.lint knowledge/nursing-iv`.

**Attribution.** {ATTRIBUTION} The step bodies are that text, with adaptable quantities turned into
slots. Titles, `when:` / `what:` lines, links and the wiki notes were written for this repository.

**The `site/` layers are invented.** `ward-7b` changes values the textbook states; `unit-4c` ADDS
sentences the source does not have — made-up unit rules of the form "a quantity, and another value of
it under a condition", there so a corpus can show that shape. Their numbers are placeholders. No real
unit's protocol is represented. One wiki note, `rates/drop-factor`, carries the chapter's own
two-valued sentence (macro-drip against micro-drip sets), byte-checked against the page.

**This is training material for a language model. It is not clinical guidance.**
"""


def _body(text: str, subs: dict) -> tuple[str, dict]:
    slots = {}
    for phrase, (name, value) in subs.items():
        assert phrase in text, f"{phrase!r} is not in the source line {text!r}"
        # a slot's textbook value may be a range in the source's own words ("2-3"): the textbook
        # layer must render the source line back, character for character, five→5 aside
        words = {"at least five seconds": "at least {{%s}} seconds", "3 to 5 mL": "{{%s}} mL",
                 "2-3 minutes": "{{%s}} minutes", "5-10 minutes": "{{%s}} minutes"}[phrase]
        text = text.replace(phrase, words % name)
        slots[name] = value
    return text, slots


def build() -> dict[str, str]:
    """path (relative to the repository) → file content."""
    files: dict[str, str] = {f"{ROOT}/README.md": README, f"{ROOT}/site/ward-7b.md": SITE,
                             f"{ROOT}/site/unit-4c.md": _site_rules_file()}
    for pslug, p in PROCEDURES.items():
        lines = CHECKLISTS[p["checklist"]]
        assert len(lines) == len(p["steps"]), (pslug, len(lines), len(p["steps"]))
        pid = f"{SUB}/harness/{pslug}"
        ids = [f"{pid}/{i:02d}-{s[0]}" for i, s in enumerate(p["steps"], 1)]
        by_slug = {s[0]: ids[i] for i, s in enumerate(p["steps"])}
        for i, (slug, title, when, what, uses) in enumerate(p["steps"]):
            body, slots = _body(lines[i], p["slots"].get(slug, {}))
            requires = ([ids[i - 1]] if i else []) + [by_slug[g] for g in p["guards"].get(slug, [])
                                                      if by_slug[g] != (ids[i - 1] if i else None)]
            n = Note(id=ids[i], shelf="harness", kind="step", title=title, when=when, what=what,
                     body=body, requires=requires, next=ids[i + 1] if i + 1 < len(ids) else None,
                     uses=[f"{W}/iv-therapy/{u}" for u in uses], slots=slots, source=SOURCE)
            files[f"knowledge/{n.id}.md"] = n.serialise()
        # THE SKELETON IS LABELS, NOT TITLES. Thirty-two full titles, numbered, are 230 tokens
        # against a limit of 150 (the lint's first finding on this library). A label is the
        # step id's own slug, so the line the expert reads is the line it will `<open>`.
        skeleton = "\n".join(f"{i:02d} {s[0].replace('-', ' ')}" for i, s in enumerate(p["steps"], 1))
        proc = Note(id=pid, shelf="harness", kind="procedure", title=p["title"], when=p["when"],
                    what=p["what"], body=skeleton, first=ids[0], steps=ids, source=SOURCE)
        files[f"knowledge/{pid}.md"] = proc.serialise()
    wiki_ids = [f"{W}/{w[0]}" for w in WIKI]
    for rel, kind, title, when, what, body, slots in WIKI:
        nid = f"{W}/{rel}"
        parent = nid.rsplit("/", 1)[0]
        n = Note(id=nid, shelf="wiki", kind=kind, title=title, when=when, what=what, body=body,
                 parent=parent if parent in wiki_ids else None,
                 children=[c for c in wiki_ids if c.rsplit("/", 1)[0] == nid], slots=slots,
                 source=SOURCE if body == DROP_FACTOR_BODY else OWN)   # the one wiki body that IS the source's text
        files[f"knowledge/{nid}.md"] = n.serialise()
    return files


# ---------------------------------------------------------------- the W1 gate

# a question's site fact (questions.SITE_FACTS, by position) → the note and slot that hold it
SITE_SLOTS = [(f"{SUB}/harness/primary-infusion/20-cleanse-cap", "seconds"),
              (f"{SUB}/harness/primary-infusion/21-assess-patency", "flush_ml"),
              (f"{SUB}/harness/discontinue-iv/07-hold-pressure", "minutes"),
              (f"{SUB}/harness/discontinue-iv/07-hold-pressure", "anticoagulant_minutes")]
PROCEDURE_OF = {p["checklist"]: f"{SUB}/harness/{slug}" for slug, p in PROCEDURES.items()}


def oracle_walk(q: dict, lib) -> list[str]:
    """The notes an oracle opens, in order, to answer one question of `questions.build()`.

    order, next   the procedure, then its steps by `next` up to the later of the steps asked about
    rate          the rates concept, then the formula the question's wording selects
    site          the procedure, its steps up to the one holding the quantity — served through a
                  site layer that overrides exactly that slot with the question's answer

    Raises if a note is missing, a step's textbook rendering is not the source line, or the site
    layer does not put the answer in the text. W1's gate is that this never raises.
    """
    from memory.layers import render
    from memory.notes import Site
    from training.nursing.questions import SITE_FACTS

    if q["kind"] == "rate":
        leaf = "gravity-drip-rate" if "drops per minute" in q["question"] else "pump-rate"
        ids = [f"{W}/iv-therapy/rates", f"{W}/iv-therapy/rates/{leaf}"]
        assert ids[1] in lib[ids[0]].children
        return [lib[i].id for i in ids]

    pid = PROCEDURE_OF[q["checklist"]]
    walk = lib.walk(pid)
    lines = CHECKLISTS[q["checklist"]]
    assert len(walk) == len(lines), (pid, len(walk), len(lines))
    if q["kind"] == "site":
        fact = next(f for f in SITE_FACTS if f[1] in q["question"])
        target, slot = SITE_SLOTS[SITE_FACTS.index(fact)]
        site = Site(name="case-site", overrides={target: {slot: q["answer"]}})
        text = render(lib[target], site)
        assert f"{q['answer']} [site]" in text, (q["id"], text)
        assert str(q["answer"]) not in render(lib[target]).split(), (q["id"], "the textbook already says it")
        return [pid] + walk[: walk.index(target) + 1]
    asked = [i for i, line in enumerate(lines) if line in q["question"]]
    assert len(asked) >= 2, (q["id"], asked)
    for i in asked:                       # the note IS the source line, once its slots are filled
        got = render(lib[walk[i]]).replace("at least 5 seconds", "at least five seconds")
        assert got == lines[i], (walk[i], got)
    if q["kind"] == "next":               # up to the step that answers it, not to a distractor
        option = next(l for l in q["question"].splitlines() if l.startswith(q["answer"] + ". "))
        return [pid] + walk[: lines.index(option[3:]) + 1]
    return [pid] + walk[: max(asked) + 1]


def gate(root: Path = ROOT) -> dict:
    """W1: the lint passes; every walk the oracle needs exists (docs/MEMORY.md §10)."""
    from memory.lint import lint
    from memory.notes import Library
    from training.nursing.questions import build as questions

    findings = lint(root)
    lib = Library.load(root)
    walks, missing = {}, {}
    for q in questions():
        try:
            walks[q["id"]] = oracle_walk(q, lib)
        except (AssertionError, KeyError, StopIteration, ValueError) as e:
            missing[q["id"]] = repr(e)[:200]
    kinds = {k: sum(1 for n in lib.notes.values() if n.kind == k) for k in
             ("procedure", "step", "concept", "formula", "table")}
    return {"library": str(root), "notes": len(lib.notes), "kinds": kinds, "sites": sorted(lib.sites),
            "lint_findings": [list(f) for f in findings],
            "questions": len(walks) + len(missing), "walks_found": len(walks), "walks_missing": missing,
            "walk_length": {"min": min(map(len, walks.values()), default=0),
                            "max": max(map(len, walks.values()), default=0)},
            "passed": not findings and not missing, "walks": walks}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    files = build()
    if "--gate" in argv:
        import json
        g = gate()
        out = Path(argv[argv.index("--gate") + 1]) if len(argv) > argv.index("--gate") + 1 else None
        if out:
            out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(g, indent=2))
        print(f"[library] W1 gate: lint {len(g['lint_findings'])} finding(s); "
              f"{g['walks_found']}/{g['questions']} oracle walks exist; "
              f"{'PASSED' if g['passed'] else 'FAILED'}", flush=True)
        return 0 if g["passed"] else 1
    if "--check" in argv:
        on_disk = {str(p) for p in ROOT.rglob("*.md")}
        drift = [p for p, text in files.items() if not Path(p).exists() or Path(p).read_text() != text]
        drift += sorted(on_disk - set(files))
        for p in drift:
            print(f"[library] drift: {p}")
        print(f"[library] {len(files)} file(s), {len(drift)} drifted", flush=True)
        return 1 if drift else 0
    for p, text in files.items():
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        Path(p).write_text(text)
    print(f"[library] wrote {len(files)} file(s) under {ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
