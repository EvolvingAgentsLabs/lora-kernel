# Arquitectura

El sistema tal como está diseñado el 2026-09-19, estado al 2026-09-20. Lo que está construido y
medido lleva la marca **[ran]**; lo que está diseñado y no construido, lo dice. Dónde se ubica
dentro de una organización entera, y qué falta para que sea un framework genérico, está en el §9 y
en [`FRAMEWORK.md`](FRAMEWORK.md). Las mediciones detrás de cada elección están en
[`RECORD.md`](RECORD.md); el orden de trabajo está en [`PLAN.md`](PLAN.md).

## 1. Un hecho, cuatro componentes — y qué es la versión 1.0

**Un experto es la distribución de su corpus.** No sólo los pesos: el bloque de
herramientas, las claves del argumento y su orden, el system prompt, la profundidad de los
problemas que vio. Servido fuera de esa distribución es un modelo distinto, peor — 2 de 32
turnos en vivo llaman a una herramienta bajo un prompt ajeno, 19 de 32 bajo el propio
**[ran]** P63; un experto que razona en cadenas de 6 a 9 pasos puntúa 11 de 90 cuando los
resultados de sus herramientas le llegan como mensajes `tool_calls` y **90 de 90** cuando se
escriben en línea, como le enseñó su corpus **[ran]** M7 brazo 0b.

**La versión 1.0 es cinco cosas [spec]:** los expertos definidos por sus corpus, el router
con su abstención, la memoria (§4), el runtime que la arbitra, y el contrato de liberación
que la hashea toda. El par del §3 se acopla por subdominio donde se mide que paga y no es
requerido por 1.0.

Todo lo demás es ese hecho aplicado cuatro veces:

| componente | qué es | estado |
|---|---|---|
| **el experto** | un QLoRA sobre el modelo chico, entrenado por SFT sobre un corpus, liberado con un contrato que registra la distribución | **[ran]** dos liberados; desde M1 sobre `Qwen3.5-4B`, cada uno empatando su liberación de Qwen 2.5 |
| **el router** | un modelo muy chico *de los mismos corpus*: a la distribución de qué experto cae este pedido — o de ninguno | un diccionario de palabras clave **[ran]**; dos brazos aprendidos **[ran]** M2, ninguno pasa; en un despliegue con un agente por rol, *el rol es la ruta* (§9) |
| **el par** | un segundo LoRA, sobre el modelo grande, entrenado sobre el *mismo corpus*; el chico borradorea, el grande verifica | diseñado; hitos 3–4 |
| **la memoria** | la biblioteca propia del subdominio — un arnés operativo y una wiki enciclopédica — un radar sobre ella, tres verbos, y un árbitro; el LoRA aprende el **hábito de navegar**, no el contenido | biblioteca, árbitro, corpus construidos **[ran]** W1, W2, W4; búsqueda debajo de su vara **[ran]** W3; **la afirmación central medida tres veces y no pasa** **[ran]** W5, W5b, W5c — la navegación se transfiere, leer un valor condicional en una nota nunca vista no (§4) |

```mermaid
flowchart TB
    subgraph REL["una liberación = un corpus, registrado"]
        K["corpus<br>bloque · claves · orden · prompt · banda"]
    end
    K --> E["LoRA experto sobre el modelo chico"]
    K --> T["LoRA sobre el modelo grande<br>mismo subdominio"]
    K --> R["router<br>una clase por corpus + abstención"]
    K --> B["base de conocimiento del subdominio<br>notas · links · embeddings"]
    E -- "navega · lee · sigue" --> B
    R -- "este corpus" --> E
    E -- "borradorea" --> T
    R -- "ningún corpus" --> F["modelo de frontera"]
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1a2240
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class K,B art
    class E,T,R local
    class F out
```

Un solo artefacto — el corpus nombrado en el manifiesto de la liberación — define al
experto, entrena su mitad grande, y entrena la clase del router para él. Agregar una región
agrega un corpus, y la base de conocimiento que las trayectorias de ese corpus recorren.

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

- *a qué distribución pertenece esto* — la del router, aprendida de los corpus. Su primer
  brazo aprendido, un modelo de n-gramas del marco de cada corpus, fue seguro sobre texto
  ajeno y perdió todos los pedidos de un remitente nunca visto **[ran]** M2; el diccionario
  se mantiene hasta que se mida el brazo de embeddings;
- *esa región se sirve localmente* — una tabla medida, `serve: local | out`. La tabla vale lo
  que valga la medición detrás: fluids estaba marcada *afuera* con un 11 de 90, que resultó
  ser el camino de servido — localmente, como le enseñaron, es 90 de 90 contra el 66 de la
  frontera **[ran]** M7 brazo 0b — y vuelve a pasar por la puerta de liberación antes de que
  la marca cambie.

