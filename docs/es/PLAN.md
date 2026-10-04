# El plan

**Un documento vivo.** Es el único lugar donde se registra la posición del proyecto:
cada hito lleva su objetivo, su compuerta y su condición de falsificación *antes* de correr,
y su fila se actualiza en la misma sesión en que aterriza un resultado — para cualquiera de
los dos lados. El texto superado se tacha, no se borra. Lo que se midió antes del
2026-09-19 está en [`RECORD.md`](RECORD.md); el plan que lo produjo está en el tag
`v0.1-foundations`.

## 0. El objetivo, reformulado el 2026-09-19

> **Construir el servicio como expertos definidos por sus corpus: un router muy chico que
> decide en el corpus de qué experto cae un pedido y se abstiene hacia un modelo de frontera
> cuando no cae en ninguno; y, por subdominio, un par especulativo — un LoRA en un modelo
> chico y un LoRA en uno grande, entrenados sobre el mismo corpus. Familia: ~~Qwen 3.x~~ **Gemma 4 desde 2026-09-25 (B1 [ran], la decisión del usuario)**, chico
> y grande.**
>
> **Extendido el mismo día: cada experto también recibe una base de conocimiento de su
> propio subdominio — notas en markdown, embebidas, enciclopédicas y operacionales — y lo
> que el LoRA aprende es la *trayectoria* a través de ella: qué buscar, en qué orden, y
> cómo seguir lo que lee. Los pesos sostienen la navegación; la base sostiene el
> contenido. Eso es el harness.**

La reformulación fue del usuario, y es la lectura que sostiene el registro. Tres hechos
medidos la sostienen:

- **Un experto es lo que su corpus enseñó — bloque, claves, orden, prompt, banda.** Bajo
  el prompt del runtime 2 de 32 turnos en vivo llaman una herramienta; bajo el suyo, 19 de
  32 **[ran]** P63.
- **El ruteo es una pregunta sobre corpus, no sobre inputs.** Con clave en lo que
  comparten los inputs de dos miembros, 15 de 60 se ruteán mal; con clave en lo que piden
  sus corpus, 0 **[ran]** P64.
- **Un modelo grande pelado no es un experto mejor.** Sin entrenar, el 32B puntuó por
  debajo del experto 3B en las dos regiones probadas — 0,967 < 1,000, 0,746 < 0,989 **[ran]**
  P55, P55b. Así que la mitad grande de un par se *entrena sobre el mismo subdominio*, no
  se toma prestada tal como sale.

- **El conocimiento en el contexto no lo sigue un modelo chico a menos que seguirlo sea lo
  que se entrenó para hacer**, y **un cuerpo fijo de conocimiento en un corpus se
  memoriza, y después no mide nada**: base + documento de procedimiento hizo 0 llamadas a
  herramientas en 351/351 **[ran]** P61; un control sin ninguna herramienta de búsqueda
  puntuó 27/30 porque catorce valores de tabla entran en 600 ejemplos **[ran]** P15, P21.
  Las dos cosas son por qué la base de conocimiento se *navega con una política entrenada*
  y su contenido es *inmemorizable por construcción* (hito 7).

**Qué es la versión 1.0 [spec].** Cinco cosas: los expertos definidos por sus corpus; el
router con su abstención; **la memoria** (hito 7, [`MEMORY.md`](MEMORY.md)); el runtime que la
arbitra; el contrato de liberación que la hashea toda. El par especulativo (hitos 3–4) se
acopla por subdominio donde se mide que paga y **no es requerido por 1.0** — cada pieza de 1.0
tiene una compuerta que puede pasar en una L4, dentro de una sesión de sesenta minutos, y un
27B no.

Lo que queda de antes: la frontera es un componente permanente, usada donde el corpus de
ningún experto cubre el pedido o donde se mide que una región falla (0,546 → 0,775 **[ran]**
P41); los expertos se entrenan por SFT ordinario; toda región entra por la compuerta de
release; el servicio de personalización y su tooling quedan afuera de este runtime y del
open source.

Lo que se retira: la aceptación como forma de *rankear* expertos no relacionados contra un
mismo target (cerrado sin veredicto después de dos precondiciones fallidas; un rediseño de
tres sin gastar, y no se va a gastar); la composición de adaptadores; el instrumento de
aceptación a nivel de carácter; ~~el experto de mecánica de fluidos~~ — **desretirado
2026-09-19 [ran] hito 7 brazo 0b**: se retiró con un 11/90, y ese era el camino de servido.
Como le enseñó su corpus, es 90/90.

### Anexo, 2026-09-20 — una arquitectura pegada, y el cierre operativo que señala

Llegó pegada a una sesión una arquitectura de cinco fases (centro educativo + distribuidora, un solo
kernel genérico, decodificación especulativa, Postgres RLS detrás de Auth0, Docker Compose). **No
entra acá como hecho** — ninguno de sus números lo produjo este repositorio. Leída completa contra
[`FRAMEWORK.md`](FRAMEWORK.md) §9: en su mayoría vuelve a derivar los §5–§7 de ese documento desde más
lejos, y lo que agrega se reduce a una brecha abierta (permiso reforzado fuera del modelo) que este
repositorio ya había nombrado y todavía no había cerrado. **Cambian dos cosas; nada más:**

- **Se nombra el próximo paso operativo:** `FRAMEWORK.md` §7 paso 4, *una organización de referencia
  sobre un dominio neutral*, acotado a **un** dominio — no los dos que suponía el plan pegado — con un
  chequeo de permiso de juguete en lugar de Auth0/Postgres RLS hasta que se muestre insuficiente.
  Falsificador fijado en el §9: una suite adversarial a **0 fugas** sobre una fila prohibida, pedido
  directo e inyectado desde una nota o un registro.
- **El paso más barato corrió primero, y falsó tal como estaba escrito:** **W5d** — la partición de
  política de respuesta (`results/M7-W5d-answer-policy-20260920/BRIEF.md`), una sesión de L4, sin
  entrenar — `policy vs withlib` empata (5 : 0, $p=0,0625$). Igual responde el valor que le faltaba
  al paso 4, diagnosticado en vez de arreglado: el base lee 21/21 donde el recorrido abrió una nota;
  las once que nunca alcanzó son la propia consulta memorizada del adaptador.

Todo lo demás del plan pegado — un segundo dominio, Postgres RLS y Auth0 por nombre, concurrencia y el
canario entre roles, la factura, Docker Compose, decodificación especulativa — queda **nombrado, no
comprado**: ya secuenciado más adelante en `FRAMEWORK.md` §7 (pasos 5–7), y nada acá lo adelanta, por
la regla contra comprar dos brazos como grilla (`../CLAUDE.md` §3). Los hitos 1–7 de abajo, sus
compuertas y sus números, no cambian con este anexo; sólo ordena lo que sigue a F3.

**Posición, 2026-09-28.** La organización de referencia nombrada arriba está construida para **las
dos** mitades del diagrama — la escuela y la distribuidora — y las dos corrieron en vivo de punta a
punta a través del OpenClaw real (LIVE, LIVE-distributor, M8–M10, todos **[ran]**); el miembro de la
distribuidora ahora se abstiene hacia la frontera sobre lo que su corpus no cubre (M10 **[ran]**).
~~Decodificación especulativa — nombrada, no comprada~~: comprada desde entonces, sobre Gemma 4
E4B/12B, tanto en el perfil server (C0, C0-upper, F0, F0b, F0c, todos **[ran]**, Colab) como en la propia
máquina del usuario (MAC, MAC2 **[ran]**) — paga en una L4/A100 y no en la Air, así que **el serving de
edge es llama.cpp en la propia máquina del usuario (decisión del usuario), no el par especulativo**; el
par se queda como ganancia del lado de Colab (§2). La suite adversarial de **0 fugas** fijada arriba
como falsificador del paso 4 **no** corrió.

**Posición, 2026-09-29.** La conversación multi-turno era el único borde del diagrama de referencia
todavía sin ejercitar: el gateway lee sólo el último pedido, así que una referencia a un turno anterior
no tiene referente. **MT0 [ran]** midió el arreglo ingenuo — la conversación en el prompt — contra eso:
HEADROOM, en el borde (43/54 turnos dependientes resueltos, contra 4/54 sin ella; una referencia
copiada en un argumento se resuelve, una escrita en texto libre no — un reclamo sobre "ese pedido" se
abre sin número de pedido, 8 de 10). **C1 [ran]** cerró la pregunta de concurrencia que esto planteaba:
una L4 sirve cuatro miembros mezclados sin contención material (1,03× el throughput de un adaptador con
16 sesiones, 504 tok/s y p95 de TTFT 0,24 s con 32), reemplazando el 0,88 de la ráfaga única de E5. La
respuesta del usuario a la falla de MT0 no es más historial en el prompt sino un **harness de flujo
dentro de cada miembro** — la máquina de estados de un dominio, sus herramientas y las claves de una
memoria operativa de corto plazo, todo aprendido en los pesos, así que el prompt lee una sola línea de
contexto en vez de la conversación creciente (`docs/review/harness-workflow-kv.md`, diseño del
usuario). **H1 [ran]** (`results/H1-workflow-harness-20260929`): leído por brazo, `harness` **PASA** —
53/54 turnos dependientes contra 43/54 de `history` (1 perdido, 11 ganados), cada acierto buscó su valor
por clave, prompt plano por turno — y `harness-noblock` **FALSA**, 0/60. Leída tal como fue escrita, la
corrida es **VOID**: la regla del brief "cada brazo ≥ 90 % de primeros turnos o VOID", aplicada entre
brazos, deja que el brazo sin bloque anule toda la corrida — un error de diseño del instrumento, ahora
registrado, no corregido después del resultado. **La decisión del usuario (2026-09-29): vale la lectura
por brazo, el VOID tal como está escrito queda como el registro de ese error del instrumento**
(§5 Historia). ~~Un segundo dominio para el harness — un tracker de equipo tipo
Jira/Confluence, con las sesiones más largas donde se vería el ahorro de tokens — está propuesto como H2, no
construido.~~ **Construido y corrido, 2026-09-29 (H2 [ran], `results/H2-tracker-harness-20260929`):**
sobre 60 sesiones largas retenidas (160 turnos dependientes) el harness llega a **146/160 (91,3 %)**,
por encima de la barra de 90 %, plano en las cinco vueltas, y descriptivamente **142 : 0** pareado
contra `base-history` en los mismos turnos. **Tal como está escrito, FALSIFIED**: los propios primeros
turnos de `base-history` (44/60) disparan la misma regla de VOID por brazo que dispararía un
tratamiento roto, anulando la comparación — un segundo error de instrumento de la familia de H1.
~~Pendiente: el usuario todavía no eligió entre leer las condiciones de arriba (146/160 ≥ 90 %,
plano, descriptivo 142:0) como el veredicto de H2, o mantener FALSIFIED tal como está escrito y
repetir la corrida con la regla por brazo acotada a los miembros entrenados y el chequeo de anchor
contando una lectura de página que contiene el enunciado.~~ **La decisión del usuario, 2026-09-29:
lectura 1.** El veredicto de H2 son las condiciones legibles — el harness **PASÓ** (146/160 ≥ 90 %,
plano, descriptivo 142:0) — con FALSIFIED-tal-como-está-escrito en el registro con sus dos errores de
instrumento (el VOID por brazo de arriba, y el chequeo de anchor que midió fraseo). No se repitió:
ningún cambio de regla podía mover a `base-history` de 4/160. Dos correcciones leídas después en los
registros de H2 [ran]: los 80/160 de `harness-noblock`, leídos primero como "aprendido en parte", son
un error del corpus, no aprendizaje parcial, porque su tercio sin bloque se armó con el mismo módulo
(`% 3`) con el que rotan los roles, así que las 400 filas sin bloque eran todas de QA; y la falla del
comentario final de QA (6/20) es un solo fraseo de la evaluación ("Note on it: …" 1/15 contra "Put a
comment on it: …" 5/5). ~~H3 está pre-registrado y corriendo~~: **H3 [ran] 2026-09-29** — `tr-s1`,
entrenado sobre un segundo corpus de tracker que arregla las dos, le gana a `tr-s0` sobre una suite
fresca retenida: dependiente 158/160 (98,8 %) contra 147/160, pareado 11:0, $p = 0,00098$, 0 perdidos,
plano — **H3a PASÓ**; sin el bloque de herramientas, 156/160 (97,5 %) en cada rol, a más o menos un
tercio de los tokens de prompt por turno — **H3b PASÓ**
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).

## 1. Los hitos

Los brazos se compran en secuencia. El brazo que puede matar un hito corre primero; los
brazos de atribución se compran sólo una vez que hay un efecto que atribuir.

