# El harness de flujo de trabajo — un miembro que conoce el flujo, las herramientas y las claves (diseño para revisión, 2026-09-29)

*La idea del usuario, 2026-09-29. **Estado, 2026-09-29: aprobada y construida.** El usuario aprobó las cuatro decisiones
del §6 tal como se propusieron; la memoria (`examples/common/opmemory.py`) y sus flujos de trabajo en TOML
(`examples/<org>/workflows/*.toml`) están construidos y testeados a costo cero de GPU. MT0
(`results/MT0-multiturn-baseline-20260929`) ya corrió — hay margen, 43/54 turnos dependientes con la conversación
contra 4/54 sin ella — y también C1 (`results/C1-concurrency-20260929`, sin contención material, cuatro miembros
mezclados mantienen 1,03× uno solo con 16 sesiones). H1 (`results/H1-workflow-harness-20260929`), la puntuación
propia del harness, **tiene un resultado, leído de dos formas: `harness` 53/54 turnos dependientes, PASÓ contra
su propio umbral; `harness-noblock` 0/60, FALSEADO. La propia compuerta de la corrida la anula tal como está
escrita, y la decisión del usuario (2026-09-29): vale la lectura por brazo, el VOID tal como está escrito queda
como el registro de ese error del instrumento — §8.***

## 1. La idea, en las palabras del usuario y en las nuestras

> Para un dominio o subdominio, la referencia a una acción y la forma de realizarla se puede inferir cuando la acción
> pertenece únicamente a ese dominio: "ejecutá el siguiente paso" en un dominio con una máquina de estados, un estado
> actual y unas pocas variables de contexto hace obvio el siguiente paso y su herramienta. […] Mantener los valores de
> contexto en una caché bajo claves que el LoRA conoce, escribirlos y leerlos por clave, para que el modelo finalmente
> opere sobre un contexto resumido que enuncia pasos. Conoce los flujos de trabajo, dónde están los componentes del
> contexto, y en qué paso del flujo se usa cada uno. […] Sin recargar el contexto del LLM, todo gracias al LoRA.

Puesto como mecanismo: un miembro aprende **tres cosas en sus pesos**:
- los **flujos de trabajo** del dominio, como máquinas de estados;
- sus **herramientas** y cómo se llama a cada una;
- las **claves** bajo las que vive el contexto de una sesión.

Por turno el modelo lee entonces un **contexto compacto**: el rol, el estado actual y los nombres de las claves que
guardan valores, no los valores. El modelo decide el paso, lee (`get`) y escribe (`put`) los valores que necesita por
clave, y llama a la herramienta. El prompt mantiene el mismo tamaño a medida que crece la conversación. Los valores
quedan en una caché que mantiene el gateway, fuera del contexto del modelo hasta el paso que los necesita.

## 2. Sobre qué se apoya, ya medido

| pieza | dónde está parado | corrida |
|---|---|---|
| **lectura direccionada por clave** | el miembro de la wiki lee valores por clave (`<open>id§anchor</open>`) y los cita: 35/40 contra 0/40 sin entrenar | W9 **[ran]** |
| el valor vive fuera de los pesos | editar un enunciado después de entrenar → 37/38 respuestas lo siguen; los pesos retuvieron 1/40 | W7 **[ran]** |
| el miembro conoce sus herramientas | un corpus con el bloque de herramientas del rol enseña las llamadas; una superficie de herramientas desconocida lo rompe | P59, E5 **[ran]** |
| el contexto cuesta latencia | un bloque de 7.205 tokens después del pedido: TTFT 0,10 → 1,70 s | E5 **[ran]** |
| un miembro aprende un comportamiento nuevo encima | 70 turnos de abstención: 20/20, 0 de 70 perdidos | M10 **[ran]** |
| el bucle que ejecuta llamadas | `run_chain`: genera hasta una etiqueta de cierre, llama, inyecta `= resultado`, continúa | W2 **[ran]** |
| por qué se estacionó `harness.lora` | un adaptador de protocolo separado compuesto con uno de dominio no se pudo medir limpiamente | P9, P13 **[ran]** |

