# Guía — entender lora-kernel desde cero

*Para personas, no para modelos.* Esta guía explica, con palabras y ejemplos, todas las piezas que usa este
repositorio: cómo genera texto un modelo de lenguaje, qué hacen los motores de inferencia (llama.cpp, vLLM, MLX), qué
es la cuantización, qué es un LoRA, cómo funciona la decodificación especulativa (con un modelo borrador, con MTP y con
EAGLE), cómo se sirven muchos expertos sobre una sola GPU, y cómo encaja todo en lo que perseguimos. Después cuenta,
en orden, qué fuimos desbloqueando y qué falta.

La matemática rigurosa vive en [`FOUNDATIONS.md`](FOUNDATIONS.md); acá está la intuición, con un enlace a la sección
formal cada vez que hace falta. Los resultados medidos viven en [`RECORD.md`](RECORD.md) y el estado vivo en
[`PLAN.md`](PLAN.md).

**Una convención que vas a ver en todo el repositorio.** **[read]** marca algo que sabemos por leer (un paper, una
documentación, código ajeno). **[ran]** marca algo que observamos corriéndolo acá, con el directorio de la corrida. Lo
que no tiene marca se trata como [read]. La regla existe porque un proyecto anterior de esta organización llegó a
18.680 líneas con tres tests: leer no es medir.

---

## 1. Qué perseguimos, en una página

Una organización que funciona con agentes — un agente por rol: atención al cliente, compras, IT, docentes — le manda
cada tarea a un modelo de frontera en la nube (OpenAI, Anthropic, Google). Muchas de esas tareas se repiten: leer una
agenda, abrir un ticket, contestar desde una lista. La tesis de este repositorio es que **esa parte repetitiva la puede
hacer un modelo chico, local, especializado**, y la frontera queda para lo que no cae en ningún terreno medido.

Las piezas, de adentro hacia afuera:

- **Un modelo base chico, residente en una GPU** (hoy Gemma 4 E4B, y Gemma 4 12B como mitad grande).
- **Un experto por tarea, como un LoRA** — un parche liviano sobre el modelo base. Cambiar de experto es cambiar de
  parche, no de modelo.
- **Una memoria por experto**: páginas de enunciados cortos y verificables. El LoRA no memoriza los hechos; aprende a
  *recorrer* la memoria y a citar el enunciado en el que se apoya.
- **Un gateway** delante: verifica la identidad, decide el rol, ejecuta las herramientas con permisos que el modelo no
  puede cambiar, retiene lo que necesita aprobación y ancla cada respuesta en lo que las herramientas devolvieron.
- **Una salida a la frontera** para lo que ningún experto cubre.
- **Un par especulativo** (chico + grande) para ganar velocidad sin perder calidad.

Y una regla de método: **cada afirmación se mide contra nuestra propia versión anterior**, con la condición que la
falsearía escrita *antes* de correr.

---

## 2. Cómo genera texto un modelo de lenguaje

### 2.1 Tokens

Un modelo no ve letras: ve **tokens**, pedazos de texto sacados de un vocabulario fijo (en Gemma 4, 262.144 tokens).
"refrigerador" puede ser un token o tres. El texto entra como una lista de números (ids) y sale como otra lista de
números que se vuelven a convertir en texto. Detalle en [`FOUNDATIONS.md`](FOUNDATIONS.md) §3.

Por qué importa acá: **dos modelos sólo pueden hacer decodificación especulativa juntos si comparten el mismo
vocabulario** — el borrador propone ids que el grande tiene que poder verificar. Gemma 4 E4B y Gemma 4 12B tienen
vocabularios idénticos byte a byte **[ran]** B2.

### 2.2 Un token por vez

Generar es un bucle: el modelo mira todo el texto hasta ahora, calcula una **distribución de probabilidad** sobre el
próximo token (los *logits*, normalizados), elige uno, lo agrega y repite. Elegir siempre el más probable se llama
**greedy** o **temperatura 0**: es determinista *en teoría* — en la práctica, ver §8.4.

### 2.3 Prefill y decode: dos regímenes muy distintos

- **Prefill**: procesar el prompt entero. Es una sola pasada sobre todas las posiciones a la vez — mucha cuenta, bien
  aprovechada por la GPU.
