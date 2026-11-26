# Cifras clave · ForMadrid (borrador 23-nov-2026)

Listas para diapositiva. Entre corchetes, de dónde sale cada número (ver `trazabilidad.md`).

1. **179 municipios · 7 conjuntos de datos de la Comunidad de Madrid + INE · 2021-2025.**
   Empleo por centro de trabajo, afiliados por residencia, paro registrado, grupo de cotización, contrato, cursos de FP para el empleo (capa complementaria) y secciones censales (mapa). Descarga reproducible por API CKAN: los 7 ficheros coinciden byte a byte con los usados.

2. **1 de cada 6 afiliados (16,7 %) no tiene municipio de residencia asignado en 2025** (14,1 % en 2021).
   Sin corregir, el cociente empleo/residentes de la Comunidad «sube» de 1,15 a 1,18; corregido, se mantiene en **0,99 todos los años**: la subida es un artefacto del dato, no del mercado laboral.
   [afiliados_residencia_rama, código 999; afiliados_centro_trabajo_rama, fila Total → `correccion_999_agregado.csv`]

3. **El ranking es robusto: Spearman = 0,985** entre el índice con afiliados residentes corregidos y con población INE 15-64 (0,99 en los 103 municipios de fiabilidad alta; 16-19 de los 20 primeros coinciden), en 2021 y 2025.
   [`sensibilidad.csv`]

4. **26 municipios concentran el mayor desajuste (cuartil superior, fiabilidad alta): 16.000 parados registrados (5,4 % del paro de la Comunidad)**, con solo el 3,9 % de los afiliados residentes. Por volumen destaca **Parla** (7.519 parados); por intensidad, **Casarrubuelos, Villarejo de Salvanés, Cadalso de los Vidrios y Colmenar de Oreja**.
   [`indice_municipios.csv`, año 2025]

5. **Más de 18.000 parados registrados (6,4 %) tendrían que cambiar de sector para encajar con el empleo de su propio municipio** (disimilitud de Duncan ponderada, 4 sectores: cota inferior). Ahí es donde la formación para el empleo tiene más recorrido.
   [paro_registrado por sector + afiliados_centro_trabajo_rama por rama, 2025, municipios ≥ 500 empleos]

6. **La recuperación no llega igual a todos: el paro cayó un 34-35 % en los polos de empleo y los grandes municipios metropolitanos (2021-2025), pero solo un 27 % en los municipios de «paro alto y empleo poco cualificado» y un 19,5 % en los pequeños.**
   [`tendencias_por_tipo.csv`; paro registrado 31-mar-2021 vs 31-mar-2025; 2021 atípico post-COVID]

7. **La oferta formativa presencial no está donde más se necesita: 4,0 cursos por 1.000 parados en los 26 municipios de mayor desajuste frente a 7,7 en el resto; 18 de esos 26 no tienen ningún curso presencial localizado.**
   ⚠ Solo cuenta los 2.156 cursos presenciales/mixtos con municipio (de 7.628; el 54 % de los presenciales no trae municipio): orientativo, no concluyente.
   [cursos_formacion_empleo × `indice_municipios.csv` → `municipios_2025_completo.csv`]

## Advertencias
- Índice **relativo** (posición entre municipios), no una tasa oficial. Paro registrado ≠ EPA; marzo tiene estacionalidad.
- 74 municipios pequeños (< 1.000 afiliados residentes; junto con 2 municipios sin componente sectorial suman el 1,5 % del paro) se muestran aparte: con cifras tan bajas el índice es inestable.
- Desde dic-2021 el empleo por centro de trabajo viene redondeado a 5 (confidencialidad); no afecta a los totales (0,01 %) pero sí a la estructura sectorial de municipios pequeños.
- 2021: sin componente sectorial (ramas de dic-2020 con valores suprimidos); 2020-2021 marcados como atípicos (COVID).
- Tipología (k-means, k = 5): silueta 0,24 → orientativa, las fronteras entre tipos son difusas.
