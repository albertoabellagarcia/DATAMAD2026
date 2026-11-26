# Fuentes de datos
Consulta y procesamiento de la entrega inicial el 24 de noviembre de 2026.

| Fuente | Variables | Transformación y límites |
|---|---|---|
| Comunidad de Madrid, catálogo regional | Meteorología horaria 2020–2026 | Indicadores de validez, agregación diaria y mensual, estaciones compartidas |
| Comunidad de Madrid, cartografía y municipios | Geometrías, códigos, superficie total | WGS84 y unión por código INE |
| Comunidad de Madrid, población | Población anual | Último año disponible para consulta territorial |
| MITECO, EGIF, Excel aportado | 1.052 partes 2020–2023 | Fechas, código municipal, superficie forestal afectada |
| Copia pública de exportaciones EGIF | Archivo 2006–2019 | SHA-256 de archivos contra manifiesto incluido |
| CAM, Plan Anual 2025 | Recuentos por municipio y causa | Tabla transcrita, contraste de totales |
| CAM, Plan Anual 2026 | 59 municipios ZAR | Correspondencia nominal con catálogo |
| Open-Meteo | Previsión meteorológica | Consulta por lotes, caché local y fechas de consulta |


## Atribución y transformaciones de la demo

Datos regionales de la Comunidad de Madrid (catálogo de datos abiertos, con atribución). Las series municipales y los polígonos se presentan transformados en tablas y cartografía web. Las observaciones horarias se agregaron por estación y fecha. Los originales se obtienen en el catálogo regional.

- Meteorología: https://datos.comunidad.madrid/dataset/calidad_aire_datos_meteo_historico
- Municipios: https://datos.comunidad.madrid/dataset/municipio_comunidad_madrid
- Incendios regionales: https://datos.comunidad.madrid/dataset/101019
- Plan anual regional de incendios forestales 2026: https://www.comunidad.madrid/transparencia/sites/default/files/plan_anual_iiff_2026.pdf
- EGIF, Ministerio para la Transición Ecológica y el Reto Demográfico. Partes con municipio de inicio, fecha y superficie. Procedencia oficial: https://servicio.mapa.gob.es/incendios/Search/Publico . Copia pública consultada para la extensión histórica: https://github.com/JaimeOnaindia/incendios-forestales-espana . Reutilización: https://www.miteco.gob.es/es/atencion-al-ciudadano/aviso-legal.html
- Previsión semanal: Open-Meteo, CC BY 4.0, consulta fechada por municipio. https://open-meteo.com/en/docs
- Proyecciones: programa CMIP6, experimento HighResMIP, modelos EC-Earth3P-HR (EC-Earth Consortium) y MRI-AGCM3-2-S (Meteorological Research Institute), suministrados por Open-Meteo, CC BY 4.0. https://open-meteo.com/en/docs/climate-api y https://creativecommons.org/licenses/by/4.0/ . Consulta del 25 de noviembre de 2026. Punto solicitado 40,42 °N, 3,70 °O. Media mensual de las máximas diarias, suma mensual de lluvia y número de días con máxima de al menos 30 °C, por modelo. Dos realizaciones no constituyen un intervalo probabilístico.
