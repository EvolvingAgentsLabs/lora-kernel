# Fundamentos — la matemática debajo de lora-kernel, atada a lo que corrió

> *[Read me in English](../FOUNDATIONS.md)*

Este documento dice, paso a paso y en matemática, qué son los modelos, por qué generar
con ellos es lento, qué es un LoRA, qué hace el motor, qué calcula la decodificación
especulativa, qué mide la aceptación entre un experto chico y el modelo grande de su
subdominio, qué son las tareas y el router como funciones, y por qué la familia Qwen 3
provee las dos mitades de un par.
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

```math
p_\theta(x_t \mid x_{<t}) = \mathrm{softmax}\big(f_\theta(x_{<t})\big)_{x_t},
\qquad
p_\theta(x_{1:T}) = \prod_{t=1}^{T} p_\theta(x_t \mid x_{<t}).
```

Generar es la recursión $x_{t} \sim p_\theta(\cdot \mid x_{\lt t})$, un id a la vez;
**cada paso necesita el prefijo entero y no puede empezar antes de que exista el id
anterior.** Ese único hecho — la generación es secuencial en $t$ — es lo que el §2
tarifa y lo que el §6 explota.

A temperatura 0 el muestreo colapsa a $x_t = \arg\max_v f_\theta(x_{\lt t})_v$, y toda la
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

1. **Pre-norm.** $\tilde h = \mathrm{RMSNorm}(h) = h \oslash \sqrt{\tfrac{1}{d}\sum_j h_j^2 + \epsilon}\ \odot\  g$.

2. **Proyecciones.** $Q = \tilde h W_q,\  K = \tilde h W_k,\  V = \tilde h W_v$ con
   $W_q \in \mathbb{R}^{d\times H d_h}$ y $W_k, W_v \in \mathbb{R}^{d \times H_{kv} d_h}$.
   Con $H_{kv} \lt  H$ cada cabeza de clave/valor sirve a $H/H_{kv}$ cabezas de consulta —
   *atención de consultas agrupadas*, que es lo que hace más chica la caché KV del §2.2.

3. **Posición rotatoria (RoPE).** Cada par de coordenadas $(q_{2i}, q_{2i+1})$ en la
   posición $t$ se rota un ángulo $t\ \omega_i$ con $\omega_i = \theta^{-2i/d_h}$; lo
   mismo para $k$. Entonces $\langle q_t, k_s\rangle$ depende sólo de $t-s$ — la posición
   entra como fase relativa. Las dos familias usan $\theta = 10^6$ **[read]**.

4. **Atención causal**, por cabeza:

```math
A = \mathrm{softmax}\!\Big(\frac{QK^\top}{\sqrt{d_h}} + M\Big)V,
\qquad M_{ts} = \begin{cases}0 & s\le t\\ -\infty & s>t\end{cases}
```

   y luego $h \leftarrow h + A\ W_o$.

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
sobre ellas no enmascara nada, y `STACK.md` §1 (el tag `v0.1-foundations`) lo registra porque una cabeza tipada
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

```math
S_t = \alpha_t\,\big(I - \beta_t\, k_t k_t^\top\big)\, S_{t-1} \;+\; \beta_t\, k_t v_t^\top,
\qquad o_t = S_t^\top q_t,
```

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

```math
\text{bytes}_{KV}(t) \;=\; 2 \cdot L \cdot H_{kv} \cdot d_h \cdot t \cdot b,
```

con $b$ bytes por elemento. Para `Qwen2.5-3B` en bf16: $2\cdot 36\cdot 2\cdot 128\cdot 2 = 36{.}864$
bytes por token — **36 KB/token**, 147 MB a 4.096 tokens. Para el 32B (caché bf16
sobre una base AWQ): $2\cdot 64\cdot 8\cdot 128\cdot 2 = 262{.}144$ bytes — **256 KB/token**,
1 GB a 4.096. GQA es por qué estos números llevan $H_{kv}$ y no $H$. Las capas de
atención lineal del §1.5 llevan en cambio un estado fijo $d_k\times d_v$, que es su
razón de ser.

### 2.3 El decode está limitado por los bytes de pesos

Un paso de decode lee cada peso una vez. Con $B_W$ bytes de pesos y ancho de banda
$\mathcal{B}$, el piso es

```math
t_{\text{step}} \;\gtrsim\; \frac{B_W}{\mathcal{B}} \;+\; \frac{\text{bytes}_{KV}(t)}{\mathcal{B}}.
```

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

### 2.5 Identidad de la KV bajo una profundidad no tocada, y conmutar a mitad de generación (E6)

La recursión del §1.2 hace que la salida del bloque $\ell$ dependa sólo de los bloques
*debajo* de él: $h^{(\ell)}$ es una función de $\theta_0,\dots,\theta_{\ell-1}$ y de la
entrada, nunca de $\theta_\ell,\dots,\theta_{L-1}$. Así que si un LoRA deja intacto cada
bloque bajo cierta profundidad $k$ ($\theta_\ell = \theta_\ell^{\text{base}}$ para
$\ell \lt  k$),

```math
h^{(\ell)}_{\text{experto}} = h^{(\ell)}_{\text{base}}, \qquad K_\ell = K_\ell^{\text{base}}, \qquad V_\ell = V_\ell^{\text{base}}, \qquad \text{para todo } \ell < k \text{ y todo prefijo.}
```

Es una identidad mecánica, no estadística — vale bit a bit o la derivación está mal —
y es la condición bajo la cual un pedido puede conmutar qué experto contesta *a mitad
de generación* sin invalidar la KV ya calculada para las capas bajo $k$.

**Medido [ran] `results/E6-upper-layers-20260927`.** El miembro de la escuela
reentrenado con su LoRA en las capas 21–41 de 42 solamente: **70/70 retenidos, 15/15 en
la demo**, exactamente el puntaje del miembro completo (0 perdidos contra él), y un
control base-contra-base sobre las 21 capas debajo del rango adaptado volvió
bit-idéntico, confirmando la identidad de arriba en vez de sólo suponerla. Dos
salvedades viajan con el resultado. El E4B comparte KV entre grupos de capas (24 de 42
son grupos que comparten caché **[ran]**), así que una conmutación igual recomputa las
capas 21–23 aunque *sus propios* pesos estén debajo de $k$ — es el compartido, no el
LoRA, lo que alcanza el rango adaptado. Y la suite está en el techo del miembro completo
con una sola semilla (§9.4), así que esto es un chequeo de mecanismo, todavía no una
comparación de calidad.

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

```math
W' = W + \frac{\alpha}{r}\, A B, \qquad A \in \mathbb{R}^{d_{in}\times r},\; B\in\mathbb{R}^{r\times d_{out}},\; r \ll \min(d_{in}, d_{out}),
```

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
parámetros LoRA son $r\ (d_{in} + d_{out})$ por matriz:

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
bytes**; el archivo en disco tiene **119.801.528 bytes** **[ran]** `STACK.md` §3 (el tag `v0.1-foundations`) — la
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

```math
\mathcal{L}(A,B) = -\sum_{t \in \text{asistente}} \log p_{\theta + \Delta}(x_t \mid x_{<t}),
```

así que el adaptador aprende $p(x_t \mid x_{\lt t})$ **para los prefijos que el corpus
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

Con adaptadores $\lbrace (A_i, B_i)\rbrace$ residentes y un batch en el que el pedido $j$ nombra al
adaptador $i(j)$, la capa calcula

```math
y_j = x_j W + s\,(x_j A_{i(j)}) B_{i(j)},
```

como un GEMM compartido para $xW$ más un par de GEMMs delgados *batcheados y
recolectados* (los kernels `bgmv` / Punica **[read]**, Chen et al. 2023; S-LoRA, Sheng
et al. 2023). Flags acá: `--enable-lora --max-lora-rank 16 --max-loras k --lora-modules
name=path` **[ran]** `STACK.md` §5 (el tag `v0.1-foundations`). El adaptador lo elige el campo `model` del pedido,
que es cómo se direcciona el pool sin ningún router.

**C18 es un test de esa ecuación.** Un motor puede cargar $(A_i, B_i)$, loguear
`Loaded new LoRA adapter`, y aun así devolver $y = xW$ — el término delta ausente en
silencio. La compuerta de identidad sirve el mismo prompt por la base y por el
adaptador y exige que los textos difieran **[ran]** P33 (`Qwen2.5-3B`: difiere;
`Qwen3.5-4B`: idéntico) y P55 A (`email-full`: 6 de 8 sondas difieren → `applied`).

### 5.3 Teacher forcing en un prefill: `prompt_logprobs`

El prefill (§2.1) calcula $f_\theta(x_{\lt t})$ **para cada $t \le P$ a la vez**. Pedirle al
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

### 5.5 La caché de prefijos se indexa por posición, no por contenido (E5)

La caché de prefijos de vLLM (§5.1) hashea los bloques de una secuencia **en orden
desde la posición 0**: el hash del bloque $j$ encadena del bloque $j-1$, así que un hit
de caché en el bloque $j$ exige que todo bloque anterior también coincida. Con
$\text{hit}(x)$ la cantidad de tokens que $x$ comparte, desde la posición 0, con alguna
secuencia servida antes,

```math
\text{TTFT}(x) \;\approx\; t_{\text{prefill}}(|x| - \text{hit}(x)),
```

con $t_{\text{prefill}}$ el costo limitado por cómputo del §2.1. **Que el contenido de
un bloque sea estático no lo vuelve cacheable** — sólo lo vuelve cacheable que su
*posición* sea un prefijo compartido. Un bloque de llamadas a herramientas servido,
como se entrenó, después del pedido del usuario queda detrás de los tokens de ese
pedido, que difieren por llamada; $\text{hit}(x)$ colapsa a lo que comparta el system
prompt, y el bloque entero se recomputa cada vez a pesar de ser idéntico byte a byte
entre pedidos.

