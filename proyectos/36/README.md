# 36 · YaVoy (inscrito como «Fiabus»)

**YaVoy te dice cuándo llega de verdad tu transporte en Madrid, no solo lo que anuncia el panel.**

Las apps oficiales dan un minuto exacto («llega en 4 min») que a menudo no se cumple. Durante noviembre grabamos las llegadas reales de la EMT, el Metro, los interurbanos y Cercanías, y las comparamos con lo que se anunciaba. Con eso YaVoy enseña una **ventana medida** («llega entre 4 y 9 min»), cuánto se puede fiar uno de cada línea a cada hora, y planifica rutas por el **peor caso realista**, no por el mejor.

## Qué hay en esta carpeta

| Carpeta | Contenido |
|---|---|
| `presentacion/` | La presentación de la final (PDF y PPTX editable). |
| `encuesta_y_entrevistas/` | Resultados de la encuesta (109 respuestas, corte 25/11), análisis de las entrevistas (anonimizado) y el código para generar el formulario y el resumen. |

## Código y datos

- **App web (código abierto):** https://github.com/anti-miguel/datamad-2026 — React + Vite, planificador propio y servidor de la pasarela (`servidor/`).
- **Datos, grabadores y análisis:** https://github.com/anti-miguel/datamad-2026-datos

## Conjuntos de datos utilizados

- Horarios GTFS del **Consorcio Regional de Transportes de Madrid** (Metro, autobuses interurbanos) — Catálogo de Datos Abiertos de la Comunidad de Madrid / datos.crtm.es.
- Tiempos de espera del Consorcio (Metro e interurbanos), servicio público de tiempos.
- **EMT de Madrid · MobilityLabs**: llegadas en directo, posiciones GPS y paradas.
- GTFS de la **EMT** y de **Renfe Cercanías**.
- Avisos oficiales de la EMT (RSS).
- Encuesta y entrevistas propias a usuarios del transporte público.
