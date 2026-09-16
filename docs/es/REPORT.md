# Informe: el plan original contra lo que pasó, y el patrón de las fallas

**2026-09-16.** Escrito para que lo discutan. Todo número es **[ran]** con su
directorio de corrida; lo que es de afuera del repo va **[read]** y citado.

---

## 1. El plan, como se escribió el 2026-09-07

> **¿Es la aceptación contra un target de frontera un criterio válido de promoción
> para un experto chico — y cuánta calidad verificada se pierde cuando se retira la
> frontera?**

Se apoyaba en dos afirmaciones, y el plan decía que sólo esas dos valían plata
primero:

1. **α significa destilación.** Una tasa alta de aceptación contra un target de
   frontera identifica a un experto que ya produce lo que la frontera produciría,
   *acá*.
2. **La frontera se puede retirar.** Cuando α cruza un umbral en una región, el
   experto genera solo y el score verificado casi no se mueve. Esa diferencia — la
   **brecha de retiro** — es el producto.

Y nombró su propia falsación: *si α no ordena candidatos como los ordena la calidad
verificada, la afirmación 1 es falsa y el router gratis no existe.*

## 2. Qué pasó con cada afirmación

| afirmación | veredicto | dónde |
|---|---|---|
| **α significa destilación** | **nunca se le pudo poner precio.** La coincidencia eligió el experto correcto en **9 de 10** casos decisivos y recuperó 0,725 de un oráculo de 0,750 — y **empató exacto** con una regla que lee `clinic:` del prompt | S3 **[ran]** |
| **la frontera se puede retirar** | **cerrada, pero no por la aceptación.** Adaptador + calculadora **40/40** = el maestro, brecha **0,000**. El adaptador solo saca 4/40 y la base con calculadora 0/40 | P7 **[ran]** |
| **α como métrica** | **retirada en caracteres.** Respuestas idénticas puntúan 0,00 entre formatos; distintas 0,44 dentro de uno | C9 **[ran]** |
| **la frontera como andamio** | **invertida.** No se retira — es el fallback permanente, y vale **0,546 → 0,775** con 38% de los casos saliendo | P41 **[ran]** |
| **la frontera como target especulativo** | **imposible, y siempre lo fue.** No devuelve logprobs de una continuación forzada, y tiene otro tokenizer | C2, C3 · P48 **[ran]** |

**Así que la pregunta original se disolvió en vez de contestarse.** No porque α fuera
falsificada — porque la configuración que suponía (frontera como target, retiro como
producto) resultó no ser construible, y lo que **sí** cerró la brecha de retiro fueron
veinte líneas de aritmética.

## 3. Lo que sí se construyó, y no es poco

- **El sustrato.** Dos adaptadores residentes sobre una base, elegidos por el campo
  `model` de un pedido HTTP, medido **tres veces**, incluso con el adaptador de un
  tercero al lado **[ran]** P40/P41/P42.
- **Un experto genuinamente bueno.** `email-full`: **384/475 = 0,808**; en mensajes
  humanos **260/351 = 0,741** contra barra 0,655, p exacta **0,00036** **[ran]** P43.
- **Ruteo que paga, por región.** 0,546 → 0,775 **[ran]** P41.
- **El end-to-end dentro de un agente real**, con las herramientas por MCP y cero
  pedidos saliendo de la máquina para lo que el pool sirve **[ran]** P43.
- **Un target elegido por hash y no por argumento** **[ran]** P48.

## 4. El patrón de las fallas, que es el punto de este informe

Poné en fila cada resultado negativo de los últimos diez días y abajo de casi todos
está lo mismo.

| corrida | qué creíamos medir | qué medíamos en realidad |
|---|---|---|
| S3 | si la coincidencia puede rutear | si el prompt ya dice la región — **la decía** |
| P13 | si un protocolo aprendido le gana al código | si copiar una expresión necesita aprenderse — **no** |
| P42 | si el adaptador de un tercero ayuda | si la base ya estaba en el techo — **0,815 vs 0,825** |
| P45 | si la profundidad es lo que bloquea al experto | si la suite tenía eje de profundidad — **ninguno; piso de seis pasos** |
| P46 | si un head tipado tiene lugar | el **techo de información de la entrada** — 69-82% del margen |
| P1 | si hace falta un router | si doce palabras clave alcanzan — **1,000** |
| P49 | si un target más grande es mejor | en una temática de tres, **nada** — los dos en el techo |

> **Casi todo resultado negativo de este proyecto es la suite estando mal, no la
> arquitectura estando mal.**

Y hay una razón por la que sigue pasando, que conviene decir derecho:

> **Toda suite de acá la genera una función que escribimos nosotros, y una suite
> generada no puede contener una dificultad que no se nos ocurrió.**

Generamos lo que podemos verificar mecánicamente. Lo que se verifica mecánicamente
tiende a ser lo que un modelo ya hace — que es por qué la base aparece una y otra vez
en el techo. Cada vez, lo que habría hecho informativo al experimento estaba diseñado
para afuera: la región venía etiquetada, la dificultad era uniforme, el dato decisivo
estaba en el prompt, la temática estaba saturada.

**El repositorio se adaptó chequeando el headroom primero**, y esa adaptación es
real — cuatro brazos cancelados antes de la GPU en dos días, que es el sistema
funcionando. Pero cancelar brazos no es producir resultados. **Nos estamos volviendo
muy buenos en no gastar de más y nada mejores en encontrar un segundo experto útil.**

## 5. Qué está genuinamente bloqueado, y es una sola cosa

**Un segundo miembro útil del pool.** Atacado desde cuatro direcciones y ninguna dio:

1. **Comprarlo.** El ecosistema público de Qwen2.5-3B tiene personas sin oráculo y
   adaptadores de opción múltiple donde la base ya está en el techo **[ran]** P42.
2. **Estrechar el experto que falla.** Ninguna subregión suya es competitiva — todas
   las familias dominadas por la frontera **[ran]**.
3. **Arreglarle la profundidad.** El piso lo enseña el corpus, y por debajo de su
   banda el experto sobre-resuelve en **18 de 18** **[ran]** P45.
4. **Un head tipado.** Cancelado por su propio techo **[ran]** P46.

Todo lo de aguas abajo — el torneo, el router que elige miembro, las verticales — está
esperando esto, y hace nueve días.

## 6. Decodificación especulativa: qué son los módulos de NVIDIA, y qué no son

Leído de [la colección][coll], [el blog][blog] y
[el README de Model-Optimizer][mo] **[read]** 2026-09-16.

[coll]: https://huggingface.co/collections/nvidia/speculative-decoding-modules
[blog]: https://developer.nvidia.com/blog/an-introduction-to-speculative-decoding-for-reducing-latency-in-ai-inference/
[mo]: https://github.com/NVIDIA/Model-Optimizer/blob/main/examples/speculative_decoding/README.md

**Qué son.** 18 módulos, y los nombres cuentan la historia:
`Qwen3-235B-A22B-Eagle3`, `Llama-3.3-70B-Instruct-Eagle3`, `gpt-oss-120b-Eagle3-*`,
`Llama-3.1-8B-Medusa-FP8`, más heads más nuevos `DFlash`/`DSpark`. **Cada uno es una
cabeza de drafting atada a un target grande específico.** Model-Optimizer los entrena
desde **los estados ocultos del propio target**, y no dice nada sobre reusarlos entre
targets — cosa que la entrada vuelve estructuralmente improbable **[read]**.

**Las tres variantes.** Draft-target (un modelo chico aparte), **EAGLE-3** (una cabeza
liviana pegada a las capas internas del target) y cabezas de predicción multi-token.
La única cifra concreta del blog es ilustrativa — tres tokens en 250 ms contra 600 —
y **no cita ni una tasa de aceptación ni un speedup** para ningún modelo nombrado, lo
cual vale notar en una introducción de un fabricante.

### Lo que esto resuelve para nosotros, y es una corrección

**La decodificación especulativa tiene dos propósitos posibles y los veníamos
mezclando.**

| propósito | qué gana | ¿lo puede reclamar nuestra arquitectura? |
|---|---|---|
| **latencia** — hacer rápido al modelo grande | una cabeza **entrenada sobre los estados ocultos de ese target** | **no** |
| **ranking** — qué experto ya produce lo que produciría el grande | **k expertos de dominio drafteando contra un target** | **sí, y sólo esto** |

Existe una cabeza EAGLE-3 para exactamente nuestro target — hay builds comunitarios de
`Qwen2.5-32B-Instruct_EAGLE3` en el Hub **[read]** — y va a draftear mejor para ese
target que cualquiera de nuestros expertos de dominio, porque para eso fue entrenada y
no tiene otro trabajo.

> **Así que nuestra especulativa no es una jugada de latencia, y los documentos deben
> dejar de sugerir que lo es.** Una cabeza de 5 MB hecha a medida nos gana en eso. Lo
> que ella **no** puede hacer es **rankear** — hay una cabeza por target, así que no
> hay entre qué elegir. La aceptación como **métrica de torneo sin juez sobre k
> expertos** es la afirmación que sobrevive, y es lo único que esta arquitectura tiene
> y EAGLE no.

### Y una cosa que sí conviene tomar

Las dos se componen. **Un 32B con cabeza EAGLE es un target más rápido**, y un target
más rápido abarata la medición de aceptación — P49 se pasó casi una hora de A100
esperando a un modelo de 19,3 GB. Es una compra de ingeniería, ortogonal a la tesis, y
está disponible hecha.

**Lo que no hay que hacer** es entrenar una cabeza EAGLE nosotros. El camino offline
de Model-Optimizer pide *"varios a decenas de terabytes"* de estados ocultos
**[read]**; el online colocaliza draft y target. Ninguno es un workspace que alquila
una A100 por hora, y ninguno contesta la pregunta que realmente tenemos.

## 7. Qué cambiar, planteado como opciones y no como decisión

1. **Dejar de generar la suite donde la dificultad importa.** Toda falla de §4 es una
   suite que escribimos nosotros. El único lugar con dificultad que no diseñamos es el
   **end-to-end con OpenClaw** — un agente real, una superficie real de 54
   herramientas, una falla real que nadie planeó. El bloqueo de 3-contra-54 es la
   primera dificultad honesta que este proyecto encontró, y llegó de casualidad.
2. **Hacer del chequeo de headroom una compuerta en el runner, no un hábito.** Se
   corrió cuatro veces a mano en dos días. Un paso que no puede declarar su techo no
   debería poder lanzarse.
3. **Aceptar que el segundo experto quizá haya que construirlo, no encontrarlo.** Tres
   de los cuatro intentos de §5 fueron búsquedas. El cuarto — construir un corpus que
   enseñe una política que la base demostrablemente no tiene — es el único que alguna
   vez funcionó, y P49 acaba de medir exactamente esa brecha: la base omite la
   referencia **28 veces de 30** y el monto 25.
4. **Ordenar las afirmaciones por lo que sobreviviría a una publicación.** El
   sustrato, el experto bueno y el ruteo por región son reales. El torneo, las capas y
   los tres niveles son análisis. La distancia entre esas dos listas es el estado
   honesto del proyecto.
