# Problemas abiertos

## Empiece por acá: qué intenta construir este proyecto

Un modelo de IA grande y capaz es caro de correr. Uno chico es barato y no muy
bueno. La apuesta de este proyecto es que se puede llegar a casi lo mismo que el
caro teniendo **un solo** modelo chico cargado en memoria y poniéndole encima un
**parche** diminuto e intercambiable — unos pocos megabytes de ajustes que hacen
que el modelo chico se comporte como un especialista mientras está aplicado, y que
se pueden sacar de nuevo en milisegundos.

Si eso funciona, todo un sistema de "agentes" deja de ser un conjunto de programas
llamando a un modelo alquilado, y pasa a ser una **biblioteca de parches sobre un
modelo barato que es tuyo**. Tenés una copia en memoria y cambiás de especialista
como un carpintero cambia la mecha del taladro.

El diseño parte los parches en dos clases, y esa partición es toda la idea:

- **Un parche enseña *cómo trabajar*.** Cómo ordenar una solución en pasos
  numerados, cuándo frenar y pedirle a una calculadora en vez de adivinar, cómo
  arrastrar el resultado al paso siguiente. No sabe ninguna materia.
- **Los otros parches enseñan *qué es cierto*.** Uno sabe mecánica de fluidos,
  otro sabe otra cosa. Saben su materia y nada de procedimiento.

La razón de la partición es económica. Si cada especialista tuviera que aprender
además el procedimiento, cambiar el procedimiento — agregar una herramienta,
cambiar cómo el sistema la pide — obligaría a reentrenar a todos los especialistas
que tenés. Partirlos significa que cambiás el parche de procedimiento una vez y
todos los especialistas lo heredan.

Todo este documento trata de los lugares donde ese plan todavía no funciona,
descriptos tan llanamente como podamos.

## Lo que ya funciona

Esto está medido, no esperado. Cada punto es una corrida real registrada en
[`results/`](../../results/), y el plan
([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md)) nombra el directorio de cada una.

**El parche de procedimiento es real y viaja.** Entrenamos uno sólo con
aritmética cotidiana — tickets de compra, promedios, interés compuesto, el volumen
de un cono. No contiene física de ningún tipo. Después le dimos problemas de
mecánica de fluidos que nunca había visto, en un dominio que nadie le enseñó, con
una consigna que jamás menciona que existe una calculadora. Fue a buscar la
calculadora en **los treinta problemas**, un promedio de casi ocho veces cada uno,
y **no escribió ni un solo pedido mal formado**. Es el resultado más fuerte del
proyecto: unos megabytes de ajustes llevando un procedimiento que funciona a una
materia que nunca vio.

**El parche de materia también es real, y su conocimiento es exacto.** El
especialista de física escribe la fórmula correcta prácticamente siempre. Sus
respuestas están mal igual, porque no sabe hacer la cuenta — escribe bien la
expresión del área de un círculo y después la calcula mal en el cuarto decimal, y
cada paso posterior hereda el error. Cuando tomamos sus propias fórmulas escritas
y las evaluamos exactamente, dan la respuesta correcta en **treinta de treinta**
problemas, contra **uno de treinta** de lo que efectivamente escribió. No necesita
que le enseñen más física. Necesita dejar de hacer la cuenta.

**Poné los dos trabajos en un solo parche y el resultado es perfecto.** Un parche
que aprendió la física y el procedimiento juntos, con calculadora disponible,
responde **cuarenta de cuarenta** — igualando exactamente al modelo caro. Y hacen
falta las dos mitades: el modelo chico con calculadora y sin entrenar no acierta
ninguna a pesar de pedirla cincuenta y tres veces, y el modelo entrenado sin
calculadora acierta cuatro de cuarenta. Ninguna mitad vale nada sola.

**Y dos parches sí componen, siempre que se turnen.** Aplicados a la vez pelean por
cada palabra; alternados — el especialista nombra la magnitud siguiente y frena, el
parche de procedimiento escribe el pedido, la herramienta responde, el especialista
retoma — los pedidos pasan de 0,6 por problema a **4,7**. La competencia nunca fue
una propiedad de los parches. Era una propiedad de hacerlos producir la misma
palabra.

