# Arquitectura

El sistema tal como está diseñado el 2026-09-19. Lo que está construido y medido lleva la
marca **[ran]**; lo que está diseñado y no construido, lo dice. Las mediciones detrás de
cada elección están en [`RECORD.md`](RECORD.md); el orden de trabajo está en
[`PLAN.md`](PLAN.md).

## 1. Un hecho, tres componentes

**Un experto es la distribución de su corpus.** No sólo los pesos: el bloque de
herramientas, las claves del argumento y su orden, el system prompt, la profundidad de los
problemas que vio. Servido fuera de esa distribución es un modelo distinto, peor — 2 de 32
turnos en vivo llaman a una herramienta bajo un prompt ajeno, 19 de 32 bajo el propio
**[ran]** P63; por debajo de su profundidad de entrenamiento un experto de razonamiento
sobre-resuelve 18 de 18 **[ran]** P45.

Todo lo demás es ese hecho aplicado tres veces:

| componente | qué es | estado |
|---|---|---|
| **el experto** | un QLoRA sobre el modelo chico, entrenado por SFT sobre un corpus, liberado con un contrato que registra la distribución | **[ran]** dos liberados, sobre Qwen 2.5 |
| **el router** | un modelo muy chico *de los mismos corpus*: a la distribución de qué experto cae este pedido — o de ninguno | un diccionario de palabras clave **[ran]**; el modelo es el hito 2 |
| **el par** | un segundo LoRA, sobre el modelo grande, entrenado sobre el *mismo corpus*; el chico borradorea, el grande verifica | diseñado; hitos 3–4 |

```mermaid
flowchart TB
    subgraph REL["una liberación = un corpus, registrado"]
        K["corpus<br>bloque · claves · orden · prompt · banda"]
    end
    K --> E["LoRA experto sobre el modelo chico"]
    K --> T["LoRA sobre el modelo grande<br>mismo subdominio"]
    K --> R["router<br>una clase por corpus + abstención"]
    R -- "este corpus" --> E
    E -- "borradorea" --> T
    R -- "ningún corpus" --> F["modelo de frontera"]
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1a2240
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class K art
    class E,T,R local
    class F out
```

Un solo artefacto — el corpus nombrado en el manifiesto de la liberación — define al
experto, entrena su mitad grande, y entrena la clase del router para él. Agregar una región
agrega un corpus.

## 2. El camino del pedido

```mermaid
sequenceDiagram
    participant C as cliente
    participant P as proxy
    participant R as router
    participant S as chico + LoRA
    participant L as grande + LoRA
    participant F as frontera
    C->>P: chat completion, sin modelo nombrado
    P->>R: el texto de usuario de la conversación, con el envoltorio del runtime recortado
    alt cae en el corpus de un miembro, región servida localmente
        R-->>P: miembro
        P->>S: prompt del miembro, herramientas podadas, límites de modo corpus
        S->>L: borrador, donde se midió que la región necesita el par
        L-->>P: respuesta verificada
    else no cae en ninguno, o la región midió que falla
        R-->>P: afuera
        P->>F: reenviado tal como llegó
    end
    P-->>C: respuesta, con la ruta registrada sólo como formas
```

**El proxy** (`openai_proxy.py`) **[ran]**. Habla la API de OpenAI. Para un miembro poda las
herramientas ofrecidas a la superficie declarada del miembro (`--prune`), reemplaza el
system prompt del runtime por el que enseñó el corpus (`--member-prompt`), y corre el bucle
de modo corpus — la generación para en una etiqueta de cierre, se inyecta el resultado de la
herramienta, continúa — acotado a seis idas y vueltas y 256 tokens por paso, los límites que
tiene el propio corpus. Se rehúsa antes que servir mal: un pedido que no puede rutear es un
503, no una adivinanza.

**El router** lee el asunto de la conversación y nada más: cada turno de usuario, con el
envoltorio de contexto interno del runtime recortado — el propio system prompt de un
runtime superó en puntaje al email del turno de usuario la primera vez que un agente en vivo
llamó **[ran]** P63. Dos decisiones se mantienen separadas a propósito:

- *a qué distribución pertenece esto* — la del router, aprendida de los corpus;
- *esa región se sirve localmente* — una tabla medida, `serve: local | out`. Fluids es una
  coincidencia temática perfecta y se midió que falla; se sirve afuera.

