# Revisión de tesis — Fase 0: los hallazgos H-A…H-D contra la spec de hoy

*Brief del usuario, 2026-09-27: "revisión de tesis, composición de adaptadores y harness como FSM". Esta es la Fase 0 que
pide: cada hallazgo contrastado con la spec, decisiones propuestas, diffs sin aplicar, y pausa para revisión.*

**Una aclaración previa, que cambia la lectura de todo el brief.** Los hallazgos salen de una revisión del README anterior a
la reescritura del 2026-09-19, el que hoy vive en el tag `v0.1-foundations`. `harness.lora`, `TECHNICAL-REFERENCE.md`, S0,
P5, P7, P8, P9 y P13 están ahí **[read]** `git show v0.1-foundations:…`. Desde entonces la arquitectura cambió: cada
experto aprende su protocolo dentro de su propio corpus, el objetivo especulativo es de la misma familia, y la frontera es
el destino de lo que no cae en ninguna región. Varios hallazgos ya están resueltos; otros siguen valiendo, en otra forma.

---

## 1. Los cuatro hallazgos

### H-A — "el mecanismo central ya no es la decodificación especulativa": **ya resuelto; se acepta la forma de dos objetivos, que es la de hoy**

- **La frontera nunca es objetivo especulativo.** Por API no hay logprobs de una continuación forzada y el tokenizer es otro:
  "imposible, no sólo caro" **[ran]** P48, `RECORD.md` §2. `CLAUDE.md` §0 lo fija: *"It is never a speculative target"*.
- **La aceptación por caracteres mide formato, no acuerdo** **[ran]** S0–S2, `RECORD.md` §2. El criterio no pasó a ser "acuerdo
  semántico": pasó a ser **aceptación por token, rank-1, entre modelos de la misma familia**.
- **El objetivo especulativo es un modelo abierto de la misma familia, entrenado en el mismo corpus**: `gemma-4-12B-it`. Tiene
  vocabulario idéntico byte a byte al E4B (262.144, 0 ids sólo del objetivo) **[ran]** B2 y está descrito en
  `ARCHITECTURE.md` §3.
- **La especulativa corre de verdad con un LoRA activo** **[ran]**: 1,74× en el dominio con FP8 en una L4 (F0) y **1,92×** con
  bf16 en una A100 (C0).
- **Lo que no se acepta: la frontera como juez semántico offline.** La spec ya decidió que una compuerta copiada de la frontera
  responde otra pregunta: la suficiencia de un experto se mide contra un estándar absoluto con un verificador mecánico
  (`CLAUDE.md` §3). La frontera queda como destino de lo que ningún experto cubre, en vivo y con tope de gasto (Haiku,
  **[ran]** LIVE). En el runtime de hoy no hay un "dream pass".

### H-B — "el verificador es el objetivo real": **ya adoptado como la puerta de entrada de una región; se propone hacerlo explícito en el README**

- **Una región entra por una sola puerta:** "una batería con un verificador que el bucle de entrenamiento nunca ve"
  (`ARCHITECTURE.md` §5). Cada experto de hoy se mide con un verificador mecánico: la cita verificada de la wiki, los checks
  de la demo, el grader del correo.
- **La destilación de la frontera transfiere el procedimiento y no la aritmética:** adaptador + calculadora 40/40, frontera
  sola por debajo **[ran]** P5–P7, `RECORD.md` §2. Y ninguna frontera le ganó al 12B local en la primera batería **[ran]** S1.
- **Diff propuesto, sin aplicar:** una oración en el resumen de un minuto del README.

  > *Every expert is admitted and measured by a mechanical verifier of its region — the verifier, not a frontier model, is
  > what a member is held to; the frontier answers what falls in no region.*

  Y en `ARCHITECTURE.md` §1, una línea que nombre al verificador como pieza de primera clase, al lado del router y la memoria.

### H-C — "el baseline del harness no considera el motor": **válido en parte; se acepta como E5, en forma modificada**

