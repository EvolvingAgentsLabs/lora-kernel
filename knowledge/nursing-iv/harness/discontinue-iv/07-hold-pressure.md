---
id: nursing-iv/harness/discontinue-iv/07-hold-pressure
shelf: harness
kind: step
title: Hold pressure on the site
when: The catheter has just come out.
what: How long to hold pressure, and longer for a patient on anticoagulants.
requires: [nursing-iv/harness/discontinue-iv/06-withdraw-catheter]
next: nursing-iv/harness/discontinue-iv/08-inspect-catheter
uses: [nursing-iv/wiki/iv-therapy/removal/pressure-after-removal]
slots: {minutes: 2-3, anticoagulant_minutes: 5-10}
source: Nursing Skills (Open RN), ch. 23 IV Therapy Management, NBK596734 — CC BY 4.0
---
Hold pressure on the IV site for {{minutes}} minutes. If the patient is on anticoagulant medication, you may need to hold for {{anticoagulant_minutes}} minutes.