**El default es la frontera.** Un modelo al que se le pide elegir siempre elige, así que la
abstención está diseñada de entrada y se mide primero (hito 2).

**Frente a las herramientas de una organización, el gateway [ran] 2026-09-25** (`examples/school/gateway.py`, el
camino de la organización de referencia). Lo que el proxy hace por un miembro, más las cuatro cosas que necesita un
sistema de agentes por rol y que un modelo no debe decidir:

| paso | qué hace | dónde vive, y por qué no en el modelo |
|---|---|---|
| **quién** | se verifica el token portador → usuario, rol, tenant; un rol pedido en `model: auto:<rol>` tiene que coincidir con él | `examples/common/tokens.py` (HS256 con un secreto de demo, en lugar del RS256/JWKS del proveedor de identidad — esa verificación no está construida) |
| **permiso** | cada herramienta corre con esa credencial; la fila de otro tenant se rechaza antes de leerla | la capa de herramientas (`examples/school/tools.py`) — 77 casos adversariales, 0 fugas **[ran]** |
| **una persona para lo que importa** | un pago o un mensaje a todas las familias queda RETENIDO; lo aprueba un director del mismo tenant, nunca la cuenta que lo pidió; después corre con el alcance de quien lo pidió | `examples/common/approvals.py` |
| **qué puede afirmar una respuesta** | cada ítem de una respuesta tiene que ocurrir en un resultado real de herramienta, o la respuesta se reemplaza por el texto propio de las herramientas; el texto con forma de instrucción encontrado en un registro se saca de lo que se muestra | `examples/common/grounding.py` — el LoRA del personal de la escuela inventó una línea de un listado de una herramienta el día de la demo; el filtro reemplazó 2 de 5 respuestas locales y el usuario no vio ninguna de las dos **[ran]** `results/DEMO-school-gemma-20260925` |
| **alcance** | un pedido que las herramientas del rol no cubren sigue la salida del rol: la frontera, o la cola de una persona | el modelo dice `OUT OF SCOPE`; la política decide adónde va — el juicio del modelo queda registrado, no se confía en él |
| **log** | una línea JSON por pedido — quién, rol, ruta, llamadas, rechazos, retenciones, anclaje, tokens — y un dashboard que tasa los tokens locales a las tarifas de la frontera | el feed de monitoreo; el costo propio de la GPU no se tasa |

**Un proceso por organización, no un solo gateway para todas [ran] 2026-09-28** (`--org school|distributor`). Las
herramientas, el corpus y el estado de aprobación de cada organización viven en su propio proceso, así que las
aprobaciones RETENIDAS de una escuela y la política de salida de una distribuidora nunca comparten memoria por
accidente. Las dos organizaciones difieren a propósito, no por omisión: el miembro de la distribuidora se sirve con su
**propio prompt de corpus**, sin línea de SCOPE — su decisión de alcance está entrenada en el corpus mismo (más abajo),
no declarada en el system prompt — y sus escrituras corren sin aprobación de un director, una decisión de política de
esa organización y sus roles, no un hueco en el mecanismo de aprobaciones de arriba.

**El gateway lleva el estado de una sesión, no su transcripción — diseñado, H1 corriendo.** La corrección ingenua
para multi-turno es `Gateway(history=True)`: repetir la conversación para que una referencia a un turno anterior
("llevalo al andén 5") tenga a qué referirse. **[ran] MT0** (`results/MT0-multiturn-baseline-20260929`, 60 sesiones
held-out de la distribuidora, 124 turnos, 54 dependientes de un turno anterior) lo mide: sin la conversación, 4 de 54
turnos dependientes se resuelven — los turnos independientes de la historia puntúan 60 de 60 en los dos brazos, así
que la brecha es específica de lo que depende de un turno anterior, no una regresión general. Con la conversación, 43
de 54 (79,6 %), al borde del margen que da esta corrección: resuelve una referencia copiada directo a un argumento
(recepción 10/10, devoluciones 10/10, compras 9/10, despacho 12/14) pero no una escrita en texto libre — un reclamo
sobre "ese pedido" se archiva sin el número de pedido 8 de 10 veces (atención al cliente 2/10) — y los tokens siguen
creciendo con la sesión (+24 % en el turno 2). La alternativa en diseño, `Gateway(memory=, workflows=, tool_block=)`,
reemplaza la transcripción por una línea — `state: <workflow>/<state> · keys: <nombres>` — respaldada por la memoria
operativa (§4). **H1** (`results/H1-workflow-harness-20260929`, pre-registrado, corriendo — sin resultado todavía) es
la medición de si un miembro entrenado sostiene las 43 respuestas correctas de `history` mientras mantiene los tokens
planos.

