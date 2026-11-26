# Proyecto 37 · Sombra Útil

**Equipo:** Álex, Gala, Paula, David, Lucía, Alba, Jaime, Claudia y Emma.

Sombra Útil combina cartografía abierta, modelos geométricos de sombra y un agente de IA para ayudar a personas y equipos municipales a encontrar recorridos y espacios con más sombra y comparar posibles actuaciones. Busca reducir exposición al sol durante los meses cálidos y apoyar decisiones urbanas y presupuestarias con evidencia espacial reproducible.

## Entrega

- **Presentación (PPTX, cuatro diapositivas: tres de contenido y una de captura/QR):** [descargar desde esta carpeta](./Sombra_Util_Pitch_DataMAD_3min_QR.pptx).
- **Demo guiada:**  
  https://jocular-bonbon-683268.netlify.app/orion.html?vista=publicados&demo=1  
  Es un walkthrough con escenarios y respuestas preparados. Algunas capas y cifras son simuladas o precalculadas; no representa una consulta en tiempo real del motor ni una validación de campo.
- **Código, documentación técnica y evidencias reproducibles:**  
  https://github.com/alex-udit/sombra-util/tree/entrega/datamad-jurado  
  Incluye la demo separada del esqueleto Orion conectable, backend, motor geométrico, contratos, pruebas, manifiestos, procedencia de datos y documentación de alcance y limitaciones.

## Cómo interpretar los resultados

Las superficies y comparaciones son resultados de simulación condicionados por la geometría, los modelos digitales de superficie, la fecha y hora y la cobertura disponible. Cuando faltan datos, se indican como desconocidos o como `null`; no deben interpretarse como ausencia de sombra. Los costes de Callao no están confirmados con precios comparables y la viabilidad física de las actuaciones requiere verificación. La capa de afluencia se identifica por separado como histórica o simulada según el caso.

## Método, datos y reproducción

La documentación del repositorio técnico describe las fuentes abiertas utilizadas (cartografía y elevaciones del IGN/CNIG y conjuntos públicos municipales), licencias, hashes, fechas, transformaciones, contratos y comandos de reproducción. La geometría se procesa en coordenadas proyectadas para medir áreas y calcular sombras por instante. Cobertura, procedencia y limitaciones acompañan los resultados.

## Recorrido sugerido

1. Abre la demo y entra en el walkthrough.
2. Explora Callao, Sol y Plaza Mayor; cambia de franja y revisa cobertura, geometría y evidencias.
3. Compara las alternativas de toldo de Callao y distingue la ganancia simulada del coste desconocido.
4. Explora ventanas y el recorrido peatonal; distingue marcha, sol, sombra y falta de datos.
5. Prueba las preguntas sugeridas al agente. En esta demo responde con contenido guiado/preestablecido; la conexión a un proveedor real pertenece a la aplicación conectada.

Para instalación, arranque y ejecución de comprobaciones, consulta el README y la guía de entrega del repositorio técnico. Los datos conservan su procedencia y hashes cuando corresponde; los ficheros se distribuyen respetando las condiciones de sus fuentes.