| # | hito | depende de | compuerta | estado |
|---|---|---|---|---|
| **1** | el pool en Qwen 3.x chico | D2 ✅ | los dos miembros liberados sobre `Qwen3.5-4B`, cada uno empatando o ganándole a su release de Qwen 2.5, pareado | ✅ **[ran] 2026-09-19 — MOVIDO.** G1 `applied` en los dos adaptadores de receta completa; `email-full` **471/475 = sus 471 grabados**, empate 1 : 1; `desk-commitment` **240/240**, empate; `releases/*@v2.json`. Cuatro sesiones de menos de una hora ([`BRIEF`](../../results/M1-pool-qwen35-20260919/BRIEF.md)) |
| **1b** | **el pool re-liberado sobre Gemma 4 E4B** | B1 ✅ | `email-full` y `desk-commitment` reentrenados sobre `google/gemma-4-E4B-it` desde los mismos corpus y la misma receta, cada uno empatando o ganándole a su release `@v2` de Qwen3.5-4B en los mismos casos, pareado; manifiestos `@v3` | **[ran] 2026-09-25 — NO SE MUEVE como pool:** `email-full` empata con su `@v2` (469 vs 471, 1 : 3) y le gana al Gemma pelado (119 : 0) → **`email-full@v3` sobre Gemma**; `desk-commitment` empata con `@v2` y con el Gemma pelado por igual (240/240, el techo) — ahí no hace falta adaptador, se queda en `@v2` ([`BRIEF`](../../results/M1b-pool-gemma4-20260925/BRIEF.md)). **2026-09-26: todos movidos** — `desk-commitment@v3` entrenado en las dos bandas (M1d [ran], profunda 239/240), `distributor-wiki@v2` (B5 [ran]) |
| **2** | el router como un modelo chico de los corpus | los corpus de los miembros | mal-ruteados-a-local no mayor que el del diccionario en prompts para los que el diccionario no fue escrito; abstiene ante texto fuera de distribución | **brazo 1 [ran] 2026-09-19 — no pasa.** Texto extranjero, conjuntos frescos: el diccionario sirve 59/128 localmente, el router de n-gramas **0/128**; pedidos legítimos de remitentes no vistos: el diccionario pierde 0/120, el router pierde **120/120**. ~~El diccionario se queda~~ — **brazo 4 [ran] 2026-10-02 — PASA.** Un router factorizado (tarea vs. contenido del miembro) sirve 0 de 600 textos ajenos localmente contra 294 del diccionario, pierde 0 de 480 pedidos legítimos (remitentes no vistos, tarea primero, envueltos por OpenClaw); las paráfrasis salen por diseño (0/120, reportado, nunca usado como compuerta). Ahora es el default del proxy, `openai_proxy --router factored` ([`BRIEF`](../../results/ROUTE0-factored-router-20261002/BRIEF.md)). **Brazo 5 [ran] 2026-10-03 — la mitad de tarea abierta: ROUTE1.** El rol más la abstención de cada miembro cubre ahora las tres organizaciones: `tr-out-s0` del tracker (la receta de M10) abstiene en 27/30 turnos fuera-de-alcance reservados contra el 0/30 de `tr-s1`, sin perder ninguno de los 160 turnos dependientes ([`BRIEF`](../../results/ROUTE1-tracker-abstain-20261003/BRIEF.md)) |
| **3** | la mitad grande de un par | 1 | un LoRA en ~~`Qwen3.8-27B`~~ ~~`gemma-4-31B-it`~~ `gemma-4-12B-it` (family.LARGE) está `applied` al servirse; grande + LoRA le gana a chico + LoRA en la banda profunda, pareado | ✅ **[ran] 2026-09-26, sobre `gemma-4-12B-it`: cerrado — el grande no compra precisión acá.** B3: 12B + LoRA 9/40 vs E4B + LoRA 10/40, empate, sin que ningún corpus mostrara una comparación; B5: mostradas, el E4B solo hace 37/40 — sin margen ([`BRIEF`](../../results/B5-comparison-corpus-20260926/BRIEF.md)). **PAIR0 [ran] 2026-10-02:** antes de entrenar un miembro 12B para una región nueva (documentos reales, hito 7), la misma pregunta sobre las bases peladas bajo el runtime servido — el 12B le pierde al E4B, 11/44 vs 21/44 respondibles, pareado 2 : 12, $p = 0,013$ — tampoco se entrena un miembro 12B para esa región ([`BRIEF`](../../results/PAIR0-large-headroom-20261002/BRIEF.md)). **PAIR1 [ran] 2026-10-03 — EMPATE:** la propia definición del par saca de en medio al pelado (las dos mitades entrenan sobre el mismo corpus) — después de dos quedadas sin memoria en A100 en la ventana 4.096 y una H100 rechazada por cupo, `span_logits_loss` dejó entrenar a `real-none-12b`; empata con `real-none-s0` sobre el registro de PAGE0, 33/44 vs 34/44 respondibles, pareado 5 : 6 ($p = 1,0$), y 33/44 contra el registro de FMT0 también — una segunda región (con B3) donde la mitad grande no compra precisión ([`BRIEF`](../../results/PAIR1-large-member-20261003/BRIEF.md)) |
| **4** | el par especulativo | 3 | la aceptación de borradores del LoRA chico bajo verificación del LoRA grande supera la aceptación bajo el modelo grande pelado | ✅ **[ran] 2026-09-26 — PASADO (B4):** α 0,871 → 0,898, 76 : 18 registros, $p\lt 10^{-4}$; la ganancia está en la distribución del propio corpus (0,855 → 0,914). ~~Reloj no medido~~ — **F0 [ran] 2026-09-27: decodificación especulativa corriendo con un experto LoRA sobre el 12B, el drafter MTP nativo 1,74× en el dominio del experto, 2,13× en texto general.** **C0 [ran] 2026-09-27, A100 bf16: 1,92× en el dominio (α 0,34), 2,40× general** (base 2,80×/2,60×) — el drafter E4B alineado no corrió (OOM al lado del 12B en una L4; ninguna cuantización aceptada en los brazos probados). **C0-upper [ran] 2026-09-27: confinar el LoRA a la mitad superior de las capas no devuelve NADA de la aceptación que pierde el drafter** (ρ = −0,02; base α 0,82, completo 0,44, mitad superior 0,43) — esa partición es una palanca para compartir KV inferior (hito 7 / E6), no para alinear al drafter. **En la Mac (MAC2 [ran] 2026-09-27): el propio MTP de llama.cpp frena al 12B en vez de acelerarlo** (0,52× en su dominio, 0,66–0,87× en lo demás), y el par alineado no entra en 16 GB al lado de él — **el par especulativo se queda como resultado del lado servidor (Colab, vLLM); el serving de edge es un track separado, posterior (§2)** ([`B4`](../../results/B4-gemma4-pair-acceptance-20260926/BRIEF.md), [`F0`](../../results/F0-spec-lora-12b-20260927/BRIEF.md), [`C0`](../../results/C0-aligned-draft-20260927/BRIEF.md), [`C0-upper`](../../results/C0-upper-e4b-20260927/BRIEF.md), [`MAC2`](../../results/MAC2-llamacpp-20260927/BRIEF.md)). **PAIR0 [ran] 2026-10-02:** una segunda región (documentos reales) tampoco encuentra caso de precisión para la mitad grande (fila de arriba) — el par especulativo se queda como resultado de velocidad sin una región que lo necesite ([`BRIEF`](../../results/PAIR0-large-headroom-20261002/BRIEF.md)). **F0c [ran] 2026-10-03: identidad de la salida a temperatura 0, establecida.** En bf16 sobre una A100, `VLLM_BATCH_INVARIANT=1`: el control plano-contra-plano es idéntico en cada conjunto (16/16, 8/8, 16/16, 8/8), así que el motor es determinista acá; MTP lo iguala hasta cada corte al que llega un recorrido servido en el dominio propio del LoRA (16/16 hasta el corte, las dos divergencias después de una etiqueta de cierre que un recorrido servido nunca lee de más, 1,98×) y por completo en LoRA/general (8/8); base/general todavía cambia por sinónimos en casi-empates (5/8), leído como un artefacto de la forma de verificación, no una falla de la regla de aceptación ([`BRIEF`](../../results/F0c-identity-bf16-20261003/BRIEF.md)). **PAIR1 [ran] 2026-10-03 — EMPATE:** el miembro que pide la propia definición del par (las dos mitades entrenadas sobre el mismo corpus) empata con el miembro E4B, 33/44 vs 34/44 respondibles pareado 5 : 6 ($p = 1,0$) — el par se queda como resultado de velocidad (B4, F0, C0, F0c) sin una región que lo necesite ([`BRIEF`](../../results/PAIR1-large-member-20261003/BRIEF.md)) |
| **5** | la primera región real, a mano | 1, 2, un sandbox, claves rotadas | la compuerta de release, sobre una suite con un verificador que nadie acá generó | **región nombrada el 2026-09-19: procedimientos de enfermería y material de educación en salud** (*Nursing Skills* de Open RN, CC BY 4.0, primero); sigue el brazo de margen, cero GPU |
| **6** | la política de servicio, con la factura | 2, 4, 5 | la porción local ahorra más de lo que cuesta, sobre tráfico real | 🔶 **primera pasada [ran] 2026-09-21, cero GPU:** el replay de P41/P62 tasado a las tarifas reales de `gemini-3.8-flash` — la factura real de hoy hacia la frontera (90 casos de fluidos) **$0,18\ast \ast , evitada al mantener locales los 150 casos de email \ast \ast$0,11**, techo si todo hubiera salido **$0,30**. **El costo en dólares de la propia GPU local no está tasado** — la tarifa de alquiler no se pudo obtener en vivo; no se adivinó |
| **7** | **una base de conocimiento por subdominio, y la trayectoria por ella como harness** — sobre mecánica de fluidos, partida en subdominios | 1; comparte su modelo de embeddings con el brazo 2 del hito 2; independiente de 3–6, **corre a continuación** | un experto entrenado para navegar y seguir notas contesta familias sobre las que nunca entrenó, donde el mismo experto sin la base está en 1/20 | 🔶 **W1–W4 construidos [ran]; el radar de W3 y el brazo que mata de W5 [ran] y no pasan.** W5: el brazo con biblioteca 35/56 contra el base sin entrenar que lee, 45/56 (6 : 16, $p=0{,}052$), 35 : 2 sobre sin-biblioteca — la navegación se transfirió, leer una nota de dos valores no. ~~Sigue a decisión del usuario: composición, sin entrenar.~~ **2026-09-24: la unidad de la biblioteca pasa a ser el enunciado atómico (diseño del usuario, `MEMORY.md` §1.6) — W9 [ran] 2026-09-25: PASADO**, las dos semillas le ganan al base sin entrenar que recorre el mundo de evaluación 35 : 0 en el titular de 40 filas, empata con el base que recibe los enunciados del oráculo. **El diseño sostiene el track de demos construido encima — la escuela y la distribuidora corren en vivo de punta a punta** (M8, M9, M10, LIVE, LIVE-school, LIVE-distributor, todos **[ran]** hasta el 2026-09-28), incluyendo un miembro que se abstiene hacia la frontera (M10) y edita una nota sin reentrenar (**W7 [ran] 2026-09-27**: 37/38 respuestas siguen una afirmación parcheada, 0 obsoletas). **Abierto:** los brazos 2–4 (la recuperación propia del experto, la atribución por tipo de conocimiento, la estrategia de recuperación) todavía no corrieron sobre el diseño de enunciados atómicos; la suite adversarial de 0 fugas nombrada en el anexo de abajo todavía no corrió. **2026-09-29:** el próximo paso del track de demos es el **harness de flujo** — una máquina de estados, herramientas y claves de una memoria de corto plazo aprendidas dentro de un miembro en vez de compuestas como un adaptador separado (diseño del usuario, `docs/review/harness-workflow-kv.md`). MT0 **[ran]** encontró margen para eso (43/54 turnos dependientes resueltos con historial contra 4/54 sin él, pero las referencias en texto libre se pierden 8/10); C1 **[ran]** despejó la concurrencia (cuatro miembros en una L4, sin contención material hasta 32 sesiones). **H1 [ran]:** por brazo, el harness **PASA** (53/54 contra 43/54 de `history`, cada acierto buscado por clave, prompt plano) y `harness-noblock` **FALSA** (0/60); leída tal como fue escrita la corrida es **VOID** (la regla de primeros turnos anula entre brazos — un error del instrumento, registrado). La decisión del usuario (2026-09-29): vale la lectura por brazo, el VOID tal como está escrito queda como el registro de ese error del instrumento. ~~Un dominio de tracker de equipo está propuesto como su próxima prueba (H2).~~ **Construido y corrido, 2026-09-29: H2 [ran]** sobre 60 sesiones largas retenidas (160 turnos dependientes) — harness **146/160 (91,3 %)**, prompt plano en las cinco vueltas, descriptivamente 142 : 0 contra `base-history`; **tal como está escrito, FALSIFIED**, porque los propios primeros turnos de `base-history` (44/60) disparan la misma regla de VOID por brazo que dispararía un tratamiento roto, anulando la comparación — el error de instrumento de H1 repitiéndose sobre un base sin entrenar. ~~Pendiente la decisión del usuario entre las condiciones legibles y repetir la corrida con la regla acotada a los miembros entrenados.~~ **La decisión del usuario, 2026-09-29: lectura 1** — las condiciones legibles son el veredicto de H2, el harness **PASÓ**; FALSIFIED-tal-como-está-escrito queda en el registro con sus dos errores de instrumento. `harness-noblock` (80/160) es un error del corpus (un aliasing `% 3` entre el tercio sin bloque y la rotación de roles), no un aprendizaje parcial. ~~H3 está pre-registrado y corriendo~~ **H3 [ran] 2026-09-29: PASÓ en las dos lecturas.** `tr-s1` (fraseo ampliado por turno en cada rol, un tercio parejo sin bloque en cada rol) le gana a `tr-s0` 158/160 contra 147/160 sobre una suite fresca retenida, pareado 11:0, $p = 0,00098$, 0 perdidos, plano — **H3a PASÓ**; lo-sin-bloque ahora aguanta en cada rol, 156/160, a más o menos un tercio de los tokens de prompt — **H3b PASÓ**, cerrando la brecha de lo-sin-bloque-solo-QA. Dos fallas nuevas se leen donde ocurren: una falla es el texto de la propia nota leído como una orden; las fallas sin bloque son el primer turno de una sesión arrastrando un error en cascada por el resto ([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)). **Próximo, 2026-10-01:** REAL5 **[ran]** lleva a `real-none-s0` a una tercera familia, densa en enlaces (PARTIAL, 15/25, bajo la barra de 70 %) — la citación estricta sobre valores repetidos queda como el ítem abierto; H5 **[ran]** encontró que la pérdida con máscara de tramo regresa un miembro de resultados cortos (su brazo de atribución 0 : 20) y acotó la regla a donde los resultados de herramienta son largos. **REAL6 [ran]** entrenó elecciones de valor repetido de un salto y dejó la citación sin cambios (15/25 contra 15/25, empate) — las fallas restantes son filas de varios saltos citadas en el extremo equivocado de un enlace, una forma que ese corpus nunca contuvo — **FALSEADO**. ~~**REAL7 — pre-registrado, en curso:** recorridos señuelo de enlace cruzado (la respuesta en el extremo de un enlace, un señuelo con el mismo número en su inicio), familia de entrenamiento extendida con 49 CFR 390/392/393/397; veredicto sobre el titular sin gemelos de REAL5 (21 filas, base 13/21), barra ≥ 15/21; sin resultado todavía.~~ **REAL7 [ran] FALSEADO, 2026-10-01:** `real-link-s0` empata con `real-none-s0` 13/21 sobre el titular sin gemelos (4:4 pareado, $p=1,0$), bajo la barra de ≥ 15/21; titular 16/25 contra 15/25, valor correcto 22 contra 20, citas erróneas de mismo valor 2 contra 2, negativas 5/5 en ambos; el guardia de REAL4 no se compró (sin efecto, tal como lo planteaba el brief). Dos cambios de corpus apuntados a esta citación (REAL6, REAL7) ya no cambiaron nada — por la regla de contar rediseños esta línea de corpus sobre esta pregunta se detiene. Nivel medido: `real-none-s0` con el runtime cita el enunciado de soporte en 13/21 filas de varios saltos sin gemelos de una tercera familia (valor correcto 20/25), se niega 5/5. No comprado: un chequeo de citación en el runtime que rechace una cita cuya página el recorrido no terminó, sobre un conjunto fresco. ~~**LIVE-library** (`examples/library/serve.py` + un driver de OpenClaw) está construido y probado offline; su primer intento en vivo quedó en pausa en la Mac, con el `llama-server` de otra sesión reteniendo ~8 GB — pendiente de memoria de GPU libre, todavía no corrió.~~ **LIVE-library [ran], 2026-10-01: PASÓ.** `real-none-s0` servido en `edge` (llama.cpp Q8_0 + LoRA GGUF f16, contexto 12.288 — 16.384 se quedó sin memoria en la Mac de 16 GB) por OpenClaw 2026.9.4, una sesión fresca por pregunta, sobre las 52 preguntas de REAL4, 22,5 minutos: 36/52 — titular 16/23, negativas 15/16, un salto 5/13 — contra el 38/52 de REAL4 sobre vLLM bf16 (16/23, 15/16, 7/13); el titular y las negativas empatan exactamente. Cada pérdida se lee como del borde: 4 recorridos desbordaron el contexto de 12.288 tokens tras abrir entera una página de ~7k tokens, una pregunta de OpenClaw hizo timeout sin recorrido, tres se reenviaron envueltas en el propio sobre de mensaje encolado de OpenClaw. ~~Pendiente: quitar ese sobre antes de que el runtime lea la pregunta; un presupuesto de página para que una página larga entre en un contexto de 12k~~ ([`results/LIVE-library-20261001/BRIEF.md`](../../results/LIVE-library-20261001/BRIEF.md)). **LIVE-library2 [ran], 2026-10-02: SIN CAMBIO.** Los dos ítems pendientes construidos: `examples/school/gateway.runtime_request` quita el sobre, y `memory.runtime.Conversation.page_budget` (servido en 2.500 tokens por `examples/library/serve.py`) abre una página que supera el presupuesto con sus enunciados en orden BM25 contra la pregunta hasta el presupuesto, dejando el resto como anclas abribles — sólo 29 CFR 1910.178 lo supera en esta biblioteca, chequeado offline para mantener 8/8 los 8 enunciados que necesitan los recorridos oráculo de REAL4 en ella, de 1.500 a 3.500, antes de que corriera ningún recorrido. Las mismas 52 preguntas: 37/52 — titular 16/23, negativas 14/16, un salto 7/13 — contra el 36/52 de esta corrida y el 38/52 de REAL4 sobre vLLM; 0 desbordes de contexto (4 antes), 0 sobres (3 antes), pareado contra LIVE-library 3 : 2 ($p = 1,0$). Veredicto tal como está escrito: SIN CAMBIO — 0 desbordes pero 37 < 38, no REGRESADO (el titular y las negativas despejan sus barras, sin pérdida pareada). Las tres ganancias son exactamente las filas que le costaba el borde; una pérdida nueva, `none-9`, es el presupuesto poniendo a la vista el enunciado que mejor empareja con la pregunta de una pregunta que la biblioteca no puede contestar. ~~**Pendiente:** por qué OpenClaw retiene un turno terminado (3 filas, una de las cuales detuvo la parte 1 de la corrida hasta que el driver se arregló para atrapar un turno con timeout y reanudar);~~ **Encontrado y resuelto, 2026-10-02:** las tres retenciones eran node sentado adentro de `process.exit()` después de una corrida exitosa (muestreado; un flag de V8 probado contra la salida misma no se separó del azar, 0/12 contra 3/15 sobre un stub) — la propia respuesta, demora y formato del endpoint no tienen ninguna parte. `live_library.run_turn` ahora corre cada turno en su propio grupo de procesos y lo termina `GRACE_S` (2 s) después de la propia línea de fin de corrida de OpenClaw, o en el timeout, matando el grupo entero; verificado contra el OpenClaw real sobre un stub sin modelo, 20 turnos de ~7 s cada uno, 0 timeouts, 0 huérfanos (el driver viejo dejaba exactamente estos como huérfanos durante horas). `serve.py` también ahora siempre responde a un recorrido que lanza una excepción (`NO_ANSWER`, registrado con su error) en vez de cerrar el socket — lo que hacía que OpenClaw reenviara el turno como `[Queued user message …]`, de donde salían las propias filas de sobre de LIVE-library y su fila de 119 s sin recorrido. ~~lo próximo es un chequeo de citación en el runtime sobre un conjunto fresco, no más trabajo de borde~~ ([`results/LIVE-library2-20261002/BRIEF.md`](../../results/LIVE-library2-20261002/BRIEF.md)). **CITE0 [ran], 2026-10-02: FALSEADO.** Ese chequeo, `cite_check` (lee sólo el propio registro del referí, nunca la respuesta), corrido sobre un conjunto fresco de 52 filas de una tercera familia (40 CFR 112, escrito a ciegas después de congelar el diseño): base `withlib-s0+page` **32/52** (titular 18/30, un salto 8/14, negativas 6/8) contra `withlib-s0+page+check` **33/52** (19/30, 8/14, 6/8); el chequeo disparó en 6 filas, convertidas 0, rotas 0 — que le digan por qué falla una cita no hace que un miembro de 4B produzca una mejor. Lo que es, medido: un detector sin falsa alarma — toda línea disparada ya estaba mal (6/6), y con el repaso offline de LIVE-library2, 15 disparos, 0 sobre una respuesta correcta; su punto ciego es el de REAL5–REAL7, un enunciado que tiene el valor preguntado pero no es el que se pregunta (7 de las 20 fallas que quedan acá). ~~**Próximo paso, ahora que la pista falló: el chequeo como compuerta** — una línea que no la pasa no se entrega; el runtime dice que no pudo verificar una cita, o la reenvía a la frontera~~ ([`results/CITE0-runtime-check-20261002/BRIEF.md`](../../results/CITE0-runtime-check-20261002/BRIEF.md)). **GATE0 [ran], 2026-10-02: LA COMPUERTA FUNCIONA.** El mismo chequeo como compuerta dura (`memory.runtime.citation_problem`, `Conversation.final_problem`, `examples/library/serve.py --cite-gate`, apagada por defecto cuando corrió esta medición, prendida por defecto desde la decisión del usuario del 2026-10-02 de abajo), repetida exacta — sin GPU — sobre 14 brazos `+page` dejados afuera de REAL3–REAL7 (532 recorridos con línea final, dos bibliotecas): respuestas correctas entregadas **275/275** (0 bloqueadas), filas respondibles no correctas **79/165** (86 bloqueadas, 52,1 %), respuestas a preguntas sin respuesta **0/11** (11 bloqueadas), precisión de lo entregado 0,625 → **0,777** — cumple LA COMPUERTA FUNCIONA (≤ 1 % de correctas perdidas, ≥ 15 % de incorrectas atrapadas). Dicho sin vueltas: "0 correctas bloqueadas" es en gran parte la propia definición del evaluador (una respuesta correcta ya cumple tres de las cuatro razones de disparo de la compuerta antes de la regla de los números); lo medido es el 52 % de captura. El costo honesto: de las 86 bloqueadas, 43 tenían el valor incorrecto y 43 tenían el valor correcto bajo una cita que falla — por valor, la compuerta retiene 43 de 347 valores correctos (12,4 %), subiendo la precisión de valor entregado 78,9 % → 85,9 % en lugar del 0,625 → 0,777 a nivel de fila. ~~Si un número correcto pero no verificable vale más que una negativa es una decisión de producto que le queda al usuario: la compuerta sale apagada por defecto~~ **Decisión del usuario, 2026-10-02: la compuerta sale prendida por defecto en el endpoint servido, aceptando el costo de 43 de 347 valores correctos retenidos; `--no-cite-gate` la apaga** ([`results/GATE0-cite-gate-20261002/BRIEF.md`](../../results/GATE0-cite-gate-20261002/BRIEF.md)). ~~**BOK0 — pre-registrado, en curso, 2026-10-02:** cómputo en tiempo de inferencia bajo la compuerta — el recorrido 1 es el brazo servido, greedy; sólo donde la compuerta lo retendría, se muestrean hasta tres recorridos más y se entrega el primero que la pasa — pareado sobre los conjuntos de 52 filas de CITE0 y de REAL4, medido contra **BOK WORKS** (ganancia > nuevas incorrectas, test de signos exacto $p\lt 0,05$, ganancia ≥ 5), calificado estrictamente contra la trampa de que la compuerta se superpone con el evaluador, nombrada en el brief; sin resultado todavía.~~ **BOK0 [ran], 2026-10-02: AYUDA tal como está escrito, no WORKS.** Pareado sobre los dos conjuntos de 52 filas: 16 filas remuestreadas, 39 recorridos de más, ganancia **4** contra 3 nuevas incorrectas (ganancia > nuevas incorrectas, test de signos exacto $p = 1,0$ — por debajo de WORKS, que pide $p\lt 0,05$ y ganancia ≥ 5); lo correcto entregado subió de 72 → 76 sobre 88 → 95 entregadas (conjunto de CITE0: 1 ganancia : 3 nuevas incorrectas; conjunto de REAL4: 3 : 0). Lectura: un recorrido 1 que pasa la compuerta es correcto 72/88 (82 %), uno remuestreado que la pasa sólo 4/7 (57 %) — la trampa de que la compuerta se superpone con el evaluador, nombrada en el brief, medida: muestrear hasta que la compuerta pase encuentra una cita que ella acepta, no necesariamente la de soporte, y las 3 filas nuevas incorrectas son exactamente eso. Queda registrado un falso bloqueo de la compuerta (una respuesta correcta cuya sección `1.908` el enunciado citado no imprime). 9 de las 16 filas remuestreadas fallan todos sus recorridos de la misma manera (sin línea final, o una cita sin `§sección`) — el hábito del miembro, no el azar. **No se prende.** El intento 1 (detenido antes de calificar) encontró un hueco de implementación — un recorrido 1 que desbordó el contexto dejó el brazo antes de que el remuestreo lo viera; arreglado, las dos corridas se repitieron desde cero ([`results/BOK0-best-of-k-20261002/BRIEF.md`](../../results/BOK0-best-of-k-20261002/BRIEF.md)). **PAGE0 [ran], 2026-10-02: AYUDA LA PÁGINA CON LO MEJOR ARRIBA.** Una cuarta familia real ingerida textual (`knowledge/hazwaste-regs`, 40 CFR Parte 262, 69 páginas, 1.103 enunciados, 162 enlaces), 52 preguntas congeladas a ciegas, oráculo 52/52: `memory.runtime.Conversation.page_top` abre una página que supera los 8 enunciados con los 8 mejores de la pregunta por BM25, en orden del documento, el resto como anclas abribles — fijado offline antes de cualquier recorrido (en 8, 113 de 115 recorridos del oráculo sobre tres conjuntos de lectura mantienen a la vista todo enunciado que necesitan). `real-none-s0` con `+top8` contesta **34/44** contra el **30/44** de la página sin cambios, pareado 6 : 2, $p = 0,29$ — AYUDA, no WORKS: 3 ganancias son desbordes de contexto que la página más chica entra (páginas de 97–134 enunciados leídas enteras), 3 reparan la falla de citar el enunciado equivocado en la página correcta, para la que existe (citas erróneas en la misma página 8 → 6), las 2 pérdidas mantienen a la vista todo enunciado necesario, los recorridos llevan 3,2× menos texto. **Decisión del usuario, 2026-10-02: `page_top = 8` sale como el default servido** (`examples/library/serve.py --page-top`, default 8; `--page-top 0` lo apaga) ([`results/PAGE0-page-top-20261002/BRIEF.md`](../../results/PAGE0-page-top-20261002/BRIEF.md)). ~~Sigue: si un corpus de formato entrenado bajo esa forma servida, y el modo `recover` de la guarda del árbitro, repara las fallas de formato que mostraban los conjuntos de lectura más viejos — todavía no corrió.~~ **FMT0 [ran], 2026-10-02: FALSEADO — sin margen en el conjunto, y el chequeo que lo habría dicho estaba en disco.** `real-fmt-s0` (el corpus de REAL4 recorrido bajo `page_top = 8`, 320 filas, un recorrido de cada tres leyendo un error de la guarda en modo `recover` al abrir un número de sección y siguiendo, esa apertura afuera de la pérdida con máscara de tramo) contra `real-none-s0` servido con `--guard recover`, los dos contra `real-none-s0` servido en `strict`, sobre el conjunto de 52 filas de PAGE0: los tres brazos puntúan **33/44**, tratamiento contra base **1 : 1** ($p = 1,0$), el runtime solo (`recover`) **0 : 0** contra `strict`. Las 11 fallas del base bajo top-8 tenían una línea faltante y ninguna cita mal formada — nada para que el corpus reparara. El error de instrumento asumido: el margen se chequeó sobre los tres conjuntos de lectura más viejos bajo `strict` (9 de 42 fallas eran de formato ahí, en gran parte por la guarda terminando recorridos y páginas leídas enteras — dos cosas que el top-8 y `recover` ya habían cambiado), no sobre el propio brazo top-8 de PAGE0 que ya estaba en disco (1 falla de formato en 10 fallas); costó una A100 y una sesión de L4. **La línea de corpus de formato se detiene acá** ([`results/FMT0-format-corpus-20261002/BRIEF.md`](../../results/FMT0-format-corpus-20261002/BRIEF.md)). **EDIT0 [ran], 2026-10-04: EDITS HOLD — pasa el brazo 5.** Una copia de `knowledge/hazwaste-regs` con un número cambiado en cada uno de 17 enunciados de soporte de las filas de PAGE0 (20 números): `real-none-s0` contesta **17/17** con el valor **nuevo**, cada uno citado al enunciado editado, **0** obsoletas — pasa el brazo 5 del hito 7, *editar sin reentrenar*, abierto desde el 2026-09-19; al lado, sin GPU, un `put` de opmemory sobre una clave existente reemplaza su valor sin dejar una copia obsoleta ([`results/EDIT0-edit-without-retraining-20261004/BRIEF.md`](../../results/EDIT0-edit-without-retraining-20261004/BRIEF.md)). **P2a [ran], 2026-10-04: LAS PARÁFRASIS CUESTAN.** Fuera de los brazos de este hito pero sobre los mismos miembros: `email-full` y la banda superficial de `desk-commitment` empatan con lo verbatim sobre tareas parafraseadas (469 → 470, 240 → 240), pero la banda profunda retrocede, 239 → 198 (1 : 42) en 4 de 16 reformulaciones de su regla compuesta — los miembros siguen una pregunta reformulada, no de forma confiable una regla reformulada, así que ROUTE2 (una sonda que mantendría paráfrasis locales) no se construye y la regla literal de ROUTE0 sigue siendo el router ([`results/P2A-paraphrase-headroom-20261004/BRIEF.md`](../../results/P2A-paraphrase-headroom-20261004/BRIEF.md)) |

### Hito 1 — el pool en Qwen 3.x chico

**Objetivo.** `email-full` y `desk-commitment` reentrenados en `Qwen/Qwen3.5-4B` a partir
de sus corpus liberados, receta sin cambios, y liberados por `release_gate` / `pool_second`.

**Por qué es posible ahora.** D2 **[ran]** 2026-09-19: el adaptador que P33 vio ignorado
estaba nombrado para la clase sólo-texto mientras vLLM sirve
`Qwen3_5ForConditionalGeneration`. Entrenar a través de la clase que sirve vLLM, o
renombrar al liberar (`training/harness/rekey.py`).

**Brazo que mata, primero.** La compuerta de identidad sobre un adaptador de miembro
*real* — la de D2 era un juguete de 60 pasos, juzgado sólo por si el texto servido
difiere. Si un adaptador de receta completa no queda `applied`, parar.

**Compuerta.** Pareado contra la corrida grabada de Qwen 2.5 sobre los mismos casos:
empata o gana, test de signos exacto sobre pares discordantes,

```math
p = 2\sum_{k=0}^{\min(b,c)} \binom{b+c}{k}\,2^{-(b+c)} .
```

**Falsificado por** un miembro que pierde contra su propio release de Qwen 2.5 — el
cambio de familia cuesta calidad en esa región, y el pool se queda en 2.5 hasta que se
encuentre una razón.

**No lo mide esto:** si el brazo de headroom del 4B se movió. Correr `knowledge_arm` una
vez sobre la nueva base: "el procedimiento tiene que estar en los pesos" de P61 fue un
hecho sobre un 3B.

### Hito 2 — el router como un modelo chico de los corpus

**Objetivo.** Reemplazar el diccionario de palabras clave en `route.py` por un
clasificador entrenado sobre los corpus liberados — una clase por miembro — que
**abstiene** cuando un pedido no cae en ningún corpus. Abstener es ir a la frontera. La
tabla medida `serve: local | out` sigue decidiendo si una región reconocida se sirve
localmente: el router contesta *de quién es esta distribución*, nunca *es bueno este
experto*.

**Headroom, antes de construir nada.** El diccionario está en 1,000 sobre cada conjunto
de prompts generado, así que ahí cualquier retador empata y el empate lee como éxito. El
router se mide sobre prompts para los que el diccionario **no** fue escrito: las
colisiones de bandeja compartida de los dos miembros (el conjunto 15-de-60), paráfrasis
de la pregunta de cada miembro, semillas de generador reservadas, y texto fuera de región
— las formas grabadas de OpenClaw y los enunciados de fluidos.

**Brazos, en orden.**

1. Un clasificador cero-GPU — n-gramas de caracteres o TF-IDF hacia regresión logística —
   entrenado sobre los turnos de usuario de los corpus. Minutos en una laptop. Si cruza la
   compuerta, el router *es* esto, y no se construye nada más grande.
2. Sólo si 1 falla: el modelo más chico de la familia con una cabeza de clasificación.

**La métrica es el término que un router puede cambiar** ([`FOUNDATIONS.md`](FOUNDATIONS.md) §8.4):

```math
\text{entregado} = \tfrac1n\sum_x [r(x)=(\text{local},m^*)]\,L_{m^*}(x) + [r(x)=\text{out}]\,F(x) + [r(x)=(\text{local},m\ne m^*)]\cdot 0 ,
```

así que se puntúa por **mal-ruteados-a-local** y por la fracción que sale, no por
exactitud de ruteo.

**Falsificado por** más pedidos mal-ruteados a un miembro local que el diccionario, o
ninguna abstención ante texto fuera de distribución. Un modelo al que se le pide elegir
siempre elige; el brazo de abstención se compra primero.

**Resultado [ran] 2026-09-19 — el brazo 1 no pasa**
([`results/M2-corpus-router-20260919/BRIEF.md`](../../results/M2-corpus-router-20260919/BRIEF.md)).
Un modelo uni+bigrama suavizado por miembro sobre el *frame* del corpus — tokens en al menos
la mitad de sus documentos; todo lo demás, un único símbolo `<slot>` — que acepta un pedido si
su transición de frame menos probable y su cobertura de frame son típicas del corpus. Tres
intentos, dos rediseños contados, cada uno escrito primero en el brief; el diseño se congeló
después y **los conjuntos frescos se escribieron después y se puntuaron una sola vez**:

| conjunto | diccionario | router de n-gramas |
|---|---|---|
| en distribución, 715 | 0 mal-ruteados · 0 perdidos | 0 mal-ruteados · 0 perdidos |
| texto extranjero, fresco — textos con clave y un listado seguido de otra tarea, 128 | **59 servidos por un miembro local** | **0** |
| pedidos legítimos de remitentes fuera de los pools del generador, 120 | 0 perdidos | **120 perdidos** |
| la pregunta del miembro parafraseada, 240 | 131 perdidos | 240 perdidos |

Aprendió la uniformidad del generador: toda dirección generada termina en `.com`, así que
`. com >` es *frame*, y un remitente real sale de la distribución. El tráfico real es toda la
tercera fila. Y para un modelo léxico una paráfrasis de la pregunta del miembro y una tarea
distinta son una sola cosa — un listado familiar, después una oración desconocida.
**Distinguirlas es semántica, así que el brazo 2 es un modelo de embeddings** (el más chico de
la línea de embeddings de la familia), con las cuatro filas de arriba como sus conjuntos que
matan. El diccionario se queda como default del proxy; `corpus_router.py` se queda como el
brazo medido. El tercer rediseño no se gastó.