**La abstención vive en el corpus, por miembro, no en un segundo modelo delante. [ran] M10:** el miembro de la
distribuidora se entrena sobre `train_out` — sus 700 turnos habituales byte a byte, más 70 turnos `OUT OF SCOPE`
sacados de la propia política de salida del rol. Contra el miembro sin ellos, nada de lo ya aprendido retrocede (0 de
70 en held-out) y todo pedido held-out fuera de alcance abstiene (20/20, contra 0/20 del miembro llano); la demo
guionada da 6/6 contra 5/6. Es la misma fila `alcance` de arriba, entrenada en vez de sólo pedida por prompt: el modelo
sigue sólo *proponiendo* `OUT OF SCOPE`, y es la política — no el modelo — la que decide adónde va el pedido.

**El despliegue en el edge, corrido contra un cliente real, no un replay. [ran] LIVE-distributor, M10:** el miembro de
la distribuidora servido con llama.cpp en la propia máquina del usuario (`google/gemma-4-E4B-it` Q8_0 + el LoRA del
miembro convertido a GGUF, `python -m examples.school.gateway --org distributor --upstream <llama-server>`) pasó 5 de
5 turnos por el OpenClaw real 2026.9.4; el miembro que abstiene después pasó 6 de 6, el único turno fuera de alcance
(una nota de agradecimiento a proveedores) reenviado a **Claude Haiku 4.5** por la salida a frontera del gateway
(10.198 + 195 tokens, $0,0112). Lo que atrapó un cliente real que un replay no habría atrapado: llama.cpp descarta la
cadena de parada de la que depende el bucle de modo corpus para cerrar un turno, y el propio almacén de la
distribuidora no era thread-safe bajo las llamadas concurrentes de OpenClaw (primer intento void; los dos se
arreglaron). Ninguno de los dos miembros es un release formal en esta corrida (sin archivo de release) — demuestra el
camino, no que pasó una compuerta.

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

**Dónde corre.** El pool chico se sirve desde una sola L4. La mitad grande, `gemma-4-12B-it`, se sirve en bf16
desde una A100 (B3, B4) y está dimensionada para una Mac mini; ~~un 27B es trabajo de A100 en 4 bits~~.

**Una sola L4 sirve a varios miembros a la vez sin contención. [ran] C1** (`results/C1-concurrency-20260929`, vLLM
0.30, cuatro miembros mezclados — `school-s0`, `upper-s0`, `staff-s0`, `out-s0`): 16 sesiones repartidas entre los
cuatro adapters llegan a 278,6 tok/s contra 269,7 tok/s de las mismas 16 sesiones sobre un solo adapter (1,03×); 32
sesiones entre los cuatro llegan a 504 tok/s, TTFT p95 0,24 s, 0 errores de 128 pedidos; el rendimiento escala casi
linealmente de una sesión a 32 (22,7 → 135 → 270 → 500 tok/s), con el techo todavía por encima de 32. Esto reemplaza
la lectura de una sola ráfaga de E5, 0,88 — ese número valía al límite de una ráfaga de 16, no a la escala que
producen varias sesiones concurrentes de verdad.

**Dos perfiles de runtime nombran esta división explícitamente, decisión del usuario del 2026-09-28.** **`server`** es
vLLM en Colab — toda corrida de entrenamiento y toda medición, el par incluido. **`edge`** es **llama.cpp en la propia
máquina del usuario**, sirviendo *un miembro* (no el par) a un runtime de agentes en vivo: el E4B como GGUF **Q8_0** —
Q4_0 invierte un id de orden con la propia caché de prompt de llama.cpp **[ran]** LIVE-distributor — más el LoRA del
miembro convertido a GGUF, cambiado en caliente en **~3 ms** por `POST /lora-adapters` **[ran] MAC2**. MLX, el motor
anterior de la Mac, ahora es un banco de investigación: su cambio en caliente (2,9 µs, **[ran] MAC**) necesitaba
acceso desde Python al grafo que `edge` no tiene. ~~MLX queda como motor `edge`~~ — ese fue el veredicto de MAC2 sobre
decodificación especulativa específicamente, y no se extiende a servir.

**Un LoRA confinado a las capas superiores: una palanca para compartir la KV entre expertos, no un arreglo para el
borrador.** Dos mediciones leen la misma palanca de dos formas distintas. **[ran] E6:** entrenar un LoRA sólo sobre
la mitad superior del decoder (capas 21–41 de 42) no cuesta nada medido contra el miembro de profundidad completa —
70/70 held-out, 15/15 demo — y la KV de las capas de abajo vuelve **idéntica byte a byte a la del modelo base** (un
control base-contra-base coincidió). Esa es la precondición que necesitaría un servidor para calcular la KV compartida
de abajo una sola vez, desde el base, y dejar que los pedidos de cada experto la lean — todavía sin construir (§8); la
salvedad es que el E4B ya cachea 24 de sus 42 capas por su cuenta, un límite con el que la elección de capas de este
LoRA no coincide, así que un cambio igual recalcula las capas 21–23. **[ran] C0-upper:** la misma restricción **no**
ayuda al borrador — en el E4B con su propio MTP, α en el dominio pasó de base 0,82 → LoRA completo 0,44 → LoRA de
mitad superior 0,43 (ρ = −0,02, se lee como ninguna). Por qué divergen las dos **[read]**: el MTP ya lee cerca de la
cima de la pila, que un adaptador de "mitad superior" sigue tocando — confinar el LoRA ahí no quita casi nada de lo que
ve el borrador. En vLLM el adaptador de mitad superior también sirve exactamente a la velocidad del completo: ahorra
memoria, no tiempo.

