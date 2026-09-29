# `docs/img/` — the images, and the brief for each

Every picture the documents ask for, in one place. A document shows a described placeholder until
its file exists here; when a file arrives, the placeholder in **both languages** is replaced by the
image. File names are fixed — the documents already point at them. `python3 scripts/place-images.py`
does the replacing; `--check` lists what is still wanted.

**Withdrawn 2026-09-25, redrawn and back 2026-09-26:** `memory-walkthrough.png` (it showed the pre-W9 walk — notes and a calculator —
where the memory is now pages of atomic statements with cited answers) and `request-path.png` (it had no gateway, no
permission, no approval and no grounding — and spelled a spine "Harenss"). Their placeholders are back in the documents;
the briefs below are new.

**House style** (from the hero): flat, warm technical illustration — ink lines, two or three muted
colours, no gradients, no glow. **No robots, no brains, no glowing neural nets**: four of the five
pieces of the memory are not neural, and the pictures should say so. Labels *inside* an image stay in
English in both language versions.

**Withdrawn 2026-09-29:** `request-path.png` v2 (moved to `withdrawn/request-path-v2.png`): it shows the path without the short-term operational memory, which is now the heart of a multi-turn request (H1 [ran]). Its placeholder is back in both READMEs; the v3 brief is below, with four new pictures.

| file | size | status | used in |
|---|---|---|---|
| `hero.png` | 1600 × 640 asked · 1983 × 793 delivered | ✅ **in** | `README.md`, `README.es.md` |
| `article-harness.png` | 1200 × 627 | ✅ **in** | `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` |
| `article-team.png` | wide, ~1600 px | ✅ **in** | `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` |
| `core-1-0.png` | wide, ~1600 px | ✅ **in** | `README.md`, `README.es.md` |
| `memory-five-pieces.png` | wide, ~1600 px | ✅ **in** | `docs/MEMORY.md`, `docs/es/MEMORY.md`, `docs/ARCHITECTURE.md`, `docs/es/ARCHITECTURE.md` |
| `memory-walkthrough.png` | tall, ~1200 × 1600 | ✅ **in (v2, 2026-09-26)** | `README.md`, `README.es.md`, `docs/MEMORY.md`, `docs/es/MEMORY.md` |
| `request-path.png` | wide, ~1600 px | ✅ v3 placed 2026-09-29 — v2 withdrawn to `withdrawn/request-path-v2.png`: it had no operational memory | `README.md`, `README.es.md` |
| `operational-memory.png` | 1200 × 627 | ✅ placed 2026-09-29 | `README.md`, `docs/ARCHITECTURE.md`, `docs/MEMORY.md`, `docs/GUIDE.md`, `docs/review/harness-workflow-kv.md` (+ each `es` mirror) |
| `runtimes.png` | wide, ~1600 px | ✅ placed 2026-09-29 | `README.md`, `docs/SERVING.md`, `docs/MECHANISMS.md` (+ `es`) |
| `tracker-domain.png` | wide, ~1600 px | ✅ placed 2026-09-29 — the counter box is empty until H2 has its reading | `README.md`, `README.es.md` |
| `mechanisms-map.png` | wide, ~1900 px | ✅ placed 2026-09-29 (badges number stations, not sections — the caption maps them) | `docs/MECHANISMS.md`, `docs/es/MECHANISMS.md` |
| `demo-escuela-preview.gif`, `demo-escuela-poster.png` | 960 px GIF · 1280 px PNG | ✅ **in** — cut from `docs/video/demo-escuela.mp4` by ffmpeg, not drawn (`video/README.md`) | not embedded — the READMEs play the video itself (a GitHub attachment of the same MP4); kept for sharing where video does not play |
| `solution-architecture.png` | wide, ~1600 px | ✅ **in** | `README.md`, `README.es.md`, `docs/articles/2026-09-it-was-the-harness.md`, `docs/articles/2026-09-era-el-arnes.es.md` (cover) |

## Briefs

### `request-path.png` — v3, with the operational memory

A clean left-to-right flow in the house style, SEVEN stations on one line. 1 "agent — one per role (OpenClaw)". 2 "gateway — signed token → user · role · organisation", a small turnstile reading a badge. 3 NEW: "operational memory" — a single index card fed into the next station, reading "state: receiving/assigned · keys: order", and beside it two small drawers, "session" and "organisation", with a dial above them labelled "workflow state — moved by the calls that ran". 4 "the role's expert — one small local model + its adapter", a desk with a thin coloured spine leaning on a thick one; two short arrows go from the desk to the drawers, labelled `get` and `put`. 5 "tools, with the badge's permission": two small insets — a red stamp across a folder, "another organisation's record — refused", and a paper clip holding a slip, "payment — held for a director". 6 "grounding — every line of the reply must be in a tool's result": a sheet with one line crossed out, "invented". 7 "answer". From station 4 a dashed branch, "out of scope", splits in two: one runs to a distant building, "frontier", the other to a person at a desk, "staff". Under the whole line, a thin band: "log → dashboard: served here · sent on · held · replaced". THE POINT: the conversation is NOT carried to the expert — only the one card and the drawers are. Labels in English; spell every word correctly.

