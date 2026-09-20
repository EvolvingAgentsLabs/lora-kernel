# M7 · W5d — the answer policy: the adapter walks, and who writes the last line depends on the kind of task (pre-registered 2026-09-20)

Step 1 of [`docs/FRAMEWORK.md`](../../docs/FRAMEWORK.md) §7, *decide who reads*. No training.

**Question (one unknown: who writes which final line).** W5, W5b and W5c **[ran]** say one thing three
ways: the adapter **navigates** a procedure it never trained on (42 : 0 against the untrained base made
to walk, 0 retrieval misses) and carries it; it does **not read** a value stated under a condition in a
note it never saw (0/11; 4/15 after a corpus that showed the shape over eight notes), where the
untrained base reads 15/15. Letting the base write *every* final line is not a serving design — it
gives back 19 control cases (W5b). **Does a split by kind of task — the adapter carries procedures and
computes rates, the bare base reads values from the pages the adapter's walk opened — beat the adapter
alone on a held-out procedure, without giving the trained band back?**

## The policy, frozen before any set below was written

`training/nursing/answer_policy.py`. The adapter **walks, always**. The final line:

| kind of task | who writes | why |
|---|---|---|
| **carry** — report the last step carried out; or say it is not in the library | the **adapter** | navigation and procedure are what training bought: shared-line 22/22 against the base's 8/22, mid-procedure 14/22 against 5/22 **[ran]** W5c |
| **rate** — a rate computed from an order | the **adapter** | a rate is computed, not read, and the adapter computes through `<calc>`. Decided **from the trained band only**: on the CONTROL sets the adapter is 15/15 (W5) and 12/12 (W5c), the base handed the same notes 7/15 and 5/12, composition 7/15 (W5b). The held-out procedure has no rate step, so no held-out number exists to have been used |
| **value** — a quantity read off a note, plain or under a condition | the **bare base**, given the pages the adapter's walk opened, served exactly as `base-reads` is | 15/15 and 16/16 where the adapter is 4/15 and 13/16 **[ran]** W5c |

**Decided without the grader's labels.** A row's `family` does not exist at serving time. `kind()`
reads the **statement** and nothing else — the form of answer the request itself asks for. Agreement
with the generator's `family`, on rows nobody evaluates (zero GPU **[ran]**): **600/600** on
`data_walks_v2/train.jsonl`, **600/600** on `data_walks/train.jsonl` (563 and 559 statements name a
form; the rest name none and default to the adapter, which is today's behaviour). The bar fixed for
this number was 0.98: under it, stop and report, do not tune against an evaluation set.

**What that 1.0 is worth, said before it is quoted anywhere.** The statements are written by a generator
whose closing sentence names the answer form, so a rule over that sentence recovers it exactly. It
shows the rule is wired to the corpus's wording; it does **not** show that a live request can be
classified. *A model of a generated corpus learns the generator* holds for a regex too. In a role pack
the answer form belongs in the task schema, or a classifier is paid for and measured on real asks. This
run does neither, and prices only the split.

The freeze is a commit of its own; its hash is cited under *Sets* below, which was written after it.

## Two stages — only one is the claim

| stage | on what | what it is |
|---|---|---|
| **claim** | NEW held-out and control sets, `training/nursing/data_walks_w5d/`, written **after** the freeze; never W5's 80, never W5c's 88/80 | **the only stage the verdict reads** |
| **attribution** | the policy over W5c's **recorded** `withlib` walks on the v2 sets (whole walks and opened ids are stored since W5b's fix; 168/168 replay exactly **[ran]**, zero GPU) | those sets are new to the policy's *design* — its 47/56 came from W5's first set — and **not new to us**: a first out-of-sample look, labelled as that, never the claim |

## Arms, in the order bought — one L4 session