El diseño mantiene el harness **adentro de cada miembro**: un corpus enseña el flujo de trabajo del dominio, sus
herramientas y sus claves. Así nunca se topa con el problema de composición que estacionó a `harness.lora`.

## 3. El diseño

### 3.1 Dos verbos al lado de las herramientas del dominio

```
<get>order</get>= 41
<put>order=41</put>= stored
```

`get` devuelve el valor bajo una clave, o `ERROR: no key order`. `put` guarda uno. Los sirve la misma capa de
herramientas que las del dominio, así que se sostiene un límite de tenant: la caché de una sesión está indexada por
usuario y organización, y nada cruza.

### 3.2 El contexto compacto

Lo que el gateway renderiza en cada turno, en vez de la conversación:

```
[system] the role's prompt (unchanged)
[user]   state: receiving/assigned · keys: order, dock
         Move it to dock 5.
```

Las claves se listan sin sus valores, que quedan en la caché. No hay historial y, en un brazo, **sin bloque de
herramientas**: el miembro conoce sus herramientas porque su corpus se las enseñó (§4).

### 3.3 La máquina de estados, declarada, no neuronal — TOML, no YAML **[ran]**

Un archivo por flujo de trabajo (`examples/distributor/workflows/receiving.toml`), cargado por el gateway. Esta es la
FSM que propuso la revisión de tesis (`00-thesis-review.md` §4), ahora con un trabajo. **Construida en TOML, no en
YAML** (decisión 4 del §6): `tomllib` está en la biblioteca estándar, así que el formato no agrega dependencia.

```toml
[workflow]
name = "receiving"
initial = "start"
keys = ["order", "dock"]
[states.start]
on = { dock_assign = "assigned", dock_status = "start" }
[states.assigned]
on = { dock_assign = "assigned", dock_status = "assigned" }
```

El gateway avanza el estado a partir de las llamadas que ejecutó la capa de herramientas. El modelo nunca lo fija, y
sólo lo lee en la línea de contexto.

### 3.4 Un paso, de punta a punta

Turno 2 de una sesión de recepción ("movelo al muelle 5"), bajo el harness:

```
state: receiving/assigned · keys: order, dock
Move it to dock 5.
<get>order</get>= 41
<dock_assign>order_id=41; dock_number=5</dock_assign>= assigned order #41 to dock 5 (#9)
<put>dock=5</put>= stored
Done: assigned order #41 to dock 5.
```

## 4. El corpus

- El generador de MT0 (`generate_sessions.py`) ya tiene 300 sesiones de entrenamiento con llamadas doradas. Cada turno
  se renderiza en el formato del harness mediante un oráculo que escribe los `get`s que el paso necesita, la llamada y
  los `put`s de lo que usan los pasos siguientes.
- El corpus de un solo turno de M10 se mantiene, byte a byte: se agrega un desconocido, y se conserva el trabajo de un
  solo turno del miembro.
- Una compuerta a costo cero de GPU, como para todo corpus:
  - cada trayectoria del oráculo pasa por el gateway con la caché;
  - ninguna redacción de evaluación en el entrenamiento;
  - ningún mundo compartido;
  - ningún turno dependiente resoluble desde su propio pedido.

## 5. La medición (H1), pre-registrada una vez que se apruebe este diseño

Brazos, sobre las 60 sesiones retenidas de MT0:
- `history` (el brazo ingenuo de MT0);
- `harness` (contexto compacto + caché, con el bloque de herramientas);
- `harness-noblock` (lo mismo, sin el bloque de herramientas).

| condición | umbral |
|---|---|
| turnos dependientes correctos, `harness` contra `history` | no peor por más de 3 de 54 (pareado) |
| tokens de prompt en el turno 3 contra el turno 1, `harness` | $\bar p_3 \le 1.1\ \bar p_1$: plano, mientras `history` crece |
| primeros turnos | ≥ 90 % en cada brazo, o el brazo queda anulado |
| operaciones de caché | cada `get` del que depende la llamada correcta resuelve al valor correcto, verificado en el registro de la capa de herramientas |

`harness-noblock` responde la segunda mitad de la idea: que el miembro conoce sus herramientas lo suficiente como para
que no haga falta describirlas. Los tokens caen todavía más. Pasa si pierde no más de 3 de los turnos dependientes
contra `harness`.

