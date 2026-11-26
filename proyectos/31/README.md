# ¿Dónde hace falta? · Equipo 31

**Un servicio con datos abiertos para dos usuarios: la Administración, que decide dónde invertir, y el vecino, que quiere saber qué tiene cerca.**

## ▶ Vídeo de la demo (2 min)

[![Ver el vídeo de la demo (2 min)](video-demo.png)](https://donde-hace-falta.vercel.app/demo.mp4)

- **[▶ Ver el vídeo en el navegador](https://donde-hace-falta.vercel.app/demo.mp4)** (se reproduce al momento).
- **[Copia del vídeo en GitHub, en esta carpeta](demo-donde-hace-falta.mp4)** (pulsa el botón de descarga).

Sin voz y con rótulos.

- **Pruébalo:** https://donde-hace-falta.vercel.app
- **Presentación (4 diapositivas):** [donde-hace-falta-DATAMAD2026.pdf](donde-hace-falta-DATAMAD2026.pdf)
- **Código (MIT) y datos derivados (CC BY 4.0):** https://github.com/guillemolero10/donde-hace-falta
- **Integrante:** Guillermo Molero Jiménez

## Qué es

Cruza los registros oficiales de centros de la Comunidad de Madrid con la población por edad de sus 4.518 secciones censales (INE, censo de 2025). Mide qué vecinos tienen cerca un centro de salud, un hospital, una farmacia, un colegio o instituto o un desfibrilador, y dónde faltan plazas de residencia para mayores.

**Para la Administración («¿Dónde hace falta?»)**
- Mapa por sección censal y ranking por municipio, distrito o zona.
- **Tú decides:** colocas un centro nuevo y ves al momento cuántos vecinos ganan acceso o cuántas plazas se cubren.
- **El modelo** calcula la mejor ubicación y la compara con la tuya: una residencia de 94 plazas en Pinto logra el 68 % del óptimo; arrastrándola hacia Getafe, más del 90 %.
- **Madrid en 2030:** el mismo cálculo con la población proyectada (proyección oficial INE/Comunidad repartida por sección y validada con 2021-2025).

**Para el vecino («Mi municipio»)**
- Ficha de cada municipio y distrito: qué servicios tiene cerca frente a la media de la Comunidad y cómo está el aire hoy (red de calidad del aire de la Comunidad, dato horario).

**Agente de IA que calcula, no inventa**
- Preguntas en lenguaje natural, por ejemplo dónde pondría 3 residencias o cómo está el municipio de un familiar. El modelo (Muse Spark, de Meta) elige entre 5 herramientas de cálculo, mueve el mapa y explica. Cada cifra del texto se valida contra esas herramientas: 12/12 en la evaluación, unos 0,01 $ por pregunta. Sin IA, responde por reglas.

**Cifra clave:** para llegar a la media de España (IMSERSO, 4,05 plazas por cada 100 mayores de 65) faltan **10.048 plazas de residencia hoy** y **15.526 en 2030**.

## Conjuntos de datos

**Portal de datos abiertos de la Comunidad de Madrid** (CC BY 4.0):
- [Centros, servicios y establecimientos sanitarios](https://datos.comunidad.madrid/catalogo/dataset/centros_servicios_establecimientos_sanitarios)
- [Registro de centros de atención social](https://datos.comunidad.madrid/catalogo/dataset/atencion_social_registro_centros)
- [Oficinas de farmacia](https://datos.comunidad.madrid/catalogo/dataset/oficinas_farmacia)
- [Desfibriladores externos fuera del ámbito sanitario](https://datos.comunidad.madrid/catalogo/dataset/desfibriladores_externos_fuera_ambito_sanitario)
- [Centros educativos](https://datos.comunidad.madrid/catalogo/dataset/centros_educativos)
- [Municipios de la Comunidad de Madrid](https://datos.comunidad.madrid/catalogo/dataset/municipio_comunidad_madrid)
- [Proyecciones de población por sexo](https://datos.comunidad.madrid/catalogo/dataset/proyecciones_poblacion_por_sexo)
- [Calidad del aire: datos diarios horarios](https://datos.comunidad.madrid/catalogo/dataset/calidad_aire_datos_dia) y [estaciones](https://datos.comunidad.madrid/catalogo/dataset/calidad_aire_estaciones)

**Otras fuentes:** INE (censo por sección censal, tabla 69213, y seccionado de 2025), IGN, IMSERSO, Decreto 78/2017, Open-Meteo / Copernicus CAMS y OpenFreeMap / OpenStreetMap. Atribuciones completas en el README del repositorio.

## Cómo reproducirlo

Instrucciones completas en el [README del repositorio](https://github.com/guillemolero10/donde-hace-falta#cómo-reproducirlo). El pipeline en Python regenera los datos de la web: dos ejecuciones dan los mismos ficheros. El proyecto tiene casi 1.000 pruebas automáticas (780 de Vitest y 214 de pytest).

## Código reutilizado e IA

- `pipeline/alergia/ckan.py` se inspira en `MCP/servidor.py` de este repositorio (Alberto Abella). Está reescrito, sin copiar código.
- El cliente del modelo y el tope de gasto están adaptados de un proyecto propio anterior (DockClerk).
- El desarrollo se hizo con ayuda de asistentes de IA. El agente de la app usa Muse Spark (Meta).
