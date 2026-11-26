# Trazabilidad de datos · ForMadrid

De dónde sale cada variable del índice. Todos los ficheros están en `Datos/` (sin modificar); las tablas limpias, en `Resultados/datos_limpios/`, generadas por `Codigo/01_carga_limpieza.py`.

## Variables del índice (año del índice Y = 2021…2025)

| Variable | Qué mide | Fichero original (dataset CM) | Filtros | Fecha de referencia | Tabla limpia |
|---|---|---|---|---|---|
| **E** empleo | Puestos de trabajo afiliados en centros del municipio | `afiliados_centro_trabajo_rama.csv` (afiliados_por_ubicacion_y_rama) | Tipo territorio = Municipios; Rama = **Total** | **31-dic de Y-1** | `empleo_centro_trabajo.csv` (`anio_indice` = Y) |
| Empleo por sector | Estructura sectorial del empleo local | mismo fichero | Ramas ≠ Total, agrupadas en 4 sectores; sin «No consta» | 31-dic de Y-1 | mismas columnas `sec_*` |
| **R** residentes | Afiliados que viven en el municipio | `afiliados_residencia_rama.csv` (afiliados_por_residencia_y_rama) | Municipios; Rama = Total; 999 aparte | **1-ene de Y** | `residentes_afiliados.csv` |
| s<sub>Y</sub> % sin asignar | Afiliados por residencia en «Sin municipio asignado» (999) | mismo fichero | 999 / (179 municipios + 999) | 1-ene de Y | `../cobertura_sin_asignar.csv` |
| **U** paro | Paro registrado total y por sector | `paro_registrado_municipios.csv` (paro_por_nacionalidad_sector_y_sexo_09) | Municipios; Nacionalidad = Total; Sexo = Total; **suma de los 5 sectores** | **31-mar de Y** | `paro_registrado.csv` |
| **P** población 15-64 | Denominador alternativo (sensibilidad) | `poblacion_municipios_ine_202125.csv` (INE, tabla 68535) | Sexo = Total; Nacionalidad = Total; suma de grupos 15-19 … 60-64 | 1-ene 2021 y 2025 | `poblacion_15_64.csv` |
| Perfil (para clustering) | Grupo de cotización y tipo de contrato de los residentes | `afiliados_residencia_grupo_cotizacion.csv`, `afiliados_residencia_contrato.csv` | Municipios; categorías ≠ Total | 1-ene de Y | `residentes_grupo_cotizacion.csv`, `residentes_contrato.csv` |
| Cursos (capa complementaria) | Oferta de FP para el empleo | `cursos_formacion_empleo.csv` | — (pendiente) | instantánea sep-2025 | — |

Agregación a 4 sectores (común a empleo, residentes y paro): Agricultura; Industria (= Minería, industria y energía); Construcción; Servicios (= distribución y hostelería + servicios a empresas y financieros + otros servicios + inmobiliarias).

## Componentes del índice (`Codigo/02_indice.py`)

| Componente | Fórmula | Datos que usa |
|---|---|---|
| R corregido | R / (1 − s<sub>Y</sub>) | residentes + % 999 |
| A · Déficit de empleo local | −ln(E / R corregido) | centro de trabajo (Total) + residencia |
| B · Presión de paro | U / (U + R corregido) | paro + residencia |
| C · Desajuste sectorial | Disimilitud de Duncan entre sectores del paro y sectores del empleo local | paro por sector + centro de trabajo por rama. Solo si E ≥ 500 y año ≥ 2022 |
| Índice | media de los z-scores disponibles de A, B, C | — |

Sensibilidad (`Codigo/03_sensibilidad.py`): se repiten A y B con P (15-64) como denominador en 2021 y 2025 y se comparan rankings (Spearman).

## Particularidades detectadas en los datos (23-nov)

1. **Centro de trabajo**: hasta el 31-dic-2020 hay valores «-» (suprimidos) por rama. **Desde el 31-dic-2021 todos los valores están redondeados a múltiplos de 5** (100 %, frente a ~20 % antes), y la fila Total puede diferir de la suma de ramas en ±15. Decisión: totales = fila Total; sector solo con E ≥ 500.
2. **Centro de trabajo**: el fichero empieza en 1999, pero 1999-2008 solo tiene la fila Total. El código 999 no tiene fila Total en ningún año (su total = suma de ramas, sin «-»).
3. **Paro**: no existe la combinación Nacionalidad = Total + Sector = Total; el total se obtiene sumando los 5 sectores y coincide con Españoles + Extranjeros desde 2014 (en 2011 hay diferencias; fuera del análisis).
4. **Contrato**: 2014-2015 sin la categoría «Contrato temporal».
5. **Residencia**: 999 pasa del 14,1 % (2021) al 16,7 % (2025); en centro de trabajo, del 0,6 % al 0,8 %.
