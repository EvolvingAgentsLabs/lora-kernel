"""The role pack: one directory per role, declaring everything a member is — and nothing it is not.

WHY IT EXISTS (docs/FRAMEWORK.md §6). What a member is lived in five places: `train_pool.POOL`,
`route.REGIONS` / `route.ROLES`, the generators' tool schemas, the proxy's flags and `releases/`. A third
party cannot fill in five places without reading the code. A pack is the one place — `roles/<role>/role.toml`
— and **every line of it is checked against an artefact** by `rolepack.lint`: a pack never *says* what the
prompt is, it names the object the corpus was generated with and the hash it must have.

A PACK DECLARES, IT DOES NOT COPY. The prompt is a reference (`module:ATTR`) plus a sha256; the tool block
is a schema reference, a surface in order, argument keys in order, and the sha256 of the block those
render to. The copy is what drifts (CLAUDE.md §3: *generators call `render_tools`; the copy is what drifted*).

Nothing here trains, serves or scores.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HEAD = "The following tools are available"
CALL = re.compile(r"<([A-Za-z_][\w-]*)>([^<]*)</\1>")
WRITERS = ("adapter", "base")
EGRESS = ("frontier", "person", "refuse")
LOOPS = ("inline", "tool_calls")
STATUS = ("released", "unreleased")


class PackError(ValueError):
    pass


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_tree(root: str | Path) -> str:
    """One hash for a library: every file's relative path and bytes, in sorted order."""
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.name != ".DS_Store":
            h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def resolve(ref: str):
    """`package.module:ATTR` → the object. A reference, so the pack can never hold a stale copy."""
    if ":" not in ref:
        raise PackError(f"{ref!r} is not a `module:ATTR` reference")
    mod, attr = ref.split(":", 1)
    obj = getattr(importlib.import_module(mod), attr)
    return obj() if callable(obj) else obj


@dataclass(frozen=True)
class RolePack:
    path: Path
    raw: dict = field(repr=False)

    # --- the declaration, by field -------------------------------------------------------------
    @property
    def id(self) -> str: return self.raw["id"]
    @property
    def member(self) -> str: return self.raw["member"]["name"]
    @property
    def adapter(self) -> str: return self.raw["member"]["adapter"]
    @property
    def status(self) -> str: return self.raw["member"].get("status", "released")
    @property
    def release(self) -> str | None: return self.raw["member"].get("release")
    @property
    def corpus(self) -> str: return self.raw["corpus"]["path"]
    @property
    def band(self) -> tuple[int, int]: return tuple(self.raw["corpus"]["band"])
    @property
    def surface(self) -> list[str]: return list(self.raw["tools"]["surface"])
    @property
    def args(self) -> dict[str, list[str]]: return {k: list(v) for k, v in self.raw["tools"].get("args", {}).items()}
    @property
    def attributes(self) -> dict[str, list[str]]:
        """Attributes a tag is written WITH — `<search shelf=wiki>` — as distinct from keys in its body."""
        return {k: list(v) for k, v in self.raw["tools"].get("attributes", {}).items()}
    @property
    def keys(self) -> tuple[str, ...]: return tuple(self.raw["route"]["keys"])
    @property
    def roles(self) -> list[str]: return list(self.raw["route"]["roles"])
    @property
    def serve(self) -> str: return self.raw["route"]["serve"]

    # --- what the declaration resolves to ------------------------------------------------------
    def prompt(self) -> str:
        return resolve(self.raw["prompt"]["source"])

    def schema(self) -> list[dict]:
        return resolve(self.raw["tools"]["schema"])

    def block(self, server: str = "lora-inbox") -> str:
        """The tool block as the proxy produces it: the schema under the names an agent runtime
        gives it, pruned to the member's surface and keys, rendered. The two calls are the proxy's."""
        from training.harness.tool_calls import prune, tools_to_instruction
        offered = [{"type": "function", "function": {**t["function"],
                                                     "name": f"mcp__{server}__{t['function']['name']}"}}
                   for t in self.schema()]
        kept, _, _ = prune(offered, self.surface, self.args or None)
        return tools_to_instruction(kept, arity=True, enums=False)


