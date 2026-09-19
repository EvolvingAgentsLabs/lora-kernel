"""What is left of the first instrument: model backends and answer parsing.

`alpha/` was the character-level acceptance surface (S0–S2). It measured format, not
agreement — identical answers scored 0.00 across formats — and `measure.py`, `report.py`
and `kernel_headroom.py` left `main` with the rewrite of 2026-09-19; they are at the tag
`v0.1-foundations` with the runs that showed it (`docs/RECORD.md` §2). Acceptance is now
measured by teacher forcing in `training/harness/accept_rank.py`.

Two modules stay because living code imports them: `backends` (one client for local and
frontier models, used by the headroom arm) and `cases` (`parse_answer`).
"""
