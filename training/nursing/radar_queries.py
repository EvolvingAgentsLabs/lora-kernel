"""The queries W3's radar is measured on — written AFTER the design was frozen, and only once.

WHY W2'S QUERIES ARE VOID HERE. W2's oracle searches for a note with that note's own `when:` line.
Any searcher — lexical, hashed, random-projected — puts a text first against itself, so its 72/72 at
rank 1 says nothing about ranking (results/M7-W2-runtime-20260919/BRIEF.md says so). A radar is
measured on queries that do **not** share the target's words.

THE DESIGN, FROZEN BEFORE A QUERY WAS WRITTEN (results/M7-W3-radar-r0-20260919/BRIEF.md):

    P   paraphrase, n = 94 — one query per note of the library, in the words of someone at the
        bedside, sharing as few content words with the target's `when:`/`what:` as practical. The
        three procedures repeat steps (supplies, identification, hand hygiene, charting), so a query
        carries which procedure it is in — in other words than the note's: *cannula*, *drip*,
        *maintenance fluids*, *piggyback*, *antibiotic*. THIS IS THE SET THE GATE READS: 94 targets,
        and the within-topic confusions are where flat retrieval failed before (MEMORY §2.2).
    E   entry, n = 72 — the stem of each of `questions.build()`'s 72 questions (text nobody wrote as
        a query) → the first note its oracle walk opens. Only four distinct targets, so it is
        reported beside P and cannot carry the gate.

`overlap(query, note)` is the leak meter: the fraction of the query's content words (W2's own
tokenizer and stop list — the lexical baseline's view of the text) that occur in the target's
`when:` + `what:`. Reported per set, so a reader can see how much a word-matcher was handed.

A set the designer has iterated against is a training set (CLAUDE.md §3). P is written once. If the
lexical baseline leaves no headroom it may be made harder ONCE, and that is counted in the brief.
"""
from __future__ import annotations

from memory.notes import Library
from memory.runtime import _words

PREFIX = "nursing-iv/"

