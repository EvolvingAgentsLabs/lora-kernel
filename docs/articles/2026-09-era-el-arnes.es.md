# Una organización que funciona con agentes, sobre una sola GPU: la arquitectura

*Artículo para LinkedIn — septiembre de 2026. Versión en inglés:
[`2026-09-it-was-the-harness.md`](2026-09-it-was-the-harness.md). Cada número de este texto sale del
registro del repositorio ([`../es/RECORD.md`](../es/RECORD.md)) y nombra su corrida.*

![Una arquitectura de solución en cinco capas: personas en cuatro roles; un runtime de agentes con un agente por rol; aplicaciones de pedidos y administración; canales de app y mensajería; una sola base de datos con identidad, pagos y monitoreo. Debajo de los agentes, una placa gráfica dibujada como estantería: un lomo grueso, el modelo residente, y un lomo fino por rol, cada uno con dos cajones de notas. Un cartel rutea por rol; líneas punteadas salen hacia la frontera y hacia una persona.](../img/solution-architecture.png)

*Los registros quedan en la base; los hábitos van en el adaptador; el conocimiento queda en notas que una persona puede leer.*

---

Cada vez más organizaciones chicas se dibujan igual: personas en unos pocos roles, **un agente por
rol** sobre un runtime como OpenClaw, las aplicaciones que esos agentes operan, los canales que la
gente ya usa, y abajo una sola base de datos. Funciona. Y tiene una propiedad de la que se habla
poco: **cada mensaje de cada persona a cada agente sale entero hacia una API de frontera.** La
factura y los datos que salen crecen con la cantidad de gente, no con la dificultad del trabajo.

Este artículo es sobre la capa que falta en ese dibujo — la que va *debajo* de la columna de agentes
— y sobre qué se puede construir con ella. Primero la arquitectura. Después, qué parte ya está medida
y qué parte no, con números.

## La arquitectura, capa por capa

El ejemplo del dibujo es una distribuidora. Se lee de arriba hacia abajo.

**1. Personas, en roles.** Clientes, proveedores y transportistas, el equipo del depósito, el
personal de oficina. No son "usuarios": cada rol pregunta cosas distintas, por canales distintos, con
permisos distintos.

**2. Un runtime de agentes, con un agente por rol.** Atención al cliente, recepción, despacho,
compras y stock, reclamos y devoluciones, IT. Esto ya existe y no lo reemplazamos: es OpenClaw, o el
runtime que uses.

**3. Las aplicaciones y los canales.** Pedidos (pedidos, entregas, muelles, devoluciones) y
administración (comunicaciones, operaciones, compras, sueldos, reportes); una app y la mensajería,
separada en clientes e interno. Tampoco los tocamos.

**4. Los sistemas de registro.** Una sola base de datos, con identidad y permisos, pagos y monitoreo
al lado. **Se quedan donde están.** Ningún dato de un cliente entra a un modelo por entrenamiento.

**5. Y la capa nueva: debajo de los agentes, una sola GPU como estantería.** Un modelo chico
residente —4 mil millones de parámetros— y, apoyado en él, **un adaptador LoRA por rol**, de unos
120 MB cada uno. Donde hoy cada agente es un *prompt* sobre el mismo modelo remoto, acá cada rol es
un **experto**: entrenado en cómo *esta* organización hace *ese* trabajo. Y cada experto tiene un
fichero de dos cajones:

- **"cómo lo hacemos acá"** — el arnés operativo: procedimientos paso a paso, con enlaces *requiere*,
  *siguiente*, *usa*;
- **"lo que sabemos"** — la wiki: qué es cada cosa, qué fórmula aplica, qué dice el catálogo.

Son notas en markdown de menos de media página. **El modelo no las memoriza: aprende a navegarlas**,
con tres verbos — buscar, abrir, calcular. *El LoRA no es el libro de texto; es el especialista que
sabe usar la biblioteca.*

Tres piezas más cierran el dibujo:

- **El router: el rol del que llega un mensaje es la ruta.** No hay que adivinar a qué experto va un
  pedido — el runtime ya sabe de qué agente, grupo o canal viene.
- **Dos salidas para lo que no está medido.** Lo que un experto no está *medido* para resolver se va
  a un modelo de frontera — o **a una persona, donde la política dice que nada sale del edificio.**
  Abstenerse es parte del diseño, no una falla.
- **Un árbitro que no es IA.** Un programa chico pasa las páginas, **aplica las reglas de este lugar
  antes de mostrar la nota** ("acá un pallet de más de 1,60 m se rearma antes de despachar") y corta si el modelo se saltea un paso
  obligatorio.

La regla que ordena todo: **los registros quedan en la base, los hábitos van en el adaptador, el
conocimiento queda en notas que una persona puede leer y corregir.** Si mañana cambia un protocolo,
se edita un archivo en git. No se reentrena nada.

## Qué se puede construir con esto

La distribuidora es un ejemplo. La forma se repite donde haya **pocos procedimientos, repetidos a diario,
con reglas locales que difieren del manual, sobre datos que no deberían salir:**

| organización | roles que pasan a ser expertos | qué va en los dos cajones |
|---|---|---|
| **una distribuidora** | atención al cliente, recepción, despacho, compras, reclamos | los procedimientos de manejo del lugar · catálogo, transportistas, niveles de servicio |
| **un estudio contable o jurídico** | ingreso de casos, revisión de documentos, vencimientos, facturación | las listas de control y plantillas del estudio · las reglas de su jurisdicción |
| **una escuela o centro de formación** | inscripciones, apoyo docente, comunicaciones, compras | cómo resuelve esta escuela cada caso · programa, calendario, reglamento |
| **un taller o servicio técnico** | recepción de equipos, diagnóstico, repuestos, garantías | el procedimiento de cada tipo de reparación · manuales, listas de repuestos, condiciones de garantía |
| **un club o centro comunitario** | socios, inscripciones a actividades, instalaciones, cobranzas | cómo resuelve este club cada caso · actividades, cuotas, reglamento interno |
| **una administración de propiedades** | pedidos de inquilinos, mantenimiento, cobranzas, proveedores | el escalamiento por edificio · contratos, reglamentos, condiciones de proveedores |

Ninguna de esas filas está medida: es hacia donde apunta el diseño. Lo que sí está medido viene
abajo.

**Si quisieras armarlo, el orden sería éste:**

1. **Elegí un rol, no la organización.** El de trabajo más repetitivo y con respuesta verificable.
2. **Mirá las formas, no los textos.** Tenemos una herramienta que lee del propio registro del
   runtime qué *forma* tiene el tráfico —cuántos turnos, qué herramientas, qué largo— sin guardar
   nunca un prompt.
3. **Medí si la frontera realmente va adelante en el trabajo de ESE rol.** Por rol, no en promedio.
   Nos pasó: en nuestra primera suite, pagar 100 veces más puntuó peor. Un rol sin brecha no tiene
   nada que destilar, y conviene saberlo antes de entrenar nada.
4. **Escribí la biblioteca antes que el adaptador.** Las notas son útiles desde el primer día, para
   las personas también — y son lo que el equipo va a mantener.
5. Recién ahí: un adaptador para ese rol, con su compuerta de liberación.

---

## Lo que ya tenemos

Se llama **lora-kernel** y es código abierto: una API compatible con OpenAI —con OpenClaw encima—
que resuelve localmente lo que cae en una región medida y manda el resto afuera. Esto es lo que hay
detrás de cada pieza del dibujo, con su número.

## El hallazgo que ordenó el proyecto: era nuestro arnés

![Dos paneles. Izquierda: un especialista mete una consulta por una ranura y la respuesta le vuelve por otra ventanilla, a su espalda, sin que la vea — 11 / 90. Derecha: la respuesta vuelve en la misma ficha, debajo de la consulta — 90 / 90.](../img/article-harness.png)