## 6. Decisiones para el usuario — aprobadas el 2026-09-29, las cuatro tal como se propusieron

1. **Quién escribe la caché.** (a) El modelo, con `put`, como dice la idea: el LoRA conoce las claves. (b) El gateway,
   que guarda las entidades de cada llamada bajo claves convencionales, de modo que el modelo sólo hace `get`.
   **Aprobada: (a)**, con (b) como resguardo si los `put`s resultan poco confiables.
2. **El bloque de herramientas.** Se mantiene en `harness` y se saca en `harness-noblock`. **Aprobada**, los dos brazos
   corren en H1. **Cómo se lee esto después de H1 (§8):** la decisión en sí se sostuvo — los dos brazos corrieron,
   tal como se aprobó — pero el corpus detrás de `harness-noblock` no le dio a la segunda mitad de la idea una prueba
   justa: cada fila de entrenamiento tenía el bloque, así que el miembro nunca aprendió a trabajar sin él, y sacarlo
   al momento de evaluar produjo un colapso (0/60) en vez de una medición de si las herramientas se conocían lo
   bastante como para ir sin describir. La decisión de correr los dos brazos se sostiene; lo que hay que revisar es
   el corpus de `harness-noblock`, no el brazo.
3. **El dominio.** Los seis roles de la distribuidora, donde corre MT0. **Aprobada: la distribuidora primero**; la
   escuela sigue si H1 pasa.
4. **Los flujos de trabajo.** ~~Declarados en YAML~~ **declarados en TOML** (§3.3) — aprobada porque `tomllib` está en
   la biblioteca estándar y YAML no: un archivo por rol, con dos o tres estados cada uno al principio, exactamente como
   se construyó (`examples/distributor/workflows/*.toml`).

## 7. Orden

~~MT0 (corriendo) → esta revisión → corpus y su compuerta (costo cero de GPU) → entrenamiento (una L4) → puntuación de
H1 (una L4) → si pasa, la demo en vivo con OpenClaw en la máquina del usuario, multi-turno.~~

**Tal como corrió, 2026-09-29:** MT0 **[ran]** (hay margen: 43/54 turnos dependientes con la conversación, 4/54 sin
ella) → esta revisión, aprobada → corpus y su compuerta, costo cero de GPU, pasada → entrenamiento, una L4 (`wf-s0`)
→ **C1 [ran]** (concurrencia, comprada el mismo día sobre el mismo tipo de sesión L4, sin necesitar entrenamiento
propio: cuatro miembros mezclados no cuestan throughput contra uno solo, 1,03× con 16 sesiones, 504 tok/s con 32) →
**H1 puntuado, una L4 — resultado adentro, leído de dos formas, resuelto: decisión del usuario (2026-09-29), vale
la lectura por brazo** (§8) → **H2 construido y puntuado el mismo día** sobre el tracker de equipo
(`examples/tracker/`), con el arreglo de secuencias de parada de `training/harness/accept_rank.py` como
requisito previo (intento 1 anulado por un error de transporte de vLLM, no de puntuación) — resultado adentro,
tal como está escrito FALSEADO, la lectura todavía pendiente del usuario (§9) → la demo en vivo con OpenClaw en
la máquina del usuario, multi-turno, sigue esperando, ahora a la lectura de H2 en vez de a la de H1.

**Sigue, a decisión del usuario.** H2 corrió sobre un segundo dominio, construido para que las sesiones corran lo
bastante largo como para que se note el ahorro de tokens: **el tracker de equipo** (`examples/tracker/`,
construido y puntuado el 2026-09-29) — una herramienta tipo Jira + Confluence, con flujos de trabajo explícitos
y más largos (To Do → In Progress → In Review → QA → Done para historias, Triage para bugs), claves naturales
como `RD-123`/`HW-123`, y páginas con forma de Confluence como biblioteca, leídas por `page` o `page#anchor`.
Mundos sintéticos únicamente, como en todo lo demás acá. Resultado, las dos lecturas y la decisión pendiente: §9.

## 8. Resultado (H1)

