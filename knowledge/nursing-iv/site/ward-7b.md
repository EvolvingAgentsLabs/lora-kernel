---
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
