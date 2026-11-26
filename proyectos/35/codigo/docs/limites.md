# Límites de CercaSalud MAD

**Fecha:** 14/11/2026. **Versión de datos:** `20261113T190802Z`. Este documento reúne lo que la herramienta **no** mide, lo que queda fuera de la entrega y los supuestos con más peso en los resultados. Cada cifra que se cita tiene su archivo de origen en `datos/procesados/20261113T190802Z/`.

## Qué mide y qué no

- **Mide la proximidad física potencial** a un centro de primaria pública y, con calor, a un refugio climático abierto.
- **No mide** citas, capacidad, listas de espera, calidad asistencial, uso real ni efectos sobre la salud. Ninguna salida habla de pacientes, de salud ni de mortalidad.
- **«Sin opción verificada» no es «sin acceso».** Significa que, con los supuestos indicados, no hay un recurso verificado dentro del umbral.
- **«No evaluable»** lleva siempre su motivo:
  - `conexion`: la unidad no engancha a la red;
  - `inventario`: no hay lista oficial de refugios verificada;
  - `horario`: el horario no consta;
  - `motor`: sin cálculo de transporte.

## Demanda

- **Población:** INE 2025 por sección y edad. Los totales se conservan con tolerancia 10⁻⁶.
- **Posición dentro de la sección:** es una estimación, con la población repartida por la superficie de planta residencial de OpenStreetMap. No son hogares.
- **Edificios mal clasificados:** 1.557 edificios claramente no residenciales (culto, enseñanza, deporte, administración…) y 278 ambiguos cuentan como vivienda por estar en zona residencial. Recalculada toda la cadena sin ellos (escenarios del 15/11), las zonas propuestas de primaria son las mismas o la celda contigua, con beneficios que varían menos de un 0,3 %, y los totales cambian en cientos de personas. Pueden deformar casos locales (p. ej., el Palacio de Liria). La corrección está calculada, pero no aplicada a la base (`fases/H2_demanda_red/edificios_no_residenciales/INFORME.md`).
- **Elección de mercados en B1** (comparación dentro de cada escenario, 15/11):
  - **Población total, cartera de 3:** estable (Pacífico, Prosperidad y Villaverde Alto en la base y en los dos escenarios de edificios); el siguiente mercado, Maravillas, queda entre un 1,5 % y un 3,0 % por debajo de la ganancia en la peor hora. El reparto de horas entre Pacífico y Villaverde Alto es indiferente.
  - **75+, un solo mercado:** empate entre Pacífico y Prosperidad (0,6 %); pequeñas perturbaciones los alternan.
  - **75+, cartera de 3:** el tercer mercado es un empate entre Santa María de la Cabeza y Argüelles (0,3 %).
  - Las diferencias de unos pocos puntos no se han comparado con la incertidumbre de los supuestos de B.
- **Transporte:** se calcula desde el centro de gravedad residencial de cada sección, no desde cada unidad.

## Primaria (A)

- **Inventario:** filtro de la SPEC (R-DAT-02), con 422 centros.
  - **Coordenadas:** 8 vienen de OSM. Dos consultorios rurales (Villar del Olmo y Gargantilla del Lozoya) tienen precisión de calle.
  - **Centros públicos fuera del filtro:** cinco centros con dependencia patrimonial del Servicio Madrileño de Salud quedan fuera por la dependencia funcional; figuran como centros del SERMAS en funcionamiento en las fichas oficiales consultadas el 14/11. Sevilla la Nueva sale entera sin opción por esa causa. El escenario «inventario ampliado» lleva los cinco desde el 15/11: a pie, 19.131 personas más con acceso que con tres, todas en Madrid capital; en transporte no cambia. La ampliación (A2) se aceptó el 15/11, pero la base sigue con 422 centros hasta que se recalcule. Coordenadas de los cinco: las del registro; en CS17064 y CS19640 difieren 376 m y 195 m de la ficha oficial.
- **Horario de los centros:** se supone que abren en la franja calculada. No se ha contrastado con una muestra de fichas (F-05).
- **Franjas de transporte:** laborable de 9 a 13 h (base de las cifras) y de 16 a 20 h (escenario `franja_16_20` y criterio estricto `ambas_franjas`). La de tarde se incorporó el 14/11 y sus resultados dependen de que termine su cálculo.
- **Horario de los centros (revisión del 23/11/2026, sin recalcular A, por decisión del usuario):** el cálculo supone que los 422 centros abren en las dos franjas.
  - Según el horario que publican las webs del SERMAS (`fases/H3_situacion_inicial_A/horarios_centros_20261123/`), 6 no abren de 16 a 20 h: los centros de salud de Campo Real, Perales de Tajuña, Torrelaguna y Villarejo de Salvanés, y los consultorios de Villaconejos y Valdelaguna.
  - Otros 10 centros rurales publican «de 8 a 21», pero su ficha dice que desde las 15 h funcionan como atención continuada (urgencias), no como consulta ordinaria.
  - 152 centros no publican horario, 145 de ellos consultorios.
  - La franja de tarde sobrestima el acceso en esos municipios. No hay horario de verano publicado por centro.
