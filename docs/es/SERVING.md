# Servir el pool a un runtime de agentes

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
