---
site: unit-4c
overrides:
  nursing-iv/wiki/iv-therapy/rates/drop-factor: {macrodrip_gtt: 15}
adds:
  nursing-iv/harness/primary-infusion/20-cleanse-cap: {text: "On this unit, a cap that is visibly soiled is cleansed for {{soiled_seconds}} seconds.", soiled_seconds: 30}
  nursing-iv/harness/primary-infusion/23-cleanse-cap-again: {text: "On this unit, a cap that is visibly soiled is cleansed for {{soiled_seconds}} seconds.", soiled_seconds: 30}
  nursing-iv/wiki/iv-therapy/asepsis/scrub-the-hub: {text: "On this unit, a cap that is visibly soiled is cleansed for {{soiled_seconds}} seconds.", soiled_seconds: 30}
  nursing-iv/harness/primary-infusion/21-assess-patency: {text: "On this unit, a catheter that has not been used since the previous shift is flushed with {{idle_ml}} mL.", idle_ml: 12}
  nursing-iv/wiki/iv-therapy/site-assessment/patency-flush: {text: "On this unit, a catheter that has not been used since the previous shift is flushed with {{idle_ml}} mL.", idle_ml: 12}
  nursing-iv/harness/secondary-infusion/16-back-prime: {text: "On this unit the y-port is cleansed for {{yport_seconds}} seconds, or for {{yport_shared_seconds}} seconds when the line is shared with another infusion.", yport_seconds: 15, yport_shared_seconds: 30}
  nursing-iv/harness/secondary-infusion/20-assess-site-after: {text: "On this unit the site is assessed again {{recheck_minutes}} minutes after the infusion begins, or {{recheck_irritant_minutes}} minutes after for a medication the pharmacy labels an irritant.", recheck_minutes: 30, recheck_irritant_minutes: 10}
---
Unit 4C — an EXAMPLE site layer, **invented for this repository**. Every sentence it adds to a note
is a made-up rule in the shape "a quantity, and another value of it under a condition" (docs/MEMORY.md
§5.2, W5c); the numbers are placeholders and each training or evaluation case draws its own. No real
unit's protocol is represented here, and nothing here is clinical guidance.
