# Proyecto 37 · Sombra Útil

**Equipo:** Álex, Gala, Paula, David, Lucía, Alba, Jaime, Claudia y Emma.

Sombra Útil combina cartografía abierta, modelos geométricos de sombra y un agente de IA para ayudar a personas y equipos municipales a encontrar recorridos y espacios con más sombra y a comparar posibles actuaciones. El objetivo es reducir la exposición al sol en los meses cálidos y apoyar decisiones de diseño y presupuesto con evidencia espacial reproducible.

## Entrega

- **Presentación:** [Sombra_Util_Pitch_DataMAD_4_slides_Entrega.pptx](./Sombra_Util_Pitch_DataMAD_4_slides_Entrega.pptx). Incluye tres diapositivas de contenido y una cuarta con captura/QR, conforme a las instrucciones de entrega.
- **Demo guiada:** https://jocular-bonbon-683268.netlify.app/orion.html?vista=publicados&demo=1  
  Es un walkthrough de demostración con escenarios y respuestas preparados; algunas capas y cifras son simuladas o precalculadas. No representa una consulta en tiempo real del motor ni una validación de campo.
- **Código, documentación técnica y evidencias reproducibles:** https://github.com/alex-udit/sombra-util/tree/entrega/datamad-jurado  
  Incluye frontend de demo separado del esqueleto Orion conectable, backend, motor geométrico, contratos, pruebas, manifiestos, procedencia de datos y documentación de alcance y limitaciones.

## Cómo leer los resultados

Las superficies y comparaciones publicadas son resultados de simulación condicionados por la geometría, los modelos digitales de superficie, la fecha/hora y la cobertura disponible. Cuando faltan datos, se indican como desconocidos o como `null`; no deben interpretarse como ausencia de sombra. Los costes de Callao siguen sin confirmación comparable y la viabilidad física de las actuaciones requiere verificación. Los datos de afluencia de la demo están separados de la simulación de sombra y se identifican como históricos o simulados según el caso.

## Fuentes y método

La documentación enlazada desde el repositorio técnico detalla las fuentes abiertas utilizadas (cartografía y elevaciones del IGN/CNIG y conjuntos públicos municipales), sus licencias, hashes, fechas, transformaciones, contratos y comandos de reproducción. La geometría se procesa en coordenadas proyectadas para medir áreas y proyectar sombras por instante; la cobertura y las limitaciones quedan asociadas a cada resultado.

## Recorrido sugerido

1. Abre el enlace de demo y entra en el walkthrough.
2. Explora Callao, Sol y Plaza Mayor; cambia franja y revisa cobertura, geometría y evidencias.
3. Compara las alternativas de toldo de Callao y observa la diferencia entre ganancia simulada y coste conocido.
4. Prueba el caso de ventanas y el recorrido peatonal; distingue los tiempos de marcha, sol, sombra y falta de datos.
5. Consulta las preguntas sugeridas del agente de IA. En esta demo responde con contenido guiado/preestablecido; la conexión a un proveedor real pertenece a la aplicación conectada.

## Reproducibilidad y auditoría

Consulta el README y la guía de entrega del repositorio técnico para instalar el proyecto, arrancar los servicios, ejecutar comprobaciones y reproducir resultados. Los archivos grandes de datos se gestionan según sus fuentes y licencias; la documentación conserva su procedencia y hashes cuando corresponde.
