# El stack, exacto

Cada id de modelo, cada hiperparámetro de adaptador, cada flag de vLLM, con la
corrida que lo estableció. **Esta página es un inventario, no una explicación** — los
mecanismos viven en [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`TECHNICAL-REFERENCE.md`](TECHNICAL-REFERENCE.md) y [`SERVING.md`](SERVING.md).

Los valores se leen del código y de los artefactos, no de la memoria. Donde un número
es una medición está marcado **[ran]** con su directorio de corrida.

---

## 1. La base

| | |
|---|---|
| **modelo** | `Qwen/Qwen2.5-3B-Instruct` |
| vocabulario | **151.643** tokens + 22 agregados = 151.665 ids |
| columnas de embedding | 151.936 — **más anchas que el vocabulario**, así que una máscara sobre las columnas extra no enmascara nada |
| dtype servido | `bfloat16` |
| dtype entrenado | `bfloat16` en Ampere o posterior; `float16` en Turing |

**Está resuelta por medición, no por preferencia.** P33 la leyó contra un control:
vLLM 0.29.0 carga un LoRA sobre `Qwen3.5-4B`, loguea `Loaded new LoRA adapter` y
**sirve la base igual** **[ran]** — la compuerta de identidad C18. Gemma 4 no es una
base peft (`Gemma4ClippableLinear` no es `nn.Linear`). Correr
`serve_openai --gate-only` contra cualquier candidata antes de proponerla.
**D2 [ran] 2026-09-19 corrigió la lectura de C18:** son los nombres de los tensores del
adaptador, no el stack de serving — renombrado a `language_model.`, el mismo adaptador de
Qwen3.5 da `applied`. Qwen 2.5 se queda porque los miembros liberados están entrenados sobre él.

**bf16 se chequea, no se asume.** `torch.cuda.is_bf16_supported()` devuelve `True` en
una T4 porque cuenta *emulación*, y la bf16 emulada no tiene kernel — toda generación
muere. El chequeo es capacidad de cómputo ≥ 8.0 **[ran]** 2026-09-08.

## 2. Los dos targets, que son trabajos distintos

| trabajo | modelo | por qué éste |
|---|---|---|
| **fallback** — contesta lo que el pool falla, medido | `google/gemini-3.8-flash` | **66/90** en la suite de fluidos por el mismo cliente que usa el experto local **[ran]** P41 |
| **target especulativo** — verifica tokens drafteados | `Qwen/Qwen2.5-32B-Instruct` | **`tokenizer.json` byte-idéntico** al de la base, `c0382117ea329cdf…` **[ran]** P48 |

### Compatibilidad de tokenizers, medida **[ran]** `results/P48-tokenizer-compat-20260916/`

| target candidato | vocab | ids coinciden | ¿sirve como target especulativo? |
|---|---:|---|---|
| `Qwen2.5-7B / 14B / 32B / 72B-Instruct` | 151.643 | sí | **sí — archivo byte-idéntico** |
| `Qwen3-14B`, `Qwen3-32B` | 151.643 | sí | sí, con 4 ids que sólo el target tiene (151665-151668: `<tool_response>`, `</tool_response>`, `<think>`, `</think>`) — **una mejora disponible, no adoptada**; ver [`analysis/qwen3-migration.md`](../analysis/qwen3-migration.md) |
| `Qwen3.5-27B`, `Qwen3.6-27B`, `Qwen3.8-27B` **con el drafter Qwen 2.5** | **248.044** | **no** | **no — otro vocabulario; los drafters 2.5 no llegan** |
| **`Qwen3.8-27B` con un drafter `Qwen3.5-2B / 4B` — el objetivo** | 248.044 | sí | **sí** — mapa idéntico, 7 ids sólo del target de audio/TTS, `<think>` compartido **[ran]** `results/P55-graded-ranking-20260916/D0-tokenizers.txt` |

