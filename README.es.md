# lora-kernel

**Un pool de deltas QLoRA sobre un modelo base residente, rankeado por un modelo más
grande de la misma familia que verifica sus tokens, con un modelo de frontera como
fallback permanente para lo que el pool está medido que falla.** Nada más es
neuronal.

*[Read me in English](README.md)*

[![corre dentro de OpenClaw](https://img.shields.io/badge/corre_dentro_de-OpenClaw-1f6feb)](https://docs.openclaw.ai/cli)
[![base hoy Qwen2.5-3B](https://img.shields.io/badge/base_hoy-Qwen2.5--3B--Instruct-555)](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
[![target hoy Qwen2.5-32B-AWQ](https://img.shields.io/badge/target_hoy-Qwen2.5--32B--AWQ-555)](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct-AWQ)
[![objetivo Qwen3.8-27B](https://img.shields.io/badge/objetivo-Qwen3.8--27B-8A5C10)](https://huggingface.co/Qwen/Qwen3.8-27B)
[![servido por vLLM multi-LoRA](https://img.shields.io/badge/servido_por-vLLM_multi--LoRA-555)](https://docs.vllm.ai)

**Corre dentro de un agente real.** [OpenClaw](https://docs.openclaw.ai/cli) en una
laptop → un proxy local → un túnel → vLLM en una placa alquilada → un QLoRA nuestro →
de vuelta, con las herramientas del inbox entregadas al agente por MCP y **cero
pedidos saliendo de la máquina** para todo lo que sirve el pool **[ran]** P43. Paso a
paso: [`docs/es/OPENCLAW.md`](docs/es/OPENCLAW.md).

Cada afirmación sobre este repositorio es **[ran]** con su directorio de corrida; cada
afirmación sobre cualquier otra cosa es **[read]** y citada; lo que no se pudo
verificar desde acá es **[unverified]** y nunca sostiene nada. Cada fórmula está
derivada, paso a paso y atada a su corrida, en
[`docs/es/FOUNDATIONS.md`](docs/es/FOUNDATIONS.md). **La regla que este proyecto
mantiene: cada documento lleva su matemática, y cada corrida en Colab actualiza la
fórmula que instancia.**

---

## Para qué sirve, y qué esperar de esto

**No** es un modelo de 3B que le gana a un modelo de frontera. **Es una arquitectura
por niveles que absorbe localmente la parte repetitiva y de alto volumen del tráfico
de una organización y manda afuera sólo el residuo** — y los números de abajo son la
razón por la que la frase está escrita así.

### Los puntos medidos

| configuración | exactitud entregada | sale de la máquina | corrida |
|---|---:|---:|---|
| todo local — el pool solo | **0,546** | 0 % | **[ran]** P41 |
| **la región que falla ruteada a la frontera** | **0,775** | **38 %** | **[ran]** P41 |
| un experto, en su propia tarea, servido como enseña su corpus | **0,992** (mensajes humanos 0,989) | 0 % | **[ran]** P55 A |
| el mismo experto, servido vía `tool_calls` | 0,808 (humanos 0,741, barra 0,655, $p = 0,00036$) | 0 % | **[ran]** P43 |

Las dos primeras filas son toda la tesis en miniatura. El plan original llamaba a la
frontera *andamio* a retirar cuando los expertos la igualaran; retirarla midió
**0,546**. Conservarla para lo que el pool está *medido* que falla — ruteado por
región, no adivinado por caso — midió **0,775** con el 62 % del tráfico sin salir
nunca. **La frontera se queda. Se queda para el residuo.**

### La economía, como modelo con sus entradas rotuladas

Sea $\rho$ la fracción de pedidos servidos localmente y $1-\rho$ la que va a una API de
frontera. Con $c_L$ el costo marginal de un pedido local y $c_F$ el de uno de frontera,

$$
\frac{\text{costo}_{\text{híbrido}}}{\text{costo}_{\text{frontera}}}
\;=\; \rho\,\frac{c_L}{c_F} + (1-\rho),
\qquad
\text{calidad}_{\text{híbrida}} = \rho\,Q_L + (1-\rho)\,Q_F .
$$

Lo que está **medido**: $\rho = 0,62$ y $\text{calidad} = 0,775$ sobre el pool de dos
regiones **[ran]** P41; un experto local en su propia región a $Q_L \approx 0,99$
**[ran]** P55 A; un delta local de **119.801.528 bytes** sobre una base que se lee una
vez por token **[ran]**. Lo que está **estimado, y se dice**: $c_L/c_F$. Un token
local es una porción de una GPU-hora amortizada sobre todos los pedidos de esa hora;
un token de frontera es un precio de lista. Sea cual sea la relación a tus precios,
la línea de costo de arriba es lineal en ella, y con $\rho = 0,62$ el híbrido queda
entre el **38 % del costo de frontera** (con $c_L \to 0$) y el costo de frontera (con
$c_L = c_F$). Tres reducciones más están medidas en forma y todavía no en tokens: la
superficie de herramientas que ofrece un agente se poda de **54 líneas a 3** antes
de armar el prompt (#190 **[ran]**); las instrucciones que vivirían en un system
prompt viven en los pesos; y **nada de lo que sirve el pool se manda a ningún lado**
**[ran]** P43.

### Dónde funcionan los expertos chicos, y dónde fallan — las dos cosas medidas

**Funcionan como obreros de línea de montaje sobre una región cerrada**: una tarea
fija, herramientas fijas, una regla mecánica. `email-full` aprende *qué* herramienta,
*con qué argumento*, y la regla *al menos dos de cuatro señales* hasta **0,989** en
mensajes humanos **[ran]**; el experto de fluidos reproduce el procedimiento de su
maestro paso a paso, **30/30** dentro de su región **[ran]** P9.

**Fallan en el borde, en silencio.** El mismo experto de fluidos cae a **1 de 20** en
familias que nunca vio — *con la misma fluidez, la misma estructura y la misma
confianza*, inventando fórmulas **[ran]** P22. Por debajo de su profundidad de
entrenamiento sobre-resuelve en **18 de 18** casos y la base pelada le gana, 0,167 a
0,000 **[ran]** P45. Cada guardia *conductual* probada — tasa de llamadas, largo del
transcript, un tripwire — dio **0,62 contra un azar de 0,60** **[ran]** P18. Una
guardia *estructural* sobrevive: el álgebra dimensional sobre $(\text{kg}, \text{m},
\text{s})$ atrapa el **0,80** del trabajo fuera de región, da falsa alarma 0,22 sola, y
combinada con el chequeo mecánico dispara **0 de 60** en región y sigue atrapando 0,35
afuera **[ran]** P22.

Entonces: **usarlos donde la tarea se repite miles de veces por día y la regla es
conocible; no usarlos solos donde un fallo silencioso cuesta más que la llamada que
ahorró.**

### Sólo modelos chicos — hoy no, y la proporción de largo plazo es una hipótesis

Hoy las guardias no son lo bastante confiables para correr sin el fallback, y el
número que lo dice es el de arriba: 0,62 contra 0,60. Los mecanismos con los que esta
arquitectura apuesta a subir $\rho$ son tres, cada uno con la matemática en la que se
apoya:

1. **Ruteo estructural, no inferido.** La propia estructura del software — la sala, el
   formulario, el endpoint — nombra al experto. Un diccionario de doce palabras clave
   ya rutea el caso grueso en **1,000** **[ran]**; eso es tanto una crítica a la suite
   como una victoria, y también es cómo rutea un despliegue real
   ([`docs/es/CASE-TEAM.md`](docs/es/CASE-TEAM.md): el grupo estable *es* la región).
2. **Verificación mecánica, y después escalar.** Donde la salida del experto se puede
   comprobar — un esquema, un test, una regla como `important()` — la frontera se
   llama sólo cuando el chequeo falla. Esa es la condición de retiro
   $Q_R(E) \ge Q_R(E\mid T) - \varepsilon$ en un test pareado, medida una vez en región
   con una calculadora en lugar del target: brecha **0,000** **[ran]** P7.
3. **Decodificación especulativa dentro de una familia.** Un experto chico draftea, un
   modelo local más grande verifica en una pasada, y los tokens emitidos se
   distribuyen exactamente como los del grande (§ *Cómo funciona*). Donde vale, la
   *calidad* del modelo grande llega a casi el *costo* del chico — y su tasa de
   aceptación rankea a los expertos sin juez.

**La expectativa, entonces:** $\rho$ alrededor de 0,6 está medido sobre un pool de dos
regiones; los mecanismos de arriba son los que lo moverían hacia 0,85–0,9 en regiones
nombradas estructuralmente y comprobables mecánicamente. **Esa proporción es una
hipótesis con ruta, no un resultado**, y 1,0 no está en la ruta: el trabajo fuera de
distribución y el arbitraje del residuo son para lo que se conserva la frontera.

---

## La tesis, con la fórmula al lado de cada reemplazo

| lo que es hoy | en qué se convierte | la matemática |
|---|---|---|
| un agente | **un QLoRA de dominio**, ~114 MB, conmutado en caliente por pedido | $W' = W + \tfrac{\alpha}{r}AB$ sobre siete proyecciones por bloque — **29.933.568** parámetros a $r=16$, **119.801.528** bytes en disco, la derivación y el artefacto coinciden **[ran]** |
| el router — una llamada extra a un modelo | **un diccionario** para la ruta gruesa (1,000 con doce palabras clave **[ran]**) y **la aceptación** para rankear expertos que se parecen | $\arg\max_i \alpha_T(E_i, c)$, válido sii $Q(T) \ge \max_i Q(E_i)$ |
| el harness — esquemas, parsers, reintentos | **serving en modo corpus**: parar en `</tag>`, inyectar el resultado real, seguir | $s_j = s_{j-1}\,\|\,\tilde s_j\,\|\,\texttt{= tool}(\tilde s_j)$ |
| el loop de evolución | **un torneo sobre adaptadores**, promovidos por un test pareado | $p = \min(1, 2\Pr[\mathrm{Bin}(n_d,\tfrac12)\ge\max(u,n_d-u)])$ |
| memoria, ejecución | markdown + git; un sandbox — **deliberadamente no neuronal** | — |

---

## El objetivo: `Qwen3.8-27B` como modelo grande, y la ruta hasta ahí

La decodificación especulativa necesita dos modelos con **el mismo espacio de ids**
(FOUNDATIONS §3.2): un id drafteado tiene que nombrar la misma cadena para los dos. Si
un par es usable es un hecho sobre el *par*, nunca sobre un modelo — y la tabla está
indexada así, porque una versión anterior se leía como un veredicto sobre el 27B y
estaba equivocada:

| drafter → target | ids del tokenizer | mapa de ids | ids sólo del target | usable |
|---|---:|---|---:|---|
| **Qwen2.5-3B → Qwen2.5-32B** *(hoy)* | 151.643 | archivo byte-idéntico | 0 | **sí** **[ran]** P48 |
| Qwen2.5-3B → Qwen3-32B | 151.643 | mapa idéntico | 4 (`<think>`, …) | sí **[ran]** P48 |
| Qwen2.5-3B → Qwen3.5 / 3.6 / 3.8-27B | 151.643 vs **248.044** | distinto | — | **no** **[ran]** P48 — *los drafters 2.5 no llegan* |
| **Qwen3.5-2B / 4B → Qwen3.8-27B** *(el objetivo)* | 248.044 | mapa idéntico | 7, todos especiales de audio/TTS; `<think>` compartido | **sí** **[ran]** D0 |

Así que el 27B es alcanzable, y lo que se mueve es el drafter: el pool migra de una
base `Qwen2.5-3B` a una base `Qwen3.5-4B`. **El target no necesita LoRA** — verifica,
nunca lleva un adaptador — así que nada sobre servir adaptadores lo restringe. Lo que
restringe al *drafter* es un hecho medido, C18: vLLM 0.29.0 carga un LoRA sobre
`Qwen3.5-4B`, loguea que lo hizo, y sirve la base igual, mientras el mismo
procedimiento sobre `Qwen2.5-3B` vuelve `applied` **[ran]** P33. La ruta, como
mecanismos:

| # | mecanismo | estado | compuerta |
|---|---|---|---|
| **D0** | un drafter 3.x que comparta espacio de ids con el 27B | ✅ **[ran]** | mapa de ids idéntico, sin colisiones |
| **D1** | C18 bajo un vLLM más nuevo | vacío — la cadena instala el último y es **0.29.0**, la versión de P33 **[ran]** | — |
| **D2** | **el mecanismo de C18**, leído con el log en la mano: G3 merge-and-serve; el mapeo clave PEFT ↔ módulo vLLM | **siguiente** | `applied` en la compuerta de identidad |
| **D3** | pensamiento apagado en el 27B | dentro de D4 | ids `<think>` emitidos sobre la suite: **0** |
| **D4** | el instrumento de P55, `--base Qwen/Qwen3.5-4B --target Qwen/Qwen3.8-27B`, pool graduado reentrenado sobre el 3.5-4B | bloqueado por D2 | la misma tabla de veredictos que M2 |

**Por qué el objetivo no es el primer paso.** Cada mecanismo de abajo es independiente
del target dado el espacio de ids; el instrumento construido sobre Qwen 2.5 es el que
corre D4. Si la aceptación resulta no rankear sobre 2.5 (M2), D4 habría comprado una
versión más rápida de un mecanismo que no funciona. Nada de M depende de D; D4 depende
de todo M.

---

## Cómo funciona, bloque por bloque

### El drafter: una base, un pool de deltas

Un bloque decoder mapea $h \in \mathbb{R}^{T\times d}$ a través de siete mapas lineales
— $W_q, W_k, W_v, W_o$ alrededor de la atención causal con RoPE y cabezas agrupadas, y
$W_{gate}, W_{up}, W_{down}$ en una MLP SwiGLU (FOUNDATIONS §1.2). Un experto parchea
exactamente esas siete en cada bloque:

$$
xW' \;=\; xW \;+\; \tfrac{\alpha}{r}\,(xA)B,
\qquad A\in\mathbb{R}^{d_{in}\times r},\ B\in\mathbb{R}^{r\times d_{out}},\ r=16.
$$

$W$ nunca se toca, así que la base queda residente y un batch de pedidos en el que el
pedido $j$ nombra al adaptador $i(j)$ es un GEMM compartido más un par de GEMMs
delgados recolectados,

$$
y_j = x_j W + s\,(x_j A_{i(j)})\,B_{i(j)},
$$

que es lo que calculan los kernels Punica / `bgmv` de vLLM **[read]** y lo que activa
`--enable-lora --max-loras k --lora-modules nombre=ruta` **[ran]**. **C18 es el test de
que el segundo término está presente**: el mismo prompt por la base y por el
adaptador, los textos tienen que diferir. `--max-loras` sólo fue 1 o 2 acá; S-LoRA
reporta miles en una máquina **[read]**, y el nuestro no está probado por encima de
dos.

En la línea 3.5/3.8 el bloque es distinto — tres capas de atención lineal **Gated
DeltaNet** por cada una de atención completa **[read]** `config.json`, la recurrencia

$$
S_t = \alpha_t\,(I - \beta_t k_t k_t^\top)\,S_{t-1} + \beta_t\,k_t v_t^\top,\qquad o_t = S_t^\top q_t,
$$

con un estado fijo $d_k\times d_v$ por capa en vez de una caché KV que crece. **Sus
proyecciones siguen siendo mapas lineales** $\tilde hW$, así que el delta de arriba se
les aplica sin cambios; si el *motor* lo aplica es C18, una propiedad del camino de
kernels y no del álgebra.

### El target: una pasada con teacher forcing verifica un draft entero

Generar es la recursión $x_t \sim p(\cdot\mid x_{<t})$; el decode lee cada peso una vez
por token, así que su piso es $t_{\text{step}} \gtrsim B_W/\mathcal B$ — **~13 ms/token
para un target de 19,3 GB en una A100** — y un 27B con 48 capas recurrentes es lento
por token por la misma razón. Una pasada de verificación sobre un prefijo y $k$ ids
drafteados cuesta **una** lectura así para las $k+1$ posiciones (FOUNDATIONS
§2.3–2.4). A temperatura 0 el target es one-hot, así que el test de aceptación de la
decodificación especulativa $\min(1, p_T/q)$ colapsa a

$$
\text{aceptar } \tilde x_i \iff \tilde x_i = \arg\max_v\, p_T(v \mid \text{prefijo}, \tilde x_{<i}),
$$

leído acá como *rango = 1* en los `prompt_logprobs` del target — la distribución
completa con teacher forcing a lo largo de un texto dado, devuelta por un prefill, sin
generar nada **[ran]** P55 A. La secuencia emitida se distribuye exactamente como la
del target sea cual sea el drafter (FOUNDATIONS §6.2), y por eso la aceptación es una
afirmación *sobre el drafter*. Con tasa por token $\alpha$ y $k$ drafts,

$$
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha},
\qquad
\text{aceleración} = \frac{\mathbb{E}[\tau]}{k\,c + 1},\quad c = \frac{t_{\text{draft}}}{t_{\text{target}}},
$$

y la ganancia crece cuando $c \to 0$ — un 4B drafteando para un 27B lento es
exactamente el régimen donde un target grande y recursivo justifica la maquinaria.
**Todavía no se midió ninguna α; el instrumento está construido.**

Sobre un target híbrido la pasada de verificación corre los tokens drafteados por la
recurrencia de arriba dentro del kernel de prefill GDN por chunks de vLLM y por las
capas de atención completa con su KV paginada; los siete ids sólo del target son
especiales de modalidad que la tarea de texto nunca alcanza, y `<think>` — compartido
por los dos modelos — es un flag de serving (D3).

### Dentro de vLLM: qué parte hace qué

| componente | trabajo acá | evidencia |
|---|---|---|
| motor + scheduler (batching continuo) | $n$ secuencias comparten una lectura de pesos por paso; 475 cadenas por el 3B en **31 s**, por el 32B en **230 s** a concurrencia 8 | **[ran]** P55 A |
| caché KV PagedAttention | $\text{bytes}_{KV}(t) = 2LH_{kv}d_h\,t\,b$ — 36 KB/token en el 3B, 256 KB/token en el 32B | **[read]** config |
| caché de estado GDN (`Mamba cache mode … align`) | el $S_t$ fijo por capa lineal en los modelos 3.5/3.8 | **[ran]** log de P33 |
| `LoRAModelManager` + `PunicaWrapper` (`bgmv` shrink/expand) | el término delta recolectado sobre los módulos `Linear` del **drafter**; el log nombra cuáles saltea — en `Qwen3.5-4B` todos los salteados eran `visual.*` | **[ran]** log de P33 |
| servidor OpenAI: `/v1/completions` con `stop`, `include_stop_str_in_output` | el loop de modo corpus: generar hasta `</tag>`, inyectar, seguir | **[ran]** P55 A |
| servidor OpenAI: `prompt_logprobs` | el rango del target para cada token drafteado en un prefill | **[ran]** P55 A |
| worker especulativo nativo (`speculative_config`) | **no se usa**: ata un drafter al arranque; el reenvío de adaptador por pedido hacia él es **[unverified]** | — |

**Dos instancias, entonces.** El servidor del drafter tiene la base y el pool; el del
target tiene el modelo grande solo. El drafter escribe toda la cadena en modo corpus;
el target la puntúa por `prompt_logprobs`. Bajo la identidad del argmax los veredictos
por token son exactamente los que calcularía un loop fusionado — un prefill por span
en vez de por ronda, más caro por token e igual de informativo, y no necesita nada del
camino especulativo de vLLM. Tampoco da aceleración de reloj, que este proyecto no
compra: **la latencia es de EAGLE** — una cabeza por target entrenada sobre los estados
ocultos del target draftea mejor que cualquier experto separado **[read]** — y lo que
una cabeza atada no puede hacer es comparar $k$ expertos distintos. **El ranking es
nuestro.**

```mermaid
flowchart LR
    subgraph D["SERVIDOR DEL DRAFTER — el pool"]
        direction TB
        B["base residente<br>hoy Qwen2.5-3B · objetivo Qwen3.5-4B"]
        E1["δ₁ = (α/r)A₁B₁"]
        E2["δ₂"]
        E3["δ₃"]
        B --- E1
        B --- E2
        B --- E3
    end
    subgraph T["SERVIDOR DEL TARGET — el modelo grande, sin adaptador"]
        direction TB
        V["una pasada con teacher forcing<br>prompt_logprobs → rango de cada token drafteado<br>hoy Qwen2.5-32B-AWQ · objetivo Qwen3.8-27B"]
    end
    E1 -- "draft, modo corpus" --> V
    E2 -- "draft" --> V
    E3 -- "draft" --> V
    V ==> R["α por experto, por caso<br>gana la rama con la que el target más concuerda — sin juez"]
    R -.-> Q["el verificador sobre los MISMOS casos:<br>válido sólo mientras Q(T) ≥ max Q(E)"]

    classDef base fill:#F4F3F0,stroke:#C4C4BF,color:#15171B
    classDef expert fill:#EAF1F9,stroke:#3E52A3,color:#15171B
    classDef target fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef win fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class B base
    class E1,E2,E3 expert
    class V target
    class R win
    class Q base
```

### Por qué la aceptación rankea — y cuándo no puede

Para expertos $E_1,\dots,E_m$ sobre una suite con verificador mecánico, la calidad
verificada es $Q(E)$ y la aceptación es $\alpha_T(E) = $ la fracción de los tokens de
decisión de $E$ que el target habría escrito. **La afirmación:**

$$
Q(E_a) > Q(E_b) \;\Rightarrow\; \alpha_T(E_a) > \alpha_T(E_b),
$$

un orden de expertos sin juez en tiempo de serving. Es sobre *calidad* sólo cuando
$Q(T) \ge \max_a Q(E_a)$: por debajo, $\alpha$ premia al experto que comparte los
errores del target. Esa desigualdad es una compuerta, probada como test de signos
pareado antes de comprar ninguna aceptación, y **disparó en la suite de triage**: el
32B sin entrenar consiguió todos los hechos y aplicó mal la regla, $0,746 < 0,989$, el
experto bien donde el target mal en 87 casos contra 2 **[ran]** P55 A. El instrumento
estaba listo y correctamente no corrió. La región `commitment` del desk es donde el
mismo 32B está medido en **1,000 en cada profundidad** **[ran]** P51 — P55b corre ahí.

---

## El retiro — del target local, por región; la frontera se queda

El target grande es andamio *por región*. Mientras verifica, cada token aceptado o
rechazado es un dato gratis: para cada región del espacio de problemas, con qué
experto el target sigue concordando. Cuando la aceptación de un experto cruza el umbral
que elegiste **y el puntaje verificado se sostiene sin el target** — $Q_R(E) \ge
Q_R(E\mid T) - \varepsilon$ en un test pareado — el target sale de esa región y el
experto genera solo. Una API de frontera nunca es el target — sin logprobs forzados
(C2), sin ids compartidos (C3) — es el **fallback** permanente para lo que el pool está
*medido* que falla: **0,546 → 0,775** con el 38 % de los casos saliendo **[ran]** P41.

```mermaid
flowchart LR
    subgraph PA["FASE A — el modelo grande local es el target"]
        direction TB
        A1["los expertos draftean"] --> A2["el target verifica,<br>token por token"] --> A3["la aceptación se acumula,<br>por región"]
    end
    subgraph PB["FASE B — el target se fue, para esa región"]
        direction TB
        B1["un diccionario elige"] --> B2["el experto genera solo"] --> B3["sin llamada al modelo grande"]
    end
    subgraph FR["LA FRONTERA — permanente, y nunca el target"]
        direction TB
        F1["lo que el pool está MEDIDO que falla<br>0,546 → 0,775, 38 % saliendo"]
    end
    PA == "la aceptación cruzó Y el puntaje verificado se sostuvo" ==> PB
    PB -. "las regiones que ningún experto cubre" .-> FR

    classDef a fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef b fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    classDef f fill:#FCF3F1,stroke:#B0523C,color:#15171B
    class A1,A2,A3 a
    class B1,B2,B3 b
    class F1 f
```

---

## El progreso, resumido

**Construido y medido.** Una base residente; deltas conmutados por el campo `model`;
servidos por vLLM detrás de un endpoint OpenAI; alcanzables desde un agente real sin
que nada salga; la superficie de herramientas podada a lo que cada miembro declara. Un
experto en **0,989** sobre su propia región, **liberado como `email-full@v1`**: re-servido
reproduce su registro caso por caso, y un reentrenamiento del mismo corpus empata 1 : 0
**[ran]** P57; la ruta de serving que le costaba 18 puntos, encontrada y arreglada. El instrumento de aceptación construido, con
preflights y compuertas. Los espacios de ids medidos por par; la ruta a `Qwen3.8-27B`
nombrada mecanismo por mecanismo.

**Todavía no.** La aceptación nunca se midió contra ningún target, y el veredicto de
orden nunca corrió — las dos filas que FOUNDATIONS §11 marca *no medido*. Un pool de
más de dos. El drafter 3.x. El torneo.

| # | mecanismo | estado | compuerta |
|---|---|---|---|
| **M0** | el drafter servido **en modo corpus** — vía `tool_calls` *inventa* el resultado que no puede recibir | ✅ **[ran]** 0,808 → **0,992** | stop honrado; adaptador ≠ base en 8 sondas (C18) |
| **M-target** | un target que valga la pena **en esta tarea** | ❌ triage: **0,746 < 0,989**, 2 : 87 **[ran]**; ✅ desk `commitment`: 32B **1,000** en cada profundidad **[ran]** P51 | le gana al mejor experto, pareado, $p\le0,05$ |
| **M-α** | aceptación en **tokens** por `prompt_logprobs` forzados | ✅ preflights pasan **[ran]**; todavía no corrió | templates idénticos; una entrada por token con `rank` |
| **M1** | **expertos que difieren en calidad** — corpus anidados graduados | ✅ por un bit **[ran]** P55b: `g25` 0, `g75` **240/240**, `g600` **240/240** — el riesgo nombrado se cumplió, **sin grado intermedio** | el verificador resuelve ≥ 1 par, o el target no se sirve |
| **M2** | **la prueba de orden** — la tesis | ❌ **cerrada 2026-09-17, no comprable en suites generadas [ran]**: en triage el 32B queda debajo del experto (0,746 < 0,989); en el desk también (0,967 < 1,000, 0 : 8); y donde el target es fuerte los grados saturan (`g75` ≡ `g600` = 1,000). **Un 32B de la misma familia sin entrenar no es target válido para una tarea en la que un 3B fue entrenado**, y ninguna suite generada ofrece a la vez un target más fuerte y un orden no trivial. El desenlace negativo es el entregable; se guarda un rediseño para una suite con datos reales | SUPPORTED / FALSIFIED / UNRESOLVED-como-fracaso, escrito antes de correr |
| **D0–D4** | la ruta a `Qwen3.8-27B` | D0 ✅, D1 vacío; **bloqueada por diseño** — la Fase 4 cerró sin veredicto, y D4 compraría una versión más rápida de un mecanismo sin veredicto | ver arriba |

Los pasos que llegaron hasta acá, cada uno con su número, están en
[`docs/es/EXPERIMENT_PLAN.md`](docs/es/EXPERIMENT_PLAN.md); el registro compacto:

| | objetivo | estado |
|:--:|---|---|
| **S1** | una brecha real contra la frontera | ✅ **+0,533** una vez que el prompt dejó de decirle a la base que no pensara |
| **S4** | el experto se especializa por región | ✅ **+63,3** |
| **S5** | la brecha de retiro se cierra, con una calculadora en lugar del target | ✅ **0,000** en región |
| **S9** | una región que es la mañana de alguien, de punta a punta dentro de un agente real | ✅ **0,741** vía `tool_calls` (P43) → **0,989** en modo corpus (P55 A), cero pedidos saliendo |
| **S10** | la base sobre la que corre el pool | ✅ **Qwen 2.5, decidido contra un control** — C18 sobre `Qwen3.5-4B` |
| **S8** | el pool detrás de un endpoint OpenAI | 🟢 tags→`tool_calls` sin dominio, 604/604; la superficie podada a lo que cada miembro declara (#190) |
| **S3** | el router le gana a una tabla | 🟡 empata con un diccionario de doce palabras en **1,000** — los miembros están demasiado lejos para encontrarse en un problema |
| **S6** | `harness.lora` — el protocolo aparte del experto | 🟡 estacionado, y reabierto abajo como el extra experimental |
| **S7** | el torneo | 🟢 fitness fijado: los dos jueces tienen que aceptar |

### Lo que realmente corrió

| afirmación | medición | dónde |
|---|---|---|
| **La ruta de serving costaba 18 puntos** | el mismo adaptador de 598 ejemplos: 0,808 vía `tool_calls`, **0,992** en modo corpus, reproducido en dos sesiones a 31 s | `results/P55-graded-ranking-20260916/` |
| **Un 32B sin entrenar no es un target válido en triage** | humanos 0,746 contra 0,989 del experto, pareado **2 : 87**, $p=0$; consigue los hechos y aplica mal la regla | ídem |
| **Los espacios de ids, por par** | 2.5 → 2.5-32B byte-idéntico; 2.5 → 3.x-27B imposible; **3.5-2B/4B → 3.8-27B idéntico, 7 especiales de audio/TTS** | `results/P48-…/`, `results/P55-…/D0-tokenizers.txt` |
| **C18** | vLLM carga un LoRA sobre `Qwen3.5-4B` y sirve la base; el control sobre `Qwen2.5-3B` aplica; los módulos salteados son todos `visual.*` | `results/P33-lora-matrix-20260914/` |
| **El desk tiene target y gradiente** | `commitment`: 32B **1,000** en cada profundidad, una llamada `message` cada uno; base 1,000 → 0,000 | `results/P51-desk-profile-20260916/` |
| **Un experto despeja su compuerta dentro de un agente real** | 260/351 = 0,741, $p=0,00036$ exacto; OpenClaw → proxy → túnel → vLLM → QLoRA, cero pedidos saliendo | `results/P43-openclaw-e2e-20260915/` |
| **Rutear por región paga; por caso no** | 0,546 → **0,775** con 38 % saliendo; reglas por caso 0,378 y 0,689 | `results/P41-routing-20260915/` |
| **El experto no siente su borde; una guardia estructural sí** | 30/30 en región → 1/20 afuera con la misma confianza; guardias conductuales 0,62 contra azar 0,60; el álgebra dimensional atrapa 0,80, combinada dispara 0/60 en región | `results/P18-…/`, `results/P22-dimensions-20260912/` |
| **Un experto está atado a la profundidad de su corpus** | bajo su banda sobre-resuelve **18 de 18**; a tres pasos la base pelada le gana 0,167 : 0,000 | `results/P45-ladder-sweep-20260915/` |
| **El 69–82 % de un margen de calibración era la suite** | agrupando por lo que un predictor puede ver, el techo deja margen 0,030 y 0,007 | `results/P46-ranking-ceiling-20260916/` |
| **La ruta gruesa no necesita modelo** | doce palabras clave, **1,000** sobre 200 casos; la ruta fina cae a 0,845 | `tests/test_router_baseline.py` |
| **La aceptación por caracteres mide formato** | respuestas idénticas 0,00 entre formatos, distintas 0,44 dentro de uno — por eso α está ahora en tokens sobre un espacio de ids compartido | `results/S0*/` |
| **La brecha de retiro se cierra, con una calculadora** | adaptador + calculadora **40/40** = el maestro; base + calculadora 0/40 | `results/P7-calculator-20260908/` |

---

## Extra experimental: cuánto del harness puede ser un LoRA

El diseño original tenía un `harness.lora` — el protocolo de ejecución en los pesos,
para que el esquema salga del prompt y el formato se emita en vez de parsearse. Se
estacionó por números, y los números son la razón por la que se reabre sólo como
experimento:

| medido | qué dice |
|---|---|
| un protocolo aprendido **9/30** donde veinte líneas de `re` dan **23/30**, en una suite con una herramienta **[ran]** P13 | donde la llamada es una copia de una expresión ya escrita, el código gana y los pesos no pueden |
| el mismo adaptador de protocolo sobre un **segundo tema** para el que nunca se editó: **27 de 63** llamadas donde la regla escrita a mano escribe **0 de 63** **[ran]** P25 | un harness escrito a mano no transfiere nada; uno aprendido transfiere parte de sí |
| una convención por conteo de parámetros recupera el **55 %** del costo esquema→tags con **0** líneas de dominio **[ran]** P28 | la mayor parte del valor del harness son un puñado de convenciones estructurales, no conocimiento |

**La pregunta experimental, enunciada para que pueda fallar:** para una superficie de
herramientas fija y estrecha — las tres del inbox, las cuatro del desk — ¿puede la
*decisión* de qué herramienta llamar y cómo llenar su argumento vivir en los pesos,
dejando la *ejecución* (parar, inyectar, seguir) a veinte líneas de harness? P55 A ya
muestra una mitad: `email-full` toma la decisión en **0,989** con **0** llamadas
rechazadas y el harness ejecuta. La compuerta de la otra mitad es la que S6 fijó y no
alcanzó: tasa de llamadas malformadas **y** tokens, ambas contra el incumbente en
código, sobre una superficie donde la llamada *no* es una copia. No es una afirmación
de producto; es un experimento acotado con su propio número a batir.

## Lo que deliberadamente NO es un LoRA

**Memoria** — markdown bajo git, porque un delta de pesos no se puede leer, diffear ni
corregir por una persona. **Ejecución** — el sandbox donde corren las herramientas.

## Cómo se libera

Open-core. **Abierto:** el runtime — multi-LoRA sobre vLLM, el instrumento de
aceptación, la maquinaria de retiro; la especificación del protocolo; el conector de
memoria markdown + git. **No abierto:** packs de adaptadores verticales entrenados; el
pipeline gestionado de dream/evolución; el plano de control enterprise.

## Linaje

| | |
|---|---|
| [`evolving-agents`](https://github.com/EvolvingAgentsLabs/evolving-agents) | El repositorio activo — flujos, memoria en cuatro niveles, agentes como markdown |
| [`gemma4nanoloop`](https://github.com/EvolvingAgentsLabs/gemma4nanoloop) | El caso medido de que un modelo local chico corre un loop cerrado |
| `agentvcs` | Versiona código, skills, objetivos, modelos y trazas juntos — el sustrato sobre el que puntúa el torneo |

## Documentos

- [`docs/es/FOUNDATIONS.md`](docs/es/FOUNDATIONS.md) — **la matemática, paso a paso y
  atada a lo que corrió** · [en](docs/FOUNDATIONS.md)
- [`docs/es/SUBSTRATE-GATE.md`](docs/es/SUBSTRATE-GATE.md) — Fase 0: el sustrato de serving
  como compuerta, y por qué existe cada uno de sus cuatro chequeos · [en](docs/SUBSTRATE-GATE.md)
- [`docs/es/EXPERIMENT_PLAN.md`](docs/es/EXPERIMENT_PLAN.md) — cada paso con su
  compuerta, su falsación y su número · [en](docs/EXPERIMENT_PLAN.md)
- [`docs/es/STACK.md`](docs/es/STACK.md) — el inventario: cada id de modelo,
  hiperparámetro de adaptador y flag de vLLM, con su corrida · [en](docs/STACK.md)
- [`docs/es/ARCHITECTURE.md`](docs/es/ARCHITECTURE.md) — las siete capas, la matemática
  de cada una y la condición de retiro · [en](docs/ARCHITECTURE.md)
- [`docs/es/TECHNICAL-REFERENCE.md`](docs/es/TECHNICAL-REFERENCE.md) — los mecanismos y
  la fórmula detrás de cada uno · [en](docs/TECHNICAL-REFERENCE.md)
- [`docs/es/REPORT.md`](docs/es/REPORT.md) — el plan original contra lo que pasó ·
  [en](docs/REPORT.md)
- [`docs/es/OPEN-PROBLEMS.md`](docs/es/OPEN-PROBLEMS.md) — los problemas abiertos, sin
  jerga · [en](docs/OPEN-PROBLEMS.md)
- [`docs/es/OPENCLAW.md`](docs/es/OPENCLAW.md) — apuntar un agente real al pool ·
  [en](docs/OPENCLAW.md)
- [`docs/es/CASE-TRIAGE.md`](docs/es/CASE-TRIAGE.md),
  [`docs/es/CASE-TEAM.md`](docs/es/CASE-TEAM.md) — la mañana de una persona; muchos
  grupos en una GPU
- [`tests/README.md`](tests/README.md) — cada archivo de test y la identidad que protege
- [`docs/es/the-frontier-is-scaffolding.md`](docs/es/the-frontier-is-scaffolding.md) —
  el artículo · [en](docs/the-frontier-is-scaffolding.md)

## Reconocimiento

Esta línea empezó con una conversación con
**[Ismael Faro](https://github.com/ismaelfaro)**, que sugirió estudiar la
decodificación especulativa y para qué podría servir.

---

<sub>Apache 2.0 · [Evolving Agents Labs](https://github.com/EvolvingAgentsLabs)</sub>
