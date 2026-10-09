# `docs/img/IMAGES.md` — pictures still wanted, as commented placeholders

Three pictures asked for on 2026-10-09. Each document already carries the `<img>` inside an HTML comment marked
`IMAGE PLACEHOLDER — see docs/img/IMAGES.md`, so nothing renders broken while the file is missing. **When a file
lands here, delete the two comment lines (`<!-- IMAGE PLACEHOLDER …` and `-->`) around it, in the English document
and in its `docs/es/` mirror, in the same commit.** That is the only edit.

These are not the blockquote placeholders `scripts/place-images.py` handles (it reads only `>` lines). They use
`<img>` rather than Markdown image syntax on purpose: `tests/test_images.py` asserts every Markdown image in a document
resolves to a file, and it would read a commented one as a broken page. Once un-commented, that test does not watch an `<img>`,
so check the path by opening the page.

House style is the one in [`README.md`](README.md): flat, warm technical illustration in the library world of the
existing plates (ink on parchment, serif lettering, two or three muted colours, no gradients, no glow), **no robots,
no brains, no glowing neural nets**, labels inside the image in English in both language versions. Charts are not
drawn: they are rendered from a committed results file with the script given, and every number on them comes from
that file.

| file | size | format | used in | kind |
|---|---|---|---|---|
| `lora-patch.png` | 1600 × 800 (2:1) | PNG | `docs/GUIDE.md` §5.1, `docs/es/GUIDE.md` §5.1 | illustration |
| `speculative-decoding.png` | 1600 × 800 (2:1) | PNG | `docs/GUIDE.md` §6.1, `docs/es/GUIDE.md` §6.1 | illustration |
| `c1-throughput.png` | 1600 × 800 (2:1; the script writes it) | PNG | `docs/FOUNDATIONS.md` §5.6, `docs/es/FOUNDATIONS.md` §5.6 | chart from `results/` |

The fourth figure of this pass, the order of the substrate gates in `docs/SUBSTRATE-GATE.md`, is a Mermaid diagram
written into the document (both languages); it needs no file.

---

## `lora-patch.png`

**Path:** `docs/img/lora-patch.png` · **size** 1600 × 800 · **format** PNG

**What it shows.** GUIDE §5.1's one idea: $W' = W + \tfrac{\alpha}{r}AB$ — the base is frozen and shared, an expert
is a thin low-rank patch on it, and switching experts means switching the patch, never the book.

**Prompt (paste into the image model):**

> One wide illustration, 2:1, in a flat, warm technical style: ink lines on a parchment-coloured background, serif
> lettering, two or three muted colours (deep green, brick red, slate blue), no gradients, no glow, no robots, no
> brains, no neural-network imagery. A quiet reading room. Centre-left, on a sturdy wooden lectern, ONE very thick
> bound volume, closed, with a small brass padlock on its clasp; its spine reads "base model — frozen" and a paper tag
> tied to it reads "~24 GB". Centre-right, a hand is clipping ONE thin, coloured booklet onto the thick volume's spine
> with a brass clip; the booklet's cover reads "A · B" and a small tag reads "rank 16 · ~140 MB". A thin dotted line
> runs from the booklet to a small chalk formula on a slate beside the lectern: "W' = W + (α/r)·A·B". On the right
> wall, a coat-rack style rail with four more thin booklets hanging from clips, each a different muted colour, labelled
> "expert 2", "expert 3", "expert 4", "expert 5" — waiting their turn. Along the bottom, one small caption in the same
> serif lettering: "the book never changes — only the booklet clipped to it". Labels in English. Calm, uncluttered,
> generous margins.

**Alt text (en):** A thick bound volume on a lectern, the base model, labelled frozen, about 24 GB. A thin booklet
labelled A·B, rank 16, about 140 MB, is being clipped onto its spine. On a rack beside it hang more thin booklets, one
per expert, waiting their turn.

