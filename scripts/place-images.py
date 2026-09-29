#!/usr/bin/env python3
"""Replace a described image placeholder with the image, once its file exists in docs/img/.

A document shows a blockquote placeholder — a brief for the illustrator — until the picture
arrives. This puts each arrived picture in, in every document and in both languages, with a
relative path that resolves from where the document lives, and leaves the placeholders of the
pictures still missing exactly as they are. Idempotent. Briefs stay in docs/img/README.md.

    python3 scripts/place-images.py          # place what has arrived
    python3 scripts/place-images.py --check  # list what is still wanted; exit 0
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "img"

# alt text and caption per image, per language. Alt text describes the picture to someone who
# cannot see it; the caption says what it is for.
TEXT = {
    "solution-architecture.png": {
        "en": ("A solution architecture in five layers: people in four roles; an agent runtime with one agent per "
               "role; order and back-office applications; app and messaging channels; one database with "
               "identity, payments and monitoring. Under the agents, one graphics card drawn as a bookshelf: one "
               "thick spine, the resident model, and a thin spine per role, each with two drawers of notes. A "
               "signpost routes by role; dashed lines leave for the frontier and for a person.",
               "*Where it sits in an organisation: records stay in the database, habits go in the adapter, knowledge stays in notes a person can read.*"),
        "es": ("Una arquitectura de solución en cinco capas: personas en cuatro roles; un runtime de agentes con un "
               "agente por rol; aplicaciones de pedidos y administración; canales de app y mensajería; una sola base "
               "de datos con identidad, pagos y monitoreo. Debajo de los agentes, una placa gráfica dibujada como "
               "estantería: un lomo grueso, el modelo residente, y un lomo fino por rol, cada uno con dos cajones de "
               "notas. Un cartel rutea por rol; líneas punteadas salen hacia la frontera y hacia una persona.",
               "*Dónde se ubica en una organización: los registros quedan en la base, los hábitos van en el adaptador, el conocimiento queda en notas que una persona puede leer.*"),
    },
    "core-1-0.png": {
        "en": ("A request meets a signpost, the router. Two lanes lead to two specialists, each at a desk with "
               "its own two-shelf bookcase; a dashed third lane leads off to a distant building, the frontier. "
               "One band runs under both desks: the runtime, the referee.",
               "*The core of 1.0: a router that may abstain, a specialist and a library per subdomain, one referee under all of them.*"),
        "es": ("Un pedido llega a un cartel indicador, el router. Dos carriles llevan a dos especialistas, cada uno "
               "en su escritorio con su estantería de dos estantes; un tercer carril, punteado, se va hacia un "
               "edificio lejano, la frontera. Una banda corre debajo de los dos escritorios: el runtime, el árbitro.",
               "*El núcleo de la 1.0: un router que puede abstenerse, un especialista y una biblioteca por subdominio, un árbitro debajo de todos.*"),
    },
    "memory-five-pieces.png": {
        "en": ("A bookcase with two shelves — a route of cards above, a tree of cards below — a small radar lighting "
               "three cards, a specialist holding three tools, and beneath them a band, the referee: a page being "
               "turned, a stamp for a site's rule, a barrier gate.",
               "*The five pieces of the memory. Four of them are not neural.*"),
        "es": ("Una estantería con dos estantes — arriba una ruta de fichas, abajo un árbol de fichas — un radar chico "
               "que ilumina tres fichas, un especialista con tres herramientas, y debajo una banda, el árbitro: una "
               "página que se pasa, un sello de regla local, una barrera.",
               "*Las cinco piezas de la memoria. Cuatro no son neuronales.*"),
    },
    "memory-walkthrough.png": {
        "en": ("Six panels joined by one line, like a subway map: a request; a search that lights three page cards; a page opening as its table of sections; one sentence whose underlined name links to the next page; a person's page and its extension; the answer with its citation stamped on it, and the referee's check.",
               '*One question, end to end: pages of one-sentence statements, links inside the sentences, an answer that names the sentence it rests on.*'),
        "es": ('Seis paneles unidos por una línea, como un mapa de subte: un pedido; una búsqueda que ilumina tres fichas de página; una página que se abre como su índice de secciones; una oración cuyo nombre subrayado enlaza a la página siguiente; la página de una persona y su interno; la respuesta con su cita estampada, y el visto bueno del árbitro.',
               '*Una pregunta, de punta a punta: páginas de enunciados de una oración, enlaces dentro de las oraciones, una respuesta que nombra la oración en que se apoya.*'),
    },
    "request-path.png": {
        "en": ("One line of seven stations: an agent; the gateway reading a signed badge; the operational memory — one index card (state and key names) and two drawers, session and organisation, with a workflow dial; the role's small local expert, fetching and storing by key; tools run with the badge's permission, one record refused and a payment held; a sheet with an invented line crossed out; the answer. A dashed branch for out of scope leads to a distant building and to a person; a log band runs under everything.",
               "*The request path: the expert reads one card and the keys it needs, never the conversation; permission, holds and grounding are the gateway's.*"),
        "es": ('Una línea de siete estaciones: un agente; el gateway que lee una credencial firmada; la memoria operativa — una ficha (estado y nombres de claves) y dos cajones, sesión y organización, con un dial de flujo; el experto local chico del rol, que busca y guarda por clave; herramientas con el permiso de la credencial, un registro rechazado y un pago retenido; una hoja con una línea inventada tachada; la respuesta. Una rama punteada para lo que está fuera de alcance lleva a un edificio lejano y a una persona; una banda de log corre debajo de todo.',
               '*El camino del pedido: el experto lee una ficha y las claves que necesita, nunca la conversación; permiso, retenciones y anclaje son del gateway.*'),
    },
    "article-harness.png": {
        "en": ("Two panels. Left: a specialist posts a query through a slot and the answer comes back through "
               "another window, behind their back, unseen — 11 / 90. Right: the answer comes back on the same "
               "card, under the query — 90 / 90.",
               "*Same model. Same problems. A different path.*"),
        "es": ("Dos paneles. Izquierda: un especialista mete una consulta por una ranura y la respuesta le vuelve "
               "por otra ventanilla, a su espalda, sin que la vea — 11 / 90. Derecha: la respuesta vuelve en la "
               "misma ficha, debajo de la consulta — 90 / 90.",
               "*Mismo modelo. Mismos problemas. Otro camino.*"),
    },
    "article-team.png": {
        "en": ("Four group chats and a stack of direct messages flow into one agent runtime, then one proxy, then "
               "one graphics card drawn as a bookshelf: a thick spine for the resident model and a thin coloured "
               "spine per group, each with its own two-drawer card file. A dashed line leaves for the frontier.",
               "*Many groups, one machine — and each group with its own specialist and its own library.*"),
        "es": ("Cuatro chats grupales y una pila de mensajes directos desembocan en un runtime de agentes, después "
               "un proxy, después una tarjeta gráfica dibujada como estantería: un lomo grueso para el modelo "
               "residente y un lomo fino de color por grupo, cada uno con su fichero de dos cajones. Una línea "
               "punteada sale hacia la frontera.",
               "*Muchos grupos, una sola máquina — y cada grupo con su especialista y su biblioteca.*"),
    },
    "operational-memory.png": {
        "en": ('Two panels. Left, the conversation in the prompt: a scroll growing turn after turn and a claim form whose order field is empty, 43 of 54. Right, the keys in a memory: one index card with the state and the key names, a drawer opened on order 58, and the claim form filled with it, 53 of 54. Title: carry the keys, not the conversation.',
               '*H1: fetching a value by key fixes what reading the history lost — the claim now names the order.*'),
        "es": ('Dos paneles. Izquierda, la conversación en el prompt: un rollo que crece turno a turno y un formulario de reclamo con el campo de pedido vacío, 43 de 54. Derecha, las claves en una memoria: una ficha con el estado y los nombres de claves, un cajón abierto en el pedido 58 y el reclamo completado con él, 53 de 54. Título: llevar las claves, no la conversación.',
               '*H1: traer un valor por clave arregla lo que leer el historial perdía — el reclamo ahora nombra el pedido.*'),
    },
    "runtimes.png": {
        "en": ('Two halves. Left, server: a rented graphics card in a cloud with one thick spine and four thin adapter spines, many users arriving, four adapters in one batch with no contention. Right, edge: a laptop with one user and one thin spine swapped in three milliseconds, llama.cpp at 8 bits, a dashed line to the frontier. Between them, a small bench: MLX, the research bench.',
               '*Two runtimes: vLLM on a rented card to measure, train and serve many; llama.cpp on your own machine to serve one.*'),
        "es": ('Dos mitades. Izquierda, server: una placa alquilada en una nube con un lomo grueso y cuatro lomos finos de adaptadores, muchos usuarios, cuatro adaptadores en un lote sin contención. Derecha, edge: una notebook con un usuario y un lomo fino que se cambia en tres milisegundos, llama.cpp en 8 bits, una línea punteada a la frontera. En el medio, un banco chico: MLX, el banco de investigación.',
               '*Dos runtimes: vLLM en una placa alquilada para medir, entrenar y servir a muchos; llama.cpp en tu propia máquina para servir a uno.*'),
    },
    "tracker-domain.png": {
        "en": ("A kanban board from To Do to Done with keyed cards and a triage gate, a stamp refusing a move the workflow does not allow; a shelf of team pages; and a five-turn session of one developer where every later turn opens the drawer holding the issue's key.",
               '*The team tracker: declared workflows the tool layer enforces, a space of one-sentence pages, and long sessions carried by key.*'),
        "es": ('Un tablero kanban de To Do a Done con tarjetas con clave y una compuerta de triage, un sello que rechaza un movimiento que el flujo no permite; una estantería de páginas del equipo; y una sesión de cinco turnos de un desarrollador donde cada turno posterior abre el cajón con la clave del issue.',
               '*El tracker del equipo: flujos declarados que la capa de herramientas hace cumplir, un espacio de páginas de una oración, y sesiones largas llevadas por clave.*'),
    },
    "mechanisms-map.png": {
        "en": ("A subway map: the main line is a request's path — agent, identity, gateway, operational memory, workflow, expert, tool layer, approvals, grounding, answer — with branch lines to the frontier and a person, the library and the router, two depots for the server and the edge runtimes, and a siding for speculative decoding.",
               '*Every mechanism on one line; each station is a section of this document.*'),
        "es": ('Un mapa de subte: la línea principal es el camino de un pedido — agente, identidad, gateway, memoria operativa, flujo, experto, capa de herramientas, aprobaciones, anclaje, respuesta — con ramales a la frontera y a una persona, a la biblioteca y al router, dos depósitos para los runtimes server y edge, y un desvío para la decodificación especulativa.',
               '*Todos los mecanismos en una línea; cada estación es una sección de este documento.*'),
    },
}


def documents():
    for p in sorted(ROOT.rglob("*.md")):
        parts = p.relative_to(ROOT).parts
        if ".git" in parts or parts[0] == "results" or p == IMG / "README.md":
            continue
        yield p


def language(doc: Path) -> str:
    rel = doc.resolve().relative_to(ROOT).as_posix()      # callers pass relative paths too
    return "es" if rel.startswith("docs/es/") or rel.endswith(".es.md") else "en"


def place(doc: Path, check: bool) -> list[str]:
    lines, out, done, i = doc.read_text().split("\n"), [], [], 0
    while i < len(lines):
        m = re.match(r">.*(?:PLACEHOLDER|MARCADOR)[^`]*`docs/img/([^`]+)`", lines[i])
        if not m:
            out.append(lines[i]); i += 1
            continue
        j = i
        while j < len(lines) and lines[j].startswith(">"):
            j += 1
        name = m.group(1)
        if (IMG / name).exists() and name in TEXT and not check:
            alt, caption = TEXT[name][language(doc)]
            rel = os.path.relpath(IMG / name, doc.parent).replace(os.sep, "/")
            out += [f"![{alt}]({rel})", "", caption]
            done.append(name)
        else:
            out += lines[i:j]
            done.append(f"wanted:{name}")
        i = j
    if not check and any(not d.startswith("wanted:") for d in done):
        doc.write_text("\n".join(out))
    return done


def main() -> int:
    check = "--check" in sys.argv
    wanted, placed = {}, {}
    for doc in documents():
        for d in place(doc, check):
            (wanted if d.startswith("wanted:") else placed).setdefault(d.replace("wanted:", ""), []).append(
                doc.relative_to(ROOT).as_posix())
    for name, docs in sorted(placed.items()):
        print(f"placed   {name}  →  {', '.join(docs)}")
    for name, docs in sorted(wanted.items()):
        print(f"wanted   {name}  ({len(docs)} places)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
