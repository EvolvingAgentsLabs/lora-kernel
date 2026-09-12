# Un problema abierto: un especialista que no siente el borde de lo que sabe

**Este documento está escrito para entregárselo a alguien — o a algo — sin contexto
previo, con la esperanza de recibir propuestas que no se nos ocurrieron.** Plantea
un problema que medimos, enumera qué probamos y qué descartó cada intento, y dice
con precisión qué tendría que satisfacer una solución y cómo la pondríamos a
prueba. Si lo está leyendo para proponer un enfoque, las dos últimas secciones son
las que lo restringen.

## 1. El escenario, en las palabras que haga falta y ni una más

Un modelo de IA grande es caro de correr. Uno chico es barato y peor. Estamos
probando si se puede llegar a casi lo mismo que el grande teniendo **un solo**
modelo chico en memoria y aplicándole un **parche** diminuto e intercambiable —
unos megabytes de ajustes de pesos que lo hacen comportarse como especialista
mientras está aplicado, y que se sacan en milisegundos.

La economía sólo cierra si en algún momento se puede **dejar de pagar el modelo
grande**. Por eso el diseño tiene dos fases:

- **Fase A.** El modelo grande hace el trabajo. El especialista mira y es puntuado
  por cuán seguido habría producido lo mismo. Ese puntaje se acumula en un mapa de
  *en qué es bueno este especialista*.
- **Fase B.** Donde el mapa dice que el especialista alcanza, el especialista toma
  el control y **el modelo grande se retira para esa clase de trabajo**.

La unidad de esa decisión es una **región** — una clase de tarea en la que el
especialista se probó. La Fase B es todo el punto. Lo demás es andamio.

## 2. El problema

**Un especialista tiene un borde duro y no lo siente.**

Entrenamos un especialista con seis tipos de problema de mecánica de fluidos.
Después le dimos dos tipos que nunca había visto — misma materia, mismo estilo de
consigna, difieren sólo en qué relación física hace falta.

Dentro de sus seis tipos, puntuando sus **fórmulas** (no su aritmética), acierta
**30 de 30**. En los dos que nunca vio, **1 de 20**.

La caída no es gradual. Y esto importa más que el número:

**Nada en su salida marca la diferencia.** Misma estructura numerada, misma
seguridad, mismo vocabulario plausible. Inventa la física:

    2. Fracción de volumen: 4/3 * pi/6 = 0.698132
    4. ¿Régimen de Stokes? v*d/(rho*mu) = 3.88*0.304/(998.0*0.001002) = 1.12832 < 1
    6. Fuerza de arrastre F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)

Una "fracción de volumen" que no lo es. Un test de régimen que no es el test de
régimen. Una ley de fuerza que no es la ley de fuerza. El mismo especialista que
puntúa perfecto en su material escribió eso, con la misma voz.

**Así que la Fase B es una promesa que el sistema no puede sostener.** Dice
"probado en esta región", y el primer pedido de apenas afuera recibe una respuesta
segura y equivocada sin nadie mirando. Peor: la evidencia disponible en el momento
de decidir la Fase B es el mapa de la Fase A, que registra **dónde el especialista
fue puesto a prueba** — no dónde deja de funcionar. Son conjuntos distintos, y la
diferencia entre ellos es exactamente donde vive la respuesta segura y equivocada.

## 3. Qué probamos, y qué descartó cada intento

**Intento 1 — preguntarle al modelo cuán seguro está.** No comprado, porque
nuestras propias corridas ya lo contestan: las respuestas equivocadas llegan con la
misma fluidez, estructura y vocabulario que las correctas. No hay diferencia
visible sobre la cual apoyarse, y la confianza auto-reportada se sabe poco fiable
en general. No es una dirección prometedora y no gastamos en ella.

**Intento 2 — mirar el proceso en vez del modelo.** Ésta fue nuestra idea y pintaba
bien. El especialista trabaja llamando herramientas (una calculadora, una consulta
a tabla, un conversor de unidades), y un harness responde esas llamadas. Fuera de
su región, el especialista nombra magnitudes que no entiende, y la capa de
herramientas tiene que convertir esos nombres en llamadas válidas. Quizás los
fallos de **la capa de herramientas** marcan el borde que la prosa no marca.

Listamos seis señales candidatas **antes de mirar ninguna** — llamadas por
problema, llamadas rechazadas, tasa de rechazo, cantidad de pasos, cadenas sin nada
evaluable, largo de la transcripción — y revisamos las seis sobre transcripciones
ya guardadas. Sólo una separaba en las dos configuraciones probadas: **la tasa con
que la herramienta rechaza lo que la cadena le pide.** Dentro de la región, el 15%
de los pedidos; afuera, el 63%. Un solo umbral clasificaba el 86% de los casos.

