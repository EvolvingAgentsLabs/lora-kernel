# La demo — una organización de referencia sobre un modelo chico local, en cinco minutos

Lo que esto muestra es lo que ya corre, sobre el mismo código que usaron las mediciones, con lo que
todavía no corre dicho al lado. Está escrita para una conversación con un equipo que ya corre agentes
por rol — un sistema de agentes delante de un backend de administración, una base de datos única,
identidad y permisos fuera del modelo — y quiere saber qué le puede sacar un modelo chico local a la
factura de frontera.

Un solo comando produce el recorrido entero, en Colab, en menos de una hora, en una sesión L4:

```bash
GPU=L4 BRANCH=main RUN_DIR=results/DEMO-org-20260924 MODULE=training.harness.demo_org \
  MARGS="" RESULTS_NAME=demo.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 training/harness/chain_serve.sh
python -m training.harness.demo_org --render results/DEMO-org-20260924/demo.json > transcript.md
```

*~~Este recorrido corrió sobre `Qwen3.5-4B`~~ — corregido 2026-09-26: **este comando nunca se había corrido**; no
existe `results/DEMO-org-*` en ningún commit, y la parte A estaba marcada [ran] sin uno. Su primera corrida, sobre Gemma 4
E4B con `distributor-wiki@v2` y verificaciones en cada escena, es `results/DEMO-org-gemma-20260926/` — el miembro de wiki 2/2, el modelo pelado en los roles 1/5. La demo de la escuela,
más abajo, sí corrió, 8/8.*

Para la versión en vivo — el mismo modelo detrás de OpenClaw, turno por turno — ver
[`OPENCLAW.md`](OPENCLAW.md); corrió en vivo, 40 turnos, todos locales **[ran]** P63. Desde entonces
corrieron en vivo las dos mitades del diagrama de referencia: la escuela, 15/15
(`results/LIVE-school-openclaw-20260926/`), y la distribuidora, 6/6, sin nada alquilado — el E4B y su
propio LoRA servidos por llama.cpp en la misma máquina que corre OpenClaw, un turno reenviado a Claude
Haiku 4.5 por $0,0112 **[ran]** `results/LIVE-distributor-openclaw-20260928/`.
Una tercera organización corre ahora de la misma manera: el arnés de flujo de trabajo sin bloque del
tracker de equipo, en vivo en la propia máquina del usuario por OpenClaw, **14/14 turnos, 8/8
dependientes** **[ran]** `results/LIVE-tracker-openclaw-20260930/`.

**Estado actual, 2026-10-01 — la línea de biblioteca real.** El minuto 4 de abajo (enunciados atómicos,
respuestas citadas) se midió sobre una wiki inventada; si esa misma memoria se traslada a una biblioteca
real ingerida textualmente es hoy su propia línea de corridas, `REAL0` a `REAL7` ([`MEMORY.md`](MEMORY.md)
§1.6, [`FOUNDATIONS.md`](FOUNDATIONS.md) §8.10): un mundo generado no transfiere (0/25), los recorridos de
documentos reales con la pérdida enmascarada sobre los propios tramos del modelo sí (18/23), y en parte a
una tercera familia densa en enlaces (15/25) — nada de esto está todavía en el recorrido de cinco minutos.
Un endpoint en vivo para ella (`examples/library/serve.py`) ~~está construido y probado offline, todavía no
corrido en vivo~~ **corrió desde entonces en vivo, en la Mac del usuario a través de OpenClaw: PASÓ, 36/52 contra los 38/52 de REAL4 en vLLM (LIVE-library, 2026-10-01 [ran])**, y se sirve con la compuerta de citación prendida, `page_top = 8`, la guarda estricta y una respuesta para cada pregunta (LIVE-library2, GATE0, PAGE0 **[ran]**).

## 1. Los cinco minutos

