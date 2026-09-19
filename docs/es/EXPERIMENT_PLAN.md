# El plan

> **Documento vivo.** Esto es la posición del proyecto, no una propuesta. Cada
> paso lleva su objetivo, su compuerta y su condición de falsación, escritas antes
> de correrlo; cada paso terminado lleva el número que salió, haya salido como
> haya salido.
>
> *[Read me in English](../EXPERIMENT_PLAN.md)*

---

## 0. Cómo se lee

| marca | significado |
|---|---|
| **[read]** | inferido de código, documentación o un issue, y citado |
| **[ran]** | observado ejecutando algo acá, con el directorio de la corrida nombrado |
| `NEXT` / `RUNNING` / `DONE` / `BLOCKED` / `DROPPED` | el estado del paso |

Reglas para quien edite este archivo: actualizar la fila de un paso **en la misma
sesión** en que el paso termina; dejar visible el texto superado con su razón en
vez de borrarlo; actualizar el espejo en inglés en el mismo commit.

## 0b. El orden de dependencias — fases, de abajo hacia arriba (adoptado 2026-09-17)

El plan es una pila: **cada capa se valida sola, queda congelada con un test que la
protege, y sólo entonces la capa de arriba se construye sobre ella.** `CLAUDE.md` §8
lleva la regla; esto es el estado. Ninguna pieza cuenta como funcionando hasta tener
(a) un preflight, (b) un artefacto persistido, (c) un test que la re-verifica en cada
sesión y (d) una condición de falla escrita antes de correr.

| # | pieza | depende de | compuerta | estado |
|---|---|---|---|---|
| **0** | el sustrato de serving — C18 en cada miembro (≥ 2 de 3 sondas difieren), herramientas alcanzables por el proxy, stop honrado. Spec: [`SUBSTRATE-GATE.md`](SUBSTRATE-GATE.md) | — | `verdict.json` `pass: true` | ✅ **[ran]** P56, 2026-09-17: los dos miembros `applied` **3/3**, herramientas alcanzables por el proxy (`email-full` 1 llamada; `fluids-full` ninguna — podado a su propia superficie), stop honrado. `results/P56-substrate-20260917/verdict.json` |
| **1** | un release reproducible de `email-full`: adaptador + corpus + hash del prompt, re-servido en modo corpus y pareado contra su 471/475 registrado | 0 | el re-serving empata por el test pareado | ✅ **[ran]** P57, 2026-09-17: re-servido vs registrado **0 : 0** discordantes (idéntico caso por caso); reentrenado con el mismo corpus y receta **472/475**, vs re-servido **1 : 0**, $p = 1,0$ — **varianza de entrenamiento: un caso en 475**. Manifiesto `releases/email-full@v1.json` |
| **2** | una suite con verificador y gradiente: `suite_gates`; gradiente de la base ≥ 0,30 en profundidad; el target le gana al mejor experto, pareado, $p \le 0,05$ (M-target, FOUNDATIONS §7.2) | 1 | las tres en una región | desk `commitment`: gradiente **1,000 → 0,000** y target **1,000** en cada profundidad **[ran]** P51 — pero un experto **entrenado** lo satura (P55b). **`commitment_deep` construida 2026-09-17** (P60 §3a): mi última promesa en 1–4 rondas con las fechas del remitente como distractores, último mensaje del remitente desde profundidad 2; la suite superficial pinada por hash, 0 desajustes contra las verdades de P55b. Su gradiente para un experto entrenado es lo que P60 mide |
| **3** | expertos que el verificador ordena (M1): `g25 ⊂ g75 ⊂ 600`; **el grado más chico se entrena y puntúa primero** — si `g25` ya satura, se para | 2 | ≥ 1 par adyacente resuelto, $p \le 0,05$ | **P58 intento 1** **[ran]** 2026-09-17: dos fallas de instrumento, mías — el loop de modo corpus reventó en un tag de cierre sin apertura canónica (`g25` escribe `<message id="msg-006" from=…>`, *fabrica* el email en XML en vez de pedirlo — 209 de 240 cadenas perdidas) y la compuerta C18 leyó un registro con error como diferencia (`applied` 8/8 sobre nada). Ambas arregladas con tests; `--max-model-len` 8192 para el desk (7 pedidos de la base dieron 400 a 4096). Base en modo corpus **41/240 = 0,171** (se pierde en XML auto-cerrado). **Intento 3 limpio [ran]: `g25` = 0/240** — 1152 de 1194 llamadas malformadas, *fabrica* el email en XML en 240 de 240 casos; C18 `applied`, 0 errores. **La condición de muerte no disparó** ($Q(g25) = 0,000 \ll 0,95$): el grado bajo existe. **P55b [ran]** 2026-09-17: `g75` **240/240**, `g600` **240/240**, `g25` 0 — M1 pasa por **un bit**: los dos pares resueltos son *roto contra perfecto*, y `g75` ≡ `g600` (0 : 0). **El riesgo de saturación era real: 75 ejemplos alcanzan para un protocolo de una llamada; no existe grado intermedio en esta suite** |
| **4** | el veredicto de orden por aceptación (M-α, M2): tres α por caso, SUPPORTED / FALSIFIED / UNRESOLVED-como-fracaso escritos antes (§7.4) | 3 | la tesis misma **P60 §3b [ran] 2026-09-18: el brazo del target entrenado se puede servir** — un LoRA aplica sobre el 32B AWQ (compuerta de logprobs 3/3 contra un control base-vs-base, texto 2/3); 3c/3d programados después del hito 5 (§0c) | **P55b se detuvo en M-target [ran]**: el 32B en modo corpus **227/240**, **232/240** una vez que el verificador dejó de rechazar `2023-01-05` por `January 5` (5 de sus 13 pérdidas eran formato; el check se borró); las 8 restantes son reales — se pierde `thread_history → inbox` y dice *no date*. Contra `g600` en 240/240: **0 : 8, $p = 0,008$** — el target sin entrenar queda resolublemente por debajo del experto entrenado, **por segunda vez** (triage: 0,746 contra 0,989). **No medido.** Contador de rediseños: 2 de 3. ~~Cerrado 2026-09-17 (decisión D): M2 no es comprable en ninguna suite que este proyecto pueda generar~~ — **corregido el mismo día por revisión: lo medido es que la ventana no existe en dos regiones fáciles con un target *sin entrenar*.** El orden entre grados lo decide la dificultad del material, y un target entrenado habilita $Q(T) \ge \max Q(E)$. **Reabierta como un brazo (P60, siguiente): un 32B entrenado sobre el desk + una banda de `commitment` más profunda donde los grados entrenados no saturen + M-target bajo el `≥` del §7.2.** Un brazo, no el último rediseño; si la ventana sigue sin aparecer, el cierre se firma con el brazo correcto corrido |
| **5** | el producto con grupos reales (CASE-TEAM), `--prune` apagado como brazo de atribución; cada miembro nuevo entra por la puerta de la Fase 1 | 1 | 0,546 → 0,775 reproducido sobre tráfico nuevo, con la fracción que sale medida | **P59 [ran]** 2026-09-17, la superficie que OpenClaw manda de verdad (54 herramientas, grabada): `--prune off` humanos **0,664**, 227 llamadas de las que **225 rechazadas** — copia `agents_list`, `apply_patch`, `browser`… del bloque; `--prune on` **0,729**, 1160 llamadas, 8 rechazadas. Pareado 87 : 64, $p = 0,073$ — **empate en exactitud a $n = 475$, no empate en conducta**: sin podar, el experto busca las herramientas del runtime. Bloque **~7.956 → ~77 tokens** por turno. `--prune` es el default recomendado. Intento 1 anulado (contexto 4096) |
| **6** | la ruta a `Qwen3.8-27B`: D2 (el mecanismo de C18, con el log) → D3 → D4 | **4 = SUPPORTED** | D2: `applied` en la compuerta de identidad | **bloqueada por diseño** — la 4 cerró sin veredicto; no por el tokenizer, no por C18 |

**Los tres desenlaces de la Fase 4 quedan comprometidos ahora.** SUPPORTED abre la
Fase 6 y el torneo. FALSIFIED cierra la aceptación-como-ranking para siempre y el
README se reescribe alrededor del producto medido. UNRESOLVED permite un rediseño más
— el tercero es la condición de parada (contador: 2 de 3 después de P55b).

**Mapa de los mecanismos de arriba a las fases:** C18 → 0 · S9, S10 → 1 · compuertas
de suite P50, headroom, M-target → 2 · M1 → 3 · M-α, M2 → 4 · S8, S3, pool > 2 → 5 ·
D2–D4 → 6.

## 0c. El orden del servicio — hitos sobre las fases (adoptado 2026-09-18)

Las fases de arriba son el orden de dependencias del instrumento; **lo que se construye
después lo decide el servicio**: una API compatible con OpenAI que resuelve local lo
que está medido que resuelve y reenvía el resto, y después instancias de OpenClaw por
tarea encima. Artesanal al principio, automatizado en dos o tres meses. **El servicio
de personalización y sus herramientas no son parte de este runtime ni de la versión
open source**; los instrumentos que miden una personalización sí. `CLAUDE.md` §8b
lleva la regla; esto es el estado.

| # | hito | depende de | compuerta | estado |
|---|---|---|---|---|
| **1** | pesos o harness en una región: base / base + `knowledge/email-triage.md` / `email-full@v1`, una sesión, los 475 casos de P55 | Fase 1 | `kb_pays`, `weights_needed`, `harness_replaces_weights` pre-registrados en el brief; los errores anulan un brazo | ✅ **[ran]** P61 2026-09-18: **HACEN FALTA LOS PESOS** — base+kb **0 llamadas** en 351/351 humanos, 0,601 debajo de la barra de mayoría 0,655 (el test de signos solo leyó un default dado vuelta como pagando: 164 : 74 — guarda agregada, número conservado); experto 0,989, **137 : 1**; documento 914 tokens/request |
| **2** | ruteo por request | 1 | el clasificador de región ≥ el 0,775 por región de P41 sobre el mismo tráfico | ✅ **[ran]** P62 2026-09-18, cero GPU: replay sobre los 240 casos de P41, por request **0,775 = por región**, **0 mal ruteados**, 37,5 % afuera; lo entrega `openai_proxy --auto` |
| **3** | OpenClaw en vivo con `--prune`; una plantilla de perfil por tarea | Fase 5 | cero llamadas a herramientas no ofrecidas; nada sale para la región del miembro | ✅ **[ran]** P63 2026-09-18: **EN VIVO** al intento 7 — 40/40 local, 0 inventadas, 19/32 turnos humanos llaman una herramienta, 0,688 contra barra 0,655 (descriptivo); el brazo con prompt del runtime 2/32, 0,281; seis fallas del camino en vivo corregidas con tests |
| **4** | la primera región real, personalizada a mano | 1–3, sandbox, claves rotadas | la compuerta de release de la Fase 1 | — |
| **5** | segunda y tercera región | 4 | cada una supera su propia barra contra la base | **mitad sintética ✅ [ran]** P64 2026-09-18: `desk-commitment@v1` LIBERADO — G1/G2 en ambos miembros, `auto` rutea a cada uno por su pregunta, empata el g600 grabado 240/240 (0 discordantes), le gana a la base **202 : 0**; las regiones reales esperan al 4 |
| **6** | trazas → corpus → compuerta → release sin manos | 4, 5 | el release automático empata al hecho a mano, pareado | — |
| **7** | `Qwen3.8-27B` (Fase 6) | 5, y la cuenta de frontera | D2 | — |

**M2 está fuera del camino crítico, no cerrada.** P60 §3b **[ran]** 2026-09-18 muestra
que el brazo del target entrenado se puede servir (abajo); 3c/3d corren después del
hito 5. Contador de rediseños sin cambio: 2 de 3.

## 1. La única pregunta

> **¿Es la aceptación contra un target de frontera un criterio válido de
> promoción para un experto chico — y cuánta calidad verificada se pierde cuando
> la frontera se retira?**

Todo lo que dicen `README.md` y [`ARCHITECTURE.md`](ARCHITECTURE.md) descansa
sobre dos afirmaciones, y sólo esas dos valen la primera plata:

1. **α significa destilación.** Una aceptación alta contra un target de frontera
   identifica a un experto que ya produce lo que la frontera produciría, *acá*.
2. **La frontera es removible.** Cuando α cruza un umbral en una región, el
   experto genera solo y el puntaje verificado casi no se mueve. Esa diferencia
   —la **brecha de retiro**— es el producto.

**Qué falsifica el proyecto:** si α no ordena a los candidatos como los ordena la
calidad verificada, la afirmación 1 es falsa y la aceptación no puede ser el
criterio de promoción. La arquitectura sobreviviría; el router gratis, no.

---

### Reformulada el 2026-09-16, y ésta es la versión construible

La pregunta de arriba nunca se contestó — se **disolvió**, porque la configuración
que suponía no era construible. Una API de frontera no puede ser target especulativo:
no devuelve logprobs de una continuación *forzada* (C2) ni comparte el tokenizer de
la base (C3) **[ran]** P48. Así que la afirmación 1 nunca tuvo precio (S3 empató con
una regex que leía `clinic:` del prompt) y la 2 se cerró con una calculadora en vez de
con aceptación (P7, 40/40).

**La misma pregunta, en la configuración que sí existe:**

> **¿Ordena la aceptación contra un modelo más grande de la misma familia a los
> expertos chicos como los ordena la calidad verificada — y se puede después retirar
> ese modelo, por región, sin que caiga el score verificado?**

Cada palabra de eso es medible hoy, y ninguna lo era el 2026-09-07:

| qué necesita | estado |
|---|---|
| un target contra el que verificar nuestros tokens | **`Qwen2.5-32B-Instruct-AWQ`** — `tokenizer.json` byte-idéntico, 19,3 GB, entra al lado del 3B en una A100 **[ran]** P48 |
| un pool que sirva varios adaptadores sobre una base | **construido, medido tres veces**, incluso con el adaptador de un tercero **[ran]** P40/P41/P42 |
| una suite donde aceptación y calidad verificada se lean las dos | **construida** — `training/email/desk.py`, cuatro regiones × cuatro profundidades, respuestas checkeables |
| una suite cuyos números sean evidencia | **siete compuertas en código**; las cuatro suites previas fallan, la nueva pasa tres y renuncia a una con nombre **[ran]** P50 |
| un corpus capaz de producir un drafter que valga aceptar | **conocido y sin construir** — lo tiene que generar el **target**, no un oráculo |
| expertos lo bastante cercanos para que elegir sea una pregunta real | **todavía no** — los dos que tenemos se distinguen con doce palabras clave al 1,000 |

**Qué cambió en la afirmación 2.** La frontera no es lo que se retira — es el fallback
permanente para lo que el pool falla, medido, y vale **0,546 → 0,775** **[ran]** P41.
Lo que una aceptación alta permitiría retirar es el **32B local**, por región, que es
una versión más barata y más honesta del mismo producto.

**Qué falsifica la pregunta reformulada, sin cambios de espíritu:** si la aceptación no
ordena a los expertos como los ordena el verificador, sobre los mismos casos, el router
gratis no existe. El pool, el sustrato de serving y el ruteo por región sobreviven a
eso; se pierde sólo el router, que hoy es un dict de todos modos.

**Qué queda afuera para siempre.** Aceptación contra una *API de frontera* — no
difícil: imposible. Composición en el espacio de pesos y `harness.lora` — descartadas
por medición, y encadenar no cuesta nada si alguna vez se quieren. Una cabeza EAGLE
como mecanismo de ranking — una por target, no hay entre qué elegir.

## 2. El orden, y por qué éste y no el de la especificación

[`ARCHITECTURE.md` §7](ARCHITECTURE.md) lista E0–E4 y tiene razón sobre el
destino. Este plan difiere en **dónde está la falsación barata**: la
especificación valida α *después* de que existan los adaptadores, que es
exactamente donde el test deja de ser barato. Acá la pregunta de α contra calidad
se responde con modelos que ya existen, antes de entrenar un solo adaptador.

| paso | objetivo | primera compuerta que abre | costo | estado |
|---|---|---|---|---|
| **S0** | que el instrumento mida lo que dice | todo | $0, local | **DONE, y movió el plan** — §3 |
| **S1** | headroom: ¿puede esta suite mostrar una brecha de retiro? | S2 | $0,47 + una re-corrida local | **HECHO — falló en la suite clínica, quedó resuelto en mecánica de fluidos con +0,533** — §4, P10 |
| **S2** | ¿el **acuerdo** ordena a los candidatos como los ordena la calidad verificada? | S4 | incluido arriba | **DONE — 14/15 pares, pero contra pares** — §5 |
| **S3** | atribución: ¿un router léxico o de embeddings hace lo mismo? | la afirmación de ruteo | $0, offline | **DONE — mecanismo 9/10, pero empata con la regla léxica** — §6 |
| **S4** | **los adaptadores** — ¿hay especialización, y es por región? | S5 | Colab T4 gratis | **DONE. P1 +63,3 puntos, sonda negativa. P2 sí, +20 puntos, asimétrica** — §6 |
| **S5** | **la brecha de retiro** | el producto | GPU + frontera | **HECHA en región — 0,000.** El borde de la región es duro y el experto no lo siente — P7, P14 |
| **S6** | `harness.lora` — un kernel separado del experto | el kernel | GPU alquilada | **a medias. La composición se resolvió turnándose (P13); si el kernel vale sus pesos se está midiendo (P15)** |
| **S7** | el torneo, con un verificador no visto | la evolución | GPU alquilada | **bloqueado: no hay juez sin oráculo** — `OPEN-PROBLEMS.md` problema 4 |
| **S9** | una **región** que es la mañana de alguien, y el bucle multi-turno | entrega | gratis | **el bucle cierra** — 24 llamadas, 0 rechazadas, 0 sin decidir; el techo de la suite leyendo el listado es exactamente su clase mayoritaria, y su verdad es verificable mecánicamente (P30) |
| **S8** | el pool detrás de un **endpoint compatible con OpenAI** | entrega | GPU alquilada | **HECHO para servir, con precio para function-calling** — cada adaptador es su propio nombre de modelo y se aplica (P26); el conversor etiqueta→`tool_calls` no tiene dominio, 604/604 idas y vueltas (P27); la dirección esquema→etiqueta cuesta **0,188** (P27 brazo 3) |

Dos reglas gobiernan la secuencia. **Los arms se compran de a uno** — el que
puede matar la hipótesis corre antes que el que la explica. **Nada que necesite
GPU se compra antes de que algo que no la necesita haya fallado en matar la
idea**: `vllm` no puede servir en esta máquina **[ran]**, así que todo paso que
dependa de vLLM es tiempo alquilado.

## 3. S0 — el instrumento · DONE

**Objetivo.** Producir una superficie de aceptación y un puntaje verificado en
una misma corrida, contra un target local que hace de suplente de la frontera, y
mostrar que los dos números se mueven de forma independiente.

**Compuerta.** Nada aguas abajo es creíble hasta que al instrumento se lo haya
hecho fallar a propósito.

**Qué se construyó.** `alpha/` — cargador de casos sobre la suite prestada
`clinical_learning` con un prompt congelado y hasheado; dos backends greedy; la
medición; el reporte. `tests/test_alpha.py` fija cada una de las formas en que el
número podría salir limpio y equivocado; pasan todas **[ran]**.

**Qué encontró la construcción antes de creerle a un resultado** (cada una es hoy
una restricción en §7):

- el renderizador de chat de ollama **no honra un prefill de asistente** — un
  drafter qwen reabrió su turno y reinició la respuesta **[ran]**. Por eso la α de
  mitad de respuesta es opcional y depende de una bandera `restarted` por
  llamada; el número primario es α en la posición 0, que no necesita prefill y es
  el que la Fase B realmente corre.
- **todos los modelos locales acá son modelos que piensan** **[ran]**. El flujo de
  razonamiento se emite antes que la respuesta y se come en silencio un
  presupuesto dimensionado para la respuesta, devolviendo un canal de respuesta
  vacío. `think=false` funciona en qwen y devuelve HTTP 500 en gemma. El
  instrumento registra los dos canales por separado y aborta en vez de puntuar
  una respuesta vacía como α = 0.

**Resultado — tres corridas, $0, y el instrumento encontró cuatro formas de mentir.**

| corrida | prompt | n | target `gemma4:12b` | `qwen3.5:4b` | `qwen3.5:9b` | qué estableció |
|---|---|---|---|---|---|---|
| [`S0`](../../results/S0-instrument-20260907/BRIEF.md) | congelado | 4 | 1/4 | 1/4 | 0/4 | el pipeline corre de punta a punta |
| [`S0b`](../../results/S0b-payload-20260907/BRIEF.md) | congelado | 12 | 3/12 | 3/12 | 2/12 | α sobre el payload; dispersión 0,076 |
| [`S0c`](../../results/S0c-canonical-20260907/BRIEF.md) | canónico | 12 | 4/12 | 3/12 | 3/12 | nuestro prompt deja de ser variable |

**[ran]** Las tres bajo `results/`, un JSON por caso, reportes regenerables con
`python3 -m alpha.report <run-dir>`.

**Dos hallazgos que cambian el plan, no sólo el código.**

**1 · Esta suite no separa a estos modelos en un solo tiro, y el target no tiene
headroom sobre sus propios drafters.** 4/12, 3/12 y 3/12 son el mismo número. Un
target de 12B que no le gana a un drafter de 4B no puede hacer de suplente de un
modelo de frontera, y un arm de frontera comprado sobre esta configuración
estaría midiendo nada. Y fijarse qué dice esto también sobre la escalera
publicada: 38–41/50 salió del *runtime* —contrato, feedback, validación de
acciones— y la generación cruda de un solo tiro da 33 %. **El harness es la mayor
parte de ese puntaje**, que es la tesis que `../verified-runtime` existe para
probar, llegando acá como restricción.

**2 · La coincidencia a nivel de caracteres mide el formato, no el acuerdo.** La
pasada escéptica la corrió en las dos direcciones **[ran]**:

| entrada | qué dijo la métrica | qué es cierto |
|---|---|---|
| misma respuesta, una indentada y con cerca de código, otra compacta | acuerdo **0,00** | el verificador aprueba las dos |
| respuestas distintas, las dos indentadas | acuerdo **0,44** | coinciden en `\n      "` y en nada más |

En la corrida S0c el 4B produjo la respuesta exactamente correcta y sacó **0,00**,
mientras que un modelo que dio la misma respuesta con indentación sacó **1,00**.
El formato le gana al contenido, así que α medida así no es sólo ruidosa: es
anti-informativa entre familias de modelos.

**Lo que eso implica, y es lo más útil que produjo S0:** en la arquitectura el
formato de la respuesta no es una variable, porque **`harness.lora` lo fija**. La
aceptación por caracteres recién significa algo cuando el kernel vuelve constante
al formato. Así que `harness.lora` no es un carril paralelo — **está aguas arriba
de α**, y el orden de §2 está equivocado sobre S6. La propuesta sobre la mesa,
que necesita una decisión y no un commit, está en §12.

## 4. S1 — headroom · BLOCKED

**Objetivo.** Establecer que un target de frontera puntúa materialmente por
encima del mejor modelo local en esta suite. Sin esa distancia no hay nada de lo
que una brecha de retiro pueda ser brecha.

**Por qué es la forma más probable de que el proyecto se trabe.** `gemma4:12b` ya
puntuó **38–41/50** en este held-out y `qwen3.5:4b` llegó a 38/50 con una
interfaz reparada **[read]**. Si un modelo de frontera puntúa 43/50, se le está
pidiendo a toda la arquitectura que preserve una diferencia de 2 puntos, todos
los arms empatan, y un empate se lee como éxito.

**Compuerta.** S2 no corre hasta que esto pase.

**Falsación.** Frontera menos el mejor local queda dentro del intervalo pareado
con n = 50 → **esta suite no puede medir este proyecto**, y el arreglo es una
distribución de tareas más difícil, no un tratamiento mejor. Reemplazos
candidatos, en orden: el split `held_out_delta` de `clinical_learning` (su regla
se invierte, así que el protocolo memorizado falla), después los dominios
`causal_workflow` y `quantum` que ya están en `../verified-runtime`.

**S1a — el fallback que este paso nombró de antemano, corrido antes de gastar
nada.** [`results/S1a-delta-20260907/`](../../results/S1a-delta-20260907/BRIEF.md),
$0, 12 casos de `held_out_delta`, todo lo demás idéntico a S0c **[ran]**:

| | `gemma4:12b` (target) | `qwen3.5:4b` | `qwen3.5:9b` |
|---|---|---|---|
| `held_out` (S0c) | 4/12 | 3/12 | 3/12 |
| **`held_out_delta` (S1a, n=20)** | **12/20** | **6/20** | **6/20** |

**Hay headroom, en el split cuya regla plantada se invierte.** El 12B se despega
**+6 de 20** de su mejor drafter donde antes empataba.
Esto es lo que el arm de frontera necesita para existir: una configuración donde
ser mejor sea posible. La pregunta de la suite quedó contestada — **S1 vale sus
$5 sobre `held_out_delta`, no sobre `held_out`.**

**Y produjo la trampa que C9 predijo, en la forma en que se le habría creído.**
Con n=12, ordenar por α coincidió con ordenar por puntaje verificado (9B > 4B) —
por la razón equivocada: el 9B indenta como el target y el 4B no. Una confirmación
de la afirmación central del proyecto, llegando por accidente de indentación,
sobre una diferencia de un caso que se evaporó en n=20. El reporte ahora se niega
a interpretar esa línea mientras C9 siga en pie.

**S1 corrió, tres veces, y falló su propia compuerta las tres.** Los 20 casos
delta, prompt canónico, verificador exacto, los cuatro candidatos locales fijos
**[ran]**:

