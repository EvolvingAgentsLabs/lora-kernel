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

---

## 7. Resultado de H1a — reanudada el 2026-10-04, FALSIFICADA como se escribió; la sustancia se sostiene

**Reanudada por decisión del usuario, el 2026-10-04**, después de la pausa de arriba (también registrado en
[`docs/review/moe-distillation-and-spotlight.md`](../review/moe-distillation-and-spotlight.md) §4). H1a corrió en una
A100, `gemma-4-26B-A4B-it` con sus expertos cuantizados a int4 en la placa (bitsandbytes no cuantiza un parámetro de
experto 3-D — leído durante la corrida — así que el modelo carga en bf16 en el host, ≈ 52 GB, y se cuantiza capa por
capa en la GPU), 150 prompts trazados (30 por dominio × 5 dominios: wiki, escuela, distribuidora, correo, general),
0 errores. **[ran]** `results/H1A-moe-routing-by-domain-20261004/BRIEF.md`.

| compuerta de §5, a 8 GB, prompts del dominio | valla | medido |
|---|---|---|
| la caché precargada por afinidad acierta más que LRU | ≥ 10 puntos | **+7,4** (LRU 92,1 %, afinidad 99,5 %) — **falla** |
| los bytes leídos por token de decode bajan | ≥ 25 % | **−93 %** (62,4 → 4,1 MB/token), afinidad adelante en 60/60 prompts |
| Jaccard dentro del dominio supera al Jaccard entre dominios | — | **0,49 contra 0,26**, 120 : 0 |

**Veredicto como se escribió: FALSIFICADA** — la única cláusula que falla es el margen absoluto de 10 puntos, y no
tenía margen: LRU solo ya acierta 92,1 % a 8 GB una vez que el prefill la calienta, así que ningún comportamiento de
ruteo podía agregar 10 puntos más. El propio instrumento de la corrida marcó `no_headroom`. Leído más allá de esa
cláusula, el dominio concentra fuerte el ruteo del 26B: el 80 % de las activaciones de decodificación de un dominio
cae en 17–21 % de los expertos (40 % en texto general, entropía 5,0–5,3 contra 6,2 bits), y una caché anclada a los
expertos top de un dominio, aprendida sobre la mitad de sus prompts, lee 93 % menos bytes por token sobre la otra
mitad a 8 GB, ganando en cada prompt. El control de texto general va al revés (afinidad −6 puntos contra LRU), así que
la ganancia es del dominio, no de la política de anclaje — la separación que pedía §2.

Al lado de la compuerta: a 4 GB el margen de afinidad sobre LRU es +15,5 puntos (77,9 % → 93,4 %), donde la elección de
8 GB de la compuerta ya le había costado su margen a la cláusula de los 10 puntos; a 12 GB las dos políticas están casi
saturadas (98,8 % → 100 %).

**Para esta línea:** la sustancia de H1a es lo que necesitaba §2.3 del documento de revisión — de donde parte la idea
de poda de REAP. H1b (¿un adaptador sólo-atención entrenado sobre la base MoE concentra el ruteo todavía más que la
base sola?) y M3 (streaming real desde el SSD de la Mac mini) son los próximos pasos, los dos decisión del usuario,
todavía no tomada.

---

## 8. ¿Vale la pena la línea? Mejores resultados, funciona, a qué velocidad (evaluación, 2026-10-04)

El usuario hizo tres preguntas sobre la línea flash. Cada una se responde desde el registro de H1a (`h1a.json`:
métricas agregadas de ruteo y caché por dominio) y desde corridas ya en disco. **Las trazas por prompt se borraron
cuando se limpiaron los worktrees** (quedaban fuera de git por diseño), así que una simulación de prefill por prompt
necesitaría volver a correr H1a (una A100).

**1. ¿Mejores resultados? Desconocido, y la evidencia hasta ahora dice que no.** Una huella de memoria más chica para
el 26B vale solo lo que valga que el 26B le gane a lo que se sirve hoy. En las regiones de este proyecto ningún
modelo más grande le ganó al miembro E4B: un 12B entrenado empata (B3, PAIR1 **[ran]**), un 12B sin entrenar pierde
(PAIR0 **[ran]**). La corrida de techo propia del 26B (TEACH0) está
**cerrada por decisión del usuario del 2026-10-05, bloqueada por el motor de servido, sin resultado [ran]**: el FP8 de
vLLM 0.30 no corre en la A100 y no tiene método `bitsandbytes` para el reintento en la L4
(`results/TEACH0-26b-headroom-20261004/BRIEF.md`). Al lado, la propia tarjeta del modelo de Google **[read]** informa
τ² (promedio de 3) en 68,2 % para el 26B-A4B contra 69,0 % para el 12B y 76,9 % para el 31B
(`docs/tau2/TEACHER-TERMS.md` §2.1; autoinformado): en ese arnés el 26B no está por delante del 12B, que es justo lo que
PAIR0/PAIR1 ya mostraron que no compra precisión acá. **El pago de la línea dependía de que un modelo más grande le
ganara al miembro, y ninguno le ganó: la línea compra velocidad o huella para un modelo sin ganancia de calidad
medida. Descansa hasta que un modelo más grande muestre valor** — la pregunta se muda a τ² T1 (Gemma 4 31B contra el
E4B base sobre un verificador externo, `docs/tau2/RECON.md`).

