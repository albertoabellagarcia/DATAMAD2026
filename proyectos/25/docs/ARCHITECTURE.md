# Arquitectura del Sistema — Madrid Apoyo Especializado v1.8

Este documento describe la arquitectura técnica de la aplicación, el pipeline determinista de ingesta registral y las garantías de privacidad, seguridad y funcionamiento sin conexión.

## 1. Visión General de Capas

```
┌───────────────────────────────────────────────────────────────────────────┐
│  FUENTES OFICIALES DE DATOS ABIERTOS (Administración Pública)             │
│  • datos.madrid.es: Catálogo Centros de Atención Social (Latin-1, CSV)    │
│  • datos.comunidad.madrid: Registro Centros (UTF-8, CSV)                  │
│  • datos.comunidad.madrid: Registro Servicios (UTF-8, CSV)                │
└───────────────────────────────────────┬───────────────────────────────────┘
                                        │ npm run ingest / GitHub Actions semanal
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  PIPELINE DE INGESTA VERIFICADA (scripts/ingest.ts)                       │
│  1. Descarga + validación HTTP 200 / anti-HTML / columnas obligatorias    │
│  2. verifyBaselineIntegrity(): comprueba SHA-256 previo antes de pisar    │
│  3. computeDiffs(): comparación fila a fila (altas, bajas, acc., coords)  │
│  4. buildCentresFromOfficialCSVs(): parseo UTM->WGS84 + anonimización RGPD│
│  5. Escritura atómica (writeFileAtomicSync) -> public/data/snapshots/     │
│     • *-latest.csv · snapshot-metadata.json · snapshot-diffs.json         │
│     • catalog-classified.json (1.086 recursos ya normalizados)            │
└───────────────────────────────────────┬───────────────────────────────────┘
                                        │ Vite Build + Workbox Precache
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  APLICACIÓN CLIENTE (React 19 + TypeScript strict + Leaflet + PWA)        │
│  • App.tsx + useDeferredValue(query) + validación estricta de URL         │
│  • liveSnapshotParser.ts: carga rápida desde catalog-classified.json      │
│  • specializedEngine.ts: evaluación explicable A1/A2/B1/B2/C + sort_rank  │
│  • Visor interactivo (Lista, Mapa clusterizado, Comparador, Auditoría)    │
│  • Exportaciones seguras (CSV anti-formula-injection, JSON sin GPS)       │
└───────────────────────────────────────────────────────────────────────────┘
```

## 2. Componentes Principales

### 2.1 Pipeline de Ingesta y Control de Integridad (`scripts/ingest.ts`)
- **Ejecución semanal automatizada**: El flujo `.github/workflows/weekly-ingest.yml` se ejecuta todos los lunes a las `03:00 UTC`.
- **Verificación de línea base (`verifyBaselineIntegrity`)**: Antes de sobrescribir `*-latest.csv`, el script calcula el SHA-256 del CSV vigente en disco y verifica que coincida con `snapshot-metadata.json` (con respaldo opcional desde Git `HEAD`). Así se previene la generación silenciosa de `0` diferencias cuando los datos ya han sido modificados parcialmente.
- **Escritura atómica**: Toda escritura de artefactos (`-latest.csv`, `snapshot-diffs.json`, `snapshot-metadata.json`, `catalog-classified.json`) utiliza un fichero temporal `.tmp.<pid>.<timestamp>` seguido de `fs.renameSync`.
- **Política `-latest` + Diffs**: En `public/data/snapshots/` solo se almacenan las últimas capturas vigentes para no inflar el repositorio, preservando el historial completo en el log de commits de Git y el resumen legible en `snapshot-diffs.json`.

### 2.2 Normalización Oficial y Anonimización RGPD (`src/utils/officialRegistryParser.ts`)
- **Conversión UTM 30N (ETRS89) a WGS84**: Las coordenadas proyectadas del registro autonómico se transforman mediante fórmulas analíticas transversales (`utm30NToWgs84`) validando el bounding box de la Comunidad de Madrid.
- **Cruce multi-fuente sin suplantación**: Se vinculan centros municipales (`MAD-PK*`) y autonómicos (`CAM-C*`, `CAM-SRV-*`) conservando `provenance_records` individuales por atributo (`official_name`, `specialisation`, `accessibility`, `coordinates`, `authorised_places`).
- **Privacidad de titulares personas físicas**: Los servicios individuales sin NIF jurídico ven anonimizados su denominación (`Profesional individual autorizado`), nombre de titular, teléfono y coordenadas exactas.
- **Normalización tipográfica española**: `formatOfficialSpanishName` preserva siglas (`CEPRI`, `APNA`, `ASPACE-TEA`, `S.A.U.`, `A.F.A.`) aplicando capitalización correcta en español.

### 2.3 Motor de Búsqueda Explicable (`src/utils/specializedEngine.ts`)
- **Evaluación transparente por matriz de criterios**: Cada recurso genera un `criterion_matrix` (`confirmed`, `confirm_required`, `not_stated`, `incompatible`) alimentado en el modal *«¿Por qué aparece este centro?»*.
- **Independencia de datos externos en tiempo de ejecución**: El cliente trabaja 100 % offline tras la primera carga gracias a la pre-clasificación en `catalog-classified.json` cacheada por Workbox (`vite-plugin-pwa`).

### 2.4 Resiliencia, Seguridad y Rendimiento en el Navegador
- **Separación de rutas con `BASE_URL`**: Todas las peticiones a `/data/...` utilizan `import.meta.env.BASE_URL` para operar tanto en raíz `/` como bajo subrutas (`/Madrid-Apoyo-Especializado/`).
- **`ErrorBoundary` y `StrictMode`**: Cualquier fallo inesperado de renderizado queda contenido con opción de recuperación accesible.
- **Validación de `localStorage` y URL**: `savedSearchesStorage.ts` valida estructuralmente los objetos cargados de `localStorage`; `App.tsx` bloquea búsquedas ante parámetros URL manipulados o fuera de taxonomía.
- **Content Security Policy (CSP)**: Inyectada en `dist/index.html` durante `vite build` impidiendo conexiones remotas ajenas al propio origen y teselas oficiales de OpenStreetMap.