**El default es la frontera.** Un modelo al que se le pide elegir siempre elige, así que la
abstención está diseñada de entrada y se mide primero (hito 2).

## 3. El par

**Por qué la mitad grande está entrenada, no prestada.** Un modelo grande sin entrenar no es
mejor experto en una región angosta: 0,967 contra el 1,000 del experto chico en desk, 0,746
contra 0,989 en triage **[ran]** P55, P55b. La verificación por un modelo que discrepa con
un borrador *correcto* rechaza tokens buenos. Entrenar el modelo grande sobre el mismo
corpus es lo que lo vuelve un verificador de este subdominio en lugar de una segunda opinión
generalista.

**Lo que ya se sabe de las mitades.** vLLM aplica un LoRA sobre un modelo grande en 4 bits
**[ran]** P60 §3b. Los adaptadores de Qwen 3.5 son servibles una vez que sus tensores llevan
los nombres de la clase que vLLM sirve **[ran]** D2. Los modelos chico y grande de la
familia comparten un espacio de ids, así que un token drafteado *puede* verificarse
**[ran]** D0 — entre familias, o contra una API de frontera, no puede **[ran]** P48.

**Lo que todavía no está disponible.** La decodificación especulativa de vLLM no acepta un
drafter con adaptador LoRA; eso es un RFC **[read]**. Hasta que salga, la aceptación se mide
por teacher forcing — el modelo grande puntúa el borrador terminado del chico en un solo
prefill (`accept_rank.py`, [`FOUNDATIONS.md`](FOUNDATIONS.md) §5.3, §6) — lo que da α
exactamente y la aceleración nada. El par es primero un dispositivo de **calidad** (¿el
grande + LoRA le gana al chico + LoRA donde el chico tiene margen?) y después uno
**especulativo** (¿el LoRA emparejado sube α?).

**Dónde corre.** El pool chico se sirve desde una sola L4. Un 27B es trabajo de A100 en 4
bits.

## 4. El contrato de liberación

Una región entra por una sola puerta **[ran]**: una suite con un verificador que el bucle de
entrenamiento nunca ve; la base pelada como brazo de headroom; el test de signos exacto
sobre pares discordantes. El manifiesto que resulta (`releases/*.json`) guarda base, receta,
hash del corpus, hash del adaptador, hash del prompt, el score y las comparaciones pareadas.
Volver a servirlo y volver a entrenar desde él empatan con la corrida registrada **[ran]**
P57. `training/harness/train_pool.py` guarda cada miembro como un registro leído de su
corpus — banda, superficie, claves, orden, system prompt — y los tests vuelven a leer cada
corpus y fallan si una declaración se desvía.

## 5. La familia

Qwen 3.x: `Qwen3.5-4B` (o `2B`) chico, `Qwen3.8-27B` grande. La línea 3.x es híbrida — tres
capas de atención lineal por cada capa de atención completa — y el adaptador renombrado de
D2 aterrizó pesos en los dos tipos. Su canal `<think>` queda apagado para los miembros. Los
miembros liberados siguen sobre `Qwen2.5-3B-Instruct`; el hito 1 los muda, con las
liberaciones 2.5 como control.

Nada en §1–§4 nombra una familia. Un par necesita un espacio de ids y una base a la que PEFT
pueda engancharse; `Gemma 4 2B / 12B` cumple lo primero y todavía no lo segundo **[ran]**
P29.

## 6. Lo que no es neuronal, a propósito

- **La memoria** es markdown y git.
- **La ejecución** es un sandbox; las herramientas son un servidor MCP
  (`training/mcp/inbox_server.py`).
- **La aritmética** es una calculadora: la destilación transfirió un procedimiento y no la
  aritmética **[ran]** P5–P7.
- **Si una región se sirve localmente** es una tabla de mediciones, no la opinión de un
  modelo.

## 7. Deliberadamente sin construir

Un runtime de inferencia a medida, compartir la caché KV entre adaptadores, tree attention
entre adaptadores, composición de adaptadores, un torneo que los cría, el control plane, los
packs verticales. Y, por alcance más que por orden: el servicio de personalización y sus
herramientas no son parte de este runtime ni de la versión open-source.
