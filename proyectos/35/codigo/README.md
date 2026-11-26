# CercaSalud MAD

Herramienta local para planificar el acceso territorial a recursos de salud en la Comunidad de Madrid. Proyecto presentado a DATAMAD 2026.

- **A:** atención primaria pública, a pie y en transporte público.
- **B:** refugios climáticos oficiales, a pie.
- **C:** carencias coincidentes de A y B.

## Estado

En construcción (14/11/2026). El código calcula A, B, C y las actuaciones, y trae una app local. Este repositorio **no contiene resultados de cobertura**: se calculan en local con `build` sobre una versión de datos. Los límites del análisis están en `docs/limites.md`.

## Entorno

Requiere [uv](https://docs.astral.sh/uv/). uv instala CPython 3.12 y las versiones exactas de las dependencias fijadas en `uv.lock`.

```
uv sync
uv run pytest
uv run ruff check .
```

Los datos no se incluyen en el repositorio. Se guardan en local, en la carpeta `datos/` hermana del repositorio o en la que indique la variable `CERCASALUD_DATOS`:

```
uv run cercasalud fetch                        # descarga y crea una versión fechada (usa la red)
uv run cercasalud verify --snapshot <ID>       # recalcula los SHA-256 de esa versión
uv run cercasalud build --snapshot <ID>        # calcula sin red todas las etapas (o --etapa E)
# Las etapas cuyas entradas, código y configuración no cambiaron se omiten (R-ARQ-03); --forzar las recalcula.
# Etapas: primaria, poblacion, demanda, acceso_pie, acceso, refugios_pie, refugios, renta, candidatos_pie,
#         actuaciones, capas_app, contexto
uv run cercasalud app                          # app local en 127.0.0.1, sin conexión
```

Las etapas `acceso_pie`, `refugios_pie` y `candidatos_pie` usan R5 (r5py) y necesitan Java 21. La matriz de transporte público es un cálculo de horas que se lanza aparte y que `build` lee si existe; si no existe, el transporte queda «no evaluable (motor)».

## Licencias y atribuciones

- **Código:** MIT (ver `LICENSE`).
- **Datos:** este repositorio no contiene los datos de las fuentes. Cada fuente conserva su licencia, y la orden `fetch` los descarga en local. Solo incluye pequeñas tablas curadas en `curado/` (ver `curado/README.md`): las derivadas de OpenStreetMap van bajo ODbL.
- Fichas de fuentes y licencias: `docs/fuentes.md`. Caso de uso: `docs/caso_de_uso.md`.

### Atribuciones

- Datos de © [OpenStreetMap](https://www.openstreetmap.org/copyright) y sus colaboradores, disponibles bajo la [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/).
- Powered by [CRTM](http://www.crtm.es/). Los horarios GTFS se usan explotados (cálculo de rutas), no en bruto. El CRTM no respalda este proyecto.
- Elaboración propia con datos extraídos del sitio web del INE: www.ine.es. El INE no respalda este proyecto.
- Fuente de los datos: Comunidad de Madrid ([datos.comunidad.madrid](http://datos.comunidad.madrid)).
- Origen de los datos: Ayuntamiento de Madrid. El Ayuntamiento no patrocina este proyecto.
- Fuentes CC BY 4.0: [licencia](https://creativecommons.org/licenses/by/4.0/legalcode.es). Las modificaciones se indican en la tabla.
- Las citas de `docs/caso_de_uso.md` indican su fuente (Comunidad de Madrid y ayuntamientos de Madrid, Coslada y Getafe), su fecha y su enlace. Fuente: Ayuntamiento de Madrid, CALORMAD 2026.

### Fuentes que usa el código

| Fuente | Organismo | Licencia | Modificaciones |
|---|---|---|---|
| Registro de centros, servicios y establecimientos sanitarios | Comunidad de Madrid | CC BY 4.0 | Se elimina la columna personal `NIF` al leerlo. Se filtran los centros de salud y consultorios dependientes del servicio de salud regional |
| Población por sección censal, sexo y edad (tabla 69213) | INE | CC BY 4.0 | Periodo 2025 y sexo «Total». Se agrega en mayores de 65, 75 y 85 años |
| Secciones censales 2025 (polígonos) | INE | CC BY 4.0 | Solo polígonos de tipo sección |
| Horarios GTFS de Metro, Metro Ligero, Cercanías, EMT, autobuses interurbanos y urbanos | CRTM (catálogo de datos abiertos de la Comunidad de Madrid) | Licencia de datos abiertos del CRTM | Calendario de Metro extendido hasta el periodo de cálculo: es un supuesto declarado («horario tipo de Metro») |
| Extracto de OpenStreetMap de la Comunidad de Madrid | Colaboradores de OpenStreetMap (extracto de Geofabrik) | ODbL 1.0 | Red viaria para el cálculo de rutas. Edificios y suelo residencial para repartir la población dentro de cada sección |
| Mercados municipales con aire acondicionado en zonas comunes y su horario (lista de madrid.es y equipamientos municipales) | Ayuntamiento de Madrid | Aviso legal de madrid.es y CC BY 4.0 | Horario comercial curado a mano, sin teléfonos ni correos (`curado/refugios_mercados_madrid.csv`) |
| Recursos de Protección Civil | Ayuntamiento de Madrid | Condiciones generales de reutilización del Ayuntamiento de Madrid | Se descarga; todavía no se usa en ningún cálculo |
| Zonas básicas de salud | Comunidad de Madrid | CC BY 4.0 | Se descarga; no se usa en ningún cálculo |

La fecha de descarga de cada archivo consta en el manifiesto de la versión (`datos/snapshots/<ID>.json`) y en el `.source.json` de cada archivo.

### Licencias de las bases derivadas

- Las bases de datos derivadas de OpenStreetMap que se publiquen se distribuyen bajo ODbL, no bajo MIT.
- Los datos del Catastro no se usan.
- La licencia del CRTM exige mantener actualizada la información mostrada. Cómo se cumple está pendiente de definir.