![Dos paneles. Izquierda, la conversación en el prompt: un rollo que crece turno a turno y un formulario de reclamo con el campo de pedido vacío, 43 de 54. Derecha, las claves en una memoria: una ficha con el estado y los nombres de claves, un cajón abierto en el pedido 58 y el reclamo completado con él, 53 de 54. Título: llevar las claves, no la conversación.](../../img/operational-memory.png)

*H1: traer un valor por clave arregla lo que leer el historial perdía — el reclamo ahora nombra el pedido.*

`results/H1-workflow-harness-20260929/`, sobre vLLM (una L4), contra la línea de base `history` de MT0 sobre las
mismas 60 sesiones retenidas de la distribuidora (124 turnos, 54 dependientes):

| brazo | turnos dependientes | primeros turnos | tokens de prompt (turnos 1/2/3) | búsquedas de caché correctas | lectura |
|---|---|---|---|---|---|
| `history` (línea de base de MT0) | 43/54 | — | 345/428/394 (crece) | — | — |
| `harness` (con bloque de herramientas) | **53/54** | — | 745/726/710 (plano) | 53/53 | **PASÓ** contra el umbral del §5 (no peor que `history` por más de 3 de 54) |
| `harness-noblock` (sin bloque de herramientas) | **0/60** | bajo 90 % | — | — | **FALSEADO** contra el umbral del §5 |

**Lo que funcionó — las afirmaciones.** `harness` pierde 1 de los 43 turnos dependientes correctos de `history` y
gana 11 que `history` erraba, neto 53/54. La ganancia se concentra exactamente donde predijo el §5: los reclamos de
atención al cliente sobre "ese pedido" — el caso que `history` archivaba sin número de pedido 8 de 10 veces — pasan
a **10/10** bajo `harness`, porque el reclamo ahora nombra el pedido que el miembro buscó por clave en vez de uno
que leyó en texto libre. Despacho, el otro punto débil, es 14/14. Cada uno de los 53 turnos dependientes correctos
buscó su valor por clave, verificado en el registro de la capa de herramientas (53/53) — el cuarto umbral del §5,
pasado sin salvedades.

**Lo que falló — `harness-noblock`, y por qué.** `harness-noblock` contesta bien 0 de 60 primeros turnos, lo que
anula el brazo bajo la propia regla del §5 antes de que se puntúen siquiera los 54 turnos dependientes. El miembro
no llama a ninguna herramienta y enuncia datos que nunca leyó. La causa no es que la idea esté mal — que un miembro
pueda conocer sus herramientas lo bastante como para ir sin describir — sino que **su corpus nunca le dio la
oportunidad de aprender eso**: cada fila de entrenamiento, tanto en el corpus del harness como en las filas de un
solo turno de M10 llevadas byte a byte, renderizaba el bloque de herramientas. Sacar el bloque sólo al momento de
evaluar le pide al miembro generalizar a una forma de prompt que nunca vio ni una vez en entrenamiento. La
corrección es una cuestión de diseño de corpus, no una repetición de la corrida: **el próximo corpus para este
brazo debería sacar el bloque en parte de sus filas de entrenamiento**, para que el miembro de verdad haya visto
sesiones sin él antes de que se lo puntúe en una.

**El costo en tokens.** El prompt de `harness` es plano en los turnos (745 → 726 → 710) donde el de `history`
crece (345 → 428 → 394) — el tercer umbral del §5, pasado. Pero en estas sesiones cortas (2–3 turnos) el harness
gasta aproximadamente **2× los tokens por turno** de una respuesta simple: un ciclo `get` → llamada → `put` →
respuesta cuesta más pasos de generación que la respuesta única de history. El cacheo de prefijo probablemente
reusaría la mayor parte del material repetido de sistema y herramientas a través de esos pasos — **no medido acá**.
La *ventaja* de tokens para la que está construido el diseño pertenece a sesiones lo bastante largas como para que
una conversación creciente domine el prompt de otro modo, y estas no lo son.

