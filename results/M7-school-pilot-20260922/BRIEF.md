# The first LoRA on `examples/school`'s generated corpus (pre-registered 2026-09-22)

**Question.** `examples/` validates the architecture against a reference organisation, code-only,
"before any adapter" (`examples/README.md`). Its biggest pure-code step — a corpus generator
(`examples/school/generate_corpus.py`) that drives the tool layer and rolls back its own writes,
891 rows across seven roles — was done 2026-09-21 and never trained. This is the next,
GPU-requiring step named in `docs/FRAMEWORK.md`'s gap table: **does a member trained on this
corpus learn to reach for its own tool**, the way `email-full`/`desk-commitment` did on the email
domain?

**One role, not seven — buy the arm in sequence.** `educador` (read the agenda of a student at
this school, one tool, `agenda_read`): the largest single-task corpus after regenerating at the
generator's own default (`--n 400`), 114 train / 19 eval, held out by student id, three phrasings
per case so the task is not one fixed template. Every other role in `examples/` has less data and
the same one-tool shape; if this one arm does not clear the gate, the other six are not worth
buying either.

**One unknown.** What is measured is **tool-call fidelity only** — did the model write
`<agenda_read>{id}</agenda_read>` with the *held-out student's own id* — not full corpus-mode
serving with a live tool result spliced back in and a continuation graded. That is a second,
larger question (`docs/RECORD.md`: *"serve an expert the way its corpus taught it, and suspect the
path before the model"*) and stays out of this run. The grader never executes a tool: truth comes
from each case's own `tool`/`entity_id` fields, so nothing about a live result can leak into
"correct."

**Headroom first.** The bare `Qwen3.5-4B` is evaluated on the held-out set before any training
exists, in the same run, recorded before the adapter is trained
(`training/harness/school_pilot.py`'s `base_eval` before `adapter_eval`) — if the base already
reaches for `agenda_read` correctly from the system prompt alone (it states the tool's name and
argument), the adapter is undecidable and the run stops meaning what it was bought to mean.

**Mechanism.** `training/harness/school_pilot.py`, reusing `training.s4_train.load_base` /
`make_generate` / `train_adapter` / `free` unchanged (the same primitives `train_pool.py`'s
released members are trained through) and `training.harness.bar.compare` for the paired sign test
— no new training or grading code, only a new corpus and a new tag regex. A fresh base per
adapter (`train_adapter` reloads rather than reusing the headroom pass's mutated model).

**Gate.** Adapter accuracy ≥ 0.90 on the 19 held-out cases, strictly more correct than the base,
and the pair significantly different (`bar.compare`, exact sign test, $\alpha = 0.05$).

**Falsified by:** adapter accuracy < 0.90, or a tie with the base (the paired test does not
reject), or the base already at or above 0.90 (headroom exhausted — a different arm, not this
one, would be needed).

**Provider.** Colab, `GPU=L4` (a T4 has no bf16; an adapter trained in bf16 and served in fp16 is
a second unknown — `../../CLAUDE.md` §3), through `training/harness/chain_serve.sh`,
`SKIP_ADAPTERS=1` (nothing carried in — this module trains its own).

**Launch:**

```bash
GPU=L4 BRANCH=m7-school-pilot-20260922 RUN_DIR=results/M7-school-pilot-20260922 \
  MODULE=training.harness.school_pilot MARGS="--role educador --out school_pilot.json" \
  RESULTS_NAME=school_pilot.json BASE=Qwen/Qwen3.5-4B TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 \
  training/harness/chain_serve.sh
```

`TRAINDEPS=1` is not optional here — `chain_serve.sh`'s own "train deps" step is gated on it being
non-empty (`[ -z '${TRAINDEPS:-}' ] || pip install peft trl datasets accelerate bitsandbytes …`)
and prints `ok` either way, so a launch without it boots clean and fails deep inside training with
`ImportError: … requires bitsandbytes` — caught on the first attempt 2026-09-22, fixed here before
relaunch, cost was boot time only.

**Redesign count: 0.**

## Result [ran] 2026-09-22 — FALSIFIED before training: headroom already exhausted

Session `srv081926`. Headroom (bare `Qwen3.5-4B`, before any adapter exists) scored
**18 of 19 = 0.9474** on tool-call fidelity — the single miss (`educador-0034`) wrote "I will
read the agenda for student 51 now." and never emitted the closing tag inside the 32-token
budget, not a wrong tool or a wrong id. **This clears the 0.90 gate on its own, exactly the
third falsification condition named before the run: "the base already at or above 0.90 —
headroom exhausted."** The pre-registered arm stops here — training an adapter on top of a task
the base already does from the system prompt alone cannot produce an attributable result.

Session ended (reclaimed or self-terminated) partway through training (step 20 of 24, ~83%,
`adapters/school-educador` never completed or reached the adapter's own eval) before this could
be confirmed with the adapter side too — but per the rule above, that arm was already decided
moot by the headroom number regardless: `school_pilot.json`'s `base_eval` (persisted before
training started, per "persist every result as it lands") is what survives, and it is enough to
answer the question this run was bought to ask. No GPU-minutes were spent chasing a session that
had already answered its own falsifier.

**What this says about the corpus, not just the model.** `agenda_read` is a single tool with one
argument the system prompt states outright ("You may read the agenda of students at this school
only... Read the agenda entries (events) for one student, by id"), and every training/eval case's
user turn already names or implies the id in plain language ("student 60", "Petrov, Zuri (id
60)"). A capable base model does not need training to bridge a gap that thin — this is the same
finding P61/W5c's own family of lessons already generalised: **a corpus with one difficulty
teaches a floor**, and here the floor was already the ceiling. The other six roles in `examples/`
share this same one-tool, id-stated-in-the-request shape (`docs/RECORD.md`'s bar on this project:
buy the arm that can kill the hypothesis first — it did, on the first and cheapest role tried, so
the other six are not bought yet either.

**Next, if this is worth another arm.** Either (a) a role whose task needs *judgement*, not just
syntax — closer to `email-full`'s shape (when to call the tool, not only how) — or (b) a harder
version of `educador` itself: multi-step or ambiguous requests where the id is not stated, only
inferable. Neither is this run; both are new, separately-bought arms.

**Falsified by:** the base already at 0.90 or above — it is, 0.9474. (The other two named
conditions — adapter < 0.90, or a tie against the base — were never reached.)
