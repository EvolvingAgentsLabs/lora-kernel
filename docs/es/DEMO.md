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

Para la versión en vivo — el mismo modelo detrás de OpenClaw, turno por turno — ver
[`OPENCLAW.md`](OPENCLAW.md); corrió en vivo, 40 turnos, todos locales **[ran]** P63.

## 1. Los cinco minutos

| minuto | qué hay en pantalla | qué muestra | estado |
|---|---|---|---|
| 1 | un endpoint compatible con OpenAI; varios adaptadores sobre un `Qwen3.5-4B` residente; cada pedido ruteado al suyo | el servicio reemplaza sin cambios el modelo que configura un runtime de agentes | **[ran]** P62, P63 |
| 2 | roles de una distribuidora — atención al cliente, compras, IT — le piden al modelo local; llama a la capa de herramientas real y responde con lo que la herramienta devolvió | un modelo chico atiende tareas rutinarias por rol, con herramientas, local | **[ran]** esta demo (`training/harness/demo_org.py` parte A) |
| 3 | el mismo usuario pide el pedido de otro cliente: **la herramienta se niega**; una nota de entrega trae una instrucción plantada: se reporta, no se obedece | el permiso vive fuera del modelo; un prompt no lo puede ampliar | capa de herramientas **[ran]** 77 casos adversariales, 0 fugas; lado del modelo, esta demo |
| 4 | una pregunta de dos o tres saltos — *¿qué interno tiene el encargado del depósito que guarda este producto?* — recorrida por una wiki de **enunciados atómicos**, respondida con la cita `[id§anchor]` que el runtime verifica | los hechos viven en páginas editables, no en pesos; cada respuesta nombra el enunciado en que se apoya | **[spec → corriendo]** W9 — ver su brief para saber dónde está |
| 5 | la ruta: un pedido en la región de un miembro entrenado queda local, uno fuera de toda región sale hacia la frontera; la factura de los turnos atendidos localmente, a las tarifas de la propia frontera | dónde está la plata — y qué no está cotizado | ruta **[ran]** M2; factura **[ran]** primera pasada de M6 |

## 2. Qué decir sin rodeos

| afirmación | estado honesto |
|---|---|
| "un 4B atiende local tus tareas rutinarias por rol" | para tareas de rol de una sola herramienta el 4B **sin entrenar** ya llega a 18/19 **[ran]** piloto de la escuela — el valor ahí es mover el tráfico a local, no un adaptador |
| "un adaptador lo convierte en experto" | mostrado en triage de correo: 0,989 contra 0,345 del base pelado **[ran]**; **todavía no hay adaptador entrenado para ningún rol de distribuidora ni de escuela** |
| "sabe cuándo derivar" | el router hoy es un diccionario de palabras clave; se midieron dos routers aprendidos y **ninguno pasó** (una paráfrasis sale — la demo lo muestra) **[ran]** M2 |
| "la memoria es verificable" | el formato, el árbitro y la verificación de la cita están construidos; si un modelo chico la recorre, con o sin adaptador de trayectorias, es la medición abierta de W9 |
| "ahorra plata" | **no mostrado sobre tráfico real.** La factura del replay es de centavos; el costo de la GPU local no está cotizado. El número que lo decide es tu tráfico, medido |

## 3. Qué la convertiría en un resultado real

Una muestra del tráfico de agentes del propio equipo — pedidos por rol, con las herramientas que usó
cada uno — reproducida por el brazo nulo del proxy (`training/harness/null_arm.py`): la parte que un
miembro local podría tomar, la que tiene que salir, y la factura de las dos maneras. Es la medición que
este repositorio no puede hacer sobre suites generadas, y la que una demo debería terminar pidiendo.
