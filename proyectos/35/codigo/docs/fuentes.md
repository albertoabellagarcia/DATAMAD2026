# Fuentes de datos y licencias

**Fecha:** 14/11/2026. Una ficha por fuente. Este repositorio no contiene datos: la orden `uv run cercasalud fetch` descarga las fuentes del catálogo en una versión fechada, con un manifiesto por archivo (URL, fecha, bytes, SHA-256, organismo y licencia).

**Estado de uso:**
- **Implementado:** el código del repositorio lo usa.
- **Previsto:** está en la especificación, sin código todavía.
- **Sin uso:** se descarga o se documenta, pero ningún cálculo lo usa.

Las atribuciones obligatorias están en el `README.md`.

## Resumen

| # | Fuente | Organismo | Licencia | Estado de uso |
|---|---|---|---|---|
| 1 | Centros, servicios y establecimientos sanitarios | Comunidad de Madrid | CC BY 4.0 | Implementado (A) |
| 2 | Zonas básicas de salud | Comunidad de Madrid | CC BY 4.0 | Sin uso |
| 3 | Población por sección censal y edad (tabla 69213) | INE | CC BY 4.0 | Implementado (demanda) |
| 4 | Secciones censales 2025 (polígonos) | INE | CC BY 4.0 | Implementado (demanda) |
| 5 | Atlas de Distribución de Renta de los Hogares 2024 | INE | CC BY 4.0 | Previsto (C) |
| 6 | Personas que viven solas | Ayuntamiento de Madrid | CC BY 4.0 | Previsto (contexto) |
| 7 | IGUALA, vulnerabilidad territorial | Ayuntamiento de Madrid | CC BY 4.0 | Previsto (contexto) |
| 8 | Recursos de Protección Civil | Ayuntamiento de Madrid | Condiciones generales de reutilización del Ayuntamiento | Sin uso (se descarga) |
| 9 | CALORMAD 2026 y su Anexo VIII | Ayuntamiento de Madrid | Aviso legal de madrid.es (cita de fuente y autor) | Previsto (B, candidatos) |
| 10 | Equipamientos municipales | Ayuntamiento de Madrid | CC BY 4.0 | Implementado (B: horarios y coordenadas de los mercados, vía `curado/refugios_mercados_madrid.csv`) |
| 11 | Mercados municipales con aire acondicionado | Ayuntamiento de Madrid | Aviso legal de madrid.es: uso libre citando la fuente y el autor | Implementado (B, situación inicial en Madrid capital) |
| 12 | Barrios (cartografía) | Ayuntamiento de Madrid | **Sin confirmar** | Previsto (contexto); no se publica |
| 13 | Horarios GTFS de seis redes de transporte | CRTM | Licencia de datos abiertos del CRTM | Implementado (A en transporte) |
| 14 | OpenStreetMap, extracto de la Comunidad | Colaboradores de OSM (Geofabrik) | ODbL 1.0 | Implementado (red, demanda y coordenadas curadas de 8 centros y de un mercado: `curado/`, bajo ODbL) |
| 15 | Catastro INSPIRE, edificios | DG del Catastro | Restrictiva | No se usa |
| 16 | Red de Calidad del Aire: estaciones y meteorología | Comunidad de Madrid | CC BY 4.0 | Previsto (contexto) |
| 17 | Informe de vigilancia del calor 2025 | Comunidad de Madrid | Aviso legal de comunidad.madrid | Contexto: cifras citadas |
| 18 | Mapa de la red de refugios climáticos | MITECO | **Sin confirmar** | Solo como pista; no se publica |
| 19 | Páginas municipales de refugios (Coslada, Getafe y Fuenlabrada) | Ayuntamientos | Coslada: **restrictiva**. Getafe y Fuenlabrada: sin revisar | Coslada: previsto (B); cómo usarla depende de su licencia; no se publica |

## 1. Centros, servicios y establecimientos sanitarios

- **Organismo:** Comunidad de Madrid, Consejería de Sanidad.
- **Conjunto:** [datos.comunidad.madrid](https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7), CSV.
- **Qué representa:** el registro regional de centros sanitarios. Hay varias filas por centro (una por oferta asistencial).
- **Uso:** oferta de atención primaria pública (A). El filtro deja los centros de salud y consultorios dependientes del servicio de salud regional.
  - Versión del 13/11/2026: 429 centros de tipo primaria, 422 públicos y 414 públicos con coordenadas.
  - Los excluidos se listan con su motivo.
- **Modificaciones:** se elimina la columna personal `NIF` al leer el archivo.
- **Límites:** no declara sistema de coordenadas; se usa EPSG:25830, inferido y validado. No incluye horarios, profesionales ni capacidad.

## 2. Zonas básicas de salud