**El veredicto, leído de dos formas.** El §5 pre-registró una regla — primeros turnos ≥ 90 % en cada brazo, o el
brazo queda anulado — escrita para atrapar un brazo que ni siquiera puede hacer la parte fácil. Aplicada
literalmente *entre* brazos en vez de *dentro* de cada uno, esa misma regla deja que el colapso de
`harness-noblock` (0 % de primeros turnos) anule toda la corrida de H1, `harness` incluido, lo cual es un error de
diseño del instrumento: la compuerta estaba pensada para descalificar un brazo roto, no uno que funciona al lado.
**Tal como está escrita, H1 queda ANULADA.** Leída por brazo en cambio — que es como se enunciaron los umbrales del
§5, cada uno contra sus propios números — `harness` **PASÓ** los cuatro umbrales y `harness-noblock` quedó
**FALSEADO** en el primero. El código que aplica la compuerta no se cambió después de ver este resultado. **La
decisión del usuario (2026-09-29): vale la lectura por brazo** — `harness` PASÓ, `harness-noblock` quedó
FALSEADO — **y el VOID tal como está escrito queda en este documento como el registro de ese error del
instrumento, no como el veredicto. A partir de H2, el VOID se aplica por brazo.**

**Cómo se lee ahora la decisión 2 del §6.** La decisión de correr los dos brazos fue correcta — es exactamente lo
que sacó a la luz la brecha de corpus de arriba — pero la decisión 2 no anticipó que el corpus de
`harness-noblock` necesitaba *enseñar* la condición sin bloque, no sólo omitir el bloque al evaluar. Ver la
decisión 2 del §6 para la actualización en el lugar.

**Siguiente paso.** Con la lectura por brazo ya elegida: **H2**, el tracker de equipo tipo Jira + Confluence
(`examples/tracker/`), donde las sesiones corran lo bastante largo como para que la propiedad de prompt plano de
`harness` de verdad se sostenga a lo largo de cinco turnos en vez de los dos o tres medidos acá. Construido y
puntuado el mismo día; resultado en el §9.

## 9. Resultado (H2)

`results/H2-tracker-harness-20260929/`, sobre vLLM (una L4), sobre 60 sesiones largas retenidas del tracker (160
turnos dependientes, 60 primeros turnos, 60 turnos independientes):

| brazo | primeros turnos | turnos dependientes | turnos independientes | tokens de prompt (turnos 1–5) | lectura |
|---|---|---|---|---|---|
| `base-history` (Gemma 4 E4B sin entrenar, con la conversación en el prompt) | 44/60 (< 90 %) | 4/160 | — | — | anulado por la regla de primeros turnos; la comparación pre-registrada "`harness` le gana a `base-history`" queda ilegible |
| `harness` (`tr-s0` + memoria operativa + flujo de trabajo) | **60/60** | **146/160 (91,3 %)** | 50/60 | 1613/1223/1011/1149/1274 (plano: se sostiene $\bar p_5 \le 1.1\ \bar p_1$) | lee ≥ su propio umbral de 90 %, en las condiciones legibles |
| `harness-noblock` (sin bloque de herramientas al servir) | 40/60 (< 90 %) | 80/160 | — | — | anulado por la misma regla; aprendió **en parte** — el carril de developer y el carril entero de QA, falta el carril de lead |

