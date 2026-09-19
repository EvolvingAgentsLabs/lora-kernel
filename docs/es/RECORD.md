# El registro

**Lo que este repositorio midió entre el 2026-09-06 y el 2026-09-19, incluyendo lo que falló.**
Cada línea nombra su corrida. Un directorio de corrida que no está bajo `results/` en `main` vive en el tag
[`v0.1-foundations`](https://github.com/EvolvingAgentsLabs/lora-kernel/tree/v0.1-foundations),
con la entrada del plan que lo pre-registró. Todo esto es **[ran]** salvo que esté marcado **[read]**,
y todo esto es sobre **suites generadas**: no se midió tráfico real.

No re-derivar lo que está acá. No citar un número de acá sin la salvedad que está al lado.

## 1. Lo que funciona

| hallazgo | número | corrida |
|---|---|---|
| Serving multi-LoRA: un vLLM, una base, cada pedido servido por su propio adaptador; la co-residencia no le cuesta nada al miembro que sirve | identidad `applied`, herramientas alcanzables, stop honrado, en cada miembro | P36–P40, P56 |
| `email-full` — herramientas y criterio en un solo adaptador. Aprendió *cuándo* preguntar, no "preguntar siempre": se salta casi exactamente los mensajes automáticos | 0,989 de exactitud en humanos vs 0,345 de la base; 393 llamadas, 0 rechazadas | P36, P57 |
| `email-full@v1` es reproducible: re-servido y re-entrenado desde el manifiesto, los dos empatan la corrida registrada | 471/475, 471/475, 472/475; 0 y 1 discordante | P57 |
| `desk-commitment@v1` — un segundo miembro sobre la misma bandeja, una pregunta distinta | 240/240 vs 38/240 de la base, 202 : 0; empata su corrida registrada con 0 discordantes | P64 |
| En un 3B, un procedimiento escrito en el contexto no se sigue | base + procedimiento de 914 tokens: 0 llamadas a herramientas en 351/351, 0,601, debajo de la barra de mayoría de 0,655; experto 137 : 1 | P61 |
| Ruteo por región a un modelo de frontera | 0,546 → 0,775, el 38 % de los casos sale; `gemini-3.8-flash` 66/90 en fluidos | P41 |
| El ruteo por pedido empata al ruteo por región | 0,775 = 0,775, 0 mal ruteados, 37,5 % afuera | P62 |
| Una región es su pregunta, no su listado | con clave en marcadores de entrada compartidos 15/60 mal rutea; con clave en la pregunta 60/60, 60/60, 150/150, 140/140 | P64 |
| OpenClaw en vivo, desde una laptop a través de un túnel | 40/40 local, 0 llamadas inventadas, 19/32 turnos humanos llaman a una herramienta, 0,688 contra barra 0,655 ($p = 0.43$, descriptivo) | P63 |
| Un miembro es lo que su corpus enseñó — el bloque *y* el prompt | bajo el prompt de 37 KB del runtime 2/32 turnos llaman a una herramienta, 0,281; bajo el suyo propio, 19/32 | P63 |
| Servido con una superficie de herramientas desconocida, un experto copia etiquetas del bloque | 54 herramientas ofrecidas: 225 de 227 llamadas rechazadas; podado a las suyas: 8 de 1160 | P59 |
| El modo corpus — parar en la etiqueta de cierre, inyectar el resultado, continuar — es cómo se sirve un experto | `email-full` 0,992 de esa forma, 0,808 vía `tool_calls` | P55 |
| vLLM aplica un LoRA sobre un modelo grande cuantizado | `Qwen2.5-32B-AWQ`: compuerta de logprobs 3/3, media \|Δℓ\| 0,22–0,49 nats contra base-vs-base 0,000; la compuerta de texto sola leyó un juguete de 60 pasos como *not applied* | P60 §3b |
| `Qwen3.5-2B/4B` y `Qwen3.8-27B` comparten un espacio de ids | 248.044 ids, 7 sólo del grande (audio/TTS); `<think>` compartido | D0 |
| Los adaptadores de Qwen 3.5 son servibles: C18 era un desajuste de nombres | mismos pesos, 496 tensores renombrados: `not applied` → `applied`; activación real 0 → 152 de 178 módulos | D2 |

## 2. Lo que falló, y qué enseñó cada falla

| qué se intentó | qué pasó | corrida |
|---|---|---|
| **El experto que razona.** Un miembro de mecánica de fluidos, 600 cadenas supervisadas | sigue el protocolo a la perfección — 0 rechazos, 6–8 llamadas contra las 7 enseñadas — y se equivoca en la física en 78 de 90; pierde, pareado, contra una regla escrita a mano ($p = 0.022$). 600 ejemplos enseñaron el protocolo y no la física | P37–P40 |
| …y por debajo de su profundidad de entrenamiento, se pasa de rosca | entrenado sólo en cadenas de 6 a 9 pasos: 18 de 18 se pasó de rosca por debajo de esa banda; en problemas de tres pasos, la base pelada le gana, 0,167 a 0,000. **Un corpus con una sola dificultad enseña un piso** | P45 |
| **Destilación desde un maestro de frontera** | transfiere el procedimiento, no la aritmética: π/4·0,22² da 0,037006 en vez de 0,038013. Adaptador + calculadora 40/40; base + calculadora 0/40 con 53 llamadas; adaptador solo 4/40 | P5–P7 |
| **La aceptación como un ranking de expertos** contra un único target más grande | la precondición falló dos veces: un target *sin entrenar* puntúa debajo del mejor experto, 0,746 < 0,989 y 0,967 < 1,000; donde el target es fuerte, los grados saturan (`g75` ≡ `g600` = 1,000). Cerrado sin veredicto | P55, P55b, P58 |
| **La aceptación contra una API de frontera** | imposible, no sólo cara: sin logprobs para una continuación forzada, un tokenizer distinto | P48 |
| **La aceptación a nivel de caracteres** | mide formato, no acuerdo: respuestas idénticas puntúan 0,00 entre formatos; la concordancia entre targets pasó de 1/5 → 4/5 sólo porque un target indenta | S0–S2 |
| **Una frontera adelante de un 12B local** en la primera suite | ninguna lo estuvo: `gemini-3.5-flash-lite` 13/20, `gemini-3.8-flash` 13/20, `gemini-3.1-pro-preview` 8/20, contra `gemma4:12b` 12/20 gratis. Pagar 100× más puntuó peor | S1 |
| **El ruteo por caso** con reglas de escalamiento escritas a mano | peor que por región: 0,378 y 0,689 contra 0,775. Las reglas buscan cadenas inconsistentes; este experto escribe cadenas que son **coherentes y equivocadas** | P41 |
| …el acuerdo con la frontera como señal por caso | funciona — de acuerdo: 8 de 8 correctos; en desacuerdo: 60 de 61 equivocados — pero llama a la frontera todas las veces, así que compra calidad y **ningún ahorro** | P41 |
| **La composición** de un adaptador de protocolo con un adaptador de dominio | nunca se midió limpiamente: los dos corpus enseñaron notaciones distintas y cada brazo se puntuó bajo un solo prompt. Apilado 0/30 y mezclado 0/30 son reales y no dicen nada causal. Estacionado | P8, P9, P13 |
| **El uso de herramientas como una sola capacidad** | es dos: la *disposición* a preguntar transfiere ampliamente (un kernel de física hace que la base estire la mano hacia herramientas de email en 123 de 150 casos — con los nombres equivocados, 127 rechazadas); el *vocabulario* transfiere angostamente (el kernel de email nunca es rechazado y pregunta en 22). Los tres brazos empatan en exactitud | P31, P34, P35 |
| **Una máscara de gramática** sobre las llamadas a herramientas | compra prolijidad, no exactitud: rechazos 23 → 10, respuestas finales 5/30 → 4/30. De 30 fallas, 19 tenían cada llamada limpia | P8, P24 |
| **Una suite de código generada** | un adaptador memoriza formas: una cola por familia (180/180 completions held-out, textuales en el entrenamiento), después un esqueleto por (familia, corte), después ~60 formas cubiertas doce veces por 720 ejemplos. Se detuvo en tres | P52–P54 |
| **El experto de un tercero** de un hub de modelos | ninguno existe a este tamaño con herramientas y un verificador mecánico; en GSM8K la base ya está en 87,6 | P42 |
| **`Qwen3.5-4B` como base** bajo vLLM 0.29.0 | el adaptador se carga, se loguea, y se sirve la base. Leído durante cinco días como un límite del stack de serving; es nombres de tensores (§1, D2) | P33 |
| **Gemma 4 como base de PEFT** | `Gemma4ClippableLinear` no es `nn.Linear` | P29 |

## 3. Lo que las suites mismas resultaron ser

Las cuatro suites medidas alguna vez fallan al menos una de `training/suite_gates.py` — P50:
cada región de cada suite se sienta en exactamente una profundidad, así que región y dificultad son una
sola variable; la región se lee del prompt a 0,856 (fluidos) y 0,940 (triage);
la redacción de emails tiene una sola dificultad para los 180 casos. Y el hallazgo más profundo no tiene compuerta:
**una suite generada no puede contener una dificultad que nadie pensó.**

Un número de calibración tiene su propio techo, fijado por la información en la entrada: una brecha de AURC
de 0,400 leída como lugar para una cabeza tipada era 69–82 % la suite — P44, P46.

## 4. Instrumentos que mintieron

Cada uno produjo un número limpio y equivocado, y cada uno es ahora una regla en
[`../../CLAUDE.md`](../../CLAUDE.md) §3 o un test que falla.

| la mentira | cómo se descubrió |
|---|---|
| T4 reporta soporte bf16 que en realidad emula; la corrida puntuó 0/60, lo que se leyó como la falsificación del paso | capacidad de cómputo, no el flag — P2 |
| Gradient checkpointing dejado prendido durante la generación: 0/60 con él, 44/60 sin él | el brazo de control |
| Un corpus entrenado sobre el enunciado pelado, servido con el bloque de herramientas agregado: 71 rechazos de 606 que parecían física | el corpus tiene que enseñar el prompt que se sirve; los generadores *llaman* a `render_tools` — P38 |
| El mismo adaptador, los mismos casos, temperatura 0: 84, 81, 82 contra una compuerta de 83 | vLLM no es determinista de corrida a corrida; un veredicto se lee al lado del test pareado — P36/P38/P40 |
| "Le gana a la barra" dispara ~45 % de las veces por azar en un modelo que está parado en la barra | binomial exacto, y comparación pareada sobre fixtures compartidos (`bar.py`) |
| vLLM servido sin su parser de llamadas a herramientas: 240 de 240 pedidos HTTP 400, y la línea de progreso decía `correct 0` — lo que parece un modelo que no puede hacer la tarea | un brazo prueba que puede alcanzar sus herramientas antes de puntuar — P51 |
| 180/180 contra 56/180 de la base — y cada completion held-out estaba textual en el conjunto de entrenamiento | deduplicar sobre lo que se escribe, no sobre lo que se pregunta — P53 |
| Un `kb_pays` pre-registrado disparó 164 : 74 porque un default se había dado vuelta | la barra de mayoría lo guarda — P61 |
| Un miembro liberado sobre 60 casos con los pesos dejados en la tarjeta | el `eval_n` de la suite; el chain trae los adaptadores a casa — P64 intento 1 |
| `modules_with_weights: 531` para un adaptador que cayó en 0 de 178 módulos | vLLM activa tres LoRAs de relleno mientras perfila; 531 = 3 × 177. El chequeo de consistencia del brief lo atrapó — D2 |
| Guardas que leen el código fuente dispararon sobre prosa que describía la ausencia que verifican — cuatro veces | una guarda lee el código, no el archivo |
| `grep -c` imprime su cero y sale con 1; un rescate de pesos se saltó a sí mismo y costó un adaptador | `weights_in()` |

## 5. Trabajo relacionado, leído y no corrido **[read]**

- **Skill-to-LoRA** (arXiv 2606.16769): un `SKILL.md` convertido en un LoRA por skill sobre
  Qwen3.6-27B. 59 / 54 / 65 de 210 para sin skill / texto completo / adaptador — el signo de P61,
  con un efecto adentro del ruido ($z = 1.19$ y $0.65$, sin pareo, sin semillas). Un LoRA
  compartido entre skills perjudica. Su auto-destilación no transfiere a una base cuyo
  maestro base + documento hace cero llamadas a herramientas (P61).
- **Adaptive Minds** (arXiv 2510.15416): el modelo base lee metadata de adaptadores y nombra
  al miembro. El ruteo por palabra clave cae de 48,3 % a 5 adaptadores a 31,7 % a 30 — la
  falla predecible de un diccionario a medida que crece el pool, y la razón por la que existe el hito 2.
  Rutea por afinidad temática y por default cae a un adaptador general; acá una tabla medida decide
  qué se sirve localmente y el default es la frontera.
- **vLLM**: multi-LoRA sobre una base y atención en árbol ya se shippearon; un drafter adaptado con
  LoRA para decodificación especulativa es un RFC (#52038). Una cabeza de draft entrenada sobre los
  estados ocultos del target existe para el 32B y le gana a todo esto en latencia — por eso la
  aceptación acá nunca fue una afirmación de velocidad.