- **Decode**: generar cada token nuevo. Cada paso procesa *una* posición… pero tiene que **leer todos los pesos del
  modelo desde la memoria**. Un 12B en bf16 son ~24 GB por paso.

Por eso generar es lento aunque la GPU sea rápida: **el cuello de botella no es multiplicar, es mover pesos desde la
memoria** (*memory-bound*). Esta sola idea explica casi todo lo que sigue: la cuantización (pesos más chicos → menos
bytes por paso), el batching (varios pedidos comparten una lectura) y la decodificación especulativa (verificar varios
tokens con una sola lectura). Ver [`FOUNDATIONS.md`](FOUNDATIONS.md) §2.3.

### 2.4 La caché KV

Para no recalcular todo en cada paso, el modelo guarda de cada capa unas matrices intermedias (claves y valores de la
atención) de los tokens ya vistos: la **caché KV**. Hace el decode rápido a cambio de memoria, que crece con el largo
del texto y con cuántos pedidos atendés a la vez. Gestionarla bien es el problema central de un servidor (§3.2).

---

## 3. Los motores de inferencia

Un modelo es un archivo de pesos. Un **motor de inferencia** es el programa que lo carga y genera texto rápido. Tres
nos importan.

### 3.1 llama.cpp (y Ollama)

**[read]** llama.cpp es un motor en C/C++ pensado para correr modelos en hardware común: CPU, Apple Silicon (Metal),
GPUs de consumo. Sus rasgos:

- **Formato GGUF**: un archivo único con pesos y metadatos, típicamente **cuantizado** (§4) con esquemas como `Q4_K_M`
  u `Q8_0`. Es lo que permite correr un 12B en una laptop.
- **Un pedido a la vez, muy bien**: está optimizado para latencia de un usuario; el servidor (`llama-server`) expone
  una API compatible con OpenAI y soporta varios pedidos en paralelo, pero no está pensado para cientos a la vez.
- **LoRA**: se puede cargar un adapter al arrancar, y el servidor permite ajustar la escala de los adapters cargados
  en tiempo de ejecución — verificar con la versión que uses.
- **Decodificación especulativa con un modelo borrador** (`--model-draft`).
- **Ollama** está construido sobre llama.cpp (y, en versiones recientes, sobre MLX en Mac): empaqueta modelos (`gemma4:12b`,
  `gemma4:12b-mlx`) con una receta (`Modelfile`) que puede incluir un `ADAPTER` LoRA **fijado al crear el modelo**. No es
  un cambio por pedido.

Cuándo conviene: un usuario, una máquina local, poca memoria. Nuestro análisis de 2026-09 lo comparó con vLLM y quedó
vLLM para desarrollo por una razón concreta: **servir muchos LoRA por pedido y medir con las mismas herramientas en todo
el proyecto**.

### 3.2 vLLM

**[read]** (Kwon et al. 2023) vLLM es un motor de servidor, pensado para **muchos pedidos concurrentes** en GPU:

- **PagedAttention**: guarda la caché KV en bloques fijos con una tabla de páginas por pedido, como la memoria virtual
  de un sistema operativo. Pedidos de distinto largo conviven sin desperdicio.
- **Continuous batching**: un pedido nuevo entra al lote en cualquier paso, sin esperar a que terminen los demás. Es lo
  que convierte "varios pedidos comparten una lectura de pesos" (§2.3) en rendimiento real.
- **API compatible con OpenAI** (`vllm serve`): cualquier cliente que hable con OpenAI habla con vLLM.
- **Multi-LoRA**: muchos adapters residentes a la vez, y **cada pedido elige el suyo por el campo `model`**; en un mismo
  lote, cada pedido usa su LoRA (§5.4). Los adapters se pueden **cargar y descargar en caliente** con
  `VLLM_ALLOW_RUNTIME_LORA_UPDATING` y los endpoints `/v1/load_lora_adapter` — **0,23–0,28 s por adapter [ran] F0**.
- **Decodificación especulativa** con modelo borrador, n-gramas, EAGLE/EAGLE-3 y MTP (§6), configurada al arrancar
  con `--speculative-config`.

Es el motor de todo este repositorio: corre en GPUs alquiladas en Colab (L4, A100) a través de
`training/harness/chain_serve.sh`. Versión actual acá: 0.30.0.

### 3.3 MLX (y mlx-lm, mlx-vlm)

