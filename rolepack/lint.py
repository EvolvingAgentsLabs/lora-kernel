"""Check every line of every role pack against the artefact it names.

    python -m rolepack.lint roles/          # exit 0 when there is nothing to report

A finding names its clause, so a failing pack says WHICH promise it broke:

    prompt    the referenced prompt has the declared sha256 — and, for a released member, IS the
              prompt the proxy serves under --member-prompt (the proxy's own table, not a copy)
    block     the schema, renamed as a runtime renames it, pruned and rendered by the proxy's two
              calls, has the declared sha256 and is byte-identical to the block in EVERY corpus row
    surface   the declared tags, in order, are the corpus's offered block
    keys      the declared argument keys, in order, are the ones the corpus writes
    hashes    the corpus file has the declared sha256; a released member's manifest agrees on name,
              corpus, corpus hash
    contract  the record derived from the pack passes `contract.validate`
    route     roles are declared once across packs; a released member has keys; serve is local|out
    policy    answer_policy writers and egress values are from the closed sets
    loop      the path the release was measured on is declared
    library   when declared: the tree has the declared hash and the named sites exist
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import rolepack
from rolepack import PackError


def lint_pack(p: rolepack.RolePack) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    add = lambda clause, msg: out.append((clause, msg))
    raw = p.raw

    if p.status not in rolepack.STATUS:
        add("route", f"member.status {p.status!r} is not one of {rolepack.STATUS}")

    # --- prompt ---
    try:
        prompt = p.prompt()
        if not isinstance(prompt, str) or not prompt.strip():
            add("prompt", f"{raw['prompt']['source']} is not a non-empty string")
        elif rolepack.sha_text(prompt) != raw["prompt"]["sha256"]:
            add("prompt", f"{raw['prompt']['source']} has sha256 {rolepack.sha_text(prompt)[:16]}…, "
                          f"the pack declares {raw['prompt']['sha256'][:16]}… — the prompt drifted")
        elif p.status == "released":
            from training.harness import openai_proxy
            openai_proxy._load_surfaces()
            served = openai_proxy.POOL_SYSTEM.get(p.member)
            if served != prompt:
                add("prompt", f"the proxy serves {p.member} another prompt than the pack references")
    except Exception as e:                                   # a reference that does not resolve is a finding
        add("prompt", f"{raw['prompt'].get('source')!r} does not resolve: {e!r}")

    # --- block, surface, keys ---
    try:
        blocks = rolepack.corpus_blocks(p.corpus)
        block = p.block(raw["tools"].get("server", "lora-inbox"))
        if rolepack.sha_text(block) != raw["tools"]["block_sha256"]:
            add("block", f"the rendered block has sha256 {rolepack.sha_text(block)[:16]}…, the pack declares "
                         f"{raw['tools']['block_sha256'][:16]}…")
        if blocks != {block}:
            add("block", f"the rendered block is not byte-identical to the corpus's "
                         f"({len(blocks)} distinct block(s) in {p.corpus})")
        taught = rolepack.corpus_surface(p.corpus) if len(blocks) == 1 else None
        if taught is not None and taught != p.surface:
            add("surface", f"declared {p.surface}, the corpus offers {taught} — order is part of it")
        written = {t: k for t, k in rolepack.corpus_keys(p.corpus).items() if t in p.surface}
        if written != p.args:
            add("keys", f"declared {p.args}, the corpus writes {written} — order is part of it")
        attrs = {t: k for t, k in rolepack.corpus_attributes(p.corpus).items() if t in p.surface}
        if attrs != p.attributes:
            add("keys", f"declared tag attributes {p.attributes}, the corpus writes {attrs}")
    except Exception as e:
        add("block", f"could not render or read the block: {e!r}")

    # --- hashes ---
    if not Path(p.corpus).exists():
        add("hashes", f"no corpus at {p.corpus}")
    elif rolepack.sha_file(p.corpus) != raw["corpus"]["sha256"]:
        add("hashes", f"{p.corpus} has sha256 {rolepack.sha_file(p.corpus)[:16]}…, the pack declares "
                      f"{raw['corpus']['sha256'][:16]}…")
    if p.status == "released":
        if not p.release or not Path(p.release).exists():
            add("hashes", f"a released member names no manifest that exists ({p.release})")
        else:
            man = json.loads(Path(p.release).read_text())
            for key, want in (("name", p.member), ("corpus", p.corpus), ("corpus_sha256", raw["corpus"]["sha256"])):
                if man.get(key) != want:
                    add("hashes", f"{p.release}: {key} is {man.get(key)!r}, the pack says {want!r}")
            if man.get("suite") and man["suite"] != raw["suites"].get("release"):
                add("hashes", f"{p.release}: suite {man['suite']!r}, the pack says {raw['suites'].get('release')!r}")
    elif p.release:
        add("hashes", "an unreleased member must not name a release manifest")

    # --- contract ---
    try:
        from training.harness import contract
        contract.validate(p.adapter, contract.text(p.corpus, contract.band(*p.band), tags=p.surface,
                                                   args=p.args, system=p.prompt()))
    except Exception as e:
        add("contract", repr(e))

    # --- route, policy, loop ---
    if p.serve not in ("local", "out"):
        add("route", f"route.serve {p.serve!r} is not local|out")
    if p.status == "released" and not p.keys:
        add("route", "a released member declares no keys: nothing could confirm a request is in its region")
    ap = raw["answer_policy"]
    if "default" not in ap:
        add("policy", "answer_policy has no default writer")
    META = ("marker", "source", "classifier")
    for kind, w in ap.items():
        if kind not in META and w not in rolepack.WRITERS:
            add("policy", f"answer_policy.{kind} = {w!r} is not one of {rolepack.WRITERS}")
    if ap.get("source"):
        try:
            frozen = rolepack.resolve(ap["source"])
            mine = {k: w for k, w in ap.items() if k not in META and k != "default"}
            if mine != frozen:
                add("policy", f"answer_policy says {mine}, {ap['source']} says {frozen} — the frozen table is the source")
        except Exception as e:
            add("policy", f"{ap['source']!r} does not resolve: {e!r}")
    if ap.get("classifier"):
        try:
            mod, attr = ap["classifier"].split(":")
            getattr(__import__("importlib").import_module(mod), attr)
        except Exception as e:
            add("policy", f"classifier {ap['classifier']!r} does not resolve: {e!r}")
    ev = raw["member"].get("evidence")
    if p.status == "unreleased" and ev:
        try:
            rec = json.loads(Path(ev["results"]).read_text())
            m = rec["members"][ev["arm"]]
            if m.get("corpus_sha256") != raw["corpus"]["sha256"]:
                add("hashes", f"{ev['results']}: the {ev['arm']} adapter was trained on another corpus than the pack names")
            if m.get("adapter_sha256") != raw["member"].get("adapter_sha256"):
                add("hashes", f"{ev['results']}: adapter sha256 differs from the pack's")
        except Exception as e:
            add("hashes", f"evidence {ev} cannot be read: {e!r}")
    for name, spec in raw["suites"].items():
        if isinstance(spec, dict):
            if not Path(spec["path"]).exists() or rolepack.sha_file(spec["path"]) != spec["sha256"]:
                add("hashes", f"suite {name}: {spec['path']} is missing or does not have the declared sha256")
    eg = raw["egress"]
    if eg.get("unmeasured") not in rolepack.EGRESS:
        add("policy", f"egress.unmeasured {eg.get('unmeasured')!r} is not one of {rolepack.EGRESS}")
    if not isinstance(eg.get("member_may_leave"), bool):
        add("policy", "egress.member_may_leave must be true or false")
    if raw["loop"].get("measured") not in rolepack.LOOPS:
        add("loop", f"loop.measured {raw['loop'].get('measured')!r} is not one of {rolepack.LOOPS}")

    # --- library ---
    lib = raw.get("library")
    if lib:
        root = Path(lib["root"])
        if not root.is_dir():
            add("library", f"no library at {root}")
        else:
            if rolepack.sha_tree(root) != lib["sha256"]:
                add("library", f"{root} has tree hash {rolepack.sha_tree(root)[:16]}…, the pack declares {lib['sha256'][:16]}…")
            for site in lib.get("sites", []):
                if not (root / "site" / f"{site}.md").exists():
                    add("library", f"site {site!r} is not in {root}/site")
    return out


def lint(root: str | Path = "roles") -> dict[str, list[tuple[str, str]]]:
    try:
        packs = rolepack.load_all(root)
    except (PackError, KeyError) as e:
        return {"<load>": [("load", repr(e))]}
    found = {name: lint_pack(p) for name, p in packs.items()}
    seen: dict[str, str] = {}
    for name, p in packs.items():
        for r in p.roles:
            if r in seen:
                found[name].append(("route", f"role {r!r} is already declared by {seen[r]}"))
            seen[r] = name
    return found


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    found = lint(argv[0] if argv else "roles")
    n = 0
    for name, items in found.items():
        print(f"[pack] {name}: {'ok' if not items else f'{len(items)} finding(s)'}")
        for clause, msg in items:
            n += 1
            print(f"[pack]   {clause}: {msg}")
    print(f"[pack] {len(found)} pack(s), {n} finding(s)")
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
