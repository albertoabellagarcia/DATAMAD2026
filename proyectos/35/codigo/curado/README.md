# Datos curados a mano

Pequeñas tablas que completan las fuentes oficiales. Cada fila lleva su método y su evidencia, y la etapa que la usa declara en su `resumen.json` qué filas aplicó.

## `primaria_coordenadas_osm.csv`

Coordenadas (EPSG:25830) de los 8 centros de primaria pública que el registro sanitario publica sin coordenadas. Las usa la etapa `primaria` de `build`. Solo rellenan coordenadas vacías: nunca sustituyen las del registro.

- **Origen:** OpenStreetMap, extracto `madrid-261112.osm.pbf` (Geofabrik, 12/11/2026). © OpenStreetMap contributors, datos disponibles bajo la Open Database License (ODbL): https://www.openstreetmap.org/copyright. Esta tabla es una base de datos derivada de OSM y se distribuye bajo la ODbL.
- **Método** (14/11/2026, `fases/H1_datos_normalizados/ubicar_centros/candidatos_osm.py`, en el repositorio raíz):
  - se buscan elementos sanitarios de OSM a menos de 400 m de las calles del término municipal con el nombre de la dirección del registro, y portales con la misma calle y número;
  - se eligió a mano, con su motivo en la columna `nota`.
- **Precisión (`precision`):**
  - `centro_y_portal_osm`: centro de salud de OSM con el mismo portal que el registro;
  - `centro_osm`: centro de salud de OSM junto a la calle de la dirección;
  - `calle_osm`: sin centro ni portal en OSM, se usa el centroide de los tramos de la calle (error de posición de cientos de metros). Afecta a los consultorios de Villar del Olmo (CS11438) y de Gargantilla del Lozoya y Pinilla de Buitrago (CS9495).
- **Límite:** que el nombre del centro de OSM corresponda al número de registro es una inferencia por la dirección. No está contrastado con una fuente oficial.

## `refugios_mercados_madrid.csv`

Los 43 mercados municipales de Madrid con aire acondicionado en zonas comunes (SPEC D-28), con el horario comercial curado. Es una copia de `fases/H4_situacion_inicial_B_C/evidencias_listas_diarias_20261114/mercados_horarios_curados.csv` del 14/11/2026, en el repositorio raíz:
- primera codificación de Claude;
- segunda lectura de 32 fichas por el mismo agente (D-35), con el domingo de San Antón corregido.

- **Origen:** lista de mercados con aire acondicionado de madrid.es y conjunto de equipamientos municipales. «Origen de los datos: Ayuntamiento de Madrid». No incluye teléfonos ni correos (comprobado el 14/11).
- **Supuesto de acceso (D-33):** `acceso_zona_climatizada` es `no_consta` en los 43. El acceso se estima dentro del horario comercial y fuera de él no se presume.
- **La segunda codificación independiente del 20 % (R-TMP-01) la hace el usuario.** Está pendiente.

## `refugios_coordenadas_osm.csv`

Coordenada del mercado de Vicálvaro (PK 12409), que el conjunto de equipamientos no trae. Se tomó del nodo «Mercado de Vicálvaro» de OpenStreetMap (11083489393), a 122 m del Paseo de los Artilleros. © OpenStreetMap contributors, ODbL.