| target | verificado | costo | headroom sobre `gemma4:12b` (12/20) |
|---|---|---|---|
| `gemini-3.5-flash-lite` | 13/20 | $0,0028 | **+1** |
| `gemini-3.8-flash` | 13/20 | $0,1338 | **+1** |
| `gemini-3.1-pro-preview` | **8/20** | $0,2885 | **−4** |
| `gemma4:12b-mlx`, local | 12/20 | $0 | — |

Gasto total $0,47, dentro del techo de $1 que el brief pre-registró. **La
compuerta decía que el target tiene que despegarse del mejor modelo local por un
margen en el que quepa una brecha de retiro. Ninguno lo hace, y el más caro es el
peor.**

**Lo que eso le cuesta a la arquitectura, dicho derecho.** La premisa de la Fase A
es *pagar precio de frontera, obtener respuestas de frontera, y llevarse la
medición gratis*. En esta tarea, pagar **48× más** compró el mismo 13/20 y pagar
**100× más** compró 8/20. No hay brecha de retiro que medir acá porque casi no hay
de qué retirarse — y ése es el resultado recurrente de este workspace llegando de
nuevo: en una tarea administrativa acotada, la capacidad está en la interfaz y en
el verificador, no en el tamaño ni en el precio del modelo.

**Es un hallazgo sobre la suite, no sobre la tesis.** La ventaja de la frontera, si
existe, no se ve en generación de un solo tiro sobre un chequeo de derivación de
20 casos. Las tres configuraciones que todavía podrían mostrarla están en la
decisión de §12.

**Ya no está bloqueado.** La key existe y se usó; lo que falló fue la elección de
target.

## 5. S2 — ¿α ordena como ordena la calidad? · BLOCKED

**Objetivo.** La condición de falsación del propio proyecto, comprada tan barata
como se puede comprar: **sin entrenar ningún adaptador**.

**El criterio, decidido el 2026-09-07 (§11, opción C).** No la aceptación por
caracteres — **acuerdo semántico de respuesta**: la respuesta parseada del
candidato contra la respuesta parseada del target, de modo que el orden de los
ítems, la indentación y una cerca de código no puedan moverlo. La α por
caracteres se sigue registrando al lado, y comparar las dos es trabajo de S6.

**Diseño.** Tres modelos cuyos puntajes verificados en esta suite ya se conocen
—`qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b`— hacen de expertos candidatos. Medir su
acuerdo con el target por región, y preguntar si ordenar por acuerdo reproduce
ordenar por puntaje verificado.

**S2a — el proxy local, y la corrección que produjo.** El criterio se aplicó a las
respuestas persistidas por S0c y S1a, y después se completó el split delta a sus
20 casos **[ran]**:

| corrida | | acuerdo | verificado | test de orden |
|---|---|---|---|---|
| S0c `held_out`, n=12 | `qwen3.5:4b` | 0,667 | 3/12 | **no comparable** — los candidatos |
| | `qwen3.5:9b` | 0,727 | 3/12 | empatan en calidad |
| ~~S1a `held_out_delta`, n=12~~ | ~~`qwen3.5:4b`~~ | ~~0,333~~ | ~~3/12~~ | ~~acuerdo y calidad coinciden~~ |
| ~~superado — ver abajo~~ | ~~`qwen3.5:9b`~~ | ~~0,556~~ | ~~4/12~~ | ~~9b > 4b en los dos~~ |
| **S1a `held_out_delta`, n=20** | `qwen3.5:4b` | 0,350 | **6/20** | **no comparable** — los |
| | `qwen3.5:9b` | 0,533 | **6/20** | candidatos empatan en calidad |

**El resultado de n=12 no sobrevivió a su propio split.** Con 12 casos los
candidatos diferían en un caso verificado y los órdenes "coincidían"; con 20
empatan exactamente, y no hay orden que el criterio pueda reproducir. Un caso de
diferencia nunca fue un orden, y la fila anterior queda tachada en vez de borrada
porque ésa es justo la falla que este plan existe para hacer visible.

**S2 corrió contra los tres targets, y el criterio aguanta** — con una salvedad
que tiene que viajar con él. El test de orden se puntúa por pares, sobre
exactamente los pares de candidatos cuyos puntajes verificados difieren, con un
cuarto candidato (`qwen3.5:2b`) agregado para que la escalera vaya de 2B a 12B y
deje de empatar **[ran]**:

| target | **acuerdo semántico** | α por caracteres | qué dijo la α por caracteres |
|---|---|---|---|
| `gemini-3.5-flash-lite` | **5/5** | 2/5 | puso al **mejor** candidato **último** |
| `gemini-3.8-flash` | **5/5** | 1/5 | puso al **mejor** candidato **último** |
| `gemini-3.1-pro-preview` | **4/5** | 4/5 | lo puso primero — este target indenta |

**14 de 15 pares discriminables ordenados bien, contra tres targets
independientes.** El criterio que el plan adoptó en §11 hace lo que un criterio de
promoción tiene que hacer.

**Y la misma tabla salda §11 empíricamente.** La α por caracteres sacó 1/5 con un
target y 4/5 con otro **sobre los mismos candidatos y los mismos casos** — lo
único que cambió es si el target indenta como el candidato. Una métrica cuya
concordancia se cuadruplica porque cambiaron las costumbres de formato del target
está midiendo formato. La opción C era la correcta y la evidencia ahora es
directa en vez de argumentada.

**La salvedad que tiene que viajar con esto.** S1 falló, así que los tres targets
son **pares del candidato más fuerte, no modelos de frontera**. Acordar con un par
no es un puntaje de destilación, y por lo tanto esto valida **la mecánica del
criterio**, no la afirmación de la arquitectura. La afirmación de destilación
necesita un target que de verdad sea mejor, y ningún Gemini disponible lo fue.

**Y C11 se ve en los números:** `qwen3.5:9b` no produjo respuesta parseable en 5 de
20 casos, que el criterio excluye, así que su acuerdo está medido sobre los 15
casos en los que contestó algo.

**Y volvió concreto a C11.** `qwen3.5:9b` saca el *mejor* acuerdo (0,533) mientras
no produce respuesta parseable en **5 de 20** casos — que el criterio excluye. Un
modelo que muchas veces no contesta nada parece uno que acuerda bien.

**Compuerta.** S4 — no se entrena ningún adaptador hasta saber que la aceptación
lleva la señal sobre la que la promoción se basaría.

**Falsación.** Los órdenes no coinciden, o el acuerdo es plano entre candidatos
que difieren en calidad verificada. Cualquiera de las dos mata a la aceptación como
criterio de promoción; el pool de adaptadores sobrevive, el router gratis no, y
el plan se reabre en el router.

**Segundo control, misma corrida, gratis.** La dispersión de α. Si todos los
candidatos aceptan igual, no hay nada que rutear, signifique α lo que signifique.

## 6. S3–S7 — los pasos que cuestan plata, y qué tiene que superar cada uno

**S3 · el arm de atribución — contestado por $0, y dice las dos cosas a la vez.**
Los arms de región de S4 registraron tres respuestas por caso (cada experto y el
adaptador general como referencia), así que el ruteo es un cálculo sobre corridas
que ya están en disco y no un experimento que comprar.
`python3 -m training.route_offline`, 40 casos **[ran]**:

| política | exactitud |
|---|---|
| oráculo — el mejor experto, caso por caso | 0,750 |
| **ruteado por acuerdo** | **0,725** |
| **siempre el experto de la propia región** | **0,725** |
| siempre el otro experto | 0,525 |

**El mecanismo funciona.** En los 10 casos donde los dos expertos difieren de
verdad, el acuerdo eligió al correcto **9 veces**, y el ruteo recuperó 0,725 de
los 0,750 disponibles.

**Y acá no compró nada.** Una regla que lee `clinic:` del prompt y elige el
experto de esa clínica saca exactamente los mismos 0,725, gratis. Es el resultado
que este workspace ya tuvo, cuando una jerarquía de memoria perdió contra búsqueda
léxica **[read]** — y aparece porque **esta suite escribe la región en el
prompt**. El ruteo existe para el caso donde la región *no* está declarada, y este
benchmark no puede plantear ese caso.

Así que el arm de atribución no mata al ruteo por aceptación: dice que la suite no
puede ponerle precio. Una suite que oculte la etiqueta de región sí puede, y ésa
es la versión más barata de la próxima pregunta.

**S4 · los adaptadores — adelantados al frente, y el kit ya está.** La falla de S1
traba el camino de la frontera, y este proyecto son adaptadores: una sesión que no
produce un adaptador no lo hizo avanzar ([`../../CLAUDE.md`](../../CLAUDE.md) §0).
Así que S4 deja de esperar detrás de S3.

**Lo que va en este repositorio** (`training/`), listo para correr en Colab porque
un 26B no entra en esta máquina:

| | |
|---|---|
| `build_dataset.py` | genera **600 train / 120 val / 60 delta** con el generador del propio benchmark sellado a **otra semilla**, y se niega a escribir si algún prompt de entrenamiento coincide con uno sellado **[ran]** |
| `evaluate.py` | el verificador exacto, una sola copia, calificando todos los arms — un modelo base y un adaptador calificados por código distinto no son comparables |
| `lora_kernel_colab.ipynb` | baseline → QLoRA → adaptador, y después dos expertos por región evaluados cruzados |

**Modelos**: `google/gemma-4-E4B-it` (T4 gratis) y `google/gemma-4-26B-A4B-it`
(A100), con `gemma-4-12B-it` como baseline local ya medido en 12/20.

**Las dos preguntas, y qué falsifica a cada una.**
1. **¿Ocurre la especialización?** El adaptador tiene que ganarle al base en `val`,
   que ninguno de los dos vio. Si no, ningún esquema de ruteo lo rescata.
2. **¿Los expertos difieren por región?** Un adaptador entrenado en la clínica α y
   otro en la β tienen que ser cada uno mejor en su propia región. Si no lo son, el
   pool es un experto con tres nombres y no hay nada que la aceptación pueda
   rutear — lo que terminaría con la afirmación central de la arquitectura, barato.

**LA PREGUNTA 1 ESTÁ CONTESTADA: LA ESPECIALIZACIÓN OCURRE.** `Qwen/Qwen3.5-2B`,
2026-09-08, [`results/S4-qwen35-2b-20260908/`](../../results/S4-qwen35-2b-20260908/BRIEF.md),
los cuatro números **[ran]** sobre casos que ningún arm vio en entrenamiento:

| | base | **adaptador** | |
|---|---|---|---|
| `val` (60) | 6/60 · **0,100** | **44/60 · 0,733** | **+63,3 puntos** |
| `val_delta` (30) | 6/30 · 0,200 | **12/30 · 0,400** | **+20,0 puntos** |

Cero respuestas inparseables en los dos arms del adaptador. Por clínica la
ganancia es pareja —alpha 15/20, beta 15/20, gamma 14/20— así que no hay un solo
protocolo cargando el resultado. El adaptador son **10,9 M de parámetros
entrenables, 0,58 % del modelo**, entrenados dos épocas sobre 600 casos generados
en una T4 gratis, adaptando **las siete** proyecciones de atención y MLP —
incluidas `q_proj` y `k_proj`, que una nota anterior afirmaba excluidas por el
QK-norm de qwen3. No lo estaban: el flag que las excluía sólo lo leía el
preflight, y la preocupación no mordió en el entrenamiento. **[ran]**

**Y la sonda de falsa promoción dio negativa, que es la mitad más fuerte.**
`delta` es la clínica que no aparece en ningún split de entrenamiento y cuya regla
no publicada **se invierte**. Un adaptador que hubiera memorizado la regla ganaría
en `val` y se derrumbaría ahí. Éste **mejoró 20 puntos**. Lo que aprendió lee el
caso en vez de recitar el protocolo.

**Cuánto de la historia de este proyecto fue infraestructura, y cómo se separó del
resultado.** El arm del adaptador devolvió 0 tres veces antes de esto, y las tres
fue la máquina: una placa sin bf16 real (C15), un reanudado que habría guardado
ese cero (C15), y gradient checkpointing activo durante la generación, que no sólo
apaga la caché KV sino que corrompe la salida. Cada cero se leía exactamente como
*"no hubo especialización"* — una de las dos condiciones de falsación de este
paso. El número verdadero es +63.

**LA PREGUNTA 2 TAMBIÉN ESTÁ CONTESTADA, Y LA RESPUESTA ES ASIMÉTRICA.** Dos
expertos, uno entrenado sólo con la clínica `alpha` y otro sólo con `beta`, cada
uno con el **presupuesto de entrenamiento igualado** al del adaptador general y no
la cantidad de épocas, evaluados cruzados **[ran]**:

| | en `alpha` | en `beta` |
|---|---|---|
| **experto α** | **0,700** (14/20) | 0,400 (8/20) |
| **experto β** | 0,650 (13/20) | **0,750** (15/20) |

**La diagonal gana en las dos direcciones** —propia región 0,725 contra ajena
0,525, **+20 puntos**— así que hay algo para que un router elija y el pool no es
un experto con tres nombres.

**Pero una sola columna puede sostener esa afirmación.** En los casos de `beta`
los dos expertos difieren en siete casos (15 contra 8); en los de `alpha` difieren
en **uno** (14 contra 13), que con n = 20 no es una diferencia. El experto β
generaliza a la clínica de α casi tan bien como α; el experto α no devuelve el
favor.

Así que lo honesto es: **la especialización por región es real y no es
simétrica.** Un router construido sobre esta superficie tendría señal fuerte en
una región y ninguna en la otra — que es un hallazgo sobre lo que el ruteo tiene
que manejar, no una falla de los adaptadores.

**El primer intento de este arm fue anulado y re-corrido**, porque 200 casos a la
misma cantidad de épocas son un tercio de las actualizaciones: el primer experto α
llegó a `train_loss` 1,079 contra 0,103 del adaptador general y sacó 3/20 en su
propia región. Comparar un experto sub-entrenado con uno entrenado mide el
presupuesto y lo llama especialización.

**La sonda que hay que reportar al lado de cualquier ganancia.** `delta` invierte
una de las reglas no publicadas y no aparece en ningún split de entrenamiento. Un
adaptador que memorizó la regla puntúa bien en `val` y se derrumba en `val_delta`.
Esa diferencia es el número de **falsa promoción**, y una ganancia publicada sin
él no es un resultado.

**S5 · la brecha de retiro.** Promover donde α cruzó el umbral, sacar la
frontera, volver a medir en el split sellado. El umbral y el margen de
no-inferioridad se pre-registran antes de la corrida;
`evaluation/frontier_gap.py` en `../verified-runtime` ya lleva la advertencia de
que una fracción de brecha cerrada no es una afirmación de equivalencia
**[read]**.

**S6 · `harness.lora`, y ahora tiene una segunda condición de victoria.** S0
encontró que la aceptación por caracteres está dominada por el formato, y fijar el
formato es exactamente lo que hace el adaptador kernel. Así que además de los
números de tokens y de llamadas malformadas, S6 contesta: **¿fijar el formato hace
que la α por caracteres coincida con el acuerdo semántico?** Si lo hace, se
recupera el puntaje de aceptación por región gratis de la arquitectura y fue el
adaptador kernel el que lo recuperó — el argumento más fuerte a favor de
`harness.lora` que este proyecto podría producir. Si no lo hace, la α por
caracteres queda como estadística intra-familia y el criterio de promoción sigue
siendo semántico.

**S6a — su headroom, calculado a $0 sobre las corridas que ya están en disco**
(`python3 -m alpha.kernel_headroom`) **[ran]**:

| número | valor | qué significa |
|---|---|---|
| overhead de protocolo en el prompt canónico | **~96 tokens, 43 % de un prompt de 223** | la vara es el pico de 817 de `gemma4nanoloop` sobre un set de herramientas real. Dos acciones no son una distribución de herramientas, y un adaptador que saca 96 tokens no puede demostrar que le gana al −85 % acá |
| tasa de llamadas malformadas, `gemma4:12b` | **0/40 en cuatro corridas** | nada que reparar |
| tasa de llamadas malformadas, `qwen3.5:4b` | 1/40 | nada que reparar |
| tasa de llamadas malformadas, `qwen3.5:9b` en `held_out_delta` | **3/12 — 25 %** | el único headroom que tiene el adaptador kernel en esta suite, y es sobre un modelo en el split más difícil |

**Así que S6 no se puede correr sobre esta suite como argumento de tokens, y
apenas se puede correr como argumento de sintaxis.** Necesita una distribución de
herramientas real —muchas acciones, varias fases— antes de que cualquiera de sus
dos números signifique algo. Eso es un hallazgo sobre la suite, y salió gratis.

Su propio headroom, cuando exista una distribución de herramientas real: cantidad de tokens de
protocolo y tasa de llamadas malformadas del modelo base con action tokens en el
prompt. Si eso ya está en 817 tokens y cero llamadas malformadas, el adaptador no
tiene qué reparar en esta suite y necesita una distribución de herramientas más
dura. Se reporta como tres números juntos —tokens, tasa de malformadas, latencia
incluyendo el swap del adaptador— contra el −85 % de `gemma4nanoloop` y contra
decodificación restringida, nunca contra prosa **[read]**.

**S7 · el torneo.** Sólo offline, con `w₁` desde un verificador que el bucle no
ve.

## 7. Restricciones dentro de las que el instrumento tiene que vivir

Hechos, no objeciones. Cada uno moldea cómo se corre un paso, no si la
arquitectura es correcta.