**Alt text (es):** Un volumen grueso encuadernado sobre un atril, el modelo base, rotulado congelado, unos 24 GB. Un
cuadernillo fino rotulado A·B, rango 16, unos 140 MB, se engancha en su lomo. En un perchero al lado cuelgan más
cuadernillos finos, uno por experto, esperando su turno.

**Where:** `docs/GUIDE.md` and `docs/es/GUIDE.md`, at the end of §5.1, right after the paragraph ending
"`FOUNDATIONS.md` §4.1.". The numbers (rank 16, ~140 MB, ~24 GB) are the ones that paragraph states.

**To place it:** in both files, delete the line `<!-- IMAGE PLACEHOLDER — see docs/img/IMAGES.md` above
`<img src="img/lora-patch.png" …>` (`../img/lora-patch.png` in the mirror) and the line `-->` after its caption.

---

## `speculative-decoding.png`

**Path:** `docs/img/speculative-decoding.png` · **size** 1600 × 800 · **format** PNG

**What it shows.** One round of GUIDE §6.1: a fast draft proposes k tokens, the large model checks them all in one
pass, accepts left to right up to the first disagreement, writes its own token there, and the round ends. The point
the picture must carry: the output is the large model's — a bad draft costs speed, never quality.

**Prompt (paste into the image model):**

> One wide illustration, 2:1, in a flat, warm technical style: ink lines on a parchment-coloured background, serif
> lettering, two or three muted colours (deep green, brick red, slate blue), no gradients, no glow, no robots, no
> brains, no neural-network imagery. An old editorial office. Left: a young clerk at a SMALL desk, writing quickly,
> labelled "draft — small and fast"; a little stopwatch on the desk. Between the desks, a row of FOUR paper slips laid
> out left to right on a long tray, each with one word: "the", "valve", "opens", "slowly". Right: a senior editor at
> a LARGE desk, labelled "large model — one pass checks the whole row", reading the tray with a single sweep of a
> magnifying glass. On the slips: the first three carry a green tick stamp; the fourth, "slowly", is crossed out in
> red and the editor has written "fully" on a fresh slip beside it. Above the tray, a small banner: "accepted: 3 + the
> editor's 1 — round ends". Bottom-right corner, a small framed note in serif: "the output is exactly the large model's
> — a bad draft costs speed, never quality". Labels in English. Calm, uncluttered, generous margins.

**Alt text (en):** A junior clerk at a small desk writes four word slips fast. A senior editor at a large desk checks
the whole row in one glance: the first three slips get a green tick, the fourth is crossed out and the editor's own
word is written in its place, and the round ends there.

**Alt text (es):** Un empleado junior en un escritorio chico escribe rápido cuatro fichas con palabras. Un editor senior
en un escritorio grande revisa toda la fila de un vistazo: las tres primeras fichas reciben un tilde verde, la cuarta
queda tachada y el editor escribe su propia palabra en su lugar, y la ronda termina ahí.

**Where:** `docs/GUIDE.md` and `docs/es/GUIDE.md`, at the end of §6.1, right after the paragraph ending
"`FOUNDATIONS.md` §6.1–6.3.". The four words are illustrative, not a measured sequence.

**To place it:** in both files, delete the `<!-- IMAGE PLACEHOLDER — see docs/img/IMAGES.md` line above
`<img src="img/speculative-decoding.png" …>` (`../img/…` in the mirror) and the `-->` line after its caption.

---

## `c1-throughput.png`