**Medido [ran] `results/E5-engine-baseline-20260928`.** El bloque de 54 herramientas de
OpenClaw (7.205 tokens de Gemma) servido después del pedido: TTFT **0,10 → 1,70 s
(16,8×)** con la caché de prefijos encendida; throughput a batch 8 **132 → 108 tok/s**;
exactitud **70/70 → 39/70** (el miembro deja de llamar a su propia herramienta en 28 de
31 fallas — una instancia de la deriva del §4.4, no del motor). El mismo bloque no
cuesta **nada** (0,09–0,11 s) en el único caso donde todo el prefijo, bloque incluido,
volvió a aparecer desde la posición 0 — **el orden, no el tamaño, derrota a la caché.**
Dos LoRAs servidos en un mismo batch (§5.2) conservan **0,88** del throughput de un
adaptador solo (contención en el edge, medida sobre una ráfaga de 16); podar el bloque
de herramientas al del miembro sigue siendo el default tanto en exactitud como en
latencia.

### 5.6 Throughput con varios adaptadores bajo carga, estable en vez de una ráfaga (C1)

El modelo de costo del §5.2 dice que un pedido bajo el adaptador $i$ cuesta un $xW$ compartido más un
par de términos finos de rango $r$, en batch — barato al lado de la lectura de pesos compartida (§2.3–2.4).
Si eso se sostiene bajo carga real, y no sólo en la lectura de una sola ráfaga de la línea de contención
del propio §5.5, mezclar $A$ adaptadores distintos en un mismo batch debería costar casi nada contra
servir las mismas $K$ sesiones con un solo adaptador. Se define el cociente a una cantidad fija de
sesiones $K$:

```math
r_A(K) = \frac{\mathrm{tps}(K\ \text{sesiones},\ A\ \text{adaptadores mezclados})}{\mathrm{tps}(K\ \text{sesiones},\ 1\ \text{adaptador})},
```

con $\mathrm{tps}$ los tokens/s generados agregados del servidor. **NO MATERIAL CONTENTION** si y sólo
si $r_A \ge 0,8$ — la vara fijada en el brief antes de la corrida, la misma vara contra la que se leyó la
propia ráfaga única del §5.5.

**Medido [ran] `results/C1-concurrency-20260929`.** Cuatro miembros (`school-s0`, `upper-s0`, `staff-s0`,
`out-s0`) en una L4, `google/gemma-4-E4B-it` bf16, $K \in \lbrace 1, 8, 16, 32\rbrace$ sesiones, cada sesión
rotando entre los adaptadores en juego: $r_4(16) = 278,6 / 269,7 = 1,03$ — **por encima de la vara de 0,8,
y por encima de 1**, así que mezclar cuatro adaptadores no cuesta nada medible contra uno solo a esta carga.
El escalado casi lineal del §2.4 en la cantidad de secuencias simultáneas se sostiene en toda la corrida
y no es un artefacto de un solo adaptador: el throughput total va **22,7 → 135,1 → 278,6 → 504,3 tok/s**
para $K = 1, 8, 16, 32$ (celdas de cuatro adaptadores), cada una dentro del ruido de su contraparte de un
solo adaptador (269,7, 490,8 en $K=16, 32$). El TTFT se mantiene bajo en todo el rango (p95 **0,24 s** en
$K=32$, un octavo del presupuesto de 2 s fijado en el brief), 0 errores de 128 pedidos, y el techo está
por encima de 32 — no se alcanzó. **Esto reemplaza el 0,88 de E5** ([`RECORD.md`](RECORD.md) §2): ese
número venía de una sola ráfaga de 16 pedidos, dentro del margen de una medición única, no de una curva —
la falla contra la que avisan tanto el §9.4 como el §1.1: leer una sola tirada como la tasa.

<!-- IMAGE PLACEHOLDER — see docs/img/IMAGES.md
<img src="../img/c1-throughput.png" alt="Gráfico de líneas de tokens generados por segundo agregados contra sesiones simultáneas K = 1, 8, 16, 32 en una L4: un adaptador y cuatro adaptadores mezclados quedan uno encima del otro, subiendo casi linealmente hasta unos 500 tokens por segundo en K = 32; un punto de dos adaptadores en K = 16 cae sobre la misma línea." width="100%">

*C1 [ran] `results/C1-concurrency-20260929`: mezclar cuatro adaptadores en un lote no cuesta nada medible, $r_4(16) = 1,03$ contra una vara de 0,8.*
-->

---

## 6. Decodificación especulativa

### 6.1 El algoritmo

Dados un target $p$ (grande, lento) y un drafter $q$ (chico, rápido) sobre el mismo
espacio de ids (§3.2), una ronda en el prefijo $x$ **[read]** (Leviathan et al. 2023;
Chen et al. 2023):

1. **Draft.** Muestrear $\tilde x_1 \sim q(\cdot\mid x)$, $\tilde x_2 \sim q(\cdot\mid x,\tilde x_1)$, …, $\tilde x_k$ — $k$ pasos de decode baratos.
2. **Verificar.** Una pasada del target sobre $x, \tilde x_1,\dots,\tilde x_k$ da
   $p(\cdot\mid x,\tilde x_{\lt i})$ para todo $i \le k+1$ a la vez (§5.3).
3. **Aceptar / rechazar**, de izquierda a derecha: aceptar $\tilde x_i$ con probabilidad

```math
a_i = \min\!\Big(1, \frac{p(\tilde x_i \mid x, \tilde x_{<i})}{q(\tilde x_i \mid x, \tilde x_{<i})}\Big).
```

   En el primer rechazo, en la posición $i$, emitir un token del **residual**

```math
p'(v) \propto \max\big(0,\; p(v \mid \cdot) - q(v \mid \cdot)\big)
```

   y terminar la ronda. Si se aceptan los $k$, emitir un token extra de
   $p(\cdot\mid x,\tilde x_{1:k})$ — la pasada ya lo calculó.

### 6.2 Exactitud

Para cualquier $v$: $\Pr[\text{emitir } v] = q(v)\min(1, p(v)/q(v)) + \big(1-\sum_u q(u)\min(1,p(u)/q(u))\big)\ p'(v) = \min(p(v),q(v)) + \max(0, p(v)-q(v)) = p(v)$.
**La salida se distribuye exactamente como la del target**, sea cual sea el drafter. Un
drafter malo cuesta velocidad, nunca corrección — por eso la aceptación se puede leer
como un puntaje *sobre el drafter* (§7).

### 6.3 Temperatura 0

Con $p$ one-hot en su argmax, $a_i = 1$ sii $\tilde x_i = \arg\max_v p(v\mid x,\tilde x_{\lt i})$
y $0$ si no. **La aceptación es igualdad de argmax**, y el prefijo aceptado es el
prefijo más largo del draft a lo largo del cual el target habría hecho la misma
elección. Es la identidad sobre la que `alpha/` descansó desde el principio y que
`accept_rank.py` lee token por token: *aceptado sii rango = 1* **[ran]** P55 A
preflight.

### 6.4 Cuánto compra, y por qué un target lento es donde paga

