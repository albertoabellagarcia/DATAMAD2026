# Nutriva · Dossier Técnico de Tratamiento de Datos Abiertos (DATAMAD 2026)

> **Propósito del documento:** Documentar de forma transparente, verificable y reproducible cómo se han obtenido, limpiado, filtrado, integrado y conectado los datos abiertos de la Comunidad de Madrid con el motor de recomendación de **Nutriva**, así como el uso supervisado de Inteligencia Artificial durante el desarrollo.

---

## 1. Arquitectura General del Flujo de Datos

El tratamiento de datos de Nutriva separa estrictamente dos planos para garantizar rigor técnico ante el jurado:

- **Plano A · Pipeline ETL real y reproducible (`pipeline/`):** Procesa fuentes oficiales descargadas vía API CKAN del Portal de Datos Abiertos de la Comunidad de Madrid hasta cubrir los **179 municipios** y **809 bibliotecas públicas** en formatos abiertos (JSON y CSV).
- **Plano B · Caso piloto detallado (`index.html`):** Toma el expediente público real **E-04.1/25 MB** de la **ETSIAE - UPM** (Ciudad Universitaria, Madrid, adjudicatario `MAXELGA 93, S.L.`, parque de 13 máquinas) y aplica el motor de reglas sobre una matriz simulada de 20 ranuras (`A1–E4`) etiquetando explícitamente qué datos son públicos verificados, qué es simulación de demostración y qué requiere ficha técnica verificada.

---

## 2. Fase 1 · Descubrimiento e Ingesta vía API CKAN

- **Mecanismo de obtención:** Consultas automáticas mediante `pipeline/00_descubrir_fuentes.py` y descarga directa con `pipeline/01_ingesta.py` contra la API CKAN v3 de la Comunidad de Madrid (`https://datos.comunidad.madrid/catalogo/api/3/action/package_search` y `package_show`).
- **Trazabilidad automática (`datos/manifest_fuentes.json`):** Cada recurso descargado registra su URL exacta, fecha de modificación en catálogo, licencia de origen (**Creative Commons Attribution**), tamaño en bytes y firma criptográfica **SHA-256**.
- **Conjuntos reales descargados e integrados en el pipeline:**
  - **Población empadronada por sexo. Municipios (`padron_por_sexo`):** 18.718 filas crudas (serie histórica hasta 2025). Licencia: Creative Commons Attribution.
  - **Edad media de la población. Municipios (`201276`):** 5.348 filas crudas (hasta 2025). Licencia: Creative Commons Attribution.
  - **Indicador de Renta Disponible Bruta Municipal (`irpf_indicador_renta`):** 5.730 filas crudas (hasta 2024). Licencia: Creative Commons Attribution.
  - **Directorio de Bibliotecas de la Comunidad de Madrid (`spacm_listado_bibliotecas_servicios_lectura`):** 809 filas crudas. Licencia: Creative Commons Attribution.
  - **Centros universitarios públicos (`centros_universitarios_publicos_por_universidad_tipo_naturaleza_y_modalidad`):** Descargado para contexto educativo.
  - **Hospitales y datos asistenciales (`1912744`):** Descargado para contexto de actividad sanitaria.
- **Fuentes de contratación y normativa del caso piloto ETSIAE-UPM:**
  - **Portal de Transparencia UPM:** Expediente `E-04.1/25 MB` (`CON16949`), adjudicatario `MAXELGA 93, S.L.`.
  - **Boletín Oficial del Estado (BOE):** Real Decreto 950/2026, de 4 de noviembre (Artículo 11 sobre máquinas expendedoras).

---

## 3. Fase 2 · Limpieza, Detección de Anomalías y Normalización

Durante la ejecución de `pipeline/02_limpieza_integracion.py` se detectaron y resolvieron problemas reales de calidad presentes en los CSV originales (documentados en `datos/reporte_limpieza.json`):