| # | restricción | consecuencia |
|---|---|---|
| C1 | Con T = 0 el prefijo aceptado **es** el prefijo común más largo con la continuación greedy del target, y greedy es prefix-consistente **[read]** | la superficie α es medible hoy — sin GPU, sin vLLM, sin `LoRA-as-drafter` |
| C2 | Las APIs de chat de frontera no exponen logprobs de una continuación **forzada** **[read]** | el rejection sampling real contra una API de frontera no es implementable; C1 es el instrumento |
| C3 | Un target de frontera no comparte el tokenizador del modelo base **[read]** | α se mide en caracteres. Sólido como puntaje de destilación, **no sólido como afirmación de velocidad** |
| C4 | `vllm` no sirve en esta máquina (arm64, 16 GB) **[ran]** | todo paso con vLLM es GPU alquilada y va tarde en el orden |
| C5 | LoRA-como-drafter es un RFC abierto, [vllm#52038](https://github.com/vllm-project/vllm/issues/52038) **[read]** | la Fase A corre con adaptadores fuera del camino especulativo, o con drafters chicos por dominio |
| C6 | ollama ignora un prefill de asistente **[ran]** | la posición 0 es primaria; la α de mitad de respuesta depende de la bandera `restarted` |
| C7 | Todos los modelos locales acá piensan **[ran]** | α se mide sobre el **canal de respuesta**; el canal de razonamiento se registra y nunca se concatena |
| C8 | No hay `OPENROUTER_API_KEY` en esta máquina **[ran]** | S1 y S2 están bloqueados por un humano |
| C9 | La coincidencia de prefijo por caracteres está dominada por el formato: respuestas idénticas sacan 0,00 entre formatos, y respuestas distintas sacan 0,44 dentro de un mismo formato **[ran]** | **decidido (§11, opción C):** el criterio de promoción es el acuerdo semántico de respuesta; la α por caracteres se reporta al lado y no ordena nada; si fijar el formato las reconcilia es la condición de victoria de S6 |
| C10 | Los agentes bajo `.claude/agents/` se cargan para una sesión rooteada en este repositorio, no en el workspace de arriba **[ran]** | están symlinkeados en `../.claude/agents/` para que una sesión rooteada en el workspace también pueda invocarlos |
| C18 | **vLLM 0.28.0 acepta un `LoRARequest` y sirve el modelo base en silencio.** Sin error, sin advertencia, salida byte a byte idéntica, con un adaptador peft válido cuya config coincide con el modelo servido **[ran]** | el sustrato de la arquitectura está sin probar, y cualquier número futuro de servido hay que contrastarlo contra una salida demostrablemente distinta antes de creerlo |
| C17 | **Gradient checkpointing activo durante la generación corrompe la salida**, no sólo apaga la caché KV: el mismo adaptador sacó 0/60 con él prendido y 44/60 apagado **[ran]** | los flags de entrenamiento se apagan antes de evaluar, y un cero de un modelo cuya loss de entrenamiento fue 0,10 se trata como falla de instrumento hasta probar lo contrario |
| C15 | Una **T4 no tiene bf16**. El base generó bien en bf16 y después toda generación con LoRA murió con "GET was unable to find an engine to execute this computation" — reportado como 0/60 **[ran]** | la precisión la elige `is_bf16_supported()`, no la costumbre. Leído como resultado habría dicho "no hubo especialización", que es una de las dos condiciones de falsación de S4 |
| C16 | Colab gratuito **reclamó tres sesiones** en unos 40 minutos de GPU cada una **[ran]** | la persistencia por arm tiene que sobrevivir a la *sesión*, no sólo al proceso: los resultados se bajan a esta máquina después de cada arm, y un reanudado tiene que volver a subirlos. Si no, hay que cambiar de tier |
| C14 | Los datos de entrenamiento se **generan** con el generador del propio benchmark a otra semilla, y un chequeo de fuga se niega a escribir si un prompt de entrenamiento es igual a uno sellado **[ran]** | se puede entrenar un adaptador con cientos de casos mientras los 50 + 20 sellados siguen sin verse; sin el chequeo la evaluación sería un test de memoria y todo número posterior quedaría anulado |
| C12 | En esta suite, tres targets Gemini sacaron 13/20, 13/20 y 8/20 contra el 12/20 de un 12B local, a $0,003, $0,13 y $0,29 **[ran]** | no hay ventaja de frontera que destilar acá; la premisa de la Fase A necesita una tarea donde pagar más compre más, y encontrar esa tarea es ahora la pregunta que gobierna |
| C13 | La concordancia por pares de la α por caracteres se movió **1/5 → 4/5** entre targets, sobre candidatos y casos idénticos, sólo porque el target pro indenta **[ran]** | evidencia directa de C9, y la razón por la que la decisión de §11 quedó saldada en vez de provisoria |
| C11 | El acuerdo semántico **excluye** los casos donde algún lado no produjo respuesta parseable, y `qwen3.5:9b` no la produjo en 3 de 12 casos delta mientras sacaba el *mejor* acuerdo **[ran]** | el criterio siempre se lee al lado de la cuenta de no-parseables, o un modelo que muchas veces no contesta nada parece el que mejor acuerda — y esa falla es justo la que `harness.lora` existe para reparar, lo que acopla S6 al criterio en vez de dejarlo aguas abajo |

## 8. Deliberadamente no construido

KV cache entre adaptadores, tree attention cruzada, un runtime propio, packs
verticales, el control plane, el marketplace. Todo aguas abajo de §S5. El
problema del KV cache es la parte cara de la arquitectura y sólo vale resolverlo
una vez que una superficie diga que las ramas valen la comparación.

## 9. Agentes y skills — el registro

Se crean, se editan y se retiran a medida que el trabajo aprende. La regla de
ciclo de vida está en [`../../CLAUDE.md`](../../CLAUDE.md) §5.

| fecha | cambio | porque |
|---|---|---|
| 2026-09-07 | creado [`headroom-auditor`](../../.claude/agents/headroom-auditor.md) | S1 es el paso con más chances de terminar el proyecto, y el que una sesión más tienta saltear |
| 2026-09-07 | creado [`instrument-skeptic`](../../.claude/agents/instrument-skeptic.md) | S0 encontró dos fallas del instrumento antes de que existiera un número; ese chequeo no debería depender de acordarse |
| 2026-09-07 | creado [`alpha-runner`](../../.claude/agents/alpha-runner.md) | las corridas tienen que streamear, persistir por caso y poder abortarse |
| 2026-09-07 | creado [`mirror-keeper`](../../.claude/agents/mirror-keeper.md) | la única compuerta de CI del repositorio son los documentos bilingües |
| 2026-09-07 | creado el skill [`experiment-brief`](../../.claude/skills/experiment-brief/SKILL.md) | el briefing va antes de la corrida, no al lado del reporte |
| 2026-09-07 | creado el skill [`alpha-surface`](../../.claude/skills/alpha-surface/SKILL.md) | qué licencia α y qué no tiene que viajar con el comando |
| 2026-09-07 | buscados los dos marketplaces de skills, no se instaló ninguno | todo skill de evaluación encontrado se apoya en LLM-como-juez; el verificador de este proyecto es exacto **[ran]** |
| 2026-09-07 | agregado [`../../CLAUDE.md`](../../CLAUDE.md) §0 — la regla anti-deriva — por indicación del usuario | dos sesiones de medición produjeron cuatro hallazgos de instrumento y **ningún adaptador**; la regla nombra la deriva para que la próxima sesión no la repita |
| 2026-09-07 | construido `training/` — constructor de dataset, verificador compartido, notebook de Colab | el proyecto son adaptadores y la máquina no puede entrenar uno; lo que se entrega para cualquier cosa que necesite GPU es un notebook commiteado acá |
| 2026-09-07 | creado [`colab-runner`](../../.claude/agents/colab-runner.md); `adapter-trainer` nunca se escribió | el CLI de Colab convierte el paso de los adaptadores en algo que esta sesión ejecuta en vez de delegar, así que el agente declarado para S4 pasó a ser el que maneja el runtime |
| 2026-09-07 | removidos el camino de prefill de mitad de respuesta, el segundo template de prompt, el verificador duplicado y la corrida superada de 6 casos | ollama ignora el prefill así que esas posiciones nunca dieron un número; dos prompts es una variable de más; un verificador copiado es una segunda cosa que mantener sincronizada |
| 2026-09-07 | editado el skill [`alpha-surface`](../../.claude/skills/alpha-surface/SKILL.md) | el criterio de promoción cambió por §11, y un skill que siguiera describiendo el viejo viajaría con cada comando futuro |

**Declarados, no construidos:** `adapter-trainer` (S4), `kernel-bench` (S6),
`tournament-referee` (S7), y los skills `withdrawal-gap` (S5) y
`adapter-training` (S4). Cada uno espera al paso que lo justifica.

## 10. Condiciones de parada, decididas ahora

- **Rediseños del instrumento.** **3, y después un cuarto hecho bajo revisión.**
  Los tres fueron: el canal de razonamiento y el prefill ausente; medir el payload
  en vez del formato; y la vuelta al prompt canónico. La condición disparó, la
  sesión se detuvo, y el cuarto cambio —que el criterio de promoción pase a ser
  semántico— **lo decidió el humano que la regla exigía**, no quien estaba
  construyendo el instrumento (§11, 2026-09-07). El contador vuelve a 0 y la regla
  queda en pie para los próximos tres.
- **Los arms planos se abandonan, no se completan.** Una corrida visiblemente
  plana a un tercio del camino se mata, y se registra cuánto costó abortar contra
  cuánto costaba terminar.
- **El número se publica salga como salga.** La brecha de retiro es el proyecto;
  una brecha grande es un resultado, no un fracaso que se re-corre hasta ser
  chico.

## 11. Las decisiones — una tomada, una abierta

### Tomada el 2026-09-07: qué es α

No es un commit — es una elección, porque cambia lo que α *es*, y ése es el
término central de la arquitectura.

**El problema.** El criterio de promoción tiene que comparar un experto chico
local con un modelo de frontera ajeno que no comparte ni tokenizador (C3) ni
convenciones de formato (C9). La aceptación por caracteres a través de esa
frontera mide el formato.

**Opción A — acuerdo semántico de respuesta.** La promoción se decide por si la
*respuesta parseada* del experto coincide con la del target. Honesta, barata,
disponible hoy, y es lo que la Fase B necesita. Lo que resigna: la palabra
"aceptación". Ya no es la α del speculative decoding; es acuerdo de respuesta, y
el relato de "gratis dentro del camino de servicio" pasa a ser "gratis dentro de
una pasada que ya estábamos pagando", que sigue siendo cierto pero es una
afirmación más chica.

**Opción B — fijar el formato primero.** La aceptación por caracteres significa
algo en cuanto el formato deja de ser una variable, y fijar el formato es
exactamente para lo que está `harness.lora`. Esto pone a **S6 aguas arriba de
S2** y reordena el plan: no hay superficie α hasta que exista el adaptador
kernel. Fiel a la arquitectura tal como está especificada, y bastante más cara:
pone una corrida de entrenamiento antes de la falsación barata del proyecto, que
es justo lo que este plan se reordenó para evitar.

**Opción C — las dos, en orden.** La opción A ahora, como criterio de promoción
para S1–S5, con la α por caracteres reportada al lado *dentro de una misma
familia de modelos*, donde sí está definida. Y después la opción B medida como la
condición de victoria del propio S6: ¿fijar el formato hace que la α por
caracteres coincida con el acuerdo semántico? Esa pregunta merece un número
propio, y es el argumento más fuerte a favor del adaptador kernel que este
proyecto podría producir.

**Decidido el 2026-09-07: la C**, y desde entonces confirmado directamente por
C13. El criterio de promoción para S1–S5 es el
acuerdo semántico de respuesta, la α por caracteres se reporta al lado y no ordena
nada, y S6 se queda con la pregunta de si fijar el formato reconcilia a las dos.
Implementado en `alpha/report.py::semantic`, fijado por seis tests, y aplicado
retroactivamente a todas las corridas que ya estaban en disco — el criterio se
calcula sobre las respuestas guardadas, así que no hubo que volver a correr nada.

### El camino de vuelta al plan original, en orden de dependencias (2026-09-08)

Colab Pro está confirmado en esta cuenta **[ran]**: **L4** (23 GB, capability 8,9)
y **A100-SXM4** (40 GB, capability 8,0), las dos con bf16 real. Tres bloqueos se
disuelven juntos — la tenencia de las sesiones, el parche de fp16 que produjo cada
cero falso, y la imposibilidad de correr vLLM.

**Y uno que nunca fue obvio: el target no tiene por qué ser una API.** Una placa de
40 GB puede hospedar un Qwen3.5 grande como referencia fuerte, y un target **de la
misma familia que los adaptadores comparte su tokenizador** — que es exactamente
lo que C2 y C3 decían que volvía inmedible la aceptación real a nivel de token. La
métrica central de la arquitectura queda disponible por primera vez.

| # | paso | placa | compuerta que tiene que pasar | costo |
|---|---|---|---|---|
| **P1** | **Ponerle precio al router.** Re-correr los 40 casos de ruteo con la línea `clinic:` **enmascarada**, para que la regla léxica no tenga qué leer | L4 | el acuerdo sigue eligiendo bien mientras el baseline por palabra clave cae a azar | ~15 min |
| **P2** | **Replicar S4 en bf16.** Los mismos arms, bf16 real, sin camino fp16 | L4 | el +63,3 sobrevive; si no, todos los números de S4 eran artefacto de precisión | ~30 min |
| **P3** | **vLLM multi-LoRA, el sustrato** | A100 | **RESUELTO sobre una base densa** — falla silenciosa sobre Qwen3.5 | gastado |
| **P4** | **Un target fuerte de la misma familia.** Servir un Qwen3.5 grande al lado de los adaptadores de 2B | A100 | aceptación **a nivel de token** medible por fin, tokenizador compartido, sin sustituto textual | ~1 h |
| **P5** | **S1 otra vez, local.** ¿El target fuerte de la misma familia le saca a los adaptadores un margen donde quepa una brecha de retiro? | A100 | si no, la suite sigue equivocada y aplican las otras opciones de §11 | ~30 min |
| **P6** | **S5 — la brecha de retiro.** Promover donde la aceptación cruza el umbral, sacar el target, volver a medir | A100 | **el producto** | ~1 h |
| **P7** | **S6 — `harness.lora`** contra una distribución de herramientas real, que esta suite no tiene | L4 | tokens, tasa de malformadas y latencia de swap juntos | primero los fixtures |
| **P8** | **S7 — el torneo**, con `w₁` desde un verificador que el bucle no ve | L4 | la evolución | después de P6 |

**Por qué este orden.** P1 y P2 son baratos y deciden si lo que ya tenemos es
real; correrlos en una placa Pro cuesta minutos y saca dos dudas de encima. P3 y
P4 compran el sustrato y la métrica — nada por encima de ellos se puede afirmar
sobre *servir* hasta que existan. P5 es la compuerta que decide si P6, el
producto, es comprable; se compra antes que P6 y no junto con él.

**La A100 es el recurso caro, así que P1, P2, P7 y P8 se quedan en la L4.**

**Los directorios de corrida se despegaron de esta tabla después de P4, y ganan
los nombres en disco.** `P5` es el chequeo de headroom sobre la suite nueva,
`P6` la brecha de retiro, `P7` el paso de la calculadora que la cerró —
insertado porque la brecha no cerraba sin herramienta — y `P8` es
`harness.lora`, al que esta tabla llama P7. El torneo, el P8 de esta tabla,
no se compró.


#### P64 — hito 5, sintético: el segundo miembro útil **[ran]** 2026-09-18 · LIBERADO al segundo intento

Una incógnita: ¿el experto `commitment` del desk entra por la puerta de la Fase 1 y co-reside con `email-full@v1` sobre una base, ruteado por su pregunta? Pre-registrado en [`results/P64-second-member-20260918/BRIEF.md`](../../results/P64-second-member-20260918/BRIEF.md). Una sesión de L4, 16 minutos: `desk-commitment` re-entrenado desde `data_desk/train.jsonl` (600 ejemplos, `release_gate.RECIPE`) en un subproceso, y después servido junto a `email-full` en un vLLM detrás del proxy con `--prune --member-prompt --auto`; suite desk, 240 casos, semilla 424242 — los casos de P55b.

**Resultado [ran].** Pasan todas las compuertas pre-registradas, leídas de `pool_second.json`: G1 identidad `applied` 3/3 en ambos miembros; G2 herramientas alcanzables en ambos; G2′ `auto` sirve un prompt de desk con `desk-commitment` y un listado con `email-full`; el brazo nuevo **empata el g600 grabado, 240/240 contra 240/240 con 0 pares discordantes**; y le gana a la base **240 a 38, discordantes 202 : 0**. Con $b$ y $c$ las cuentas discordantes el test de signos exacto es

$$p = 2\sum_{k=0}^{\min(b,c)} \binom{b+c}{k} 2^{-(b+c)} = 2\cdot 2^{-202} \approx 3\times10^{-61}.$$

La base no está ociosa en esta región — **331 llamadas, 13 rechazadas, 3 malformadas, 19 sin decidir** — estira la mano hacia las herramientas y no sabe qué hacer con lo que vuelve; el miembro hace **240 llamadas en 240 casos, 0 rechazadas**. Esta vez el adaptador volvió a casa: `adapter_model.safetensors` da el hash `05022bec…` del manifiesto **[ran]**. Manifiesto: `releases/desk-commitment@v1.json`.

**Chequeado antes de creerlo, cero GPU:** 0 de 240 ids evaluados y 0 de 240 prompts evaluados aparecen en el corpus de 600 ejemplos (la falla de P53); la respuesta es una fecha leída del resultado de una herramienta, y la base con la misma herramienta está en 0,158, así que el 1,000 es el protocolo y no memoria.

**Lo que no dice.** Un techo no ordena: `g75` ya satura esta banda (P55b), así que nada acá rankea expertos, y la banda `commitment_deep` (P60 §3c/3d) está sin medir. El router se ejercitó con una sonda por miembro en vivo y con prompts generados offline (60/60, 60/60, 150/150, 140/140) — su prueba real es el tráfico del hito 4. Y estos dos miembros *sí* se encuentran en un problema — leen el mismo inbox, por eso las claves sobre el listado mal-rutearon 15 de 60 y las claves sobre la pregunta no — pero la selección entre ellos la sigue haciendo un diccionario, no la aceptación.

**El intento 1** liberó sobre 60 casos — el `eval_n` por defecto de la suite — y dejó los pesos en la tarjeta; queda en `attempt1_60_cases_weights_lost/`. Un arreglo del runner, no un rediseño del instrumento: las compuertas y el brief no se movieron.

#### P63 — hito 3: el turno en vivo de OpenClaw **[ran]** 2026-09-18 · EN VIVO al séptimo intento

OpenClaw 2026.9.4 en esta Mac → proxy local (`--prune --auto`) → cloudflared → vLLM en una L4 → `email-full@v1`; las herramientas del inbox por MCP; 40 turnos sintéticos, una sesión cada uno; identidad a través del túnel 3/3. Pre-registrado: todo turno local, ninguna llamada a una herramienta no ofrecida, ≥ la mitad de los turnos humanos llama una herramienta; exactitud contra la barra 0,655, descriptiva con n = 32. **Bajo el prompt del runtime (intento 4): NOT LIVE — 2/32 turnos humanos llaman una herramienta, humanos 0,281**, la conducta de la base pelada con las herramientas al alcance. **Bajo el prompt liberado del miembro (intento 7, `--member-prompt`, el tope de idas y vueltas y 256 tokens por paso — las dos cotas del loop del corpus): EN VIVO — 40/40 local, 0 inventadas, 19/32 turnos humanos llaman una herramienta, 22/32 = 0,688 contra 0,655 ($p = 0,43$)**, 3,5 s por turno. Seis fallas del camino en vivo en el medio, cada una encontrada por el camino real y corregida con test: el router leía el system prompt de 37 KB del runtime y su sobre de contexto interno; el experto repetía el bloque de herramientas y el proxy ejecutaba sus propios placeholders; sin corte en `</tag>` el experto inventaba el resultado de la herramienta de un tirón; sin tope de idas y vueltas (30 repeticiones de una llamada malformada); sin cota de tokens (turnos de tres minutos); el lock de gateway de un turno matado. **Qué decide: un miembro es lo que su corpus enseñó — el bloque y el prompt; `--prune` y `--member-prompt` son los defaults para un miembro.** Libro de intentos en `results/P63-openclaw-live-20260918/BRIEF.md`; cada intento guardado al lado.

#### P62 — ruteo por request: el cliente no nombra modelo **[ran]** 2026-09-18 · EMPATA, cero GPU

`route.py`: una superficie de palabras clave por región (el diccionario del baseline del router, movido al lado de la decisión), `serve: local | out` según lo medido (fluidos afuera, P40). `openai_proxy --auto NOMBRE [--auto-out MODELO]` reescribe `model` en el lugar y registra la decisión sólo con formas. Instrumento: `route.replay` sobre los registros de P41 — entregado(política) según FOUNDATIONS §8.4, un caso entregado al miembro equivocado cuenta como mal. Pre-registrado en el test antes del replay: empata al por región y 0 mal ruteados. **Resultado:** por región 0,775 · por request **0,775** · mal ruteados **0** · afuera 37,5 %. La capa de decisión no cuesta nada sobre tráfico generado; el hito 4 vuelve a medir el diccionario sobre tráfico real, donde un clasificador aprendido (la base zero-shot) es el brazo a comprar si falla. `results/P62-route-per-request-20260918/`.

#### P61 — pesos o harness en la región de email **[ran]** 2026-09-18 · HACEN FALTA LOS PESOS

Una incógnita: ¿la base 3B, con `knowledge/email-triage.md` en su system prompt, resuelve la región de email como el experto QLoRA? Tres brazos, una sesión L4, los 475 casos de P55, el loop en modo corpus; pre-registrado en `results/P61-knowledge-vs-weights-20260918/BRIEF.md` (FOUNDATIONS §7.3, el test de signos sobre pares discordantes): `kb_pays` (base+kb > base, $p<0,05$), `weights_needed` (experto > base+kb, $p<0,05$), `harness_replaces_weights` (ninguno, y exactitud humana dentro de 0,05). La línea de precio se graba con el veredicto: tokens del documento por request, llamadas a herramientas por caso. La falla escrita primero: base+kb ≤ base cierra el lado del harness para esta base. Por qué un procedimiento y no la regla: P55 **[ran]** tiene a la base contestando NOT IMPORTANT con **cero llamadas a herramientas en 230 de 351** mensajes humanos aunque el system prompt enuncia la regla.

**Resultado [ran].** **Hito 1 [ran] 2026-09-18, P61 — hacen falta los pesos en esta región, y la razón es precisa.** La base con el documento de procedimiento hizo **0 llamadas a herramientas en 351 de 351** mensajes humanos, igual que la base pelada: no sigue un procedimiento escrito en el contexto. Su exactitud se movió 0,345 → 0,601 porque el documento le dio vuelta la respuesta por defecto, todavía debajo de la barra de siempre-IMPORTANT de 0,655; el experto, en 0,989 con 1053 llamadas, le gana **137 : 1**. El documento cuesta 914 tokens en cada request; el adaptador, ninguno. Así que en un 3B el harness lleva conocimiento, no procedimiento — el procedimiento tiene que estar en los pesos. El `kb_pays` pre-registrado disparó con 164 : 74, $p = 0$ — un test de signos contra una base que contesta una palabra no distingue un procedimiento seguido de un default dado vuelta; ahora lo guarda la barra de mayoría (`knowledge_arm.verdict`, test agregado, la sesión releída con `--reread`, brazos intactos). `results/P61-knowledge-vs-weights-20260918/session.json`. **Qué decide:** en un 3B la personalización sólo por documento queda cerrada; los documentos llevan conocimiento sobre un adaptador que lleva el procedimiento, o la base tiene que ser más grande — el próximo documento no se escribe para esta base.

#### P60 §3b — vLLM aplica un LoRA sobre el 32B AWQ **[ran]** 2026-09-18

El preflight que decide si un target entrenado se puede servir. Un adaptador de juguete (150 pasos, r=16, base NF4) entrenado sobre `Qwen2.5-32B-Instruct`, servido sobre `Qwen2.5-32B-Instruct-AWQ` con `--enable-lora`. Compuerta de texto (cambios de argmax en 3 probes): **2/3**. Compuerta de logprobs — media de $|\ell_m(t) - \ell_b(t)|$ sobre una continuación fija, contra el control base-vs-base (FOUNDATIONS §3.4): **0,49, 0,34, 0,22 nats contra 0,000 — 3/3, aplicado**. Tres intentos, dos fallas de instrumento atrapadas antes de creer un número: el `MARGS` vacío del chain cayó a los flags `--adapter` del pool y el runner le pasó a vLLM `tiny32=domain=…` (intento 1); la compuerta de texto sola leyó un adaptador de 60 pasos como *no aplicado* con 1/3 mientras el engine lo había cargado y usaba el wrapper Punica de GPU (intento 2) — se agregó la compuerta de logprobs con control de determinismo, con tests. `results/P60-deep-window-20260917/awq_gate.json`; los intentos quedan al lado.

#### P24 — una máscara gramatical compra limpieza, no acierto

[`results/P24-constrained-20260912/`](../../results/P24-constrained-20260912/BRIEF.md).
Enmascarar el sampler para que una llamada malformada sea imposible en vez de
improbable. Los rechazos caen **23 → 10** mientras los valores del oráculo quedan en
**94/96, idénticos** — el canje para el que fue construida, y una *subida* de
cobertura habría significado que la gramática hacía el trabajo del adaptador. La
respuesta final va de 5/30 a 4/30, que es un caso: **P21 ya mostró que 22 de 25
fallos eran física con todos los valores en la mano.** La predicción, replayada
offline sobre los transcripts de P21, decía que el 74% de los rechazos se volverían
imposibles y fue el 57% — buen predictor de dirección, optimista de tamaño, porque la
reparación es una propiedad de la distribución de fallos que encuentra y no una
constante de la máscara. Y el tratamiento crasheó una vez sobre una forma que
`grammar_check.py` no podía ver: Qwen rellena su matriz de embeddings más allá del
vocabulario, y **un verificador de la gramática no es un verificador del sampler**.

#### P28 — una convención de esquema funciona, la otra sale al revés

[`results/P28-schema-conventions-20260914/`](../../results/P28-schema-conventions-20260914/BRIEF.md).

| brazo | valores del oráculo | rechazadas |
|---|--:|--:|
| instrucción entrenada | 59/96 = 0,615 | 17 |
| esquema OpenAI, plano | 41/96 = 0,427 | **88** |
| **esquema + aridad** | 51/96 = **0,531** | **17** |
| esquema + aridad + enums | 48/96 = 0,500 | 37 |

**La aridad —un parámetro requerido se renderiza posicionalmente— baja los rechazos al
número exacto del brazo entrenado y recupera el 55% del costo del esquema**, con 0 de
48 líneas que nombren una herramienta o un dominio.

**Los enums estaban predichos para no hacer nada acá y lo empeoraron.** Arreglaron
aquello a lo que apuntaban — `property=D` aparece siete veces sin ellos y nunca con
ellos — y los fallos de manual subieron **3 → 17**: decirle al adaptador parte del
vocabulario lo hizo consultar con más confianza y errar en otro argumento. **"El 56%
de los rechazos fuera de dominio son nombres" sobrevive; "entonces decile los nombres"
no se sigue.**

#### P30 — una región que es la mañana de alguien, y la primera corrida multi-turno

[`results/P30-email-triage-20260914/`](../../results/P30-email-triage-20260914/BRIEF.md).
Triar el correo de una persona es una tarea estrecha repetida a diario, y a
diferencia de la mecánica de fluidos **la respuesta correcta es verificable
mecánicamente** — un verificador sin juez, que es lo que a S7 todavía le falta.

**La suite tuvo que fallar su propio test dos veces antes de valer la pena.** Una
regla que sólo lee el listado llegaba a **0,795** contra una barra de 0,520 en el
primer borrador, porque `Re:` se escribía exactamente cuando el usuario había
respondido y el preview traía el pedido; **0,770** en el segundo, porque `noreply@`
se ve y lo automático nunca es importante. El segundo fallo corrigió el instrumento y
no el material: detectar un remitente automático es gratis y un humano lo hace de un
vistazo, así que el techo se mide sobre los mensajes **humanos**, donde queda en
**0,680 contra una barra de 0,680** — exactamente la clase mayoritaria, con los 0,320
de margen restante enteramente para las herramientas.

**Y el bucle multi-turno corrió por primera vez.** `docs/SERVING.md` lo llamaba
ensamblado y sin medir; un cliente OpenAI mandando `tools=[…]`, leyendo `tool_calls`,
ejecutándolas y devolviendo resultados `role: "tool"` cerró el camino con **24
llamadas, 0 rechazadas, 0 sin decidir**. Eso ahora es un test y no una esperanza.
**Ningún modelo entrenado corrió sobre esta suite** — el stub prueba la plomería, no
el pool.

#### P44 — la confianza que este pool ya tiene no ordena sus errores

[`results/P44-calibration-20260915/`](../../results/P44-calibration-20260915/BRIEF.md).
Un chequeo de headroom comprado **antes** de entrenar ningún adapter tipado, porque
la propuesta de [`docs/analysis/typed-adapters.md`](../analysis/typed-adapters.md) se
apoya en una afirmación — *el logprob del primer token es un proxy pobre* — que llegó
**[read]** de un brief que cita a un lab sin benchmark público, y que se puede probar
gratis sobre nuestro propio modelo.

| | `email-full` | base |
|---|--:|--:|
| exactitud, **sin herramientas** | 0,425 | 0,345 |
| **confianza media** | **0,902** | **0,999** |
| ECE | 0,478 | 0,654 |
| **AURC** | **0,612** | 0,627 |
| piso oráculo | 0,213 | 0,289 |
| **brecha** | **0,400** | **0,338** |

**La base dice estar 99,9% segura y acierta el 34%** **[ran]**.

**La fila del medio, pre-registrada, es lo que hace legible esto.** Una confianza mal
calibrada pero *rankeable* se arregla con temperature scaling, que no cuesta
entrenamiento — y ésa habría sido la respuesta honesta a un ECE grande solo. **Éstas
no son rankeables**: 0,40 y 0,34 por encima del piso. El brazo tipado se **compra**,
no empata ni se cancela.

**La salvedad viaja con los números**: estas exactitudes son sin herramientas, una
pasada desde el listado, por eso 0,425 y no el 0,741 de P43. Ésa es la línea base
pareja que una cabeza tipada enfrentaría, y no es el experto haciendo su trabajo.

**El piso a superar queda explícito**: brecha de AURC **0,400** sobre 351 casos, con
`bar.calibration()` como instrumento.

#### P43 — el end-to-end corre, y la compuerta por fin puede decidir

[`results/P43-openclaw-e2e-20260915/`](../../results/P43-openclaw-e2e-20260915/BRIEF.md).

**La compuerta decide ahora.** 260/351 mensajes humanos = **0,741** contra una barra
de 0,655, pasando en 246, **p exacta a una cola = 0,00036** — clarea por catorce
casos, no por uno **[ran]**.

**Y la exactitud casi no se movió**: 0,726 → 0,741, adentro de la dispersión que tres
corridas anteriores ya mostraban. Lo que cambió es la compuerta. Los **84, 81, 82**
que caían a los costados de un umbral de 83 nunca fueron el modelo titubeando — **la
suite era demasiado chica para el efecto y el umbral caía adentro de su propia
dispersión**. La potencia a n = 351 es **87%**; a n = 113 era **47%**.

`bar.n_for(0,655, 0,071)` fijó el tamaño *antes* de correr, y el brief pre-registró
que volver a caer cerca del umbral se leería como **un efecto más chico, no una suite
más grande**.

**El end-to-end corre**: OpenClaw en la Mac del usuario → proxy local → cloudflared →
vLLM en una L4 → el QLoRA `email-full` → vuelta, `status=200`, `NOT IMPORTANT`,
`stopReason=stop`, y **cero requests salieron de la máquina**.

**Lo que NO demuestra.** El turno de OpenClaw no hizo **ninguna llamada a
herramientas** — OpenClaw manda sus propias herramientas, no las del inbox, así que el
experto contestó sólo desde el listado, que es lo que hace la base. **El 0,741 viene
de `agent_sim`, que provee las herramientas del inbox y las ejecuta.** El turno del
agente demuestra el transporte; la suite demuestra el experto. Cablear las
herramientas del inbox en OpenClaw es trabajo real y no está hecho.

**Tres cosas que correrlo encontró y ningún test podía**: un `/v1` duplicado en la URL
de fallback (todos los tests mockeaban el fetch), `config patch` que toma `--file` y no
un argumento posicional (el manual estaba mal dos horas después de escrito), y
**OpenClaw haciendo streaming por defecto** con su `streaming: false` por modelo sin
tomar efecto. El rechazo del proxy — *rechazar en vez de fingir* — era correcto
mientras la alternativa era una medición engañosa y **equivocado cuando la alternativa
era ser inusable**.

#### P41 — rutear los fallos a la frontera, con la frontera medida

[`results/P41-routing-20260915/`](../../results/P41-routing-20260915/) ·
`training/harness/routing.py`. Los expertos del pool no son igual de buenos, así que
la frontera deja de ser andamio a retirar y pasa a ser **fallback para lo que el
experto local falla, medido**. Esto es eso, en números.

**`google/gemini-3.8-flash` sobre la suite de fluidos, por el mismo cliente que usa
el experto local: 66/90 = 0,733** **[ran]** — no 1,000, así que el `≤ 0,871` anterior
era una cota y queda reemplazado por un resultado.

| política | entrega | sale de la máquina |
|---|--:|--:|
| todo local | 0,546 | 0% |
| **fluidos → frontera, por región** | **0,775** | **38%** |
| por caso · tripwire `has_left_its_region` | 0,378 | 37% |
| por caso · quality gate `is_probably_wrong` | 0,689 | 91% |

**El ruteo por región funciona y paga: +0,23 entregado, y el 62% del trabajo se queda
sobre una base residente.** Ése es el argumento económico del pool enunciado como
medición y no como esperanza — le pagamos a la frontera sólo la parte que medimos que
no sabemos hacer.

**Y el ruteo por caso es PEOR que por región, que es el hallazgo.** Las dos reglas de
escalación — construidas y medidas en P19/P21 — detectan una cadena **dimensional o
mecánicamente inconsistente**. Las cadenas de este experto son perfectamente
consistentes y la física está mal: sigue el procedimiento, las unidades cierran, la
aritmética cierra, y la respuesta no es la correcta. **Las reglas buscan un fallo que
este experto no tiene.**

Así que el problema abierto es filoso y es nuevo: **una señal de ruteo que vea una
cadena coherente y equivocada.** Ahí es exactamente donde la maquinaria de aceptación
estacionada tiene trabajo — no como criterio de promoción para entrenar, sino como la
decisión de confianza por caso — y es la razón por la que la reformulación de §11 la
conserva en vez de retirarla.

**Dos hallazgos de instrumento pagados acá.** La frontera sacó primero **0/4**, y
reportarlo habría dicho *"la frontera tampoco puede con esta suite"* — la conclusión
más interesante y más falsa disponible. Era una herramienta rechazando `T=20 C` por su
redacción y un tope de tokens cortado a la medida de un experto cuyos mensajes finales
tienen 19 caracteres. Arreglado, sacó **5/6** en la misma sonda **[ran]**.

#### P37–P40 — el pool sirve dos expertos, y sólo uno es bueno

[`results/P40-pool-retried-20260915/`](../../results/P40-pool-retried-20260915/BRIEF.md).
Un segundo experto sobre un subdominio genuinamente distinto — mecánica de fluidos,
elegida por encima de una suite de calendario justamente porque la distancia entre
dominios es lo que la tesis afirma que no importa — entrenado igual y servido **al
lado** del experto de email en un solo vLLM.

**El sustrato funciona, medido tres veces.** Los dos adaptadores aplicados,
**distintos entre sí**, una base residente, cada uno enrutado por el campo `model` a
su propio cliente y su propio oráculo **[ran]**. La comprobación de distinción es
nueva: dos nombres sobre un mismo adaptador darían dos números respetables y serían un
solo experto, que es el fallo que más se parece a un éxito.

**La co-residencia no le cuesta nada al miembro que sirve**: 84/113 solo contra 81 y
82 en dos corridas del pool, los tres pares empatados, con 393/393/390 llamadas
**[ran]**.

| miembro | resultado | llamadas | rechazadas | sin turnos |
|---|--:|--:|--:|--:|
| `email-full` | 82/113 = 0,726 | 390 | 0 | — |
| `fluids-full` | **12/90 = 0,133** | 603 | **0** | **0** |

**El brazo de fluidos fue nulo una vez y ahora está limpio.** El corpus de P38 nunca
le mostró al modelo la superficie con la que se lo sirvió — el proxy agrega 388
caracteres que listan los argumentos alfabéticamente donde el corpus los escribe en el
orden de las herramientas — y **71 de 606 llamadas fueron rechazadas por razones que
no tenían nada que ver con la física**. El generador ahora *usa* `render_tools` en vez
de una copia, y el test que verifica esto existía para email y nunca se había escrito
para fluidos.

**Arreglarlo empeoró el número, y ése es el hallazgo.** 0 rechazos, 0 turnos agotados,
90 de 90 respondidos, 6–8 llamadas contra las 7 que enseña el corpus: **el protocolo
salió exactamente bien y la física está mal 78 veces de 90.** Pareado contra P24 sobre
casos que son literalmente los mismos por id, **pierde contra la regla escrita a
mano** — 3/30 contra 12/30, 2:11 discordante, **p = 0,022** — y empata con todo lo
demás.

**Dos correcciones que este proyecto se debe a sí mismo.**

1. P38 nombró *"ganarle a la regla escrita a mano, pareado"* como barra de fluidos.
   **La regla no es un solucionador** — escribe llamadas y un modelo pone la física —
   así que esa barra nunca fue medible como se enunció. La comparación pareada contra
   los brazos de P24 sí lo es.
2. **El titular de P36 queda matizado.** El mismo adaptador, los mismos casos,
   temperatura 0, da **84, 81, 82** en tres corridas con los tres pares empatados. La
   compuerta pide 83. vLLM no es determinista corrida a corrida, así que *"el primer
   miembro del pool clarea su compuerta"* clareó **una vez de tres**, decidido por el
   planificador. **El efecto no es marginal, sólo el veredicto lo es**: contra la base
   es **8 : 51 discordante, p ≈ 0**.

**Qué dice la división entre los miembros.** Funciona el miembro que tiene que
**decidir**; falla el que tiene que **razonar**. Email es una regla de dos-de-cuatro
sobre hechos que las herramientas entregan; fluidos compone Manning, Swamee-Jain,
profundidades de centroide y áreas sobre números que cambian por caso. **600 ejemplos
supervisados enseñaron el protocolo a la perfección y la física nada.**

Eso ancla contra P6/P7, donde un experto de fluidos llegó a **40/40 — con calculadora,
sobre una suite cuyos valores venían en el enunciado** **[ran]**. Acá tiene calculadora
y además tiene que *buscar* los valores. El salto de dificultad entre esas dos suites
ahora tiene número.

**"Pool" sigue sin estar ganado**, y falta exactamente una cosa: un segundo miembro
*útil*. (**Respondido sobre una región sintética el 2026-09-18 [ran] P64** — el segundo
miembro útil es `desk-commitment@v1`, otro subdominio y no más corpus; el párrafo queda
como lo que era cierto el 2026-09-15.) Si eso pide más corpus, otro subdominio, o admitir que 600 ejemplos no compran
razonamiento compuesto queda abierto — y es la primera pregunta que el mecanismo de
aceptación estacionado podría estar en posición de contestar.

#### P36 — el primer miembro del pool clarea su compuerta

[`results/P36-ceiling-20260915/`](../../results/P36-ceiling-20260915/BRIEF.md). Un
adaptador, herramientas y juicio juntos, servido sobre Qwen2.5-3B con la compuerta de
identidad `applied` antes de puntuar un caso.

| brazo | pidió en | rechazadas | mensajes humanos | p exacta |
|---|--:|--:|--:|--:|
| base (P31) | 0/150 | 0 | 39/113 = 0,345 | 1,000 |
| kernel-mt, física (P34) | 123/150 | 127 | 39/113 = 0,345 | 1,000 |
| kernel-email, nombres (P35) | 22/150 | 0 | 42/113 = 0,372 | 1,000 |
| **email-full (P36)** | **113/150** | **0** | **84/113 = 0,743** | **0,028** |

**Clarea** — 84 contra los 83 que exige el binomial exacto a una cola con α = 0,05, y
los 0,320 de margen que tenían las herramientas quedan **reclamados en un 28%**,
0,655 → 0,743 **[ran]**.

**393 llamadas, 0 rechazadas.** Pidió en 113 de 150 casos y en 37 no, y esos 37 son
casi exactamente los mensajes automáticos que el corpus enseña a resolver de un
vistazo. **Aprendió *cuándo* preguntar, no "preguntá siempre"** — el fallo que habría
producido un corpus que consultara tres herramientas para todo. 97 casos con 3
llamadas, 14 con 6, 2 con 9; ninguno se quedó sin turnos y ninguno quedó indeciso.
**0 de 150** contestaron desde un resultado fabricado, así que el confundido
pre-registrado en el brief de P35 sigue muerto.

**Bajo la decisión tomada mientras esto corría**, la lectura no es permiso para seguir
midiendo — es el resultado: **un QLoRA autocontenido, entrenado con fine-tuning
supervisado común sobre un subdominio, servido sobre una base residente e
intercambiable por request, hace un trabajo que la base no puede hacer en absoluto.**
El 0,345 de la base es el complemento exacto de su propia barra, de contestar `NOT
IMPORTANT` a todo sin consultar nada. Toda la diferencia es el adaptador, sin
composición, sin kernel compartido y sin torneo.

**Tres cosas que esto no afirma.** No que un pool compuesto no pudiera hacerlo mejor —
la composición está estacionada y nada acá compara contra eso. No un techo — 0,743
contra un 1,000 que nadie alcanzó, y lo que cuesta el 0,257 restante está sin medir.
**No generalización**: un subdominio, un generador, una base. *Un pool* necesita un
segundo experto antes de que la palabra esté ganada.

#### P35 — el vocabulario es aprendible, y aprenderlo cuesta la disposición

[`results/P35-email-kernel-20260914/`](../../results/P35-email-kernel-20260914/BRIEF.md).
Un kernel entrenado sobre 600 ejemplos de los **nombres de las herramientas de email
y nada sobre triage**, servido sobre Qwen2.5-3B con la compuerta de identidad
`applied` antes de puntuar un solo caso.

| brazo | pidió en | llamadas | rechazadas | mensajes humanos |
|---|--:|--:|--:|--:|
| base (P31) | 0/150 | 0 | 0 | 39/113 = 0,345 |
| kernel-mt, herramientas de física (P34) | **123/150** | 127 | **127** | 39/113 = 0,345 |
| **kernel-email (P35)** | **22/150** | 44 | **0** | 42/113 = 0,372 |

**El vocabulario se aprendió**: las 44 preguntas fueron contestadas — nombres
correctos, claves correctas, **0 rechazadas** contra las 127 de P34. Ese era el hueco
que P34 dejó abierto, y se cerró **[ran]**.

**Y enseñarlo costó la disposición**: preguntar cayó de **123 de 150 casos a 22**. Es
la cuarta salida que el brief nombró de antemano, y la razón se ve en el corpus —
enseña cuatro *formas de pregunta*, y un prompt de triage no es ninguna. El adaptador
aprendió *preguntá cuando la pregunta se vea así*; el kernel de física, entrenado en
otro dominio por completo, había generalizado *preguntá cuando te falte un dato*.

**Ningún brazo clarea la compuerta**, y los tres **empatan** en exactitud: base contra
kernel-email es **0:3 discordante, p = 0,250**, la misma forma de afirmación retirada
de P15 esta mañana. **El confundido pre-registrado está muerto** — `strip_calls` deja
un `= {…}` fabricado en el contenido y **0 de 150** lo llevan, así que el modelo no
contestó desde su propia invención.

**El enunciado más filoso de la tesis del pool.** El uso de herramientas no es una
capacidad que un LoRA lleva o no lleva. Son al menos dos, y generalizan distinto:

| | cómo transfiere |
|---|---|
| **disposición a preguntar** | ampliamente pero vagamente — estira la mano en 123 de 150 casos, con el vocabulario equivocado |
| **vocabulario** | precisamente pero angostamente — pregunta bien siempre, sólo para las formas que entrenó |

Ninguna sola alcanza el margen, así que la pregunta siguiente del pool es si las dos
**componen** — la forma que P8 ya midió para física, secuencialmente y por turnos.

#### P34 — el protocolo transfiere como conducta, no como vocabulario

[`results/P34-protocol-transfer-20260914/`](../../results/P34-protocol-transfer-20260914/BRIEF.md).
`kernel-mt` — entrenado sobre `<calc>`, `<lookup>` y `<convert>` en mecánica de
fluidos — servido sobre Qwen2.5-3B contra la suite de **email**, cuyas herramientas
nunca vio.

| | base sola (P31) | **kernel-mt** |
|---|--:|--:|
| llamadas a herramientas | 0 | **127** |
| rechazadas | 0 | **127** |
| casos que pidieron algo | 0 de 150 | **123 de 150** |
| mensajes humanos | 39/113 = 0,345 | 39/113 = 0,345 |

**Cero se volvió 127, y las 127 fueron rechazadas.** La base sola no pidió nada 150
veces; con el adaptador de protocolo la misma base estira la mano hacia una
herramienta en 123 de 150 casos sobre un dominio sin ningún solapamiento — en el
vocabulario que aprendió, no en el que esta suite tiene **[ran]**.

Es la lectura del medio de las tres escritas antes de correr, y ninguna vecina
encaja: el protocolo **sí** cruza vocabularios (0 → 127), y **no** sirve herramientas
para las que no fue entrenado (0 de 127 contestadas).

**La exactitud no se movió — 39/113 las dos veces, idéntico.** Un adaptador de
protocolo que pide y es rechazado saca lo mismo que una base que nunca pide. **El
pedido es el hallazgo y el puntaje no lo es**, que es lo que el brief dijo de
antemano que reportaría en cualquier dirección.

**Lo que no se compró**: qué nombre pidió. El registro contaba rechazos sin registrar
el pedido, y eso se arregló la misma sesión para que la próxima corrida lo conteste
gratis. No se compró como brazo propio porque **no puede cambiar la compra
siguiente** — un nombre equivocado y un argumento malformado llevan los dos a un
adaptador de protocolo entrenado sobre este vocabulario, y un corpus armado desde el
esquema de las herramientas cubre ambos.

**Para la tesis del pool esta es la mitad no obvia.** La capacidad reutilizable es la
**disposición a preguntar**, y sobrevive demostrablemente a un cambio completo de
dominio, tarea y nombres de herramienta. Lo que no viaja es el vocabulario — barato
de enseñar y específico del dominio por naturaleza. Así que el pool no necesita un
adaptador de protocolo por dominio para la *conducta*; necesita uno que sepa los
*nombres*. Si un solo adaptador puede llevar varios conjuntos de herramientas es
ahora una pregunta sobre datos de entrenamiento y no sobre si la idea funciona.

#### P31 — la base no puede hacer triage, y eso no significa lo que decía el brief

[`results/P31-triage-headroom-20260914/`](../../results/P31-triage-headroom-20260914/BRIEF.md).
Qwen2.5-3B-Instruct, sin adaptador, 150 mensajes por vLLM, el proxy y el loop de
agente real. Contestó **`NOT IMPORTANT` a los 150, con palabras idénticas, en la
primera llamada al modelo** — **39/113 = 0,345** en los mensajes humanos contra una
barra de 0,655, p exacta a una cola = **1,000**, y **0 llamadas a herramientas**
**[ran]**.

La superficie de herramientas no fue el problema: el renderizado del proxy se
reprodujo fuera de línea y al modelo se le mostraron los tres tags más la línea *"Use
the tools to find out — the listing does not say"*. **Se le ofrecieron las
herramientas, se le dijo que las usara, y no pidió ninguna.**

**La regla pre-registrada decía que la compra siguiente es otra base, y esa regla se
retira en vez de aplicarse.** Razonaba que "un adaptador enseña una política; no
enseña a un modelo a sostener una conversación de herramientas que no puede
sostener". P8 midió lo contrario sobre esta misma base **[ran]**:

| brazo | llamadas a herramientas en 30 casos |
|---|--:|
| base + tool | 44 |
| **kernel + tool** | **169** |
| domain + tool | 0 |

Un adaptador de protocolo casi cuadruplica cuántas veces esta base pide una
herramienta; un adaptador de dominio sin protocolo en su corpus lo baja a cero. **El
fallo que P31 observó es exactamente el que un adaptador de protocolo existe para
reparar**, así que piso-en-la-base no implica piso-con-adaptador, y comprar otra base
sería gastar plata sobre una inferencia que este repositorio ya contradijo.

**La comparación es sugestiva, no exacta**, y el límite queda anotado con ella: P8
corre física por un harness de stop-string, P31 corre email por la convención
`tools=[…]` de OpenAI. Lo que transfiere es el contraste interno de P8 — misma base,
misma tarea, mismo canal — no el conteo crudo.

**Lo que el brazo sí establece**: la base no puede sola; la suite no se contesta desde
el listado; y los 0,320 de margen siguen enteros del lado de las herramientas, sin que
nadie los haya reclamado.

#### P33 — Qwen3.5 entrena un LoRA; vLLM sirve la base igual

[`results/P33-lora-matrix-20260914/`](../../results/P33-lora-matrix-20260914/BRIEF.md).
**Pre-registrado antes de correr, y existe porque cuatro corridas produjeron un
resultado ilegible.** Cada una preguntó si vLLM aplica un LoRA a `Qwen3.5-4B`; cada
una contestó `IDENTICAL TO BASE`; y ninguna podía separar *la clase del modelo no
aplica LoRA* de *el adaptador nunca se entrenó* de *el chequeo mismo estaba mal*.
Era el chequeo, dos veces — así que **los dos diagnósticos sobre Qwen3.5 de esta
página quedaron retirados el 2026-09-14**: que su adaptador tocaba sólo los MLP (el
árbol de módulos cargado sí lleva `q_proj`), y que la clase no sirve LoRA (medido a
través de un self-check que generaba dos veces a través del adaptador y llamaba
idénticos a los resultados).

**Lo que faltaba nunca fue un sujeto mejor. Era un control.** Un resultado negativo
sólo se lee al lado de uno positivo tomado de la misma manera, así que el
procedimiento idéntico corre sobre `Qwen2.5-3B-Instruct` — donde P26 midió base 0/60
contra adaptador 20/60 **[ran]** — en la misma sesión que el sujeto.

| compuerta | pregunta | concluyente sola |
|---|---|---|
| **G1** en proceso | ¿se movió `lora_B` **y** cambió la salida? | sí — un adaptador no-op nunca llega a G2 |
| **G2** servido | ¿el texto de vLLM difiere del de la base? | sí |
| **G3** fusionado | se compra sólo si G2 falla | sí, y **no es un pool** |

**Falsificación, escrita antes de correr**: si el control falla cualquiera de las dos
compuertas la corrida es **nula** y ninguna afirmación sobre Qwen3.5 la sobrevive.
Esa fila no existía en ninguna de las cuatro corridas previas, y es lo único que
separa "el sujeto es malo" de "el instrumento es malo".

**G3 tiene su precio dicho de antemano, no descubierto después.** Fusionar escribe el
delta en los pesos y sirve un modelo común — la propia guía de unsloth para Qwen3.5
pasa por `save_pretrained_merged` exactamente por eso **[read]**. Funciona, y cuesta
una copia completa de los pesos por experto, sin base compartida y sin swapping por
request: justo lo que esta arquitectura existe para evitar.

## El resultado — 2026-09-14 **[ran]**

| base | rol | G1 en proceso | G2 servido | s |
|---|---|---|---|--:|
| `Qwen2.5-3B-Instruct` | control | **pasa** · `lora_B=18660,98` | **applied** | 323 |
| `Qwen3.5-4B` | sujeto | **pasa** · `lora_B=18739,84` | **IDENTICAL TO BASE** | 495 |

**`control_valid: true`**, así que el negativo del sujeto es un hecho sobre Qwen3.5 y
no sobre este código. La lectura, de la tabla escrita antes de correr:

> el adaptador entrena y cambia la salida en proceso, y vLLM sirve la base igual —
> **un límite del stack de serving, no del modelo**

**Esto es distinto en todo de las dos afirmaciones retiradas el mismo día.** Qwen3.5
no es incapaz de LoRA: `lora_B_abs_sum = 18739,84` sobre las doce proyecciones,
incluidas `in_proj_qkv` y `out_proj` de las capas de atención lineal, y la salida
cambia. Lo que falla es el stack de serving — **y falla en silencio**, que es C18
entero. `vllm.log` trae `Loaded new LoRA adapter: name 'tiny'` y después sirve la
base. Un deployment que leyera esa línea creería estar sirviendo un experto.

El G2 del sujeto además trae **`"exit": 0`**: `serve_openai` sale limpio en una
corrida cuya compuerta dijo *not applied*, así que leer el código de retorno en vez
del archivo lo habría reportado como éxito — la misma forma de error detrás de los
dos diagnósticos retirados.

**Decisión: Qwen 2.5 para el end-to-end.** No porque Qwen3.5 sea peor, sino porque un
pool de QLoRAs necesita adaptadores intercambiables por request sobre una base
residente, y vLLM no los aplica en esa clase. **G3 no se compró**: fusionar
funcionaría y no es un pool — una copia completa de los pesos por experto, sin base
compartida ni swapping — así que queda anotado como fallback con su precio dicho en
vez de como opción, y no se gastó GPU en confirmar un costo que podemos enunciar.

**Nota de instrumento que sobrevivió a la corrida.** El chain murió antes de que la
A100 hiciera nada, por un comentario de Python dentro de un heredoc sin comillas:

    # raised on `import`, so vllm never starts

Ahí el `#` no comenta nada y los backticks ejecutan. `chain_serve.sh` ya llevaba una
nota que decía *"No backticks in this heredoc — tercera vez hoy"*; la cuarta llegó en
una línea agregada debajo. Una regla que una persona tiene que recordar no es una
regla, así que `tests/test_chain_scripts.py` ahora falla el build por eso — y
encontró dos instancias vivas apenas existió, incluida la advertencia misma **[ran]**.

#### P26 — el pool responde en `/v1/chat/completions`, y cada adaptador se aplica

[`results/P26-openai-server-20260913/`](../../results/P26-openai-server-20260913/BRIEF.md).
`/v1/models` lista la base y los dos adaptadores como nombres de modelo distintos, y
el mismo prompt a cada uno produce **texto distinto** — el kernel escribiendo
etiquetas y delegando la aritmética, el dominio escribiendo física numerada sin emitir
una sola etiqueta. **Dos personalidades sobre una base residente, seleccionadas por el
campo `model` de una petición HTTP.** Es la pregunta de sustrato que P3 dejó abierta
**[ran]**.

**La salvedad viaja con el resultado**: el fallo silencioso de P3 fue vLLM 0.28.0
sobre una base híbrida multimodal y esto es 0.29.0 sobre una densa — **cambiaron dos
cosas**.

**El brazo 2 no prueba lo que fue construido para probar**, y queda registrado en vez
de disfrazado: los dos adaptadores sacan 0/30, y ninguno de los ceros es sobre vLLM.
El kernel emite `<calc>` y espera una respuesta que un endpoint de un turno nunca da;
el dominio no sabe aritmética (1/30 crudo, 30/30 reevaluado, medido hace tiempo). La
fidelidad de serving necesita el mismo *harness*, no sólo los mismos casos, y sigue
sin respuesta.

**El brazo 3 descarta la versión catastrófica y poco más.** El mixto salió *más
rápido* que el puro — 3,01 contra 2,69 prompts/s — y los dos bursts corren en orden
fijo con el primero pagando el calentamiento, así que **−11,9% es el tamaño del
confound, no un hallazgo**. Lo que sobrevive es que dos adaptadores intercalados están
dentro del ruido de uno en un mismo paso de scheduling, contra el 20× anulado de P3.

#### P27 — el puente a `tool_calls` es un serializador, y la dirección del esquema tiene precio

[`results/P27-tool-calls-20260913/`](../../results/P27-tool-calls-20260913/BRIEF.md).
P26 cerró advirtiendo que puentear etiquetas a `tool_calls` "reintroduce el harness
escrito a mano". **Eso confundía decidir con serializar**, y los dos miden distinto:

| | líneas de código que nombran el vocabulario de la suite |
|---|--:|
| la regla escrita a mano | **19 de 76** |
| el conversor etiqueta→`tool_calls` | **0 de 38** |

**604 de 604** llamadas de ambas suites vuelven byte a byte idénticas, y
`search_flights`, `sql_query` y `send_email` — herramientas que este proyecto no
conoce — se convierten limpiamente, así que la fidelidad no es un artefacto de un
vocabulario compartido **[ran]**.

**La otra dirección no es gratis, y ahora tiene número.** Renderizar el `tools=[…]` de
un cliente a la superficie de etiquetas, contra la instrucción entrenada sobre los
mismos treinta casos y el mismo adaptador:

| brazo | llamadas | rechazadas | valores del oráculo |
|---|--:|--:|--:|
| instrucción entrenada | 178 | 16 | **59/96 = 0,615** |
| **esquema OpenAI** | 176 | **93** | **41/96 = 0,427** |

**El protocolo no se apaga — se deforma la forma.** Los dos brazos producen llamada en
los treinta casos y hacen la misma cantidad. Y **33 de los 93 rechazos del brazo del
esquema son una sola discrepancia**: un esquema JSON de una propiedad renderiza
`<calc>expression=…</calc>` donde el adaptador se entrenó con `<calc>1.2 * 3</calc>`.
Todas las demás categorías de rechazo son idénticas entre brazos — 4 y 4, 3 y 3.

**Los números absolutos no viajan**: el brazo entrenado da 0,615 acá contra el 0,979
de P21 porque esto es *un solo turno* sin harness que conteste, así que el modelo
escribe la cadena entera sin ver un valor intermedio. **Sólo el A/B dentro de esta
corrida es comparable.**

#### P20 — un fitness que no selecciona por fallar en silencio

[`results/P20-fitness-20260911/`](../../results/P20-fitness-20260911/BRIEF.md). P19
encontró que un juez que lee transcripciones acepta el **41% del trabajo equivocado
que se ve limpio**, así que una variante con fallos invisibles le gana a una que
acierta más seguido. Se listaron cuatro combinaciones de dos jueces antes de
puntuar ninguna, y se reportan las cuatro **[ran]**:

| fitness | pares con brecha real ordenados bien |
|---|---|
| juez modelo solo | 1/2 |
| procedural solo | 1/2 |
| **los dos deben aceptar** | **2/2** |
| cualquiera puede aceptar | 1/2 |

| | trabajo equivocado que se ve limpio | trabajo correcto |
|---|---|---|
| juez modelo solo | acepta **41%** | acepta 96% |
| **los dos deben aceptar** | acepta **2%** | acepta 90% |

**La falsa aceptación cae de 41% a 2% a cambio de seis puntos de trabajo correcto.**
El juez modelo lee una transcripción y no puede distinguir *limpio porque está bien*
de *limpio porque nunca lo intentó*; la comprobación procedural re-ejecuta la cadena
y es indiferente a cómo se ve. Ninguna alcanza sola y la conjunción sí — y sale casi
calibrada: puntúa el control de P13 en 0,767 contra una verdad de 0,767 y la regla
de P15 en 0,231 contra 0,231.

**El arreglo obvio era al revés y vale registrarlo así.** Restar los rechazos de la
capa de herramientas castiga al brazo que muestra sus fallos, que es el mejor. Un
error visible es una señal: le cuesta casi nada al trabajo correcto y le permite a
un juez rechazar el equivocado.

**Dos pares no son un torneo.** Los candidatos no los crió un bucle, así que nada
acá muestra que la selección repetida converja, ni que un bucle optimizando este
fitness no aprenda a satisfacer a los dos jueces estando equivocado.

#### P17 — existe un juez, y juzgar es más fácil que resolver

[`results/P17-judges-20260910/`](../../results/P17-judges-20260910/BRIEF.md). 100
cadenas de P13 y P14 con corrección conocida — 33 bien, 67 mal — puntuadas por
candidatos que nunca ven la respuesta. La vara es **0,67**, la clase mayoritaria
**[ran]**:

| juez | exactitud | halla lo correcto | halla lo incorrecto |
|---|---|---|---|
| siempre "incorrecto" — la vara | 0,67 | 0,00 | 1,00 |
| procedural (sin modelo) | 0,66 | 0,94 | 0,52 |
| `qwen3.5:4b` — un par | **0,82** | 0,97 | 0,75 |
| `gemini-3.8-flash` — la frontera | **0,89** | 0,89 | 0,89 |

**Los números del par son los que importan.** `qwen3.5:4b` *resuelve* este material
a **0,467** y lo *juzga* a **0,82**. **Juzgar es más fácil que resolver**, por
mucho, para el mismo modelo sobre los mismos problemas — que es lo que vuelve
construible un torneo después de retirar la frontera. La nota no tiene que venir de
algo que hubiera podido hacer el trabajo.

**El juez procedural falla con una forma que vale conservar.** Empata la vara
trivial en exactitud con el perfil de error opuesto: encuentra el 94% del trabajo
correcto y el 52% del incorrecto. Ve aritmética y es ciego a una relación
equivocada — y una relación equivocada es exactamente lo que produce un experto
fuera de su región.

**De lo que esto no se escapa.** La frontera juzga bien acá en parte porque puede
resolver el problema: saca 1,000 en este material. Donde nada disponible pueda
resolver el trabajo, juzgar queda sin probar. Y 7 de sus 100 respuestas no fueron
veredictos, registradas como abstenciones en vez de plegarse a "incorrecto", que le
habría regalado la clase mayoritaria.

**La falla cazada en el camino**: la primera corrida le dio 8 tokens a un veredicto
de una palabra. Un modelo de razonamiento los gasta pensando y devuelve una
respuesta vacía, así que la frontera se abstuvo en 100 de 100 y se leía como "no
puede juzgar". Los dos jueces se re-corrieron con 400; el brazo invalidado se tiró
en vez de reportarse.

#### P22 — la consistencia dimensional es la primera señal de borde confirmada

[`results/P22-dimensions-20260912/`](../../results/P22-dimensions-20260912/BRIEF.md).
Dos señales baratas habían fallado: la confianza del propio modelo y la tasa de
rechazo de la capa de herramientas, falsificada en familias a las que no había sido
ajustada. La hipótesis acá es que fuera de su región un especialista no falla en
silencio — **inventa relaciones**, y una relación inventada difícilmente sea
dimensionalmente consistente:

    6. Fuerza de arrastre F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)
       kg/m^3 · (m/s)^2 / [1]  =  kg/(m·s^2)  — una presión, donde se pedía fuerza

