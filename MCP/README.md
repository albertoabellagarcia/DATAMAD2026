# DATAMAD 2026 · Ejemplos de las diapositivas

Programas que acompañan a la presentación «Datos abiertos de Madrid, de cero a IA».

| Diapositiva | Programa | Qué hace |
|---|---|---|
| 57 · Conectar un servidor MCP real | `servidor.py` | Servidor MCP con 3 herramientas sobre el CKAN de la Comunidad de Madrid: `buscar_datasets`, `detalle_dataset`, `leer_datos` |
| 57 | `probar_servidor.py` | Arranca `servidor.py` y prueba sus herramientas sin necesidad de un cliente de IA |
| 57 | `claude_desktop_config.json` | Configuración para Claude Desktop (cambiar `/ruta/servidor.py`) |
| 63 · Accidentes de tráfico | `caso_accidentes.py` | Descarga el dataset 1908061 y resume los accidentes con víctimas por ubicación y resultado |
| 64 · Carreteras | `caso_carreteras.py` | Busca datasets de carreteras e indica cuáles tienen datos geográficos; `--mapa` genera un mapa HTML |
| 65 · Gasolineras | `caso_gasolineras.py` | API del Ministerio: provincia → municipio → gasolineras, ranking de precios, CSV y GeoJSON |
| 66 · Turismo | `caso_turismo.py` | Busca datasets de turismo y alojamientos con coordenadas; `--poi` los convierte a PointOfInterest (Smart Data Models) |

## Instalación

```bash
pip install requests mcp httpx
pip install pysmartdatamodels   # opcional, para validar en caso_turismo.py --poi
```

## Uso rápido

```bash
python probar_servidor.py "calidad del aire"
python caso_accidentes.py
python caso_carreteras.py --mapa
python caso_gasolineras.py --municipio "Alcalá de Henares"
python caso_turismo.py --poi
```

## Notas

- **SDK de MCP 2.x:** en la versión 2 del SDK, `FastMCP` pasó a llamarse `MCPServer`. `servidor.py` funciona con las dos versiones. El código literal de la diapositiva solo funciona con `mcp<2`, y `uv run --with mcp` instala la última versión.
- **Otro portal CKAN:** `servidor.py` usa la variable de entorno `CKAN_URL`, por ejemplo `CKAN_URL=https://datos.madrid.es/api/3/action` para el Ayuntamiento.
- **Columnas de accidentes:** si la detección automática de columnas falla en `caso_accidentes.py`, indícalas con `--ubicacion`, `--resultado` y `--valor`. Si el fichero trae filas de «Total», los sumatorios las incluyen.