# Equipo 35 · CercaSalud MAD

**DATAMAD 2026 · Hackathon de Datos Abiertos de la Comunidad de Madrid**

**Integrantes:** COMPLETAR ANTES DE SUBIR

**Web publicada:** https://inigo-diez.github.io/CERCASALUD-MAD/

CercaSalud MAD mide a cuántos minutos, a pie y en transporte público, queda cada persona de la Comunidad de Madrid de los recursos de salud que necesita, y señala dónde conviene actuar:

- **A · Atención primaria pública:** tiempo hasta el centro de salud más cercano, a pie y en transporte público (franjas de 9 a 13 h y de 16 a 20 h), y simulación de carteras de zonas donde estudiar centros nuevos.
- **B · Refugios climáticos:** acceso a pie a espacios frescos durante el calor.
- **C · Carencias coincidentes:** zonas donde faltan a la vez A y B.

La población se reparte en celdas de 100 m a partir de las secciones censales del INE, y los tiempos se calculan con R5 (r5py) sobre la red peatonal de OpenStreetMap y los horarios GTFS del CRTM. Lo que no se puede evaluar se marca como «no evaluable», nunca como «sin acceso».

## Contenido de esta carpeta

| Ruta                                                                 | Qué es                                                                                                                                                                                                     |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CercaSalud_Madrid_DATAMAD2026_Presentacion_Final.pdf` / `.pptx` | Presentación de la entrega                                                                                                                                                                                 |
| `CercaSalud_Madrid_producto_con_musica.mp4`                        | Vídeo de la aplicación                                                                                                                                                                                    |
| `web/`                                                             | Copia de la aplicación web estática con los resultados (mapa con deck.gl), publicada en https://inigo-diez.github.io/CERCASALUD-MAD/. No hace cálculos en el navegador ni pide nada a servicios externos |
| `codigo/`                                                          | Código en Python que descarga los datos, hace los cálculos y genera la web, con sus tests                                                                                                                 |

Repositorio del proyecto: https://github.com/inigo-diez/CERCASALUD-MAD

## Cómo abrir la web

**Web publicada (GitHub Pages): https://inigo-diez.github.io/CERCASALUD-MAD/**

Es la forma de verla: se abre directamente en el navegador, sin instalar nada.

Alternativa sin conexión a esa dirección: la misma web está en `web/`. Carga sus datos desde `web/datos/`, así que necesita un servidor local (abrir `index.html` con doble clic no funciona). Con Python instalado, desde la carpeta `web/`:

```
python -m http.server 8000
```

y abrir http://127.0.0.1:8000 en el navegador.

## Cómo reproducir el cálculo

Con [uv](https://docs.astral.sh/uv/) y Java 21 (requisito de r5py), desde `codigo/`:

```
uv sync
uv run pytest
uv run cercasalud fetch
uv run cercasalud build --snapshot <versión creada por fetch>
uv run cercasalud web --exportar <carpeta vacía>
```

Los datos descargados no se incluyen en el repositorio: `fetch` los descarga de su origen y guarda la URL, la fecha, la licencia y el SHA-256 de cada archivo. Más detalle en `codigo/README.md` y `codigo/docs/`.

## Conjuntos de datos utilizados

**Comunidad de Madrid (Portal de Datos Abiertos)**

- Centros, servicios y establecimientos sanitarios: https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7 (CC BY 4.0; la columna NIF se elimina en la ingesta)
- Bibliotecas y servicios de lectura: https://datos.comunidad.madrid/dataset/e6a74331-d329-4ba2-8bb9-6be2669417a2 (CC BY 4.0)

**Ayuntamiento de Madrid**

- Equipamientos municipales (horarios de los mercados): https://datos.madrid.es/dataset/300331-0-equipamientos-municipales (CC BY 4.0)
- Bibliotecas, centros de mayores, centros culturales, piscinas municipales y fuentes de agua: https://datos.madrid.es (CC BY 4.0)
- Salas de estudio: https://datos.madrid.es/dataset/217921-0-salas-estudio (CC BY 4.0)
- Polideportivos: https://datos.madrid.es/dataset/200186-0-polideportivos (CC BY 4.0)
- Recursos de Protección Civil (geoportal): https://geoportal.madrid.es (condiciones generales de reutilización del Ayuntamiento)
- Mercados con aire acondicionado en zonas comunes: https://www.madrid.es (aviso legal de madrid.es)

**INE**

- Población por sección censal, sexo y edad (tabla 69213): https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/69213.csv (CC BY 4.0)
- Secciones censales 2025 (cartografía): https://www.ine.es/dyngs/AYU/index.htm?cid=125 (CC BY 4.0)
- Atlas de Distribución de Renta de los Hogares 2024: https://www.ine.es (CC BY 4.0)

**Consorcio Regional de Transportes de Madrid (CRTM)**

- GTFS de Metro, EMT, interurbanos, urbanos, Metro Ligero y Cercanías (licencia de datos abiertos del CRTM)

**OpenStreetMap**

- Extracto de Madrid de Geofabrik: https://download.geofabrik.de/europe/spain/ (ODbL 1.0)

## Licencias y atribuciones

- **Código:** licencia MIT (`codigo/LICENSE`, `web/LICENSE`). deck.gl 9.3.12, licencia MIT (`web/vendor/`).
- **OpenStreetMap:** © colaboradores de OpenStreetMap, https://www.openstreetmap.org/copyright. Los valores por sección derivados de OSM se distribuyen bajo la Open Database License (ODbL 1.0): https://opendatacommons.org/licenses/odbl/1-0/.
- **CRTM:** Powered by CRTM (http://www.crtm.es/). Los horarios GTFS se usan para calcular los tiempos de viaje (datos explotados, no en bruto).
- **INE:** Elaboración propia con datos extraídos del sitio web del INE: www.ine.es.
- **Comunidad de Madrid:** Fuente de los datos: Comunidad de Madrid (http://datos.comunidad.madrid).
- **Ayuntamiento de Madrid:** Origen de los datos: Ayuntamiento de Madrid.

Las fuentes con licencia CC BY 4.0 se han modificado: se filtran, se unen y se agregan. La web explica qué se hace con cada una y la fecha de cada descarga.