P: dict[str, str] = {
    # --- taking a cannula out -------------------------------------------------------------------
    "harness/discontinue-iv": "The doctor says the cannula in her forearm can come out today. How do I go about it?",
    "harness/discontinue-iv/01-gather-supplies": "What do I need to collect from the store room before I take a cannula out?",
    "harness/discontinue-iv/02-safety-steps": "I've walked in with everything for taking the cannula out. What comes before I touch anything?",
    "harness/discontinue-iv/03-prepare-gauze": "I know it's the right person, the cannula is still in. What do I lay out within reach?",
    "harness/discontinue-iv/04-clamp-iv": "Swabs and sticky strips are laid out. Fluid could still run through the cannula — what now?",
    "harness/discontinue-iv/05-loosen-dressing": "Flow is shut off. Which way do I lift the clear film covering the cannula?",
    "harness/discontinue-iv/06-withdraw-catheter": "The film is lifted. At what angle do I slide the cannula out, and what do I cover it with?",
    "harness/discontinue-iv/07-hold-pressure": "It's out and oozing. How many minutes do I press, and what if he takes warfarin?",
    "harness/discontinue-iv/08-inspect-catheter": "Could the tip have snapped off inside? What do I look at once I'm done pressing?",
    "harness/discontinue-iv/09-assess-site": "The oozing has settled. Redness, warmth, pus — when do I look for those where the cannula was?",
    "harness/discontinue-iv/10-dress-site": "The skin looks clean and healthy where the cannula was. What do I cover it with?",
    "harness/discontinue-iv/11-comfort": "The plaster is on after taking the cannula out. What do I do for the person before tidying up?",
    "harness/discontinue-iv/12-leave-safely": "Before I walk out after taking a cannula out — buzzer, height of the mattress, side bars: what is the list?",
    "harness/discontinue-iv/13-hand-hygiene": "I'm in the corridor after taking a cannula out. Do I wash again?",
    "harness/discontinue-iv/14-document": "What goes in the notes after a cannula is taken out, and whom do I tell if something looked off?",
    # --- hanging maintenance fluids -------------------------------------------------------------
    "harness/primary-infusion": "New prescription: a litre of saline running all day through the cannula she already has. Where do I begin?",
    "harness/primary-infusion/01-gather-supplies": "What kit do I collect before hanging a litre of maintenance fluids?",
    "harness/primary-infusion/02-verify-order": "I've got the kit for the maintenance fluids. Which two documents must agree before I go on?",
    "harness/primary-infusion/03-first-check": "I'm at the automated cabinet taking out the litre of saline. What do I verify right there — dates, reactions?",
    "harness/primary-infusion/04-inspect-bag": "I've torn the outer wrap off the litre of saline. How do I find a pinhole?",
    "harness/primary-infusion/05-check-solution": "The litre of saline holds when squeezed. Cloudy, discoloured, floating specks — when do I look for that?",
    "harness/primary-infusion/06-second-check": "The saline looks fine and I'm still at the med station with the maintenance fluids. What verification is due now?",
    "harness/primary-infusion/07-enter-room": "Maintenance fluids verified twice, I'm in the hallway. Knock, introduce myself — what does the sheet say?",
    "harness/primary-infusion/08-safety-steps": "I've said hello and I'm carrying the maintenance fluids. Wash, wristband, date of birth — in which order?",
    "harness/primary-infusion/09-third-check": "Wristband matches for the maintenance fluids. What last verification happens right next to her?",
    "harness/primary-infusion/10-unpack-tubing": "Where do I find how many drops make a millilitre for this giving set for the maintenance fluids?",
    "harness/primary-infusion/11-clamp-roller": "The giving set for the maintenance fluids is unwrapped. Where does the little wheel go and should it be shut?",
    "harness/primary-infusion/12-uncover-port": "The wheel on the maintenance giving set is shut. What do I pull off the litre of saline next?",
    "harness/primary-infusion/13-spike-bag": "How do I push the sharp end of the giving set into the litre of saline without contaminating it?",
    "harness/primary-infusion/14-fill-drip-chamber": "The sharp end is in the litre of saline. How full should the little reservoir under it be, and how do I get it there?",
    "harness/primary-infusion/15-prime-tubing": "The reservoir is at the right level on the maintenance set. How do I run fluid through to push the bubbles out, and where?",
    "harness/primary-infusion/16-check-air": "I've run saline through the maintenance giving set. What do I inspect before it goes anywhere near her?",
    "harness/primary-infusion/17-cap-tubing": "The maintenance giving set has no bubbles. What do I do with its free tip so it stays clean?",
    "harness/primary-infusion/18-label": "What do I write on the litre of saline and stick on its giving set so the next shift knows when to replace them?",
    "harness/primary-infusion/19-assess-site-before": "Maintenance fluids are all set up. Before hooking up, what do I examine on her forearm — swelling, redness along the vessel?",
    "harness/primary-infusion/20-cleanse-cap": "I'm going to screw a flush onto her cannula's needleless connector for the maintenance fluids. How do I wipe it first?",
    "harness/primary-infusion/21-assess-patency": "The connector is wiped and I've got the 10 mL flush in hand. How do I push it to prove the cannula still works?",
    "harness/primary-infusion/22-remove-syringe": "The flush went through easily. What do I do with it and with the short pigtail line?",
    "harness/primary-infusion/23-cleanse-cap-again": "Flush is unscrewed, I'm going to hook up the maintenance giving set. Do I wipe the connector once more?",
    "harness/primary-infusion/24-attach-tubing": "The connector has been wiped twice and aired. How do I hook the maintenance giving set onto it?",
    "harness/primary-infusion/25-open-slide-clamp": "The maintenance set is hooked up but nothing can flow: the pigtail is still pinched shut. What do I release?",
    "harness/primary-infusion/26-set-rate": "Maintenance fluids hooked up and unpinched. How do I get it running at what was prescribed — machine or counting?",
    "harness/primary-infusion/27-assess-site-after": "Maintenance fluids began dripping a moment ago. What do I watch for at her forearm?",
    "harness/primary-infusion/28-secure-tubing": "Maintenance fluids are going and the giving set dangles. How do I stop it getting tugged?",
    "harness/primary-infusion/29-comfort": "Maintenance fluids are going and taped down. What do I do for her before I tidy up?",
    "harness/primary-infusion/30-leave-safely": "Before I walk out with maintenance fluids going — buzzer, height of the mattress, side bars: what is the list?",
    "harness/primary-infusion/31-hand-hygiene": "I'm in the corridor after getting maintenance fluids going. Do I wash again?",
    "harness/primary-infusion/32-document": "What goes in the notes once maintenance fluids are going — and does the litre count toward her fluid balance?",
    # --- hanging a piggyback --------------------------------------------------------------------
    "harness/secondary-infusion": "He has saline going already and is due a small bag of antibiotic every eight hours. How is a piggyback hung?",
    "harness/secondary-infusion/01-gather-supplies": "What kit do I collect before hanging a piggyback antibiotic?",
    "harness/secondary-infusion/02-verify-order": "I've got the kit for the piggyback antibiotic. Which two documents must agree before I go on?",
    "harness/secondary-infusion/03-first-check": "I'm at the automated cabinet taking out the piggyback antibiotic and its short set. What do I verify right there?",
    "harness/secondary-infusion/04-verify-compatibility": "Can this antibiotic be mixed into the same line as the saline he already has going? When do I look that up?",
    "harness/secondary-infusion/05-inspect-bag": "I've torn the wrap off the piggyback antibiotic. What do I look at — drips, cloudiness, tint?",
    "harness/secondary-infusion/06-second-check": "The piggyback antibiotic looks fine and I'm still at the med station. What verification is due now?",
    "harness/secondary-infusion/07-enter-room": "Piggyback antibiotic verified twice, I'm in the hallway. Knock, introduce myself — what does the sheet say?",
    "harness/secondary-infusion/08-safety-steps": "I've said hello and I'm carrying the piggyback antibiotic. Wash, wristband, date of birth — in which order?",
    "harness/secondary-infusion/09-third-check": "Wristband matches for the piggyback antibiotic. What last verification happens right next to him?",
    "harness/secondary-infusion/10-teach-first-dose": "He has never had this antibiotic before. What do I tell him and his wife about side effects, and when?",
    "harness/secondary-infusion/11-unpack-tubing": "I'm next to him with the short piggyback set still wrapped. What now?",
    "harness/secondary-infusion/12-clamp-roller": "The short piggyback set is unwrapped. Should its little wheel be shut before I pierce the antibiotic?",
    "harness/secondary-infusion/13-uncover-spike-and-port": "The wheel on the piggyback set is shut. Which two protective caps come off now?",
    "harness/secondary-infusion/14-spike-bag": "Both caps are off. How do I pierce the antibiotic with the piggyback set without contaminating it?",
    "harness/secondary-infusion/15-fill-drip-chamber": "The antibiotic is pierced. How full should the piggyback's little reservoir be, and how do I get it there?",
    "harness/secondary-infusion/16-back-prime": "How do I clear bubbles from the piggyback set without spilling a drop of antibiotic — using the saline line and the top Y-site?",
    "harness/secondary-infusion/17-hang-bags": "Which should sit higher on the stand, the antibiotic or the saline?",
    "harness/secondary-infusion/18-label": "The antibiotic is up on the stand, bubbles cleared. Where on the piggyback set do I stick the dated sticker?",
    "harness/secondary-infusion/19-set-rate": "Antibiotic is up, stickered and ready. How do I get the piggyback running at what was prescribed — machine or counting?",
    "harness/secondary-infusion/20-assess-site-after": "The piggyback antibiotic began dripping a moment ago. What do I watch for at his forearm?",
    "harness/secondary-infusion/21-comfort": "The piggyback antibiotic is going. What do I do for him before I tidy up?",
    "harness/secondary-infusion/22-leave-safely": "Before I walk out with a piggyback antibiotic going — buzzer, height of the mattress, side bars: what is the list?",
    "harness/secondary-infusion/23-hand-hygiene": "I'm in the corridor after getting a piggyback antibiotic going. Do I wash again?",
    "harness/secondary-infusion/24-document": "What goes in the notes once a piggyback antibiotic is going, and whom do I tell if something looked off?",
    # --- the wiki ---------------------------------------------------------------------------------
    "wiki/iv-therapy": "I have a general doubt about drips and don't know which topic it belongs under. Where's the table of contents?",
    "wiki/iv-therapy/asepsis": "Why does everyone fuss about not letting connectors and sharp ends brush against anything?",
    "wiki/iv-therapy/asepsis/hand-hygiene": "At which moments around a bedside task am I supposed to wash or use gel?",
    "wiki/iv-therapy/asepsis/scrub-the-hub": "Fifteen seconds of wiping the needleless connector, or more? And do I wait for it to air?",
    "wiki/iv-therapy/medication-safety": "Is a plain litre of saline really treated like a drug, with all the same verifications?",
    "wiki/iv-therapy/medication-safety/compatibility": "Two drugs down one lumen — what is the worry, and at what point is it looked up?",
    "wiki/iv-therapy/medication-safety/six-rights": "Right person, right drug, right dose… what are the rest of that list?",
    "wiki/iv-therapy/medication-safety/three-checks": "Cabinet, med station, bedside — which verification is done at which place?",
    "wiki/iv-therapy/medication-safety/two-identifiers": "Is the name alone enough to be sure I've got the right person? What else do I ask for?",
    "wiki/iv-therapy/priming": "A fresh giving set is empty. What is the general idea of getting fluid through it before hooking it up?",
    "wiki/iv-therapy/priming/air-in-line": "There are little pockets of gas stuck along the set after I ran fluid through. How do I get rid of them?",
    "wiki/iv-therapy/priming/back-priming": "What is that trick where you lower the piggyback below the main bag so saline runs up into it?",
    "wiki/iv-therapy/rates": "The prescription says 1 L over 8 h. How do I know which calculation to use to get a setting?",
    "wiki/iv-therapy/rates/drop-factor": "Is it 10, 15, 20 or 60 gtt/mL for this set, and where is that printed?",
    "wiki/iv-therapy/rates/gravity-drip-rate": "No machine available: how many gtt/min for 500 mL in 4 h with a 20 gtt/mL set?",
    "wiki/iv-therapy/rates/pump-rate": "The machine wants a number for 100 mL in 30 min. What do I key in?",
    "wiki/iv-therapy/removal": "Not the checklist — just the reasoning behind taking a cannula out: angle, whether it's whole, stopping the ooze.",
    "wiki/iv-therapy/removal/pressure-after-removal": "Two minutes or five with the swab held down afterwards? He's on blood thinners.",
    "wiki/iv-therapy/site-assessment": "What am I looking at on the forearm around the cannula, and at which moments?",
    "wiki/iv-therapy/site-assessment/infiltration-and-irritation": "Her forearm is puffy, cool and tender around the cannula. Do I carry on running fluid?",
    "wiki/iv-therapy/site-assessment/patency-flush": "How much saline, and with what push-pause motion, to be sure a cannula isn't blocked?",
}