*Mismo modelo. Mismos problemas. Otro camino.*

Durante cuatro días, la frase más repetida de nuestro proyecto fue: **"el experto que decide
funciona; el experto que razona falla."** Era falsa.

Entrenamos un modelo chico —3 mil millones de parámetros, con un adaptador LoRA— para resolver
problemas de mecánica de fluidos: cadenas de 6 a 9 pasos, cada paso con una herramienta (buscar una
propiedad en un manual, convertir unidades, calcular). Lo evaluamos con 90 problemas nuevos.

**Resultado: 11 de 90.** El modelo llamaba a las herramientas a la perfección —603 llamadas, ninguna
rechazada— y después se equivocaba en la física. Conclusión obvia: los modelos chicos siguen
protocolos, pero no razonan. Lo escribimos en el plan, retiramos al experto, y mandamos esa región a
un modelo de frontera.

Cuatro días después quisimos construir algo encima de esa conclusión, y antes de hacerlo leímos las
79 fallas una por una, mirando **dónde** se rompía cada cadena. No era la física.

En 74 de las 79, el modelo usaba un número que no salía de ningún lado. Buscaba la densidad del
fluido, la herramienta le devolvía 882,3… y en el paso siguiente multiplicaba por 1359,7. Un número
inventado, con pinta de densidad.

¿Por qué ignoraría el resultado que acababa de pedir? Porque **nunca lo vio donde había aprendido a
leerlo.** En su entrenamiento, el resultado de cada herramienta aparecía escrito a continuación de
la llamada, en el mismo texto:

`<calc>3.96 + 0.541/2</calc>= 4.2305`

Pero nosotros lo estábamos sirviendo por el camino estándar de la API: la llamada sale como
`tool_calls`, el resultado vuelve como un mensaje aparte con `role: "tool"`. Para un modelo grande
es lo mismo. Para uno chico entrenado de la otra forma, el resultado simplemente no estaba.

Lo volvimos a servir como su entrenamiento le enseñó. **Mismo adaptador. Mismos 90 problemas.**

**90 de 90.**

Pareado caso por caso, 79 a 0. Como un número tan limpio es justo el que aprendimos a no creer, lo
revisamos antes de anotarlo: ninguno de los 90 enunciados estaba en sus datos de entrenamiento,
ninguna respuesta se repetía, y en 89 de 90 la respuesta final salía del último cálculo del propio
modelo. En esos mismos casos, un modelo de frontera había sacado 66. (Con la salvedad que
corresponde: son problemas generados por nosotros, dentro de la región exacta para la que ese
experto entrenó. Que un especialista le gane a un generalista *ahí* es lo esperable.)

No habíamos medido al modelo. Habíamos medido nuestro arnés.

## Qué significa si usás OpenClaw con un modelo afinado

No es un caso aislado. En doce días lo encontramos tres veces más:

- **El prompt de sistema.** Bajo el prompt de 37 KB del runtime, nuestro experto de correo llamó a
  una herramienta en 2 de 32 turnos. Bajo el prompt con el que se entrenó, en 19 de 32.
- **La lista de herramientas.** Con las 54 herramientas que OpenClaw ofrece, el experto copiaba
  nombres del bloque: 225 de 227 llamadas rechazadas. Podado a las suyas, 8 de 1160.
- **El formato del resultado.** El mismo experto de correo: 0,992 con el resultado en línea, 0,808
  por `tool_calls`.

La lección es una sola: **un modelo chico afinado es lo que su corpus le enseñó — el prompt, el
bloque de herramientas, el orden de los argumentos y la forma en que le llega el resultado.** Servido
de otra manera es otro modelo, y peor. Antes de concluir que "el modelo no sirve para esto":

1. Miren dónde falla, no sólo si falla. *¿Usó lo que la herramienta le devolvió?*
2. Sírvanlo una vez exactamente como se entrenó. Es una corrida de diez minutos.
3. Saquen la aritmética de la cabeza del modelo. Con calculadora, 40 de 40; sin ella, 4 de 40.

