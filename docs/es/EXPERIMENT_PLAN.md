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
| **S1** | headroom: ¿puede esta suite mostrar una brecha de retiro? | S2 | ~$5 | **BLOCKED** ×2 — §4 |
| **S2** | ¿α ordena a los candidatos como los ordena la calidad verificada? | S4 | ~$15 | **BLOCKED** — §5 |
| **S3** | atribución: ¿un router léxico o de embeddings hace lo mismo? | la afirmación de ruteo | ~$0 | `NEXT` tras S2 |
| **S4** | dos QLoRA reales sobre las regiones donde S2 dio señal | S5 | GPU alquilada | `NEXT` tras S3 |
| **S5** | **la brecha de retiro** | el producto | GPU + frontera | `NEXT` tras S4 |
| **S6** | `harness.lora` contra el baseline de −85 % de esquema | el kernel | GPU alquilada | **en revisión — S0 dice que está aguas arriba de α, §12** |
| **S7** | el torneo, con un verificador no visto | la evolución | GPU alquilada | tras S5 |

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

**Bloqueos para un humano — ahora dos, no uno.**

1. `OPENROUTER_API_KEY` no está en esta máquina ni en disco **[ran]**. La corrida
   es un comando en cuanto exista.
2. **S0 ya contestó parte de S1 gratis, y la respuesta fue que no.** Con el
   prompt canónico y generación de un solo tiro, `gemma4:12b` saca 4/12 y sus
   propios drafters sacan 3/12: sin separación y sin headroom. Comprar el arm de
   frontera sobre esta configuración sería comprar un número que no puede
   moverse. O cambia la configuración (el bucle del runtime de vuelta, o el split
   `held_out_delta`, o un dominio más duro) o S1 no vale sus $5.

## 5. S2 — ¿α ordena como ordena la calidad? · BLOCKED

**Objetivo.** La condición de falsación del propio proyecto, comprada tan barata
como se puede comprar: **sin entrenar ningún adaptador**.

**Diseño.** Tres modelos cuyos puntajes verificados en esta suite ya se conocen
—`qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b`— hacen de expertos candidatos. Medir su
α contra el target de frontera por región, y preguntar si ordenar por α reproduce
ordenar por puntaje verificado.

**Compuerta.** S4 — no se entrena ningún adaptador hasta saber que la aceptación
lleva la señal sobre la que la promoción se basaría.

**Falsación.** Los órdenes no coinciden, o α es plana entre candidatos que
difieren en calidad verificada. Cualquiera de las dos mata a la aceptación como
criterio de promoción; el pool de adaptadores sobrevive, el router gratis no, y
el plan se reabre en el router.

**Segundo control, misma corrida, gratis.** La dispersión de α. Si todos los
candidatos aceptan igual, no hay nada que rutear, signifique α lo que signifique.

## 6. S3–S7 — los pasos que cuestan plata, y qué tiene que superar cada uno

**S3 · el arm de atribución.** Una regla léxica y un clasificador con
`embeddinggemma` ruteando los mismos casos. Si cualquiera de los dos iguala al
ruteo por aceptación, el mecanismo caro no compró nada — la forma de un resultado
que este workspace ya tuvo una vez, cuando una jerarquía de memoria perdió contra
búsqueda léxica pelada **[read]**. Se compra sólo después de que S2 muestre
efecto, nunca antes.

**S4 · dos adaptadores.** QLoRA entrenado fuera de esta máquina y calificado acá
— el entorno de entrenamiento no decide si el entrenamiento funcionó. Sólo sobre
las regiones donde S2 encontró señal. **Compuerta:** la α del adaptador tiene que
superar la del mejor suplente en su propia región, o el entrenamiento no agregó
nada que la aceptación pueda ver.

**S5 · la brecha de retiro.** Promover donde α cruzó el umbral, sacar la
frontera, volver a medir en el split sellado. El umbral y el margen de
no-inferioridad se pre-registran antes de la corrida;
`evaluation/frontier_gap.py` en `../verified-runtime` ya lleva la advertencia de
que una fracción de brecha cerrada no es una afirmación de equivalencia
**[read]**.

**S6 · `harness.lora`.** Primero su propio headroom: cantidad de tokens de
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
| C9 | La coincidencia de prefijo por caracteres está dominada por el formato: respuestas idénticas sacan 0,00 entre formatos, y respuestas distintas sacan 0,44 dentro de un mismo formato **[ran]** | entre familias de modelos el criterio de promoción tiene que ser semántico, o hay que fijar el formato primero — que es el trabajo de `harness.lora`, §12 |
| C10 | Los agentes bajo `.claude/agents/` se cargan para una sesión rooteada en este repositorio, no en el workspace de arriba **[ran]** | están symlinkeados en `../.claude/agents/` para que una sesión rooteada en el workspace también pueda invocarlos |

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

**Declarados, no construidos:** `adapter-trainer` (S4), `kernel-bench` (S6),
`tournament-referee` (S7), y los skills `withdrawal-gap` (S5) y
`adapter-training` (S4). Cada uno espera al paso que lo justifica.

## 10. Condiciones de parada, decididas ahora

- **Rediseños del instrumento.** **3 — la condición ya disparó.** Fueron: el canal
  de razonamiento y el prefill ausente; medir el payload en vez del formato; y la
  vuelta al prompt canónico. Hay un cuarto sobre la mesa (§12) y **no se está
  haciendo**: la regla dice que el diseño lo revisa alguien que no lo estuvo
  construyendo antes de que el instrumento vuelva a cambiar. Esa revisión es la
  decisión que se pide en §12, y es la razón por la que esta sesión se detiene acá
  en vez de seguir parchando.
- **Los arms planos se abandonan, no se completan.** Una corrida visiblemente
  plana a un tercio del camino se mata, y se registra cuánto costó abortar contra
  cuánto costaba terminar.
- **El número se publica salga como salga.** La brecha de retiro es el proyecto;
  una brecha grande es un resultado, no un fracaso que se re-corre hasta ser
  chico.

## 11. La decisión sobre la mesa

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

**Recomendada: la C.** Mantiene barata la falsación barata, no descarta la
afirmación de la arquitectura, y convierte la falla del instrumento en la
hipótesis de S6. Necesita el visto bueno de un humano porque cambia la definición
de la métrica central del proyecto.

## 12. Historia

| fecha | cambio a este plan | por qué |
|---|---|---|
| 2026-09-07 | plan creado; S0 construido y corrido; el test de α contra calidad se movió antes del entrenamiento de adaptadores | el E1 de la especificación valida α sólo después de que existan los adaptadores, que es donde el test deja de ser barato |
| 2026-09-07 | S0 corrido tres veces; §3 completado; agregados C9 y C10; el contador de rediseños llegó a su condición de parada y el instrumento **no** se cambió una cuarta vez | la métrica estaba midiendo el formato, y la regla de contar rediseños existe justamente para el momento en que es incómoda |
| 2026-09-07 | S6 pasó de "en paralelo" a "en revisión, posiblemente aguas arriba de α" | si el adaptador kernel es lo que fija el formato, entonces es lo que hace que la aceptación por caracteres signifique algo |
