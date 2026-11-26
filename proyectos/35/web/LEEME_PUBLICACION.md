# CercaSalud MAD: página de resultados

Página estática con los resultados de CercaSalud MAD. Muestra a qué distancia en minutos quedan los centros de atención primaria pública de la Comunidad de Madrid, a pie y en transporte público, y compara carteras de zonas donde estudiar nuevos centros. No calcula nada en el navegador ni pide nada a servicios externos: todo lo que enseña viene de los archivos de `datos/`.

## Qué contiene

| Ruta | Contenido |
|---|---|
| `index.html`, `app.js`, `estilo.css` | La página. |
| `vendor/` | deck.gl 9.3.12 (licencia MIT, en `vendor/LICENSE-deckgl.txt`), copiado sin cambios. |
| `datos/mapa.json`, `carteras.json`, `textos.json`, `puntos.json` | Cifras y textos ya calculados de la versión de datos indicada en `datos/manifiesto.json`. |
| `datos/capas/` | Capas del mapa: secciones censales con sus valores, municipios, límites y vías. |
| `datos/descargas/` | Fichas de decisión (HTML), zonas (CSV y GeoJSON) y escenarios reproducibles (JSON). |
| `datos/manifiesto.json` | Versión de datos, fecha de generación y SHA-256 de cada tabla de origen. |

## Cómo se genera

Desde el repositorio del código: `uv run cercasalud web --exportar <carpeta vacía>`. La orden lee los resultados guardados de la versión de datos y no repite ningún cálculo. El cálculo completo está documentado en el repositorio.

## Licencias y atribuciones

- **Código:** licencia MIT.
- **OpenStreetMap:** © colaboradores de OpenStreetMap, https://www.openstreetmap.org/copyright. Los valores por sección (`datos/capas/secciones.json`) se calculan con la red peatonal y los edificios residenciales de OSM, que reparten la población del INE dentro de cada sección. Como base de datos derivada de OSM, se distribuye bajo la Open Database License (ODbL 1.0): https://opendatacommons.org/licenses/odbl/1-0/.
- **CRTM:** Powered by CRTM (http://www.crtm.es/). Los horarios GTFS se usan para calcular los tiempos de viaje; la fecha de cada archivo GTFS figura en la página («Para quién, datos y código»).
- **INE:** Elaboración propia con datos extraídos del sitio web del INE: www.ine.es.
- **Comunidad de Madrid:** Fuente de los datos: Comunidad de Madrid (http://datos.comunidad.madrid).
- **Ayuntamiento de Madrid:** Origen de los datos: Ayuntamiento de Madrid.

Las fuentes con licencia CC BY 4.0 se han modificado: se filtran, se unen y se agregan. La página explica qué se hace con cada una.

## Qué no contiene

- Datos personales. El registro sanitario se usa sin su columna NIF.
- Datos de fuentes con licencia sin confirmar. Coslada no se incluye.

## Qué mide

Mide la proximidad física potencial con supuestos declarados: umbral, velocidad y franja horaria. No mide citas, capacidad, listas de espera ni efectos sobre la salud.

## Ampliación de refugios del 22/11/2026

El inventario de Madrid capital incorpora 569 espacios por nivel de evidencia. La cobertura ampliada está en `datos/refugios_detalle.json`; el inventario, horarios y evidencias en `datos/capas/refugios.json`; los resultados completos en `datos/descargas/refugios_ampliados_lineas.csv`. La versión y los SHA-256 figuran en `datos/manifiesto.json`.

Se usan CALORMAD 2026 y los conjuntos municipales de bibliotecas, centros culturales y centros de mayores para clasificar espacios y codificar horarios; Protección Civil aporta solo geometría e identificadores. Se filtran, unen y clasifican registros. Las fuentes de agua operativas (conjunto 300051, versión 2026) y las piscinas municipales al aire libre (210227), adquiridas el 22/11/2026, se muestran aparte bajo CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. Origen de los datos: Ayuntamiento de Madrid. Museos, cines, centros comerciales y parques procedentes de OpenStreetMap se distribuyen bajo ODbL 1.0. Natural Earth se usa únicamente como fondo del mapa, en dominio público.

Los horarios codificados proceden de textos oficiales de verano y no han recibido segunda codificación independiente. Tener climatización no acredita por sí solo acceso libre. Los pendientes se mantienen no evaluables y el máximo posible es un techo hipotético. El mapa de horas por sección, las carteras B1 y los cruces sociales conservan el cálculo de los 43 mercados.

## Contexto social y cruces de indicadores

La vista Contexto social incorpora los conteos de personas que viven solas, total y 65+, por barrio del Padrón municipal de Madrid a 1/1/2026. Fuente: https://datos.madrid.es/dataset/300431-0-personas-viven-solas (Ayuntamiento de Madrid, CC BY 4.0). Vivir solo no equivale a soledad no deseada.

Los cruces conservan renta por sección (ADRH 2024), población INE 2025 y los supuestos de accesibilidad de la base. Los conteos de personas solas se mantienen por barrio y no se convierten en tasas con población de otro año. Una coincidencia territorial no identifica qué personas concretas cumplen ambos indicadores. Los no evaluables no se consideran buena accesibilidad ni se rellenan con cero.

La geometría de los 131 barrios procede del Ayuntamiento de Madrid: https://datos.madrid.es/dataset/300496-0-barrios-madrid. Licencia CC BY 4.0 verificada en esa ficha el 22/11/2026. Modificaciones: asignación espacial sobre la geometría completa; para dibujo, reproyección de EPSG:25830 a WGS84 y simplificación a 40 m. No se modifica el dato original. La agregación de acceso mantiene fuera las unidades sin asignación a barrio, documentadas en los metadatos.

En los cruces, refugios representa la peor hora 20–21 h del laborable de julio con acceso supuesto en horario comercial; se distingue de la media de horas del mapa simple y de los efectos de las actuaciones. Las carteras de primaria muestran la ganancia por quintil de renta de la sección, a partir de los pesos originales sin redondear. El reparto entero conserva el total de la cartera. Los cruces son exploración y contexto; no cambian la elección de actuaciones.

Activos nuevos: `datos/cruces.json` (valores, clases, fuentes, años y controles), `datos/capas/barrios_cruces.json` (dibujo) y `datos/descargas/cruces/` (12 CSV). Los datos derivados de la red y edificios de OpenStreetMap mantienen la ODbL 1.0 y las atribuciones anteriores.
