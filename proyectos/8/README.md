# moviliMAD · Equipo 8

**Tu asistente de movilidad inclusiva en Madrid. Convertimos los datos abiertos en respuestas y rutas adaptadas.**

https://github.com/user-attachments/assets/4cd542a3-f760-4498-b979-b952985f7afd

- **Demostración (búsqueda y recorrido 3D de una ruta accesible):** https://movilimad.es/app.php?demo=recorrido
- **Disponible en** https://www.moviliMAD.es
- **Presentación (PDF, 4 diapositivas):** [moviliMAD-DATAMAD2026.pdf](moviliMAD-DATAMAD2026.pdf)
- **Presentación interactiva (HTML, con vídeo):** carpeta [presentacion/](presentacion/). Descarga la carpeta completa y abre `index.html` en el navegador; funciona sin conexión. Teclas: flechas o espacio para avanzar, 1–4 para saltar, F para pantalla completa.
- **Vídeo de la aplicación (39 s):** [presentacion/media/demo.mp4](presentacion/media/demo.mp4)
- **Fuentes de datos, con sus registros:** https://movilimad.es/fuentes.php
- **Estadísticas de uso:** https://movilimad.es/estadisticas/
- **Integrante:** Eugenio Serrano Mayor (e.serranom.2020@alumnos.urjc.es)

## Qué es

Para que cualquier persona, especialmente quien tiene movilidad reducida, encuentre el servicio público que necesita y tenga una ruta adaptada para llegar, con distancia y tiempo reales, calculados para su forma de moverse: en silla de ruedas, a pie, en bici o en coche con tráfico real.

moviliMAD saca a la luz recursos públicos que solo están en los datos abiertos y que los navegadores tradicionales excluyen. Entiende preguntas en lenguaje natural, como «desfibriladores cerca de Sol», y muestra sobre un mapa 3D dónde está cada recurso y cómo llegar.

## En cifras (catálogo del 26 de noviembre de 2026)

- **85** conjuntos de datos abiertos de 5 organismos (Comunidad de Madrid, Ayuntamiento de Madrid, Consorcio Regional de Transportes, EMT y Renfe).
- **94** categorías y **61.019** servicios y recursos públicos geolocalizados en los 21 distritos.
- **14** conjuntos de la Comunidad de Madrid y sus organismos de transporte, con **21.915** registros: el **36 %** de lo que muestra el mapa.

## Tecnologías abiertas

OpenStreetMap, Leaflet, MapLibre, openrouteservice, Valhalla, CartoCiudad (IGN) y GeoParquet. El código de moviliMAD se publicará como código abierto.

## Conjuntos de datos de la Comunidad de Madrid

**Portal de datos abiertos (datos.comunidad.madrid)**

