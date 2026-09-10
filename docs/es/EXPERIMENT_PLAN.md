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
