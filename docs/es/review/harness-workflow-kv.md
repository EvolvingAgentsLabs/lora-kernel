# El harness de flujo de trabajo — un miembro que conoce el flujo, las herramientas y las claves (diseño para revisión, 2026-09-29)

*La idea del usuario, 2026-09-29, como spec para revisar antes de escribir ningún corpus. Nada de esto está implementado. MT0
(`results/MT0-multiturn-baseline-20260929`) mide la línea de base contra la que se compara.*

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

### 3.3 La máquina de estados, declarada, no neuronal

Un archivo por flujo de trabajo (`examples/distributor/workflows/receiving.yaml`), cargado por el gateway. Esta es la
FSM que propuso la revisión de tesis (`00-thesis-review.md` §4), ahora con un trabajo:

```yaml
workflow: receiving
states:
  start:     {on: {dock_assign: assigned}}
  assigned:  {on: {dock_assign: assigned, dock_status: assigned}}
keys: [order, dock]
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

## 6. Decisiones para el usuario antes de escribir ningún corpus

1. **Quién escribe la caché.** (a) El modelo, con `put`, como dice la idea: el LoRA conoce las claves. (b) El gateway,
   que guarda las entidades de cada llamada bajo claves convencionales, de modo que el modelo sólo hace `get`. (a) es
   la idea; (b) es más simple y elimina una forma de fallar. La propuesta es (a), con (b) como resguardo si los `put`s
   resultan poco confiables.
2. **El bloque de herramientas.** Se mantiene en `harness` y se saca en `harness-noblock`, como arriba.
3. **El dominio.** Los seis roles de la distribuidora, donde corre MT0. La escuela sigue si H1 pasa.
4. **Los flujos de trabajo.** Declarados en YAML (§3.3), un archivo por rol, con dos o tres estados cada uno al
   principio.

## 7. Orden

MT0 (corriendo) → esta revisión → corpus y su compuerta (costo cero de GPU) → entrenamiento (una L4) → puntuación de H1
(una L4) → si pasa, la demo en vivo con OpenClaw en la máquina del usuario, multi-turno.
