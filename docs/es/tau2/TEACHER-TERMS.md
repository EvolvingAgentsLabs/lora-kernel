# Términos del maestro: qué modelos pueden generar salidas para entrenar un adaptador publicado

**La decisión que esto informa.** Planeamos publicar adaptadores abiertos chicos (QLoRA sobre Gemma 4), entrenados por
destilación, SFT o RL sobre trayectorias de τ²-bench airline que genera un "maestro". Este documento lista qué
términos de maestros permiten usar sus salidas de esa manera. No elige uno. Decide el usuario.

**Cómo se leyó.** Cada fuente de abajo se leyó el **2026-10-05**. Una afirmación marcada **[read]** viene de la URL que
tiene al lado. **[inferred]** marca mi propia aritmética o lectura, como las estimaciones de VRAM o lo que implica una
cláusula. **[not read]** marca una fuente que no abrí, como los términos de API de un proveedor. Esto es una lectura de
términos públicos, no asesoramiento legal. Donde una cláusula es ambigua, este documento lo dice y la deja sin resolver.

**Las cláusulas citadas se dejan en su inglés original**, porque son el texto del proveedor y una traducción mía no
tiene valor legal; cada cita lleva una *glosa* en español que dice qué significa, no una traducción literal.

Notas de recuperación: openai.com y x.ai devuelven HTTP 403 a las descargas directas, así que esas páginas se leyeron a
través de un proxy de renderizado de texto (`r.jina.ai/<url>`). Las citas son el texto propio de los proveedores, pero
las páginas no se leyeron directamente. Los archivos de licencia de Hugging Face se descargaron del
`resolve/main/LICENSE` de cada repositorio.

---

## 0. Dos hechos que cambian la pregunta