## Las piezas del dibujo, una por una

- **Varios expertos sobre un solo modelo residente, en una GPU.** Medido: un servidor, una base,
  varios adaptadores, cada pedido atendido por el suyo; que convivan no le cuesta nada al que sirve.
- **Dos expertos liberados**, ahora sobre la familia Qwen 3.x (4B): triage de correo **471/475** y
  compromisos de escritorio **240/240** — cada uno empata, caso por caso, con su versión anterior
  sobre otra base. Nada se libera sin esa compuerta.
- **La API rutea por pedido; el cliente no nombra ningún modelo.** En un replay de 240 casos, 0,546 →
  0,775, con 0 mal ruteados.
- **OpenClaw en vivo contra el sistema:** 40 de 40 turnos resueltos localmente, 0 llamadas inventadas.
- **La biblioteca existe.** La primera está armada con procedimientos paso a paso de un manual
  abierto (CC BY 4.0) — 94 notas enlazadas que pasan un *lint*, con una
  capa de reglas locales de ejemplo.
- **El árbitro existe.** Los 72 recorridos de referencia pasan por él sin un solo rechazo; los tres
  recorridos tramposos —saltearse un paso requerido, abrir una nota que nadie le mostró, ir fuera de
  orden— se cortan.
- **Y una señal alentadora sobre leer notas:** un 4B sin entrenar pasa de 29/48 a 45/48 con la nota
  correcta delante, y de 0/12 a 12/12 cuando la nota trae la regla local de un sitio.

## Cuando el rol es un grupo: un equipo en modo multijugador

La misma arquitectura, vista desde la mensajería. El caso que cada vez veo más: **un equipo entero corriendo OpenClaw en modo multijugador.** Cada persona le escribe a
los agentes desde su mensajería. Hay varios agentes. Hay decenas de sesiones abiertas a la vez. Y las
conversaciones viven en **grupos estables por área**: desarrollo, marketing, interno, operaciones,
más los mensajes directos de cada uno y algún bot que cada tanto muestra "la corrida falló".

![Cuatro chats grupales y una pila de mensajes directos desembocan en un runtime de agentes, después un proxy, después una tarjeta gráfica dibujada como estantería: un lomo grueso para el modelo residente y un lomo fino de color por grupo, cada uno con su fichero de dos cajones. Una línea punteada sale hacia la frontera.](../img/article-team.png)

*Muchos grupos, una sola máquina — y cada grupo con su especialista y su biblioteca.*

**Primero lo que esto NO arregla**, porque es lo que más duele a esa escala: una barra lateral que
se llena de sesiones, un gateway que cada tanto queda inalcanzable detrás de un proxy de acceso, un
websocket que se cae. Eso es la mitad de *infraestructura* de un despliegue así, y nada de lo que
hacemos la toca. Lo nuestro es la otra mitad: **la mitad del modelo.**

Y en esa mitad, un equipo cambia tres cosas respecto de un usuario solo.

**1. El grupo es la región — y el problema en el que fallamos dos veces desaparece.** Nuestra
arquitectura sólo afirma una cosa: un experto chico le gana a un generalista *dentro* de una región
— y fuera de ella cae de 30/30 a 1/20. Una persona haciendo trabajo variado no tiene región; hay que
descubrir si existe, y después hay que *adivinar* a cuál pertenece cada mensaje. Ahí es donde
fallamos: nuestros dos routers aprendidos mandaban afuera el 100 % de los pedidos de remitentes
nuevos. **Un grupo estable es una región por construcción**: se repite, tiene su vocabulario, sus
personas y sus convenciones. Y la ruta no hay que inferirla: *el identificador del grupo ES la ruta.*
El cliente ya sabe en qué sala está. Un contexto que elimina un problema abierto vale más que uno
que mejora un número.

