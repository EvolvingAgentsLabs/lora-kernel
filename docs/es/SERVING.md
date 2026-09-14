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

**El bucle multi-turno.** Un agente devuelve resultados con `role: "tool"` y el proxy
los pliega en la transcripción como `= valor`, donde el adaptador fue entrenado para
leerlos. **Todas las mediciones hasta acá fueron de un solo turno** — P27 brazo 3
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