Si cada token se acepta independientemente con tasa $\alpha$, el número esperado de
tokens emitidos por ronda con $k$ drafts es

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}.
```

Sea $c = t_{\text{draft}} / t_{\text{target}}$ el costo de un paso del drafter relativo
a un paso del target. Una ronda cuesta $k\ c + 1$ pasos-de-target y rinde
$\mathbb{E}[\tau]$ tokens, así que

```math
\text{aceleración} \;=\; \frac{\mathbb{E}[\tau]}{k\,c + 1}
\;=\; \frac{1-\alpha^{k+1}}{(1-\alpha)(k c + 1)}.
```

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
sobre $k$ expertos** es la afirmación que esta arquitectura conserva ([`RECORD.md`](RECORD.md) §5),
y es lo que el §7 formaliza.

### 6.7 Aceptación del MTP bajo un LoRA de dominio, y restricción de capas (C0, C0-upper)

La propia cabeza de predicción multi-token (MTP) de Gemma draftea a partir de los
estados ocultos finales del propio target — una cabeza atada en el sentido del §6.6,
así que la fórmula de aceleración del §6.4 aplica con $c$ el costo de la cabeza MTP
relativo a un paso de decode completo. **Un LoRA de dominio sobre el target mueve los
estados ocultos de los que lee la cabeza, y la aceptación cae con ellos.**

**Medido [ran] `results/C0-aligned-draft-20260927`** (A100, bf16, el MTP nativo de
`gemma-4-12B-it`, $k=4$): sin adaptador la aceleración es **2,80×** en el dominio y
**2,60×** en general; con el LoRA del experto encendido, la aceptación de dominio cae y
la aceleración con ella — **1,92× en el dominio ($\alpha$ 0,34, contra
$\alpha \approx 0,79$ sin adaptador)**, **2,40× en general** (el LoRA apenas toca los
estados ocultos de texto general). **El LoRA le cuesta al drafter, no al target** — la
$c$ del §6.4 no cambia; lo que se movió es $\alpha$.

**¿Restringir el LoRA a las capas superiores lo recupera? [ran]
`results/C0-upper-e4b-20260927`.** La esperanza natural de la identidad del §2.5 — si
las capas inferiores quedan intactas, tal vez la *entrada* de la cabeza también quede
intacta — hay que chequearla, porque la cabeza lee el estado de la *última* capa, que
un LoRA confinado a la mitad superior igual mueve. Normalizar la aceptación del
adaptador restringido a la mitad superior entre la base intacta y el modelo totalmente
adaptado:

```math
\rho = \frac{\alpha_{\text{superior}} - \alpha_{\text{completo}}}{\alpha_{\text{base}} - \alpha_{\text{completo}}},
```

así que $\rho = 1$ dice que restringir las capas recupera toda la aceptación que perdió
el LoRA completo, $\rho = 0$ dice que es exactamente tan dañino como el LoRA completo.
Sobre el E4B y su propio drafter MTP, dominio: $\alpha_{\text{base}} = 0,82$,
$\alpha_{\text{completo}} = 0,44$, $\alpha_{\text{superior}} = 0,43$, así que

```math
\rho = \frac{0,43 - 0,44}{0,82 - 0,44} = -0,02.
```

**NONE: restringir las capas no ayuda al drafter** — $\rho$ está en (dentro del ruido
de) cero, no cerca de 1. Restringir el adaptador a las capas cercanas a la cabeza igual
mueve exactamente los estados que la cabeza lee. En una L4 el propio MTP del E4B sigue
pagando con el LoRA encendido (2,4× batch 1, 2,1× batch 8); servido en vLLM, el
adaptador de mitad superior corre exactamente a la *velocidad* del adaptador completo —
restringir capas ahorra memoria, no tiempo de decode (**[read]**, probablemente capas
rellenadas con ceros en vez de saltadas).

**Un régimen distinto, donde se mueve $c$ en vez de $\alpha$ [ran]
`results/MAC2-llamacpp-20260927`.** Sobre llama.cpp/Metal (la Air), el MTP de Gemma
*enlentece* al 12B en vez de acelerarlo — **0,52×** con el LoRA en su dominio,
**0,66–0,87×** en el resto. La salida de la decodificación especulativa es idéntica en
ambos casos (20/20), así que no es un efecto de $\alpha$: la $c$ del §6.4, el costo del
drafter relativo al del target, es lo bastante alta en este motor como para que
$kc+1$ supere a $\mathbb{E}[\tau]$ aun con la misma aceptación que una GPU pagaría con
gusto — la misma fórmula, un término de hardware distinto.

---

## 7. La aceptación — entre un experto chico y el modelo grande de su subdominio

### 7.1 Definiciones y la afirmación

Una suite es un conjunto de casos $\mathcal{C}$ con un verificador mecánico
$\mathrm{ok}(c, \text{respuesta}) \in \lbrace 0,1\rbrace$. Para un experto $E$ (base + un adaptador)
su **calidad verificada** es $Q(E) = \tfrac{1}{|\mathcal C|}\sum_c \mathrm{ok}(c, E(c))$.
Para un target $T$, su **aceptación** en el caso $c$ es

```math
\alpha_T(E, c) = \frac{1}{n_c}\sum_{i=1}^{n_c} \mathbf{1}\big[\tilde x_i^{E}(c) = \arg\max p_T(\cdot \mid \text{prefijo}, \tilde x_{<i}^{E}(c))\big],
```

la fracción de los $n_c$ *tokens de decisión* de $E$ en ese caso que el target habría
escrito él mismo (§6.3), y $\alpha_T(E) = \tfrac1{|\mathcal C|}\sum_c \alpha_T(E,c)$.

**La afirmación que este proyecto hizo primero (P55), y qué fue de ella.** *La aceptación
ordena a los expertos como los ordena la calidad verificada* — $Q(E_a) > Q(E_b) \Rightarrow
\alpha_T(E_a) > \alpha_T(E_b)$, un router gratis. Su precondición (§7.2) falló dos veces para
un target sin entrenar y la pregunta se cerró sin veredicto ([`RECORD.md`](RECORD.md) §2).

**La afirmación ahora (2026-09-19, [`PLAN.md`](PLAN.md) hito 4).** Sea $S_\theta$ el modelo
chico con el LoRA de un subdominio, $T$ el modelo grande pelado y $T_\phi$ el modelo grande
con un LoRA entrenado sobre el *mismo corpus*. El par es especulativo sii

```math
\alpha_{T_\phi}(S_\theta) > \alpha_{T}(S_\theta),
```

pareado sobre casos — entrenar la mitad grande en el subdominio la hace coincidir con los
borradores correctos del experto chico más que el generalista. Se lee al lado de
$Q(T_\phi) \gt  Q(S_\theta)$ (hito 3): un verificador que no es mejor que su drafter no tiene
nada que verificar. **Todavía sin medir.**

### 7.2 La precondición, y P55 A como su instancia

$\alpha_T(E)$ es acuerdo con $T$. Si $T$ está equivocado en un caso, un experto que
está *bien* es **rechazado ahí**, y $\alpha$ premia al experto que comparte el error del
target. Así que la afirmación es sobre calidad sólo cuando

```math
Q(T) \;\ge\; \max_a Q(E_a)
```

— "es un puntaje de destilación sólo cuando el target es más fuerte que cada candidato"
(skill `alpha-surface`). La compuerta M-target de P55 es esa desigualdad como test
pareado, y disparó: en 351 casos humanos de triage el 32B acertó donde el experto falló
en **2** y falló donde el experto acertó en **87**, $p = 0,0$;
$Q(T)=0,746 \lt  Q(E) = 0,989$ **[ran]** P55 A. El modelo grande sin entrenar *consigue
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

### 7.4 La prueba, para un orden y para un par

**Como se escribió para la afirmación de orden (P55).** Para cada par $(E_a, E_b)$ que el
verificador resuelve (§9.2), tomar los casos en que ambos fueron puntuados y contar
$u = \lvert\lbrace c: \alpha(E_a,c) \gt  \alpha(E_b,c)\rbrace\rvert$, $d = \lvert\lbrace c: \alpha(E_a,c) \lt  \alpha(E_b,c)\rbrace\rvert$;
los empates se excluyen; decide el binomial exacto a dos colas sobre $(u,d)$.
**SUPPORTED** si todo par resuelto coincide; **FALSIFIED** si algún par queda ordenado al
revés con $p\le0.05$; **UNRESOLVED** si el verificador vio una diferencia y $\alpha$ no
**[ran]** `results/P55-graded-ranking-20260916/BRIEF.md`.

**Para un par (hito 4)** la misma cuenta se hace sobre *targets* en vez de expertos:
$u = \lvert\lbrace c: \alpha_{T_\phi}(S_\theta,c) \gt  \alpha_{T}(S_\theta,c)\rbrace\rvert$ y $d$ su espejo, mismo
binomial. El borrador es el mismo texto bajo ambos targets, así que la comparación es
pareada por construcción y cuesta un prefill extra por caso (§5.3).

---

## 8. Las tareas, como funciones

### 8.1 El triage, la cadena y la deriva con números

Un mensaje $m$ lleva hechos $\phi(m) = (\text{automated}, w, a, s, f)$ — *yo escribí en
el hilo*, *dirigido a mí*, *pide algo*, *remitente frecuente*. La etiqueta es

```math
y(m) = \neg\,\text{automated} \;\wedge\; \big[\,w + a + s + f \;\ge\; 2\,\big],
```

`training/email/inbox.py::important`. **El listado no muestra ninguno de $w, a, f$** —
viven detrás de tres herramientas (`thread_history` → $w$, `sender_stats` → $f$,
`message` → $a$ y el cuerpo para $s$), y `tests/test_email.py` afirma que la mejor regla
que sólo lee el listado da exactamente la clase mayoritaria en mensajes humanos
**[ran]**. Así que el trabajo del experto es una *cadena*: decidir qué herramientas,
llamarlas con el argumento correcto, leer los resultados, aplicar la regla.

El harness de modo corpus $\mathcal H$ es la recursión

```math
s_0 = \text{prompt},\qquad
\tilde s_{j} = E(s_{j-1}) \text{ hasta } \texttt{</tag>},\qquad
s_j = s_{j-1} \,\|\, \tilde s_j \,\|\, \texttt{= } \mathrm{tool}(\tilde s_j)\texttt{\textbackslash n},
```

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

### 8.5 El router: un clasificador sobre distribuciones de corpus, con abstención

Cada miembro liberado $m$ tiene un corpus $K_m$; sus turnos de usuario son muestras de la
distribución $P_m$ bajo la que el miembro fue entrenado. Un router es una función
$r(x) \in \lbrace m_1,\dots,m_M,\ \mathrm{out}\rbrace$ construida con un puntaje $s_m(x)$ por miembro y
un umbral:

```math
r(x) = \begin{cases} \arg\max_m s_m(x) & \text{si } \max_m s_m(x) \ge \tau \ \text{y el margen al segundo} \ge \delta,\\ \mathrm{out} & \text{si no.}\end{cases}
```

El diccionario de P62 es el caso particular $s_m(x) = \lvert\lbrace \text{claves de } m \text{ en } x\rbrace\rvert$,
$\tau = 1$, $\delta = 1$. En la suma de §8.4 el único término que un router puede cambiar es
el tercero — un pedido mandado a un miembro a cuyo corpus no pertenece cuenta como mal —
así que un router se puntúa por **mal-ruteados-a-local** y por la fracción que sale, no por
exactitud, y $\tau$ se fija sobre texto fuera de distribución antes de medir nada más: un
modelo al que se le pide elegir siempre elige. **[ran]** para el diccionario: P62, P64. El
$s_m$ aprendido es el hito 2 de [`PLAN.md`](PLAN.md): los dos brazos de pedido completo (n-gramas, embeddings) perdieron todo
pedido legítimo de un remitente no visto, y el brazo que pasó no puntúa el pedido entero — **[ran] ROUTE0**, un router
factorizado que parte un pedido en sus párrafos y lo manda a $m$ sólo si exactamente un párrafo no es contenido de $m$,
$\lvert\lbrace p \in x : p \notin C_m\rbrace\rvert = 1$, y ese párrafo es la tarea de $m$, $p \in T_m$. Sirve 0 de 600 textos
ajenos localmente donde el diccionario sirve 294 y pierde 0 de 480 pedidos legítimos; una paráfrasis de la tarea sale por
diseño (0 de 120 se mantienen locales, reportado, nunca con compuerta).

### 8.6 Una base de conocimiento, y una trayectoria por ella

La base de un subdominio es un conjunto de notas $\mathcal N = \mathcal N_{\text{enc}} \cup \mathcal N_{\text{op}}$
— enciclopédicas y operacionales — con links $\mathcal L \subseteq \mathcal N \times \mathcal N$
y un embedding $e:\text{texto}\to\mathbb R^d$. Una **trayectoria** sobre el caso $x$ es la
secuencia de notas que el experto abre, $\pi(x) = (n_1,\dots,n_T)$, cada una elegida a partir de
lo que expuso el último paso:

```math
n_{t+1} \in \underbrace{\mathrm{top\text{-}}k_{\,n \in \mathcal N}\ \langle e(q_t), e(n)\rangle}_{\text{una consulta que escribió el experto}} \ \cup\ \underbrace{\{n : (n_t, n) \in \mathcal L\}}_{\text{un link que ofreció la última nota}} .
```

Los parámetros del adaptador son la **política** — qué $q_t$ escribir, qué candidato abrir,
cuándo parar; la base es el **contenido**. Dos condiciones hacen que esa separación sea medible
y no sólo nominal. *Contenido inmemorizable:* lo que dice una nota se sortea por caso,
$n = n(x)$, así que $I(\text{respuesta}; \text{pesos} \mid \text{política}) = 0$ para la parte
consultada — el manual de P21, extendido a procedimientos. *Un canal necesario:* ningún valor
consultado aparece en el enunciado.

Con $\pi^{\star}(x)$ la trayectoria del oráculo y $Q_{\pi}(F)$ la calidad verificada sobre la
familia $F$ bajo la trayectoria $\pi$, el hito 7 lee tres diferencias, en este orden:

```math
\underbrace{Q_{\pi^{\star}}(F') - Q_{\varnothing}(F')}_{\text{lo que compra leer sobre una familia hermana } F'} \qquad
\underbrace{Q_{\pi^{\star}}(F') - Q_{\hat\pi}(F')}_{\text{lo que pierde la navegación}} \qquad
\underbrace{Q_{\hat\pi}^{\text{op}} \ \text{contra}\ Q_{\hat\pi}^{\text{enc}}}_{\text{qué tipo de conocimiento lo carga}}
```

cada una pareada (§9.2). $Q_{\varnothing}(F') \approx 1/20$ está medido **[ran]** P14; el resto
está **todavía sin medir** — hito 7 de [`PLAN.md`](PLAN.md). La navegación se puntúa donde
sucede — recuperada, abierta, seguida — no sólo en la respuesta: un lector que tuvo suerte sobre
una nota vacía es un caso que el score final no puede ver.

### 8.7 Abstención dentro de un miembro, al lado de la del router (M10)

El $r(x)$ del §8.5 abstiene *antes* de que un pedido llegue a un miembro. Un miembro
puede abstener una segunda vez, *dentro* de su propia región, una vez que su corpus le
enseña un veredicto `OUT OF SCOPE` — el análogo a nivel de generación de
$r(x) = \mathrm{afuera}$, puntuado igual: una tasa de **perdido** sobre lo que el
miembro ya contestaba, y una tasa de **atrapado** sobre lo que ahora rechaza
correctamente.

```math
\ell = \frac{|\{x \in D_{\text{previo}} : \text{contestaba antes, mal o mudo ahora}\}|}{|D_{\text{previo}}|}, \qquad
\text{atrapado} = \frac{|\{x \in D_{\text{fuera}} : \text{abstuvo}\}|}{|D_{\text{fuera}}|}.
```

**Medido [ran] `results/M10-distributor-abstain-20260928`.** `train_out` suma 70 turnos
`OUT OF SCOPE`, de la propia salida del rol, a los 700 turnos de M9 **byte a byte**.
Contra el miembro previo (`staff-s0`): **$\ell = 0$ de 70** — nada de lo que el miembro
ya hacía se pierde por enseñarle a rechazar — y **atrapado = 20/20** casos retenidos
fuera de alcance (`staff-s0` mismo: 0/20, porque nunca se le enseñó el veredicto); demo
6/6 contra el 5/6 de `staff-s0`. En vivo sobre la Air, la sexta escena (una nota de
agradecimiento a proveedores) es justo el caso que abstiene y se reenvía — 10.198 + 195
tokens a través de **Claude Haiku 4.5**, $0,0112 — el componente frontera de `CLAUDE.md`
alcanzado por la propia abstención de un miembro, no por la del router.

### 8.8 Editar la biblioteca después de entrenar (W7)

La condición de contenido inmemorizable del §8.6, $I(\text{respuesta}; \text{pesos}
\mid \text{política}) = 0$, hace una predicción: si la política de verdad no lleva
ningún hecho, parchear un enunciado de la biblioteca después de entrenar debería cambiar
toda respuesta que lo cite, sin nada en los pesos para disentir. Dos tasas leen los
recorridos contra el parche — **sigue**, sobre las respuestas del control que tocan el
enunciado parcheado, y **stale**, sobre el mismo conjunto, mutuamente excluyentes por
definición ($\text{sigue} + \text{stale} \le 1$, el resto siendo respuestas que no
llegan al enunciado):

```math
\text{sigue} = \frac{|\{x : \text{respuesta}(x) = \text{valor nuevo, citado a la línea parcheada}\}|}{|\{x : \text{el control contesta, toca el enunciado}\}|}, \qquad
\text{stale} = \frac{|\{x : \text{respuesta}(x) = \text{valor viejo}\}|}{|\{x : \text{el control contesta, toca el enunciado}\}|}.
```

**Medido [ran] `results/W7-edit-after-training-20260927`**, un enunciado parcheado
sobre los mundos y preguntas de entrenamiento propios de `distributor-wiki@v2`:
**sigue = 37/38**, citado a la línea parcheada; **stale = 0**. A libro cerrado — las
mismas preguntas sin la biblioteca abierta — los pesos igual escriben el valor viejo en
**1 de 40**: el miembro aprendió *la ruta al enunciado*, no el enunciado, y ese caso es
una ruta memorizada lo bastante bien como para contestar sin abrir la página, no la
biblioteca siendo pasada por alto. Es el mecanismo que [`MEMORY.md`](MEMORY.md) §7 lista
como "un valor … sin reentrenar", ahora medido y no sólo afirmado.

---

### 8.4 Exactitud entregada bajo una política de ruteo

Una política $r$ manda el caso $x$ a un miembro local $m$ o afuera a la frontera. Con
$L_m(x) \in \lbrace 0,1\rbrace$ si el miembro $m$ contesta bien $x$, $F(x)$ si la frontera lo
hace, y $m^\ast (x)$ el miembro de la región de $x$,

```math
\mathrm{entregado}(r) = \frac{1}{n}\sum_x \Big( [r(x) = (\mathrm{local}, m^*(x))]\,L_{m^*}(x) + [r(x) = \mathrm{afuera}]\,F(x) + [r(x) = (\mathrm{local}, m \ne m^*(x))]\cdot 0 \Big)
```

Un caso entregado al miembro equivocado cuenta como mal por construcción — la lectura
conservadora. La política por región (P41) es $r(x) = \mathrm{región}(x)$ leída de una
etiqueta; el ruteo por request reemplaza la etiqueta por un clasificador y sólo puede
perder por sus mal ruteados, así que las dos se comparan sobre los mismos casos y la
compuerta es un empate con cero mal ruteados. **[ran]** P62: por región 0,775, por
request 0,775, mal ruteados 0 (§11).

### 8.9 Exactitud en turnos dependientes multi-turno, y la condición de contexto plano (MT0, H1)

Una conversación es una secuencia de turnos $x_1,\dots,x_n$; el turno $i$ es **dependiente** cuando el
argumento de la llamada correcta es un valor que el usuario nombró, o que devolvió una herramienta, en
un turno anterior $j\lt i$ y $x_i$ mismo no lo contiene. Para un conjunto $D$ de turnos dependientes y
un brazo $a$ (lo que el gateway le muestra al modelo en un turno),

```math
A_{\text{dep}}(a) = \frac{1}{|D|}\sum_{x\in D} \mathbf 1[\,\text{respuesta}_a(x)\text{ correcta}\,].
```

**Medido [ran] `results/MT0-multiturn-baseline-20260929`**, $|D| = 54$: leyendo sólo el último pedido,
$A_{\text{dep}}(\text{last}) = 4/54$ — sin la conversación el referente no existe, y los 4 son azar sobre
una elección de tres ítems. Cargando cada turno anterior en el prompt, $A_{\text{dep}}(\text{history}) =
43/54$ (79,6%): resuelve una referencia que sólo tiene que **copiar** en un argumento (32/34) pero no una
que tiene que **escribir en texto libre** — un reclamo sobre "ese pedido" se presenta sin número de
pedido, 8 de 10 veces. Esa división — copiado en una llamada contra compuesto en prosa — es exactamente
lo que apunta el `get`/`put` del harness de flujo: el valor se busca por clave hacia la llamada, no se
deja a la lectura que el modelo haga del historial.

**Longitud del prompt por posición de turno, y por qué un brazo es plano por construcción.** Sea
$\bar p_i^a$ la longitud media del prompt renderizado en el turno $i$, sobre las sesiones que llegan a
él. Bajo `history`, el prompt del turno $i$ lleva el pedido y la respuesta de cada turno anterior, así
que

```math
\bar p_i^{\text{history}} \;\approx\; \bar p_1 + \sum_{j=1}^{i-1} \ell_j = O(i),
```

con $\ell_j$ la longitud renderizada del turno $j$ — creciendo de verdad con la cantidad de turnos,
cualquiera sea su contenido. El harness de flujo en cambio renderiza una sola línea, `state:
<workflow>/<state> · keys: <names>`, cuya longitud está acotada por la cantidad de claves y el nombre
del estado — propiedades del flujo **del dominio**, fijadas una vez escrito el TOML, no de **cuántos
turnos** lleva la conversación:

```math
\bar p_i^{\text{harness}} \;\approx\; \bar p_1 + O(1) \quad\text{en } i,
```

el mismo orden que `last` (el brazo de arriba que falla en exactitud), pero sin perder el referente,
porque el valor mismo vive en la caché de la memoria operativa y se busca por clave en vez de llevarse
en el prompt. **La condición de planitud de H1** vuelve operativo el contraste: con $\bar p_1,\bar
p_2,\bar p_3$ los tokens medios de prompt en las primeras tres posiciones de turno,

```math
\bar p_3 \;\le\; 1,1\ \bar p_1
```

es la vara que un brazo de harness tiene que cruzar — a lo sumo 10 % de crecimiento para el tercer
turno, distinguiendo un comportamiento $O(1)$ genuino (un cambio chico por la longitud del nombre del
estado) de una implementación que en secreto reinyecta contenido creciente. **Medido [ran] MT0**, los dos
brazos contra los que se fija esta vara: $\bar p_1,\bar p_2,\bar p_3 = 345, 376, 303$ para `last` y $345,
428, 394$ para `history` — el crecimiento que `history` muestra aun en una suite de dos a tres turnos
(+24 % en el turno 2, $\bar p_2/\bar p_1 = 1,24$) es exactamente el término que el argumento de batching
del §2.4 no toca: un prompt más largo es un prefill más largo (§2.1) en cada turno, para cada sesión,
esté o no la GPU ociosa por lo demás.

**Medido [ran] H1** (`results/H1-workflow-harness-20260929`): un miembro (`wf-s0`) entrenado para leer la
línea de contexto del harness en vez de la creciente de `history`, sobre las mismas 60 sesiones de MT0.
$A_{\text{dep}}(\text{harness}) = 53/54$ contra $A_{\text{dep}}(\text{history}) = 43/54$ — un turno perdido,
once ganados, un conteo de pares discordantes de $11 : 1$ a favor de `harness` ($n_d = 12$, $p \approx
0,006$ por el sign test exacto del §9.2) — y los 53 turnos dependientes bien contestados buscaron su valor
en el almacén por clave, ninguno leyéndolo de la transcripción. La vara de planitud se cumple por
construcción: $\bar p_1,\bar p_2,\bar p_3 = 745, 726, 710$, así que $\bar p_3/\bar p_1 = 0,953 \le 1,1$,
plano y no sólo acotado — la longitud de la línea de contexto sigue el estado propio del workflow y los
nombres de las claves, no la cantidad de turnos. Estos valores de $\bar p$ son **más altos que los de
cualquiera de los dos brazos de MT0** (745 contra los 345 de `history` en el turno 1) porque el harness
gasta más **pasos de generación** por turno — un `<get>` y su resultado, la llamada a la herramienta, un
`<put>` y su confirmación, y recién la respuesta — donde `last`/`history` escriben la respuesta directo;
el costo del prefill del §2.1 se paga una vez por paso, así que más pasos con un piso por turno plano es
un costo real que esta medición asienta en vez de esconder. Lo que no asienta: cuánto de ese andamiaje
get/call/put repetido absorbería un caché de prefijo (§3.6) entre turnos — no medido acá, y la razón por
la que el argumento de *tokens* del harness es para sesiones más largas que los dos o tres turnos de MT0,
aunque su argumento de *exactitud* ya se sostenga a esa longitud. Un cuarto brazo, `harness-noblock` (el
mismo corpus, el bloque de herramientas retirado al servir aunque siempre presente al entrenar), puntúa
$A_{\text{dep}} = 0/60$: un prompt desconocido, no uno más difícil (§8.1, §8.6). **La regla de corte de la
propia corrida — exactitud de primeros turnos $\ge 0,90$ en *todos* los brazos o la corrida es VOID — se
escribió para cuidar toda la comparación y en cambio dejó que la falla de un brazo anulara el resultado
real de los otros dos; leída por brazo y no tal como fue escrita, `harness` pasa las varas de esta sección
y `harness-noblock` no.** La decisión del usuario (2026-09-29): vale la lectura por brazo para la compuerta
de liberación — `harness` PASÓ, `harness-noblock` quedó FALSEADO — y el VOID tal como está escrito queda
como el registro de ese error del instrumento.

**Medido [ran] H2** (`results/H2-tracker-harness-20260929`), el mismo arnés sobre un segundo dominio
construido para eso (un tracker de equipo tipo Jira + Confluence), 60 sesiones largas retenidas,
$|D| = 160$ turnos dependientes, 60 primeros turnos, 60 turnos independientes. Acá las sesiones corren
cinco turnos en vez de dos o tres, así que la condición de planitud se enuncia sobre cinco: con
$\bar p_1,\dots,\bar p_5$ el promedio de tokens de prompt en las primeras cinco posiciones de turno,

```math
\bar p_5 \;\le\; 1.1\ \bar p_1
```

es la barra contra la que se lee esta corrida. $A_{\text{dep}}(\text{harness}) = 146/160$ (91,3%), contra
un umbral del 90%, con $\bar p_1,\dots,\bar p_5 = 1613, 1223, 1011, 1149, 1274$ — $\bar p_5/\bar p_1 =
0,790 \le 1,1$, plano (de hecho cayendo, a medida que el andamiaje get/put se amortiza una vez que el
propio estado del flujo de trabajo se asienta). La línea de base sin entrenar `base-history` (Gemma 4 E4B
puro, la conversación en el prompt) puntúa $A_{\text{dep}} = 4/160$ y sus propios primeros turnos, 44/60,
caen bajo el umbral del 90%; aplicar la regla de VOID por brazo que estableció H1 vuelve ilegible la
comparación pre-registrada "`harness` le gana a `base-history`", así que **H2 se lee FALSEADA tal como
está escrita, no ANULADA** — anular a una línea de base sin entrenar cuyo bajo puntaje en primeros turnos
*es* el margen que se está midiendo es un error de instrumento más angosto que el de H1, registrado en vez
de parchado. Descriptivamente, sobre los mismos 160 turnos dependientes: **142 : 0** a favor de `harness`,
$p\lt 10^{-40}$ por la prueba de signo exacta del §9.2 — enunciado porque no cuesta nada enunciarlo, no
ofrecido como sustituto del veredicto pre-registrado que su brazo anulado vuelve ilegible. **La decisión
del usuario (2026-09-29), como para H1: lectura 1** — las condiciones legibles de arriba son el veredicto
de H2, `harness` **PASÓ**; FALSEADO-tal-como-está-escrito queda en el registro con sus dos errores de
instrumento (el VOID por brazo de arriba y el chequeo de anchor de abajo). No se repitió: ningún cambio de
regla podía mover un base en $4/160$. `harness-noblock` ($80/160$) se leyó primero como "aprendido en
parte"; esa lectura era un error del corpus, no un aprendizaje parcial — su tercio sin bloque compartía el
módulo (`% 3`) con el que rotan los roles, así que las 400 filas de entrenamiento sin bloque eran de QA, y
el miembro aprendió lo-sin-bloque exactamente en el rol que se le mostró (QA 80/80; lead/developer 0/20,
la única excepción de lead `sprint_board`, una llamada sin argumento). En `harness`, las 14 fallas dependientes son todas un mismo turno, el comentario final de QA (6/20): el miembro relee el issue o intenta una transición rechazada en vez de comentar — una falla real, sobre un solo fraseo de la evaluación ("Note on it: …" 1/15 contra "Put a comment on it: …" 5/5); aparte, 10 de los 60 turnos independientes (50/60) son el chequeo del ancla — "¿dónde tienen que pasar los tests?" lee la página entera `definition-of-done` en vez de `#tests`, y el enunciado está en lo que leyó (mide fraseo, registrado, no aflojado). **H3 tiene un resultado [ran]:**
`tr-s1`, entrenado sobre un corpus que arregla las dos correcciones (fraseo ampliado en dos versiones por
turno en cada rol, un tercio sin bloque de cada rol), contra `tr-s0` sobre una suite fresca retenida. El
margen se sostiene primero — `s0-harness` 147/160 (91,9%), bajo el techo del 95%, así que la suite fresca
no es más fácil que la de H2. **H3a PASÓ:** `s1-harness` 158/160 (98,8%) contra `s0-harness` sobre los
mismos turnos, 11 pares discordantes todos a favor de un lado, 0 perdidos. Para $n=11$ la prueba de signo
exacta de dos colas es $p = 2\cdot 2^{-11} \approx 0,00098$ — la prueba del §9.2, aplicada acá — y la
corrida es plana, $\bar p_5 = 1275 \le 1,1\cdot\bar p_1 = 1,1\cdot 1465$. **H3b PASÓ:** `s1-noblock`
156/160 (97,5%), perdiendo sólo 4 de los turnos dependientes que `s1-harness` acierta — bajo la barra de
8 — cada rol por encima — developer 76/80, lead 40/40, QA 40/40 — a más o menos un tercio de los tokens
de prompt por turno (p̄ ≈ 285–503 contra 958–1465); lo-sin-bloque de H2, todas filas de QA, había sido
80/160. Leído donde ocurre: las 2 fallas de `tr-s1` son un solo caso, el texto de la propia nota leído
como una orden (`issue_transition → qa`, rechazada por la capa de herramientas); las 4 fallas de
`s1-noblock` son una sola sesión cuyo primer turno llama a la herramienta equivocada, no pone nada, y los
cuatro turnos dependientes siguientes encuentran una memoria vacía — un error del primer turno en cascada
por la sesión
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).

