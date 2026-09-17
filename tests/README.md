# The tests, and the formula each one guards

This project's rule: **a test documents the mathematics it protects.** A check that
cannot be written as a formula is measuring phrasing, and the repository's history
says such checks get deleted rather than loosened. The derivations live in
[`docs/FOUNDATIONS.md`](../docs/FOUNDATIONS.md); the map from test file to formula is
here so that a failing test names the identity that broke.

| test file | the identity it guards | FOUNDATIONS |
|---|---|---|
| `test_accept_rank.py` | acceptance at $T=0$: token $i$ accepted **iff** its rank under the target is 1; $\alpha = \text{accepted}/\text{tokens}$ over all decision tokens, $\alpha_{\text{tags}}$, $\alpha_{\text{verdict}}$, $\alpha_{\text{lcp}}$; the harness-supplied `= {result}` text is in **no** span; the gates: $Q(T)$ must beat $\max Q(E)$ on a paired test, the grades must be resolved by the verifier before the target is served, and the ordering verdict is SUPPORTED / FALSIFIED / UNRESOLVED; nested subsets $\mathcal D_{75}\subset\mathcal D_{200}$ with balance in $[0.3, 0.7]$; the stop preflight is decided by the mechanism, and a positional tag body is keyed by parameter count | §6.3, §7.1–7.4, §8.3, §5.4 |
| `test_prune.py` | the tool surface a member is offered equals, **byte for byte**, the block its corpus taught — including order where a corpus teaches one; a namespaced name matches on its last segment; two servers offering the same tail are refused rather than guessed; a call leaves under the caller's name | §4.4 (the corpus is the served prompt) |
| `test_contract.py` | a member's band is read off its corpus, never asserted: $\min$/$\max$ steps over 600 rows, and 0 is a legal floor | §8.3 |
| `test_bar.py`, `test_paired.py` | the exact two-sided sign test on discordant pairs, $p=\min(1,2\Pr[\mathrm{Bin}(n_d,\tfrac12)\ge\max(u,n_d-u)])$; the majority bar $\max(\pi,1-\pi)$; power $\Pr[\mathrm{Bin}(n,\pi_0+\delta)\ge t]$ and the $n$ that resolves $\delta$ | §9 |
| `test_ceiling.py` | the best predictor that sees only what a case shows; negative room indicts the grouping, not the model | §9.4 |
| `test_tokenizer_compat.py` | speculative decoding lives in id space: the id map must agree, merges may differ, target-only ids are guaranteed rejections, an id meaning two things disqualifies the pair; the report names **both** vocabularies | §3.2–3.3 |
| `test_email.py`, `test_desk.py` | $y(m) = \neg\text{automated}\wedge[w+a+s+f\ge2]$; the listing carries none of $w,a,f$, so the best listing-only rule scores exactly the majority class; the desk's answer is never in its prompt | §8.1–8.2 |
| `test_draft_headroom.py`, `test_desk_profile.py` | headroom before a treatment: the target must clear the base by a margin `resolvable` at the run's $n$; a saturated cell contributes nothing | §9.4 |
| `test_lora_matrix.py` | C18: an adapter is *applied* iff the served text differs from the base's; a control base with a known answer is what makes the subject's answer readable | §5.2 |
| `test_mermaid.py` | every diagram class has a `classDef`; **no node draws a frontier as the speculative target** — it shares neither ids (C3) nor forced logprobs (C2) | §3.2, §6.5 |
| `test_chain_scripts.py` | every prefix a runner prints is watched by the chain (a run nobody can see cannot be stopped early); every chain that can train installs what the trainer imports; a chain runs from a copy of itself | — (instrument hygiene) |
| `test_suite_gates.py` | a suite has a difficulty axis, depth is not the region, and exactly one of *asking is a decision* / *the answer is not a copy* | §8.2 |

**What no test can guard yet:** $\alpha$ against a target, and the ordering verdict —
because neither has been measured (FOUNDATIONS §11). The tests above make sure that
when they are, the number will mean what the formula says.
