# moviliMAD · Equipo 8

**Tu asistente de movilidad inclusiva en Madrid. Convertimos los datos abiertos en respuestas y rutas adaptadas.**

https://github.com/user-attachments/assets/4cd542a3-f760-4498-b979-b952985f7afd

- **Demostración (búsqueda y recorrido 3D de una ruta accesible):** https://movilimad.es/app.php?demo=recorrido
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

Cada ficha de la aplicación indica su fuente y enlaza al registro original. Los datos se actualizan a diario.

## Tecnologías abiertas

OpenStreetMap, Leaflet, MapLibre, openrouteservice, Valhalla, CartoCiudad (IGN) y GeoParquet. El código de moviliMAD se publicará como código abierto.