**2. Una sola GPU, un modelo residente, un adaptador por grupo.** Esto sí está medido: un servidor,
un modelo base, varios adaptadores, y cada pedido atendido por el suyo; que convivan no le cuesta
nada al que está sirviendo. Un adaptador pesa unos 120 MB. El de marketing no sabe nada de
desarrollo, y no tiene por qué.

**3. La biblioteca de cada grupo es donde vive "cómo lo hacemos nosotros".** El arnés operativo de
marketing —cómo se arma un brief, qué se revisa antes de publicar— y el de desarrollo —cómo se hace
el triage de un bug, qué pide una revisión— son archivos markdown que **el propio equipo edita**.
Cambia el proceso, se edita la nota, y el agente de ese grupo lo sigue al día siguiente sin
reentrenar nada. Es la diferencia entre "el agente de marketing debería saber cómo habla marketing"
y tener que repetírselo en cada prompt.

Lo que eso ataca es concreto: **hoy, cada mensaje de cada persona a cada agente sale entero hacia
una API de frontera.** La factura y los datos que salen de la empresa crecen con la cantidad de
gente, no con la dificultad del trabajo.

## Lo que todavía no es

Prefiero decirlo yo:

- **Todo lo medido es sobre datos que generamos nosotros.** Ningún tráfico real pasó por el sistema.
- **No es instalable todavía.** Hoy corre con una GPU alquilada, un túnel y nuestro proxy.
- **La afirmación central de la biblioteca está sin probar:** que extiende a un experto a un
  procedimiento que nunca entrenó. Es la próxima medición, y puede salir mal.
- **El buscador de notas todavía no alcanza.** Un modelo de embeddings estándar encuentra la nota
  correcta entre las 3 primeras en el 64 % de consultas parafraseadas — contra 6 % de una búsqueda por
  palabras, pero debajo del 80 % que nos habíamos fijado antes de medir. No movimos la vara.
- **Mudar de base no es gratis.** El experto de fluidos, reentrenado sobre el modelo nuevo, sacó
  80/90 contra su propio 90/90: en los diez casos la cuenta estaba bien y la *última línea* salió en
  un formato que su corpus nunca le enseñó. No quedó liberado. Otra vez el arnés.
- **El router aprendido falló dos veces:** seguro frente a texto ajeno, pero mandaba afuera el 100 %
  de los pedidos legítimos de remitentes nuevos. Por eso en esta arquitectura la ruta es el rol.
- **A escala de equipo falta:** aislamiento entre usuarios, streaming, el ciclo de vida de los
  adaptadores, y el costo de servir decenas de sesiones alternando entre roles.
- **Nunca medimos el ahorro en plata.**

## Hoja de ruta

1. ~~El pool sobre una base más nueva~~ — hecho.
2. **La prueba que puede matar la biblioteca:** que el experto resuelva un procedimiento hermano que
   nunca vio, sólo porque sus notas están en la biblioteca — contra el mismo modelo sin entrenar
   leyendo las mismas notas.
3. **Un buscador que separe la tarea del contenido**, para las notas y para el router.
4. **La primera región real: un rol de una organización que ya trabaje así** — ahí la región viene
   dada, con las adaptaciones de cada sitio como notas editables.
5. **La política del servicio, con la factura medida.**

Cada paso tiene escrita, antes de correr, la condición que lo daría por falso. Así fue como
encontramos lo del arnés.

## Si tu organización ya se dibuja así

Buscamos dos o tres equipos —idealmente uno que ya tenga un agente por rol— con una tarea que cumpla
tres condiciones: se repite mucho, tiene una respuesta verificable, y hoy se la mandan entera a un
modelo de frontera. No tenemos un producto para venderles. Tenemos una arquitectura, un método para
medir si una parte de ese trabajo puede resolverse en su propia máquina — y la costumbre de publicar
el número salga como salga.

Repositorio: github.com/EvolvingAgentsLabs/lora-kernel
