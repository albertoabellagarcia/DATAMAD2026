# ¿Dónde cabes?

Proyecto para DataMad 2026. Escribes tu sueldo bruto anual y la parte que dedicarías al alquiler, y el mapa enseña en cuáles de los 179 municipios de la Comunidad de Madrid entra el alquiler mediano. En cada municipio se ven centros de salud, farmacias, colegios, transporte, deporte, cultura y parques, donde la fuente tiene dato.

Integrantes: Andrea Àvila Rodriguez, Marcos Jiménez González, Lucas Henrique Silva de Carvalho, Daniel Cals Antón, Rodrigo García Sánchez. Aplicación: https://andreavilaro0.github.io/donde-cabes/

## Resultado con el sueldo de referencia

El sueldo medio de 26 a 35 años en la Comunidad de Madrid fue de 26.037 euros brutos en 2024 (importe total de salarios dividido entre el número de asalariados). Incluye a quien trabajó parte del año o a tiempo parcial. Un municipio entra si doce meses de alquiler no superan la parte elegida del sueldo bruto.

| Caso | Tope mensual | Municipios que entran, de 163 con dato |
|---|---|---|
| Un sueldo, 30 % | 650 € | 118 (en 20 solo hay cifra de casas unifamiliares) |
| Un sueldo, 40 % | 867 € | 152 |
| Dos sueldos iguales, 30 % | 1.301 € | 163 |

## Límites

El alquiler es de 2024. Los anuncios de hoy pueden ser más caros.

16 municipios no tienen cifra de alquiler. "Sin dato" no significa que el alquiler esté a tu alcance.

La cifra del mapa es la mediana del archivo del Ministerio de Vivienda: de pisos y, donde falta, de casas unifamiliares. La unidad (euros al mes) y la definición de sus columnas están sin confirmar con una definición oficial. La media del portal de la Comunidad, disponible en 37 municipios, es otra medida y se muestra aparte.

Deporte, cultura y parques vienen de la encuesta EIEL 2023 y no cubren todos los municipios (Madrid, entre ellos, no aparece). Las paradas de autobús son solo las interurbanas.

## Reproducir

Hace falta Python 3 sin paquetes adicionales. El primer paso usa la red: descarga los archivos que no están en el repositorio (datos que no se versionan por tamaño o porque contienen datos personales, y las librerías) y compara su huella SHA-256. Si una fuente ha publicado una versión nueva, avisa de la diferencia.

```sh
python3 -I pipeline/fetch_missing.py
```

Montar la página con los datos incluidos:

```sh
if [ -f demo/story/build.py ]; then python3 -I demo/story/build.py; fi
if [ -f demo/match/build.py ]; then python3 -I demo/match/build.py; fi
python3 -I demo/build.py
```

El resultado es `demo/index.html`, que se abre en el navegador.

Rehacer los datos desde las copias y comprobarlos (funciona sin red una vez descargados los archivos):

```sh
python3 -I pipeline/build.py
python3 -I pipeline/check.py
```

Los CSV descargados contienen nombres, números de identificación fiscal, teléfonos o correos. `.gitignore` los excluye; no los subas.

La lista de centros privados con nombre de persona, cuyo nombre se sustituye por el tipo de centro, se publica como huellas SHA-256. Está hecha a mano para esta copia de los datos y puede dejarse alguno.

## Privacidad y red

La página pide al IGN las imágenes de las calles cuando se abre un municipio; sin conexión funciona sin calles. En esa petición el IGN recibe la dirección IP y la zona que se está mirando.

## Datos

