# Reconocimiento de τ²-bench (T0, pasos 2–4)

**Escrito el 2026-10-05** para `results/TAU2-T0-recon-20261005/BRIEF.md`. Toda afirmación es **[read]** de
`sierra-research/tau2-bench` en el commit fijado, salvo que diga **[ran]**; las rutas de abajo son relativas a
ese checkout (`~/evolvingagents/tau2-bench`). No se puntuó ningún miembro y no corrió ningún modelo localmente.

| | |
|---|---|
| commit | `5bfa7e37b36656b37dc6d022156be6563c1007f3` (2026-09-28, `git describe` v1.0.1-47) |
| paquete | `tau2` 1.0.1 (`pyproject.toml`), Python 3.12.13, litellm 1.81.11, gymnasium 1.2.2 |
| registro completo | `results/TAU2-T0-recon-20261005/MANIFEST` |

**Estado, 2026-10-05, después de las decisiones del usuario (`results/TAU2-T0-recon-20261005/BRIEF.md`).** T0 **pasa por la
opción (b)**: no se reprodujo ningún puntaje publicado; en cambio, `tau2 evaluate-trajs` recalificó los cuatro archivos de
trayectorias de airline que vienen con τ² y **800 de 800 simulaciones obtienen la recompensa registrada** [ran], así que el
calificador local es el calificador de τ². El maestro y el simulador de usuario son **Gemma 4 31B, autoalojado**
(`docs/tau2/TEACHER-TERMS.md`). Las secciones de abajo se escribieron antes de esas decisiones y se dejan como se
escribieron; donde una dice "decide el usuario" o "no se corrió", ese es el estado del reconocimiento, no del plan.

## 0. Instalación y corrida de mock [ran]

- El README pide `uv sync` y Python `>=3.12,<3.14` (`README.md:37`, `:58–73`). Se instaló en su propio
  `.venv` (python3.12) con `uv sync --extra gym --extra dev`, que sigue `uv.lock`.
- **La instalación base no importa.** `tau2` falla con `ModuleNotFoundError: websockets`: la cadena de importación
  `data_model/simulation.py:62` → `voice/audio_native/openai/provider.py:12` necesita `websockets`, que sólo instala el
  extra `voice`. Se arregló con `uv pip install websockets` (queda en el MANIFEST). En Colab, hacer lo mismo o instalar
  `--extra voice`.
- **Mock, haiku 4.5 como agente y como simulador de usuario, 3 tareas × 1 intento:** `create_task_1` 1,0,
  `update_task_1` 1,0, `impossible_task_1` 0,0 → **pass^1 = 0,667**. El comando está en el MANIFEST, los resultados en
  `results/TAU2-T0-recon-20261005/mock_results.json`. El arnés corre de punta a punta.
- **El único fallo fue del simulador, y es lo que cuesta plata.** En `impossible_task_1` el agente
  llamó correctamente a `transfer_to_human_agents`; el *usuario* haiku nunca mandó `###TRANSFER###`
  (`data/tau2/user_simulator/simulation_guidelines.md:15`) y los dos modelos se agradecieron mutuamente durante 200
  mensajes hasta `max_steps`. Cualquier terminación que no sea una parada del agente o del usuario puntúa 0
  (`src/tau2/evaluator/evaluator.py:115–127`). Esa única conversación costó **0,96 USD de los 0,97 de la corrida**.
  Lección para T1: el fallo de un simulador de usuario débil parece un fallo del agente y se paga por paso. Poner tope a
  `--max-steps` (o `--timeout`) en toda corrida simulada con haiku, y decir en el reporte que se hizo.

## 1. Dominios

Registrados (`src/tau2/registry.py`; los imprime `tau2 run --help`): **`mock`, `airline`, `retail`, `telecom`,
`telecom-workflow`, `banking_knowledge`**. Conjuntos de tareas: `mock`, `airline`, `retail`, `telecom_full`,
`telecom_small`, `telecom`, `telecom-workflow`, `banking_knowledge`.

