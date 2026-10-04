# Apuntar OpenClaw al pool, paso a paso

**Todo lo de acá se leyó del CLI instalado y de su propio esquema de configuración**
(OpenClaw 2026.9.4), no se adivinó. Donde una afirmación es sobre comportamiento y no
sobre configuración va marcada **[read]** hasta que una corrida la marque **[ran]**.

## Antes que nada: esto no toca tu instalación de trabajo

El `--profile <nombre>` de OpenClaw aísla `OPENCLAW_STATE_DIR` y
`OPENCLAW_CONFIG_PATH` bajo `~/.openclaw-<nombre>` **[read]** — lo dice su propio
`--help`. Todos los comandos de abajo usan `--profile lorakernel`, así que tu agente
`main`, sus cuentas y sus sesiones quedan intactos y no hay nada que deshacer.

**Leé esto antes de correr nada, no después**: un request que el pool no sirve se
**reenvía a lo que hayas configurado como fallback**, y para correo real eso significa
que el mensaje sale de tu máquina. El proxy imprime una línea por request reenviado
nombrando formas y nunca contenido, así que podés ver qué salió —
[`SERVING.md`](SERVING.md).

## 1. El pool tiene que estar en algún lado

Esta máquina es una Mac arm64 de 16 GB: **no puede servir vLLM**. Así que el pool corre
en una tarjeta alquilada y el proxy corre acá, que es el arreglo que deja tu credencial
en tu propia máquina:

    tu Mac                                     Colab
    OpenClaw ──▶ proxy :8001 ──(túnel)──▶ vLLM :8000 + adaptadores
                     │
                     └──▶ api.openai.com   (lo que el pool no sirve)

**La consecuencia, dicha en vez de descubierta**: lo que el pool *sí* sirve viaja a
Colab, y lo que no, viaja a OpenAI. Ninguna de las dos es tu máquina.

## 2. Levantar el pool y el proxy

En la tarjeta alquilada, según [`SERVING.md`](SERVING.md); después, acá:

    export OPENAI_API_KEY=...          # nunca en la línea de comandos: `ps` la ve
    python3 -m training.harness.openai_proxy \
        --upstream http://127.0.0.1:8000 --port 8001 \
        --prune --member-prompt --auto auto --auto-out gpt-5.6-sol \
        --fallback https://api.openai.com/v1

**`--prune` es lo que hace que el §4b valga la pena**, y se explica ahí. Imprime la
superficie de etiquetas que declara cada miembro:

    [prune] email-full: ['thread_history', 'sender_stats', 'message']
    [prune] fluids-full: ['calc', 'lookup', 'convert']
    [prune] domain-mt: no tools — declares none
    [prune] a model not listed above is offered every tool, unpruned

Imprime qué se queda y qué sale antes de servir un solo request:

    [proxy] local, never leaves: ['email-full', 'Qwen/Qwen2.5-3B-Instruct']
    [proxy] everything else -> https://api.openai.com/v1 (key from $OPENAI_API_KEY)

**Mirá esa línea.** Es todo el contrato de privacidad en dos renglones, y se lee del
propio `/v1/models` del upstream y no de una lista que alguien mantiene a mano.

## 3. Registrar el pool como proveedor

`models.providers.<nombre>` acepta `baseUrl`, un adaptador `api` y un estilo `auth` —
los tres leídos del esquema. `openai-completions` es el adaptador que habla
`/v1/chat/completions`.

**`config patch` lee de `--file` o `--stdin`, nunca de un argumento posicional** — la
primera versión de esta página lo tenía mal y el CLI lo dijo. Escribí el patch,
validalo, y recién ahí aplicalo:

    cat > /tmp/lorapool.json5 <<'J5'
    {
      models: {
        providers: {
          lorapool: {
            baseUrl: "http://127.0.0.1:8001/v1",
            api: "openai-completions",
            auth: "api-key",
            apiKey: "unused",
            models: [ { id: "email-full", name: "Experto de triage de email (QLoRA local)" } ]
          }
        }
      }
    }
    J5

    ~/.openclaw/bin/openclaw --profile lorakernel config patch \
        --file /tmp/lorapool.json5 --dry-run     # dice en qué archivo escribiría
    ~/.openclaw/bin/openclaw --profile lorakernel config patch \
        --file /tmp/lorapool.json5

