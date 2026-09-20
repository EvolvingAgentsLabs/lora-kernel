# F3 — the role pack (pre-registered 2026-09-20, zero GPU)

**Question.** What a member *is* lives in five places today — `train_pool.POOL` (corpus, band, tags,
argument keys, prompt), `route.REGIONS` and `route.ROLES` (keys, role, local/out), the generators (the
tool schema the block is rendered from), the proxy's flags (what may leave) and `releases/*.json`
(hashes, verdict). **Can one declarative directory per role carry all of it, checked against the
artefacts, without losing anything the member's corpus taught** ([`FRAMEWORK.md`](../../docs/FRAMEWORK.md)
§6, §7.3)?

**The format.** `roles/<role>/role.toml`, read with the standard library's `tomllib`:
`id` · `[member]` name, adapter, release manifest, status · `[corpus]` path, sha256, band · `[prompt]`
a *reference* to the object the corpus was generated with, plus its sha256 — never a copy ·
`[tools]` the schema the block is rendered from (a reference), the surface in order, the argument
keys in order, the sha256 of the rendered block · `[suites]` · `[route]` role ids, keys, local/out ·
`[answer_policy]` kind → writer · `[egress]` where the unmeasured goes (frontier | person | refuse) and
whether the member may ever leave · `[library]` optional: root, sha256 of its tree, sites · `[loop]`
the path its release was measured on (inline | tool_calls).

**The gate, fixed before building.** For the two released members, `email-full` and `desk-commitment`:

| clause | how it is checked |
|---|---|
| G1 served prompt | the pack's prompt **is** (`==`) what the proxy serves under `--member-prompt`: `openai_proxy._load_surfaces()` then `POOL_SYSTEM[name]` — the proxy's own function, not a copied string |
| G2 served tool block | the pack's schema, renamed the way an agent runtime renames it (`mcp__<server>__<name>`), pruned with the pack's surface and keys by `tool_calls.prune`, rendered by `tools_to_instruction(arity=True, enums=False)` — the two calls the proxy makes — is **byte-identical** to the block in the corpus's first row, and to the block in every row |
| G3 surface and keys | equal, in order, what the corpus teaches: tags read off the offered block, keys read off the calls the corpus writes |
| G4 hashes | corpus sha256 == the file == the release manifest's; manifest name/corpus/base agree with the pack |
| G5 derivation | `rolepack.pool()` == `train_pool.POOL` and `rolepack.regions()` / `rolepack.roles()` == `route.REGIONS` / `route.ROLES`, for these two members, as Python equality |
| G6 the linter can fail | a tampered corpus hash, argument keys reordered, a prompt hash that drifted, a surface re-sorted — each makes `python -m rolepack.lint` exit non-zero naming the clause |

**Falsifier (FRAMEWORK §7.3).** A member cannot be expressed without losing part of what its corpus
taught: any of G1–G5 cannot be made to hold without adding to the format something that is not a
declaration (code, a special case keyed on a member's name).

**The third pack.** `nursing-walks` — the memory's member — is attempted. It was never released (W5 did
not pass), runs under the referee and not through the proxy, and carries a library, site layers and an
answer policy (W5d, frozen, **not yet run**). If it fits, it ships marked `status = "unreleased"` and
its policy `[spec]`. If something does not fit, this brief's result says exactly what, and the format
is not bent.

**Not in this step.** `POOL`, `REGIONS` and `ROLES` are not deleted: the packs are *shown equal* to
them; making the packs the single source of truth is a later change and the result lists what it needs.

**Redesign count: 0.**

## Result **[ran]** 2026-09-20 · the gate PASSED; all three members are expressible; one thing the pack can say that nothing can serve yet

Zero GPU. `python -m rolepack.gate` → `gate.json`; `python -m rolepack.lint roles/` → 3 packs, 0 findings.

| clause | `triage` (`email-full`, 598 rows) | `desk` (`desk-commitment`, 600 rows) |
|---|---|---|
| G1 the prompt **is** `openai_proxy.POOL_SYSTEM[member]` | ✓ | ✓ |
| G2 the block, pruned and rendered by the proxy's two calls, is byte-identical in **every** row | ✓ | ✓ |
| G3 surface and keys, in order, are the corpus's | ✓ | ✓ |
| G4 corpus sha256 = the file = the release manifest's | ✓ | ✓ |
| G5 `rolepack.pool()` == `POOL`; `regions()`/`roles()` == `REGIONS`/`ROLES` for these members | ✓ | ✓ |

G6, the linter failing on a copy of `roles/`: a tampered corpus hash → `hashes`; a prompt hash that
drifted → `prompt`; another member's prompt referenced → `prompt`; the surface re-sorted → `surface`
and `block`; a tag's key replaced → `keys`. (*Reordered* keys cannot be built from these members: every
tag is written with one key. The clause compares ordered lists, and a member with two keys would
exercise it.) Nine more breakages in `tests/test_rolepack.py`.

**The linter found something before it was finished:** the first `desk` pack said `suite = "desk"`;
the release manifest records `desk:commitment`. Fixed in the pack; the manifest is the record.

**The falsifier did not fire** — no member needed code or a special case in the format. It needed
three *declarations* the first draft did not have, all added as optional fields:

- `[tools.attributes]` — `nursing-walks` writes `<search shelf=wiki>` 479 times; an attribute on the
  tag is not a key in its body, and `args` could not say it.
- `[member.evidence]` + `adapter_sha256` — an unreleased member has no manifest, so its adapter's
  identity is pinned to the run that recorded it.
- `[answer_policy] source` — the frozen W5d table is *referenced*; the pack's own lines must equal it.

**What a pack can say and nothing can serve yet.** `nursing-walks` declares `[loop] referee =
"memory.runtime:Conversation"`: its verbs are executed by the referee, server-side, with a carried page
in 270 of 600 user turns. The proxy only knows the other loop — the *caller* executes tools. So the
pack is complete as a declaration and **the member is not servable through the API**. The same field
says something uncomfortable about the two released members: `measured = "inline"` — they were released
on results written inline, and the proxy serves them through `tool_calls`, a path measured to cost
0.992 → 0.808 **[ran]** P55. The pack now states the gap instead of hiding it.

**Before packs can be the single source of truth** (not done here, by the brief):
1. `train_pool.POOL`, `route.REGIONS`, `route.ROLES` become `rolepack.pool/regions/roles(load_all())`
   — a three-line change each, but `fluids-full` (in `REGIONS`, marked `out`, no corpus on `main`
   until arm 0c's restore) needs a pack or a documented exception first.
2. The proxy's `--local` and `--fallback` read `[egress]`; today the field is declared and unread.
3. `[answer_policy]` is read by a serving path; today only W5d's runner applies it.
4. The proxy gains the referee loop, or `[loop]` stays a statement of what is not served.
5. `prompt_sha` in the manifests hashes a *rendered* prompt (template + case), so it cannot be checked
   without a tokenizer; the pack hashes the prompt text. One of the two should be recorded both ways.

**Redesign count: 0.**
