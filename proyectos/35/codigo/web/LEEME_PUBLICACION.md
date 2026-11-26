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