**2. ¿Funciona? La mitad del ruteo, sí [ran].** Sobre los tokens de decode de un dominio, el 80 % de las activaciones
cae en 17–21 % de los expertos (texto general: 40 %). Una caché anclada a los expertos top del dominio lee 93 %
menos bytes por token de decode a 8 GB (62 → 4,1 MB) y 70 % menos a 4 GB (175 → 52 MB). **El prefill es más amplio:**
el 80 % de las activaciones de prefill cae en alrededor del 25 % de los expertos (general: 31 %), y un prefill de
unos cientos de tokens toca la mayoría de los expertos de la mayoría de las capas.

**3. ¿A qué velocidad, en una máquina de 16 GB? El decode plausiblemente sí; el prefill y la memoria son los riesgos
(derivado, no medido).** La cota es la fórmula de §3, con el ancho de banda de lectura $\mathcal B$ asumido en 3
GB/s, todavía sin medir:

$$\text{tok/s}_{\text{decode}} \;\lesssim\; \frac{\mathcal B}{\text{MB leídos por token}}$$

| | caché de expertos | MB leídos por token de decode [ran] | techo de I/O a 3 GB/s |
|---|---|---|---|
| anclada por afinidad | 8 GB | 4,1 | ~730 tok/s — el I/O deja de importar; lo acota el cómputo (~4B activos por token, cerca del E4B) |
| anclada por afinidad | 4 GB | 52 | ~58 tok/s |
| LRU | 4 GB | 175 | ~17 tok/s |

- **Memoria.** 16 GB menos el sistema (~4 GB) y la parte densa (2,5 GB) deja ~9,5 GB para expertos *y* la caché KV.
  Las caminatas de este proyecto llegan a 12k tokens: en esta Mac, el E4B se quedó sin memoria con un contexto de
  16.384 tokens (LIVE-library **[ran]**). Una caché de expertos de 8 GB deja ~1,5 GB para KV, demasiado poco para
  estas caminatas. Una caché de 4–6 GB es la realista.
- **Prefill.** Cada turno con herramienta vuelve a prefillear sus tokens nuevos, y tocan la mayoría de los expertos.
  Con la caché anclada, los expertos que quedan afuera se leen del almacenamiento una vez por prefill. Eso es hasta
  (1 − proporción en caché) × 12,9 GB: unos 9 GB con una caché de 4 GB, unos 3 s por prefill a 3 GB/s. Una caminata
  hace 3–5 llamadas, así que son **+9–15 s por caminata** en el peor caso, contra los 13 s de toda la caminata del
  E4B (mediana, LIVE-library **[ran]**). La cifra real es menor, porque no se toca cada experto, pero no está
  medida.

**Veredicto de esta evaluación:** el mecanismo funciona para decode, y la velocidad de decode en una máquina de 16
GB es plausible con una caché de 4–6 GB. El prefill, en las caminatas de este proyecto que usan muchas herramientas,
y la memoria que le queda a la caché KV son los riesgos abiertos. El pago de la línea depende por completo de un
resultado de calidad que no tiene. **Orden:**
1. ~~TEACH0 (mañana, en Colab).~~ **Corrió el 2026-10-04, bloqueada; cerrada el 2026-10-05 por decisión del usuario, sin
   resultado**: FP8 falló dos veces (compilación de inductor; después el kernel FP8 de vLLM no corre en el sm80 de la
   A100); la A100 fue rechazada tres veces; el único reintento con bitsandbytes que permite el brief (una L4) se
   encontró con un vLLM 0.30 sin ese método. ~~El reintento corre cuando vuelva la cuota de A100.~~ No hay reintento: la
   línea del 26B está cerrada, y por eso PAIR0/PAIR1 más la tarjeta de Google **[read]** (26B 68,2 contra 12B 69,0 en
   τ²). La línea **descansa hasta que un modelo más grande muestre valor**; τ² T1 se lo pregunta al 31B.
2. ~~Solo si el 26B le gana al miembro E4B: M3, la prueba real de streaming de §5, en la máquina del usuario. Necesita
   la aprobación del usuario: unos 45–60 minutos de la máquina, que cubren descargar un GGUF de 4 bits de ~15 GB,
   cronometrar decode y prefill sobre los prompts de nuestras caminatas, y medir el ancho de banda real del SSD.~~ No se
   llegó, y no se pidió: su condición nunca se cumplió. M3 volvería solo si un modelo más grande muestra valor primero.
3. ~~H1b (adaptador solo de atención) solo después de M3, porque no agrega nada si la base no puede servirse lo
   bastante rápido.~~ Igual: está detrás de M3, así que también descansa.
