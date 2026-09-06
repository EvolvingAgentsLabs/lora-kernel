# speculative-experts

**¿Puede un torneo entre expertos chicos elegir cuál tiene razón — gratis, en el
forward pass que iba a ocurrir de todos modos?**

*[Read this in English](README.md)*

> **Estado: nada construido, nada corrido.** Este repositorio existe para
> contestar una pregunta, y abre con la razón por la que esa pregunta todavía no
> está contestada: el mecanismo en el que se apoya la idea mide otra cosa.

## La idea, tal como llegó

Un modelo base servido una vez. Muchos adaptadores QLoRA — uno por experto.
Cuando llega un prompt, varios adaptadores borradorean en paralelo, todas las
ramas se verifican en un solo forward pass con tree attention, y **se emite la
rama con mayor tasa de aceptación**. El enrutamiento sale gratis. Todo agente
colapsa en un delta de pesos.

Es una arquitectura hermosa. Dos de sus tres patas se sostienen.

## La pata que no se sostiene, dicha primero

**La decodificación especulativa preserva la distribución de salida del modelo
target.** No es un efecto lateral: es la garantía entera — el muestreo por
rechazo está construido para que los tokens aceptados se distribuyan exactamente
como los habría emitido el target. **[read]**

Tres consecuencias, y son fatales para el enrutamiento por aceptación:

1. **El conocimiento del experto nunca llega a la salida.** Sepa lo que sepa el
   adaptador que borrada, los tokens emitidos son los del *target*. Un adaptador
   de dominio usado como drafter hace que la respuesta llegue antes. No hace que
   sea otra respuesta.
2. **La tasa de aceptación es una métrica de latencia.** Mide cuántas veces el
   drafter adivinó lo que el target iba a decir. La literatura que formaliza la
   selección de drafters ([Not-a-Bandit, arXiv:2510.20064](https://arxiv.org/abs/2510.20064))
   lo plantea como un problema de *no-regret* sobre **velocidad**, nunca sobre
   calidad. **[read]**
3. **Así que el torneo selecciona por parecido con la base**, que es lo contrario
   de lo que buscaba. Gana el adaptador que **menos** se alejó del modelo base:
   el menos especializado del grupo.

Y una corrección más ordinaria: el mecanismo **tampoco está disponible hoy**.
vLLM sirve muchos LoRA sobre un target, pero la decodificación especulativa
todavía pide un draft model entero por dominio. LoRA-como-drafter es un RFC
abierto el 2026-08-12 ([vllm#52038](https://github.com/vllm-project/vllm/issues/52038));
un intento anterior aplicaba el adaptador al target y lo **desactivaba en el
draft** ([vllm#11966](https://github.com/vllm-project/vllm/pull/11966)). **[read]**

## Lo que sobrevive, que es la parte interesante

| ruta | qué cuesta | qué compra |
|---|---|---|
| **Aceptar que es sin pérdida.** Muchos expertos sobre una base, especulados por velocidad | nada — esto shippea hoy, salvo el RFC | costo y latencia, sin afirmación de capacidad |
| **Romper la ausencia de pérdida a propósito.** El adaptador de dominio va en el *target* | un pase de verificación por experto — se acabó el enrutamiento gratis | salida experta de verdad |
| **Conservar la aceptación, pero como *señal* y no como veredicto** | un experimento | si funciona, enrutamiento gratis |

> **¿La tasa de aceptación de un drafter lleva alguna señal sobre si su experto
> habría dado una mejor respuesta — o sólo sobre cuánto coincide con la base?**

**No es obvio hacia dónde cae.** Un drafter y un target que coinciden están
representando el problema del mismo modo, y *"este experto ya piensa como el
modelo que lo va a juzgar"* no es nada despreciable. Pero es una hipótesis con un
nulo plausible, que es la única clase que merece un instrumento.

## La condición de falsación, escrita antes de construir nada

> Sobre una distribución de tareas con **headroom demostrado**, ordenar los
> expertos por tasa de aceptación y ordenarlos por puntaje verificado. **Si los
> dos órdenes no correlacionan, el enrutamiento por aceptación está muerto** y
> este repositorio lo dice en su README.

El chequeo de headroom va primero y es el arm más barato. Una base ya en el techo
hace que todos los expertos empaten, y un empate se lee como éxito.

## Documentos

- [`docs/TECHNICAL-REFERENCE.md`](docs/TECHNICAL-REFERENCE.md) — los mecanismos,
  qué existe hoy en vLLM y qué es un RFC, y dónde se pone caro el KV cache.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — las capas, y por qué el
  **router se dibuja como un hueco** en vez de como un componente.
- [`docs/agents-as-weight-deltas.md`](docs/agents-as-weight-deltas.md) — el
  artículo: la idea, la objeción, y lo que queda en pie.

## Reconocimiento

Esta línea empezó con una conversación con **[Ismael Faro](https://github.com/ismaelfaro)**,
que sugirió estudiar la decodificación especulativa y para qué podría servir. La
sugerencia fue acertada, y lo primero que encontró el estudio es que el uso obvio
no es el que funciona — que es justamente lo que la vuelve digna de escribirse.

---

<sub>Apache 2.0 · [Evolving Agents Labs](https://github.com/EvolvingAgentsLabs)</sub>