### 8.10 La línea de biblioteca real: entrada, pérdida y cita (REAL0–REAL7)

REAL0 **[ran]** encontró la falla que "el contenido se extrae por caso" de §8.6 no descarta por sí
sola: un miembro de trayectoria entrenado sobre una biblioteca *generada* nunca entra a una real — en
40 de 40 caminatas su primer acto es una búsqueda del estante del harness con una consulta de su
propio mundo de entrenamiento, y no abre ni una página en ninguna. Arreglarlo toca tres lugares: cómo
una pregunta encuentra una página, sobre qué se toma la pérdida de entrenamiento, y qué acepta el
calificador como cita.

**Entrada — BM25 de texto completo sobre las sentencias de una nota.** `memory.runtime.FullText`
reemplaza la coincidencia léxica de la pregunta contra el título de una nota por Okapi BM25 sobre el
cuerpo de la nota (sus sentencias), más un bono plano por cada palabra que la pregunta comparte con el
`when`/`what` de la nota:

```math
\mathrm{score}(n\mid q)=\sum_{w\in q} \mathrm{idf}(w)\,\frac{f_{w,n}(k_1+1)}{f_{w,n}+k_1\,(1-b+b\,|n|/\overline{|n|})}
  + 2\,\bigl|q\cap(\mathrm{when}\cup\mathrm{what})\bigr|,\qquad \mathrm{idf}(w)=\ln\!\Bigl(1+\frac{N-\mathrm{df}_w+0.5}{\mathrm{df}_w+0.5}\Bigr)
```