def load(path: str | Path) -> RolePack:
    path = Path(path)
    f = path / "role.toml" if path.is_dir() else path
    raw = tomllib.loads(f.read_text())
    for section in ("member", "corpus", "prompt", "tools", "suites", "route", "answer_policy", "egress", "loop"):
        if section not in raw:
            raise PackError(f"{f}: no [{section}]")
    if "id" not in raw:
        raise PackError(f"{f}: no id")
    return RolePack(f.parent, raw)


def load_all(root: str | Path = "roles") -> dict[str, RolePack]:
    packs = {}
    for f in sorted(Path(root).glob("*/role.toml")):
        p = load(f)
        if p.id in packs:
            raise PackError(f"{f}: the role id {p.id!r} is declared twice")
        if p.id != f.parent.name:
            raise PackError(f"{f}: id {p.id!r} is not its directory's name")
        packs[p.id] = p
    return packs


# --- what a corpus teaches, read off the corpus ------------------------------------------------

def corpus_blocks(corpus: str | Path) -> set[str]:
    """Every distinct offered tool block in the corpus — one, when the corpus teaches one surface."""
    out = set()
    for line in Path(corpus).read_text().splitlines():
        if not line.strip():
            continue
        for m in json.loads(line)["messages"]:
            t = m.get("content") or ""
            if m.get("role") == "user" and HEAD in t:
                out.add(t[t.index(HEAD):])
    return out


def corpus_surface(corpus: str | Path) -> list[str]:
    blocks = corpus_blocks(corpus)
    if len(blocks) != 1:
        raise PackError(f"{corpus}: {len(blocks)} distinct tool blocks — a surface is one block")
    return [m.group(1) for m in CALL.finditer(next(iter(blocks)))]


def corpus_keys(corpus: str | Path) -> dict[str, list[str]]:
    """The argument keys each tag is WRITTEN with, in the order first seen, from assistant turns."""
    seen: dict[str, list[str]] = {}
    for line in Path(corpus).read_text().splitlines():
        if not line.strip():
            continue
        for m in json.loads(line)["messages"]:
            if m.get("role") != "assistant":
                continue
            for c in CALL.finditer(m.get("content") or ""):
                for k in re.findall(r"([\w.\-]+)\s*=", c.group(2)):
                    if k not in seen.setdefault(c.group(1), []):
                        seen[c.group(1)].append(k)
    return seen


ATTR = re.compile(r"<([A-Za-z_][\w-]*)((?:\s+[\w-]+=[^\s>]+)+)\s*>")


def corpus_attributes(corpus: str | Path) -> dict[str, list[str]]:
    """The attributes each tag is written with in assistant turns: `<search shelf=harness>` → shelf."""
    seen: dict[str, list[str]] = {}
    for line in Path(corpus).read_text().splitlines():
        if not line.strip():
            continue
        for m in json.loads(line)["messages"]:
            if m.get("role") != "assistant":
                continue
            for c in ATTR.finditer(m.get("content") or ""):
                for k in re.findall(r"([\w-]+)=", c.group(2)):
                    if k not in seen.setdefault(c.group(1), []):
                        seen[c.group(1)].append(k)
    return seen


# --- the registries the code reads today, derived from the packs -------------------------------

def pool(packs: dict[str, RolePack]) -> dict:
    """`train_pool.POOL`, from the packs that declare a served member."""
    from training.harness import contract
    out = {}
    for p in packs.values():
        if p.status != "released":
            continue
        out[p.adapter] = contract.text(p.corpus, contract.band(*p.band), note=p.raw["corpus"].get("note", ""),
                                       tags=p.surface, args=p.args, system=p.prompt())
    return out


def regions(packs: dict[str, RolePack]) -> dict:
    from training.harness.route import Region
    return {p.member: Region(p.member, p.keys, p.serve) for p in packs.values() if p.status == "released"}


def roles(packs: dict[str, RolePack]) -> dict[str, str]:
    return {r: p.member for p in packs.values() if p.status == "released" for r in p.roles}
