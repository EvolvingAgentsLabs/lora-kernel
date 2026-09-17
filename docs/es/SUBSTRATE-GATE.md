# SUBSTRATE-GATE — la Fase 0, especificada

> *[Read me in English](../SUBSTRATE-GATE.md)*

Compañera de `training/harness/verify_substrate.py`. El sustrato de serving — una
base residente, un pool de LoRAs que vLLM **realmente aplica**, herramientas
alcanzables a través del proxy, stop strings honrados — es la capa sobre la que se
apoya todo en [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) §0b. Se verificaba por
ritual. Esta es la compuerta, y cada fila existe porque un número ya la pagó.

## La matemática que protege

Un miembro es un delta sobre las siete proyecciones por bloque de la base,
$y = xW + s\,(xA)B$ ([`FOUNDATIONS.md`](FOUNDATIONS.md) §4–§5). Con $W$ congelado,
**un miembro cuyo texto servido nunca difiere del de la base está sirviendo
$y = xW$** — el término delta ausente, diga lo que diga el log del motor. Eso es C18,
y G1 es su test.

## Por qué existe cada compuerta

| compuerta | valida | qué costó aprenderlo |
|---|---|---|
| **P0** | `/v1/models` es la fuente de verdad de los miembros | cuatro listas mantenidas a mano quedaron atrás de lo que seguían (`CLAUDE.md` §3) |
| **G1 (C18)** | el término delta está presente: el texto servido difiere de la base en **≥ 2 de 3** sondas | vLLM 0.29.0 cargó un LoRA sobre `Qwen3.5-4B`, lo logueó, sirvió la base **[ran]** P33; la compuerta de identidad lo ve en segundos |
| **G2** | el miembro alcanza sus herramientas **a través del proxy** — sin error HTTP, una llamada o una respuesta | el primer brazo de P51: **240 de 240** pedidos HTTP 400 por flags del parser faltantes, la línea de progreso leyendo `correct 0 calls 0` — una corrida rota disfrazada de piso **[ran]** |
| **G3** | `stop` + `include_stop_str_in_output` honrados sobre una continuación que el modelo no puede evitar | el loop de modo corpus (parar en `</tag>`, inyectar, seguir) es imposible sin eso; el primer preflight midió la frase del modelo **[ran]** P55 A intento 1 |

## Decisiones de diseño

- **El umbral de G1 es 2 de 3, no 1 de 1.** A temperatura 0 un prompt corto puede
  coincidir entre base y miembro sin que el delta esté ausente; un falso NOT APPLIED
  cuesta una sesión. La compuerta de P55 A vio **6 de 8** sondas distintas sobre un
  adaptador real; 2 de 3 es el piso por debajo del cual la coincidencia deja de ser
  la explicación.
- **G2 se saltea con aviso si no se da `--proxy`.** Es compuerta del *sistema*
  (servidor + proxy + traducción tag ↔ `tool_calls`), no del servidor; correrla
  contra el upstream directo no probaría nada sobre la traducción.
- **El veredicto se lee del archivo, no del código de salida.** Los registros se
  escriben antes del resumen y el resumen se calcula en un `try` (regla de P47); el
  código de salida es para CI, `verdict.json` es para las personas.
- **Reusa lo que existe.** `serve_openai --gate-only` (P29) es la comparación de
  identidad profunda; `accept_rank.stop_check` es G3. Este runner es la versión de
  humo que corre cada sesión y delega el análisis fino en las compuertas existentes
  cuando falla.

## Dónde corre

**La Fase 0 es siempre GPU** — esta laptop no puede servir vLLM (`CLAUDE.md` §0).
Corre en la placa al inicio de cualquier sesión que sirva el pool, por la cadena:

    GPU=L4 RUN_DIR=results/P56-substrate-<fecha> MODULE=training.harness.verify_substrate \
      RESULTS_NAME=verdict.json MARGS="" SESSIONS=1 training/harness/chain_serve.sh

Lo que corre en cualquier máquina, siempre, es la mitad estática:
`tests/test_contract.py` (las declaraciones del pool contra sus corpus) y
`tests/test_verify_substrate.py` (la lógica del veredicto sobre cada desenlace que
una compuerta puede tener).

## Primera corrida — P56, 2026-09-17 **[ran]**

L4, los dos miembros del pool subidos (el tarball de P41), proxy arrancado con `--prune`.
**`SUBSTRATE OK`**: P0 lista `email-full` y `fluids-full`; G1 **3/3** sondas difieren para
cada uno; G2 `email-full` responde con **1 llamada**, `fluids-full` responde sin ninguna — la
superficie podada no le ofrece herramienta de inbox, que es la forma correcta; G3
`stop_reason: '3'`. `results/P56-substrate-20260917/verdict.json`.

## Su lugar en el plan

- **La Fase 0 ✅ es la entrada de todas las demás.**
- **Si cambia vLLM o la base, la Fase 0 se re-corre antes que cualquier otra cosa** —
  la única forma permitida de re-validar. Si se rompe, el plan se detiene hasta que
  vuelva a pasar.
- **G1 es la misma compuerta que la Fase 6 correrá sobre `Qwen3.5-4B` (D2)** antes de
  D4 — el mismo script con otra base y otros miembros, no otro script.
