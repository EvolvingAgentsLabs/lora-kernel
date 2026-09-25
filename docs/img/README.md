# `docs/img/` — the images, and the brief for each

Every picture the documents ask for, in one place. A document shows a described placeholder until
its file exists here; when a file arrives, the placeholder in **both languages** is replaced by the
image. File names are fixed — the documents already point at them. `python3 scripts/place-images.py`
does the replacing; `--check` lists what is still wanted.

**Withdrawn 2026-09-25, to be redrawn:** `memory-walkthrough.png` (it showed the pre-W9 walk — notes and a calculator —
where the memory is now pages of atomic statements with cited answers) and `request-path.png` (it had no gateway, no
permission, no approval and no grounding — and spelled a spine "Harenss"). Their placeholders are back in the documents;
the briefs below are new.

**House style** (from the hero): flat, warm technical illustration — ink lines, two or three muted
colours, no gradients, no glow. **No robots, no brains, no glowing neural nets**: four of the five
pieces of the memory are not neural, and the pictures should say so. Labels *inside* an image stay in
English in both language versions.

| file | size | status | used in |
|---|---|---|---|
| `hero.png` | 1600 × 640 asked · 1983 × 793 delivered | ✅ **in** | `README.md`, `README.es.md` |
| `article-harness.png` | 1200 × 627 | ✅ **in** | `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` |
| `article-team.png` | wide, ~1600 px | ✅ **in** | `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` |
| `core-1-0.png` | wide, ~1600 px | ✅ **in** | `README.md`, `README.es.md` |
| `memory-five-pieces.png` | wide, ~1600 px | ⬜ wanted | `docs/MEMORY.md`, `docs/es/MEMORY.md`, `docs/ARCHITECTURE.md`, `docs/es/ARCHITECTURE.md` |
| `memory-walkthrough.png` | tall, ~1200 × 1600 | ⬜ **wanted — redraw (v2)** | `README.md`, `README.es.md`, `docs/MEMORY.md`, `docs/es/MEMORY.md` |
| `request-path.png` | wide, ~1600 px | ⬜ **wanted — redraw (v2)** | `README.md`, `README.es.md` |
| `solution-architecture.png` | wide, ~1600 px | ✅ **in** | `README.md`, `README.es.md`, `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` (cover) |

## Briefs

### `article-harness.png`

Two panels side by side, in the repository's flat illustrated style. Left: a specialist at a desk writes a query on a card and posts it through a slot; the answer comes back through ANOTHER window, behind their back, unseen — and they keep writing a number from memory. Below, a counter: "11 / 90". Right: the same scene, but the answer comes back written on the same card, right under the query; they read it and carry on. Counter: "90 / 90". Title over the image: "Same model. Same problems. A different path."

### `article-team.png`

One horizontal diagram in the same flat style. On the left, four group-chat bubbles labelled "Dev", "Marketing", "Internal", "Ops", each with a few small faceless silhouettes, and a fifth stack of single bubbles, "direct messages". All flow into a central box, "agent runtime — dozens of sessions". One line leaves it to "proxy", and from there to ONE graphics card drawn as a bookshelf: a thick spine "one small resident model" and, leaning on it, four thin coloured spines, one per group — "dev adapter", "marketing adapter"… Under each thin spine, a small two-drawer card file: "how this team does it" and "what this team knows". A dashed line leaves the proxy for a distant building, "frontier — everything else". The visual idea: many groups, one machine, and each group with its own specialist and its own library.

### `core-1-0.png`

One horizontal diagram in the hero's style. A request enters from the left and meets a small signpost labelled "router — whose corpus does this look like?". Three lanes leave it. The top two lanes each lead to a small desk with a specialist and its own little bookcase (label one "inbox triage", the other "IV therapy"); each bookcase shows the two shelves, harness above and wiki below. The bottom lane, dashed, leads off the right edge to a distant large building, "frontier — when it looks like none". Under the two desks runs one continuous band labelled "runtime — referee: turns the pages · applies the site's rules · enforces the order". Above each desk a small tag: "LoRA — trained to navigate, not to remember".

### `memory-five-pieces.png`