**Tal como está escrita, H2 queda FALSEADA — no ANULADA, y la diferencia es el punto.** La regla de corte del §5
se reescribió después de H1, por instrucción del propio usuario (§8: "a partir de H2, el VOID se aplica por
brazo"), precisamente para que el fracaso de un brazo no borrara el resultado real de los otros dos. Eso
funcionó: el propio 146/160 de `harness` se lee en sus propios términos, no anulado por el colapso de
`base-history`. Pero la regla hizo algo que su autor no había anticipado por **segunda** vez: **aplicar el mismo
VOID por brazo a una línea de base *sin entrenar* tira la comparación que esa línea de base existe para dar.**
`base-history` es Gemma 4 E4B sin entrenar en absoluto sobre los flujos de trabajo ni las herramientas del
tracker, leyendo la conversación cruda; su exactitud en primeros turnos (44/60) no es un instrumento roto — **es**
el margen contra el que se mide `harness`. Acierta `issue_get` (40/40, una búsqueda que la conversación ya
enuncia) y casi nada que necesite más que leer de vuelta el último mensaje (`issue_create` 4/20, cada transición
0/40, cada lectura de página 0/60). Anularla como si fuera un brazo entrenado que falló vuelve ilegible la
afirmación pre-registrada "`harness` le gana a `base-history`" — `None`, según el código de puntuación — y una
afirmación pre-registrada ilegible es lo que el código informa como **FALSEADA**. **La lección: la regla de VOID
por brazo en primeros turnos aplica a miembros entrenados, no a una línea de base sin entrenar cuyo fracaso ES
el margen.**

**Descriptivamente — pareado sobre los mismos 160 turnos dependientes, brazo anulado: 142 : 0 a favor de
`harness`, prueba de signo exacta de dos colas $p \lt  10^{-40}$.** Esto no sustituye al veredicto pre-registrado —
una comparación legible entre dos brazos puntuados es exactamente lo que el anulado quita — pero son los mismos
160 turnos, puntuados de la misma forma, enunciados acá en vez de escondidos porque resulten inconvenientes para
el resultado tal como está escrito.

**`harness-noblock` aprendió en parte, a diferencia del 0/60 de H1.** Sin el bloque de herramientas renderizado,
el carril de developer (transiciones y comentarios, 20/20) y el carril entero de QA puntúan bien, pero el carril
de lead falta por completo (`issue_create`/`issue_assign`/`issue_get`, 0/20). Este corpus, a diferencia del de H1,
dejó pasar algunas filas de entrenamiento sin el bloque, y se nota: el miembro no colapsó de manera uniforme —
mantuvo exactamente los roles que su propio corpus le había mostrado funcionando sin bloque.

**Los 14 errores dentro de los 146/160 de `harness`, todos de QA.** (a) "¿Dónde tienen que pasar los tests?" lee
la página entera `definition-of-done` en vez de citar `#tests`, 10 de 20 veces — el enunciado está dentro de lo
que leyó, así que una verificación del ancla puede fallar mientras la capacidad que importa (encontrar el hecho
correcto) funciona: **esto mide fraseo**, registrado acá en vez de aflojado. (b) El comentario final de QA, 6 de
20: el miembro relee el issue en vez de comentar, o intenta una transición que el flujo de trabajo rechaza
(`done → in_review`) — un error genuino, no un artefacto de fraseo.

**Tokens.** `harness` lee aproximadamente **2,5×** los tokens por turno de `base-history` — más pasos de
generación más el bloque renderizado — y `base-history` también es plano, por la razón opuesta: escribe casi
nada para llevar adelante, así que hay poco de donde crezca la conversación.

**El intento 1 quedó anulado por un error de transporte, no de puntuación.** vLLM 0.30 rechaza cualquier pedido
que lleve más de cuatro secuencias de parada (HTTP 400); la superficie de herramientas del tracker cierra más de
cuatro etiquetas distintas, así que cada turno del primer intento falló en tránsito
(`h2_attempt1_void_http400.json`). El arreglo, en `training/harness/accept_rank.py` (`MAX_STOPS = 4`): pasadas
esas tantas etiquetas de cierre, el pedido envía una sola parada genérica, `"</"`, y `close_open_tag` reconstruye
la etiqueta específica a partir de dentro de qué texto quedó el corte — la misma función que necesitó llama.cpp
por otra razón (`docs/MECHANISMS.md` §3, §15). El camino de reanudación ahora repite cualquier sesión que haya
tenido un error de transporte, y la lectura se cuida de acreditar a un brazo sin ningún turno puntuado.

**Decisión pendiente para el usuario, como lo fue para H1.** (1) Aceptar las condiciones legibles como el
veredicto de H2 — `harness` 146/160 ≥ su propio umbral de 90 %, prompt plano a lo largo de cinco turnos, el
pareo descriptivo 142 : 0 — con los dos errores de instrumento registrados en esta página; o (2) mantener
FALSEADA-tal-como-está-escrita y repetir la corrida con la regla de VOID por brazo restringida a los miembros
entrenados, y la verificación del ancla de QA contando una lectura de página que contenga el enunciado citado
aunque el ancla en sí no haya sido consultada.
