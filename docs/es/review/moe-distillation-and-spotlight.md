# Dos propuestas externas, leídas contra lo que este repositorio ya midió: una base MoE con destilación, y Spotlight Memory

**Escrito el 2026-10-04 a pedido del usuario.** Es un análisis y un plan, no un resultado. Nada de lo que sigue corrió
todavía, salvo que un reclamo nombre una corrida. Las dos fuentes se tratan como hipótesis: una nota de diseño pegada
por el usuario, y el post de Percepta *Spotlight Memory* (2026-10-02, [read] en
<https://www.percepta.ai/blog/spotlight-memory>). Un reclamo tomado de cualquiera de las dos se marca
**[read: source]** y no se repite como hecho hasta que una corrida acá lo instancia.

## 1. Lo que ya está medido y pesa sobre las dos

| hecho | corrida |
|---|---|
| Sobre la wiki generada de W9, un miembro 12B empata con el miembro E4B (9/40 contra 10/40); una vez enseñado, el E4B solo hace 37/40 | B3, B5 **[ran]** |
| Sin entrenar sobre documentos reales bajo el runtime servido, el 12B pierde contra el E4B, 11/44 contra 21/44 (2 : 12) | PAIR0 **[ran]** |
| Entrenado sobre el mismo corpus de documentos reales, el miembro 12B empata con el miembro E4B, 33/44 contra 34/44 (5 : 6) | PAIR1 **[ran]** |
| Los dos miembros se equivocan en filas distintas; cuando los dos coinciden, las respuestas incorrectas entregadas bajan de 9 a 3 (un conjunto ya visto, post-hoc) | nota de PAIR1 **[ran]**, hipótesis |
| La decodificación especulativa con el LoRA preserva la salida del miembro hasta cada corte, a 1,98× | F0c **[ran]** |
| Un embedding del pedido entero no puede separar quién escribe de qué se pregunta; los remitentes no vistos se pierden 120/120 | M2b **[ran]** |
| Un router que factoriza la tarea del contenido pasa: 0 de 600 textos ajenos servidos localmente, 0 de 480 pedidos legítimos perdidos | ROUTE0 **[ran]** |
| Los miembros de tarea abierta se rutean por el rol en el token, y se abstienen a través de su corpus | F2, M10 **[ran]**; ROUTE1 corriendo |
| Una página mostrada como los 8 mejores enunciados de la pregunta; una memoria operacional leída como una línea constante | PAGE0, H3 **[ran]** |
| `gemma-4-26B-A4B-it`: 30 capas, 128 expertos por capa, 8 activos; 15,37 GB en 4 bits; una línea flash (H1a: ¿el *dominio* concentra el ruteo?) escrita y **en pausa para la revisión del usuario** | [`flash-inference/00-analysis.md`](../flash-inference/00-analysis.md) [read] |
| Los nuevos miembros se entrenan sobre Gemma 4 E4B | decisión del usuario, 2026-09-25 (CLAUDE.md §0) |

Los hechos de esta tabla acotan cada propuesta de abajo. El más importante es este: **en las regiones que este proyecto
tiene, un modelo más grande no compró precisión, entrenado ni sin entrenar.** Cualquier propuesta cuyo retorno dependa
de un maestro o una base más fuerte tiene que mostrar ese margen primero, antes de construir nada sobre él.

## 2. La propuesta de MoE, punto por punto

### 2.0 Dos routers, dos granularidades — de acuerdo

El router de un MoE elige expertos feed-forward **por token y por capa**. Un experto es una FFN adentro de una capa,
sin atención propia y sin sentido afuera de su pila. **[read: source]**, y consistente con la configuración del 26B
de arriba. El router de este repositorio elige un miembro **por pedido**. La conclusión de la fuente se sostiene, y
es la que este diseño ya pone en práctica: un experto de MoE no se puede extraer como especialista, y un router no se
puede destilar en el otro. **Nada para implementar; la distinción entra al vocabulario.**

### 2.1 Un router destilado en una sonda sobre el estado oculto de la base — probar primero, y sólo para el hueco que queda

**Reclamo [read: source]:** una sonda lineal o un MLP chico sobre el estado oculto de una capa intermedia, etiquetado
offline por un maestro que corre cada adaptador candidato y se queda con el que un verificador (o la pérdida)
prefiere. El ruteo entonces cuesta casi nada (X-LoRA, LoRA-Switch, MoLE).

**Lo que dicen nuestros datos.** El problema de ruteo que la sonda resuelve ya está resuelto acá en las dos formas que
el sistema usa. Para miembros de tarea fija, ROUTE0 factoriza la tarea del contenido sin modelo y pasa. Para miembros
de tarea abierta, el rol nombra al miembro y el miembro se abstiene. Lo que queda abierto es más angosto:
- las **paráfrasis** de la tarea de un miembro, que ROUTE0 manda afuera por diseño (B3: 0/120 quedan locales);
- pedidos que llegan **sin rol**.

También hay una advertencia en M2b. Una representación del pedido *entero* — un embedding, o muy probablemente
también un estado oculto de una capa media — pone "el contenido del miembro más otra tarea" exactamente donde se
sienta "un remitente no visto más la tarea del miembro". Una sonda entrenada sin negativos difíciles de los dos tipos
aprendería el contenido.

**Lo que una sonda tiene y M2b no tenía:** supervisión. Las etiquetas pueden salir de nuestros propios verificadores:
la compuerta de citación (GATE0) y el calificador de cada región.

**Veredicto: probar primero, en dos pasos, el más barato primero.**
1. **P2a — margen.** ¿Un miembro contesta bien una paráfrasis de su tarea? (`email-full` y `desk-commitment` sobre el
   conjunto B3 de ROUTE0; una L4.) Si no, las paráfrasis se van bien como están, y una sonda que las retuviera local
   serviría respuestas incorrectas. La línea se detiene ahí.
2. **ROUTE2 — el brazo de la sonda**, sólo si P2a muestra que los miembros contestan paráfrasis. Los estados ocultos
   del E4B se extraen una vez en una L4. La sonda entrena en segundos, con negativos difíciles de los dos tipos de
   M2b. Tiene que mantener la seguridad de ROUTE0 (0 ajenos servidos localmente) **y** recuperar paráfrasis, puntuado
   sobre conjuntos frescos.

### 2.2 Destilación de especialistas, 26B → un LoRA sobre el E4B — con compuerta en un margen que el proyecto no vio

**Reclamo [read: source]:** el 26B, con o sin LoRA, es el maestro. Cada adaptador del E4B aprende de sus logits,
idealmente on-policy (GKD, MiniLLM). La familia comparte tokenizador. B2 **[ran]** confirma un único espacio de ids
para el E4B y el 12B; el 26B todavía no se chequeó.

**Lo que dicen nuestros datos.** La destilación transfiere lo que el maestro sabe y el alumno no. Acá el alumno
*entrenado sobre recorridos oráculo* igualó a todo modelo más grande medido (B3, PAIR1). La supervisión que dan
nuestros corpus ya es exacta: recorridos verificados, un enunciado citado, una calificación. Los targets blandos
agregan información donde el target duro es ruidoso o está subespecificado. Agregan poco donde es un recorrido
verificado. **La destilación no tiene maestro hasta que se muestre que un modelo más grande le gana al miembro E4B.**

**Veredicto: una corrida de margen lo decide.** En **TEACH0**, `gemma-4-26B-A4B-it` corre sin entrenar bajo el
runtime servido, con `--empty-thought` (la lección de PAIR0 para los modelos más grandes de Gemma 4). Se compara
contra el E4B pelado y contra `real-none-s0`, sobre las 52 filas de PAGE0. Necesita una sesión de A100. El 26B no
entra en una A100 en bf16, así que corre en FP8 o en 4 bits; eso es una segunda incógnita, y queda dicho.
- **Mata:** el 26B no le gana a `real-none-s0` (34/44), pareado, $p \lt 0,05$. Entonces no se construye ninguna
  destilación, y el 26B no se propone como base.
- **Pasa:** un piloto de destilación, con su propio brief. GKD sobre el corpus de una región, el alumno contra
  `real-none-s0`.

### 2.3 Podar expertos por dominio (REAP), y "un especialista es un LoRA más una máscara de expertos" — investigación; su primer paso ya existe

**Reclamo [read: source]:** los datos de calibración por dominio muestran qué expertos se activan. El resto se poda o
se enmascara; las podas de REAP mantienen la calidad en el dominio. Un miembro podría ser un LoRA más una máscara de
expertos, cambiado al cambiar la máscara del router. La fuente misma llama a esto territorio sin explorar.

**Lo que dicen nuestros datos.** La medición de la que parte REAP — estadísticas de activación de expertos por
dominio — es exactamente **H1a** de la línea flash: ¿el dominio concentra el ruteo del 26B (entropía por capa, los
expertos que cubren el 80 % de las activaciones, Jaccard dentro del dominio contra Jaccard entre dominios)? H1a está
escrita, con compuerta, no necesita entrenamiento, y está en pausa para la revisión del usuario. También le da su
respuesta a la línea flash.

**Veredicto:** nada de trabajo nuevo hasta que corra **H1a**, y H1a corre sólo con la aprobación del usuario para
reanudar la línea flash. Las máscaras más el cambio de LoRA se quedan como investigación detrás de H1a y H1b.
Necesitan su propio benchmark y un motor de servido con máscaras de expertos por pedido, que vLLM no ofrece **[read]**.

### 2.4 El 26B como base de cada miembro — no ahora; es decisión del usuario, y la evidencia no la pide

**Reclamo [read: source]:** el cómputo por token es cercano al del E4B (unos 4B activos), en 15–17 GB en 4 bits más la
caché KV. Entra en un diseño de "base en flash, adaptadores en RAM", y una base más fuerte suele ganarle a cualquier
destilación.

**Lo que dicen nuestros datos.**
- La decisión es del usuario (E4B, 2026-09-25).
- El tamaño no compró precisión en ninguna región medida (§1).
- En la Mac de 16 GB, 15,37 GB de pesos no dejan lugar para la caché KV. El 12B ya estaba ajustado ahí
  (MAC2 **[ran]**). La línea flash es precisamente el plan para que eso entre, manteniendo cacheado cerca del 60 % de
  los expertos.

**Veredicto: no se propone** hasta que TEACH0 pase. Si pasa, el cambio va al usuario como decisión, con la corrida.

**Dos advertencias de la fuente, adoptadas como reglas para cualquier LoRA de MoE:**
- **Ubicación.** Sólo atención y expertos compartidos, no expertos ruteados. La Fase 0 ya propone sólo-atención.
- **El router.** Congelarlo, y medir la entropía de ruteo antes y después de entrenar.

## 3. Spotlight Memory — la arquitectura no se puede adoptar; tres de sus ideas se pueden probar sobre lo que existe

**Qué es [read: source].** Una capa de mezcla de secuencia para el preentrenamiento. Claves y consultas mapean a
direcciones en una grilla 2D de celdas. Cada lectura o escritura toca una vecindad fija de 3×3 a través de un kernel
de protuberancia suave. Las celdas son estados DeltaNet, asignados en la primera escritura. La memoria crece con el
contexto, y el acceso cuesta una constante por token. El ruteo (2D) está separado del contenido (de alta dimensión).
Actualizar una clave reemplaza su valor, así que la tasa de valores obsoletos sobre claves reescritas es cero.

**Por qué no se puede adoptar acá.** Es una arquitectura entrenada desde cero: modelos de 140M–670M preentrenados
sobre FineWeb-Edu. Este proyecto afina adaptadores sobre una base Gemma fija y no entrena nada desde cero. **Ninguna
parte de la capa se puede agregar a Gemma 4 E4B sin preentrenar.**

**Qué mapea sobre la memoria de este proyecto, y cómo se puede probar cada una:**

| propiedad de Spotlight | contraparte de este proyecto | estado | la prueba barata |
|---|---|---|---|
| la memoria crece, el acceso por paso es constante | la biblioteca y la memoria operacional crecen; un turno lee una línea de estado (H3) y una página muestra 8 enunciados (PAGE0) | medido **[ran]** para el acceso; el crecimiento no se forzó | — |
| **separar el ruteo del contenido** | ROUTE0 (tarea contra contenido); la biblioteca direcciona por id y ancla, su contenido es el enunciado | medido **[ran]** para el router | — |
| **actualizar una clave reemplaza su valor — tasa obsoleta 0** (su variante MQAR de "olvido") | un `put` de opmemory sobreescribe una clave; un enunciado de biblioteca se puede editar sin reentrenar | **nunca medido**: el brazo 5 del hito 7 del PLAN, *editar sin reentrenar*, no corrió | **EDIT0**, abajo |
| direccionamiento aprendido, de baja dimensión (2D alcanza) | la etapa R1 del radar (`MEMORY.md` §2.2): una proyección aprendida a un $d$ chico, diseñada y no construida; su brief prueba $d$ = 64 | no construida | una vez que R1 exista, probar $d \ll 64$ |
| recuerdo a 16× el largo de entrenamiento | no aplica: este diseño mantiene el contexto corto a propósito | — | — |

**EDIT0 — la prueba de edición, la propiedad de sobreescritura de Spotlight sobre nuestra memoria.** Se hace una copia
de `knowledge/hazwaste-regs` en la que se cambia el número en ~20 enunciados de soporte de las filas de PAGE0, y nada
más. A `real-none-s0` se le preguntan esas filas bajo el runtime servido; nunca vio esta biblioteca, así que no hay
reentrenamiento que deshacer.
- **Pasa** si ≥ 90 % cita el valor **nuevo** del enunciado editado y como mucho 1 contesta el valor viejo (obsoleto).
- **Falla** si el miembro escribe valores desde sus pesos.
- Una sesión de L4, sin entrenamiento. También cierra el brazo 5 del hito 7, abierto desde el 2026-09-19.

Al lado, a costo cero de GPU: una prueba de que un `put` de memoria operacional sobre una clave existente hace que el
próximo `get` devuelva el valor nuevo, y sólo ese.

## 4. El plan, en orden

Cada paso está pre-registrado con un brief antes de correr, compra primero la falsificación más barata, y detiene la
línea a la que pertenece si falla.

| paso | qué | costo | detiene la línea si |
|---|---|---|---|
| 1 | **EDIT0** — editar sin reentrenar (la propiedad de sobreescritura de Spotlight); prueba de sobreescritura de opmemory | una L4 · cero GPU | el miembro escribe valores obsoletos: la memoria no es donde vive el conocimiento |
| 2 | **P2a** — ¿un miembro contesta paráfrasis de su tarea? | una L4 | los miembros fallan las paráfrasis: se van bien como están, y no se construye ninguna sonda |
| 3 | **ROUTE2** — una sonda de router sobre el estado oculto del E4B, con los negativos difíciles de M2b, sobre conjuntos frescos | una L4 + segundos | pierde la seguridad de ROUTE0, o no recupera ninguna paráfrasis |
| 4 | **TEACH0** — ¿`gemma-4-26B-A4B-it` le gana al miembro E4B sin entrenar? | una A100 | no: ninguna destilación, ningún base 26B |
| 5 | **H1a** — ¿el dominio concentra el ruteo del 26B? (el primer paso de la línea flash; los datos que necesita REAP) | horas de una GPU | **sólo con la aprobación del usuario para reanudar la línea flash** |
| — | diferido: destilación (después de TEACH0), máscaras de expertos más cambio de LoRA (después de H1a/H1b), direccionamiento aprendido de $d$ chico (después de R1) | — | — |
| — | no hecho: implementar la capa de Spotlight (necesita preentrenamiento); extraer expertos de MoE como especialistas (no son especialistas) | — | — |

**Decisiones que son del usuario:**
- si reanudar la línea flash (paso 5);
- cualquier cambio de base, que sólo seguiría a un TEACH0 que pase.