A single wide diagram, left to right, flat technical style, light background. Far left, a bookcase with two labelled shelves: the top shelf "Operational harness" holds cards joined by arrows in a line (a procedure); the bottom shelf "Encyclopedic wiki" holds cards arranged as a tree. In the middle, a small radar dish labelled "radar — embeddings of this subdomain only" sweeping over the bookcase and lighting up three cards. To its right, a figure at a desk labelled "LoRA — the specialist" holding exactly three tools labelled `search`, `open`, `calc`. Beneath everything, a thin band labelled "runtime — referee" with three icons: a page being turned, a stamp reading "site rule applied", and a barrier gate reading "requires step 1". No robots, no brains, no glowing neural nets: the point of the picture is that four of the five pieces are not neural.

### `memory-walkthrough.png` — v2, pages of atomic statements

A vertical storyboard of six numbered panels joined by one line, like a subway map, in the house style. 1: a request
card, "What extension reaches the manager of the depot that stocks the Lumo-410 pallet wrap?". 2: the expert writes
`search`; three PAGE cards light up on the wiki shelf. 3: the page "Lumo-410 pallet wrap" opens as a small table of
contents — four section tabs, "§supplier · §warehouse · §pack · §reorder-point" — and the expert's finger is on
"§warehouse". 4: that ONE sentence, on its own slip, "The Lumo-410 pallet wrap is stocked at Old Mill depot", with "Old
Mill depot" underlined; the line runs along the underline to a second page, "Old Mill depot", and its tab "§manager".
5: a third page, a person — "Wanda Marrow" — and its tab "§extension": "can be reached on extension 9970". 6: the answer
card, "extension 9970", with the citation as a small stamped tag, "[9du§extension]". Along the bottom, the referee band,
with a green check under panel 6: "citation checked — the walk opened this sentence, and it holds 9970". THE POINT: a
page is a list of one-sentence slips, the links live inside the sentences, and the answer names the slip it rests on.
No robots, no brains.

### `request-path.png` — v2, through the gateway

A clean left-to-right flow in the house style, six stations on one line. 1 "agent — one per role (OpenClaw)". 2 "gateway —
signed token → user · role · school", drawn as a small turnstile reading a badge. 3 "the role's expert — one small local
model + its adapter", a desk with a thin coloured spine leaning on a thick one. 4 "tools, with the badge's permission":
two small insets — a red stamp across a folder, "another school's record — refused", and a paper clip holding a slip,
"payment — held for a director". 5 "grounding — every line of the reply must be in a tool's result": a sheet with one
line crossed out, "invented". 6 "answer". From station 3 a dashed branch, "out of scope", splits in two: one runs to a
distant building, "frontier", the other to a person at a desk, "staff". Under the whole line, a thin band: "log →
dashboard: served here · sent on · held · replaced". Labels in English; spell every word correctly.

### `solution-architecture.png`

One wide solution-architecture diagram in the repository's warm flat style (ink on parchment, serif lettering), five layers top to bottom. TOP, one long band "people": four groups with small faceless silhouettes — "customers", "suppliers and carriers", "warehouse crew", "office staff". LEFT COLUMN, a tall box "agent runtime — one agent per role", holding six cards: "customer service", "receiving", "dispatch", "purchasing and stock", "claims and returns", "IT". CENTRE, two boxes the agents exchange arrows with: "orders" (orders · deliveries · docks · returns) and "back office" (communications · operations · purchasing · payroll · reporting). RIGHT COLUMN, the channels: "app", and "messaging" splitting into "customers" and "internal". BOTTOM, the systems of record: one drum "one database" and three small boxes, "identity and permissions", "payments", "monitoring" — generic, no brand names, no logos. THE POINT OF THE PICTURE: under the agent-runtime column, where a cloud API would normally be, draw ONE graphics card as a bookshelf — a thick spine "one small resident model" and six thin coloured spines, one per role card above ("customer service adapter", "receiving adapter", …), each joined to its card by a thin line. Under each thin spine a two-drawer card file: "how we do it here" and "what we know". A small signpost sits between the runtime and the shelf: "router — the role a message comes from is the route". A dashed line leaves the signpost for a distant building, "frontier — everything unmeasured", and a second dashed line ends at a person: "or a human, where policy says nothing leaves the building". A thin band under the shelf: "runtime — referee: applies this site's rules before a note is shown". One caption inside the image, bottom right: "records stay in the database; habits go in the adapter; knowledge stays in notes a person can read". Icons: boxes, pallets, a truck, a loading dock, a calendar. No medical imagery of any kind.