**[read]** MLX es el framework de Apple para su **memoria unificada**: en un Mac con Apple Silicon, CPU y GPU comparten
la misma memoria, así que un modelo no se copia entre ellas. `mlx-lm` genera y entrena texto; `mlx-vlm` agrega los
modelos multimodales.

Lo que encontramos al leer su código (2026-09-27):

- El 12B de Gemma 4 es multimodal (`gemma4_unified`): **lo carga `mlx-vlm`, no `mlx-lm`**.
- El servidor de `mlx-lm` acepta un adapter por pedido, pero **al cambiarlo recarga el modelo entero** — no es un
  cambio en caliente.
- `mlx-vlm` trae el **drafter MTP de Gemma 4** (`gemma4_unified_assistant`) y uno EAGLE-3.

Por eso la pista Mac de este proyecto construye su propio cambio en caliente: el modelo base se carga una vez y cada
capa lleva los parches de todos los expertos; cambiar de experto es cambiar un puntero (§5.5).

### 3.4 Cuál usar, en una tabla

| | llama.cpp / Ollama | vLLM | MLX |
|---|---|---|---|
| hardware | CPU, Mac, GPU de consumo | GPU NVIDIA (y otras) | Apple Silicon |
| fuerte en | un usuario, poca memoria | muchos pedidos, muchos LoRA | Mac, memoria unificada |
| LoRA por pedido | limitado | **sí, nativo** | no nativo (lo construimos) |
| especulativa | modelo borrador | borrador, EAGLE-3, MTP | borrador, MTP (mlx-vlm) |
| acá | comparado, no usado | **el motor del proyecto** | pista Mac (2026-09-27) |

---

## 4. Cuantización: pesos más chicos

Los pesos se guardan como números. En **bf16/fp16** ocupan 2 bytes cada uno: un 12B ≈ 24 GB. Cuantizar es guardarlos
con menos bits:

- **FP8** (1 byte): la mitad. Las GPUs recientes (L4, H100) lo aceleran en hardware. vLLM puede cuantizar a FP8 al
  cargar (`--quantization fp8`). **Así corrimos el 12B en una L4 de 24 GB [ran] F0.**
- **INT4 / 4 bits** (½ byte): AWQ y GPTQ en GPU; `Q4_K_M` en GGUF; 4 bits "affine" en MLX. Un 12B entra en ~7 GB — por
  eso corre en tu Mac de 16 GB.

El costo es una pequeña pérdida de precisión numérica. Dos consecuencias prácticas acá:

1. **Un LoRA entrenado sobre pesos bf16 se puede aplicar sobre pesos cuantizados** (QLoRA hace justamente eso al
   entrenar). Lo verificamos: el LoRA del 12B, entrenado en bf16, queda aplicado sobre el 12B en FP8 **[ran] F0**
   (G1, §8.2).
2. **Los números no se comparan entre precisiones como si fueran iguales**: un resultado en MLX 4 bits no es el mismo
   experimento que uno en vLLM bf16.

Detalle: [`FOUNDATIONS.md`](FOUNDATIONS.md) §4.3.

---

## 5. LoRA: un experto como parche

### 5.1 La idea

Ajustar un modelo entero (*fine-tuning* completo) cambia miles de millones de pesos y produce otro modelo del mismo
tamaño. **LoRA** (Hu et al. 2021) **[read]** congela los pesos y aprende, para algunas matrices, una corrección de
**rango bajo**:

$$W' = W + \tfrac{\alpha}{r}\,A\,B$$

donde $A$ y $B$ son dos matrices finitas (rango $r$, acá 16). En vez de cambiar $W$ (millones de números) se aprenden
$A$ y $B$ (miles). Un LoRA del 12B pesa ~140 MB contra ~24 GB del modelo. Ver [`FOUNDATIONS.md`](FOUNDATIONS.md) §4.1.

### 5.2 Por qué es la pieza central

Como $W$ nunca se toca, **el modelo base queda residente y lo único que cambia entre expertos es el parche**. Se puede:

- cambiar por pedido;
- mezclar pedidos de distintos expertos en un mismo lote;
- versionar, publicar y descartar un experto sin tocar la base.

*El sistema es un conjunto de parches sobre una base residente.*

### 5.3 Cómo se entrena acá

- Con **PEFT** (Hugging Face), en Colab, sobre las siete proyecciones de atención y MLP de cada capa, $r = 16$,
  $\alpha = 32$.