`apiKey` lo exige el adaptador y el proxy lo ignora salvo que lo arranques con
`--api-key`. **Arrancalo con uno en cuanto sea alcanzable desde algo que no sea
localhost.**

## 4. Apuntar un agente

    printf '{ agents: { defaults: { model: "lorapool/email-full" } } }\n' \
        > /tmp/agentdef.json5
    ~/.openclaw/bin/openclaw --profile lorakernel config patch --file /tmp/agentdef.json5

    ~/.openclaw/bin/openclaw --profile lorakernel models list

**O no nombrar ningún miembro.** Arrancá el proxy con `--auto auto --auto-out <modelo de
frontera>` y registrá `auto` como el modelo del proveedor: el proxy lee el texto de cada
request, lo sirve local cuando cae en una región que un miembro está medido que
resuelve, y lo reenvía si no — el cliente no conoce el pool. Reproducido sobre el tráfico
de P41 entrega exactamente lo que el ruteo por región, 0,775 sin ningún mal ruteado
**[ran]** P62; la línea que imprime por request nombra la decisión y las formas, nunca
el contenido.

## 5. Correr un turno y mirar los dos lados

    ~/.openclaw/bin/openclaw --profile lorakernel agent --local \
        -m "Is this important? From: Bruno Costa <bruno.costa@tallgrass.com> \
            Subject: Re: the migration  Preview: Hello, following up here. \
            Answer with one line: IMPORTANT or NOT IMPORTANT."

Así se ve un turno que funciona **[ran]** 2026-09-15:

    [model-fetch] response provider=lorapool model=email-full status=200
                  elapsedMs=4009 contentType=text/event-stream
    NOT IMPORTANT
    [agent] run ... ended with stopReason=stop

Dos cosas deberían pasar a la vez: el agente contesta, y el proxy **no dice nada** —
porque `email-full` es local y no salió nada. Pedí un modelo que el pool no sirve y
obtenés la otra línea:

    [route] OUT -> gpt-5.6-sol · 4 messages · 2317 chars · 3 tools

## 4b. Darle al agente las herramientas del inbox — el paso que hace que la demo signifique algo

**Sin esto la demo muestra el transporte y no al experto.** El primer turno de P43 no
hizo **ninguna llamada a herramientas**: OpenClaw manda las suyas, así que `email-full`
contestó sólo desde el listado — que es lo que hace la base, 0,345 **[ran]**.

OpenClaw habla MCP, así que las tres herramientas que la suite puntúa pasan a ser
herramientas del agente:

    cat > /tmp/inboxmcp.json5 <<'J5'
    {
      mcp: {
        servers: {
          "lora-inbox": {
            enabled: true,
            command: "/ruta/a/python",
            args: ["-m", "training.mcp.inbox_server", "--seed", "717171", "--n", "150"],
            cwd: "/ruta/a/lora-kernel"
          }
        }
      }
    }
    J5

    ~/.openclaw/bin/openclaw --profile lorakernel config patch --file /tmp/inboxmcp.json5

**Sirve el inbox sintético a propósito.** `training/email/inbox.generate` sortea un
inbox determinista desde una semilla; **no se lee, abre ni reenvía correspondencia
real**, y la semilla es la de la suite para que la demo y el número hablen del mismo
inbox. Apuntarlo a correo real es otro programa con otra revisión.

### Enchufar el servidor no alcanza — hay que podar la superficie

**Ofrecer las tres herramientas no elimina el problema que encontró P43; le agrega
tres líneas.** Un runtime de agentes manda su caja de herramientas *entera*, así que
el experto ve sus tres etiquetas entre decenas que nunca conoció — y ahí hay dos
cosas distintas mal en lo que lee:

| | qué sale mal | cuánto cuesta, medido |
|---|---|---|
| **volumen** | decenas de nombres de etiqueta que los pesos nunca vieron | P25: sobre una superficie desconocida el adaptador llega a **27 de 63** — sabe *que* un paso necesita un lookup y le erra al nombre **[ran]** |
| **renombrado** | las tres que *sí* conoce llegan como `mcp__lora-inbox__message` | una etiqueta que nunca escribió, así que conocer la herramienta no le sirve |

