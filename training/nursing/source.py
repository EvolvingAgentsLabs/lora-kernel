"""The first text in this repository that nobody here wrote: three IV-therapy checklists.

SOURCE AND LICENCE. *Nursing Skills*, Open Resources for Nursing (Open RN), Chippewa Valley
Technical College — Chapter 23, "IV Therapy Management", NCBI Bookshelf NBK596734. Licensed
**CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/): reuse and adaptation, commercial
included, with attribution — this is the attribution. WHO material was the other candidate and
defaults to CC BY-NC-SA 3.0 IGO, which cannot ship in a service nor sit in an Apache-2.0 tree.

WHAT IS HERE AND WHAT IS NOT **[read]** 2026-09-19. The top-level steps of each checklist, in
order, as returned by a fetch of the page; sub-bullets (the repeated "safety steps" list, the
leaving-the-room list) are left out. The fetch passes through a summarising model, so the wording
is *as returned*, not byte-checked against the page. For what it is used for — the ORDER of steps
and a handful of quantities — that is enough to measure headroom; a released region re-reads the
source itself.

THIS IS TRAINING MATERIAL. The questions built from it are a student's. Nothing here advises a
patient, and nothing here is a medical device.
"""

ATTRIBUTION = ("Adapted from Nursing Skills (Open RN, Chippewa Valley Technical College), "
               "Chapter 23 IV Therapy Management, NCBI Bookshelf NBK596734, CC BY 4.0.")