- En Gemma 4 hay que **excluir las torres de visión y audio**: sus proyecciones son de otro tipo y PEFT no las acepta
  (fue el bloqueo P29; `training/s4_train.py::towers_to_exclude`).
- El corpus es **exactamente lo que el modelo va a ver cuando se lo sirva**: el mismo prompt de sistema, el mismo
  bloque de herramientas, el mismo formato. Un corpus que enseña otro prompt enseña otra cosa (§8).

### 5.4 Servir muchos LoRA a la vez

**[read]** (Punica, Chen et al. 2023; S-LoRA, Sheng et al. 2023) En un lote donde cada pedido usa un experto distinto,
la parte común ($xW$) se calcula una sola vez para todos y la corrección de cada uno se calcula con kernels que
"juntan" los $A_i, B_i$ de cada pedido. vLLM lo hace con `--enable-lora --lora-modules nombre=ruta`, y el pedido elige
su experto con el campo `model`. Ver [`FOUNDATIONS.md`](FOUNDATIONS.md) §5.2.

### 5.5 Cambio en caliente: qué significa de verdad

Hay tres cosas distintas que se llaman "cambio de LoRA":

| | cómo | costo |
|---|---|---|
| **recargar** | descargar el modelo y volver a cargarlo con otro adapter | segundos (lo que hace el servidor de `mlx-lm`) |
| **cargar en caliente** | agregar un adapter nuevo a un servidor corriendo | **0,23–0,28 s en vLLM [ran] F0** |
| **elegir por pedido** | todos los adapters residentes, cada pedido usa el suyo | casi cero (vLLM; nuestra pista Mac) |

### 5.6 La trampa del adapter que no se aplica

Un motor puede decir "adapter cargado" y responder con el modelo base, sin error. Nos pasó (C18: los nombres de los
tensores no coincidían con el modelo servido). Por eso **todo experto pasa la compuerta G1 antes de medirse**: la misma
pregunta al base y al experto tiene que dar textos distintos (§8.2).

---

## 6. Decodificación especulativa

### 6.1 La idea

Generar con el modelo grande es lento porque cada token es una lectura completa de pesos (§2.3). Pero verificar **k
tokens propuestos** cuesta casi lo mismo que generar uno: se procesan todos en una sola pasada. Entonces:

1. Un **borrador** rápido propone k tokens.
2. El modelo grande los **verifica todos en una pasada**.
3. Se aceptan de izquierda a derecha mientras coinciden con lo que el grande habría elegido; en el primer desacuerdo,
   el grande pone su token y la ronda termina.

**La salida es exactamente la del modelo grande** — con cualquier borrador. Un borrador malo cuesta velocidad, nunca
calidad **[read]** (Leviathan et al. 2023; Chen et al. 2023). A temperatura 0 la regla es simple: se acepta un token si
es exactamente el que el grande habría elegido. Demostración: [`FOUNDATIONS.md`](FOUNDATIONS.md) §6.1–6.3.

### 6.2 Cuánto rinde: α y el largo aceptado

- **α (aceptación)**: la fracción de tokens propuestos que se aceptan.
- **Largo medio aceptado**: cuántos tokens se emiten por cada pasada del grande (incluye el que pone el grande).

Si cada token se acepta con probabilidad α independiente y se proponen k:

$$\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}$$

tokens por pasada. La aceleración real depende además de cuánto cuesta el borrador ([`FOUNDATIONS.md`](FOUNDATIONS.md) §6.4).
Con batch grande rinde menos: la GPU ya está ocupada con otros pedidos y "verificar gratis" deja de ser gratis.

### 6.3 Tres tipos de borrador

| | qué es | ve al modelo grande | acá |
|---|---|---|---|
| **modelo borrador** | un modelo chico completo con el mismo vocabulario (E4B para el 12B) | no: genera por su cuenta | B4 midió su aceptación |
| **EAGLE / EAGLE-3** **[read]** | una cabeza chica que predice a partir de los *estados ocultos* del grande | sí | EAGLE-3 público de BCCard, F0 |
| **MTP** (*multi-token prediction*) **[read]** | el borrador que Google publicó con Gemma 4 (`-assistant`): 4 capas que usan las activaciones y la caché del grande | sí | **el que mejor rindió, F0** |