No consulta ningún modelo, no necesita la respuesta y no tiene umbral que ajustar
**[ran]**:

| | desarrollo (P13/P14) | **confirmación (P18)** |
|---|---|---|
| trabajo fuera de región marcado | 0,78 | **0,80** |
| cobertura | 0,80 | 0,82 |
| separación | **0,72** contra una línea de azar de 0,60 | — |
| falsa alarma sobre trabajo correcto en región | **0,22** | — |

**No cae sobre material que nunca vio.** El guardia conductual se desplomó de 0,63 a
0,18 en exactamente esta pregunta; éste se sostiene en 0,80. Cuatro de cada cinco
cadenas fuera de región quedan atrapadas en `weir_flow` y `jet_reaction`, producidas
por P18 antes de que el guardia existiera.

**No es desplegable.** Una de cada cinco cadenas correctas en región queda marcada, y
un sistema que escala un acierto de cada cinco ya gastó buena parte de lo que el
retiro venía a ahorrar. La pre-registración decía que ese número cuenta igual.

**Y no es libre de dominio.** La `n` de Manning es s·m^(-1/3), así que esa familia
sólo tipa si el enunciado nombra la constante — un dominio nuevo cuesta una tabla de
sus propias constantes empíricas. Y los números se emparejan por valor, así que un
intermedio que coincida con una cantidad impresa hereda su dimensión.

