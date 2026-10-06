# τ² T1b — is the 12B the student? Gemma 4 12B base on airline `test` against T1's E4B and 31B (pre-registered 2026-10-06)

**Why.** T1 **[ran]** (the user's decision, reading 1): the 31B scores pass^1 0.5375 and the E4B base 0.175 (empty first
replies scored 0) — **DISTIL HERE**, +36.2 pp, CI [20.0, 53.8], 11 : 0 tasks. Before T2 (the 31B's trajectories on
`train`) is planned, the user asked (2026-10-06, "prueba 3") which model is the student: the E4B, or the 12B — the large half
of the pair, which runs on their Mac in MLX at 8.4 GB (MAC, MLXK0 **[ran]**). On real documents the trained 12B tied the
E4B (PAIR1 **[ran]**); τ² is a different region — long policy, 14 tools, multi-turn — where size may matter. Google's card
**[read]**: τ² 69.0 % for the 12B, 76.9 % for the 31B (averaged over domains, another simulator; not comparable to ours).

**What.** T1's instrument unchanged (`examples.tau2.t1_run`, τ² at `5bfa7e3`, airline `test`, 20 tasks × k = 4, τ²'s seed
300, `--max-steps 150`, temperature 0, thinking off, the 31B as the user simulator), with the agent of the base arm
`google/gemma-4-12B-it` at revision `707f0a3b…` (`--base-rev`, the only code change), bf16. **The 31B's arm is carried
from T1's record** (same simulator, tasks, trials and seeds) so only the 12B runs; the 31B is served as the simulator.
**Model and provider:** Colab, one G4 (96 GB; the 31B W4A16 at 45 % + the 12B bf16 at 40 %), vLLM, through
`chain_serve.sh`; API spend 0 USD. Fallback: H100 (the one card change T1 allowed).

**The verdict** (`read.py`, written and checked against T1's record before the run — it reproduces T1's 31B-vs-E4B gap):

$$\Delta_{12B,E4B} = \overline{p_{12B}(t) - p_{E4B}(t)}, \text{ paired over the 20 tasks; CI by bootstrap over tasks}$$

- **12B IS THE STUDENT** — $\Delta_{12B,E4B} \ge 15$ pp **and** its 95 % CI excludes 0 → T2 is planned for the 12B.
- **E4B STAYS THE STUDENT** — anything else.
- **VOID** — the 12B arm's preflight fails, or more than 5 % of its simulations end in an error **other than** an empty
  first reply (τ²'s `AssistantMessage must have either content or tool_calls`), which is scored 0 as the agent's own
  failure — T1's reading 1, applied here before the run, not after. **INCOMPLETE** — fewer than 80 simulations.
- **Beside, not gating:** $\Delta_{31B,12B}$ with its CI — whether the 31B still has ≥ 15 pp to teach a 12B student; the
  empty-first-reply count per arm; pass^4; calls per simulation.

**Stopping condition.** At most 2 G4 sessions (the E4B arm took one with the 31B's; this is one arm). Nothing in the
tasks, trials, simulator, thresholds or gate moves after this brief. **After T1b the line pauses again**: T2 gets its own
brief and the user's go. Redesign count: 0 (a new arm on a frozen instrument).
