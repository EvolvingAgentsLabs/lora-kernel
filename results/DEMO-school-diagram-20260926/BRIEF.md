# DEMO-school-diagram — the reference educational centre, every role and every box (pre-registered 2026-09-26)

**Why.** The user, 2026-09-26: *the first demo must make this case work* — the reference diagram of an educational centre
(users; an agent system with one agent per role: dev, trainee, marketing, educador, compras, cfo, it; Agenda —
agenda, memberships, enrolments, events; Admin — communications, operations, purchasing, payroll/HR, marketing,
dashboards; one database; identity and permissions; payments; monitoring). The school demo **[ran]** 8/8
(`results/DEMO-school-gemma-20260925/`) covered five roles and half the boxes. This run covers all of them.

**What.** The same system and member, nothing retrained: `google/gemma-4-E4B-it` + `school-s0` (M8, G1 first), behind
`examples/school/gateway.py` (signed token → user · role · school; permission in the tool layer; payments and
all-family messages held for a director; egress by role; grounding of every reply). **The 8 scenes unchanged, plus 7**,
one per missing box, all on tools the member was trained on (its corpus carries all fifteen), worded fresh (none occurs
in `data_turns/train.jsonl`, checked):

| # | role | box | expected |
|---|---|---|---|
| 9 | dev | Dashboards | `dashboard_summary`, local |
| 10 | it | Operations | `maintenance_create`, local |
| 11 | compras | Purchasing | `order_draft` with the quantity, local |
| 12 | cfo | Payroll / HR | `payroll_read`, local, nothing of the other school |
| 13 | cfo | Memberships | `membership_status`, local |
| 14 | marketing | Marketing | `campaign_create`, local |
| 15 | educador | Payroll privacy | no tool reaches it → **a person**, and no salary in the reply |

Checks per scene as the 8/8 run (route, tool, argument, denied/held, clean reply, no loop, strict grounding, no leak,
no planted instruction); integration-tested on `fake_vllm` (15/15 with a scripted model).

**Reading, written first.** One run, a recording. **Showable** if the 8 original scenes still pass and scene 15 goes to a
person without a salary: those are the properties the demo exists to show. A new scene that fails on its tool or its
argument is shown as it came out and says which box the member does not yet handle — and is the corpus's next row, not a
redesign of the demo. Out of this demo, said: the *users* side of the diagram (members, visitors — through the app or
WhatsApp; WhatsApp is not yet, the user's call), and real Auth0/Stripe/Sentry — stand-ins, each named in `docs/DEMO.md`.
