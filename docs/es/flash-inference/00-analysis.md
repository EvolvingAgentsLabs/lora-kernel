# Inferencia desde flash — Fase 0: análisis y cambios de spec propuestos

*Brief del usuario, 2026-09-27: "base congelada en flash/ROM + adaptadores en RAM". Este documento es la Fase 0 que ese brief
pide: responde sus preguntas, corrige la hipótesis donde hace falta, propone cambios de spec **sin implementarlos** y se frena
acá para revisión. Nada de esto toca el runtime de lora-kernel.*

---

## 1. Las tres preguntas del brief

**¿Sobre qué base corre hoy lora-kernel? ¿Densa o MoE?** Densa. Todos los miembros publicados están sobre
`google/gemma-4-E4B-it` y la mitad grande del par es `gemma-4-12B-it`, también densa **[ran]** B1, B2, M1b, M1d, B5. La
variante MoE, `gemma-4-26B-A4B-it`, está nombrada como alternativa de la mitad grande (`training/harness/family.py`,
`LARGE_ALTERNATIVE`) y nunca se usó.

Un matiz que importa para este brief: **el E4B ya es en parte "base en flash"**. De sus ~8.000 millones de parámetros,
~2.800 millones son tablas de embeddings por capa (42 capas × 256 × 262.144 filas, `hidden_size_per_layer_input: 256`
**[read]** config.json). Por token se lee **una fila** de cada tabla, así que esas tablas pueden vivir en almacenamiento
lento casi sin costo. Gemma 3n/4 las diseñó para eso **[read]**. Son también las tablas que hoy no dejan entrar al E4B como
borrador al lado del 12B en una L4 **[ran]** C0.

**¿Sobre qué módulos se aplican los adaptadores?** Sobre las siete proyecciones de cada capa del texto: `q, k, v, o`
(atención) y `gate, up, down` (MLP), con $r = 16$, $\alpha = 32$. Las torres de visión y audio quedan excluidas **[ran]**
`adapter_config.json`. Sobre una base MoE, eso significaría parchear también los expertos: ver §3.

**¿El kernel conoce el adaptador activo antes de generar?** Sí, y antes del primer token:
- el gateway resuelve el rol desde el token firmado y con eso el experto (`examples/school/gateway.py`);
- en vLLM el pedido nombra el adapter por el campo `model`;
- en la pista Mac el experto se activa con un puntero antes de `generate` **[ran]** LIVE, F0, MAC. **Superado el
  2026-09-28:** el serving del edge corre ahora en llama.cpp, no en MLX (`CLAUDE.md` §0); MLX queda como el banco
  de investigación de este documento, donde los números de cambio por puntero de arriba siguen valiendo.

**Hay una ventana para prefetch entre la llegada del pedido y el primer token de decode**: dura todo el prefill.

---

## 2. La hipótesis, corregida

**H1 del brief:** un adaptador de dominio concentra el ruteo de expertos respecto de la base sin adaptador.

**El problema de control.** Un MoE ya concentra su ruteo según el **tema** del texto, sin ningún LoRA. Si se compara
"base sobre prompts generales" contra "base + adapter sobre prompts del dominio", la concentración que puso el dominio se
le atribuye al adapter. El control correcto es **la base sin adapter sobre los mismos prompts del dominio**. H1 se parte en dos:

| | hipótesis | qué necesita | costo |
|---|---|---|---|
| **H1a** | **el dominio concentra el ruteo**: sobre prompts de un dominio, la base usa un conjunto de expertos más chico y más estable que sobre prompts generales, y una caché precargada por dominio acierta más | la base MoE y trazas; **nada entrenado** | horas de GPU |
| **H1b** | **el adapter lo concentra además**: sobre los *mismos* prompts del dominio, base + adapter concentra más que la base sola | un LoRA sobre la base MoE, que **no existe** | una sesión QLoRA en A100 + trazas |

**Orden:** H1a primero. Si el dominio no concentra el ruteo, H1 cae entera sin haber entrenado nada. Es la regla del
repositorio: primero la prueba barata que puede falsear.

---

## 3. La base MoE: qué hay y qué cuesta leerla

**Bases verificadas hoy [read]** (Hugging Face, 2026-09-27):

| | capas | expertos / capa | activos por token | tamaño de un experto | en MLX |
|---|--:|--:|--:|---|---|
| `google/gemma-4-26B-A4B-it` | 30 | 128 | 8 (`top_k_experts`) | $3 \times 2816 \times 704 \approx 5{,}95$ M parámetros | `mlx-community/gemma-4-26b-a4b-it-4bit`, **15,37 GB** |
| `Qwen/Qwen3-30B-A3B` | — | — | — | — | `mlx-community/Qwen3-30B-A3B-4bit` (sin verificar config) |

**La cuenta para Gemma 4 26B-A4B en 4 bits (derivada, no medida):**
- un experto ≈ 5,95 M × ~0,56 bytes (4 bits más escalas por grupo de 64) ≈ **3,3 MB**;
- todos los expertos: 128 × 30 × 3,3 MB ≈ **12,9 GB**; lo demás (atención, MLP denso, embeddings) ≈ **2,5 GB**, siempre en RAM;
- por token se leen 8 × 30 = **240 expertos ≈ 0,8 GB si ninguno está en caché**.