con $k_1=1,2$, $b=0,75$ — los valores estándar, nunca ajustados sobre un conjunto de preguntas; los
empates se rompen por el id de la nota. **Por qué (REAL0 [ran]):** el `when`/`what` de un reglamento
ingerido es el título de su sección, y la pregunta de una persona comparte pocas palabras con él — una
coincidencia léxica sólo por título encontró la página de inicio de una caminata en 5 de 36
preguntas, la página de soporte en 10; BM25 sobre las sentencias encuentra la página de inicio 34/36 y
el soporte 32/36 (REAL1–2 **[ran]**, $k=3$). Bajo esta entrada más páginas abiertas con sus
sentencias (`page_text`), el puntaje del titular de la base sin entrenar sobre el conjunto de REAL0
sube 1 → 4 → 7 de 25 a través de REAL0–REAL2; el miembro del mundo generado se queda en 0 → 1 → 5 — la
entrada repara llegar a la página, nunca la cita sobre ella.

**La pérdida — sólo los tramos propios del modelo.** El objetivo de §4.4 suma la entropía cruzada
sobre "el tramo del asistente", que para un turno de chat corto es la respuesta entera. Una caminata de
trayectoria sobre una página real leída entera es sobre todo *esa página*: REAL3 **[ran]** encontró
que `training/s4_train.py` sumaba la pérdida sobre todo el texto renderizado — sistema, pregunta y
cada resultado de herramienta — así que en un corpus donde los resultados son largos el adaptador
aprende a escribir el resultado, no a responder desde él (`real-walks-s0` escribió párrafos de
reglamento después de una página, 1/23). La corrección restringe la suma a $S$, los tramos que el
propio modelo escribe — sus etiquetas y su respuesta citada, nunca un resultado de herramienta, una
pregunta o el texto del sistema — una restricción estricta de la $\mathcal L(A,B)$ de §4.4:

