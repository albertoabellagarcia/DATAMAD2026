# ForMadrid · ¿Dónde reforzar la formación para el empleo?

**Índice de desajuste territorial del mercado laboral para los 179 municipios de la Comunidad de Madrid (2021-2025)**, construido con datos abiertos del Portal de Datos Abiertos de la Comunidad de Madrid.

Proyecto finalista de **DATAMAD 2026**. Equipo: JiaJie Daniel Zheng · Barbara Cui.

## Qué responde

¿En qué municipios el empleo local, el paro registrado y el perfil de los trabajadores residentes encajan peor, y llega allí la oferta de formación para el empleo? Para **ayuntamientos** (dónde pedir o diseñar formación) y **centros de formación** (dónde abrir cursos y de qué sectores).

## Resultados principales (2025)

- **Ranking robusto**: Spearman 0,985 entre el índice con afiliados residentes (corregidos) y con población INE de 15 a 64 años.
- **26 municipios** concentran el mayor desajuste (cuartil superior): 16.000 parados registrados.
- **Más de 18.000 parados** tendrían que cambiar de sector para encajar con el empleo de su propio municipio.
- **Recuperación desigual** 2021-2025: el paro baja un 34-35 % en los polos de empleo y un 19,5 % en los municipios pequeños.
- **Oferta formativa**: 4,0 cursos presenciales por 1.000 parados en los municipios de mayor desajuste frente a 7,7 en el resto (orientativo: ver limitaciones).

Detalle y fuentes de cada cifra: [`Resultados/cifras_clave.md`](Resultados/cifras_clave.md). Herramienta interactiva: [`Mapa/ForMadrid_mapa.html`](Mapa/ForMadrid_mapa.html) (abrir en el navegador).

## Método

Para cada año Y y municipio:

| Componente | Cálculo | Datos |
|---|---|---|
| A · Déficit de empleo local | −ln(empleos / afiliados residentes corregidos) | Afiliados por centro de trabajo (31-dic Y-1) y por residencia (1-ene Y) |
| B · Presión de paro | paro / (paro + afiliados residentes corregidos) | Paro registrado (31-mar Y) |
| C · Desajuste sectorial | Disimilitud de Duncan entre los sectores del paro y del empleo local (4 sectores) | Paro por sector + afiliados por centro de trabajo y rama |

**Índice** = media de los z-scores de A, B y C (relativo entre los 179 municipios). **Corrección del 999**: los afiliados residentes se dividen por (1 − % sin municipio asignado del año). **Tipología**: k-means (k = 5) con A, B, C, cualificación (grupo de cotización), temporalidad (tipo de contrato) y variación del paro. Trazabilidad completa: [`Resultados/trazabilidad.md`](Resultados/trazabilidad.md).

## Reproducir

Requisitos: Python (probado con 3.14) y las versiones de `requirements.txt`.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python Codigo/00_descarga_ckan.py      # descarga los 7 ficheros desde la API CKAN (no sobrescribe)
python Codigo/01_carga_limpieza.py     # limpieza + validaciones (para si hay anomalías)
python Codigo/02_indice.py             # índice de desajuste 2021-2025
python Codigo/03_sensibilidad.py       # sensibilidad al denominador (Spearman)
python Codigo/04_clustering.py         # tipología de municipios
python Codigo/05_tendencias.py         # tendencias 2021-2025
python Codigo/06_mapa.py               # mapas PNG + herramienta HTML
```

Los scripts se ejecutan desde la raíz del repositorio o desde `Codigo/`.

### Datos de la Comunidad de Madrid (API CKAN)

`00_descarga_ckan.py` llama a `https://datos.comunidad.madrid/api/3/action/package_show?id=<dataset>` y descarga el recurso indicado. Comprobado el 23-nov-2026: los 7 ficheros descargados coinciden byte a byte (MD5) con los usados en el análisis.