- **Organismo:** Comunidad de Madrid, DG de Salud Pública.
- **Conjunto:** se obtiene del conjunto «Covid 19 - TIA Zonas Básicas de Salud», con cobertura temporal de 2020 a 2022. Es un ZIP con shapefile.
- **Uso:** ninguno. Una métrica secundaria de A (el centro de la zona asignada) está propuesta, pero depende de comprobar que la zonificación está vigente.
- **Límites:** puede no reflejar la zonificación actual.

## 3. Población por sección censal y edad (INE, tabla 69213)

- **Uso:** población residente por sección y edad. Periodo 2025, sexo «Total»; se agrega en mayores de 65, 75 y 85 años.
- **Comprobaciones:** 4.518 secciones con dato y 7.113.886 habitantes en la Comunidad. La suma por sección cuadra con los agregados municipales y provinciales del INE.
- **Límites:** 48 códigos de sección no tienen dato en 2025 ni polígono. Se documentan sin imputar en `codigos_ine_sin_poligono.md`.

## 4. Secciones censales 2025 (INE)

- **Descarga:** servicio WFS del INE, provincia 28, en EPSG:25830.
- **Uso:** geometría de las secciones. Solo se usan los polígonos de tipo sección: la capa trae también polígonos de distrito, que se solapan.
- **Comprobación:** las 4.518 secciones con población tienen su polígono.

## 5. Atlas de Distribución de Renta de los Hogares 2024 (INE)

- **Descarga:** servicio ArcGIS del INE, secciones de la provincia 28.
- **Uso previsto:** estratificar las carencias coincidentes (C) por renta, sin índice compuesto. La renta de la sección no es la renta de cada persona.
- **Estado:** adquirido; sin perfilar ni enlazar con la población.

## 6. Personas que viven solas (Ayuntamiento de Madrid)

