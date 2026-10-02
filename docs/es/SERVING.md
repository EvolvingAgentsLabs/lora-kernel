# Servir el pool a un runtime de agentes

> **El sistema que esto sirve está descrito en [`ARCHITECTURE.md`](ARCHITECTURE.md); en qué
> se apoya cada número de acá está en [`RECORD.md`](RECORD.md).**

Esto es con lo que habla un agente — OpenClaw, Hermes, cualquiera que hable OpenAI.
Cada pieza fue medida antes de ensamblarse, y la única que no lo fue está nombrada al
final en vez de quedar para descubrirse.

## La forma

    agente  --(OpenAI, tools=[…], tool_calls)-->  proxy  --(etiquetas)-->  vLLM + adaptadores

Dos procesos. vLLM sostiene una base residente con los adaptadores registrados como
nombres de modelo; el proxy traduce en ambas direcciones y reenvía todo lo demás sin
tocarlo.

## Cómo se corre

    # 1. el pool
    vllm serve Qwen/Qwen2.5-3B-Instruct --enable-lora --max-lora-rank 16 \
        --max-loras 2 --dtype bfloat16 \
        --lora-modules kernel=adapters/kernel-mt domain=adapters/domain-mt

    # 2. la traducción
    python3 -m training.harness.openai_proxy --upstream http://127.0.0.1:8000 --port 8001

Apuntá el agente a `http://127.0.0.1:8001/v1` y poné `model` en `kernel` o `domain`.
`/v1/models` los lista.

## El perfil edge: llama.cpp en tu propia máquina, al lado de `server`

![Dos mitades. Izquierda, server: una placa alquilada en una nube con un lomo grueso y cuatro lomos finos de adaptadores, muchos usuarios, cuatro adaptadores en un lote sin contención. Derecha, edge: una notebook con un usuario y un lomo fino que se cambia en tres milisegundos, llama.cpp en 8 bits, una línea punteada a la frontera. En el medio, un banco chico: MLX, el banco de investigación.](../img/runtimes.png)

*Dos runtimes: vLLM en una placa alquilada para medir, entrenar y servir a muchos; llama.cpp en tu propia máquina para servir a uno.*

Todo lo de arriba es el perfil **`server`**: vLLM en Colab, y por ahí pasa cada medición y cada
entrenamiento de este repositorio. **`edge`** es un segundo perfil, decidido el 2026-09-28, para
servir un miembro ya liberado a un runtime de agentes en vivo, en la máquina que lo corre — sin
tarjeta alquilada, sin túnel **[ran]** `results/MAC2-llamacpp-20260927/`,
`results/LIVE-distributor-openclaw-20260928/`. ~~MLX se queda como el motor de `edge`~~ — ese
veredicto (2026-09-27) era sobre decodificación especulativa, nada más; MLX se queda como banco de
investigación, por el acceso en Python que da al grafo (hot-swap por puntero 2,9 µs), no como lo que
contesta un pedido en vivo. El motor que hace eso en la Mac del usuario es **llama.cpp**.

    # una vez por miembro: su LoRA a GGUF
    python llama.cpp/convert_lora_to_gguf.py --base <snapshot HF de gemma-4-E4B-it> --outtype f16 \
        --outfile lora-distributor-staff-out-s0-f16.gguf adapters/distributor-staff-out-s0
    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-distributor-staff-out-s0-f16.gguf \
        --port 8792 -c 8192 -ngl 99

**Usá el E4B como Q8_0, nunca Q4_0.** Q4_0 no es sólo un archivo más chico: invierte un id de orden
adentro de la propia caché de prompts de llama.cpp **[ran]** LIVE-distributor, así que un pedido en
vivo puede servirse contra el turno cacheado equivocado. `edge` significa Q8_0 hasta que eso se
arregle aguas arriba.

La fuerza del adaptador es un campo por request en la llamada de completions (`"lora": [{"id": 0,
"scale": 1.0}]`), y el adaptador mismo se cambia en caliente sin reiniciar el servidor: `POST
/lora-adapters` sobre una instancia corriendo cambia el GGUF de un miembro por otro y restaura la
base exactamente, en **3 ms** **[ran]** MAC2 — tres órdenes de magnitud por debajo del propio cambio
de vLLM de 0,25 s, en una máquina sin memoria de sobra para un segundo modelo residente.

**llama.cpp no corta en el stop string** — una completion no se detuvo en la etiqueta de cierre
propia del miembro como sí lo hace la de vLLM, y un turno en vivo siguió de largo inventando texto;
el arreglo es del lado del cliente, no un flag (`accept_rank.close_open_tag`) **[ran]**
LIVE-distributor. Quien reuse `edge` necesita ese mismo parche, no sólo la misma línea de comandos.