Con una tasa de acierto $h$ en la caché de expertos y un ancho de banda de lectura $\mathcal B$ del almacenamiento, el techo
de decode por I/O es

```math
\text{tok/s} \;\lesssim\; \frac{\mathcal B}{(1-h)\cdot 0{,}8\ \text{GB}}
```

A 3 GB/s: con $h = 0{,}8$ el techo es ~19 tok/s; con $h = 0{,}5$, ~7,5 tok/s. **El ancho de banda real del SSD se mide, no
se supone.** En una Mac de 16 GB, descontando sistema (~4 GB), la parte densa (2,5 GB) y la caché KV (~1 GB), quedan unos 8 GB
para expertos: ~60 % de ellos. **Toda la pregunta es qué 60 %.**

---

## 4. Cambios de spec propuestos (no implementados)

1. **Dónde va el LoRA en una base MoE.** Parchear sólo **atención** (y el router, si es entrenable), dejando los expertos
   intactos. Así los expertos, que son el 84 % de los bytes, quedan congelados y aptos para flash/ROM, y los deltas
   caben en RAM. Hay que medir si un LoRA sólo de atención conserva la calidad del experto: es un experimento propio,
   no una suposición.
2. **El manifiesto del miembro** (`releases/*.json`) suma `base_kind: dense | moe` y `lora_scope: attention | attention+router | all`.
3. **`expert_affinity` por miembro**: los expertos más usados por capa, con su frecuencia, calculados offline sobre un conjunto de
   prompts del dominio **distinto** del que se evalúa, y hasheados como hoy se hashea el corpus.
4. **Adaptadores sin fusionar**, aplicados como delta en tiempo de ejecución. Ya es lo que hacemos (vLLM por pedido; la pista
   Mac por puntero, 2,9 µs **[ran]** MAC); la fusión queda sólo para cuando un motor no admite delta, como el borrador de C0.
5. **Prefetch en el gateway**: al resolver el rol, antes del prefill, pedir la precarga de los expertos de afinidad del miembro.

---

## 5. Plan: H1a en la nube, con compuerta

**Dónde:** Colab, por decisión del usuario (2026-09-27): las corridas del MoE de Gemma 4 van en la nube, no en la Mac. Con
`transformers`, el modelo en 4 bits (bitsandbytes, ~15 GB) entra en una L4 o una A100. Un *forward hook* en el router de
cada capa registra los 8 expertos elegidos por token.

**Qué:**
- **Prompts** de los dominios que ya tenemos, ~30 por dominio: la wiki de la distribuidora, los turnos de la escuela, los
  turnos del personal de la distribuidora y el correo. A eso se suman ~30 prompts generales.
- **Trazas** del prefill y de 128 tokens de decode greedy. Pesa el decode, porque es donde se lee flash.
- **Formato:** `traces/{dominio}/{prompt_id}.parquet` con `token_idx, layer, expert_ids[8]`, fuera de git como todo artefacto pesado.
- **Métricas por dominio contra generales:**
  - entropía de expertos por capa;
  - fracción de expertos que cubren el 80 % de las activaciones;
  - Jaccard entre prompts del mismo dominio contra el de prompts de dominios distintos;
  - reuso entre tokens consecutivos.
- **Simulador de caché** con 4, 8 y 12 GB y las políticas LRU, LFU y "precargada por afinidad de dominio". La afinidad se
  calcula con la mitad de los prompts y se evalúa con la otra mitad.

**Compuerta de H1a, escrita antes de correr.** Con 8 GB, sobre prompts del dominio:
- la caché precargada por afinidad tiene que acertar **≥ 10 puntos más** que LRU sin afinidad;
- los bytes leídos por token tienen que bajar **≥ 25 %**;
- el Jaccard dentro del dominio tiene que superar al Jaccard entre dominios.

La comparación es prompt por prompt, con la prueba de signos del repositorio. Si falla, **H1 queda refutada** y la línea se
cierra con su documento.

**Si H1a pasa → H1b:**
- un LoRA **sólo de atención** sobre la base MoE, para el dominio wiki, entrenado con QLoRA en una A100;
- las mismas trazas con base y con base + LoRA, **sobre los mismos prompts**;
- la misma compuerta, ahora del adapter contra la base.

**Después, M3 y M4 como pide el brief.** M3 es la corrida real con streaming (mmap) en la Mac mini: vaciar la caché de
páginas (`sudo purge`) entre corridas, medir los bytes leídos del disco y separar prefill de decode. M4 es el borrador de
hardware.

---

## 6. Riesgos y decisiones abiertas

- **Alcance**: esto es una línea hermana del objetivo de `CLAUDE.md`, no el objetivo. Queda acotada en tiempo y bajo
  `experiments/flash-inference/` y `docs/flash-inference/`, sin tocar el runtime.
- **Medir en la Mac**: la excepción del usuario la cubre, pero el usuario prefiere la nube para el MoE. Sólo M3 (el streaming real)
  necesita la Mac mini, porque mide su SSD.
- **ROM**: congelar la base en silicio impide actualizarla; los LoRA siguen siendo la única vía de cambio.
- **Prefill**: con la base en flash, el prefill (que lee todos los expertos que el prompt toque) puede ser lento; se mide
  aparte.

**Pausa para revisión.** No sigo con código hasta que apruebes esta Fase 0: la partición H1a/H1b, la compuerta y el lugar
del LoRA.
