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
el proyecto**. Desde el 2026-09-28 llama.cpp es también, por decisión del usuario, el **runtime de servido edge** — el
perfil que pone a un miembro delante de un runtime de agentes en vivo en la propia máquina del usuario, una vez que el
entrenamiento y la medición ya se hicieron en el perfil de servidor (§3.5).

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

Por eso la pista Mac de este proyecto construyó su propio cambio en caliente: el modelo base se carga una vez y cada
capa lleva los parches de todos los expertos; cambiar de experto es cambiar un puntero (§5.5). ~~MLX queda como motor
`edge`~~ — desde el 2026-09-28 eso quedó superado (§3.5): el veredicto detrás era sobre decodificación especulativa
nada más, y sigue en pie en esa pregunta angosta. MLX sigue siendo el **banco de investigación**: es el único runtime
con acceso desde Python al grafo mismo, que es lo que necesita el truco del puntero del cambio en caliente.

### 3.4 Cuál usar, en una tabla

| | llama.cpp / Ollama | vLLM | MLX |
|---|---|---|---|
| hardware | CPU, Mac, GPU de consumo | GPU NVIDIA (y otras) | Apple Silicon |
| fuerte en | un usuario, poca memoria | muchos pedidos, muchos LoRA | Mac, memoria unificada |
| LoRA por pedido | limitado | **sí, nativo** | no nativo (lo construimos) |
| especulativa | modelo borrador | borrador, EAGLE-3, MTP | borrador, MTP (mlx-vlm) |
| acá | **perfil de servido edge (2026-09-28)** | **perfil de servidor — entrenamiento, medición** | banco de investigación (acceso desde Python al grafo) |

### 3.5 Dos perfiles, la decisión del usuario (2026-09-28)

El proyecto ahora nombra dos perfiles de runtime en vez de decidir caso por caso qué motor usar:

- **`server`** es vLLM en Colab: toda corrida de entrenamiento y toda medición de este repositorio pasa por ahí, por
  una razón que no cambia con el hardware — **la misma herramienta, los mismos números, en todo el proyecto** (§8).
- **`edge`** es **llama.cpp en la propia máquina del usuario** (una MacBook Air M4, 16 GB): sirve un miembro a un
  runtime de agentes en vivo. **[ran] MAC2:** llama.cpp build 11146 carga el E4B, el LoRA del 12B actúa una vez
  convertido a GGUF (6/6), y `POST /lora-adapters` lo cambia en **3 ms**, restaurando el base exacto — el mismo
  comportamiento de cambio-y-restauración que mostró MLX en 2,9 µs, en otro motor. Servir el E4B como **Q8_0**, no
  Q4_0: Q4_0 invierte el id de orden con la propia caché de prompt de llama.cpp **[ran]** LIVE-distributor — una
  elección de cuantización que cambia *qué token* sale, no sólo cuán rápido.

Esto no revierte el hallazgo de MAC sobre decodificación especulativa en la Mac: el drafter MTP de Gemma sigue
frenando al 12B ahí (0,52× con el LoRA del experto en su propio dominio, 0,66–0,87× en el resto, **[ran]** MAC2), y el
par E4B+12B juntos siguen sin entrar en 16 GB de Metal. Lo que cambió es más angosto y más barato de decir: para
*servir* un miembro — sin par especulativo, sin un segundo modelo residente — llama.cpp en la Mac es lo que corre el
usuario, y MLX queda para la investigación que necesita entrar al grafo.

### 3.6 Caché de prefijo: lo que la derrota es el orden, no el tamaño

vLLM (y llama.cpp) pueden reusar la caché KV del prefijo compartido de un prompt entre pedidos, así que un bloque de
herramientas que todo pedido repite debería, en principio, calcularse una sola vez. **[ran] E5:** no fue así. El bloque
de 54 herramientas de OpenClaw (7.205 tokens de Gemma) servido exactamente como se entrenó al miembro — el pedido
primero, el bloque de herramientas después, dentro del mismo turno de usuario — hizo que el TTFT pasara de 0,10 s a
1,70 s (16,8×) y que el rendimiento en b8 bajara de 132 a 108 tok/s; la precisión cayó con eso, de 70/70 a 39/70,
porque el miembro dejó de llamar a su propia herramienta en 28 de 31 fallas. Poner ese mismo bloque *antes* del
pedido en cambio — el único cambio que deja que una caché lo reuse como un prefijo literal — no cuesta nada: 0,09–0,11
s, indistinguible de la línea base podada.

**Por qué [read]:** una caché de prefijo indexa por los bytes exactos que encabezan un prompt. Dos pedidos que
difieren en sus primeros cientos de tokens nunca comparten una entrada de caché por más idéntico que sea el resto —
así que el *tamaño* de un bloque nunca fue la variable que importaba; su *posición* sí. Por eso podar sigue siendo el
default acá en los dos ejes: el corpus nunca se entrenó con el bloque primero, así que moverlo entrenaría a otro
miembro, no sería un cambio de formato. **[ran] E5** también encontró que dos LoRA compartiendo un mismo lote
mantienen 0,88 del rendimiento de uno solo (contención al límite de una ráfaga de 16) — chico al lado del efecto de la
caché, pero real.

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

```math
W' = W + \tfrac{\alpha}{r}\,A\,B
```

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

