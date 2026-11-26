# ForMadrid · DATAMAD 2026

Proyecto: índice de desajuste territorial del mercado laboral por municipio (Comunidad de Madrid) para decidir dónde reforzar la formación.
Equipo: JiaJie Daniel Zheng · Barbara Cui. Fuentes: Portal de Datos Abiertos de la Comunidad de Madrid (CKAN, sin clave) y una tabla del INE (población). Detalle y enlaces en FUENTES.md.

## Documentos/ (solo en la carpeta local del equipo; no se publica en el repositorio)
- Bases_DATAMAD_2026.pdf: bases de participación (rúbrica de 100 puntos, entrega máx. 3 diapositivas + 1 captura, 5 min + 5 min preguntas).
- Formacion_Alberto_Abella_DATAMAD_2026.pptx: diapositivas de la formación (CKAN, MELODA, Smart Data Models).

## Datos/
| Archivo | Contenido | Fecha de referencia | Codificación |
|---|---|---|---|
| paro_registrado_municipios.csv | Paro registrado por municipio, nacionalidad, sector y sexo | 31 marzo, 2006–2026 (2026 sin desglose por sector) | UTF-8, ; |
| afiliados_residencia_rama.csv | Afiliados por municipio de residencia y rama | 1 enero, 2014–2026 | UTF-8, ; |
| afiliados_centro_trabajo_rama.csv | Afiliados por municipio del centro de trabajo y rama | 31 diciembre, 1999–2025 (1999–2008 solo fila Total; desde 31-dic-2021 valores redondeados a múltiplos de 5) | UTF-8, ; |
| afiliados_residencia_grupo_cotizacion.csv | Afiliados por residencia y grupo de cotización | 1 enero | UTF-8, ; |
| afiliados_residencia_contrato.csv | Afiliados por residencia y tipo de contrato | 1 enero | UTF-8, ; |
| cursos_formacion_empleo.csv | Cursos de FP para el empleo (sin año; actualizado 26-sep-2025; ~72 % sin municipio) | instantánea | latin-1 |
| poblacion_municipios_ine_202125.csv | INE, Censo Anual de Población (tabla 68535): población de los 179 municipios de Madrid por grupo de edad (Sexo=Total, Nacionalidad=Total). Incluye una fila de total provincial (Municipios vacío): filtrarla | 1 enero 2021 y 2025 | latin-1, tabulador, miles con punto |

## Mapa/
- limites_secciones_censales_2019.zip: shapefile Seccionado_2019 (EPSG:25830; campos CDMUNI, CDDISTRITO, CDSECCION, Area_k2). Original, no se modifica.
- municipios_cm.geojson: 179 municipios (secciones disueltas por CDMUNI, WGS84) con el índice 2025 (generado por `Codigo/06_mapa.py`).
- mapa_indice_2025.png, mapa_tipologia_2025.png: mapas finales.
- ForMadrid_mapa.html: herramienta interactiva (abrir en el navegador).

## Claves para unir tablas
- Código de 4 dígitos en afiliados/paro = código INE de municipio (3 dígitos) + 1 dígito de control. Los 3 primeros coinciden con CDMUNI. En el fichero del INE el código es de 5 dígitos (28001…): usar los 3 últimos. 9999 (3 dígitos: 999) = «Sin municipio asignado».
- Alineación temporal: residencia año Y (1 ene) ↔ centro de trabajo año Y-1 (31 dic) ↔ paro año Y (31 mar).
- Paro: filtrar Nacionalidad=Total y Sexo=Total y sumar los 5 sectores (no existe la fila Nacionalidad=Total con Sector=Total; la suma coincide con Españoles+Extranjeros desde 2014).
- Excluir o marcar 2020 (COVID); 2021 atípico.

## Limitaciones a declarar
Sectores muy agregados (4–5), «No procede» ≈15 % en grupo de cotización, saldo empleo/residentes no son flujos origen-destino, paro registrado ≠ EPA, estacionalidad de marzo, denominador de población solo para 2021 y 2025 (INE); para otros años interpolar o usar afiliados residentes.

## Fuentes
Ver FUENTES.md (enlaces al Portal de Datos Abiertos y fecha de descarga: 19-nov-2026).

## Avisos de datos (revisión del 23-nov-2026)
Todos los ficheros de afiliados y paro: las 179 localidades coinciden con las del INE (código de 4 dígitos: usar los 3 primeros). Los de afiliados incluyen además el código 999 «Sin municipio asignado»; el de paro no.
1. Filtrar «Tipo territorio = Municipios». Los ficheros también contienen filas de «Comunidad de Madrid» y «Zonas Estadísticas»; sumarlas duplica totales.
2. Excluir la categoría «Total» (rama, grupo, contrato, sector) al sumar; si no, el total sale doble.
3. Afiliados por residencia: entre el 10 % (2014) y el 17 % (2026) de los afiliados figura en 999 «Sin municipio asignado» (16,7 % en 2025). Por centro de trabajo solo el 0,8 %. El cociente empleo/residentes queda inflado y no es una cifra absoluta: usarlo como índice relativo entre municipios y declararlo.
4. Centro de trabajo: valores «-» (suprimidos, no ceros) hasta el 31-dic-2020. Desde el 31-dic-2021 no hay «-» porque todos los valores vienen redondeados a múltiplos de 5: la fila Total puede diferir de la suma de ramas en ±15. Se usa la fila Total para los totales; la estructura sectorial solo en municipios con ≥ 500 empleos. El código 999 no tiene fila Total (total = suma de ramas).
5. Paro 2026: sin desglose por sector (último año con sectores: 2025).
6. Población INE: solo 2021 y 2025 y con fila de total provincial (filtrar).
7. Cursos: sin año, ~72 % sin municipio (todos los de teleformación y el 54 % de los presenciales).
8. Contrato: 2014-2015 sin la categoría «Contrato temporal».
9. Paro 2011: el total no coincide con Españoles+Extranjeros en algunos municipios (fuera del periodo analizado).