def overlap(query: str, note) -> float:
    """The share of the query's content words a word-matcher finds in the target's two fields."""
    q = _words(query)
    return len(q & (_words(note.when) | _words(note.what))) / len(q) if q else 0.0


def stem(question: str) -> str:
    """The question as asked, without its options: up to the first option line."""
    lines = []
    for line in question.splitlines():
        if line[:3] in ("A. ", "B. ", "C. ", "D. "):
            break
        lines.append(line)
    return " ".join(lines).strip()


def build(lib: Library) -> dict[str, list[dict]]:
    """{"P": [...], "E": [...]}, each row {id, query, target, overlap}."""
    from training.nursing import questions
    from training.nursing.library import oracle_walk

    p = [{"id": f"P-{i:02d}", "query": q, "target": PREFIX + short,
          "overlap": round(overlap(q, lib[PREFIX + short]), 4)}
         for i, (short, q) in enumerate(P.items())]
    e = []
    for q in questions.build():
        target = oracle_walk(q, lib)[0]
        text = stem(q["question"])
        e.append({"id": f"E-{q['id']}", "query": text, "target": target,
                  "overlap": round(overlap(text, lib[target]), 4)})
    return {"P": p, "E": e}


def overlap_summary(rows: list[dict]) -> dict:
    v = sorted(r["overlap"] for r in rows)
    return {"n": len(v), "mean": round(sum(v) / len(v), 4), "median": v[len(v) // 2], "max": v[-1],
            "zero": sum(x == 0 for x in v)}
