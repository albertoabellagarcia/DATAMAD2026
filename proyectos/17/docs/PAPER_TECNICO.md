# FireRisk Madrid. Análisis predictivo municipal

Abstract. Plataforma reproducible de análisis de incendios forestales para 179 municipios. Se contrastan 1.052 partes de 2020–2023 y se construyen modelos de ocurrencia mensual y diaria. La interfaz integra cartografía local, observaciones y previsiones, explicaciones, escenarios y planificación. La evaluación retrospectiva permite identificar límites de discriminación y calibración.

# Problema, fuentes y cobertura

El objetivo estadístico mensual es la presencia de al menos un parte en un municipio y mes. El objetivo diario se construye directamente con fechas de partes. La EGIF es la fuente oficial de referencia. Los archivos aportados incluyen meteorología horaria CAM 2020–2026, población, superficie y cartografía. La exportación del equipo coincide en identificadores y variables cotejadas con una copia pública de EGIF. La ampliación 2006–2019 se presenta como archivo histórico. Solo 2020–2023 se habilita para construir ceros del modelo. La superficie forestal municipal permanece pendiente.

# Preparación y método

Los códigos INE son cadenas de cinco dígitos y se contrastan con el catálogo municipal. Se aplican indicadores de validez horaria meteorológica. La estación de referencia se asigna con información de 2020. La meteorología climática para cada año usa exclusivamente años anteriores. El modelo mensual compara prevalencia, mes, municipio y mes, clima y territorio, e híbrido. La regresión logística usa regularización L2 y C=1. La imputación y estandarización se ajustan en entrenamiento. Los coeficientes expresan asociaciones y no porcentajes de importancia causal.

# Diseño experimental y resultados

Se ejecutan ventanas expansivas con evaluación de 2021, 2022 y 2023. La selección mensual compara Brier y AP en 2021–2022. Se ofrecen también evaluación espacial y comparación 2020–2022 frente a 2023. El umbral binario se documenta en las tablas. ROC-AUC, AP, Brier, Log Loss, precisión, recall, F1, matriz de confusión y recall de los veinte primeros se exportan.

            modelo  roc_auc       ap    brier
Prevalencia global 0.500000 0.076350 0.070868
Frecuencia por mes 0.662564 0.118568 0.071564
   Municipio + mes 0.757103 0.204772 0.070007
Clima y territorio 0.727964 0.163626 0.071731
           Híbrido 0.762084 0.206320 0.070875

# Predicción diaria y meteorología

La referencia diaria ajusta municipio y armónicos del calendario sobre etiquetas municipio-día. El experimento meteorológico emplea ventanas que terminan siete días antes de la fecha objetivo. Se compara sobre la misma muestra que las referencias. La interfaz semanal muestra la probabilidad histórica diaria y previsiones reales de Open-Meteo. El modelo de calendario no responde al tiempo previsto. La evaluación de 2023 diaria es retrospectiva y no demuestra transportabilidad a 2026.

                                    modelo  roc_auc       ap    brier
                               Prevalencia 0.500000 0.003046 0.003038
                                Calendario 0.669139 0.004949 0.003044
                    Municipio y calendario 0.759585 0.014368 0.003059
Municipio, calendario y tiempo antecedente 0.769355 0.009898 0.003058

# Escenarios, interpretación y discusión

Los escenarios favorable, central y adverso seleccionan meses históricos reales próximos a cuantiles 20, 50 y 80 del VPD. Conservan conjuntamente temperatura, humedad y precipitación observadas del análogo. La planificación 2027–2030 usa estos escenarios de referencia y evita extrapolar una tendencia con cuatro años de incendios. VPD=0,6108 exp(17,27 T/(T+237,3)) (1−HR/100), con temperatura y humedad simultáneas. Los intervalos Wilson describen frecuencias históricas y no intervalos de predicción futura. La asignación de visitas usa una regla explícita de proporcionalidad y restos mayores.

# Limitaciones, impacto y referencias

La evaluación 2023 ya había informado versiones previas. Se necesita una campaña posterior consolidada para validación externa. Faltan superficie forestal, combustible, interfaz urbano-forestal medida y etiquetas recientes completas. La previsión meteorológica tiene incertidumbre propia. FWI requiere componentes acumulativos, viento y observaciones normalizadas. No se implementa aquí. La aplicación permite estudiar territorio y reproducir comparaciones, con revisión humana en decisiones públicas.

Referencias verificables. EGIF, MITECO https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html . Copernicus https://climate.copernicus.eu/fire-weather-index . FAO Irrigation and Drainage Paper 56, capítulo 3 https://www.fao.org/4/X0490E/x0490e07.htm . Open-Meteo https://open-meteo.com/en/docs . Catálogo CAM https://datos.comunidad.madrid/catalogo/ . DATAMAD https://eventos.urjc.es/155632/detail/datamad-2026.html .