```math
\mathcal{L} = \sum_{t \in S} -\log p_{\theta+\Delta}(x_t \mid x_{<t}), \qquad S = \{\,t : x_t \in \text{los tramos propios del modelo}\,\}
```

**Medido [ran] REAL3:** de 552.495 tokens en el corpus de caminatas, 18.241 (3,3 %) son del modelo —
entrenar sólo sobre ellos convierte 1/23 en 18/23 (§11 más abajo). **Esta no es la receta por
defecto para todo miembro:** H5 **[ran]** encontró que le cuesta a un miembro de resultados cortos una
familia de frases completa (§11) — la pérdida con máscara de tramos es la receta sólo donde los
resultados de herramienta son largos (páginas reales: REAL3); donde son líneas cortas (el rastreador
de equipo), se queda la pérdida de texto completo de §4.4.

**La cita — la sentencia de soporte misma, no cualquier sentencia que tenga el valor.** Un valor se
repite a través de una biblioteca real ("12" ocurre en 12 sentencias sólo en la biblioteca de REAL0),
así que una caminata puede tener el valor correcto y citar el párrafo equivocado. La regla estricta
del calificador, opcional por fila (`check.cite = "support"`, `grade.py`), exige que la nota citada
sea exactamente la sentencia que el plan de la pregunta nombra como soporte:

```math
\mathrm{cite\_ok}(x) = \mathbf{1}\big[\,\mathrm{cited}(x) = \mathrm{support}(x)\,\big], \qquad \text{más estricto que } \mathbf{1}\big[\,\mathrm{value}(x) \in \mathrm{statement}(\mathrm{cited}(x))\,\big]
```

**Medido [ran] REAL5:** sobre una tercera familia densa en enlaces, el valor es correcto 20/25 pero la
cita estricta sólo 15/25 — 3 de las 5 pérdidas citan otra sentencia que tiene el mismo número repetido
(§11). REAL6 **[ran]** entrenó elecciones de valor repetido de un salto y lo dejó sin cambios (15/25,
empate): las fallas restantes son filas de varios saltos citadas en el extremo equivocado de un
enlace, una forma que ese corpus nunca contuvo. REAL7 **[ran]** entrenó exactamente esa forma — un
señuelo con el mismo número al inicio de un enlace, la respuesta en su extremo — y tampoco cambió
nada: sobre el titular sin gemelos de REAL5, `real-link-s0` empata con `real-none-s0` 13/21 (4:4
pareado, $p=1,0$), bajo la barra de ≥ 15/21, aunque el valor es correcto más seguido (22 contra 20) —
**FALSEADO**. Dos cambios de corpus apuntados a esta citación (REAL6, REAL7) ya no cambiaron nada; por
la regla de contar rediseños esta línea de corpus sobre la citación se detiene acá. Lo que necesitaría
un tercer intento no es un corpus sino un mecanismo — un chequeo del runtime que rechace una cita cuya
página el recorrido no terminó — medido sobre un conjunto fresco.

**Tests de signos pareados sobre esta línea (el test de §9.2, aplicado aquí):**

| corrida | par | discordantes | $p$ |
|---|---|---|---|
| REAL3 (semilla 0, titular fresco) | `real-spans-s0` vs `base-walks+page` | 10 : 1 | 0,0117 |
| REAL3 (semilla 1, titular fresco) | `real-spans-s1` vs `base-walks+page` | 9 : 1 | 0,0215 |
| REAL5 (titular, tercera familia) | `real-none-s0` vs `base-walks+page` | 13 : 0 | 0,00024 |
| H5 (turnos dependientes, bloque de herramienta mostrado) | `tr-s3` (máscara de tramos) vs `tr-s1` (texto completo) | 0 : 20 | regresión |

Las primeras tres dicen que la pérdida con máscara de tramos transfiere navegación y cita a través de
familias de documentos que nunca vio. La última dice que no es un sustituto gratuito de la pérdida de
texto completo donde los resultados son cortos — un miembro entrenado en la forma en que se sirve
(§4.4) todavía necesita la pérdida sobre los tokens que esa forma en verdad le exige producir.

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

```math
p = \min\Big(1,\; 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u, n_d-u)\big]\Big),
```

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

## 10. La familia Qwen 3: chico y grande de un mismo espacio de ids

### 10.1 Las dos mitades llevan un LoRA

La decodificación especulativa tiene dos modelos y dos trabajos. El **drafter** es el pool
— multi-LoRA es requisito *suyo*. El **target** verifica en una pasada (§6.1 paso 2).

~~El target es un modelo denso, sin modificar, y no necesita LoRA.~~ **Reformulado el
2026-09-19.** Un modelo grande sin modificar sacó *menos* que el experto chico en las dos
regiones probadas — $Q(T) \lt  \max Q(E)$, 0,746 < 0,989 y 0,967 < 1,000 **[ran]** P55, P55b
(§7.2) — así que el target de un par es $T_\phi$: el modelo grande con un LoRA del mismo
subdominio. Eso vuelve servir un LoRA un requisito de **las dos** mitades, y las dos están
medidas: sobre un modelo grande en 4 bits el adaptador se aplica, $|\Delta\ell|$ medio
0,22–0,49 nats contra un base-vs-base de 0,000 **[ran]** P60 §3b (§4.3); sobre el modelo
chico 3.x se aplica una vez que sus tensores llevan los nombres de la clase que vLLM sirve
**[ran]** D2 (§10.4).

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

Lo que se sabía el 2026-09-17: el adaptador es real (G1: `lora_B` se movió, la salida
cambió en proceso), el motor dice que lo cargó, el texto servido es igual al de la base.

**El mecanismo, leído y después corrido — D2 [ran] 2026-09-19.** Con $K$ los nombres de
tensores del adaptador, $m$ el mapper de nombres de vLLM para la clase servida y $M$ los
módulos del modelo servido,

```math
\text{applied}(K) = \{\,k \in K : m(k) \in M\,\}.
```

Entrenado por `AutoModelForCausalLM`, PEFT nombra los tensores `model.layers.N…`; vLLM sirve
`Qwen3_5ForConditionalGeneration` y activa por `language_model.model.layers.N…`. La carga
valida sólo el último componente de cada nombre y loguea *Loaded*; la activación busca el
nombre completo y resetea el slot. Tal como se entrenó $|\text{applied}(K)| = 0$ de 496 y
la activación real fija 0 de 178 módulos; renombrado por `training/harness/rekey.py`, 496
de 496 y 152 de 178, y la compuerta de identidad pasa de `not applied` a `applied`. Los 26
módulos que quedan vacíos son `lm_head`, `embed_tokens` y 24 `conv1d`, ninguno apuntado;
las proyecciones de atención lineal están entre los 152.

### 10.5 La ruta, como mecanismos

| # | mecanismo | estado |
|---|---|---|
| D0 | un modelo chico 3.x que comparte espacio de ids con 3.8-27B | **[ran]** ✓ |
| D1 | C18 bajo un vLLM más nuevo | void — el chain instala el último y es **0.29.0**, la versión de P33 **[ran]** |
| D2 | el mecanismo de C18: mapeo clave PEFT ↔ módulo vLLM, con el log | **[ran]** ✓ 2026-09-19 — un desajuste de nombres (§10.4) |
| D3 | pensamiento apagado, verificado por conteo | dentro de los hitos 3–4 |
| ~~D4~~ | ~~el instrumento de ranking apuntado a 3.5-4B → 3.8-27B~~ | retirado junto con la afirmación de ranking; lo reemplazan los hitos 1, 3 y 4 de [`PLAN.md`](PLAN.md) |