**vLLM tiene la falla opuesta en el mismo lugar: rechaza de plano demasiadas secuencias de parada.** Una
superficie de herramientas que cierra más de cuatro etiquetas distintas hace que cada pedido se rechace
con HTTP 400 en el endpoint OpenAI de vLLM 0.30 — un error de transporte, no de puntuación, y anuló de
lleno el primer intento de H2 **[ran]** `h2_attempt1_void_http400.json`. El arreglo, el `MAX_STOPS = 4` de
`training/harness/accept_rank.py`: pasadas esas tantas etiquetas de cierre, el pedido envía una sola
parada genérica, `"</"`, y el mismo `close_open_tag` de arriba reconstruye la etiqueta específica a partir
de dentro de qué texto quedó. Una sola función, los dos motores, por razones opuestas.

## El endpoint de la biblioteca: el miembro de documentos reales como servidor compatible con OpenAI

`examples/library/serve.py` sirve a `real-none-s0` — el miembro aceptado después de REAL4
([`ARCHITECTURE.md`](ARCHITECTURE.md) §4) — de la forma en que un runtime de agentes realmente le hablaría: un
proceso, una biblioteca, el propio runtime de REAL4 (el texto completo de la pregunta como primera búsqueda en todos
los estantes, un fallback a todos los estantes, páginas abiertas con sus enunciados). Es el perfil `edge` de arriba
más el runtime de la memoria delante, no una tercera cosa.

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-real-none-s0-f16.gguf --port 8793 -c 12288 -b 512 -ub 512 -ngl 99
    python -m examples.library.serve --library knowledge/logistics-regs --upstream http://127.0.0.1:8793 --port 8766

**En una Mac de 16 GB, achicar el contexto y limpiar la GPU primero.** 16.384 es contra lo que se midieron las
propias preguntas de REAL4 sobre vLLM, pero una máquina de 16 GB no tiene 16.384 tokens de contexto de sobra *y* el
resto de la pila: usar **`-c 12288 -b 512 -ub 512`**, y asegurarse de que nada más esté reteniendo memoria de GPU
antes de arrancar `llama-server` — el primer intento en vivo acá se quedó sin memoria exactamente por esto, otra
sesión ya tenía el `llama-server` reteniendo ~8 GB; el segundo intento, a 12.288, corrió de punta a punta y
**PASÓ** (36/52 contra el 38/52 de vLLM, titular y negativas exactos) — las cuatro pérdidas que cuesta son
recorridos que desbordan 12.288 tokens tras abrir entera una página larga, leídas donde ocurren, no como del miembro
([`LIVE-library`](../../results/LIVE-library-20261001/BRIEF.md)).
Q8_0, no Q4_0, por la misma razón que cualquier otro miembro en `edge` — el vuelco del order-id del caché de prompt
de arriba.

**Una página larga es la otra mitad del mismo límite de contexto, y ahora tiene su propio presupuesto.**
`--page-budget` (default **2.500** tokens Gemma) acota con qué abre una página: por encima del presupuesto,
`memory.runtime.Conversation` muestra los propios enunciados de la página en orden BM25 contra la pregunta hasta
gastar el presupuesto, en orden del documento, y después lista el resto como anclas abribles (`id§ancla`) — sólo
los enunciados mostrados cuentan como leídos. En esta biblioteca sólo 29 CFR 1910.178 (7.389 tokens entera) lo
supera, a 2.452–2.558 tokens después. Elegido offline, antes de cualquier recorrido: de 1.500 a 3.500 de presupuesto
los 8 enunciados que necesitan los recorridos oráculo de REAL4 en esa página se mantienen 8/8
([`LIVE-library2`](../../results/LIVE-library2-20261002/BRIEF.md)).

**La regla de salida de red es la misma del gateway (§6 de [`OPENCLAW.md`](OPENCLAW.md), [`MECHANISMS.md`](MECHANISMS.md)
§6): cerrada por default.** `serve.py` instala `examples.common.egress` antes de que cargue cualquier otra cosa,
permitido sólo hacia el upstream de `llama-server` y loopback, con `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` fijados
para que cargar el tokenizador nunca llegue al hub de modelos — el mismo refuerzo que el gateway consiguió con el
#310, aplicado a esta segunda puerta de entrada.

