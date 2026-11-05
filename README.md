# DATAMAD 2026 · Información técnica

Recursos técnicos para participantes en **DATAMAD 2026 · Hackathon de Datos Abiertos**, el datathon de datos abiertos de la Comunidad de Madrid.

Con la colaboración de la Universidad Rey Juan Carlos y la Universidad complutense de Madrid y Gaia-X España 

Este repositorio explica cómo acceder, descargar y verificar datos del **Catálogo de Datos Abiertos de la Comunidad de Madrid**, e incluye scripts listos para usar, para que los equipos dediquen su tiempo a construir soluciones y no a pelearse con las APIs.

> Para las bases oficiales, la inscripción, el programa y los premios, consulta siempre la web del evento:
> **https://eventos.urjc.es/155632/detail/datamad-2026.html**

---

## Índice

- [Sobre el evento](#sobre-el-evento)
- [Fechas clave](#fechas-clave)
- [Fuentes de datos](#fuentes-de-datos)
- [Acceso a los datos](#acceso-a-los-datos)
- [Contenido del repositorio](#contenido-del-repositorio)
- [Inicio rápido](#inicio-rápido)
- [Ejemplo: descarga y verificación de un conjunto de datos](#ejemplo-descarga-y-verificación-de-un-conjunto-de-datos)
- [Consejos para trabajar con los datos](#consejos-para-trabajar-con-los-datos)
- [Resolución de problemas](#resolución-de-problemas)
- [Enlaces útiles](#enlaces-útiles)

---

## Sobre el evento

DATAMAD es un datathon orientado a resolver problemas utilizando datos abiertos. Los participantes, de forma individual o en equipo, utilizan conjuntos de datos del **Portal de Datos Abiertos de la Comunidad de Madrid**, que pueden combinar con otras fuentes nacionales o internacionales, para desarrollar proyectos, estudios, aplicaciones o servicios que aporten **valor económico, social o medioambiental**.

| | |
|---|---|
| **Organizan** | Comunidad de Madrid (Consejería de Digitalización), Universidad Rey Juan Carlos (URJC), Universidad Complutense de Madrid (UCM) y Gaia-X España |
| **Quién puede participar** | Estudiantes universitarios, profesionales y entusiastas del análisis de datos |
| **Formato** | Individual o por equipos |
| **Coste** | Gratuito |
| **Formación** | Seminarios prácticos sobre datos abiertos e Inteligencia Artificial, presenciales u online, sin necesidad de conocimientos previos |
| **Sede de la jornada final** | URJC, Campus de Vicálvaro, Paseo de los Artilleros, Madrid |

## Fechas clave

| Fecha | Hito |
|---|---|
| Hasta el **5 de noviembre de 2026** | Inscripción abierta |
| **5 y 6 de noviembre de 2026** | Formación intensiva (UCM + online) |
| **Del 7 al 26 de noviembre de 2026** | Desarrollo de los proyectos por los equipos |
| **26 de noviembre de 2026** | Jornada final en la URJC Vicálvaro: charlas de especialistas, presentación de proyectos (al menos un miembro del equipo de forma presencial) y entrega de premios |

Las fechas proceden de los anuncios oficiales. Si hubiera cambios, prevalece la información de la web del evento.

---

## Fuentes de datos

Todos los proyectos deben utilizar uno o varios conjuntos de datos del catálogo regional.

| Fuente | URL |
|---|---|
| Catálogo de Datos Abiertos (web) | https://datos.comunidad.madrid/catalogo/ |
| API CKAN | https://datos.comunidad.madrid/api/3/action/ |
| Iniciativa de datos abiertos | https://www.comunidad.madrid/gobierno/datos-abiertos |
| Guía de reutilización | https://www.comunidad.madrid/gobierno/datos-abiertos/reutiliza-datos-abiertos-comunidad-madrid |

---

## Acceso a los datos

El catálogo funciona con **CKAN**, que ofrece una API REST estándar. No se necesita clave de API para leer datos públicos.

### Endpoints del catálogo

| Uso | Endpoint |
|---|---|
| Listar todos los conjuntos de datos | `GET /api/3/action/package_list` |
| Conjuntos de datos con sus recursos | `GET /api/3/action/current_package_list_with_resources` |
| Buscar conjuntos de datos | `GET /api/3/action/package_search?q=<texto>` |
| Listar grupos (temáticas) | `GET /api/3/action/group_list` |
| Detalle de un conjunto de datos | `GET /api/3/action/package_show?id=<id_conjunto>` |
| Detalle de un recurso (incluye URL de descarga) | `GET /api/3/action/resource_show?id=<id_recurso>` |

### Lectura de los registros (DataStore)

```
GET https://datos.comunidad.madrid/api/3/action/datastore_search?resource_id=<id_recurso>&limit=1000&offset=0
```

- `limit`: número de registros por petición
- `offset`: número de registros que se saltan
- `result.total`: número total de registros disponibles

**Importante:** la API devuelve un número limitado de registros por llamada (la pasarela, por ejemplo, devuelve 10 por defecto). Para obtener un conjunto de datos completo hay que **paginar**, aumentando `offset` hasta llegar a `result.total`, o descargar el fichero completo desde el campo `url` que devuelve `resource_show`.

### Ejemplo mínimo en Python

```python
import requests

BASE = "https://datos.comunidad.madrid/api/3/action"
RID = "<id_recurso>"

filas, offset, limit = [], 0, 5000
while True:
    r = requests.get(f"{BASE}/datastore_search",
                     params={"resource_id": RID, "limit": limit, "offset": offset}).json()
    lote = r["result"]["records"]
    filas += lote
    if not lote or len(filas) >= r["result"]["total"]:
        break
    offset += limit

print(len(filas), "registros descargados")
```

---

## Contenido del repositorio

```
.
├── README.md
├── descargar_afiliados_json.py   # Descarga un conjunto de datos completo en un único JSON
└── comparar_json.py              # Compara dos ficheros JSON (normalizado + estricto)
```

### `descargar_afiliados_json.py`

Descarga **todos los registros** de un conjunto de datos (no solo la primera página) y los guarda en un único fichero JSON en UTF-8. Prueba tres estrategias por orden y se detiene en la primera que funciona:

1. Descargar directamente el recurso JSON publicado del conjunto de datos (mediante `resource_show` / `package_show`).
2. Paginar el DataStore de CKAN con `limit` / `offset`.
3. Paginar la pasarela API con `limit` / `offset`.

Configura `RESOURCE_ID` y `OUTPUT_FILE` al principio del script para usarlo con cualquier otro conjunto de datos.

### `comparar_json.py`

Comprueba que dos ficheros JSON contienen los mismos datos, por ejemplo un fichero descargado mediante la API y el fichero original del catálogo. Realiza dos comparaciones:

| Modo | Pregunta que responde | Qué comprueba |
|---|---|---|
| **Normalizado** | ¿Contienen ambos ficheros la misma información? | Número de registros, campos, registros presentes solo en un fichero y diferencias de valores. Ignora el orden de las filas y el formato (`"1.234"` = `1234`, espacios sobrantes, `""` = `null`, mayúsculas en los nombres de campo). |
| **Estricto** | ¿Son ambos ficheros exactamente iguales? | Todo lo anterior, más los tipos de los valores (`"1500"` ≠ `1500` ≠ `1500.0`), el texto exacto, el orden de las filas y la identidad byte a byte (SHA-256). |

Los registros se emparejan por campos clave (detectados automáticamente o definidos en `KEY_FIELDS`), de modo que el informe indica exactamente **qué campo de qué registro** es distinto. El informe completo se guarda en `comparacion_resultado.json`.

---

## Inicio rápido

Requisitos: **Python 3.8 o superior**

```bash
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
pip install requests
```

Descargar un conjunto de datos:

```bash
python descargar_afiliados_json.py
```

Comparar dos ficheros:

```bash
python comparar_json.py                  # normalizado + estricto
python comparar_json.py --solo-normal    # solo normalizado
python comparar_json.py --solo-estricto  # solo estricto
```

---

## Ejemplo: descarga y verificación de un conjunto de datos

Conjunto de datos: **Afiliados a la Seguridad Social en alta laboral (media mensual) por sexo y edad – Comunidad de Madrid**
ID del recurso: `f809ef2a-8385-43a5-87c6-c079d217a658`

1. `descargar_afiliados_json.py` descargó el conjunto de datos completo mediante la API en
   `api_extraccionesafiliados-a-la-seguridad-social-en-alta-laboral-media-mensual-por-sexo-y-edad.-comu.json`.
2. `comparar_json.py` lo comparó con el fichero original del catálogo.

Resultado de la comparación estricta:

| Comprobación | Resultado |
|---|---|
| Registros (API / original) | 46.266 / 46.266 |
| Registros idénticos | 46.266 |
| Campos | 9 en ambos, en el mismo orden: `Año`, `Edad`, `Estado dato`, `Indicador`, `Periodo`, `Sexo`, `Territorio`, `Unidad`, `Valor` |
| Diferencias de valor o de tipo | 0 |
| Mismo orden de filas | Sí |
| Idénticos byte a byte | No |

**Conclusión:** la extracción mediante la API es una copia completa y exacta de los datos originales. Los ficheros solo se diferencian en cómo está escrito el texto JSON (sangría, espacios o codificación de caracteres), no en su contenido.

---

## Consejos para trabajar con los datos

- **Pagina siempre.** Una respuesta con exactamente 10, 100 o 1.000 filas suele ser una página, no el conjunto completo. Comprueba `result.total`.
- **Revisa el formato de los números.** Algunos ficheros usan el formato español (`1.234,5`). Conviértelos antes de hacer cálculos.
- **Lee los metadatos.** Campos como `Estado dato` (por ejemplo, provisional o definitivo) y `Unidad` determinan cómo interpretar los valores.
- **Usa UTF-8.** Los nombres de campo llevan tildes (`Año`). En Python, guarda los ficheros con `ensure_ascii=False` y ábrelos como UTF-8.
- **Verifica tus descargas** con `comparar_json.py` antes de construir sobre los datos.
- **Combina fuentes.** Las bases permiten enriquecer los datos regionales con otros datos abiertos nacionales o internacionales.
- **Cuida los servidores.** Usa páginas grandes (por ejemplo, 5.000 registros) en lugar de muchas peticiones pequeñas.

---

## Resolución de problemas

| Problema | Solución |
|---|---|
| Solo se devuelven 10 registros | Añade los parámetros `limit` y `offset`, o usa `descargar_afiliados_json.py`. |
| `resource_show` indica que no encuentra el recurso | Prueba la URL base alternativa `https://datos.comunidad.madrid/catalogo/api/3/action`. |
| `datastore_search` falla | Puede que el recurso no esté en el DataStore; descarga el fichero desde la `url` de `resource_show`. |
| Las tildes aparecen como `\u00f1` | Guarda el JSON con `ensure_ascii=False`. |
| La comparación dice "diferentes" pero los datos parecen iguales | Revisa la sección estricta: puede que las diferencias sean solo de formato, tipos u orden de las filas. |

---

## Enlaces útiles

- Web del evento e inscripción: https://eventos.urjc.es/155632/detail/datamad-2026.html
- Catálogo de Datos Abiertos: https://datos.comunidad.madrid/catalogo/
- Guía de reutilización e información de la API: https://www.comunidad.madrid/gobierno/datos-abiertos/reutiliza-datos-abiertos-comunidad-madrid
- Documentación de la API de CKAN: https://docs.ckan.org/en/latest/api/
- Documentación de la API DataStore: https://docs.ckan.org/en/latest/maintaining/datastore.html
- DATAMAD en LinkedIn: https://www.linkedin.com/company/datamad-hackathon-de-datos-abiertos/