**El instrumento cambió siete veces y la regla nunca se movió.** Cada cambio fue el
verificador fallando en leer su entrada — un veredicto leído del último paso que
*tipaba* en vez del paso final, `Pa.s` matcheando el prefijo `Pa`, exponentes enteros
incapaces de expresar `R**(2/3)`, y cuatro más, todos listados en el brief. Siete
está pasado el punto donde la regla de este proyecto dice que una medición está
buscando su resultado. **La defensa no es que cada arreglo estuviera justificado: es
que el conjunto de confirmación se puntuó una sola vez, después de los siete, sobre
material nunca abierto durante el desarrollo, y se sostuvo.**

#### P21 — el protocolo aprendido empata con la regla escrita a mano, como estaba pre-registrado

[`results/P21-handbook-20260911/`](../../results/P21-handbook-20260911/BRIEF.md).
El material de P15 se podía responder de memoria, así que la suite ganó un **manual
por caso**: las propiedades que un problema necesita no existían cuando el experto se
entrenó y no se pueden recordar. El brazo que podía matar la hipótesis se compró
primero y funcionó — un control sin capa de herramientas cayó de **27/30 a 6/30**
**[ran]**.

| brazo | respuesta final | valores del oráculo | llamadas | rechazadas |
|---|--:|--:|--:|--:|
| sin capa de herramientas | **6/30** | 0/96 | 0 | 0 |
| regla escrita a mano | 5/30 | 93/96 = **0,969** | 96 | **0** |
| kernel adapter | 4/30 | 94/96 = **0,979** | 116 | **20** |

**Un valor de diferencia en el eje declarado de antemano, y el brief fijó antes de
correr que un kernel a menos de tres es empate.** Se reporta empate. Los tres brazos
empatan también en respuesta final, con el control *sin herramientas* arriba — que es
lo que predijo el chequeo de headroom: 22 de los 25 fallos de la regla tenían todos
los valores del oráculo y el experto igual respondió mal, así que una capa perfecta
sólo podía mover tres casos.

**Lo que los separa es el carácter.** La regla hace 96 llamadas sin ninguna rechazada;
el kernel hace 116 con 20 rechazadas — **17,2%** — y aun así termina arriba en
cobertura. De sus 14 casos fallidos con rechazo, **13 obtuvieron igual todos los
valores del oráculo**. La taxonomía de fallos sobre-atribuye a protocolo acá, y
`classify` se deja como está en vez de reordenarse después de ver a qué brazo castiga.

**Zanjado**: un protocolo aprendido no vale más que una regla escrita a mano en esta
suite, ni menos — lo opuesto al 9/30 contra 23/30 de P13. **Sin zanjar**: si un 17,2%
de llamadas desperdiciadas importa contra una herramienta paga o lenta, y si algo de
esto es portable. La regla son **144 líneas** que conocen el vocabulario de etiquetas
de esta suite, su tabla de unidades, sus fluidos y sus frases; el adaptador aprendió
de un corpus sin ninguna familia de evaluación. Un empate entre esos dos no es empate
en especie, pero P21 no midió portabilidad y el resultado de transferencia de P9 sigue
siendo la única evidencia.

#### P23 — S2 recomprado contra un target que sí está adelante · CORRIENDO

[`results/P23-ranking-20260912/`](../../results/P23-ranking-20260912/BRIEF.md). S2
pasó 14 de 15 pares contra targets que eran **pares** del candidato más fuerte, lo que
prueba la mecánica del criterio y no la afirmación de la arquitectura. P10 encontró una
suite donde un target sí está adelante, y sus respuestas ya están en disco.

**El primer target de reemplazo quedó anulado, y el dato que lo anuló ya estaba ahí.**
Contra un target de 30/30, estar de acuerdo con el target es estar en lo correcto, así
que el test pasaría tautológicamente. El mismo modelo con presupuesto menor saca 17/30
— y **los 13 fallos son truncamientos**, derivaciones cortadas a mitad de página cuya
"respuesta" es un área de cañería. A presupuesto completo acierta los 13 de 13. El
target no estaba equivocado, estaba callado.

**`gemini-3.5-flash-lite` a presupuesto completo califica**: 43/60, nada sin parsear, y
**17 de 17 fallos son respuestas completas** contra una barra pre-registrada de 0,80
**[ran]**. La escalera hasta ahora, todos con nada sin parsear:

| candidato | verificado |
|---|--:|
| `qwen3.5:2b` | 13/60 |
| `qwen3.5:4b` | 29/60 |
| `qwen3.5:9b` | 39/60 |
| `gemma4:12b` | corriendo |
| *target* | *43/60* |

Diferencias de 16 y 10 casos — el empate de ±1 que anuló S2a no está en juego.
**Conteo de rediseños: 3**, contabilizado en el brief en vez de reinterpretado, y el
presupuesto queda declarado gastado: si el test se anula a n=60, S2 se reporta no
respondible en esta suite.

#### P24 — el único número donde el código le gana a los pesos · CONSTRUIDO, SIN CORRER

[`results/P24-constrained-20260912/`](../../results/P24-constrained-20260912/BRIEF.md).
P21 dejó exactamente uno: 0 llamadas rechazadas contra 20. El adaptador no es peor
sabiendo qué pedir, es peor *diciéndolo* — y un sampler puede cerrar eso. Una máscara
gramatical sobre el turno del kernel, ~120 líneas, sin pesos y sin forward pass extra.

**El resultado está predicho desde los transcripts de P21, antes de la GPU [ran]**:
replayada sobre cada llamada que los tools rechazaron, la máscara vuelve **imposibles
14 de 19**. Las cinco que se le escapan son llamadas sintácticamente perfectas
rechazadas por algo que ninguna gramática puede ver — el adaptador pidiendo agua
cuando el manual del problema tiene códigos inventados. **Una máscara que atrapara eso
estaría decidiendo contenido**, así que la pre-registración se corrige a la baja antes
de correr: las rechazadas caen a unas cinco, no a cero, y **una corrida que llegue a
cero anula el brazo**.

`grammar_check.py` replaya las 2226 llamadas de ambos corpus y la evaluación y falla si
un solo carácter legal es rechazado. Encontró tres bugs en la gramática antes de que
nada corriera; cada uno habría aparecido en la GPU como el adaptador empeorando.

#### P18 — el guardia queda falsificado: P16 midió dos familias, no un borde

[`results/P18-confirm-20260910/`](../../results/P18-confirm-20260910/BRIEF.md). El
corte de P16 aplicado sin cambios en `rejection_rate > 0,50`, sobre `weir_flow` y
`jet_reaction` — familias que ninguna corrida que ajustara algo había visto **[ran]**:

| brazo | en región | familias nuevas | exactitud del guardia |
|---|---|---|---|
| secuencial | 0,15 | **0,18** | **0,62** |
| control | 0,15 | **0,14** | **0,58** |

**Fuera de su región la capa de herramientas rechaza llamadas casi a la misma tasa
que adentro.** Y 0,62 es el azar: con 30 casos dentro y 20 fuera, contestar "en
región" siempre da 0,60.

**El 0,86 de P16 vino de seis señales elegidas con las respuestas a la vista y un
corte ajustado sobre los mismos cincuenta problemas que lo puntuaban** — justo lo
que advertía su propio brief. La advertencia tenía razón y el número no. Para esto
sirve una confirmación pre-registrada, y es el experimento más barato que este
proyecto corrió.

**Un matiz, porque dos cifras reales no coinciden.** Agregando todo el brazo, 23 de
66 llamadas fueron rechazadas — 0,348. Promediando por caso, 0,18. Un detector pone
umbral a un *caso*, así que la media por caso es la que cuenta; la agregada es más
alta porque unos pocos casos fallan mucho y la mayoría no. Citar 0,348 habría sido
cierto y engañoso.

**Qué cuesta.** Las fórmulas del experto siguen cayendo de 30/30 dentro de su
región a 1/20 afuera, nada en su prosa marca la diferencia, y ahora nada en la
conducta de la capa de herramientas tampoco. **La promoción por región sigue sin
guardia**, y la dirección barata —leer el proceso en vez del modelo— está agotada.
Queda un segundo experto cuyo desacuerdo marque el borde, o muestrear la frontera
después del retiro, que es el costo que el retiro existe para evitar.

#### P16 — un guardia en el borde de la región, leído de la capa de herramientas y no del modelo

[`results/P16-tripwire-20260910/`](../../results/P16-tripwire-20260910/BRIEF.md).
P14 descartó el guardia obvio: nada en la prosa del experto marca el borde. Se
pre-registraron seis señales y se reportan las seis, sobre transcripciones que P13
y P14 ya tenían bancadas — aritmética sobre archivos, sin GPU **[ran]**:

| señal | brazo secuencial | brazo de control | veredicto |
|---|---|---|---|
| llamadas por caso | 0,66 | 0,60 | ninguno |
| **llamadas rechazadas por caso** | **0,86** | **0,76** | **los dos** |
| **tasa de rechazo** | **0,86** | **0,76** | **los dos** |
| pasos numerados | 0,68 | 0,68 | ninguno |
| cadenas sin un paso evaluable | 0,60 | 0,60 | ninguno |
| largo de la transcripción | 0,72 | 0,62 | ninguno |

**La tasa de rechazo corre a 0,15 en región y 0,63 afuera** donde el kernel escribe
las llamadas. Fuera de su región el experto nombra magnitudes que no entiende, y la
capa de herramientas no puede convertir esos nombres en llamadas válidas — **la capa
de herramientas falla donde la prosa no**, así que el guardia lee un proceso en vez
de la opinión del modelo sobre sí mismo.

Es más débil donde el harness escribe las llamadas (0,76), lo que encaja con el
mecanismo: un harness que sólo evalúa la expresión que le pasan tiene menos que
rechazar que un kernel que debe construir una llamada a partir de una etiqueta. **El
guardia es una propiedad de tener una capa de herramientas que puede fallar** — lo
que vuelve a `harness.lora` una pieza portante por una razón que nada anterior
sugería.

**No es un detector y el brief lo dice.** Las señales se eligieron con las
respuestas a la vista, el umbral se ajusta sobre los mismos 50 puntos que lo
puntúan, y las dos familias usadas son las únicas held-out que tiene la suite.
Volverlo detector pide dos familias que ninguna corrida usó, un umbral fijado desde
ésta y no reajustado, y que la separación sobreviva.

#### P15 — el kernel le gana a la regla, y la suite falla su propia pregunta

[`results/P15-multitool-20260910/`](../../results/P15-multitool-20260910/BRIEF.md),
cuatro familias, tres herramientas, tres redacciones cada una, enunciados que
nombran su fluido en vez de entregar una densidad **[ran]**:

| brazo | exactitud | consultas del oráculo reproducidas | consultas | rechaz |
|---|---|---|---|---|
| **adaptador kernel** | **10/30** | **91/96 — 94,8%** | 118 | 19 |
| regla escrita a mano | 7/30 | 88/96 — 91,7% | 96 | 0 |
| **sin capa de herramientas** | **27/30** | — | **0** | 0 |

~~**Un protocolo aprendido le gana a una regla escrita a mano donde la llamada no es
copia**, en las dos métricas y por poco: 94,8% contra 91,7%, 10/30 contra 7/30. Eso
da vuelta el veredicto de P13 y lo ubica.~~ **Retirado el 2026-09-14: las dos
métricas son empates.**

Todos los brazos corren las mismas 30 fixtures, así que la comparación es **pareada**,
y toda la información sobre una diferencia vive en los casos donde los dos brazos
discrepan. Esos totales esconden **tres** discrepancias en la respuesta final y
**cuatro contra una** en los valores de herramienta:

| métrica | totales | discrepancias | p exacta a dos colas |
|---|---|--:|--:|
| respuesta final | 10/30 vs 7/30 | 3 : 0 | **0,250** |
| valores del oráculo | 91/96 vs 88/96 | 4 : 1 | **0,375** |

**[ran]** 2026-09-14, `tests/test_paired.py`. Tres monedas cayendo del mismo lado dan
p = 0,25. La dirección fue consistente las dos veces y **la afirmación nunca se
midió** — y P21, que quitó la memorización sorteando un handbook por caso, dejó a los
mismos tres brazos en 4, 5 y 6 de 30, cada par también un empate.

Lo que P15 establece es el control, no la competencia: **sin ninguna capa de
herramientas el experto saca 27/30, el triple que cualquiera de los dos brazos con
herramientas** (p < 0,001 contra los dos), y eso es una afirmación sobre la suite. Si
un protocolo aprendido le gana a una expresión regular eligiendo entre tres
herramientas **queda abierto**, y la lectura honesta de P13 es que nunca fue revertido.

**El único lugar donde el código realmente le gana a los pesos sobrevive**: en P24 la
regla escrita a mano le gana al adaptador kernel 12/30 contra 5/30 sobre **7 : 0**
discrepancias, p = 0,016 — una diferencia real, y es desfavorable al tratamiento, que
es justamente por qué merece el mismo cuidado. **Esto no es una duda general sobre la
suite; es el mismo test aplicado en las dos direcciones.**

**Y el control anula la pregunta para la que la suite fue construida.** Sin ninguna
capa de herramientas el experto saca **27/30 sin consultar nada**, el triple que
cualquiera de los dos brazos con herramientas. El corpus de dominio muestra los
valores de la tabla, y siete fluidos por dos propiedades son catorce números más
cinco conversiones — memorizable de sobra con 600 ejemplos. Las herramientas nunca
fueron necesarias acá, y agregarlas **empeora**.

**El brazo que podía matar el experimento se compró último**, contra la regla de
este proyecto, y el brief ya había marcado la memorización como costo conocido. Se
pagaron dos brazos antes de enterarse de que el material no los sostenía.

**El arreglo es al material, no a la arquitectura**: darle a cada problema su propio
manual, con propiedades sorteadas por caso, para que un valor no se pueda recordar y
haya que consultarlo. El experto sabría *qué* propiedad necesita — la física — y no
*cuánto vale*, que es trabajo de la herramienta.

#### P14 — la región del experto tiene un borde duro, y el experto no lo siente

[`results/P14-held-out-20260910/`](../../results/P14-held-out-20260910/BRIEF.md),
`drag_force` y `orifice_discharge` — dos familias que el experto nunca vio, mismo
dominio, mismo estilo de consigna **[ran]**:

| brazo | en región | fuera |
|---|---|---|
| control · experto solo, aritmética reparada | 23/30 crudo, **30/30 reparado** | 1/20 crudo, **1/20 reparado** |
| secuencial · el dominio planifica, el kernel ejecuta | 9/30, 13/30 | 0/20, 0/20 |

**La exactitud reparada cae de 1,000 a 0,050.** Esa medida son las fórmulas y no la
aritmética, así que no es el experto fallando en calcular — es el experto sin saber
la relación y escribiendo una igual.

**Y nada en la salida marca la diferencia.** Misma estructura numerada, misma
seguridad, física inventada: una "fracción de volumen" de `4/3 * pi/6`, un criterio
de Stokes que no es el criterio de Stokes, una fuerza de arrastre que no es la
fuerza de arrastre. El especialista que saca 30/30 en su propio material produjo
eso, con la misma voz.

**Qué le cuesta al diseño.** La promoción por región es lo que permite retirar la
frontera, y esto dice que **"probado en esta región" no informa nada sobre el pedido
de apenas afuera**. La evidencia disponible cuando se toma la decisión de promoción
es el mapa de acuerdo, que registra dónde el experto *fue puesto a prueba* — no
dónde deja de funcionar. La diferencia entre esos dos conjuntos es exactamente
donde aparece una respuesta segura y equivocada sin nadie mirando. La regla necesita
un guardia, y esta corrida dice que el guardia es necesario sin aportarlo.

#### P13 — turnarse restaura la delegación, y el kernel pierde contra un harness delgado

[`results/P13-sequential-20260910/`](../../results/P13-sequential-20260910/BRIEF.md),
mismos 30 casos, mismo contrato compartido, **[ran]**:

| brazo | crudo | reparado | llam/caso |
|---|---|---|---|
| **secuencial · el dominio planifica, el kernel ejecuta** | **9/30** | 13/30 | **4,7** |
| **control · el dominio solo, el harness repara** | **23/30** | **30/30** | 4,9 |
| *(P9 apilado)* | *4/30* | *22/30* | *0,6* |
| *(P9 dominio solo, sin herramienta)* | *1/30* | *30/30* | *0,0* |

**La activación secuencial funciona, y contesta la pregunta que tres pasos no
pudieron alcanzar.** La delegación pasa de 0,6 llamadas por caso a **4,7 — ocho
veces** — y la exactitud más que se duplica. La competencia que suprimía al kernel
en 25 de 30 pasos desaparece en cuanto los dos parches dejan de tener que producir
la misma palabra. La opción 1 de §5, la default declarada de esa referencia, quedó
medida por fin y se sostiene.

**Y el kernel pierde su trabajo contra veinte líneas de `re`.** El control — el
experto escribiendo su cadena con un harness delgado ejecutando la aritmética
exacta y **sin cargar los pesos del kernel** — saca 23/30 crudo y **30/30
reparado**. Pedirle al kernel que escriba la expresión de una etiqueta de física
que no entiende es pedirle el trabajo del experto al parche equivocado.

**El sesgo del brazo secuencial se midió, no se supuso.** El kernel escribe
`<calc>A = 1.96 * 1.27 = 2.4932</calc>` — la asignación y su propia respuesta
adentro de la etiqueta — y el evaluador rechaza el **16% de sus 130 llamadas, en 11
de 30 casos, ninguno aprobado**. Aceptando todas las formas recuperables el techo
queda cerca de 20/30, igual por debajo del control. Real, y no cambia el veredicto,
así que el brazo no se re-corre.

**Qué le cuesta esto a la arquitectura, dicho llanamente.** La modularidad que
quería §4 se alcanza — un experto sin protocolo en sus pesos, sin adaptador
fusionado — pero se alcanza **sin el mecanismo de §4**. En esta suite un protocolo
aprendido no tiene nada que aportar que no aporte una expresión regular, porque hay
una sola herramienta y la llamada es una copia de una expresión ya escrita.
`harness.lora` tiene que ganarse el lugar donde la llamada **no** sea una copia:
varias herramientas, argumentos que formatear, una elección de cuál usar. Ese
experimento todavía no existe.

#### La geometría de los dos parches [ran]

252 módulos compartidos, rango 16, cada uno comparado contra el azar de sus propias
dimensiones:

| | medido |
|---|---|
| qué LEEN (espacios de filas de `A`) | **0,99× el azar** |
| dónde ESCRIBEN (espacios de columnas de `B`) | **3,87× el azar** (mediana 3,42, máx 10,05) |
| alineación de los deltas (coseno de Frobenius) | **+0,035** |

Leen de forma independiente, escriben en direcciones que se solapan, y sus deltas
no están alineados. Eso es **contención sobre un canal de salida compartido**, no
una colisión de subespacios — que es por qué los módulos disjuntos de P11 no
ayudaron (las direcciones de escritura son del residual stream, no de la matriz
desde la que se escriben), y predice que la regularización de ortogonalidad o la
proyección al espacio nulo reproducirían el intercambio ponderado de P11 en vez de
escaparle: sacá al experto del canal compartido y el experto se va con él.

#### P11 — los dos arreglos en espacio de pesos fallan, y uno cierra una familia entera

[`results/P11-disjoint-20260909/`](../../results/P11-disjoint-20260909/BRIEF.md) **[ran]**:

| brazo | crudo | reparado | llam/caso |
|---|---|---|---|
| dominio (sólo MLP) | 1/30 | **30/30** | 0,0 |
| kernel (sólo atención) | 0/30 | 0/30 | **6,0** |
| **F3 · kernel + dominio, matrices disjuntas** | 0/30 | 5/30 | **0,2** |
| **F2 · kernel 1,0 + dominio 0,5** | 0/30 | 0/30 | **3,5** |
| *(P9 · matrices compartidas)* | *4/30* | *22/30* | *0,6* |

**F3 cierra la familia del álgebra lineal.** Darle a cada adaptador sus propias
proyecciones — ninguna matriz en común, nada que sumar — **empeoró** la delegación
(0,2 contra 0,6) y costó casi toda la física. Dos adaptadores sin un solo parámetro
compartido siguen peleando, así que la competencia nunca fue una colisión en
espacio de pesos: los dos deltas moldean la misma distribución de salida, y dónde
viven es irrelevante para eso.

