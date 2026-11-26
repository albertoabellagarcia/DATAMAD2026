# Metodología de Clasificación y Explicabilidad Algorítmica

Este documento formaliza el modelo determinista de **Madrid Apoyo Especializado v1.8**, diseñado bajo el principio de **orientación informativa y trazabilidad registral**, nunca de diagnóstico clínico ni de recomendación opaca.

## 1. Principios Epistemológicos del Modelo

1. **Separación estricta entre dato registral e inferencia**: El sistema distingue qué consta explícitamente en los boletines/registros oficiales (`datos.madrid.es`, `datos.comunidad.madrid`) frente a lo que requiere confirmación directa en la sede.
2. **Prioridad absoluta de la evidencia sobre la proximidad**: Ningún recurso genérico próximo puede desplazar por encima a un centro con especialización confirmada, sin importar la cercanía kilométrica.
3. **Degradación honesta de la incertidumbre**: La falta de un dato oficial (edad no declarada, accesibilidad código `3` «sin información», apoyo no detallado) se explicita al ciudadano en lugar de rellenarse con suposiciones optimistas.

## 2. Niveles de Evidencia (`EvidenceLevel` y `EvidenceSublevel`)

| Nivel | Subnivel | Definición Operativa | Criterio Registral Exigido |
| :--- | :--- | :--- | :--- |
| **`A1`** | `A1` | **Especialización publicada** | El centro declara explícitamente la condición/perfil buscado **y** (si el usuario pide apoyos concretos) acredita esos apoyos en la misma sede. |
| **`A2`** | `A2_support` | **Especialización publicada; confirme el apoyo** | El centro declara explícitamente el perfil buscado, pero falta confirmar en ficha algún apoyo específico seleccionado. |
| **`A2`** | `A2_entity` | **Lo declara la entidad titular** | La entidad gestora o asociación es monográfica de esa condición (p. ej. AUCAVI, PAUTA, APNA), pero el registro específico de esa sede no lo detalla explícitamente; requiere confirmación en sede. |
| **`B1`** | `B1` | **Servicios relacionados revisados** | El centro comparte al menos `2` servicios asistenciales afines al perfil buscado sin regla negativa activa ni incompatibilidad vital. |
| **`B2`** | `B2` | **Posible recurso / limitado por regla negativa** | Afinidad asistencial parcial (`1` servicio relacionado) o bien aplicación de una regla negativa preventiva (topado máximo `B2`). |
| **`C`** | `C` | **Orientación general compatible** | Recurso social autorizado sin especialización explícita ni servicios relacionados directos para ese perfil, compatible en etapa vital y accesibilidad física. |

## 3. Reglas Negativas Anti-Sesgo (Limitación de Evidencia sin Exclusión)

El registro histórico de servicios sociales contiene términos amplios que, tratados ingenuamente por *keywords*, generarían falsos positivos graves. El motor aplica reglas negativas formales (`NEGATIVE_INFERENCE_RULES`), entre ellas:

- **Discapacidad intelectual ≠ TEA**: Que un centro atienda discapacidad intelectual no autoriza clasificarlo como especializado en autismo.
- **Atención Temprana general ≠ Parálisis cerebral o déficit psicomotor específico**: Los centros genéricos de Atención Temprana se topan en `B2` cuando se busca apoyo psicomotor específico sin mención expresa, preservándolos como visibles con advertencia explícita.
- **Enfermedad mental crónica ≠ TEA ni neurología (`NEG-006`)**: Evita confundir recursos de salud mental psicosocial con plazas clínicas de daño cerebral o neurodesarrollo.
- **Centro ocupacional ≠ Terapia ocupacional clínica**: Previene que talleres ocupacionales de inserción figuren como rehabilitación terapéutica sanitaria.

> **Comportamiento v1.8**: Ninguna regla negativa elimina el centro hacia `incompatible`. Su efecto es **limitar el nivel máximo (`B2` o `C`)** y registrar el motivo literal en `suitability_reasons`. Solo excluyen al apartado secundario de incompatibles:
> 1. **Etapa vital declarada explícitamente incompatible** (si no consta edad en el registro, el centro permanece visible marcado como `partial` y `Edad: no consta, confirmar`).
> 2. **Requisito de accesibilidad física solicitado no acreditado** por el código registral oficial.

## 4. Ordenación Lexicográfica Formal (`sort_rank`)

La función de puntuación `sort_rank` implementa un orden total determinista donde los pesos están separados en órdenes de magnitud estrictos para impedir compensaciones indeseadas:

```
sort_rank = evidenceRank + suitabilityRank + combinationRank + networkRank + sublevelRank + distRank
```

Donde:

