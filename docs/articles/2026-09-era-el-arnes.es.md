# Creíamos que un modelo chico no podía razonar. Era nuestro arnés.

*Artículo para LinkedIn — septiembre de 2026. Versión en inglés:
[`2026-09-it-was-the-harness.md`](2026-09-it-was-the-harness.md). Cada número de este texto sale del
registro del repositorio ([`../es/RECORD.md`](../es/RECORD.md)) y nombra su corrida.*

![Dos paneles. Izquierda: un especialista mete una consulta por una ranura y la respuesta le vuelve por otra ventanilla, a su espalda, sin que la vea — 11 / 90. Derecha: la respuesta vuelve en la misma ficha, debajo de la consulta — 90 / 90.](../img/article-harness.png)

*Mismo modelo. Mismos problemas. Otro camino.*

---

Durante cuatro días, la frase más repetida de nuestro proyecto fue ésta: **"el experto que decide
funciona; el experto que razona falla."**

Era falsa. Y la forma en que descubrimos que era falsa le sirve a cualquiera que ponga un modelo
afinado detrás de un runtime de agentes como OpenClaw.

## El hallazgo

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

## El panorama: qué estamos construyendo

Se llama **lora-kernel**, es código abierto, y es el runtime de un servicio: una API compatible con
OpenAI —e instancias de OpenClaw por tarea encima— que resuelve localmente lo que cae en una región
medida y manda el resto a un modelo de frontera.

Tres ideas lo sostienen:

**Un experto es su corpus.** Cada región es un LoRA chico sobre un modelo residente, y se sirve
exactamente bajo lo que su corpus le enseñó. Lo de arriba es por qué.

**Un router que sabe abstenerse.** Decide a qué experto se parece un pedido, y cuando no se parece a
ninguno, lo manda a la frontera. Abstenerse es parte del diseño, no una falla.

**El LoRA no es el libro de texto; es el especialista que sabe usar la biblioteca.** Ésta es la pieza
central de la versión 1.0. Cada experto tiene una biblioteca de notas en markdown, en dos estantes:
un **arnés operativo** (*¿cómo se hace?* — pasos con enlaces: *requiere*, *siguiente*, *usa*) y una
**wiki enciclopédica** (*¿qué es, qué fórmula aplica?*). El modelo no memoriza las notas: aprende a
navegarlas con tres verbos —buscar, abrir, calcular—. Un programa chico, sin IA, hace de árbitro:
pasa las páginas, aplica las reglas locales de cada sitio antes de mostrar la nota, y corta si el
modelo se saltea un paso obligatorio.

La ganancia: si mañana cambia un protocolo, **se edita un archivo markdown en git. No se reentrena
nada.**

## El cuadro completo: cuando es todo un equipo

Hasta acá hablé de un experto y un usuario. El caso donde esto rinde de verdad es otro, y cada vez
lo veo más: **un equipo entero corriendo OpenClaw en modo multijugador.** Cada persona le escribe a
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

**Si tu equipo trabaja así, el orden sería éste:**

1. **Elegí un grupo, no la empresa.** El de trabajo más repetitivo y con respuesta verificable.
2. **Mirá las formas, no los textos.** Tenemos una herramienta que lee del propio registro del
   runtime qué *forma* tiene el tráfico —cuántos turnos, qué herramientas, qué largo— sin guardar
   nunca un prompt. A escala de equipo eso importa más, no menos.
3. **Medí si la frontera realmente va adelante en el trabajo de ESE grupo.** Por grupo, no en
   promedio: un promedio de empresa esconde al grupo donde hay mucho que ganar y al grupo donde no
   hay nada. Nos pasó: en nuestra primera suite, pagar 100 veces más puntuó peor. Un grupo sin
   brecha no tiene nada que destilar, y conviene saberlo antes de entrenar nada.
4. Recién ahí: un adaptador y una biblioteca para ese grupo, con su compuerta.

**Y lo que todavía no tenemos a escala de equipo**, para que nadie lo descubra tarde: aislamiento
entre usuarios (hoy es una clave y un solo destino), streaming (lo bufferizamos a propósito: una
llamada a herramienta sólo es una llamada cuando se cierra), el ciclo de vida de los adaptadores por
grupo, y la medición que más nos interesa —qué cuesta servir un lote mixto con decenas de sesiones
alternando entre grupos—, que nunca pudimos hacer bien porque no tuvimos tráfico real. Un equipo así
es exactamente donde esa medición deja de ser un argumento y pasa a ser un número.

## Lo que todavía no es

Prefiero decirlo yo:

- **Todo lo medido es sobre datos que generamos nosotros.** Ningún tráfico real pasó por el sistema.
- **No es instalable todavía.** Hoy corre con una GPU alquilada, un túnel y nuestro proxy.
- **La biblioteca está especificada, no construida.** Su afirmación central —que extiende a un
  experto a un procedimiento que nunca entrenó— está sin probar.
- **El router aprendido falló dos veces.** Las dos versiones eran seguras frente a texto ajeno y las
  dos mandaban afuera el 100 % de los pedidos legítimos de remitentes nuevos. Sigue siendo un
  diccionario de palabras clave.
- **Nunca medimos el ahorro en plata.**

Una señal alentadora, en el primer texto real que tocamos —procedimientos de enfermería de un manual
abierto—: un modelo de 4B sin entrenar pasa de 29/48 a 45/48 cuando tiene la nota correcta delante,
y de 0/12 a 12/12 cuando la nota trae la regla local de una unidad ("acá se limpia 8 segundos, no
5"). Lee bien. Lo que le falta —y lo que hay que entrenar— es *actuar* siguiendo un procedimiento.

## Hoja de ruta

1. **El pool sobre una base más nueva** (Qwen 3.5, 4B). En curso.
2. **La biblioteca, pieza por pieza**, con una prueba que puede matarla temprano: que el experto
   resuelva un procedimiento hermano que nunca vio, sólo porque sus notas están en la biblioteca.
3. **La primera región real:** procedimientos de enfermería, como material de formación —no consejo
   a pacientes—, con las adaptaciones locales de cada sitio como notas editables. Y, si aparece, **el
   grupo de un equipo que ya trabaje en modo multijugador**: ahí la región viene dada.
4. **Un router que separe la tarea del contenido**, que es lo que les faltó a los dos que fallaron.
5. **La política del servicio, con la factura medida.**

Cada paso tiene escrita, antes de correr, la condición que lo daría por falso. Así fue como
encontramos lo del arnés.

## Si usás OpenClaw para trabajo repetitivo

Buscamos dos o tres equipos —idealmente uno que ya trabaje en modo multijugador, con grupos por área— con una tarea que cumpla tres condiciones: se repite mucho, tiene una
respuesta verificable, y hoy se la mandan entera a un modelo de frontera. No tenemos un producto
para venderles. Tenemos un método para medir si una parte de ese trabajo puede resolverse localmente
— y la costumbre de publicar el número salga como salga.

Repositorio: github.com/EvolvingAgentsLabs/lora-kernel