**F2 demuestra que la delegación es controlable, y muestra el precio.** Ponderar el
kernel hacia arriba movió las llamadas por caso de 0,2 a 3,5, diecisiete veces — y
el experto desapareció con eso, reparado 0/30 contra su propio 30/30. Bajo una
ponderación las dos mitades no se combinan; una gana del todo.

**Cada mitad sigue sana por separado**: el kernel llama 6,0 veces por caso
entrenado sólo en atención, la física del dominio es exacta sólo en el MLP. El
fallo es competencia de conductas en el token, que es exactamente por qué una
perilla de magnitud cambia una mitad por la otra. Lo que queda es de otra especie:
cambiar lo que se le enseña a producir al experto (P12), o volver **imposible** la
conducta perdedora en decodificación — una máscara de logits sobre dígitos fuera de
`<calc>` es la única intervención que un delta rival no puede out-votar, y todavía
no se compró.

#### P10 — la brecha honesta de frontera es +0,533, y la mitad de +0,975 era el prompt

[`results/P10-baseline-recheck-20260909/`](../../results/P10-baseline-recheck-20260909/BRIEF.md),
mismos 30 casos, semilla de evaluación de P9, presupuesto de 6000 tokens **[ran]**:

| brazo | exactitud |
|---|---|
| `qwen3.5:4b` con el prompt **legacy** ("no muestres el trabajo") | **0/30 — 0,000** |
| `qwen3.5:4b` con el contrato **compartido** | **14/30 — 0,467** |
| `gemini-3.8-flash` con el contrato compartido | **30/30 — 1,000** |
| **la brecha honesta** | **+0,533** |

**El prompt valía 0,467 de los 0,975 que reportó P5.** A todas las líneas de base
de P5–P8 se les dijo que no mostraran el trabajo mientras que todos los
tratamientos se entrenaron para mostrarlo, así que la brecha publicada era en parte
la diferencia entre un modelo al que se le permite pensar y otro al que se le
prohíbe. La cifra corregida reemplaza a +0,975 donde sea que se la cite.

**Y un presupuesto de tokens valía el resto de la duda.** Con 2000 tokens la misma
frontera sacaba 17/30 y el mismo modelo local 12/30: los dos se truncaban a mitad
de cadena, y `parse_answer` cae al último número suelto, así que una derivación
cortada puntúa un intermedio y se lee como física mala. El registro ahora guarda el
largo, la cola y si el JSON acordado aparece; con 6000 tokens **ninguno de los dos
brazos tiene una sola respuesta sin él**.

**El headroom sobrevive, a la mitad.** +0,533 sigue siendo una brecha desde la cual
un retiro puede caer — la suite clínica, donde este proyecto se trabó, ofrecía
+0,05. Y afila a P7 en vez de debilitarlo: el adaptador con calculadora saca 1,000
donde una línea de base justa saca 0,467, así que el tratamiento cierra un +0,533
real y no un +0,975 fabricado.

#### P9 — composición bajo un contrato que las dos mitades comparten · HECHO

[`results/P9-shared-contract-20260909/`](../../results/P9-shared-contract-20260909/BRIEF.md).
Escrito antes de correr, así que es un plan y no una descripción.

Los brazos de P8 no se pueden re-leer, sólo re-correr: los dos corpus enseñaron
notaciones distintas y todos los brazos usaron el system prompt del dominio.
`training/protocol.py` ahora tiene **un** system prompt y **una** instrucción de
usuario, importados por los dos corpus y por la evaluación, y la instrucción **no
menciona `<calc>`** — si el prompt pidiera etiquetas, el prompt sería el protocolo
y el adaptador kernel sería decoración. El corpus de dominio son las cadenas del
propio oráculo con las etiquetas sacadas y la aritmética hecha en el lugar. Los dos
adaptadores difieren ahora en exactamente una cosa: si la aritmética se delega. P6
y P7 siguen reproducibles — 600/600 mensajes legacy sin cambio **[ran]**.

**La medición que a P8 le faltaba.** `training/physics/repair.py` re-evalúa cada
paso de una cadena de forma exacta y arrastra el valor corregido hacia adelante,
así *fórmula equivocada* y *fórmula bien, aritmética mal* dejan de compartir
puntaje. Recupera la respuesta del oráculo en **200/200** cadenas que se saben
correctas **[ran]**. Sin eso, el aporte de la mitad de dominio es inmedible — y en
P8 nunca se midió.

| # | brazo | qué contesta |
|---|---|---|
| 1 | **dominio** | ¿El experto sabe la física? Puntuado crudo **y** reparado |
| 2 | kernel | El protocolo, bajo un prompt que no lo pide |
| 3 | **kernel + dominio** | La afirmación |
| 4 | base | Atribución, se compra último porque no puede matar nada |

**El brazo 1 reportó [ran].** La exactitud **reparada** del adaptador de dominio es **30/30** contra un crudo **1/30**, con **0** llamadas. Sus fórmulas son exactas en todos los casos; sólo falla la aritmética. La compuerta (0,25) se abre por lejos, la mitad de dominio queda verificada como aportante, y el brazo de composición se compra.

**La condición de parada, impuesta en el corredor y no en el criterio de alguien.**
Si la exactitud reparada del brazo de dominio queda por debajo de **0,25**, los
brazos 2–4 no se compran: no se le puede mostrar ganancia a una composición cuya
mitad no aporta nada.

**Falsación.** Con el contrato compartido y la mitad de dominio verificada, si
`kernel + dominio` sigue sin superar a las dos mitades solas, **la composición en
espacio de pesos está muerta** y §4 hay que servirlo de otra forma — activación
secuencial (§5 opción 1) o módulos disjuntos, y ninguna de las dos se compra acá.

**Los cuatro brazos reportaron [ran].**

| brazo | crudo | reparado | llam/caso |
|---|---|---|---|
| dominio | 1/30 | **30/30** | 0,0 |
| kernel | 0/30 | n/d | **7,7** |
| **kernel + dominio** | **4/30** | 22/30 | 0,6 |
| base (control) | **4/30** | indefinido | 0,0 |

**1. La conclusión de P8 era el confound, y la composición sí compone.** Con el
contrato compartido, `kernel + dominio` le gana a las dos mitades — 4/30 contra
1/30 del dominio y 0/30 del kernel — y hereda casi toda la física, 22/30 reparado
contra 30/30 del dominio. Nada de esto se parece al 0/30 que reportó P8.

**2. El mecanismo funciona cada vez que se dispara, y se dispara poco.** Partiendo
los 30 casos de la composición según si delegó o no:

| | casos | aciertos |
|---|---|---|
| la composición delegó | 5 | **3 — 0,60** |
| no delegó | 25 | 1 — 0,04 |

Una diferencia de quince veces. La composición no está rota: **delega en 5 de 30
casos, donde el kernel solo delega en los 30 con 7,7 llamadas cada uno.** El delta
de dominio gana la competencia por el formato en casi cada paso, y el protocolo del
kernel sólo sobrevive donde no la gana.

**3. El hallazgo más caro: la base no está en cero.** Bajo un prompt que pide una
cadena numerada, `Qwen2.5-3B-Instruct` **sin adaptador** saca **4/30** — empata con
la mejor composición y le gana a cada adaptador solo. Todas las líneas de base de
P5–P8 se midieron con un system prompt que le decía al modelo que **no mostrara el
trabajo**, mientras que todos los tratamientos se entrenaron para mostrarlo. El
headroom que esos pasos reportaron es menor de lo reportado, en una cantidad que
esta corrida no mide. **La brecha de +0,975 y los brazos de atribución en 0/40
heredan esta duda y hay que re-medirlos bajo el contrato compartido antes de
volver a citarlos.**

**4. `reparado` es indefinido para la base, no cero.** Escribe un encabezado
numerado y pone la aritmética en las líneas siguientes: 83 líneas numeradas en 30
casos, de las cuales el extractor lee **0**. La métrica vale donde el layout de la
cadena coincide con el corpus y en ningún otro lado; comparar puntajes reparados
entre layouts distintos sería medir el layout — el mismo error que cometió la α
por caracteres.

**Deliberadamente no comprado:** decoding restringido y reparación de etiquetas (19
de los 30 fallos apilados de P8 tenían todas las llamadas limpias, así que la
sintaxis nunca fue el fallo dominante) y más perillas de ponderación (una mezcla se
pre-registró y se corrió; una segunda sería una búsqueda).

#### P8 — el protocolo es separable, y no se apila

[`results/P8-harness-lora-20260909/`](../../results/P8-harness-lora-20260909/BRIEF.md),
`Qwen/Qwen2.5-3B-Instruct`, dos adaptadores sobre una misma base residente, 30
casos vistos cada uno, con el harness respondiendo cada llamada `<calc>` **[ran]**:

| brazo | exactitud | llamadas | llamadas/caso |
|---|---|---|---|
| base + herramienta | 0/30 | 44 | 1,5 |
| **kernel + herramienta** (nunca vio física) | 1/30 | **169** | **5,6** |
| **dominio + herramienta** (nunca vio una etiqueta) | 0/30 | **0** | 0,0 |
| **kernel + dominio + herramienta** (apilados) | **0/30** | 154 | 5,1 |

**La primera mitad de §4 se sostiene, y es la mitad sorprendente.** Un kernel
entrenado sólo con tickets de compra, promedios, crecimiento compuesto y
volúmenes de cono — *sin cañería, sin fluido, sin Reynolds* — entra a mecánica de
fluidos y llama a la herramienta 5,6 veces por caso, en los 30 casos. El experto
de dominio, que sabe la física, la llama **cero** veces en 30. El protocolo es
algo que se puede aprender solo, en pesos propios, y transfiere a un dominio que
su corpus nunca contuvo.

**La segunda mitad no.** Apilados, los dos adaptadores sacan 0/30 — por debajo
del kernel solo. Y el fallo no es que gane uno: **los dos están visiblemente
presentes en la salida**. La composición nombra la física correcta *y* llama a la
herramienta, y las llamadas salen corrompidas:

    1. área transversal: <calc>1.96 * 1.27</calc>= 2.4892
    2. perímetro mojado: <calc>1.96 + 2 * 1.27</calc>= 4.5
    3. radio hidráulico: <calc><b>2.4892</b> / 4.5</b>= 0.553133</calc>= ERROR
    4. velocidad: <calc>0.015 * 0.553133 * \sqrt{1 + 4*0.01518^2}</calc>= ERROR

LaTeX que se filtra, marcado suelto dentro de las etiquetas, términos que
desaparecen de las fórmulas. Esto es lo que le hacen dos deltas a α=32 a una base
ajustada para uno: `LoraModel` **suma** los deltas activos, así que la composición
perturba los pesos el doble de fuerte que aquello con lo que se entrenó cada
adaptador, y la fidelidad es lo primero que se cae.

**La falsación se disparó como estaba escrita**: la composición no le ganó a las
dos mitades, así que el protocolo no compone *por apilado*. Se compró una sola
alternativa, nombrada en el brief antes de que este número existiera —
`add_weighted_adapter` a 0,5/0,5, la corrección mecánica de una perturbación
duplicada.

**La mezcla también falla, y refuta la razón que yo di para el primer fallo.**

| brazo | exactitud | llamadas | casos con una llamada rechazada por el evaluador |
|---|---|---|---|
| kernel + herramienta | 1/30 | 169 | **0 / 30** |
| kernel + dominio, apilados | 0/30 | 154 | 11 / 30 |
| **kernel + dominio, mezclados 0,5/0,5** | **0/30** | 129 | **12 / 30** |

Partir a la mitad cada delta no devolvió la fidelidad de las llamadas — empeoró
apenas. Así que la corrupción **no** es un efecto de magnitud, y "dos adaptadores
a α=32 perturban el doble" era la explicación equivocada, ofrecida antes del dato
que la pone a prueba. Lo que sí muestra la mezcla es la forma de la corrupción:
las cadenas conservan los nombres de los pasos y su orden, y pierden el
*contenido* — una línea de Swamee-Jain que no es Swamee-Jain, el largo de la
cañería puesto en lugar del diámetro, una etiqueta abierta dentro de otra. El
kernel solo no malforma una sola llamada en 30 casos.

~~**La lectura que sobrevive.** Dos LoRAs entrenadas por separado sobre las mismas
proyecciones no se suman en la unión de sus conductas; interfieren, y la
interferencia cae justo sobre aquello en lo que cada adaptador era más
específico.~~ **Retirada el mismo día, 2026-09-09** — ver el confound abajo. Los
números de arriba se sostienen; esta explicación de ellos no.

#### El confound que anula la afirmación causal de P8 (2026-09-09) [ran]

Leyendo los dos corpus lado a lado, después de que corrieran los brazos:

| | corpus kernel | corpus dominio |
|---|---|---|
| ejemplos con `<calc>` | **600 / 600** | **0 / 598** |
| ejemplos con LaTeX (`\text`, `\frac`, `$`) | **0 / 600** | **433 / 598** |
| su system prompt | "no podés hacer aritmética vos: todo número calculado viene de una llamada `<calc>`" | "no muestres el trabajo en el mensaje final: contestá un solo objeto JSON" |

Hay tres cosas mal ahí, y cada una alcanza sola.

1. **Los dos corpus enseñaron notaciones distintas, no sólo contenidos
   distintos.** La corrupción que yo atribuí a interferencia de subespacios —
   `\sqrt{...}` adentro de una etiqueta `<calc>`, `\times`, marcado suelto — es
   *la superposición de dos formas de superficie que los adaptadores literalmente
   vieron en entrenamiento*. La calculadora no parsea LaTeX, así que una cadena
   que las mezcla falla en la etiqueta y no en la física.
2. **El system prompt del corpus de dominio contradice a sus propios targets.**
   Dice "no muestres el trabajo" sobre 598 mensajes de asistente que muestran el
   trabajo. Es un resto del prompt de headroom de P6.
3. **Todos los brazos se evaluaron con el system prompt del DOMINIO**, incluido el
   brazo del kernel y los dos de composición — un prompt que instruye lo contrario
   de aquello para lo que el kernel fue entrenado.

Así que P8 no puede distinguir *"la composición en espacio de pesos falla"* de
*"a los dos adaptadores se les enseñó a escribir en idiomas distintos y se los
juzgó con un prompt que no coincidía con ninguno"*. Lo segundo es más simple y
encaja con todas las observaciones.

**Lo que sí se sostiene, porque no depende del confound.** El kernel llamó a la
herramienta en **30 de 30** casos y no malformó **ni una** — bajo un system prompt
que le decía que no mostrara el trabajo, en un dominio que su corpus nunca
contuvo. Eso es un resultado más fuerte para la transferencia del protocolo que
el que decía el texto original, no más débil.

**Lo que ahora se sabe que quedó sin medir.** El adaptador de dominio emitió sólo
`{"answer": ...}` en los 30 casos — ninguna cadena bajo el prompt de evaluación —
así que nunca se midió si sabe la física. Sus respuestas directas quedan a un
factor ~2. No se le puede mostrar ganancia a una composición cuya mitad nunca
demostró aportar nada.

**Y la sintaxis no es el fallo dominante**, cosa que el diagnóstico gratis dejó
resuelta antes de escribir todo esto: de los 30 fallos del brazo apilado, **19
tenían todas las llamadas limpias** y aun así erraron la física. Reparar etiquetas,
o restringirlas con una gramática, ataca a lo sumo un tercio de la brecha.

**Qué le cuesta esto a la arquitectura.** La separación de §4 queda en pie como
hecho sobre el *aprendizaje* — el kernel existe y transfiere a un dominio que su
corpus nunca contuvo — y se cae como hecho sobre el *servicio*: la configuración
que funciona es el adaptador fusionado de P7, 40/40, y un cambio en la superficie
de herramientas cuesta entonces reentrenar cada experto del pool. Ése es
exactamente el precio que §4 existe para evitar, y no queda evitado.

**No comprado, a propósito.** La opción 1 de `TECHNICAL-REFERENCE.md` §5 —
activación secuencial, los dos adaptadores nunca vivos a la vez — sigue sin
medirse y es barata, porque los dos adaptadores ya existen. No se corre acá: el
brief pre-registró **una** alternativa, y comprar un tercer modo de composición
después de dos fallos es como una medición se convierte en una búsqueda. Se lleva
un paso propio, con su compuerta escrita antes, o no se compra.

#### P7 — la brecha de retiro se cierra, y hacen falta las dos mitades

[`results/P7-calculator-20260908/`](../../results/P7-calculator-20260908/BRIEF.md),
`Qwen/Qwen2.5-3B-Instruct`, 600 cadenas escritas por el oráculo, con el harness
respondiendo cada llamada `<calc>` **[ran]**:

| arm | | exactitud | llamadas |
|---|---|---|---|
| maestro `gemini-3.8-flash` | 40/40 | **1,000** | — |
| base | 0/40 | 0,000 | 0 |
| base + calculadora | 0/40 | **0,000** | **53** |
| adaptador solo | 4/40 | 0,100 | 0 |
| **adaptador + calculadora** | **40/40** | **1,000** | 156 |

**La brecha de retiro es 0,000** en la región para la que se destiló el experto.
Y ninguna mitad lo logra sola: el base hizo 53 llamadas a la herramienta y no
acertó ninguna; el procedimiento sin herramienta acertó 4 de 40.
`ARCHITECTURE.md` separa el kernel que actúa del experto que piensa — acá esa
separación es la diferencia entre 4/40 y 40/40, con cada mitad aislada por turno.

**El límite es el de la propia arquitectura.** Las familias reservadas iban 0 de
10 cuando la sesión terminó: el experto no generaliza fuera de su región, que es
exactamente por qué el plan promueve y retira **por región**. Ese arm no terminó,
y el 0/10 se reporta como observado y no como resultado persistido.


#### P3 resuelto — el sustrato existe, sobre una base que vLLM puede servir

`Qwen/Qwen2.5-3B-Instruct` — `Qwen2ForCausalLM`, densa, sin torre de visión — en
una A100 con vLLM 0.28.0 **[ran]**:

    [gate] adapter changes output: True
    [pure batch]  20/60 = 0,333   77,66 prompts/s

La compuerta pasó, y la exactitud servida coincide con la que midió
`transformers` con la misma receta (18/60). **Que dos implementaciones coincidan
es para lo que se construyó P3**, y es la primera vez que la capa 1 de esta
arquitectura existe.

Por eliminación queda explicado el silencio anterior: `Qwen3.5-2B` es híbrido y
multimodal, y la clase de vLLM que declara `SupportsLoRA` no es ninguna de las dos.

**El arm de batch mezclado queda anulado, y la culpa es de este repositorio.**
Llamaba a `generate()` una vez por prompt ciclando adaptadores —sesenta
round-trips secuenciales— y reportó 3,85 prompts/s contra 77,66, que se lee como
un castigo de 20× por sostener un pool. Medía el bucle. Ponerle precio al pool de
verdad necesita adaptadores por request *dentro de una misma pasada de
scheduling*: el motor async, o el servidor compatible con OpenAI con un nombre de
modelo por adaptador. Hasta entonces ese arm no reporta nada.


#### P3 — el pool no es servible, y falla sin avisar

[`results/P3-vllm-20260908/`](../../results/P3-vllm-20260908/BRIEF.md), A100,
vLLM 0.28.0, `Qwen/Qwen3.5-2B` **[ran]**:

| arm | exactitud | throughput |
|---|---|---|
| base, sin adaptador | 0,100 | — |
| `all-clinics` | **0,100** | 90,2/s |
| `alpha` | **0,100** | 93,3/s |
| `beta` | **0,100** | 92,7/s |

Cada adaptador saca **exactamente el 6/60 del base**, y una comparación directa de
dos prompts devolvió `RESULT IDENTICAL` las dos veces: el texto servido es byte a
byte el del modelo base. vLLM aceptó cada `LoRARequest` **sin error ni
advertencia** y no aplicó nada.

Descartado: los archivos del adaptador son válidos (`adapter_config.json` + 43 MB
de `adapter_model.safetensors`), `base_model_name_or_path` coincide,
`max_lora_rank` coincide con `r`, y no hay V0 al que caer — `VLLM_USE_V1` es
variable desconocida en 0.28.0. Abierto: el soporte de LoRA en V1 está documentado
como experimental **[read]**; `q_proj`/`k_proj` bajo el QK-norm de qwen3 es
justamente el mapeo que un stack de servido tiene que reconstruir; o una regresión
de esta versión.

**El arm que lo agarró fue el que parecía redundante** — "que salgan los mismos
números". Midiendo sólo throughput, esto habría reportado tres adaptadores
servidos a 90 prompts/s y dado el sustrato por probado.

**P4, P5 y P6 sirven adaptadores, así que ninguno se puede comprar hasta que un
adaptador cambie demostrablemente la salida de vLLM.** El próximo movimiento es
una decisión, no una corrida: fijar otra versión de vLLM, o reentrenar el pool sin
`q_proj`/`k_proj` y volver a probar. Las dos son baratas; elegir entre ellas no le
toca a esta sesión.

### Tomada el 2026-09-15: se deja la composición, y `harness.lora` se estaciona con ella

**Decisión del usuario, y el diagnóstico es correcto.** `harness.lora` es justamente
lo que requiere composición — existe para que el protocolo se enseñe una vez y cada
experto no lo re-aprenda. Un experto que trae su propio protocolo no tiene trabajo
para él.

**La tesis queda intacta.** Un pool de QLoRAs **autocontenidos** sobre una base
residente, intercambiados por request, sigue siendo *todo el sistema agéntico son
QLoRAs*. La composición era una **optimización** — compartir el protocolo — no el
enunciado. Sacarla saca maquinaria, no la pregunta.

**Qué compra.** Lo único que este repositorio nunca midió limpiamente es la
composición: el aparente "dos adaptadores interfieren" de P8 está anulado por un
confound de notación, y P35 midió que partir tiene un costo real — el vocabulario se
aprendió y preguntar cayó de 123 de 150 casos a 22. Sacar el split saca a la vez el
mecanismo sin medir y el costo medido.

**Qué cuesta, dicho en vez de descubierto.** Cada experto de subdominio nuevo paga
aprender el protocolo otra vez. Es un costo de **datos de entrenamiento**, no de
runtime, y es chico: 600 ejemplos y nueve minutos de L4 enseñaron el vocabulario de
email con **0 rechazos** **[ran]** P35.

**P34 queda estacionado, no falsificado.** Que un kernel entrenado sobre herramientas
de mecánica de fluidos lleve a esta base de **0 a 123 de 150** casos estirando la mano
hacia herramientas de email que nunca vio está medido y se sostiene. Es la única
evidencia de que la idea del kernel tiene patas, y si producir expertos autocontenidos
sale caro a escala, vuelve con ese resultado ya pago. Los adaptadores quedan en disco;
no se borra nada.

**P36 queda re-encuadrado por esto, antes de que existiera su número.** Se compró como
techo — *si el margen es alcanzable siquiera* — con el brief insistiendo en que un
monolito que clarea es sólo permiso para seguir midiendo. Bajo esta decisión **un
monolito que clarea es el resultado**: el primer miembro del pool puntuando en su
subdominio. Y un monolito que falla ya no significa *ninguna disposición del pool
sirve*; significa **esta base no puede con este subdominio**, que es más angosto y más
honesto.

### Tomada el 2026-09-15: primero los expertos supervisados, el mecanismo sólo si les gana

**La propuesta del usuario, y se adopta.** Entrenar cada experto de subdominio con
fine-tuning supervisado común, componerlo con el adaptador kernel, y gastar la
maquinaria de aceptación sólo en **mejorar** un experto que ya existe — si puede.

**Por qué es mejor, y no es cuestión de gusto.** Crea la línea base que el mecanismo
tiene que superar. Construido al revés, un experto salido del torneo no tiene nada al
lado, y cualquier número que saque se lee como éxito. La regla propia de este
repositorio es que **la línea base somos nosotros mismos**, y bajo este orden el
experto supervisado *es* esa versión.

**Y pone primero la mitad barata y probada.** Lo supervisado está medido acá varias
veces — la destilación transfiere el procedimiento (P6/P7, adaptador más calculadora
40/40), el protocolo es separable (P8), el vocabulario de herramientas se aprendió
exactamente como se quería, con 0 rechazos (P35). Del torneo tenemos **aptitud por
conjunción ordenando 2 de 2 pares** y un router que empata. Comprar primero la mitad
cara y menos validada es al revés.

**Qué cambia.** La frontera tenía dos trabajos — maestro de destilación y oráculo de
promoción. El primero queda. **El segundo pasa a ser condicional**: se compra recién
cuando haya un experto supervisado sobre el cual mejorar. Eso corre un paso más tarde
la pregunta central declarada de este repositorio, y por eso queda anotado como
decisión y no librado a la deriva.

**Lo que no vuelve más fácil.** P35 midió que entrenar una capacidad supervisadamente
**costó otra** — el vocabulario se aprendió y preguntar cayó de 123 de 150 casos a
22. Entrenar expertos por subdominio y después sumarles el kernel choca justo con esa
interferencia, y **la composición de dos LoRAs nunca se midió limpiamente acá**: el
aparente "dos adaptadores interfieren" de P8 está anulado por un confound de notación
y no debe citarse como hecho. Bajo este orden esa pregunta deja de estar aguas abajo
y pasa a ser la central.

**P36 ya es el primer paso de los dos planes.** Se compró como techo — si el margen
es alcanzable siquiera — y bajo esta decisión es además el primer experto supervisado
de subdominio. El mismo gasto contesta las dos cosas.

### Abierta: cómo lograr que a un adaptador se lo califique

Seis fallas de infraestructura y tres sesiones reclamadas, y al adaptador nunca
se lo puntuó. La elección es entre:

