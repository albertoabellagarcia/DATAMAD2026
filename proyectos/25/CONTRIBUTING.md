# Guía de Contribución — Madrid Apoyo Especializado

Gracias por contribuir a mejorar la transparencia y la utilidad pública de **Madrid Apoyo Especializado** (`Apache-2.0`). Este proyecto sigue una ética estricta de **rigor registral**: nunca afirmamos ni inferimos lo que no consta expresamente en los conjuntos de datos oficiales de la Comunidad de Madrid y el Ayuntamiento de Madrid.

## Principios No Negociables

1. **Trazabilidad fuente a código**: Toda nueva condición, perfil, servicio de apoyo o regla de clasificación debe respaldarse en los ficheros oficiales de `datos.madrid.es` o `datos.comunidad.madrid` y declararse explícitamente en `src/data/specializedTaxonomy.ts`.
2. **Privacidad efímera y RGPD**: Nunca añadas telemetría, rastreadores externos, *cookies* analíticas, Google Fonts remotas ni almacenamiento persistente de perfiles clínicos o coordenadas GPS del usuario.
3. **Reglas negativas sin exclusión opaca**: Las reglas negativas limitan el nivel de evidencia (como máximo `B2` o `C`), nunca eliminan recursos compatibles salvo incompatibilidad expresa de etapa vital o accesibilidad arquitectónica solicitada.
4. **Cero datos sintéticos**: No escribas catálogos ficticios; las pruebas deben apoyarse en los fixtures verificados y sobre la descarga real vigente en `public/data/snapshots/`.

## Flujo de Desarrollo Local

```bash
git clone https://github.com/herasr/Madrid-Apoyo-Especializado.git
cd Madrid-Apoyo-Especializado
npm ci
npm run dev
```

### Comandos de Verificación Obligatorios antes de un Pull Request

```bash
# 1. Batería de pruebas unitarias, de regresión y de auditoría real sobre CSV
npm run test

# 2. Cobertura mínima de código (motor, parser, almacenamiento e ingesta)
npm run test:coverage

# 3. Comprobación estricta de tipos TypeScript (strict: true)
npm run lint

# 4. Compilación de producción y empaquetado PWA offline con subruta GitHub Pages
VITE_BASE_PATH='/Madrid-Apoyo-Especializado/' npm run build

# 5. Re-clasificación determinista offline tras cambios en parser o taxonomía
npx tsx scripts/ingest.ts --only-classify
```

## Cómo Proponer un Cambio en la Taxonomía o Reglas

1. Abre un *Issue* describiendo el identificador del recurso (`MAD-PK...` o `CAM-C...` / `CAM-SRV-...`), el valor literal del campo registral y el motivo por el que el motor actual asigna un nivel erróneo.
2. Si propones añadir una especialización explícita o regla negativa en `src/utils/officialRegistryParser.ts`, incluye al menos **3 registros reales confirmados** para perfiles `approved` y un caso de control anti-falso-positivo en `src/utils/specializedEngine.test.ts`.
3. Asegúrate de ejecutar `npx tsx scripts/ingest.ts --only-classify` para mantener sincronizado `public/data/snapshots/catalog-classified.json` sin alterar los CSV oficiales ni sus huellas SHA-256.

## Estilo de Commits

Utiliza mensajes descriptivos siguiendo [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(engine): ...`
- `fix(parser): ...`
- `chore(ci): ...`
- `docs(methodology): ...`
- `test(e2e): ...`