`--prune` arregla las dos, y lo hace **sin que el proxy aprenda un solo nombre de
herramienta**. Cada miembro del pool declara las etiquetas que le enseñó su corpus —
en el mismo lugar donde vive su banda de dificultad, `contract.py` — y el proxy
conserva sólo las herramientas ofrecidas que coinciden con una, por nombre exacto o
por el último segmento de uno con namespace (`mcp__…__`, `.`, `/`, `:`). Una llamada
que escribe el adaptador sale con el nombre que ofreció el agente, así el agente
todavía puede rutearla.

**Lo que llega al modelo es entonces, byte a byte, el bloque con el que entrenó** —
`tests/test_prune.py` lo afirma exactamente contra el corpus, y afirmarlo fue lo que
descubrió que la primera versión alfabetizaba las tres líneas en un orden que el
adaptador nunca había leído **[ran]** 2026-09-16.

Dos cosas que esto deliberadamente no hace:

- **No vuelve a ofrecer lo que descartó.** Un miembro que no reconoce ninguna de las
  herramientas ofrecidas se queda sin ninguna, y el log del request lo dice en
  `tools_offered` contra `tools`. Caer de vuelta a la superficie completa sería
  volver a ofrecer la que P25 ya tarifó.
- **No adivina entre dos servidores.** Si dos herramientas ofrecidas terminan en la
  misma etiqueta, la etiqueta se descarta: llamar a la equivocada de dos es peor que
  no llamar a ninguna.

**Medido, P59 [ran] 2026-09-17**, sobre la superficie que OpenClaw manda de verdad (54
herramientas, grabadas de un turno): **sin podar, el experto copia etiquetas del bloque** —
llama a `agents_list`, `apply_patch`, `ask_user`, `browser` — 225 de 227 llamadas
rechazadas por el inbox, y dentro de OpenClaw esas se habrían *ejecutado*. Podado a sus
tres: 1160 llamadas, 8 rechazadas. Exactitud 0,664 → 0,729 en mensajes humanos, 87 : 64,
$p = 0,073$ — empate a $n = 475$; la conducta no. El bloque son **~7.956 tokens** sin podar,
**~77** podado.

**Y cuesta latencia, con caché de prefijos o sin ella — E5 [ran] 2026-09-28.** El corpus de un miembro pone el bloque de
herramientas *después* del pedido, así que dos pedidos nunca lo comparten como prefijo: en el miembro de la escuela (E4B,
vLLM 0.30, caché encendida) el bloque de 54 herramientas (7.205 tokens de Gemma) lleva el tiempo al primer token de
**0,10 s a 1,70 s** (16,8×) y el throughput con 8 en vuelo de 132 a 108 tok/s; exactitud 70/70 → 39/70. Donde el prefijo
entero se repitió, el mismo bloque no costó nada (0,09–0,11 s): lo que la caché no absorbe es el orden, no el tamaño
([`E5`](../../results/E5-engine-baseline-20260928/BRIEF.md)).

**Así que: arrancá el proxy con `--prune`.** Sigue siendo un flag para que el brazo sin
podar se pueda volver a comprar; ya no es el default que esta página recomendaba en
contra.

### Qué encontró el turno en vivo, y por qué tres flags son ahora el default para un miembro

**Medido, P63 [ran] 2026-09-18**, 40 turnos en vivo desde esta misma configuración: con
las herramientas del inbox ofrecidas y podadas, **bajo el system prompt de 37 KB de
OpenClaw el experto llamó una herramienta en 2 de 32 turnos humanos y sacó 0,281** — la
conducta de la base pelada con las herramientas al alcance. Servido bajo el prompt que
enseñó su corpus (`--member-prompt`, el `system` del contrato), con la generación
cortada en sus etiquetas de cierre, seis idas y vueltas como máximo y 256 tokens por
paso — las cotas del propio loop del corpus — **llamó una herramienta en 19 de 32 y sacó
22/32 = 0,688 contra la barra de 0,655**, 40/40 turnos locales, 3,5 s cada uno. Seis
fallas del camino en vivo se encontraron en el trayecto y están corregidas con tests: el
router leyendo el system prompt del runtime y su sobre de contexto interno, el eco del
bloque de herramientas ejecutado como llamadas, sin corte en `</tag>` (inventaba la
respuesta de la herramienta), sin tope de idas y vueltas, sin cota de tokens, el lock de
gateway viejo de un turno matado. El libro está en
`results/P63-openclaw-live-20260918/BRIEF.md`.

