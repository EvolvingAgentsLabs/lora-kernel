#!/usr/bin/env python3
r"""Make a document's mathematics survive GitHub's Markdown, and check that it does.

GitHub runs Markdown BEFORE the math renderer, so inside `$…$` and `$$…$$` a backslash before punctuation is eaten
(`\,` `\;` `\!` `\\` `\{` `\#`), `<` is escaped twice, `*` can pair into emphasis and `|` splits a table cell — the
FOUNDATIONS render showed every one of them (2026-09-27). Checked against GitHub's own renderer (`POST /markdown`):
a ```` ```math ```` fence reaches the renderer byte for byte, and in inline math `\ `, `\lt`, `\gt`, `\ast`, `\vert`,
`\lbrace`, `\rbrace` survive. So:

    display  every `$$…$$` becomes a ```` ```math ```` fence (indented like its list item)
    inline   \, \; \: → '\ '   \! → ''   \{ \} → \lbrace \rbrace   \#\{…\} → \lvert\lbrace…\rbrace\rvert
             < → \lt   > → \gt   * → \ast   | → \vert (in table rows)
    both     \operatorname{X} → \mathrm{X} (not allowed by GitHub's renderer)

    python3 scripts/fix-math.py docs/FOUNDATIONS.md docs/es/FOUNDATIONS.md          # rewrite in place
    python3 scripts/fix-math.py --check docs/FOUNDATIONS.md                          # render through GitHub and compare
    python3 scripts/fix-math.py --display-only docs/PLAN.md    # only $$ blocks, where the text also has dollar amounts
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)
INLINE = re.compile(r"(?<![\\$])\$(?!\$)([^$\n]+?)(?<![\\$])\$(?!\$)")


def _opname(m: str) -> str:
    return re.sub(r"\\operatorname\{([^}]*)\}", lambda g: r"\mathrm{" + g.group(1).replace("-", r"\text{-}") + "}", m)


def fix_inline(m: str, in_table: bool) -> str:
    m = _opname(m)
    if r"\#\{" in m:
        m = m.replace(r"\#\{", r"\lvert\lbrace ").replace(r"\}", r"\rbrace\rvert ")
    for a, b in ((r"\,", r"\ "), (r"\;", r"\ "), (r"\:", r"\ "), (r"\!", ""), (r"\{", r"\lbrace "), (r"\}", r"\rbrace "),
                 (r"\#", r"\sharp "), ("<", r"\lt "), (">", r"\gt "), ("*", r"\ast ")):
        m = m.replace(a, b)
    if in_table:
        m = m.replace(r"\|", r"\Vert ").replace("|", r"\vert ")
    return m.strip()                                       # GitHub does not open or close `$` next to a space


def fix_text(text: str, inline: bool = True) -> str:
    out, fence = [], False
    # display first: $$…$$ anywhere outside code fences → a math fence on its own lines
    parts = re.split(r"(^\s*```.*?^\s*```\s*$)", text, flags=re.S | re.M)
    rebuilt = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            rebuilt.append(part)
            continue

        def disp(mm: re.Match) -> str:
            start = part.rfind("\n", 0, mm.start()) + 1
            indent = re.match(r"[ \t]*", part[start:]).group(0)
            body = _opname(mm.group(1).strip())
            return f"\n{indent}```math\n" + "\n".join(indent + l.strip() for l in body.splitlines()) + f"\n{indent}```\n{indent}"
        rebuilt.append(DISPLAY.sub(disp, part))
    text = "".join(rebuilt)
    # then inline math, line by line, skipping fences and code spans
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence or not inline:
            out.append(line)
            continue
        in_table = line.lstrip().startswith("|")
        segs = re.split(r"(`[^`]*`)", line)
        segs = [s if s.startswith("`") else INLINE.sub(lambda mm: "$" + fix_inline(mm.group(1), in_table) + "$", s) for s in segs]
        out.append("".join(segs).rstrip() if line.strip() == "" else "".join(segs))
    text = "\n".join(out)
    # A ```math fence nested in a list item reaches GitHub as <pre lang="math">, not as rendered math [ran] POST /markdown,
    # 2026-09-27: every math fence is lifted to the top level (the list resumes after it).
    text = re.sub(r"^[ \t]+(```math\n)((?:[ \t]*.*\n)*?)[ \t]+```", lambda m: m.group(1) + re.sub(r"(?m)^[ \t]+", "", m.group(2)) + "```", text,
                  flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text)


def check(path: str) -> int:
    """Render through GitHub (`gh api markdown`) and compare every math segment with its source."""
    src = Path(path).read_text()
    out = subprocess.run(["gh", "api", "markdown", "-f", f"text={src}", "-f", "mode=gfm", "-f",
                          "context=EvolvingAgentsLabs/lora-kernel"], capture_output=True, text=True).stdout
    rendered = [html.unescape(x) for x in re.findall(r"<math-renderer[^>]*>(.*?)</math-renderer>", out, re.S)]
    want = []
    fence, buf = False, []
    for line in src.split("\n"):
        if line.strip() == "```math":
            fence, buf = True, []
            continue
        if fence and line.strip() == "```":
            want.append("$$" + "\n".join(l.strip() for l in buf) + "$$"); fence = False
            continue
        if fence:
            buf.append(line)
            continue
        for s in re.split(r"(`[^`]*`)", line):
            if not s.startswith("`"):
                want += ["$" + m + "$" for m in INLINE.findall(s)]
    norm = lambda s: re.sub(r"\s+", "", s)
    bad = [w for w in want if norm(w) not in {norm(r) for r in rendered}]
    print(json.dumps({"file": path, "math_in_source": len(want), "rendered": len(rendered), "not_reaching_the_renderer_intact": len(bad),
                      "examples": bad[:5]}, ensure_ascii=False, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--check":
        sys.exit(max(check(p) for p in args[1:]))
    display_only = bool(args) and args[0] == "--display-only"      # documents that also write dollar amounts ($45)
    for p in args[1:] if display_only else args:
        Path(p).write_text(fix_text(Path(p).read_text(), inline=not display_only))
        print(f"fixed {p}")
