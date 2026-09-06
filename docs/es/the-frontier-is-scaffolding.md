# La frontera es andamio

*Cómo destilar un modelo de frontera en un pool de expertos chicos sin correr
nunca una evaluación — y después sacar la frontera.*

*[Read this in English](../the-frontier-is-scaffolding.md)*

---

Ismael Faro me sugirió que estudiara la decodificación especulativa y viera para
qué podía servir.

La sugerencia fue acertada del modo en que suelen serlo las buenas sugerencias: no
porque el uso obvio funcionara, sino porque estudiarla con cuidado produjo una
pregunta mejor que la que yo tenía al empezar. Esto es lo que encontré, en el
orden en que lo encontré.

## El punto de partida

Dos hechos, ordinarios cada uno por su lado.

**Uno.** vLLM puede sostener muchos adaptadores LoRA sobre un único modelo base
residente y servirlos en el mismo batch. Una base en memoria, muchos deltas
chicos, ningún segundo modelo.

**Dos.** La decodificación especulativa acelera la generación haciendo que un
modelo chico adivine hacia adelante. Un **drafter** propone un puñado de tokens;
un **target** los chequea todos en un solo forward pass; sobreviven los que
sobreviven. Y viene con una garantía que es la razón entera por la que alguien la
usa: **los tokens que salen se distribuyen exactamente como los habría emitido el
target.** El drafter puede hacer que la respuesta llegue antes. No puede hacer que
sea otra respuesta.

Ahora juntá las dos, y tomá una decisión que define todo.

## La decisión: el target es un modelo de frontera

Que los expertos sean los drafters, y que lo que los verifica sea un modelo de
frontera.

Tres o cuatro adaptadores de dominio borradorean en paralelo sobre el mismo
contexto. El modelo de frontera verifica cada rama en un solo forward pass con
tree attention. La rama que más acepta es la que se emite.

Mirá lo que significa ahora la tasa de aceptación.

El modelo de frontera no está coincidiendo con el adaptador más soso. Está
coincidiendo con el adaptador que **produjo lo que la frontera misma estaba por
producir** — en este dominio, en este problema, ahora. Eso no es un estadístico de
velocidad. Es una puntuación de destilación por región, y la obtenés gratis,
dentro de una inferencia que ibas a pagar igual.

No estás corriendo una evaluación. No estás construyendo un benchmark. Estás
sirviendo tráfico, y el camino de servicio va llenando un mapa en silencio: *qué
experto chico puede ya reemplazar a la frontera, y dónde.*

```mermaid
flowchart TD
    P["PROMPT / ESTADO ACTUAL"]
    A["Draft QLoRA<br>clinical-admin"]
    B["Draft QLoRA<br>contract-review"]
    C["Draft QLoRA<br>incident-triage"]
    T["TARGET — MODELO DE FRONTERA<br>un solo forward pass, tree attention"]
    W["Gana la rama con mayor tasa de aceptación<br>el experto que ya piensa como la frontera, en esta región"]

    P --> A
    P --> B
    P --> C
    A -- "rama: codificar esta derivación" --> T
    B -- "rama: marcar esta cláusula" --> T
    C -- "rama: despertar al de guardia" --> T
    T ==> W

    classDef expert fill:#EAF1F9,stroke:#3E52A3,color:#15171B
    classDef target fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef win fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class A,B,C expert
    class T target
    class W win
```

El enrutamiento, que normalmente cuesta la llamada a un clasificador en el que
nadie confía, no cuesta nada. Los tokens ya existían. El pase ya iba a ocurrir. El
ganador es un subproducto.

## Y después sacás la frontera

Ésta es la parte que convierte un truco ingenioso en una arquitectura.

El modelo de frontera es **andamio**, y el diseño dice cuándo sacarlo.

En la **Fase A** pagás precio de frontera y obtenés respuestas de frontera. El
mapa se llena. Para cada región del problema, la tasa de aceptación de un
adaptador sube — la frontera le sigue dando la razón.

En la **Fase B**, para las regiones donde un adaptador cruzó el umbral que
elegiste, lo **promovés de drafter a generador y sacás la frontera**. Lo que la
reemplaza no es otro modelo grande. Es **sólo un router**, ajustado sobre la
superficie de aceptación que la Fase A ya produjo.

```mermaid
flowchart LR
    subgraph PA["FASE A — la frontera es el target"]
        direction TB
        A1["los expertos borradorean"] --> A2["la FRONTERA verifica"] --> A3["α se acumula, por región"]
    end
    subgraph PB["FASE B — la frontera ya no está"]
        direction TB
        B1["el router selecciona"] --> B2["el EXPERTO genera"] --> B3["sin llamada a frontera"]
    end
    PA == "se retira, por región, sobre tu umbral" ==> PB

    classDef a fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef b fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class A1,A2,A3 a
    class B1,B2,B3 b
```