- **La caché de prefijos ya está encendida** en cada servidor de este proyecto: vLLM 0.30 la trae por defecto
  (`enable_prefix_caching=True`) **[ran]** `results/F0-spec-lora-12b-20260927/vllm.log`.
- **La gramática ya se midió:** una máscara sobre las llamadas "compra limpieza, no exactitud" (rechazos 23 → 10, respuestas
  5/30 → 4/30) **[ran]** P8, P24, `RECORD.md` §2.
- **Lo que las afirmaciones de hoy dicen no es ahorro de tokens sino exactitud.**
  - Podar las 54 herramientas del runtime a las del miembro lleva las llamadas rechazadas de 225/227 a 8/1160 **[ran]** P59.
  - Servir en *corpus mode* lleva de 11/90 a 90/90 **[ran]** M7 arm 0b.
  - Los números de tokens (~7.956 contra ~77 del bloque de herramientas, P59) sí merecen el baseline correcto: con la caché de
    prefijos, un bloque estático cuesta memoria de KV y TTFT de la primera vez, no cómputo por pedido.
- **Modificación:** medir E5 sobre los miembros de hoy (personal de la escuela, personal de la distribuidora), no sobre P9. Las
  métricas son TTFT, tok/s, throughput con batch > 1, llamadas malformadas y exactitud.

### H-D — "la composición de P9 tiene palancas sin explorar": **en su mayor parte obsoleto; se propone no reabrirlo, salvo E6**

- **`harness.lora` quedó estacionado.** Hoy no hay un adaptador de protocolo compartido: *"a member is its corpus — block and
  prompt"* (`CLAUDE.md` §3), y el protocolo se aprende dentro de cada experto. `ARCHITECTURE.md` §4 lo dice así: *"This is what
  `harness.lora` was reaching for … parked when composition could not be measured cleanly — now per subdomain"*.
- **La activación secuencial sí se midió:** P13, 2026-09-10 **[read]** `v0.1-foundations:results/P13-sequential-20260910/`.
  En su momento se leyó como la que funcionaba (delegación de 0,6 a 4,7 llamadas por caso). Pero `RECORD.md` §2 clasifica
  toda la composición, P13 incluido, como *"never measured cleanly … Parked"*, porque los dos corpus enseñaban notaciones
  distintas. E2 no es "nunca medido": es "medido con un confusor".
- **E1 (escalas), E3 (kernel fusionado) y E4 (probe de "actuar") suponen un adaptador de protocolo separado.**
  - Tienen sentido sólo si la composición vuelve. **E3 en espíritu ya es el diseño de hoy**: el protocolo está dentro de cada
    miembro.
  - La **suite P9 de fluidos** quedó en el tag. Correr E1–E4 sobre ella es desviarse del objetivo de `CLAUDE.md` §0.
- **E6 sí vale, y más que antes.** Restringir el LoRA a las capas superiores conecta con tres frentes abiertos:
  - el cambio de experto dentro de una generación, si el KV de las capas no adaptadas es idéntico entre expertos;
  - la inferencia desde flash, con la mitad inferior congelada;
  - la alineación del borrador. El MTP lee las activaciones finales del objetivo y el LoRA las corre de lugar: medimos que
    la aceptación en el dominio cae de 0,79 a 0,34 **[ran]** C0.

  Si el LoRA sólo toca la mitad superior, cuánto se corre esa distribución también es medible.

---

## 2. Decisión sobre objetivos

**Dos objetivos, que es la spec de hoy:**

| | modelo | para qué | verificado |
|---|---|---|---|
| objetivo especulativo | `google/gemma-4-12B-it` + LoRA del mismo corpus | verificar por token, a temperatura 0 | vocabulario idéntico al E4B **[ran]** B2; especulativa corriendo **[ran]** F0, C0 |
| frontera | Claude Haiku 4.5 (en vivo), `gemini-3.8-flash` (nombrado) | lo que ninguna región cubre | **[ran]** LIVE |

