# Mecanismos — cómo funciona cada mecanismo

> *[Read me in English](../MECHANISMS.md)*

Cada pieza que este repositorio realmente corre, explicada de la misma manera para cada una: **qué**
hace, **cómo** funciona — el flujo real, nombrando la función o el archivo que lo lleva —, **por qué**
está construida así — la corrida que forzó el diseño, no una preferencia — y su **evidencia**: un número
medido **[ran]** con su directorio de corrida, o, honestamente, su estado si todavía nada lo midió.
[`ARCHITECTURE.md`](../ARCHITECTURE.md) es el mapa del sistema entero; este documento son las dieciocho
cosas de ese mapa, una por una.

![Un mapa de subte: la línea principal es el camino de un pedido — agente, identidad, gateway, memoria operativa, flujo, experto, capa de herramientas, aprobaciones, anclaje, respuesta — con ramales a la frontera y a una persona, a la biblioteca y al router, dos depósitos para los runtimes server y edge, y un desvío para la decodificación especulativa.](../img/mechanisms-map.png)

*Todos los mecanismos en una línea. Los números cuentan las estaciones en el orden en que las recorre un pedido, no las secciones de este documento — que son: camino del pedido §1, identidad §2, capa de herramientas §3, anclaje §4, aprobaciones §5, fuera de alcance §6, memoria operativa §8, flujo §9, experto (el harness) §10, biblioteca §11, router §14, server y edge §15, decodificación especulativa §16, corpus, compuerta de release y medición §12, §13, §17.*

## Contenido