- **Metro:** horario tipo con el calendario extendido (D-27). Es un supuesto declarado.
- **Matriz de transporte en Madrid capital:** puede ser algo optimista. Reconstruidos con los horarios GTFS completos (frecuencias incluidas) y hasta un transbordo, los 4 casos urbanos más dudosos quedan de 0,3 a 3,4 min por encima de la matriz, sin cambiar ningún estado (la mediana más alta, 21,4 min, frente a un umbral de 30). Se publican escenarios de +2, +4 y +6 min. Una primera comprobación del 14/11 no leía las frecuencias y exageraba la diferencia.
- **El modo transporte incluye ir andando.**
- **Borde regional:** no hay centros de comunidades limítrofes en los datos (P-23).
- **Métrica de zona básica de salud (P-07):** fuera de la entrega. La cartografía disponible es de 2020–2022.
- **Rutas frente a línea recta:** medir en línea recta sobrestimaría en 1,02 millones de personas el acceso a pie (cociente red/recta: mediana de 1,32).
- **Mapa de minutos (pantalla 2, P-27):** en transporte, todas las celdas de una sección comparten el tiempo de su centro residencial. En las secciones sin matriz de transporte (todas sus unidades llegan a pie en 20 min o menos) vale el tiempo a pie: el transporte podría acortarlo, así que las clases por debajo de 20 min pueden ser algo pesimistas. El reparto por clases no cambia ningún estado: en las unidades evaluables, «minutos ≤ umbral» coincide con «con acceso» en todas (comprobado al preparar las capas: 0 discrepancias en las tres variables). La población de cada celda es una estimación (reparto por edificios residenciales).
- **Mapa de la página web (P-28), por secciones:** cada sección se colorea con la mediana de minutos de su población (ponderada), así que dentro de una sección grande puede haber zonas más cerca y más lejos que el color. Las barras de la leyenda cuentan la población exacta por tramo. «Qué cambia» marca las secciones donde alguien gana opción, no cuánta gente: la tarjeta da las personas.
- **Refugios en el desglose en 3D:** horas al día (12 a 21 h, laborable de julio, cota central) con refugio a 10 min, media de la sección. Supone acceso en horario comercial (D-33).
- **Método de demanda:** con el punto interior de cada sección en vez de la malla residencial, 520 de 4.518 secciones cambian de estado (R-DEM-04).

## Refugios (B)

- **Territorio:** solo Madrid capital (43 mercados municipales con aire acondicionado en zonas comunes).
  - Coslada está documentada, pero queda fuera del cálculo público hasta aclarar su licencia (D-30).
  - En el resto de municipios, B es no evaluable (inventario). **Que no haya lista verificada no significa que no haya refugios.**
- **Acceso a la zona climatizada:** no consta en ninguno de los 43 mercados.
  - El resultado central supone acceso durante el horario comercial (D-33).
  - Sin ese supuesto, la cobertura acreditable es nula. Es **cobertura documental insuficiente**, no ausencia de servicio.
- **Horarios:**
  - **Origen y revisión:** son de las fichas municipales, con una segunda lectura del mismo agente. La segunda codificación independiente del 20 % (R-TMP-01) está pendiente del usuario.
  - **Agosto:** las fichas no declaran cierres, así que el laborable de julio y el de agosto usan el mismo horario.
  - **Domingo:** casi siempre «no figura». El fin de semana queda sobre todo pendiente, y por eso tiene cotas tan separadas.
- **Laborable:** cuenta como abierto solo si abre de lunes a viernes; manda el día más restrictivo.

## Refugios ampliados (decisión del usuario del 22/11/2026)

- **Qué son:** además de los 43 mercados, el mapa señala otros espacios frente al calor de Madrid capital, cada uno con su tipo y su **nivel de evidencia**. Etapa `refugios_ampliados`; método en el docstring de `src/cercasalud/refugios_ampliados.py`.
  - **Verificado:** los 43 mercados (la base de B, sin cambios).
  - **Con respaldo oficial:** las bibliotecas municipales y los cinco museos municipales que el CALORMAD 2026 declara climatizados (p. 86 del PDF), y los recursos del Anexo VIII con climatización «Sí». **El Anexo VIII es un inventario potencial de emergencia, no una red abierta a diario.**
  - **Potencial, no verificado:** museos, cines y centros comerciales de OpenStreetMap; bibliotecas de la Comunidad de Madrid; recursos del Anexo VIII con climatización parcial o en blanco; servicios sociales y juntas de distrito (horario administrativo).