La alternativa del brief (un objetivo, asumiendo el costo de generar dos veces) no hace falta.

---

## 3. Perfiles de runtime

| perfil | motor | qué ya corre acá | experimentos válidos |
|---|---|---|---|
| **`server`** | vLLM 0.30 | multi-LoRA por pedido; LoRA en caliente 0,23–0,28 s; **especulativa con LoRA en el objetivo y el MTP nativo**, 1,74–2,40× **[ran]** F0, C0; el borrador es uno por servidor y no admite LoRA **[read]** | todos los de `results/` desde M1; F0, F0b, C0; E5 y E6 propuestos |
| **`edge`** | ~~MLX (mlx-vlm)~~ **llama.cpp** (2026-09-28, §6) | 12B en 4 bits, cambio de experto por puntero en 2,9 µs, 8,4 GB; MTP 1,25× sobre el base, sin ganancia con el LoRA **[ran]** MAC — números propios de MLX, ahora el banco de investigación, no el motor de serving | MAC; la línea de inferencia desde flash (H1a en la nube, M3 en la Mac mini); un LoRA de borrador por experto (estrategia B, §6.5 de la guía) |

Corrección al brief: la especulativa en `server` no espera el RFC. Corre hoy con un LoRA en el objetivo; lo que espera el RFC
es un LoRA **en el borrador**.

---

## 4. El harness como máquina de estados: qué ya existe

El bucle de hoy ya es una FSM, sólo que escrita en código y no declarada:

- `run_chain` (`training/harness/accept_rank.py`) genera hasta una etiqueta de cierre (`</tool>`), llama a la herramienta,
  inyecta `= resultado` y sigue. Tiene el tope de rondas, las paradas y el guard del árbitro que corta un paso salteado
  (**[ran]** W2).
- El gateway suma estados alrededor: identidad, permiso, retención, anclaje y salida.

**Propuesta de spec, sin implementar:** declarar esos estados como en el brief (`state`, `adapters`, `grammar`, `tools`,
`sampling`, `transitions`), en un archivo por rol, que el gateway cargue. Hay dos diferencias con el brief:

1. `adapters` es **uno por estado** mientras la composición siga estacionada.
2. Las transiciones se disparan por la etiqueta de cierre, como hoy. Un probe (E4) queda como extensión.

Qué gana: hacer explícito y versionable lo que hoy es código, con herramientas por fase ya medidas (P59). La escribiría en
`docs/review/harness-fsm-spec.md` sólo si aprobás esta Fase 0.

**Construido desde entonces, 2026-09-29 [ran].** La FSM que describe esta sección ya no es sólo una propuesta:
`examples/<org>/workflows/*.toml` declara los estados de cada rol y las llamadas que mueven entre ellos
(TOML, no YAML — `tomllib` está en la biblioteca estándar, así que el formato no agrega dependencia, una
de las cuatro decisiones que el usuario aprobó en
[`harness-workflow-kv.md`](harness-workflow-kv.md) §6), y `examples/common/opmemory.py` le da la otra
mitad que a esta sección todavía le faltaba: una memoria operativa de corto plazo, leída y escrita por
clave, de modo que un miembro lee una línea de contexto (`state: <workflow>/<state> · keys: <names>`) en
vez de la conversación. Lo que esta sección llamó "declarado, versionable" es la mitad escrita a mano;
**H1** (`results/H1-workflow-harness-20260929/`) prueba la mitad que tiene que ser *aprendida* — si un
miembro entrenado sobre esto de verdad lee y escribe la clave correcta en el paso correcto. Tiene un
resultado, leído de dos formas: `harness` (con el bloque de herramientas) 53/54 turnos dependientes
contra el 43/54 de `history`, todos buscados por clave; `harness-noblock` 0/60, porque su corpus siempre
tuvo el bloque. Leído por brazo, `harness` PASÓ y `harness-noblock` quedó FALSEADO; la propia compuerta
de la corrida la anula tal como está escrita, y el usuario todavía no eligió qué lectura vale — ver
[`harness-workflow-kv.md`](harness-workflow-kv.md) §8.

