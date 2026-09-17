# Fundamentos — la matemática debajo de lora-kernel, atada a lo que corrió

> *[Read me in English](../FOUNDATIONS.md)*

Este documento dice, paso a paso y en matemática, qué son los modelos, por qué generar
con ellos es lento, qué es un LoRA, qué hace el motor, qué calcula la decodificación
especulativa, por qué la aceptación puede rankear expertos, qué son las tareas como
funciones, y por qué la familia Qwen 3 y `Qwen3.8-27B` pueden ser el modelo grande.
**Cada fórmula que tiene un número debajo nombra la corrida que produjo el número.**

## 0. Cómo leer esto, y la regla permanente

| marca | significado |
|---|---|
| **[read]** | de un paper, un `config.json` o el código, y citado |
| **[ran]** | observado ejecutando algo en este repositorio, con la corrida nombrada |
| **[unverified]** | afirmado en algún lado, no verificado desde acá; nunca sostiene nada |

**La regla permanente (2026-09-17).** Cada corrida en Colab actualiza este documento:
el número aterriza en la sección cuya fórmula instancia, y el mapa del §11 gana una
fila. Una fórmula sin corrida debajo es una afirmación; una corrida sin fórmula encima
es un número. Ninguna de las dos es conocimiento por sí sola.

Las dimensiones de los modelos se leyeron del `config.json` de cada uno en el Hub el
2026-09-17 **[read]**; los tamaños en disco y cada exactitud son **[ran]**.

---

## 1. El modelo de lenguaje como función

### 1.1 Tokens y la factorización autorregresiva

Un tokenizer mapea texto a una secuencia de ids enteros $x_1, \dots, x_T$ sobre un
vocabulario $V$. Un modelo de lenguaje causal es una función $f_\theta$ de un prefijo a
una distribución sobre el próximo id:

$$
p_\theta(x_t \mid x_{<t}) = \mathrm{softmax}\big(f_\theta(x_{<t})\big)_{x_t},
\qquad
p_\theta(x_{1:T}) = \prod_{t=1}^{T} p_\theta(x_t \mid x_{<t}).
$$

Generar es la recursión $x_{t} \sim p_\theta(\cdot \mid x_{<t})$, un id a la vez;
**cada paso necesita el prefijo entero y no puede empezar antes de que exista el id
anterior.** Ese único hecho — la generación es secuencial en $t$ — es lo que el §2
tarifa y lo que el §6 explota.

A temperatura 0 el muestreo colapsa a $x_t = \arg\max_v f_\theta(x_{<t})_v$, y toda la
generación pasa a ser una función determinista del prompt. Cada medición de este
repositorio se toma a temperatura 0 — con la salvedad de que vLLM a temperatura 0 no
es reproducible bit a bit entre sesiones (84, 81, 82 sobre casos idénticos **[ran]**
P36/P38/P40), por eso se usan tests pareados en todos lados (§9).

### 1.2 Un bloque decoder, paso a paso

Las dos familias son transformers sólo-decoder **[read]** (Vaswani et al. 2017; la
variante Qwen2 con RMSNorm, RoPE, atención de consultas agrupadas y una MLP SwiGLU).
Con ancho oculto $d$, $H$ cabezas de consulta, $H_{kv}$ cabezas de clave/valor, ancho de
cabeza $d_h$ y ancho de MLP $d_{ff}$, el bloque $\ell$ mapea $h^{(\ell)} \in \mathbb{R}^{T\times d}$
a $h^{(\ell+1)}$:

1. **Pre-norm.** $\tilde h = \mathrm{RMSNorm}(h) = h \oslash \sqrt{\tfrac{1}{d}\sum_j h_j^2 + \epsilon}\;\odot\; g$.

2. **Proyecciones.** $Q = \tilde h W_q,\; K = \tilde h W_k,\; V = \tilde h W_v$ con
   $W_q \in \mathbb{R}^{d\times H d_h}$ y $W_k, W_v \in \mathbb{R}^{d \times H_{kv} d_h}$.
   Con $H_{kv} < H$ cada cabeza de clave/valor sirve a $H/H_{kv}$ cabezas de consulta —
   *atención de consultas agrupadas*, que es lo que hace más chica la caché KV del §2.2.

3. **Posición rotatoria (RoPE).** Cada par de coordenadas $(q_{2i}, q_{2i+1})$ en la
   posición $t$ se rota un ángulo $t\,\omega_i$ con $\omega_i = \theta^{-2i/d_h}$; lo
   mismo para $k$. Entonces $\langle q_t, k_s\rangle$ depende sólo de $t-s$ — la posición
   entra como fase relativa. Las dos familias usan $\theta = 10^6$ **[read]**.

4. **Atención causal**, por cabeza:
   $$
   A = \mathrm{softmax}\!\Big(\frac{QK^\top}{\sqrt{d_h}} + M\Big)V,
   \qquad M_{ts} = \begin{cases}0 & s\le t\\ -\infty & s>t\end{cases}
   $$
   y luego $h \leftarrow h + A\,W_o$.

5. **MLP (SwiGLU).** $h \leftarrow h + \big(\sigma(\tilde h W_{gate}) \odot \tilde h W_{up}\big) W_{down}$,
   con $\sigma$ la SiLU, $W_{gate}, W_{up} \in \mathbb{R}^{d\times d_{ff}}$,
   $W_{down} \in \mathbb{R}^{d_{ff}\times d}$.

Las siete matrices $W_q, W_k, W_v, W_o, W_{gate}, W_{up}, W_{down}$ de cada bloque son
exactamente los `target_modules` que parchea cada adaptador de acá (§4) **[ran]**
`adapters/email-full/adapter_config.json`.

### 1.3 El unembedding