| dominio | tareas (`tasks.json`) | particiones (`split_tasks.json`) |
|---|---|---|
| mock | 10 | base 10 |
| airline | **50** | **train 30 / test 20 / base 50** |
| retail | 114 | train 74 / test 40 / base 114 |
| telecom | `tasks.json` 2.285 | small 20 / train 74 / test 40 / full 2.285 / base 114 |
| banking_knowledge | 97 (+698 documentos) | sin archivo de particiones |

**`banking_knowledge` existe.** Es un dominio de recuperación que necesita `--extra knowledge` y un
`--retrieval-config` (`README.md:28`, `:70`; `src/tau2/knowledge/README.md`). Su calificación cambió en v1.0.1, y
los resultados de antes de esa versión no son comparables (`README.md:24`).

## 2. Airline

### Política
`data/tau2/domains/airline/policy.md`, 1.313 palabras. Secciones: Domain Basic (User / Flight / Reservation), Book
flight, Modify flight, Cancel flight, Refunds and Compensation (`grep '^#'`). Reloj fijo: "The current time is
2024-05-15 15:00:00 EST" (`policy.md:3`; también `AirlineTools._get_datetime`, `src/tau2/domains/airline/tools.py:100–102`).
Reglas que tocan la brecha de formato: obtener un "yes" explícito antes de cualquier escritura (`policy.md:7`), y "only
make one tool call at a time … not respond to the user simultaneously" (`policy.md:11`). La regla no se hace cumplir a
menos que se pase `--enforce-communication-protocol`.

### Herramientas (14) — `src/tau2/domains/airline/tools.py`, tipo según `@is_tool(ToolType.…)`

| herramienta | tipo | argumentos (tipo JSON-schema) | línea |
|---|---|---|---|
| `book_reservation` | WRITE | user_id, origin, destination, flight_type, cabin (str); **flights, passengers, payment_methods (arreglo de objetos)**; **total_baggages, nonfree_baggages (int)**; insurance (str) | 186 |
| `calculate` | GENERIC | expression | 321 |
| `cancel_reservation` | WRITE | reservation_id | 339 |
| `get_reservation_details` | READ | reservation_id | 371 |
| `get_user_details` | READ | user_id | 387 |
| `list_all_airports` | READ | — | 403 |
| `search_direct_flight` | READ | origin, destination, date | 432 |
| `search_onestop_flight` | READ | origin, destination, date | 451 |
| `send_certificate` | WRITE | user_id, **amount (int)** | 488 |
| `transfer_to_human_agents` | GENERIC | summary | 532 |
| `update_reservation_baggages` | WRITE | reservation_id, **total_baggages, nonfree_baggages (int)**, payment_id | 547 |
| `update_reservation_flights` | WRITE | reservation_id, cabin, **flights (arreglo de objetos)**, payment_id | 591 |
| `update_reservation_passengers` | WRITE | reservation_id, **passengers (arreglo de objetos)** | 692 |
| `get_flight_status` | READ | flight_number, date | 720 |

El esquema OpenAI de las herramientas ocupa 11.148 caracteres como JSON **[ran]**. **τ² no valida los tipos de los
argumentos al llamar:** `ToolKitBase.use_tool` llama a la función de Python con `**kwargs` directamente
(`src/tau2/environment/toolkit.py:138–142`). Un string `"50"` donde el esquema dice `integer` entra a la base de datos
como string, y la comparación de la base falla después.

### Base de datos
`data/tau2/domains/airline/db.json`, 7,0 MB: **300 vuelos, 500 usuarios, 2.000 reservas** [ran]. Los modelos están en
`src/tau2/domains/airline/data_model.py` (`User` :203, `Reservation` :222, `Flight` :162, unión de medios de pago
tarjeta de crédito / tarjeta de regalo / certificado :53–73, unión de estados de fecha de vuelo :94–141).