La diferencia importa para los expertos: un borrador que **ve las activaciones del grande** "ve" también el efecto del
LoRA activo, así que un único borrador podría servir a todos los expertos.

### 6.4 El problema del LoRA: el borrador no fue entrenado con él

El MTP de Gemma 4 se entrenó mirando al 12B **sin** LoRA. Con el LoRA activo, el grande escribe distinto — con el
estilo y el formato del experto — y el borrador acierta menos. **Lo medimos [ran] F0:** en las preguntas del propio
experto, la aceptación en la primera posición cae de 0,98 a 0,58 y la aceleración de 2,73× a 1,74×.

Cómo se cierra esa brecha (el documento de estrategias del usuario, 2026-09-27):

- **A. Un borrador compartido**, entrenado con respuestas de todos los expertos.
- **B. Un borrador base + un LoRA de borrador por experto**, elegido junto con el LoRA del grande (vLLM no lo soporta
  todavía; es una propuesta, RFC #52038).
- **C. Un borrador completo por experto**: el techo de aceptación, caro en GPU.
- **D. Reentrenar el MTP nativo por experto.**

---

## 7. De un modelo a un sistema

### 7.1 La memoria: páginas de enunciados atómicos

Un LoRA que memoriza hechos se equivoca cuando los hechos cambian y no puede mostrar de dónde sacó un dato. El diseño
del usuario (2026-09-24) separa las dos cosas:

- **La memoria** es una wiki de páginas; cada página es una lista de **enunciados de una oración**, verificables, con
  los enlaces *dentro* de los enunciados ("El film Lumo-410 se guarda en el depósito Old Mill").
- **El LoRA aprende la trayectoria**: buscar, abrir una página, abrir el enunciado, seguir el enlace, y **citar**
  `[id§ancla]` el enunciado en el que se apoya. El "árbitro" verifica la cita mecánicamente.

**[ran]** W9: sobre un mundo que el modelo nunca vio, el modelo sin entrenar recorre 19/40 preguntas de varios saltos
(Gemma); entrenado en otros mundos, 38/40. Una habilidad que el corpus no mostró (comparar) no se aprende (10/40);
mostrada, sí (37/40) **[ran]** B3, B5. Detalle: [`MEMORY.md`](MEMORY.md).

### 7.2 El router y la frontera

Decidir *qué experto* atiende un pedido es un clasificador que también tiene que saber decir "ninguno". Probamos un
modelo de n-gramas, embeddings (Qwen3-Embedding y EmbeddingGemma) y un clasificador chico: **ninguno pasó** — todos
pierden pedidos legítimos de remitentes que no vieron **[ran]** M2, E1. En producción, **el rol del usuario (que viene
en su token) es la ruta**, y lo que el rol no cubre va a la frontera o a una persona según la política del rol.

### 7.3 Agentes y el gateway

**OpenClaw** es un runtime de agentes: cada agente habla con "un modelo" por una API compatible con OpenAI. El gateway
de este repositorio se pone en ese lugar:

1. **Identidad**: un token firmado dice usuario, rol y escuela. El modelo no puede cambiarlo.
2. **Turno**: el prompt y las herramientas del rol, sobre el experto local.
3. **Permisos en las herramientas**: pedir el registro de otra escuela lo rechaza la herramienta, escriba lo que escriba
   el modelo.
4. **Retenciones**: un cobro o un aviso a todas las familias espera la aprobación de un director.
5. **Anclaje**: cada renglón de la respuesta tiene que estar en lo que devolvieron las herramientas; si no, se muestra el
   texto de la herramienta — y se cuenta.
6. **Salida**: lo que el rol no cubre va a la frontera (Claude Haiku en la corrida en vivo) o a una persona.

**[ran]** la escuela del diagrama de referencia, 15/15 escenas guionadas y 15/15 **a través del OpenClaw real** con el
modelo real y Haiku como frontera. Lo que enseñó el primer turno en vivo: OpenClaw agrega su propio contexto como último
mensaje; el gateway tiene que leer el pedido real dentro de eso. Ver [`OPENCLAW.md`](OPENCLAW.md) §6, [`DEMO.md`](DEMO.md).

---

## 8. Cómo medimos (y por qué así)

### 8.1 Primero el margen

Antes de construir un tratamiento se mide si **puede** mover algo: si el modelo sin entrenar ya saca 10/10, ningún
tratamiento puede mejorar y todos empatan — y un empate se lee como éxito. Al revés, si todo está fuera de alcance,
todo falla y se lee como "no funciona". Una batería necesita un eje de dificultad.

### 8.2 G1: ¿está aplicado el experto?

Tres preguntas al base y al experto; si ninguna cambia, el adapter no se aplicó. Un hallazgo de este mes: en un experto
entrenado sólo con turnos de herramientas, las preguntas genéricas pueden cambiar poco (1 de 3) aunque el adapter esté
aplicado; por eso G1 ahora repite con preguntas del dominio, con la misma regla **[ran]** M9.

### 8.3 Comparar de a pares

Dos variantes sobre los mismos casos se comparan **caso por caso**: sólo cuentan los casos donde difieren (uno acierta y
el otro no). Con $b$ casos a favor de A y $c$ a favor de B, la prueba exacta de signos:

$$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$$

Así "53 a 0" es una diferencia real y "5 a 6" es un empate, aunque los totales parezcan distintos. Ver
[`FOUNDATIONS.md`](FOUNDATIONS.md) §9.2.

### 8.4 Temperatura 0 no garantiza la misma salida

En teoría, greedy es determinista. En una GPU, **la misma pregunta puede dar otro texto si cambia el tamaño del lote**:
las sumas en punto flotante se hacen en otro orden, y en un empate casi exacto entre dos tokens gana el otro. vLLM tiene
un modo invariante al lote (`VLLM_BATCH_INVARIANT=1`) para cuando hace falta comparar textos exactos. **[ran] F0:** sin
ese modo, la decodificación especulativa dio textos distintos de la normal en parte de los casos — y el mismo LoRA
recargado *sin* borrador también. Mientras no se repita en modo invariante, "salida idéntica" no está establecida.

### 8.5 Pre-registrar

Cada corrida tiene un `BRIEF.md` escrito **antes**: qué, por qué, con qué modelo, qué la falsea y la tabla de veredictos.
Se cuentan los rediseños: uno está bien, dos es sospechoso, el tercero ya busca el resultado.

### 8.6 Los instrumentos mienten de pocas maneras

Una lista pagada con tiempo ([`CLAUDE.md`](../../CLAUDE.md) §3, [`RECORD.md`](RECORD.md) §4): una batería en el techo; una
verificación de una palabra que mide redacción; un corpus con una sola dificultad que enseña un piso; un conocimiento
fijo en el corpus que se memoriza; un modelo sin el prompt con el que se entrenó; una clave que la cadena lee como
"terminado" (nos pasó la semana pasada).

---

## 9. Qué fuimos desbloqueando

| cuándo | qué se desbloqueó | cómo lo sabemos |
|---|---|---|
| 2026-09 | un experto por tarea sobre un modelo chico, publicado por una compuerta | M1, M1b, M1d **[ran]** |
| 2026-09-15 | un runtime de agentes real (OpenClaw) usando un experto local | P63, 40/40 **[ran]** |
| 2026-09-24 | la memoria como páginas de enunciados atómicos, con citas verificables | W9, 35/40 → 38/40 en Gemma **[ran]** |
| 2026-09-25 | toda la familia en Gemma 4 (decisión del usuario, sobre un empate medido) | B1 **[ran]** |
| 2026-09-26 | el par E4B + 12B: comparten vocabulario, el LoRA del grande sube la aceptación | B2, B4 **[ran]** |
| 2026-09-26 | el grande no compra precisión; el corpus sí (comparaciones 10 → 37/40) | B3, B5 **[ran]** |
| 2026-09-26 | la escuela del diagrama completa, 15/15, y **en vivo** con OpenClaw y Haiku | DEMO-school-diagram, LIVE **[ran]** |
| 2026-09-26 | la distribuidora con su propio experto, 5/5 | M9 **[ran]** |
| 2026-09-27 | **decodificación especulativa con un LoRA experto sobre el 12B, en un servidor** | F0 **[ran]** |

---

## 10. Lo que todavía no funciona, y el próximo paso de cada uno

| qué | estado | próximo paso |
|---|---|---|
| salida idéntica con especulativa | no establecida | repetir F0 con `VLLM_BATCH_INVARIANT=1` y un control |
| el borrador con el LoRA activo | pierde aceptación en el dominio (1,74×) | estrategias A–D (§6.4), empezando por la más barata |
| la pista Mac | programa listo, sin correr | 12B en MLX con cambio de LoRA en caliente y MTP |
| router aprendido | ninguno pasa | el rol es la ruta; queda abierto |
| buscador de notas con embeddings | 0,63 contra 0,80 | búsqueda por palabras en uso |
| tráfico real | todo es sintético | una muestra anonimizada de un sistema en uso |
| el modelo todavía inventa | 3 de 12 respuestas las atrapa el filtro | un corpus que enseñe a repetir sólo lo que dice la herramienta |
| identidad real (Auth0), WhatsApp, concurrencia, instalación | no construidos | después de lo anterior |

---

## 11. Glosario

- **Adapter / LoRA**: el parche de rango bajo que convierte al modelo base en un experto (§5).
- **α (aceptación)**: fracción de tokens del borrador que el modelo grande acepta (§6.2).
- **bf16, FP8, 4 bits**: precisiones de los pesos (§4).
- **Borrador (drafter)**: el modelo o cabeza que propone tokens en la especulativa (§6.3).
- **Caché KV**: lo que el modelo guarda de los tokens ya vistos para no recalcularlos (§2.4).
- **Continuous batching**: sumar pedidos a un lote en marcha (§3.2).
- **EAGLE-3**: borrador que predice desde los estados ocultos del grande (§6.3).
- **Frontera**: un modelo grande en la nube (Haiku, Gemini) para lo que ningún experto cubre.
- **G1**: la compuerta que verifica que un adapter esté aplicado (§8.2).
- **Gateway**: el servidor delante del modelo que maneja identidad, permisos, retenciones y anclaje (§7.3).
- **GGUF**: el formato de archivo de llama.cpp (§3.1).
- **MTP**: *multi-token prediction*; el borrador nativo de Gemma 4 (§6.3).
- **OpenClaw**: el runtime de agentes que usa el sistema de referencia (§7.3).
- **PagedAttention**: la gestión en páginas de la caché KV en vLLM (§3.2).
- **Prefill / decode**: procesar el prompt / generar cada token (§2.3).
- **[read] / [ran]**: leído / corrido acá.

---

## 12. Fuentes

**Papers [read]:** Hu et al. 2021 (LoRA) · Kwon et al. 2023 (vLLM, PagedAttention) · Leviathan et al. 2023 y Chen et al.
2023 (decodificación especulativa) · Chen et al. 2023 (Punica) · Sheng et al. 2023 (S-LoRA) · Gemma 4 Technical Report
(arXiv 2607.02770).

**Documentación y código [read], 2026-09-27:**
- [vLLM — Speculative Decoding](https://docs.vllm.ai/en/latest/features/speculative_decoding/) y
  [matriz de compatibilidad](https://docs.vllm.ai/en/latest/features/)
- [vLLM PR #21068 — LoRA con decodificación especulativa (mergeado)](https://github.com/vllm-project/vllm/pull/21068) ·
  [PR #55628 (cerrado sin mergear)](https://github.com/vllm-project/vllm/pull/55628) ·
  [RFC #52038 — LoRA en borradores](https://github.com/vllm-project/vllm/issues/52038) ·
  [test_lora.py](https://github.com/vllm-project/vllm/blob/main/tests/v1/e2e/spec_decode/draft_model/test_lora.py)
- [Google — MTP para Gemma 4](https://ai.google.dev/gemma/docs/mtp/overview) ·
  [google/gemma-4-12B-it-assistant](https://huggingface.co/google/gemma-4-12B-it-assistant)
- [BCCard — EAGLE-3 para gemma-4-12B-it](https://huggingface.co/BCCard/MoAI-gemma-4-12B-it-speculator.eagle3)
- [mlx-lm — servidor](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/server.py) ·
  [mlx-vlm — drafter MTP de Gemma 4](https://github.com/Blaizzy/mlx-vlm/blob/main/mlx_vlm/speculative/drafters/gemma4_assistant/README.md) ·
  [mlx-optiq — especulativa de Gemma 4 en Apple Silicon](https://mlx-optiq.com/blog/gemma-spec-decoding)

**Nuestras corridas [ran]:** [`RECORD.md`](RECORD.md) las lista todas; las de esta guía: W9, B1–B5, M8, M9, DEMO-school-diagram,
LIVE-school-openclaw, E1 y F0, cada una en `results/` con su `BRIEF.md`.