### `operational-memory.png` — carry the keys, not the conversation

Two panels side by side, in the style of `article-harness.png`. LEFT, "the conversation in the prompt": a specialist at a desk reads a paper scroll that gets visibly longer turn after turn (three turn markers on it); they fill in a claim form whose field "order" is left EMPTY, the sentence "the seal on that order was broken" copied as is. Counter: "43 / 54". RIGHT, "the keys in a memory": the same specialist reads only a small index card, "state: customer_service/order_known · keys: order"; a drawer labelled "order = 58" is pulled open; the claim form reads "order 58: the seal on that order was broken". Counter: "53 / 54". Title over the image: "Carry the keys, not the conversation." No robots, no brains.

### `runtimes.png` — server and edge

Two halves, one horizontal diagram, house style. LEFT, "server — measure and train, many users": a rented graphics card in a small cloud, drawn as a bookshelf with one thick spine ("one resident model — vLLM") and FOUR thin coloured spines ("school", "school upper", "distributor", "distributor abstains"); 32 small arrows arrive from many users. A tag: "four adapters mixed in one batch — no contention". RIGHT, "edge — serve on your own machine": a laptop, one user, a single thin spine being swapped for another with a small clock reading "3 ms"; a tag "llama.cpp · 8-bit". A thin dashed line from the laptop to a distant building, "frontier — only what no tool covers". Between the halves, a small bench with a notebook, "MLX — the research bench".

### `tracker-domain.png` — the team tracker (H2)

One wide diagram, house style. TOP LEFT, a kanban board with five columns — "To Do", "In Progress", "In Review", "QA", "Done" — and small cards keyed "RD-169", "RD-313", "RD-354"; a bug card enters through a narrow gate "Triage". A small stamp on an arrow that jumps two columns: "not allowed — the workflow refuses it". TOP RIGHT, a shelf of wiki pages: "definition of done", "component owners", "release process", "bug policy", each page a list of one-sentence slips. BOTTOM, a five-station session line for one developer: "show me RD-169" → "move it to review" → "log 2 hours on it" → "who owns its component?" → "comment: ready for QA"; above each of stations 2–5 a small drawer "issue" being opened (`get`), and at station 4 a second drawer "component" and a line to the "component owners" page. Three roles as small silhouettes: "developer", "lead", "qa". Leave room in the bottom-right corner for a counter to be added when H2 has its result.

### `mechanisms-map.png` — every mechanism on one line (optional)

A subway map in the house style: one main line, "a request's path", with stations in order — agent, identity, gateway, operational memory, workflow, expert (LoRA), tool layer, approvals, grounding, answer — and branch lines: "out of scope → frontier / person", "library (pages of statements)", "router". Two depots at the edges: "server (vLLM, Colab)" and "edge (llama.cpp, your machine)"; a siding "speculative decoding". A legend strip at the bottom: "corpora and gates · release gate · measurement discipline". Each station labelled with its section number in MECHANISMS.md (§1–§17).

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


### `solution-architecture.png`

One wide solution-architecture diagram in the repository's warm flat style (ink on parchment, serif lettering), five layers top to bottom. TOP, one long band "people": four groups with small faceless silhouettes — "customers", "suppliers and carriers", "warehouse crew", "office staff". LEFT COLUMN, a tall box "agent runtime — one agent per role", holding six cards: "customer service", "receiving", "dispatch", "purchasing and stock", "claims and returns", "IT". CENTRE, two boxes the agents exchange arrows with: "orders" (orders · deliveries · docks · returns) and "back office" (communications · operations · purchasing · payroll · reporting). RIGHT COLUMN, the channels: "app", and "messaging" splitting into "customers" and "internal". BOTTOM, the systems of record: one drum "one database" and three small boxes, "identity and permissions", "payments", "monitoring" — generic, no brand names, no logos. THE POINT OF THE PICTURE: under the agent-runtime column, where a cloud API would normally be, draw ONE graphics card as a bookshelf — a thick spine "one small resident model" and six thin coloured spines, one per role card above ("customer service adapter", "receiving adapter", …), each joined to its card by a thin line. Under each thin spine a two-drawer card file: "how we do it here" and "what we know". A small signpost sits between the runtime and the shelf: "router — the role a message comes from is the route". A dashed line leaves the signpost for a distant building, "frontier — everything unmeasured", and a second dashed line ends at a person: "or a human, where policy says nothing leaves the building". A thin band under the shelf: "runtime — referee: applies this site's rules before a note is shown". One caption inside the image, bottom right: "records stay in the database; habits go in the adapter; knowledge stays in notes a person can read". Icons: boxes, pallets, a truck, a loading dock, a calendar. No medical imagery of any kind.