### Recompensa
- **Toda tarea de airline tiene `reward_basis = [DB, COMMUNICATE]`** (50/50 [ran]). 43 de 50 tareas tienen
  `actions` de referencia (media 2,84, máximo 19). Las 50 tienen `nl_assertions` y 6 tienen `communicate_info`. Ninguna
  tarea tiene `initial_state`.
- La recompensa final = **producto** de los componentes de la base (`evaluator.py:241–256`). ACTION y NL_ASSERTION
  no están en la base de airline, así que ni la coincidencia de llamadas a herramientas ni el juez LLM (por defecto
  gpt-4.1, `config.py:24`) **cuentan**. La calificación de airline no necesita modelo juez.
- **DB:** reproducir las acciones de referencia de la tarea en un entorno nuevo, reproducir la trayectoria del agente en
  otro, y comparar el SHA-256 de `json.dumps(db.model_dump(), sort_keys=True)` de ambos, tanto para la base del agente
  como para la del usuario (`evaluator_env.py:104–131`, `utils/utils.py:39–45`). La coincidencia es todo o nada.
- **COMMUNICATE:** cada string de `communicate_info` debe aparecer, sin distinguir mayúsculas y sin comas, como
  subcadena de algún mensaje de texto del asistente (`evaluator_communicate.py:60–70`). Si la lista está vacía, el
  puntaje es 1.
- Una corrida que llega a max_steps, a demasiados errores o a un timeout puntúa 0 antes de cualquiera de estos chequeos
  (`evaluator.py:115–127`).
- Éxito = recompensa a menos de 1e-6 de 1 (`metrics/agent_metrics.py:12–14`).

### pass^k
`pass_hat_k(n, c, k) = C(c, k) / C(n, k)` por tarea (`agent_metrics.py:113–126`, citando arXiv 2406.12045),
promediado sobre las tareas (`:169–180`, `:238–244`). Con 1 intento, pass^1 es la tasa media de éxito.

### Particiones — y la regla "nada se ajusta sobre test"
- τ² trae una partición oficial: **airline train 30 / test 20, disjuntas** [ran], `base` = las 50
  (`data/tau2/domains/airline/split_tasks.json`; la carga `src/tau2/domains/airline/environment.py:35–53`;
  agregada en 0.2.1 "Train/test task splits for all domains", `CHANGELOG.md:244`). Se elige con `--task-split-name`.
- **La partición por defecto y el leaderboard usan ambos `base`, que incluye las 20 tareas de test**
  (`README.md:35`, `docs/leaderboard-submission.md:25`). Así que un número publicado de airline es sobre train+test.
  Para este proyecto: ajustar y destilar sólo sobre `train`, reportar el miembro sobre `test`, y tratar una
  comparación sobre `base` con el leaderboard sólo como contexto. 20 tareas de test es un denominador chico: una tarea
  son 5 puntos, y el error estándar binomial con p≈0,7 es de unos 10 pp por intento.

### Simulador de usuario
- Modelo por defecto `gpt-4.1-2025-04-14`, temperatura 0,0 (`src/tau2/config.py:18–22`). Se cambia con
  `--user-llm` / `--user-llm-args`.
- Prompt de sistema = guías globales (`data/tau2/user_simulator/simulation_guidelines.md`, o `_tools.md` cuando el
  usuario tiene herramientas) + persona + `<scenario>{instructions}</scenario>` (`src/tau2/user/user_simulator.py:33–37`, `:86–92`).
  La conversación termina con los tokens `###STOP###`, `###TRANSFER###` y `###OUT-OF-SCOPE###` (`simulation_guidelines.md:14–16`).
- Las corridas publicadas del leaderboard v1.0.1 usan **gpt-5.2 (reasoning_effort low)** como simulador de usuario,
  4 intentos, semilla 300 (p. ej. `web/leaderboard/public/submissions/claude-sonnet-4-5_sierra_2026-02-26/submission.json`, methodology.notes).

