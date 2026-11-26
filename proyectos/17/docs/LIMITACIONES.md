# Cobertura y limitaciones

La versión incluye mapa y calendario de escenarios, heatmap municipal, comparador, laboratorio y simulación de visitas. La demo se comprobó en Chromium en Linux. La predicción diaria presentada utiliza municipio y calendario, con evaluación retrospectiva. La integración estadística del tiempo previsto en la probabilidad diaria requiere validación adicional.

Los 1.052 partes de 2020–2023 se contrastaron con la exportación aportada. El histórico ampliado 2006–2019 procede de una copia pública de exportaciones EGIF. Solo 2020–2023 se habilita aquí para construir los ceros de entrenamiento.

2023 ya se había utilizado para comparar versiones del proyecto. Su evaluación tiene carácter retrospectivo. La meteorología se asigna mediante estaciones de la red CAM y distancia geográfica, con representatividad espacial limitada.

La superficie forestal municipal permanece ausente. La superficie total se identifica expresamente y no se usa como superficie forestal.

La tabla anual usa dos simulaciones CMIP6 para un punto de Madrid capital. El mapa de campaña aplica una regresión logística a esas temperaturas como aproximación regional. Véase PREDICCION_CAMPANAS.md para conocer las limitaciones de la validación. VPD mide demanda atmosférica de humedad. El sistema FWI completo no está implementado.

La referencia diaria se entrena sobre etiquetas diarias reales y calendario municipal. La ventana meteorológica del experimento termina siete días antes, para respetar el horizonte semanal. Los valores probabilísticos requieren más validación y calibración. La herramienta es experimental y su uso previsto es análisis preventivo.

El arranque multiplataforma se ha preparado mediante rutas relativas y Python estándar. La ejecución nativa en Windows y macOS está pendiente.