**Por qué el orden.** Todo en §6–§7 es agnóstico al target dado §3.2. El hito 1 mueve los
miembros liberados al modelo chico 3.x con sus releases de Qwen 2.5 como control; el hito 3
entrena la mitad grande; el hito 4 mide la desigualdad de §7.1.

---

## 11. Mapa: sección → corrida

**Las corridas nombradas acá que no tienen directorio en `main` viven en el tag `v0.1-foundations`.**

| sección | fórmula / afirmación | corrida que la instancia |
|---|---|---|
| §1.3 | ancho de embedding > vocabulario | `STACK.md` §1 (el tag `v0.1-foundations`), P48 |
| §1.4–1.5 | dimensiones, `layer_types` híbridos | `config.json` **[read]** 2026-09-17; log de P33 |
| §2.4 | batching: 475 cadenas, 31 s / 230 s | P55 A `session_a.json` |
| §3.3 | tabla de mapas de ids | P48; P55 `D0-tokenizers.txt` |
| §4.2 | 29.933.568 parámetros ↔ 119.801.528 bytes | `STACK.md` §3 (el tag `v0.1-foundations`) |
| §4.4, §8.1 | deriva: 0,741 → 0,989 | P43 `arm_email_475.json`; P55 A |
| §4.4, §9.2 | **un release reproduce**: re-servido 0 : 0 contra su registro; reentrenado 1 : 0 — varianza de entrenamiento un caso en 475 | P57 `release.json`, `releases/email-full@v1.json` |
| §5.2 | compuerta de identidad C18 | P33 `lora_matrix.json`; P55 A `applied`; **Fase 0 P56: los dos miembros 3/3 `applied`, herramientas alcanzables, stop honrado** |
| §5.3 | forma de `prompt_logprobs` | P55 A `preflight_target` |
| §5.4 | preflight del stop; shim posicional | P55 A intentos 1, 2 |
| §7.2 | $Q(T) \lt  \max Q(E)$: 2 : 87, $p=0$ | P55 A `target_gate` |
| §8.2 | techo 0,989; gradiente de commitment | P55 A; P51 `desk_profile.json` |
| §8.3 | el grado más chico no está saturado: $Q(g25) = 0,000$, base 0,171 — fabrica la respuesta de la herramienta | P58 `g25.json` |
| §8.3 | **sin grado intermedio**: `g75` ≡ `g600` = 1,000 en un protocolo de una llamada; M1 pasa por un bit | P55b `p55b.json` |
| §8.2 | **una banda más profunda existe por construcción**: `commitment_deep`, la última de 1–3 promesas entre las propuestas del remitente, último mensaje del remitente desde profundidad 2; la suite superficial pinada por hash después de que #206 la moviera en silencio (0 desajustes vs P55b) | P60 §3a, `tests/test_desk_deep.py` |
| §7.2 | **$Q(T) \lt  \max Q(E)$ por segunda vez**: 32B 0,967 (fechas normalizadas) contra `g600` 1,000, 0 : 8, $p = 0,008$ | P55b `target_gate` |
| §9.3 | potencia a $n=351$ | `bar.resolvable` **[ran]** 2026-09-16 |
| §10.2 | espacio de ids 3.5 → 3.8 | P55 `D0-tokenizers.txt` |
| §10.5 D1 | vLLM resuelve a 0.29.0 | log de boot de P55 A |
| §4.4 | **una superficie desconocida es extrapolación**: sin podar (54 herramientas) el experto copia etiquetas del bloque, 225 de 227 llamadas rechazadas; podado, 8 de 1160; el bloque son ~7.956 contra ~77 tokens — y servido después del pedido, como se entrenó, cuesta TTFT 0,10 → 1,70 s con la caché de prefijos encendida | P59 `attribution.json`; E5 `e5.json` |
| §6.4 | **α, $\mathbb{E}[\tau]$, aceleración** | α por token (aceptación rank-1) **[ran]** B4: 0,871 el 12B pelado, 0,898 el 12B + LoRA sobre 107 registros de borradores del E4B; $\mathbb{E}[\tau]$ con $k=4$ bajo la independencia de §6.4, 3,87 → 4,08 — derivado, no medido; **reloj [ran] F0** (12B FP8 + LoRA, el drafter MTP nativo, k = 4): el base 2,73× a batch 1 con largo medio aceptado 4,16, el experto LoRA 1,74× en su dominio (4,16 → 2,25) — el LoRA le cuesta al drafter, medido; **identidad de la salida a temperatura 0, establecida [ran] F0c** (bf16, un A100, `VLLM_BATCH_INVARIANT=1`): el control (plano contra plano) es idéntico en los cuatro conjuntos, 16/16, 8/8, 16/16, 8/8 — el motor es determinista acá; MTP contra plano en el dominio propio del LoRA es idéntico hasta cada corte servido (14/16, las 2 divergencias caen después de una etiqueta de cierre que una caminata servida nunca lee de más), 1,98×, y en LoRA/general 8/8; base/general cambia 5/8 por sinónimos en casi-empates, un artefacto de la forma de verificación, no una falla de la regla de aceptación |
| §7.4 | **el veredicto de orden** | **cerrado sin veredicto el 2026-09-19**: el §7.2 falla para un target *sin entrenar* en dos regiones fáciles (P55 A, P55b). Lo que sobrevivió es el target entrenado — ahora la mitad grande de un par (§7.1, §10.1) |
| §10.5 D2 / §3.4 | **un LoRA aplica sobre el 32B AWQ**: media de $\vert \Delta\ell\vert$ 0,22–0,49 nats contra base-vs-base 0,000, 3/3; compuerta de texto 2/3 | P60 §3b `awq_gate.json` |
| §10.5 D2 | **C18 es un desajuste de nombres**: $\text{applied}(K)=\lbrace k\in K: m(k)\in M\rbrace$ — tal como se entrenó 0 de 496 tensores caen sobre el stack de texto servido y la activación real fija 0 de 178 módulos (`not applied`); renombrado, 496 de 496 y 152 de 178 (`applied`); control `applied` | D2 `lora_matrix.json`, `vllm.log` |
| §7.1, §7.4 | **la desigualdad del par** $\alpha_{T_\phi}(S_\theta) \gt  \alpha_T(S_\theta)$ | **se cumple [ran] B4**: 76 : 18 registros, $p \lt  10^{-4}$ — en la distribución del propio corpus (0,855 → 0,914), no en una banda que ninguna mitad entrenó (0,885 → 0,881); hito 4 de [`PLAN.md`](PLAN.md) |
| §8.5 | **el router como clasificador con abstención**; el diccionario es su caso particular | diccionario: P62, P64. **Un modelo de n-gramas del marco de cada corpus [ran] M2**: texto ajeno 0/128 servido localmente contra 59/128 del diccionario; pedidos legítimos de remitentes nunca vistos 120/120 perdidos contra 0/120 — no pasa; el brazo de embeddings **[ran] M2b**: texto ajeno 15/338 servido localmente contra 119 del diccionario, 120/120 pedidos de remitentes no vistos perdidos — no pasa; un tercer codificador **[ran] M2c**: no seguro (62 de 142 casos fuera de región servidos localmente); **el router factorizado [ran] ROUTE0 pasa: 0/600 textos ajenos servidos localmente contra 294, 0/480 pedidos legítimos perdidos** |
| §8.6 | **una trayectoria por la base de conocimiento de un subdominio**; la política en los pesos, el contenido afuera | $Q_\varnothing(F') \approx 1/20$: P14. Recorridos de dos y tres saltos sobre páginas de enunciados atómicos, citados y verificados: 0/40 sin entrenar → 35/40, 38/40 sobre Gemma **[ran]** W9, B1; una habilidad que el corpus nunca mostró no se aprende (comparaciones 10/40), mostrada sí (37/40) **[ran]** B3, B5; en la biblioteca de enfermería la afirmación central no pasa **[ran]** W5, W5c |
| §7.3, §8.2 | **pesos o harness — pesos**: base 0,345, base + procedimiento de 914 tokens 0,601 (las dos con 0 llamadas, debajo de la barra de mayoría 0,655), experto 0,989; experto contra base+kb **137 : 1**; el test de signos solo leyó el default dado vuelta como pagando (164 : 74) — la barra de mayoría lo guarda | P61 `session.json` |
| §8.4 | **el ruteo por request empata al por región**: 0,775 = 0,775, 0 mal ruteados, 37,5 % afuera sobre los 240 casos de P41 | P62 `replay.json` (cero GPU) |
| §4.4, §8.1 | **el turno en vivo es modo corpus o no es nada**: bajo el prompt del runtime 2/32 turnos humanos llaman una herramienta (0,281); bajo el prompt liberado del miembro con cortes en `</tag>`, tope de idas y vueltas y 256 tokens/paso, 19/32 llaman y 0,688 contra barra 0,655 ($p=0,43$), 40/40 local | P63 `live.json`, intentos 4 y 7 |
| §9.2, §8.4 | **un segundo miembro por la puerta de la Fase 1**: `desk-commitment` empata su corrida grabada 240/240 (0 discordantes, $p=1$) y le gana a la base 202 : 0 ($p = 2\cdot2^{-202}$); co-residente con `email-full`, `auto` rutea a cada uno por su pregunta | P64 `pool_second.json` |
| §2.5 | **la KV bajo una profundidad no tocada es bit-idéntica**: LoRA en las capas 21–41 de 42 solamente, 70/70 retenidos = el miembro completo (0 perdidos), control base-contra-base sobre las capas 0–20 idéntico bit a bit; salvedad: 24 de 42 capas comparten KV, así que 21–23 igual recomputan | E6 `results/E6-upper-layers-20260927/BRIEF.md` |
| §5.5 | **la caché de prefijos se indexa por posición, no por contenido**: TTFT 0,10 → 1,70 s (16,8×), throughput b8 132 → 108 tok/s, exactitud 70/70 → 39/70; 0,09–0,11 s donde volvió todo el prefijo; dos LoRAs en un mismo batch conservan 0,88× | E5 `results/E5-engine-baseline-20260928/BRIEF.md` |
| §6.7 | **aceleración del MTP bajo un LoRA de dominio**: sin adaptador 2,80×/2,60× (dominio/general), con LoRA 1,92× ($\alpha$ 0,34) / 2,40× | C0 `results/C0-aligned-draft-20260927/BRIEF.md` |
| §6.7 | **restringir capas no ayuda al drafter**: $\rho = -0,02$ (el propio MTP del E4B, base 0,82, completo 0,44, superior 0,43) — NONE | C0-upper `results/C0-upper-e4b-20260927/BRIEF.md` |
| §6.7 | **sobre llama.cpp/Metal el drafter no es barato**: el MTP de Gemma *enlentece* al 12B, 0,52× con el LoRA en su dominio, 0,66–0,87× en el resto — se movió la $c$ del §6.4, no la $\alpha$ | MAC2 `results/MAC2-llamacpp-20260927/BRIEF.md` |
| §8.7 | **abstención dentro de un miembro**: $\ell = 0$ de 70, atrapado 20/20 contra el 0/20 de `staff-s0`, demo 6/6; en vivo, el turno abstenido llega a Claude Haiku 4.5, $0,0112 | M10 `results/M10-distributor-abstain-20260928/BRIEF.md` |
| §8.8 | **editar la biblioteca después de entrenar**: sigue 37/38, stale 0, a libro cerrado 1/40 | W7 `results/W7-edit-after-training-20260927/BRIEF.md` |
| §8.9 | **exactitud en turnos dependientes sin y con historial**: $A_{\text{dep}}$(last) 4/54, $A_{\text{dep}}$(history) 43/54; tokens de prompt $\bar p_1,\bar p_2,\bar p_3$ = 345/376/303 (last), 345/428/394 (history) | MT0 `results/MT0-multiturn-baseline-20260929/BRIEF.md` |
| §5.6 | **cociente de throughput con varios adaptadores**: $r_4(16) = 278,6/269,7 = 1,03$, NO MATERIAL CONTENTION; casi lineal 22,7 → 135,1 → 278,6 → 504,3 tok/s para K = 1, 8, 16, 32; TTFT p95 0,24 s en K = 32, 0 errores de 128 | C1 `results/C1-concurrency-20260929/BRIEF.md` |
| §8.9 | **el harness de flujo contra el brazo con historial de MT0 y la vara de planitud $\bar p_3 \le 1,1\ \bar p_1$**: $A_{\text{dep}}$(harness) 53/54 contra 43/54, 11 : 1 emparejado ($p\approx0,006$); $\bar p_1,\bar p_2,\bar p_3$ = 745/726/710, plano; `harness-noblock` 0/60. Tal como fue escrita VOID (la regla de primeros turnos anula entre brazos); leída por brazo, `harness` PASÓ y `harness-noblock` quedó FALSADO — la decisión del usuario (2026-09-29): vale la lectura por brazo, el VOID tal como está escrito queda como el registro de ese error del instrumento | H1 `results/H1-workflow-harness-20260929/BRIEF.md` |
| §8.9 | **el mismo harness sobre un dominio de tracker de cinco turnos, la vara de planitud $\bar p_5 \le 1,1\ \bar p_1$**: $A_{\text{dep}}$(harness) 146/160 (91,3%) contra un umbral del 90%; $\bar p_1,\dots,\bar p_5$ = 1613/1223/1011/1149/1274, plano; `base-history` 4/160, sus propios primeros turnos 44/60 lo anulan bajo la regla por brazo de H1, lo que vuelve ilegible la comparación pre-registrada — se lee FALSEADA tal como está escrita, no ANULADA, en el registro con ese y el error de instrumento del chequeo de anchor; descriptivo pareado 142 : 0, $p\lt 10^{-40}$ (brazo anulado, no un veredicto sustituto); **la decisión del usuario (2026-09-29): lectura 1** — las condiciones legibles son el veredicto de H2, `harness` PASÓ. `harness-noblock` 80/160 es un error del corpus (un aliasing `% 3` entre el tercio sin bloque y la rotación de roles), no un aprendizaje parcial | H2 `results/H2-tracker-harness-20260929/BRIEF.md` |
| §8.9 | **H3 [ran], las dos barras PASARON**: `tr-s1` (entrenado sobre un segundo corpus que amplía el fraseo por turno/rol y da a cada rol un tercio parejo sin bloque) 158/160 contra `tr-s0` 147/160 sobre una suite fresca retenida, pareado 11:0, prueba de signo exacta $p=2\cdot2^{-11}\approx0,00098$, plano; `s1-noblock` 156/160, perdiendo 4 de 8 turnos contra el bloque, cada rol por encima de la barra, más o menos un tercio de los tokens de prompt | H3 [`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md) |
| §8.10 | **REAL0 — un miembro de mundo generado nunca entra a una biblioteca real**: `nolib` 0/25 (compuerta — los valores no están en los pesos); `base-reads` 22/25 (el techo de lectura); `base-walks` 1/25; `withlib-s1` (`distributor-wiki@v2`) 0/25, empatado contra `base-walks` ($p=1,0$) — **NO GENERALIZA**; en 40 de 40 caminatas su primera búsqueda es una consulta de su propio mundo de entrenamiento, 0 páginas abiertas | REAL0 [`results/REAL0-real-library-20260930/BRIEF.md`](../../results/REAL0-real-library-20260930/BRIEF.md) |
| §8.10 | **REAL1–2 — la entrada BM25 + page_text reparan llegar a la página, no la cita**: el titular de la base sin entrenar 1 → 4 → 7 de 25 a través de REAL0–REAL2; `distributor-wiki@v2` 0 → 1 → 5; la página de soporte se alcanza 24/25 | REAL1 [`results/REAL1-entry-20260930/BRIEF.md`](../../results/REAL1-entry-20260930/BRIEF.md), REAL2 [`results/REAL2-page-text-20260930/BRIEF.md`](../../results/REAL2-page-text-20260930/BRIEF.md) |
| §8.10 | **REAL3 — pérdida con máscara de tramos, M3 FUNCIONA sobre una familia de documentos nunca entrenada, dos semillas**: `real-spans-s0` 18/23 (78 %) contra `base-walks+page` 9/23, 10 : 1, $p=0,0117$; semilla 1 `real-spans-s1` 17/23 (74 %), 9 : 1, $p=0,0215$; intento 1 (pérdida de texto completo, antes de la corrección) `real-walks-s0` 1/23 — la falla leída, luego nombrada | REAL3 [`results/REAL3-real-corpus-20260930/BRIEF.md`](../../results/REAL3-real-corpus-20260930/BRIEF.md) |
| §8.10 | **REAL4 — la negativa es entrenable**: `real-none-s0` se niega en 15/16 filas sin respuesta (barra 13) y 5/6 de las adyacentes por tema, 0 negativas falsas de 36; contra `real-spans-s0` el costo en el titular es un empate dentro de la propia dispersión de corrida a corrida de vLLM (16/23 vs 17/23, 2 : 3, $p=1,0$) — **NEGATIVA CORREGIDA**, aceptado por el usuario como el miembro de documento real (2026-10-01) | REAL4 [`results/REAL4-refusal-20260930/BRIEF.md`](../../results/REAL4-refusal-20260930/BRIEF.md) |
| §8.10 | **REAL5 — transfiere a una tercera familia densa en enlaces (EPA 40 CFR 112); la cita es el faltante**: `real-none-s0` 15/25 (60 %) contra `base-walks+page` 2/25, 13 : 0, $p=0,00024$; valor correcto 20/25; negativas 5/5 — **PARCIAL**, bajo la barra del 70 % sólo por la cita estricta | REAL5 [`results/REAL5-third-family-20261001/BRIEF.md`](../../results/REAL5-third-family-20261001/BRIEF.md) |
| §8.10 | **REAL6 — entrenar valor repetido de un salto no corrige una cita de varios saltos**: `real-cite-s0` 15/25 contra `real-none-s0` 15/25, empate 1 : 1; las citas erróneas restantes son filas de varios saltos citadas en el extremo equivocado de un enlace, una forma que el corpus de 50 filas nunca contuvo — **FALSEADO** | REAL6 [`results/REAL6-citation-20261001/BRIEF.md`](../../results/REAL6-citation-20261001/BRIEF.md) |
| §8.10 | **H5 — la pérdida con máscara de tramos no es la receta por defecto**: con el bloque de herramienta mostrado a ambos, `tr-s3` (máscara de tramos) 140/160 turnos dependientes contra `tr-s1` (texto completo) 160/160, pareado 0 : 20 sobre una familia de frases (`type=defect` vs `type=bug`) — regresión, así que la pérdida con máscara de tramos se queda acotada a resultados de herramienta largos (páginas reales); los miembros de resultados cortos conservan la pérdida de texto completo de §4.4 | H5 [`results/H5-span-loss-tracker-20261001/BRIEF.md`](../../results/H5-span-loss-tracker-20261001/BRIEF.md) |
| §8.10 | **REAL7 — FALSEADO**: caminatas señuelo de enlace cruzado (la respuesta en el extremo de un enlace, el mismo número como señuelo en su inicio), familia de entrenamiento extendida con 49 CFR 390/392/393/397; sobre el titular sin gemelos de REAL5, `real-link-s0` empata con `real-none-s0` 13/21 (4:4, $p=1,0$), bajo la barra de ≥ 15/21 — valor correcto 22 vs 20, citas erróneas de mismo valor 2 vs 2, negativas 5/5 en ambos, el guardia de REAL4 no se compró; dos cambios de corpus sobre esta citación ya no cambiaron nada, la línea de corpus se detiene | REAL7 [`results/REAL7-crosslink-20261001/BRIEF.md`](../../results/REAL7-crosslink-20261001/BRIEF.md) |