1. **Encadenar sesiones cortas.** Un arm por sesión, subiendo los resultados
   parciales al arrancar y bajándolos al terminar. La persistencia ya existe en
   una dirección; esto agrega la otra. Sin plata, más orquestación, y cada arm
   tiene que entrar en ~15 minutos.
2. **Colab Pro.** Más tenencia y una L4 o A100 —que además tiene bf16, así que el
   camino fp16 deja de hacer falta. Cuesta plata y la decisión es del usuario.
3. **Otro proveedor.** Superficie nueva, y la regla del workspace es que la
   superficie nueva es la forma cara de progresar.

Recomendado: **la 1, y la 2 si una corrida encadenada también falla.** Los arms
base ya están en el banco, así que la próxima sesión sólo debe el adaptador.

### Abierta: dónde se ve una ventaja de frontera, si es que se ve

S1 dice que esta suite no puede mostrarla. Tres configuraciones podrían, en costo
ascendente, y la elección es del usuario porque decide qué mide el proyecto:

1. **Poner de vuelta el bucle del runtime.** El 38–41/50 publicado salió de
   contrato, feedback y validación de acciones; un solo tiro crudo da 33–60 %. Si
   la ventaja de la frontera está en *usar* un contrato de interacción y no en la
   precisión de un tiro, ahí es donde aparece — y reutiliza `../verified-runtime`
   entero.
2. **Un dominio más difícil.** `causal_workflow` y `quantum` ya existen al lado
   con sus propios verificadores. Una tarea con un espacio de soluciones real es
   donde un 12B debería quedarse atrás de un modelo de frontera.
3. **Otra forma de tarea directamente** — documentos legales o clínicos largos,
   que es la vertical para la que se escribió la arquitectura y el único lugar
   donde un 12B local es menos probable que aguante.

Hasta elegir una, S4 y S5 no se pueden comprar: promover un experto y retirar una
frontera que nunca estuvo adelante no mide nada.

### Analizado 2026-09-15: la composición puede volver como pipeline, y P4 se reapunta

Análisis completo: [`../analysis/composition-and-speculative.md`](../analysis/composition-and-speculative.md).
No se implementó nada; en este plan cambian tres cosas.

- **Encadenar no es la composición que se descartó.** `base→lora1` y después
  `base→lora2` nunca tiene dos deltas vivos en el mismo forward, así que la pregunta
  por la interferencia no aparece — y el pool ya sirve exactamente eso, medido tres
  veces **[ran]** P40/P41/P42. Son dos pedidos con dos nombres de modelo, y no
  cuestan trabajo de serving.
- **La familia de P4 está mal y su premisa no está verificada.** Dice *un Qwen3.5
  grande*; los adaptadores están sobre Qwen2.5-3B, así que el target tiene que ser un
  **Qwen2.5** grande. Y que un 3B y un hermano grande compartan tokenizer es
  **[read]** — comparar dos hashes de `tokenizer.json` es lo primero que corre P4, no
  un supuesto debajo de P4.
