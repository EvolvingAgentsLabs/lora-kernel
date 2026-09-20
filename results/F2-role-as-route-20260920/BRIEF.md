# F2 — the role as the route (pre-registered 2026-09-20, zero GPU)

**Question.** The target deployment has one agent per role, and the runtime already knows which agent
a message came from ([`FRAMEWORK.md`](../../docs/FRAMEWORK.md) §5 row A). Two learned routers lost
every request from an unseen sender **[ran]** M2. **If the request carries its role, does routing get
at least as good as the keyword dictionary — and what happens to a message that arrives under the
wrong role, or that belongs to nobody?**

**The carrier [read].** The one thing OpenClaw sets per agent, without a patch, is the model id
(`agents.<name>.model: "provider/<id>"`, `docs/OPENCLAW.md` §3–4): the provider registers one id per
role and each agent points at its own. So the role rides in the model name: `auto:<role>` beside the
existing `auto`. A header would need the runtime to be able to set one per agent, which nothing we have
read shows; the `user` field is not sent by the adapter we use. `auto` with no role behaves as today.

**Two policies, both declared before any number** (`route.decide(req, role=…, policy=…)`):

- **`role_first`** — the role's member is served, *unless the keys name another region*, in which case
  the keys decide exactly as today. A role whose member is measured `out` leaves. Unknown role = today.
- **`role_confirmed`** — the role *narrows* the keys to its own region: the member is served only when
  its own keys fire; otherwise the request leaves. Keys of another region never serve.

**Arms, no model anywhere.**
1. *dictionary* — today's `decide`, no role.
2. *true role* — every request carries the role of the member it truly belongs to; texts that belong
   to nobody (sets C, C2, D) are scored under **each** role and the worst is reported; texts built from
   a member's own listing followed by another task (E, E2) carry that member's role — that is the agent
   they would really arrive at.
3. *wrong role* — in-region requests of one member arriving under the other member's role (A and the
   paraphrased B, both directions).

**Instruments.** `route.replay` on P41's 240 cases (delivered accuracy, misrouted, out — P62's own
number: 0.775, 0 misrouted) and `router_sets.score` on A, B, C, D, E and the after-the-freeze C2, E2, F
(right member, misrouted-to-local, lost-local, abstained). Misrouted-to-local is the zero term
(FOUNDATIONS §8.4): a request served by a member it does not belong to.

**Falsifier, fixed now.** A policy FAILS if, against the dictionary: (a) on true-role traffic its
delivered accuracy on the replay is lower or it misroutes more there; or (b) on any set its
misrouted-to-local is higher than the dictionary's; or (c) under the wrong role an in-region request is
**silently served by the wrong member** — *caught* means it is served by its true member or it leaves.
A policy that fails does not become the proxy's default. If both fail, the role is accepted by the
proxy only behind a flag and `FRAMEWORK.md` row A says why.

**What it cannot show.** Every text is generated; the role labels are ours. Whether real traffic of a
role stays inside that role's region is exactly what no generated set can contain.

**Redesign count: 0.** A third policy invented after seeing these numbers is a new brief, not a fix.

## Result **[ran]** 2026-09-20 · `role_confirmed` passes and becomes the default; `role_first` fails — a role says WHICH member, never WHETHER

Zero GPU, `python -m training.harness.role_route` → `role_route.json`. Misrouted-to-local, by set
(lower is better; the dictionary is today's route):

| set | what it is | n | dictionary | true role · `role_first` | true role · `role_confirmed` |
|---|---|--:|--:|--:|--:|
| A | in-region requests | 715 | 0 (715 right) | 0 (715 right) | 0 (715 right) |
| B | the question paraphrased | 240 | 0 (109 right, 131 lost) | 0 (**240 right**) | 0 (109 right, 131 lost) |
| C | foreign text carrying a key | 14 | 13 | **14** | 8 |
| D | plain foreign text | 76 | 0 | **25** | 0 |
| E | a member's own listing, another task | 120 | 47 | **111** | 47 |
| C2 | as C, written after M2's freeze | 8 | 8 | 8 | 5 |
| E2 | as E, written after M2's freeze | 120 | 51 | **120** | 45 |
| F | unseen senders, in region | 120 | 0 (120 right) | 0 (120 right) | 0 (120 right) |

Replay on P41's 240 cases, true role attached: 186 delivered, 0.775, 0 misrouted, 90 out — identical
for the dictionary and both policies.

Wrong role attached (in-region requests of one member arriving at the other's agent):

| | A (715) | B (240) | F (120) |
|---|---|---|---|
| `role_first` | 715 served by their true member | 109 by their true member, **131 silently served by the wrong member** | 120 by their true member |
| `role_confirmed` | 715 leave | 240 leave | 120 leave |

**Verdict, by the falsifier above.** `role_first` FAILS on (b) and (c): it is the only arm that serves
every paraphrase (240/240), and it pays for it by serving a foreign task with the role's member —
120 of 120 on E2, 25 plain foreign texts, and 131 requests under the wrong role. `role_confirmed`
PASSES: never more misroutes than the dictionary (fewer on C, C2, E2, because another member's keys
no longer serve), nothing served under a wrong role, the replay a tie. It is now the proxy's default
for `auto:<role>`; `role_first` stays selectable only so it can be measured.

**What this corrects.** *"The role is the route, so routing costs nothing"* was too strong. The role
answers **which** member — and that half is now free and safe. It does not answer **whether** the
request is inside that member's region: an agent of a role is also asked to draft, to summarise, to
forward. That half is still the keys — 131 of 240 paraphrases lost, 45–47 of 120 foreign tasks over a
member's own listing served — and is still milestone 2's open problem, now one class smaller: with
the role given, the router has to tell *in region* from *not*, for one member at a time.

**Redesign count: 0.**