- **Conjunto:** [datos.madrid.es, 300431](https://datos.madrid.es/dataset/300431-0-personas-viven-solas), XLSX.
- **Uso previsto:** solo como capa de contexto por barrio, fuera de cualquier puntuación. Vivir solo no equivale a soledad no deseada.

## 7. IGUALA, índice de vulnerabilidad territorial (Ayuntamiento de Madrid)

- **Conjunto:** [datos.madrid.es, 300577](https://datos.madrid.es/dataset/300577-0-iguala-vulnerabilidad), cobertura de 2020 a 2023.
- **Uso previsto:** solo como capa de contexto por barrio, fuera de cualquier puntuación.

## 8. Recursos de Protección Civil (Ayuntamiento de Madrid)

- **Descarga:** geoportal municipal, ZIP con shapefile: 249 recursos más 11 de gran capacidad.
- **Uso:** ninguno en el código. Los recursos coinciden con los del Anexo VIII del CALORMAD (ficha 9).
- **Límites:** el horario está truncado en parte de los registros, y varios campos no tienen significado documentado. Antes de publicar un derivado hay que comprobar que los teléfonos y correos son institucionales.

## 9. CALORMAD 2026 y su Anexo VIII (Ayuntamiento de Madrid)

- **Documento:** [plan municipal ante altas temperaturas](https://www.madrid.es/UnidadWeb/Contenidos/ContenidoGenerico/PlanesEmergencia/olacalor8.pdf), PDF de 130 páginas.
- **Qué es el Anexo VIII:** una lista **informativa** de 260 instalaciones municipales que «se podrían utilizar» como refugio climático en una emergencia. Para cada una da la disponibilidad, la climatización, el aforo y si abre en fin de semana. No es una red de refugios abiertos con horario.
- **Uso previsto:** candidatos a activar en una emergencia. No sirve como situación inicial de refugios abiertos. El encuadre está pendiente de confirmar en la especificación.
- **Atribución:** «Fuente: Ayuntamiento de Madrid, CALORMAD 2026».

## 10. Equipamientos municipales (Ayuntamiento de Madrid)

- **Conjuntos:** equipamientos y entidades de la ciudad; centros culturales, de mayores y de día; bibliotecas (datos.madrid.es).
- **Uso previsto:** horario del edificio de los refugios y candidatos a activar.
- **Límites:** los CSV están en CP1252. El horario es el del edificio, no el de un uso como refugio. No se asume gratuidad, acceso general ni climatización.
- **Licencia:** CC BY 4.0. Así lo declaran las fichas de los cuatro conjuntos temáticos y la del conjunto general [«Equipamientos y entidades de la ciudad de Madrid»](https://datos.madrid.es/dataset/300331-0-equipamientos-municipales), del que se toman los horarios de los mercados.

## 11. Mercados municipales con aire acondicionado en zonas comunes (Ayuntamiento de Madrid)

- **Página:** madrid.es, «Mercados con aire acondicionado en zonas comunes»: 43 mercados. El Ayuntamiento los ofrece en verano «para que los ciudadanos puedan resguardarse» (nota municipal del 28/05/2026).
- **Uso previsto:** base de la situación inicial de refugios en Madrid capital. El horario comercial de cada mercado se toma de la ficha 10.
- **Límites:**
  - La página no muestra fecha.
  - El horario comercial no acredita el horario de acceso a la zona común climatizada.
    - Dentro del horario comercial, el acceso se estima con un supuesto explícito.
    - Fuera de él no se presume.
    - Siempre se muestra también la cobertura acreditable sin el supuesto. Si es casi nula, se explica como cobertura documental insuficiente, no como ausencia de servicio.
  - La página incluye datos de contacto que no se reutilizan.
- **Licencia:** el [aviso legal de madrid.es](https://www.madrid.es/portales/munimadrid/avisoLegal.html) permite usar libremente la información del portal, «indicando la fuente y el nombre del autor». Fuente: Ayuntamiento de Madrid.

## 12. Barrios (Ayuntamiento de Madrid)

- **Uso previsto:** unir las capas de contexto por barrio.
- **Licencia:** sin confirmar. No se publica ningún derivado hasta confirmarla.

## 13. Horarios GTFS de seis redes de transporte (CRTM)

- **Conjuntos:** Metro, Metro Ligero, Cercanías, EMT, autobuses interurbanos y autobuses urbanos de los demás municipios. Son seis conjuntos del catálogo de datos abiertos de la Comunidad de Madrid, publicados por el CRTM en ArcGIS.
- **Uso:** tiempos de viaje en transporte público a la atención primaria (A), con R5.
- **Modificaciones:** el GTFS de Metro se publicó el 30/05/2025 y su calendario acaba el 27/05/2026. Se extiende el calendario hasta el periodo de cálculo como supuesto declarado («horario tipo de Metro»). Los demás se usan sin cambios.
- **Licencia:** la del CRTM. Exige «Powered by CRTM» con enlace, no sugerir respaldo y mantener actualizada la información mostrada; cómo cumplir esto último está pendiente de definir. El GTFS de la EMT que se usa es la copia publicada por el CRTM, no el del portal de la EMT.

## 14. OpenStreetMap, extracto de la Comunidad de Madrid (Geofabrik)

- **Descarga:** extracto del 12/11/2026. El md5 publicado por Geofabrik coincide con el calculado.
- **Uso:**
  - red viaria y peatonal para R5;
  - edificios residenciales y suelo residencial, para repartir la población de cada sección en una malla de 100 m.
- **Licencia:** ODbL 1.0. Las bases de datos derivadas que se publiquen van solo bajo ODbL.

## 15. Catastro INSPIRE, edificios

- **No se usa.** La licencia solo autoriza derivados que sean «una obra diferente», y los metadatos del servicio exigen solicitud previa para distribuir información modificada. La alternativa es OSM (ficha 14).

## 16. Red de Calidad del Aire: estaciones y datos meteorológicos (Comunidad de Madrid)

- **Uso previsto:** solo como contexto térmico. No se presenta como temperatura por calle.

## 17. Informe de vigilancia de los efectos del calor 2025 (Comunidad de Madrid)

- **Documento:** [PDF](https://www.comunidad.madrid/docs/assets/2025/11/24/informe_morbi_mortalidad_calor_temporada_2025.pdf), Dirección General de Salud Pública.
- **Uso:** contexto del problema. Estima 383,42 muertes atribuibles a temperaturas extremas entre el 1/06 y el 15/09/2025 (tabla 5, p. 10). Es un estudio observacional, y no permite estimar efectos de esta herramienta.

## 18. Mapa de la red de refugios climáticos (MITECO)

- **Qué es:** 63 registros de la Comunidad de Madrid, extraídos de un mapa web. No es un conjunto de datos abierto, y el propio MITECO indica que los requisitos están «en fase de verificación».
- **Uso:** solo como pista para localizar listas municipales oficiales. No se publica ningún registro.

## 19. Páginas municipales de refugios climáticos

- **Coslada** (nota del 10/07/2026): siete espacios climatizados, con horario por centro y día. Es la primera lista oficial con horario fuera de la capital.
- **Getafe** (nota del 01/07/2026): centros cívicos y Espacio Getafe Joven, sin horario por centro en el texto leído.
- **Fuenlabrada:** solo una moción para reforzar la red, sin lista.
- **Licencia:**
  - El [aviso legal de Coslada](https://coslada.es/legal/) exige el consentimiento expreso del Ayuntamiento para reproducir o comunicar públicamente los contenidos de su web, así que la lista no se publica.
  - Los avisos de Getafe y Fuenlabrada no se han revisado.
  - No se publica ningún derivado.