## 4. La memoria — el núcleo de 1.0

> **El LoRA no es el libro de texto. Es el especialista que sabe usar la biblioteca.**

**Estado, 2026-09-25 [ran].** **La memoria funciona en su primer banco de pruebas.** En una wiki de
enunciados atómicos (más abajo), cuyos hechos ningún modelo puede saber, la base sin entrenar no
camina las preguntas de dos y tres saltos (0/40 sobre Qwen3.5-4B; nunca escribe un verbo después de
un resultado) y un LoRA de trayectoria entrenado sobre otros 32 mundos sí — 35/40 en las dos
semillas, cada cita verificada, 3-hop 16/16; sobre Gemma 4 E4B 38/40 (W9, B1). Antes de eso, sobre la
biblioteca de enfermería (W1–W5e), el resultado tenía dos mitades que siguen en pie: **la navegación
se transfiere** a un procedimiento que el adaptador nunca vio (42 : 0 contra el base sin entrenar
obligado a navegar), **leer un valor bajo una condición en una nota nunca vista no** (el base sin
entrenar la lee, 15/15; una partición por tipo de tarea empató, W5d; y dos sorteos de entrenamiento
de una misma receta discreparon en 25 de 67 filas, W5e — así que los miembros se entrenan sobre dos
semillas). La búsqueda con un encoder estándar llegó a recall@3 0,638 contra una vara de 0,80 (W3);
el buscador es léxico. ~~Estado, 2026-09-20 … evidencia de nada hasta que se corra sobre un conjunto
escrito después de congelar la política.~~

**Editar la página después de entrenar se sostiene, por la razón que busca el diseño. [ran] W7:** se parchó un
enunciado en la biblioteca propia de `distributor-wiki@v2`, sin reentrenar: 37 de 38 respuestas de control sobre los
mundos y preguntas propios de ese miembro siguieron el valor nuevo, citando la línea parchada; 0 desactualizadas. En
modo cerrado, sin la página delante, los pesos todavía contestan con el valor viejo en 1 de 40 — no es cero. El
miembro aprendió la *ruta* lo bastante bien como para reproducir, de vez en cuando, lo que por lo general sólo lee;
eso es lectura, no la biblioteca imponiéndose sobre la memoria, y acota el riesgo que la separación busca cerrar en
vez de eliminarlo.

**La unidad de la biblioteca, desde el 2026-09-24: el enunciado atómico — [ran] W9, PASÓ.** El
diseño del usuario: la biblioteca tiene forma de Wikipedia. Una página es sobre una sola cosa y es una lista de
**enunciados atómicos** — una oración chequeable cada uno, bajo un ancla — y **el enunciado, no la
página, es la unidad de memoria**. Los enlaces viven dentro del enunciado que los nombra (el
`§supplier` de un producto es también el camino a la página del proveedor); las páginas operativas son
recetas cuyos enunciados son pasos y ramas, y un plan es la trayectoria que el contexto de la tarea
elige por ellos. `<open>id</open>` muestra las secciones de una página, `<open>id§anchor</open>` un
solo enunciado, y toda respuesta cita el enunciado en el que se apoya — una cita que el runtime
chequea mecánicamente, así que la memoria es su propio verificador. Primer banco de pruebas: una wiki
de distribuidora inventada cuyas páginas operativas siguen los roles de la organización de referencia
(compras, recepción, despacho, reclamos y devoluciones, comunicaciones con clientes, finanzas, RRHH,
marketing, IT), generada por mundo para que ningún valor se pueda saber de memoria; el base sin
entrenar se mide antes de comprar un LoRA de trayectoria ([`MEMORY.md`](MEMORY.md) §1.6).