| # | arm | why now |
|---|---|---|
| 0 | zero GPU: `kind()` agreement, the floor on the new sets, the attribution ceiling | before anything is paid for |
| 1 | **`base-reads`** on the new sets — the untrained base, the oracle's notes open | **headroom first**, and W5's bar. If it has credit on ≥ n − 5 of the headline, no arm can *beat* it by a sign test: `no_headroom_for_the_bar` is reported. **The session continues either way** — the pair that can falsify the policy is the next one, its headroom is `withlib`'s failures, and the session is already bought |
| 2 | **`withlib`** walks the new sets — W5c's v2 adapter (`adapters/nursing-walks-v2-q35`, sha256 `0f7d872d…`), **carried in, not retrained** | the policy's walks have to exist on the new set; G1 identity first |
| 3 | **`policy`** on the new sets — `withlib`'s record where the adapter writes; its replayed walk plus the base's line where the base does | the claim |
| 4 | **`policy`** on the v2 sets, from W5c's recorded walks | attribution; last, because a session lives sixty minutes and this is the stage that does not count |

**Not bought:** `nolib` and `base-walks` on the new sets (W5 and W5c settled both: 35 : 2, 39 : 0, 42 : 0);
a policy that sends only values from *untrained* notes to the base (decidable at serving time — the
release knows which notes its corpus opened — and a redesign of this one); any training.

## Verdict — written first (`walks_policy.verdict`)

On the NEW **headline** (held-out, depth ≤ 9, final line no other procedure states), by **credit**
(`right` or `format`, the untouched `grade_walks`), paired by case id, exact two-sided sign test on
discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at
$p<0.05$:

| pair | required | reading if not |
|---|---|---|
| **policy vs withlib**, headline | **improvement** | **FALSIFIED** — on a set written after the freeze the split buys nothing over the adapter alone; the 47/56 was the set |
| **policy vs withlib**, control | **not a REGRESSION** | **NOT A SERVING DESIGN** — what composition did (W5b, 0 : 19) |
| **policy vs base-reads**, headline | W5's bar; the spec says ***beats*** | a **tie is reported as a tie**, with totals. What a tie would mean here: *learned* navigation plus the base's reading reaches what the *oracle's* navigation plus the base's reading reaches — the adapter paid for the walk `base-reads` is handed for free — while on control the policy is far ahead of `base-reads`, printed beside. It is still a tie, and W5's bar is not cleared by it |

`passed` = all three. `right` alone — the contract: right **and** in the taught form — is paired and
printed beside credit for both headline pairs. Void, not failed: G1 not applied; any headline record
missing or lost to transport. A walk that cannot be replayed leaves every slice for every arm and is
counted (zero are expected: records keep their whole walk now).

**W5's verdict stands whatever this says.** A policy that passes is a candidate serving design with one
held-out set under it — an entry for the role pack's *answer policy* — not a second reading of W5.

Beside the headline, never folded in: shared-line rows; quantity by layer and by which value was asked;
control with and without `rate`; `policy` credit by writer; `format`, `unread`, `context`; transport
errors; `prompt_identical_to_base_reads`.

## Suite, models, parameters

**Suite.** See *Sets* below. **Models and provider.** `Qwen/Qwen3.5-4B` (Hugging Face weights, bf16)
served by **vLLM on Colab**, with one LoRA module, `withlib`; no API provider is called. Thinking off
in every render. **Parameters.** Temperature 0; walking arm 160 tokens a step, stop at the closing tag,
64 calls; arms with no verbs 320 tokens, no stop strings; window 8192 — a prompt that outgrows it is
`context`, not an error; concurrency 8; searcher lexical (R0 did not pass W3), as the corpus was
generated.

## Cost, abort, redesigns

**Cost.** One L4 session expected: ≈ 170 `base-reads` replies, ≈ 170 walks, ≈ 130 single replies —
W5c's scoring session did more in 24 minutes. **Ceiling: 2 sessions**, on this arm's own budget. No
dollars to a provider. **Abort rule.** No `[arm]` progress line for 8 minutes once the base is up →
stop the session; the runner persists every record and resumes. Never `colab exec` by hand into the
session the chain is polling. **Redesign count: 0** for this arm; the instrument's count stays **2**
(the grader is untouched; a third ends the step). Changing `WRITER` or `kind()` after the freeze
commit is a redesign and is counted.

## Sets and zero-GPU numbers

*Written after the freeze commit — see the next commit on this branch.*
