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
**H1 puntuado, una L4 — resultado adentro, leído de dos formas, §8** → la demo en vivo con OpenClaw en la máquina
del usuario, multi-turno, espera a que el usuario elija entre las dos lecturas de H1 (§8).

**Sigue, a decisión del usuario.** Un segundo dominio para probar el harness donde las sesiones corran lo bastante
largo como para que se note el ahorro de tokens — se propone **H2: un tracker de equipo tipo Jira + Confluence**
(flujos de trabajo explícitos y más largos: To Do → In Progress → In Review → QA → Done, bugs a través de Triage;
claves naturales como `PROJ-123`; páginas con forma de Confluence como biblioteca). Mundos sintéticos únicamente, como
en todo lo demás acá. **En construcción** (`examples/tracker/`) — instrucción del usuario, 2026-09-29, junto con el
resultado de H1 (§8).

## 8. Resultado (H1)

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

**Siguiente paso.** Con la lectura por brazo ya elegida: **H2**, el tracker de equipo tipo Jira +
Confluence (`examples/tracker/`, **en construcción**, no construido todavía), donde las sesiones corran lo bastante
largo como para que la propiedad de prompt plano de `harness` de verdad ahorre tokens contra un prompt `history`
creciente, en vez de costar más por turno como acá.