**Y después falló la confirmación.** Las señales se habían elegido con las
respuestas a la vista y el umbral ajustado sobre los mismos cincuenta problemas que
lo puntuaban, así que pre-registramos una confirmación: dos tipos de problema
*nuevos* que ninguna corrida había usado, con el umbral **fijo** y no reajustado.
Resultado: fuera de la región la herramienta rechaza llamadas al **0,18**, contra
**0,15** adentro. El guardia puntúa 0,62 donde el azar es 0,60.

**Así que el 86% era una propiedad de esos dos tipos de problema, no de un borde.**
La señal está muerta, y con ella la dirección barata: *leer el proceso en vez del
modelo* era la idea, y el proceso tampoco sabe.

## 4. Qué queda, y por qué cada opción es poco atractiva

**Un segundo especialista, entrenado en otra región; tratar el desacuerdo como
señal de borde.** Plausible, y duplica el costo de cada pedido que custodia.
Además sólo detecta un borde donde *otro* especialista resulte competente — que no
es el mismo conjunto que "fuera de la región de éste", y puede ser una fracción
chica de él.

**Muestrear el modelo grande después de la Fase B y comparar.** Es la respuesta de
la industria y funciona. También cuesta plata para siempre, en cada pedido
custodiado, que es justamente el costo que la Fase B existe para eliminar.
Convierte un salto en un descuento.

**Achicar las regiones hasta que el borde quede lejos.** Vuelve barata la prueba de
cada región y multiplica la cantidad de especialistas y la carga de ruteo, y no
elimina el problema — sólo vuelve más raro el primer pedido fuera de región, y
nada menos seguro.

Ninguna es obviamente correcta. Por eso existe este documento.

## 5. Qué tiene que satisfacer una propuesta

No son preferencias. Cada una está porque algo que probamos falló ahí.

1. **No puede consultar al modelo grande en el camino custodiado.** Un guardia que
   paga aquello que reemplazó no es un guardia. (Muestrear *una fracción* fuera de
   línea es otra propuesta y está permitida, pero entonces su costo hay que
   enunciarlo como fracción y defenderlo.)
2. **No puede apoyarse en el auto-reporte del especialista.** Medido: las
   respuestas equivocadas son indistinguibles en presentación de las correctas.
3. **No puede necesitar la respuesta correcta en tiempo de servicio.** Si la
   necesitara, no haría falta el especialista.
4. **Tiene que distinguir "fuera de la región" de "adentro y difícil".** Un
   detector que se dispara con todo problema difícil le cuesta el rendimiento al
   despliegue y lo van a apagar.
5. **Su umbral, si tiene uno, debe poder fijarse de antemano.** Un umbral ajustado
   sobre el material con el que se lo prueba es el error que mató a nuestro último
   candidato.
6. **Tiene que ser lo bastante barato para correr en cada pedido**, o su tasa de
   muestreo debe ser parte de la propuesta.

## 6. Cómo probaríamos una propuesta, y con qué contamos ya

Podemos evaluar una propuesta rápido y con honestidad, porque los instrumentos
están construidos:

- **Problemas con respuesta conocida**, generados de fórmulas cerradas, en seis
  tipos "en región" y cuatro tipos con los que no se entrenó ningún especialista.
  La verdad es exacta y está disponible para puntuar, y nunca visible para aquello
  que se puntúa.
- **Especialistas entrenados**, y transcripciones de muchas configuraciones, con la
  corrección de cada cadena ya conocida.
- **Un juez que acierta el 82% de las veces** sin ver la respuesta, más una
  comprobación procedural que re-ejecuta la aritmética de la propia cadena. Exigir
  que los dos acepten atrapa el 98% del trabajo equivocado que se ve limpio, lo que
  puede o no servirle a una propuesta acá.
- **Una disciplina de pre-registro**: señales y umbrales se escriben antes de
  puntuarlos, y un candidato encontrado buscando en un espacio se trata como
  hipótesis hasta que sobreviva material sobre el que no fue encontrado.

**Qué reportaríamos de cualquier propuesta:** su exactitud separando material en
región de material fuera, sobre tipos de problema contra los que no fue
desarrollada, con cualquier umbral fijado de antemano — y la tasa con que se
dispara en problemas difíciles pero en región, porque un guardia que no distingue
esos dos casos es inusable por bueno que se vea su titular.

**La vara es baja y nada la superó.** Nuestro mejor candidato puntuó 0,62 donde el
azar era 0,60.

## 7. La formulación honesta de la pregunta

No estamos preguntando "cómo hacemos que un modelo sepa lo que no sabe", que es un
programa de investigación. Preguntamos algo más angosto:

> Dado un especialista medido como competente sobre un conjunto de ejemplos, y un
> pedido nuevo, ¿hay algo barato y observable — en el pedido, en la conducta del
> especialista, en las herramientas que usa, o en comparaciones baratas que no
> involucren al modelo caro — que distinga un pedido que el especialista va a
> resolver de uno que va a contestar con seguridad y mal?

Medimos que la respuesta no es la confianza del modelo, y no es la tasa de fallo de
la capa de herramientas. No sabemos qué más mirar.