**Apuntarle OpenClaw es registrar un proveedor, no parchear un agente.** El endpoint escribe su propio parche de
OpenClaw al arrancar (`--openclaw-patch`, default `~/.config/lora-kernel/openclaw/library-reader.json5`):

    {
      models: { providers: { library: { baseUrl: "http://127.0.0.1:{port}/v1", api: "openai-completions",
        auth: "api-key", apiKey: "local", models: [ { id: "auto", name: "regulations library — real-none-s0" } ] } } },
      agents: { defaults: { model: "library/auto" } }
    }

Un pedido entra, un recorrido sale: la respuesta lleva la contestación con su citación renderizada como
`[título de página §ancla]`, o `Not in my library.`, y el propio campo `x_walk` de la respuesta lleva todo el
recorrido — ids mostrados, enunciados abiertos — así que un driver puede calificar la citación exactamente como lo
hizo la medición, en vez de volver a parsear el texto de la respuesta. `examples/library/live_library.py` es ese
driver: manda las 52 preguntas de REAL4 por `openclaw agent --local`, una sesión fresca por cada una, y califica el
propio registro de recorrido del endpoint con el calificador de REAL4. **Construido, probado offline, y ahora
corrido de punta a punta sobre el servidor real: PASÓ** — 36/52 contra el 38/52 de REAL4 sobre vLLM bf16 (titular
16/23 y negativas 15/16 exactos, un salto 5/13), 22,5 minutos, 2026-10-01
([`LIVE-library`](../../results/LIVE-library-20261001/BRIEF.md)) — ver [`OPENCLAW.md`](OPENCLAW.md)
sobre cómo apuntarlo a una instancia de OpenClaw corriendo.

**Una corrida de seguimiento reparó las dos pérdidas del borde y leyó SIN CAMBIO.** OpenClaw también reenvía una
pregunta lenta envuelta en su propio sobre de mensaje encolado, sobre el que corría la primera búsqueda del runtime;
`examples/school/gateway.runtime_request` ahora lo quita antes de que el runtime lea la pregunta. Con eso y el
presupuesto de página de arriba, las mismas 52 preguntas: **37/52** — titular 16/23, negativas 14/16, un salto 7/13
— contra el 36/52 de esta corrida y el 38/52 de REAL4 sobre vLLM; **0** desbordes de contexto (4 antes), **0**
sobres (3 antes), pareado contra esta corrida **3 : 2** ($p = 1,0$). Veredicto tal como está escrito: **SIN CAMBIO**
— 0 desbordes pero 37 < 38, no REGRESADO ([`LIVE-library2`](../../results/LIVE-library2-20261002/BRIEF.md)).

**El endpoint siempre responde, aunque el recorrido mismo lance una excepción.** Un desborde de contexto o un
upstream caído solían cerrar el socket sin respuesta; OpenClaw leía eso como una falla de transporte y
reenviaba el turno envuelto en su propio sobre `[Queued user message from a previous active turn …]` — hasta
cinco veces, ninguna registrada. El handler de `serve.py` ahora atrapa la excepción y responde 200 con
`NO_ANSWER`, el error registrado al lado del recorrido: una solicitud entra, una respuesta sale, sin importar
cómo termine el recorrido.