1. **El simulador de usuario también escribe en las trayectorias.** τ²-bench corre un LLM como *usuario* además del
   agente. El ejemplo del README es
   `tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1`
   [read, https://github.com/sierra-research/tau2-bench README]. Los turnos del usuario terminan en los datos de
   entrenamiento, aun cuando se enmascaren de la pérdida. Así que los términos del modelo simulador de usuario importan
   tanto como los del maestro.
   [inferred] La configuración limpia usa un simulador de usuario con términos tan permisivos como los del maestro.
2. **Dónde se llama a un modelo decide qué términos aplican, no qué modelo es.** Los mismos pesos de Gemma 4 son
   Apache 2.0 si se autoalojan. Llamados por la API de Gemini, caen bajo los términos de la API de Gemini y su cláusula
   anticompetencia (ver §1.3). Por OpenRouter, el usuario además debe cumplir los "Model Terms" de cada modelo
   [read, https://openrouter.ai/terms, "Last Updated: August 31, 2026"; también
   prohíbe usar el servicio para "reselling API access to Models or otherwise
   developing a competing service"]. [inferred] Para pesos abiertos, **autoalojar es la única ruta donde la licencia del
   modelo es toda la historia.**

---

## 1. APIs de frontera

### 1.1 Anthropic (API de Claude)

- **Commercial Terms, D.4**, vigentes desde el 17 de junio de 2025
  [read, https://www.anthropic.com/legal/commercial-terms]:
  > "Customer may not and must not attempt to (a) access the Services to build a
  > competing product or service, including to train competing AI models or resell
  > the Services except as expressly approved by Anthropic; (b) reverse engineer or
  > duplicate the Services; …"

  *(Glosa: el cliente no puede usar los Servicios para construir un producto competidor, incluido entrenar modelos de IA
  competidores, salvo aprobación expresa de Anthropic, ni hacer ingeniería inversa o duplicar los Servicios.)*
- **Usage Policy**, vigente desde el 15 de septiembre de 2025, bajo "Do Not Abuse our Platform"
  [read, https://www.anthropic.com/legal/aup]:
  > "Utilization of inputs and outputs to train an AI model (e.g., "model scraping"
  > or "model distillation") without prior authorization from Anthropic"

  *(Glosa: está prohibido usar entradas y salidas para entrenar un modelo de IA —por ejemplo "model scraping" o "model
  distillation"— sin autorización previa de Anthropic.)*
- Propiedad: "Customer (a) retains all rights to its Inputs, and (b) owns its
  Outputs" [read, commercial-terms §B] *(el cliente conserva sus entradas y es dueño de sus salidas)*.
- (a) Entrenar otro modelo: **no**, salvo que Anthropic dé autorización previa. La cláusula de la Usage Policy no tiene
  calificativo "competidor", así que cualquier entrenamiento queda cubierto.
  (b) Ser dueño de las salidas no anula la restricción de uso. (c) Publicar el adaptador: no, sin autorización.
  (d) Llamada a herramientas: sí. Precios por MTok, entrada/salida:
  Opus 5.5 \$4/\$20, Sonnet 5.5 \$2/\$10, Haiku 4.5 \$1/\$5; la Batch API los reduce a la mitad
  [read, https://platform.claude.com/docs/en/about-claude/pricing].

### 1.2 OpenAI (API)

- **Services Agreement §3.3(e)**, vigente desde el 1 de enero de 2026
  [read vía proxy, https://openai.com/policies/services-agreement/]:
  > "Customer will not, and will not permit End Users to: … (e) except for a
  > Permitted Exception, use Output to develop artificial intelligence models that
  > compete with OpenAI's products and services;"

  > "'Permitted Exception' means Customer using Output to: (a) develop artificial
  > intelligence models primarily intended to categorize, classify, or organize data
  > (e.g., embeddings or classifiers), if these models are not distributed or made
  > commercially available to third parties; and (b) fine tune or customize models
  > provided as part of OpenAI's fine-tuning or other Services …"

  *(Glosa: el cliente no usará la Salida para desarrollar modelos de IA que compitan con los productos y servicios de
  OpenAI, salvo una "Excepción Permitida": (a) modelos pensados sobre todo para categorizar, clasificar u organizar datos
  —embeddings o clasificadores— si no se distribuyen ni se ponen a disposición comercial de terceros; y (b) afinar o
  personalizar modelos que sean parte del fine-tuning u otros Servicios de OpenAI.)*
- **Terms of Use** (consumidores), vigentes desde el 1 de enero de 2026, prohíben: "Use Output to
  develop models that compete with OpenAI." [read vía proxy,
  https://openai.com/policies/row-terms-of-use/] *(usar la Salida para desarrollar modelos que compitan con OpenAI)*
- Propiedad: "you … own the Output" [read, row-terms-of-use] *(usted es dueño de la Salida)*.
- (a) **Ambiguo.** Entrenar está permitido a menos que el modelo "compete[s] with OpenAI's
  products and services", y el acuerdo no define "compete". Un adaptador general publicado de atención al cliente con
  llamadas a herramientas podría leerse razonablemente como competidor. Ninguna de las dos Excepciones Permitidas cubre
  nuestro caso: (a) es para clasificadores/embeddings que *no se distribuyen*, y (b) es el fine-tuning propio de OpenAI.
  (c) Publicar abiertamente es ambiguo, con inclinación a no. (d) Llamada a herramientas: sí.
  Precios aproximados por MTok vía OpenRouter: gpt-5.5 \$5/\$30, gpt-5.4 \$2.50/\$15,
  gpt-5.6-sol \$2/\$10 [read, https://openrouter.ai/api/v1/models; la página de precios propia de OpenAI
  no se leyó].

### 1.3 Google (API de Gemini)

- **Gemini API Additional Terms**. La página muestra "Last modified March 23, 2026" y
  el pie dice "Last updated 2026-04-28 UTC"
  [read, https://ai.google.dev/gemini-api/terms]:
  > "You may not use the Services to develop models that compete with the Services
  > (e.g., Gemini API or Google AI Studio). You also may not attempt to reverse
  > engineer, extract or replicate any component of the Services, including the
  > underlying data or models (e.g., parameter weights)."

  *(Glosa: no se pueden usar los Servicios para desarrollar modelos que compitan con ellos, ni intentar hacer ingeniería
  inversa, extraer o replicar ningún componente de los Servicios, incluidos los datos o modelos subyacentes, por
  ejemplo los pesos.)*
- Propiedad: "Google won't claim ownership over that content." [read, misma página] *(Google no reclamará la propiedad
  de ese contenido)*
- (a) **Ambiguo.** Tiene la misma forma de "compete" que OpenAI y ninguna definición.
  "Extract or replicate any component … including the underlying … models" también podría leerse como cubriendo la
  destilación. (c) Ambiguo, con inclinación a no. (d) Llamada a herramientas: sí.
  Gemini 3.8 Flash cuesta \$0.75/\$3.75 por MTok hasta 2026-12-31 y \$1.50/\$7.50
  después; Gemini 3.1 Pro Preview cuesta \$2/\$12
  [read, https://ai.google.dev/gemini-api/docs/pricing, actualizada 2026-10-01].
  **Gemma 4 figura ahí sólo en el nivel gratuito.** [inferred] Si Gemma 4 corre por la API de Gemini, esta cláusula le
  aplica. Autoalojarlo lo evita.

### 1.4 xAI (API de Grok)

- **Terms of Service — Enterprise, §3.2 "Rights in Input and Output"**. La página no
  muestra fecha de vigencia, y la parte ahora es "SpaceXAI LLC"
  [read vía proxy, https://x.ai/legal/terms-of-service-enterprise]:
  > "Customer will not, and will not permit any third party to: (i) use any Output to
  > train any foundation models, large language models, or other artificial
  > intelligence systems except as may be expressly permitted in an Order Form; …"

  *(Glosa: el cliente no usará ninguna Salida para entrenar modelos de fundación, modelos de lenguaje grandes ni otros
  sistemas de inteligencia artificial, salvo que un Order Form lo permita expresamente.)*
- Propiedad: el cliente "owns all right, title, and interest in the Output in
  perpetuity" [read, misma página] *(es dueño de todo derecho sobre la Salida a perpetuidad)*.
- (a) **No**, salvo que un Order Form lo permita. La cláusula no tiene calificativo de competencia. (c) No. (d) Llamada a
  herramientas: sí. Grok 4.7 cuesta alrededor de \$2/\$6 por MTok vía
  OpenRouter [read, API de modelos de openrouter].

### 1.5 Mistral (API / Studio)

- **Commercial Terms of Service**, vigentes desde el 25 de septiembre de 2026
  [read, https://legal.mistral.ai/terms/commercial-terms-of-service]:
  > "3.3. Output Restrictions. To the extent permitted by applicable law, Customer may
  > not use image Outputs to develop or train any image generation product that
  > competes with a Mistral AI Product."

  *(Glosa: en la medida que la ley lo permita, el cliente no puede usar Salidas de imagen para desarrollar o entrenar un
  producto de generación de imágenes que compita con un producto de Mistral AI.)*

  Restricciones (d)/(e) del mismo documento:
  > "(d) attempt to reverse engineer, decompile, or otherwise attempt to discover the
  > source code or underlying components (e.g., algorithms, weights, or systems) of
  > the Mistral AI Products, including using the Output or any modified version of the
  > Output to do any of the foregoing …; (e) use the Output or any modified version of
  > the Output to reverse engineer the Mistral AI Products;"

  *(Glosa: está prohibido intentar hacer ingeniería inversa, descompilar o descubrir el código fuente o los componentes
  subyacentes —algoritmos, pesos o sistemas— de los productos de Mistral AI, incluso usando la Salida o una versión
  modificada de ella, y usar la Salida para hacer ingeniería inversa de los productos de Mistral AI.)*
- Propiedad: "Customer … owns all Output." (§3.1) [read] *(el cliente es dueño de toda la Salida)*
- La Usage Policy, vigente desde el 11 de junio de 2026, no tiene cláusula de destilación ni de entrenamiento
  [read, https://legal.mistral.ai/terms/usage-policy; busqué "distill" y
  "train" y no encontré ninguna de las dos].
- (a) **Sí para salidas de texto, con una ambigüedad menor.** La única restricción explícita de entrenamiento cubre
  salidas de *imagen*. Es ambiguo si (d)/(e) ("discover … weights … using the Output") alcanzan a la destilación
  conductual. Leídas literalmente, apuntan a la ingeniería inversa, no a la imitación. (c) Probablemente publicable. (d)
  Llamada a herramientas: sí. Mistral Medium 3.5 cuesta alrededor de \$1.50/\$7.50 por MTok vía OpenRouter
  [read, API de modelos de openrouter].
- Los modelos Mistral de pesos abiertos se tratan en §2.7.

---

## 2. Modelos de pesos abiertos (autoalojados, así que sólo aplica la licencia)

### 2.1 Google Gemma 4 (la misma familia que nuestra base)

- Licencia: **Apache 2.0**. La tarjeta de HF de `google/gemma-4-31B-it` dice
  `license: apache-2.0` y enlaza a https://ai.google.dev/gemma/docs/gemma_4_license
  [read, https://huggingface.co/google/gemma-4-31B-it]. La página de la licencia es el texto de
  Apache 2.0 y se actualizó por última vez el 2026-04-01 [read,
  https://ai.google.dev/gemma/docs/gemma_4_license].
- Los viejos **Gemma Terms of Use** ahora dicen "For Gemma 4 terms, see the Gemma 4
  license" [read, https://ai.google.dev/gemma/terms, última modificación 1 de abril de 2026]
  *(para los términos de Gemma 4, ver la licencia de Gemma 4)*.
  Los términos viejos definían "Model Derivatives" para incluir cualquier modelo "created by transfer
  of patterns of the weights, parameters, operations, or Output of Gemma", lo que
  incluye explícitamente la destilación *(creado por transferencia de patrones de los pesos, parámetros, operaciones o
  Salida de Gemma)*. Esa definición regía Gemma 1–3 y **no rige
  Gemma 4** [read, misma página].
- **Ambigüedad:** la página de la licencia de Gemma 4 enlaza una política de "Prohibited use" y una
  "Intended use statement" en su navegación. No dice nada sobre si son
  vinculantes para Gemma 4 bajo Apache [read, página gemma_4_license]. La Prohibited
  Use Policy ("You may not use nor allow others to use Gemma or Model Derivatives
  to: …", última modificación 21 de febrero de 2024) no contiene ninguna cláusula sobre entrenar otros
  modelos [read, https://ai.google.dev/gemma/prohibited_use_policy].
- (a) **Sí.** Apache 2.0 no pone restricciones sobre las salidas. (b) Las obligaciones de aviso y
  atribución del §4 de Apache aplican si el adaptador se trata como Obra Derivada. Nuestro
  adaptador *ya es* un derivado de la base Gemma 4, así que el maestro no agrega ninguna obligación nueva.
  (c) **Sí**, bajo la misma licencia que la base. (d) Los tamaños son 31B
  denso, 26B-A4B MoE, 12B, E4B y E2B. Existen builds QAT oficiales q4_0 y w4a16
  [read, lista de modelos de HF para google/gemma-4-*]. [inferred] El 31B pesa unos 62 GB en
  bf16, así que entra en una GPU de 80 GB con una caché KV modesta. En 40 GB necesita el
  build QAT oficial de 4 bits (unos 17–20 GB). Llamada a herramientas nativa: sí [read, tarjeta].
  Por OpenRouter cuesta alrededor de \$0.09/\$0.34 por MTok, pero entonces aplican los términos de OpenRouter
  [read, API de modelos de openrouter].
- Nota de margen, de la tarjeta y no de nuestra medición: la tarjeta informa "Tau2
  (average over 3)" de **76,9 %** para el 31B, contra 68,2 % para el 26B-A4B y
  69,0 % para el 12B [read, README de gemma-4-31B-it]. El promedio no está definido en
  la tarjeta y la cifra es autoinformada. [inferred] La brecha entre maestro y
  alumno dentro de la familia es de unos 8 puntos en esa métrica. Ese es el
  efecto máximo disponible de un maestro de la misma familia, antes de cualquier medición nuestra.

### 2.2 OpenAI gpt-oss-120b (pesos abiertos)

- Licencia: **Apache 2.0** [read, etiqueta `license:apache-2.0` de la API de HF,
  https://huggingface.co/openai/gpt-oss-120b]. El archivo USAGE_POLICY dice completo:
  "We aim for our tools to be used safely, responsibly, and democratically, while
  maximizing your control over how you use them. By using OpenAI gpt-oss-120b, you
  agree to comply with all applicable law." [read,
  https://huggingface.co/openai/gpt-oss-120b/blob/main/USAGE_POLICY]
  *(Glosa: busca que sus herramientas se usen de forma segura, responsable y democrática, maximizando el control del
  usuario; al usar gpt-oss-120b, usted acepta cumplir con toda la ley aplicable.)*
- La cláusula "compete" del OpenAI Services Agreement rige *los Servicios*, es decir,
  la API. Los pesos de gpt-oss autoalojados no son los Servicios. [inferred]
- (a) **Sí.** (c) Sí, con aviso de Apache. (d) [inferred] Los pesos MXFP4 de unos
  63 GB entran en una GPU de 80 GB, pero no en 40 GB. Llamada a herramientas: sí. Cuesta alrededor de
  \$0.04/\$0.17 por MTok vía OpenRouter [read, API de modelos de openrouter].

### 2.3 DeepSeek (V4 / V4.1)

- Pesos: **MIT**. Ejemplos son `DeepSeek-V4-Pro-0813` (unos 1,65T de parámetros),
  `DeepSeek-V4.1-Flash` (unos 763B) y `DeepSeek-V4-Flash-0731` (unos 304B)
  [read, archivo LICENSE de HF y API de HF]. El README de V4-Pro dice "This repository and
  the model weights are licensed under the MIT License." [read]
- **Los términos de la API son explícitamente permisivos.** DeepSeek Open Platform Terms of
  Service, vigentes desde el 29 de abril de 2026
  [read, https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html]:
  > "You may apply the Inputs and Outputs of the Services to a wide range of use
  > cases, including personal use, academic research, derivative product
  > development, training other models (such as model distillation), etc."

  *(Glosa: se pueden aplicar las Entradas y Salidas de los Servicios a una amplia gama de usos, incluido el uso
  personal, la investigación académica, el desarrollo de productos derivados y el entrenamiento de otros modelos —como
  la destilación—, etc.)*
- (a) **Sí, tanto autoalojado como por la API.** Esta es la única API que nombra la destilación como permitida. (c) Sí.
  (d) Ninguno de estos entra en 40/80 GB [inferred].
  La API soporta "Tool Calls". deepseek-flash cuesta \$0.15–0.30 de entrada y
  \$0.60–1.20 de salida por MTok, y deepseek-v4-pro cuesta \$0.66–1.32 y \$1.98–3.96,
  en tarifas valle/pico [read, https://api-docs.deepseek.com/quick_start/pricing].
  Nota: usar la API implica aceptar el manejo de datos de DeepSeek y las disposiciones de la ley china en los mismos
  términos (no analizadas acá).

### 2.4 Qwen (Qwen3.8)

- **Qwen3.8-27B: Apache 2.0** [read, tarjeta de HF `license: apache-2.0`,
  https://huggingface.co/Qwen/Qwen3.8-27B].
- **Qwen3.8-2.4T-A95B: "Qwen3.8-Max License"** [read,
  https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B/blob/main/LICENSE]. Es del estilo MIT,
  con dos condiciones:
  > "If the Software (or any derivative works thereof) is Used for any of the
  > licensee's commercial products or services that have more than 100,000,000
  > monthly active users or US\$ 20,000,000 … monthly revenue, respective model name
  > must be prominently displayed …"

  *(Glosa: si el Software —o cualquier obra derivada— se usa en productos o servicios comerciales del licenciatario con
  más de 100.000.000 de usuarios activos mensuales o US\$ 20.000.000 de ingresos mensuales, debe mostrarse de forma
  destacada el nombre del modelo.)*

  > "If the licensee or any of its affiliates conducts a Model as a Service or AI
  > Work Assistant business, and the aggregate revenue … exceeds US\$50,000,000 …,
  > the licensee shall obtain a separate license from Qwen …"

  *(Glosa: si el licenciatario o sus afiliadas operan un negocio de Modelo como Servicio o de Asistente de Trabajo de IA
  y el ingreso agregado supera US\$50.000.000, debe obtener una licencia aparte de Qwen.)*
- **Qwen3.8-Flash-Next (unos 180B): "Qwen Community License 1.0"** [read,
  LICENSE de HF]. Es el mismo texto, salvo que la condición de MaaS/Asistente de Trabajo de IA no tiene
  **ningún umbral de ingresos**: "If the licensee … conducts a Model as a Service or AI
  Work Assistant business, the licensee shall obtain a separate license" *(si el licenciatario opera un negocio de
  Modelo como Servicio o de Asistente de Trabajo de IA, debe obtener una licencia aparte)*.
- Nada en estas licencias menciona salidas ni destilación. **Ambiguo:** no
  definen "derivative works", así que no está claro si un modelo entrenado con
  salidas cuenta como uno. Si cuenta, las condiciones viajan con el adaptador hacia
  cualquiera que lo use comercialmente. Para Flash-Next, eso incluye a cualquier operador de MaaS
  de cualquier tamaño. [inferred]
- (a) 27B: sí. 2.4T y Flash-Next: probablemente sí, ambiguo en el límite de la obra
  derivada. (c) 27B: sí. Los otros son publicables, pero pueden adjuntarse condiciones aguas abajo. (d) [inferred] El 27B pesa unos 56 GB en bf16 y entra en 80 GB, o en 40 GB a 8/4 bits.
  El 2.4T necesita una API. Precios en OpenRouter: qwen3.8-27b \$0.42/\$2.55, 2.4T \$2/\$6
  [read, API de modelos de openrouter]. Los términos propios de la API de Alibaba (Qwen Cloud) [not read].

### 2.5 Meta Llama 4

- **Llama 4 Community License**, fecha de versión 5 de abril de 2025, §1.b.i
  [read, https://dev.meta.ai/llama/llama4/license/]:
  > "If you use the Llama Materials or any outputs or results of the Llama Materials
  > to create, train, fine tune, or otherwise improve an AI model, which is
  > distributed or made available, you shall also include "Llama" at the beginning
  > of any such AI model name."

  *(Glosa: si se usan los Llama Materials o cualquier salida o resultado de ellos para crear, entrenar, afinar o de otro
  modo mejorar un modelo de IA que se distribuye o se pone a disposición, hay que incluir "Llama" al principio del
  nombre de ese modelo.)*

  La misma sección exige "Built with Llama" al redistribuir Llama
  Materials o derivados. El §1.b.iv incorpora la Acceptable Use Policy "by
  reference". El §2 aplica un umbral de 700M de MAU [read].
- (a) **Sí, con condiciones.** Se contempla explícitamente entrenar con salidas.
  (b) Un adaptador publicado tendría que llamarse "Llama-…", lo que choca con la identidad de un
  adaptador basado en Gemma, y la AUP de Llama obliga en el uso. (c) Publicable, pero
  sólo bajo la condición del nombre. (d) Maverick es 17B activos/128 expertos, unos
  400B en total, así que necesita una API [inferred]. Cuesta alrededor de \$0.19/\$0.65 vía
  OpenRouter [read]. [inferred] Es más débil que las alternativas de 2026 como maestro.

### 2.6 GLM (Z.AI), Kimi (Moonshot), MiniMax

- **GLM-5.3-Flash (unos 321B): MIT** [read, LICENSE de HF,
  https://huggingface.co/zai-org/GLM-5.3-Flash]. **GLM-5.3 (unos 753B): "GLM-5.3
  License"** [read, LICENSE de HF]. Es del estilo MIT. Su única condición es una revisión de seguridad
  para operadores de MaaS con más de **US\$10 mil millones** de ingresos en 12 meses.
  Nada sobre salidas. La misma ambigüedad de "derivative works" que Qwen. En la práctica esa
  condición nunca puede obligarnos. Sólo API en estos tamaños [inferred]. OpenRouter:
  glm-5.3-flash \$0.15/\$0.50 [read].
- **Kimi K3 (unos 2,8T): "Kimi K3 License"** [read,
  https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE]. Los negocios de MaaS
  de más de US\$20M de ingresos necesitan un acuerdo aparte. Los productos con más de 100M de MAU o US\$20M
  de ingresos mensuales deben mostrar "Kimi K3". Ambas condiciones se levantan para uso
  interno. **Kimi K2.6** es "Modified MIT" con sólo la condición de mostrar el nombre [read,
  página LICENSE de HF]. Nada sobre salidas. "Derivative works" es ambiguo de la misma
  manera. OpenRouter: kimi-k3 \$1.39/\$14 [read].
- **MiniMax-M3 (unos 427B): "MiniMax Community License"** [read,
  https://huggingface.co/MiniMaxAI/MiniMax-M3/blob/main/LICENSE]. La concesión es
  "to deal in the Software **for non-commercial purposes**" *(para tratar con el Software con fines no comerciales)*.
  El uso comercial del Software "or any derivative work thereof" *(o de cualquier obra derivada)* exige mostrar "Built with MiniMax
  M3" más un aviso o autorización a MiniMax. El apéndice lista usos prohibidos,
  incluido "any military purpose". **Ambiguo, y más restrictivo:** si un
  adaptador entrenado con salidas cuenta como obra derivada, sus usuarios comerciales
  aguas abajo heredan estas condiciones, y nuestra licencia abierta chocaría con ellas.
  OpenRouter: \$0.30/\$1.20 [read].

### 2.7 Pesos abiertos de Mistral

- **Mistral-Small-4-119B-2603: Apache 2.0** [read, etiqueta de la API de HF]. **Mistral-Large-3-675B:
  Apache 2.0** [read, etiqueta de la API de HF].
- **Mistral-Medium-3.5-128B: "Modified MIT"** [read, LICENSE de HF]:
  > "You are not authorized to exercise any rights under this license if the global
  > consolidated monthly revenue of your company (or that of your employer) exceeds
  > \$20 million … This restriction … applies to the Model and any derivatives,
  > modifications, or combined works based on it …"

  *(Glosa: no se está autorizado a ejercer ningún derecho bajo esta licencia si el ingreso mensual global consolidado de
  la empresa —o de su empleador— supera \$20 millones; la restricción aplica al Modelo y a cualquier derivado,
  modificación u obra combinada basada en él.)*

  Si un adaptador entrenado con salidas es un "derivative … based on it" es **ambiguo**.
- (d) [inferred] Small-4-119B necesita unos 120 GB en FP8. El build NVFP4 oficial
  (unos 60–65 GB) entra en 80 GB pero necesita hardware con FP4 (Blackwell). Una A100
  no tiene FP4 nativo. No entra en 40 GB.

---

## 3. La licencia propia de τ²-bench y sus datos de tareas

- Licencia del repositorio: **MIT**, "Copyright (c) 2025 Sierra Research". El archivo LICENSE
  y `pyproject.toml` dicen ambos `license = "MIT"` [read,
  https://github.com/sierra-research/tau2-bench, LICENSE y pyproject.toml].
- Los datos de las tareas viven *dentro* de ese repositorio (`data/tau2/domains/airline/`: `tasks.json`,
  `split_tasks.json`, `policy.md`, `db.json`). No se encontró una licencia de datos aparte en
  el repositorio, y el README no declara ninguna [read, API de contenidos de GitHub]. [inferred] La licencia
  MIT del repositorio cubre entonces los datos de las tareas. No está dicho
  explícitamente para los datos.
- El dominio airline viene del τ-bench original, que también es **MIT**
  [read, https://github.com/sierra-research/tau-bench].
- Partición de airline: **train 30, test 20, base 50** [read, `split_tasks.json`]. El README
  dice: "If you are evaluating an agent (not training), use the `base` task split …
  This is the default." [read] *(si se evalúa un agente, no se entrena, usar la partición `base`; es la predeterminada)*. [inferred] `base` = train ∪ test. Todo
  número publicado sobre `base` o en el leaderboard incluye entonces las 30 tareas con las que se entrenaron
  los adaptadores. Los adaptadores publicados deben reportar **sólo test (20)**, o decir por qué no.
- [inferred, ambiguo] El repositorio también contiene `data/tau2/results/` y
  `data/tau2/user_simulator/` [read, listado de contenidos]. Las trayectorias que otros
  generaron con modelos cerrados (corridas del leaderboard) son MIT en el repositorio. Los
  términos de salida del proveedor que las generó obligan a quien las corrió, no a nosotros. Si
  entrenar con *esas* es limpio queda sin resolver, y este documento no lo resuelve.

---

## 4. Tabla resumen

| Modelo (ruta) | Las salidas pueden entrenar un modelo **publicado** | Cláusula clave | Llamada a herramientas | Costo / servido |
|---|---|---|---|---|
| Claude (API de Anthropic) | **No** (sin autorización previa) | AUP: "Utilization of inputs and outputs to train an AI model … without prior authorization"; CTOS D.4 | sí | Sonnet 5.5 \$2/\$10; Opus 5.5 \$4/\$20 por MTok |
| GPT-5.x (API de OpenAI) | **Ambiguo → inclinado a no** | SA §3.3(e) "use Output to develop artificial intelligence models that compete"; las excepciones no encajan | sí | gpt-5.6-sol ~\$2/\$10; gpt-5.5 ~\$5/\$30 |
| Gemini (API de Gemini) | **Ambiguo → inclinado a no** | "may not use the Services to develop models that compete with the Services" | sí | 3.8 Flash \$0.75/\$3.75 (hasta 2026-12-31) |
| Grok (API de xAI) | **No** (salvo Order Form) | Ent. ToS §3.2 "use any Output to train any … artificial intelligence systems" | sí | ~\$2/\$6 |
| Mistral (API) | **Sí** (texto); ambigüedad menor en (d)/(e) | sólo se restringe entrenar con salidas de imagen (§3.3) | sí | Medium 3.5 ~\$1.5/\$7.5 |
| **Gemma 4 31B (autoalojado)** | **Sí** | Apache 2.0; los viejos términos de "Model Derivatives" no rigen Gemma 4 | sí (nativa) | 80 GB bf16 / 40 GB QAT de 4 bits; ~\$0.09/\$0.34 alojado |
| **gpt-oss-120b (autoalojado)** | **Sí** | Apache 2.0; la política de uso = "comply with all applicable law" | sí | 80 GB (MXFP4), no 40 GB; ~\$0.04/\$0.17 alojado |
| **DeepSeek V4 / V4.1 (API o pesos)** | **Sí (explícito)** | ToS de la API: "training other models (such as model distillation)"; pesos MIT | sí | sólo API en estos tamaños; flash \$0.15–0.30/\$0.60–1.20 |
| Qwen3.8-27B (autoalojado) | **Sí** | Apache 2.0 | sí | 80 GB bf16 / 40 GB cuantizado; ~\$0.42/\$2.55 alojado |
| Qwen3.8-2.4T / Flash-Next | Sí, **ambiguo** en "derivative works" | condición de licencia de MaaS/Asistente de Trabajo de IA (Flash-Next: sin umbral) | sí | API; 2.4T ~\$2/\$6 |
| GLM-5.3-Flash / GLM-5.3 | Sí / sí (derivado ambiguo; sólo la condición de MaaS >\$10B) | MIT / GLM-5.3 License | sí | API; flash ~\$0.15/\$0.50 |
| Kimi K3 / K2.6 | Sí, **ambiguo** en "derivative works" | MaaS >\$20M + condiciones de mostrar el nombre | sí | API; K3 ~\$1.39/\$14 |
| MiniMax-M3 | **Ambiguo** (concesión no comercial; condiciones sobre derivados) | "for non-commercial purposes"; "Built with MiniMax M3" | sí | API; ~\$0.30/\$1.20 |
| Llama 4 Maverick | Sí, **con condición de nombre** | "include "Llama" at the beginning of any such AI model name" | sí | API; ~\$0.19/\$0.65 |
| Mistral-Small-4-119B (autoalojado) | **Sí** | Apache 2.0 | sí | 80 GB sólo con NVFP4 (Blackwell); no A100/40 GB |

Los precios son USD por millón de tokens, entrada/salida. Salvo que la fila cite la página propia del
proveedor, vienen de la API pública de modelos de OpenRouter del 2026-10-05
y dependen del proveedor. Llamar a un modelo por OpenRouter suma los términos de OpenRouter
y los términos del modelo de origen.

---

## 5. Las opciones más limpias para publicar (no es una decisión)

Se listan en el orden en que los términos las hacen limpias, no por calidad esperada.
Elige el usuario.

1. **Gemma 4 31B, autoalojado, como maestro y como simulador de usuario.** La licencia
   del maestro es la misma Apache 2.0 que la de la base, así que la procedencia del adaptador es una sola
   licencia de punta a punta. Entra en la A100-80GB en bf16, o en 40 GB con el build QAT oficial
   de 4 bits. La cifra de τ² de la propia tarjeta da una brecha disponible de unos 8 puntos
   sobre el 26B/12B. Ese techo es chico, y es lo primero que hay que medir
   (margen antes del tratamiento). No llamarlo por la API de Gemini, porque eso
   suma el §1.3.
2. **gpt-oss-120b, autoalojado.** Apache 2.0, una política de uso de una línea, y entra en
   una sola GPU de 80 GB. Es de una familia distinta a la del alumno, así que trae un
   comportamiento distinto, que puede ayudar o perjudicar. No entra en el nivel de 40 GB.
3. **DeepSeek V4/V4.1 por la API de DeepSeek.** Es la única *API* cuyos términos
   nombran la destilación como permitida, y es barata. Los costos: los datos van a un
   proveedor bajo términos de ley china (no analizados acá), y el modelo no se puede autoalojar en nuestro hardware.

No se recomiendan para un adaptador publicado sin un acuerdo aparte: Claude y
Grok (prohibiciones explícitas). Tampoco se recomiendan GPT y Gemini (una cláusula
"compete" sin definir). MiniMax-M3 y Llama 4 traen condiciones que viajarían con el adaptador
o lo renombrarían. Qwen3.8-27B (Apache 2.0) es tan limpio como la opción 2 en términos.
Quedó fuera del top tres sólo porque 1–3 ya cubren las rutas de la misma familia,
de una sola GPU y de API.

Sea cual sea el maestro, el modelo simulador de usuario debe estar bajo términos igual de limpios
(§0.1). La tarjeta del adaptador también debe reportar τ² airline **test (20)**, no `base`
(§3).

---

**Decisión del usuario, 2026-10-05 (después de esta tabla):** el maestro y el simulador de usuario son **Gemma 4 31B,
autoalojado** (la opción 1 de §5); la línea del 26B se cierra (`results/TAU2-T0-recon-20261005/BRIEF.md`).
