# P2a — does a pool member answer a paraphrase of its task?

**Written 2026-10-04, after the instrument was frozen (code and tests) and before any GPU is bought.** Step 2 of
[`docs/review/moe-distillation-and-spotlight.md`](../../docs/review/moe-distillation-and-spotlight.md).

## What and why

ROUTE0's factored router keeps a request local only when its task paragraph is, verbatim, a task its member was trained
on. A paraphrase leaves for the frontier by design: B3, 0/120 kept local **[ran]**
[`results/ROUTE0-factored-router-20261002`](../ROUTE0-factored-router-20261002/BRIEF.md). That brief named the reason:
*the members were trained on one wording each, and serving a paraphrase locally would bet on the member*. The bet was
never measured. ROUTE2 (a probe router on the E4B's hidden state that keeps paraphrases local) is worth building only if
the members **do** answer paraphrases; if they do not, paraphrases are leaving correctly and ROUTE2 has nothing to win.
This run is that measurement and nothing else: no router, no training.

**Model and provider.** One Colab **L4**, vLLM (the chain installs `vllm>=0.28`), base `google/gemma-4-E4B-it`, bf16,
thinking off in every render, both released adapters served together as LoRAs in one server:

| member | release | adapter dir in the tarball | sha256 (safetensors) | carried from |
|---|---|---|---|---|
| `email-full` | `releases/email-full@v3.json` (M1b) | `adapters/email-full-g4` | `725ad8dd…76b1` | `~/lora-kernel-adapters/M1b-pool-gemma4-20260925/adapters.tgz` |
| `desk-commitment` | `releases/desk-commitment@v3.json` (M1d) | `adapters/desk-commitment-g4b` | `dd8e2ba0…c122` | `~/lora-kernel-adapters/M1d-desk-both-g4b/adapters.tgz` |

Both hashes re-checked against the manifests from the tarballs **[ran]** 2026-10-04; the runner re-hashes them on the VM
and stops if either differs. The chain carries one file, `results/P2A-paraphrase-headroom-20261004/adapters.tgz`
(258 MB, git-ignored), built from those two (M1b's tarball also holds the superseded `desk-commitment-g4` — not carried):

```bash
T=$(mktemp -d); R=results/P2A-paraphrase-headroom-20261004
tar xzf ~/lora-kernel-adapters/M1b-pool-gemma4-20260925/adapters.tgz -C $T adapters/email-full-g4
tar xzf ~/lora-kernel-adapters/M1d-desk-both-g4b/adapters.tgz -C $T adapters/desk-commitment-g4b
tar czf $R/adapters.tgz -C $T adapters/email-full-g4 adapters/desk-commitment-g4b
```

## The instrument — `training/harness/paraphrase_arm.py`, the release's path changed in one line

How the released scores were measured **[read]** `training/harness/pool_base.py::main` (M1b, M1d):

- **cases** — `training/harness/suites.py::load(name).cases(eval_n, eval_seed)`: `email` 475 (`_email`, inbox seed
  717171), `desk:commitment` 240 and `desk:commitment_deep` 240 (`_desk`, `training/email/desk.py::generate`, seed
  424242). A case's `user` is the listing, a blank line, and the **task line**: `Is this important?` /
  `What date did you commit to in this thread?` / the same plus `If you committed more than once, the latest one counts.`
- **render** — `suite.system` + `suite.user_text(case)` (the user turn, a blank line, the tool block the corpus taught)
  through the base's chat template, `enable_thinking=False`: the member's own prompt, corpus mode.
- **loop** — `training/harness/accept_rank.py::draft_arm` → `run_chain`: generate to a closing tag, answer the call for
  real from `case.ctx`, continue, ≤ 6 calls.
- **grader** — `case.verify(suite.parse(final span))`: email `said == truth` on IMPORTANT / NOT IMPORTANT
  (`suites._email.parse`); desk `training/email/desk.py::correct`, exactly one date and the right one.

`paraphrase_arm` runs **that** function on **those** cases twice per suite: **verbatim** (the released condition) and
**paraphrase** — the same `Case` object with only its last line replaced (`paraphrased`), `ctx`, `truth`, `verify` the
same objects. Paraphrases are drawn round-robin by case position from a fixed list per suite:

- `email` — 19, ROUTE0's B3 wordings (`results/ROUTE0-factored-router-20261002/make_sets.py`, written blind to that
  router), one dropped: *"Can I safely ignore this email?"* inverts the polarity — a correct "Yes" holds no
  IMPORTANT / NOT IMPORTANT and the release grader would score phrasing, not the member.
- `desk:commitment` — 18, ROUTE0's B3 wordings unchanged.
- `desk:commitment_deep` — 16, new, each carrying the band's rule (the most recent promise counts); without it the
  paraphrase asks another question and a right answer to it would be graded wrong.

None of the 53 occurs in its member's corpus (`corpus_leaks`, case-insensitive) **[ran]** zero GPU,
`--zero-gpu` 2026-10-04: 475 / 240 / 240 cases, 0 leaks. Why not ROUTE0's B3 rows themselves: they carry no `ctx` and
no truth, so the release grader cannot score them; their wordings on the release's held-out cases can.

Order on the card: G1 identity per member (`verify_substrate.identity`, 2 of 3 probes differ, none empty) — not applied →
stop, nothing scored; then the verbatim prompts of every case are hashed and compared with the `prompt_sha` the release
recorded (reported); then per member and suite verbatim, paraphrase. Every record persisted as it lands
(`p2a.json`, resumable — an errored case is redrafted, a finished one never), `[p2a]` lines per gate and arm, `draft_arm`'s `[rank] arm … n/N correct k` every 25 cases.
`tests/test_paraphrase_arm.py` (zero GPU, `fake_vllm` with a scripted model) holds: only the task line changes, the
rest of the case byte-identical; the records are graded by `case.verify(suite.parse(…))` through `draft_arm`; the
verdict reads the pair; resume drafts nothing twice.

## Arms

| arm | cases | condition |
|---|---|---|
| `email-full · email · verbatim` | 475 | released task line |
| `email-full · email · paraphrase` | 475 | the 19 wordings, round-robin |
| `desk-commitment · desk:commitment_deep · verbatim` | 240 | released task line |
| `desk-commitment · desk:commitment_deep · paraphrase` | 240 | the 16 wordings |
| `desk-commitment · desk:commitment · verbatim` | 240 | released task line |
| `desk-commitment · desk:commitment · paraphrase` | 240 | the 18 wordings |

Not bought now: the bare base on paraphrases (the attribution arm — whether a paraphrase loss is the adapter's or the
base's) — only once there is an effect to attribute. Headroom, said first: the question is whether a paraphrase
*loses*, so the room that matters is below verbatim, and verbatim sits at 469/475, 239/240, 240/240 in the release. The
shallow desk band does not tell the member from the bare base (both 240/240, M1b **[ran]**); the deep band (base 83)
carries the desk signal. Sensitivity: with no case won back, a loss of **6** cases is $p = 2\cdot 2^{-6} = 0.031$ —
1.3 % of email, 2.5 % of a desk band.

## Verdict (fixed here, `paraphrase_arm.verdict`)

Per suite $s$, paired by case id, $b$ = only the paraphrase right, $c$ = only verbatim right, exact two-sided sign test
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$ (FOUNDATIONS §9.2, `release_gate.pair`); drop
$\Delta_s = \mathrm{acc}_{\text{verbatim}} - \mathrm{acc}_{\text{paraphrase}}$ in accuracy points.

| verdict | condition | reading |
|---|---|---|
| **MEMBERS ANSWER PARAPHRASES** | every suite of both members: $\Delta_s \le 0.05$ **and** not a REGRESSION ($p < 0.05$, $c > b$) | ROUTE2 (a router that keeps paraphrases local) is worth building |
| **PARAPHRASES COST** | any suite of any member is a REGRESSION | paraphrases correctly leave to the frontier; ROUTE2 is not built |
| **UNRESOLVED** | otherwise ($\Delta_s > 0.05$ without significance) | ROUTE2 not built on this evidence |
| **VOID** | G1 not applied for a member; any transport error left in an arm; or a verbatim arm a REGRESSION against the release's own records (`M1b pool_base.json`, `M1d shallow.json`, `deep.json`) — the serving path is not the release's | nothing is read |

Beside, never gated: per-paraphrase scores, the deep band by depth, `undecided` (a final span with no verdict word —
format) versus a wrong verdict (content), and the render check (verbatim prompt sha against the release's).

## Stopping condition

One scoring session (`SESSIONS=2` only so a session that dies mid-run resumes from its records; a second session never
re-scores a finished arm). The cases, the paraphrase lists, the grader and the table above do not change after the
card starts. A VOID is repaired once, in the instrument, and rerun; a second VOID ends P2a as unmeasured. Redesign
counter: 0. Ceiling: one L4 session (~60 min; ~10 min of scoring at M1d's 240 cases / 45 s).

## Launch (not run)

`BRANCH` must be pushed first — the chain clones it from GitHub.

```bash
R=results/P2A-paraphrase-headroom-20261004
GPU=L4 BRANCH=p2a-20261004 RUN_DIR=$R MODULE=training.harness.paraphrase_arm \
  MARGS="--concurrency 8" RESULTS_NAME=p2a.json BASE=google/gemma-4-E4B-it SESSIONS=2 \
  training/harness/chain_serve.sh
```

The chain uploads `$R/adapters.tgz` (no `SKIP_ADAPTERS`), unpacks it to `adapters/`, runs
`python -m training.harness.paraphrase_arm --base google/gemma-4-E4B-it --concurrency 8 --out p2a.json`, watches
`[p2a]` and `[rank]` lines (both in the peek filter), and stops on `"finished"` in `p2a.json`.

## Result *(written after the run)*
