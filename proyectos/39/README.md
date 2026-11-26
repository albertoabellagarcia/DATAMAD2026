# 39 · Ojo Ciudadano

**Para que cualquier ciudadano pueda consultar y ver a dónde va su dinero: de cada organismo de la Comunidad de Madrid a cada empresa, con cada cifra enlazada a su fuente oficial.**

**Integrantes:** Ismael El Harrak · Ignacio Vallejo Garach

| | |
| --- | --- |
| **Web** | [ojo-ciudadano.iismael.workers.dev](https://ojo-ciudadano.iismael.workers.dev/) (no hace falta instalar nada) |
| **Presentación para el jurado** | [ojo-ciudadano.iismael.workers.dev/presentacion/jurado.html](https://ojo-ciudadano.iismael.workers.dev/presentacion/jurado.html) |
| **Presentación de la exposición** | [ojo-ciudadano.iismael.workers.dev/presentacion/](https://ojo-ciudadano.iismael.workers.dev/presentacion/) |
| **Código** | [github.com/iisma-ai/Ojo-Ciudadano](https://github.com/iisma-ai/Ojo-Ciudadano) (licencia MIT) |

Las presentaciones son 3D en tiempo real: se abren en Chrome y se avanza con la flecha derecha o con un clic.

![Página de inicio de Ojo Ciudadano](ojo-ciudadano-web.jpg)

## La propuesta

Ojo Ciudadano une los contratos y las subvenciones de la Comunidad de Madrid, señala dónde hay más riesgo y menos transparencia, y permite investigarlo todo en lenguaje natural. Cada cifra enlaza a su documento oficial.

## El problema

La información sobre el gasto de la Comunidad de Madrid es pública, pero está dispersa y es difícil de seguir. Contratos, subvenciones, presupuestos y convenios están en portales distintos, con formatos distintos y sin identificadores comunes. Datos clave, como cuántas empresas se presentaron a una licitación, a veces solo aparecen en PDF.

Saber qué empresas reciben más dinero de una consejería, o si contrata casi siempre con las mismas, exige hoy descargar ficheros de varios portales, unirlos a mano y dominar la jerga de la contratación pública.

## Datos utilizados

**Catálogo de Datos Abiertos de la Comunidad de Madrid** ([datos.comunidad.madrid](https://datos.comunidad.madrid)), entre otros:

- [Presupuestos liquidados de gastos, por órgano y fase de ejecución](https://datos.comunidad.madrid/dataset/presupuestos_liquidados_gastos_consolidados_por_organo_y_fase_ejecucion)
- [Presupuestos liquidados de ingresos, por capítulo](https://datos.comunidad.madrid/dataset/presupuestos_liquidados_ingresos_consolidados_por_capitulo_y_fase_ejecucion)
- [Presupuestos iniciales de gastos, por sección y capítulo](https://datos.comunidad.madrid/dataset/presupuestos_generales_iniciales_gastos_consolidados_por_seccion_y_capitulo)
- [Presupuesto por clasificación orgánica](https://datos.comunidad.madrid/dataset/1902000)
- [Contratos administrativos por tipo (estadística de la Junta Consultiva)](https://datos.comunidad.madrid/dataset/1914620)
- [Ayudas del presupuesto de la Unión Europea](https://datos.comunidad.madrid/dataset/1902617)
- [Recursos del sistema de financiación autonómica](https://datos.comunidad.madrid/dataset/1902613)
- [Registro de transparencia](https://datos.comunidad.madrid/dataset/registro_transparencia), [fundaciones](https://datos.comunidad.madrid/dataset/registro_fundaciones) y [cooperativas](https://datos.comunidad.madrid/dataset/registro_cooperativas)
- [Personal de la Comunidad de Madrid, por área de actividad](https://datos.comunidad.madrid/dataset/personal_comunidad_madrid_por_area_actividad_y_sexo) y [relación de puestos de trabajo](https://datos.comunidad.madrid/dataset/relacion_puestos_trabajo_funcionarios_resumida)

El asistente busca además en todo el catálogo para responder.

**Contratos y subvenciones, registro a registro** (el catálogo los publica solo agregados):

- [Portal de la Contratación Pública de la Comunidad de Madrid](https://contratos-publicos.comunidad.madrid/contratos)
- [Plataforma de Contratación del Sector Público](https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/LicitacionesAgregacion.aspx)
- [Base de Datos Nacional de Subvenciones](https://www.infosubvenciones.es)
- [Tribunal Administrativo de Contratación Pública de la Comunidad de Madrid](https://www.comunidad.madrid/tacp/busquedaresoluciones)
- [Portal de Transparencia: convenios](https://www.comunidad.madrid/transparencia/convenios)

En total, más de 1,35 millones de contratos (de enero de 2023 a septiembre de 2026), 872.821 concesiones de subvenciones y 132 organismos.

## Principales resultados

- **Unimos y limpiamos los datos:** licitaciones, contratos menores y subvenciones, sin duplicados y con los NIF normalizados, relacionados con el presupuesto y los registros de cada organismo.
- **Mapa del dinero, red del dinero y fichas** de cada empresa y cada organismo.
- **Señales de riesgo:** seis indicadores con metodología abierta comparan cada contrato con otros parecidos y señalan dónde mirar primero.
- **Aprendizaje automático:** un modelo no supervisado (Isolation Forest) destaca los contratos más atípicos frente a sus pares.
- **El agente de Ojo Ciudadano:** responde en lenguaje natural, consulta los datos en modo de solo lectura y cita la fuente oficial de cada cifra.

Son indicadores de riesgo, no acusaciones: indican dónde mirar, siempre con el enlace al expediente oficial.

## Utilidad, impacto y viabilidad

- **Utilidad.** Periodistas de datos, ONG, órganos de control como la Cámara de Cuentas, la propia Administración, las empresas y cualquier ciudadano ven en minutos lo que hoy exige días de descargas y cruces.
- **Impacto.** Más control ciudadano del gasto, con metodología abierta: señala dónde hay más riesgo y menos transparencia, sin acusar a nadie, y siempre con el enlace al documento oficial.
- **Viabilidad.** Solo usa datos públicos y reutilizables, y el código es abierto (licencia MIT), reproducible por código y probado. Se despliega con pocos recursos, y como la Plataforma de Contratación y la BDNS son nacionales, el método se puede extender a otras administraciones.

Más detalle, instrucciones para ejecutarlo y documentación completa en el [repositorio del proyecto](https://github.com/iisma-ai/Ojo-Ciudadano).