**Path:** `docs/img/c1-throughput.png` · **size** 1600 × 800 (the script's `figsize=(10, 5)` at 160 dpi) ·
**format** PNG

**What it shows.** FOUNDATIONS §5.6, C1 **[ran]**: aggregate generated tokens/s against concurrent sessions
$K \in \{1, 8, 16, 32\}$ on one L4, `google/gemma-4-E4B-it` bf16, with one adapter, two mixed (one cell, $K = 16$) and
four mixed; annotated with $r_4(16) = 278.6 / 269.7 = 1.03$ against the 0.8 bar. Every point is a cell of
`results/C1-concurrency-20260929/c1.json`; nothing is typed in by hand.

**Steps.** Matplotlib is not a dependency of this repository; use a throwaway venv outside the tree.

```bash
python3 -m venv /tmp/lk-img && /tmp/lk-img/bin/pip install matplotlib
cat > /tmp/lk-img/c1.py <<'PY'
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, out = sys.argv[1], sys.argv[2]
cells = json.load(open(src))["cells"]
series = {}
for c in cells:
    series.setdefault(c["adapters"], []).append((c["k"], c["tps"]))
style = {1: ("one adapter", "#2b2b2b", "o", "-"),
         2: ("two adapters mixed", "#8a6d3b", "s", ""),
         4: ("four adapters mixed", "#3b6e8a", "D", "--")}
fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
for a in sorted(series):
    pts = sorted(series[a]); label, col, mk, ls = style[a]
    ax.plot([k for k, _ in pts], [t for _, t in pts], marker=mk, linestyle=ls or "none",
            color=col, label=label, linewidth=1.6, markersize=6)
ax.set_xticks([1, 8, 16, 32])
ax.set_xlabel("concurrent sessions K")
ax.set_ylabel("aggregate generated tokens/s")
ax.set_title("C1 — one L4, gemma-4-E4B-it bf16: mixing adapters costs nothing measurable")
r = {c["adapters"]: c["tps"] for c in cells if c["k"] == 16}
ax.annotate(f"r_4(16) = {r[4]:.1f} / {r[1]:.1f} = {r[4]/r[1]:.2f}  (bar: 0.8)",
            xy=(16, r[4]), xytext=(17.5, r[4] - 120), arrowprops=dict(arrowstyle="-", color="#666"))
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.3)
ax.legend(frameon=False, loc="upper left")
fig.text(0.99, 0.01, "source: results/C1-concurrency-20260929/c1.json", ha="right", fontsize=8, color="#666")
fig.tight_layout()
fig.savefig(out)
PY
/tmp/lk-img/bin/python /tmp/lk-img/c1.py results/C1-concurrency-20260929/c1.json docs/img/c1-throughput.png
```

Run from the repository root. Rendered once on 2026-10-09 to check the recipe (not committed): one-adapter
22.7 → 135.1 → 269.7 → 490.8 tok/s, four-adapter 139.4 → 278.6 → 504.3 at $K = 8, 16, 32$, two-adapter 263.2 at
$K = 16$. Note the file has no four-adapter cell at $K = 1$; the §5.6 sentence that lists "22.7 → 135.1 → 278.6 →
504.3 … (four-adapter cells)" mixes the one-adapter cells at $K = 1, 8$ into that row.

**Alt text (en):** Line chart of aggregate generated tokens per second against concurrent sessions K = 1, 8, 16, 32 on
one L4: one adapter and four adapters mixed lie on top of each other, rising almost linearly to about 500 tokens per
second at K = 32; a two-adapter point at K = 16 sits on the same line.

**Alt text (es):** Gráfico de líneas de tokens generados por segundo agregados contra sesiones simultáneas K = 1, 8,
16, 32 en una L4: un adaptador y cuatro adaptadores mezclados quedan uno encima del otro, subiendo casi linealmente
hasta unos 500 tokens por segundo en K = 32; un punto de dos adaptadores en K = 16 cae sobre la misma línea.

**Where:** `docs/FOUNDATIONS.md` and `docs/es/FOUNDATIONS.md`, at the end of §5.6, after the paragraph that ends
"reading one draw as the rate." / "leer una sola tirada como la tasa.".

**To place it:** in both files, delete the `<!-- IMAGE PLACEHOLDER — see docs/img/IMAGES.md` line above
`<img src="img/c1-throughput.png" …>` (`../img/…` in the mirror) and the `-->` line after its caption.
