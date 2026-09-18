# P64 — milestone 5, synthetic: the second useful member (2026-09-18)

**Question (one unknown).** Does a second useful member — the desk `commitment` expert —
enter through Phase 1's door and co-reside with `email-full` on one base, routed by
its question?

**Headroom, zero GPU, before anything trained.** Keyed on the listing's markers
(`From:`, `Subject:`, `Preview:`) the desk's prompts route to triage 15 of 60. Keyed on
the question ("is this important" vs "did you commit"), desk 60/60, desk-deep 60/60,
email 150/150, fluids 140/140. `route.REGIONS` is rewritten that way; the router has
headroom to add the region.

**Set-up.** Colab L4. `desk-commitment` trained from `data_desk/train.jsonl` (600
examples, `release_gate.RECIPE`) — the P55b weights were never brought back, so the
release *is* the retrain. Served with `email-full@v1` in one vLLM; proxy `--prune
--member-prompt --auto`. Desk suite, 240 cases, seed 424242 (P55b's cases).

**Pre-registered (`pool_second.verdict`).** `released` iff:

- G1 identity applied for both members (empty-arm rule); G2 tools reachable for both;
- G2' `auto` serves a desk prompt with `desk-commitment` and a listing with `email-full`
  (read off the reply's `model`);
- the new arm **ties the recorded g600 240/240** ($p \ge 0.05$ on discordant pairs, §9.2)
  and **beats the base** (recorded 38/240; $p < 0.05$).

**Failure written first.** A loss to the recorded run: the training chain does not
reproduce this region — no manifest. A tie with the base: the member is not useful.
A wrong live route: the region table is not ready for two members on one inbox.

**Not measured:** the desk-deep band (P60 §3c/3d, behind this); real traffic for the router.