Tras $L$ bloques y una RMSNorm final, los logits son $z = h_T W_{out}$ con
$W_{out} \in \mathbb{R}^{d\times |V_{emb}|}$. En `Qwen2.5-3B` el unembedding está atado al
embedding de entrada (`tie_word_embeddings: true`) y tiene $|V_{emb}| = 151{.}936$
columnas — **más ancho que el tokenizer de 151.643 entradas más sus 22 tokens agregados
= 151.665 ids** **[read]**/**[ran]** P48. Las columnas extra son relleno; una máscara
sobre ellas no enmascara nada, y `STACK.md` §1 lo registra porque una cabeza tipada
alguna vez supuso lo contrario.

### 1.4 Las dos familias que servimos

| | `Qwen2.5-3B-Instruct` | `Qwen2.5-32B-Instruct-AWQ` | `Qwen3.5-4B` | `Qwen3.8-27B` |
|---|---:|---:|---:|---:|
| clase | `Qwen2ForCausalLM` | `Qwen2ForCausalLM` | `Qwen3_5ForConditionalGeneration` | `Qwen3_5ForConditionalGeneration` |
| $d$ | 2.048 | 5.120 | 2.560 | 5.120 |
| $d_{ff}$ | 11.008 | 27.648 | 9.216 | 17.408 |
| $L$ | 36 | 64 | 32 = 24 lineales + 8 completas | 64 = 48 lineales + 16 completas |
| $H$ / $H_{kv}$ / $d_h$ | 16 / 2 / 128 | 40 / 8 / 128 | 16 / 4 / 256 | 24 / 4 / 256 |
| ids del tokenizer | 151.643 | 151.643 | 248.044 | 248.044 |
| pesos en disco | ~6 GB bf16 | **19,3 GB** AWQ int4 g128 | — | — |
| rol acá | **la base residente; cada adaptador se apoya en ella** | **el target especulativo** | drafter 3.x candidato (D0) | el modelo grande al que apunta la ruta |

Todas las dimensiones **[read]** `config.json`, 2026-09-17; tamaños en disco **[ran]** P48/P49.

### 1.5 Las capas híbridas de Qwen 3.5 / 3.8: Gated DeltaNet

La línea 3.x **no** es una pila de bloques de atención idénticos. Sus `layer_types`
alternan: tres capas de *atención lineal*, luego una de *atención completa*
(`full_attention_interval: 4`) **[read]**. El log de serving de P33 nombra el kernel:
`qwen_gdn_linear_attn.py … GDN decode kernel: cuda` **[ran]**.

Una capa de atención lineal reemplaza el softmax $T\times T$ por un **estado
recurrente** $S_t \in \mathbb{R}^{d_k\times d_v}$ actualizado una vez por token. La regla de
Gated DeltaNet **[read]** (Yang et al., *Gated Delta Networks*, 2024) es

$$
S_t = \alpha_t\,\big(I - \beta_t\, k_t k_t^\top\big)\, S_{t-1} \;+\; \beta_t\, k_t v_t^\top,
\qquad o_t = S_t^\top q_t,
$$

con compuertas dependientes de los datos $\alpha_t \in (0,1]$ (decaimiento) y
$\beta_t \in (0,1]$ (fuerza de escritura). El primer término *olvida* a lo largo de
$k_t$, el segundo *escribe* $v_t$ en $k_t$ — una regla delta. Dos consecuencias
importan acá:

- **El costo por token es $O(d_k d_v)$ e independiente de $T$**, y la "caché" es una
  matriz por capa en vez de $T$ vectores — así que los modelos 3.x son baratos en
  contexto largo, y por eso son atractivos como modelo grande.
- **Las proyecciones que producen $q_t, k_t, v_t$ y las compuertas siguen siendo mapas
  lineales ordinarios** $\tilde h W$ — la forma que LoRA parchea. Nada en la recurrencia
  prohíbe un delta sobre $W$. Si un *motor de serving* lo aplica es otra pregunta, y
  es C18 (§10.4).

El envoltorio `ForConditionalGeneration` agrega una torre de visión (módulos
`visual.*`) delante del modelo de texto; la clase propia del modelo de texto es
`qwen3_5_text` **[read]**.

---

## 2. Por qué generar es lento: recursión, la caché KV y el ancho de banda

### 2.1 Prefill y decode son regímenes distintos

Dado un prompt de $P$ tokens, el **prefill** corre una pasada hacia adelante sobre las
$P$ posiciones a la vez — trabajo matriz–matriz, limitado por cómputo. El **decode**
produce después cada token nuevo con una pasada sobre *una* posición — trabajo
matriz–vector, limitado por cuán rápido se pueden leer los pesos de memoria.

### 2.2 La caché KV

La atención en el paso $t$ necesita $K_{1:t}, V_{1:t}$ de cada capa. Recomputarlos
cuesta $O(t)$ por paso; cachearlos hace el decode $O(1)$ en recómputo al precio de
memoria:

$$
\text{bytes}_{KV}(t) \;=\; 2 \cdot L \cdot H_{kv} \cdot d_h \cdot t \cdot b,
$$

con $b$ bytes por elemento. Para `Qwen2.5-3B` en bf16: $2\cdot 36\cdot 2\cdot 128\cdot 2 = 36{.}864$
bytes por token — **36 KB/token**, 147 MB a 4.096 tokens. Para el 32B (caché bf16
sobre una base AWQ): $2\cdot 64\cdot 8\cdot 128\cdot 2 = 262{.}144$ bytes — **256 KB/token**,
1 GB a 4.096. GQA es por qué estos números llevan $H_{kv}$ y no $H$. Las capas de
atención lineal del §1.5 llevan en cambio un estado fijo $d_k\times d_v$, que es su
razón de ser.

### 2.3 El decode está limitado por los bytes de pesos

Un paso de decode lee cada peso una vez. Con $B_W$ bytes de pesos y ancho de banda
$\mathcal{B}$, el piso es

$$
t_{\text{step}} \;\gtrsim\; \frac{B_W}{\mathcal{B}} \;+\; \frac{\text{bytes}_{KV}(t)}{\mathcal{B}}.
$$

En una A100-40GB ($\mathcal{B}\approx 1,5$ TB/s **[read]**): el 3B (~6,2 GB) tiene piso
de **~4 ms/token**; el 32B-AWQ (19,3 GB), **~13 ms/token**. La aritmética es diminuta
en comparación — $2\cdot\text{params}$ FLOPs por token contra $3\times 10^{14}$ FLOP/s
— que es lo que significa *limitado por memoria*: **la GPU pasa el tiempo moviendo
pesos, no multiplicándolos.** Cuantizar a 4 bits (AWQ, §4.3) ayuda al decode
exactamente achicando $B_W$.

### 2.4 El batching amortiza la lectura de pesos

$n$ secuencias concurrentes comparten una lectura de pesos por paso, así que el
throughput escala casi linealmente en $n$ hasta que la caché KV o el cómputo saturan.
Por eso P55 corrió los casos con concurrencia 8: **475 cadenas en modo corpus por el
3B en 31 s, y por el 32B en 230 s** **[ran]**
`results/P55-graded-ranking-20260916/session_a.json` — una relación de 7,4× en tiempo
de pared para 3,1× en bytes de pesos, el resto siendo las cadenas más largas del 32B
(2,6 llamadas/caso contra 2,2) y su descuantización int4.

**Esta es toda la razón de existir de la decodificación especulativa** (§6): el paso
de decode del target cuesta una lectura completa de pesos *tanto si verifica un token
como cinco*, porque las $k+1$ posiciones se puntúan en una pasada con forma de prefill.

---

## 3. El texto como ids: BPE, mapas de ids y merges

### 3.1 Byte-pair encoding en tres líneas

Se parte de bytes. Se fusiona repetidamente el par adyacente más frecuente en un
símbolo nuevo; cada fusión es una regla $(a, b) \to ab$ y las reglas, en orden, son la
lista `merges`. El `vocab` mapea cada símbolo a un id. Codificar texto aplica las
fusiones; **después de eso, todo lo que hace el modelo ocurre en el espacio de ids.**

### 3.2 Qué necesita la decodificación especulativa: el mismo mapa de ids

El muestreo por rechazo (§6.1) compara $p_{\text{target}}(v)$ y $q_{\text{draft}}(v)$
**en el mismo $v$**. Así que un id drafteado tiene que nombrar la misma cadena para
los dos modelos: $\text{vocab}_D(v) = \text{vocab}_T(v)$ para cada $v$ que el drafter
pueda emitir, y ningún id puede significar dos cosas. **Los `merges` pueden diferir** —
sólo deciden cómo el *texto* se vuelve ids, lo que ocurre una vez, para el prompt; a un
target que segmenta el prompt distinto que el drafter se le entregan los ids del
drafter y puntúa esos. `tokenizer_compat.py` verifica el mapa de ids y reporta los
merges aparte por esta razón **[ran]** P48.

### 3.3 Medido

| drafter → target | vocab | mapa de ids | ids sólo del target | usable |
|---|---:|---|---:|---|
| Qwen2.5-3B → Qwen2.5-32B | 151.643 | archivo byte-idéntico, `c0382117…` | 0 | **sí** |
| Qwen2.5-3B → Qwen3-32B | 151.643 | mapa idéntico, merges distintos | 4 (`<think>`, `</think>`, `<tool_response>`, `</tool_response>`) | sí |
| Qwen2.5-3B → Qwen3.5/3.6/3.8-27B | 151.643 vs **248.044** | **distinto** | — | **no** |
| Qwen3.5-2B / 4B → Qwen3.8-27B | 248.044 | mapa idéntico | 7, todos especiales de audio/TTS | **sí** |

Filas 1–3 **[ran]** `results/P48-tokenizer-compat-20260916/`; fila 4 **[ran]**
`results/P55-graded-ranking-20260916/D0-tokenizers.txt`.

Un **id sólo del target** es uno que el target puede emitir y el drafter no puede
proponer: en cualquier posición donde el argmax del target sea ese id, la aceptación es
**0 por construcción** — un rechazo sistemático, no aleatorio. Para Qwen3-32B son las
etiquetas de pensamiento, manejadas sirviendo con el pensamiento apagado; para
Qwen3.8-27B son especiales de modalidad que la tarea de texto nunca alcanza. En el par
3.5 → 3.8 `<think>` es *compartido*, así que el canal de pensamiento es un flag de
serving, no un problema de ids.

---

## 4. LoRA: el parche, como álgebra lineal

### 4.1 El delta

LoRA **[read]** (Hu et al. 2021) reemplaza un peso congelado $W \in \mathbb{R}^{d_{in}\times d_{out}}$
por

$$
W' = W + \frac{\alpha}{r}\, A B, \qquad A \in \mathbb{R}^{d_{in}\times r},\; B\in\mathbb{R}^{r\times d_{out}},\; r \ll \min(d_{in}, d_{out}),
$$

entrena sólo $A, B$, y en inferencia calcula $xW' = xW + \tfrac{\alpha}{r}(xA)B$ — dos
productos delgados al lado del congelado. Cada adaptador de acá usa $r=16$,
$\alpha=32$, dropout 0,05 sobre las siete proyecciones del §1.2 **[ran]**
`adapter_config.json`.

Como $W$ nunca se toca, **la base queda residente y el delta es lo único que cambia
entre expertos** — se puede conmutar por pedido, batchear entre pedidos (§5.2),
versionar y descartar. Esa es toda la premisa arquitectónica: *el sistema es un pool
de deltas sobre una base residente.*

### 4.2 La cuenta, reconciliada con el artefacto

Por bloque de `Qwen2.5-3B` ($d = 2048$, $H_{kv} d_h = 256$, $d_{ff} = 11008$), los
parámetros LoRA son $r\,(d_{in} + d_{out})$ por matriz:

| matriz | $d_{in}\to d_{out}$ | parámetros |
|---|---|---:|
| $W_q$ | 2048 → 2048 | 65.536 |
| $W_k$ | 2048 → 256 | 36.864 |
| $W_v$ | 2048 → 256 | 36.864 |
| $W_o$ | 2048 → 2048 | 65.536 |
| $W_{gate}$ | 2048 → 11008 | 208.896 |
| $W_{up}$ | 2048 → 11008 | 208.896 |
| $W_{down}$ | 11008 → 2048 | 208.896 |
| por bloque | | **831.488** |
| × 36 bloques | | **29.933.568** |

A 4 bytes (fp32, el default de PEFT para adaptadores guardados) son **119.734.272
bytes**; el archivo en disco tiene **119.801.528 bytes** **[ran]** `STACK.md` §3 — la
diferencia de 67.256 bytes es el encabezado de safetensors. **La derivación y el
artefacto coinciden**, y el adaptador es ~1 % de los 3,09 B parámetros de la base.

### 4.3 QLoRA y AWQ: dos historias distintas de 4 bits

**Entrenamiento** (QLoRA **[read]**, Dettmers et al. 2023): la base congelada se guarda
en NF4 de 4 bits y se descuantiza al vuelo dentro de cada matmul; los gradientes fluyen
sólo a los $A, B$ en bf16. Acá la base se entrena en bf16 en Ampere y float16 en Turing
**[ran]** P2 — bf16 se verifica por capacidad de cómputo, porque
`torch.cuda.is_bf16_supported()` cuenta la emulación y el bf16 emulado no tiene kernel.

**Serving** (AWQ **[read]**, Lin et al. 2023): los pesos del *target* se cuantizan una
vez a int4 con escalas por grupo elegidas para proteger los canales salientes en
activación; es un $B_W$ más chico en el §2.3 y nada más. El 32B se sirve AWQ
(`bits: 4, group_size: 128` **[read]**) y **no lleva ningún adaptador** — que es la
observación sobre la que descansa el §10.1.

### 4.4 El objetivo de entrenamiento, y por qué el corpus es el prompt servido

SFT minimiza la entropía cruzada del próximo token sobre el span del asistente
solamente:

$$
\mathcal{L}(A,B) = -\sum_{t \in \text{asistente}} \log p_{\theta + \Delta}(x_t \mid x_{<t}),
$$

así que el adaptador aprende $p(x_t \mid x_{<t})$ **para los prefijos que el corpus
contiene**. Servirle un prefijo de otra distribución es pedirle que extrapole. El corpus
de email-full renderiza toda la cadena en un solo turno de asistente,
`<tag>…</tag>= {resultado}\n…\nIMPORTANT`, así que la condicional aprendida es
$p(\text{próximo tag o veredicto} \mid \text{resultados reales hasta acá})$. Servido vía
`tool_calls`, el modelo no puede recibir un resultado a mitad de generación y escribe
$p(\cdot \mid \hat h)$ donde $\hat h$ es un resultado **que inventó**; cada decisión
posterior condiciona sobre $\hat h \ne h$. Medido: el mismo adaptador da **0,808**
servido así (P43) y **0,992** servido como enseña el corpus (P55 A) **[ran]** — §8.1.

---

## 5. El motor: vLLM

### 5.1 PagedAttention y batching continuo

vLLM **[read]** (Kwon et al. 2023) guarda la caché KV del §2.2 en bloques de tamaño
fijo direccionados por una tabla de páginas por secuencia, así secuencias de distinto
largo comparten una GPU sin fragmentación y un pedido nuevo puede sumarse a un batch en
curso en cualquier paso (*batching continuo*). Eso es lo que convierte el "el batching
amortiza la lectura de pesos" del §2.4 en throughput que un cliente ve. Cada servidor de
acá es `vllm serve` 0.29.0 **[ran]** P3…P55.

### 5.2 Serving multi-LoRA

Con adaptadores $\{(A_i, B_i)\}$ residentes y un batch en el que el pedido $j$ nombra al
adaptador $i(j)$, la capa calcula

$$
y_j = x_j W + s\,(x_j A_{i(j)}) B_{i(j)},
$$

como un GEMM compartido para $xW$ más un par de GEMMs delgados *batcheados y
recolectados* (los kernels `bgmv` / Punica **[read]**, Chen et al. 2023; S-LoRA, Sheng
et al. 2023). Flags acá: `--enable-lora --max-lora-rank 16 --max-loras k --lora-modules
name=path` **[ran]** `STACK.md` §5. El adaptador lo elige el campo `model` del pedido,
que es cómo se direcciona el pool sin ningún router.

**C18 es un test de esa ecuación.** Un motor puede cargar $(A_i, B_i)$, loguear
`Loaded new LoRA adapter`, y aun así devolver $y = xW$ — el término delta ausente en
silencio. La compuerta de identidad sirve el mismo prompt por la base y por el
adaptador y exige que los textos difieran **[ran]** P33 (`Qwen2.5-3B`: difiere;
`Qwen3.5-4B`: idéntico) y P55 A (`email-full`: 6 de 8 sondas difieren → `applied`).

### 5.3 Teacher forcing en un prefill: `prompt_logprobs`

El prefill (§2.1) calcula $f_\theta(x_{<t})$ **para cada $t \le P$ a la vez**. Pedirle al
servidor `prompt_logprobs` devuelve, en cada posición, los top-$k$ ids del target con
log-probabilidades *y el rango del token real* — es decir, la distribución completa con
teacher forcing a lo largo de un texto dado, en una pasada, sin generar nada. Esa es la
operación que el §6.5 usa para verificar un draft: entregarle al target `prefijo +
draft`, leer si cada token del draft fue la elección de rango 1 del target. El preflight
midió la forma: una entrada por token del prompt, la primera `None`, cada una con
`rank` **[ran]** P55 A.

### 5.4 Stop strings y el harness de modo corpus

`stop=[…]` termina una generación en el momento en que se produce una cadena listada;
`include_stop_str_in_output` la devuelve. El loop de modo corpus (§8.1) es
exactamente: generar hasta `</tag>`, contestar el tag con una herramienta real,
anexar `= {resultado}\n`, seguir. Dos preflights lo guardan — el servidor honra el stop
sobre una continuación que el modelo no puede evitar (contar, parado en `3`), y un
cuerpo posicional de tag se convierte a clave por conteo de parámetros antes de que la
herramienta lo vea — ambos agregados después de un intento cada uno **[ran]** P55 A
intentos 1 y 2.

---

## 6. Decodificación especulativa

### 6.1 El algoritmo

Dados un target $p$ (grande, lento) y un drafter $q$ (chico, rápido) sobre el mismo
espacio de ids (§3.2), una ronda en el prefijo $x$ **[read]** (Leviathan et al. 2023;
Chen et al. 2023):

1. **Draft.** Muestrear $\tilde x_1 \sim q(\cdot\mid x)$, $\tilde x_2 \sim q(\cdot\mid x,\tilde x_1)$, …, $\tilde x_k$ — $k$ pasos de decode baratos.
2. **Verificar.** Una pasada del target sobre $x, \tilde x_1,\dots,\tilde x_k$ da
   $p(\cdot\mid x,\tilde x_{<i})$ para todo $i \le k+1$ a la vez (§5.3).
3. **Aceptar / rechazar**, de izquierda a derecha: aceptar $\tilde x_i$ con probabilidad
   $$
   a_i = \min\!\Big(1, \frac{p(\tilde x_i \mid x, \tilde x_{<i})}{q(\tilde x_i \mid x, \tilde x_{<i})}\Big).
   $$
   En el primer rechazo, en la posición $i$, emitir un token del **residual**
   $$
   p'(v) \propto \max\big(0,\; p(v \mid \cdot) - q(v \mid \cdot)\big)
   $$
   y terminar la ronda. Si se aceptan los $k$, emitir un token extra de
   $p(\cdot\mid x,\tilde x_{1:k})$ — la pasada ya lo calculó.

### 6.2 Exactitud

Para cualquier $v$: $\Pr[\text{emitir } v] = q(v)\min(1, p(v)/q(v)) + \big(1-\sum_u q(u)\min(1,p(u)/q(u))\big)\,p'(v) = \min(p(v),q(v)) + \max(0, p(v)-q(v)) = p(v)$.
**La salida se distribuye exactamente como la del target**, sea cual sea el drafter. Un
drafter malo cuesta velocidad, nunca corrección — por eso la aceptación se puede leer
como un puntaje *sobre el drafter* (§7).

### 6.3 Temperatura 0

Con $p$ one-hot en su argmax, $a_i = 1$ sii $\tilde x_i = \arg\max_v p(v\mid x,\tilde x_{<i})$
y $0$ si no. **La aceptación es igualdad de argmax**, y el prefijo aceptado es el
prefijo más largo del draft a lo largo del cual el target habría hecho la misma
elección. Es la identidad sobre la que `alpha/` descansó desde el principio y que
`accept_rank.py` lee token por token: *aceptado sii rango = 1* **[ran]** P55 A
preflight.

### 6.4 Cuánto compra, y por qué un target lento es donde paga

Si cada token se acepta independientemente con tasa $\alpha$, el número esperado de
tokens emitidos por ronda con $k$ drafts es

$$
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}.
$$

Sea $c = t_{\text{draft}} / t_{\text{target}}$ el costo de un paso del drafter relativo
a un paso del target. Una ronda cuesta $k\,c + 1$ pasos-de-target y rinde
$\mathbb{E}[\tau]$ tokens, así que

$$
\text{aceleración} \;=\; \frac{\mathbb{E}[\tau]}{k\,c + 1}
\;=\; \frac{1-\alpha^{k+1}}{(1-\alpha)(k c + 1)}.
$$

Dos lecturas. **La pasada de verificación del target cuesta una lectura de pesos para
$k+1$ posiciones** (§2.3–2.4): de ahí salen los tokens. Y **la ganancia crece cuando
$c \to 0$** — un 3B drafteando para un 32B tiene $c \approx 0,3$ por bytes de pesos; un
2B drafteando para un 27B *con 48 capas de atención lineal cuyo costo por token no
crece con el contexto* (§1.5) tiene un target lento por token por otra razón y un
drafter que no lo es — la observación del usuario de que el modelo grande *"es lento y
justifica muy bien"* es esta relación. Con $\alpha = 0,8$ y $k=4$: $\mathbb{E}[\tau] = 3,36$,
y a $c=0,3$ la aceleración es $1,5\times$; a $c = 0,1$, $2,4\times$. **Todavía no se
midió ninguna tasa de aceptación** — §11.

### 6.5 El atajo de dos instancias que se usa acá

El worker especulativo nativo de vLLM ata *un* drafter al arranque y no conmuta su
adaptador por pedido (el estado del reenvío de `lora_request` a ese worker es
**[unverified]** desde acá). Este repositorio no lo necesita para *medir*: el servidor
del drafter (3B, multi-LoRA) produce el draft entero en modo corpus; el servidor del
target lo puntúa por `prompt_logprobs` (§5.3). Bajo el §6.3, **los veredictos por token
son idénticos a lo que calcularía el loop fusionado** — un prefill por span en vez de
uno por ronda, más caro por token y exactamente igual de informativo. Lo que no da es
aceleración de reloj, que el §6.6 dice que este proyecto no compra.

### 6.6 La latencia es de EAGLE; el ranking es nuestro

EAGLE-3 / Medusa / DFlash **[read]** enganchan una cabeza chica a los estados ocultos
del *target* y draftean desde ellos; se entrenan por target y alcanzan una aceptación que
un modelo chico separado no puede. Existe un `Qwen2.5-32B-Instruct_EAGLE3` de la
comunidad **[read]**. Así que **la decodificación especulativa como dispositivo de
latencia está resuelta, y no por nosotros.** Lo que una cabeza atada no puede hacer es
comparar $k$ drafters *distintos* — hay una sola. **La aceptación como orden sin juez
sobre $k$ expertos** es la afirmación que esta arquitectura conserva (`REPORT.md` §6),
y es lo que el §7 formaliza.

---

## 7. La aceptación como ranking — la tesis, formalmente

### 7.1 Definiciones y la afirmación

Una suite es un conjunto de casos $\mathcal{C}$ con un verificador mecánico
$\mathrm{ok}(c, \text{respuesta}) \in \{0,1\}$. Para un experto $E$ (base + un adaptador)
su **calidad verificada** es $Q(E) = \tfrac{1}{|\mathcal C|}\sum_c \mathrm{ok}(c, E(c))$.
Para un target $T$, su **aceptación** en el caso $c$ es

$$
\alpha_T(E, c) = \frac{1}{n_c}\sum_{i=1}^{n_c} \mathbf{1}\big[\tilde x_i^{E}(c) = \arg\max p_T(\cdot \mid \text{prefijo}, \tilde x_{<i}^{E}(c))\big],
$$

la fracción de los $n_c$ *tokens de decisión* de $E$ en ese caso que el target habría
escrito él mismo (§6.3), y $\alpha_T(E) = \tfrac1{|\mathcal C|}\sum_c \alpha_T(E,c)$.

**La afirmación (P55):** para expertos $E_1,\dots,E_m$ sobre una suite,
$Q(E_a) > Q(E_b) \;\Rightarrow\; \alpha_T(E_a) > \alpha_T(E_b)$ — la aceptación ordena
expertos como los ordena la calidad verificada, **sin juez y sin verificador en tiempo
de serving**. Si vale, un pool selecciona entre expertos cercanos dejando que el target
puntúe sus drafts; si falla, el "router gratis" desaparece y la arquitectura sobrevive
sin él.

### 7.2 La precondición, y P55 A como su instancia

$\alpha_T(E)$ es acuerdo con $T$. Si $T$ está equivocado en un caso, un experto que
está *bien* es **rechazado ahí**, y $\alpha$ premia al experto que comparte el error del
target. Así que la afirmación es sobre calidad sólo cuando

$$
Q(T) \;\ge\; \max_a Q(E_a)
$$

— "es un puntaje de destilación sólo cuando el target es más fuerte que cada candidato"
(skill `alpha-surface`). La compuerta M-target de P55 es esa desigualdad como test
pareado, y disparó: en 351 casos humanos de triage el 32B acertó donde el experto falló
en **2** y falló donde el experto acertó en **87**, $p = 0,0$;
$Q(T)=0,746 < Q(E) = 0,989$ **[ran]** P55 A. El modelo grande sin entrenar *consigue
todos los hechos y aplica mal la regla*; un orden medido contra él habría sido un orden
por acuerdo con sus errores. **El instrumento estaba listo y correctamente no corrió.**

### 7.3 Tres α por caso, porque una cadena no es un token

Una cadena de triage son ~40 tokens de decisión de los que el veredicto es uno o dos.
La aceptación pesa cada token por igual, así que dos expertos que difieren sólo en
veredictos difieren en $\alpha$ por unos pocos puntos. Por eso el instrumento reporta,
por caso,

| | sobre | lee |
|---|---|---|
| $\alpha$ | todos los tokens de decisión | la afirmación tal como está |
| $\alpha_{\text{tags}}$ | los spans de llamada a herramienta | acuerdo de protocolo |
| $\alpha_{\text{verdict}}$ | el span final | los 1–2 tokens que el verificador puntúa |
| $\alpha_{\text{lcp}}$ | prefijo aceptado por span ÷ tokens | lo que una ronda especulativa se quedaría |

y **las líneas `= {resultado}` que aporta el harness están en el prefijo del target y en
ningún span** — puntuarlas sería puntuar la herramienta. Un resultado de "α no rankea"
dice entonces *dónde* vivió el acuerdo y no sólo que falló.

### 7.4 La prueba de orden

Para cada par $(E_a, E_b)$ que el verificador resuelve (§9.2), tomar los casos en que
ambos fueron puntuados y contar $u = \#\{c: \alpha(E_a,c) > \alpha(E_b,c)\}$,
$d = \#\{c: \alpha(E_a,c) < \alpha(E_b,c)\}$; los empates se excluyen; el binomial
exacto bilateral sobre $(u,d)$ decide. Escrito antes de cualquier corrida:
**SUPPORTED** si cada par resuelto concuerda; **FALSIFIED** si algún par se ordena al
revés con $p\le0,05$; **UNRESOLVED** si el verificador vio una diferencia y $\alpha$ no —
*un fracaso de la afirmación tal como está, no un empate* **[ran]**
`results/P55-graded-ranking-20260916/BRIEF.md`.

---

## 8. Las tareas, como funciones

### 8.1 El triage, la cadena y la deriva con números

Un mensaje $m$ lleva hechos $\phi(m) = (\text{automated}, w, a, s, f)$ — *yo escribí en
el hilo*, *dirigido a mí*, *pide algo*, *remitente frecuente*. La etiqueta es

$$
y(m) = \neg\,\text{automated} \;\wedge\; \big[\,w + a + s + f \;\ge\; 2\,\big],
$$

`training/email/inbox.py::important`. **El listado no muestra ninguno de $w, a, f$** —
viven detrás de tres herramientas (`thread_history` → $w$, `sender_stats` → $f$,
`message` → $a$ y el cuerpo para $s$), y `tests/test_email.py` afirma que la mejor regla
que sólo lee el listado da exactamente la clase mayoritaria en mensajes humanos
**[ran]**. Así que el trabajo del experto es una *cadena*: decidir qué herramientas,
llamarlas con el argumento correcto, leer los resultados, aplicar la regla.

El harness de modo corpus $\mathcal H$ es la recursión

$$
s_0 = \text{prompt},\qquad
\tilde s_{j} = E(s_{j-1}) \text{ hasta } \texttt{</tag>},\qquad
s_j = s_{j-1} \,\|\, \tilde s_j \,\|\, \texttt{= } \mathrm{tool}(\tilde s_j)\texttt{\textbackslash n},
$$

hasta que un span no lleva tag, cuyo texto se parsea como veredicto. Los *spans*
$\tilde s_j$ son las decisiones del experto y lo único que el target puntúa (§7.3).

| serving | condiciona cada decisión sobre | exactitud humanos |
|---|---|---:|
| `tool_calls` (P43) | $\hat h$ — un resultado que el experto **inventó** porque no podía recibir uno a mitad de turno | **0,741** |
| modo corpus (P55 A) | $h$ — el resultado real, inyectado en `</tag>` | **0,989** |
| base pelada, cualquiera | nada — 0 llamadas | 0,345 |

**[ran]** — el mismo adaptador de 598 ejemplos, los mismos 351 casos humanos. La
diferencia de 25 puntos es la deriva del §4.4 hecha visible: nada en los pesos cambió.

### 8.2 El techo, y dónde existe un gradiente

Dos cosas tienen que valer para que el §7 sea medible: $Q(T) \ge \max Q(E)$ **y** margen
arriba del mejor experto. En triage no vale ninguna — $Q(E) = 0,989$ deja a lo sumo
cuatro casos humanos para que un target gane (un par 4 : 0 da $p = 0,0625$, por debajo
de la resolución), y $Q(T)=0,746$. La suite del desk (`training/email/desk.py`) varía la
profundidad por *cuánto se entrega* independientemente de la pregunta; en su región
`commitment` P51 midió al 32B en **1,000 en cada profundidad** y a la base cayendo
**1,000 → 0,800 → 0,133 → 0,000** **[ran]** `results/P51-desk-profile-20260916/` — un
target más fuerte por construcción y un gradiente sobre el que ningún experto se va a
sentar. Ese es el rediseño que quedó para decidir.

### 8.3 Expertos graduados

Subconjuntos anidados de un corpus: un barajado con semilla, y cada grado es un prefijo
de él, $\mathcal D_{75} \subset \mathcal D_{200} \subset \mathcal D_{598}$
(`training/harness/graded.py`, balance 43 % / 49 % importante **[ran]**). El anidamiento
es lo que hace que *cuánto* sea la única variable: un grado que vio ejemplos distintos en
vez de menos confundiría cantidad con contenido. Misma base, mismos $r, \alpha$, mismas
épocas — así que si $Q$ los ordena, hay, por primera vez, un orden con el que $\alpha$
puede concordar o no.

---

## 9. Estadística usada, y sólo esta

### 9.1 La barra de clase mayoritaria

Contestar la clase mayoritaria a cada caso da $\max(\pi, 1-\pi)$; un sistema por debajo
no aprendió nada. Sobre los 351 casos humanos de triage es **0,655** **[ran]**; sobre
los 475 completos es más fácil, porque `noreply@` es gratis, y por eso los mensajes
humanos son el subconjunto reportado.

### 9.2 El test de signos exacto bilateral sobre pares discordantes

Dos brazos puntuados sobre los mismos casos discrepan en $n_d$ de ellos; $u$ de esos
favorecen a $A$. Bajo $H_0$ cada caso discordante favorece a cualquiera de los dos con
probabilidad $\tfrac12$, así que $u \sim \mathrm{Bin}(n_d, \tfrac12)$ y

$$
p = \min\Big(1,\; 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u, n_d-u)\big]\Big),
$$

`training/harness/bar.py::sign_test`. Los empates no llevan información y se excluyen
— eso es lo que lo hace el test pareado y no una comparación de dos proporciones. **Los
totales nunca se comparan**: 84, 81, 82 correctos sobre casos idénticos fueron tres
empates por este test, y leerlos como movimiento fue el error que el chequeo de
potencia de P43 terminó.

### 9.3 Potencia y el tamaño que resuelve un efecto

Para una barra $\pi_0$ y $n$ casos, el umbral de aprobación es el menor $t$ con
$\Pr[\mathrm{Bin}(n,\pi_0)\ge t] \le 0,05$, y la **potencia** para ver una tasa real
$\pi_0+\delta$ es $\Pr[\mathrm{Bin}(n,\pi_0+\delta) \ge t]$. `bar.resolvable` y
`bar.n_for` son esas dos funciones. A $n=351$ sobre $0,741$: $\delta=0,07$ se ve el
**93 %** de las veces, $\delta=0,05$ sólo el **71 %** **[ran]** — por eso los grados de
P55 se pusieron en 75 / 200 / 598 y no más cerca.

### 9.4 Qué significa margen

Un tratamiento no puede mover una línea de base que está en el techo; hay que verificar
que el brazo tenga lugar *antes* de comprarlo (el adaptador ARC de P42, 0,825 sobre una
base en 0,815, era irresoluble a $n=200$ **[ran]**). El §8.2 es la misma regla aplicada
al target.

---

## 10. Por qué la familia Qwen 3, y `Qwen3.8-27B` como modelo grande

### 10.1 El target no necesita LoRA

La decodificación especulativa tiene dos modelos y dos trabajos. El **drafter** es el
pool — el multi-LoRA es requisito *suyo*. El **target** verifica en una pasada (§6.1
paso 2) y es un modelo denso, sin modificar. C18 — *vLLM carga un LoRA sobre una base
3.x y sirve la base igual* **[ran]** P33 — es una afirmación sobre servir un LoRA, así
que **restringe al drafter y no dice nada del target**. El 32B de acá se sirve AWQ sin
adaptador (§4.3) y esa es exactamente la forma del target.

### 10.2 El espacio de ids

Del §3.3: un drafter Qwen 2.5 puede ser verificado por `Qwen3-32B` hoy (mapa idéntico,
cuatro ids de pensamiento a mantener apagados); **no puede** ser verificado por
`Qwen3.8-27B` (248.044 ≠ 151.643). Pero `Qwen3.5-2B` y `Qwen3.5-4B` **sí pueden** —
mapa idéntico, siete especiales de audio/TTS que la tarea de texto nunca alcanza,
`<think>` compartido **[ran]** D0. Así que el par *drafter-3.5 → target-3.8-27B* es
sano en espacio de ids, y los expertos 3B de hoy no son los drafters de ese par.

### 10.3 El canal de pensamiento

Un target que piensa abre `<think>` antes de su respuesta; el drafter escribe la
respuesta. En cada posición así la aceptación es 0 (§3.3). El target se sirve con el
pensamiento deshabilitado y el conteo de ids `<think>` en su salida greedy sobre la
suite tiene que ser **0** — D3, una compuerta dentro de D4.

### 10.4 La arquitectura híbrida y C18: qué muestra la evidencia

| afirmación del análisis externo | qué muestra el log de P33 **[ran]** | estado |
|---|---|---|
| la clase es un envoltorio multimodal | `Resolved architecture: Qwen3_5ForConditionalGeneration` | **confirmada** |
| la atención lineal / Gated DeltaNet es real | `qwen_gdn_linear_attn.py … GDN decode kernel: cuda`; `layer_types` 24 lineales + 8 completas **[read]** | **confirmada** |
| los kernels LoRA de vLLM no despachan en las capas de lenguaje | cada línea `no matching PunicaWrapper … will be ignored` nombra un módulo **`visual.`**; `_lora_expand_kernel` compiló JIT **durante la inferencia** | **contradicha** |
| restringir `target_modules` a la MLP para desbloquearlo | "el adaptador tocaba sólo los MLP" fue un diagnóstico que P33 **retiró** — el árbol cargado lleva `q_proj` | **sin respaldo** |
| un RFC cierra el LoRA por pedido en el worker especulativo; SGLang maneja híbridos | no verificado desde acá | **[unverified]** |

Lo que se sabe: el adaptador es real (G1: `lora_B` se movió, la salida cambió en
proceso), el motor dice que lo cargó, el texto servido es igual al de la base. **La
falla está medida; su mecanismo no**, y la regla de este proyecto después de dos
diagnósticos retirados es leer el mecanismo con el log en la mano (D2), no adoptar uno.

### 10.5 La ruta, como mecanismos

| # | mecanismo | estado |
|---|---|---|
| D0 | un drafter 3.x que comparta espacio de ids con 3.8-27B | **[ran]** ✓ |
| D1 | C18 bajo un vLLM más nuevo | vacío — la cadena instala el último y es **0.29.0**, la versión de P33 **[ran]** |
| D2 | el mecanismo de C18: G3 merge-and-serve; mapeo clave PEFT ↔ módulo vLLM, con el log | siguiente |
| D3 | pensamiento apagado, verificado por conteo | dentro de D4 |
| D4 | el instrumento de P55, `--base Qwen/Qwen3.5-4B --target Qwen/Qwen3.8-27B`, pool graduado reentrenado sobre 3.5-4B | bloqueado por D2 |

**Por qué el orden.** Todo en §6–§7 es independiente del target dado el §3.2; el
instrumento construido sobre Qwen 2.5 es el que corre D4. Si el §7 falla sobre 2.5, D4
habría comprado una versión más rápida de un mecanismo que no rankea. Nada de lo de
arriba depende de D; D4 depende de todo.

---

## 11. Mapa: sección → corrida

| sección | fórmula / afirmación | corrida que la instancia |
|---|---|---|
| §1.3 | ancho de embedding > vocabulario | `STACK.md` §1, P48 |
| §1.4–1.5 | dimensiones, `layer_types` híbridos | `config.json` **[read]** 2026-09-17; log de P33 |
| §2.4 | batching: 475 cadenas, 31 s / 230 s | P55 A `session_a.json` |
| §3.3 | tabla de mapas de ids | P48; P55 `D0-tokenizers.txt` |
| §4.2 | 29.933.568 parámetros ↔ 119.801.528 bytes | `STACK.md` §3 |
| §4.4, §8.1 | deriva: 0,741 → 0,989 | P43 `arm_email_475.json`; P55 A |
| §4.4, §9.2 | **un release reproduce**: re-servido 0 : 0 contra su registro; reentrenado 1 : 0 — varianza de entrenamiento un caso en 475 | P57 `release.json`, `releases/email-full@v1.json` |
| §5.2 | compuerta de identidad C18 | P33 `lora_matrix.json`; P55 A `applied`; **Fase 0 P56: los dos miembros 3/3 `applied`, herramientas alcanzables, stop honrado** |
| §5.3 | forma de `prompt_logprobs` | P55 A `preflight_target` |
| §5.4 | preflight del stop; shim posicional | P55 A intentos 1, 2 |
| §7.2 | $Q(T) < \max Q(E)$: 2 : 87, $p=0$ | P55 A `target_gate` |
| §8.2 | techo 0,989; gradiente de commitment | P55 A; P51 `desk_profile.json` |
| §9.3 | potencia a $n=351$ | `bar.resolvable` **[ran]** 2026-09-16 |
| §10.2 | espacio de ids 3.5 → 3.8 | P55 `D0-tokenizers.txt` |
| §10.5 D1 | vLLM resuelve a 0.29.0 | log de boot de P55 A |
| §6.4 | **α, $\mathbb{E}[\tau]$, aceleración** | **todavía no medido** |
| §7.4 | **el veredicto de orden** | **todavía no corrió** — bloqueado hasta una suite donde valga el §7.2 |