| Conjunto | Registros |
|---|---:|
| [Desfibriladores (DEA)](https://datos.comunidad.madrid/dataset/d2478503-a4ae-4753-9540-9200071803c4) | 7.967 |
| [Registro sanitario: clínicas dentales y consultas médicas](https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7) | 5.106 |
| [Centros educativos y FP](https://datos.comunidad.madrid/dataset/c750856d-3166-4dac-8e80-d1b824c968b5) | 2.953 |
| [Oficinas de farmacia](https://datos.comunidad.madrid/dataset/2d682b1d-e2e8-4c6f-b902-7a3f108e2fb9) | 1.811 |
| [Centros de atención social](https://datos.comunidad.madrid/catalogo/dataset/b8cdb7f7-3185-4938-800a-fefda72333f5) | 1.249 |
| [Librerías](https://datos.comunidad.madrid/catalogo/dataset/b155ad55-f386-4afb-a9fa-647f7d17c6c3) | 388 |
| [Áreas recreativas y espacios naturales](https://datos.comunidad.madrid/dataset/cd55d34c-64e2-4ad0-911d-d3e7bdf53a91) | fuera del municipio |

**Consorcio Regional de Transportes y Metro de Madrid**

| Conjunto | Registros |
|---|---:|
| [Estaciones y accesos de Metro](https://www.arcgis.com/home/item.html?id=5c7f2951962540d69ffe8f640d94c246) | 923 |
| [Puntos de venta de la Tarjeta Transporte](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/PtosVenta/FeatureServer/0) | 752 |
| [Paradas de autobuses interurbanos](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M8_Red/FeatureServer/0) | 668 |
| [Aparcamientos disuasorios](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/AparcamientosCM/FeatureServer/0) | 37 |
| [Estaciones de Metro Ligero](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M10_Red/FeatureServer/0) | 30 |
| [Oficinas de la Tarjeta Transporte](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/OOGG/FeatureServer/0) | 16 |
| [Aparcamientos de bicicletas reB](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/Bici_Publica_TP/FeatureServer/0) | 15 |

## Resto de conjuntos de datos

Además de los 14 de la Comunidad de Madrid, moviliMAD integra los conjuntos de datos abiertos del Ayuntamiento de Madrid, la EMT y Renfe.

**Ayuntamiento de Madrid** (67 conjuntos)

| Conjunto | Registros |
|---|---:|
| [Plazas de aparcamiento reservadas PMR](https://datos.madrid.es/egob/catalogo/208083-5-estacionamiento-pmr.csv) | 13.415 |
| [Áreas Infantiles de Juego](https://datos.madrid.es/dataset/200652-0-areas-infantiles/resource/200652-20-areas-infantiles-csv/download/200652-20-areas-infantiles-csv.csv) | 1.971 |
| [Monumentos de Madrid](https://datos.madrid.es/dataset/300356-0-monumentos-ciudad-madrid/resource/300356-5-monumentos-ciudad-madrid-csv/download/300356-0-monumentos-ciudad-madrid.csv) | 1.765 |
| [Fuentes de Agua Potable](https://datos.madrid.es/egob/catalogo/300051-5-fuentes.csv) | 1.536 |
| [Agenda de Actividades y Eventos Municipales](https://datos.madrid.es/egob/catalogo/300107-0-agenda-actividades-eventos.csv) | 1.270 |
| [Agenda de Eventos y Actividades Culturales (Próximos 100 días)](https://datos.madrid.es/egob/catalogo/206974-0-agenda-eventos-culturales-100.csv) | 1.130 |
| [Aparcabicicletas](https://datos.madrid.es/dataset/205099-0-aparca-bicis/resource/205099-22-aparca-bicis-csv/download/205099-22-aparca-bicis-csv.csv) | 1.067 |
| [Puntos de interés turístico](https://datos.madrid.es/egob/catalogo/300030-10037182-puntos-interes-turistico.xml) | 899 |
| [Restaurantes de interés turístico](https://datos.madrid.es/egob/catalogo/300033-10037079-turismo-restauracion.xml) | 868 |
| [Comercios y mercados con perfil turístico](https://datos.madrid.es/egob/catalogo/300034-10037028-turismo-comercio.xml) | 719 |
| [Agenda turística de la ciudad de Madrid](https://datos.madrid.es/egob/catalogo/300028-10037314-agenda-turismo.xml) | 645 |
| [Estaciones de BiciMAD](https://datos.emtmadrid.es/dataset/5fcc0945-2cbd-46c3-801a-6a83f4167c11/resource/bd458215-6265-4941-ab2f-e2bdd849b6c6/download/bikestationbicimad_csv.csv) | 631 |
| [Alojamientos Turísticos](https://www.esmadrid.com/opendata/alojamientos_v1_es.xml) | 608 |
| [Instalaciones Deportivas Básicas](https://datos.madrid.es/dataset/200215-0-instalaciones-deportivas/resource/200215-0-instalaciones-deportivas-csv/download/200215-0-instalaciones-deportivas.csv) | 606 |
| [Puntos de Acceso Wi-Fi Municipal](https://datos.madrid.es/dataset/216619-0-wifi-municipal/resource/216619-0-wifi-municipal-csv/download/216619-0-wifi-municipal.csv) | 546 |
| [Placas conmemorativas (Memoria de Madrid)](https://datos.madrid.es/egob/catalogo/300329-1-placas-conmemorativas-madrid.csv) | 478 |
| [Paradas de Taxi](https://datos.madrid.es/dataset/208094-0-reserva-paradas-taxis/resource/208094-4-reserva-paradas-taxis-csv/download/208094-4-reserva-paradas-taxis-csv.csv) | 474 |
| [Escuelas infantiles privadas y guarderías](https://datos.madrid.es/egob/catalogo/300614-0-centros-educativos.csv) | 430 |
| [Puntos Limpios Móviles](https://datos.madrid.es/dataset/300101-0-puntos-limpios-moviles/resource/300101-0-puntos-limpios-moviles-csv/download/300101-0-puntos-limpios-moviles-csv.csv) | 351 |
| [Templos e iglesias católicas](https://datos.madrid.es/egob/catalogo/209426-0-templos-catolicas.csv) | 350 |
| [Edificios y Palacios Históricos](https://datos.madrid.es/dataset/208844-0-monumentos-edificios/resource/208844-5-monumentos-edificios-csv/download/208844-0-monumentos-edificios.csv) | 342 |
| [Colegios privados y concertados](https://datos.madrid.es/egob/catalogo/300614-0-centros-educativos.csv) | 312 |
| [Ocio nocturno](https://datos.madrid.es/egob/catalogo/300035-10037017-turismo-nocturno.xml) | 308 |
| [Áreas de actividades deportivas en vía pública](https://datos.madrid.es/egob/catalogo/300390-16-areas-deportivas.csv) | 294 |
| [Colegios Públicos](https://datos.madrid.es/egob/catalogo/202311-0-colegios-publicos.csv) | 249 |
| [Actividades Gratuitas en Bibliotecas Municipales (Próximos 60 días)](https://datos.madrid.es/egob/catalogo/206717-0-agenda-eventos-bibliotecas.csv) | 206 |
| [Parques y Jardines Históricos](https://datos.madrid.es/egob/catalogo/200761-0-parques-jardines.csv) | 202 |
| [Áreas Recreativas para Mayores](https://datos.madrid.es/dataset/200637-0-areas-mayores/resource/200637-13-areas-mayores-csv/download/200637-13-areas-mayores-csv.csv) | 198 |
| [Centros de Salud (Atención Primaria)](https://datos.madrid.es/dataset/212769-0-atencion-medica/resource/212769-0-atencion-medica-csv/download/212769-0-atencion-medica.csv) | 176 |
| [Auditorios y Centros Culturales](https://datos.madrid.es/dataset/200304-0-centros-culturales/resource/200304-1-centros-culturales-csv/download/200304-0-centros-culturales.csv) | 129 |
| [Centros Juveniles](https://datos.madrid.es/dataset/200304-0-centros-culturales/resource/200304-1-centros-culturales-csv/download/200304-0-centros-culturales.csv) | 129 |
| [Puntos de Recarga Eléctrica](https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/MOVILIDAD/VEHICULOS_ELECTRICOS/CSV/PUNTOS_PUBLICOS_RECARGA_VEHICULOS_ELECTRICOS.csv) | 119 |
| [Institutos de Educación Secundaria](https://datos.madrid.es/dataset/212790-0-centros-educacion/resource/212790-5-centros-educacion-csv/download/212790-0-centros-educacion.csv) | 114 |
| [Áreas Caninas en Parques](https://datos.madrid.es/dataset/300094-0-areas-caninas/resource/300094-2-areas-caninas/download/300094_20260624_062621.csv) | 113 |
| [Centros Municipales de Mayores](https://datos.madrid.es/dataset/200337-0-centros-mayores/resource/200337-2-centros-mayores-csv/download/200337-0-centros-mayores.csv) | 94 |
| [Centros de Día Municipales](https://datos.madrid.es/dataset/200342-0-centros-dia/resource/200342-0-centros-dia-csv/download/200342-0-centros-dia.csv) | 89 |
| [Centros de Formación Profesional](https://datos.madrid.es/egob/catalogo/300614-0-centros-educativos.csv) | 87 |
| [Centros Deportivos Municipales](https://datos.madrid.es/egob/catalogo/200186-0-polideportivos.csv) | 82 |
| [Centros para personas con discapacidad](https://datos.madrid.es/egob/catalogo/205712-0-centros-discapacidad.csv) | 78 |
| [Escuelas Infantiles Municipales](https://datos.madrid.es/dataset/202318-0-escuelas-infantiles/resource/202318-4-escuelas-infantiles-csv/download/202318-0-escuelas-infantiles.csv) | 77 |
| [Espacios deportivos con interés turístico](https://datos.madrid.es/egob/catalogo/300031-10037140-deporte-turismo.xml) | 74 |
| [Salas de Estudio](https://datos.madrid.es/egob/catalogo/217921-0-salas-estudio.csv) | 70 |
| [Oficinas de Correos](https://datos.madrid.es/dataset/212841-0-oficinas-correos/resource/212841-4-oficinas-correos-csv/download/212841-0-oficinas-correos.csv) | 69 |
| [Museos de la Ciudad de Madrid](https://datos.madrid.es/egob/catalogo/201132-0-museos.csv) | 68 |
| [Comisarías de Policía Municipal](https://datos.madrid.es/dataset/207044-0-oficina-policia/resource/207044-1-oficina-policia-csv/download/207044-0-oficina-policia.csv) | 65 |
| [Comisarías de Policía](https://datos.madrid.es/dataset/300600-0-comisaria/resource/300600-2-comisaria-csv/download/300600-0-comisaria.csv) | 65 |
| [Aparcamientos Públicos](https://datos.madrid.es/dataset/202625-0-aparcamientos-publicos/resource/202625-3-aparcamientos-publicos-csv/download/202625-0-aparcamientos-publicos.csv) | 62 |
| [Piscinas Municipales (Cubiertas y de Verano)](https://datos.madrid.es/dataset/210227-0-piscinas-publicas/resource/210227-0-piscinas-publicas-csv/download/210227-0-piscinas-publicas.csv) | 56 |
| [Bibliotecas Públicas](https://datos.madrid.es/dataset/201747-0-bibliobuses-bibliotecas/resource/201747-1-bibliobuses-bibliotecas-csv/download/201747-0-bibliobuses-bibliotecas.csv) | 53 |
| [Hospitales de Madrid](https://datos.madrid.es/dataset/212769-0-atencion-medica/resource/212769-0-atencion-medica-csv/download/212769-0-atencion-medica.csv) | 53 |
| [Oficinas de Registro Municipal](https://datos.madrid.es/dataset/202139-0-oficinas-registro/resource/202139-2-oficinas-registro-csv/download/202139-0-oficinas-registro.csv) | 47 |
| [Mercados Municipales](https://datos.madrid.es/dataset/200967-0-mercados/resource/200967-4-mercados-csv/download/200967-0-mercados.csv) | 45 |
| [Centros de Servicios Sociales](https://datos.madrid.es/dataset/209094-0-centros-servicios-sociales/resource/209094-1-centros-servicios-sociales-csv/download/209094-0-centros-servicios-sociales.csv) | 40 |
| [Centros de Educación de Adultos](https://datos.madrid.es/dataset/212790-0-centros-educacion/resource/212790-5-centros-educacion-csv/download/212790-0-centros-educacion.csv) | 39 |
| [Centros de Educación Especial](https://datos.madrid.es/egob/catalogo/300614-0-centros-educativos.csv) | 39 |
| [Centros de Salud Mental](https://datos.madrid.es/dataset/212769-0-atencion-medica/resource/212769-0-atencion-medica-csv/download/212769-0-atencion-medica.csv) | 27 |
| [Oficinas de Atención (Línea Madrid)](https://datos.madrid.es/dataset/200149-0-oficinas-linea-madrid/resource/200149-5-oficinas-linea-madrid-csv/download/200149-0-oficinas-linea-madrid.csv) | 26 |
| [Agenda de Actividades Deportivas](https://datos.madrid.es/egob/catalogo/212504-0-agenda-actividades-deportes.csv) | 25 |
| [Universidades y Centros de Estudios](https://datos.madrid.es/dataset/203166-0-universidades-educacion/resource/203166-0-universidades-educacion-csv/download/203166-0-universidades-educacion.csv) | 22 |
| [Centros de Salud Comunitaria (CMSc)](https://datos.madrid.es/dataset/212769-0-atencion-medica/resource/212769-0-atencion-medica-csv/download/212769-0-atencion-medica.csv) | 19 |
| [Puntos Limpios Fijos](https://datos.madrid.es/dataset/200284-0-puntos-limpios-fijos/resource/200284-0-puntos-limpios-fijos-csv/download/200284-0-puntos-limpios-fijos.csv) | 16 |
| [Oficinas de Empleo](https://datos.madrid.es/dataset/212086-0-oficinas-empleo/resource/212086-1-oficinas-empleo-csv/download/212086-0-oficinas-empleo.csv) | 13 |
| [Parques de Bomberos](https://datos.madrid.es/dataset/211642-0-bomberos-parques/resource/211642-3-bomberos-parques-csv/download/211642-0-bomberos-parques.csv) | 13 |
| [Teatros y Espacios Escénicos](https://datos.madrid.es/dataset/208862-7650046-ocio_salas/resource/208862-7650046-ocio_salas-csv/download/208862-7650046-ocio_salas.csv) | 12 |
| [Salas de Cine](https://datos.madrid.es/dataset/208862-7650046-ocio_salas/resource/208862-7650046-ocio_salas-csv/download/208862-7650046-ocio_salas.csv) | 12 |
| [Oficinas de Información Turística](https://datos.madrid.es/dataset/201105-0-informacion-turismo/resource/201105-2-informacion-turismo-csv/download/201105-0-informacion-turismo.csv) | 10 |
| [Centros de Atención a la Infancia (CAI)](https://datos.madrid.es/dataset/205732-0-centros-sin-hogar/resource/205732-1-centros-sin-hogar-csv/download/205732-0-centros-sin-hogar.csv) | 7 |

**EMT Madrid** (1 conjunto)

| Conjunto | Registros |
|---|---:|
| [Paradas de Autobuses de la EMT](https://datos.madrid.es/dataset/900023-0-emt-paradas-autobus/resource/900023-0-emt-paradas-autobus/download/900023-0-emt-paradas-autobus.csv) | 4.945 |

**Renfe** (1 conjunto)

| Conjunto | Registros |
|---|---:|
| [Estaciones de Cercanías Madrid (Renfe)](https://data.renfe.com/dataset/ed3d44e5-1d04-41d6-9aa5-396442bf3e07/resource/783e0626-6fa8-4ac7-a880-fa53144654ff/download/listado-estaciones-completo-act.csv) | 20 |

**Capas del mapa** (2 conjuntos)

| Conjunto | Fuente |
|---|---|
| [Vías ciclistas](https://datos.madrid.es/dataset/205107-0-vias-ciclistas/resource/205107-0-vias-ciclistas/download/205107-0-vias-ciclistas.zip) | Ayuntamiento de Madrid |
| [Intensidad del tráfico en tiempo real](https://datos.madrid.es/dataset/202087-0-trafico-intensidad/resource/202087-0-trafico-intensidad/download/202087-0-trafico-intensidad.xml) | Ayuntamiento de Madrid |

Cada ficha de la aplicación indica su fuente y enlaza al registro original. Los datos se actualizan a diario.