- **Las cifras no se mezclan.** Hay tres líneas:
  - solo verificados;
  - con respaldo oficial, donde **solo cuentan como abiertos los espacios con horario de verano curado**: las 36 bibliotecas municipales y otros 48 espacios (39 centros culturales, 7 centros de mayores, una sala de estudio y el Museo de Arte Contemporáneo). Los otros 109 se señalan, pero su entorno queda no evaluable. Fuera de las bibliotecas, **el acceso es un supuesto** (los centros de mayores son para personas mayores; los deportivos, de pago), como en los mercados (D-33), y no entra en la cobertura acreditable;
  - máximo posible si todos fueran refugios, que **es un techo y no un dato**: supone abiertos a todas horas y con acceso libre todos los espacios, también los de pago (cines, piscinas cubiertas, museos de pago).
- **Horario de los otros espacios con respaldo** (codificación explícita en `fases/H4_situacion_inicial_B_C/refugios_ampliados_20261122/codificacion_respaldo.py`, lectura única de Claude): solo se codifica el verano cuando el texto lo trata y solo el horario «del centro» (no el de secretaría). Si el texto no dice nada del verano, queda pendiente: la nota municipal del 28/05/2026 indica que solo algunos centros de mayores abren a diario en julio y agosto, así que el horario general no vale para el verano. Muchos centros culturales cierran en agosto: la cobertura con respaldo de agosto es menor que la de julio. De los cinco museos municipales solo se pudo leer la página oficial del Museo de Arte Contemporáneo (madrid.es y la del Planetario rechazan las lecturas automáticas); cierra los lunes, así que en «laborable» cuenta como cerrado. Los centros deportivos solo publican el horario de taquilla: quedan pendientes.
- **Horario de las bibliotecas:** de su ficha en datos.madrid.es, vigente al inventariar (13/11/2026); el de verano es el que la ficha declara (del 15 de junio al 15 de septiembre). Lectura única de Claude, sin segunda codificación. Las 7 que abren el fin de semana cierran 7 de los 9 fines de semana de julio y agosto: el fin de semana de verano se codifica cerrado. En verano cierran a las 20 h, así que **en la peor hora (de 20 a 21 h) no cambian la cobertura**; sí la cambian a lo largo del día.
- **OpenStreetMap:** ubicación aportada por sus colaboradores, sin fuente oficial de climatización, horario ni acceso libre; puede faltar o sobrar algún espacio. Los cinco museos municipales se localizan en OSM por su nombre.
- **Capas aparte, que no son refugio:** parques y zonas verdes (OSM; el CALORMAD, §3.3, los cuenta entre las zonas especialmente sensibles al calor), fuentes de agua operativas y piscinas municipales al aire libre (de pago, en temporada). No entran en ninguna cifra.
- **Zonas verdes de toda la Comunidad (23/11/2026):** 6.579 zonas de OSM en cuatro clases: parque, jardín público, área recreativa y monte o bosque. Sus límites:
  - «Monte o bosque» es cubierta del suelo, y muchas fincas privadas no declaran su acceso en OSM: no acredita que se pueda entrar.
  - Se excluyen el Monte de El Pardo (acceso restringido en su mayor parte; OSM no delimita la parte abierta), los espacios protegidos completos (por ejemplo, el Parque Natural Los Cerros de Alcalá), el césped urbano y los jardines sin nombre dentro de zonas residenciales.
  - La Casa de Campo figura como monte o bosque porque así está etiquetada en OSM.
  - La regla depende del etiquetado de OSM: un parque mal etiquetado puede faltar.