| Fichero | Dataset CKAN | MD5 |
|---|---|---|
| `Datos/paro_registrado_municipios.csv` | `paro_por_nacionalidad_sector_y_sexo_09` | `8c6bea26a713ec8214b8b525c85f8457` |
| `Datos/afiliados_residencia_rama.csv` | `afiliados_por_residencia_y_rama` | `553b3fc182a6895d535d437c292b37b5` |
| `Datos/afiliados_centro_trabajo_rama.csv` | `afiliados_por_ubicacion_y_rama` | `39c3cf23307c1185083b56d152464b47` |
| `Datos/afiliados_residencia_grupo_cotizacion.csv` | `afiliados_por_residencia_y_grupo` | `fd1f5ef11bd7e143730112e52d305c3f` |
| `Datos/afiliados_residencia_contrato.csv` | `afiliados_por_residencia_y_contrato` | `82b7aa47b30d132802e4dfb5cd06bd5d` |
| `Datos/cursos_formacion_empleo.csv` | `cursos_formacion_profesional_empleo` | `b5eb21261b3aaa3a28e7b306e0dd4335` |
| `Mapa/limites_secciones_censales_2019.zip` | `secciones_censales` (recurso SHP) | `7d9fb3fc8b5debe3ff97e0d9d0cbb568` |

### Datos del INE

`Datos/poblacion_municipios_ine_202125.csv` (incluido en el repositorio): INE, Censo Anual de Población, [tabla 68535](https://www.ine.es/jaxiT3/Tabla.htm?t=68535&L=0), provincia 28 Madrid, sus 179 municipios, todos los grupos de edad, Sexo = Total, Nacionalidad = Total, 1-ene-2021 y 1-ene-2025. Exportado como CSV separado por tabuladores. Solo se usa en la prueba de sensibilidad.

## Estructura

```
Codigo/        scripts 00-06 + utilidades.py
Datos/         datos originales (no se modifican)
Resultados/    tablas limpias, índice, sensibilidad, tipología, tendencias, cifras clave, figuras
Mapa/          geometría, mapas PNG, herramienta HTML
Presentacion/  captura de la herramienta
```

## Limitaciones (declaradas)

- **Afiliados por residencia sin municipio asignado (código 999)**: 14,1 % (2021) → 16,7 % (2025). Por eso el índice es relativo y se aplica una corrección proporcional; la prueba con población INE 15-64 confirma el ranking.
- **Empleo por centro de trabajo**: hasta dic-2020 hay valores suprimidos («-», no son ceros); desde dic-2021 todos los valores vienen redondeados a múltiplos de 5. Totales: fila Total; componente sectorial solo en municipios con ≥ 500 empleos.
- **Municipios pequeños** (< 1.000 afiliados residentes, 74): se muestran, pero con fiabilidad baja y fuera de la tipología.
- Sectores muy agregados (4); el saldo empleo/residentes no son flujos origen-destino; paro registrado ≠ EPA; estacionalidad de marzo; 2020-2021 afectados por la COVID.
- **Cursos**: sin año; el 54 % de los presenciales y todos los de teleformación sin municipio → capa complementaria, no forma parte del índice.
- Tipología con silueta 0,24: orientativa.

## Licencia

Código: [MIT](LICENSE).

Datos incluidos en `Datos/` y `Mapa/` (copia sin modificar, descargada el 19-nov-2026; INE el 23-nov-2026):
- Comunidad de Madrid, Portal de Datos Abiertos (datos.comunidad.madrid): los 7 conjuntos se publican con licencia [Creative Commons Reconocimiento 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode.es). Fuente: Comunidad de Madrid.
- Instituto Nacional de Estadística (INE), Censo Anual de Población, tabla 68535. Fuente: INE. Reutilización permitida citando la fuente, según el aviso legal del INE.

Las tablas de `Resultados/` y los mapas son elaboración propia a partir de esos datos.