**Hay lugar real para mejorar.** Un modelo caro puntúa perfecto en este material y
el chico saca menos de la mitad, así que hay una brecha genuina que un
especialista puede cerrar. (Casi nos engañamos acá, y la historia está en
["Cómo leer los números"](#cómo-leer-los-números-de-este-documento) al final.)

O sea: las dos mitades existen, cada una está sana por su cuenta, y ponerlas en un
parche funciona. El problema es ponerlas en **dos** parches, que es todo el punto
del diseño.

## Problema 1 — dos especialistas que no se turnaban (resuelto; y lo que lo reemplazó)

### Lo que vemos

Cargue el parche de procedimiento y el de física al mismo tiempo. Los dos están
presentes: la respuesta nombra las magnitudes físicas correctas, en el orden
correcto, como lo haría el especialista de física — y a veces frena a pedirle a la
calculadora, como lo haría el de procedimiento. Las dos conductas se ven mezcladas
en la misma respuesta.

Pero la mezcla está desbalanceada. Solo, el parche de procedimiento pide la
calculadora casi ocho veces por problema. Combinado con el de física, la pide
**0,6 veces por problema**. En veinticinco de treinta problemas no la pide nunca.

Y pedirla es exactamente lo que importa:

| cuando la combinación... | problemas | acertó |
|---|---|---|
| pidió la calculadora al menos una vez | 5 | **3 — 60%** |
| no la pidió nunca | 25 | 1 — 4% |

Quince veces de diferencia. **El mecanismo no está roto. Casi nunca se dispara.**
Algo en la combinación suprime la única conducta que el parche de procedimiento
existe para aportar.

La forma más llana de describirlo: dos personas dictan la misma oración a la vez.
Una dice *"escribí el número acá"*. La otra dice *"pará, pedí la calculadora,
esperá la respuesta"*. En casi cada paso, gana la primera.

### Lo que probamos, y qué enseñó cada intento

**Intento uno: darle a cada parche una parte distinta del modelo para modificar.**
Un modelo es una pila de tablas numéricas grandes. Un parche ajusta algunas. Si el
parche de procedimiento sólo toca las tablas A, B y C, y el de física sólo toca D,
E y F, entonces los dos ajustes se suman en lugares distintos y no pueden chocar.
Cuesta una sola opción probarlo.

Lo empeoró. Los pedidos bajaron de 0,6 a 0,2 por problema, y la física se degradó
mucho también. Dos parches **sin una sola tabla en común** siguen peleando.

Ese resultado vale más de lo que costó el intento, porque elimina una familia
entera de arreglos propuestos. El primer instinto de cualquiera — el nuestro
incluido — es que esto es una colisión entre dos conjuntos de ajustes cayendo
sobre los mismos números, y que mantenerlos separados lo arregla. No es eso. Los
dos parches gobiernan lo mismo al final: **qué palabra escribe el modelo a
continuación**. Pueden estar construidos con partes completamente separadas y aun
así discrepar sobre esa única elección, porque en esa elección desembocan los dos.
Separar dónde viven no separa aquello sobre lo que discuten.

**Intento dos: subirle el volumen a un parche y bajárselo al otro.** Si el de
física gana siempre, aplicalo a media fuerza y al de procedimiento a fuerza
completa.

Esto **funcionó sobre aquello que apuntábamos, y destruyó aquello que queríamos
conservar.** Los pedidos saltaron de 0,2 a 3,5 por problema — diecisiete veces
más, así que la conducta es genuinamente controlable con esta perilla. Pero la
física se fue con eso: las fórmulas del especialista, que son correctas treinta de
treinta por su cuenta, fueron correctas **cero** de treinta en la combinación con
el volumen bajo.

Así que la perilla no mezcla a los dos especialistas. Elige un ganador. Girala
para un lado y tenés procedimiento sin conocimiento; girala para el otro y tenés
conocimiento sin procedimiento. No parece haber un punto intermedio que dé las dos
cosas, y los datos no nos dan ninguna razón para esperarlo.


**Intento tres: dejar de pedirles que hablen al mismo tiempo.** Todo lo anterior
supone que los dos parches están aplicados a la vez y tienen que compartir la
oración de algún modo. No hace falta. El especialista puede escribir el *nombre*
de la magnitud siguiente y frenar; ahí se enciende el parche de procedimiento, que
escribe el pedido a la calculadora y se apaga; el harness lo responde; el
especialista retoma. En ningún momento están los dos activos, así que no hay nada
que discutir.

**Esto funcionó.** Los pedidos pasaron de 0,6 por problema a **4,7** — ocho veces
— y la exactitud más que se duplicó. La competencia no es una propiedad de los dos
parches; es una propiedad de hacerlos producir la misma palabra. Sacá eso y las dos
conductas sobreviven.

**Y dejó a la vista otro problema, que es el que queda abierto.** En la división
que medimos, el especialista nombraba la magnitud y el *parche de procedimiento*
tenía que escribir la fórmula — y el parche de procedimiento no sabe física. Un
control que lo sacó por completo, dejando que el especialista escribiera su propia
cadena y que unas pocas líneas de código común ejecutaran la aritmética exacta,
sacó **23 de 30** contra los **9 de 30** del arreglo por turnos.

### Lo que no sabemos

La pregunta original está contestada: dos parches entrenados por separado **sí**
expresan los dos su conducta, siempre que se turnen en vez de compartir una
oración.

Lo que la reemplaza es más incómodo. **No sabemos que un parche de procedimiento
aprendido valga sus pesos.** Sobre este material unas pocas líneas de código común
le ganan — y no por poco. No es sorprendente una vez dicho: acá hay exactamente una
herramienta, y pedirla significa copiar una expresión que el especialista ya
escribió. Copiar es para lo que sirve el código común.

El parche de procedimiento tendría que ganarse el lugar donde el pedido **no** sea
una copia — varias herramientas entre las cuales elegir, argumentos que dar forma,
una decisión sobre cuál corresponde. Creemos que ahí vive la diferencia. No
construimos ese material, así que no podemos afirmarlo.

Hay además un sesgo medido en el número por turnos que no conviene esconder: el
parche de procedimiento tiende a escribir `A = 2 * 3 = 6` adentro del pedido, y la
calculadora lo rechaza — el 16% de sus pedidos, tocando 11 de los 30 problemas,
ninguno aprobado. Aceptar todas las formas recuperables lo subiría a unos 20 de 30,
igual por debajo del control. El sesgo es real; no cambia cuál arreglo gana.

### Cómo sabríamos que quedó resuelto

La pregunta de la composición la cierran los números de arriba. Lo que queda
necesita otra medición: material con varias herramientas, donde elegir y dar forma
al pedido sea trabajo de verdad. Resuelto se vería como el parche de procedimiento
aprendido ganándole a una regla escrita a mano sobre ese material — con la regla
escrita a mano efectivamente construida y con una oportunidad justa, porque una
comparación contra una regla que nadie escribió no es una comparación.

## Problema 2 — elegir el especialista correcto, y si elegir bien vale algo

### Lo que vemos

Si el sistema tiene muchos especialistas, algo tiene que decidir cuál responde
cada pedido. La respuesta del diseño es elegante: mientras el modelo caro todavía
supervisa, el sistema ya va registrando cuán seguido cada especialista coincide
con él en cada tipo de pedido. Ese registro es un mapa de quién es bueno en qué, y
sale gratis — es un subproducto de operar el sistema, no una evaluación aparte que
haya que pagar.

El mecanismo funciona. En los pedidos donde la elección realmente importaba, eligió
al especialista correcto nueve de cada diez veces, y recuperó casi todo el
beneficio que habría obtenido un elector omnisciente.

### Por qué la prueba obvia no lo resuelve

El problema es la comparación. Un método mucho más tonto — leer una palabra clave
del pedido y buscarla en una tabla — anduvo **exactamente igual**. No parecido:
empatado.

Eso ya pasó dos veces, con dos materiales distintos, y no es casualidad. Las dos
veces, el material sobre el que probábamos anunciaba su propia categoría en el
texto del pedido. Un pedido que dice de qué departamento viene no necesita un
router inteligente; necesita una búsqueda. Nuestro material estaba etiquetado, así
que el método barato podía leer la etiqueta, y cualquier comparación sobre ese
material no mide nada.

Esto es una trampa general y vale enunciarla sola: **cuando un método sofisticado
empata con uno trivial, lo primero que hay que sospechar es la prueba, no el
método.** Una prueba donde se espera que el método trivial tenga éxito no puede
mostrarte nada sobre el sofisticado.

### Lo que no sabemos

No sabemos cómo construir una prueba donde elegir bien sea genuinamente difícil —
donde el especialista correcto para un pedido no se pueda identificar a partir de
las palabras del pedido.

Eso requiere material donde superficie y sustancia se separen: dos pedidos que se
parezcan y necesiten especialistas distintos, o dos que se vean distintos y
necesiten el mismo. Podemos imaginar ese material. No lo construimos, y todavía no
sabemos si se puede construir sin volverse artificial de un modo que haga el
resultado igual de vacío, en la otra dirección.

Hasta entonces no podemos decir cuánto vale el mecanismo de ruteo. Podemos decir
que funciona. No podemos decir que sea mejor que una tabla de búsqueda, y dos veces
medimos que no lo es.

### Cómo sabríamos que quedó resuelto

Un conjunto de pedidos en el que el método de palabras clave rinda como el azar, y
el método basado en acuerdo siga eligiendo bien. Sin la primera mitad, la segunda
no prueba nada.

## Problema 3 — un especialista que no conoce el borde de su propia especialidad

### Lo que vemos

El especialista de física se entrenó con seis tipos de problema. Dele un séptimo
— sigue siendo mecánica de fluidos, sigue siendo el mismo estilo de consigna, sólo
que un tipo que nunca vio — y produce una respuesta segura, bien formateada y
equivocada.

Esto ahora está medido en serio y no entrevisto. Puntuando sus *fórmulas* en vez de
su aritmética, el especialista acierta **treinta de treinta** en el material para el
que fue entrenado y **una de veinte** en dos tipos para los que no. La caída no es
gradual, y los problemas de un lado y del otro se parecen.

Cómo se ve el fallo importa más que el número. Conserva la estructura numerada, la
seguridad y el vocabulario plausible, e inventa la física: una "fracción de volumen"
que no lo es, un test de régimen que no es el test de régimen, una ley de fuerza que
no es la ley de fuerza. El mismo especialista que puntúa perfecto en su propio
material escribió eso, con la misma voz.

No duda. No dice que el problema le resulta desconocido. Responde como responde
todo.

Esto importa más que un número de exactitud, por cómo se supone que se usa el
sistema. Todo el plan es dejar que un especialista se haga cargo de una categoría
de trabajo una vez que se probó en esa categoría, y dejar de pagar el modelo caro
para esa categoría. Si un especialista no puede darse cuenta de cuándo un pedido se
corrió afuera de aquello en lo que se probó, entonces "probado en esta categoría"
es una promesa que no puede sostener. El primer pedido de apenas afuera del borde
recibe una respuesta segura y equivocada sin nadie mirando.

### Lo que no sabemos

No sabemos cómo darle a un especialista una noción usable de su propio borde.

El enfoque obvio — preguntarle cuán seguro está — se sabe poco confiable, y en
nuestras propias corridas las respuestas equivocadas llegan con exactamente la
misma presentación fluida que las correctas. No hay diferencia visible sobre la
cual apoyarse.

Hay una segunda versión, más silenciosa, del problema. Aunque un especialista
pudiera reconocer pedidos desconocidos, el sistema tiene que decidir el borde de
una categoría **antes** de dejar de pagar el modelo caro, y la única evidencia
disponible en ese momento es el registro de acuerdo del Problema 2 — que te dice
dónde el especialista fue puesto a prueba, no dónde deja de funcionar. Esas dos
cosas no son la misma, y la diferencia entre ellas es exactamente la región donde
va a aparecer una respuesta segura y equivocada.

**Hay un candidato, encontrado mirando el proceso en vez del modelo.** Se listaron
seis señales de antemano y se revisaron las seis sobre transcripciones ya
guardadas. Sólo una separa: **cuán seguido la herramienta rechaza lo que la cadena
le pide**. Dentro de la región eso pasa en el 15% de los pedidos; afuera, en el 63%
— porque el especialista nombra magnitudes que no entiende y la capa de
herramientas no puede convertir esos nombres en un pedido válido. **La herramienta
falla donde la prosa no**, y un guardia que lea eso nunca tiene que preguntarle al
modelo cómo se siente.

Todavía no es un detector, y no hay que citarlo como tal: las señales se eligieron
con las respuestas ya a la vista, el umbral se ajusta sobre los mismos cincuenta
problemas que lo puntúan, y los dos tipos desconocidos usados son los únicos que
tiene este material. Confirmarlo pide dos más, con el umbral fijado de antemano.

### Cómo sabríamos que quedó resuelto

Un especialista que se abstenga, o derive hacia arriba, sobre material fuera de su
categoría a una tasa mucho más alta que sobre material de adentro — medido sobre
los dos, con la comparación explícita. Un método que lo haga abstenerse de todo no
es una solución, y la medición tiene que estar construida de modo que no se la
pueda pasar así.

## Problema 4 — quién corrige el trabajo cuando el maestro se va

### Lo que vemos

El diseño tiene dos fases. En la primera, un modelo caro hace el trabajo mientras
los especialistas miran y son puntuados por cuán seguido habrían producido lo
mismo. En la segunda, los especialistas que puntuaron lo suficiente toman el
control y el modelo caro se retira.

El plan además prevé que los especialistas sigan mejorando después de eso —
variantes que compiten, las mejores sobreviven. Eso requiere una nota, y la nota
tiene que venir de algún lado.

### Por qué corregirse solo no funciona

Si la nota viene de algo que está adentro del bucle de mejora, el bucle optimiza al
corrector en vez de al trabajo. No es un riesgo hipotético; la falla está bien
documentada en general y esta organización tiene su propio caso, donde un cambio
que parecía una ganancia genuina de capacidad en un modelo resultó ser el modelo
compensando por cómo se le preguntaba, y no una ganancia.

Así que la nota tiene que venir de un juez que el bucle no pueda influir, y ese
juez tiene que acertar lo bastante seguido como para que valga la pena obedecerlo.

### Lo que no sabemos

En nuestros experimentos teníamos un juez perfecto y gratis: los problemas se
generaban a partir de fórmulas cerradas, así que la respuesta exacta se conocía
antes de formular la pregunta. Por eso los resultados de este proyecto son
confiables, y también por eso no transfieren. El trabajo real no viene con
solucionario.

No sabemos de dónde sale el juez en un dominio que no tiene oráculo. Los
candidatos tienen todos problemas visibles. Un segundo modelo de IA como juez
comparte los puntos ciegos de aquello que juzga. Una persona es precisa y
demasiado lenta y cara como para cerrar un bucle con ella. Las pruebas escritas de
antemano sólo cubren lo que a alguien se le ocurrió anotar.

No elegimos entre estas opciones, y no diseñamos el experimento que elegiría. Es el
problema menos explorado del proyecto y está debajo de toda la mitad de
auto-mejora del diseño.

### Cómo sabríamos que quedó resuelto

Un juez, en un dominio sin solucionario, cuyos veredictos coincidan con una
revisión humana cuidadosa lo bastante seguido como para actuar en consecuencia —
medido contra esa revisión humana sobre una muestra, con los desacuerdos
examinados en vez de promediados.

## Problema 5 — la medición central no se puede tomar entre familias de modelos distintas

### Lo que vemos

La medición sobre la que se apoya todo el diseño es: *¿cuán seguido el modelo
chico produce exactamente lo que habría producido el modelo caro?* Hecha al grano
más fino, es casi gratis — sale como subproducto de una técnica en la que un
modelo chico propone texto y uno grande lo verifica, que ya se usa para acelerar
sistemas, y convierte ese truco de velocidad en un puntaje continuo de calidad sin
costo extra.

Eso es genuinamente elegante, y es la razón por la que la arquitectura tiene la
forma que tiene.

### El sustituto que usamos, y lo que cuesta

Sólo funciona si los dos modelos cortan el texto en los mismos pedazos. Modelos de
familias distintas no lo hacen: la misma oración se vuelve una secuencia distinta
de fragmentos en cada uno. Así que la medición fina no se puede tomar entre un
modelo chico de una familia y uno caro de otra, que es exactamente el par que el
diseño pide.

Medimos algo más grueso en su lugar: si los dos llegaron a la misma respuesta. Eso
funciona, y lo validamos — pero recién después de descubrir por las malas que
nuestro primer intento de una versión a nivel de texto medía **el formato**. Dos
respuestas idénticas sacaron cero de acuerdo porque una estaba indentada y la otra
no, y un modelo que dio la respuesta correcta sacó cero contra uno que la dio mal.
Pasar a comparar respuestas en vez de texto lo arregló, y nos costó el grano fino:
ahora aprendemos un número por pedido en vez de una señal en cada palabra.

### Lo que no sabemos

No sabemos cómo recuperar la medición fina entre familias de modelos.

Quedarse en una sola familia esquiva el problema, pero entonces el supervisor caro
tiene que ser un modelo grande de la misma familia que el chico — lo que restringe
la elección del supervisor a lo que esa familia ofrezca, y toda la premisa es que
el supervisor sea el mejor modelo disponible, no el mejor *relativo*.

Traducir entre los dos esquemas de corte es posible en principio y con pérdida en
la práctica, y no medimos cuánta pérdida, ni si lo que sobrevive sigue valiendo la
pena.

### Cómo sabríamos que quedó resuelto

Un puntaje de acuerdo fino entre dos familias distintas que siga al puntaje grueso
a nivel de respuesta en el que ya confiamos — medido sobre los mismos pedidos, para
que los dos se puedan comparar directamente, y con los casos donde discrepan
examinados en vez de promediados.

## Lo que es sólo trabajo, no un misterio

No todo lo que falta es desconocido. Estas son cosas que sabemos cómo hacer y no
hicimos, y vale separarlas para que los problemas genuinamente abiertos de arriba
queden visibles:

- **Volver a probar si el acuerdo ordena bien a los especialistas**, ahora que hay
  una brecha real entre el modelo caro y el chico. La prueba anterior se corrió
  contra casi-iguales, donde no había nada que ordenar. El instrumento existe y el
  material existe.
- ~~Medir bien el problema del borde.~~ **Hecho, y es peor de lo que sugería la
  corrida cortada**: fórmulas exactas treinta de treinta dentro de la región y una
  de veinte afuera. Lo que queda no es una medición sino un guardia, y el primer
  candidato está en el Problema 3.
- **Poner precio a sostener muchos parches a la vez.** Nuestro primer intento midió
  nuestro propio banco de pruebas en vez del sistema de servicio, y está anulado.
  Hacerlo bien es trabajo conocido con una herramienta conocida.
- **Compartir cómputo entre parches.** Dos especialistas trabajando sobre el mismo
  pedido hoy repiten trabajo que en principio se podría compartir. Es un problema
  de ingeniería real y con costo real, pero es ingeniería, no una pregunta sin
  respuesta.

## Cómo leer los números de este documento

Cada cifra de acá viene de una corrida registrada en [`results/`](../../results/),
y varias reemplazaron a una cifra anterior que estaba mal. Eso es deliberado, y las
correcciones se dejan a la vista en vez de barrerse, porque la forma en que estas
mediciones fallan es en sí misma uno de los hallazgos.

Dos ejemplos, los dos del mismo día, uno en la dirección que nos favorecía y el
otro en la que no.

Reportamos que el modelo caro le ganaba al chico por un margen enorme. Después
notamos que todas las mediciones del modelo chico se habían tomado
instruyéndolo a **no mostrar el trabajo**, mientras que todas las mediciones de la
versión entrenada se habían tomado instruyéndola a mostrarlo. El mismo modelo
chico saca cero de treinta con la primera instrucción y catorce de treinta con la
segunda. Aproximadamente la mitad de la brecha que habíamos publicado era la
instrucción, no los modelos. La brecha corregida sigue siendo lo bastante grande
como para valer la pena cerrarla, y es la que se cita más arriba.

Inmediatamente después, la comparación corregida dio una brecha mucho *más chica*
— y eso también estaba mal, en la dirección opuesta. El modelo caro escribe
derivaciones largas, y se había cortado a mitad de camino por un límite de largo;
el puntaje entonces levantaba un valor intermedio a medio terminar y lo marcaba
como error. Con espacio para terminar, puntúa perfecto. Publicar el número chico
habría sido el mismo error que publicar el grande, sólo que favoreciendo otra
conclusión.

La lección que sacamos, y la razón por la que existe esta sección: **una medición
que coincide con lo que esperabas no queda verificada por eso.** Las dos se
cazaron mirando lo que los modelos efectivamente escribieron, no el puntaje.
