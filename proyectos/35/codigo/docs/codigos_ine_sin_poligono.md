# Códigos de sección del INE sin dato en 2025 ni polígono (R-DEM-03)

**Fuente:** INE, tabla 69213 («Población por sección censal, sexo y edad»), y polígonos de las secciones censales 2025 del INE, ambos con licencia CC BY 4.0. Elaboración propia con datos extraídos del sitio web del INE: www.ine.es.

**Versión de los datos:** `20261113T190802Z`. Generado por `cercasalud build` (etapa de población, `src/cercasalud/poblacion.py`), que escribe `codigos_sin_dato_ni_poligono.csv` en la carpeta de datos procesados. Esta tabla es una copia de ese archivo.

## Qué son

La tabla 69213 contiene 48 códigos de sección de la Comunidad de Madrid sin ningún valor en el periodo 2025, aunque tienen dato en algún periodo anterior. Ninguno de ellos tiene polígono en la capa de secciones 2025 del INE. A la inversa, las 4.518 secciones con dato en 2025 tienen todas su polígono.

| Recuento | Valor |
|---|---:|
| Códigos sin dato en 2025 | 48 |
| De ellos, con polígono en la capa 2025 | 0 |
| Secciones con dato en 2025 y sin polígono | 0 |
| Con dato solo en 2021 | 8 |
| Con dato en 2021 y 2022 | 33 |
| Con dato de 2021 a 2024 | 7 |
| En Madrid capital | 34 |

## Cómo se tratan

- **No se imputan.** No se les asigna población cero ni se reparte población a partir de periodos anteriores.
- No se interpretan como habitantes omitidos. La población 2025 de la Comunidad (7.113.886 habitantes) se toma de las 4.518 secciones con dato, y cuadra con los agregados municipales y provinciales del propio INE.
- La causa más probable es un cambio en el seccionado: secciones suprimidas, divididas o renumeradas. **No se ha comprobado** sección por sección.

## Listado

| Código de sección | Código de municipio | Municipio | Periodos con dato |
|---|---|---|---|
| 2800505019 | 28005 | Alcalá de Henares | 2021, 2022 |
| 2800601020 | 28006 | Alcobendas | 2021 |
| 2800702026 | 28007 | Alcorcón | 2021 |
| 2800703028 | 28007 | Alcorcón | 2021 |
| 2801401006 | 28014 | Arganda del Rey | 2021, 2022 |
| 2804901001 | 28049 | Coslada | 2021 |
| 2804901011 | 28049 | Coslada | 2021 |
| 2804902007 | 28049 | Coslada | 2021 |
| 2804902013 | 28049 | Coslada | 2021 |
| 2807402012 | 28074 | Leganés | 2021, 2022 |
| 2807403005 | 28074 | Leganés | 2021, 2022 |
| 2807901124 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807903070 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807903088 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807904095 | 28079 | Madrid | 2021, 2022 |
| 2807904129 | 28079 | Madrid | 2021, 2022 |
| 2807906098 | 28079 | Madrid | 2021, 2022 |
| 2807907005 | 28079 | Madrid | 2021, 2022 |
| 2807907134 | 28079 | Madrid | 2021, 2022 |
| 2807908087 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807908130 | 28079 | Madrid | 2021, 2022 |
| 2807910004 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807910034 | 28079 | Madrid | 2021, 2022 |
| 2807910111 | 28079 | Madrid | 2021, 2022 |
| 2807910134 | 28079 | Madrid | 2021, 2022 |
| 2807910150 | 28079 | Madrid | 2021, 2022 |
| 2807911066 | 28079 | Madrid | 2021, 2022 |
| 2807913027 | 28079 | Madrid | 2021, 2022 |
| 2807913114 | 28079 | Madrid | 2021, 2022 |
| 2807913126 | 28079 | Madrid | 2021, 2022 |
| 2807914006 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807914019 | 28079 | Madrid | 2021, 2022 |
| 2807914066 | 28079 | Madrid | 2021, 2022 |
| 2807914068 | 28079 | Madrid | 2021, 2022 |
| 2807914074 | 28079 | Madrid | 2021, 2022 |
| 2807915104 | 28079 | Madrid | 2021, 2022 |
| 2807915145 | 28079 | Madrid | 2021, 2022 |
| 2807916041 | 28079 | Madrid | 2021, 2022 |
| 2807916047 | 28079 | Madrid | 2021, 2022 |
| 2807916056 | 28079 | Madrid | 2021, 2022 |
| 2807916072 | 28079 | Madrid | 2021, 2022 |
| 2807920014 | 28079 | Madrid | 2021, 2022 |
| 2807920016 | 28079 | Madrid | 2021, 2022, 2023, 2024 |
| 2807920019 | 28079 | Madrid | 2021, 2022 |
| 2807920024 | 28079 | Madrid | 2021, 2022 |
| 2811502010 | 28115 | Pozuelo de Alarcón | 2021, 2022 |
| 2812701027 | 28127 | Rozas de Madrid, Las | 2021 |
| 2813401023 | 28134 | San Sebastián de los Reyes | 2021, 2022 |