### Cómo se configura el modelo del agente
- `--agent-llm <string de modelo de litellm>`, por defecto `gpt-4.1-2025-04-14`, temperatura 0,0 (`config.py:17–21`).
  `--agent-llm-args '<json>'` se pasa tal cual como `**kwargs` a `litellm.completion`
  (`src/tau2/utils/llm_utils.py:409–415`).
- **Endpoint compatible con OpenAI (vLLM o el shim):** `--agent-llm openai/<nombre-servido> --agent-llm-args
  '{"temperature":0,"api_base":"http://HOST:PORT/v1","api_key":"x"}'`. Que ese `api_base` pase es
  [read] por el pase directo de kwargs y la convención de proveedores de litellm. La documentación de τ² nunca lo
  menciona. `OPENAI_API_BASE` en el entorno es la alternativa de litellm. Costo de un modelo sin precio: `completion_cost`
  lanza excepción, y τ² registra el error y anota **0,0** (`llm_utils.py:119–131`).
- Prompt de sistema: `<instructions>` (responder o llamar a una herramienta, nunca ambas; "generate valid JSON only") +
  `<policy>{policy.md}</policy>` (`src/tau2/agent/llm_agent.py:24–41`).
- **El formato de herramientas es function calling nativo vía litellm.** Cada llamada manda `tools=[t.openai_schema …]` con
  `tool_choice="auto"` (`llm_utils.py:388–391`). El historial vuelve como mensajes OpenAI: un turno del asistente lleva
  `tool_calls[{id, type:"function", function:{name, arguments: json.dumps(args)}}]` y cada resultado es un
  `{"role":"tool","content":…,"tool_call_id":…}` (`llm_utils.py:168–209`). Los resultados son strings JSON del valor de
  retorno de pydantic (`environment/environment.py:413+`). Se aceptan varias llamadas en un mismo mensaje del asistente:
  en las trayectorias de airline de gpt-4.1-mini que vienen incluidas, 221 mensajes del asistente llevan más de una llamada
  y 185 llevan texto más una llamada [ran], a pesar de `policy.md:11`.

### Interfaz Gymnasium / RL
`src/tau2/gym/gym_agent.py` (`--extra gym`; `src/tau2/gym/README.md`). `register_gym_agent()` registra
`AgentGymEnv` (`TAU_BENCH_ENV_ID`, :45, clase :549), donde uno hace de agente contra el simulador de usuario, y
`UserGymEnv` (:1091), donde uno hace de usuario. `reset()` → (observación, info con `tools`, `policy`).
`step(action: str)` (:747) toma **un solo string**: un `ToolCall` en JSON, una **llamada funcional
`name(arg=value, …)`**, o texto plano para el usuario, que analiza `tau2.utils.tools.parse_action_string`. El
orquestador corre en un hilo. La recompensa es `evaluate_simulation(..., EvaluationType.ALL)` sobre lo corrido hasta ahora
(:832–857), así que es rala y terminal, 0 hasta que la conversación termina con normalidad. `truncated` es siempre False.
`tau2 play` es la versión interactiva.

### Puntajes de referencia y costo [read]
Pass^1 publicado de airline (texto, `web/leaderboard/public/submissions/*/submission.json`):

| modelo | pass^1 | sim. de usuario | ver. τ² | agente USD/conv. |
|---|---|---|---|---|
| Claude Sonnet 4.5 (thinking) | 72,0 | gpt-5.2 | 1.0.1 | 0,296 |
| Claude Opus 4.5 | 84,0 | gpt-5.2 | 1.0.1 | 0,399 |
| GPT-5.2 (reasoning none) | 52,5 | gpt-5.2 | 1.0.1 | 0,054 |
| GPT-5.2 | 83,0 | gpt-5.2 | 1.0.1 | 0,114 |
| GPT-4.1-mini | 48,7 | gpt-4.1 | 0.1.3 | — |
| Claude 3.7 Sonnet | 64,2 | gpt-4.1 | 0.1.3 | — |