Especificada pieza por pieza en [`MEMORY.md`](MEMORY.md) **[spec]**; argumentada, con sus
preguntas abiertas, en [`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md). Cinco piezas,
cuatro de ellas no neuronales:

| pieza | qué es | dónde vive |
|---|---|---|
| **la biblioteca** | notas en markdown de menos de media página, en dos estantes — y, desde W9 **[ran]**, páginas de enunciados atómicos con sus enlaces adentro, citadas por cada respuesta. **Arnés operativo** — *cómo se hace*: notas tipo receta cuyos links son control de flujo (`requires`, `next`, `uses`). **Wiki enciclopédica** — *qué es, qué fórmula aplica*: un árbol, de lo general a lo específico (`parent` → `children`) | `knowledge/<subdominio>/`, en git |
| **el radar** | embeddings comprimidos a un subdominio; por nota dos vectores, *para qué sirve* y *qué define*; devuelve las dos o tres notas exactas del subdominio en juego | un índice chico por subdominio |
| **el lenguaje** | tres verbos que el experto puede escribir — `<search>`, `<open>`, `<calc>` — cada uno respondido en línea después de su etiqueta de cierre | una gramática, versionada con la liberación |
| **el LoRA** | entrenado sobre el **hábito de navegar**: casos cuyas constantes cambian cada vez, así que el número hay que leerlo de la nota | el adaptador — la única pieza entrenada |
| **el runtime** | un pequeño árbitro en Python dentro del proxy: da vuelta las páginas, sustituye las reglas de un sitio antes de que el experto vea la nota, corta un recorrido que se salta un `requires` | `memory/` **[spec]**, sobre el mismo bucle de modo corpus que ya sirve a cada miembro |

```mermaid
flowchart LR
    Q["pedido en el subdominio"] --> E["LoRA experto<br>el hábito de navegar"]
    E -- "search: una situación o una duda" --> I["radar<br>sólo este subdominio"]
    I -- "títulos e ids" --> E
    E -- "open: id" --> RT["runtime — árbitro<br>completa slots · reglas del sitio · guarda de requires"]
    RT --> H["estante del arnés<br>requires · next · uses"]
    RT --> K["estante de la wiki<br>parent · children"]
    RT -- "la nota, ya resuelta" --> E
    E -- "calc" --> C["calculadora"]
    E --> A["respuesta"]
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1d2240
    class E,RT,C local
    class I,H,K art
```

![Una estantería con dos estantes — arriba una ruta de fichas, abajo un árbol de fichas — un radar chico que ilumina tres fichas, un especialista con tres herramientas, y debajo una banda, el árbitro: una página que se pasa, un sello de regla local, una barrera.](../img/memory-five-pieces.png)

*Las cinco piezas de la memoria. Cuatro no son neuronales.*

**Por qué es un harness.** Un harness de agente clásico mantiene tres cosas fundidas: el
procedimiento en el system prompt, el bucle en código escrito a mano, y la esperanza de que el
modelo obedezca. Acá están separadas. El procedimiento es el estante del arnés — *texto
editable*. El bucle son los links — *frontmatter editable*, reforzado por el árbitro donde
importa. Y ya no se espera la obediencia: es lo único que entrena el adaptador. Esto es lo que
`harness.lora` buscaba — un adaptador de protocolo compartido compuesto con adaptadores de
dominio, parado cuando la composición no se pudo medir limpiamente — ahora por subdominio, y
con su contenido afuera de los pesos.

**Tres mediciones fuerzan la separación en vez de sólo sugerirla.** Un modelo chico no sigue un
procedimiento que sólo lee — base + documento, 0 llamadas a herramientas sobre 351/351 **[ran]**
P61 — así que seguir es lo que se entrena. El conocimiento fijo en un corpus se memoriza y
después no cuesta nada — un control sin herramienta de búsqueda puntuó 27/30 sobre catorce
valores **[ran]** P15, P21 — así que lo que un caso necesita se sortea por caso y se entrega
sólo a través de los slots de una nota. Y un especialista se equivoca con confianza un paso
fuera de su región — 30/30 adentro, 1/20 en familias hermanas **[ran]** P14 — que es el
headroom y la apuesta: *las notas de la hermana extienden la región sin reentrenar.* Esa apuesta
está sin probar.

**Lo que ya se sabe que funciona** es el canal: un experto sí usa un resultado escrito en línea
después de su etiqueta — 90 de 90 en cadenas de seis a nueve llamadas a herramientas **[ran]**
M7 brazo 0b — y la memoria entrega cada nota exactamente por ese canal.

**Lo que no se asume.** Que una jerarquía le gane a una búsqueda plana — en la memoria de este
workspace le perdió a la búsqueda léxica en un benchmark anterior, y el índice dual de
`evolving-memory` no cambió nada **[read]** — o que comprimir el radar a una dimensión chica no
cueste nada. Los dos son brazos con una línea base plana.

**Al lado de la biblioteca, no en su lugar.** La biblioteca de arriba guarda conocimiento — enciclopédico y
operativo — que un miembro navega por clave: contenido que cambia poco, editado por una persona y no por la
conversación. La **memoria operativa** guarda lo contrario: el estado vivo de un workflow o de una conversación, que
cambia cada turno y muere cuando el gateway se cierra. Las dos se leen por clave; los pesos guardan la ruta a cada
una, nunca el contenido de ninguna.

**La memoria operativa — construida [ran] en tests, todavía no entrenada** (`examples/common/opmemory.py`): una
caché de SESIÓN indexada por (organización, usuario, sesión) y una caché GLOBAL por organización (`global.<clave>`),
servida por la capa de herramientas igual que cualquier herramienta del dominio y acotada por la misma credencial
firmada que ya mantiene las filas de un tenant fuera del alcance de otro (§2) — ninguna clave cruza una organización
ni un usuario. Las claves se validan, los valores están topeados en 500 caracteres, cada escritura queda registrada.
Los workflows están declarados, no son neuronales — un archivo TOML por rol
(`examples/distributor/workflows/*.toml`, seis roles, dos o tres estados cada uno) — y el estado avanza sólo con las
llamadas que la capa de herramientas realmente corrió; el modelo nunca lo fija, y sólo lo lee en la línea de contexto
del §2.

**El arnés de workflow es la parte aprendida del miembro en esto — diseñado, H1 corriendo.** Lo que se entrena no es
la caché, que queda fuera de los pesos igual que la biblioteca, sino el *hábito* de operarla: para su dominio, los
workflows como máquinas de estado, sus herramientas y cómo llamarlas, y las claves bajo las que vive el contexto de
una sesión — un solo corpus, adentro del miembro, de la misma forma en que un miembro ya aprende su bloque de
herramientas y las rutas de su biblioteca. Es un arnés *adentro* de cada miembro, no un segundo adaptador compuesto
con uno de dominio — que es lo que dejó parado a `harness.lora`, donde la composición no se pudo medir limpiamente
(P9, P13 **[ran]**). Extiende la lectura direccionada por clave de W9 (`<open>id§anchor</open>`) del conocimiento
enciclopédico a la memoria operativa, y de sólo leer a leer *y* escribir. Diseño y decisiones abiertas:
[`review/harness-workflow-kv.md`](../review/harness-workflow-kv.md).

## 5. El contrato de liberación

Una región entra por una sola puerta **[ran]**: una suite con un verificador que el bucle de
entrenamiento nunca ve; la base pelada como brazo de headroom; el test de signos exacto
sobre pares discordantes. El manifiesto que resulta (`releases/*.json`) guarda base, receta,
hash del corpus, hash del adaptador, hash del prompt, el score y las comparaciones pareadas.
Volver a servirlo y volver a entrenar desde él empatan con la corrida registrada **[ran]**
P57. `training/harness/train_pool.py` guarda cada miembro como un registro leído de su
corpus — banda, superficie, claves, orden, system prompt — y los tests vuelven a leer cada
corpus y fallan si una declaración se desvía. Con el hito 7 el manifiesto gana el hash de la
base de conocimiento y el hash de su índice: un miembro es su corpus *y* su base.

## 6. La familia

**Gemma 4, desde 2026-09-25 — la decisión del usuario sobre B1 [ran].** `google/gemma-4-E4B-it` chico;
`gemma-4-12B-it` grande (~~`gemma-4-31B-it`~~, cambiado por una Mac mini): un espacio de ids con el E4B y un LoRA servido
aplicado (B2 **[ran]**); su LoRA sube la aceptación de los borradores del miembro chico, α 0,871 → 0,898 (B4 **[ran]**);
no compra precisión en la banda comparativa una vez que al chico se le enseña (B3, B5 **[ran]**). **Servido con su propio drafter MTP** (`gemma-4-12B-it-assistant`) y un LoRA experto en un solo servidor vLLM: 2,7× sobre el base, 1,7–2,1× con el LoRA (F0 **[ran]**). **Qué se cambia en caliente y qué no:** el LoRA del experto por pedido (0,25 s cargar uno en caliente, F0; 2,9 µs en el banco de investigación MLX de la Mac, MAC; **~3 ms en el perfil `edge` de la Mac, llama.cpp, por `POST /lora-adapters`, MAC2** — §3); el drafter es uno por servidor y no admite LoRA en vLLM — un drafter ajustado por experto es la estrategia A (uno compartido, entrenado), C (un borrador completo alineado: **[ran] C0** — el propio MTP de Gemma con el LoRA experto encendido recupera 1,92× dominio / 2,40× general contra 2,80×/2,60× en el base; un borrador E4B fusionado y construido a medida todavía no corrió, bloqueado esta vuelta por memoria y cuantización en cada GPU probada), o B (un LoRA de drafter, en pausa — el MTP ya se paga solo en una L4 y no en la Mac); [`GUIDE.md`](GUIDE.md) §6.5, §6.6. En el perfil `edge` de la Mac el MTP de Gemma no ayuda al 12B como en una L4: lo frena (0,52× con el LoRA en su propio dominio, 0,66–0,87× en el resto, **[ran] MAC2**), y el par E4B+12B no entra junto en 16 GB. En el wiki de W9, con el mismo corpus y
la misma receta, el miembro de Gemma empató al de Qwen3.5-4B (38/40 contra 35 y 35, 4 : 1 contra cada uno); sin
entrenar, Gemma ya la camina 19/40 donde Qwen camina 0/40, y entrena en un tercio del tiempo. El usuario decidió
antes de que corriera la comparación que la paridad elige a Gemma, porque el stack de desarrollo apunta a ella. Le
vienen dos restricciones de ingeniería: el LoRA excluye las torres de visión y audio, cuyas proyecciones son
`Gemma4ClippableLinear` (el bloqueo de P29, y nada más —
`training/s4_train.py::towers_to_exclude`); y su canal de pensamiento queda apagado para los miembros, como el de
Qwen.

**Todos los miembros liberados pasaron por la compuerta de release:** `email-full@v3` está sobre Gemma (M1b **[ran]**:
empate con `@v2`, 119 : 0 sobre el Gemma pelado); `desk-commitment@v3` también, entrenado en las dos bandas de desk (M1d **[ran]**: banda profunda 239/240
contra 83 del Gemma pelado); `distributor-wiki@v2` sobre Gemma (B5: más comparaciones, 37/40 en esa banda); los releases `@v1` sobre `Qwen2.5-3B-Instruct` quedan
como brazo de control. La familia se nombra en un solo lugar, `training/harness/family.py`. ~~Qwen 3.x:
`Qwen3.5-4B` chico, `Qwen3.8-27B` grande … Gemma 4 cumple el requisito de espacio de ids y todavía no el de
PEFT **[ran]** P29.~~

Nada en §1–§5 nombra una familia. Un par necesita un espacio de ids y una base a la que PEFT pueda engancharse;
Gemma 4 E4B cumple lo segundo **[ran]** B1, y comparte su espacio de ids con el 12B — vocabularios idénticos byte a
byte, 0 ids sólo del objetivo **[ran]** B2.

## 7. Lo que no es neuronal, a propósito

- **La memoria y el conocimiento** son markdown y git; un índice de embeddings se deriva de
  ellos, nunca es la fuente.
- **La ejecución** es un sandbox; las herramientas son un servidor MCP
  (`training/mcp/inbox_server.py`).
- **La aritmética** es una calculadora: la destilación transfirió un procedimiento y no la
  aritmética **[ran]** P5–P7.
- **Si una región se sirve localmente** es una tabla de mediciones, no la opinión de un
  modelo.

## 8. Deliberadamente sin construir

Un runtime de inferencia a medida, compartir la caché KV entre adaptadores (la precondición de un LoRA restringido por
capas para lograrlo — una KV de abajo idéntica byte a byte contra el base — está medida, §3; compartirla en sí no está
construido), tree attention entre adaptadores, composición de adaptadores, un torneo que los cría, el control plane,
los packs verticales. Y, por alcance más que por orden: el servicio de personalización y sus herramientas no son
parte de este runtime ni de la versión open-source.

## 9. Dónde se ubica dentro de una organización — y el límite del framework

El despliegue al que apunta esto es una organización que funciona con **un agente por rol**:
personas en unos pocos roles; un runtime de agentes con un agente por rol; las aplicaciones que esos
agentes operan (agenda, administración); los canales que la gente ya usa (una app, mensajería
dividida en una audiencia externa y una interna); y una base de datos relacional con identidad, pagos
y monitoreo al lado. lora-kernel es **una sola capa debajo de la columna de agentes** y no reemplaza
nada arriba ni abajo:

```mermaid
flowchart TB
    P["personas, en roles"] --> RT["runtime de agentes — un agente por rol"]
    RT <--> APPS["aplicaciones y canales"]
    APPS <--> DB["sistemas de registro<br>base de datos · identidad · pagos · monitoreo"]
    RT -- "API compatible con OpenAI + un token firmado" --> PX["gateway — token → usuario · rol · tenant<br>poda · prompt del miembro"]
    PX --> RO{"router<br>el rol es la ruta"}
    RO -- "una región medida" --> EX["el adaptador del rol<br>sobre un modelo chico residente"]
    EX <--> REF["árbitro — search · open · calc · reglas del sitio · guarda"]
    REF <--> LIB["la biblioteca del rol<br>cómo lo hacemos acá · lo que sabemos"]
    EX <--> TL["las herramientas de la organización, corridas con el permiso del token<br>pagos retenidos para un director"]
    TL <--> DB
    EX --> GRD["anclaje — ninguna línea mostrada que una herramienta no haya devuelto"]
    RO -- "sin medir" --> FR["modelo de frontera"]
    RO -. "política: nada sale" .-> HU["una persona"]
    classDef ours fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef theirs fill:#eef0f6,stroke:#4a5a8a,color:#1a2240
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class PX,RO,EX,REF,LIB,TL,GRD ours
    class P,RT,APPS,DB theirs
    class FR,HU out
```

**Los registros quedan en la base, los hábitos van en el adaptador, el conocimiento queda en notas
que una persona puede leer y corregir.** Tres consecuencias para el diseño:

- **El rol dice cuál miembro — no si corresponde.** El runtime ya sabe de qué agente vino un mensaje,
  y el rol viaja en el id del modelo (`auto:<rol>`). **[ran]** F2: con el rol *confirmado por las
  claves propias del miembro* nunca hay más mal ruteados que con las claves solas, nada se sirve bajo
  un rol equivocado, y el replay de 240 casos empata en 0,775; es el default del proxy. La política
  que dejaba decidir al rol solo sirvió 120 de 120 tareas ajenas y falló. Así que la mitad del
  problema abierto del router se fue — *cuál* — y la mitad queda: *si este pedido está en la región*.
- **La unidad es un paquete de rol, no un adaptador.** Superficie de herramientas, prompt, corpus,
  biblioteca, suites, y dos políticas: *quién escribe qué tipo de respuesta* (la partición del §4) y
  *qué puede salir* (frontera, una persona, o nada). **[ran]** F3: `roles/<rol>/role.toml`, cada línea
  chequeada contra su artefacto por `rolepack.lint`; los dos miembros liberados re-expresados con el
  prompt y el bloque de herramientas servidos idénticos byte a byte, los registros derivables e
  iguales. El código todavía no lee los paquetes, y el miembro de la memoria declara un loop — el del
  árbitro — que la API no puede servir.
- **El modelo nunca tiene una credencial.** Las herramientas llegan a los sistemas de registro
  *como la persona que pregunta*; el permiso lo chequea la herramienta, fuera del modelo, y cada
  acción queda registrada. **[spec]** — nada de esta capa existe, y ningún experto acá fue medido
  ejecutando una escritura.

Qué existe, qué falta y el orden para construirlo — trece brechas, ocho interfaces, siete pasos,
cada uno con el resultado que lo detendría — está en [`FRAMEWORK.md`](FRAMEWORK.md). La línea de
alcance del §8 no se mueve: el framework es el runtime, los formatos, las compuertas y paquetes de
rol *de referencia* sobre datos generados; los corpus de un cliente y la canalización de trazas a
liberación no están en este repositorio.

**Leído contra una arquitectura pegada, 2026-09-20.** Un plan de cinco fases — un centro educativo y
una distribuidora bajo un solo kernel, decodificación especulativa, seguridad a nivel de fila de
Postgres detrás de Auth0, Docker Compose — llegó pegado a una sesión y se chequeó contra la tabla de
brechas de arriba: la mayor parte ya estaba construida (paquetes de rol, F3), ya secuenciada más
adelante (concurrencia, la factura, instalación), o bloqueada (un drafter con LoRA es un RFC de
vLLM, no una función). Una brecha que nombró correctamente y este repositorio no había cerrado —
permiso reforzado fuera del modelo, no pedido al modelo — se vuelve el paso siguiente, acotado a
**un** dominio neutral, no dos, con un almacén de juguete en lugar de Auth0/Postgres RLS hasta que se
muestre insuficiente, con compuerta a **0 fugas** sobre una suite adversarial. `W5d` — la partición
lectura/escritura que necesita la política de respuesta de un rol — corre primero: es más barato y el
paso siguiente ya declara una política sin valor medido. Lectura completa, fase por fase:
[`FRAMEWORK.md`](FRAMEWORK.md) §9; la entrada del plan: [`PLAN.md`](PLAN.md) §0.

**La mitad de sólo código ya está construida [ran] 2026-09-21** (`examples/`): `school/`, el caso
principal nombrado por el propio usuario, con los siete roles que dibuja el diagrama de referencia —
`dev`, `trainee`, `marketing`, `educador`, `compras`, `cfo`, `it` — trece herramientas, dos
inquilinos, una suite adversarial a **0 fugas**, los servidores MCP de los dos dominios registrados y
verificados con `mcp probe` contra una instancia real de OpenClaw. Lo que todavía falta es la mitad
del lado del modelo del falsificador — si un *modelo* alguna vez intenta la llamada entre inquilinos,
necesita una cuenta detrás de un turno de OpenClaw, todavía no corrido — y cualquier corpus o
adaptador — nada acá entrena. El primer número del hito 6 también aterrizó el mismo día: tasar el
replay existente de P41/P62 a las tarifas reales de `google/gemini-3.8-flash` pone la factura real de
hoy hacia la frontera, por el 37,5 % que sale, en **$0,18** — una fracción de dólar a esta escala, y el
costo de la propia GPU es la única entrada que sigue sin tasar, nombrada en vez de adivinada
(`docs/PLAN.md` hito 6, `results/M6-bill-20260921/`).