| Fuente | Licencia o condiciones | Crédito |
|---|---|---|
| [Alquiler medio mensual de viviendas arrendadas con valor catastral para municipios de más de 20.000 habitantes por tipo de vivienda. Municipios](https://datos.comunidad.madrid/dataset/alquiler_medio_mensual_viviendas_arrendadas_valor_catastral_municipios_mas_20000) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Recursos económicos de los hogares. Óptica perceptores. Salarios por grupo de edad, nacionalidad y sexo](https://datos.comunidad.madrid/dataset/perceptores_salarios_por_edad_nacionalidad_y_sexo) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Recursos económicos de los hogares. Óptica perceptores. Asalariados por grupo de edad, nacionalidad y sexo](https://datos.comunidad.madrid/dataset/perceptores_asalariados_por_edad_nacionalidad_y_sexo) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Bono Alquiler Joven (2022)](https://datos.comunidad.madrid/dataset/spacm_bono_alquiler_joven_2022) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Centros educativos de la comunidad de Madrid](https://datos.comunidad.madrid/dataset/centros_educativos) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Población censada por edad, nacionalidad y sexo. Censo anual. Municipios](https://datos.comunidad.madrid/dataset/poblacion_censada_por_edad_nacionalidad_y_sexo) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos |
| [Divisiones Administrativas de la Comunidad de Madrid (IDEM)](https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=UnidadesAdministrativas:IDEM_CM_UNID_ADMIN&outputFormat=application/json&srsName=EPSG:25830) | CC BY 4.0 | Contornos IDEM, CC BY 4.0 Comunidad de Madrid, convertidos a longitud y latitud |
| [Alquiler por municipio 2011 a 2024 (VDP001_01, Ministerio de Vivienda y Agenda Urbana)](https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP001_01.csv) | Reutilización con las condiciones del artículo 7 y el anexo del RD 1495/2011 (deducida de su artículo 8.1; el conjunto no trae licencia escrita) | Origen de los datos: Ministerio de Vivienda y Agenda Urbana. Datos hasta 2024, descargados el 26/11/2026. El Ministerio no participa en este proyecto ni lo apoya. |
| [Modelo digital del terreno a 200 m (IGN)](https://servicios.idee.es/wcs-inspire/mdt?service=WCS&version=2.0.1&request=GetCoverage&CoverageId=Elevacion25830_200&subset=x%28365000,496000%29&subset=y%284415000,4558000%29&format=image/tiff) | CC BY 4.0 scne.es | Obra derivada de modelos digitales del terreno del IGN, CC BY 4.0 scne.es |
| [Registro de centros, servicios y establecimientos sanitarios](https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos, CC BY |
| [Oficinas de farmacia](https://datos.comunidad.madrid/dataset/2d682b1d-e2e8-4c6f-b902-7a3f108e2fb9) | cc-by | Origen de los datos: Comunidad de Madrid, portal de datos abiertos, CC BY |
| [Paradas de autobús interurbano (CRTM)](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M8_Red/FeatureServer/0/query?where=1%3D1&outFields=CODIGOMUNICIPIO%2CCODIGOPROVINCIA%2CDENOMINACION&outSR=25830&geometryPrecision=0&f=geojson) | Licencia de uso del CRTM, https://www.crtm.es/licencia-de-uso | Fuente: Consorcio Regional de Transportes de Madrid (CRTM), datos explotados. Powered by CRTM. Datos editados el 04/06/2026. |
| [Estaciones de metro (CRTM)](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M4_Red/FeatureServer/0/query?where=1%3D1&outFields=CODIGOMUNICIPIO%2CCODIGOPROVINCIA%2CDENOMINACION&outSR=25830&geometryPrecision=0&f=geojson) | Licencia de uso del CRTM, https://www.crtm.es/licencia-de-uso | Fuente: Consorcio Regional de Transportes de Madrid (CRTM), datos explotados. Powered by CRTM. Datos editados el 04/06/2026. |
| [Estaciones de cercanías (CRTM)](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M5_Red/FeatureServer/0/query?where=1%3D1&outFields=CODIGOMUNICIPIO%2CCODIGOPROVINCIA%2CDENOMINACION&outSR=25830&geometryPrecision=0&f=geojson) | Licencia de uso del CRTM, https://www.crtm.es/licencia-de-uso | Fuente: Consorcio Regional de Transportes de Madrid (CRTM), datos explotados. Powered by CRTM. Datos editados el 04/06/2026. |
| [Paradas de metro ligero (CRTM)](https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/M10_Red/FeatureServer/0/query?where=1%3D1&outFields=CODIGOMUNICIPIO%2CCODIGOPROVINCIA%2CDENOMINACION&outSR=25830&geometryPrecision=0&f=geojson) | Licencia de uso del CRTM, https://www.crtm.es/licencia-de-uso | Fuente: Consorcio Regional de Transportes de Madrid (CRTM), datos explotados. Powered by CRTM. Datos editados el 05/06/2026. |
| [Instalaciones deportivas, EIEL 2023 (IDEM)](https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=ServiciosPublicos:IDEM_EIEL_INSTAL_DEPORTIVA_23&outputFormat=application/json&srsName=EPSG:25830) | CC BY 4.0 Comunidad de Madrid | Fuente: IDEM, EIEL 2023, CC BY 4.0 Comunidad de Madrid |
| [Parques, EIEL 2023 (IDEM)](https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=CubiertaTerrestre:IDEM_EIEL_PARQUE_23&outputFormat=application/json&srsName=EPSG:25830) | CC BY 4.0 Comunidad de Madrid | Fuente: IDEM, EIEL 2023, CC BY 4.0 Comunidad de Madrid |
| [Centros culturales, EIEL 2023 (IDEM)](https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=ServiciosPublicos:IDEM_EIEL_CENT_CULTURAL_23&outputFormat=application/json&srsName=EPSG:25830) | CC BY 4.0 Comunidad de Madrid | Fuente: IDEM, EIEL 2023, CC BY 4.0 Comunidad de Madrid |
| [Áreas caninas (Ayuntamiento de Madrid)](https://datos.madrid.es/dataset/300094-0-areas-caninas) | CC BY 4.0 | Origen de los datos: Ayuntamiento de Madrid, CC BY 4.0. Descargados el 26/11/2026. |
| [Zonas caninas y veterinarios (OpenStreetMap)](https://www.openstreetmap.org/copyright) | ODbL 1.0 | © OpenStreetMap (ODbL). Datos hasta el 26/11/2026. |
| [Mapa base de calles, IGN, en línea](https://www.ign.es/wmts/ign-base?SERVICE=WMTS&REQUEST=GetCapabilities) | CC BY 4.0 scne.es | Mapa base: IGN, CC BY 4.0 scne.es |

La definición y la fecha de cada copia están en `demo/data/municipalities.json` y en los archivos `MANIFIESTO.json`.

Los archivos del Consorcio Regional de Transportes de Madrid, y lo que se deriva de ellos en `demo/data/places.json`, se rigen por su [licencia de uso](https://www.crtm.es/licencia-de-uso), que pide atribución, mantener los datos actualizados y compartirlos con las mismas condiciones. Aquí son una copia fechada.

Las capas de `demo/data/places.json` que proceden de OpenStreetMap, y las copias de las que salen, se comparten con su licencia, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Son listas incompletas: que un municipio no tenga ningún lugar de una capa no significa que no exista.

La condición de reutilización del archivo del Ministerio ([RD 1495/2011](https://www.boe.es/buscar/act.php?id=BOE-A-2011-17560)) está deducida de su artículo 8.1, porque el conjunto no trae licencia escrita. El Ministerio no participa en este proyecto ni lo apoya.

## Librerías

[MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) 5.24.1 (BSD-3-Clause) dibuja el mapa y [Motion](https://github.com/motiondivision/motion) 14.14.0 (MIT) mueve el mapa y la lista. La idea de panel lateral con fichas parte de [OasisMadrid](https://github.com/ariaslombardero/Oasis-Madrid) (Apache-2.0).

[GSAP y ScrollTrigger](https://gsap.com/community/standard-license/) 3.15.1, de Webflow, se usan en las animaciones con su licencia estándar sin coste. No es una licencia de código abierto, así que sus archivos no se incluyen en este repositorio.

## Herramientas de inteligencia artificial

El proyecto se ha desarrollado con asistentes de programación de inteligencia artificial.

## Licencia

Licencia del código propio: MIT (archivo `LICENSE`). No cubre los datos ni las librerías de terceros.