**`--cite-gate`: el chequeo de citación como compuerta, prendida por defecto.**
`memory.runtime.Conversation.final_problem` es el mismo chequeo que CITE0 midió como pista
(`citation_problem`, que lee sólo el propio registro del referí: los ids mostrados, los enunciados abiertos,
su propio texto), aplicado una vez a la línea final del recorrido; detrás de `--cite-gate` una línea que no la
pasa no se entrega — la respuesta pasa a ser `UNVERIFIED` ("The library could not verify an answer to this —
its citation does not check out.") en vez del propio texto del recorrido, reenviando a una frontera
configurada donde exista una. El recorrido mismo no cambia; la compuerta lee el mismo registro que ya escribía
`cite_check`. Repetido exacto sobre 14 brazos `+page` dejados afuera de REAL3–REAL7 (532 recorridos, dos
bibliotecas): 0 de 275 respuestas correctas bloqueadas, 86 de 165 respuestas incorrectas bloqueadas (52,1 %),
0 de 11 respuestas a preguntas sin respuesta entregadas, precisión 0,625 → 0,777 — LA COMPUERTA FUNCIONA según
la propia barra del brief. Lo que queda, dicho con honestidad: de las 86 bloqueadas, 43 tenían el valor
correcto bajo una cita que falla (43 de 347 valores correctos retenidos, 12,4 %) — **sale prendida por
defecto, decisión del usuario del 2026-10-02 que acepta ese costo; `--no-cite-gate` la apaga**
([`GATE0`](../../results/GATE0-cite-gate-20261002/BRIEF.md)).

## Cuánto cuesta servir en vivo: el orden le gana al tamaño, y dos adaptadores no cuestan el doble

Dos hallazgos de la misma corrida ponen precio al motor mismo, en `server` y en `edge` por igual,
porque los dos sirven a través de una caché de prefijos y un batch multi-adaptador.

**Un bloque de herramientas puesto después del pedido nunca es un prefijo compartido.** El corpus de
un miembro pone el pedido primero y la superficie (grande) de herramientas después — la forma que
enseñó el corpus, no un accidente — así que dos pedidos nunca comparten ese bloque como prefijo aun
con la caché encendida. Sirviendo el bloque real de 54 herramientas de OpenClaw (7.205 tokens de
Gemma) así, después del pedido, sobre el miembro de la escuela (E4B, vLLM 0.30) el tiempo al primer
token va de 0,10 s a 1,70 s (16,8×) y el throughput con 8 en vuelo de 132 a 108 tok/s, al lado de la
exactitud cayendo 70/70 → 39/70 **[ran]** `results/E5-engine-baseline-20260928/`. Donde el prefijo
entero se repitió en cambio, el mismo bloque no costó nada (0,09–0,11 s) — **la caché la vence el
orden en que el corpus puso las cosas, no el tamaño del bloque.**

~~**Dos LoRAs en un mismo batch se quedan con 0,88 del throughput de uno solo.** Una ráfaga de 16
pedidos repartida entre dos adaptadores servidos juntos pierde 12% contra servir los mismos 16 por
separado — contención, no una pared, y vale la pena tarifarla antes de dimensionar un servidor para
más de un miembro a la vez **[ran]** E5.~~

**Superada — C1 [ran] 2026-09-29: bajo carga sostenida, cuatro miembros mezclados no cuestan
throughput contra uno solo.** El 0,88 de E5 era una sola ráfaga de 16 pedidos; C1
(`training/harness/load_test.py`, una L4, vLLM 0.30, `google/gemma-4-E4B-it` bf16, cuatro miembros:
`school-s0`, `upper-s0`, `staff-s0`, `out-s0`) corrió la misma pregunta como una curva. Con 16
sesiones concurrentes, cuatro adaptadores mezclados entregan **278,6 tok/s** contra **269,7 tok/s**
de un solo adaptador — una razón de **1,03**, contra una barra de contención de 0,8. Con 32
sesiones, cuatro adaptadores llegan a **504,3 tok/s** con **p95 de tiempo al primer token 0,24 s** y
**0 errores de 128** pedidos. El throughput escala casi linealmente con las sesiones (22,7 → 135 →
270 → 500 tok/s para 1 → 8 → 16 → 32), y el techo está por encima de 32 sesiones, no alcanzado
[`results/C1-concurrency-20260929/BRIEF.md`](../../results/C1-concurrency-20260929/BRIEF.md). **No
medido:** más de cuatro adaptadores, sesiones más allá de 32, el overhead propio del gateway,
generaciones más largas.

## Las opciones de servido del gateway: `history=`, `memory=`, `workflows=`, `tool_block=`

`examples/school/gateway.py`'s `Gateway` es la segunda puerta de entrada del pool — una organización
por proceso, recorrida de punta a punta en [`OPENCLAW.md`](OPENCLAW.md) §6. Hay tres organizaciones
registradas en `ORGS` y se eligen con `--org`: `school`, `distributor`, y, desde el 2026-09-29,
`tracker` (`examples/tracker`, una herramienta de equipo tipo Jira + Confluence — ver
`docs/MECHANISMS.md` §9). Cuatro opciones del constructor deciden qué lee un turno, además del
prompt y las herramientas propias del rol:

| opción | por defecto | qué hace |
|---|---|---|
| `history=True` | `False` | renderiza cada pedido y respuesta anterior antes del actual — la forma ingenua de cargar una conversación multi-turno, el brazo `history` de `out-s0` en MT0 más abajo |
| `memory=<OpMemory>` | `None` | activa el arnés de flujos de trabajo (`examples/common/opmemory.py`): un turno lee una línea de contexto — el estado del flujo de trabajo del rol y los **nombres** de las claves de sus cachés de sesión y de organización, nunca sus valores — y el miembro busca (`<get>`) o guarda (`<put>`) un valor sólo en el paso que lo necesita |
| `workflows={role: Workflow}` | `{}` | mapea un rol a su máquina de estados declarada (`examples/<org>/workflows/*.toml`); el gateway avanza el estado por las llamadas que la capa de herramientas **ejecutó**, nunca por el modelo |
| `tool_block=False` | `True` | quita la superficie de herramientas renderizada del turno — el miembro confía en conocer sus herramientas por su propio corpus (el brazo `harness-noblock` de H1, **0/60**: su corpus siempre tuvo el bloque, así que sacarlo al evaluar lo dejó sin llamar nada) |

Desde la línea de comandos (2026-09-30): `--memory` enciende la memoria operativa con los workflows declarados de la organización (`examples/<org>/workflows/*.toml`), `--no-tool-block` fija `tool_block=False`, `--max-calls N` acota las llamadas a herramientas de un turno; `--state-dir` persiste lo que espera a una persona (aprobaciones, handoffs) y la salida de red queda cerrada a los hosts configurados salvo `--open-egress` (`docs/MECHANISMS.md` §5, §6). La sesión de la memoria es el header `X-Session-Id` del cliente o el campo `user` del pedido, si no una por token (`tests/test_tracker.py`: dos sesiones de un mismo usuario no comparten una clave). El miembro del tracker se sirve así en vivo en [`results/LIVE-tracker-openclaw-20260930/BRIEF.md`](../../results/LIVE-tracker-openclaw-20260930/BRIEF.md) — **[ran] PASÓ, 14/14 turnos, dependientes 8/8** en la Mac del usuario. En `edge` el stop de muchos tags (`"</"`) también se descarta, como cualquier string de stop: `accept_rank.completion` reconstruye el tag en cualquiera de los dos servidores (LIVE-tracker intento 1, nulo).

`history=True` y `memory=…` responden el mismo problema de dos maneras distintas y no están
pensadas para correr juntas: history es la línea de base contra la que se mide el arnés de flujos de
trabajo, no una segunda copia de él. H1 (`results/H1-workflow-harness-20260929/`) puntuó los dos brazos
contra ella sobre vLLM (una L4): `harness` (con el bloque) alcanzó 53/54 turnos dependientes contra el
43/54 de history; `harness-noblock` colapsó, por la razón de arriba. Leído por brazo, `harness` PASÓ y
`harness-noblock` quedó FALSEADO, pero la propia compuerta de la corrida la anula tal como está escrita
— la decisión del usuario (2026-09-29): vale la lectura por brazo, el VOID tal como está escrito queda
como el registro de ese error del instrumento. Una segunda corrida, **H2** sobre la organización
`tracker` de arriba, encontró la misma regla mal aplicada de otra forma — anuló a una línea de base sin
entrenar en vez de a un brazo roto — y se lee FALSEADA tal como está escrita, en el registro con ese y el
error de instrumento del chequeo de anchor. **La decisión del usuario (2026-09-29), como para H1: lectura
1** — las condiciones legibles son el veredicto de H2, `harness` **PASÓ** (146/160, plano, descriptivo
142:0). `harness-noblock` (80/160) es un error del corpus, no un aprendizaje parcial — su tercio sin
bloque compartía módulo (`% 3`) con la rotación de roles, así que las filas sin bloque eran todas de QA.
**H3 [ran], las dos barras PASARON**: `tr-s1`, entrenado sobre un segundo corpus (fraseo ampliado por
turno en cada rol, un tercio parejo sin bloque de cada rol), le gana a `tr-s0` 158/160 contra 147/160
sobre una suite fresca retenida (pareado 11:0, $p = 0,00098$, plano), y sin el bloque de herramientas
sostiene 156/160 en cada rol a más o menos un tercio de los tokens de prompt — el miembro de contexto
compacto ahora funciona
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
**El arnés desde entonces corrió en vivo a través de OpenClaw**: `tr-s1` sin bloque, en `edge` (llama.cpp en la
propia Mac del usuario), en tres sesiones (lead, developer, QA) — 14 de 14 turnos, dependientes 8 de 8
([`LIVE-tracker`](../../results/LIVE-tracker-openclaw-20260930/BRIEF.md)); ver [`OPENCLAW.md`](OPENCLAW.md) para la
historia del multi-turno y `docs/review/harness-workflow-kv.md` §§8–9 para los resultados completos y las lecturas
elegidas.

## La base tiene que ser una a la que vLLM realmente le aplique adaptadores — se chequea, no se supone

**vLLM puede aceptar un LoRA, registrar en el log que lo cargó, y servir la base.**
Sin error, sin advertencia. Sobre `Qwen/Qwen3.5-4B` el servidor imprime

    Loaded new LoRA adapter: name 'tiny', path 'adapters/tiny-subject'

y después devuelve texto **idéntico byte a byte al de la base** en cada request
**[ran]** `results/P33-lora-matrix-20260914/`. El adaptador de esa corrida era real:
entrenado sobre esa base, con `lora_B` movido, y cambiaba la salida del modelo en
proceso. Un despliegue que leyera esa línea del log creería estar sirviendo un experto.

**Así que lo primero que se corre contra una base nueva es la compuerta de identidad**,
antes de juntar cualquier número de exactitud:

    python3 -m training.harness.serve_openai --base <modelo> \
        --adapter tiny=<adaptador> --gate-only --out gate.json

Manda un prompt a la base y a cada adaptador y compara. El `gate_verdict` se lee
**del archivo**: el proceso sale 0 en una corrida limpia cuya compuerta dijo *not
applied*, así que el código de retorno no es la respuesta.

| veredicto | qué significa |
|---|---|
| `applied` | el texto servido difiere del de la base; seguir |
| `not applied: served text is identical to the base` | **parar**; todo número posterior mide la base |
| `inconclusive: the adapter was refused out loud` | desajuste de forma o de rango, no un no-op silencioso |

**Las familias que este repositorio chequeó:**

| base | ¿vLLM 0.29.0 aplica los adaptadores? |
|---|---|
| `Qwen/Qwen2.5-3B-Instruct` | **sí** — el pool corre sobre ella |
| `Qwen/Qwen3.5-4B` | **sí, una vez que los tensores del adaptador llevan los nombres de la clase que vLLM sirve** — tal como los escribe PEFT por `AutoModelForCausalLM`, **no, en silencio** |

**Por qué la misma base da las dos respuestas — D2 [ran] 2026-09-19**,
`results/D2-rekey-20260918/`. vLLM sirve `Qwen3.5-4B` como
`Qwen3_5ForConditionalGeneration` y activa los pesos del adaptador por
`language_model.model.layers.N…`; un adaptador entrenado por la clase de sólo texto los
nombra `model.layers.N…`. La carga valida sólo el último componente de cada nombre — de ahí
la línea *Loaded* — y la activación, al no encontrar un módulo con ese nombre completo,
resetea el slot detrás de un mensaje de debug. Los mismos pesos con 496 tensores
renombrados, sin reentrenar, vuelven `applied`:

    python3 -m training.harness.rekey adapters/<tal-como-se-entrenó> adapters/<renombrado>

Leído durante cinco días como un límite del stack de serving, era un desajuste de nombres.
La lección que enseña la compuerta no cambia y se afila: **la línea del log no es el
veredicto — el texto servido lo es.**

## Rutear lo que el pool no sabe hacer — el end-to-end que corre hoy

**Ésta es la configuración para usar de verdad.** El pool sirve aquello en lo que está
medido que es bueno; todo lo demás se reenvía a un modelo de frontera en tu cuenta.

    # 1. el pool
    vllm serve Qwen/Qwen2.5-3B-Instruct --enable-lora --max-lora-rank 16 \
        --max-loras 2 --dtype bfloat16 \
        --lora-modules email-full=adapters/email-full

    # 2. la traducción, con ruta de salida
    export OPENAI_API_KEY=...        # nunca en la línea de comandos: `ps` la ve
    python3 -m training.harness.openai_proxy \
        --upstream http://127.0.0.1:8000 --port 8001 \
        --fallback https://api.openai.com/v1

Apuntá el agente a `http://127.0.0.1:8001/v1`. Pedí **`email-full`** y contesta el
experto local; pedí **cualquier otro nombre de modelo** y el request se reenvía.

**Lo que se queda es lo que el pool sirve**, leído del propio `/v1/models` del
upstream — mejor que una lista escrita a mano, que se desactualiza apenas se agrega un
adaptador. Se puede fijar con `--local a,b` cuando querés ser explícito.

**Qué decide la ruta hoy, y qué se probó en su lugar [ran] M2 2026-09-19.** `--auto` usa el
diccionario de palabras clave de `route.py`. Un modelo del corpus de cada miembro — el router
del diseño — se midió primero como modelo de n-gramas: sobre texto ajeno es más seguro (0 de
128 servidos por un miembro local contra el 59 del diccionario), y manda afuera **todos** los
pedidos legítimos cuyo remitente el generador nunca sorteó, 120 de 120. Así que el diccionario
se queda como default, y el costo conocido de eso queda registrado: un pedido que sólo
*contiene* la pregunta de un miembro — "…¿esto es importante para mergear antes del viernes?" —
lo sirve ese miembro. El brazo de embeddings es lo próximo
(hito 2 de [`PLAN.md`](PLAN.md)), y va a compartir su espacio con la base de conocimiento de
cada subdominio (hito 7): **esta página todavía no sirve ninguna base de conocimiento.**

**Sobre una base 3.x el canal de pensamiento está apagado para los miembros.** El proxy manda
`chat_template_kwargs: {"enable_thinking": false}` en cada request de un miembro, así que el
prompt servido es un prefijo exacto del texto con el que se entrenó al miembro; una plantilla
sin ese switch lo ignora.

### El número que esto vale

| | entrega | sale de la máquina |
|---|--:|--:|
| todo local | 0,546 | 0% |
| **la región que falla, reenviada** | **0,775** | **38%** |

**[ran]** `results/P41-routing-20260915/`. En su región el experto local le gana a la
base **8 : 51** sobre los mismos casos; la región donde falla, falla 12/90 y una
frontera contesta 66/90. **Pagamos la parte que medimos que no sabemos hacer.**

### Qué sale, y cómo lo ves

Un request reenviado **sale de tu máquina**. Para suites sintéticas eso no es nada;
para correo real es el mensaje. El proxy imprime una línea por request reenviado:

    [route] OUT -> gpt-5 · 4 messages · 2317 chars · 3 tools

**Formas, nunca contenido** — la misma línea que sostiene `openclaw_traffic.py`. Podés
ver qué salió sin que la transcripción quede escrita en un log, y un test verifica que
el contenido no sobrevive al anuncio.

Un fallback configurado sin credencial **se niega a arrancar**, en vez de fallar en la
primera escalación.

### Qué NO hace

**No decide caso por caso.** La ruta es por nombre de modelo, que es la elección del
que llama. La escalación por caso está medida y hoy es **peor**: las dos reglas
disponibles entregan menos que rutear por región, porque buscan una cadena
inconsistente y las cadenas de este experto son consistentes y equivocadas **[ran]**
P41. Es un problema abierto, no una función faltante.

## Qué está medido, y dónde

| | resultado | paso |
|---|---|---|
| cada adaptador es su propio nombre de modelo, y **se aplica** | base y adaptador responden distinto | P26 |
| etiquetas → `tool_calls` | **0 de 38** líneas que nombren un dominio; **604/604** idas y vueltas | P27 |
| `tools=[…]` → superficie de etiquetas | cuesta **0,188** en los valores del oráculo | P27 |
| la convención de aridad | recupera el **55%**, rechazos **88 → 17** | P28 |
| declarar los valores permitidos (`enum`) | **lo empeoró** — apagado por defecto | P28 |

## Qué está ensamblado y sin medir

**El bucle multi-turno — ahora ejercitado, ver el ejemplo trabajado abajo.** Un agente
devuelve resultados con `role: "tool"` y el proxy los pliega en la transcripción como
`= valor`, donde el adaptador fue entrenado para leerlos. **Todas las mediciones
anteriores a P30 fueron de un solo turno** — P27 brazo 3
explícitamente. `tests/test_proxy.py` muestra que la traducción no pierde nada y que
un resultado aterriza en la línea que lo pidió; **no** muestra que el adaptador siga
correctamente desde ahí. **Esa es otra afirmación y no está comprada.**

## Qué no hace

- **No elige el adaptador.** Lo elige el campo `model` del cliente, porque S3 midió
  un router empatando con una tabla de búsqueda y todavía no hay nada mejor que
  ofrecer.
- **No hace streaming.** Una etiqueta recién es una llamada cuando se cierra, así que
  hacer streaming significaría bufferear la respuesta entera y llamarla stream. El
  proxy lo rechaza con esa frase en vez de fingirlo.
- **No agrega conocimiento de dominio.** No nombra herramientas, argumentos ni
  unidades; hay un test que falla si eso deja de ser cierto.

## Antes de entrenar nada para un despliegue nuevo

    python3 -m training.harness.openai_proxy --upstream … --log traffic.jsonl
    python3 -m training.harness.null_arm --log traffic.jsonl

Dos preguntas, las dos contestadas desde el tráfico mismo y ninguna necesita GPU más
allá de la base ya servida.

**¿Hay una región?** La afirmación de la arquitectura es que un experto chico le gana
a un generalista *dentro de su región* — S5 cerró la brecha de retiro a 0,000 en
región, y las fórmulas de ese mismo experto caen de 30/30 a 1/20 afuera. Si el
tráfico es cola larga no hay nada en qué especializarse, y la recomendación honesta es
un generalista. El instrumento dice `NO REGION` cuando las tres formas más comunes
cubren menos del 60% de los pedidos, y está escrito para poder decirlo.

**¿La base sostiene el protocolo?** Con qué frecuencia el modelo base *solo* emite una
llamada bien formada. Si no puede, un adaptador encima no lo arregla — la compra
siguiente es otra base, no un entrenamiento. Y las llamadas que nombran una
herramienta que nadie ofreció se cuentan aparte, porque P25 midió exactamente ese
fallo en el 56% de los rechazos sobre un tema desconocido.

## Apuntar un agente real

Dos formas, y **la primera conviene hacerla antes que la segunda.**

### 1. Medir el tráfico mientras el agente sigue trabajando

    python3 -m training.harness.openai_proxy \
        --upstream https://api.openai.com --upstream-key "$OPENAI_API_KEY" \
        --passthrough --log traffic.jsonl --api-key "$(openssl rand -hex 16)"

En `--passthrough` no se traduce nada: el pedido va arriba tal como llegó y la
respuesta vuelve sin tocar. **El agente sigue dando sus respuestas de siempre** y la
corrida deja un registro de las formas que envía. Ese registro es la entrada que el
brazo nulo necesita, y no se puede adivinar desde una suite.

**Sólo se registran formas** — qué herramientas se ofrecieron, cuán profunda fue la
conversación, y el texto de la respuesta. El prompt no se escribe: es del usuario, y
la medición no lo necesita.

### 2. Servir el pool por un túnel

    # dentro de una sesión de Colab
    bash training/harness/tunnel.sh

Levanta vLLM con los adaptadores, el proxy en `:8001` y un túnel rápido de
Cloudflare, e imprime una URL base pública y una clave generada. Apuntá el agente a
`<url>/v1`.

**La clave no es opcional y el script no corre sin una.** Un túnel convierte un proxy
de localhost en un endpoint de inferencia público; uno abierto es la GPU de otro, y
una URL difícil de adivinar no es un control. La comparación es de tiempo constante.

**Qué esperar de las respuestas.** El pool es un 3B con un adaptador que sabe mecánica
de fluidos y un kernel entrenado en tres herramientas. En trabajo de agente general va
a andar **mal**, y eso no es un bug para reportar — es la pregunta de la región de la
sección anterior, llegando como experiencia en vez de como número.

### Cuando la credencial del agente no se puede proxyear

`--passthrough` necesita un token que el proxy pueda reenviar. Un OpenClaw que habla
con ChatGPT por una sesión OAuth no lo tiene — meter un proxy en el medio significaría
tomar la credencial del usuario, y además no hace falta:

    python3 -m training.harness.openclaw_traffic --out traffic.jsonl
    python3 -m training.harness.null_arm --log traffic.jsonl

**OpenClaw ya registra cada corrida.** Esto lee su log de trayectoria y emite las
mismas líneas que consume el brazo nulo — **sin el prompt, sin el texto del asistente
y sin los argumentos de ninguna llamada.** La pregunta de la región es sobre formas, y
ninguna necesita el contenido.

Y se niega a fingir: con menos de cincuenta corridas avisa que la muestra es muy chica
y que tres formas cubriendo el 60% de seis corridas no es evidencia de una región.

## Un ejemplo trabajado: el correo de una mañana

    python3 -m training.harness.agent_sim \
        --base-url http://127.0.0.1:8001/v1 --model kernel --n 12

`training/email/` es una región con forma de una real: una tarea estrecha repetida
todos los días, con una respuesta **verificable mecánicamente**. Un mensaje es
importante cuando se cumplen al menos dos de *continúa un hilo en el que escribí*,
*dirigido a mí directamente*, *me pide algo*, *remitente frecuente* — y nunca cuando
es automático.

**Los dos hechos decisivos no están en el listado.** Si el usuario escribió en el
hilo vive detrás de `thread_history`; cuánta correspondencia real existe vive detrás
de `sender_stats`. Una regla que sólo lee el listado saca **0,680 contra una barra de
clase mayoritaria de 0,680** sobre los mensajes humanos — no le gana al azar
informado ni por un caso, y hay un test que lo afirma en vez de confiarlo.

`agent_sim` tiene forma de cliente, no de test: habla sólo OpenAI — una base URL, un
nombre de modelo, `tools`, `tool_calls`, `role: "tool"` — así que cualquier cosa que
necesite y el protocolo no provea es una brecha entre este proyecto y un runtime
real.

**Esto es lo que cerró el bucle multi-turno**: 24 llamadas, 0 rechazadas, 0 sin
decidir, contra un modelo stub a través del proxy real. La sección de arriba ya no
dice que ese camino esté sin medir — pero mirá qué mide. **La plomería, no el pool.**
Ningún adaptador entrenado corrió todavía sobre esta suite.