**Así que un miembro es lo que su corpus enseñó — el bloque *y* el prompt.** `--prune`,
`--member-prompt` y `--auto` son con lo que arranca el comando de arriba.

**Dos miembros sobre un inbox, P64 [ran] 2026-09-18.** `desk-commitment@v1` se sirve junto a
`email-full@v1` desde el mismo vLLM, y los dos leen `From: / Subject: / Preview:`. Con claves
sobre esos marcadores, `--auto` mandó prompts de desk al miembro de triage 15 de 60 veces; con
claves sobre lo que se *pregunta* — "is this important" contra "did you commit" — los separa, y
en vivo sirvió cada sonda con el miembro correcto. **Una región es su pregunta, no su
listado**: cuando el perfil de una tarea suma un miembro, se agrega a `route.REGIONS` la
pregunta que responde, nunca un marcador que también llevan los prompts de otro miembro.

### El streaming, y por qué está buffereado

**OpenClaw hace streaming por defecto**, y poner
`agents.defaults.models.<modelo>.streaming` en `false` **no tomó efecto** **[ran]**. El
proxy antes rechazaba `stream` de plano, con el argumento de que un tag recién es una
llamada cuando cierra y bufferear toda la respuesta no es streaming. Ese principio era
correcto mientras la alternativa era una medición engañosa; acá era equivocado, porque
la alternativa era **que el pool fuera inalcanzable desde cualquier runtime de agente
real**.

Así que un request con stream se trae entero y se entrega como **un chunk SSE válido**,
y cada chunk lleva `x_buffered: true` **en el payload** — no sólo en un comentario. El
cliente recibe SSE correcto y una respuesta correcta. Lo que no recibe es entrega
incremental, que es latencia y no corrección.

## 6. Un solo gateway, una organización por proceso