- **Horario general publicado:** cuando un espacio no tiene horario de verano curado, la ficha muestra el horario general de su fuente (datos.madrid.es o `opening_hours` de OSM), avisando de que no es el de verano. No entra en ninguna cifra.
- **Fuera de la ampliación:** centros de día, enseñanzas artísticas, espacios de igualdad, información juvenil y el recinto ferial del Anexo VIII (no estaban en la lista aceptada); hospitales y centros de salud (son el recurso de A); grandes almacenes, supermercados y hoteles. Los centros de acogida para personas sin hogar se aceptaron, pero no se han incluido: no hay una fuente con su ubicación adquirida.
- **Bibliotecas públicas del resto de la Comunidad (decisión del usuario del 23/11/2026), solo en el mapa:** del directorio de bibliotecas de la Comunidad de Madrid (CC BY 4.0), las 162 de punto fijo fuera de Madrid capital (las universitarias, escolares y especializadas no son espacios abiertos al público). El directorio no trae coordenadas: cada una se casa con una biblioteca de OpenStreetMap de su municipio, «segura» si el nombre coincide (69) o «probable» si es la única biblioteca pública del municipio en las dos fuentes (25). Las 68 restantes no se ubican (en 25 municipios OSM no tiene ninguna; en el resto, ninguna con nombre que coincida); su lista y su motivo están en `refugios_ampliados/bibliotecas_comunidad_sin_ubicar.csv`. Nivel «potencial»: la climatización no consta y su horario de verano no está curado. **No son destino de R5 ni entran en ninguna línea:** fuera de la capital, B sigue no evaluable. El CSV escribe «l A» como «L-» en 34 nombres y una localidad («RafaeL-lberti»); se corrige con una regla explícita.
- **«Probar un refugio» en la página web (decisión del usuario del 23/11/2026):** para cada espacio ya inventariado que no es mercado, las personas de Madrid capital sin refugio en la peor hora (de 20 a 21 h, laborable de julio; base de los 43 mercados verificados, con el supuesto D-33) que lo tendrían a 10 min a pie **si ese espacio abriera de 12 a 21 h con acceso libre**, y cuántas de ellas no tienen hoy refugio a ninguna hora. Usa los pares de la etapa `refugios_ampliados` (sin cálculo nuevo). Es un supuesto: la mayoría de esos espacios no acredita climatización ni acceso libre, y algunos son de pago (cines, centros comerciales). El primero de la lista, un cine, lo muestra: la cifra mide lo que pasaría si abriera, no una recomendación. Las cifras de dos espacios no se suman. Dos espacios en el mismo edificio dan la misma cifra y se dibujan uno encima del otro.

## Carencias coincidentes (C)

- Solo donde A y B son evaluables en la misma unidad, es decir, en Madrid capital.
- La franja de referencia de B es la peor hora del laborable de julio (cota central).
- **C apenas depende de la hora elegida para B.** Con A en transporte, son 25.300 personas en todas las horas y tipos de día.
- **Prueba de integración (R-BCH-02):** C prioriza casi los mismos barrios que A sola (Jaccard de 0,82 a 1,00), porque la cobertura de B es baja a cualquier hora. Con los datos actuales, la integración no cambia el orden de prioridades.
- **Renta (ADRH 2024):** quintiles de población por sección; es estratificación, no causa. El porcentaje sin acceso en transporte sube con la renta. El año de referencia de los ingresos no figura en la capa.
- **Capas de contexto (personas solas por barrio e IGUALA por distrito):** solo contexto; no intervienen en ningún cálculo.

## Actuaciones (H5)

- **Zonas de búsqueda de A:** son celdas de 250 m con población residencial, no solares ni edificios.
- **«Probar una zona» en la página web (decisión del usuario del 23/11/2026):** da, para cada zona de búsqueda, las personas sin opción verificada que tendrían un centro dentro del umbral si se abriera uno **solo en esa zona**, a pie y en transporte de 9 a 13 h. No calcula tiempos nuevos: usa los mismos pares y funciones de cobertura que `build`, y la mejor zona coincide con la cartera de una zona del MILP en las cuatro combinaciones (a pie y en transporte, total y 65+; comprobado en la exportación y en un test). Las cifras de dos zonas **no se suman**, porque pueden compartir personas; para varias zonas vale la cartera calculada. Solo se pueden probar las zonas de búsqueda, no un punto cualquiera (haría falta R5 en vivo). Zonas vecinas dan cifras muy parecidas (la segunda mejor a pie, 37.111 frente a 37.632). La capa omite las zonas que ganan menos de media persona; el puesto y el total («de 11.309 zonas») las cuentan, como el MILP.
- **Presupuesto:** se cuenta en número de actuaciones, no en euros. No se compara coste ni efectividad.
- **A en transporte:** la cartera de 5 zonas elige una en Sevilla la Nueva por el filtro de inventario; con el inventario ampliado, su ganancia baja de 68.807 a 60.917. Reoptimizada con ese inventario, cambia esa zona por una segunda en Boadilla del Monte y gana 68.754. Con el p80 o con márgenes de 4–6 min, la ganancia de las carteras de 3 y 5 zonas baja entre un 25 y un 40 %.
- **Fuera de la entrega:** B2 (activar candidatos; D-34). El contraste con la enumeración exhaustiva se hizo en 168 instancias reales pequeñas a pie, no en transporte.
- **Robustez con otras velocidades:** reescala los tiempos a pie de 3,0 km/h (R5 calcula distancia / velocidad), lo que es una aproximación por el redondeo a minutos. A 2,4 km/h la ganancia es una cota inferior.

## Verificación pendiente (H7)

- Revisión geográfica de 11 rutas a pie con incidencias y de 4 casos urbanos en transporte con más de 4 min de diferencia: en curso (`fases/H7_validacion_documentacion/revision_rutas_20261114/`).
- Reproducción completa del transporte: solo se repite a pie.
- **App sin conexión:** comprobada registrando las peticiones de red del navegador (solo 127.0.0.1), no desconectando la red.
