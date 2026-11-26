Este es el repositorio para el participante número 49
# Nutriva — Vending Saludable, Inclusivo y Sostenible con Datos Abiertos (DATAMAD 2026)

Plataforma web interactiva y pipeline ETL reproducible en Python para adaptar las máquinas expendedoras de la Comunidad de Madrid al **Real Decreto 950/2026** (≥ 70 % oferta saludable en filas centrales), evitando mermas en productos frescos y garantizando opciones verificadas para celiaquía, alergias, intolerancias y diabetes.

- **Autora:** Ikram Souali (Estudiante de Ingeniería Mecánica, URJC)
- **Mentoría y estrategia:** Giuliana García Zevallos
- **Licencia de código:** MIT (`LICENSE`) · **Datos derivados propios:** CC BY 4.0

## Qué incluye este repositorio

- **`index.html`:** Simulador interactivo 2D del caso piloto **ETSIAE - UPM** (Expediente público `E-04.1/25 MB`, comparativa Estado A Pliego Base vs. Estado B Optimizada Nutriva, filtros sanitarios y proveedores de proximidad).
- **`pipeline.html`:** Caso práctico interactivo conectado a los **179 municipios** y **809 bibliotecas** reales descargados hoy vía API CKAN del Portal de Datos Abiertos de la Comunidad de Madrid.
- **`pipeline/`:** Scripts Python reproducibles sin dependencias externas (solo librería estándar Python 3.12):
  - `00_descubrir_fuentes.py`: Consulta a la API CKAN (`package_search`) del portal de la Comunidad de Madrid.
  - `01_ingesta.py`: Descarga de CSV oficiales con registro de URL, licencia y hash SHA-256 en `datos/manifest_fuentes.json`.
  - `02_limpieza_integracion.py`: Limpieza, detección de anomalías, normalización a código INE de 5 dígitos (`28XXX`) e integración municipal.
- **`datos/`:** Conjuntos limpios en JSON y CSV abiertos (`municipios_madrid_integrado.csv`, `municipios_madrid_integrado.json`, `bibliotecas_madrid_limpio.json`, `reporte_limpieza.json`, `manifest_fuentes.json`) y datos del piloto UPM.

## Cómo reproducir el pipeline en local

```bash
python pipeline/00_descubrir_fuentes.py
python pipeline/01_ingesta.py
python pipeline/02_limpieza_integracion.py
```

Para ver la web completa (`index.html` y `pipeline.html`) en local basta con servir la carpeta con cualquier servidor HTTP estático (por ejemplo, `python -m http.server 8080`) o desplegarla directamente en **Vercel** / **GitHub Pages**.