- **Heterogeneidad de codificación y BOM:** Los ficheros estadísticos utilizan `utf-8-sig` (con marca BOM `\ufeff` al inicio de la cabecera), mientras que el directorio de bibliotecas usa `latin-1`. El pipeline detecta y normaliza todo a **UTF-8 limpio**.
- **Mezcla de niveles territoriales:** En las series municipales conviven filas agregadas (`Comunidad de Madrid`, `Otros`) junto a los municipios. Se filtraron **1.176 filas agregadas** en el padrón para aislar exactamente los **179 municipios**.
- **Prevención de doble conteo por desagregación:** En `padron_por_sexo`, cada municipio repite filas para `Mujeres`, `Total` y `Hombres`. Se aisló exclusivamente la métrica `Sexo == "Total"` para evitar duplicar o triplicar la población (validado en Madrid `28079`: **3.506.730 habitantes** en 2025).
- **Normalización de códigos territoriales al estándar INE:** El portal autonómico usa códigos de 4 dígitos con dígito de control (por ejemplo, `0796` para Madrid). El script los transforma al estándar **INE de 5 dígitos (`28XXX`)** mediante la regla `28 + codigo[:3]` (`0796 → 28079`), garantizando la interoperabilidad estatal.
- **Limpieza de textos y detección de anomalías en equipamientos:** Se eliminaron espacios múltiples y artículos invertidos entre paréntesis (como `Acebeda (La)`) para cruzar localidades, y se detectaron **232 teléfonos concatenados anómalos** en el directorio de bibliotecas (ej. `9172885091728860`) que quedan marcados para auditoría.
- **Valores ausentes:** Los guiones (`-`) y celdas vacías se convierten en `null` explícito sin inventar ni imputar valores artificiales.

---

## 4. Fase 3 · Integración y Caso Práctico (Madrid `28079` → ETSIAE-UPM)

El cruce por código INE (`28079`) y localidad unifica las cuatro capas en `datos/municipios_madrid_integrado.json` y `.csv`:

- **Perfil real obtenido para Madrid (`28079`):**
  - **Población (2025):** 3.506.730 habitantes.
  - **Edad media (2025):** 44,35 años.
  - **Renta bruta disponible per cápita (2024):** 26.470,96 € (sobre 92.826,52 M€ totales).
  - **Bibliotecas públicas integradas:** 534 puntos de lectura.
- **Regla determinista aplicada por el motor:**
  - Al superar el umbral de alta densidad y tránsito (`rotación ALTA`), el motor autoriza un **máximo de hasta 35 % de producto fresco** (controlando el riesgo de merma por caducidad), frente a municipios pequeños de rotación baja/periódica donde limita los frescos al **10 %** y prioriza snacks saludables de larga vida útil.
  - En el piloto **ETSIAE-UPM (`index.html`)**, esta lógica se combina con el cumplimiento del **Real Decreto 950/2026 (≥ 70 % saludable en filas centrales)** y la **regla estricta de seguridad alimentaria**: ningún producto puede mostrarse como apto para celiaquía, alergias o diabetes si `ficha_tecnica_verificada == false`.

---

## 5. Uso de Inteligencia Artificial y Supervisión Humana

En línea con la formación de **IA Aplicada a los Datos Abiertos (DATAMAD 2026)**, la IA se empleó como acelerador de prototipado y análisis bajo control humano estricto:

- **Exploración y prototipado de interfaz:** Generación asistida del simulador 2D (`index.html`), filtros de inclusión alimentaria y visualización comparativa Estado A vs. Estado B.
- **Automatización del pipeline reproducible:** Creación y validación de scripts Python de ingesta CKAN, limpieza de anomalías y exportación abierta (`pipeline/`).
- **Control de alucinaciones y trazabilidad:** Cada cifra generada se contrastó contra las salidas reales de los CSV oficiales (corrigiendo errores de lectura antes de exportar) y separando explícitamente en la interfaz los datos públicos verificados de los escenarios simulados.

---

## 6. Estándares Abiertos e Interoperabilidad (Alineación Gaia-X)

- **Identificadores estándar:** Códigos municipales **INE (5 dígitos)** y preparación para códigos orgánicos **DIR3** en futuros pliegos de contratación pública.
- **Formatos abiertos:** Toda la salida del pipeline se publica en **JSON** y **CSV (UTF-8)** sin dependencias propietarias.
- **Licenciamiento abierto:** Código fuente bajo **MIT License** y conjuntos derivados bajo **CC BY 4.0**.
