# La memoria — implementación

> **El LoRA no es el libro de texto; es el especialista que sabe usar la biblioteca.**
> No memoriza ningún dato: aprende **a qué estante ir, qué ficha abrir y qué paso
> ejecutar después.**

Esta es la especificación de implementación de la memoria por experto, el núcleo de la versión 1.0. El
*por qué* — diez hallazgos medidos, cinco estrategias de trayectoria, las preguntas para quien revise — está en
[`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md); este documento es el *qué construir*. La
explicación que implementa es la del usuario, 2026-09-19. Marcadores de estado como en todas partes acá: **[ran]**
medido en este repositorio, **[read]** leído en el código fuente o en un paper, **[spec]** decidido y todavía no
construido. **Nada de lo que hay en este documento está construido todavía**; el §10 dice en qué orden se va a
construir, y qué puede detenerlo.

Cinco piezas:

| # | pieza | una línea | ¿neuronal? |
|---|---|---|---|
| 1 | **la biblioteca** | notas markdown pequeñas en dos estantes — el arnés operativo y la wiki enciclopédica | no — texto en git |
| 2 | **el radar** | embeddings comprimidos a un subdominio: *para qué es esta nota*, *qué define* | un encoder chico, congelado al servir |
| 3 | **el lenguaje** | tres verbos que el experto puede escribir: `<search>`, `<open>`, `<calc>` | no — una gramática |
| 4 | **el LoRA** | entrenado sobre el *hábito de navegación*, nunca sobre los datos | sí — la única parte entrenada |
| 5 | **el runtime** | un árbitro chico en Python: pasa las páginas, aplica reglas locales, hace cumplir el orden | no — puro software |

> **[MARCADOR DE ILUSTRACIÓN — `docs/img/memory-five-pieces.png`]**
> *Un único diagrama ancho, de izquierda a derecha, estilo técnico plano, fondo claro. A la izquierda del todo, una
> biblioteca con dos estantes rotulados: el estante de arriba "Operational harness" tiene fichas unidas por
> flechas en línea (un procedimiento); el estante de abajo "Encyclopedic wiki" tiene fichas dispuestas en
> árbol. En el medio, una pequeña antena de radar rotulada "radar — embeddings of this subdomain only"
> que barre la biblioteca e ilumina tres fichas. A su derecha, una figura en un escritorio rotulada
> "LoRA — the specialist" sosteniendo exactamente tres herramientas rotuladas `search`, `open`, `calc`. Debajo
> de todo, una banda fina rotulada "runtime — referee" con tres íconos: una página siendo pasada, un
> sello que dice "site rule applied", y una barrera que dice "requires step 1". Sin robots, sin
> cerebros, sin redes neuronales brillantes: el punto de la imagen es que cuatro de las cinco piezas no son
> neuronales.*

---

## 1. La biblioteca — dos estantes de markdown

Una carpeta por subdominio, un archivo por nota, **menos de media página** (límite duro: 150 tokens de
cuerpo — una nota tiene que entrar en la atención de un 4B con margen de sobra, y una nota larga es dos notas).

```
knowledge/
  nursing-iv/
    harness/                     # how it is done
      primary-infusion.md            ← a procedure: the skeleton, step titles only
      primary-infusion/
        03-cleanse-catheter-cap.md   ← a step
        04-assess-patency.md
    wiki/                        # what it is, which formula applies
      asepsis/scrub-the-hub.md
      rates/gravity-drip-rate.md
    site/                        # a ward's adaptations — overrides only (§5.2)
      ward-7b.md
```

### 1.1 El arnés operativo — *¿cómo se hace?*

Notas tipo receta. Sus enlaces son **fijos y tipados**, y son el flujo de control:

| enlace | se lee como | lo usa |
|---|---|---|
| `requires` | *antes de esto tiene que haberse hecho …* | el experto — y **el runtime, como guarda** (§5.3) |
| `next` | *el paso que sigue es …* | el experto, para avanzar |
| `uses` | *para este paso, consultar …* (una nota de la wiki, o un sub-procedimiento) | el experto, para hacer una parada en la wiki |

```markdown
---
id: nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap
shelf: harness
kind: step                       # procedure | step | check
title: Cleanse the catheter cap before attaching tubing
when: You are about to connect a syringe or tubing to a patient's IV port.
what: Disinfection of the IV port's cap with an alcohol pad or scrub hub.
requires: [nursing-iv/harness/primary-infusion/02-safety-steps]
next: nursing-iv/harness/primary-infusion/04-assess-patency
uses: [nursing-iv/wiki/asepsis/scrub-the-hub]
slots: {seconds: 5}
source: Nursing Skills (Open RN), ch. 23 — CC BY 4.0
---
Vigorously cleanse the catheter cap for at least {{seconds}} seconds and allow it to dry.
```

Una nota de **procedimiento** es sólo un esqueleto — ~~los títulos~~ las **etiquetas** de sus pasos, en orden (el slug del id de cada paso: `20 cleanse cap`), y el id del primer paso. *Enmendado por W1 **[ran]**: treinta y dos títulos numerados son 230 tokens contra el límite de 150 de este mismo documento; las etiquetas son 98.* El
detalle vive en los pasos. Leer una checklist de 32 pasos de una sola vez y *recorrerla* son tareas
distintas, y la segunda es la que se está construyendo.

### 1.2 La wiki enciclopédica — *¿qué es, qué fórmula aplica?*

Notas con forma de árbol, de lo general a lo específico, unidas por `parent` → `children`. Existen para **clasificar
en qué caso estás antes de calcular**:

```markdown
---
id: fluids/wiki/pipe-flow/turbulent/friction-factor
shelf: wiki
kind: formula                    # concept | formula | table
title: Friction factor in turbulent pipe flow
when: Reynolds number above 2300 and you need the Darcy friction factor.
what: The Swamee–Jain correlation for f from Reynolds number and relative roughness.
parent: fluids/wiki/pipe-flow/turbulent
children: []
slots: {a: 5.74, b: 3.7}
---
f = 0.25 / ( log10( eps/({{b}}·D) + {{a}}/Re^0.9 ) )^2
```

### 1.3 Dos campos que lleva cada nota, y por qué

`when:` — *para qué situación es esta nota.* `what:` — *qué concepto define.* Estas dos
líneas, no el cuerpo, son lo que indexa el radar (§2). Las escribe quien escribe la nota,
con las palabras que usaría un practicante para preguntar.

### 1.4 Huecos (`slots`)

`{{seconds}}`, `{{a}}` — valores que el runtime completa cuando sirve la nota. Son cómo entran las tres
fuentes de variación sin tocar el texto: **el default del libro de texto** (`slots:` en la
nota), **la regla de un sitio** (§5.2), y, sólo en entrenamiento y evaluación, **un valor sorteado para un
caso** (§4.1).

### 1.5 La biblioteca se lintea, como el código **[spec]**

`python -m memory.lint knowledge/<subdomain>` hace fallar el build cuando: un enlace no resuelve; una
cadena de `next` tiene un ciclo o un paso no pertenece a ningún procedimiento; un cuerpo supera el límite de tokens; un
`{{slot}}` se usa y no está declarado; falta un `when:` o un `what:`; dos notas de un mismo subdominio
tienen el mismo `when:`. El conocimiento que vive en git recibe las mismas compuertas que recibe el código.

---

## 2. El radar — embeddings comprimidos a un subdominio

No es un motor de búsqueda general, ni un modelo de embeddings grande construido para saber de historia, cultura pop y
cocina al mismo tiempo.

### 2.1 Qué se indexa

Por nota, dos vectores: $e_{\text{when}}(n)$ y $e_{\text{what}}(n)$. Un índice **por subdominio** —
el router ya ubicó el pedido en el subdominio, así que el radar nunca busca afuera de él.
La biblioteca de un subdominio es unos cientos de notas: el índice es una matriz, la búsqueda es un producto de matrices,
no hay librería ANN ni servidor.

### 2.2 Por qué "compresión" es la palabra correcta — la hipótesis **[spec]**

En un dominio cerrado el vocabulario tiene un significado funcional exacto. *Patency*, *drip factor*, *relative
roughness* apuntan cada uno a una sola cosa. Un encoder general gasta la mayoría de sus dimensiones en distinguir una
receta de un soneto — distinciones que nunca ocurren adentro de *IV therapy*. Entonces un **vector muy chico,
o un encoder liviano afinado a la jerga, debería alcanzar** para separar las dos únicas intenciones que
importan acá: *para qué situación es esto*, y *qué define esto*.

Esa es una hipótesis con una prueba barata, y está construida en dos etapas para que la prueba venga primero:

| etapa | el radar | costo |
|---|---|---|
| **R0** | un encoder chico de fábrica de la familia del pool (`Qwen3-Embedding-0.6B` **[read]**), todo texto embebido bajo una instrucción — *representá la situación para la que es esto* | ninguno: sin entrenamiento |
| **R1** | los vectores de R0 pasados por una **proyección aprendida a una dimensión chica** $d$ (64–128), entrenada sólo sobre este subdominio | minutos |

**Los datos de entrenamiento de R1 son gratis.** Los recorridos oráculo que entrenan el LoRA (§4) ya dicen, para cada
paso, *esta consulta tendría que haber encontrado esta nota*. Esos pares (consulta, nota necesaria), con las otras
notas del subdominio como negativos, son un conjunto de entrenamiento contrastivo que nadie tiene que etiquetar:

$$\mathcal L = -\log \frac{\exp(\langle W e(q), W e_{\text{when}}(n^+)\rangle / \tau)}{\sum_{n \in \mathcal N}\exp(\langle W e(q), W e_{\text{when}}(n)\rangle/\tau)}, \qquad W \in \mathbb R^{d \times D},\ d \ll D .$$

**Lo que mostraría que la afirmación de compresión es cierta:** el recall@3 de la nota necesaria, sobre recorridos
retenidos, quedándose plano a medida que $d$ baja de $D$ a 64 — y R1 con $d = 64$ ganándole a R0 a ancho completo en
confusiones *dentro del mismo tema*, que es donde la recuperación plana falló antes (F9 del documento de diseño).
**Lo que mostraría que es falsa:** el recall cayendo con $d$, o R1 no mejor que R0. Las dos se reportan.

### 2.3 Puntuar una búsqueda

$$s(n \mid q) = \langle e(q), e_{\text{when}}(n)\rangle + \beta\,\langle e(q), e_{\text{what}}(n)\rangle, \qquad \text{devolver el top } k = 3 .$$

Una búsqueda puede restringirse a un estante: `<search shelf=harness>` para "encontrame el protocolo",
`<search shelf=wiki>` para "qué fórmula". $\beta$ y los términos condicionados por la trayectoria del
documento de diseño (§4, S4) son brazos sobre esta línea de base, no parte de ella.

**Dos priors en contra de la viveza [read]**, traídos acá para que no se olviden: una jerarquía de memoria
perdió contra búsqueda léxica plana en un benchmark anterior de este workspace, e indexar *para qué sirve*
al lado de *qué es* no cambió nada en el propio de `evolving-memory` (acc@1 80 % con cualquier peso, n = 10).
Así que R0 con un único vector `when`, y la búsqueda léxica plana, se quedan los dos como líneas de base, y un nulo
se reporta como nulo.

**El mismo encoder es el del router** (hito 2, brazo 2): un subdominio es una región de un espacio —
lo que cae adentro se rutea al miembro, y lo que el miembro busca se encuentra ahí.

---

## 3. El lenguaje — tres verbos, y nada más

El experto puede escribir exactamente tres comandos en su propio texto. La generación se para en cada tag de cierre;
el runtime escribe el resultado **inline, justo después del tag**, y devuelve el turno — la forma en
la que ya está entrenado y servido cada experto de este pool (0,992 así contra 0,808 a través de
mensajes `tool_calls` **[ran]** P55).

| verbo | lo que escribe el experto | lo que responde el runtime |
|---|---|---|
| **search** | `<search>situation or doubt</search>` | `= 3 notes` y, por nota, `[id] kind · title — when: …`. **Sólo títulos y líneas `when` — nunca cuerpos** |
| **open** | `<open>id</open>` | el cuerpo de la nota, con los huecos completados y las reglas locales aplicadas, y después sus enlaces: `next …` · `requires …` · `uses …` (en el estante wiki `parent …` · `children …`; todo enlace salvo `next` lleva el título de la nota junto a su id — W2 **[ran]**) |
| **calc** | `<calc>500 * 20 / (4 * 60)</calc>` | `= 41.6667` — así el modelo **nunca hace aritmética de memoria**, donde siempre falla (adaptador solo 4/40, adaptador + calculadora 40/40 **[ran]** P5–P7) |

```
<search shelf=harness>start a primary IV infusion by gravity</search>= 3 notes
  [k3f] procedure · Primary IV solution administration — when: a provider orders IV fluids
  [9c1] procedure · Secondary IV solution administration — when: adding a piggyback medication
  [77e] procedure · Discontinuing an IV — when: an IV is to be removed
<open>k3f</open>= Primary IV solution administration — 32 steps. First step: a01
  next a01
```

Reglas de la gramática:

- **Seguir un enlace es `<open>` sobre su id.** No hay un cuarto verbo.
- **Los ids que se le muestran al experto son cortos y opacos, y se sortean de nuevo por conversación.** El experto
  no puede aprender "para la limpieza, abrir `k3f`"; tiene que leer lo que devolvieron `<search>` y `<open>`.
  La navegación de memoria funciona hasta que la biblioteca cambia, y entonces falla en silencio.
- **Los errores son observaciones, no excepciones:** `= ERROR: no note k3x in this conversation`,
  `= ERROR: requires a02 first` (§5.3). El experto los lee como cualquier otro resultado.
- **Los verbos se enseñan, así que quedan congelados con el release** — nombres de los tags, orden de los atributos,
  renderizado de los resultados. A un miembro entrenado en otro idioma se le enseñan los verbos de ese idioma
  (`<buscar>`, `<abrir>`, `<calcular>`); el manifiesto del release registra la versión de la gramática.
- **Los presupuestos son del runtime:** $k = 3$ notas por búsqueda, el tope de tokens por nota, como mucho ~~24~~ **48**
  aperturas y 12 búsquedas por tarea. Un recorrido que llega a un tope termina como *no contestado* y el pedido
  va hacia la frontera.
  *Enmendado por W2 **[ran]**: el procedimiento más largo de la primera biblioteca tiene 32 pasos, y un
  tope por debajo de la profundidad del propio corpus mide el tope.*

---

## 4. El LoRA — entrenar el hábito de navegación

**Lo que se enseña es el método de trabajo, nunca los datos.**

### 4.1 Casos sintéticos cuyos datos siempre cambian

Cada caso de entrenamiento sortea sus propias constantes: un líquido inventado para este ejercicio (`TD-78`, densidad
882,3), un tiempo de permanencia local de 15 segundos en vez de 5, una correlación cuyos coeficientes difieren de
los del libro de texto. Los valores se entregan **sólo a través de los huecos de la nota**, así que el modelo no
puede memorizar una respuesta — *está obligado a abrir la nota para ver el número*. Esto no es un detalle cosmético:
sobre una tabla fija de 14 valores un control **sin ninguna herramienta de búsqueda** puntuó 27/30, porque 600
ejemplos memorizan 14 números **[ran]** P15, P21. El generador verifica, por caso, que ningún valor de hueco aparezca
en el enunciado de la tarea.

### 4.2 La coreografía

1. Leer el problema.
2. `<search shelf=harness>` para encontrar el protocolo.
3. `<open>` el protocolo.
4. Si un paso dice que `uses` algo — *verificar el régimen de flujo* — hacer una parada en la wiki:
   `<open>` esa nota, o `<search shelf=wiki>` si el paso sólo nombra la necesidad.
5. Mandar los números a `<calc>`.
6. Seguir `next` hasta que el procedimiento termine, y después responder.

### 4.3 Cómo un caso se vuelve un ejemplo de entrenamiento **[spec]**

Para cada caso generado el **oráculo conoce el recorrido** — qué notas necesita la solución, en qué
orden. El corpus es ese recorrido renderizado como el propio turno del experto, comandos y resultados inline
juntos, **byte a byte como se va a servir**: el generador *llama* al runtime para renderizar cada
observación en vez de imitar su salida, porque una copia fue lo que se desvió la última vez (71 llamadas
rechazadas que parecían física **[ran]** P38).

```
[user]      A provider orders 500 mL of IV fluid over 4 hours by gravity; the tubing's drop factor
            is 20 gtt/mL. Set the rate.
[assistant] <search shelf=harness>set the rate of a primary IV infusion by gravity</search>= 3 notes
              [k3f] procedure · Primary IV solution administration — when: a provider orders IV fluids
              …
            <open>k3f</open>= … First step: a01
            …
            <open>a26</open>= Set the infusion rate based on the provider order. For gravity: calculate
              drops per minute.  uses q81 · next a27
            <open>q81</open>= Gravity drip rate: drops/min = volume (mL) × drop factor (gtt/mL) ÷ time (min).
            <calc>500 * 20 / (4 * 60)</calc>= 41.6667
            Set the roller clamp to 42 drops per minute.
```

Cuatro propiedades que el corpus tiene que tener, cada una de una medición:

| propiedad | porque |
|---|---|
| **distractores** en cada resultado de `<search>`, y algunos casos donde **no aplica ninguna nota** — el recorrido enseñado termina en *no está en mi biblioteca*, que el proxy convierte en la frontera | un especialista se equivoca con confianza un paso afuera de su región: 30/30 adentro, 1/20 en familias hermanas **[ran]** P14 |
| **cada profundidad que va a servir el experto** — recorridos de una, dos, cinco aperturas; procedimientos entrados por el primer paso y por el medio | un corpus con una sola dificultad enseña un piso: sobre-resuelve 18/18 por debajo de su profundidad de entrenamiento **[ran]** P45 |
| **procedimientos hermanos retenidos** cuyas notas están en la biblioteca y cuyos recorridos nunca se entrenaron | esa es la afirmación: *la biblioteca extiende la región sin reentrenar* |
| el bloque de herramientas, el system prompt y el formato del resultado **exactamente como se sirve** | un miembro es lo que su corpus le enseñó: 2/32 → 19/32 turnos que llaman a una herramienta bajo su propio prompt **[ran]** P63 |

### 4.4 Lo que "memoria" **no** significa acá

El adaptador no guarda hechos sobre el subdominio y la biblioteca no guarda comportamiento. Un hallazgo que el
diseño tiene que sobrevivir: un modelo chico no sigue un procedimiento que sólo lee — base + un
documento de procedimiento hizo 0 llamadas a herramientas en 351/351 mensajes **[ran]** P61 — que es exactamente por qué
*seguir lo que lee* es lo que entrena el adaptador, y lo único.

**Y la otra mitad de ese hallazgo, medida sobre texto real [ran] M5:** el mismo tipo de base chica
*responde preguntas sobre* una nota que sólo lee, y muy bien — el orden de pasos y el paso siguiente
en tres listas de verificación IV pasan de 29/48 a libro cerrado a **45/48 con la nota abierta**, y
una cantidad que cambió el protocolo de una unidad de **0/12 a 12/12**, sin entrenar nada. La
comprensión está; lo que falta es *actuar bajo un procedimiento*. Así que la parte entrenada de esta
memoria se gana su lugar sólo en **recorridos** — varios pasos, herramientas, un chequeo que habilita
una acción — y nunca en preguntas y respuestas sobre una nota. Todo brazo desde W5 lleva la línea de
base que lo dice: *la base pelada con la nota del oráculo abierta.*

---

## 5. El runtime — el árbitro de software

Python puro, sin modelo, unos cientos de líneas, adentro del proxy. Hace el trabajo entre un comando
y el siguiente.

### 5.1 Pasa las páginas

Ante `<open>id</open>`: encuentra el archivo, completa los huecos, renderiza el cuerpo y los enlaces, los escribe
después del tag, devuelve el turno. Este es el loop de modo corpus que el pool ya corre — parar en el tag de
cierre, inyectar `= result`, continuar (`training/harness/accept_rank.py::run_chain`) — con una nueva función de
respuesta que tiene **estado por conversación**: el mapa de ids, las notas abiertas hasta ahora, los presupuestos.

```
memory/
  notes.py      load, validate and lint a subdomain's library
  index.py      build and query the radar; exhaustive cosine; R0 and R1
  layers.py     textbook → site → case resolution of slots
  guard.py      conformance: `requires` before the step it guards
  runtime.py    the three verbs; ids; budgets; the walk log
```

### 5.2 Aplica reglas locales automáticamente

Si un hospital o un cliente tiene su propia regla — *"acá limpiamos durante 20 segundos, no 15"* — es
una línea en la capa de sitio:

```markdown
---
site: ward-7b
overrides:
  nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap: {seconds: 20}
---
```

El runtime sustituye el valor **antes** de que la nota llegue al experto, y lo marca:
`…for at least 20 [site] seconds…`. **El modelo nunca ve el conflicto; lee la regla ya
resuelta.** Orden de resolución, gana el más cercano: *caso* (sólo entrenamiento y evaluación) → *sitio* →
*libro de texto*. Es determinista y auditable, y le ahorra al experto lo único que el registro
dice que hace peor — reconciliar dos cosas que leyó.

### 5.3 Vigila que no haga trampa — la guarda de conformidad

Si el paso 4 dice `requires: step-1` y el experto intenta correr el paso 4 sin haber abierto nunca
el paso 1, **el runtime corta la ejecución y reporta el error — sin necesitar saber si
la respuesta final era correcta.** Eso es un verificador que no consulta ninguna clave de respuestas y que el
loop de entrenamiento nunca ve, que es lo que tiene que ser cualquier señal que se use para aceptar o rechazar una
respuesta; su precedente acá es el análisis dimensional sobre una cadena de física, que atrapa una relación
inventada sin saber el número **[ran]** P22.

**[spec]** Dos modos. `strict` — el default en 1.0: la primera violación termina el recorrido como *no
contestado* y el pedido va hacia la frontera. `recover` — la violación se escribe inline como una
observación (`= ERROR: requires a02 first`) y el experto puede volver atrás; si los expertos chicos *efectivamente*
recuperan es un brazo, no un supuesto.

### 5.4 Registra el recorrido

Una línea JSON por comando: verbo, argumento, ids devueltos, nota abierta, huecos resueltos y de qué
capa, veredicto de la guarda, tokens. Es de lo que se calcula cada medición del §9, y la materia
prima de la memoria episódica del documento de diseño (§7) — registrada en 1.0, consolidada después.
Si el registro de un cliente puede guardar el *contenido* de una nota o sólo sus *formas* es una configuración,
con formas como default.

---

## 6. En operación — una tarea, de punta a punta

![Siete paneles numerados unidos por una línea, como un mapa de subte: un pedido, una búsqueda que ilumina tres fichas, un procedimiento que se abre, la línea que recorre el estante del arnés, un desvío hacia el estante de la wiki y de vuelta, una calculadora, la respuesta.](../img/memory-walkthrough.png)

*Una tarea, de punta a punta. El desvío del arnés a la wiki y de vuelta es el punto.*

1. **Llega la tarea:** *"Infuse 500 mL over 4 hours by gravity; drop factor 20 gtt/mL."*
2. **El experto consulta su radar:** `<search shelf=harness>start a primary infusion</search>`.
3. **El radar responde:** `[k3f] procedure · Primary IV solution administration`.
4. **El experto recorre el arnés:** `<open>k3f</open>`, y después paso a paso siguiendo `next`. En *set
   the rate* el paso `uses` una nota de la wiki.
5. **El experto hace una parada en la wiki:** `<open>q81</open>` — la fórmula del goteo.
6. **El experto delega la aritmética:** `<calc>500 * 20 / (4 * 60)</calc>` → `41.6667`.
7. **El experto sigue adelante:** sigue `next` hasta el siguiente paso del arnés, hasta que la tarea se cierra.

**La ganancia.** Si el protocolo cambia mañana, **se edita un archivo markdown en git**. El LoRA no
se reentrena, porque lo que aprendió fue a obedecer los enlaces y leer las notas; el conocimiento
operacional y factual vive afuera de él, estructurado y versionado.

## 7. Qué se puede editar sin reentrenar — y qué no

| cambio | ¿reentrenar? | por qué |
|---|---|---|
| un valor, una redacción, una regla de sitio | **no** | el experto lo lee de nuevo cada vez |
| un paso nuevo adentro de un procedimiento; un `next` reordenado | **no** | sigue enlaces, no los memoriza |
| un procedimiento nuevo de un tipo sobre el que se entrenó (un hermano) | **no — esta es la afirmación que prueba el §4.3** | |
| una rama nueva de la wiki | **no** | |
| un **verbo** nuevo, un **tipo de enlace** nuevo, un **kind** de nota nuevo, un **renderizado** de resultados cambiado | **sí** | esa es la gramática que se le enseñó al adaptador (§3) |
| un procedimiento de una *forma* que nunca vio — ramas, loops, esperas | **sí, probablemente** | la coreografía es lo que está en los pesos |

El segundo grupo es chico a propósito. Es el número de versión de la gramática.

## 8. Qué registra un release

Un miembro es su corpus, su biblioteca y la forma en que se le enseñó a recorrerla. El manifiesto
(`releases/*.json`) gana: el hash y la ruta de la biblioteca, el id del encoder del radar, la etapa (R0/R1) y
el hash del índice, la versión de la gramática, el modo de la guarda. Volver a servir un release vuelve a chequear
todos esos, tal como ya vuelve a chequear el adaptador y el corpus.

## 9. Cómo se mide

Por comando, no sólo en la respuesta — un lector que tuvo suerte sobre una nota vacía es un caso que un
puntaje final no puede ver:

| métrica | pregunta |
|---|---|
| **recuperada** | ¿estaba la nota necesaria entre las tres que devolvió `<search>`? |
| **abierta** | ¿la abrió el experto? |
| **usada** | ¿su valor llegó a un paso posterior? (`training/physics/result_use.py` — el instrumento que encontró que el experto de fluidos busca una densidad, 882,3, y la multiplica por 1359,7 **[ran]**) |
| **conforme** | ¿el recorrido respetó cada `requires`? |
| **correcta** | el veredicto del verificador |
| **tokens** | un recorrido no es gratis |

Los brazos y su orden están en el hito 7 de [`PLAN.md`](PLAN.md). Dos bancos de prueba con trabajos distintos: **la
mecánica de fluidos** es el instrumento — un oráculo exacto, contenido inmemorizable por construcción; **los
procedimientos de enfermería** (*Nursing Skills* de Open RN, CC BY 4.0) son la región — texto que nadie acá generó, y
una capa de sitio real.

## 10. Orden de construcción para 1.0 **[spec]**

Cada paquete termina en una compuerta, entra en una sesión de Colab de sesenta minutos donde necesita GPU, y
**ningún modelo corre en la máquina del usuario**.

| # | paquete | ¿necesita un modelo? | compuerta |
|---|---|---|---|
| W1 | `memory/notes.py`, el lint, y la primera biblioteca: IV therapy, tres procedimientos como esqueleto + pasos, una wiki chica | no | el lint pasa; existe cada recorrido que necesita el oráculo — ✅ **[ran] 2026-09-19**: 94 notas, 0 hallazgos, 72/72 recorridos ([`BRIEF`](../../results/M7-W1-library-20260919/BRIEF.md)) |
| W2 | `memory/runtime.py`, `layers.py`, `guard.py` sobre el loop de modo corpus existente | no | **cada recorrido oráculo pasa por el runtime**, 0 rechazos, la guarda en silencio; un recorrido que viola se corta — ✅ **[ran] 2026-09-19**: 72/72 recorridos, 949 comandos (72 búsquedas, 865 aperturas, 12 cálculos), 0 rechazados, 0 mal formados, la guarda en silencio; tres recorridos que violan se cortan en `strict` y siguen en `recover`; `<search>` es léxico hasta W3 ([`BRIEF`](../../results/M7-W2-runtime-20260919/BRIEF.md)) |
| W3 | `memory/index.py`, radar **R0**, al lado de una línea de base léxica | Colab, minutos | recall@3 de la nota necesaria sobre las consultas del oráculo; la línea de base reportada al lado — 🔶 **construido, corrida R0 pendiente [ran] 2026-09-19 (cero GPU):** las consultas de W2 acá son nulas (una nota sale primera para su propio `when:`), así que el radar se mide sobre un conjunto escrito después de congelar el diseño — **P**, una paráfrasis de cabecera por nota (94, solapamiento medio de palabras con el objetivo 0,039), la compuerta; **E**, los 72 enunciados → la primera nota del recorrido, al lado. Recall@3 de la base léxica: **0,064** en P, 0,125 en E — hay margen, y un piso por construcción, así que la compuerta lleva además un estándar absoluto: R0 gana el par **y** recall@3 ≥ 0,80 ([`BRIEF`](../../results/M7-W3-radar-r0-20260919/BRIEF.md)) |
| W4 | el generador de corpus: huecos inmemorizables, ids opacos, distractores, callejones sin salida, mezcla de profundidades | no | ningún valor de hueco en ningún enunciado; ningún recorrido evaluado en el corpus |
| W5 | **el brazo que mata** — dos adaptadores sobre un subdominio, con y sin la biblioteca, puntuados sobre un procedimiento hermano retenido, **como recorridos, no como preguntas**; al lado, la *base pelada con las notas del oráculo abiertas* | Colab, dos sesiones | con-biblioteca le gana a sin-biblioteca, pareado — **y le gana a la base sin entrenar leyendo las mismas notas**, que en preguntas y respuestas ya está en 45/48 **[ran]** M5 — o la memoria se detiene acá a este tamaño de modelo |
| W6 | radar **R1**, la afirmación de compresión | Colab, minutos | recall@3 plano a medida que $d$ baja a 64 |
| W7 | editar una nota después de entrenar; la respuesta tiene que seguir a la biblioteca | Colab, minutos | la sigue |

**Lo que podría haberlo detenido, y no lo hizo [ran] 2026-09-19.** El brazo 0b del hito 7 preguntó si el
experto de fluidos usa el resultado de una herramienta cuando le llega inline, como le enseñó su corpus — había
puntuado 11 de 90 a través de mensajes `tool_calls`, buscando una densidad y después multiplicándola por un número
propio. Servido inline: **90 de 90**, 79 : 0 pareado, ningún caso evaluado en su corpus. **Un 3B sí usa
lo que lee, cuando lo lee de la forma en que se le enseñó**, y esta memoria entrega todo a través de
exactamente ese canal. Lo que queda sin probar es la afirmación misma — W5: que una biblioteca extiende la
región a un procedimiento sobre el que el experto nunca entrenó.
