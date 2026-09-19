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
> chico y un LoRA en uno grande, entrenados sobre el mismo corpus. Familia: Qwen 3.x, chico
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

Lo que queda de antes: la frontera es un componente permanente, usada donde el corpus de
ningún experto cubre el pedido o donde se mide que una región falla (0,546 → 0,775 **[ran]**
P41); los expertos se entrenan por SFT ordinario; toda región entra por la compuerta de
release; el servicio de personalización y su tooling quedan afuera de este runtime y del
open source.

Lo que se retira: la aceptación como forma de *rankear* expertos no relacionados contra un
mismo target (cerrado sin veredicto después de dos precondiciones fallidas; un rediseño de
tres sin gastar, y no se va a gastar); la composición de adaptadores; el instrumento de
aceptación a nivel de carácter; el experto de mecánica de fluidos.

## 1. Los hitos

Los brazos se compran en secuencia. El brazo que puede matar un hito corre primero; los
brazos de atribución se compran sólo una vez que hay un efecto que atribuir.

| # | hito | depende de | compuerta | estado |
|---|---|---|---|---|
| **1** | el pool en Qwen 3.x chico | D2 ✅ | los dos miembros liberados en `Qwen3.5-4B`, cada uno empatando o ganándole a su release de Qwen 2.5, pareado | — |
| **2** | el router como un modelo chico de los corpus | los corpus de los miembros | mal-ruteados-a-local no mayor que el del diccionario en prompts para los que el diccionario no fue escrito; abstiene ante texto fuera de distribución | **brazo 1 [ran] 2026-09-19 — no pasa.** Texto extranjero, conjuntos frescos: el diccionario sirve 59/128 localmente, el router de n-gramas **0/128**; pedidos legítimos de remitentes no vistos: el diccionario pierde 0/120, el router pierde **120/120**. El diccionario se queda; **el brazo 2 es un modelo de embeddings**, compartido con el hito 7 |
| **3** | la mitad grande de un par | 1 | un LoRA en `Qwen3.8-27B` está `applied` al servirse; grande + LoRA le gana a chico + LoRA en la banda profunda, pareado | — |
| **4** | el par especulativo | 3 | la aceptación de borradores del LoRA chico bajo verificación del LoRA grande supera la aceptación bajo el modelo grande pelado | — |
| **5** | la primera región real, a mano | 1, 2, un sandbox, claves rotadas | la compuerta de release, sobre una suite con un verificador que nadie acá generó | bloqueado: el usuario nombra la región |
| **6** | la política de servicio, con la factura | 2, 4, 5 | la porción local ahorra más de lo que cuesta, sobre tráfico real | — |
| **7** | **una base de conocimiento por subdominio, y la trayectoria por ella como harness** — sobre mecánica de fluidos, partida en subdominios | 1; comparte su modelo de embeddings con el brazo 2 del hito 2; independiente de 3–6, **corre a continuación** | un experto entrenado para navegar y seguir notas contesta familias sobre las que nunca entrenó, donde el mismo experto sin la base está en 1/20 | — |

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

$$p = 2\sum_{k=0}^{\min(b,c)} \binom{b+c}{k}\,2^{-(b+c)} .$$

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

$$\text{entregado} = \tfrac1n\sum_x [r(x)=(\text{local},m^*)]\,L_{m^*}(x) + [r(x)=\text{out}]\,F(x) + [r(x)=(\text{local},m\ne m^*)]\cdot 0 ,$$

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

### Hito 4 — el par especulativo

**Objetivo.** Medir la aceptación de los borradores del miembro chico bajo la
verificación del miembro grande, los dos llevando el LoRA del mismo subdominio.

**Cómo se mide, y por qué.** vLLM trae multi-LoRA y decodificación especulativa, pero un
drafter con LoRA es un RFC, no una feature **[read]**. Así que la aceptación se mide como
este repositorio ya la mide (`accept_rank.py`): el miembro chico genera, el grande puntúa
el borrador en una sola pasada con teacher forcing (`prompt_logprobs`), y un token se
acepta cuando es el argmax del modelo grande a temperatura 0. Con aceptación por token
$\alpha$ y largo de borrador $k$, los tokens esperados por pasada del modelo grande son

$$\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha} .$$

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

### Hito 5 — la primera región real

Personalizada a mano, liberada por la misma puerta: una suite con un verificador, la base
como brazo de headroom, el test de signos. Setenta y cinco a cien ejemplos escritos a mano
es el primer tamaño correcto — ahí saturó la banda superficial del desk. **Bloqueado en
una decisión que es del usuario: qué región, de quién son los datos.** Necesita un sandbox
para todo lo que ejecute y claves rotadas.

### Hito 6 — la política de servicio, con la factura

Router → miembro chico → par donde se mide que la región lo necesita → frontera. El
número que nunca se midió es la plata: la factura de la frontera con y sin la porción
local, sobre tráfico real. **Falsificado por** una porción local que cuesta más correrla
de lo que ahorra.

