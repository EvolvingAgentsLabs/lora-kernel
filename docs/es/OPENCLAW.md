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
        --fallback https://api.openai.com/v1

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
