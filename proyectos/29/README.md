# Equipo 29 · Madrid Data Explorer

**Integrantes:** Camilo Escobar, Alejandro Arevalo y Gohan García.

**DATAMAD 2026 — entrega del 26 de noviembre de 2026.**

Aplicación de Streamlit para consultar, preparar, cruzar, analizar y visualizar datos abiertos de la Comunidad de Madrid. Permite construir mapas de los 179 municipios, gráficos y análisis estadísticos, conservar la trazabilidad de las fuentes y compartir proyectos portables.

**Puedes probar la aplicación directamente en el navegador, sin instalar nada: [Madrid Data Explorer](https://madrid-data-explorer.streamlit.app/).**

- [Presentación del proyecto (PDF)](PRESENTACION.pdf)
- [Vídeo de demostración de la aplicación (MP4)](demo.mp4)
- [Repositorio de desarrollo del equipo](https://github.com/GohanGH/Madrid-Data-Explorer)
- [Resultados y metodología](RESULTADOS_DATAMAD.md)
- [Fuentes y metadatos de los extractos](demo_data/sources.json)

Esta entrega contiene la copia local actualizada a la versión 4.0 del repositorio de desarrollo y el ejemplo de edad media municipal en `data/edad_media_poblacion/`. Para ejecutarla desde la raíz del repositorio DATAMAD2026, entra primero en `proyectos/29` y sigue las instrucciones siguientes.

## Madrid Data Explorer 4.0

Madrid Data Explorer es un espacio de trabajo en español para investigar con datos abiertos de la Comunidad de Madrid. Busca fuentes oficiales o importa tus propios datos, elige cómo preparar y cruzar las tablas y calcula resultados para tu pregunta. Comparte el proyecto completo para que otra persona pueda continuarlo.

[Abrir Madrid Data Explorer en Streamlit](https://madrid-data-explorer.streamlit.app/)

| Espacio | Qué puedes hacer |
| --- | --- |
| **Home** | Buscar en el catálogo, iniciar o abrir un proyecto e importar archivos. |
| **Datos** | Consultar fichas y recursos CKAN, previsualizar, importar varias fuentes y explorar la biblioteca. |
| **Preparación** | Limpiar y transformar, calcular indicadores, combinar tablas y recuperar versiones. |
| **Análisis** | Elegir variables, revisar supuestos y ejecutar descriptivos, contrastes, modelos y análisis temporal o espacial. |
| **Visualización** | Construir gráficos y mapas con la tabla activa. |
| **Resultados** | Organizar tablas, análisis y figuras en el cuaderno y redactar informes HTML. |
| **Mis proyectos** | Guardar un ZIP portable con el trabajo o abrir un proyecto existente. |

La barra lateral mantiene el proyecto y la tabla activa accesibles. Cada transformación confirmada crea una versión. El cuaderno guarda los resultados con su tabla, configuración, fecha y fuentes.

## Ejecutar en macOS o Linux

Desde la carpeta que contiene `app.py`, usa Python 3.11.

```bash
python3.11 -m venv "$HOME/.venvs/madrid-data-explorer-4"
source "$HOME/.venvs/madrid-data-explorer-4/bin/activate"
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre [localhost:8501](http://localhost:8501). El catálogo en vivo requiere conexión. Con archivos locales o los extractos oficiales incluidos puedes preparar datos, analizar y guardar un proyecto sin credenciales. Se admiten CSV, TSV, XLSX, XLS y JSON tabular. Los mapas municipales incorporan los límites de los 179 municipios derivados de la BDLJE del IGN, con atribución CC BY 4.0.

## Investigar y compartir

1. Busca una fuente en **Home** o **Datos → Catálogo**. Consulta su ficha, previsualiza un recurso y añádelo a la selección. Las importaciones aparecen en **Datos → Biblioteca**.
2. Selecciona una tabla y abre **Preparación**. Previsualiza y confirma cada transformación. Para unir fuentes, elige claves equivalentes y revisa la cardinalidad y los registros sin pareja.
3. En **Análisis**, elige el método, las variables y los filtros. Pulsa **Ejecutar** para calcular y guardar un resultado. En **Visualización** crea gráficos y mapas con cualquier tabla compatible.
4. En **Resultados → Informes**, selecciona resultados y añade texto. Descarga el HTML y usa **Imprimir → Guardar como PDF** en el navegador cuando necesites ese formato.
5. En **Mis proyectos → Proyecto activo**, prepara y descarga el ZIP. Tu compañero puede importarlo en **Mis proyectos → Abrir**. La versión 4.0 lee proyectos guardados con la 3.1.

[Guía del equipo](docs/GUIA_EQUIPO.md) · [Arquitectura 4.0](docs/MDE_4.md) · [Validación reproducible](docs/VALIDACION_FINAL.md) · [Registro de cambios](CHANGELOG.md)

## Fuentes y pruebas

Los extractos oficiales y sus fechas, unidades y recursos están en [los metadatos](demo_data/sources.json). Los análisis históricos se documentan en [Resultados DATAMAD](RESULTADOS_DATAMAD.md). Para regenerar los extractos en otra carpeta, usa `python demo_data/build.py --output nuevos-extractos --save-raw csv-originales`. Para recrearlos a partir de archivos descargados, usa `--local carpeta-csv` y consulta los nombres esperados en `demo_data/build.py`.

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -q
MDE_RUN_INTEGRATION=1 python -m pytest -q -m integration
```

La última línea consulta el catálogo en vivo. La suite habitual usa datos locales y respuestas controladas para que el recorrido sea reproducible.

## Community Cloud

El archivo de entrada es **`app.py`**, con `requirements.txt` en la raíz. Para un despliegue nuevo, selecciona el repositorio, la rama y Python 3.11. Para actualizar la aplicación existente, publica los cambios revisados en la rama conectada y comprueba el arranque y el catálogo en sus logs. [Instrucciones de publicación](docs/GUIA_EQUIPO.md#actualizar-github-y-streamlit-después-de-la-revisión) · [Documentación de Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

El espacio de trabajo funciona sin una API de IA. El asistente opcional de planes utiliza `OPENAI_API_KEY`, `MDE_AI_MODEL` y `MDE_AI_BASE_URL` como ajustes. Envía la pregunta y los nombres de hasta 100 columnas al proveedor configurado. El plan se muestra para revisión y se calcula localmente al ejecutar. [Configuración de ejemplo](.env.example)