CHECKLISTS = {
    "primary IV solution administration": [
        "Gather supplies: IV fluid, primary tubing, tubing change label, and alcohol pads/scrub hubs.",
        "Verify the provider order with the medication administration record (eMAR/MAR).",
        "Perform the first check of the six rights of medication administration while withdrawing the IV fluids from the medication dispensing unit. Check expiration date and verify patient allergies.",
        "Remove the IV solution from the packaging and gently apply pressure to the bag while inspecting for tears or leaks.",
        "Check the color and clarity of the solution.",
        "Perform the second check of the six rights of medication administration.",
        "Enter the patient room and greet the patient.",
        "Perform safety steps, including hand hygiene and confirming patient ID using two patient identifiers.",
        "Perform the third medication check of the six rights of medication administration at the patient's bedside.",
        "Remove the primary IV tubing from the packaging. If administering IV fluid by gravity, note the drip factor on the package and calculate drops/min.",
        "Move the roller clamp so that it is halfway up the tubing and clamp it.",
        "Remove the cover from the tubing port on the bag of IV fluid.",
        "Remove the cap from the insertion spike on the tubing. While maintaining sterility, insert the spike into the tubing port of the bag of IV fluid.",
        "Squeeze the drip chamber two or three times to fill the chamber halfway.",
        "Loosen the cap from the end of the IV tubing and open the clamp to prime the tubing over the sink.",
        "Once primed, clamp the IV tubing and check the entire length of the tubing for air bubbles. Tap the tubing gently to remove any air.",
        "Replace or tighten the cap on the end of the tubing.",
        "Label the primary IV fluid bag with the date and time. Place the tubing label on the tubing near the drip chamber.",
        "Assess the patient's venipuncture site for signs and symptoms of vein irritation or infiltration. Do not proceed with administering fluids at this site if there are any concerns.",
        "Vigorously cleanse the catheter cap on the patient's IV port with an alcohol pad/scrub hub for at least five seconds and allow it to dry.",
        "Assess IV site patency: attach a prefilled normal saline syringe purged of air, undo the clamp, and inject 3 to 5 mL of normal saline using a turbulent stop-start technique. If resistance is felt, do not force the flush.",
        "Remove the syringe from the IV cap and then clamp the extension tubing.",
        "Vigorously cleanse the catheter cap on the patient's IV port again for at least five seconds and allow it to dry.",
        "Remove the protective cap from the end of the primary tubing and attach it to the IV port while maintaining sterility.",
        "Move the slide clamp on the saline lock to open the tubing.",
        "Set the infusion rate based on the provider order (pump: volume and mL/hr; gravity: drops per minute).",
        "Assess the patient's IV site for signs and symptoms of vein irritation or infiltration after infusion begins.",
        "Secure the tubing to the patient's arm.",
        "Assist the patient to a comfortable position, ask if they have any questions, and thank them for their time.",
        "Ensure safety measures when leaving the room (call light, bed low and locked, side rails, table, room risk-free for falls).",
        "Perform hand hygiene.",
        "Document the procedure and related assessment findings. Include IV fluids on the patient's input/output documentation.",
    ],
    "secondary IV solution administration": [
        "Gather supplies: secondary IV fluid/medication, secondary IV tubing, alcohol wipe/scrub hubs, and tubing labels.",
        "Verify the provider order with the medication administration record (eMAR/MAR).",
        "Perform the first check of the six rights of medication administration while withdrawing the IV solution and tubing from the medication dispensing unit. Check expiration dates and verify allergies.",
        "Verify compatibility of the secondary IV solution with the other IV fluids the patient is currently receiving.",
        "Remove the IV solution from the packaging and gently apply pressure to the bag while inspecting for tears or leaks. Check the color and clarity of the solution.",
        "Perform the second check of the six rights of medication administration.",
        "Enter the patient room and greet the patient.",
        "Perform safety steps, including hand hygiene and confirming patient ID using two patient identifiers.",
        "Perform the third check of the six rights of medication administration at the patient's bedside.",
        "If the patient is receiving the medication for the first time, teach the patient and family about the potential adverse reactions and other concerns related to the medication.",
        "Remove the secondary IV tubing from the packaging.",
        "Place the roller clamp to the \"off\" position.",
        "Remove the protective sheath from the IV spike and the cover from the tubing port of the IV solution.",
        "Insert the spike into the IV bag while maintaining sterility.",
        "Compress and release the drip chamber, filling halfway.",
        "Prime the secondary IV tubing by back priming: cleanse the y-port closest to the drip chamber, connect the secondary tubing, lower the secondary bag below the primary bag until the tubing fills, then raise it.",
        "Hang the secondary IV solution on the IV pole with the primary bag lower than the secondary bag.",
        "Label the secondary tubing near the drip chamber.",
        "Set the infusion rate (pump: volume and mL/hr; gravity: roller clamp to the appropriate drops per minute).",
        "Assess the patient's IV site for signs and symptoms of vein irritation or infiltration after infusion begins.",
        "Assist the patient to a comfortable position, ask if they have any questions, and thank them for their time.",
        "Ensure safety measures when leaving the room (call light, bed low and locked, side rails, table, room risk-free for falls).",
        "Perform hand hygiene.",
        "Document the procedure and assessment findings. Report any concerns according to agency policy.",
    ],
    "discontinuing an IV": [
        "Gather supplies: gauze, tape, or a Band-Aid.",
        "Perform safety steps, including hand hygiene and confirming patient ID using two patient identifiers.",
        "Prepare the gauze and tape.",
        "Place the IV clamp to the \"off\" position (clamped).",
        "Loosen the edges of the transparent dressing and tape in the direction of the IV site.",
        "Place a gauze pad over the IV site and gently pull the IV out parallel to the skin in a slow and steady motion.",
        "Hold pressure on the IV site for 2-3 minutes. If the patient is on anticoagulant medication, you may need to hold for 5-10 minutes.",
        "Inspect the catheter to ensure it is intact and dispose of it in an appropriate container.",
        "Remove the gauze pad once bleeding has stopped and assess for any signs of infection at the site.",
        "Tape the gauze or apply a Band-Aid over the IV site.",
        "Assist the patient to a comfortable position, ask if they have any questions, and thank them for their time.",
        "Ensure safety measures when leaving the room (call light, bed low and locked, side rails, table, room risk-free for falls).",
        "Perform hand hygiene.",
        "Document the procedure and related assessment findings. Report any concerns according to agency policy.",
    ],
}

# PROSE the checklists do not carry. **BYTE-CHECKED** 2026-09-19, unlike the checklists above: the
# chapter page was fetched with `curl` (https://www.ncbi.nlm.nih.gov/books/NBK596734/, 102 091 bytes,
# sha256 e600a131853d9248…) and each sentence below is one contiguous run of its HTML, §23.2 "IV
# Therapy Basics" › "IV Administration Equipment". Same work, same licence, same attribution.
# WHY IT IS HERE: it is the only place outside the discontinuation checklist where this chapter
# states TWO VALUES OF ONE QUANTITY UNDER A CONDITION — the shape W5 found the corpus never showed.
PROSE = {
    "drop factor": [
        "A macro-drip infusion set delivers 10, 15, or 20 drops per milliliter, whereas a micro-drip "
        "infusion set delivers 60 drops per milliliter.",
        "The drop factor is located on the packaging of the IV tubing and is important to verify when "
        "calculating medication administration rates.",
    ],
}


def note(name: str) -> str:
    """One checklist as the note a knowledge base would hold."""
    steps = CHECKLISTS[name]
    return (f"Checklist for {name}\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
            + f"\n\n({ATTRIBUTION})")