- **No hay entrada publicada para claude-haiku-4-5**, y ninguna entrada de texto publicada usa un simulador de usuario
  Claude. Toda entrada v1.0.1 usa gpt-5.2 como simulador.
- **Con sólo la clave de Anthropic no se puede reproducir ningún puntaje publicado.** Cada configuración publicada
  necesita una clave de OpenAI para el simulador. Bajo la compuerta del brief este es el caso "se reporta como no
  reproducido, decide el usuario". Las opciones son: (a) una clave de OpenAI y Sonnet 4.5 + gpt-5.2 (≈ 50 × (0,30 + sim) ≈ 17–20 USD
  con k=1, más de la mitad de T0+T1); (b) GPT-5.2-none + gpt-5.2 (el publicado más barato, unos pocos USD, sólo OpenAI); (c) haiku 4.5
  para ambos, que no tiene ancla y sirve sólo como línea base interna.
- **Las trayectorias incluidas no coinciden con el leaderboard.** `data/tau2/results/final/` trae archivos de airline de 4
  intentos. La recompensa media del archivo de gpt-4.1-mini es 0,505 contra 48,7 listado, y la del archivo de claude-3-7-sonnet es
  **0,50 contra 64,2 listado** [ran]. Ambos archivos son anteriores a las correcciones de tareas de v1.0 (commits `ade3949`, `c30d59a`).
  No citar ninguno como objetivo de reproducción sin esa advertencia.
- **Un chequeo gratis que vale la pena correr primero:** `tau2 evaluate-trajs` recalifica las trayectorias incluidas sin
  llamadas a modelos. Eso muestra que el calificador local coincide, separado de si un modelo reproduce.
- **Estimación de costo, agente + simulador haiku 4.5, airline, k=1.** Tokens del archivo de airline de claude-3-7 incluido
  (tokenizador de Claude, 200 simulaciones) [ran]: agente ≈ 107k de entrada / 1,8k de salida por conversación, usuario ≈ 6,1k de entrada / 0,24k de salida,
  29 mensajes. A precio de lista 1 / 5 USD por MTok (`model_cost` de litellm) [read], eso es ≈ 0,116 + 0,007 ≈
  **0,12 USD por conversación → ≈ 6,2 USD para base (50) y ≈ 2,5 USD para test (20)**, sin prompt caching.
  Encima está el riesgo de cola medido en la corrida mock, ≈ 1 USD por conversación desbocada con max_steps=200.
  Esto no cabe en el tope de 3 USD de esta tarea, así que no se corrió.

## 3. La brecha de formato

### Los dos lados
- **τ²** manda `tools=[…]` (esquema OpenAI) más `tool_choice:"auto"`, lee los `tool_calls` de vuelta, los ejecuta
  él mismo, y devuelve cada resultado como un mensaje `role:"tool"` con un `tool_call_id` (§2).
- **Los miembros** escriben etiquetas en línea y leen los resultados en línea. La etiqueta es `<nombre>k=v; k=v</nombre>`, o `<nombre>valor</nombre>`
  para una herramienta de un solo argumento. El resultado sigue como `= valor` en la misma transcripción corrida, y la generación
  se detiene en la etiqueta de cierre (`training/harness/tool_calls.py`, `training/harness/accept_rank.run_chain`,
  `examples/common/agent_loop.py`). Servidos al revés, se rompen (11/90 contra 90/90, CLAUDE.md).

### Lo que ya existe en este repositorio
`training/harness/openai_proxy.py` **ya es este shim** para los runtimes de agentes OpenAI, y casi todo se reutiliza:

- `render_tools` + `tool_calls.tools_to_instruction`: renderiza `tools=[…]` como el bloque de etiquetas, con la convención de aridad.
- `rebuild_transcript`: pliega el historial de `tool_calls` + `role:"tool"` de vuelta a etiquetas más `= valor`. Su docstring
  lo marca como *sin medir*.
- `tool_calls.to_tool_calls`, `strip_calls`, `keep_offered` y `stop_for`: convierten las etiquetas de vuelta en `tool_calls`
  y se detienen en `</etiqueta>` con `include_stop_str_in_output`.
- `enable_thinking: False` para los miembros. SSE con buffer (τ² no hace streaming; irrelevante acá).
- `examples/school/gateway.py` es el otro patrón: **el gateway ejecuta las herramientas él mismo** (`run_chain` sobre
  una `ToolSuite`). τ² debe ejecutar cada llamada él mismo para que la reproducción de la DB la califique, así que el patrón
  del gateway **no** es reutilizable acá. Sólo lo es el patrón del proxy.

### Qué se rompe si se apunta el proxy a τ² airline sin cambios [ran sobre datos incluidos, sin modelo]
Reproduje las 1.587 llamadas a herramientas de las trayectorias de airline de gpt-4.1-mini incluidas, pasándolas por
`from_tool_call` → `to_tool_calls`:

- **Ida y vuelta exacta: 1.345 / 1.587.** Toda pérdida cae sobre las llamadas que importan para la DB: **se pierden 220 de 320 llamadas
  de escritura**, que son todas las de `book_reservation`, `update_reservation_flights`, `update_reservation_baggages`,
  `update_reservation_passengers` y `send_certificate`. Sólo sobrevive `cancel_reservation`, que tiene un argumento
  string. Causas: los arreglos anidados de objetos vuelven como un string truncado; los enteros vuelven como
  strings, y como τ² no hace coerción de tipos (`toolkit.py:138–142`) el hash de la DB falla; `PAIR` corta un valor en
  `,`, lo que truncó 19/40 resúmenes de `transfer_to_human_agents`; y una llamada sin
  argumentos (`list_all_airports`, 3/3) se descarta porque un cuerpo vacío cuenta como marcador de posición.
- `MAX_ROUNDTRIPS = 6` cuenta cada mensaje `role:"tool"` de la conversación. Airline promedia 7,9 llamadas por
  conversación (máximo 36), y **106 de 200 conversaciones superan 6** [ran]. Pasado ese punto el shim convertiría
  cada llamada posterior en texto.
- `under_member_prompt` (`--member-prompt`) **reemplaza** los mensajes de sistema, lo que borraría la política de
  airline. Para τ² no debe usarse tal cual.

### Especificación del adaptador (no construido)
Un shim HTTP compatible con OpenAI entre τ² y vLLM, `openai_proxy` con un perfil τ²:

1. **Conectarlo.** `--agent-llm openai/<miembro> --agent-llm-args '{"temperature":0,"api_base":"http://shim:8001/v1","api_key":…}'`.
   El shim reenvía a `/v1/chat/completions` de vLLM sacando `tools`/`tool_choice`. El simulador de usuario nunca
   pasa por el shim.
2. **Entrada (τ² → miembro).** Conservar el prompt de sistema de τ² (instrucciones + política). Un prompt de miembro, si lo hay,
   se *antepone*, nunca se sustituye. Renderizar `tools` con `tools_to_instruction`. Plegar el historial con
   `rebuild_transcript`, de modo que cada turno con `tool_calls` pase a sus etiquetas y cada `role:"tool"` pase a `= <string json>`
   emparejado por `tool_call_id`.