Una API de frontera nunca puede ser target especulativo: no devuelve logprobs de una
continuación **forzada** (C2) y no comparte el tokenizer (C3). Chequear cualquier par
nuevo con `training/harness/tokenizer_compat.py` antes de servirlo.

## 3. Los adaptadores

Todos son **LoRA sobre la misma base**, hiperparámetros idénticos, difiriendo sólo en
el corpus. Cada uno pesa **119.801.528 bytes** de `adapter_model.safetensors` — unos
114 MiB, contra ~6 GB de pesos de la base.

| adaptador | corpus | filas | banda | superficie | qué puntúa |
|---|---|---:|---|---|---|
| `email-full` — **liberado como `email-full@v1`** | `training/harness/data_ef/train.jsonl` | 598 | 0-3 pasos | `thread_history`, `sender_stats`, `message` | en modo corpus **471/475 = 0,992**, humanos **347/351 = 0,989**, reproducido en tres sesiones; un reentrenamiento del mismo corpus empata 1 : 0 **[ran]** P55 A, P57. Vía `tool_calls`: 0,808, humanos 0,741 contra barra 0,655, p 0,00036 **[ran]** P43 |
| `fluids-full` | `training/physics/data_ff/train.jsonl` | 600 | 6-9 pasos | `calc`, `lookup`, `convert` | **11/90 = 0,122** contra 0,733 de la frontera **[ran]** P41; bajo su banda sobre-resuelve **18 de 18** **[ran]** P45 |
| `kernel-mt` | `training/harness/data_mt/train.jsonl` | 600 | 2-4 pasos | `calc`, `convert`, `lookup` | el protocolo sin el dominio |
| `kernel-email` | `training/harness/data_ep/train.jsonl` | 600 | 1-1 pasos | `thread_history`, `sender_stats`, `message` | el mismo protocolo en el vocabulario del email |
| `domain-mt` | `training/physics/data_mt/train.jsonl` | 600 | **0-0 pasos** | **ninguna** — no llama nada | la física con el protocolo sacado — no llama nada, por diseño |

**Las bandas y las superficies se leen de los corpus, no se declaran** —
`tests/test_contract.py` y `tests/test_prune.py` releen cada uno, y hacerlo cazó tres
de cinco bandas mal en el primer intento **[ran]**, y después el *orden* de la
superficie mal en todos los corpus que enseñan uno **[ran]** 2026-09-16. Declaradas en
`POOL` vía `training/harness/contract.py`.

**El orden de una superficie es parte de ella, donde el corpus enseña uno.** Los tres
corpus que llevan bloque de herramientas lo listan en un orden fijo en cada prompt, y
ninguno de esos órdenes es alfabético; renderizar una superficie podada ordenada le
mostraría al adaptador un listado que nunca leyó. Los dos corpus `-mt` no llevan
bloque, así que sus etiquetas se escriben alfabéticamente para decir que no se enseñó
ningún orden.

### Hiperparámetros LoRA — idénticos para todos

| | valor | nota |
|---|---|---|
| `r` | **16** | y `--max-lora-rank 16` al servir tiene que cubrirlo |
| `lora_alpha` | **32** | |
| `lora_dropout` | 0,05 | |
| `bias` | `none` | |
| `task_type` | `CAUSAL_LM` | |
| `target_modules` | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` | **las siete proyecciones** |
| `modules_to_save` | `null` | **sin redimensionar embeddings** — que es lo que hace posibles los valores de un token único de un head tipado |
| peft | 0.20.0 | registrado en cada `adapter_config.json` |

### La corrida de entrenamiento

| | valor |
|---|---|
| trainer | `trl.SFTTrainer` / `SFTConfig` |
| épocas | 3 |
| learning rate | 2e-4 |
| batch × acumulación | 2 × 8 = efectivo 16 |
| largo máximo de secuencia | 1536, **`packing=False`** — empaquetar rellena cada secuencia hasta el máximo y devuelve el presupuesto de tokens |
| gradient checkpointing | prendido al entrenar, **apagado antes de generar** — desactiva el KV cache |
| semilla | 0 |
| 4-bit | opcional `--four-bit`: nf4, doble cuantización, dtype de cómputo = la decisión bf16/fp16 de arriba |

## 4. vLLM

**Versión 0.29.0** **[ran]** — registrada en el `vllm.log` de cada corrida.

```
vllm serve Qwen/Qwen2.5-3B-Instruct \
    --dtype bfloat16 \
    --enable-lora \
    --max-lora-rank 16 \
    --max-loras <N> \
    --lora-modules nombre=ruta [nombre=ruta ...]