El gateway (`examples/school/gateway.py`) es en sí un endpoint compatible con OpenAI, y **desde el
2026-09-28 sirve una organización por proceso** — `--org school` o `--org distributor`, compartiendo
la forma de roles/herramientas/almacén pero no el prompt con el que entrenó el miembro de cada
organización: el corpus de la escuela termina en `SCOPE` y enseña `OUT OF SCOPE`; el de la
distribuidora corre sus escrituras sin aprobación de un director, y hasta M10 nunca se abstuvo. El
OpenClaw de cada rol apunta al gateway con **su propio token firmado como clave del proveedor** — el
rol lo decide el token, nunca el id del modelo:

    python -m examples.school.gateway --upstream <URL de vLLM> --org school --member school-s0 \
        [--frontier-url https://api.openai.com/v1 --frontier-model <modelo>]    # la clave desde $FRONTIER_API_KEY
    ~/.openclaw/bin/openclaw --profile school-educador-north config patch \
        --file ~/.config/lora-kernel/openclaw/educador-north.json5
    ~/.openclaw/bin/openclaw --profile school-educador-north agent --local -m "¿Qué tiene en la agenda el alumno 1?"

`python -m examples.school.live_openclaw --org school` juega así toda la demo guionada y la puntúa
con las mismas verificaciones. **[ran] 2026-09-26: 15/15 a través de OpenClaw 2026.9.4 con el modelo
real (Gemma 4 E4B + `school-s0` en una L4) y Claude Haiku 4.5 como frontera** — el cableado pasó antes
15/15 con un sustituto ([`BRIEF`](../../results/LIVE-school-openclaw-20260926/BRIEF.md)). Algo que
enseñó el primer turno en vivo: OpenClaw agrega su propio contexto interno como *último* mensaje de
usuario y le pone fecha al pedido; el gateway lee el pedido de la persona dentro de eso
(`runtime_request`).

### La distribuidora, en vivo y local — `--org distributor`

El mismo gateway, apuntado al perfil `edge` en vez de a una tarjeta alquilada
([`SERVING.md`](SERVING.md)): llama.cpp sirviendo el E4B como Q8_0 con el LoRA propio de la
distribuidora, en la misma máquina que corre OpenClaw — nada alquilado, nada por túnel.

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-distributor-staff-out-s0-f16.gguf --port 8792 -c 8192 -ngl 99
    python -m examples.school.gateway --org distributor --upstream http://localhost:8792 --member out-s0 \
        --tokenizer google/gemma-4-E4B-it --port 8766 \
        [--frontier-url https://api.anthropic.com/v1 --frontier-model claude-haiku-4-5 \
         --frontier-key-env FRONTIER_API_KEY --frontier-budget-usd 1 --frontier-rates 1,5]
    python -m examples.school.live_openclaw --org distributor --out live.json

**[ran] 2026-09-28: 6/6 a través del OpenClaw real** — cinco turnos contestados local y el sexto, una
nota de agradecimiento a proveedores que `out-s0` reconoce como `OUT OF SCOPE` (M10, retenidos 20/20),
reenviado a **Claude Haiku 4.5**: 10.198 + 195 tokens, **$0,0112**
([`BRIEF`](../../results/LIVE-distributor-openclaw-20260928/BRIEF.md)). `out-s0` no es una liberación
formal (sin archivo de release) — es el brazo que usó esta corrida en vivo. Las dos mitades del
diagrama de referencia ahora corren en vivo, sobre la misma forma de gateway: la escuela en una
tarjeta alquilada, la distribuidora sin nada más que la propia Mac del usuario.

### Multi-turno a través del gateway — hoy `history=True`, después el arnés de flujos de trabajo

**El gateway solía descartar la conversación.** Todos los turnos de arriba leen `runtime_request` — el
último mensaje de la persona, extraído del sobre propio de OpenClaw — y nada anterior: "muévelo al
muelle 5" llegaba sin "lo" que resolver. **OpenClaw ya envía toda la conversación** en cada turno, en
ese mismo sobre; el hueco era el gateway descartando todo menos el último mensaje, no el cliente
reteniéndolo.

`Gateway(history=True)` renderiza cada pedido y respuesta anterior antes del actual — la manera
ingenua de cargar una conversación, y el brazo contra el que se mide **[ran]**
`results/MT0-multiturn-baseline-20260929/`: `out-s0` sobre 60 sesiones retenidas de la distribuidora
(124 turnos, 54 cuyo argumento viene sólo de un turno anterior). Sin history, 4/54; con ella,
**43/54 (79,6 %)**. Resuelve una referencia que puede copiar directo a un argumento (recepción 10/10,
devoluciones 10/10, compras 9/10, despacho 12/14); **no resuelve una que tiene que escribirse en texto
libre** — un reclamo sobre "ese pedido" se archiva sin número de pedido en 8 de 10 turnos de atención
al cliente.

**El arnés que este diseño busca poner en el lugar de `history=True` — H1 tiene un resultado, leído de
dos formas.** En vez de la conversación, `Gateway(memory=, workflows=)`
(`examples/common/opmemory.py`, [`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md))
renderiza una línea de contexto — el estado del flujo de trabajo del rol y los **nombres** de las
claves que guarda la caché de una sesión — y el miembro busca y guarda valores por clave
(`<get>`/`<put>`) sólo en el paso que los necesita, cerrando exactamente la falla que `history=True`
deja abierta: un reclamo que necesita el número de pedido lo obtiene de la caché, no de la lectura
propia del modelo sobre la transcripción. `results/H1-workflow-harness-20260929/` puntuó dos brazos
contra `history` sobre las 60 sesiones retenidas de MT0: `harness` (con el bloque de herramientas)
alcanzó **53/54** turnos dependientes contra el 43/54 de history, nombrando el pedido buscado por clave
en los 10 reclamos de atención al cliente (history: 2/10), con cada turno dependiente correcto buscado
por clave (53/53) y un prompt plano (745/726/710 tokens en los turnos 1–3, contra 345/428/394 de
history); `harness-noblock` (lo mismo, sin el bloque de herramientas) dio **0/60** — su corpus siempre
tuvo el bloque, así que sacarlo al momento de evaluar dejó al miembro sin llamar nada y enunciando
datos que nunca leyó. **Tal como está escrita, la corrida queda ANULADA**: la compuerta del brief anula
un brazo cuyos primeros turnos caen bajo el 90%, y aplicada entre brazos eso deja que el colapso de
`harness-noblock` anule toda la corrida — un error de instrumento, registrado, no corregido después del
hecho. **Leído por brazo, `harness` PASÓ y `harness-noblock` quedó FALSEADO. La decisión del usuario
(2026-09-29): vale la lectura por brazo, y el VOID tal como está escrito queda como el registro de ese
error del instrumento.** Ver
[`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md) §8 para la tabla completa.

**[ran] H2** corrió el mismo arnés después, sobre un dominio de sesiones más largas construido para eso:
un tracker de equipo tipo Jira + Confluence (`examples/tracker/`), sesiones de cinco turnos en vez de dos
o tres. `results/H2-tracker-harness-20260929/` puntúa a `harness` en **146/160** turnos dependientes
(91,3 %) con un prompt plano en los cinco turnos ($\bar p_5 \le 1.1\ \bar p_1$), pero la línea de base sin
entrenar `base-history` dispara con sus propios 44/60 primeros turnos la misma regla de VOID por brazo que
arregló a H1 — anular a una línea de base cuyo bajo puntaje *es* el margen que se mide, no un defecto,
vuelve ilegible la comparación pre-registrada, así que **la corrida se lee FALSEADA tal como está escrita,
no ANULADA**, en el registro con ese y el error de instrumento del chequeo de anchor. Descriptivamente,
142 de 160 favorecen a `harness` contra 0.
**La decisión del usuario (2026-09-29), como para H1: lectura 1** — las condiciones legibles son el
veredicto de H2, `harness` **PASÓ**: [`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md)
§9. `harness-noblock` (80/160) se leyó primero como "aprendido en parte"; era un error del corpus — su
tercio sin bloque compartía módulo con la rotación de roles, así que las filas sin bloque eran todas de
QA — no un aprendizaje parcial. **H3 [ran], las dos barras PASARON**: `tr-s1`, entrenado sobre un segundo
corpus (fraseo ampliado por turno en cada rol, un tercio parejo sin bloque de cada rol), le gana a
`tr-s0` 158/160 contra 147/160 sobre la misma suite fresca (pareado 11:0, $p = 0,00098$, plano), y sin el
bloque de herramientas sostiene 156/160 en cada rol a más o menos un tercio de los tokens de prompt
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).

**H1 y H2 corrieron sobre vLLM (una L4), no a través de OpenClaw — el miembro de H3 ya se corrió en vivo,
multi-turno, el último paso de ese orden.** `tr-s1` (el miembro sin bloque de H3, con la memoria operativa y la
captura de claves) servido por llama.cpp en la propia Mac del usuario, el mismo arreglo `edge` que LIVE-distributor,
manejado por OpenClaw en **tres sesiones separadas** (lead, developer, QA): **14 de 14 turnos, dependientes 8 de 8**,
latencia del gateway mediana 3,7 s, ~370 tokens de prompt por turno — la propiedad de prompt plano para la que está
construido cargar claves en vez de la conversación se sostiene sobre un cliente real, no sólo sobre un replay
([`LIVE-tracker`](../../results/LIVE-tracker-openclaw-20260930/BRIEF.md)). Toda otra corrida en vivo de esta página —
escuela 15/15, distribuidora 6/6 — sigue siendo de un solo turno: un pedido, una respuesta, ningún turno anterior
que resolver; ésta es la primera en llevar estado *a través* de turnos en vivo.

**El miembro servido del tracker desde el 2026-10-04 es `tr-out-s0`, en lugar de `tr-s1`** — decisión del usuario
sobre ROUTE1 (`docs/ARCHITECTURE.md`): el propio comando `llama-server`/gateway de `examples/tracker/live_tracker.py`
ahora nombra `lora-tracker-out-s0-f16.gguf` y `--member tr-out-s0`. El registro de LIVE-tracker de arriba queda
como que corrió `tr-s1`.

## 7. La biblioteca, como proveedor de OpenClaw — una corrida en vivo, PASÓ

[`examples/library/serve.py`](../../examples/library/serve.py) ([`SERVING.md`](SERVING.md)) es una *segunda* puerta
de entrada, al lado del gateway: un endpoint compatible con OpenAI que corre a `real-none-s0` (el miembro de
documentos reales aceptado después de REAL4, [`ARCHITECTURE.md`](ARCHITECTURE.md) §4) sobre el runtime de REAL4, en
llama.cpp. Apuntarle OpenClaw es registrarlo como proveedor como cualquier otro, porque el endpoint escribe el
parche solo al arrancar:

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-real-none-s0-f16.gguf --port 8793 -c 12288 -b 512 -ub 512 -ngl 99
    python -m examples.library.serve --library knowledge/logistics-regs --upstream http://127.0.0.1:8793 --port 8766 \
        --openclaw-patch ~/.config/lora-kernel/openclaw/library-reader.json5

    ~/.openclaw/bin/openclaw --profile lorakernel config patch \
        --file ~/.config/lora-kernel/openclaw/library-reader.json5
    ~/.openclaw/bin/openclaw --profile lorakernel agent --local -m "How long must a logistics carrier keep a driver's record of duty status?"

La respuesta es la contestación del miembro con su citación renderizada como `[título de página §ancla]`, o
`Not in my library.` si la biblioteca no tiene nada que decir — `real-none-s0` se entrenó para preferir eso antes que
una adivinanza (§7.1 de [`GUIDE.md`](GUIDE.md), [`REAL4`](../../results/REAL4-refusal-20260930/BRIEF.md)).

**La corrida en vivo está construida, probada offline, y ahora corrida de punta a punta sobre el servidor real — PASÓ.**
`examples/library/live_library.py` mandó las propias 52 preguntas de REAL4 por `openclaw agent --local` (OpenClaw
2026.9.4), una sesión fresca por cada una, y calificó el propio registro de recorrido del endpoint como lo hizo
REAL4 — valor y citación estricta. En la Mac del usuario, con el contexto achicado a **12.288** (16.384 se quedó sin
memoria), 22,5 minutos: **36/52** — titular 16/23, negativas 15/16, un salto 5/13 — contra el 38/52 de REAL4 sobre
vLLM bf16 (16/23, 15/16, 7/13): **PASÓ** (barra ≥ 34, negativas ≥ 13, titular ≥ 14), con el titular y las negativas
empatando exactamente con el brazo medido. Cada pérdida se lee como del borde: 4 recorridos desbordaron el contexto
de 12.288 tokens tras abrir entera una página de ~7k tokens, una pregunta hizo timeout sin recorrido grabado, tres
preguntas lentas se reenviaron envueltas en el propio sobre de mensaje encolado de OpenClaw
([`LIVE-library`](../../results/LIVE-library-20261001/BRIEF.md)). ~~**Pendiente, no hecho**: quitar ese sobre antes de
que el runtime lea la pregunta, y un presupuesto de página para que una página larga entre en un contexto de 12k.~~

**Los dos ya están construidos, y una corrida de seguimiento los leyó donde ocurren: SIN CAMBIO, 37/52.**
`examples/school/gateway.runtime_request` quita el sobre antes de que el runtime lea la pregunta (test
`test_openclaw_queued_envelope_is_stripped`), y `memory.runtime.Conversation.page_budget` (servido en **2.500**
tokens por `examples/library/serve.py --page-budget`) abre una página que supera ese presupuesto con sus enunciados
en orden BM25 contra la pregunta hasta el presupuesto, dejando el resto como anclas abribles, `id§ancla` — sólo las
mostradas cuentan como leídas. En esta biblioteca sólo 29 CFR 1910.178 lo supera. Las mismas 52 preguntas, corridas
de nuevo: **37/52** — titular 16/23, negativas 14/16, un salto 7/13 — contra el 36/52 de esta corrida y el 38/52 de
REAL4 sobre vLLM bf16; **0** desbordes de contexto (4 antes) y **0** sobres (3 antes), pareado contra LIVE-library
**3 : 2** ($p = 1,0$). Veredicto tal como está escrito: **SIN CAMBIO** — 0 desbordes pero 37 < 38, no REGRESADO. Las
tres ganancias son exactamente las filas que le costaba el borde (dos recorridos que desbordaban, uno sin recorrido
grabado); la única pérdida nueva, `none-9`, es el presupuesto poniendo a la vista el enunciado que mejor empareja con
la pregunta de una pregunta que la biblioteca no puede contestar. OpenClaw retuvo un turno ya terminado más allá de
la propia respuesta del endpoint en 3 filas — una de ellas más allá del timeout de 600 s del driver, que detuvo la
primera parte de la corrida hasta que el driver se arregló para atraparlo y reanudar. ~~**Pendiente, no hecho**: por
qué OpenClaw retiene un turno terminado~~
([`LIVE-library2`](../../results/LIVE-library2-20261002/BRIEF.md)).

**Encontrado y resuelto, 2026-10-02: node quedaba retenido adentro de su propia salida, y el driver ahora deja de
esperar una que puede no llegar nunca.** `sample`, corrido contra las tres retenciones de LIVE-library2, encontró
a las tres ya adentro de `process.exit()` después de una corrida exitosa — la propia respuesta, demora y formato
del endpoint no tienen ninguna parte, y un flag de V8 probado contra la salida misma no se separó del azar sobre
un stub (0/12 contra 3/15). `examples/library/live_library.run_turn` ahora arranca el turno en su propio grupo de
procesos y vuelve una vez que se imprimió la propia línea de fin de corrida de OpenClaw y pasó `GRACE_S` (2 s), o
en el timeout — de cualquier forma se mata el grupo entero, así que no queda nada corriendo; el `subprocess.run`
del driver viejo dejaba exactamente estos procesos retenidos como huérfanos durante horas. Verificado contra el
OpenClaw real sobre un stub sin modelo: 20 turnos, ~7 s cada uno, 0 timeouts, 0 huérfanos. Aparte, `serve.py` ahora
siempre responde a un recorrido que lanza una excepción (`NO_ANSWER`, el error registrado al lado) en vez de
cerrar el socket sin respuesta — el comportamiento viejo era lo que hacía que OpenClaw leyera un timeout como una
falla de transporte y reenviara el turno envuelto como `[Queued user message …]`, de donde salían las propias
filas de sobre de LIVE-library y su fila de 119 s sin recorrido [read: el propio registro de `Connection error` de
OpenClaw antes del reenvío, según el mensaje del commit y `test_a_walk_that_raises_still_answers_so_the_runtime_does_not_resend`
de `tests/test_library_live.py`].

## Cuánto vale esto, medido

| | entrega | sale de la máquina |
|---|--:|--:|
| todo local | 0,546 | 0% |
| **la región que falla, reenviada** | **0,775** | **38%** |

**[ran]** `results/P41-routing-20260915/`. En su región el experto local le gana a la
base **8 : 51** sobre los mismos casos **[ran]** `results/P40-pool-retried-20260915/`.

## Qué esperar que no es buena noticia

- **Hay un experto útil, no dos.** El de fluidos sigue el protocolo a la perfección y
  se equivoca en la física 78 veces de 90 **[ran]**. Por eso no está en la
  configuración de arriba.
- **La ruta es por nombre de modelo**, que es la elección de tu agente. La escalación
  por caso está medida y hoy es **peor** que rutear por región **[ran]**.
- **El veredicto de la compuerta sobre el experto de email no es reproducible entre
  corridas** — 84, 81, 82 contra un umbral de 83, los tres pares empatados **[ran]**.
  El *efecto* contra la base no es marginal; el *veredicto* sí.

## Cómo deshacerlo

    rm -rf ~/.openclaw-lorakernel

Ningún comando de esta página escribió nada en `~/.openclaw`.
