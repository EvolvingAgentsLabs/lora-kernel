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
| **2** | el router como un modelo chico de los corpus | los corpus de los miembros | mal-ruteados-a-local no mayor que el del diccionario en prompts para los que el diccionario no fue escrito; abstiene ante texto fuera de distribución | — |
| **3** | la mitad grande de un par | 1 | un LoRA en `Qwen3.8-27B` está `applied` al servirse; grande + LoRA le gana a chico + LoRA en la banda profunda, pareado | — |
| **4** | el par especulativo | 3 | la aceptación de borradores del LoRA chico bajo verificación del LoRA grande supera la aceptación bajo el modelo grande pelado | — |
| **5** | la primera región real, a mano | 1, 2, un sandbox, claves rotadas | la compuerta de release, sobre una suite con un verificador que nadie acá generó | bloqueado: el usuario nombra la región |
| **6** | la política de servicio, con la factura | 2, 4, 5 | la porción local ahorra más de lo que cuesta, sobre tráfico real | — |

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

- **2026-09-19** — objetivo reformulado alrededor del ruteo por distribución de corpus y
  el par especulativo; el árbol limpiado a lo que funciona; el plan anterior y sus
  setenta y cuatro corridas se conservan en `v0.1-foundations`.
- **2026-09-06 → 2026-09-19** — ver [`RECORD.md`](RECORD.md).
