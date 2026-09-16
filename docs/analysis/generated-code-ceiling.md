# Generated code has a shape ceiling, and we have now hit it twice

**Analysis, 2026-09-16. Written to stop, not to patch.** The redesign counter for this
suite is at three, and this repository's rule is that three is looking for the result.

## What was asked, and it was a good question

Build small experts on **one algorithm in several programming languages**, complete an
advanced prefix, and let speculative acceptance pick the right expert. The reasoning
behind it is sound and it is the best predicate this project has had:

- **The prefix fixes the format**, which is what C9 measured as the thing that broke
  agreement — identical answers scoring 0.00 across formats **[ran]**.
- **The verifier is execution**, exact and judge-free.
- **The difficulty is the cut point**, which comes from the algorithm rather than from
  us — the answer to the report's finding that a generated suite cannot hold a
  difficulty its author did not think of.

All three still hold. What follows is about the *generator*, not about the idea.

## Three attempts, each one measured, each one failing one level up

| attempt | what varied | what the adapter learned | measured |
|---|---|---|---|
| **P53** | nothing in the tail | **one tail per family** | 180/180 held-out completions verbatim in training |
| **P54** | the constants, inlined | **one skeleton per (family, cut)** | 197 distinct completions, **6** distinct skeletons |
| **now** | names, loop form, counts | **one of 55 skeletons** | 43 skeletons in the held-out set, **204/204 already in training** |

Each fix worked at the level it targeted and was defeated one level up. The third is
the clearest: structural variety raised the shape space from 6 to about **60**, and
720 training examples cover every shape **twelve times over**.

## The arithmetic that says to stop

For a held-out shape to be **novel**, the structural space has to exceed the training
set. At 720 examples that means thousands of distinct shapes — roughly **ten
structural dimensions of four choices each**. That is a program generator, and
building one is a different project from the one this suite exists to serve.

**The tension is structural, not a bug:**

- **Generated code** is exactly verifiable and its shape space is bounded by its
  generator — so a big enough adapter memorises the shapes.
- **Real code** has an unbounded shape space and the base model has already read it —
  so the ceiling risk moves to the baseline, and verification gets harder.

## What survives, and it is not small

- **Step zero is answered: yes.** A base model with the right LoRA learns this
  predicate and beats the base **0.137 → 1.000**, paired, 170 to 0, p < 1e-5
  **[ran]** P54. That question is closed.
- **The machinery is proven end to end**: subprocess training, C18, execution-based
  verification over 394 completions with **zero transport errors**, resumable arms,
  a preflight.
- **The suite gates work.** Every failure above was caught by a check rather than by
  a GPU, and each left a test behind.

## What this does not license

**It does not license the α matrix.** A cross-language matrix — `lora-c` on a Python
prefix rejecting at token 1 — measures **syntax filtering**, which twelve keywords
also do, and this project has already priced that trap at 1.000 **[ran]** P1/S3. And
within a language there is nothing to rank: P54's expert reaches **1.000**, so
acceptance against the 32B would measure the 32B's idiosyncrasies rather than any
expert's quality.

**Ranking needs experts that differ in quality.** On a suite where the right expert is
perfect, they cannot.

## The two honest ways forward, and the choice is not mine

1. **Real code, accepting the new risks.** Thousands of human implementations of the
   same algorithms give an unbounded shape space. The cost is that the base has read
   them — so the first thing to buy is a **headroom check on the base**, not a
   training run, and the verifier needs harnessing per repository.
2. **Go back to the domain with traction.** `email-full` is the one expert that
   clears its gate (**260/351 = 0.741**, p = 0.00036 **[ran]**), and the live blocker
   there is not a suite at all: OpenClaw sends **54 tools** and the expert calls none
   **[ran]**. Pruning that surface in the proxy needs **no GPU** and closes the gap
   between the simulation and the real agent.

**One session of four remains.** Option 2 costs none of it.