```

| flag | por qué |
|---|---|
| `--dtype bfloat16` | el camino fp16 produjo todos los ceros falsos de S4 |
| `--max-lora-rank 16` | tiene que ser ≥ al `r` más grande servido, incluido el de un tercero |
| `--max-loras N` | cuántos pueden estar **activos a la vez** |
| `--lora-modules nombre=ruta` | el nombre es lo que selecciona el campo `model` de un request HTTP |

vLLM escucha en **:8000**; `training/harness/openai_proxy.py` está en **:8001** y es
con quien habla todo cliente — agrega la superficie de herramientas, serializa
tag ↔ `tool_calls`, y anuncia rutas como **formas, nunca contenido**.

> **`--max-loras` sólo fue 1 o 2 en este repositorio.** El pool más grande servido es
> `['email-full', 'fluids-full']` **[ran]** P41. S-LoRA reporta miles en una máquina
> **[read]**; lo nuestro no se probó arriba de dos, y es el primer riesgo real de
> cualquier diseño que necesite muchos.

### Hardware

| placa | qué sostiene | usada para |
|---|---|---|
| **L4** (24 GB) | el 3B más uno o dos adaptadores rank-16 | todas las corridas de serving hasta ahora |
| **A100** (40 GB) | lo mismo, con lugar para un target grande al lado | P3, P33, y lo que va a necesitar P4 |
| esta laptop | **nada** — arm64, 16 GB, vLLM no corre (C4) | escribir y analizar solamente |

## 5. Qué se rechaza, y con qué

| rechazo | dónde | por qué |
|---|---|---|
| un adaptador `.bin` | `third_party.py` | es un pickle — ejecuta código al cargar |
| una base que no coincide | `third_party.py` | un adaptador de otra base no es miembro del pool |
| un adaptador que carga y no se aplica | la compuerta **C18** en cada runner | vLLM loguea éxito y sirve la base |
| un pool cuyos miembros no difieren entre sí | `pool_run.py` | dos nombres sobre un adaptador es un experto |
| un miembro tipado sin ids de token único verificados | `contract.py` | un contrato tipado cuyos valores no son un token es un contrato de texto con etiqueta |
| un miembro sin banda declarada | `contract.py` | P45: un adaptador servido fuera de su banda sobre-resuelve y nada en la salida lo dice |
| una credencial en la línea de comandos | `tests/` | queda en `ps` y en el historial del shell |

## 6. De dónde salió cada número

| afirmación | corrida |
|---|---|
| la base es la que vLLM sí aplica adaptadores | `results/P33-…` |
| un pool sirve, miembros distintos, entra el adaptador de un tercero | `results/P40-…`, `results/P42-third-party-20260915/` |
| `email-full` despeja su barra | `results/P43-openclaw-e2e-20260915/` |
| ruteo por región 0,546 → 0,775 | `results/P41-routing-20260915/` |
| el piso de profundidad que enseña un corpus | `results/P45-ladder-sweep-20260915/` |
| el techo del ordenamiento | `results/P46-ranking-ceiling-20260916/` |
| compatibilidad de tokenizers | `results/P48-tokenizer-compat-20260916/` |