### Hito 7 — una base de conocimiento por subdominio, y la trayectoria por ella como harness

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
real — la frontera 66/90, el experto 12/90 **[ran]** P40, P41 — y su falla es del tipo que una
base de conocimiento ataca: el protocolo perfecto, la física equivocada, 19 de 30 fallas con
cada llamada limpia **[ran]** P8. Un solo adaptador sobre todo eso se entrenó a una sola
profundidad y se pasó de rosca por debajo de ella **[ran]** P45. Entonces: subdominios de dos
familias hermanas cada uno — flujo interno (`pipe_head_loss`, `pump_power`), medición
(`venturi_flow`, `orifice_discharge`), flujo externo (`terminal_velocity`, `drag_force`),
canales y estática (`manning_channel`, `hydrostatic_force`) — cada uno a través de la escalera
de dificultad (`training/physics/ladder.py`), así que región y profundidad son dos variables.

**Tres hechos medidos dan forma al diseño — restricciones, no objeciones.**

1. **Un modelo chico no sigue lo que lee a menos que seguir sea lo que se entrenó** **[ran]**
   P61. → La navegación y el seguimiento de notas son *el contenido del adaptador*: el corpus
   son trayectorias — `<kb>consulta</kb>`, `<open>nota</open>`, después `<calc>` — escritas por
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
| **0** | margen, cero GPU: las 90 cadenas grabadas de P41 reproducidas contra el handbook propio de cada caso (`training/physics/result_use.py`) | **[ran] 2026-09-19.** De 79 fallas, **74** tienen un `<calc>` con un número que no salió de ningún lado y **74** dejan un resultado de herramienta sin usar; 132 de 371 resultados no finales se ignoran — el experto busca la densidad, 882,3, y multiplica por 1359,7. **La falla dominante no es una relación equivocada: es no usar lo que se le devolvió** |
| **0b** | **el mismo adaptador, los mismos 90 casos, servido en modo corpus** — el resultado inline después del tag de cierre, como enseñó su corpus — en vez de por `tool_calls`, que a `email-full` le cuesta 0,992 → 0,808 **[ran]** P55. Diez minutos de L4, el adaptador está en disco | separa *un 3B no usa lo que lee* de *el harness no se lo mostró como se lo enseñaron*. **Se compra antes del brazo 1**: cualquiera de las dos respuestas decide cómo una base tiene que entregar lo que recupera, y la segunda significaría que "el experto que razona falla" fue en parte un instrumento |
| **1** | **trayectoria oráculo.** Dos adaptadores sobre un subdominio, mismos casos: entrenados *con* las notas que el oráculo abriría, inyectadas por el protocolo `<kb>`/`<open>`, y *sin* ellas. Puntuados sobre la familia entrenada y sobre su **hermana dejada afuera**, pareado | la cota superior: si leer exactamente las notas correctas no levanta a la hermana de ~1/20, ninguna navegación lo hará — **parar** |
| **2** | navegación aprendida: el experto emite sus propias consultas; recuperación por embeddings adentro de la base del subdominio. Medido **donde pasa** — se recuperó la nota necesaria, se abrió, se siguió — no sólo en la respuesta final | qué pierde la navegación contra la trayectoria oráculo |
| **3** | atribución: sólo notas enciclopédicas · sólo notas operacionales · las dos | qué clase de conocimiento lleva la ganancia — las dos clases, tasadas por separado |
| **4** | recuperación: léxica plana · embeddings · embeddings restringida a la trayectoria hasta ahora (enlaces y vecinos de la última nota abierta) | si una estrategia de trayectoria le gana a una búsqueda plana; el resultado previo del workspace dice no asumirlo |
| **5** | editar sin reentrenar: cambiar el coeficiente de una nota después de entrenar; la respuesta tiene que seguir a la base, no a los pesos | que el conocimiento vive donde se puede editar |

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

## 2. La familia, y la alternativa

**Adoptada: Qwen 3.x.** `Qwen3.5-2B/4B` y `Qwen3.8-27B` comparten un espacio de ids —
248.044 ids, 7 sólo del grande, todos especiales de audio/TTS; `<think>` es compartido
**[ran]** D0. El canal de pensamiento está apagado para los miembros: ningún corpus lo
enseñó. Los miembros liberados están en `Qwen2.5-3B-Instruct` hasta que aterrice el hito
1, y la línea Qwen 2.5 sigue siendo el control en cada compuerta.

**Alternativa, no ahora: Gemma 4, 2B y 12B.** El diseño es agnóstico de familia — un par
necesita un espacio de ids y una base a la que PEFT pueda engancharse. Gemma 4 falla lo
segundo hoy: `Gemma4ClippableLinear` no es `nn.Linear` **[ran]** P29. `lora_matrix` con
un sujeto Gemma es la compuerta que la reabre.

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

- **2026-09-19** — hito 2 brazo 1 **[ran]**: seguro ante texto extranjero, pierde todo pedido
  de un remitente no visto; el diccionario se queda, el brazo 2 es un modelo de embeddings.
  Se agregó el hito 7: una base de conocimiento por subdominio con la trayectoria por ella
  como harness, sobre mecánica de fluidos partida en subdominios — dado forma por P61, P21 y
  P14.
- **2026-09-19** — objetivo reformulado alrededor del ruteo por distribución de corpus y
  el par especulativo; el árbol limpiado a lo que funciona; el plan anterior y sus
  setenta y cuatro corridas se conservan en `v0.1-foundations`.
- **2026-09-06 → 2026-09-19** — ver [`RECORD.md`](RECORD.md).
