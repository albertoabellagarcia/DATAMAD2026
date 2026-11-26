# Madrid Cuida

**Si un equipo de limpieza solo puede revisar veinte calles esta semana, ¿por cuáles empieza?**

Madrid Cuida ayuda a planificar rondas de revisión de muebles y enseres abandonados usando datos abiertos del Ayuntamiento de Madrid. Propone veinte paradas por semana, explica el motivo de cada calle y ordena el recorrido. La demostración cubre **Usera, Carabanchel, Puente de Vallecas y Villaverde**.

- **Autor:** Jose Armando Alarcon Arone · **DATAMAD 2026 · Proyecto 44**
- **Material:** [Presentación en PDF (3 minutos)](docs/madrid-cuida-datamad.pdf) · [Guion oral](docs/pitch-datamad.md) · [Repositorio completo en GitHub](https://github.com/JoseAAA/madrid-cuida)

---

## 1. El problema

Entre enero y septiembre de 2026, el Ayuntamiento recogió **6,37 millones de kilos de muebles abandonados en la calle** en estos cuatro distritos (**86,4 %** de todo el peso de muebles recogido allí). Madrid ya ofrece recogida programada, el 010 y vehículos con cámaras; **Madrid Cuida complementa ese trabajo antes de salir**, ayudando a decidir qué calles conviene revisar primero.

---

## 2. Cómo funciona y qué resultados obtiene

### Plan semanal y detalle por calle

De las **20 paradas**, **16** se eligen por previsión de nuevos avisos en los próximos siete días y **4** se reservan a calles con contenedores donde nadie ha avisado en los últimos 90 días (para evitar puntos ciegos). Al elegir una calle se ven sus portales, su historial, los contenedores cercanos y la próxima recogida programada.

![Plan semanal de Usera: 16 prioridades, 4 paradas de exploración y ficha de la calle de Campotejar](docs/capturas/01-plan-usera.png)

### Ejemplo real en Usera

El lunes **9 de febrero de 2026**, la **calle de Antonio López (n.º 149–268)** llevaba 30 días sin avisos. El modelo la colocó en el **puesto 11** y el jueves **12 de febrero** registró un aviso de muebles abandonados.

![Caso retrospectivo de la calle de Antonio López: puesto 11 sin avisos en 30 días y aviso registrado tres días después](docs/capturas/02-caso-antonio-lopez.png)

### Comparación en 45 semanas de 2026

Comparamos tres formas de elegir 20 calles cada semana (900 visitas propuestas por método). Un acierto significa que esa calle recibió al menos un aviso en los siete días siguientes.

![Resultados en Usera: 165 aciertos del modelo frente a 155 del historial completo y 134 del último mes](docs/capturas/03-resultados-usera.png)

| Distrito | Solo último mes | Todo el historial | Modelo Madrid Cuida | Método usado en la app |
| --- | ---: | ---: | ---: | --- |
| **Usera** | 134 / 900 | 155 / 900 | **165 / 900**\* | Modelo predictivo |
| **Carabanchel** | 191 / 900 | 154 / 900 | **217 / 900** | Modelo predictivo |
| **Puente de Vallecas** | 279 / 900 | 274 / 900 | **314 / 900** | Modelo predictivo |
| **Villaverde** | 100 / 900 | 104 / 900 | 106 / 900 | Avisos recientes\*\* |

*\*En Usera, el plan combinado de 16 prioridades + 4 de exploración obtuvo **167 / 900** aciertos y redujo la distancia del recorrido entre paradas de **22,05 km a 7,52 km**.*
*\*\*En Villaverde se mantiene la regla sencilla por prudencia porque la mejora del modelo fue pequeña.*

---

## 3. Datos abiertos utilizados

Los ficheros originales no se suben a GitHub por su tamaño, pero se descargan desde el portal oficial del Ayuntamiento de Madrid. La aplicación ya incluye las tablas resumidas y listas para usar.

| Fuente oficial | Qué aporta a la decisión |
| --- | --- |
| [Avisos de Madrid](https://datos.madrid.es/dataset/212411-0-madrid-avisa) | Qué calles recibieron avisos de muebles y en qué fecha. |
| [Callejero por tramos](https://datos.madrid.es/dataset/300734-0-mapas-callejero-subviales) | Todas las calles del distrito, incluidas las que nunca reciben avisos. |
| [Inventario de contenedores](https://datos.madrid.es/dataset/300276-0-contenedor-papel-carton-todos) | Dónde mirar exactamente al llegar a la calle. |
| [Calendario de recogida de enseres](https://datos.madrid.es/dataset/300606-0-muebles-mapas-enseres) | Cuándo está previsto que pase el servicio municipal por cada zona. |
| [Pesajes de limpieza urbana](https://datos.madrid.es/dataset/300152-0-limpieza-urbana) | Cuántos kilos de muebles se recogen en calle frente a otras modalidades. |

---

## 4. Cómo instalar y probar la aplicación

El código completo y los datos listos para ejecutar están en mi repositorio personal:
👉 **[https://github.com/JoseAAA/madrid-cuida](https://github.com/JoseAAA/madrid-cuida)**

Solo necesitas tener instalado **Git** y **[uv](https://docs.astral.sh/uv/)** (descarga Python 3.12 y todas las dependencias automáticamente). Luego ejecuta en tu terminal:

```sh
git clone https://github.com/JoseAAA/madrid-cuida.git
cd madrid-cuida
uv sync --locked
uv run --locked streamlit run app.py
```

Abre en tu navegador la dirección que aparece en pantalla (`http://localhost:8501`). También funciona sin conexión activando **Ajustes → Cartografía local**. Para comprobar la integridad del proyecto y las pruebas automáticas:

```sh
uv run --locked pytest
uv run --locked python -m madrid_cuida.distritos --verificar
```

---

## 5. Qué mejoras faltan por realizar

Madrid Cuida es hoy un prototipo funcional validado sobre datos históricos abiertos. Para convertirlo en una herramienta diaria de operación faltan cinco pasos clave:

1. **Validación en calle con el servicio de limpieza:** comparar dos rondas de igual duración para medir **muebles encontrados por hora** y aceras despejadas (hasta ahora se han medido avisos ciudadanos, no hallazgos físicos).
2. **Registro de inspecciones desde la aplicación:** permitir anotar en campo si había enseres o si el punto estaba limpio, para que el modelo aprenda de resultados reales y corrija zonas donde la ciudadanía avisa poco.
3. **Actualización automática de cada nueva publicación:** conectar la captura diaria de datos municipales con la regeneración automática de la lista semanal y el seguimiento del modelo sobre pronósticos guardados antes de conocer el resultado.
4. **Rutas sobre calles reales y tiempos de turno:** sustituir la distancia en línea recta entre tramos por el callejero transitable, los sentidos de circulación y la duración estimada de cada parada.
5. **Previsión diaria de carga y ampliación a más distritos:** estimar cuántos avisos esperar al día siguiente para dimensionar equipos, probar modelos compartidos entre distritos y extender la herramienta al resto de Madrid.

---

**Documentación ampliada:** [Especificación técnica](docs/spec.md) · [Auditoría y límites](docs/qa.md) · [Plan del proyecto](docs/plan.md) · [Guía de despliegue](docs/deploy-datamad.md) · [Cuadernos paso a paso](notebooks/) · [Licencia MIT](LICENSE)
