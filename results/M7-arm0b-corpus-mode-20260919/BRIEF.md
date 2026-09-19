# M7 arm 0b — the fluids expert served the way its corpus taught (pre-registered 2026-09-19)

**Question (one unknown: the serving path).** `fluids-full` scored **11 of 90** through
`tool_calls` / `role: "tool"` **[ran]** P41 and became *the expert that reasons fails*. Read where
it happens (`training/physics/result_use.py`, 0 tool errors in the replay): of 79 failures, **74**
hold a number that came from nowhere and **75** leave a tool result unused — 217 of 456 results
ignored; it looks the density up, 882.3, and multiplies by 1359.7. Its corpus taught the result
**inline**, `<calc>…</calc>= 4.2305`; that other path costs `email-full` 0.992 → 0.808 **[ran]**
P55, and fluids was never re-served in corpus mode. **Same adapter, same cases, corpus mode: does
the score move?**

**Why before any knowledge base.** A base delivers what it retrieves into this same channel. The
answer decides how milestone 7 has to hand a note to an expert.

**Set-up.** Colab **L4**, one session, ~10 minutes, no training, no API provider.
`MODULE=training.harness.corpus_mode_arm`; base `Qwen/Qwen2.5-3B-Instruct`; adapter `fluids-full`
carried in from `results/P39-second-expert-retrained-20260915/adapters.tgz` — safetensors sha
`825abeb8…`, identical in P40's pool tarball, the one P41 served. 90 cases,
`multitool.generate(90, 616161)` — P41's own, paired by id. Temperature 0, 200 tokens a step, up to
12 calls (the corpus's chains are 6–9).

**Checked before it runs, zero GPU (`tests/test_fluids_corpus_mode.py`).** The served turn is
byte-for-byte what `render_tools` writes, as the generator at the tag built it; results are `:.6g`
as the corpus wrote them; **all 90 oracle chains pass through this loop** with 0 refusals — a
harness its oracle cannot pass measures itself; the recorded run rescored under this suite's rule
gives 11, the stored total.

**Verdict, written first (`corpus_mode_arm.verdict`)** — paired, exact two-sided sign test on
discordant pairs, $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

| outcome | reading | what follows |
|---|---|---|
| G1 not applied | VOID | nothing is about the expert |
| **improvement** | the path was part of it | *"the expert that reasons fails"* is corrected in `RECORD.md` to what the number now is; fluids' `serve: out` is re-measured against the frontier's 66/90 before it changes; a knowledge base has a channel that works |
| **tie** | the path was not it | a 3B does not use an inline result either: reading is the wall, milestone 7's arm 1 is predicted to fail at this size, and its first arm moves to the 4B |
| regression | corpus mode is worse | read the chains before anything else |

Beside the score, the same instrument as arm 0 on this arm's chains: results used, ignored,
numbers from nowhere. An *improvement* in which the unused-result failure did **not** fall would
mean the score moved for another reason — say so.

**Not measured:** whether the physics relations are right when the numbers are read; any knowledge
base; the 4B.

**Redesign counter: 0.**

## Result **[ran]** 2026-09-19 · THE PATH WAS PART OF IT — 90 of 90

Colab L4, one session, 7 minutes of run. Read off `corpus_mode.json`.

| | through `tool_calls` (P41, recorded) | **corpus mode — result inline, as the corpus taught** |
|---|--:|--:|
| correct | 11 / 90 | **90 / 90** |
| calls · refused | 603 · 0 | 628 · 0 |
| by family | — | 23/23 · 23/23 · 22/22 · 22/22 |

G1 identity `applied` 3/3. Paired by case id: **79 : 0**, $p = 2\cdot2^{-79}$. The recorded run
rescored under this suite's rule gives 11, the stored total, so both arms were scored by one rule.

**Checked before it was believed, zero GPU** — a number this clean is the kind this repository
learned to distrust (P53): **0 of 90** evaluated statements occur in the 600-example corpus; **0 of
90** oracle answers occur as a training answer; of the made-up fluid names only **1 of 90** recurs,
with a different density; the final answer equals the model's **own last `<calc>` result in 89 of
90**; calls per case 6–9, the oracle's depth. The runtime evaluates only what the model writes — it
never sees the oracle's expressions.

**And against the frontier, on the same 90 cases, paired (zero GPU):** local in corpus mode 90,
`google/gemini-3.8-flash` 66 (P41) — **24 : 0**. The region was marked *serve out* on a measurement
of the serving path.

**What this overturns.** *"The expert that decides works, the expert that reasons fails"* — the most
quoted line of the record — was read off a harness that never showed the expert its results the way
it was taught to read them. In its region, served as taught, the expert that reasons is at the
ceiling.

**What it does not say.** Anything **outside** the region: P45's over-solving below the training
depth was measured through the same `tool_calls` path and is **open again**; P14's 1/20 on sibling
families was under an earlier in-process harness and is not re-checked. The **bare base in corpus
mode** was not run in this session — the attribution arm. And 90/90 is a ceiling: it ranks nothing.

**What follows.** A knowledge base has a channel that works: a 3B *does* use an inline result.
`fluids-full` goes back through the release gate, in corpus mode, before `route.REGIONS` stops
sending its region out. The proxy's member loop is capped at six round-trips — below a fluids chain's
6–9 — so the cap has to come from the member's contract.