**Brazo 2 [ran] 2026-09-19 — un modelo de embeddings; tampoco pasa**
([`BRIEF`](../../results/M2b-embed-router-20260919/BRIEF.md)). `Qwen3-Embedding-0.6B`, coseno medio a los
cinco pedidos más cercanos del corpus, todo texto embebido como *la tarea que se pide*: texto ajeno
15/338 servidos localmente (diccionario 119, n-gramas 0), paráfrasis 99/240 recuperadas — y **120/120
pedidos de remitentes no vistos perdidos**, como el brazo 1. Con los puntajes por caso guardados, **no
es calibración**: los remitentes no vistos (mediana 0,89, máx 0,964) y *el listado propio de un
miembro seguido de otra tarea* (0,87–0,91, máx 0,966) ocupan el mismo rango, así que ningún umbral
separa lo que debería quedarse de lo que debería salir. En este espacio, cambiar quién escribe mueve
un pedido tanto como cambiar qué se pide. **Lo que queda es una representación que factorice la tarea
del contenido** — una proyección chica entrenada por contraste (misma tarea / otro contenido contra
mismo contenido / otra tarea), que es la etapa R1 del radar ([`MEMORY.md`](MEMORY.md) §2.2) alcanzada
desde el lado del router. Necesita conjuntos de evaluación nuevos; el diccionario sigue siendo el default.

**Dónde el problema del router no aparece — restituido el 2026-09-19** (el análisis es `docs/CASE-TEAM.md`
en el tag `v0.1-foundations`; la reescritura lo sacó y no debió). Un equipo que corre el runtime de
agentes en modo multijugador — cada persona en el chat, varios agentes, decenas de sesiones
concurrentes, conversaciones en **grupos estables por área** — tiene sus regiones por construcción: un
grupo se repite, tiene su propio vocabulario y una membresía estable. **El id del grupo es la ruta**;
no se infiere nada, porque el cliente ya sabe en qué sala está. Los dos brazos aprendidos de arriba
fallan en *quién escribe*; en un despliegue de equipo ésa no es una señal que alguien tenga que leer.
Es también el primer escenario que ejercita el pool como pool — lotes mixtos entre decenas de
sesiones, **sin medir** acá — y vuelve el margen una pregunta por grupo: un promedio de empresa
esconde al grupo con brecha y al grupo sin ella. Lo que **no** aborda es la mitad de infraestructura
de un despliegue así — una lista de sesiones que se llena, un gateway inalcanzable detrás de un proxy
de acceso, un websocket que se cae. No construido para eso: aislamiento entre usuarios, streaming,
ciclo de vida de adaptadores por grupo.

**Brazo 3, solo margen [ran] 2026-09-21 — `cactus-compute/needle`, pesos de fábrica; no se
compra un brazo real** ([`BRIEF`](../../results/M2c-needle-router-20260921/BRIEF.md)). Leído
[read] como candidato no por tamaño sino por las dos piezas que le faltaban al brazo 2 — una
cabeza de confianza calibrada y ajuste fino local por LoRA desde un formato de contraste
`query`/`answers` — el mismo `EmbedRouter`, `score_cases` y `verdict` que usó el brazo 2, solo
cambia el codificador. Submuestreado (40 por lote, hasta 715 en un lote) después de que el
primer intento corrió ~15 minutos sin línea de progreso — arreglado con impresión de progreso
por llamada y un `--limit` con semilla, no comparado a la resolución propia del brazo 2.
**`NOT SAFE: serves foreign text locally`** — 62 de 142 casos fuera de región servidos
localmente (mismo contenido, tarea distinta, E/E2: 29/40 y 33/40), contra 15/338 del brazo 2
(4,4 %) — cerca de **10×** la tasa de fuga. Sí recupera tráfico real que el brazo 2 perdía por
completo (remitentes no vistos, F: 19/40 contra 0/120) pero no de forma confiable (52,5 % se
sigue perdiendo). Ninguno de los dos resultados nombrados en el brief: ni "seguro pero pierde
F" ni "F mejora sin que el texto ajeno empeore" — sacrifica justo la propiedad para la que
existe el router. Los pesos de fábrica y un τ prestado no ejercitan las dos piezas por las que
se eligió este brazo; un brazo real (su propio brief, los pesos afinados a los que apunta el
propio README de Needle) no queda justificado por esta mirada.

**Brazo 4 [ran] 2026-10-02 — un router factorizado: local sii exactamente un párrafo no es
contenido del miembro y es la tarea del miembro; PASA**
([`BRIEF`](../../results/ROUTE0-factored-router-20261002/BRIEF.md)). Los brazos 1–3 leen el pedido
entero y fallan igual: un remitente no visto (F) y el listado propio de un miembro seguido de otra
tarea (E, E₂) ocupan un mismo rango en ese espacio — quién escribe mueve un pedido tanto como qué se
pide. Un pedido a un miembro es **contenido** que lee más **una tarea** para la que fue entrenado; la
pregunta del router es la tarea. `training/harness/factored_router.py`, cero GPU, sin modelo:
párrafos; el *content frame* de un miembro (claves de línea de los párrafos no finales de su corpus) y
sus tareas (los párrafos finales de su corpus, normalizados). Local a $m$ sii exactamente un párrafo
no es contenido de $m$ y es una de las tareas de $m$, con al menos un párrafo de contenido; los
envoltorios de OpenClaw se sacan primero. Comprado primero por ser el brazo más barato que podía pasar
(el propio orden del hito 2): si cruza la compuerta, no se construye nada más grande. Puntuado una
sola vez, sobre conjuntos frescos (`make_sets.py`) escritos a ciegas del código de la regla a partir
de una especificación escrita, después de congelado el diseño:

| conjunto | router factorizado | diccionario (default de hoy) |
|---|---|---|
| ajeno — E3, E4, I3, C3, D3 (600) servidos localmente | **0** | 294 |
| A3 perdidos / mal-ruteados (120) | 0 / 0 | 0 / 0 |
| F3 remitentes no vistos perdidos (120) | **0** | 7 |
| G3 tarea primero perdidos (120) | **0** | 3 |
| H3 envuelto por OpenClaw perdidos / mal-ruteados (120) | **0 / 0** | 0 / 65 |
| B3 paráfrasis mantenidas locales (120, reportado) | 0 (salen, como diseñado) | 54 (3 mal-ruteadas) |

**Veredicto: PASA** — 100 % del texto ajeno abstenido (barra 95 %), menos mal-ruteos que el diccionario
(0 vs 294), A3 0/0, F3/G3/H3 0 perdidos cada uno. **La pared que chocaron los brazos 1–3 — remitentes
no vistos perdidos 120/120 — desaparece** porque el remitente es contenido, y el contenido sólo tiene
que ser del *tipo* del miembro. **Pasa a ser el default del proxy**
(`training/harness/openai_proxy.py --router factored`, `route.decide_factored`); una región sin corpus
en el pool (fluidos) se queda en sus claves, como antes. **Lo que no hace:** mantener una paráfrasis
local (B3, 0/120, reportado, nunca compuerta) — los miembros se entrenaron sobre una sola redacción
cada uno, y servir una paráfrasis localmente apostaría al miembro, no al ruteo. **Llevado como
advertencia, fuera del veredicto:** una prueba de estrés post-hoc — un header `Cc:`/`To:` de más,
cortesía alrededor de la tarea ("¡Hola! ¿Es importante esto? Gracias"), la tarea escrita en el propio
párrafo del header — manda afuera cada variante, nunca a un miembro equivocado: la regla es segura
porque falla hacia la frontera, y literal porque mantiene local exactamente el formato que el propio
gateway escribe; donde un cliente formatea el contenido a su manera, la fracción local baja y la
corrección no.

**Brazo 5 [ran] 2026-10-03 — la mitad de tarea abierta del router: el rol más la abstención de cada
miembro, ahora en las tres organizaciones medidas** ([`BRIEF`](../../results/ROUTE1-tracker-abstain-20261003/BRIEF.md)).
El brazo 4 factoriza la tarea del contenido para miembros de **tarea fija**; un miembro de **tarea
abierta** (el tracker, la distribuidora, la escuela) no carga una sola tarea contra la que factorizar,
así que su router es el rol que viaja en el token firmado (F2 **[ran]**) más la abstención propia del
miembro hacia la frontera de su rol, aprendida en su corpus. El corpus de la escuela la enseña (74 de
700 turnos); el de la distribuidora desde M10 **[ran]** (20/20 reservados abstenidos, 0 de 70
perdidos). El del tracker nunca lo hizo — **0 de 1.400 turnos del corpus** — así que un pedido fuera de
su rol se intentaba con sus herramientas en lugar de llegar a la frontera (el frontier para desarrollador
y líder, una persona para QA). **ROUTE1** entrena `tr-out-s0` sobre el corpus de `tr-s1` más 126 turnos
de abstención (la receta de M10, 9 %, un tercio sin bloque por rol): abstiene en **27 de 30** turnos
fuera-de-alcance reservados (14/16 fuera del tracker, 13/14 fuera del rol) contra el 0/30 de `tr-s1`,
pierde **0** de los 160 turnos dependientes que `tr-s1` contesta bien (barra ≤ 3), y no abstiene en
ningún turno dentro de alcance. **Con esto, el router para miembros de tarea abierta es el rol más la
abstención de cada miembro en las tres organizaciones: escuela, distribuidora (M10), tracker (ROUTE1).**
Servir `tr-out-s0` en lugar de `tr-s1` es el cambio que esto pide; **el usuario lo decidió, el
2026-10-04: `tr-out-s0` es ahora el miembro servido del tracker** (el propio comando de
`examples/tracker/live_tracker.py`), con el registro **[ran]** de LIVE-tracker conservado como que
corrió `tr-s1`.

### Hito 3 — la mitad grande de un par

**Objetivo.** Un LoRA en `Qwen/Qwen3.8-27B`, QLoRA NF4, a partir del *mismo corpus* que
un miembro chico, en la banda donde el miembro chico tiene headroom — el
`commitment_deep` del desk, ya que la banda superficial satura a los 75 ejemplos **[ran]**
P55b.

**Brazos que matan, en orden.** (a) La compuerta de serving: un LoRA sobre el 27B
cuantizado queda `applied` — la compuerta de logprobs con su control base-contra-base, no
la compuerta de texto, que malinterpretó un adaptador de juguete sobre un 32B **[ran]**
P60 §3b. (b) Headroom: el miembro chico está debajo del techo en la banda elegida. Si ya
está en 1,000 ahí, la mitad grande no tiene nada que comprar.

**Compuerta.** Grande + LoRA le gana a chico + LoRA en esa banda, pareado, $p \le 0.05$.

**Falsificado por** un empate o una derrota: en este subdominio la mitad grande no compra
nada, y el par no se construye acá. Eso es un resultado sobre el subdominio, no sobre el
diseño.

**Restricción.** A100, 4 bits. No corre en la L4 desde la que se sirve el pool.

**Estado (2026-09-26) — cerrado en Gemma 4 E4B / 12B.** ~~Qwen3.8-27B~~: la familia es Gemma 4 y la mitad grande es
`gemma-4-12B-it` (B2 **[ran]**). En la banda comparativa las mitades empataron mientras ningún corpus mostraba una
comparación (B3 **[ran]**, 9 vs 10 de 40); enseñadas, la mitad chica hace 37/40 (B5 **[ran]**, 28 : 1 sobre su predecesor,
su puntaje de W9 intacto) — sin margen, así que **la mitad grande no compra precisión acá**, como dice la cláusula de falsación. Su trabajo es el del hito 4.

**PAIR0 [ran] 2026-10-02 — margen chequeado antes de entrenar un miembro 12B para una región nueva
(la línea de documentos reales del hito 7), no después.** Pelado, bajo el runtime servido
(`base-walks+page+top8`, el conjunto de 52 filas de PAGE0 sobre `knowledge/hazwaste-regs`,
`page_top = 8`), `gemma-4-12B-it` le pierde a `gemma-4-E4B-it`: respondibles 11/44 contra 21/44,
pareado 2 : 12, test de signo exacto $p = 0,013$, rechazos 1/8 contra 8/8 — ninguno de los dos
resultados pre-registrados (empate o margen del 12B) queda como se escribió; el 12B lee este protocolo
significativamente peor. El intento 1 fue **VOID**: el 12B pelado abrió su canal de pensamiento con el
pensamiento apagado y dio vueltas en él hasta agotar el presupuesto de llamadas (34 de 43 fallos, sin
cita) — arreglado con `wiki_arm --empty-thought` (un canal vacío prellenado); queda anotado un canal
residual (254 líneas cortas de `thought` en las 52 caminatas, dentro del presupuesto) y una segunda
corrección no gastada, ya que incluso un canal limpio tendría que convertir un déficit de 2 : 12 en una
victoria significativa para cambiar la decisión. **Tampoco se entrena un miembro 12B para esta
región**; el par especulativo se queda como resultado de velocidad sin una región que necesite la
mitad grande ([`BRIEF`](../../results/PAIR0-large-headroom-20261002/BRIEF.md)).

**PAIR1 [ran], 2026-10-03 — EMPATE: el miembro que pide la propia definición del par.**
Las bases de PAIR0 estaban peladas, lo que confunde tamaño con protocolo; la propia definición del par
saca eso de en medio entrenando las dos mitades sobre el mismo corpus. Los intentos de entrenamiento 1
y 2 se quedaron sin memoria en la ventana de 4.096 en una A100 (el intento 2 por el tamaño exacto del
tensor de logits de 4,00 GiB contra 4,00 GiB libres); un intento 3 en H100 fue rechazado por cupo tres
veces, el límite que marcaba el brief; `s4_train.span_logits_loss` dejó terminar al intento 4 sin
cambiar el corpus, la receta ni las varas (315 filas, 19.454 tokens entrenados de 594.798). Entrenado,
`real-none-12b` (mismo corpus y receta que `real-none-s0`) empata con `real-none-s0` sobre el registro
de PAGE0: 33/44 contra 34/44 respondibles, pareado 5 : 6 ($p = 1,0$), 23/30 contra 24/30 multi-hop,
10/14 one-hop y 7/8 rechazos los dos, y 33/44 contra el registro de FMT0 también. **Veredicto: EMPATE**
— con B3, una segunda región donde un miembro grande no compra precisión; el par especulativo se queda
como resultado de velocidad medido (B4, F0, C0, F0c) sin una región que necesite su mitad grande.
Entrenado, el 12B camina limpio — 0 líneas de pensamiento donde el 12B pelado dejó cientos en PAIR0 —
así que el protocolo que el 12B pelado de PAIR0 fallaba era el entrenamiento, no el tamaño. Una
observación al lado del veredicto, no un reclamo: los dos miembros empatan en totales pero se
equivocan en filas distintas (11 discordantes de 44 — 5 que sólo el 12B acierta, 6 que sólo el E4B
acierta; 39/44 correctas por cualquiera de los dos); si algo puede elegir entre ellos por pedido está
sin probar ([`BRIEF`](../../results/PAIR1-large-member-20261003/BRIEF.md)).

### Hito 4 — el par especulativo

**Objetivo.** Medir la aceptación de los borradores del miembro chico bajo la
verificación del miembro grande, los dos llevando el LoRA del mismo subdominio.

**Cómo se mide, y por qué.** vLLM trae multi-LoRA y decodificación especulativa, pero un
drafter con LoRA es un RFC, no una feature **[read]**. Así que la aceptación se mide como
este repositorio ya la mide (`accept_rank.py`): el miembro chico genera, el grande puntúa
el borrador en una sola pasada con teacher forcing (`prompt_logprobs`), y un token se
acepta cuando es el argmax del modelo grande a temperatura 0. Con aceptación por token
$\alpha$ y largo de borrador $k$, los tokens esperados por pasada del modelo grande son

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha} .
```

**α se reporta con su $k$ y al lado del puntaje verificado de la misma corrida.** α sola
no es una decisión.

**Brazos, en orden.** El par contra **borradores del LoRA chico bajo el modelo grande
pelado** — la comparación que puede matarlo. Sólo si el par gana: borradores del chico
pelado bajo el LoRA grande, para decir qué mitad lleva la ganancia.

**Falsificado por** α(par) ≤ α(LoRA chico, grande pelado): entrenar la mitad grande sobre
el subdominio no la hace concordar más con el experto chico, y el par es un dispositivo de
calidad (hito 3) pero no uno especulativo.

**No se afirma:** aceleración de reloj. Eso necesita la feature del runtime y es una
medición aparte.

**Estado (2026-09-26) — pasado en Gemma 4 E4B / 12B (B4 [ran]).** El LoRA del 12B sube la aceptación de los borradores del
miembro E4B, α 0,871 → 0,898 agregado, 76 : 18 registros — toda en la distribución del propio corpus (0,855 → 0,914).

**PAIR0 [ran] 2026-10-02** agrega una segunda región sin caso de precisión para la mitad grande: en
documentos reales, pelado, el 12B lee significativamente peor que el E4B (hito 3, arriba), no mejor ni
empatado. El caso de calidad del par especulativo sigue descansando sólo en la medición de aceptación
sobre la propia distribución de B4; se queda como resultado puramente de velocidad hasta que se
encuentre una región que necesite la precisión de la mitad grande
([`BRIEF`](../../results/PAIR0-large-headroom-20261002/BRIEF.md)). **PAIR1 [ran] 2026-10-03 —
EMPATE:** el miembro 12B entrenado que pide el propio orden de PAIR0, sobre la misma región, empata
con el miembro E4B (33/44 vs 34/44 respondibles, pareado 5 : 6, $p = 1,0$) — el caso de calidad del
par especulativo sigue descansando sólo en la medición de aceptación sobre la propia distribución de
B4; se queda como resultado puramente de velocidad, ahora con dos regiones chequeadas y ninguna
necesitando la precisión de la mitad grande
([`BRIEF`](../../results/PAIR1-large-member-20261003/BRIEF.md)).

**F0c [ran] 2026-10-03 — no cierra lo que afirma el hito, pero salda lo que el hito 4 dejó abierto:
la identidad de la salida a temperatura 0.** F0 corrió en una L4 en FP8, donde F0b encontró que el
motor mismo no era determinista (el control plano-contra-plano difería). En bf16 sobre una A100, con
`VLLM_BATCH_INVARIANT=1`, ese control es idéntico en cada conjunto (16/16, 8/8, 16/16, 8/8) — el motor
es determinista acá — y MTP lo iguala hasta cada corte al que llega un recorrido servido en el dominio
propio del LoRA (1,98×, las dos divergencias después de una etiqueta de cierre que ningún recorrido
servido lee de más) y por completo en LoRA/general (8/8); base/general todavía cambia por sinónimos en
casi-empates (5/8), un artefacto de la forma de verificación, no una falla de la regla de aceptación.
**Lo que esto establece:** con el LoRA propio del experto, en su propio dominio, la decodificación
especulativa preserva lo que escribe un recorrido servido hasta cada corte — no una garantía bit a bit
general de vLLM ([`BRIEF`](../../results/F0c-identity-bf16-20261003/BRIEF.md)).

### Hito 5 — la primera región real

**Nombrada por el usuario, 2026-09-19: procedimientos de enfermería, y material de educación en
salud para la formación de expertos locales.** Es la primera región correcta por razones que da el
registro:

- **Es conocimiento que nadie acá generó.** Toda suite hasta ahora la escribió este repositorio, y
  una suite generada no puede contener una dificultad que su autor no pensó (`RECORD.md` §3); el
  router de n-gramas aprendió el `.com` de un generador (M2). Un manual de procedimientos es texto
  de otro.
- **Es conocimiento operacional en su forma más pura** — pasos ordenados, chequeos antes de actuar,
  qué hacer cuando un chequeo falla — al lado de conocimiento enciclopédico (indicaciones, rangos,
  tablas). Los dos tipos de la base del hito 7, en una sola fuente real.
- **Tiene verificadores mecánicos**, y lo que le faltó a la suite clínica de S0–S1 fue margen, no
  verificadores: el paso siguiente de un procedimiento, el orden de uno desordenado, un chequeo que
  debe preceder a una acción, y la aritmética — goteos, diluciones, dosis por peso desde una tabla
  — que es la forma `lookup` + `calc` de fluidos sobre contenido real. La calculadora se queda: un
  experto destilado escribe π/4·0,22² como 0,037006 (P5–P7), y acá eso es una dosis.
- **"Expertos locales" es la base inmemorizable, de verdad.** La adaptación que hace una sala o un
  ministerio de una guía — otra dilución, un chequeo extra — es exactamente una nota cuyo contenido
  los pesos no pueden guardar porque cambia por sitio. El brazo 5 del hito 7 (editar una nota, la
  respuesta sigue a la base, sin reentrenar) deja de ser un truco de instrumento y pasa a ser el
  producto.

**Restricciones, como hechos.**

- **La licencia decide la fuente, antes que la calidad [read] 2026-09-19.** Las publicaciones de la
  OMS salen por defecto bajo **CC BY-NC-SA 3.0 IGO**: sin uso comercial, y las adaptaciones heredan
  la licencia — sirve para medir, no para entregar en un servicio, y no se puede commitear a este
  repositorio Apache-2.0. ***Nursing Skills* de Open RN** (Chippewa Valley Technical College, en
  NCBI Bookshelf) es **CC BY 4.0**: uso comercial y adaptación con atribución. Así que el libro
  abierto es la primera fuente; un texto de la OMS es un segundo brazo, no comercial; los
  procedimientos propios de un cliente son el caso real y viven del lado de la personalización,
  fuera de este repositorio (§0). Verificar la licencia de cada documento que se use.
- **Es material de formación, no consejo a un paciente.** Las preguntas de la región son las de un
  estudiante o un formador local. Nada acá es un dispositivo médico, y la compuerta de release de
  esta región es más estricta, no más laxa: lo que el experto no está medido para responder, sale.
- **Sin datos de pacientes**, por construcción: sólo procedimientos y texto de enseñanza.
- **El idioma es una incógnita más.** Arrancar en el idioma de la fuente; una edición en español es
  un segundo brazo, no una suposición gratis sobre un 4B.

**Orden — lo más barato que puede matarlo, primero.**

1. **Margen primero:** tres listas de verificación, 72 preguntas verificables de los cuatro tipos de
   arriba, la base pelada contra ellas a libro cerrado y a libro abierto — en Colab, diez minutos
   de una L4 (`training/nursing/headroom.py`). **[ran] 2026-09-19 — hay margen, y leer cierra casi
   todo:** orden de pasos y paso siguiente 29/48 a libro cerrado → **45/48 con la nota abierta**; una
   cantidad que cambió el protocolo de la unidad **0/12 → 12/12**; goteos 7/12 → 6/12 — aritmética, no
   conocimiento ([`BRIEF`](../../results/M5-nursing-headroom-20260919/BRIEF.md)). **Consecuencia:** una
   base chica *responde sobre* una nota que sólo lee, aunque no *actúa bajo* una (P61). La trayectoria
   entrenada se tiene que medir sobre **recorridos**, nunca sobre preguntas y respuestas, y todo brazo
   de acá en adelante lleva la línea de base *base pelada + la nota del oráculo abierta*. Si la base ya ordena los pasos de un procedimiento que
   nunca se le mostró, no hay nada que comprar — así murió la suite clínica (S1: ningún modelo
   adelante de un 12B local gratis). Margen primero, otra vez.
2. Después el diseño del hito 7, sin cambios, sobre este contenido: trayectorias sobre las notas del
   capítulo, **un procedimiento retenido que existe sólo en la base**, la trayectoria oráculo primero.
3. La mecánica de fluidos conserva su trabajo al lado: es el **instrumento** — un oráculo exacto y
   contenido inmemorizable por construcción. Enfermería es la **región**. Un resultado que aparece
   en una y no en la otra es un hallazgo sobre las suites generadas.

Setenta y cinco a cien ejemplos escritos a mano es el primer tamaño correcto — la banda llana del
desk saturó ahí. Necesita un sandbox para todo lo que ejecute y claves rotadas.

### Hito 6 — la política de servicio, con la factura

Router → miembro chico → par donde se mide que la región lo necesita → frontera. El
número que nunca se midió es la plata: la factura de la frontera con y sin la porción
local, sobre tráfico real. **Falsificado por** una porción local que cuesta más correrla
de lo que ahorra.

**Primera pasada [ran] 2026-09-21, cero GPU** (`training/harness/bill.py`,
[`BRIEF`](../../results/M6-bill-20260921/BRIEF.md)). No es tráfico real — lo más cercano en disco: el
replay de P41/P62 (150 casos de email-full servidos localmente, 90 casos de fluidos enviados de
verdad a `google/gemini-3.8-flash`, confirmado en el propio campo `model` de `frontier_fluids.json`),
tasado a la tarifa real de ese modelo en el nivel pago ($0,75 /$3,75 por 1M de tokens de
entrada/salida, fuente `ai.google.dev/gemini-api/docs/pricing`, obtenida el mismo día). El email se
tasa exacto, turno por turno, como factura de verdad una API de chat una llamada multi-turno; los
fluidos se tasan con una aproximación declarada (toda la cadena de llamadas a herramientas a la
tarifa de salida) sesgada a **sobreestimar**, nunca subestimar, el costo de la frontera.

| | tokens (entrada / salida) | USD |
|---|---|--:|
| factura real de hoy hacia la frontera (90 casos de fluidos) | 8.961 / 47.255 | **$0,1839** |
| evitada al mantener locales los 150 casos de email | 72.745 / 15.184 | **$0,1115** |
| techo si todo hubiera salido a la frontera | — | **$0,2954** |

**Lo que esto no responde, nombrado en vez de adivinado:** el costo en dólares de la propia GPU
local. La tarifa de alquiler de Colab se renderiza del lado del cliente y dos intentos en vivo no
devolvieron un número utilizable — no se fabricó ninguno. `local_token_volume_for_rate_substitution`
en `bill.json` es lo que una tarifa real de $/hora o$/token multiplica una vez que se provea. **A la
escala de este replay (240 casos) cada número de arriba es una fracción de un dólar** — antes de leer
un veredicto de "ahorra más de lo que cuesta" en estas cifras, la plata todavía no es la cantidad que
decide a este volumen; lo que una primera pasada como esta puede mostrar es la forma de la respuesta,
no su tamaño.

### Hito 7 — una base de conocimiento por subdominio, y la trayectoria por ella como harness

**Esto es el núcleo de la versión 1.0. Lo que se construye, pieza por pieza y en qué orden, es
[`MEMORY.md`](MEMORY.md)** — los dos estantes de la biblioteca, el radar, tres verbos, el
hábito de navegar del LoRA, el árbitro de software. El *por qué*, escrito para que lo discutan
otros modelos, es [`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md).