| Componente | Valores Posibles | Rango Máximo | Propósito |
| :--- | :--- | :--- | :--- |
| `evidenceRank` | `A1: 1_000_000`, `A2: 2_000_000`, `B1: 3_000_000`, `B2: 4_000_000`, `C: 5_000_000` | `5_000_000` | Garantiza dominancia estricta del nivel de evidencia. |
| `suitabilityRank` | `complete: 0`, `partial: 100_000`, `unknown: 200_000`, `incompatible: 900_000` | `900_000` | Dentro de un nivel de evidencia, prioriza coincidencia completa frente a parcial. |
| `combinationRank` | `0` (todos), `20_000` (parcial en sede), `50_000` (ninguno confirmado) | `50_000` | Prioriza sedes que reúnen todos los apoyos solicitados. |
| `networkRank` | `0` (coincide preferencia de red o `all`), `30_000` (no coincide) | `30_000` | Refleja preferencia de red pública/concertada vs. privada autorizada. |
| `sublevelRank` | `0` (`A1`, `A2_support`, etc.), `10_000` (`A2_entity`) | `10_000` | Sitúa la confirmación directa en sede (`A2_support`) por delante de la inferida por titular (`A2_entity`). |
| `distRank` | `min(round(distance_km * 10), 9_999)` o `5_000` sin coordenadas | `9_999` | Desempata exclusivamente por distancia geográfica en igualdad de todo lo anterior. |

### Prueba de No-Interferencia (Invariante Matemático)

La suma máxima de los niveles subordinados a `evidenceRank` (excluyendo `incompatible`, que se separa previamente a otra sección de UI) es:

$$100\,000 + 50\,000 + 30\,000 + 10\,000 + 9\,999 = 199\,999 < 1\,000\,000$$

Y la suma máxima subordinada a `suitabilityRank` es:

$$50\,000 + 30\,000 + 10\,000 + 9\,999 = 99\,999 < 100\,000$$

Por tanto, **es matemáticamente imposible** que la proximidad geográfica, la preferencia de red o el subnivel alteren el orden jerárquico `A1 > A2 > B1 > B2 > C`, ni que un recurso `partial` supere a un recurso `complete` del mismo nivel de evidencia.

## 5. Accesibilidad Oficial Literal y Estimaciones de Desplazamiento

- **Códigos oficiales `datos.madrid.es`**:
  - `1`: Accesible (`wheelchair_access` confirmado).
  - `2`: Parcialmente accesible (`wheelchair_access` parcial, exige confirmación).
  - `3`: Sin información (nunca se filtra como accesible).
  - `4`: Lengua de signos (`sign_language`).
  - `5`: Señalización podotáctil (`tactile_signage`).
  - `6`: Bucle magnético (`magnetic_loops`).
- **Distancias y transporte público**: Las distancias se calculan mediante la fórmula esférica de Haversine desde el origen activo (coordenadas de centroide municipal, Madrid Centro por defecto o geolocalización efímera del navegador). Cuando `radius_km > 0` (por ejemplo `10`, `30`, `50` o `80 km`), los resultados georreferenciados fuera de radio quedan excluidos de la lista y del mapa; **`radius_km = 0` desactiva el corte kilométrico** (búsqueda sin límite de distancia). Los centros sin coordenadas registrales permanecen visibles en la lista con aviso expreso (`GEO-001/002`). El tiempo en transporte público (`calculatePublicTransitTime`) es una estimación matemática lineal orientativa (`est.`), nunca una consulta en tiempo real a horarios CRTM.
- **Accesibilidad de visualización territorial y comparativa**: Los marcadores en lienzo/DOM de Leaflet se complementan con un panel lateral sincronizado compuesto por botones nativos navegables por teclado y un comparador tabular dotado de `<caption>`, cabeceras `scope="col"`/`scope="row"` y región desplazable (`tabIndex={0}`), garantizando limpieza completa de instancia (`map.remove()`) al desmontar la pestaña.

## 6. Gobernanza Taxonómica, Offline y Validación Continua

- Toda condición con estado `approved` en `CORE_PROFILES` debe estar respaldada por un mínimo de **3 centros explícitos `A1` verificados** sobre el catálogo real vigente (verificado automáticamente por `specializedEngine.test.ts`). Las condiciones sin registros literales en los CSV oficiales vigentes (por ejemplo TDAH) se auditan en Gobernanza Taxonómica y no se exponen como falsos filtros públicos con 0 resultados.
- Los perfiles sin suficiente respaldo registral estructurado (`cerebral_palsy`) permanecen marcados como `experimental` hasta disponer de cobertura homogénea en ambos portales públicos.
- **Pruebas basadas en propiedades (`fast-check`)**: Se ejecutan `1000` iteraciones aleatorias en cada *suite* de pruebas verificando el invariante lexicográfico (`sort_rank(A1) < sort_rank(B1)` y `complete < partial`) y que ninguna regla negativa produce jamás niveles `A1`/`A2`.
- **Actualizaciones PWA (`registerType: 'prompt'`)**: Las actualizaciones del *Service Worker* se anuncian con un aviso accesible no intrusivo (*«Nueva versión disponible»*) para evitar recargas inesperadas durante una búsqueda activa.