**¿Mezclar expertos en un mismo servidor cuesta algo? [ran] C1** (`results/C1-concurrency-20260929`, una L4, vLLM
0.30, cuatro miembros mezclados — `school-s0`, `upper-s0`, `staff-s0`, `out-s0`): sin contención material. 16
sesiones repartidas entre los cuatro adapters llegan a 278,6 tok/s contra 269,7 tok/s de las mismas 16 sesiones sobre
un solo adapter (1,03×); 32 sesiones entre los cuatro llegan a 504 tok/s, TTFT p95 0,24 s, 0 errores de 128 pedidos;
el rendimiento escala casi linealmente de 1 a 32 sesiones concurrentes (22,7 → 135 → 270 → 500 tok/s), y el techo
todavía está por encima de 32. Esto reemplaza la lectura de E5 en §3.6, 0,88 para dos LoRA compartiendo un lote — ese
número valía al límite de una ráfaga de 16; C1 es la misma pregunta a la escala que un gateway en vivo vería de
verdad.

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

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}
```

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

### 6.5 Cambiar en caliente: el LoRA sí, el borrador todavía no

Lo que queremos es un servidor con **un modelo base**, **N expertos** y, para cada uno, **un borrador ajustado a ese
experto**, todo intercambiable por pedido. Son dos cosas distintas que cambiar en caliente, y hoy están en lugares
muy distintos.

**El LoRA del modelo grande — funciona hoy.**

| dónde | cómo | medido |
|---|---|---|
| vLLM | todos los LoRA residentes; cada pedido elige el suyo por el campo `model`; se agregan y quitan con `/v1/load_lora_adapter` | carga en caliente **0,23–0,28 s**, también con el borrador encendido **[ran] F0** |
| Mac (MLX, nuestro código) | cada capa lleva los parches de todos los expertos; uno activo; cambiar es mover un puntero | **2,9 µs**, y el texto del base vuelve exacto **[ran] MAC** |
| Mac (llama.cpp, perfil `edge`) | el LoRA se convierte a GGUF una vez; `POST /lora-adapters` lo cambia sobre un servidor corriendo | **3 ms**, base restaurado exacto, salida de especulativa idéntica 20/20 **[ran] MAC2** |

**El borrador (MTP, EAGLE, un modelo chico) — un solo borrador por servidor.**

- En vLLM el borrador se fija **al arrancar** (`--speculative-config`) y es **uno solo para todo el servidor**: no hay
  un borrador por pedido, ni forma de cambiarlo sin reiniciar **[read]** documentación de vLLM.
- vLLM **no aplica LoRA a un borrador**: la propuesta existe (RFC #52038, para los borradores DFlash) pero no está
  implementada **[read]**.
- El borrador MTP de Gemma 4 **no se puede reentrenar con `speculators`**: su "MTP finetuning" cubre las cabezas MTP que
  vienen dentro del checkpoint (Qwen3-Next, Qwen3.5), no el `assistant` externo de Gemma 4 **[read]**.

**Qué pasa hoy con un borrador y varios LoRA.** Funciona, y la salida sigue siendo la del modelo grande (§6.1), pero el
borrador acierta menos en el terreno de cada experto: con el LoRA de la wiki, la aceptación en la posición 0 cae de 0,98
a 0,58 y la aceleración de 2,73× a 1,74× **[ran] F0**. En la Mac, con el LoRA, el borrador no acelera **[ran] MAC**; en
llama.cpp es peor que eso — el drafter MTP *frena* al 12B con el LoRA del experto en su propio dominio (0,52×) y sólo
da una ganancia modesta en el resto (0,66–0,87×) **[ran] MAC2**. Restringir qué capas llevan el LoRA tampoco rescata al
borrador — ver §6.6.

**Cómo se consigue "un borrador ajustado por experto", según lo que exista:**

| estrategia | qué cambia por pedido | ¿existe hoy? |
|---|---|---|
| **A. un borrador compartido**, entrenado con respuestas de todos los expertos | sólo el LoRA del grande | sí, con vLLM tal cual; falta entrenarlo (EAGLE-3 con `speculators`) |
| **B. borrador base + un LoRA de borrador por experto** | el LoRA del grande **y** el del borrador | **no en vLLM** (haría falta modificar el componente que corre el borrador). **Sí se puede en nuestra pista Mac**: el mismo `HotLoRA` que envuelve las capas del grande puede envolver las del borrador |
| **C. un borrador completo por experto** | todo el servidor (una instancia por experto, o reiniciar) | sí, pero no escala; sirve como techo |
| **D. el MTP nativo reentrenado por experto** | igual que C | sin soporte en `speculators`; habría que escribir el entrenamiento |

**Lo que medimos después:**
- ~~**F0b**: si la salida con el borrador es idéntica a la normal~~ — **[ran]**: no se puede probar en una L4 en FP8; las diferencias se leen como deriva (§8.4).
- **C0 [ran]:** en una A100 en bf16, el propio drafter MTP de Gemma con el LoRA experto del dominio encendido da 1,92×
  en el dominio (α 0,34) y 2,40× general, contra 2,80×/2,60× en el base — una recuperación real sobre el 1,74× de F0,
  pero todavía por debajo de la velocidad del base. El otro brazo — el E4B de la wiki, ya alineado al mismo corpus (B4:
  el 12B aceptó el 90 % de sus borradores), fusionado y servido como borrador completo independiente (estrategia C) —
  no corrió: se queda sin memoria (OOM) al lado del 12B en una L4; el FP8 online de vLLM falla en esa GPU; bitsandbytes
  no es una cuantización de borrador aceptada; una H100 fue rechazada por cupo. **Esto sigue abierto** — un borrador
  alineado al experto (estrategia B o C, bien dimensionada) queda en pausa, no refutado, porque el MTP ya se paga solo
  en una L4 y no en la Mac (§6.5).
- **C0-upper [ran]:** ¿confinar el LoRA a la mitad superior de las capas (§6.6) ayuda al borrador, ya que el MTP lee
  las activaciones de las capas superiores del grande? No: α en el dominio va de base 0,82 → LoRA completo 0,44 →
  LoRA de mitad superior 0,43 (ρ = −0,02). **Restringir las capas no ayuda al borrador** — ver §6.6 para el porqué, y
  para qué sí sirve.

### 6.6 Restringir el LoRA a las capas superiores: una palanca para compartir la KV, no un arreglo para el borrador

Todo en §6.4–§6.5 cambia el LoRA del experto y pregunta qué le hace al borrador. Esta sección hace una pregunta
distinta sobre la *misma* palanca — poner el LoRA sólo en las capas superiores del decoder — y obtiene una respuesta
distinta según a qué problema apunte.

**Como forma de compartir la KV entre expertos — funciona. [ran] E6:** el miembro de la escuela entrenado de nuevo con
su LoRA alcanzando sólo las capas 21–41 de 42 del decoder (la mitad superior; `--layers-from half`) puntúa exactamente
como el miembro completo: 70/70 en el held-out, 15/15 en la demo, 0 perdido. Más al punto: **la caché KV de las 21
capas de abajo es idéntica byte a byte a la del modelo base** (un control base-contra-base también dio idéntico). La
razón es mecánica, no una propiedad de este experto en particular: una capa que el LoRA nunca toca calcula las mismas
claves y valores para cualquier experto, porque nada de los pesos que las produjeron cambió. Un servidor que tenga
varios expertos podría calcular esa KV de abajo una sola vez, desde el modelo base, y dejar que los pedidos de cada
experto la compartan — pagando el costo extra del LoRA sólo desde la capa 21 para arriba. **La salvedad [ran] E6:** el
E4B ya cachea 24 de sus 42 capas por su cuenta (un rasgo de la arquitectura, sin relación con este LoRA), y ese límite
no coincide con el del LoRA: cambiar de experto igual recalcula las capas 21–23. La batería también está en el techo
del miembro completo, y esto corrió sobre una sola semilla.

**Como forma de ayudar al borrador — no funciona. [ran] C0-upper:** la esperanza era que si el MTP lee sobre todo
activaciones ocultas de las capas superiores, un adaptador confinado a esa misma mitad superior cambiaría menos de lo
que ve el borrador que uno de profundidad completa, y así le costaría menos aceptación. No es así: α en el dominio
queda en 0,43 con el adaptador de mitad superior contra 0,44 con el completo — sin mejora (ρ = −0,02, se lee como
ninguna). **Por qué, [read]:** el adaptador de mitad superior sigue tocando exactamente las capas de las que lee el
MTP — confinar el LoRA a la mitad *superior* deja sin restringir justo la parte de arriba, así que desde el punto de
vista del borrador casi nada cambió. En una L4 el propio MTP del E4B sigue pagando con su LoRA encendido de todos
modos (2,4× b1, 2,1× b8) — un resultado sobre que ese borrador es barato y está alineado desde el vamos (C0), no sobre
qué capas llevan el adaptador. **En vLLM, el adaptador de mitad superior sirve exactamente a la velocidad del
completo** — medio adaptador ahorra memoria, no tiempo, probablemente porque las capas de abajo sin tocar quedan
rellenas con ceros en vez de saltarse **[read]**.

**Las dos lecturas lado a lado, para no confundirlas:** el LoRA restringido por capas es una palanca genuina para
*servir muchos expertos barato* (KV compartida de abajo, un control ya corrido para confirmarlo, §6.6 arriba) y un
callejón sin salida genuino para *alinear un borrador a un experto* (§6.4–§6.5) — la misma perilla, dos mecanismos
distintos, y sólo uno de los dos se movió.

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

**Editar la biblioteca después de entrenar se sostiene — por la razón que el diseño busca, no una más fuerte. [ran]
W7:** se parchó un enunciado en la biblioteca markdown, sin reentrenar, sobre los mundos y preguntas propios de
`distributor-wiki@v2`: 37 de 38 respuestas de control siguieron el valor nuevo, cada una citando la línea parchada; 0
desactualizadas. Eso es la separación funcionando como se diseñó — el LoRA nunca guardó el hecho, así que no hay nada
en los pesos que contradiga la página. En modo cerrado, sin la nota delante, los pesos todavía contestan con el valor
*viejo* en 1 de 40 preguntas: no es cero. **Por qué [read]:** el miembro aprendió la *ruta* al enunciado lo bastante
bien como para, en casos raros, reproducir el valor que por lo general sólo lee — es lectura, no la biblioteca
imponiéndose sobre la memoria, y un recordatorio de que "el LoRA no memoriza hechos" es una cuestión de grado medida
acá, no una garantía de la arquitectura.

**Qué es una "biblioteca real", y por qué la generada no preparó al miembro para ella.** Toda biblioteca de arriba —
la wiki de W9, `distributor-wiki@v2` — fue generada: un script escribe las páginas, así que también puede escribirles
constantes nuevas en cada mundo, que es lo que obligó al modelo a leer en vez de recitar. Una **biblioteca real** es
el objeto opuesto: una regulación de verdad (el Código de Regulaciones Federales de EE. UU., tal como lo publica el
propio eCFR del gobierno), convertida a la misma forma de página-de-enunciados de manera *mecánica* — una sección por
página, un párrafo por enunciado, las referencias cruzadas vueltas enlaces exactamente donde la regulación los puso
(`memory/ingest.py`) — sin que nadie reescriba una oración para que sea más fácil de buscar. Poner al miembro del
mundo generado frente a esto hace fallar el recorrido de lleno: `distributor-wiki@v2` sacó **0 de 25** preguntas de
varios saltos, porque buscaba con las formas de consulta exactas que su mundo generado le había entrenado y los
títulos de las páginas reales casi no comparten palabras con la pregunta de una persona
([`REAL0`](../../results/REAL0-real-library-20260930/BRIEF.md)). **Había aprendido el generador, no la biblioteca.**

**Cómo el miembro aprendió a recorrer regulaciones reales en cambio.** Dos tipos de arreglo, comprados en ese orden
porque el más barato se probó primero. El arreglo del **runtime** no cuesta reentrenar: buscar las propias palabras
de la pregunta en todos los estantes en vez de confiar en la consulta aprendida del modelo, caer a todos los estantes
cuando uno nombrado no devuelve nada, y mostrar los enunciados de una página bajo sus propios anclajes en vez de un
listado desnudo de números de sección — juntos cerraron la mayor parte de la brecha, a 24/25, con el mismo adaptador
sin tocar
([`REAL1`](../../results/REAL1-entry-20260930/BRIEF.md)–[`REAL2`](../../results/REAL2-page-text-20260930/BRIEF.md)). El
arreglo de **entrenamiento** necesitó un corpus nuevo: recorridos sobre documentos reales de una familia regulatoria
*distinta* a la que se pregunta, para que el miembro no pueda haber memorizado la respuesta, con la pérdida
restringida a los propios tramos del modelo — un bug, no una decisión de diseño, fue lo que hizo necesario este
arreglo: el entrenamiento siempre había puesto la pérdida sobre el turno *entero*, incluyendo cada página que el
runtime mostraba, y una página real leída entera es casi toda tokens de página, así que el primer intento acá
simplemente aprendió a copiar la regulación de vuelta, 1 de 23. Enmascarar la pérdida a lo que el modelo mismo
escribe dio **18 de 23 (78 %)** sobre un set fresco y más difícil, contra el 9 de 23 del base sin entrenar
([`REAL3`](../../results/REAL3-real-corpus-20260930/BRIEF.md)).

**Qué significa la negativa acá, y por qué tuvo que entrenarse en vez de asumirse.** Un miembro que siempre contesta
se equivoca justo cuando una biblioteca no tiene respuesta que dar — y el miembro de arriba nunca había visto ese
caso, así que contestó las 4 preguntas de prueba sin respuesta igual. El arreglo tiene la misma forma que todo lo
demás en este diseño: no una regla pegada encima, sino más corpus — 27 recorridos cuya biblioteca genuinamente no
tiene respuesta, terminando en `Not in my library.` en vez de una adivinanza. Entrenado con ellos, el miembro se
niega en 15 de 16 preguntas sin respuesta held-out mientras sigue contestando con 0 negativas falsas de 36 que sí
puede contestar ([`REAL4`](../../results/REAL4-refusal-20260930/BRIEF.md)) — este miembro, **`real-none-s0`**, es el
que el usuario aceptó como el miembro de documentos reales, y es lo que `examples/library/serve.py` sirve ahora —
en vivo, por OpenClaw en la Mac del usuario, a **36/52 contra el 38/52 de REAL4 sobre vLLM bf16** (titular 16/23 y
negativas 15/16 exactos, un salto 5/13): **PASÓ**, con las pérdidas leyéndose como el propio límite de contexto
del borde ([`LIVE-library`](../../results/LIVE-library-20261001/BRIEF.md)). Llevado a una tercera familia, más densa en enlaces,
el mismo miembro se queda bien por encima del base sin entrenar (15/25 contra 2/25) pero se queda corto de la barra
de citación: la mayor parte de lo que se equivoca es citar un enunciado *distinto* que tiene el mismo número que el
preguntado — un problema que el recorrido no tiene y la citación sí. Un segundo corpus apuntado exactamente a esa
forma (REAL7, señuelos a través del enlace) tampoco cambió nada — empató 13/21 sobre el titular sin gemelos,
**FALSEADO** — así que esta línea de corpus sobre la citación se detiene; lo que podría moverla no es un tercer
corpus sino un chequeo en el propio runtime
([`REAL5`](../../results/REAL5-third-family-20261001/BRIEF.md)–[`REAL7`](../../results/REAL7-crosslink-20261001/BRIEF.md)).
Y el arreglo que hizo que los documentos reales se pudieran aprender — pérdida sólo sobre los propios tramos del
modelo — no es gratis en todos lados: probado sobre un miembro de resultado corto (el tracker de equipo, el dominio
del §7.4), *retrocede* una frase 0 de 20 contra la pérdida de texto completo de siempre, así que es la receta sólo
donde las páginas que se leen son largas, no un nuevo default
([`H5`](../../results/H5-span-loss-tracker-20261001/BRIEF.md)).

### 7.2 El router y la frontera

Decidir *qué experto* atiende un pedido es un clasificador que también tiene que saber decir "ninguno". Probamos un
modelo de n-gramas, embeddings (Qwen3-Embedding y EmbeddingGemma) y un clasificador chico: **ninguno pasó** — todos
pierden pedidos legítimos de remitentes que no vieron **[ran]** M2, E1. En producción, **el rol del usuario (que viene
en su token) es la ruta**, y lo que el rol no cubre va a la frontera o a una persona según la política del rol.

Eso deja una segunda decisión que el router nunca iba a tomar por un solo miembro de todos modos: una vez que un
pedido *está* dentro del corpus de un rol, ¿cuándo tiene que decir ese mismo miembro "esto no es mío"? **[ran]** M10 la
responde entrenando la abstención directamente en el corpus en vez de agregar un clasificador delante: `train_out` son
los 700 turnos habituales del miembro distribuidor, byte a byte, más 70 turnos `OUT OF SCOPE` sacados de la propia
política de salida del rol. Contra el miembro llano (`staff-s0`), el que abstiene (`out-s0`) no pierde nada de lo que
ya tenía — 0 de 70 turnos held-out retroceden — y gana lo que se entrenó para ganar: 20 de 20 pedidos held-out fuera de
alcance abstenidos, contra 0 de 20 del miembro que nunca vio el patrón; la demo en vivo dio 6/6 contra 5/6. **[read]**
por qué esto es más barato que un router: el miembro ya lee todo el pedido para contestarlo, así que pedirle que
también clasifique "esto es mío" cuesta unos pocos turnos de entrenamiento, no un segundo modelo en el camino — al
precio de hacerlo por miembro en vez de una sola vez para todos.

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

**Al gateway no le importa qué sirve al modelo por debajo — probado corriéndolo en el edge. [ran] LIVE-distributor:**
el miembro de la distribuidora (E4B Q8_0 + su LoRA) servido con llama.cpp en la propia máquina del usuario (§3.5), 5 de
5 turnos a través del OpenClaw real 2026.9.4. La misma maquinaria de identidad/permiso/retención/anclaje/salida se
aplicó sin cambios; lo que corrió contra un cliente real y el perfil de servidor nunca habría atrapado: llama.cpp
descarta la cadena de parada de la que depende el bucle de modo corpus para cerrar un turno limpio, y el propio
almacén de la distribuidora no era thread-safe bajo las llamadas concurrentes de OpenClaw (primer intento void; los
dos se arreglaron). **[ran] M10** después corrió en vivo, de la misma forma, al miembro que abstiene: 6 de 6 a través
de OpenClaw, 5 contestados localmente y el sexto — una nota de agradecimiento a proveedores, leída correctamente como
fuera de alcance — reenviado a **Claude Haiku 4.5** a través de la salida a frontera del gateway: 10.198 + 195 tokens,
$0,0112. Ese miembro no es un release formal (todavía no tiene archivo de release) — la corrida en vivo es una
demostración del camino de salida, no una afirmación de que el miembro pasó la compuerta.

### 7.4 Multi-turno y memoria: por qué cargar la conversación no es la solución

![Dos paneles. Izquierda, la conversación en el prompt: un rollo que crece turno a turno y un formulario de reclamo con el campo de pedido vacío, 43 de 54. Derecha, las claves en una memoria: una ficha con el estado y los nombres de claves, un cajón abierto en el pedido 58 y el reclamo completado con él, 53 de 54. Título: llevar las claves, no la conversación.](../img/operational-memory.png)

*H1: traer un valor por clave arregla lo que leer el historial perdía — el reclamo ahora nombra el pedido.*

Un gateway que sólo lee el último pedido no tiene cómo resolver "llevalo al andén 5" si "lo" se nombró dos turnos
antes — la referencia no tiene a qué apuntar en ese único mensaje. La reparación obvia es darle al modelo toda la
conversación: `Gateway(history=True)`.

**Por qué eso sigue siendo la línea base ingenua. [ran] MT0** (`results/MT0-multiturn-baseline-20260929`): sobre 60
sesiones held-out de la distribuidora (124 turnos, 54 dependientes de un turno anterior), un miembro sin conversación
acierta 4 de 54 turnos dependientes — y hasta eso es azar: los 4 caen en compras, cuyo 4/10 no es mejor que adivinar,
mientras los otros 44 turnos dependientes, fuera de compras, puntúan 0. El mismo miembro con la conversación acierta
43 de 54 (79,6 %) — una ganancia real, y esto no es arreglar un miembro roto en general: los turnos independientes,
sin historia, puntúan 60 de 60 en los dos brazos. Pero mirá dónde se agrupan los 11 errores: una referencia copiada
directo a un argumento de herramienta se resuelve bien (recepción 10/10, devoluciones 10/10, compras 9/10, despacho
12/14); una referencia que sólo aparece en texto libre — una respuesta de atención al cliente que dice "ese pedido"
sin volver a nombrar el número — se archiva mal 8 de 10 veces. **[read]**: el modelo puede leer la historia; no la usa
de forma confiable para reponer un dato que la respuesta necesita pero que la persona no repitió. Y la corrección
tampoco sale barata: los tokens crecen con la sesión incluso en dos o tres turnos (+24 % en el turno 2) — una forma
que empeora a medida que las sesiones se alargan, justo el caso que un gateway de producción tiene que atender.

**Qué es una memoria operativa por clave.** En vez de repetir la conversación, guardar lo que una sesión ya aprendió
— un id de pedido, un número de andén — en una caché chica fuera del prompt, direccionada por nombre, de la misma
forma en que la biblioteca del §7.1 se direcciona por clave: `<get>order</get>` devuelve un valor, `<put>dock=5</put>`
guarda uno. Cada turno el modelo ve una línea en vez de una transcripción: `state: receiving/assigned · keys: order,
dock` — el estado actual del workflow y los *nombres* de las claves que tienen algo guardado, nunca los valores. El
estado no lo decide el modelo: avanza sólo cuando la capa de herramientas efectivamente corre una llamada — la misma
disciplina que el gateway del §7.3 ya aplica a permisos y anclaje, ahora aplicada a qué significa "el paso actual".
**[ran] en tests, y entrenada desde entonces por dos miembros** (`examples/common/opmemory.py`): una caché de sesión acotada a (organización,
usuario, sesión) más una caché global por organización, servida por la capa de herramientas como cualquier otra
herramienta y acotada por la misma credencial firmada ya descripta en el §7.3 — ninguna clave cruza un tenant ni un
usuario.

**Cómo podría un LoRA aprender a operarla.** El §7.1 mostró a un LoRA aprendiendo a *leer* una biblioteca por clave —
buscar, abrir, citar. El arnés de workflow en diseño pide un segundo hábito sobre la misma base: en qué workflow está
una sesión, qué herramienta pide su estado actual, y qué clave tiene el valor que esa llamada necesita — leyendo con
`<get>`, y ahora también escribiendo con `<put>`. Nada de los *valores* se entrena adentro: la caché queda fuera de
los pesos y se escribe en tiempo de ejecución, nunca se memoriza, igual que la biblioteca nunca se memoriza (§7.1). Y
se entrena *adentro* del miembro, al lado de sus herramientas y su corpus, no como un segundo adaptador apilado
encima. **[read]**: esa elección no es incidental — un adaptador de protocolo compartido compuesto con uno de dominio
es lo que probó `harness.lora`, y lo que quedó parado porque la composición no se pudo medir limpiamente. Enseñar el
mismo hábito adentro del corpus propio de cada miembro es una apuesta distinta sobre la misma idea, no un reintento de
la que falló.

**Qué midió H1, y qué muestra. [ran]** `results/H1-workflow-harness-20260929` entrenó un miembro (`wf-s0`) sobre el
corpus de MT0 más 627 turnos de arnés y comparó tres brazos sobre las mismas 60 sesiones de MT0: `history` (la línea
base de arriba), `harness` (el contexto de una línea, con el bloque de herramientas) y `harness-noblock` (lo mismo,
sin repetir las herramientas en el prompt). **`harness`: 53 de 54 turnos dependientes, contra los 43/54 de
`history`** (1 perdido, 11 ganados), tokens de prompt planos por posición de turno, y — el chequeo que agrega este
diseño — todo turno dependiente contestado bien también buscó su valor por la clave correcta, 53 de 53.
**`harness-noblock`: 0 de 60.**

*Por qué buscar por clave arregla lo que la historia no pudo.* El resultado de MT0 del §7.4 se partía según cómo la
referencia llega a la respuesta: una referencia copiada se resuelve con la historia, una que el modelo tiene que
**componer en texto libre** no (un reclamo sobre "ese pedido" archivado sin número de pedido, 8 de 10). `<get>order</get>`
saca ese paso por completo — el número de pedido entra a la llamada como el valor que devuelve el almacén, no como
algo que el modelo tiene que notar en la transcripción y volver a escribir. Los reclamos de atención al cliente, el
peor caso de MT0 (2/10 con historia), pasan a **10/10** con el arnés, y cada uno nombra el pedido que buscó. El
mecanismo no es "el modelo mejoró leyendo la historia"; es que leer la historia deja de ser el camino por el que
viaja el valor.

*Por qué el brazo sin bloque cae a cero, no a algo peor que `history`.* `harness-noblock` nunca vio sus propias
herramientas sin describir **en el entrenamiento** — su corpus, como todo corpus de este repositorio, siempre llevó
el bloque de herramientas. Sacar el bloque en el momento de servir no es una versión más difícil de la misma tarea;
es un prompt distinto al que se le mostró al miembro, y el miembro hace lo que hace todo experto fuera de su corpus
(§7.2, §8.6): no llama nada y afirma datos que nunca leyó. **Un corpus enseña el prompt con el que se lo sirve, no
uno con el que podría servírselo después.** Es la misma lección del resultado de poda de E5 y de "una superficie
desconocida es extrapolación" de P59, ahora sobre el bloque de herramientas propio del arnés y no sobre el de un
runtime.

*Por qué el conteo de tokens es más alto, en estas sesiones cortas.* Por turno, `harness` lee aproximadamente **2× los
tokens de prompt** de `history` en el turno 1 (745 contra 345, §8.9 de FOUNDATIONS) — no porque la línea de contexto
sea más larga que una transcripción corta, sino porque contestar ahora exige más **pasos de generación**: get →
llamada → put → respuesta, donde `history` escribe la respuesta directo. Ese costo es real y no está escondido; lo
que todavía no se mide es cuánto de eso absorbería el caché de prefijo, ya que el andamiaje get/call/put se repite de
turno en turno de la misma forma que el prefijo compartido del §3.6. El argumento de tokens del arnés es sobre el
**crecimiento**, no sobre el piso por turno: el prompt de `history` sigue subiendo con la sesión (§8.9), el del arnés
no — y esa ventaja sólo se ve una vez que las sesiones duran más que los dos o tres turnos de MT0.

*La lección sobre VOID, independiente de cualquiera de los dos números.* La regla de corte del brief — primeros
turnos en 90 % o más en todos los brazos, o la corrida es VOID — se escribió para atrapar una falla (un arnés roto
que también rompe lo que ya funcionaba) y en cambio atrapó otra distinta: un brazo que nunca iba a pasar con
herramientas para las que no fue entrenado. Aplicada al pie de la letra sobre tres brazos, el 0 % de primeros turnos
de un brazo que falla anula los resultados reales de los otros dos. **Leída tal como fue escrita, H1 es VOID; leída
por brazo, `harness` PASÓ y `harness-noblock` quedó FALSADO — una regla VOID comprada para cuidar toda una corrida
tiene que revisarse por brazo, o un resultado que se sostiene solo se tira junto con uno que no.** La decisión del
usuario (2026-09-29): vale la lectura por brazo, y el VOID tal como está escrito queda como el registro de ese
error del instrumento, no como el veredicto. **[ran] H2**, el mismo arnés sobre un dominio de tracker de equipo
de cinco turnos (`results/H2-tracker-harness-20260929`): `harness` sostiene 146 de 160 turnos dependientes
(91,3 %) con un prompt plano en los cinco turnos, pero la corrida se lee **FALSEADA tal como está escrita, no
ANULADA** — los propios 44/60 primeros turnos de la línea de base sin entrenar `base-history` disparan la misma
regla por brazo que arregló a H1, y anular a una línea de base *sin entrenar* cuyo bajo puntaje es todo su punto
vuelve ilegible la comparación en vez de falsa, una segunda instancia que queda en el registro. Descriptivamente,
142 de 160 favorecen al arnés contra 0. Una
segunda instancia, más angosta, de la misma lección: **un VOID por brazo aplica a miembros entrenados, no a una
línea de base cuyo fracaso ES el margen.** **La decisión del usuario (2026-09-29), como para H1: lectura 1** —
las condiciones legibles son el veredicto de H2, `harness` **PASÓ**; FALSEADO-tal-como-está-escrito queda en el
registro con sus dos errores de instrumento (el VOID por brazo y el chequeo de anchor). `harness-noblock`
(80/160) se leyó primero como "aprendido en parte"; eso era un error del corpus — su tercio sin bloque
compartía módulo (`% 3`) con la rotación de roles, así que las filas sin bloque eran todas de QA — no un
aprendizaje parcial. **H3 [ran], las dos barras PASARON**: `tr-s1`, entrenado sobre un corpus que arregla
las dos correcciones (fraseo ampliado por turno en cada rol, un tercio parejo sin bloque de cada rol), le
gana a `tr-s0` 158/160 contra 147/160 sobre una suite fresca retenida (pareado 11:0, $p = 0,00098$, plano),
y sin el bloque de herramientas sostiene 156/160 en cada rol a más o menos un tercio de los tokens de
prompt — lo-sin-bloque deja de ser sólo de QA
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
Diseño y decisiones abiertas:
[`review/harness-workflow-kv.md`](../review/harness-workflow-kv.md) §§8–9; el mecanismo detrás de `<get>`/`<put>`
y la línea de estado está en [`MECHANISMS.md`](MECHANISMS.md).

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

```math
p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}
```

Así "53 a 0" es una diferencia real y "5 a 6" es un empate, aunque los totales parezcan distintos. Ver
[`FOUNDATIONS.md`](FOUNDATIONS.md) §9.2.

### 8.4 Temperatura 0 no garantiza la misma salida

En teoría, greedy es determinista. En una GPU, **la misma pregunta puede dar otro texto si cambia el tamaño del lote**:
las sumas en punto flotante se hacen en otro orden, y en un empate casi exacto entre dos tokens gana el otro. vLLM tiene
un modo invariante al lote (`VLLM_BATCH_INVARIANT=1`) para cuando hace falta comparar textos exactos. **[ran] F0:** sin
ese modo, la decodificación especulativa dio textos distintos de la normal en parte de los casos — y el mismo LoRA
recargado *sin* borrador también. Mientras no se repita en modo invariante, "salida idéntica" no está establecida. **[ran] F0b:** repetido en ese modo, en una L4 en FP8, dos corridas normales ya difirieron (9/16 idénticas en el dominio), así que el modo no vuelve determinista a esta placa; la especulativa difirió de la normal más o menos lo mismo — se lee como deriva, pero probarlo necesita bf16 en una A100/H100.

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
| 2026-09-28 | la distribuidora servida en el edge (llama.cpp, la propia máquina del usuario), abstiene correctamente hacia la frontera, en vivo por OpenClaw | LIVE-distributor, M10 **[ran]** |
| 2026-09-29 | el tracker de equipo corriendo en vivo por OpenClaw, multi-turno, llevando claves a través de tres sesiones | LIVE-tracker, 14/14, dependientes 8/8 **[ran]** |
| 2026-09-30 | el recorrido de la memoria se transfiere a documentos reales de una familia que el miembro nunca entrenó, una vez que la pérdida queda enmascarada a sus propios tramos | REAL3, 18/23 contra el 9/23 del base sin entrenar **[ran]** |
| 2026-09-30 | el miembro de documentos reales aprende a negarse ante lo que su biblioteca no puede contestar | REAL4, 15/16 se niega, 0 negativas falsas de 36 **[ran]** |
| 2026-09-30 | el gateway sobrevive a un reinicio sin reejecutar un cobro retenido, y su propio proceso no puede alcanzar fuera de sus hosts configurados | #310 **[ran]** |

---

## 10. Lo que todavía no funciona, y el próximo paso de cada uno

| qué | estado | próximo paso |
|---|---|---|
| salida idéntica con especulativa | **no se puede probar en una L4 en FP8 [ran] F0b**: la decodificación normal dos veces ya difiere; la especulativa difiere más o menos lo mismo (se lee como deriva) | bf16 en una A100/H100, donde el modo invariante al lote está pensado |
| un borrador ajustado por experto, en caliente | **[ran] C0**: el MTP nativo + el LoRA experto recupera algo de velocidad (1,92× dominio, 2,40× general, contra 2,80×/2,60× en el base) pero no toda; el borrador E4B fusionado y bien alineado (estrategia C) no corrió — OOM al lado del 12B en una L4, FP8/bitsandbytes/H100 bloqueados esta vuelta. **[ran] C0-upper**: restringir las capas del LoRA tampoco ayuda (§6.6) | **sigue abierto, en pausa, no refutado**: la estrategia B (un LoRA de borrador) espera porque el MTP ya se paga solo en una L4 y no en la Mac — todavía no hay razón para construir lo más difícil |
| el borrador con el LoRA activo | pierde aceptación en el dominio; alinear el propio MTP del grande recupera parte (1,74× → 1,92×, C0) pero restringir las capas no suma nada a eso (C0-upper) | estrategias A, C (bien dimensionada) o D (§6.4), empezando por la más barata |
| la pista Mac | **[ran]**: cambio en caliente MLX en 2,9 µs (banco de investigación, §3.5); **el servido edge ahora es llama.cpp** — cambio de LoRA en caliente en 3 ms, pero el MTP también frena al 12B ahí (0,52–0,87×, MAC2) y el par E4B+12B no entra en 16 GB | servir un miembro a la vez en el edge, como hace LIVE-distributor; un drafter alineado al LoRA sigue en pausa (arriba) |
| router aprendido | ninguno pasa; el router del hito 2 pierde pedidos que parecen reales | el rol es la ruta; la abstención por miembro (M10) cubre la mitad de "esto es mío" sin uno — queda abierto sólo para rutear entre roles |
| buscador de notas con embeddings | 0,63 contra 0,80 | búsqueda por palabras en uso |
| tráfico real | todo es sintético | una muestra anonimizada de un sistema en uso |
| el modelo todavía inventa | 3 de 12 respuestas las atrapa el filtro | un corpus que enseñe a repetir sólo lo que dice la herramienta |
| la memoria (biblioteca) dentro de un miembro que sirve | vive en `distributor-wiki@v2`, un miembro separado del que abstiene, `out-s0` (M10) | juntarlos, o mantenerlos separados por diseño — todavía sin decidir |
| una corrida en vivo de la distribuidora en vLLM bf16 | no corrida — el único brazo local medido es llama.cpp Q8_0 (LIVE-distributor) | correrla cuando haga falta una comparación a la misma precisión contra el edge |
| el resultado de H1 (el arnés de workflow) | **[ran] — la decisión del usuario (2026-09-29): por brazo.** Por brazo: `harness` PASÓ (53/54 contra 43/54, todo acierto buscado por clave); `harness-noblock` quedó FALSADO (0/60). Tal como fue escrita: **VOID**, superada — la regla de primeros turnos del brief anula entre brazos, un error del instrumento, queda como su registro | liberar el miembro con la lectura por brazo; el VOID es por brazo a partir de H2 |
| el resultado de H2 (el arnés sobre un dominio de cinco turnos) | **[ran] — la decisión del usuario (2026-09-29): lectura 1.** `results/H2-tracker-harness-20260929`: `harness` 146/160 dependientes (91,3 %), prompt plano en los cinco turnos; `base-history` 4/160, sus propios 44/60 primeros turnos lo anulan bajo la regla por brazo, así que la comparación pre-registrada queda ilegible — tal como está escrita **FALSEADA**, en el registro junto con ese y el error de instrumento del chequeo de anchor; las condiciones legibles son el veredicto de H2, `harness` **PASÓ**, descriptivo 142:0 al lado | el resultado de H3 está abajo (fila siguiente) |
| el resultado de H3 (un segundo corpus de tracker, lo-sin-bloque ya contestado) | **[ran] — las dos barras PASARON.** `results/H3-tracker-corpus-v2-20260929`: `s1-harness` 158/160 dependientes (98,8 %) contra `s0-harness` 147/160, pareado 11:0, prueba de signo exacta $p = 0,00098$, plano — **H3a PASÓ**; sin el bloque de herramientas, `s1-noblock` 156/160 (97,5 %), cada rol por encima de la barra (developer 76/80, lead 40/40, QA 40/40), a más o menos un tercio de los tokens de prompt — **H3b PASÓ**, cerrando la brecha de lo-sin-bloque-solo-QA que dejó abierta H2 | la demo en vivo por OpenClaw (fila de abajo); el brazo de atribución (`s0-noblock` sobre la suite fresca) no se compró, la causa ya está en disco |
| un router adentro del propio camino del gateway | no construido — el rol sigue siendo la ruta (§7.2) | construirlo sólo cuando haga falta rutear entre roles, no la abstención por miembro |
| el arnés en vivo por OpenClaw, multi-turno | **[ran]**: `tr-s1` sin bloque con la memoria operativa, llama.cpp en la propia Mac del usuario, tres sesiones (lead, developer, QA) — 14/14 turnos, dependientes 8/8, ~370 tokens de prompt por turno | — |
| una nota con forma de orden, obedecida y no sólo archivada como comentario | **[ran] H4 — sin margen**: sobre 40 notas nuevas con forma de orden `tr-s1` escribe las 40 como comentarios y no ejecuta ninguna; cada falla residual entre H2 y H4 fue una sola frase del eval, no el arnés | no se persigue — un tercer rediseño de corpus por una sola frase no se compra |
| la pérdida enmascarada por tramos como receta default | **[ran] H5 — acotada, no adoptada en todos lados**: retrocede un miembro de resultado corto 0 de 20 en una frase contra la pérdida de texto completo; queda como receta sólo donde los resultados son largos (páginas reales, REAL3) | la regla del §3 de `CLAUDE.md` escrita para decirlo así |
| sesiones de más de 2–3 turnos | **[ran] H2, H3**: el tracker de equipo (`examples/tracker/`) corre sesiones de cinco turnos y la propiedad de prompt plano se sostiene ($\bar p_5 \le 1.1\ \bar p_1$) en los dos corpus | lectura elegida (fila de arriba); el segundo corpus de H3 ya está medido (fila de arriba) |
| la caché global entrenada | **[ran]**: construida, probada, y entrenada dentro de los corpus propios de dos miembros (`wf-s0`, H1; `tr-s0`, H2) | — |
| la citación de documentos reales cuando un valor se repite entre enlaces | **[ran] REAL5 PARCIAL (15/25, bajo la barra de 70 %), REAL6 FALSEADO (el arreglo de un salto la deja sin cambios, 15/25), REAL7 FALSEADO (los señuelos entre enlaces empatan 13/21 sobre el titular sin gemelos), CITE0 FALSEADO (el chequeo del runtime dispara 6/6 limpio, convierte 0 de 6), GATE0 LA COMPUERTA FUNCIONA (el mismo chequeo como compuerta dura, repetido exacto sobre 532 recorridos grabados: 0 de 275 respuestas correctas bloqueadas, 86 de 165 incorrectas bloqueadas (52,1 %), precisión de lo entregado 0,625 → 0,777; de las 86 bloqueadas, 43 tenían el valor incorrecto y 43 tenían un valor correcto bajo una cita que falla — 43 de 347 valores correctos retenidos, 12,4 %), PAGE0 AYUDA (mostrar sólo las 8 mejores afirmaciones de la pregunta en una página repara la mitad de las fallas de citar el enunciado equivocado en la misma página de las que trata esta fila, 8 → 6 de 44, sumado a la reparación de los desbordes de contexto hasta 34/44 contra 30/44, pareado 6:2, $p = 0,29$ — AYUDA, no WORKS)**: tres cambios de corpus/runtime dejaron la citación sin cambios, y el chequeo que no podía reparar una línea mala la bloquea de manera confiable, pero una página servida más chica repara directamente una parte | ~~sale apagado por defecto (`--cite-gate`); si prenderlo para un despliegue dado es decisión de producto del usuario, no una medición más~~ **sale prendido por defecto, decisión del usuario, 2026-10-02, aceptando el costo de 43 de 347 valores retenidos; `--no-cite-gate` lo apaga.** `page_top 8` sale de la misma forma, servido por defecto desde el 2026-10-02; `--page-top 0` lo apaga |
| el miembro de documentos reales servido como lo serviría el producto | **[ran] PASÓ, después SIN CAMBIO, después un chequeo de citación FALSEADO, después el mismo chequeo LA COMPUERTA FUNCIONA como compuerta, después una página servida más chica AYUDA, después un corpus de formato entrenado bajo esa página FALSEADO**: `examples/library/serve.py` + un driver de OpenClaw, 36/52 contra el 38/52 de REAL4 sobre vLLM bf16 (LIVE-library); los dos ítems pendientes del borde ya están hechos — `gateway.runtime_request` quita el sobre de mensaje encolado de OpenClaw, `Conversation.page_budget` (2.500 tokens) abre una página que supera el presupuesto por BM25 — **0** desbordes (4 antes), **0** sobres (3 antes), **37/52**, pareado contra LIVE-library 3:2 ($p=1,0$): SIN CAMBIO tal como está escrito, 0 desbordes pero 37 < 38, no REGRESADO (LIVE-library2). `cite_check` (lee sólo el propio registro del referí) sobre un conjunto fresco de 52 filas de una tercera familia: base 32/52, con el chequeo 33/52, disparó en 6, convertidas 0, rotas 0 — un detector sin falsa alarma (15 disparos, 0 sobre una respuesta correcta entre los dos conjuntos) que el miembro no puede aprovechar (CITE0); el mismo chequeo como compuerta dura (`--cite-gate`) bloquea 0/275 correctas e incorrectas 86/165 al repetir exacto (GATE0) — las tres retenciones de OpenClaw en esta corrida están diagnosticadas y resueltas (columna siguiente). Sobre una cuarta familia real (`knowledge/hazwaste-regs`), acotar una página por las 8 mejores afirmaciones de la pregunta (`--page-top`, ahora el default) contesta 34/44 contra el 30/44 de la página sin cambios, pareado 6:2 ($p=0,29$) — AYUDA (PAGE0); entrenar `real-fmt-s0` sobre recorridos bajo esa forma servida, con la guarda `recover` medida por primera vez, empata con el base 33/44 contra 33/44 (1:1) — el base ya tenía sólo 1 falla de formato en 11 fallas una vez que las páginas sirven top-8, así que no había nada en este conjunto para que el corpus reparara, y la guarda `recover` sola es inofensiva (0:0) — la línea de corpus de formato se detiene acá (FMT0) | ~~por qué OpenClaw retiene un turno terminado (3 filas)~~ — **encontrado y resuelto, 2026-10-02**: node quedaba adentro de `process.exit()` después de una corrida exitosa; el driver ahora termina el grupo de procesos de cada turno poco después de la propia línea de fin de corrida de OpenClaw en vez de esperar una salida que puede no llegar nunca, y el endpoint siempre responde a un recorrido que lanza una excepción en vez de dejar que OpenClaw lo reenvíe; ~~**el chequeo de citación pasa a ser una compuerta** — una línea que no la pasa no se entrega, el runtime responde que no pudo verificar la cita, o la reenvía a la frontera~~ — **construido y corrido, GATE0 LA COMPUERTA FUNCIONA**: ver la fila de arriba; ~~sale apagado por defecto~~ **sale prendido por defecto desde el 2026-10-02; `--no-cite-gate` lo apaga**. ~~una página servida más chica~~ — **construido y corrido, AYUDA, sale como default (`--page-top 8`, PAGE0)**; el ítem abierto sigue siendo el chequeo de citación del runtime, no el corpus (FMT0 cerró esa línea) |
| una instrucción plantada en un resultado de herramienta cambiando lo que hace un miembro | **[ran] INJ0 — sin margen**: 70 expuestos en todos los turnos grabados, 0 actuaron | no construido — no hay nada en estas suites para que lo arregle |
| identidad real (Auth0), WhatsApp, instalación | no construidos | después de lo anterior |

---

## 11. Glosario

- **Adapter / LoRA**: el parche de rango bajo que convierte al modelo base en un experto (§5).
- **α (aceptación)**: fracción de tokens del borrador que el modelo grande acepta (§6.2).
- **bf16, FP8, 4 bits**: precisiones de los pesos (§4).
- **Borrador (drafter)**: el modelo o cabeza que propone tokens en la especulativa (§6.3).
- **`edge` / `server`**: los dos perfiles de runtime — `edge` es llama.cpp en la propia máquina del usuario, sirviendo
  un miembro a un runtime de agentes en vivo; `server` es vLLM en Colab, para entrenar y medir (§3.5).
- **Caché KV**: lo que el modelo guarda de los tokens ya vistos para no recalcularlos (§2.4).
- **Continuous batching**: sumar pedidos a un lote en marcha (§3.2).
- **EAGLE-3**: borrador que predice desde los estados ocultos del grande (§6.3).
- **Frontera**: un modelo grande en la nube (Haiku, Gemini) para lo que ningún experto cubre.
- **Caché de prefijo**: reusar la caché KV de los bytes iniciales compartidos de un prompt entre pedidos; se derrota
  moviendo el bloque compartido más adelante en el prompt, no por su tamaño (§3.6).
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
LIVE-school-openclaw, E1, F0, C0, C0-upper, E6, MAC2, W7, E5, LIVE-distributor, M10, MT0, C1 y H1, cada una en
`results/` con su `BRIEF.md`.
