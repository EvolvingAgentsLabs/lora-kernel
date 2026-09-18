# P62 — routing per request (milestone 2), 2026-09-18, zero GPU

**Question (one unknown).** Can the proxy decide local or frontier from the request's
text alone — the client names no model — without delivering less than the by-region
policy of P41 (0.775) on the same traffic?

**Mechanism.** `training/harness/route.py`: a keyword surface per region (the router
baseline's dictionary, moved next to the decision), `serve: local | out` per region as
measured (P40: fluids fails 78/90 → out). `openai_proxy --auto NAME [--auto-out MODEL]`
rewrites `model` in place: the member if local, the frontier model if it leaves. The log
line names the decision and the shapes, never the content.

**Instrument.** `route.replay` on P41's records: for each of the 240 cases (150 email,
90 fluids), the per-request decision delivers the local record's correctness if kept by
the right member, the frontier's if sent out, **0 if handed to the wrong member**
(conservative). Beside it, the by-region policy on the same cases. Formula in
FOUNDATIONS §8.4.

**Pre-registered, in the test before the replay ran** (`tests/test_route.py`):
by-request ties by-region **and** misroutes = 0. Failure written first: any misroute, or
by-request < 0.775 → the dictionary is not enough and a learned classifier (the base
zero-shot) is the next arm.

**Result [ran].** by region 0.775 · by request **0.775** · misrouted **0** · out 37.5 % →
**TIES**. The decision layer costs nothing on this traffic; what changed is the
interface: `lorapool/auto` instead of a member's name.

**Not measured:** real traffic (milestone 4 re-measures the dictionary there); requests
that carry two regions; the latency of the classification (a dictionary over one
string — negligible, not measured).