- **El número que la literatura usa para esta arquitectura es aceptación, y nunca lo
  medimos.** Todos los números de acá son exactitud entregada.
  [TaskSpec](https://arxiv.org/html/2505.08600v1) reporta que un clasificador de
  prompt sobre cuatro drafters específicos por tarea sube la aceptación **16% → 58%**
  — nuestro pool, construido por otra gente, puntuado con una cantidad que no
  necesita verificador.

No adoptado: ruteo de adaptador por token (MoLoRA, WhiFlash). Es composición en el
espacio de pesos con otro nombre, y esa pregunta se cerró hoy.

### Analizado 2026-09-15: el experto que falla no tiene ninguna subregión buena

Análisis completo: [`../analysis/narrow-experts.md`](../analysis/narrow-experts.md).
Sin GPU; se releyó `results/P41-routing-20260915/`, partido por familia y apareado
contra la frontera sobre los mismos 90 casos.

| familia | n | local | frontera | sólo local | sólo frontera |
|---|---:|---:|---:|---:|---:|
| manning_channel | 23 | **0.304** | 0.826 | 1 | 13 |
| venturi_flow | 22 | 0.136 | 0.682 | 2 | 14 |
| hydrostatic_force | 23 | 0.043 | 0.609 | 0 | 13 |
| pipe_head_loss | 22 | 0.000 | 0.818 | 0 | 18 |
| **todas** | **90** | **0.122** | **0.733** | **3** | **58** |

**[ran]** 2026-09-15.

- **Todas las subregiones están dominadas**, así que un router más fino no habría
  encontrado nada. Estrechar un subdominio tiene que **crear** su ganancia
  entrenando; no puede revelar una que ya estuviera ahí.
- **La mitad "harness" de este experto ya funciona**: 604 llamadas, **0 rechazos**,
  6,7 llamadas por caso contra las 7,6 de la frontera, y siempre devuelve un número.
  Lo que falla es la física — de 79 fallos, **44 equivocados**, **12 dentro del 10%
  pero fuera de la tolerancia del 2%**, 2 errados por un factor de diez.
- **Más expertos es seguro sólo mientras el borde más fino siga siendo declarable.**
  El ruteo por región entrega 0,775 porque la región se conoce antes de que el
  modelo corra; un borde que exige leer la respuesta hereda el 0,378 del ruteo por
  caso.

**Próximo brazo (preregistrado).** Un experto estrecho sobre `manning_channel` solo,
puntuado sobre casos nuevos de esa familia. **Compuerta: 0,826**, el número de la
frontera ahí. Por debajo, estrechar no repara a un experto que razona y la idea se
cierra. `bar.n_for(0.304, effect=0.522)` devuelve **10**, así que el brazo resuelve
con cualquier n que corramos **[ran]**.

### Analizado 2026-09-15: la suite no tiene eje de dificultad, y la compuerta era la equivocada

Análisis completo: [`../analysis/sufficiency.md`](../analysis/sufficiency.md). Sin
GPU; se regeneraron los 90 casos de P41 desde su semilla y se leyó el **largo de la
solución del oráculo**.

| familia | pasos del oráculo | herramientas | local | frontera |
|---|---:|---:|---:|---:|
| manning_channel | 6 | 2 | 0,304 | 0,826 |
| hydrostatic_force | 6 | 3 | 0,043 | 0,609 |
| venturi_flow | 7 | 3 | 0,136 | 0,682 |
| pipe_head_loss | 9 | 3 | 0,000 | 0,818 |

**[ran]** 2026-09-15.

- **El piso de la suite son seis pasos y cada familia está clavada en una sola
  profundidad**, así que profundidad y familia son la misma variable. El experimento
  sólo podía preguntar *¿puede un 3B resolver una cadena de 6 a 9 pasos?*; nunca
  pudo preguntar si un experto chico alcanza en la punta fácil, porque la punta
  fácil nunca se generó.
- **Headroom, al revés.** Chequeamos techos; para los pisos no había regla. Una
  suite con una sola dificultad no distingue *demasiado débil* de *demasiado
  difícil* — las dos dan 0,122. Agregado a `CLAUDE.md` §3.
- **Qwen 2.5 es un piso que no elegimos** (C18, P33), así que todos estos números
  son una **cota inferior** de lo que puede un experto chico, no una estimación.

**Construido:** `training/physics/ladder.py`, cuatro escalones de 1 a 4 pasos por
debajo del piso de la suite — mismo dominio, mismas tres herramientas, mismo manual
por caso imposible de memorizar — y `fluids_sim --families {suite,ladder,full}` que
reporta `by_steps`, exactitud contra profundidad en vez de contra nombre de familia.
El oráculo se verifica corriendo sus propias cadenas con las herramientas reales, lo
que cazó una discrepancia de 1,3e-6 entre respuesta y cadena en `L4`.

**Reemplaza al brazo propuesto más temprano el mismo día** (*experto estrecho sobre
`manning_channel`, compuerta 0,826*): tomaba el número de la frontera como compuerta
sobre una familia sin punta fácil. No se compra.

**Próximo brazo (preregistrado), sin entrenar nada:** la base pelada, después el
experto `fluids-full` tal cual está, después la frontera **sólo como chequeo de
techo**, sobre la escalera completa 1 → 9. El brazo 1 dice qué escalones pueden
mostrar algo de un adaptador; el brazo 2 es la curva real de dónde un experto chico
deja de alcanzar, y sólo cuesta inferencia. **Compuerta para afirmar suficiencia:
0,90, absoluta** — con 0,80 una respuesta de cada cinco está mal y hay que
verificarlas todas a mano, que es justo lo que saca la razón de tener el experto.
**Falsación:** si la curva es plana — el experto falla un lookup de un paso más o
menos al mismo ritmo que una cadena de nueve — la dificultad no es lo que lo bloquea
y este análisis está equivocado.

### P45 — 2026-09-15 **[ran]** · FALSIFICADO, y no por la dificultad

Reporte: [`../../results/P45-ladder-sweep-20260915/RESULT.md`](../../results/P45-ladder-sweep-20260915/RESULT.md).
Una L4, dos brazos, 140 casos cada uno, semilla 454545. La sesión se apagó sola.

| profundidad del oráculo | base | experto | n |
|---:|---:|---:|---:|
| 1 | 0,111 | 0,278 | 18 |
| 2 | 0,000 | 0,000 | 18 |
| 3 | **0,167** | **0,000** | 18 |
| 4 | 0,000 | 0,000 | 18 |
| 6 | 0,000 | 0,382 | 34 |
| 7 | 0,000 | 0,000 | 17 |
| 9 | 0,000 | 0,000 | 17 |
| **total** | **5/140** | **18/140** | |

**Se disparó la falsación preregistrada**: punta fácil 0,069, punta dura 0,191 — la
fácil está *por debajo* de la dura, no apenas dentro de 0,15. La afirmación que
compró la corrida — que la profundidad es el eje que revela una banda de suficiencia
en este experto — está equivocada, y equivocada en una dirección que nadie propuso.

**El mecanismo, medido.** Por debajo de su profundidad de entrenamiento el experto
**sobre-resuelve en 18 de 18** casos; en ella o por encima, **0 de 17**. Su cadena
mediana tiene piso en unas cinco llamadas y no baja. Pedido `ρ g h` en dos pasos,
convirtió metros a metros, **inventó un área de 100 mm²** y contestó sobre fuerza.
**Un corpus con una sola dificultad enseña un piso, no sólo una habilidad** —
agregado a `CLAUDE.md` §3.

**Qué sobrevive.** No que este experto tenga una banda de suficiencia: no la tiene,
porque esa banda nunca estuvo en sus datos. Pero la afirmación general — que un
experto chico puede alcanzar en un nivel conocido y aceptable — sigue **sin probar**,
porque ningún experto de este repo fue entrenado nunca con un problema fácil. La
punta fácil que le faltaba a la suite pasó a faltarle al experto, porque el corpus se
genera desde la suite.

**Deliberadamente no lanzado:** un experto entrenado sobre la escalera completa. El
brief decía que una curva plana frena la GPU, e inventar una hipótesis y comprarla la
misma noche es como un instrumento empieza a buscar un resultado. Queda especificado.

**Salvedad sobre el brazo de la base:** 140 llamadas para 140 casos, 85 rechazadas,
contra 810 y 75 del experto. Mide **disposición**, no dificultad — no citar *"la base
saca 0,111 en un paso"* como *"los problemas de un paso son difíciles"*.

### P46 — 2026-09-16 **[ran]** · casi todo el margen de P44 era la suite

Reporte: [`../../results/P46-ranking-ceiling-20260916/RESULT.md`](../../results/P46-ranking-ceiling-20260916/RESULT.md).
**Sin GPU.** Los mismos 475 casos de P44, con el inbox regenerado desde su semilla y
los ids y la verdad verificados antes de cruzar nada.

| subconjunto · brazo | gap medido | IC 95% | techo | margen | es la suite |
|---|---:|---|---:|---:|---:|
| all · email-full | 0,128 | [0,105, 0,155] | 0,098 | **+0,030** | 77% |
| all · base | 0,105 | [0,084, 0,127] | 0,098 | **+0,007** | 94% |
| human · email-full | 0,400 | [0,346, 0,449] | 0,277 | +0,123 | 69% |
| human · base | 0,338 | [0,288, 0,388] | 0,277 | +0,062 | 82% |

**P44 preguntó si el gap era grande. Nunca preguntó cuánto de él era reclamable.** En
el inbox completo los dos brazos ya están en el techo. En el subconjunto humano el
predictor de techo es una **constante** — un solo grupo, `rankable: false` — así que
los 0,123 que quedan son margen para dejar de ser *peor* que una constante, no para
ordenar mejor.

**Se cancela el brazo tipado que lee sólo el listado**: una confianza constante no
rutea nada, que es exactamente la ceguera que P41 encontró en la escalación por caso.

**Reapuntado:** una respuesta tipada **encima** de la cadena de herramientas, no en
lugar de ella. Con las herramientas todos los hechos son recuperables, la verdad
queda decidible y el techo colapsa al piso del oráculo. `email-full` llega a 0,741 con
herramientas **[ran]** P43 y nadie midió la confianza de *esa* respuesta. **Servir, sin
entrenar** — el próximo chequeo de headroom, no el próximo tratamiento.

Regla nueva en `CLAUDE.md` §3: chequear el techo del *ordenamiento*, no sólo el de la
exactitud. Instrumento: `training/harness/ceiling.py`.

### Analizado 2026-09-16: cuatro capas, y P1 por fin tiene precio

Análisis completo: [`../analysis/layered-routing.md`](../analysis/layered-routing.md).
Sin GPU.

**P1 — *ponerle precio al router* — estaba abierto desde el 2026-09-08 y queda
contestado**, con una regla de doce líneas de palabras clave sobre 140 casos de
fluidos que cubren las siete profundidades de la escalera más 60 listados de email
**[ran]** 2026-09-16, n = 200:

| pregunta | decide | baseline léxico |
|---|---|---|
| **gruesa** — qué suite | **qué superficie de herramientas montar** | **1,000** |
| fina — qué familia | qué drafter preferir | 0,845 |

- **La ruta gruesa no necesita modelo.** Es el trabajo que la capa de herramientas
  necesita y sale perfecto con palabras clave. La capa 1 empieza siendo un **dict**.
- **Las capas 1 y 4 son un solo artefacto** — una decisión, dos consumidores — y es el
  bloqueo vivo del producto: 54 herramientas frente a un experto entrenado con 3, y no
  llamó ninguna **[ran]**. `contract.accepts()` le da la regla de rechazo gratis.
- **La confusión fina que queda es el borde de profundidad** (`L2` y `L3` son la misma
  física, una necesita conversión), que es lo que declara `band` y lo que midió P45.
- **La capa 2 (tokens estructurales) es un cambio de corpus, no de entrada**, y el
  único resultado cercano es negativo: los valores declarados de P28 fueron
  *dañinos*, fallos de manual 3 → 17. Se compra como A/B sobre un experto o no se
  compra.
- **La capa 3 está aguas abajo de P4** — un 3B drafteando para un 3B no compra nada.
  Cuando esté viva el emparejamiento es libre, porque todos los miembros comparten el
  tokenizer de la base residente. TaskSpec y Not-a-Bandit dicen lo mismo: *elegir con
  un clasificador*, nunca evaluar a todos.

`tests/test_router_baseline.py` mantiene el número re-corrible en vez de citado.

### Abierto 2026-09-16: nunca servimos más de dos adaptadores a la vez

`--max-loras` sólo fue 1 o 2 en este repo — el pool más grande que se sirvió es
`['email-full', 'fluids-full']` **[ran]** P41. El diseño por capas de
[`../analysis/layered-routing.md`](../analysis/layered-routing.md) §6b es lo primero
que necesita muchos, y los *miles en una máquina* de S-LoRA son **[read]**, no
nuestros.

**La prueba barata, sin comprar:** cargar diez nombres sobre los dos adaptadores que
ya tenemos y mirar tokens/s contra un baseline de un solo adaptador. Sin entrenar, sin
corpus, una sesión corta. Es el único riesgo real en la afirmación de que las capas
son asequibles.

### P48 — 2026-09-16 **[ran]** · la premisa del tokenizer, verificada en vez de asumida

`results/P48-tokenizer-compat-20260916/`. **Sin GPU.** Se hashearon los tokenizers
publicados y se compararon id por id. C3 decía *un target de frontera no comparte el
tokenizer de la base* y P4 asumía que uno de la misma familia sí; ninguna de las dos
estaba medida.

| target | vocab del target | ids coinciden | usable | ids extra |
|---|---:|---|---|---:|
| **Qwen2.5-7B / 14B / 32B / 72B-Instruct** | 151.643 | **sí** | **sí** | 0 |
| Qwen3-14B / Qwen3-32B | 151.643 | **sí** | **sí** | 4 (`<think>`, …) |
| **Qwen3.5-27B / Qwen3.6-27B / Qwen3.8-27B** | **248.044** | **no** | **NO** | 26-33 |

**El drafter es `Qwen2.5-3B-Instruct`**, la base sobre la que viven todos los
adaptadores. **El vocabulario de Qwen3.x cambió en la 3.5** — 151.643 → 248.044 — así
que los 27B no sirven como target especulativo por buenos que sean.
`Qwen2.5-32B-Instruct` es la elección: tokenizer byte-idéntico, sin canal de
pensamiento, mismo chat template.

- **Un target de la misma familia no necesita argumento.** Todos los tamaños de
  Qwen2.5-Instruct hashean el mismo archivo.
- **Un target de otra generación es usable**, que es lo que C3 había descartado. Los
  `merges` gobiernan texto→ids, que ocurre una vez para el prompt; la especulación
  vive en el espacio de ids después de eso.
- **Lo que los hashes no muestran:** los cuatro ids que sólo el target tiene son
  inalcanzables para el drafter, así que un target **pensante** rechaza en cada
  `<think>`. La regla C7 —leer la aceptación en el canal de respuesta— deja ahí de ser
  una convención y pasa a ser la diferencia entre una tasa de aceptación real y una
  ficticia.

Instrumento: `training/harness/tokenizer_compat.py`, 5 tests. **Es el primer paso de
P4**, antes de servir nada.

### P4 reformulado 2026-09-16: la aceptación como torneo, retiro por subdominio

Análisis: [`../analysis/layered-routing.md`](../analysis/layered-routing.md) §6b.

La redacción vieja —*servir un Qwen3.5 grande al lado de los adaptadores 2B,
aceptación a nivel token por fin medible*— era una afirmación de velocidad. La forma
ahora es:

**k drafters expertos de un mismo tamaño contra un target más grande.** Que todos los
drafters sean 3B es irrelevante; lo que paga es que el target sea más grande y lento,
así que el chico emite varios tokens mientras el grande emite uno.

- **La aceptación se vuelve un ranking de expertos que no necesita juez** — mismo
  target, mismo prefijo, mismas condiciones. Es lo que el torneo de S7 nunca tuvo, y
  es la cantidad que la literatura usa para esta arquitectura mientras todos nuestros
  números son exactitud entregada.
- **Restaura la brecha de retiro en la granularidad correcta.** Si el experto de un
  subdominio alcanza al target lo suficiente, el target se retira **para ese
  subdominio** — la misma granularidad por región que entregó 0,546 → 0,775 **[ran]**
  P41.
- **La aceptación sola no dice quién tenía razón.** Un rechazo es el chico
  equivocándose o el grande equivocándose, y sólo el verificador al lado los separa.
  El brazo es *aceptación y score verificado sobre los mismos casos*.
- **Compuerta, a preregistrar antes de correr:** un umbral de aceptación solo no puede
  autorizar un retiro — el score verificado no debe caer donde se saca el target. Es
  la lección de S5 y aplica sin cambios.

### Planificado 2026-09-16: expertos cercanos sobre un mismo problema, elegidos por aceptación

Diseño: [`../analysis/close-experts.md`](../analysis/close-experts.md). **Nada construido.**

**La corrección, y da vuelta un resultado mío.** La ruta gruesa de P1 dio **1,000** y
yo la reporté como *la capa es un dict, qué barato*. La lectura correcta es que **un
problema de discriminación que se resuelve con doce palabras clave no es una prueba
de selección de expertos** — mecánica de fluidos y triaje de email nunca se encuentran
en un mismo problema. La misma corrida muestra el régimen difícil: la ruta fina cae a
**0,845**, confundiendo familias que difieren sólo en si hay que convertir una unidad.

**Tres expertos de redacción sobre una bandeja**, un solo set de herramientas, una
base, **cambiando sólo la política**: `draft-client`, `draft-team`, `draft-vendor`.

**Por qué aceptación y no router.** Un router pregunta qué experto *parece*
relevante; la aceptación pregunta qué experto *escribió lo que el modelo grande
hubiera escrito*. Sólo la segunda sobrevive cuando los candidatos se parecen. Y
redactar **no tiene verificador mecánico**, que es donde el torneo de S7 siempre se
trabó — mientras que la aceptación no necesita ninguno.

**Target: `Qwen2.5-32B-Instruct`**, tokenizer byte-idéntico **[ran]** P48.
`Qwen3.6-27B` no puede verificar a nuestros drafters *Qwen 2.5* — un drafter `Qwen3.5` sí puede ser verificado por `Qwen3.8-27B` **[ran]** D0 — 248.044 entradas contra
151.643 — y queda disponible como referencia de calidad, que es otro trabajo.

| paso | qué compra | ¿entrena? | compuerta |
|---|---|---|---|
| **P49** | **headroom** — ¿el target redacta mejor que la base pelada? | no | un chequeo mecánico de contenido (¿están los hechos requeridos en el borrador?) debe separarlos por un margen que `bar.resolvable()` llame detectable. **Si no, el diseño no se compra** |
| **P50** | ¿son tres expertos tres expertos, y la aceptación varía por temática? | sí, 3 | `members_are_distinct` del pool, y después por temática el experto que corresponde le gana al mejor de los otros en un **test de signos apareado** |
| **P51** | la selección corriendo dentro de OpenClaw, sobre las herramientas MCP y la bandeja que ya funcionan **[ran]** P43 | no | sólo si P50 despeja |

**Falsación, antes de correr:** aceptación plana en la grilla experto × temática
significa un experto con tres nombres, y el gate del pool es lo que lo dice.

**El riesgo que no es excusa:** lo bastante cerca para ser interesante es lo bastante
cerca para estar dentro del ruido. El chequeo de potencia va antes del brazo, no
después.

### P49 — 2026-09-16 **[ran]** · se compra, y una temática de tres no tiene headroom

Reporte: [`../../results/P49-draft-headroom-20260916/RESULT.md`](../../results/P49-draft-headroom-20260916/RESULT.md).
Una A100, dos brazos, 90 casos, **sin entrenar nada**. La sesión se apagó sola.

| brazo | borradores completos | tasa de hechos |
|---|---:|---:|
| `Qwen2.5-32B-Instruct-AWQ` | **76/90 = 0,844** | 0,948 |
| `Qwen2.5-3B-Instruct` | **49/90 = 0,544** | 0,756 |

**Margen 0,300 contra un 0,10 preregistrado — el diseño se compra.**

**Pero el titular esconde lo que importa:**

| temática | target | base | brecha |
|---|---:|---:|---:|
| **client** | 0,667 | **0,033** | **0,633** |
| vendor | 0,867 | 0,633 | 0,233 |
| **team** | **1,000** | **0,967** | **0,033** |

**`team` no tiene headroom** — los dos brazos en el techo, que es el fallo de ARC de
P42 aislado en una temática. El margen de 0,300 es casi todo `client`, donde la base
completa **1 de 30**.

**Qué hace la base, leído y no inferido:** escribe una respuesta razonable y **omite
los datos concretos** — la referencia falta 28 veces y el monto 25. Y el chequeo no
mide puntuación: de **80** hechos faltantes en los dos brazos, **0** aparecen escritos
de otra forma.

**Tres consecuencias para P50.**
1. **`team` se arregla o se saca.** Promediar una temática saturada diluye lo que
   muestren las otras dos. Ojo: las dos con headroom piden un **monto** y la que no
   tiene pide un **nombre de pila**.
2. **La brecha es de capacidad, no de estilo** — *nombrar siempre la referencia y la
   cifra* es una política, entrenable y chequeable mecánicamente, y un objetivo mejor
   definido que "escribir en registro de cliente".
3. **Hasta el target falla 10 de 30 en `client`**, así que aceptación contra él no es
   corrección. `carries()` va **al lado** de la aceptación, nunca detrás.

### Corregido 2026-09-16: el corpus de un drafter lo debería escribir el target

Leer el README completo de Model-Optimizer en vez de un resumen cambió dos cosas en
[`../REPORT.md`](../REPORT.md) §6, y una cambia la **sesión 2**.

> *"Para lograr tasas de aceptación más altas conviene usar como datos de
> entrenamiento conversaciones generadas por el modelo base. Eso asegura que la
> distribución de salida del draft se alinee con la del base."* **[read]**

**Todo corpus de este repo se genera desde un oráculo** — la cadena que escribiría un
solucionador correcto. Si la aceptación contra un target es el criterio de promoción,
el corpus que produce al drafter lo debería generar **ese target**. Nadie había
conectado las dos cosas.

**Y la sutileza es lo que la mantiene como señal de ranking.** Cada experto se entrena
con conversaciones generadas por el target **sólo de su región**. Entonces A coincide
con el target en A, B en B, y la aceptación varía por región — que es la señal que
necesita la sesión 3. **Si todos se entrenaran con la salida del target en todas las
regiones, la aceptación sería uniforme y el ranking colapsaría.** Preregistrar contra
eso.

También corregido: **Qwen 2.5 está en la matriz de soporte de EAGLE3**, y el camino de
entrenamiento online es para modelos que entran en memoria — un 3B entra, en la A100
que ya alquilamos. Los terabytes son del camino *offline* y yo generalicé el costo de
uno a los dos. Lo que no cambió: **una cabeza EAGLE no puede rankear expertos.**

### P51 — 2026-09-16 **[ran]** · sesión 1 de 4: la banda disparó, `usable: false`

Reporte: [`../../results/P51-desk-profile-20260916/RESULT.md`](../../results/P51-desk-profile-20260916/RESULT.md).
Una A100, dos brazos, 240 casos, **sin entrenar**. La sesión se apagó sola.

**base 69/240 = 0,288 · target 101/240 = 0,421**, y tres celdas de dieciséis
sobreviven a la banda — las tres de `importance`. El grid colapsó en una fila, que es
lo que el brief decía que frenaría las otras tres sesiones. **La banda no se mueve.**

**Dos regiones de cuatro son incontestables para los dos modelos.** `owed` saca
**0,000 también con el target**, en las cuatro profundidades; `counterpart` llega a
0,133 como mucho. Las dos preguntan sobre todo el inbox — enumerar 24 hilos, después
consultar por candidato, después comparar — y ni un 3B ni un 32B lo terminan en 8
turnos. Por la regla de este mismo proyecto, esas son **celdas rotas, no difíciles**.

**Y la regla encontró su propio defecto.** `commitment@4` es **base 0,000, target
1,000** — descartada porque la base está en el piso, por una cláusula escrita para
*"todos los brazos fallan y se lee como que el enfoque no funciona"*. Pero el target
prueba que la tarea se puede, así que esa celda es **exactamente la forma que un
experto chico existe para cerrar**, con toda la distancia a la vista. `commitment` va
1,000 → 0,800 → 0,133 → 0,000 mientras el target se mantiene en 1,000: el gradiente
más limpio que produjo este proyecto, y la banda tiró su mitad de abajo.

**Notarlo después de los números es justo cuando no se puede arreglar por mi cuenta.**
La cláusula del piso necesita una compañera — *salvo que el target despeje la celda* —
y hacer ese cambio ahora es indistinguible de mover la banda para que encaje. Queda
escrito, y la decisión es tuya.

**Próximo movimiento, si se toma:** volver contestables `owed` y `counterpart` y hacer
que el gradiente de `commitment` aterrice dentro de la banda — **cambios de suite con
la banda fija**, que es un acto distinto de mover la banda. Sería el **primer rediseño
post-resultado** de esta suite; el contador arranca en uno.

### P53 — 2026-09-16 **[ran]** · el paso cero pasa con +0,689, y el número es nulo

Reporte: [`../../results/P53-step-zero-20260916/RESULT.md`](../../results/P53-step-zero-20260916/RESULT.md).

**base 56/180 = 0,311 · adaptador 180/180 = 1,000**, apareado, el adaptador ganando
124 casos que la base pierde y perdiendo 0, p exacta < 1e-5. La compuerta preregistrada
pasa.

**Y todas las completaciones retenidas aparecen literales en el entrenamiento — 180 de
180.** Los prompts difieren porque difieren las constantes; la *completación* es
idéntica, porque las constantes se referencian por nombre y viven en el prefijo. El
adaptador aprendió una cola por familia, no a computar nada.

**Lo causó el arreglo anterior.** La partición del corpus encontró que el corte más
profundo se llevaba la línea con la entrada del programa, así que dos programas daban
el mismo prompt con respuestas distintas; la reparación volvió incortable todo lo que
está arriba de la implementación — lo que puso cada valor variable en el prefijo y dejó
la cola constante. Parametrizar las constantes no sirvió de nada, porque las constantes
son justo la parte que nunca hay que escribir.

**Qué sobrevive:** la maquinaria entera — entrenamiento en subproceso, C18, verificación
por ejecución sobre 360 completaciones sin un solo error de transporte — y el 0,311 de
la base, con **38 de 180** completaciones que ni compilan.

**El arreglo:** poner las constantes en línea donde se usan, para que la cola las lleve
y dos programas de una familia nunca compartan respuesta. **Segundo rediseño
post-resultado de una suite hoy; el contador va en dos.**

### P54 — 2026-09-16 **[ran]** · el paso cero pasa con +0,863, y agota la suite

Reporte: [`../../results/P54-step-zero-rebuilt-20260916/RESULT.md`](../../results/P54-step-zero-rebuilt-20260916/RESULT.md).

**base 27/197 = 0,137 · adaptador 197/197 = 1,000**, apareado, 170 a 0, p < 1e-5.

**El chequeo de filtración fue primero, y esto no es P53.** Completaciones retenidas
literales en entrenamiento: **0 de 197** contra las 180 de 180 de P53. Todas las
completaciones que produjo el adaptador son distintas. Generalizó sobre constantes
sorteadas del espacio completo de 32 bits, así que **el +0,863 es real**.

**Y lo que aprendió es más angosto de lo que el número sugiere.** Con las constantes en
blanco, las 197 completaciones colapsan a **6 esqueletos distintos** — dos familias por
tres profundidades de corte son unas seis combinaciones (familia, punto de corte), cada
una con una única forma correcta. La tarea es *reconocer cuál de seis aplica y poner
constantes que están en el comentario*. La base igual llega sólo a 0,137, así que no es
trivial; pero es **esta familia de plantilla**, no completación de código.

**Entonces: el paso cero está contestado que SÍ** — una base con el LoRA adecuado
aprende este predicado y le gana por lejos. **Y nada aguas abajo es medible acá**: un
experto en 1,000 no se puede rankear, y la aceptación no tiene nada que discriminar. Es
el techo de P42 llegando desde el lado del tratamiento.

**La suite siguiente necesita variedad estructural, no más constantes** — el arreglo que
falló dos veces fue variar los *valores*; lo que tiene que variar es la *forma* de la
cola. Objetivo: tantos esqueletos distintos como casos, no seis.

**Proceso:** `compare` toma dos mapas, y el mismo `TypeError` terminó P53 **y** P54,
porque la primera vez se esquivó en vez de repararse. Arreglado, con test.

### Analizado 2026-09-16: si conviene pasarse a la familia Qwen 3, y la respuesta es todavía no

Análisis completo: [`../analysis/qwen3-migration.md`](../analysis/qwen3-migration.md).
Sin GPU.

**El hecho que replantea todo: el target nunca necesitó LoRA.** C18 — vLLM loguea
`Loaded new LoRA adapter` y sirve la base igual **[ran]** P33 — restringe al
**drafter**, que es donde vive el pool. No dice nada de un modelo denso al que sólo
se le pide verificar.

Así que la pregunta se parte, y las mitades tienen respuestas distintas:

| | respuesta | por qué |
|---|---|---|
| un **target** Qwen 3 | **disponible hoy, gratis** | `Qwen3-32B` son 151.643 ids, coinciden, 4 sólo del target **[ran]** P48. Servirlo con el pensamiento apagado, porque esos 4 ids son `<think>`/`<tool_response>` y el drafter no tiene columna para ellos |
| `Qwen3.8-27B` como target | **bloqueado** | 248.044 ids. Obliga a mover el drafter a 3.x, y 3.x es donde vive C18 |

**El mecanismo que se propone para C18 no es lo que dice nuestro propio log.** Acierta
en que la clase es `Qwen3_5ForConditionalGeneration` y en que la atención lineal GDN
está corriendo **[ran]**; se equivoca en que los kernels del lado del lenguaje no
despachan — cada línea `no matching PunicaWrapper` nombra un módulo `visual.`,
`_lora_expand_kernel` compiló JIT *durante la inferencia*, y "el adaptador tocaba sólo
los MLP" es un diagnóstico que P33 ya **retiró**. La falla está medida; el mecanismo
**no se conoce**, y queda anotado como no conocido.

**Por qué igual va tercero.** Este proyecto le compra **ranking** a la decodificación
especulativa, no latencia — y α nunca se midió, contra ningún target.
`Qwen2.5-32B-Instruct` alcanza para medirlo. Un target más nuevo y más lento no acerca
esa medición; encarece una que no se tomó. Y
[`../analysis/generated-code-ceiling.md`](../analysis/generated-code-ceiling.md) anota
el bloqueo más duro que hay debajo: **rankear necesita expertos que difieran en
calidad**, y este proyecto tiene un experto útil.

Orden: expertos que difieran en calidad → α los rankea o no → *después* un target que
valga la migración.

### Construido 2026-09-16: la superficie de herramientas que declara cada miembro, y la poda

**No es un experimento — es la reparación que P43 nombró y dejó sin hacer.** `--prune`
en `openai_proxy`, `surface` en el contrato del pool, `tests/test_prune.py`.

El turno de agente de P43 no hizo **ninguna llamada a herramientas** **[ran]**, y había
dos cosas separables mal en lo que leía el experto: el **volumen** de etiquetas
desconocidas (P25 tarifa una superficie desconocida en 27 de 63 **[ran]**) y el
**renombrado** de las tres que sí conocía a `mcp__lora-inbox__…`. Ahora cada miembro
declara las etiquetas que le enseñó su corpus, al lado de la banda, y el proxy conserva
sólo las herramientas ofrecidas que coinciden con una — nombre exacto, o el último
segmento de uno con namespace. Las llamadas salen con el nombre de quien llamó.

**Lo que apareció al construirlo, y que ninguna cantidad de lectura habría dado.**
Renderizar la superficie podada y exigir que sea igual al bloque entrenado **carácter
por carácter** cazó que la primera versión alfabetizaba las tres líneas — un bloque que
`email-full` nunca había leído, en un cambio cuyo propósito entero era mostrarle el
bloque que sí había leído **[ran]** 2026-09-16. El orden ahora es parte de la
declaración donde el corpus enseña uno, y alfabético donde no.

**Viene apagado por defecto**, porque toda medición anterior a hoy corrió sin él.
`--prune` prendido y apagado es el par de brazos, y no se corrió.

### Pre-registrado 2026-09-16: P55 — aceptación como ranking, sobre expertos graduados por construcción

Brief: [`../results/P55-graded-ranking-20260916/BRIEF.md`](../../results/P55-graded-ranking-20260916/BRIEF.md).
Runner `training/harness/accept_rank.py`, compuertas como código en
`tests/test_accept_rank.py`.
**Sesión A — `DONE`, 2026-09-17, tres intentos, detenida `UNBOUGHT` en M-target.**
Resultado: [`../../results/P55-graded-ranking-20260916/session_a.json`](../../results/P55-graded-ranking-20260916/session_a.json);
los intentos 1 y 2 quedan con su propio nombre — los dos fueron fallas mías del
instrumento (un preflight que medía la frase de la base; un loop que rechazaba las
llamadas posicionales que el propio bloque pide), cada una arreglada con un test antes
de relanzar.

| brazo | 475 | humanos 351 | llamadas · rechazadas | qué dice |
|---|---:|---:|---|---|
| base `Qwen2.5-3B` | 0,516 | **0,345** | 0 · 0 | reproduce P31 exacto |
| **`email-full`, modo corpus** | **0,992** | **0,989** | 1053 · **0** | **M0 desbloqueado**: vía `tool_calls` el mismo adaptador dio 0,808 (P43). Servido como enseña su corpus — parar en `</tag>`, inyectar el resultado real — resuelve la tarea. Reproducido en dos sesiones, 31 s cada una |
| `Qwen2.5-32B-AWQ`, modo corpus | 0,813 | **0,746** | 1248 · 195 | consigue todos los hechos en 3–4 llamadas y **aplica mal la regla** en 83 casos humanos; pareado contra el experto **2 : 87**, p = 0,0 — **resolublemente peor** |

**Todos los preflights de M-α pasaron** — C18 `applied`, templates idénticos,
`prompt_logprobs` con una entrada por token y `rank` — así que el instrumento está
listo y nunca corrió: **la compuerta rechazó el target por la razón para la que fue
escrita.** En esta suite un 32B sin entrenar no es más fuerte que el 3B entrenado, y
la aceptación contra él premiaría estar de acuerdo con veredictos equivocados. Fallan
dos cosas a la vez, las dos de la suite: el mejor experto está en el techo (0,99) y el
target está por debajo (0,75).

**La matemática de este paso** ([`FOUNDATIONS.md`](FOUNDATIONS.md) §7, §9). La
afirmación es $Q(E_a) > Q(E_b) \Rightarrow \alpha_T(E_a) > \alpha_T(E_b)$ con
$\alpha_T(E,c) = \tfrac{1}{n_c}\sum_i \mathbf 1[\tilde x_i = \arg\max p_T(\cdot\mid\cdot)]$;
es sobre calidad sólo bajo $Q(T) \ge \max_a Q(E_a)$, que es lo que M-target prueba como
test de signos pareado y lo que falló acá ($0,746 < 0,989$, 2 : 87). Los grados son
resolubles a $n=351$ sólo para $\delta \ge 0,07$ (potencia 0,93), lo que los fijó en
75 / 200 / 598. **Próximo paso, en los mismos términos:** una suite donde valga
$Q(T) \ge \max Q(E)$ y $\max Q(E) < 1$ — la región `commitment` del desk satisface la
primera por medición (target 1,000 en cada profundidad) y la segunda por su gradiente.

**Candidato a rediseño, contado como el primero:** mover la prueba de orden a la
región `commitment` del desk, donde P51 ya midió al 32B en **1,000 en las cuatro
profundidades** y a la base cayendo **1,000 → 0,800 → 0,133 → 0,000** **[ran]** — un
target más fuerte que la base por construcción y un gradiente sobre el que ningún
experto se va a sentar. Necesita un corpus de desk (no existe) y tres expertos de desk
graduados. Queda para decidir.

También del boot: la cadena instala `vllm>=0.28` y resuelve a **0.29.0 — la misma
versión que corrió P33** **[ran]**, así que la pista D1 no tiene nada más nuevo que
re-verificar; D2 es el paso vivo para un drafter 3.x.

**La primera prueba de la afirmación central.** La aceptación contra un target más
grande nunca se midió contra ningún target, y el motivo nunca fue hardware: rankear
necesita expertos que difieran en calidad, y este proyecto tuvo uno. Así que los
expertos se gradúan **por construcción** — `g75 ⊂ g200 ⊂ email-full`, un corpus, una
base, sólo cambia la cantidad de datos — y el verificador tiene que ordenarlos *antes*
de que se sirva el target.

**Una deriva corpus/serving encontrada en el camino, y arreglada primero.** El corpus
renderiza una cadena como `<tag>…</tag>= {resultado}`; servido vía `tool_calls` el
experto no puede recibir un resultado a mitad de generación y **lo inventa** — el
registro de P43 tiene `= {"turns": 1, "i_wrote_in_thread": false}` donde la
herramienta dijo `2, true` **[ran]**. El runner sirve al drafter como enseña el
corpus: parar en `</tag>`, inyectar el resultado real, seguir. Los resultados
inventados se cuentan (`stray_results`), nunca se puntúan.

**Aceptación en tokens, por primera vez.** Mismo tokenizer **[ran]** P48, así que al
target se le entrega el draft tal cual y se le piden `prompt_logprobs`: un token se
acepta sii su rango bajo el target es 1. Reportada sobre todos los tokens de decisión
(primaria), los spans de etiqueta, el span del veredicto y como prefijo aceptado —
porque una cadena son ~40 tokens y el veredicto es uno, y *"α no rankea"* tiene que
poder decir dónde vivió el acuerdo.

**Un mecanismo por compuerta, una compuerta por sesión:** servir en modo corpus y C18
→ un target que le gane al experto *en triage* (P49 lo compró en drafting) → los
preflights del instrumento → los grados resueltos por el verificador → la prueba de
orden. Veredictos pre-registrados: SUPPORTED / FALSIFIED / UNRESOLVED (un fracaso, no
un empate) / M1 no desbloqueado / UNBOUGHT.

**Pista D — `Qwen3.8-27B` como modelo grande** está en la ruta, como mecanismos en
orden. **D0 [ran] hoy:** `Qwen3.5-2B` y `Qwen3.5-4B` comparten espacio de ids con
`Qwen3.8-27B` — 248.044 ids, 7 sólo del target, todos especiales de audio/TTS;
`<think>` es compartido. D1 re-verifica C18 bajo el vLLM que la cadena instala hoy;
D2 lee el mecanismo con el log en la mano; D4 es este instrumento apuntado a
3.8-27B. Nada de P55 depende de D; D4 depende de todo P55.

### Analizado 2026-09-18: Skill-to-LoRA y Adaptive Minds, leídos contra el registro

Análisis completo: [`../analysis/s2l-and-adaptive-minds.md`](../analysis/s2l-and-adaptive-minds.md). Sin GPU, todo **[read]**.

**Ninguno mueve el camino crítico.** S2L (un `SKILL.md` convertido en un LoRA por
skill, Qwen3.6-27B) reporta 59 / 54 / 65 de 210 para sin-skill / texto completo /
adaptador — el signo de P61 y un efecto dentro del ruido ($z = 1{,}19$ y $0{,}65$, sin
parear, sin semillas), así que es trabajo relacionado y no respaldo; la evidencia es el
137 : 1 de P61 **[ran]**. Su auto-destilación no transfiere: el maestro es base +
documento, que sobre esta base hace cero llamadas a herramientas **[ran]** P61.
Adaptive Minds (la base lee la metadata de los adaptadores y nombra al miembro) reporta
que el ruteo por keywords cae de 48,3% con 5 adaptadores a 31,7% con 30 — la falla
predecible de `route.py` en el hito 5.

Quedan registradas tres cosas y no se compra ninguna:

- **El candidato a router para el hito 4**, estacionado porque el diccionario está en
  1,000 y cualquier retador empata: la base como router sobre la `description` de cada
  release, la tabla medida `serve: local|out` sigue decidiendo, **la frontera como
  default**, puntuado por **mal-ruteados-a-local** (el término cero de FOUNDATIONS
  §8.4), con el brazo de abstención primero.
- **Un primer brazo para D2:** los adaptadores de S2L se aplican sobre Qwen3.6-27B bajo
  vLLM **[read]** y apuntan sólo a `q_proj,v_proj`, mientras los de P33 cubrían las
  proyecciones de atención lineal. `tiny_adapter` con esos dos targets sobre
  `Qwen3.5-4B` por `--gate-only`, al lado del control Qwen2.5-3B, localiza C18 en los
  módulos target o lo descarta.
- **A 27B el documento de procedimiento tampoco ayuda [read]** — no asumir que el hito
  7 rescata el brazo de sólo-harness; `knowledge_arm` sobre el 32B lo mide.

### Pre-registrado 2026-09-18: D2 — C18 leído como un desajuste de nombres, y el brazo que lo prueba

Brief: [`results/D2-rekey-20260918/BRIEF.md`](../../results/D2-rekey-20260918/BRIEF.md).
Leído sin GPU en vLLM v0.29.0 y en el log de P33 **[read]**: el adaptador, entrenado por
`AutoModelForCausalLM`, nombra sus tensores `model.layers.N…`; vLLM sirve
`Qwen3_5ForConditionalGeneration` y su mapper sólo reescribe `model.language_model.`.
La carga valida el último componente de cada nombre y loguea *Loaded*; la activación
busca el nombre completo, no encuentra nada y resetea el slot detrás de un `logger.debug`.
Con $\text{applied}(K)=\{k\in K: m(k)\in M\}$, tal como se entrenó $|\text{applied}|=0$;
renombrado, predicho $|K|$. `lora_matrix --rekey` compra el brazo renombrado **sólo si
falla el G2 del sujeto**, con el control al lado y las líneas de activación contadas en
DEBUG. Lo falsifica un G2r `not applied`. Esto reemplaza al brazo de sólo
`q_proj,v_proj` registrado arriba. Contador de rediseños de D2: 0.

## 12. Historia

| fecha | cambio a este plan | por qué |
|---|---|---|
| 2026-09-09 | **P8 corrido: el protocolo es separable pero no se apila.** Un kernel que nunca vio física llama a la herramienta 5,6 veces por caso en mecánica de fluidos; el experto de física la llama 0 veces; apilados sacan 0/30, con las dos conductas visiblemente presentes y las llamadas corrompidas. La mezcla a 0,5/0,5 quedó pre-registrada antes de que el número existiera | §4 separa lo que posee el kernel de lo que posee el experto, y sólo se había medido el caso fusionado — la mitad que se sostiene y la que no son mitades distintas de las que la arquitectura suponía |
| 2026-09-07 | plan creado; S0 construido y corrido; el test de α contra calidad se movió antes del entrenamiento de adaptadores | el E1 de la especificación valida α sólo después de que existan los adaptadores, que es donde el test deja de ser barato |
| 2026-09-07 | S0 corrido tres veces; §3 completado; agregados C9 y C10; el contador de rediseños llegó a su condición de parada y el instrumento **no** se cambió una cuarta vez | la métrica estaba midiendo el formato, y la regla de contar rediseños existe justamente para el momento en que es incómoda |
| 2026-09-07 | S6 pasó de "en paralelo" a "en revisión, posiblemente aguas arriba de α" | si el adaptador kernel es lo que fija el formato, entonces es lo que hace que la aceptación por caracteres signifique algo |
| 2026-09-07 | S1a corrido sobre `held_out_delta`: 8/12 contra 3/12 y 4/12. La pregunta de suite de S1 quedó cerrada por $0; sólo la key la bloquea | el fallback estaba nombrado en el paso antes de correrlo, que es la única razón por la que cambiar el split acá es un plan y no una búsqueda de un número más amable |
| 2026-09-08 | S3 contestado offline con los registros de S4: el acuerdo elige al experto correcto en 9 de 10 casos decisivos y recupera 0,725 de un oráculo de 0,750 — y empata exacto con leer `clinic:` del prompt | el mecanismo es real y esta suite no puede ponerle precio, porque etiqueta la región que el router debería inferir |
| 2026-09-08 | **S4 completo. Pregunta 2 contestada: propia región 0,725 contra ajena 0,525, diagonal ganando en las dos direcciones — pero en los casos de `alpha` los dos expertos difieren en un caso de veinte, así que la señal es asimétrica.** El primer arm de región fue anulado por presupuesto de entrenamiento desigual | hay un pool que rutear, y ahora se sabe que el problema de ruteo es desparejo entre regiones en vez de suponerlo uniforme |
| 2026-09-08 | **S4 pregunta 1 contestada: el adaptador saca 44/60 contra 6/60 del base, +63,3 puntos, y gana 20 puntos en el split de regla invertida que nunca vio.** Agregado C17 | el primer resultado real que produjo este proyecto, y el tercer cero previo era gradient checkpointing, no el modelo |
| 2026-09-08 | S4 corrido sobre `Qwen/Qwen3.5-2B`: arms base guardados en 6/60 y 6/30; los del adaptador bloqueados. Agregados C15 y C16; la regla de aborto disparó en la tercera sesión reclamada | el 0/60 que produjo la T4 se habría leído como "no hubo especialización" — una condición de falsación cumplida por la GPU y no por el modelo |
| 2026-09-07 | S1 comprado y fallado tres veces ($0,47 en total); S2 comprado en las mismas compras y aprobado 14 de 15 pares; agregados C12 y C13 | la compuerta estaba escrita antes de la corrida y disparó — el desenlace más barato posible, porque impidió comprar S4 y S5 sobre una configuración donde la frontera nunca estuvo adelante |
| 2026-09-07 | agregado un cuarto candidato (`qwen3.5:2b`) por sugerencia del usuario | la escalera local empataba en 6/20 y un empate vuelve incomprable el test de orden; ir de 2B a 12B le dio al criterio algo sobre lo que acertar o errar |
| 2026-09-07 | los targets tienen su propio presupuesto de tokens, y las respuestas locales se cachean | un target que piensa devolvió 9 de 20 respuestas truncadas en 700 tokens, y regenerar cuatro candidatos locales por cada target nuevo eran ocho minutos que no compraban nada |
| 2026-09-07 | S1a extendido al split completo de 20 casos; la coincidencia de órdenes de n=12 **no sobrevivió** y la fila superada queda tachada, no borrada | los candidatos diferían en un caso verificado con n=12 y empatan exactamente con n=20 — un caso nunca fue un orden, y un plan que tirara la fila anterior en silencio sería el registro de nada |
| 2026-09-07 | S6a corrido a $0 sobre corridas existentes: el protocolo cuesta ~96 tokens acá y el 12B nunca malforma, así que S6 necesita una distribución de herramientas real antes de que sus números signifiquen algo | chequear el headroom del tratamiento antes de construirlo es la corrida más barata que existe, y ésta no costó ni una inferencia |
| 2026-09-07 | agregado C11 y hecho visible en el reporte | el modelo con mejor acuerdo era también el que no contestaba nada el 25 % de las veces, y el criterio estaba excluyendo justo esos casos en silencio |
| 2026-09-07 | §11 decidido (opción C): el criterio de promoción es el acuerdo semántico de respuesta; S2 reescrito alrededor de él; S6 ganó una segunda condición de victoria; las cuatro corridas en disco se re-puntuaron sin volver a correr nada | la coincidencia por caracteres falló sobre una respuesta correcta y acertó por razones ajenas a la calidad, en la misma suite y el mismo día |
| 2026-09-07 | un empate en calidad verificada ya no se reporta como test de orden fallido | los candidatos de S0c sacaron los dos 3/12, y llamar a eso desacuerdo fabrica un test fallido a partir de uno que no era testeable |
| 2026-09-07 | arreglado un bug del reporte — el orden global usaba la métrica de payload y el orden por región usaba la cruda, así que un mismo reporte afirmaba acuerdo y desacuerdo sobre la misma corrida. No es un rediseño; el contador sigue en 3 | un reporte que se contradice en dos líneas es peor que uno que no dice nada |
