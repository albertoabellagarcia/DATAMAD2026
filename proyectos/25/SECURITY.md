# Política de Seguridad y Privacidad — Madrid Apoyo Especializado

## Alcance de la Seguridad del Proyecto

**Madrid Apoyo Especializado** es una aplicación web estática (*Client-Side SPA / PWA*) sin base de datos de usuarios, sin servidor de sesiones ni procesamiento remoto de datos personales.

### Controles Técnicos Implementados

- **Content Security Policy (CSP) estricta en producción**: La compilación inyecta en `dist/index.html` políticas restrictivas (`default-src 'self'`, `connect-src 'self'`, `font-src 'self'`, `img-src 'self' data: blob: https://tile.openstreetmap.org https://*.tile.openstreetmap.org`, `worker-src 'self'`, `manifest-src 'self'`) evitando ejecución de scripts de terceros o exfiltración hacia dominios no autorizados.
- **Neutralización de CSV Injection (Formula Injection)**: Todo valor exportado mediante `buildResultsCsv` que comience por `=`, `+`, `-`, `@`, tabulación o retorno de carro es escapado automáticamente (`'`) siguiendo las recomendaciones OWASP.
- **Validación estricta de URL y `localStorage`**: Los parámetros de consulta URL se validan contra la taxonomía y el nomenclátor oficial de municipios de la Comunidad de Madrid antes de evaluarse; las búsquedas guardadas en `localStorage` pasan por validación de esquema estricta en tiempo de ejecución.
- **Integridad criptográfica SHA-256 e inmutabilidad atómica en ingesta**: `scripts/ingest.ts` valida los encabezados, detecta respuestas HTML de error, verifica SHA-256 byte a byte sobre disco y escribe los ficheros mediante escritura atómica temporal (`writeFileAtomicSync`).
- **Privacidad efímera (RGPD)**:
  - Las coordenadas del navegador nunca salen del dispositivo ni se incluyen en enlaces compartidos o exportaciones JSON/CSV.
  - Los titulares personas físicas sin NIF jurídico se anonimizan automáticamente durante la ingesta (`officialRegistryParser.ts`).
- **Supply Chain en CI/CD**: Todos los flujos de GitHub Actions fijan las acciones por SHA de commit completo (`40` caracteres) y las dependencias se auditan mediante Dependabot semanalmente.

## Notificación Responsable de Vulnerabilidades

Si detectas una vulnerabilidad de seguridad (por ejemplo, XSS en el renderizado de nombres registrales, inyección CSV, exposición inadvertida de datos personales en `catalog-classified.json` o fallo de validación):

1. **No abras un Issue público** con los detalles de explotación antes de su corrección.
2. Envía un reporte privado mediante **GitHub Security Advisories** en el repositorio (`Security → Advisories → Report a vulnerability`) indicando:
   - Versión o commit afectado.
   - Pasos exactos de reproducción o payload de prueba.
   - Impacto estimado.
3. Responderemos acusando recibo en un plazo máximo de **72 horas** y publicaremos un parche verificable junto con las pruebas de regresión correspondientes en Vitest.
