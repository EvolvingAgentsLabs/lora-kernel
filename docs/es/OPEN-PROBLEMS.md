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

**Y ahora hay material donde las herramientas hacen falta de verdad.** Una suite
anterior falló su propio propósito: el especialista había memorizado los catorce
valores de tabla que necesitaba, así que sacaba 27 de 30 sin pedir nada, y una suite
cuyas llamadas se pueden recordar no puede medir cuánto vale una capa de
herramientas. Darle a cada problema su propio manual —una sustancia con nombre
inventado y propiedades que existen sólo en ese problema— baja al mismo especialista
a **6 de 30 cuando no puede preguntar**. El valor no estaba en el entrenamiento y no
está en la consigna, así que hay que pedirlo.

**Hay lugar real para mejorar.** Un modelo caro puntúa perfecto en este material y
el chico saca menos de la mitad, así que hay una brecha genuina que un
especialista puede cerrar. (Casi nos engañamos acá, y la historia está en
["Cómo leer los números"](#cómo-leer-los-números-de-este-documento) al final.)

O sea: las dos mitades existen, cada una está sana por su cuenta, y ponerlas en un
parche funciona. El problema es ponerlas en **dos** parches, que es todo el punto
del diseño.

## Dónde está esto parado, 2026-09-12

Tres de los cuatro problemas de abajo se movieron desde que se escribieron, y uno se
cerró. Las secciones conservan su texto original — eso es lo que las hace valer la
relectura — y esto es el delta.

**El Problema 1 está cerrado dos veces.** Turnarse resolvió la composición, y la
sospecha que sobrevivió a eso — que las llamadas eran memorizables, así que la capa
de herramientas era decoración — se probó y se eliminó: con un manual por caso, un
control **sin capa de herramientas** cae de 27/30 a **6/30**. Sobre ese material un
protocolo aprendido reproduce **94 de 96** llamadas del oráculo contra **93 de 96**
de una regla escrita a mano. El brief fijó antes de correr que tres valores es
empate, así que se reporta empate, y la diferencia que queda es de carácter y no de
puntaje: la regla hace 96 llamadas sin **ninguna rechazada**, el kernel hace 116 con
**20 rechazadas**. `results/P21-handbook-20260911/`.

**El Problema 2 no cambió y el Problema 3 tiene una señal que no tenía.** La guardia
de comportamiento sigue falsificada. Sobrevive una **estructural**: el álgebra
dimensional sobre (kg, m, s) marca el **0,80** del trabajo fuera de región en
familias selladas antes de que el verificador existiera. Sola da 0,22 de falsa
alarma sobre trabajo correcto en región, que es inusable — pero escalar sólo cuando
fallan la dimensional **y** la mecánica **no se dispara nunca en región** (0 de 60) y
aun así atrapa el 0,35 del trabajo de afuera. `escalate.has_left_its_region` es esa
regla; `escalate.is_probably_wrong` es la ancha, que lleva el acierto entregado de
0,53 a 0,83 en región y manda afuera la mitad del trabajo en región para lograrlo.
**Cuál corresponde depende de cuánto cuesta escalar, y este repositorio no lo midió.**
`results/P22-dimensions-20260912/`.

**El Problema 4 tiene su criterio.** El acuerdo con un target que está genuinamente
adelante ordena cuatro candidatos como lo hace la calidad verificada — **6 de 6 pares
discriminables**, incluido el par que el conteo de parámetros invierte, donde un
modelo de 12B queda debajo de uno de 4B. La mitad honesta: sólo los **17** casos que
el target falló pueden separar el criterio del oráculo, y sobre esos solos da 4 de 6
con dos sin resolver y ninguno invertido, a partir de tres errores reproducidos.
`results/P23-ranking-20260912/`.

**Lo que sigue siendo cierto de los cuatro**: nada de esto se midió fuera de mecánica
de fluidos, y la regla escrita a mano con la que empata un protocolo aprendido son 144
líneas que conocen el vocabulario de esta suite. **La portabilidad es el experimento
sin comprar**, y es aquel del que realmente depende el empate del Problema 1.

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

## Problema 3 — un especialista que no siente el borde de lo que sabe

**Éste es el problema que bloquea el producto, y va enunciado completo acá para que
se lo pueda entregar a alguien sin ningún otro contexto.**

### Lo que vemos

Entrenamos un especialista con seis tipos de problema de mecánica de fluidos y
después le dimos dos que nunca había visto — misma materia, mismo estilo de
consigna, difieren sólo en qué relación física hace falta.

Puntuando sus **fórmulas** y no su aritmética: **30 de 30** dentro de sus seis
tipos, **1 de 20** en los dos que nunca vio. La caída no es gradual.

Y lo que importa más que el número: **nada en su salida marca la diferencia.** Misma
estructura numerada, misma seguridad, mismo vocabulario plausible. Inventa la
física:

    2. Fracción de volumen: 4/3 * pi/6 = 0.698132
    4. ¿Régimen de Stokes? v*d/(rho*mu) = 3.88*0.304/(998.0*0.001002) = 1.12832 < 1
    6. Fuerza de arrastre F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)

Una "fracción de volumen" que no lo es. Un test de régimen que no es el test de
régimen. Una ley de fuerza que no es la ley de fuerza. El especialista que puntúa
perfecto en su propio material escribió eso, con la misma voz.

**Así que la segunda fase del diseño es una promesa que el sistema no puede
sostener.** Dice "probado en esta región", y el primer pedido de apenas afuera
recibe una respuesta segura y equivocada sin nadie mirando. Peor, y estructural: la
evidencia disponible cuando se toma esa decisión es el registro de dónde el
especialista **fue puesto a prueba**, no dónde **deja de funcionar**. Son conjuntos
distintos, y la diferencia entre ellos es exactamente donde vive la respuesta segura
y equivocada.

### Qué probamos, y qué descartó cada intento

**Preguntarle al modelo cuán seguro está.** No comprado, porque nuestras propias
corridas lo contestan: las respuestas equivocadas llegan con la misma fluidez,
estructura y vocabulario que las correctas. No hay nada visible sobre lo cual
apoyarse.

**Mirar el proceso en vez del modelo.** El especialista trabaja llamando
herramientas, y un harness responde esas llamadas. Fuera de su región nombra
magnitudes que no entiende, así que quizás los fallos de **la capa de herramientas**
marcan el borde que la prosa no marca.

Se listaron seis señales candidatas **antes de mirar ninguna** — llamadas por
problema, llamadas rechazadas, tasa de rechazo, pasos, cadenas sin nada evaluable,
largo de la transcripción — y se revisaron las seis. Una separaba en las dos
configuraciones: **la tasa con que la herramienta rechaza lo que la cadena pide**,
15% adentro contra 63% afuera, clasificando el 86% de los casos con un solo umbral.

**Y falló la confirmación.** Las señales se habían elegido con las respuestas a la
vista y el umbral ajustado sobre los mismos cincuenta problemas que lo puntuaban,
así que se pre-registró una confirmación: dos tipos de problema *nuevos*, umbral
**fijo**. Fuera de la región la herramienta rechaza al **0,18** contra **0,15**
adentro, y el guardia puntúa 0,62 donde el azar es 0,60.

**El 86% era una propiedad de esos dos tipos de problema, no de un borde.** La
dirección barata —leer el proceso en vez del modelo— está agotada: el proceso
tampoco sabe.

### Qué queda, y por qué cada opción es poco atractiva

**Un segundo especialista cuyo desacuerdo marque el borde.** Duplica el costo de
cada pedido custodiado, y sólo detecta un borde donde *otro* especialista resulte
competente — que no es el mismo conjunto que "fuera de la región de éste", y puede
ser una fracción chica.

**Muestrear el modelo caro después del retiro.** La respuesta de la industria;
funciona, y cuesta plata para siempre en cada pedido custodiado, que es el costo que
el retiro existe para eliminar. Convierte un salto en un descuento.

**Achicar las regiones hasta que el borde quede lejos.** Multiplica especialistas y
carga de ruteo, y no elimina el problema — vuelve más raro el primer pedido fuera de
región, y nada menos seguro.

### Qué tiene que satisfacer una propuesta

Cada punto está porque algo que probamos falló ahí.

1. **No consultar al modelo caro en el camino custodiado.** Un guardia que paga
   aquello que reemplazó no es un guardia. Muestrear una fracción fuera de línea es
   otra propuesta, permitida, pero su costo hay que enunciarlo como fracción y
   defenderlo.
2. **No apoyarse en el auto-reporte del especialista.** Medido: las respuestas
   equivocadas son indistinguibles en presentación de las correctas.
3. **No necesitar la respuesta correcta en tiempo de servicio.** Si la tuviera, el
   especialista sobraría.
4. **Tiene que separar "fuera de la región" de "adentro y difícil".** Un detector
   que se dispara con todo problema difícil cuesta rendimiento y lo van a apagar.
5. **Cualquier umbral debe poder fijarse de antemano.** Un umbral ajustado sobre el
   material con el que se lo prueba es el error que mató al último candidato.
6. **Lo bastante barato para correr en cada pedido**, o su tasa de muestreo es parte
   de la propuesta.

### Cómo sabríamos que quedó resuelto

Exactitud separando material en región de material fuera, **sobre tipos de problema
contra los que la propuesta no fue desarrollada y con cualquier umbral fijado de
antemano** — reportada al lado de la tasa con que se dispara en problemas difíciles
pero en región, porque un guardia que no distingue esos dos casos es inusable por
bueno que se vea su titular.

**La vara es baja y nada la superó: nuestro mejor candidato sacó 0,62 donde el azar
era 0,60.**

Los instrumentos existen: problemas con verdad exacta en tipos con los que no se
entrenó ningún especialista, transcripciones cuya corrección se conoce, un juez que
acierta el 82% sin ver la respuesta, y una disciplina de pre-registro que trata a un
candidato encontrado buscando como hipótesis hasta que sobreviva material sobre el
que no fue encontrado.

### La versión angosta de la pregunta

No "cómo sabe un modelo lo que no sabe", que es un programa de investigación, sino:

> Dado un especialista medido como competente sobre un conjunto de ejemplos, y un
> pedido nuevo, ¿hay algo **barato y observable** — en el pedido, en la conducta del
> especialista, en las herramientas que usa, o en comparaciones que no involucren al
> modelo caro — que distinga un pedido que va a resolver de uno que va a contestar
> con seguridad y mal?

Medimos que la respuesta no es la confianza del modelo y no es la tasa de fallo de
la capa de herramientas. No sabemos qué más mirar.

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

**Existe un juez, y eso ya está medido.** Sobre 100 cadenas con corrección conocida
— 33 bien, 67 mal, así que contestar "mal" siempre saca 0,67 — un modelo grande
corrige a **0,89**, balanceado en las dos clases, y un modelo del mismo tamaño que
el corregido llega a **0,82**.

**Y la mitad útil es el par de números del modelo chico.** *Resuelve* este material
a 0,467 y lo *juzga* a 0,82. **Juzgar es más fácil que resolver**, por mucho, para
el mismo modelo sobre los mismos problemas. Eso es lo que vuelve construible el
bucle de mejora después de que el modelo caro se va: la nota no tiene que venir de
algo capaz de haber hecho el trabajo.

**Una combinación es mejor que cualquiera de los dos jueces solo.** Una comprobación
puramente mecánica —re-ejecutar la aritmética de la propia cadena y preguntar si su
respuesta se sigue— acepta el 94% del trabajo correcto y sólo el 52% del incorrecto,
el perfil de error opuesto al del juez modelo. Exigir que **los dos** acepten baja la
falsa aceptación de trabajo equivocado que se ve limpio de **41% a 2%**, a cambio de
seis puntos de trabajo correcto, y sale casi calibrada.

**Lo que seguimos sin saber es el caso que más importa.** El modelo grande juzga bien
acá en parte porque puede *resolver* este material — saca perfecto en él. Donde nada
disponible pueda resolver el trabajo, juzgar queda sin probar, y ése es justamente el
dominio donde un especialista valdría la pena. Nada en estas corridas habla de eso.

**Y seleccionar no es acertar.** Un juez que acierta el 82% de las veces puede
ordenar dos candidatos al revés. Sobre pares con brecha real la conjunción los ordena
bien, pero son dos pares, y los candidatos no los produjo un bucle de mejora — así
que nada muestra que la selección repetida converja, ni que un bucle optimizando esta
nota no aprenda a satisfacer a los dos jueces estando equivocado.

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
  una brecha real entre el modelo caro y el chico, y un juez contra el cual
  compararlo. La prueba anterior se corrió contra casi-iguales, donde no había nada
  que ordenar. El instrumento existe y el material existe, y esto lleva listado acá
  el tiempo suficiente como para dar vergüenza.
- **Medir la tasa de aceptación que le da nombre al diseño.** La arquitectura se
  apoya en cuán seguido un modelo chico produce exactamente lo que produciría uno
  grande, y nunca la calculamos — sustituimos por un acuerdo más grueso a nivel de
  respuesta porque modelos de familias distintas cortan el texto distinto. Dentro de
  una misma familia la versión fina es medible, tenemos los modelos, y nunca se
  compró. Es el hueco más conspicuo del proyecto.
- **Prohibir de plano la llamada malformada.** Un pedido a una herramienta se puede
  volver sintácticamente imposible en vez de meramente improbable, restringiendo qué
  le está permitido escribir al modelo en cada paso. Se dejó de lado cuando la
  sintaxis no era el fallo dominante; desde entonces costó 19 de 118 pedidos en una
  corrida, que es otro argumento distinto del que la archivó.
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