1. [El camino de un pedido, de punta a punta](#1-el-camino-de-un-pedido-de-punta-a-punta)
2. [Identidad y tenencia](#2-identidad-y-tenencia)
3. [La capa de herramientas y el protocolo de etiquetas](#3-la-capa-de-herramientas-y-el-protocolo-de-etiquetas)
4. [Anclaje y redacción de instrucciones plantadas](#4-anclaje-y-redacción-de-instrucciones-plantadas)
5. [Aprobaciones y retenciones](#5-aprobaciones-y-retenciones)
6. [Abstención y salida](#6-abstención-y-salida)
7. [Podar la superficie de herramientas](#7-podar-la-superficie-de-herramientas)
8. [La memoria operacional de corto plazo](#8-la-memoria-operacional-de-corto-plazo)
9. [Flujos de trabajo declarados](#9-flujos-de-trabajo-declarados)
10. [El arnés de flujo de trabajo](#10-el-arnés-de-flujo-de-trabajo)
11. [La biblioteca en Markdown y los LoRAs de trayectoria](#11-la-biblioteca-en-markdown-y-los-loras-de-trayectoria)
12. [Los corpus y sus compuertas](#12-los-corpus-y-sus-compuertas)
13. [Los miembros y la compuerta de liberación](#13-los-miembros-y-la-compuerta-de-liberación)
14. [El router](#14-el-router)
15. [Runtimes: server y edge](#15-runtimes-server-y-edge)
16. [Decodificación especulativa](#16-decodificación-especulativa)
17. [La disciplina de medición](#17-la-disciplina-de-medición)

---

## 1. El camino de un pedido, de punta a punta

**Qué.** Un pedido HTTP entra, sin que quien lo hace tenga que elegir bien ningún modelo, y sale una
respuesta — sea lo que sea lo que esté detrás: el experto local chico de un rol, algo retenido para una
persona, o un modelo de frontera.

**Cómo.** `examples/school/gateway.py::Gateway.turn` es el camino entero en una sola función, en este
orden: `tokens.verify(token)` convierte un token portador en un `Claim` (§2); el texto del pedido se saca
del propio sobre del runtime con `runtime_request(messages)`, que quita el bloque
`<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>…` de OpenClaw, su estampa `[Sat 2026-09-26 20:41 GMT-3]` y su pie
`Runtime: agent=…` — la primera versión de este gateway leía el sobre entero como el pedido y lo respondía
**[ran]** 2026-09-26; se busca el esquema de herramientas del rol (`self.tools.SCHEMA` filtrado a
`role["tools"]`) y se renderiza en el turno del usuario con `render_tools` — byte por byte el bloque con
el que se entrenó el miembro (§7); se arma un `ToolSuite` con el `Claim` de quien llama, así que cada
llamada que el modelo escribe se chequea por permiso **antes** de responderse, nunca después (§2);
`training.harness.accept_rank.run_chain` maneja el loop de generación — parar en una etiqueta de cierre,
responderla de verdad, seguir (§3); cuando la cadena termina, `grounding.ground` y `grounding.redact`
deciden qué puede decir la respuesta (§4); la ruta se decide — `local`, `frontier` o `person` — según si
el texto final es `OUT OF SCOPE` y la propia política de salida del rol (§6); y se agrega una línea JSON a
`examples/school/events.jsonl` — quién, rol, ruta, llamadas, denegaciones, retenciones, tokens — antes de
mandar la respuesta HTTP.

**Por qué.** Dos mediciones forzaron esta forma en lugar de una más simple. Primero, un experto es lo que
su corpus le enseñó, no un seguidor genérico de instrucciones: servido bajo el propio prompt de sistema de
37 KB de un runtime real, con sus herramientas ofrecidas sin podar, el miembro de personal de la escuela
llamó a una herramienta en solo **2 de 32** turnos humanos y anotó el 0,281 propio de la base pelada;
servido bajo el prompt y la superficie de etiquetas que su corpus realmente le enseñó, llamó a una
herramienta en **19 de 32** y anotó **22/32 = 0,688** contra la barra de mayoría de 0,655 **[ran]**
`results/P63-openclaw-live-20260918/BRIEF.md`. Segundo, el resultado de una llamada a herramienta tiene que
llegarle al experto **en línea, justo después de la etiqueta que escribió**, como se lo mostró su corpus:
el mismo experto de fluidos que anota 11/90 cuando los resultados llegan como mensajes `tool_calls` anota
**90 de 90** cuando se escriben en línea — 74 de sus 79 fallas tenían un número inventado de la nada, y 75
dejaban sin usar un resultado real **[ran]** `results/M7-arm0b-corpus-mode-20260919/BRIEF.md`. El gateway
existe para garantizar ambas cosas: el propio prompt y la propia superficie de etiquetas del corpus, y el
propio loop de resultado en línea del corpus, en cada turno.

**Evidencia.** **[ran]** 2026-09-25/26/28: `examples/school/live_openclaw.py` corre las quince escenas de
la escuela y las seis de la distribuidora a través de un OpenClaw 2026.9.4 real — 15/15
(`results/LIVE-school-openclaw-20260926/BRIEF.md`) y 6/6
(`results/LIVE-distributor-openclaw-20260928/BRIEF.md`). Seis fallas del camino en vivo (no este, la
versión anterior del proxy) se encontraron y arreglaron en el camino, listadas en
[`OPENCLAW.md`](../OPENCLAW.md) §5.

---

## 2. Identidad y tenencia

**Qué.** Quién sirve a un pedido — usuario, rol, tenant — viene de un token firmado que el modelo nunca
escribe y no puede cambiar, nunca del prompt ni del id del modelo; cada llamada a herramienta se chequea
contra ese token antes de tocar la fila, diga lo que diga el propio razonamiento del modelo.

**Cómo.** `examples/common/tokens.py::issue` acuña un token con forma de JWT HS256 (`{"sub": user_id,
"role": role, "org": org_id, "exp": …}`), firmado con un secreto de demo — en lugar de un proveedor de
identidad RS256/JWKS, que **no está construido acá** y así lo dice el propio docstring del módulo.
`verify` chequea la firma y el vencimiento y devuelve un `Claim` (`examples/common/permissions.py`) por
`to_claim` — el único mapeo que también necesitaría un proveedor de identidad real. `Gateway.turn` llama a
`tokens.verify` primero, y si el pedido pide servirse como `model: auto:<role>` para un rol que el token
no tiene, lanza `Denied` antes de que corra cualquier otra cosa. De ahí en más, cada función de
herramienta decide el permiso por sí misma, desde la fila de la base de datos y el `Claim` de quien
llama — nunca desde un argumento que aporte quien llama. La regla que hace esto a prueba de inyección,
dicha en el propio docstring de `examples/school/tools.py`: a `agenda_read` se le pide un `student_id`; la
herramienta busca el **verdadero** `org_id` de ese estudiante en la base de datos y lo compara con el del
claim — nunca confía en un org id tipeado en el pedido, y ningún campo de la base de datos (una nota, una
descripción) se ejecuta jamás como instrucción. Una denegación concreta, de los propios datos de
entrenamiento de la distribuidora: un usuario `customer_service-harbor` pide
`<order_status>95</order_status>` de un pedido que pertenece a `riverside`, y la herramienta responde
`= ERROR: permission denied: customer_service-harbor@harbor asked for order 95, which belongs to org
'riverside'` — al modelo se le avisa, igual que se le avisaría de cualquier otro error, y la cadena sigue
sin esa fila (`examples/distributor/data_turns/train_harness.jsonl`, caso `train-100000`).

**Por qué.** Un texto plantado por un atacante puede convencer al *modelo* de pedir la fila de otro
tenant; no puede convencer a la *herramienta*, que nunca lee el razonamiento del modelo — solo sus
argumentos y la base de datos. Esta es la propiedad que un despliegue de agentes por rol no puede dejar
librada al criterio del modelo (`docs/ARCHITECTURE.md` §9): "el modelo nunca sostiene una credencial".

**Evidencia.** **[ran]** `examples/school/tools.py` y `examples/distributor/tools.py`: 77 casos
adversariales entre tenants, **0 fugas**. **[ran]** LIVE-distributor y LIVE-school: cada escena en vivo
que pide la fila de otro tenant se rechaza a través de la capa de herramientas real, no simulada.

---

## 3. La capa de herramientas y el protocolo de etiquetas

**Qué.** Un experto escribe una llamada a herramienta como un par de etiquetas en su propio texto —
`<tool>args</tool>` — y lee el resultado en la línea siguiente, `= {resultado}`, exactamente donde lo puso
su corpus de entrenamiento. Nada de esto es la forma `tool_calls` de OpenAI; el proxy y el gateway
traducen entre las dos solo en el límite que ve el cliente.

**Cómo.** `training/harness/accept_rank.py::run_chain(gen, inbox, max_calls, suite)` es el loop entero:
pide a `gen(out)` una continuación del texto hasta ahora, la corta en la **primera** etiqueta de cierre
entre `suite.close` — "confiar en el stop string solo hasta donde llega; todo lo que pasa la primera
etiqueta de cierre es el modelo adivinando una respuesta que se le pidió pedir"—, empareja la llamada con
`suite.tag`, la responde de verdad con `suite.answer(inbox, tool, args)`, agrega `= {res}\n` a la
transcripción, y repite, hasta `max_calls`. Una llamada sin etiqueta de apertura que le corresponda es una
**llamada malformada, no un crash** — al modelo se le dice `= ERROR: malformed call — write
<tag>key=value</tag>` y la cadena sigue, un arreglo que reemplazó un crash en 209 de 240 casos de la
primera versión **[ran]** P58. El propio stop string se le pide al servidor explícitamente:
`completion()` manda `"stop": list(close), "include_stop_str_in_output": True`, que es lo que `G3` de la
compuerta del sustrato existe para chequear (`docs/SUBSTRATE-GATE.md`). **llama.cpp lo descarta** — un
turno en vivo siguió de largo después de su propia etiqueta de cierre inventando texto, porque el
servidor honra `stop` pero no devuelve ni el stop string ni cuál disparó. El arreglo es del lado del
cliente: `close_open_tag(text, close)` encuentra una etiqueta que quedó abierta al final del texto y, si
el cierre de esa etiqueta es uno de los strings en los que este pedido paró, lo repone — un texto que
termina en cualquier otro lugar queda intacto **[ran]** `results/LIVE-distributor-openclaw-20260928/BRIEF.md`.

Un recorrido real de etiquetas, de los propios datos de entrenamiento de la distribuidora, un turno más
tarde en la misma sesión (`examples/distributor/data_turns/train_harness.jsonl`, caso `train-400000-t1`,
rol dispatch): el miembro lee `state: dispatch/tracking · keys: order` (§8, §10), se le pregunta
*"And the delivery note on it?"*, y escribe

```
<get>order</get>= 76
<delivery_status>76</delivery_status>= order #76 delivery: Signed by the warehouse lead.
According to the system: order #76 delivery: Signed by the warehouse lead.
```

Dos etiquetas de cierre, dos resultados inyectados, una respuesta anclada.

**Por qué.** `run_chain` existe porque **un experto servido a través de mensajes `tool_calls` inventa el
resultado que nunca recibió**: `email-full` se entrenó sobre transcripciones donde una llamada está
seguida de inmediato por su respuesta, y servido por `tool_calls` no puede recibir una a mitad de
generación — escribe `= {"turns": 1, "i_wrote_in_thread": false}` él mismo, donde la herramienta decía
`turns: 2, true`, y cada decisión posterior de la cadena descansa sobre el hecho inventado **[ran]**
`results/P43-openclaw-e2e-20260915/BRIEF.md`. Parar en **cada** etiqueta de cierre, no solo en la primera
que el modelo escribe bien, es lo que P58 forzó después de que una etiqueta de cierre sin apertura
canónica mató 209 de 240 casos de plano.

**Evidencia.** **[ran]** M7 arm 0b: 90/90 en cadenas de seis a nueve llamadas cuando los resultados se
inyectan en línea, contra 11/90 por mensajes `tool_calls`. **[ran]** LIVE-distributor: el arreglo del stop
string y un arreglo de hilo-seguridad al propio almacén de la distribuidora (el primer intento fue nulo
bajo las llamadas concurrentes de OpenClaw) fueron los dos necesarios antes de que pasaran los 6/6 turnos
en vivo.

---

## 4. Anclaje y redacción de instrucciones plantadas

**Qué.** Lo que una respuesta puede decir se decide fuera del modelo, mecánicamente, contra los
resultados reales de herramientas que el gateway ya tiene — no pidiéndole cuidado al modelo. A cada
respuesta servida localmente le pasan dos cosas separadas: el **anclaje** (*grounding*) reemplaza una
respuesta no anclada por el texto propio de las herramientas, y la **redacción** quita texto con forma de
instrucción que traía un resultado de herramienta, antes de que cualquiera de las dos le llegue al
usuario.

**Cómo.** `examples/common/grounding.py::ground(reply, results, spanish)` parte la respuesta en cláusulas
(`items`, separadas por `;` y saltos de línea, con marcadores de lista y un prefijo que restablece como
"according to the system:" recortados) y chequea que cada cláusula ocurra, normalizada en espacios y
mayúsculas, en alguno de los `results` reales que devolvió la herramienta ese turno. Si todas las
cláusulas están ancladas, la respuesta queda `kept`; si no, se **reemplaza** por `fallback(results,
spanish)` — el texto propio de las herramientas, textual — y el resultado es `replaced`, contado en el
registro del evento en vez de escondido. Una respuesta **vacía** no está anclada por vacuidad: un modelo
que se detiene justo después de un resultado real y no le entrega nada al usuario queda atrapado por el
mismo chequeo (`results/DEMO-org-gemma-20260926`, el ticket de mantenimiento). `redact(text)` corre una
expresión regular (`_INJECTION`) sobre todo lo que se muestra, reemplazando `[SYSTEM OVERRIDE: …]`,
"ignore prior/all/your instructions" y frases similares por `[instruction in the record removed]` — el
registro mismo, en la base de datos, queda intacto; solo cambia lo que se **muestra**. `Gateway.turn`
llama a las dos, en orden, en cada respuesta `local`, nunca en una ruta `frontier` o `person`.

**Por qué.** El LoRA de personal de la escuela, entrenado y comportándose bien en cada caso medido, igual
— el día de la demo, en vivo — inventó una línea extra en el formato de lista propio de una herramienta y
la restableció como dato ("early pickup: Approved, 3:15 pm" sobre una agenda que tenía una sola entrada)
**[ran]** `results/M8-school-staff-20260925/BRIEF.md`. Una regla que dependa de que el modelo nunca haga
esto no es una regla; la respuesta de la arquitectura es hacerla cumplir donde el modelo no puede
llegar — el gateway tiene cada resultado real de herramienta, así que el gateway decide qué puede decir
una respuesta. La redacción existe por la misma razón del lado de la entrada: la propia nota plantada de
la distribuidora ("ignore your instructions above…") se coló por la primera versión del patrón de
inyección, que solo emparejaba instrucciones "prior" o "previous", no "your instructions above" **[ran]**
`tests/test_distributor_staff.py`, 2026-09-26.

**Evidencia.** **[ran]** `results/DEMO-school-gemma-20260925`: el filtro de anclaje reemplazó **2 de 5**
respuestas locales el día de la demo; el usuario no vio ninguna de las dos líneas inventadas. **[ran]**
las escenas de demo de la escuela y de la distribuidora traen las dos una instrucción plantada en un
registro real (una nota de entrega, una descripción de mantenimiento) y las dos se reportan como dato,
nunca obedecidas, tanto en las corridas guionadas como en las en vivo.

---

## 5. Aprobaciones y retenciones

**Qué.** Una escritura que las herramientas de un rol pueden hacer pero que una persona debe autorizar —
un cargo, un mensaje a todas las familias — no se ejecuta con la llamada del modelo. Queda retenida, un
director del *mismo* tenant la aprueba o la rechaza, y si se aprueba corre con el alcance de **quien la
pidió**, nunca el de quien aprobó.

**Cómo.** `examples/common/approvals.py::Queue`. `NEEDS_APPROVAL = {"billing_charge": ("director",),
"announcement_post": ("director",)}` nombra las herramientas y los roles habilitados para decidirlas.
`hold(claim, tool, args)` registra la llamada como un ítem pendiente y devuelve `PENDING APPROVAL #<id>:
… held until a person approves it — it has not been executed`, que se le dice al modelo exactamente igual
que cualquier otro resultado, así su propia respuesta puede decir que el pedido está esperando.
`Gateway.approve(token, item_id)` verifica que quien llama sea director (`_director`), y entonces
`Queue.approve` chequea, en este orden, que el tenant de quien aprueba coincida con el de quien pidió, que
el rol de quien aprueba sea uno de los aprobadores de esa herramienta, y que quien aprueba **no** sea la
cuenta que pidió — y solo entonces llama a `execute(item["requested_by"], item["tool"], item["args"])`
**con el `Claim` de quien pidió**, bajo `DB_LOCK`. Nada que el modelo escriba llega a `approve` — es un
endpoint HTTP (`POST /admin/approvals/<id>/approve`) que llama el propio cliente de un director, protegido
por el propio token firmado de ese director (§2).

**Por qué.** Antes de que existiera este módulo, el `billing_charge` de la escuela se ejecutaba con la
llamada del modelo — la propia documentación de la demo prometía un paso de aprobación que el código no
tenía **[ran]** 2026-09-25, leído directamente en la historia de `examples/school/tools.py`. Un modelo
local barato que puede llamar a una herramienta que mueve dinero o llega a todas las familias solo es
seguro si el cargo no puede pasar *porque el modelo lo pidió*.

**Evidencia.** **[ran]** pruebas de `examples/school/tools.py`: una llamada retenida no se ejecuta hasta
aprobarse; un aprobador de otro tenant, del rol equivocado, o quien pidió el ítem, quedan denegados. **No
medido**: un director aprobando en vivo un ítem retenido a través de una sesión real de OpenClaw — cada
corrida en vivo hasta ahora es un solo rol, un solo turno. Los roles de la distribuidora corren sus
escrituras **sin** la aprobación de un director por diseño (`ORGS["distributor"]["approvals"] = False`,
`examples/school/gateway.py`) — una decisión de política para los roles de esa organización, no un hueco
en este mecanismo.

---

**Lo que espera a una persona sobrevive a un reinicio (2026-09-30).** Con un directorio de estado (`Gateway(state_dir=…)`, `--state-dir`, por defecto `examples/<org>/state`) la cola agrega cada paso a `approvals.jsonl` — `held`, `executing`, `approved` / `rejected` — y los handoffs a `handoffs.jsonl`; los dos se releen al arrancar. `executing` se escribe antes de que corra la herramienta, así que un proceso que muere a mitad de un cobro vuelve con ese pedido `interrupted`: listado para quien aprueba, nunca re-ejecutado solo, sólo rechazable — una escritura retenida se ejecuta como mucho una vez, con el alcance de quien la pidió (`tests/test_persistence_egress.py`). La memoria operativa sigue siendo efímera (§8); sólo persiste lo que espera a una persona.

## 6. Abstención y salida

**Qué.** Un pedido que las herramientas de un rol no cubren no se responde con una adivinanza. El modelo
dice `OUT OF SCOPE`, y una política que el modelo no elige decide a dónde va el pedido después: un modelo
de frontera, o la cola de una persona.

**Cómo.** Para una organización con `scope: True` (la escuela), el prompt del rol termina con la línea
fija `SCOPE`, y `Gateway.turn` chequea `if OUT in final.upper()`. A dónde va después es `role["egress"]`
— `"frontier"` llama a `self.frontier(messages)` (construido solo si se configuró `--frontier-url`, y que
se niega a arrancar sin credencial), `"person"` agrega el pedido a `self.handoffs` y le dice al usuario
que una persona lo va a atender. Para la distribuidora (`scope: False`), la misma decisión está
**entrenada en el propio corpus**, no dicha en el prompt: `examples/distributor/generate_turns.py` agrega
un cuarto tipo de fila, `out`, a los datos de entrenamiento — un pedido que ninguna herramienta de ningún
rol cubre, respondido `OUT OF SCOPE`, sin llamada, con la propia política de salida del rol aplicada por
el oráculo que escribió la fila. `frontier_client` pone precio a cada llamada real reenviada según
`--frontier-rates` y se niega a reenviar una vez gastado `--frontier-budget-usd`, avisándole al usuario en
vez de escalar el costo en silencio.

**Por qué.** "Un modelo al que se le pide elegir siempre elige" (`docs/ARCHITECTURE.md` §2) — la
abstención hay que medirla y entrenarla, no asumirla. Antes de M10, el miembro de la distribuidora
(`distributor-staff-s0`, M9) nunca había visto un pedido fuera de alcance en el entrenamiento, así que la
mitad de la distribuidora del diagrama de referencia no podía llegar a la frontera en absoluto: quedaba
respondiendo *algo* a un pedido que ninguna de sus herramientas cubre.

**Evidencia.** **[ran] M10** (`results/M10-distributor-abstain-20260928/BRIEF.md`): `train_out.jsonl` es
los 700 turnos de M9 byte por byte más 70 turnos `OUT OF SCOPE` sacados de la propia salida del rol; contra
`staff-s0` (nunca enseñado a abstenerse), `out-s0` pierde **0 de 70** turnos retenidos ya aprendidos, se
abstiene en **20 de 20** pedidos retenidos fuera de alcance (`staff-s0`: 0/20), y pasa las seis escenas de
la demo guionada **6/6** (`staff-s0`: 5/6). **[ran] LIVE-distributor**
(`results/LIVE-distributor-openclaw-20260928/BRIEF.md`): servido en vivo por OpenClaw 2026.9.4 en la
propia Mac del usuario, `out-s0` hace **6 de 6** — cinco turnos respondidos localmente y el sexto, una
nota de agradecimiento a proveedores, abstenido y reenviado a través de la salida real de frontera del
gateway a **Claude Haiku 4.5**: **10.198 + 195 tokens, US$0,0112**. `out-s0` **no es una liberación
formal** — sin archivo de liberación (§13) — es el brazo que usó esta corrida en vivo.

---

**La salida de red del proceso está cerrada a sus hosts configurados (2026-09-30).** La regla de arriba gobierna lo que decide el *modelo*; `examples/common/egress.py` gobierna a qué puede llegar el *proceso*. El gateway la instala antes de cargar nada: `socket.getaddrinfo` y `socket.socket.connect` rechazan cualquier host fuera del servidor del miembro, el host de la frontera (si está configurada) y loopback — la consulta DNS incluida, así que un nombre rechazado ni siquiera se resuelve — y cada intento se agrega al log de eventos como `{"egress": "denied", …}`. Lo primero que encontró fue el propio arranque del gateway: cargar el tokenizer consulta el hub de modelos por la red, así que el gateway ahora fija `HF_HUB_OFFLINE` y lo lee de la caché local (un arranque de humo: 0 rechazos). `--open-egress` lo apaga para desarrollo. Es una guarda de este proceso — un subproceso o una extensión en C quedan afuera; el firewall del sistema operativo es la capa del despliegue.

## 7. Podar la superficie de herramientas

**Qué.** A un miembro se le sirve la superficie de herramientas ofrecida recortada a exactamente las
etiquetas que le enseñó su propio corpus — por nombre, nunca porque el proxy aprenda cómo se llama una
herramienta — así el bloque que le llega al modelo es byte por byte con el que se entrenó, no las docenas
de herramientas que siempre manda un runtime de agentes real.

**Cómo.** `--prune` (`training/harness/openai_proxy.py`) lee de `contract.py` la superficie de etiquetas
que declara cada miembro, y conserva solo las herramientas ofrecidas que empatan con una, por nombre
exacto o por el último segmento de un nombre con espacio de nombres (`mcp__…__`, `.`, `/`, `:`). No
reofrece lo que descartó, y no adivina entre dos herramientas que terminan en la misma etiqueta — llamar a
la equivocada de dos es peor que no llamar a ninguna. `render_tools`, llamado desde `Gateway.turn`,
renderiza el esquema ya filtrado del rol (`self.tools.SCHEMA` filtrado a `role["tools"]`) después del
pedido en el turno del usuario, exactamente en el orden que enseñó el corpus.

**Por qué.** Ofrecerle a un experto las herramientas que un runtime de agentes realmente manda, sin
podar, agrega el problema en vez de sacarlo: sobre la superficie real que manda OpenClaw (54 herramientas,
7.205 tokens de Gemma), el experto sin podar **copia etiquetas del bloque que nunca se entrenó para
leer** — llama a `agents_list`, `apply_patch`, `ask_user`, `browser` — 225 de 227 de esas llamadas
rechazadas por el inbox, y dentro de un runtime de agentes real esas se habrían **ejecutado** **[ran] P59**
(`results/P59-prune-attribution-20260917/BRIEF.md`). Podado a sus tres herramientas propias, el mismo
miembro llama 1.160 veces y es rechazado 8; la precisión se mueve 0,664 → 0,729 sobre mensajes humanos
(87 : 64, empatado con p = 0,073 — un empate en el número, no en el comportamiento); el bloque mismo cae
de ~7.956 tokens a ~77.

**Evidencia.** **[ran] P59**, arriba. **[ran] E5** (`results/E5-engine-baseline-20260928/BRIEF.md`): el
bloque sin podar también cuesta latencia, y peor de lo que sugiere su tamaño, porque el corpus de un
miembro renderiza **el pedido primero y el bloque de herramientas después** — así que ningún par de
pedidos comparte el bloque como prefijo aunque el prefix caching de vLLM esté encendido. Servir al
miembro de la escuela (E4B, vLLM 0.30) el bloque real de 54 herramientas de esta manera lleva el tiempo
al primer token de **0,10 s a 1,70 s (16,8×)**, el throughput a 8 en vuelo de 132 a 108 tok/s, y la
precisión de 70/70 a **39/70** — donde en cambio el prefijo entero se repetía, el mismo bloque no costó
nada (0,09–0,11 s): **el orden, no el tamaño, derrota la caché.** Podar sigue siendo el default por
ambos motivos. **[ran] C1 supersede** el hallazgo separado de E5 de que dos adaptadores en una ráfaga de
16 mantenían 0,88 del throughput de uno solo: bajo una curva de carga sostenida
(`results/C1-concurrency-20260929/BRIEF.md`), cuatro adaptadores mezclados a 16 sesiones concurrentes
llegan a 278,6 tok/s contra 269,7 tok/s de un solo adaptador (**1,03×**, sin contención material), y 504
tok/s a 32 sesiones, p95 de tiempo al primer token 0,24 s, 0 errores de 128.

---

## 8. La memoria operacional de corto plazo

**Qué.** Una caché que un miembro de flujo de trabajo lee y escribe por clave, en vez de cargar la
conversación entera en el prompt: un alcance por sesión (este usuario, esta conversación) y uno por
organización, servido por la capa de herramientas exactamente igual que cualquier herramienta del
dominio, y acotado por el mismo claim firmado que ya mantiene las filas de un tenant fuera del alcance de
otro.

**Cómo.** `examples/common/opmemory.py::OpMemory`. Una caché de **sesión** se indexa por `(org_id,
user_id, session)`; una caché **global**, una por organización, se direcciona como `global.<key>`.
`get(claim, session, key)` y `put(claim, session, key, value)` son las únicas dos operaciones, servidas
al modelo como dos etiquetas, `<get>key</get>` y `<put>key=value</put>` (`opmemory.SCHEMA`,
`opmemory.VERBS`), enrutadas a través de `ToolSuite` exactamente igual que una herramienta de dominio, así
que `run_chain` (§3) las responde de la misma manera que responde `<order_status>…</order_status>`.
`_where(claim, session, key)` es el límite entero: una clave que no matchea `KEY`
(`^(global\.)?[a-z][a-z0-9_]{0,40}$`) se rechaza, y una clave nunca se busca a través de una organización
o un usuario, escriba lo que escriba el modelo. Un valor por encima de `MAX_VALUE` (500 caracteres) se
rechaza; cada `put` se agrega a `self.log` con quién lo escribió y cuándo. `keys(claim, session)` devuelve
los **nombres** de las claves que un turno puede usar — las de la sesión, y luego las de la organización
como `global.<key>` — **nunca los valores**; `context_line` renderiza exactamente eso más el estado del
flujo de trabajo (§9) en la única línea que un turno lee en vez de la conversación (§10). Se sirve en
memoria y **muere con el gateway** — corto plazo por diseño, nunca un sistema de registro.

**Un intercambio concreto**, siguiendo el recorrido de etiquetas de §3 un turno antes (`train-400000-t0`,
rol dispatch, misma sesión): a la pregunta *"Where is order 76?"*, el miembro llama a la herramienta de
dominio y guarda el id para después:

```
<order_status>76</order_status>= order #76: pallet of canned goods — in transit
<put>order=76</put>= stored order
According to the system: order #76: pallet of canned goods — in transit.
```

El `<get>order</get>= 76` del turno siguiente (§3) lee de vuelta exactamente ese valor.

**Por qué.** Sin ninguna memoria de la conversación, una referencia a un turno anterior no tiene
referente en absoluto (§10, MT0: 4 de 54 turnos dependientes se resuelven sin historia); cargar la
conversación entera en el prompt resuelve a la mayoría pero crece en cada turno y de todos modos pierde
una referencia que hay que *escribir*, no copiar, en texto libre (§10). Una caché direccionada por clave,
leída a través del mismo límite de claim que ya respeta cada herramienta de dominio, es el diseño que
mantiene el prompt plano sin importar cuánto dure la sesión y que igual responde a qué se refiere "eso".

**Evidencia.** **[ran] en pruebas, todavía no entrenado fuera de H1.** La propia batería de pruebas de
`examples/common/opmemory.py` ejercita el límite (una clave nunca cruza una organización o un usuario), la
validación (una clave malformada, un valor demasiado largo) y el registro, a costo cero de GPU. El hábito
de usarlo bajo un corpus real es el H1 de §10, cuyo resultado es la primera evidencia con GPU que tiene
este mecanismo.

---

## 9. Flujos de trabajo declarados

**Qué.** Las tareas de un rol avanzan por una pequeña máquina de estados — pocos estados, las llamadas
que mueven entre ellos — declarada en un archivo de texto, no aprendida: el gateway avanza el estado a
partir de las llamadas que la capa de herramientas realmente **ejecutó**; el modelo solo la lee.

**Cómo.** `examples/common/opmemory.py::Workflow.load` lee un archivo TOML por rol (stdlib `tomllib`, sin
dependencia) de `examples/<org>/workflows/*.toml`. La distribuidora declara seis, de dos a tres estados
cada uno. `dispatch.toml` completo:

```toml
# dispatch: an order is looked up, then its delivery is followed
[workflow]
name = "dispatch"
initial = "start"
keys = ["order"]
[states.start]
on = { order_status = "tracking", delivery_status = "tracking" }
[states.tracking]
on = { order_status = "tracking", delivery_status = "tracking" }
```

`Workflow.state(memory, claim, session)` lee el estado actual de la memoria operacional bajo una clave
reservada, `wf_<name>` (recayendo en `initial` si nunca se puso); `Workflow.advance(memory, claim, session,
calls)` recorre las llamadas que ejecutó la capa de herramientas, **en orden** — saltando una denegación o
un error, que nunca traen `"result"` — y mueve el estado por cada llamada cuyo nombre de herramienta sea
una transición fuera del estado actual, y después escribe el estado nuevo con `memory.put`. `Gateway.turn`
llama a `advance` una vez por turno, después de que termina `run_chain`, a partir de `suite.calls` — el
registro de lo que realmente se ejecutó, nunca de lo que el modelo dice haber hecho.

**Por qué.** No hay que confiar en que el modelo siga su propio lugar en un procedimiento — es exactamente
la falla de seguir un procedimiento que solo se lee, que el propio diseño de la biblioteca descarta por la
misma razón (§11, F1: un modelo chico no sigue un procedimiento que solo se le muestra, 0 llamadas a
herramienta en 351 de 351 **[ran]** P61). Derivar el estado de lo que las herramientas realmente hicieron,
en vez de la narración del modelo, hace que el estado del flujo de trabajo sea tan confiable como la
propia capa de herramientas.

**Evidencia.** **[ran] en pruebas, costo cero de GPU**: `Workflow.advance` se ejercita contra una
secuencia guionada de llamadas por rol; una llamada que falla o es denegada no avanza el estado; el modelo
nunca escribe `wf_<name>` directamente (`opmemory.SCHEMA` solo ofrece `get`/`put`, y `KEY` matchea nombres
`wf_`, pero es `Gateway.turn` quien escribe la clave del flujo de trabajo, no el `<put>` propio del
modelo). Bajo un corpus real, si el *miembro* lee correctamente el estado de un flujo de trabajo y llama a
la herramienta correcta a partir de él es el H1 de §10.

**Una tercera organización lleva la misma declaración más lejos.** `examples/tracker/` (construido,
sintético — todavía sin liberación) es una herramienta de equipo tipo Jira + Confluence, al lado de la
escuela y la distribuidora: dos organizaciones por semilla (`riverdev`, prefijo `RD-`; `harborworks`,
prefijo `HW-`) construidas por `world(seed)`, con un equipo de demostración fijo de `build()`. Sus flujos
de trabajo de issues se declaran de la misma manera idéntica, un TOML por tipo de issue —
`issue_workflows/story.toml`, `bug.toml` — y **se hacen cumplir en la capa de herramientas exactamente
como arriba**: una transición que el flujo de trabajo no permite se rechaza sea lo que sea que el modelo
pidió, nunca simplemente narrada. Sus roles (`developer`, `lead`, `qa`) llevan cada uno su propio TOML de
flujo de trabajo para la memoria operacional (§8), y su herramienta `page_read` toma una `page` o un
`page#anchor` — el enunciado atómico direccionado directamente, la misma unidad con la que la biblioteca
del §11 se indexa.

---

**Una clave que nombra el usuario se conserva aunque la llamada del propio turno salga mal (2026-09-30).** Un flujo puede declarar `[capture]` — una clave y un patrón sobre el pedido del usuario (el developer y QA del tracker: `issue = '\b[A-Z]{2,5}-\d+\b'`). Después del turno, si el patrón aparece en el pedido y el miembro no hizo `put` de esa clave él mismo, el gateway guarda la última coincidencia, y el evento lo registra (`captured`). Se declara, nunca se infiere, y nunca pisa el `put` del miembro. Existe porque una primera llamada equivocada dejó la memoria vacía y cada turno dependiente posterior no encontró nada — las cuatro fallas de `s1-noblock` en H3 **[ran]**; la misma sesión, guionada, pasa de 0/3 a 3/3 (`tests/test_tracker.py`).

## 10. El arnés de flujo de trabajo

**Qué.** Lo que aprende un miembro de flujo de trabajo, en sus pesos, para un dominio: sus flujos de
trabajo como máquinas de estados, sus herramientas y cómo llamarlas, y los **nombres** de las claves bajo
las que están los valores vivos de una sesión — de modo que un turno lea una línea en vez de la
conversación, y busque o guarde un valor solo en el paso que lo necesita.

**Cómo.** La línea de contexto que lee un turno, `examples/common/opmemory.py::context_line`:

    state: dispatch/tracking · keys: order

— el nombre y estado actual del flujo de trabajo (§9), y luego cada nombre de clave que hoy tienen la
caché de la sesión y la caché global de la organización (§8), **nunca un valor**. `Gateway(memory=OpMemory(),
workflows={role: Workflow…})` es lo que activa esto; `Gateway.turn` antepone la línea de contexto al
pedido antes de renderizar el bloque de herramientas, ofrece `<get>`/`<put>` junto a las herramientas
propias del rol, y avanza el flujo de trabajo después de que corre la cadena (§9). `tool_block=False` es
la ablación contra la que también se mide este arnés: sacar del todo la superficie de herramientas
renderizada y confiar en que el miembro conoce sus herramientas solo por su corpus (el brazo
`harness-noblock` de `Gateway` más abajo).

**Por qué.** `Gateway(history=True)` — renderizar cada pedido y respuesta anteriores — es el arreglo
ingenuo al mismo problema, y se midió primero: sin ninguna conversación, solo se resuelven **4 de 54**
turnos dependientes sobre 60 sesiones retenidas de la distribuidora; con toda la historia, **43 de 54
(79,6%)**, pero de todos modos pierde exactamente la referencia que hay que *escribir* en texto libre en
vez de copiar directo a un argumento — un reclamo sobre "that order" presentado sin el número de pedido, 8
de 10 veces en atención al cliente — y su prompt sigue creciendo con la sesión (+24% para el turno 2)
**[ran] MT0** (`results/MT0-multiturn-baseline-20260929/BRIEF.md`). El arnés está diseñado para conservar
las respuestas correctas de `history` manteniendo el prompt plano sin importar cuánto dure la sesión, y
para cerrar el hueco específico que `history` deja abierto — un valor buscado por clave en vez de
reconstruido a partir de una transcripción.

**Evidencia — [ran] H1**, pre-registrado, `results/H1-workflow-harness-20260929/BRIEF.md`. Tres brazos
sobre las mismas 60 sesiones de MT0: `history` (`out-s0`, la base de arriba, re-corrida para un par
limpio), `harness` (`wf-s0`, entrenado sobre el corpus de M10 más 627 filas de arnés — 277 con `get`, 250
con `put` — escritas por un oráculo a través del gateway real), y `harness-noblock` (`wf-s0` de nuevo, con
el bloque de herramientas sacado).

| | `history` | `harness` | `harness-noblock` |
|---|--:|--:|--:|
| primeros turnos | 60/60 | 60/60 | **0/60** |
| turnos dependientes | 43/54 | **53/54** | 0/54 |
| atención al cliente ("that order") | 2/10 | **10/10** | 0/10 |
| turnos dependientes correctos que buscaron por clave | — | **53/53** | — |
| tokens de prompt, turno 1 / 2 / 3 | 345 / 428 / 394 | 745 / 726 / 710 | 251 / 119 / 82 |

**El veredicto tal como se pre-registró es VOID.** La propia primera condición del brief — "primeros
turnos ≥ 90% en cada brazo, o VOID" — la aplica el código de puntaje a los tres brazos, y el 0/60 de
`harness-noblock` anula la lectura de toda la corrida. **Esto fue un error del instrumento, no del
miembro**: `harness-noblock` estaba pensado para tener su propia condición de aprobación, no para anular
la lectura de los otros dos brazos. El error queda registrado acá y el código de puntaje **no se cambió
después del resultado** (§17). Se lee **por brazo** en cambio, con el mismo código aplicado solo a
`history` y `harness`: **`harness` PASÓ** — 1 turno dependiente perdido contra `history`, 11 ganados,
cada turno dependiente correcto buscó su valor por clave (53/53), y la barra de planitud se sostiene
($\bar p_3 = 710 \le 1{,}1 \times 745$). **`harness-noblock` está FALSEADO** — sin el bloque de
herramientas renderizado el miembro no llama a ninguna herramienta y declara datos que nunca leyó, porque
su corpus siempre lo entrenó con el bloque presente; esa mitad de la idea necesitaría su propio corpus, no
el de esta corrida. **La decisión del usuario (2026-09-29): vale la lectura por brazo** — `harness` PASÓ,
`harness-noblock` quedó FALSEADO — y el VOID tal como está escrito queda como el registro de ese error
del instrumento, no como el veredicto. Diseño y las decisiones detrás de él:
[`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md).

**Evidencia — [ran] H2**, `results/H2-tracker-harness-20260929/BRIEF.md`: el mismo arnés sobre el tracker
de equipo (§9), 60 sesiones largas retenidas, 160 turnos dependientes, 60 primeros, 60 independientes.
`harness` (`tr-s0` + memoria operacional + flujo de trabajo) puntúa primeros turnos **60/60**,
dependientes **146/160 (91,3%)** contra un umbral de 90%, independientes 50/60, con el prompt por turno
plano a lo largo de cinco turnos — $\bar p_1,\dots,\bar p_5 = 1613, 1223, 1011, 1149, 1274$, así que se
sostiene $\bar p_5 \le 1.1\ \bar p_1$. `base-history` (Gemma 4 E4B sin entrenar, la conversación en el
prompt) acierta `issue_get` (40/40) y casi nada más — dependientes 4/160 — y sus propios primeros turnos,
44/60, caen bajo el umbral del 90%; anularlo con la misma regla por brazo que arregló a H1 vuelve ilegible
la afirmación pre-registrada "`harness` le gana a `base-history`", así que **la corrida se lee FALSEADA
tal como está escrita, no ANULADA**, y queda en el registro con ese error de instrumento y el del
chequeo de anchor (abajo). Descriptivamente, pareado sobre los mismos 160 turnos dependientes:
**142 : 0** a favor de `harness`, prueba de signo exacta $p\lt 10^{-40}$ — enunciada, no sustituida por el
veredicto pre-registrado, porque el brazo contra el que se compara está anulado. **La decisión del usuario
(2026-09-29): lectura 1** — las condiciones legibles son el veredicto de H2, `harness` **PASÓ**.
`harness-noblock` (bloque de herramientas sacado al servir) puntúa dependientes 80/160 — leído al
principio como "aprendido **en parte**" (el carril de developer y el carril entero de QA, pero no el
`issue_create`/`issue_assign`/`issue_get` del carril de lead, 0/20), pero esa lectura era un error del
corpus, no un aprendizaje parcial: `--harness-corpus` armó su tercio sin bloque con `j % 3 == 2`, el
mismo módulo con el que rotan los roles, así que las 400 filas de entrenamiento sin bloque eran todas de
QA — el miembro aprendió lo-sin-bloque exactamente en el rol que se le mostró (QA 80/80; lead/developer
0/20, la única excepción de lead `sprint_board`, una llamada sin argumento). En `harness`, las 14 fallas dependientes son todas un mismo turno, el comentario final de QA (6/20): el miembro relee el issue o intenta una transición rechazada en vez de comentar — una falla real, sobre un solo fraseo de la evaluación ("Note on it: …" 1/15 contra "Put a comment on it: …" 5/5); aparte, 10 de los 60 turnos independientes (50/60) son el chequeo del ancla — "¿dónde tienen que pasar los tests?" lee la página entera `definition-of-done` en vez de `#tests`, y el enunciado está en lo que leyó (mide fraseo, registrado, no aflojado). **Un segundo error de instrumento
de la familia de H1**: la regla de VOID por
brazo, escrita para que un brazo roto no borrara el resultado real de otro, esta vez anuló a una línea de
base *sin entrenar* cuyo bajo puntaje en primeros turnos ES su margen, no un defecto — ver §17. El
intento 1 de esta corrida quedó anulado por un error de transporte, no de puntuación (el límite de
secuencias de parada del §15); el arreglo es el `MAX_STOPS` de
`training/harness/accept_rank.py`. **H3 tiene un resultado [ran]:** `tr-s1`, entrenado sobre un segundo
corpus que arregla las dos correcciones de arriba (fraseo ampliado por turno en cada rol, un tercio sin
bloque de cada rol), contra `tr-s0` sobre una suite fresca retenida. El margen se sostiene primero —
`s0-harness` 147/160 (91,9%), bajo el techo del 95% — y después **H3a PASÓ**: `s1-harness` 158/160
(98,8%) contra `s0-harness`, pareado 11:0, prueba de signo exacta $p = 0,00098$, 0 perdidos, plano
($\bar p_5 = 1275 \le 1,1\cdot 1465$). **H3b PASÓ**: sin el bloque de herramientas, `s1-noblock` 156/160
(97,5%), cada rol por encima de la barra (developer 76/80, lead 40/40, QA 40/40) — el error de aliasing
de arriba queda arreglado — a más o menos un tercio de los tokens de prompt por turno. Dos fallas se leen
donde ocurren, nuevas acá: las 2 fallas de `tr-s1` son un solo caso, el texto de la propia nota leído
como una orden (`issue_transition → qa`, rechazada por la capa de herramientas); las 4 fallas de
`s1-noblock` son una sola sesión cuyo primer turno llama a la herramienta equivocada y los cuatro turnos
dependientes siguientes encuentran una memoria vacía — un error del primer turno en cascada por la sesión
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
Resultado completo y
las dos lecturas: [`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md) §9.

---

## 11. La biblioteca en Markdown y los LoRAs de trayectoria

**Qué.** El conocimiento estable de un subdominio — enciclopédico y operacional — vive en markdown, en
git, nunca en los pesos; lo que aprende un LoRA es el **hábito de navegarlo por clave**: qué buscar, qué
enlace seguir, cuándo parar y citar. Los pesos sostienen la ruta; las notas sostienen el contenido.

**Cómo.** El diseño del usuario, desde el 2026-09-24: una página trata de una sola cosa y es una lista de
**enunciados atómicos**, cada uno una oración verificable bajo un ancla, y **el enunciado — no la
página — es la unidad de memoria**. Los enlaces viven dentro del enunciado que los nombra. Una página real
del primer banco de pruebas (`training/wiki/data`, `distributor-wiki/wiki/products/brisk-40`):

```
---
id: distributor-wiki/wiki/products/brisk-40
shelf: wiki
kind: page
title: Brisk-40 pallet wrap
when: You need a fact about the Brisk-40 pallet wrap — who supplies it, where it is stocked, its pack.
what: A stretch film for pallets; one of the products the distributor carries.
---
§supplier Brisk-40 is supplied by [[distributor-wiki/wiki/suppliers/norvale]].
§warehouse Brisk-40 is stocked at [[distributor-wiki/wiki/warehouses/east-quay]].
§pack A pack of Brisk-40 holds 18 rolls.
```

Tres verbos, y nada más: `<search>situación o duda</search>` devuelve solo títulos y líneas `when`, nunca
cuerpos; `<open>id</open>` sobre una página devuelve sus **secciones** (las anclas, como una tabla de
contenido); `<open>id§ancla</open>` devuelve **un enunciado**, con sus enlaces escritos para poder
abrirse después — `<open>brisk-40§supplier</open>` → la página del proveedor. El propio recorrido del
usuario: *"¿cuáles son las obras del autor de la Mona Lisa?"* → la búsqueda encuentra `La_Gioconda` → su
enunciado `§author` enlaza a `Leonardo_da_Vinci` → el modelo abre `§works` ahí. La línea final de la
respuesta termina con la cita del enunciado en el que se apoya, `[id§ancla]`, chequeada
**mecánicamente**: verificado significa que el valor ocurre en el enunciado citado **y** que el recorrido
lo abrió; un valor correcto sin cita, o con una que no lo contiene, es `unverified`, se reporta, nunca se
acredita.

**Por qué.** Tres mediciones anteriores descartan los diseños más baratos. Un modelo chico no sigue un
procedimiento que solo se le muestra — 0 llamadas a herramienta en 351 de 351 mensajes con un
procedimiento de 914 tokens pegado en el prompt **[ran]** P61 — así que navegar tiene que **entrenarse**.
El conocimiento fijo metido en un corpus de entrenamiento se memoriza y después no cuesta nada — un
control sin herramienta de búsqueda anotó 27/30 sobre catorce valores **[ran]** P15/P21 — así que el banco
de pruebas tiene que generarse fresco por mundo, imposible de memorizar por construcción; hechos famosos
(quién pintó la Mona Lisa) ya están en los pesos de un 4B, por eso el primer banco de pruebas es una wiki
de distribuidora inventada, no la Wikipedia real. Y un especialista se equivoca con confianza un paso
afuera de su región — 30/30 adentro, 1/20 en una familia hermana que nunca entrenó **[ran]** P14 — que es
el reclamo abierto que este diseño todavía no probó: que las notas de una familia hermana extienden la
región sin reentrenar.

**Evidencia.** **[ran] W9** (`results/M7-W9-atomic-statements-20260924/BRIEF.md`): la base sin entrenar
nunca escribe un verbo después de un resultado de búsqueda, 0 de 40; un LoRA de trayectoria entrenado
sobre 32 mundos distintos recorre el mundo retenido **35 de 40** en las dos semillas, cada cita
verificada, preguntas de 3 saltos 16/16 — un empate con la base a la que se le dan los enunciados propios
del oráculo. Sobre Gemma 4 E4B el mismo corpus anota 38/40 **[ran]** B1. **[ran] W7**
(`results/W7-edit-after-training-20260927/BRIEF.md`): un enunciado parchado en la propia biblioteca de
`distributor-wiki@v2`, **sin reentrenar** — 37 de 38 respuestas de control sobre los propios mundos y
preguntas de ese miembro siguen el valor nuevo, citado a la línea parchada, 0 obsoletas. A libro cerrado,
sin la página delante, los pesos todavía responden con el valor viejo 1 de 40 veces — no cero: el miembro
aprendió la *ruta* lo bastante bien como para reproducir ocasionalmente lo que normalmente solo lee, lo
que acota en vez de eliminar el riesgo que la separación entre contenido y pesos busca cerrar.

**Documentos reales.** `memory/ingest.py` convierte una fuente real (regulaciones federales de EE. UU.,
eCFR) en la biblioteca, textual — sin wiki inventada. Sobre una biblioteca ingerida así apareció primero el
punto débil del diseño anterior: la consulta de `<search>` que entrenó el miembro está memorizada de su
propio mundo de entrenamiento, así que nunca abre ninguna página, 0 de 25 **[ran]** REAL0. El runtime
responde a eso sin reentrenar: el texto completo de la pregunta es la **primera** entrada, probada en
**todos los estantes** (`FullText`, BM25 sobre los enunciados), con un **fallback** al texto literal del
runtime cuando una búsqueda no devuelve nada, y una página abierta con sus enunciados adjuntos como
`page_text` en vez de sólo su lista de secciones — juntos llevan un recorrido a la página que sostiene la
respuesta 24/25, contra un techo de lectura de 22 **[ran]** REAL1–REAL2.

Entrenar sobre páginas reales necesitó un arreglo más. Un corpus de trayectorias sobre documentos reales de
una familia que la evaluación nunca ve, recorrido por este mismo runtime, sacó 1 de 23 la primera vez — la
pérdida caía sobre todo el recorrido, y un recorrido sobre páginas reales leídas enteras es ~97 % tokens de
página, así que el LoRA aprendió a escribir regulaciones en vez de contestar. La **pérdida con máscara de
tramo** — entrenar sólo los propios tags del modelo y su respuesta citada, nunca la pregunta ni un resultado
del runtime — lo arregla: 18/23 contra el 9/23 del base sin entrenar sobre un set fresco de varios saltos,
las dos semillas **[ran]** REAL3; la misma receta con 27 recorridos sin respuesta agregados enseña entonces
la negativa, 15/16, a un costo en el titular cuya lectura el usuario todavía no saldó **[ran]** REAL4.

---

## 12. Los corpus y sus compuertas

**Qué.** Cada caso de entrenamiento y evaluación se dibuja sobre su propio **mundo** sintético — sus
propios clientes, pedidos, stock, notas, texto plantado — generado desde una semilla, así nada que
necesite una respuesta puede recordarse por haber visto antes el valor exacto. Extender un corpus con una
capacidad nueva se hace **byte por byte**: las filas viejas intactas, filas nuevas agregadas, así una
regresión en lo que ya funcionaba no puede esconderse dentro de una reescritura. Una **compuerta de
datos** — una batería de chequeos mecánicos, no la opinión de un modelo — tiene que pasar a costo cero de
GPU antes de que se permita arrancar cualquier corrida de entrenamiento.

**Cómo.** `examples/distributor/generate_turns.py::_world(seed)` dibuja fresco por caso ambos centros,
clientes, pedidos, muelles, stock y una instrucción plantada; `gate(train, evals)` chequea, según su
propio docstring, "ningún pedido de la demo en ninguno de los dos conjuntos, ningún pedido de evaluación
en el corpus, ningún mundo compartido, cada recorrido es el que se quiso, cada fila del oráculo pasa los
propios chequeos de la demo" — cinco cláusulas (`G1`…`G5`), cada una un conteo que tiene que dar
**exactamente cero**, `passed = all(v == 0 for k, v in g.items() if k.startswith("G"))`. Las extensiones
son capas literales, byte por byte, una sobre otra: `train_out.jsonl` **es** `train.jsonl` más 70 turnos
`OUT OF SCOPE` (§6); `train_harness.jsonl` **es** `train_out.jsonl` más 627 filas de arnés (§10). La
propia compuerta de `generate_turns.py --out-turns` (`gate_out.json`, en disco en este repositorio) dice:

```json
{
 "O1_demo_request_in_sets": 0,
 "O2_eval_wording_in_corpus": 0,
 "O3_shared_world": 0,
 "O4_does_not_abstain": 0,
 "train_out": 70,
 "eval_out": 20,
 "egress": {"frontier": 48, "person": 22},
 "passed": true
}
```

El corpus de la wiki (`training/wiki/corpus.py::gate`) y el generador de recorridos de enfermería
(`training/nursing/generate_walks.py`) aplican la misma disciplina sobre la propia restricción de la
biblioteca: **0** valores de slot aparecen jamás dentro del texto de un enunciado, **0** recorridos
evaluados se filtran al corpus de entrenamiento, **0** filas que el runtime no reproduzca byte por byte en
modo `strict` — cada cláusula respaldada por una prueba que puede hacerla fallar (`tests/test_wiki.py`,
`M7-W4`).

**Por qué.** El F2 de las propias reglas de diseño de la memoria (`docs/KNOWLEDGE-TRAJECTORIES.md` §2):
"el conocimiento fijo en un corpus de entrenamiento se memoriza, y después no cuesta nada" — un control
sin herramienta de búsqueda anotó 27/30 sobre catorce valores porque 600 ejemplos memorizan 14 números
**[ran]** P15/P21. Un corpus que dibuja valores frescos por mundo es la única manera de que un número de
evaluación sea sobre *navegar*, no sobre *recordar*. Y una compuerta que corre antes del entrenamiento, a
costo cero de GPU, es lo que hace que "el corpus no filtra su propia evaluación" sea un hecho chequeado
por código, no una afirmación hecha en un brief.

**Evidencia.** **[ran]** cada corpus citado en este documento — los 700 turnos de M9, los +70 de M10, las
+627 de H1, los mundos generados de W9, los 600 recorridos de enfermería de W4 — trae un `gate.json` (o
`gate_out.json`, `gate_harness.json`) en disco, en la misma corrida que entrenó sobre él, chequeado antes
de que arrancara el entrenamiento.

---

## 13. Los miembros y la compuerta de liberación

**Qué.** Un miembro no se vuelve un experto liberado por anotar bien una vez. Tiene que sostener su
puntaje registrado al re-servirse, empatar con un reentrenamiento fresco desde el mismo corpus, ganarle a
su propia base pelada, y no perder contra la frontera — cuatro chequeos, cada uno un test estadístico
exacto sobre los *mismos casos*, antes de escribir un manifiesto contra el que se pueda chequear cualquier
corrida posterior.

**Cómo.** La compuerta de identidad, `G1` (`training/harness/verify_substrate.py::identity`, también
`C18` en `docs/SUBSTRATE-GATE.md`), manda un mismo prompt a la base y al miembro y exige que el texto
servido **difiera** en al menos 2 de 3 sondas — porque vLLM puede cargar un LoRA, loguear que lo cargó, y
de todos modos servir el propio texto de la base byte-idéntico **[ran]** P33, y la línea del log no es el
veredicto, el texto servido lo es. Cada comparación después de `G1` es el mismo **test de signo exacto de
dos colas sobre pares discordantes** (`training/harness/bar.py::sign_test`, `docs/FOUNDATIONS.md` §9.2):

```math
p = \min\Big(1,\ 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u,\, n_d-u)\big]\Big)
```

sobre los $n_d$ casos donde dos brazos discrepan, con $u$ de ellos a favor de uno — los empates no cargan
información y se excluyen, que es lo que lo vuelve el test *apareado* y no una comparación de dos puntajes
crudos. `training/harness/release_gate.py::pair` lo corre dos veces para la **reproducibilidad**:
re-servido contra la corrida registrada, y reentrenado-desde-el-mismo-corpus contra re-servido — los dos
tienen que empatar. `training/harness/region_release.py` lo corre tres veces para una **región**, sobre
los mismos 90 casos: el miembro nuevo contra su propia corrida registrada (no puede perder), contra la
base pelada (tiene que ganar, o el corpus no compró nada), y contra la frontera (no puede perder). El
manifiesto que sale, `releases/<name>@v<n>.json`, registra la base, la receta, el sha256 del corpus, el
sha256 del adaptador, el hash del prompt servido, y cada puntaje apareado — así que re-servir o
reentrenar desde él se puede chequear contra ese mismo archivo después.

**Por qué.** Dos mediciones enseñaron las dos mitades de esta regla. El umbral de `G1` es 2 de 3, no
1 de 1, porque a temperatura 0 un prompt corto puede coincidir entre la base y el miembro sin que el
delta esté ausente — un `NOT APPLIED` falso cuesta una sesión entera, y la propia compuerta de P55 vio
6 de 8 sondas distintas sobre un adaptador real, bien lejos de la coincidencia. Y el par de
reproducibilidad existe porque una cadena de entrenamiento que en silencio mejora entre dos corridas
idénticas es exactamente tan poco reproducible como una que empeora — una mejora se reporta, no se
festeja sin más.

**Evidencia.** **[ran] P57** (`results/P57-release-20260917/BRIEF.md`): `email-full@v1` re-servido y
reentrenado empatan los dos con la corrida registrada, 471/475, 471/475, 472/475 (0 y 1 discordantes).
**[ran] P64**: `desk-commitment@v1`, un segundo miembro sobre el mismo inbox, empata su propia corrida
registrada con 0 discordantes y le gana a la base 202 : 0. Miembros liberados en registro:
`email-full@v3`, `desk-commitment@v3`, `distributor-wiki@v2` (`training/harness/family.py`). **No todos
los miembros medidos en este documento son una liberación formal** — `distributor-staff-s0`, `out-s0` y
`wf-s0` **no tienen archivo de liberación**; las corridas en vivo y H1 se leen como brazos, no como pasos
por esta compuerta.

---

## 14. El router

**Qué.** En qué distribución de qué miembro cae un pedido, o en ninguna — decidido antes de que el
pedido llegue a un modelo, por una tabla de regiones medidas, no por la opinión propia del modelo sobre
lo que puede hacer.

**Cómo.** El default de `route.py`, y el que realmente se sirve, es un **diccionario de palabras
clave**: cada miembro declara las palabras que usan los pedidos de su propio corpus, y un pedido se enruta
a un miembro cuyas palabras contiene. `--auto` lo lee; el propio listado de `/v1/models` decide qué queda
local, "mejor que una lista mantenida a mano, que se atrasa en el momento en que se agrega un adaptador"
(`docs/SERVING.md`). En `examples/school/gateway.py`, el ruteo es todavía más simple: **el rol del token
es la ruta** — `Gateway.turn` busca `self.roles.ROLES[claim.role]` directamente, sin ningún paso de
selección de miembro, porque el runtime ya sabe qué agente, y por lo tanto qué rol, mandó el mensaje.

**Por qué.** Un router aprendido se probó y se midió contra el diccionario, no se asumió mejor. Un
modelo de n-gramas del propio marco de cada corpus es **más seguro sobre texto ajeno** — 0 de 128
servidos localmente contra los 59 del diccionario — pero **pierde cada pedido legítimo de un remitente
que su generador nunca dibujó**, 120 de 120, porque cada dirección de entrenamiento generada terminaba en
`.com` **[ran] M2** (`results/M2-corpus-router-20260919/BRIEF.md`). El propio costo conocido del
diccionario está en registro en vez de escondido: un pedido que simplemente *contiene* la pregunta de un
miembro — "…is this important to merge before Friday?" — se sirve con ese miembro, sea o no lo correcto.
Rutear por rol, en la escuela y en la distribuidora, cierra de plano la mitad de este problema: **[ran]
F2** (`results/F2-role-as-route-20260920/BRIEF.md`), con el rol confirmado por las propias claves del
miembro, nunca hay más errores de ruteo que los que dan las claves solas y nada se sirve bajo un rol
equivocado — una repetición de 240 casos empata en 0,775. Lo que el ruteo por rol **no** responde es la
mitad que queda abierta: *si este pedido está adentro de la región en absoluto*, para el único miembro
que atiende el tráfico de un rol — el problema del hito 2, sin resolver, una clase más chico.

**Evidencia.** **[ran] M2**, **[ran] F2**, arriba. **[ran]** `results/M2b-embed-router-20260919/` y
`results/M2c-needle-router-20260921/`: el brazo de embeddings se midió después; ningún brazo aprendido
todavía le ganó al diccionario que debía reemplazar. El radar del hito 7 (§11) está construido para
compartir su espacio de embeddings con este router, y todavía no lo sirve.

---

## 15. Runtimes: server y edge

![Dos mitades. Izquierda, server: una placa alquilada en una nube con un lomo grueso y cuatro lomos finos de adaptadores, muchos usuarios, cuatro adaptadores en un lote sin contención. Derecha, edge: una notebook con un usuario y un lomo fino que se cambia en tres milisegundos, llama.cpp en 8 bits, una línea punteada a la frontera. En el medio, un banco chico: MLX, el banco de investigación.](../img/runtimes.png)

*Dos runtimes: vLLM en una placa alquilada para medir, entrenar y servir a muchos; llama.cpp en tu propia máquina para servir a uno.*

**Qué.** Dos perfiles de servido, nombrados explícitamente por la decisión del usuario (2026-09-28), para
dos trabajos distintos: **`server`** es donde pasa cada medición y cada corrida de entrenamiento de este
repositorio; **`edge`** es donde se sirve un único miembro ya liberado a un runtime de agentes en vivo en
la misma máquina que lo corre, sin placa alquilada ni túnel.

**Cómo.** `server` es **vLLM** sobre una placa de Colab alquilada: una base residente, el LoRA de cada
miembro registrado como su propio nombre de modelo (`--lora-modules name=path`), un campo `model` por
pedido que elige qué adaptador responde, cargado en caliente en **0,23–0,28 s** sin reiniciar
(`/v1/load_lora_adapter`, **[ran]** F0). `edge` es **llama.cpp** en la propia máquina del usuario: el E4B
servido como GGUF **Q8_0** — nunca Q4_0, que invierte un id de orden dentro de la propia caché de prompt
de llama.cpp y puede servir un pedido contra el turno cacheado equivocado **[ran]** LIVE-distributor —
más el LoRA de un miembro convertido una sola vez (`llama.cpp/convert_lora_to_gguf.py`) y cambiado en
caliente sobre un servidor corriendo con `POST /lora-adapters`, restaurando la base exactamente, en
**3 ms** **[ran]** MAC2 — tres órdenes de magnitud por debajo del propio swap de vLLM, en una máquina sin
memoria de sobra para un segundo modelo residente. **MLX**, el motor anterior de la Mac, hoy es un **banco
de investigación**, no un motor de servido: su propio cambio en caliente es mover un puntero dentro del
propio acceso de Python al grafo, **2,9 µs** **[ran]** MAC — más rápido que los 3 ms de `edge` por otros
tres órdenes de magnitud, pero necesita el acceso a nivel Python a los internos del modelo que un motor de
servido no le da a un cliente. ~~MLX sigue siendo el motor de `edge`~~ — ese fue el veredicto de MAC2 sobre
la *decodificación especulativa* específicamente (§16), y no se extiende a servir un pedido en vivo.

**Por qué.** El vLLM de `server` es donde se midieron el par (§16), la compuerta de liberación (§13) y
cada número de precisión de este documento — nada de los números de `edge` se asume transferido sin su
propia corrida. `edge` existe porque la segunda mitad del despliegue de referencia — la distribuidora —
corre en vivo en la propia Mac de 16 GB del usuario, **sin placa alquilada ni túnel**: la propia
contabilidad de `docs/SERVING.md` es explícita en que lo que sirve `server` viaja a Colab y lo que no
viaja a una API de frontera — `edge` es el único arreglo donde nada salvo la base y el adaptador sale
jamás de la máquina.

**vLLM 0.30 también rechaza demasiadas secuencias de parada, no solo deja caer una.** El propio endpoint
OpenAI de `server` devuelve HTTP 400 ante cualquier pedido que lleve más de cuatro strings de `stop` —
cada turno de una superficie de herramientas que cierra más de cuatro etiquetas distintas falla en
tránsito, no en el puntaje (**[ran]** intento 1 de H2, `h2_attempt1_void_http400.json`). El arreglo, el
`MAX_STOPS = 4` de `training/harness/accept_rank.py`: pasadas esas tantas etiquetas de cierre, el pedido
envía una sola parada genérica, `"</"`, y `close_open_tag` reconstruye la etiqueta específica a partir de
dentro de qué texto quedó una vez que el servidor para ahí — **la misma función que necesitó `edge` con
llama.cpp arriba**, por la razón opuesta (ahí el servidor deja caer el string de parada que honró; acá se
niega a aceptar más de cuatro), y el mismo arreglo en los dos casos.

**Evidencia.** **[ran] C1** (`results/C1-concurrency-20260929/BRIEF.md`, `server`): cuatro miembros
mezclados en un L4 llegan a **278,6 tok/s** contra **269,7 tok/s** de un solo adaptador a 16 sesiones
concurrentes (1,03×, sin contención material), **504,3 tok/s** a 32 sesiones, p95 de tiempo al primer
token **0,24 s**, 0 errores de 128 pedidos; el throughput escala casi linealmente de 1 a 32 sesiones y el
techo está por encima de 32, sin alcanzarse. **[ran] MAC2** (`results/MAC2-llamacpp-20260927/BRIEF.md`,
`edge`): el GGUF del E4B carga, el GGUF del LoRA del 12B actúa (6/6), el cambio en caliente restaura la
base exactamente y la salida de decodificación especulativa es idéntica 20/20 — pero el par E4B+12B juntos
se queda sin memoria Metal en 16 GB. **[ran] LIVE-distributor** (`server` con túnel primero, después
`edge` en vivo): 6/6 a través del OpenClaw real sobre el arreglo que documenta paso a paso
`docs/SERVING.md` §"The distributor, live and local".

---

## 16. Decodificación especulativa

**Qué.** Un modelo chico (el borrador) propone varios tokens de una vez; un modelo grande (el objetivo)
los chequea todos en una sola pasada y se queda con el prefijo que acepta — tokens extra gratis cuando los
dos coinciden, sin pérdida de la propia salida del modelo grande cuando no. Acá el borrador es el propio
cabezal MTP incorporado de Gemma 4, y la pregunta que este repositorio hace es qué le pasa a ese mecanismo
una vez que se enciende al lado un LoRA de **experto**.

**Cómo.** La aceptación se mide, no se simula: a temperatura 0 el objetivo es one-hot, así que "aceptar"
se reduce a "el token del borrador es el propio argmax del objetivo" — `training/harness/accept_rank.py`
le pide al objetivo `prompt_logprobs` sobre el borrador que se le entrega, un solo prefill, nada muestreado.
**Lo que cambia en caliente**: el LoRA del experto sobre el modelo grande, por pedido, exactamente como
describe §15 — la propia carga de vLLM, el movimiento de puntero de MLX, el `POST /lora-adapters` de
llama.cpp. **Lo que no**: el borrador mismo. En vLLM el borrador queda fijo al arrancar el servidor
(`--speculative-config`) y es **uno solo para todo el servidor** — no hay borrador por pedido ni soporte
de LoRA para un borrador en absoluto; la propuesta existe como RFC, no como funcionalidad **[read]**.

**Por qué — las cuatro lecturas, una al lado de la otra.** **F0 [ran]:** con el LoRA de un experto de
dominio encendido, la aceptación en posición 0 de las propias adivinanzas del borrador cae de 0,98 a
0,58, y la aceleración de 2,73× a 1,74× — el borrador nunca se entrenó sobre las respuestas de este
experto, así que adivina peor en su propio terreno. **C0 [ran]**
(`results/C0-aligned-draft-20260927/BRIEF.md`, A100 bf16): el propio borrador MTP de Gemma, con el LoRA
del experto encendido, **se recupera** a **1,92× en el dominio** (α 0,34) y **2,40× general**, contra
**2,80×/2,60× sobre la base** — mejor que F0, todavía por debajo de la velocidad propia de la base. La
alternativa alineada — un borrador de tamaño E4B, fusionado y hecho a medida para este experto (estrategia
C) — **no corrió esta vuelta**: se queda sin memoria al lado del 12B en un L4, el FP8 en línea de vLLM
falla en esa capacidad de cómputo de GPU, bitsandbytes no es una cuantización de borrador aceptada, y un
H100 fue rechazado por cupo — aparcado, no falseado. **C0-upper [ran]**
(`results/C0-upper-e4b-20260927/BRIEF.md`): ¿confinar el LoRA del experto a la mitad superior del decoder
ayuda al borrador, ya que MTP lee sobre todo cerca de arriba de la pila? No — α en el dominio se mueve de
base 0,82 → LoRA de profundidad completa 0,44 → LoRA de mitad superior 0,43 ($\rho = -0{,}02$, leído como
nulo): el adaptador de mitad superior todavía toca exactamente las capas de las que lee MTP, así que casi
nada cambia desde el punto de vista del borrador. **E6 [ran]** (`results/E6-upper-layers-20260927/BRIEF.md`)
lee la *misma* restricción de capas con otro propósito y ahí sí encuentra un resultado real: entrenar el
LoRA del miembro de la escuela solo en las capas 21–41 de 42 no cuesta nada contra el miembro de
profundidad completa (70/70 retenido, 15/15 demo, 0 perdido), y la caché KV de las 21 capas intactas de
abajo vuelve **bit-idéntica a la de la propia base** — la precondición que necesitaría un servidor para
calcular una KV inferior compartida una sola vez y dejar que varios expertos reusen los pedidos, todavía
no construida, con la salvedad de que el E4B ya cachea 24 de sus 42 capas por su propia arquitectura, un
límite con el que no coincide el corte de este LoRA. **MAC2 [ran]** (`results/MAC2-llamacpp-20260927/BRIEF.md`,
el motor `edge` de la Mac): el cambio en caliente del LoRA y la salida de decodificación especulativa
funcionan los dos (20/20 idéntica), pero el MTP de Gemma **frena** al 12B en `edge` en vez de ayudarlo —
**0,52×** con el LoRA del experto encendido sobre su propio dominio, 0,66–0,87× en el resto — y el par
E4B+12B no entra junto en 16 GB en absoluto, por lo que `edge` (§15) sirve un miembro, no el par.

**Evidencia.** Las cinco corridas de arriba son todas **[ran]**; ninguna está simulada. El resumen
honesto, dicho una sola vez en vez de por corrida: un LoRA restringido por capas es una palanca genuina
para **servir muchos expertos barato** (E6 de §16) y un callejón sin salida genuino para **alinear un
borrador a un experto** (C0-upper) — la misma perilla, dos mecanismos distintos, y solo uno de los dos se
movió.

---

## 17. La disciplina de medición

**Qué.** Cada corrida de este documento, y cada número citado de ella, se decidió **antes** de correr:
qué se mide, por qué, sobre qué modelo, y qué resultado falsearía la hipótesis — escrito en un
`BRIEF.md` y leído del archivo que produce, nunca de un código de salida ni de una impresión recordada.

**Cómo.** El brief de una corrida declara sus brazos, su función de veredicto, y su **condición de
parada** antes de gastar tiempo de GPU; el veredicto lo calcula código (`session_arm.reading`,
`staff_arm.abstain_verdict`, `h1_reading`, …) y se escribe a un archivo `.json` junto a los registros
crudos, así que cualquiera puede re-derivar la lectura después, del mismo archivo. Cada afirmación de este
repositorio, incluida cada una de este documento, lleva **[read]** (de un paper, una config, o el código,
citado) o **[ran]** (observado ejecutando algo acá, con la corrida nombrada) — nunca afirmado a secas.
**VOID** es un desenlace de primera clase, no algo para esconder: una corrida cuya precisión en primeros
turnos cae bajo el 90% en *cualquier* brazo, o cuya compuerta de identidad (§13) no aplica al miembro, se
lee como que no dice nada sobre el miembro, y se reporta así en vez de puntuarse igual.

**Por qué — y la regla que gobierna qué pasa cuando el instrumento mismo está mal.** El error de diseño
de un instrumento se **registra, no se corrige en silencio y se re-corre como si siempre hubiera estado
bien** — porque corregir en silencio la compuerta después de ver el resultado que produjo es exactamente
cómo se elige un resultado en vez de encontrarlo. **H1 (§10) es el ejemplo más fresco.** Su propia regla
pre-registrada — "primeros turnos ≥ 90% en cada brazo, o toda la corrida es VOID" — se escribió para
atrapar un renderizado que rompe a un miembro, e hizo algo que su autor no había anticipado: el propio
modo de falla de `harness-noblock` (0 de 60 primeros turnos, porque el miembro nunca se entrenó sin su
bloque de herramientas) anuló también la lectura de los *otros dos brazos*, aunque `history` y `harness`
anotaron los dos 60/60 en exactamente la misma condición. El arreglo no es editar `h1_reading` y
re-correrlo contra los mismos datos — eso sería ajustar la compuerta a la respuesta que ya produjo. En
cambio: el error se escribe en el propio brief, la corrida se lee **por brazo** con el código sin
modificar, y las dos lecturas que resultan — `harness` **PASÓ**, `harness-noblock` **FALSEADO** — se
declaran las dos, con la elección de cuál lectura vale para toda la corrida hecha explícitamente por el
usuario (2026-09-29: vale la lectura por brazo, el VOID tal como está escrito queda como el registro de
ese error del instrumento), no decidida por quien escriba el próximo documento.

**H2 (§10) encontró el límite de ese mismo arreglo.** Leer VOID por brazo, en vez de a través de todos los
brazos, fue el arreglo de H1 — y funcionó para `harness` contra `harness-noblock`. Pero aplicado sin
excepción anuló a `base-history`, una línea de base *sin entrenar* cuyo propósito entero es fallar: su bajo
puntaje en primeros turnos es el margen contra el que se mide `harness`, no un renderizado roto. **La regla
que necesita el instrumento es más angosta que la que se le dio: un VOID por brazo en primeros turnos
aplica a miembros entrenados, no a una línea de base sin entrenar cuyo fracaso ES el margen.** El resultado
queda registrado como FALSEADO-tal-como-está-escrito, con el pareo descriptivo enunciado al lado, exactamente
como el VOID de H1 quedó registrado al lado de su lectura por brazo — la compuerta no se editó después de
ver el resultado. **La decisión del usuario (2026-09-29), como para H1: lectura 1** — las condiciones
legibles son el veredicto de H2, `harness` PASÓ — con FALSEADO-tal-como-está-escrito en el registro junto a
sus dos errores de instrumento, no reemplazado por él.

**Una verificación que puede fallar mientras la capacidad funciona mide fraseo, no el mecanismo.** Los
errores de QA de H2 incluyen diez casos que leen la página entera `definition-of-done` en vez de citar su
ancla `#tests` específicamente — el enunciado que preguntaba la pregunta está dentro de lo que el miembro
leyó, así que una verificación del ancla falla exactamente en los casos donde la capacidad de fondo
(encontrar el hecho correcto) tuvo éxito. El error queda registrado, no aflojado hasta convertirlo en un
acierto, ni tampoco usado para afirmar que la capacidad falta.

**H3 (§10) arregló el chequeo del ancla y tasó un scorer que todavía no carga el veredicto.**
`turn_right_h3` puntúa una lectura de página como correcta cuando el texto devuelto contiene el enunciado
citado, cerrando la brecha del párrafo anterior; aplicado a los propios registros de H2 no cambia ningún
conteo dependiente, así que el arreglo no movió un número que no debía mover. Un scorer informal aparte,
"ancla-por-resultado" — acreditar cualquier turno cuyo resultado *contenga* el hecho, sin importar qué
herramienta lo produjo — se probó al lado y acredita 9 de los turnos independientes de `tr-s0` y 0 de los
de `tr-s1`: premia a un miembro por leer más de lo que se le pidió, no por usar bien el workflow, así que
se reporta y no se usa para decidir H3a. La regla de VOID por brazo (§10) se aplicó sin sobresaltos acá —
cada brazo entrenado (`s0-harness`, `s1-harness`, `s1-noblock`) superó el 90% de primeros turnos, así que
no se repitió ningún error de instrumento en esta corrida.

**Evidencia.** Esto no es un reclamo que necesite su propia corrida — es la disciplina a la que ya estuvo
sometida cada corrida citada en otra parte de este documento: el arreglo de llamada malformada de P58, la
regla de P47 de que un veredicto se lee de un archivo y nunca de un código de salida
(`docs/SUBSTRATE-GATE.md`), el chequeo de holgura de M10 sobre `staff-s0` antes de acreditar la abstención
de `out-s0`, el propio error de instrumento registrado de H1, y el arreglo más angosto de H2 a la misma
regla, arriba, son cinco instancias de la misma disciplina dentro de este repositorio, no cinco reglas
distintas.
