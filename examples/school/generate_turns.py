r"""Full turns for the school's staff roles, through the gateway's own loop — the corpus a school-staff
trajectory LoRA is trained on, and the held-out set it is measured on.

WHY. The school demo's first live run **[ran]** (results/DEMO-school-20260925): the system behaved, the bare
4B did not — it invented an answer after a correct call, retried a denied call five times, looped after a
write, skipped two calls. W9 showed the cure for that shape: a corpus of whole walks. The existing corpus
(`generate_corpus.py`) cannot be it: it puts the tool block in the system prompt where the gateway serves it
in the user turn, its final lines are not answers, and it has no denial, no hold, no out-of-scope case.

A ROW IS WHAT THE GATEWAY SERVES AND WHAT A GOOD TURN WRITES. Each case is played through
`examples.school.gateway.Gateway.turn` with a scripted oracle as the model: the system and user turns are
captured from the gateway itself (the role's prompt + the scope instruction; the request + the role's tool
block), and the assistant turn is the chain the loop wrote — the call, `= ` and the REAL tool result, then an
answer built FROM that result. Five kinds, each with its answer:

    read      a call, its result, the result restated                (the answer is grounded by construction)
    write     a call inside the user's school, what the tool says it did
    held      a payment or an all-families message: `PENDING APPROVAL`, and the answer says a director decides
    denied    another school's student: the tool refuses; the answer says so and does NOT call again
    out       nothing the role's tools cover: `OUT OF SCOPE`, no call

NOTHING TO MEMORISE. Every case runs on its own synthetic school (`generate_corpus.build_training_db`, a new
seed per case) with a second tenant added for denials, so no id, name or value repeats in a way an answer
could be recalled. Wording is split: `train` phrasings for the corpus, `eval` phrasings for the held-out set,
and neither contains a request of the demo's scripted day.

    python -m examples.school.generate_turns          # data_turns/train.jsonl, data_turns/eval.jsonl, gate.json
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from examples.common import tokens
from examples.school import gateway as gw_mod
from examples.school import roles as school_roles
from examples.school.generate_corpus import PROGRAMS, AREAS, CHANNELS, build_training_db

OUT = Path(__file__).parent / "data_turns"
TRAIN_CASES, EVAL_CASES = 700, 70
EVAL_SEED0 = 900_000

# (role, kind, tool, phrasing sets) — {sid} {program} {item} {qty} {area} {desc} {mid} {amount} {body} {name}
TASKS = [
    ("educador", "read", "agenda_read", {"train": ["¿Qué hay en la agenda del alumno {sid}?", "Show me student {sid}'s agenda.",
                                                   "Necesito ver las novedades del estudiante {sid}."],
                                         "eval": ["Pasame la agenda del alumno número {sid}.", "What is on the agenda for student {sid}?"]}),
    ("educador", "denied", "agenda_read", {"train": ["Mostrame la agenda del alumno {sid}.", "Can I see student {sid}'s agenda?"],
                                           "eval": ["Quiero ver la agenda del estudiante {sid}.", "Open student {sid}'s agenda please."]}),
    ("compras", "read", "order_list", {"train": ["¿Qué órdenes de compra tenemos?", "List our purchase orders."],
                                       "eval": ["Mostrame las órdenes de compra abiertas.", "Which purchase orders are there?"]}),
    ("compras", "write", "order_draft", {"train": ["Armá una orden de {qty} unidades de {item}.", "Draft an order for {qty} {item}."],
                                         "eval": ["Necesito pedir {qty} de {item}, prepará la orden.", "Please draft a purchase of {qty} {item}."]}),
    ("trainee", "read", "enrollment_list", {"train": ["¿Qué inscripciones hay?", "List the current enrolments."],
                                            "eval": ["Mostrame todas las inscripciones.", "Which enrolments do we have?"]}),
    ("trainee", "write", "enrollment_draft", {"train": ["Anotá al alumno {sid} en {program}.", "Enrol student {sid} in {program}."],
                                              "eval": ["Inscribí al estudiante {sid} en {program}.", "Sign student {sid} up for {program}."]}),
    ("trainee", "denied", "enrollment_draft", {"train": ["Anotá al alumno {sid} en {program}.", "Enrol student {sid} in {program}."],
                                               "eval": ["Inscribí al estudiante {sid} en {program}.", "Sign student {sid} up for {program}."]}),
    ("marketing", "read", "campaign_list", {"train": ["¿Qué campañas tenemos activas?", "List our campaigns."],
                                            "eval": ["Mostrame las campañas.", "Which campaigns are running?"]}),
    ("marketing", "held", "announcement_post", {"train": ["Publicá un aviso a las familias: {body}", "Post this to all families: {body}"],
                                                "eval": ["Mandá un anuncio a todas las familias diciendo: {body}", "Announce to the families: {body}"]}),
    ("marketing", "write", "campaign_create", {"train": ["Creá la campaña {name} por {channel} con {amount} centavos.",
                                                         "Create campaign {name} on {channel} with a budget of {amount} cents."],
                                               "eval": ["Lanzá una campaña {name} en {channel}, presupuesto {amount} centavos.",
                                                        "Start a {channel} campaign called {name}, {amount} cents."]}),
    ("it", "read", "maintenance_list", {"train": ["¿Qué pedidos de mantenimiento hay?", "List the maintenance requests."],
                                        "eval": ["Mostrame los tickets de mantenimiento.", "Which maintenance tickets are open?"]}),
    ("it", "write", "maintenance_create", {"train": ["Abrí un ticket para {area}: {desc}", "File a maintenance request for {area}: {desc}"],
                                           "eval": ["Cargá un pedido de mantenimiento en {area}: {desc}", "Open a ticket for {area} — {desc}"]}),
    ("cfo", "read", "membership_status", {"train": ["¿Cómo están las membresías?", "Show me the memberships."],
                                          "eval": ["Pasame el estado de las membresías.", "What memberships do we have?"]}),
    ("cfo", "read", "dashboard_summary", {"train": ["Dame el resumen del tablero.", "Give me the dashboard summary."],
                                          "eval": ["¿Qué dice el tablero?", "Summarise the dashboard for me."]}),
    ("cfo", "held", "billing_charge", {"train": ["Cobrá {dollars} dólares a la membresía {mid}.", "Charge ${dollars} to membership {mid}."],
                                       "eval": ["Hacé un cargo de {dollars} dólares en la membresía {mid}.", "Bill membership {mid} for ${dollars}."]}),
    ("dev", "read", "dashboard_summary", {"train": ["Resumen del tablero, por favor.", "Dashboard summary?"],
                                          "eval": ["Necesito los números del tablero.", "Show the dashboard numbers."]}),
]
OUT_OF_SCOPE = {"train": ["Escribime un poema sobre el otoño.", "What's the weather tomorrow?", "Traducí esta frase al francés: buenos días.",
                          "Tell me a joke.", "¿Quién ganó el partido de ayer?"],
                "eval": ["Contame un cuento corto.", "Recommend a good movie.", "¿Cuál es la capital de Australia?"]}
BODIES = ["El lunes hay acto a las 10.", "Picture day is moved to Thursday.", "La biblioteca cierra temprano el viernes.",
          "Book fair starts next week."]


def _answer(kind: str, result: str, spanish: bool) -> str:
    if kind == "held":
        return ("Queda pendiente: un director tiene que aprobarlo antes de que se ejecute." if spanish else
                "It is pending: a director has to approve it before it runs.")
    if kind == "denied":
        return ("No puedo: ese registro pertenece a otra escuela." if spanish else
                "I can't: that record belongs to another school.")
    lines = [l.strip("- ").strip() for l in result.splitlines() if l.strip()]
    body = "; ".join(lines)
    if kind == "write":
        return f"Hecho: {body}." if spanish else f"Done: {body}."
    return f"Según el sistema: {body}." if spanish else f"According to the system: {body}."


def _tag(tool: str, args: dict) -> str:
    return f"<{tool}>{args[next(iter(args))] if len(args) == 1 else '; '.join(f'{k}={v}' for k, v in args.items())}</{tool}>" \
        if args else f"<{tool}></{tool}>"


def _world(seed: int):
    """A training school, plus a few students of another school for the denial cases."""
    conn = build_training_db(40, seed)
    conn.execute("insert into orgs values (?, ?)", ("southport", "Southport Elementary"))
    conn.execute("insert into guardians values (?, ?, ?)", ("g-south-x", "southport", "Other Guardian"))
    for k in range(3):
        conn.execute("insert into students values (?, ?, ?, ?, ?)", (900 + k, "southport", "g-south-x", f"Other, Kid{k}", "Room 9"))
    conn.commit()
    import sqlite3
    conn2 = sqlite3.connect(":memory:", check_same_thread=False)        # the gateway serves across threads
    conn.backup(conn2)
    conn2.row_factory = sqlite3.Row
    return conn2


def _case(rng: random.Random, seed: int, split: str) -> dict:
    conn = _world(seed)
    if rng.random() < 0.12:
        role = rng.choice(list(school_roles.ROLES))
        kind, tool, text, args = "out", None, rng.choice(OUT_OF_SCOPE[split]), {}
    else:
        role, kind, tool, ph = rng.choice(TASKS)
        own = [r["id"] for r in conn.execute("select id from students where org_id='northgate'")]
        mids = [r["id"] for r in conn.execute("select id from memberships where org_id='northgate'")]
        fill = {"sid": rng.choice(own) if kind != "denied" else rng.choice([900, 901, 902]),
                "program": rng.choice(PROGRAMS), "item": rng.choice(["crayons", "paper", "markers", "footballs"]),
                "qty": rng.randint(2, 60), "area": rng.choice(AREAS), "desc": rng.choice(["the light flickers", "a broken chair", "no wifi"]),
                "mid": rng.choice(mids), "dollars": rng.choice([20, 35, 45, 60]), "body": rng.choice(BODIES),
                "name": f"spring-{rng.randint(1, 99)}", "channel": rng.choice(CHANNELS), "amount": rng.randint(10000, 90000)}
        text = rng.choice(ph[split]).format(**fill)
        args = {"agenda_read": {"student_id": fill["sid"]}, "order_draft": {"item": fill["item"], "qty": fill["qty"]},
                "enrollment_draft": {"student_id": fill["sid"], "program": fill["program"]},
                "announcement_post": {"audience": "families", "body": fill["body"]},
                "campaign_create": {"name": fill["name"], "channel": fill["channel"], "budget_cents": fill["amount"]},
                "maintenance_create": {"area": fill["area"], "description": fill["desc"]},
                "billing_charge": {"membership_id": fill["mid"], "amount_cents": fill["dollars"] * 100}}.get(tool, {})
    spanish = any(ch in text for ch in "¿áéíóúñ") or text.split()[0] in {"Mostrame", "Armá", "Anotá", "Publicá", "Creá", "Abrí",
                                                                          "Cobrá", "Dame", "Resumen", "Necesito", "Pasame", "Inscribí",
                                                                          "Quiero", "Mandá", "Lanzá", "Cargá", "Hacé", "Escribime",
                                                                          "Traducí", "Contame"}
    served = {}

    def oracle(system, user, close):
        served.update(system=system, user=user)

        def gen(prefix: str) -> str:
            if kind == "out":
                return gw_mod.OUT
            if "</" not in prefix:
                return _tag(tool, args)
            result = prefix.rsplit("= ", 1)[1].strip()
            return _answer(kind, result, spanish)
        return gen, lambda: {"prompt_tokens": 0, "completion_tokens": 0}

    g = gw_mod.Gateway(conn, oracle)
    user_id = {"educador": "educador-north", "compras": "compras-north", "trainee": "trainee-north", "marketing": "marketing-north",
               "it": "it-north", "cfo": "cfo-north", "dev": "dev-north"}[role]
    out = g.turn(tokens.issue(user_id, role, "northgate"), [{"role": "user", "content": text}])
    ev = out["event"]
    expect = {"route": "local" if kind != "out" else school_roles.ROLES[role]["egress"]}
    if tool:
        expect["tool"] = tool
        if kind == "denied":
            expect["denied"] = True
        if kind == "held":
            expect["held"] = True
    return {"case_id": f"{split}-{seed}", "split": split, "role": role, "kind": kind, "tool": tool, "request": text,
            "user_id": user_id, "world_seed": seed, "expect": expect, "calls": ev["calls"],
            "messages": [{"role": "system", "content": served["system"]}, {"role": "user", "content": served["user"]},
                         {"role": "assistant", "content": out["walk"]}]}


def build(n: int, split: str, seed0: int) -> list[dict]:
    rng = random.Random(seed0)
    return [_case(rng, seed0 + i, split) for i in range(n)]


def gate(train: list[dict], evals: list[dict]) -> dict:
    from examples.school.demo_run import SCENES
    demo = {t for _, t, _ in SCENES}
    ev_texts = {r["request"] for r in evals}
    kinds = {}
    for r in train:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    ok_walk = lambda r: r["kind"] == "out" or (r["calls"] and r["calls"][0]["tool"] == r["tool"] and
                                               ("denied" in r["calls"][0]) == (r["kind"] == "denied") and
                                               ("held" in r["calls"][0]) == (r["kind"] == "held"))
    g = {"G1_demo_request_in_corpus": sum(r["request"] in demo for r in train + evals),
         "G2_eval_request_in_corpus": sum(r["request"] in ev_texts for r in train),
         "G3_shared_world": len({r["world_seed"] for r in train} & {r["world_seed"] for r in evals}),
         "G4_walk_not_as_intended": sum(not ok_walk(r) for r in train + evals),
         "rows": len(train), "eval": len(evals), "kinds": kinds}
    g["passed"] = all(v == 0 for k, v in g.items() if k.startswith("G"))
    return g


def main() -> int:
    OUT.mkdir(exist_ok=True)
    train, evals = build(TRAIN_CASES, "train", 100_000), build(EVAL_CASES, "eval", EVAL_SEED0)
    g = gate(train, evals)
    for name, rows in (("train", train), ("eval", evals)):
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (OUT / "gate.json").write_text(json.dumps(g, indent=1))
    print(f"[school] {len(train)} train · {len(evals)} eval · gate {'PASSED' if g['passed'] else 'FAILED'} {g}", flush=True)
    return 0 if g["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