3. **Codificación de argumentos (el único cambio real).** El cuerpo de la etiqueta es `k=v; k=v` sólo cuando todo valor es un string
   sin `; , < = salto de línea` y sin espacios alrededor. En otro caso el cuerpo es el **objeto JSON de los
   argumentos**: `<book_reservation>{"user_id": …, "flights": [{…}], "total_baggages": 1}</book_reservation>`.
   La regex CALL `[^<]*` ya admite JSON sin `<`. Decodificación: un cuerpo que empieza con `{` pasa por
   `json.loads`, cualquier otro por el camino `k=v` existente. **Después, coerción de escalares por el tipo JSON
   declarado en el esquema** (`integer`, `number`, `boolean`). Esto lo maneja el propio esquema de τ², así que sigue siendo un serializador y
   no nombra ningún dominio. Un cuerpo vacío en una herramienta cuyo esquema no tiene propiedades es una llamada con `{}`, no un marcador de posición.
   Candidato medido sobre las mismas 1.587 llamadas: **1.587/1.587 exactas** [ran]; 242 de ellas necesitan el cuerpo JSON.
   Una alternativa que ya está dentro de τ² es la sintaxis funcional del gym `name(k='v', n=1, flights=[…])`
   (`to_functional_format` / `parse_action_string`), que también da ida y vuelta **1.587/1.587** [ran]. No es
   la superficie entrenada de los miembros, sin embargo, así que la etiqueta con cuerpo JSON queda más cerca del corpus.
4. **Salida (miembro → τ²).** Detenerse en `</etiqueta>`, incluirla, y emitir **una** entrada de `tool_calls` con un
   id único por conversación (no `call_0` reusado en cada turno). El contenido es `None` cuando hay una llamada, lo que
   coincide con `policy.md:11`. Cortar el texto posterior a la etiqueta de cierre. Una etiqueta cuyo nombre no se ofreció se devuelve
   como texto y se cuenta.
5. **Topes.** Sin `MAX_ROUNDTRIPS` para τ². Rigen los propios `--max-steps` / `--max-errors` de τ², y cualquier tope del shim es
   por turno del asistente, nunca por conversación. `MEMBER_MAX_TOKENS` debe alcanzar para un `book_reservation` en JSON, así que
   subirlo a por lo menos 512.
6. **Registro.** Una línea por pedido, sólo con formas (herramientas ofrecidas, llamadas de salida, descartadas, cuerpo JSON vs k=v), como hace `_record`.

### El chequeo de no pérdida (el paso de Colab de T0, antes de puntuar cualquier miembro)
- **G-shim-1, offline, $0, corre en la Mac (sin modelo):** reproducir toda trayectoria de τ² disponible (los archivos de airline
  incluidos más los resultados del mock) por entrada renderizada → salida analizada. Afirmar **identidad** de
  `(name, arguments)` en cada llamada a herramienta, con tipos, e identidad de cada string de resultado de herramienta recuperado
  de la transcripción renderizada. Pasa = 100%, sin tolerancia.
- **G-shim-2, Colab:** `mock` de τ² (`create_task_1`, `update_task_1`) con el agente servido **a través del shim**
  por un modelo cuyo function calling nativo también funcione (el Gemma 4 base sobre vLLM). Correrlo dos veces, una de forma nativa
  (`openai/<base>` directo a vLLM con su parser de herramientas) y otra por el shim, y verificar que ambas corridas
  terminan con normalidad. El registro de pedidos del shim debe mostrar que lo que recibió τ² es igual a lo que escribió el modelo. Este
  es el chequeo del camino. No es un puntaje.
- **G-shim-3, chequeo de fuga:** confirmar que el shim ve sólo los mensajes del agente y las herramientas de τ². Nada de los
  `evaluation_criteria` de la tarea ni de las acciones de referencia puede llegarle (no puede, por construcción, pero afirmarlo en el registro).

## 4. Gasto
Corrida mock: 207 llamadas a modelos, **0,970 USD** (`cost` por mensaje de τ²/litellm), registradas una por una en
`results/TAU2-T0-recon-20261005/spend.jsonl`. Todo lo demás de este documento se leyó o se calculó offline.