| minuto | qué hay en pantalla | qué muestra | estado |
|---|---|---|---|
| 1 | un endpoint compatible con OpenAI; varios adaptadores sobre un ~~`Qwen3.5-4B`~~ `gemma-4-E4B-it` residente (todo el pool desde M1b, 2026-09-26); cada pedido ruteado al suyo | el servicio reemplaza sin cambios el modelo que configura un runtime de agentes | **[ran]** P62, P63 |
| 2 | **demo de la escuela [ran] 2026-09-26: 15/15 sobre cada rol y caja del diagrama de referencia — y 15/15 otra vez a través del OpenClaw real con Claude Haiku 4.5 como frontera** ([`LIVE`](../../results/LIVE-school-openclaw-20260926/BRIEF.md)) ([`results/DEMO-school-diagram-20260926/`](../../results/DEMO-school-diagram-20260926/BRIEF.md)); primero 8/8 el 2026-09-25 — **sobre Gemma 4 E4B + el LoRA del personal, cada respuesta anclada por el gateway** ([`results/DEMO-school-gemma-20260925/`](../../results/DEMO-school-gemma-20260925/README.md)) · las **seis escenas** de la distribuidora — estado de pedido, stock, un ticket de mantenimiento, un rechazo entre inquilinos, una instrucción plantada reportada y no obedecida, y un pedido que nada cubre, abstenido y derivado a la frontera — le piden al modelo local; llama a la capa de herramientas real y responde con lo que la herramienta devolvió, o deriva | un modelo chico atiende tareas rutinarias por rol, con herramientas, local, y sabe qué queda fuera de ellas | escuela **[ran]** 8/8; distribuidora **[ran]**: el E4B pelado **1/5** (`DEMO-org-gemma-20260926`, pide un id de pedido que ya tenía) → con el LoRA del personal de la distribuidora **5/5** (M9: retenidos 70/70) → enseñado a abstenerse, **6/6** incluyendo la escena de frontera (`results/M10-distributor-abstain-20260928/`) — y **6/6 en vivo**, en la propia máquina del usuario por llama.cpp + OpenClaw, el sexto turno escrito por Claude Haiku 4.5 por **$0,0112** (`results/LIVE-distributor-openclaw-20260928/`) |
| 3 | el mismo usuario pide el pedido de otro cliente: **la herramienta se niega**; una nota de entrega trae una instrucción plantada: se reporta, no se obedece | el permiso vive fuera del modelo; un prompt no lo puede ampliar | capa de herramientas **[ran]** 77 casos adversariales, 0 fugas; lado del modelo, esta demo y, en vivo sobre la Air, `results/LIVE-distributor-openclaw-20260928/` |
| 4 | una pregunta de dos o tres saltos — *¿qué interno tiene el encargado del depósito que guarda este producto?* — recorrida por una wiki de **enunciados atómicos**, respondida con la cita `[id§anchor]` que el runtime verifica | los hechos viven en páginas editables, no en pesos; cada respuesta nombra el enunciado en que se apoya | **[ran]** W9 — PASÓ: 35/40 contra el 0/40 del recorrido sin entrenar; sobre Gemma 4 E4B 38/40; con comparaciones en su corpus, 37/40 en una banda comparativa (B5); en la corrida de la demo, `distributor-wiki@v2` 2/2 correctas y citadas |
| 5 | la ruta: un pedido en la región de un miembro entrenado queda local, uno fuera de toda región sale hacia la frontera; la factura de los turnos atendidos localmente, a las tarifas de la propia frontera | dónde está la plata — y qué no está cotizado | ruta **[ran]** ROUTE0 (los tres brazos de pedido completo de M2 fallaron primero); factura **[ran]** primera pasada de M6 |

## 2. Qué decir sin rodeos

| afirmación | estado honesto |
|---|---|
| "un 4B atiende local tus tareas rutinarias por rol" | para tareas de rol de una sola herramienta el 4B **sin entrenar** ya llega a 18/19 **[ran]** piloto de la escuela — el valor ahí es mover el tráfico a local, no un adaptador |
| "un adaptador lo convierte en experto" | mostrado en triage de correo (0,989 contra 0,345 del base pelado) y en los roles del personal de la escuela: 70/70 turnos held-out contra el 27/70 del Gemma pelado, día de la demo 8/8 contra 3/8 **[ran]** M8 — sobre turnos generados, no tráfico real |
| "sabe cuándo derivar" | ~~el router hoy es un diccionario de palabras clave; se midieron dos routers aprendidos y **ninguno pasó**~~ el router del proxy es uno **factorizado** — la tarea contra el contenido del miembro — que sirve 0 de 600 textos ajenos localmente (los 294 del diccionario) y pierde 0 de 480 pedidos legítimos, después de que fallaran tres routers de pedido completo **[ran]** ROUTE0, M2; una paráfrasis de la tarea igual sale, por diseño (0/120 se mantienen locales), y mantenerla le cuesta precisión a un miembro entrenado en una regla compuesta **[ran]** P2a (la demo muestra la salida). Un miembro sí puede aprender su *propio* límite: el `out-s0` de la distribuidora contesta `OUT OF SCOPE` en 20 de 20 pedidos retenidos que sus herramientas no cubren, y el egreso del rol los reenvía **[ran]** M10 — eso es el límite propio del rol, no el router eligiendo entre miembros |
| "la memoria es verificable" | cada respuesta sobre la wiki cita el enunciado en el que se apoya y el árbitro la chequea (W9 **[ran]**); frente a las herramientas, el gateway no muestra ninguna línea que una herramienta no haya devuelto — reemplazó 2 de 5 respuestas locales el día de la demo, así que el modelo todavía inventa y el sistema todavía lo atrapa |
| "ahorra plata" | **no mostrado sobre tráfico real.** La factura del replay es de centavos; el costo de la GPU local no está cotizado. El número que lo decide es tu tráfico, medido |

## 3. Qué la convertiría en un resultado real

Una muestra del tráfico de agentes del propio equipo — pedidos por rol, con las herramientas que usó
cada uno — reproducida por el brazo nulo del proxy (`training/harness/null_arm.py`): la parte que un
miembro local podría tomar, la que tiene que salir, y la factura de las dos maneras. Es la medición que
este repositorio no puede hacer sobre suites generadas, y la que una demo debería terminar pidiendo.