**La idea, del usuario.** El subdominio de un experto tiene un cuerpo de conocimiento de dos
clases: **enciclopédico** — jerárquico: qué es una magnitud, qué correlación vale en qué
régimen, cuáles son las propiedades de un material — y **operacional** — secuencial: cómo se
resuelve este tipo de problema, paso a paso, y qué chequear. Poner las dos en una base de
conocimiento que pertenece al subdominio (notas en markdown, enlazadas, embebidas; la memoria
es markdown y git — `ARCHITECTURE.md` §7). Lo que el LoRA aprende entonces no es el contenido
sino la **trayectoria**: qué nota abrir primero, qué enlace seguir, cuándo dejar de leer y
calcular. *Una trayectoria por notas operacionales es un harness* — lo que `harness.lora`
estaba buscando, ahora por subdominio y afuera de los pesos, donde se puede editar.

**Por qué mecánica de fluidos, y por qué partirla.** Es el único dominio acá con headroom
real — la frontera 66/90, el experto ~~12/90~~ **[ran]** P40, P41. *(Corregido el mismo día por
el brazo 0b: 12/90 era el camino de servido; en su región, como le enseñaron, el experto está
en 90/90. Mecánica de fluidos se queda como el banco de pruebas de lo que eso **no** cubre —
una familia hermana sobre la que nunca entrenó, 1/20 **[ran]** P14 — y porque su contenido es
inmemorizable por construcción.)* Un solo adaptador sobre todo eso se entrenó a una sola
profundidad y se pasó de rosca por debajo de ella **[ran]** P45. Entonces: subdominios de dos
familias hermanas cada uno — flujo interno (`pipe_head_loss`, `pump_power`), medición
(`venturi_flow`, `orifice_discharge`), flujo externo (`terminal_velocity`, `drag_force`),
canales y estática (`manning_channel`, `hydrostatic_force`) — cada uno a través de la escalera
de dificultad (`training/physics/ladder.py`), así que región y profundidad son dos variables.

**Tres hechos medidos dan forma al diseño — restricciones, no objeciones.**

1. **Un modelo chico no sigue lo que lee a menos que seguir sea lo que se entrenó** **[ran]**
   P61. → La navegación y el seguimiento de notas son *el contenido del adaptador*: el corpus
   son trayectorias — `<search>…</search>`, `<open>id</open>`, después `<calc>` — escritas por
   el oráculo.
2. **El conocimiento fijo en un corpus se memoriza, y entonces la base no mide nada** **[ran]**
   P15, P21. → Las notas que necesita un caso son **inmemorizables por construcción**, el manual
   por caso de P21 extendido de valores a procedimientos: propiedades de un fluido que existe
   sólo en este caso, y una variante de correlación cuyos coeficientes se sortean por caso. El
   experto puede aprender *cuál* nota necesita un paso; no puede aprender *qué dice* la nota.
3. **Un especialista se equivoca con confianza apenas fuera de su región** — 30/30 en sus
   fórmulas adentro, **1/20 en familias que nunca vio**, la prosa igual de fluida **[ran]** P14.
   → Ese es el headroom y la afirmación: *con las notas de la familia hermana en la base y sin
   reentrenar, el experto entrenado para navegar contesta a la familia hermana.*

Y uno del workspace: una jerarquía de memoria perdió contra búsqueda léxica plana en su primer
benchmark, y una suite de física de respuesta exacta fue el instrumento equivocado para memoria
porque todo en ella era derivable. → El canal tiene que ser *necesario* (el hecho 2 lo
garantiza; la corrida afirma la ausencia de la fuga: ningún valor buscado aparece en el
enunciado), y la jerarquía es un brazo, no un supuesto.

**Brazos, en orden — el que puede matarlo primero.**

| # | brazo | qué decide |
|---|---|---|
| **0** | margen, cero GPU: las 90 cadenas grabadas de P41 reproducidas contra el handbook propio de cada caso (`training/physics/result_use.py`) | **[ran] 2026-09-19.** De 79 fallas, **74** tienen un `<calc>` con un número que no salió de ningún lado y **75** dejan un resultado de herramienta sin usar; 217 de 456 resultados no finales se ignoran — el experto busca la densidad, 882,3, y multiplica por 1359,7. **La falla dominante no es una relación equivocada: es no usar lo que se le devolvió.** *(Corregido el mismo día: la primera reproducción pasó el handbook en su forma JSON, cada `<lookup>` levantó una excepción dentro de un `except` amplio, y los 74 sin usar / 132 de 371 ignorados publicados estaban mal. Con los lookups evaluados — 0 errores de herramienta — son 75 y 217 de 456; los 74 con un número que no salió de ningún lado se sostuvieron.)* |
| **0b** | **el mismo adaptador, los mismos 90 casos, servido en modo corpus** — el resultado inline después del tag de cierre, como enseñó su corpus | **[ran] 2026-09-19 — EL CAMINO ERA PARTE: 90/90** contra 11/90 por `tool_calls`, 79 : 0 pareado; 24 : 0 contra el 66/90 de la frontera; ningún caso evaluado en el corpus ([`BRIEF`](../../results/M7-arm0b-corpus-mode-20260919/BRIEF.md)). **Un 3B sí usa lo que lee, cuando lo lee como se lo enseñaron — la memoria tiene un canal que funciona.** Abre dos cosas: `fluids-full` vuelve a pasar por la compuerta de release antes de que su región deje de mandarse afuera; y P45 (por debajo de la profundidad de entrenamiento), medido por el mismo camino, vuelve a estar abierto |
| **0c** | **el mismo miembro de vuelta por la compuerta, sobre la base donde corre el pool** — reentrenado sobre `Qwen3.5-4B`, mismo corpus y receta, modo corpus, los mismos 90 casos; tres pruebas de signos pareadas; Colab, dos sesiones | ❌ **[ran] — no liberado.** 80/90 contra su propio 90/90 (**0 : 10**, $p=0{,}002$); 80 : 0 contra el 4B pelado; 21 : 7 contra la frontera. Las diez son cadenas de venturi idénticas a las del 3B hasta la línea final, que el 4B escribe como un tag `<answer>` que el corpus nunca enseñó; el número verifica 10/10. La región sigue `out` · `results/M7-arm0c-fluids-rerelease-20260919` |
| **1** | **trayectoria oráculo.** Dos adaptadores sobre un subdominio, mismos casos: entrenados *con* las notas que el oráculo abriría, inyectadas por el protocolo `<search>`/`<open>`, y *sin* ellas. Puntuados sobre la familia entrenada y sobre su **hermana dejada afuera**, pareado | la cota superior: si leer exactamente las notas correctas no levanta a la hermana de ~1/20, ninguna navegación lo hará — **parar** |
| **2** | navegación aprendida: el experto emite sus propias consultas; recuperación por embeddings adentro de la base del subdominio. Medido **donde pasa** — se recuperó la nota necesaria, se abrió, se siguió — no sólo en la respuesta final | qué pierde la navegación contra la trayectoria oráculo |
| **3** | atribución: sólo notas enciclopédicas · sólo notas operacionales · las dos | qué clase de conocimiento lleva la ganancia — las dos clases, tasadas por separado |
| **4** | recuperación: léxica plana · embeddings · embeddings restringida a la trayectoria hasta ahora (enlaces y vecinos de la última nota abierta) | si una estrategia de trayectoria le gana a una búsqueda plana; el resultado previo del workspace dice no asumirlo |
| **5** | editar sin reentrenar: cambiar el coeficiente de una nota después de entrenar; la respuesta tiene que seguir a la base, no a los pesos | que el conocimiento vive donde se puede editar — **[ran] 2026-10-04 PASA: EDIT0**, `real-none-s0` sobre una copia de `knowledge/hazwaste-regs` con un número cambiado en cada uno de 17 enunciados de soporte (20 números), contesta **17/17** con el valor **nuevo** citado al enunciado editado, **0** obsoletas ([`BRIEF`](../../results/EDIT0-edit-without-retraining-20261004/BRIEF.md)) |

**Qué se reutiliza de `evolving-memory`, y qué dice su única medición — auditado [read]/[ran]
2026-09-19** (sugerencia del usuario; `EvolvingAgentsLabs/evolving-memory` en `a635898`, Apache-2.0,
su suite corrida acá: 184 pasan, 12 se saltean por falta de una API key). Es un motor de
*consolidación de trazas* — trazas de un agente comprimidas por un LLM en una estrategia con pasos
ordenados, embebida, recuperada por top-k plano. **No** es una base de notas escritas y editables, y
**ningún código suyo lee una arista para decidir qué recuperar después**: el grafo tipado se escribe
y nunca se recorre; el orden de los pasos es `ORDER BY step_index`. Así que el brazo de trayectoria
(brazo 4) es trabajo nuevo, no un port. Lo que se toma:

- **`resolver/` (~370 líneas) — el índice dual.** Cada ítem embebido dos veces, *qué es* y *para qué
  sirve*, se busca en la **unión** de ambos, y cada sub-puntaje se conserva en el match en vez de
  colapsarse — que es lo que hace falta para comparar tres brazos de recuperación. Las notas
  enciclopédicas y operacionales son esa misma división. Su boost de historial con tope
  (`MAX_BOOST = 0.05`: la popularidad desempata, nunca da vuelta la relevancia) se copia como regla.
- **Los dobles de prueba offline** — un encoder de bolsa de palabras hasheada y un índice de coseno
  exhaustivo, ~40 líneas — para que la base sea testeable en CI sin GPU y sin clave. Al tamaño de la
  base de un subdominio el índice exhaustivo *es* el índice de producción: un producto de matrices,
  sin librería ANN. **Con su bug arreglado primero:** agrupa por el `hash()` de Python, aleatorizado
  por proceso, y el test que sostiene la afirmación central de ese repositorio falla en 6 de 30
  semillas **[ran]**.
- **`storage/migrations.py` (95 líneas)** y la forma `nodes / children / edges(source, target, type,
  weight)`, con el vocabulario de aristas — contención, `NEXT_STEP`/`PREVIOUS_STEP`, enlaces
  cruzados — esta vez *leído* al recuperar.
- **`isa/parser.py` + el loop acumular-y-después-commitear de la VM**, si una trayectoria se emite
  como acciones: un parser de texto que nunca lanza, con los errores como datos, un loop de despacho
  acotado, y un registro del recorrido con el que puntuarlo.

Se deja atrás: el servidor FastAPI, el embedder sólo-Gemini importado en la raíz del paquete, los
tres proveedores de LLM atados a una API, el pipeline de consolidación por LLM (las notas acá se
escriben), faiss, y un `networkx` declarado y sin usar. El embedder es un modelo abierto chico
**servido en Colab** como todo otro modelo acá — nada corre en la máquina del usuario (instrucción
del 2026-09-19).

**Y su único benchmark honesto es un resultado negativo, que el brazo 4 hereda como prior.** Indexar
*para qué sirve* una cosa al lado de *qué es* no cambió nada: acc@1 80 % con cualquier peso de
mezcla, n = 10, el segundo embedding genuinamente distinto (coseno 0,753) — commiteado como *"medir
que no ayuda"*. Los errores son **dentro del tema**: el área correcta, el ítem equivocado adentro.
Ahí es donde una restricción de vecindario debería pagar, si algo paga, y también es una advertencia
de esperar un delta chico sobre la similitud plana. Con el resultado anterior de este mismo workspace
— una jerarquía perdió contra búsqueda léxica — son dos priors contra la estructura. El arnés viene
antes que el recuperador ingenioso, y un nulo se reporta como nulo.

**Compuerta.** Brazo 1: con-base le gana a sin-base en la familia hermana dejada afuera,
pareado, test de signos exacto, $p \le 0.05$ — y el brazo sin-base reproduce el colapso de P14
ahí, o la hermana no estaba fuera de la región y la corrida no dice nada.

**Falsificado por** un empate en la hermana bajo la trayectoria oráculo: a este tamaño, leer no
extiende una región ni siquiera con la página correcta abierta. Queda entonces un brazo barato:
lo mismo sobre el 4B del hito 1. Después de eso la pregunta es de la mitad grande de un par.

**El contrato de release crece un campo.** Un miembro es su corpus *y su base*: el manifiesto
registra la ruta y el hash de la base de conocimiento y el hash del índice de embeddings junto
al hash del corpus. El brazo 2 del router y la base comparten un modelo de embeddings, así que
un subdominio es una región de un solo espacio — lo que cae adentro se rutea al miembro, y lo
que el miembro busca se encuentra ahí.

**No se afirma hasta medirlo:** que una jerarquía ayude; que los embeddings le ganen a la
búsqueda léxica adentro de una base chica; que algo de esto transfiera de una suite generada a
una real.

**W1 [ran] 2026-09-19 — la primera biblioteca y su lint: PASÓ.** `memory/notes.py`, `memory/lint.py`,
`knowledge/nursing-iv/`: tres procedimientos de Open RN como esqueleto + 70 notas de paso, una wiki de
21 notas, una capa de sitio de ejemplo; ningún modelo involucrado. Compuerta, escrita antes —
$\text{pasa} \iff |\text{hallazgos}| = 0 \wedge \forall q: \text{recorrido}(q)$ existe — lint **0 hallazgos**,
recorridos del oráculo **72/72**, y la compuerta falla cuando se quita un paso
([`BRIEF`](../../results/M7-W1-library-20260919/BRIEF.md)). La primera corrida del lint encontró al
esqueleto de la propia especificación por encima de su propio límite (230 tokens > 150): un esqueleto
lista *etiquetas* de paso, no títulos. Sigue **W2** — el runtime, las capas y la guarda sobre el loop de
modo corpus, todavía sin modelo.

**W2 [ran] 2026-09-19 — el runtime: PASÓ.** `memory/runtime.py` (tres verbos, ids opacos re-sorteados por
conversación, presupuestos, la bitácora del recorrido), `memory/layers.py`, `memory/guard.py` — una función
de respuesta con estado, sobre `accept_rank.run_chain` **sin tocarlo**. Compuerta, escrita antes: cada
recorrido del oráculo reproducido como una generación guionada que lee sus ids de la propia salida del
runtime. **72/72** recorridos, 949 comandos, 0 rechazados, 0 mal formados, la guarda en silencio; los
valores de sitio llegan marcados (`8 [site]`), el `<calc>` de los 12 recorridos de caudal da la respuesta;
ningún id de la biblioteca en ningún texto mostrado. La regla de la guarda es
$\text{violation}(n) \iff \text{requires}(n) \setminus \text{opened} \ne \emptyset$: tres recorridos que
violan se cortan en `strict` y siguen en `recover`, y la compuerta falla sobre una biblioteca con un enlace
roto ([`BRIEF`](../../results/M7-W2-runtime-20260919/BRIEF.md)). **No medido:** si un *modelo* se recupera,
ni la búsqueda — acá es léxica y el oráculo consulta una nota por su propio `when`, así que su 72/72 en
rango 1 no dice nada sobre el ranking. El presupuesto de 24 aperturas de §3 quedaba por debajo del
procedimiento de 32 pasos de la biblioteca: ahora 48. Sigue **W3** — el radar R0 junto a esta base léxica.

**W3 — [ran] 2026-09-19: no pasa.** `memory/index.py`: por nota
$e_{\text{when}}, e_{\text{what}}$, $s(n\mid q)=\langle e(q),e_{\text{when}}(n)\rangle+\beta\langle e(q),e_{\text{what}}(n)\rangle$,
los 3 primeros, un `Searcher` que el runtime toma sin cambios, el codificador inyectado (acá no corre ningún
modelo, nunca). Las consultas que cuentan se escribieron **después** de congelar el diseño: **P**, una
paráfrasis de cabecera por nota (94 objetivos, solapamiento medio de palabras con el objetivo 0,039, 56
consultas en cero) — la compuerta; **E**, los 72 enunciados → la primera nota del recorrido del oráculo
(4 objetivos) — al lado. El recall@3 del buscador por palabras es **0,064 en P** y 0,125 en E: hay margen, y
en P un piso *por construcción*, así que "le gana al léxico" solo sería un trámite y el veredicto exige además
recall@3 ≥ 0,80. Falsado si R0 apenas empata con el buscador por palabras — entonces el radar no tiene trabajo
a este tamaño de biblioteca y W5 corre sobre búsqueda léxica
([`BRIEF`](../../results/M7-W3-radar-r0-20260919/BRIEF.md)).

**R0 [ran] 2026-09-19 — le gana a un buscador por palabras y no alcanza.** `Qwen3-Embedding-0.6B`, una sesión de L4: en P
recall@3 **0,638** contra 0,064 del léxico, pareado **56 : 2** — y por debajo del 0,80 escrito antes de correr, así que W3
**no pasa**; β = 0,5 le gana a sólo-`when:` 30 : 4. Dónde están los 34 fallos: 13 en rango 4–6 (recall@6 0,777,
recall@10 0,830), 16 más allá del 10, cuatro de los cuales se resuelven dentro de su propio estante. No se afloja nada y el
conjunto no se retoca (rediseños: 0). Dos consecuencias: **W5 cuenta un fallo de recuperación aparte del puntaje del experto** — o
corre sobre los resultados de búsqueda del oráculo — y la brecha es de **W6 (R1)**, medida sobre conjuntos nuevos, nunca más sobre P.

**W4 [ran] 2026-09-19 — el corpus del hábito: PASÓ.** `training/nursing/generate_walks.py` no escribe ninguna
observación: cada fila es un plan *pasado por* `memory/runtime.py` dentro de `run_chain`, el bloque de verbos
por `render_tools` (`memory/prompt.py`, el único lugar donde se escribe el prompt de un miembro), la página
llevada por `Conversation.resume`. Compuerta, por fila, con $V$ los valores leídos de un hueco o de un `<calc>`
y $N$ los números que el enunciado dice: $V(r)\cap N(r)=\varnothing$ — **0** de 740; ningún recorrido ni caso
evaluado en el corpus — **0** de 140; ninguna apertura de las 17 notas que son solo de `discontinue-iv` —
**0** de 600; cada fila reproducida byte por byte por el árbitro en `strict` — **0** fallas; cada cláusula
rota una vez por un test. 600 filas en cuatro familias (avanzar 286 · dosis 144 · cantidad 108 · *no está en
mi biblioteca* 62), de 0 a 9 notas abiertas, 24 callejones sin salida deliberados, y los mismos 600 casos sin
verbos como segundo brazo de W5. **Apartado: `discontinue-iv`** — las dos infusiones comparten 11 líneas de la
fuente casi palabra por palabra, así que apartar cualquiera mediría un hermano memorizado; el retiro comparte
4 y 6 líneas genéricas, y los 24 de sus 80 recorridos de evaluación que terminan en una están marcados. **Un
recorrido de 32 pasos no entra en `max_seq` 1536 y no se trunca:** una tarea es una ventana de 1 a 8 pasos, y
la que entra por el medio lleva su estado — por la última página del árbitro, o encontrando su lugar por el
esqueleto y una búsqueda (dos verbos; seguir una página es uno, y una sola herramienta es copiar **[ran]**
P13). La fila más larga mide 1 298 tokens con el tokenizador de la base. Un rediseño, de la cláusula de
enunciados de G2, anotado en el brief. Sigue **W5**, el brazo que puede matar la memoria; si R0 gana W3 el
corpus se regenera antes con el índice
([`BRIEF`](../../results/M7-W4-corpus-20260919/BRIEF.md)).

**El evaluador de W4, reemplazado antes de que nada se leyera a través de él (rediseño 2) [ran]
2026-09-19.** Una revisión adversarial lo encontró mal en los dos sentidos: una paráfrasis del paso
correcto fallaba (subcadena exacta, con marcador `[site]` y todo — 57 de las 80 filas apartadas), y
*"15 años … espera 8 segundos"* aprobaba un chequeo de 15 segundos. `training/nursing/grade_walks.py`
lee sólo la línea final; un número cuenta sólo pegado a su unidad; un paso se *atribuye* entre las 70
notas de paso, $s(n)=|W(\text{línea})\cap W(n)|/|W(n)|\ge 0{,}5$, con los números que la nota
aporta; el recorrido se lee del registro del árbitro. `right` · `format` · `unread` · `wrong`. Las 740
filas del oráculo son `right` bajo él; no se regeneró ninguna fila. Un tercer rediseño termina el paso.

**W5 [ran] 2026-09-19 — NO PASA TAL COMO ESTÁ ESCRITO.** En el titular (n = 56) el brazo con biblioteca
saca **35**, el base sin entrenar leyendo las notas del oráculo **45**, el brazo sin biblioteca 2, el base
sin entrenar navegando solo 0. `withlib` vs `nolib` 35 : 2 y vs `base-walks` 35 : 0 — pero **vs
`base-reads` 6 : 16, $p = 0{,}052$**: un empate que se inclina a derrota, y el veredicto pide *ganar*.
Doce de las 21 fallas son una sola: la nota retenida da dos valores para una cantidad, ninguna fila de
cantidad entrenada leyó una nota así (0 de 108), y el adaptador responde el primer valor — 11/12 cuando
se pide el primero, 0/11 cuando se pide el segundo, el base que lee acierta las 12. Ocho son
`carry/middle-find`, donde el base también falla 5. La navegación sí se transfirió: 0 fallos de
recuperación en el titular, 3 verbos rechazados en 140 recorridos contra 368, control 58/60 contra 41/60.
Rediseños: 0; el corrector no se toca. **La composición — el adaptador recorre, el base pelado escribe la línea final — [ran] W5b: quedan 0 de
las 12 fallas de cantidad, y en todo lo que al adaptador se le enseñó el base lee peor (control 39 contra 58), así
que es atribución, no un diseño de servicio. Sigue, a decisión del usuario:** una biblioteca y un corpus que
muestren notas de dos valores dentro de procedimientos entrenados, los dos adaptadores reentrenados, medido sobre
un conjunto retenido nuevo
([`BRIEF`](../../results/M7-W5-kill-arm-20260919/BRIEF.md)).