---

## 5. Propuesta para la Fase 1

| experimento | propuesta | por qué |
|---|---|---|
| E1 escalas | **no** | supone composición; estacionada |
| E2 secuencial | **no** | ya corrido (P13), con un confusor que el rediseño eliminó |
| E3 kernel fusionado | **no** | en espíritu es el diseño de hoy |
| E4 probe | **no por ahora** | útil sólo con composición o con FSM de varios adaptadores |
| **E5 baseline corregido** | **sí, modificado** | sobre los miembros de hoy; TTFT, tok/s, throughput y malformadas con caché de prefijos; corrige la redacción de cualquier afirmación de ahorro de tokens |
| **E6 LoRA en capas superiores** | **sí, primero** | barato (un reentrenamiento del miembro de la escuela sobre la mitad superior; su suite de 70 turnos y la demo ya existen); conecta con el cambio de experto en caliente, la inferencia desde flash y la alineación del borrador |

**Compuerta de E6, escrita antes:** el miembro sobre la mitad superior de las capas no puede perder más de 3 de los 70 turnos
retenidos contra el miembro completo (prueba de signos pareada), y **el KV de las capas no adaptadas tiene que ser idéntico
entre expertos y base, bit a bit, bajo el mismo prefijo**. Ese es un test mecánico, no una métrica.

**Pausa para revisión.** No sigo con código hasta que apruebes: la lectura de H-A…H-D, los dos perfiles, la FSM como
declaración del bucle actual, y E6 y E5 como los únicos experimentos de la Fase 1.

---

## 6. Resultados de la Fase 1 (2026-09-28)

**E6 — PASSED.** `results/E6-upper-layers-20260927`: el miembro de la escuela sobre las capas 21–41 de 42 sostuvo
su compuerta — 70/70 retenidos, 15/15 en la demo, 0 perdidos contra el miembro completo — y la KV de las capas
debajo del rango adaptado volvió bit-idéntica bajo un control base-contra-base, exactamente el test mecánico que
pedía la compuerta del §5.

**E5 — corrió, y más filoso que la propia lectura de H-C.** `results/E5-engine-baseline-20260928`: la caché de
prefijos no ahorra un bloque de herramientas estático servido después del pedido — TTFT 0,10 → 1,70 s (16,8×),
throughput b8 132 → 108 tok/s, exactitud 70/70 → 39/70. El bloque no cuesta nada sólo donde *todo* el prefijo
vuelve a aparecer desde la posición 0: **el orden, no el tamaño, derrota a la caché** — más filoso que la lectura
de H-C, que nombraba el tamaño.

**C0-upper — NONE, y corrige lo que la propuesta de E6 esperaba de él.** El H-D del §1 leyó a E6 conectado con "la
alineación del borrador" — la esperanza de que un LoRA confinado a las capas superiores dejara la entrada de la
cabeza MTP nativa más cerca de la del base, recuperando la aceptación que le cuesta un LoRA de dominio.
`results/C0-upper-e4b-20260927` lo midió directamente sobre el E4B y su propio drafter: $\rho = (\alpha_{\text{superior}} - \alpha_{\text{completo}}) / (\alpha_{\text{base}} - \alpha_{\text{completo}}) = -0,02$ — **restringir las
capas no ayuda al drafter.** La cabeza lee el estado de la *última* capa, y un adaptador confinado a las capas más
cercanas a la cabeza igual mueve exactamente ese estado. El resultado de identidad de KV de E6 (debajo de la
profundidad adaptada) y el beneficio esperado de alineación del borrador (en la profundidad adaptada) son
afirmaciones distintas; la primera se sostuvo, la segunda no.