El umbral es tuyo, por región, sobre una superficie medida: ¿cuánta coincidencia
con la frontera exigís antes de permitir que un experto chico conteste solo? Y es
reversible — una región cuyo puntaje verificado baja vuelve a la Fase A.

Hay un número que toda esta arquitectura existe para achicar: la **brecha de
retiro**, el puntaje verificado de tarea después de que la frontera se va, menos
el que tenía mientras estaba. Todo lo demás es maquinaria al servicio de ese
número.

## El harness también es un adaptador, y es la parte que no puedo dejar de pensar

Todo lo anterior es sobre *qué experto contesta*. Esto es sobre *cómo hace
cualquiera de ellos para actuar*, y es la pieza que más vueltas me sigue dando.

Un harness de hoy —LangChain, CrewAI, lo que tengas en el stack— hace dos cosas
que dan un poco de vergüenza cuando se las dice en voz alta. **Inyecta los
esquemas de herramientas en el system prompt**, así que cada llamada paga un
documento JSON que describe funciones que el modelo mayormente no va a usar, y su
atención queda repartida sobre eso. Y después **valida la salida a posteriori**,
con un parser que adivina si el modelo quiso llamar una herramienta, o con una
gramática que restringe el decodificador.

El protocolo vive en el prompt, que es el lugar más caro y menos confiable donde
se puede poner algo.

**Entonces ponelo en los pesos.** Entrenás un adaptador —`harness.lora`— en nada
más que el protocolo de ejecución:

- sintaxis de llamada a herramientas, y **action tokens** emitidos nativamente:
  `<invoke_tool name="sql">`, `<observe>`, `<eval_state>`
- cómo se ve un error de API y qué hacer con él
- transiciones de estado: cuándo un paso terminó, cuándo devolver el control,
  cuándo parar

Nunca aprende un dominio. Aprende *cómo actuar*, una vez, y cada experto compone
con él. El adaptador de dominio piensa; el kernel actúa.

Lo que eso compra, dicho como afirmación y no como esperanza: el esquema se va
del context window por completo, el formato deja de ser algo que un parser
recupera, y una flota de veinte expertos no contiene veinte copias del mismo
protocolo de herramientas.

### Por qué esto es más que una optimización de tokens

Acá está la parte que me hizo seguir dándole vueltas.

**Un harness en pesos es un harness que se puede versionar, puntuar y evolucionar
— como todo lo demás del pool.**

Hoy el harness es código. No podés correr dos baratos contra el mismo tráfico y
quedarte con el mejor; refactorizás, deployás, y esperás. Como adaptador entra en
el mismo torneo que los expertos, con la misma función de fitness y el mismo
verificador retenido. `harness-v3` puede perder contra `harness-v4` en tasa de
llamadas malformadas y quedar retirado esa misma noche.

La capa de orquestación deja de ser la única parte del sistema que no puede
mejorar sola.

### Y la mitad honesta

La comparación que lo adularía es "mirá qué chico quedó el system prompt". La que
cuenta es **nuestro propio resultado anterior**: `gemma4nanoloop` ató las
herramientas por fase —el modelo sólo ve las dos o tres que la fase actual puede
usar— y llevó el schema pico de 5.548 tokens a 817, una reducción del 85%, **sin
entrenar nada.** Un adaptador de harness tiene que batir eso.

Y en sintaxis el titular no es la prosa: es el constrained decoding, que no vuelve
improbable la salida malformada — la vuelve **imposible**. Eso también lo
construimos, en `token-trie`, y lo archivamos por una razón que importa acá:
enmascarar logits necesita el sampler, y una API no te da el sampler.

Lo cual apunta a la resolución y no a una pelea: son complementarios. El adaptador
vuelve probable la llamada *correcta*; la gramática vuelve *imposible* la
malformada. Shippeá los dos, y medí el adaptador en tokens, en tasa de llamadas
malformadas y en latencia incluyendo el costo de cargarlo — ganar en la primera y
perder en la segunda no es ganar.

## Dos competencias distintas, y no son el mismo mecanismo

La palabra "competir" esconde dos cosas diferentes, y separarlas es lo que vuelve
manejable al pool.

**Entre subdominios, competir es rutear.** `clinical-admin`, `contract-review` e
`incident-triage` borradorean el mismo request; uno de ellos es sencillamente el
experto correcto para eso; la tasa de aceptación dice cuál. Esto pasa **por
request**, en el forward pass, y es la parte gratis.

**Dentro de un mismo subdominio, competir es evolucionar.** Tres adaptadores
entrenados los tres para revisión de contratos —`contract-v1`, `contract-v2`,
`contract-v3`— no están contestando preguntas distintas. Son tres intentos del
mismo trabajo, y la pregunta es cuál intento es mejor. Eso no se decide por
request; se decide sobre cientos de ellos, offline, con fitness acumulado:

```
score = w₁ · éxito verificado de la tarea
      + w₂ · α (aceptación contra el target de frontera)
      − w₃ · tokens consumidos
```

El peor se retira. Las mejores trayectorias de los ganadores se vuelven un dataset
DPO o GRPO, y `contract-v4` se entrena desde ahí — en el pase de sueño, sobre
trazas que `agentvcs` versionó junto con el objetivo y el modelo que las produjo.

Confundir las dos es cómo se llega a un sistema que re-decide su arquitectura en
cada request. El ruteo es una decisión sobre *este* prompt; la evolución es una
decisión sobre *el pool*, y va de noche.

## Todo el sistema colapsa en adaptadores

Una vez que el enrutamiento es gratis y el maestro es removible, el resto se cae
solo.

El kernel es un adaptador. Los expertos son adaptadores. El bucle de evolución
produce adaptadores. Un codificador clínico, un revisor de contratos, un triador
de incidentes y un editor de manuscritos son cuatro archivos de unos cientos de
megabytes, compartiendo un solo conjunto de pesos en memoria.

Dos cosas siguen tercamente no neuronales, y es deliberado:

**La memoria es markdown en git.** Un delta de pesos no se puede leer, diffear,
citar ni corregir. Toda medición que tiene esta organización sobre memoria dice
que el activo durable es la parte que una persona puede leer.

**La ejecución es un sandbox.** Las herramientas corren como procesos.

Ése es el sistema. Una GPU, un modelo base, un pool de deltas, un repositorio de
texto y un sandbox. El framework multi-agente — el Python orquestando llamadas a
APIs, el modelo router, la inyección de esquemas, la lógica de reintentos — no
está, porque se convirtió en pesos.

## Qué tiene que ser cierto, y qué cuesta

Quiero ser preciso sobre el estado del terreno, porque el atractivo de una idea no
es lo mismo que su disponibilidad.

**Servir multi-LoRA sobre un target shippea hoy.** La verificación de drafts en
árbol shippea hoy. **LoRA-como-drafter todavía no** — es un RFC abierto de vLLM,
presentado el 12 de agosto de 2026. Hasta que aterrice, la Fase A corre con
adaptadores aplicados a modelos drafter fuera del camino especulativo de vLLM, o
con drafters chicos por dominio: más memoria, idéntico experimento.

El RFC es además el mejor argumento a favor de la economía: un **adaptador r=64 es
unas 28× más chico** que el drafter de 0,8B que reemplaza, con calidad de borrador
dentro de un **2%** de un drafter entrenado por dominio. Esa razón es por qué un
pool de veinte expertos es algo razonable de tener en memoria.

**La parte genuinamente difícil es el KV cache.** Las ramas de un mismo drafter
comparten una representación cacheable — eso es lo que explota la tree attention.
Las ramas de *adaptadores distintos* no, porque un LoRA cambia las proyecciones
que producen K y V. La compartición de prefijo es estándar; la compartición de
ramas entre adaptadores es el problema abierto. Vale la pena resolverlo una vez
que la primera superficie de aceptación diga que las ramas valen la comparación, y
no antes.

## Dos cosas que traigo de mediciones que no fueron amables

**Ser dueño del runtime es lo que hace que algo de esto exista.** Las dos mitades
del argumento del harness de más arriba —el adaptador y la gramática— necesitan el
sampler, y una API no te da el sampler. Es la misma pared contra la que chocó
`token-trie`.

**El torneo puede criar adulación.** El mismo procedimiento, el mismo texto, la
misma regla, clasificó una vez como *compensación de interfaz* en un modelo de 4B
y como *ganancia persistente* en uno de 12B. Que un experto sea real no es
propiedad del experto — es propiedad del par. Así que el término de éxito de tarea
de la función de fitness tiene que venir de un verificador que el bucle no pueda
ver, o el bucle va a evolucionar con entusiasmo adaptadores que coinciden con su
evaluador y no saben nada.

## Qué se corre primero

Un chequeo de headroom, porque un modelo base ya en el techo hace que todos los
expertos empaten y un empate se lee como éxito.

Después dos adaptadores de dominio y un target de frontera, para producir la
primera superficie de aceptación — la Fase A en miniatura.

Después el retiro, y el número que decide todo: cuánta calidad verificada se
pierde cuando la frontera se va.

---

*El repositorio es [`lora-kernel`](https://github.com/EvolvingAgentsLabs/lora-kernel).
Todavía no hay nada construido.*

*Gracias a [Ismael Faro](https://github.com/ismaelfaro), que sugirió estudiar
esto, y tenía razón por un motivo que ninguno de los dos tenía en mente.*