**W5c — el brazo de la forma del corpus [ran]: FALSADO, ver el resultado abajo.** *(Como se pre-registró:)* La fuente no tiene ninguna
afirmación de dos valores dentro de los procedimientos entrenados (revisado línea por línea), así que la forma
sale de **A** la única oración real del capítulo (equipos de macrogoteo contra microgoteo, verificada byte a
byte, ahora el cuerpo de `rates/drop-factor`) y **B** oraciones que un sitio AGREGA a siete notas entrenadas
(`Site.adds`; **contenido de ejemplo inventado, aprobado por el usuario y marcado como inventado**). Corpus v2
(`data_walks_v2/`, generador por importación, v1 intacto): 153 de 600 filas piden uno de los dos valores de una
nota, mitad cada uno, la condición explícita o implícita; "copiar el primer número" vale 0,51. Conjunto retenido
nuevo (88; titular 66) y control (80); compuerta v2 PASÓ, piso 6/66, corte de margen 61/66. Falsador, exacto y
en código: crédito ≤ 4/15 en el corte condicional es indistinguible del 0/11 de W5 (Fisher). Los pares de W5 se
vuelven a preguntar sobre el titular nuevo; un empate es un empate ([`BRIEF`](../../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).

**Resultado de W5c [ran] — el diagnóstico queda falsado: 4 de 15.** El crédito en el valor condicional sobre el
set retenido nuevo es 4/15 contra el 0/11 del primer corpus (Fisher $p=0{,}091$; la banda ≤ 4 se fijó antes de
correr). El par de W5 sobre el titular nuevo ($n=66$): `withlib` 42, `base-reads` 46 — **12 : 16, $p=0{,}57$, un
empate: no pasa**; contra `nolib` 39 : 0, contra el base caminando 42 : 0. Las 14 fallas de cantidad tienen el
recorrido limpio y `base-reads` las acierta; el adaptador escribe **el primer número, como un entero** (pedían 22
→ `7 minutes`; `5-10` → `5`). En las ocho notas que entrenó sí lee la condición (17/18): aprendió esas notas, no
la habilidad. Lo que v2 sí compró es navegación: línea compartida 22/22 (base 8), `middle-find` 14/22 (base 5),
control 78/80 (base 56). Sigue, a decisión del usuario: partir por tipo de tarea (exploratorio, post-hoc sobre el
set de W5: 47/56), entrenar más suave, o muchas más notas — que es la opción E.

**W5, tal como se construyó y pre-registró.** `training/nursing/walks_arm.py`: `base-reads` (base
sin entrenar, las notas del oráculo abiertas), `base-walks`, `nolib`, `withlib`. Primero la sesión de
margen: `base-reads` con ≥ 51/56 en el titular detiene el paso antes de entrenar. Titular n = 56
(apartado, profundidad ≤ 9, línea final no compartida); al lado las 2 filas de profundidad 15, las 22
de línea compartida, cantidad por capa, control sin `rate`, fallos de recuperación, `context`,
`format`. Piso de la política trivial **3/56** [ran]; el oráculo es 140/140 por la misma función
([`BRIEF`](../../results/M7-W5-kill-arm-20260919/BRIEF.md)).

## 2. La familia, y la alternativa

**Adoptada, 2026-09-25: Gemma 4** — `google/gemma-4-E4B-it` para todo miembro nuevo; `gemma-4-12B-it` para la
mitad grande (~~`gemma-4-31B-it`~~ — decisión del usuario, para correr en una Mac mini), medido en B2–B5. B1 **[ran]**: un empate con Qwen3.5-4B en W9 (38 contra 35, 35), que por la
regla del usuario escrita antes de la comparación elige a Gemma. El bloqueo de P29 se levanta excluyendo las
torres de visión/audio. Todos los miembros liberados
se movieron: `email-full@v3` (M1b [ran]), `desk-commitment@v3` (M1d [ran]), `distributor-wiki@v2` (B5 [ran]); Qwen 2.5
sigue siendo el brazo de control.

**Previa: Qwen 3.x** (`Qwen3.5-4B`, `Qwen3.8-27B`) — un espacio de ids **[ran]** D0,
la familia de cada release hasta ahora. ~~Adoptada: Qwen 3.x … Alternativa, no ahora: Gemma 4, bloqueada en
PEFT [ran] P29.~~

**Dos runtimes, decisión del usuario 2026-09-28.** `server` es vLLM en Colab — todo entrenamiento y toda
medición se quedan ahí, sin cambios. `edge` es **llama.cpp en la propia máquina del usuario** (una
MacBook Air M4, 16 GB) — sirviendo un miembro a un runtime en vivo (OpenClaw): el E4B como GGUF **Q8_0**
(Q4_0 le da vuelta al id de un pedido con el propio caché de prompt de llama.cpp **[ran]**
LIVE-distributor) más el LoRA del miembro convertido a GGUF, cambiado en caliente por pedido o por
`POST /lora-adapters` en ~3 ms (**[ran]** MAC2). La distribuidora corrió 6/6 en vivo así, con
**Claude Haiku 4.5** escribiendo el único turno fuera de alcance (**[ran]** M10). MLX se queda como
banco de investigación — acceso en Python al grafo, cambio de puntero en caliente 2,9 µs (**[ran]**
MAC) — ~~y se queda como motor de `edge`~~: ese veredicto era sobre decodificación especulativa
solamente (el propio resultado del drafter en MAC2), no sobre serving, que es lo que `edge` nombra
ahora. Un resultado de `edge` es un brazo distinto del mismo miembro sobre `server` bf16/FP8, y lo dice.

## 3. Reglas que sigue cada paso

Las reglas de medición que se pagaron están en [`../../CLAUDE.md`](../../CLAUDE.md) §3.
Las cuatro que deciden la forma de un paso:

- **Headroom antes del tratamiento** — el piso tanto como el techo.
- **El brief antes de la corrida**: qué, por qué, qué modelo, qué proveedor, qué lo
  falsifica, en `results/<run>/BRIEF.md` antes de que arranque el chain.
- **Una incógnita por corrida**, y el veredicto se lee del archivo, nunca del código de
  salida.
- **Contar los rediseños.** Una vez está bien, dos veces es sospechoso, la tercera está
  buscando el resultado. La condición de parada va en el brief.

## 4. Bitácora de agentes y skills

| fecha | cambio | por qué |
|---|---|---|
| 2026-09-19 | `alpha-runner` → `deprecated/`; se sacó el skill `alpha-surface` | el instrumento de aceptación a nivel de carácter que manejaba medía formato, no acuerdo (S0), y se sacó con la reescritura |
| 2026-09-19 | se mantienen: `colab-runner`, `headroom-auditor`, `instrument-skeptic`, `mirror-keeper`; skill `experiment-brief` | cada uno tiene un paso en §1 |

## 5. Historia

- **2026-10-04** — **Cambia el miembro servido del tracker: `tr-out-s0` en lugar de `tr-s1`, decisión del usuario sobre ROUTE1; junto con eso, se evaluó la línea flash.** El propio comando de `examples/tracker/live_tracker.py` ahora dice `llama-server … --lora lora-tracker-out-s0-f16.gguf` y `gateway --member tr-out-s0`; **el registro [ran] de LIVE-tracker queda como que corrió `tr-s1`** — el cambio es prospectivo, no una repetición de esa corrida en vivo. Todo documento que nombra al miembro servido del tracker o su comando de serving se actualizó con el cambio (`SERVING.md`, `OPENCLAW.md`, `GUIDE.md`, `ARCHITECTURE.md`, `README.md`, este plan). **Junto con esto se evaluó cuánto vale la línea flash** ([`docs/flash-inference/00-analysis.md`](flash-inference/00-analysis.md) §8): mejores resultados es **desconocido**, y la evidencia hasta ahora dice que no — ninguna región muestra todavía al 26B MoE ganándole al miembro E4B, y TEACH0 (la corrida de techo que lo mostraría) está bloqueada por el motor de serving y el cupo de A100; el mecanismo de ruteo en sí **funciona** para decode **[ran]** (el 93 % menos bytes por token a 8 GB de H1A); a qué velocidad es plausible para decode en una máquina de 16 GB con una caché de expertos de 4–6 GB, con el prefill y la porción de memoria para la caché KV como los riesgos abiertos (derivado, no medido). El pago de la línea todavía espera a TEACH0.
- **2026-10-04** — **ROUTE1 [ran]: ABSTIENE — el miembro del tracker ya llega a la frontera de su rol, el router para tareas abiertas cubre las tres organizaciones.** `tr-out-s0` (la receta de M10: el corpus de `tr-s1` más 126 turnos de abstención, 9 %, un tercio sin bloque por rol) abstiene en **27 de 30** turnos fuera-de-alcance reservados (14/16 fuera del tracker, 13/14 fuera del rol) contra el **0/30** de `tr-s1`, pierde **0** de los 160 turnos dependientes que `tr-s1` contesta bien, y no abstiene en ningún turno dentro de alcance. Las tres veces que no abstuvo, leídas donde pasan: un pedido de un desarrollador de redactar un mensaje (contestado local, bien), un "que me traigan un café" de un líder (se creó un issue para eso — el daño que la abstención existe para prevenir, ahora 1 de 30 en vez de siempre), un pedido de QA por una página de sprint board que no existe. **Con esto, el router para miembros de tarea abierta es el rol más la abstención de cada miembro en las tres organizaciones medidas: escuela, distribuidora (M10), tracker (ROUTE1).** Servir `tr-out-s0` en lugar de `tr-s1` quedó **decidido el mismo día** (viñeta de arriba) ([`BRIEF`](../../results/ROUTE1-tracker-abstain-20261003/BRIEF.md)).
- **2026-10-04** — **EDIT0 [ran]: EDITS HOLD — pasa el brazo 5 del hito 7, editar sin reentrenar.** Una copia de `knowledge/hazwaste-regs` con un número cambiado en cada uno de 17 enunciados de soporte de las filas de PAGE0 (20 números, nada más tocado): `real-none-s0`, que nunca vio esta biblioteca, contesta **17/17** filas con el valor **nuevo**, cada una citada al enunciado editado, **0** obsoletas (barra ≥ 16/17 con como mucho 1 obsoleta). El contenido que entrega un miembro viene de la biblioteca, no de sus pesos. Al lado, sin GPU: un `put` de opmemory sobre una clave existente reemplaza su valor y nunca deja una copia obsoleta. Prueba la propiedad de sobreescritura de Spotlight Memory de Percepta (`docs/review/moe-distillation-and-spotlight.md` §3) sobre la memoria propia de este proyecto ([`BRIEF`](../../results/EDIT0-edit-without-retraining-20261004/BRIEF.md)).
- **2026-10-04** — **P2a [ran]: LAS PARÁFRASIS CUESTAN — ROUTE2 no se construye.** ¿Un miembro del pool contesta una paráfrasis de su tarea? `email-full` sobre email empata con lo verbatim (469 → 470) y `desk-commitment` sobre la banda superficial empata (240 → 240), pero la banda profunda — una regla compuesta ("la última promesa cuenta") adjunta a la pregunta — retrocede, **239 → 198** (1 : 42 pareado). Leído donde pasa: 12 de 16 reformulaciones profundas puntúan 15/15; la pérdida está en cuatro, dos de las cuales caen a 0/15 — los miembros siguen una *pregunta* reformulada pero no de forma confiable una *regla* adjunta a ella. Una sonda de router que mantuviera local cada paráfrasis (ROUTE2, propuesta en el documento de revisión §2.1) serviría mal esas cuatro reformulaciones; no se construye. La regla literal de ROUTE0 — fuera de la redacción, sale hacia la frontera — sigue siendo la correcta ([`BRIEF`](../../results/P2A-paraphrase-headroom-20261004/BRIEF.md)).
- **2026-10-04** — **H1A [ran]: FALSIFICADA como se escribió sobre su única cláusula sin margen; el dominio concentra fuerte el ruteo de `gemma-4-26B-A4B-it`.** El usuario aprobó reanudar la línea flash (en pausa desde la Fase 0 de `docs/flash-inference/00-analysis.md`) el 2026-10-04. A 8 GB, prompts del dominio: la caché precargada por afinidad le gana a LRU por **+7,4** puntos (99,5 % contra 92,1 %), por debajo del **≥ 10** de la compuerta — pero LRU ya estaba en 92,1 %, así que el margen no tenía dónde crecer, marcado `no_headroom` por el propio instrumento. Las otras dos cláusulas pasan con comodidad: los bytes leídos por token de decodificación bajan **93 %** (62,4 → 4,1 MB), ganando en 60/60 prompts; Jaccard ponderado dentro del dominio **0,49** contra **0,26** entre dominios (120 : 0). El 80 % de las activaciones de decodificación de un dominio cae en 17–21 % de los expertos (40 % en texto general); el control de texto general va al revés (afinidad −6 puntos), así que la ganancia es del dominio, no de la política de anclaje. H1b (un adaptador sólo-atención concentrándolo más) y M3 (streaming real de SSD) son decisión del usuario, todavía no tomada ([`BRIEF`](../../results/H1A-moe-routing-by-domain-20261004/BRIEF.md); [`docs/flash-inference/00-analysis.md`](flash-inference/00-analysis.md) §7).
- **2026-10-04** — **TEACH0 bloqueada por el motor de servido y la cuota de A100, sin resultado.** FP8 falló dos veces (compilación de inductor; después el kernel FP8 de vLLM no corre en el sm80 de la A100); el único reintento con bitsandbytes del brief espera cuota de A100. Los resultados viven en la rama `teach0-20261004`, no mergeada acá. Si `gemma-4-26B-A4B-it` le gana al miembro E4B sin entrenar — la compuerta para cualquier destilación o cambio de base — sigue sin respuesta.
- **2026-10-04** — **análisis de dos propuestas externas (MoE + destilación, Spotlight Memory), con un plan — no un resultado** ([`docs/review/moe-distillation-and-spotlight.md`](review/moe-distillation-and-spotlight.md)). El §1 pone sobre la mesa lo que el proyecto ya midió y pesa sobre las dos: en cada región medida, un modelo más grande no compró precisión, entrenado ni sin entrenar (B3, B5, PAIR0, PAIR1). El §2 lee la propuesta de MoE punto por punto contra ese piso — un router destilado en una sonda sobre el estado oculto de la base (probar primero P2a y después ROUTE2, la falsificación más barata primero), destilación desde un maestro 26B (con compuerta en una sola corrida de margen, TEACH0, ya que el alumno propio de este proyecto ya igualó a todo modelo más grande medido), poda de expertos por dominio al estilo REAP (su primer paso es exactamente H1a, de la propia línea flash), y el 26B como base de cada miembro (no se propone; la decisión del usuario de E4B del 2026-09-25 se mantiene a menos que TEACH0 pase). El §3 lee *Spotlight Memory* de Percepta: la arquitectura misma necesita preentrenamiento desde cero y no se puede adoptar sobre una base Gemma afinada, pero tres de sus propiedades ya mapean sobre la memoria de este proyecto, y una — la sobreescritura de una clave que reemplaza su valor con tasa obsoleta cero — nunca se midió acá (**EDIT0**, propuesta). El §4 ordena cinco pasos pre-registrados, la falsificación más barata primero (EDIT0, P2a, ROUTE2, TEACH0, H1a); H1a y cualquier cambio de base quedan como decisiones del usuario. **Estado 2026-10-04, el mismo día:** EDIT0 pasó, P2a encontró LAS PARÁFRASIS CUESTAN (ROUTE2 no se construye), H1a FALSIFICADA como se escribió con su sustancia sosteniéndose, TEACH0 bloqueada — ver las entradas de arriba y el §4 del documento de revisión.
- **2026-10-03** — **PAIR1 [ran]: EMPATE — el miembro que pide la propia definición del par empata con el miembro E4B** ([`BRIEF`](../../results/PAIR1-large-member-20261003/BRIEF.md)). PAIR0 encontró al 12B pelado peor que al E4B pelado sobre documentos reales, pero el tamaño sin entrenar no es el diseño propio del par — las dos mitades se entrenan sobre el mismo corpus. Los intentos de entrenamiento 1 y 2 se quedaron sin memoria en la ventana de 4.096 en una A100 (el intento 2 por el tamaño exacto del tensor de logits de 4,00 GiB contra 4,00 GiB libres); un intento 3 en H100 fue rechazado por cupo tres veces, el límite que marcaba el brief. `s4_train.span_logits_loss` — probado **[ran]** igual a la entropía cruzada desplazada propia de HuggingFace sobre un LM causal diminuto, con y sin acumulación (`tests/test_span_logits.py`) — dejó terminar al intento 4 sin cambiar el corpus, la receta ni las varas. Entrenado, `real-none-12b` empata con `real-none-s0` sobre el registro de PAGE0: 33/44 contra 34/44 respondibles, pareado 5 : 6 ($p = 1,0$), 23/30 contra 24/30 multi-hop, 10/14 one-hop y 7/8 rechazos los dos, y 33/44 contra el registro de FMT0 también — **EMPATE**, una segunda región (con B3) donde un miembro grande no compra precisión; el par especulativo se queda como resultado de velocidad (B4, F0, C0, F0c) sin una región que lo necesite. Entrenado, el 12B camina limpio (0 líneas de pensamiento contra los cientos del 12B pelado en PAIR0) — el protocolo que fallaba el 12B pelado de PAIR0 era el entrenamiento, no el tamaño. Una observación al lado del veredicto, no un reclamo: los miembros se equivocan en filas distintas (39/44 correctas por cualquiera de los dos); elegir entre ellos por pedido está sin probar.
- **2026-10-03** — **F0c [ran]: identidad de la salida a temperatura 0, establecida — bf16, una A100.** F0b no pudo probarlo en una L4 en FP8 porque el control plano-contra-plano mismo no era determinista ahí; en bf16 sobre una A100, con `VLLM_BATCH_INVARIANT=1`, el control es idéntico en cada conjunto (16/16, 8/8, 16/16, 8/8) — el motor es determinista acá. Contra eso, la especulativa con el drafter MTP nativo: base/dominio 16/16, base/general 3/8, LoRA/dominio 14/16, LoRA/general 8/8. Leído donde diverge: las dos divergencias de LoRA/dominio ocurren *después* de una etiqueta de cierre que esta prueba sin herramienta decodifica de más para inventar una línea de resultado — un recorrido servido se detiene en esa etiqueta, así que **hasta cada corte, 16/16 concuerdan, a 1,98×**; LoRA/general es 8/8 directo. Los 5 de 8 cambios de base/general son elecciones de sinónimos en casi-empates, un artefacto de la forma de verificación al puntuar varias posiciones en una sola pasada, no una falla de la regla de aceptación. **Lo que esto establece:** con el LoRA propio del experto, en su propio dominio, la decodificación especulativa preserva lo que escribe un recorrido servido hasta cada corte; la identidad bit a bit no es una garantía general de vLLM, y sobre texto general — que sirve la frontera, no un miembro — los sinónimos todavía cambian ([`BRIEF`](../../results/F0c-identity-bf16-20261003/BRIEF.md)).
- **2026-10-02** — **FMT0 [ran]: FALSEADO — un corpus de formato entrenado bajo la forma de página servida no le gana al base, y el chequeo de margen que lo habría dicho antes ya estaba en disco.** `real-fmt-s0` (el corpus de REAL4 recorrido bajo `page_top = 8`, 320 filas, un recorrido de cada tres leyendo un error de la guarda `recover` sobre un número de sección abierto y continuando, esa apertura afuera de la pérdida con máscara de tramo) contra `real-none-s0` servido con `--guard recover`, los dos contra `real-none-s0` servido `strict` (el base), sobre el conjunto de 52 filas de PAGE0: los tres brazos anotan **33/44**; tratamiento contra base pareado **1 : 1** ($p = 1,0$); el runtime solo (`recover`, sin reentrenar) **0 : 0** contra `strict`. Bajo la forma servida de top-8, las 11 fallas del base tenían una línea faltante y ninguna cita mal formada — nada en este conjunto para que el corpus reparara. El error de instrumento asumido: el margen se chequeó sobre los tres conjuntos de lectura más viejos bajo `strict` (9 de 42 fallas eran de formato, sobre todo la guarda terminando recorridos y páginas leídas enteras — dos cosas que top-8 y `recover` ya habían cambiado), no sobre el propio brazo top-8 de PAGE0 ya en disco (1 falla de formato en 10) — la regla "chequear el margen antes de construir el tratamiento" se aplicó sobre el base equivocado, costando una sesión de A100 y una de L4. La línea de corpus de formato se detiene acá ([`BRIEF`](../../results/FMT0-format-corpus-20261002/BRIEF.md)).
- **2026-10-02** — **PAGE0 [ran]: PAGE TOP AYUDA, no WORKS — adoptado como default servido.** Una cuarta familia real ingerida textual (`knowledge/hazwaste-regs`, 40 CFR Parte 262, 69 páginas, 1.103 enunciados, 162 enlaces), 52 preguntas congeladas a ciegas, oráculo 52/52: `memory.runtime.Conversation.page_top` abre una página de más de 8 enunciados con los 8 mejores de la pregunta por BM25, en orden del documento, el resto como anclas abribles. `real-none-s0` con `+top8` contesta **34/44** contra el **30/44** de la página sin cambios, pareado 6 : 2 ($p = 0,29$) — 3 victorias son desbordes de contexto que la página más chica evita, 3 reparan la falla de enunciado-equivocado-en-la-página-correcta para la que se construyó (enunciados equivocados en la misma página 8 → 6), las 2 derrotas mantienen a la vista cada enunciado necesario, los recorridos cargan 3,2× menos texto. **La decisión del usuario, 2026-10-02: `page_top = 8` sale como default servido** (`examples/library/serve.py --page-top`; `--page-top 0` lo apaga) ([`BRIEF`](../../results/PAGE0-page-top-20261002/BRIEF.md)).
- **2026-10-02** — **BOK0 [ran]: BOK AYUDA tal como está escrito, no BOK WORKS — no se prende.** Cómputo en tiempo de prueba bajo la compuerta: el recorrido 1 es el brazo servido voraz; sólo donde la compuerta lo retendría, se muestrean hasta tres recorridos más y se entrega el primero que la pasa, calificado estrictamente. Agregado sobre los conjuntos de 52 filas de CITE0 y REAL4: 16 filas remuestreadas, 39 recorridos extra, ganancia **4** contra nuevas incorrectas **3** (prueba de signo exacta $p = 1,0$, por debajo del $p\lt 0,05$ y ganancia ≥ 5 de WORKS); entregadas correctas 72 → 76 de 88 → 95 entregadas. Un primer recorrido que pasa la compuerta es correcto 72/88 (82 %), uno remuestreado que la pasa sólo 4/7 (57 %) — la trampa de que la compuerta se superpone con el calificador, nombrada antes de la corrida, medida: muestrear hasta que la compuerta pase encuentra una cita que acepta, no necesariamente la de soporte, y las 3 filas nuevas incorrectas son exactamente eso. 9 de 16 filas remuestreadas fallan cada recorrido de la misma forma (sin línea final, o una cita sin `§sección`) — el hábito del miembro, no el azar. **No se prende.** El intento 1 se detuvo antes de calificar — un recorrido 1 que desbordó el contexto dejó el brazo antes de que el remuestreo lo viera; arreglado, los dos conjuntos recorridos de nuevo desde cero para este resultado ([`BRIEF`](../../results/BOK0-best-of-k-20261002/BRIEF.md)).
- **2026-10-02** — **GATE0 [ran]: LA COMPUERTA FUNCIONA — sale prendida por defecto.** El chequeo de citación del runtime (`memory.runtime.citation_problem`, `Conversation.final_problem`, `examples/library/serve.py --cite-gate`) aplicado como compuerta dura en vez de pista, repetido exacto — sin GPU — sobre 14 brazos `+page` retenidos de REAL3–REAL7 (532 recorridos, dos bibliotecas): respuestas correctas entregadas **275/275** (0 bloqueadas), filas respondibles incorrectas entregadas **79/165** (86 bloqueadas, 52,1 %), respuestas a preguntas sin respuesta entregadas **0/11** (11 bloqueadas), precisión de lo entregado 0,625 → **0,777**. El costo que el titular esconde: de las 86 bloqueadas, 43 tenían el valor incorrecto y 43 tenían el valor correcto bajo una cita que falla — por valor la compuerta retiene 43 de 347 valores correctos (12,4 %), subiendo la precisión de valor entregado 78,9 % → 85,9 %. **La decisión del usuario, 2026-10-02: la compuerta sale prendida por defecto en el endpoint servido, aceptando el costo de 43 de 347 valores correctos retenidos; `--no-cite-gate` la apaga** ([`BRIEF`](../../results/GATE0-cite-gate-20261002/BRIEF.md)).
- **2026-10-02** — **CITE0 [ran]: FALSEADO como pista.** `cite_check` (lee sólo el propio registro del referí, nunca la respuesta) corrido sobre un conjunto fresco de 52 filas de una tercera familia (40 CFR 112, escrito a ciegas después de congelar el diseño): base `withlib-s0+page` **32/52** (titular 18/30, un salto 8/14, negativas 6/8) contra `withlib-s0+page+check` **33/52** (19/30, 8/14, 6/8); el chequeo disparó en 6 filas, convirtió 0, rompió 0. Cada línea rechazada ya era incorrecta (6/6); con el replay offline de LIVE-library2, 15 disparos, 0 sobre una respuesta correcta — un detector sin falsa alarma que un miembro chico no puede aprovechar. La clase de falla más grande que queda (7 de 20) — un enunciado que tiene el valor preguntado pero no es el que se pedía — le sigue siendo invisible. No se repite: el próximo uso es como **compuerta**, no como pista ([`BRIEF`](../../results/CITE0-runtime-check-20261002/BRIEF.md)).
- **2026-10-02** — **LIVE-library2 [ran]: SIN CAMBIO — las dos pérdidas del edge reparadas, el puntaje no las sigue.** Los dos ítems que debía LIVE-library: `examples/school/gateway.runtime_request` saca el sobre de mensaje encolado de OpenClaw, y `memory.runtime.Conversation.page_budget` (servido a 2.500 tokens por `examples/library/serve.py`) abre una página que supera el presupuesto con sus enunciados en orden BM25 contra la pregunta hasta el presupuesto. Las mismas 52 preguntas: **37/52** — titular 16/23, negativas 14/16, un salto 7/13 — contra el 36/52 propio de esta corrida y el 38/52 de REAL4 sobre vLLM; **0** desbordes de contexto (4 antes), **0** sobres (3 antes), pareado contra LIVE-library **3 : 2** ($p = 1,0$). Veredicto tal como está escrito: **SIN CAMBIO** — 0 desbordes pero 37 < 38, no REGRESADO (titular y negativas pasan sus barras, sin derrota pareada). Las tres victorias son exactamente las filas que le había costado el edge; una pérdida nueva, `none-9`, es el presupuesto poniendo a la vista el enunciado que mejor coincide con una pregunta que la biblioteca no puede contestar. ~~Pendiente: por qué OpenClaw retiene un turno terminado después de que el endpoint ya respondió, en 3 filas~~ — **encontrado y resuelto, 2026-10-02:** las retenciones eran node quedándose adentro de `process.exit()` después de una corrida exitosa; `live_library.run_turn` ahora corre cada turno en su propio grupo de procesos y lo termina poco después de la propia línea de fin de corrida de OpenClaw en vez de esperar una salida que puede no llegar, y `serve.py` ahora siempre responde a un recorrido que lanza una excepción en vez de cerrar el socket — lo que hacía que OpenClaw reenviara un turno como sobre, para empezar ([`BRIEF`](../../results/LIVE-library2-20261002/BRIEF.md)).
- **2026-10-02** — **ROUTE0 [ran]: PASA — un router factorizado se vuelve el default del proxy.** `training/harness/factored_router.py`, sin GPU, sin modelo: local a un miembro si y sólo si exactamente un párrafo no es contenido del miembro y es una de sus tareas. Conjuntos frescos, escritos a ciegas del código de la regla: texto ajeno (600) servido localmente **0** contra el 294 del diccionario; remitentes no vistos (120) **0** perdidos contra el 7 del diccionario; tarea primero (120) **0** perdidos contra 3; envueltos por OpenClaw (120) **0** perdidos/mal rutados; paráfrasis (120, reportadas, nunca filtradas) **0** quedan locales, por diseño. La pared que golpeaban los tres brazos de pedido entero (remitentes no vistos, 120/120 perdidos) desaparece; se vuelve el default del proxy, `openai_proxy --router factored` ([`BRIEF`](../../results/ROUTE0-factored-router-20261002/BRIEF.md)).
- **2026-10-02** — **PAIR0 [ran]: SIN MARGEN — antes de entrenar un miembro 12B para la región de documentos reales, las dos bases peladas bajo el runtime servido.** `base-walks+page+top8`, el conjunto de 52 filas de PAGE0 sobre `knowledge/hazwaste-regs`: `gemma-4-E4B-it` respondibles **21/44** contra `gemma-4-12B-it` **11/44**, pareado **2 : 12** ($p = 0,013$); negativas **8/8** contra **1/8**; todo (52) 29 contra 12. **El intento 1 fue VOID:** el 12B pelado abrió su canal de pensamiento con el pensamiento apagado y dio vueltas en él hasta agotar el presupuesto de llamadas (34 de 43 fallos, sin cita) — arreglado con `wiki_arm --empty-thought` (un canal vacío prellenado); queda anotado un canal residual (254 líneas cortas de `thought` en las 52 caminatas, dentro del presupuesto) y una segunda corrección no gastada. Ninguno de los dos resultados pre-registrados queda como se escribió (no es empate, es una derrota); tampoco se entrena un miembro 12B para esta región, y el par especulativo se queda como resultado de velocidad sin una región que necesite la mitad grande ([`BRIEF`](../../results/PAIR0-large-headroom-20261002/BRIEF.md)).
- **2026-10-01** — **REAL7 [ran]: FALSEADO — los recorridos señuelo de enlace cruzado dejan la citación sin cambios** ([`BRIEF`](../../results/REAL7-crosslink-20261001/BRIEF.md)). REAL6 leyó dónde fallan las citas de REAL5: una fila de varios saltos cita un enunciado al **inicio** de un enlace que tiene el mismo número que la respuesta en su **extremo**. El único cambio: `real_corpus.build_crosslink` agrega 98 recorridos de dos saltos cuya respuesta está en el extremo de un enlace mientras el mismo número está en la página señuelo de la que parte el recorrido (Claude Haiku, $0,46); la familia de entrenamiento gana 49 CFR 390/392/393/397 (`knowledge/regs-train2`) para encontrar suficientes enlaces así, las bibliotecas de evaluación quedan intactas. Gate G1–G6 pasado (418 filas, 212 de dos saltos); misma receta con máscara de tramo, semilla 0: `real-link-s0`. Veredicto sobre el conjunto de REAL5, leído sobre el **titular sin gemelos** (21 de 25 filas): `real-link-s0` empata con `real-none-s0` **13/21** (4 : 4 pareado, $p = 1,0$) — bajo la barra de ≥ 15/21. Las 25 completas: titular 16 contra 15, valor correcto 22 contra 20, citas erróneas de mismo valor 2 contra 2, negativas 5/5 en ambos. **El guardia de REAL4 no se compró** — sin efecto sobre el conjunto de REAL5, tal como lo planteaba el brief. **Dos cambios de corpus apuntados a esta citación (REAL6, REAL7) ya no cambiaron nada; por la regla de contar rediseños, esta línea de corpus sobre esta pregunta se detiene.** Lo que queda en pie: `real-none-s0` con el runtime cita el enunciado de soporte en 13/21 filas de varios saltos sin gemelos de una tercera familia (valor correcto 20/25), se niega 5/5 — el nivel medido. Próximo posible, no comprado: un chequeo de citación en el runtime que rechace una cita cuya página el recorrido no terminó, medido sobre un conjunto fresco.
- **2026-10-01** — **REAL6 [ran]: FALSIFIED — los recorridos con valores repetidos no cambian la cita** ([`BRIEF`](../../results/REAL6-citation-20261001/BRIEF.md)). 50 recorridos de un salto cuyo valor se repite en las regulaciones de entrenamiento: en REAL5 `real-cite-s0` 15/25 contra `real-none-s0` 15/25 (empate 1:1). Las fallas son filas de varios saltos citadas en el extremo equivocado de un enlace — el corpus enseñó elecciones de un salto; el enunciado de una fila tiene un gemelo palabra por palabra (un límite del instrumento). Próximo, no comprado: valores repetidos a través de un enlace en recorridos de dos saltos, y un gate sobre enunciados gemelos.
- **2026-10-01** — **REAL5 [ran]: PARTIAL — el miembro de documentos reales transfiere a una tercera familia, bajo la barra de citación estricta.** `real-none-s0` sin cambios recorre una tercera familia (EPA 40 CFR 112, SPCC, `knowledge/spcc-regs`, 15 páginas ingeridas textuales, 146 enlaces — 9,7/página, densa en enlaces donde la familia de REAL3 era pobre en ellos) sobre 40 preguntas congeladas a ciegas: titular **15/25 (60 %)**, bajo la barra de 70 %; valor correcto 20/25; contra `base-walks+page` una mejora, **13 : 0**, $p = 0{,}00024$; negativas **5/5** (barra 4), una negativa falsa de 35; `nolib` 1/25 valor correcto — la Parte 112 no está en los pesos, la corrida lee. **Leído donde ocurre — la cita, no el recorrido:** de las 5 filas perdidas del titular, 3 citan un enunciado que tiene el mismo número pero no es el que se preguntó (la biblioteca repite valores, p. ej. "60 days" en seis enunciados) y 2 citan uno que no lo tiene. Una transferencia grande, 7× el base sin entrenar, sobre otra agencia y otro tema; la citación estricta sobre valores repetidos es el ítem abierto ([`BRIEF`](../../results/REAL5-third-family-20261001/BRIEF.md)).
- **2026-10-01** — **H5 [ran]: VOID tal como está escrito; el brazo de atribución REGRESSION 0 : 20 — la pérdida con máscara de tramo no es el default donde los resultados de herramienta son cortos.** `tr-s3` (el corpus de `tr-s1` byte por byte, pérdida sólo sobre los propios tramos del modelo) contra `tr-s1` (pérdida sobre el texto entero) sobre la suite fresca de H4 (sin bloque, 160 turnos dependientes): primeros turnos **50/60** (barra 90 %) — **VOID tal como está escrito**; las 10 fallas son el fraseo del lead "New defect — …" (`tr-s3` llama a `issue_create` con `type=defect`, la herramienta se niega, sigue una clave inventada, y los dos turnos dependientes de esas sesiones fallan). **El brazo de atribución, comprado porque había un efecto:** con el bloque de herramientas delante de los dos miembros, `tr-s1` **160/160**, `tr-s3` sigue en **140/160** (`type=defect` 10/10 incluso con el enum en la página) — la hipótesis del bloque memorizado queda **refutada**; pareado sobre los turnos dependientes, `tr-s3` contra `tr-s1`: **0 : 20, REGRESSION**. Decisión: la pérdida con máscara de tramo se queda como receta sólo donde los resultados de herramienta son largos (REAL3, 1/23 → 18/23); los miembros de resultados cortos se quedan con la pérdida sobre el texto entero; la regla del §3 de `CLAUDE.md` se acota. **Infraestructura, en REAL5 y H5 por igual:** las subidas a Colab fallaron sobre un uplink de 0,2 MB/s (chunks de 48 MB con timeout 408, que se leía como "los adaptadores no subieron"); `chain_serve` ahora manda chunks de 16 MB con 4 reintentos cada uno ([`BRIEF`](../../results/H5-span-loss-tracker-20261001/BRIEF.md)).
- **2026-09-30** — **REAL4 [ran]: la negativa se arregla; tal como está escrito, FALSIFIED en la barra de costo, por una fila** ([`BRIEF`](../../results/REAL4-refusal-20260930/BRIEF.md)). `real-none-s0` — el corpus de REAL3 más 27 recorridos sin respuesta (el oráculo abre la mejor página que muestra la entrada, no encuentra nada, contesta `Not in my library.`) — se niega en 15/16 filas sin respuesta (barra 13) y en 5/6 de las adyacentes (temas de la familia de entrenamiento, ausentes de esta biblioteca; barra 4), 0 negativas falsas de 36 contestables. **A costo cero, no se cumple:** contra `real-spans-s0` en el titular de 23 filas de REAL3 pierde 3 filas que contestaba (barra ≤ 2) y gana 2, terminando en 16/23 = 69,6 % (barra ≥ 70 %) — un empate, 2 : 3, $p = 1{,}0$, y dentro de la propia dispersión de corrida a corrida de `real-spans-s0` (18/23 y 17/23 en dos sesiones de puntaje). **Tal como está escrito: FALSIFIED** ("una negativa comprada con respuestas"); la lectura de que la negativa está arreglada y el costo del titular es indistinguible de la dispersión de vLLM fue **adoptada por el usuario el 2026-10-01** — `real-none-s0` es el miembro de documentos reales; antes: pendiente la decisión del usuario**, como las de H1 y H2.
- **2026-09-30** — **REAL3 [ran]: M3 FUNCIONA, las dos semillas — un miembro de trayectoria entrenado sobre documentos reales transfiere a otra familia** ([`BRIEF`](../../results/REAL3-real-corpus-20260930/BRIEF.md)). `real-walks-s0` — entrenado sobre recorridos de documentos reales de una familia que la evaluación nunca ve (49 CFR 391/395/396, 21 CFR 117, 29 CFR 1910 Subparte E; `knowledge/regs-train`, 134 páginas, 284 recorridos, preguntas escritas por Claude Haiku y revisadas mecánicamente) — **el intento 1 sacó 1/23** sobre un titular fresco de varios saltos: escribía texto de regulación en vez de contestar. **Causa, leída donde ocurre: el entrenador, no la transferencia** — `training/s4_train.py` ponía la pérdida sobre todo el texto, incluidos los resultados propios del runtime, y un recorrido sobre páginas reales leídas enteras es ~97 % tokens de página, así que el LoRA aprendió a escribir regulaciones; todo miembro anterior entrenó igual, y nunca se notó porque los resultados de W9 eran cortos. **Arreglo: pérdida con máscara de tramo** — sólo se entrena lo que escribe el propio modelo (sus tags y la respuesta citada), 3,3 % de los tokens de cada recorrido (`s4_train.span_labels` / `_train_on_spans`). `real-spans-s0` saca **18/23 (78 %)** contra el 9/23 del base sin entrenar (10 : 1, prueba de signos exacta $p = 0{,}0117$); la semilla 1 **17/23** (9 : 1, $p = 0{,}0215$), las dos semillas empatan entre sí. Sobre el set de REAL0: 18/25 contra el 7/25 del base, desde el 0/25 de `distributor-wiki@v2` (REAL0), contra un techo de lectura de 22/25. **Una regresión, llevada a REAL4:** el miembro nunca se niega — 0/4 en las preguntas que la biblioteca no puede contestar, porque su corpus no tenía ninguna.
- **2026-09-30** — **REAL1–REAL2 [ran]: las mitigaciones de runtime ayudan y no alcanzan** ([`REAL1`](../../results/REAL1-entry-20260930/BRIEF.md), [`REAL2`](../../results/REAL2-page-text-20260930/BRIEF.md)). La entrada por la pregunta con texto completo (`FullText`, BM25 sobre los enunciados; en todos los estantes; fallback) lleva los recorridos a la página que sostiene la respuesta 17/25; una página abierta con el texto de sus enunciados, 24/25. Varios saltos bien: base 1 → 4 → 7, `distributor-wiki@v2` 0 → 1 → 5 de 25, contra un techo de lectura de 22 — lo que se pierde es la cita que falta y el párrafo equivocado entre los muchos de una página. Las variantes de runtime terminan ahí, como decía el brief; ~~lo próximo es el corpus (M2, M3), y el ganador se confirma sobre un set de preguntas no visto~~ — **hecho: M3 corrió (REAL3) y FUNCIONA; M2 no hizo falta, su lección (sin strings de pregunta repetidos) se dobló en la compuerta de M3 como G6.**
- **2026-09-30** — **REAL0 [ran]: la trayectoria no generaliza a documentos reales — NO GENERALIZA** ([`BRIEF`](../../results/REAL0-real-library-20260930/BRIEF.md)). Una biblioteca ingerida textual de regulaciones de EE. UU. (`memory/ingest.py`, 20 páginas); `distributor-wiki@v2` sin cambios saca 0/25 de varios saltos contra el 1/25 del base sin entrenar, mientras el base con los enunciados correctos abiertos lee 22/25 y el libro cerrado 0. El miembro nunca abrió una página: 40/40 recorridos empezaron con una búsqueda en el estante harness memorizada de su mundo de entrenamiento. W9/B5 midieron recorridos sobre el mundo de un generador. ~~**Próximo, con su propio brief:** un corpus de trayectorias sobre documentos reales ingeridos, entrenado en una familia de documentos y medido en otra.~~ **Hecho — REAL3, arriba: entrenado sobre documentos reales de otra familia, transfiere.**
- **2026-09-30** — **INJ0 [ran]: no hay margen para envolver el material ajeno** ([`BRIEF`](../../results/INJ0-planted-headroom-20260930/BRIEF.md)). Cada turno registrado repasado: 70 recibieron una instrucción plantada en un resultado de herramienta, 0 actuaron sobre ella (ninguna escritura no pedida, ningún acceso a otra organización). El cambio de corpus no se construye. Al lado, publicado (#310): las aprobaciones y los handoffs persisten tras un reinicio (como mucho una vez, con el alcance de quien pidió) y la salida de red del gateway está cerrada a sus hosts configurados.
- **2026-09-30** — **H4 [ran]: SIN MARGEN — `tr-s2` no se entrenó, por la regla de parada del propio brief** ([`BRIEF`](../../results/H4-tracker-command-notes-20260930/BRIEF.md)). Sobre una suite fresca cuyas 40 notas de comentario suenan todas a órdenes (pool disjunto del entrenamiento), `tr-s1` sin bloque con la memoria y la nueva captura de claves escribe **40/40** como comentarios y obedece **0**; dependientes 149/160. Las 11 fallas son el caso inverso sobre un solo fraseo — "It's verified, done." 0/11 tomado como comentario, "Passed QA, set to done." 9/9. Toda falla residual del miembro del tracker en H2–H4 fue un solo fraseo de la evaluación: cobertura léxica, no el arnés. No se persigue (sería el tercer rediseño de corpus). La cascada se arregla como mecanismo: los flujos declaran `[capture]`.
- **2026-09-30** — **LIVE-tracker [ran]: PASÓ, 14/14 turnos, dependientes 8/8** — `tr-s1` sin bloque con la memoria en la Mac del usuario (llama.cpp Q8_0), a través de OpenClaw; latencia del gateway mediana 3,7 s, ~370 tokens de prompt por turno. Intento 1 nulo: llama.cpp descarta el string de stop y el camino de muchos tags (`stop: ["</"]`) reconstruía el tag sólo cuando vLLM devolvía `"</"` — arreglado en `accept_rank.completion`, con test. ~~LIVE-tracker pre-registrado~~ ([`BRIEF`](../../results/LIVE-tracker-openclaw-20260930/BRIEF.md)): `tr-s1` sin bloque con la memoria operativa, en el `edge` (llama.cpp, Q8_0 + su LoRA como GGUF, convertido), manejado por OpenClaw en tres sesiones (lead, developer, QA; 14 turnos, 8 dependientes) sobre el propio store del gateway. Barra: todos los turnos dependientes bien y ≥ 13/14. El gateway ganó `--memory`, `--no-tool-block`, `--max-calls` y un id de sesión por cliente (`X-Session-Id`). Corre en la máquina del usuario después de la pausa.
- **2026-09-29** — **H3 [ran]: el segundo corpus del miembro del tracker le gana al primero, las dos barras PASARON.**
  `tr-s1` entrena sobre un segundo corpus (`generate_sessions --suite h3`) que amplía el fraseo de entrenamiento en dos
  variantes por turno en cada rol y da a cada rol un tercio parejo sin bloque (165/165/132 filas), arreglando las dos
  correcciones de H2 (el error de aliasing de lo-sin-bloque y el fraseo del comentario final de QA). Medido contra
  `tr-s0` — nuestro propio miembro anterior, no el base pelado — sobre una suite fresca retenida (mundos nuevos,
  fraseo que ni el entrenamiento ni la evaluación de H2 usaron). El margen se sostiene (`s0-harness` 147/160, bajo el
  techo del 95 %). **H3a PASÓ:** `s1-harness` 158/160 (98,8 %) contra `s0-harness` 147/160, pareado 11:0, prueba de
  signo exacta $p = 0,00098$, 0 perdidos, plano ($\bar p_5 = 1275 \le 1,1 \cdot 1465$). **H3b PASÓ:** `s1-noblock`
  pierde 4 turnos dependientes contra el bloque (barra 8), cada rol por encima — developer 76/80, lead 40/40, QA
  40/40 — a más o menos un tercio de los tokens de prompt por turno. Dos fallas se leen donde ocurren: las 2 fallas de
  `tr-s1` son un solo caso, el texto de la propia nota leído como una orden (`issue_transition → qa`, rechazada); las
  4 fallas de `s1-noblock` son una sola sesión cuyo primer turno arrastra un error en cascada por el resto
  ([`BRIEF`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
- **2026-09-29** — **La lectura de H2 elegida por el usuario: lectura 1 — las condiciones legibles son el veredicto de
  H2, el harness PASÓ.** 146/160 (91,3 %) dependiente, plano en las cinco vueltas, descriptivo 142 : 0;
  FALSIFIED-tal-como-está-escrito queda en el registro con sus dos errores de instrumento (el VOID por brazo pedido a
  una línea de base sin entrenar, y el chequeo de anchor que midió fraseo). No se repitió: ningún cambio de regla
  podía mover a `base-history` de 4/160. Dos correcciones leídas después: los 80/160 de `harness-noblock`, leídos
  primero como "aprendido en parte", son un error del corpus — el tercio sin bloque se armó con el mismo módulo
  (`% 3`) con el que rotan los roles, así que las 400 filas sin bloque eran todas de QA, no un aprendizaje parcial; y
  la falla del comentario final de QA (6/20) es un solo fraseo de la evaluación ("Note on it: …" 1/15 contra "Put a
  comment on it: …" 5/5) ([`BRIEF`](../../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H2 [ran]: como está escrito, FALSIFIED — el brazo de comparación quedó nulo; el harness cumplió las dos condiciones que se pueden leer.** En 60 sesiones largas del tracker (160 turnos dependientes) `tr-s0` con la memoria operativa resuelve **146/160 (91,3 %)** con el prompt por turno plano (1.613 → 1.274 en cinco turnos). El base sin entrenar con la conversación saca 4/160 (descriptivamente 142 : 0 en los mismos turnos) pero sus primeros turnos (44/60) disparan la regla VOID por brazo, así que la "mejora sobre el base" pre-registrada no se puede leer y el código dice FALSIFIED — un segundo error de instrumento de la familia de H1 (una regla para un tratamiento roto anulando un baseline sin entrenar). Sin el bloque de herramientas, 80/160 (H1: 0/60). Las fallas son de QA: una página leída entera en vez de por ancla (un chequeo que puede fallar con la capacidad funcionando) y un comentario final. El usuario decide la lectura ([`BRIEF`](../../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **El dominio tracker construido, y H2 pre-registrado: el harness de flujo en sesiones largas.** `examples/tracker/`: un equipo sintético tipo Jira + Confluence (issues con claves, flujos declarados que hace cumplir la capa de herramientas, un espacio de enunciados atómicos, tres roles). 60 sesiones retenidas de 4–5 turnos (160 turnos dependientes — claves nombradas, claves creadas, valores leídos); `tr-s0` entrenado sobre 1.400 filas del harness, un tercio sin el bloque de herramientas. PASSED pide ≥ 90 % de turnos dependientes, una mejora pareada sobre el base con la conversación en el prompt, y un prompt por turno plano; VOID por brazo ([`BRIEF`](../../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H1 [ran]: como está escrito, VOID; por brazo, el harness de flujo PASSED.** `wf-s0` con la memoria operativa resuelve **53/54 turnos dependientes contra 43/54 del historial** (1 perdido, 11 ganados), busca por clave el valor de cada acierto (53/53) y mantiene plano el prompt por turno; los reclamos que MT0 perdía ahora nombran el pedido, 10/10 (historial 2/10). **Sin el bloque de herramientas el miembro no llama ninguna y afirma datos que no leyó: 0/60** — y la regla del brief "cada brazo ≥ 90 % de primeros turnos o VOID", un error de diseño, anula toda la corrida tal como está escrita. En estas sesiones cortas el harness lee ~2× tokens de prompt por turno (más pasos de generación); su argumento de tokens necesita sesiones más largas. El usuario decide entre la lectura por brazo y repetir la corrida ([`BRIEF`](../../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **La lectura de H1 elegida por el usuario: por brazo — el arnés de flujo de trabajo PASÓ, no-block quedó FALSEADO**; el VOID tal como está escrito (la regla de primeros turnos aplicada entre brazos) queda como el registro de un error del instrumento; el VOID es por brazo a partir de H2 ([`BRIEF`](../../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H1 [ran]: como está escrito, VOID; por brazo, el harness de flujo PASSED.** `wf-s0` con la memoria operativa resuelve **53/54 turnos dependientes contra 43/54 del historial** (1 perdido, 11 ganados), busca por clave el valor de cada acierto (53/53) y mantiene plano el prompt por turno; los reclamos que MT0 perdía ahora nombran el pedido, 10/10 (historial 2/10). **Sin el bloque de herramientas el miembro no llama ninguna y afirma datos que no leyó: 0/60** — y la regla del brief "cada brazo ≥ 90 % de primeros turnos o VOID", un error de diseño, anula toda la corrida tal como está escrita. En estas sesiones cortas el harness lee ~2× tokens de prompt por turno (más pasos de generación); su argumento de tokens necesita sesiones más largas. La decisión del usuario (2026-09-29): vale la lectura por brazo — `harness` PASÓ, `harness-noblock` quedó FALSEADO — y el VOID tal como está escrito queda como el registro de ese error del instrumento, no como el veredicto ([`BRIEF`](../../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **C1 [ran]: NO MATERIAL CONTENTION — una L4 sirviendo cuatro miembros mezclados en un lote conserva 1,03× el throughput de un miembro con 16 sesiones, y sostiene 32 sesiones simultáneas a 504 tok/s, p95 de TTFT 0,24 s, 0 errores** (throughput casi lineal de 1 a 32 sesiones; el techo está por encima de 32). Reemplaza el 0,88 de una sola ráfaga de E5 ([`BRIEF`](../../results/C1-concurrency-20260929/BRIEF.md)).
- **2026-09-29** — **La memoria operativa de corto plazo construida, y H1 pre-registrado.** `examples/common/opmemory.py`: una caché de sesión y una de la organización que un miembro opera por clave (`<get>` / `<put>`, acotadas por el claim, cada escritura registrada), flujos declarados en TOML que avanzan con las llamadas que corrieron, y un gateway que muestra una línea de contexto (estado + nombres de claves) en vez de la conversación. H1 entrena `wf-s0` sobre el corpus de M10 + 627 turnos del harness (compuerta pasada) y lo empareja contra el brazo con historial de MT0: PASSED pide ≤ 3 de 54 turnos dependientes perdidos, tokens planos, y cada turno dependiente acertado buscado por clave ([`BRIEF`](../../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **MT0 [ran]: HEADROOM, en el borde — con la conversación en el prompt el miembro resuelve 43/54 turnos dependientes (79,6 %), sin ella 4/54.** Resuelve una referencia que copia en un argumento ("movelo al dock 5": 10/10; "otra devolución sobre el mismo pedido": 10/10) pero no una que tiene que escribir en texto libre: pedido un reclamo sobre "ese pedido", lo abre sin número de pedido, 8 de 10 — el objetivo del harness de flujo. El contexto crece sólo +24 % en 2–3 turnos; el argumento de costo del harness necesita sesiones más largas ([`BRIEF`](../../results/MT0-multiturn-baseline-20260929/BRIEF.md)).
- **2026-09-29** — **C1 pre-registrado: concurrencia en el perfil `server`** — cuatro miembros en una L4 (escuela ×2, distribuidora ×2), K ∈ {1, 8, 16, 32} sesiones simultáneas × 1, 2 o 4 adaptadores; NO MATERIAL CONTENTION si cuatro adaptadores conservan ≥ 0,8 del throughput de uno con K = 16; se reporta el mayor K con p95 de TTFT de cuatro adaptadores bajo 2 s ([`BRIEF`](../../results/C1-concurrency-20260929/BRIEF.md)).
- **2026-09-29** — **MT0 pre-registrado: el baseline multi-turno**, antes del harness de flujo del usuario (máquina de estados + caché con claves en vez de historial en el prompt). 60 sesiones retenidas de la distribuidora, 54 turnos dependientes cuyo argumento sólo sale de un turno anterior; `out-s0` servido sólo con el último pedido (el gateway de hoy) y con el historial en el prompt; HEADROOM para el harness si el historial acierta menos del 80 % de los dependientes; tokens de prompt por turno reportados por posición ([`BRIEF`](../../results/MT0-multiturn-baseline-20260929/BRIEF.md)).
- **2026-09-28** — **M10 [ran]: PASSED — el miembro de la distribuidora se abstiene (20/20 retenidos, 0 de 70 perdidos, demo 6/6), y en vivo hace 6/6 a través del OpenClaw real en la notebook del usuario con Claude Haiku 4.5 escribiendo lo que ninguna herramienta cubre ($0,0112)**. Las dos mitades del diagrama de referencia corren en vivo, cada una con expertos locales y la frontera tomando su parte. La primera puntuación en vivo dio 5/6 porque el puntuador no pasaba la ruta del gateway; arreglado, testeado, repuntuado sobre los mismos turnos registrados ([`BRIEF`](../../results/M10-distributor-abstain-20260928/BRIEF.md)).
- **2026-09-28** — **M10 pre-registrado: el miembro de la distribuidora aprende a abstenerse**, para que la mitad distribuidora del diagrama pueda llegar a la frontera: el corpus de M9 byte a byte + 70 turnos `OUT OF SCOPE` según el egreso del rol (compuerta de datos pasada); contra `staff-s0`, PASSED pide ≤ 3 de 70 turnos perdidos, ≥ 18 de 20 turnos fuera de alcance retenidos abstenidos y las seis escenas de la demo (la sexta, una nota de agradecimiento enviada a la frontera) ([`BRIEF`](../../results/M10-distributor-abstain-20260928/BRIEF.md)).
- **2026-09-28** — **LIVE-distributor [ran]: 5/5 a través del OpenClaw real, todo el stack en la MacBook Air del usuario** — `gemma-4-E4B-it` Q8_0 + `distributor-staff-s0` en llama.cpp, el gateway `--org distributor`, OpenClaw 2026.9.4; el pedido de otro centro rechazado por la herramienta, la instrucción plantada reportada como dato; 5–8 s por escena. Hallado en el camino: Q4_0 cambia el número de pedido según la caché de llama.cpp (se corrió en Q8_0); llama.cpp no devuelve el stop (ahora lo cierra `accept_rank`); el store de la distribuidora no era thread-safe (intento 1 nulo, arreglado) ([`BRIEF`](../../results/LIVE-distributor-openclaw-20260928/BRIEF.md)).
- **2026-09-28** — **LIVE-distributor pre-registrado: la demo de la distribuidora a través del OpenClaw real.** El gateway sirve una organización por proceso (`--org distributor`: el prompt propio del miembro, sin la línea SCOPE, escrituras sin director, como su corpus); `live_openclaw --org distributor` recorre `demo_org.SCENES` puntuadas con `demo_org.check`. La vara es el 5/5 guionado (M9) ([`BRIEF`](../../results/LIVE-distributor-openclaw-20260928/BRIEF.md)).
- **2026-09-28** — **E5 [ran]: el bloque de herramientas sin podar cuesta latencia aun con la caché de prefijos encendida — 16,8× el tiempo al primer token (0,10 → 1,70 s)**, porque el corpus de un miembro lo pone después del pedido, donde dos pedidos nunca lo comparten; exactitud 70/70 → 39/70 (el miembro deja de llamar a su propia herramienta). Q2 NOT FREE como se registró, pero los mismos 7.205 tokens no costaron nada donde el prefijo entero se repitió (0,09–0,11 s): lo que la caché no absorbe es el orden, no el tamaño. Dos LoRA en un lote conservan 0,88 del throughput de uno (CONTENTION, en el borde). Podar sigue siendo el default por las dos razones ([`BRIEF`](../../results/E5-engine-baseline-20260928/BRIEF.md)).
- **2026-09-28** — **E5 pre-registrado: el baseline del harness contando el motor** (H-C de la revisión de tesis, aprobado). Sobre el miembro de la escuela: cuánto cuesta el bloque de 54 herramientas de OpenClaw (7.205 tokens) en TTFT y throughput con la caché de prefijos encendida, servido como se entrenó (después del pedido) y como prefijo (antes); y si dos LoRA en un mismo lote cuestan throughput. Hallado antes de correr: tal como se sirve, el bloque nunca es un prefijo compartido, así que la caché no puede reutilizarlo ([`BRIEF`](../../results/E5-engine-baseline-20260928/BRIEF.md)).
- **2026-09-27** — **C0-upper [ran]: NONE ($\rho=-0{,}02$) — restringir el LoRA a la mitad superior no le devuelve nada de la aceptación perdida al drafter MTP.** En el E4B con su propio MTP: base α 0,82, miembro completo 0,44, miembro de mitad superior 0,43 en los turnos de la escuela; el drafter lee el último estado oculto, donde actúan los dos LoRA. La aceleración con el LoRA sigue en 2,4× b1 / 2,1× b8 en una L4. Restringir capas es una palanca para compartir el KV inferior (E6), no para alinear el drafter ([`BRIEF`](../../results/C0-upper-e4b-20260927/BRIEF.md)).
- **2026-09-27** — **C0-upper pre-registrado: ¿la aceptación del drafter MTP se recupera cuando el LoRA deja la mitad inferior?** En el E4B con su propio drafter MTP, el `upper-s0` de E6 contra el `school-s0` completo (mismo corpus y receta), sobre 16 turnos de la escuela; la lectura es la fracción de la aceptación perdida que se devuelve, $\rho = (\alpha_{upper}-\alpha_{full})/(\alpha_{base}-\alpha_{full})$ ([`BRIEF`](../../results/C0-upper-e4b-20260927/BRIEF.md)).
- **2026-09-27** — **W7 [ran]: PASSED — se edita un enunciado después de entrenar y la respuesta sigue a la biblioteca.** Sobre los mundos y preguntas de entrenamiento de `distributor-wiki@v2`, una línea de Markdown parcheada por caso: **37 de los 38** que el control responde siguen el valor nuevo, citado a la línea parcheada, **0 viejos**. Sin biblioteca, los pesos tienen el valor viejo en **1 de 40** — el miembro aprendió el camino, no los hechos, así que esto es leer, no la biblioteca ganándole a la memoria ([`BRIEF`](../../results/W7-edit-after-training-20260927/BRIEF.md)).
- **2026-09-27** — **W7 pre-registrado: editar un enunciado después de entrenar; la respuesta tiene que seguir a la biblioteca.** Sobre los mundos y preguntas de entrenamiento de `distributor-wiki@v2`, donde sus pesos podrían tener el valor: 40 casos, una línea de Markdown parcheada por caso, el miembro recorre la biblioteca parcheada — PASSED pide que ≥ 90 % de las respuestas correctas del control sigan el valor nuevo y ≤ 2 viejas; el brazo sin biblioteca reporta cuánto recuerdan los pesos. El oráculo pasa por los parches 40/40 sin GPU ([`BRIEF`](../../results/W7-edit-after-training-20260927/BRIEF.md)).
- **2026-09-27** — **Inferencia desde flash, Fase 0 escrita (el brief del usuario), en pausa para revisión**: la H1 del brief se parte en dos — el *dominio* concentrando el ruteo de un MoE (H1a, sin entrenar, primero) y el *adapter* concentrándolo además sobre los mismos prompts (H1b); la compuerta, la cuenta para Gemma 4 26B-A4B en 4 bits (240 expertos ≈ 0,8 GB por token sin caché) y LoRA sólo de atención para un almacén de expertos congelado ([`00-analysis`](flash-inference/00-analysis.md)).
- **2026-09-27** — **MAC2 [ran]: la pista Mac sobre llama.cpp.** El E4B en GGUF carga; el LoRA del 12B en GGUF actúa (6/6); el cambio por `/lora-adapters` es en caliente (3 ms) y exacto; la salida de la especulativa es idéntica (20/20). Pero **el MTP de Gemma enlentece al 12B en la Air (0,52–0,87×), y el par alineado E4B+LoRA no entra en 16 GB al lado del 12B** (Metal sin memoria en Q4_0, Q3_K_M y con los embeddings por capa en la CPU). Por el veredicto escrito antes, ~~**MLX sigue como motor `edge`**~~ (reemplazado el 2026-09-28: el servicio `edge` es llama.cpp en la máquina del usuario, decisión del usuario; este veredicto era sobre la decodificación especulativa); el par pasa a una Mac mini con ≥ 24 GB ([`BRIEF`](../../results/MAC2-llamacpp-20260927/BRIEF.md)).
- **2026-09-27** — **E6 [ran]: PASSED — el miembro de la escuela con su LoRA sólo en la mitad superior de las capas (21…41 de 42) hace 70/70 en los turnos retenidos y 15/15 en la demo, igual que el miembro completo (0 de 70 perdidos)**, y las capas debajo de 21 son las del base bit a bit (KV y entradas de capa, con control base contra base). Todo experto entrenado así comparte la mitad inferior. Salvedades: el E4B comparte KV entre capas, así que un cambio igual recomputa las capas 21–23; la suite está en el techo del miembro completo; una semilla ([`BRIEF`](../../results/E6-upper-layers-20260927/BRIEF.md)).
- **2026-09-27** — **E6 pre-registrado (Fase 1 de la revisión de tesis, aprobada): el miembro de la escuela con su LoRA sólo en la mitad superior de las capas**, contra el miembro completo en los 70 turnos retenidos — PASSED pide ≤3 turnos perdidos y las capas debajo de $k$ idénticas al base bit a bit (control: base contra base), medido en el proceso de entrenamiento; la precondición para cambiar de experto a mitad de una generación y para una mitad inferior congelada ([`BRIEF`](../../results/E6-upper-layers-20260927/BRIEF.md)).
- **2026-09-27** — **C0 [ran]: en una A100 en bf16, el drafter MTP nativo con el LoRA puesto llega a 1,92× en el dominio del experto (α 0,34) y 2,40× en texto general** (base 2,80×/2,60×) — por encima de la vara de 1,8×. **El drafter E4B alineado no corrió:** al lado del 12B no entra en una L4; el FP8 en línea de vLLM falla en sm80; bitsandbytes no es una cuantización aceptada para el drafter. Próximo: una H100, o el E4B fusionado precuantizado a GPTQ/AWQ ([`BRIEF`](../../results/C0-aligned-draft-20260927/BRIEF.md)).
- **2026-09-27** — **C0 pre-registrado: un drafter alineado sin entrenar** — el miembro E4B de la wiki (el mismo corpus que el LoRA del 12B, α 0,898 offline en B4) fusionado en sus pesos y servido como modelo borrador de vLLM para el 12B + LoRA, contra el drafter MTP nativo ([`BRIEF`](../../results/C0-aligned-draft-20260927/BRIEF.md)).
- **2026-09-27** — **Revisión de tesis, Fase 0 (el brief del usuario H-A…H-D), para revisión:** H-A y H-B ya son la spec de hoy (dos objetivos: el 12B de la misma familia para la especulativa, la frontera para lo que ninguna región cubre; el verificador como puerta de entrada de una región); H-C pasa a ser E5 sobre los miembros de hoy; las palancas de composición de H-D siguen estacionadas salvo E6 — un LoRA sólo en las capas superiores, con compuerta de ≤3 de 70 turnos perdidos y KV idéntico bit a bit debajo. Sin código hasta la aprobación ([`revisión`](review/00-thesis-review.md)).
- **2026-09-27** — **F0b [ran]: la identidad de la salida no se puede probar en una L4 en FP8** — con `VLLM_BATCH_INVARIANT=1`, la decodificación normal corrida dos veces ya difiere (9/16, 1/8, 3/16, 0/8); la especulativa difiere de la normal más o menos lo mismo (12/16, 0/8, 3/16, 0/8), así que las divergencias de F0 se leen como deriva numérica; la prueba necesita bf16 en una A100/H100. Las aceleraciones reproducen F0 ([`BRIEF`](../../results/F0b-batch-invariant-20260927/BRIEF.md)).
- **2026-09-27** — **F0b pre-registrado: identidad de la salida de la especulativa en el modo invariante al lote de vLLM**, con un control normal contra normal — F0 no podía separar un defecto de la especulativa de la deriva numérica ([`BRIEF`](../../results/F0b-batch-invariant-20260927/BRIEF.md)).
- **2026-09-27** — **MAC [ran]: Gemma 4 12B en la MacBook Air M4 16 GB del usuario (MLX, 4 bits) con expertos LoRA cambiados por pedido y el drafter MTP.** El cambio es en caliente (2,9 µs, el texto del base vuelve exacto), el LoRA actúa sobre pesos de 4 bits, pico 8,4 GB. El drafter MTP: 1,25× sobre el base en texto limpio, **0,92–1,04× con el LoRA** — sin ganancia; la fila base/dominio es nula (el base en MLX entra en un bucle con el prompt de sistema de la wiki) ([`BRIEF`](../../results/MAC-mlx-12b-lora-mtp-20260927/BRIEF.md)).
- **2026-09-27** — **F0 [ran]: un experto LoRA sobre Gemma 4 12B con decodificación especulativa, de verdad.** vLLM 0.30 sirve el 12B (FP8, una L4 — A100/H100 rechazadas) + el LoRA experto con el drafter MTP nativo y con el EAGLE-3 público; G1 aplicado, un LoRA se carga en caliente en 0,25 s con el drafter encendido. MTP: base 2,73× (α 0,79), **experto LoRA 1,74× en su dominio** (aceptación en la posición 0 0,98 → 0,58), 2,13× en texto general; EAGLE-3 1,17–1,59×. Identidad de la salida a temperatura 0 **no establecida** — la corrida no fue invariante al batch; lo próximo bajo `VLLM_BATCH_INVARIANT=1` con un control ([`BRIEF`](../../results/F0-spec-lora-12b-20260927/BRIEF.md)).
- **2026-09-27** — **F0 pre-registrado: un experto LoRA sobre Gemma 4 12B con decodificación especulativa, de verdad** (el brief del usuario). Primero el drafter MTP nativo — lee las activaciones del objetivo, así que ve el LoRA sin entrenar nada — al lado del EAGLE-3 público; salidas idénticas a temperatura 0, aceptación con y sin el LoRA, tokens/s a batch 1 y 8, carga de un LoRA en caliente con el drafter encendido ([`BRIEF`](../../results/F0-spec-lora-12b-20260927/BRIEF.md)).
- **2026-09-26** — **M9 [ran]: el LoRA del personal de la distribuidora PASA — 70/70 retenidos contra 6/70 del base pelado (53 : 0), la demo 5/5 contra 1/5.** Entrenado en una L4 (A100 rechazada, cuota). El modelo ahora llega a la frontera entre clientes (rechazado por la herramienta) y a la nota plantada (servida tachada). G1 queda en su umbral con este miembro (1/3, luego 2/3) ([`BRIEF`](../../results/M9-distributor-staff-20260926/BRIEF.md)).
- **2026-09-26** — **LIVE [ran]: la escuela a través del OpenClaw real, el modelo real y una frontera real, 15/15.** OpenClaw 2026.9.4 un perfil por rol, Gemma 4 E4B + `school-s0` en una L4 de Colab por el túnel, Claude Haiku 4.5 como frontera con un tope de $50: cada escena de la demo guionada pasa a través del runtime; el único turno a la frontera costó$0,0112; la aprobación del director ejecutó el cobro retenido ([`BRIEF`](../../results/LIVE-school-openclaw-20260926/BRIEF.md)).
- **2026-09-26** — **La escuela a través del OpenClaw real, cableado [ran]: 15/15 con un modelo sustituto.** Un perfil por rol, cada uno con su token firmado; el gateway ahora habla lo que manda un runtime en vivo (SSE, partes de contenido, el contexto interno que agrega OpenClaw y las fechas). La corrida con el modelo real espera una GPU ([`BRIEF`](../../results/LIVE-school-openclaw-20260926/BRIEF.md)).
- **2026-09-26** — **M9 pre-registrado: el LoRA de trayectoria del personal de la distribuidora**, la receta de M8 sobre el propio loop de la distribuidora — 700 turnos jugados por `demo_org.scene` con un oráculo, 70 retenidos, compuerta pasada (cada fila del oráculo pasa las verificaciones de la demo); `staff-s0 vs base` tiene que ser una mejora. La prueba del corpus encontró que el filtro de anclaje no captaba "Ignore your instructions above…", plantado en la base de la distribuidora — corregido ([`BRIEF`](../../results/M9-distributor-staff-20260926/BRIEF.md)).
- **2026-09-26** — **La demo como video**: 76 s, en español, renderizado desde HTML con HyperFrames; cada línea en pantalla está copiada de `DEMO-school-diagram` (15/15). Enlazado desde el README con una vista previa ([`video/`](../../video/README.md)). Conteo corregido en el camino: el filtro de anclaje reemplazó 3 de **12** respuestas locales, no 3 de 11.
- **2026-09-26** — **DEMO-school-diagram [ran]: 15/15 — el centro educativo de referencia, cada rol y cada caja.** Las 8 escenas sin cambios y 7 nuevas (dev → dashboards, it → operaciones, compras → un borrador de orden con su cantidad, CFO → la nómina de su propia escuela y las membresías, marketing → una campaña, un educador que pregunta sueldos → una persona, ninguno mostrado), con el mismo miembro sobre Gemma, sin reentrenar. El filtro de anclaje reemplazó 3 de 12 respuestas locales, contadas ([`BRIEF`](../../results/DEMO-school-diagram-20260926/BRIEF.md)).
- **2026-09-26** — **La primera demo es el centro educativo de referencia, completo (decisión del usuario).** `DEMO-school-diagram` pre-registrada: las 8 escenas de la demo de la escuela sin cambios más 7, una por cada rol y caja del diagrama que no alcanzaba (dev, it, compras, nómina/RRHH, membresías, marketing, privacidad de la nómina), con el mismo miembro sobre Gemma, sin reentrenar ([`BRIEF`](../../results/DEMO-school-diagram-20260926/BRIEF.md)). El encoder del router queda en Qwen3-Embedding (el usuario, después de E1).
- **2026-09-26** — **E1 [ran]: EmbeddingGemma en lugar de Qwen3-Embedding.** Radar: empate (recall@3 0,628 vs 0,638, 13 : 14) — el default pasa a `google/embeddinggemma-300m`; ninguno llega a 0,80. Router: más seguro (5 vs 15 textos ajenos mal ruteados, 98 vs 120 remitentes nuevos perdidos) pero pierde **304 de 715** pedidos de su propia distribución contra 13 — una regresión; el default del router no se mueve, se consulta al usuario. Ninguno está en producción ([`BRIEF`](../../results/E1-embeddinggemma-20260926/BRIEF.md)).
- **2026-09-26** — **DEMO-org [ran], primera corrida sobre Gemma**: `distributor-wiki@v2` 2/2 correctas y citadas (tres saltos, una comparación); el E4B pelado en las cinco escenas de roles de la distribuidora **1/5** — tres nunca llaman a una herramienta y piden un id de pedido que el pedido ya daba, así que el modelo nunca llegó ni a la frontera entre clientes ni a la nota plantada; una oración errada reemplazada por el filtro de anclaje; una respuesta vacía que el filtro dejaba pasar, ya corregido. Siguiente: un miembro del personal de la distribuidora, el camino de la escuela ([`BRIEF`](../../results/DEMO-org-gemma-20260926/BRIEF.md)).
- **2026-09-26** — **Dos briefs, antes de correr.** `DEMO-org-gemma-20260926`: el recorrido de la distribuidora de `docs/DEMO.md` **nunca se había corrido** aunque estaba marcado [ran] — su primera corrida, sobre Gemma 4 E4B con `distributor-wiki@v2`, ahora con verificaciones que pueden fallar en cada escena ([`BRIEF`](../../results/DEMO-org-gemma-20260926/BRIEF.md)). `E1`: EmbeddingGemma en lugar de Qwen3-Embedding en el radar (W3: 0,638 < 0,80) y el router de embeddings (M2b: 120/120 perdidos), decisión del usuario; un empate o mejor mueve el default ([`BRIEF`](../../results/E1-embeddinggemma-20260926/BRIEF.md)).
- **2026-09-26** — **B5 [ran]: se cierra el hito 3 — la mitad chica compara cuando le muestran comparaciones.** E4B entrenado con el corpus de W9 + 128 recorridos comparativos: 37/40 en la banda (liberado: 10/40, 28 : 1), el conjunto de W9 intacto (39/40, 63/67, 0 : 0). Sin margen: el 12B no se entrenó, como decía el brief. Se libera `distributor-wiki@v2` ([`BRIEF`](../../results/B5-comparison-corpus-20260926/BRIEF.md)).
- **2026-09-26** — **B5 pre-registrado: la segunda y última mirada al hito 3** — un corpus que muestra comparaciones (las 600 filas de W9 byte a byte + 128 recorridos comparativos, compuerta pasada contra los dos conjuntos de evaluación), entrenado en las dos mitades; primero el E4B contra su miembro liberado, el 12B sólo si el chico deja margen. Lo que diga cierra el hito 3 en esta familia ([`BRIEF`](../../results/B5-comparison-corpus-20260926/BRIEF.md)).
- **2026-09-26** — **B4 [ran]: el hito 4 PASA** — el LoRA del 12B sube la aceptación de los borradores del miembro E4B, 76 : 18 registros, α agregado 0,871 → 0,898; la ganancia está en la distribución del corpus (0,855 → 0,914), ninguna en una banda que ninguna de las dos mitades entrenó ([`BRIEF`](../../results/B4-gemma4-pair-acceptance-20260926/BRIEF.md)).
- **2026-09-26** — **B3 [ran]: el hito 3 NO pasa en la banda comparativa** — E4B + LoRA 10/40 (hay margen), 12B + LoRA 9/40, empate (5 : 6); el 12B pelado 2/40. Los dos recorren y fallan la comparación: el corpus de W9 nunca mostró una. Siguiente: comparaciones en el corpus de entrenamiento, las dos mitades reentrenadas ([`BRIEF`](../../results/B3-gemma4-large-member-20260926/BRIEF.md)).
- **2026-09-26** — **M1d [ran]: `desk-commitment@v3` sobre Gemma, un miembro para las dos bandas** — entrenado con el corpus superficial y el profundo: superficial 240/240 (empate con `@v2`), profunda **239/240** contra 83 del Gemma pelado (156 : 0) y 64 de `@v2`. **Todos los miembros liberados están ahora sobre Gemma 4 E4B** ([`BRIEF`](../../results/M1d-desk-both-bands-20260926/BRIEF.md)).
- **2026-09-26** — **B2 [ran]: el par es posible sobre Gemma 4 E4B + 12B** — vocabularios idénticos byte a byte (262.144), merges idénticas, 0 colisiones, 0 ids que sólo emite el grande; un LoRA sobre el 12B entrena y vLLM lo sirve aplicado. Las dos precondiciones del hito 3 se cumplen con una mitad grande que entra en una Mac mini ([`BRIEF`](../../results/B2-gemma4-large-gate-20260926/BRIEF.md)).
- **2026-09-26** — **M1c [ran]: `desk-commitment` no es miembro sobre Gemma, y ninguno de los dos miembros resuelve la banda profunda.** En `commitment_deep` el Gemma pelado saca 82/240 (hay margen); los miembros entrenados en la banda superficial sacan 60 (Gemma, 0 : 22 contra su base) y 64 (Qwen `@v2`) — los dos copian la fecha del último mensaje. `desk-commitment` se queda en Qwen; siguiente, un miembro entrenado en las dos bandas ([`BRIEF`](../../results/M1c-desk-deep-20260926/BRIEF.md)).
- **2026-09-26** — **el miembro de la wiki liberado sobre Gemma 4 E4B (`releases/distributor-wiki@v1.json`).** Una segunda semilla de Gemma: las dos le ganan al recorrido sin entrenar (19 : 0, 20 : 0; 38 y 39 de 40), las dos tiradas coinciden en 65 de 67, y las dos empatan con las semillas de Qwen con Gemma adelante ([`BRIEF`](../../results/B1-gemma4-vs-qwen35-20260925/BRIEF.md)).
- **2026-09-25** — **M1b [ran]: `email-full` liberado sobre Gemma 4 E4B (`@v3`)** — empate con su `@v2` de Qwen (469 vs 471 de 475) y 119 : 0 sobre el Gemma pelado. `desk-commitment` empata con `@v2` y con el Gemma pelado a 240/240: por el veredicto tal como está escrito el pool no se mueve como unidad; desk se queda en Qwen hasta que una suite con margen sobre el base lo decida ([`BRIEF`](../../results/M1b-pool-gemma4-20260925/BRIEF.md)).
- **2026-09-25** — **la demo de la escuela [ran]: 8/8 sobre Gemma 4 E4B, el sistema de punta a punta.** M8: un
  LoRA de trayectoria del personal de la escuela sobre 700 turnos completos de gateway — held-out 70/70 en las dos
  semillas contra el 27/70 del Gemma pelado (43 : 0), día de la demo 8/8 contra 3/8. Leído donde ocurre, todavía
  puede inventar una línea con el formato de un resultado de herramienta y citar una instrucción plantada; el
  gateway ahora fundamenta cada respuesta en resultados reales de herramientas y redacta las instrucciones
  plantadas, afuera del modelo — en el día de la demo grabado reemplazó 2 de 5 respuestas locales, el usuario no
  vio ninguna. Dos imágenes retiradas para ser redibujadas (`memory-walkthrough.png`, `request-path.png`); los
  documentos llevan sus marcadores
  ([`M8`](../../results/M8-school-staff-20260925/BRIEF.md), [`demo`](../../results/DEMO-school-gemma-20260925/README.md)).
- **2026-09-25** — **todo se muda a Gemma 4, la decisión del usuario sobre el empate de B1.** Los miembros nuevos
  se entrenan sobre `gemma-4-E4B-it` (`training/harness/family.py`: SMALL; los runners activos lo usan por
  default); la mitad grande de un par se nombra `gemma-4-31B-it`, no medida; el hito 1b vuelve a liberar a los dos
  miembros de Qwen sobre Gemma a través de la compuerta. El gateway de la demo de la escuela ahora fundamenta
  cada respuesta en resultados reales de herramientas y redacta instrucciones plantadas, afuera del modelo,
  después de que M8 [ran] mostrara que el LoRA de personal de la escuela puede inventar una línea de la lista de
  una herramienta.
- **2026-09-25** — **B1 [ran]: Gemma 4 E4B contra Qwen3.5-4B — empate, que por la regla del usuario elige Gemma.**
  El bloqueo de P29 se levanta (el LoRA excluye las torres de visión y audio de Gemma; vLLM lo sirve aplicado). Sin
  entrenar, Gemma recorre la wiki de W9 19/40 donde Qwen recorre 0/40, y lee 40/40 donde Qwen lee 29/40. Con el corpus y la
  receta de W9, el miembro de Gemma 38/40 contra 35 y 35 de Qwen — 4 : 1 contra cada una, empate. El usuario decidió antes
  de correr cualquier tramo que la paridad elige Gemma (el stack de desarrollo apunta ahí): **los miembros nuevos se
  entrenan sobre Gemma 4 E4B**; los miembros de Qwen liberados siguen hasta volver a liberarse
  ([`BRIEF`](../../results/B1-gemma4-vs-qwen35-20260925/BRIEF.md)).
- **2026-09-25** — memoria **W9 [ran]: PASÓ.** Un LoRA de trayectorias sobre una wiki de enunciados
  atómicos: las dos semillas (`wiki-walks-s0`, `-s1`, entrenadas sobre 32 mundos que nunca se evalúan) le ganan
  al base sin entrenar recorriendo el mundo de evaluación **35 : 0** en el titular de 40 filas (35/40 contra
  0/40, citas verificadas); contra el base al que se le dan los enunciados del oráculo, empates (9 : 3, 8 : 2).
  3 saltos 16/16. Las dos tiradas coinciden en 57 de 67 filas. Tres intentos de medición se perdieron por bugs
  del harness, que ahora reproduce un `vllm serve` falso en la Mac
  ([`BRIEF`](../../results/M7-W9-atomic-statements-20260924/BRIEF.md)).
- **2026-09-24** — memoria **W9 pre-registrado, sin correr: enunciados atómicos.** El diseño del
  usuario: la biblioteca con forma de Wikipedia, una página una lista de enunciados de una oración,
  verificables, bajo anclas, los enlaces dentro del enunciado que los nombra, la misma forma para las
  recetas operativas; toda respuesta cita `[id§anchor]` y el runtime verifica la cita mecánicamente
  (`MEMORY.md` §1.6). Banco de pruebas: una wiki de distribuidora — páginas de productos, proveedores,
  depósitos, transportistas y personal, y recetas operativas que siguen los roles de la organización
  de referencia (compras, recepción, despacho, reclamos y devoluciones, comunicaciones, finanzas,
  RRHH, marketing, IT) — **generada por mundo** para que ningún valor se sepa de memoria; un mundo
  commiteado como evaluación. Una L4, sin entrenar: el brazo a libro cerrado tiene que fallar, después
  `base-walks` contra `base-reads` decide si hace falta un LoRA de trayectoria; si hace falta, dos
  semillas (W5e: dos sorteos de una misma receta discreparon en 25 de 67)
  ([`BRIEF`](../../results/M7-W9-atomic-statements-20260924/BRIEF.md)).
- **2026-09-23** — memoria **W5e [ran]: SIN MARGEN — el adaptador reentrenado no escribe la consulta memorizada.**
  El adaptador de W5c no estaba en ningún disco, así que se reentrenó (mismo corpus, misma receta; sha
  `4caceaa3…`). La nueva tirada pierde **0** filas de valor del titular por su propia consulta (la de W5c: 11) —
  escribe consultas que su corpus nunca tuvo y abre la nota 11 de 11 — así que la primera búsqueda del árbitro
  no tenía nada que reparar. Al lado del veredicto: el par de W5d sobre sus sets posteriores al congelamiento,
  `policy vs withlib`, da **9 : 1, $p=0.021$** con esta tirada (5 : 0, empate, con la de W5c), control 72 vs 72;
  y las dos tiradas de una misma receta discrepan en **25 de 67** filas del titular (15 : 10). **Un brazo
  decidido sobre una sola corrida de entrenamiento de un adaptador que navega decide sobre una tirada.**
  Siguiente, decisión del usuario: medir la tirada con 2–3 semillas, o la afirmación de la política sobre un set
  nuevo. El lanzamiento que nunca arrancó costó una sesión A100; la cadena ahora prueba un lanzamiento con
  `run.log` ([`BRIEF`](../../results/M7-W5e-first-search-20260923/BRIEF.md)).
- **2026-09-23** — memoria **W5e pre-registrado, sin correr: el árbitro escribe la primera búsqueda.** La
  única incógnita abierta de W5d. `Conversation.first_query` (apagado por defecto): la primera búsqueda del
  recorrido corre sobre el enunciado del pedido, en el estante que nombró el adaptador; nada más cambia. Sin
  GPU **[ran]**: en las 11 filas que W5d perdió — todas en el estante correcto con una consulta de
  entrenamiento del tema de goteos — el enunciado lista la nota que aporta el valor 11 de 11; sobre el corpus
  de entrenamiento lista una nota del recorrido en 268 de 274 filas, contra 258 de la consulta del oráculo.
  El adaptador de W5c no está en ningún disco, así que se reentrena (una A100, misma receta) y
  `withlib`/`policy` se vuelven a correr en la sesión de medición (una L4). Primero el margen (el adaptador
  reentrenado tiene que seguir fallando ≥ 4); se falsa si el recorrido, con la nota a la vista, sigue
  fallando en al menos la mitad; atribución sobre los sets ya vistos de W5d, nunca la afirmación
  ([`BRIEF`](../../results/M7-W5e-first-search-20260923/BRIEF.md)).
- **2026-09-22** — el primer LoRA de `examples/school` **[ran]: FALSEADO antes de entrenar — el
  margen ya estaba agotado.** Un rol (`educador`, su corpus de una sola herramienta más grande,
  regenerado con el default propio del generador: 114 train / 19 eval), un desconocido
  (fidelidad de llamada a herramienta), compuerta ≥ 0,90 — el `Qwen3.5-4B` pelado sacó
  **18/19 = 0,9474** antes de que existiera ningún adaptador, cubriendo la compuerta por sí solo:
  una de las tres condiciones de falsificación escritas antes de la corrida. La única
  herramienta del corpus, con un solo argumento, dicha explícitamente en el system prompt y
  nombrada o implícita en cada pedido, es una brecha demasiado angosta para que el entrenamiento
  la cierre. No se compra ningún brazo de adaptador; los otros seis roles comparten la misma
  forma y tampoco se compran ([`BRIEF`](../../results/M7-school-pilot-20260922/BRIEF.md)).
- **2026-09-22** — memoria **W8 [ran]: sólo la pregunta de esquema, pasó.** No es mecánica de
  fluidos, no depende de W1–W7 — desde el propio ejemplo del usuario de la Mona Lisa → pintor →
  dibujos: ¿el formato de nota expresa una referencia que no es un enlace de árbol? Se agregó
  `refs`, un campo genérico y sin tipo, en cualquiera de los dos estantes; probado sobre una
  rebanada de tres notas, `knowledge/wikipedia-arts/` (CC BY-SA 4.0, aislada), 0 hallazgos del
  lint, la trayectoria nombrada resuelve mecánicamente. No está indexado por el radar, no lo
  recorre nada, no está entrenado ([`MEMORY.md`](MEMORY.md) §1.2a,
  [`BRIEF`](../../results/W8-wikipedia-refs-20260922/BRIEF.md)).
- **2026-09-21** — hito 2 **brazo 3 [ran]: no se compra un brazo real.** `cactus-compute/needle`,
  pesos de fábrica, mismo evaluador que el brazo 2 — `NOT SAFE: serves foreign text locally`,
  62/142 casos fuera de región servidos localmente (~10× la tasa de fuga del brazo 2), contra
  19/40 de tráfico de remitentes no vistos recuperado que el brazo 2 perdía por completo. Margen
  sobre una submuestra, no la resolución propia del brazo 2; el diccionario sigue siendo el
  default ([`BRIEF`](../../results/M2c-needle-router-20260921/BRIEF.md)).
- **2026-09-20** — **replanificación a partir de una arquitectura pegada, anexo en el §0.** Leída
  contra [`FRAMEWORK.md`](FRAMEWORK.md) §9: en su mayoría ya construida (role packs F3) o ya
  secuenciada más adelante (concurrencia, la factura, instalación) o bloqueada (un drafter LoRA es un
  RFC de vLLM, no una función). Una brecha que nombró correctamente y este repositorio no había
  cerrado — permiso reforzado fuera del modelo — se vuelve el paso 4 de `FRAMEWORK.md` §7, acotado a
  un dominio con un almacén de juguete y una compuerta adversarial a 0 fugas; Postgres/Auth0 quedan
  como elección de implementación. **W5d corre primero** — más barato, ya pre-registrado, y los role
  packs del paso 4 necesitan su respuesta antes de poder construirse. Ninguna compuerta de hito de
  abajo se movió.
- **2026-09-19** — memoria **W4 [ran]: PASÓ.** El generador de corpus maneja el runtime: 600 recorridos, 0 valores en un
  enunciado, 0 casos evaluados en el corpus, 0 aperturas del apartado, 0 filas que el árbitro no reproduzca; `discontinue-iv`
  apartado; los recorridos largos son ventanas con el estado llevado. Todavía sin modelo.
- **2026-09-19** — memoria **W5 [ran]: no pasa tal como está escrito.** Titular 35/56 contra el base sin entrenar que
  lee, 45/56 (6 : 16, $p=0{,}052$); 35 : 2 sobre sin-biblioteca, 35 : 0 sobre el base navegando solo. 12 de 21 fallas
  son el segundo de dos valores en un tipo de nota que el corpus nunca mostró. La navegación se transfirió; esa lectura no.
- **2026-09-19** — memoria **W5c construido y pre-registrado, sin correr.** La fuente no tiene ningún valor
  condicional en los procedimientos entrenados; el usuario eligió una oración real (factores de goteo, verificada
  byte a byte) más oraciones agregadas por el sitio, declaradas como inventadas. Un sitio ahora puede AGREGAR una
  oración, nunca reescribir una. Corpus v2, conjuntos retenido y de control nuevos, compuerta v2 PASÓ, falsador
  exacto en código ([`BRIEF`](../../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).
- **2026-09-20** — pasos 2 y 3 del framework **[ran]**, cero GPU. **F2, el rol como ruta:** el rol viaja en el id del
  modelo (`auto:<rol>`) y dice *cuál* miembro, nunca *si corresponde*: `role_confirmed` pasa (nunca más mal ruteados
  que las claves, nada servido bajo un rol equivocado, replay 0,775) y es el default del proxy; `role_first` falla
  (120/120 tareas ajenas servidas). **F3, el paquete de rol:** `roles/` + `rolepack.lint`; compuerta pasada — prompt y
  bloque servidos idénticos byte a byte para los dos miembros liberados, registros derivables e iguales; el miembro de
  la memoria expresado como no liberado, su loop sin servir por la API. La cadena ahora se detiene cuando el backend
  rechaza el acelerador ([`F2`](../../results/F2-role-as-route-20260920/BRIEF.md), [`F3`](../../results/F3-role-pack-20260920/BRIEF.md)).
- **2026-09-20** — memoria **W5d [ran]: FALSADO tal como estaba escrito.** Sobre el conjunto escrito
  después del congelamiento, `policy vs withlib` es 5 : 0, $p=0,0625$ — un empate, tal como la línea de
  poder del brief había dicho que se leería ese caso (titular 67: policy 42, withlib 37, base-reads 52;
  contra base-reads 6 : 16); el control aguanta, 75 contra 73. Leído donde ocurre: donde el recorrido
  abrió la nota que daba el valor, el base la lee bien **21 de 21**; las otras 11 son fallas de búsqueda
  **causadas por la propia consulta del adaptador** — ante una redacción nueva escribe una consulta de
  entrenamiento de otro tema, textual en 9 de 11, y calcula un goteo — mientras el mismo buscador léxico,
  con el enunciado del pedido, lista la nota necesaria 16 de 16 (cero GPU). Sobre los sets de W5c, con 0
  fallas, no es la afirmación: 56/66, 14 : 0 y 12 : 2 contra base-reads, control 75/80. Sigue, una
  incógnita: que el runtime emita la primera búsqueda desde el enunciado
  ([`BRIEF`](../../results/M7-W5d-answer-policy-20260920/BRIEF.md)).
- **2026-09-20** — memoria **W5d pre-registrado, sin correr** — paso 1 de [`FRAMEWORK.md`](FRAMEWORK.md) §7, *decidir
  quién lee*. La política de respuesta: el adaptador camina siempre; escribe la línea cuando la tarea es llevar un
  procedimiento, decir que no está en la biblioteca, o calcular una tasa (la tasa se decidió sólo con la banda
  entrenada: 15/15 y 12/12 contra 7/15 y 5/12 del base); el base pelado la escribe cuando la tarea pide un valor,
  desde las páginas que abrió el recorrido del adaptador. El tipo se lee sólo del enunciado (600/600 con la familia
  del generador — lo que muestra que la regla está atada a la redacción del generador, no que un pedido real se
  pueda clasificar). Congelada en el commit `d3e5056`; DESPUÉS se escribieron un conjunto retenido nuevo (89,
  titular 67) y un control (78), compuerta PASADA, piso 5/67. Falsador: `policy vs withlib` empate o peor en el
  titular nuevo; el control no debe retroceder; contra `base-reads` un empate es un empate. Una sesión de L4, el
  adaptador de W5c llevado adentro, sin entrenar
  ([`BRIEF`](../../results/M7-W5d-answer-policy-20260920/BRIEF.md)).
- **2026-09-20** — memoria **W5c [ran]: FALSADO.** Valor condicional 4/15 (antes 0/11, Fisher $p=0{,}091$); el par de
  W5 sobre el titular nuevo 12 : 16, un empate — no pasa. El adaptador lee los condicionales de las ocho notas que
  vio (17/18) y en una nota nueva escribe el primer número; la navegación mejoró (línea compartida 22/22, control
  78/80). Cinco sesiones de seis; una perdida en el arranque ([`BRIEF`](../../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).
- **2026-09-19** — memoria **W5b [ran]: el diagnóstico se sostiene, y la composición no es un diseño de servicio.**
  Los recorridos grabados de `withlib` reproducidos, el base pelado escribe la línea final: quedan **0 de las 12**
  fallas de cantidad con recorrido limpio; `composed` 41/54, exactamente su techo sin GPU; 12 : 4 contra `withlib`
  ($p=0{,}077$, empate), 1 : 5 contra `base-reads`; `carry/middle-find` quedan 8 de 8. Pero en lo que al adaptador
  se le enseñó, lee mucho mejor que el base — control 58 contra 39 (0 : 19), línea compartida 15 contra 8.
  El lector falla en una forma que su corpus nunca mostró; las dos notas de dos valores de la biblioteca están en
  el procedimiento retenido. El veredicto de W5 queda ([`BRIEF`](../../results/M7-W5b-composition-20260919/BRIEF.md)).
- **2026-09-19** — el evaluador de W4 reemplazado tras una revisión adversarial (rediseño 2: fallaba con una paráfrasis y
  aprobaba con un número señuelo); **W5 construido y pre-registrado**, primero la sesión de margen, titular n = 56, piso 3/56. Sin correr.
- **2026-09-19** — memoria **W2 [ran]: PASÓ.** El runtime, las capas y la guarda sobre el loop de modo corpus sin tocarlo;
  72/72 recorridos del oráculo, 0 rechazados, tres recorridos que violan cortados en `strict`. Todavía sin modelo.
- **2026-09-19** — memoria **W3 construido, margen [ran]:** el índice, un conjunto de consultas escrito después de congelar (P 94, E 72),
  recall@3 léxico 0,064 / 0,125. La sesión de R0 en Colab está pendiente; el veredicto y su estándar de 0,80 están en el brief.
- **2026-09-19** — memoria **W3 R0 [ran]: no pasa.** recall@3 0,638 en P, 56 : 2 contra el léxico, por debajo del 0,80
  fijado antes de correr; la mitad de los fallos está en rango 4–10, la otra mitad lejos. La brecha es de W6; W5 cuenta los fallos de recuperación aparte.
- **2026-09-19** — memoria **W1 [ran]: PASÓ.** La primera biblioteca (`knowledge/nursing-iv/`, 94 notas de
  tres checklists de Open RN, CC BY 4.0), `memory/notes.py` y el lint; 0 hallazgos, 72/72 recorridos del oráculo.
- **2026-09-19** — hito 1 **[ran]: MOVIDO.** Los dos miembros liberados, reentrenados sobre `Qwen3.5-4B`,
  empatan a sus releases de Qwen 2.5 (471/475, 240/240); manifiestos `@v2`; el pool está sobre la
  familia 3.x. Cuatro sesiones de menos de una hora, cinco relanzamientos, cada uno un arreglo del arnés.
- **2026-09-19** — la memoria especificada como el núcleo de 1.0 ([`MEMORY.md`](MEMORY.md)), a
  partir de la explicación en cinco piezas del usuario: biblioteca, radar, tres verbos, un LoRA
  entrenado sobre el hábito de navegar, un árbitro de software. Hito 7 brazo 0b **[ran]**: el
  experto de fluidos, servido como le enseñó su corpus, está en 90/90 donde había estado en
  11/90 — *"el experto que razona falla"* queda retirado.
- **2026-09-19** — hito 7 brazo 0c **[ran]**: `fluids-full` reentrenado sobre `Qwen3.5-4B` **no queda
  liberado** — 80/90 contra su propio 90/90 (0 : 10, pareado). Las diez son cadenas de venturi, correctas
  hasta el número, que terminan en un tag `<answer>` que el corpus nunca enseñó en vez de la línea JSON.
  La región sigue `out`; sigue el mismo miembro bajo el runtime de la memoria, cuyo guard nombra inline un tag desconocido.
- **2026-09-19** — hito 2 brazo 1 **[ran]**: seguro ante texto extranjero, pierde todo pedido
  de un remitente no visto; el diccionario se queda, el brazo 2 es un modelo de embeddings.
  Se agregó el hito 7: una base de conocimiento por subdominio con la trayectoria por ella
  como harness, sobre mecánica de fluidos partida en subdominios — dado forma por P61, P21 y
  P14.
- **2026-09-19** — objetivo reformulado alrededor del ruteo por distribución de corpus y
  el par especulativo; el árbol limpiado a lo que funciona; el plan anterior y sus
  setenta y cuatro corridas se conservan en `v0.1-foundations`.
- **2026-09-06 → 2026-09-19** — ver [`RECORD.md`](RECORD.md).
