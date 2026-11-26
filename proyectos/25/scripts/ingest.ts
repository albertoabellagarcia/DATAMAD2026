/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado - Script de Ingesta Real de Datos Registrales
 * Descarga las fuentes oficiales de datos abiertos:
 *   1. Ayuntamiento de Madrid (datos.madrid.es) - Catálogo de Centros de Atención Social (Latin-1)
 *   2. Comunidad de Madrid (datos.comunidad.madrid) - Registro General de Centros de Atención Social (UTF-8)
 *   3. Comunidad de Madrid (datos.comunidad.madrid) - Registro General de Servicios de Atención Social (UTF-8)
 * Valida integridad (HTTP 200, ausencia de páginas HTML 404, cabeceras y filas mínimas),
 * verifica firma SHA-256 byte a byte sobre el fichero guardado en disco y calcula diferencias reales.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { buildCentresFromOfficialCSVs } from '../src/utils/officialRegistryParser';

export interface OfficialSourceSpec {
  source_id: 'madrid_municipal' | 'cam_centros' | 'cam_servicios';
  source_name: string;
  source_url: string;
  latest_file: string;
  encoding: 'latin1' | 'utf-8';
  required_headers: string[];
  min_rows: number;
}

export const OFFICIAL_SOURCES: OfficialSourceSpec[] = [
  {
    source_id: 'madrid_municipal',
    source_name: 'Catálogo de Centros de Atención Social (Ayuntamiento de Madrid - datos.madrid.es)',
    source_url: 'https://datos.madrid.es/dataset/212774-0-atencion-social/resource/212774-0-atencion-social-csv/download/212774-0-atencion-social-csv.csv',
    latest_file: 'snapshot-latest.csv',
    encoding: 'latin1',
    required_headers: ['PK', 'NOMBRE', 'ACCESIBILIDAD'],
    min_rows: 100
  },
  {
    source_id: 'cam_centros',
    source_name: 'Registro de Centros de Atención Social (Comunidad de Madrid - datos.comunidad.madrid)',
    source_url: 'https://datos.comunidad.madrid/dataset/b8cdb7f7-3185-4938-800a-fefda72333f5/resource/0d815439-396e-4975-983e-5bb421f617a0/download/atencion_social_registro_centros.csv',
    latest_file: 'cam-centros-latest.csv',
    encoding: 'utf-8',
    required_headers: ['numero_registro', 'sector', 'denominacion', 'plazas_autorizadas_numero'],
    min_rows: 100
  },
  {
    source_id: 'cam_servicios',
    source_name: 'Registro de Servicios de Atención Social (Comunidad de Madrid - datos.comunidad.madrid)',
    source_url: 'https://datos.comunidad.madrid/dataset/95c75a5f-40ea-4af7-8b62-860918224c02/resource/1feb4b85-58da-4178-9391-f8821629ed7e/download/atencion_social_registro_servicios.csv',
    latest_file: 'cam-servicios-latest.csv',
    encoding: 'utf-8',
    required_headers: ['numero_registro', 'sector', 'tipo', 'denominacion'],
    min_rows: 100
  }
];

export interface SourceIngestionRecord {
  source_id: 'madrid_municipal' | 'cam_centros' | 'cam_servicios';
  source_name: string;
  source_url: string;
  file: string;
  encoding: 'latin1' | 'utf-8';
  sha256_hash: string;
  file_size_bytes: number;
  extracted_records_count: number;
  status: 'SUCCESS' | 'FAILED';
}

export interface IngestionMetadata {
  ingestion_id: string;
  timestamp: string;
  previous_timestamp?: string | null;
  source_url: string;
  sha256_hash: string;
  file_size_bytes: number;
  extracted_records_count: number;
  total_combined_records: number;
  status: 'SUCCESS' | 'FAILED';
  verification_notes: string;
  sources: SourceIngestionRecord[];
}

export interface RealSnapshotDiff {
  change_id: string;
  change_type:
    | 'centre_added'
    | 'centre_removed'
    | 'centre_renamed'
    | 'service_added'
    | 'service_removed'
    | 'access_route_changed';
  centre_id: string;
  centre_name: string;
  previous_snapshot: string;
  current_snapshot: string;
  detail: string;
  reason: string;
  category: 'alta' | 'baja' | 'servicio' | 'acceso';
}

export function parseCSV(text: string): string[][] {
  const clean = text.replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentVal = '';
  let insideQuote = false;

  for (let i = 0; i < clean.length; i++) {
    const char = clean[i];
    const nextChar = clean[i + 1];

    if (char === '"' && insideQuote && nextChar === '"') {
      currentVal += '"';
      i++;
    } else if (char === '"') {
      insideQuote = !insideQuote;
    } else if (char === ';' && !insideQuote) {
      currentRow.push(currentVal.trim());
      currentVal = '';
    } else if ((char === '\r' || char === '\n') && !insideQuote) {
      if (char === '\r' && nextChar === '\n') i++;
      currentRow.push(currentVal.trim());
      if (currentRow.length > 1) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentVal = '';
    } else {
      currentVal += char;
    }
  }
  if (currentRow.length > 1) {
    currentRow.push(currentVal.trim());
    rows.push(currentRow);
  }
  return rows;
}

interface NormalizedRowSummary {
  id: string;
  name: string;
  phone: string;
  address: string;
  places: string;
  accessibility: string;
  coords: string;
}

function summarizeSourceRows(sourceId: OfficialSourceSpec['source_id'], rows: string[][]): Map<string, NormalizedRowSummary> {
  const map = new Map<string, NormalizedRowSummary>();
  if (rows.length < 2) return map;
  const h = rows[0].map(col => col.trim().toLowerCase());
  const idx = (name: string) => h.indexOf(name.toLowerCase());

  if (sourceId === 'madrid_municipal') {
    const pkI = idx('pk');
    const nameI = idx('nombre');
    const phoneI = idx('telefono');
    const viaClaseI = idx('clase-vial');
    const viaNameI = idx('nombre-via');
    const numI = idx('num');
    const accI = idx('accesibilidad');
    const latI = idx('latitud');
    const lonI = idx('longitud');

    for (let i = 1; i < rows.length; i++) {
      const r = rows[i];
      const pk = r[pkI]?.trim();
      if (!pk) continue;
      const addr = [r[viaClaseI], r[viaNameI], r[numI]].filter(Boolean).join(' ').trim();
      const lat = latI >= 0 ? (r[latI] || '').trim() : '';
      const lon = lonI >= 0 ? (r[lonI] || '').trim() : '';
      const coords = lat || lon ? `${lat},${lon}` : '';
      map.set(`MAD-PK${pk}`, {
        id: `MAD-PK${pk}`,
        name: r[nameI] || `PK ${pk}`,
        phone: (r[phoneI] || '').trim(),
        address: addr,
        places: '',
        accessibility: (r[accI] || '').trim(),
        coords
      });
    }
  } else {
    const idI = idx('numero_registro');
    const nameI = idx('denominacion');
    const phoneI = idx('contacto_telefono');
    const viaTipoI = idx('direccion_via_tipo');
    const viaNameI = idx('direccion_via_nombre');
    const portalI = idx('direccion_portal');
    const plazasI = idx('plazas_autorizadas_numero');
    const coorXI = idx('direccion_coor_x');
    const coorYI = idx('direccion_coor_y');
    const prefix = sourceId === 'cam_centros' ? 'CAM-' : 'CAM-SRV-';

    for (let i = 1; i < rows.length; i++) {
      const r = rows[i];
      const regId = r[idI]?.trim();
      if (!regId) continue;
      const addr = [r[viaTipoI], r[viaNameI], r[portalI]].filter(Boolean).join(' ').trim();
      const cx = coorXI >= 0 ? (r[coorXI] || '').trim() : '';
      const cy = coorYI >= 0 ? (r[coorYI] || '').trim() : '';
      const coords = cx || cy ? `${cx},${cy}` : '';
      map.set(`${prefix}${regId}`, {
        id: `${prefix}${regId}`,
        name: r[nameI] || regId,
        phone: (r[phoneI] || '').trim(),
        address: addr,
        places: plazasI >= 0 ? (r[plazasI] || '').trim() : '',
        accessibility: '',
        coords
      });
    }
  }
  return map;
}

export function computeDiffs(
  sourceId: OfficialSourceSpec['source_id'],
  prevRows: string[][] | null,
  currRows: string[][],
  prevDate: string,
  currDate: string
): RealSnapshotDiff[] {
  if (!prevRows || prevRows.length < 2) return [];
  const prevMap = summarizeSourceRows(sourceId, prevRows);
  const currMap = summarizeSourceRows(sourceId, currRows);
  const diffs: RealSnapshotDiff[] = [];
  let seq = 1;

  const sourceTag = sourceId === 'madrid_municipal'
    ? 'datos.madrid.es'
    : sourceId === 'cam_centros'
    ? 'CAM Centros'
    : 'CAM Servicios';

  for (const [id, curr] of currMap.entries()) {
    const prev = prevMap.get(id);
    if (!prev) {
      diffs.push({
        change_id: `DIFF-${sourceId.toUpperCase()}-ADD-${seq++}`,
        change_type: 'centre_added',
        centre_id: id,
        centre_name: curr.name,
        previous_snapshot: prevDate,
        current_snapshot: currDate,
        detail: `Alta detectada en la descarga oficial (${sourceTag}): ${curr.address || 'dirección registrada'}.`,
        reason: `Comparativa automática SHA-256 sobre ${sourceTag}.`,
        category: 'alta'
      });
    } else {
      const changes: string[] = [];
      if (prev.name !== curr.name) changes.push(`Denominación: "${prev.name}" -> "${curr.name}"`);
      if (prev.phone !== curr.phone) changes.push(`Teléfono: "${prev.phone || 'N/D'}" -> "${curr.phone || 'N/D'}"`);
      if (prev.address !== curr.address) changes.push(`Dirección: "${prev.address}" -> "${curr.address}"`);
      if (prev.places !== curr.places) changes.push(`Plazas autorizadas: "${prev.places || 'N/D'}" -> "${curr.places || 'N/D'}"`);
      if (prev.accessibility !== curr.accessibility) changes.push(`Accesibilidad código: "${prev.accessibility || 'N/D'}" -> "${curr.accessibility || 'N/D'}"`);
      if (prev.coords !== curr.coords) changes.push(`Coordenadas: "${prev.coords || 'N/D'}" -> "${curr.coords || 'N/D'}"`);

      if (changes.length > 0) {
        const onlyAccessOrCoordsChanged =
          (prev.accessibility !== curr.accessibility || prev.coords !== curr.coords) &&
          prev.name === curr.name &&
          prev.phone === curr.phone &&
          prev.address === curr.address &&
          prev.places === curr.places;
        diffs.push({
          change_id: `DIFF-${sourceId.toUpperCase()}-UPD-${seq++}`,
          change_type:
            prev.name !== curr.name
              ? 'centre_renamed'
              : onlyAccessOrCoordsChanged
              ? 'access_route_changed'
              : 'service_added',
          centre_id: id,
          centre_name: curr.name,
          previous_snapshot: prevDate,
          current_snapshot: currDate,
          detail: `Cambio registral real (${sourceTag}): ${changes.join(' · ')}.`,
          reason: `Comparación directa fila a fila entre descargas oficiales de ${sourceTag}.`,
          category: onlyAccessOrCoordsChanged ? 'acceso' : 'servicio'
        });
      }
    }
  }

  for (const [id, prev] of prevMap.entries()) {
    if (!currMap.has(id)) {
      diffs.push({
        change_id: `DIFF-${sourceId.toUpperCase()}-DEL-${seq++}`,
        change_type: 'centre_removed',
        centre_id: id,
        centre_name: prev.name,
        previous_snapshot: prevDate,
        current_snapshot: currDate,
        detail: `El registro ${id} ya no figura en la descarga actual de ${sourceTag}.`,
        reason: `Comparativa automática SHA-256 sobre ${sourceTag}.`,
        category: 'baja'
      });
    }
  }

  return diffs;
}

function assertValidCsvPayload(spec: OfficialSourceSpec, buffer: Buffer): string[][] {
  if (buffer.length < 1024) {
    throw new Error(`[${spec.source_id}] Tamaño anómalo (${buffer.length} bytes).`);
  }

  const headSample = buffer.subarray(0, 512).toString('utf8').toLowerCase();
  if (
    headSample.includes('<!doctype html') ||
    headSample.includes('<html') ||
    headSample.includes('var _paq') ||
    headSample.includes('<head>')
  ) {
    throw new Error(`[${spec.source_id}] El portal devolvió una página HTML en lugar de un CSV válido.`);
  }

  const decoded = new TextDecoder(spec.encoding).decode(buffer);
  const rows = parseCSV(decoded);
  if (rows.length < spec.min_rows + 1) {
    throw new Error(`[${spec.source_id}] Solo se parsearon ${Math.max(0, rows.length - 1)} filas (mínimo requerido: ${spec.min_rows}).`);
  }

  const headerSet = new Set(rows[0].map(h => h.trim().toLowerCase()));
  for (const req of spec.required_headers) {
    if (!headerSet.has(req.toLowerCase())) {
      throw new Error(`[${spec.source_id}] Falta la columna obligatoria "${req}" en la cabecera CSV.`);
    }
  }

  return rows;
}

export function writeFileAtomicSync(targetPath: string, data: string | Buffer, encoding?: BufferEncoding): void {
  const dir = path.dirname(targetPath);
  const base = path.basename(targetPath);
  const tmpPath = path.join(dir, `.${base}.tmp.${process.pid}.${Date.now()}`);
  try {
    if (typeof data === 'string') {
      fs.writeFileSync(tmpPath, data, encoding || 'utf-8');
    } else {
      fs.writeFileSync(tmpPath, data);
    }
    fs.renameSync(tmpPath, targetPath);
  } catch (err) {
    try {
      if (fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath);
    } catch {
      // noop
    }
    throw err;
  }
}

export function verifyBaselineIntegrity(params: {
  sourceId: OfficialSourceSpec['source_id'];
  latestPath: string;
  expectedSha256?: string;
  gitFallbackLoader?: () => Buffer | null;
}): Buffer | null {
  const { sourceId, latestPath, expectedSha256, gitFallbackLoader } = params;
  if (!fs.existsSync(latestPath)) {
    return null;
  }
  const prevBuf = fs.readFileSync(latestPath);
  if (!expectedSha256) {
    return prevBuf;
  }
  const actualSha = crypto.createHash('sha256').update(prevBuf).digest('hex');
  if (actualSha === expectedSha256) {
    return prevBuf;
  }

  if (gitFallbackLoader) {
    const recovered = gitFallbackLoader();
    if (recovered) {
      const recoveredSha = crypto.createHash('sha256').update(recovered).digest('hex');
      if (recoveredSha === expectedSha256) {
        console.warn(`⚠️ [${sourceId}] Base mutable en disco incoherente; recuperada desde Git HEAD (${expectedSha256.slice(0, 12)}...).`);
        return recovered;
      }
    }
  }

  throw new Error(
    `[${sourceId}] Integridad de línea base comprometida: el fichero ${path.basename(latestPath)} en disco (${actualSha.slice(0, 12)}...) no coincide con snapshot-metadata.json (${expectedSha256.slice(0, 12)}...). Proceso detenido para no emitir un informe falso de 0 cambios.`
  );
}

export async function runIngestionProcess() {
  console.log('=== INICIANDO PROCESO DE INGESTA REGISTRAL MULTI-FUENTE ===');

  const snapshotsDir = path.resolve(process.cwd(), 'public/data/snapshots');
  if (!fs.existsSync(snapshotsDir)) {
    fs.mkdirSync(snapshotsDir, { recursive: true });
  }

  const timestamp = new Date().toISOString();
  const dateStr = timestamp.slice(0, 10);
  const metadataPath = path.join(snapshotsDir, 'snapshot-metadata.json');

  let prevTimestamp: string | null = null;
  let prevMetaSourcesMap: Record<string, string> = {};
  if (fs.existsSync(metadataPath)) {
    try {
      const prevMeta = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
      if (prevMeta?.timestamp) prevTimestamp = prevMeta.timestamp;
      if (Array.isArray(prevMeta?.sources)) {
        prevMetaSourcesMap = Object.fromEntries(
          prevMeta.sources.map((s: { source_id: string; sha256_hash: string }) => [s.source_id, s.sha256_hash])
        );
      }
    } catch {
      prevTimestamp = null;
    }
  }

  const downloaded: {
    spec: OfficialSourceSpec;
    buffer: Buffer;
    sha256: string;
    rows: string[][];
    prevRows: string[][] | null;
    prevHash: string | null;
  }[] = [];

  // Fase 1: Descargar y validar TODAS las fuentes + integridad estricta de la línea base
  for (const spec of OFFICIAL_SOURCES) {
    const latestPath = path.join(snapshotsDir, spec.latest_file);
    const expectedPrevSha = prevMetaSourcesMap[spec.source_id];
    const prevBuf = verifyBaselineIntegrity({
      sourceId: spec.source_id,
      latestPath,
      expectedSha256: expectedPrevSha
    });
    const prevRows = prevBuf ? parseCSV(new TextDecoder(spec.encoding).decode(prevBuf)) : null;
    const prevHash = prevBuf ? crypto.createHash('sha256').update(prevBuf).digest('hex') : null;

    console.log(`Descargando [${spec.source_id}]: ${spec.source_url}`);
    const response = await fetch(spec.source_url, {
      headers: {
        'User-Agent': 'MadridApoyoEspecializadoBot/1.8 (DataMad 2026 Audit; +https://datos.madrid.es)'
      }
    });

    if (!response.ok) {
      throw new Error(`[${spec.source_id}] Respuesta HTTP ${response.status} al descargar ${spec.source_url}. Ingesta abortada sin sobreescribir snapshots.`);
    }

    const buffer = Buffer.from(await response.arrayBuffer());
    const rows = assertValidCsvPayload(spec, buffer);
    const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');

    console.log(
      `✓ [${spec.source_id}] ${rows.length - 1} registros válidos (${buffer.length} bytes, SHA-256: ${sha256.slice(0, 12)}...)`
    );

    downloaded.push({ spec, buffer, sha256, rows, prevRows, prevHash });
  }

  // Fase 1.5: Verificación idempotente contra la última captura publicada (disco + snapshot-metadata.json).
  // Si todas las huellas coinciden, NO sobrescribir snapshot-diffs.json ni metadata salvo --force.
  const forceIngest = process.argv.includes('--force');
  const classifiedPath = path.join(snapshotsDir, 'catalog-classified.json');
  const allHashesMatchPublished = downloaded.every(item => {
    const metaHash = prevMetaSourcesMap[item.spec.source_id];
    return item.prevHash === item.sha256 && (!metaHash || metaHash === item.sha256);
  });

  if (!forceIngest && allHashesMatchPublished && fs.existsSync(classifiedPath) && fs.existsSync(metadataPath)) {
    console.log('✓ Registros oficiales sin cambios respecto a la huella publicada en snapshot-metadata.json. Informe snapshot-diffs.json preservado.');
    try {
      const existingMeta = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
      return existingMeta;
    } catch {}
  }

  // Fase 2: Preparar diffs y escrituras atómicas en disco (todo o nada mediante ficheros temporales)
  const allDiffs: RealSnapshotDiff[] = [];
  const prevDateLabel = prevTimestamp ? prevTimestamp.slice(0, 10) : dateStr;

  for (const item of downloaded) {
    const sourceDiffs = computeDiffs(item.spec.source_id, item.prevRows, item.rows, prevDateLabel, dateStr);
    allDiffs.push(...sourceDiffs);

    const latestPath = path.join(snapshotsDir, item.spec.latest_file);
    writeFileAtomicSync(latestPath, item.buffer);

    // Verificación estricta de que el SHA-256 del archivo en disco coincide byte a byte
    const diskHash = crypto.createHash('sha256').update(fs.readFileSync(latestPath)).digest('hex');
    if (diskHash !== item.sha256) {
      throw new Error(`Fallo de integridad SHA-256 en disco para ${item.spec.latest_file}: esperado ${item.sha256}, obtenido ${diskHash}`);
    }
  }

  // Fase 3: Solo actualizar snapshot-diffs.json si hubo cambios reales detectados o no existía el informe
  const diffsPath = path.join(snapshotsDir, 'snapshot-diffs.json');
  if (allDiffs.length > 0 || !fs.existsSync(diffsPath) || !allHashesMatchPublished) {
    let finalDiffs = allDiffs;
    let prevForReport = prevDateLabel;
    let currForReport = dateStr;
    if (allDiffs.length === 0 && fs.existsSync(diffsPath)) {
      try {
        const existingDiffs = JSON.parse(fs.readFileSync(diffsPath, 'utf-8'));
        if (Array.isArray(existingDiffs?.diffs) && existingDiffs.diffs.length > 0) {
          finalDiffs = existingDiffs.diffs;
          prevForReport = existingDiffs.previous_snapshot || prevDateLabel;
          currForReport = existingDiffs.current_snapshot || dateStr;
        }
      } catch {}
    }

    const diffsPayload = {
      generated_at: timestamp,
      previous_snapshot: prevForReport,
      current_snapshot: currForReport,
      total_changes: finalDiffs.length,
      diffs: finalDiffs
    };
    writeFileAtomicSync(diffsPath, JSON.stringify(diffsPayload, null, 2), 'utf-8');
  }

  // Fase 4: Guardar metadatos de auditoría multi-fuente atómicamente
  const primary = downloaded.find(d => d.spec.source_id === 'madrid_municipal')!;
  const sourcesMeta: SourceIngestionRecord[] = downloaded.map(d => ({
    source_id: d.spec.source_id,
    source_name: d.spec.source_name,
    source_url: d.spec.source_url,
    file: d.spec.latest_file,
    encoding: d.spec.encoding,
    sha256_hash: d.sha256,
    file_size_bytes: d.buffer.length,
    extracted_records_count: d.rows.length - 1,
    status: 'SUCCESS'
  }));

  const totalCombined = sourcesMeta.reduce((acc, s) => acc + s.extracted_records_count, 0);

  const metadata: IngestionMetadata = {
    ingestion_id: `ING_${Date.now()}`,
    timestamp,
    previous_timestamp: prevTimestamp,
    source_url: primary.spec.source_url,
    sha256_hash: primary.sha256,
    file_size_bytes: primary.buffer.length,
    extracted_records_count: primary.rows.length - 1,
    total_combined_records: totalCombined,
    status: 'SUCCESS',
    verification_notes: 'Descarga directa e íntegra (sin re-codificación) de 3 registros oficiales abiertos: Ayuntamiento de Madrid y Comunidad de Madrid (Centros y Servicios). Firma SHA-256 verificada byte a byte en disco.',
    sources: sourcesMeta
  };

  writeFileAtomicSync(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8');

  // Fase 5: Generar catálogo pre-clasificado JSON para carga instantánea y soporte offline PWA (#7)
  const classifiedPayload = generatePreclassifiedCatalogFile({
    snapshotsDir,
    timestamp,
    totalRecords: totalCombined
  });

  console.log('=== INGESTA REAL FINALIZADA CON ÉXITO ===');
  console.log(`Total registros oficiales verificados (3 CSVs): ${totalCombined}`);
  console.log(`Recursos clasificados en catalog-classified.json: ${classifiedPayload.active_centres_count}`);
  console.log(`Diferencias detectadas frente al snapshot anterior: ${allDiffs.length}`);
  return metadata;
}

export function generatePreclassifiedCatalogFile(params: {
  snapshotsDir: string;
  timestamp?: string;
  totalRecords?: number;
}) {
  const { snapshotsDir } = params;
  const metaPath = path.join(snapshotsDir, 'snapshot-metadata.json');
  let metaTimestamp = params.timestamp;
  let metaTotal = params.totalRecords;
  if ((!metaTimestamp || !metaTotal) && fs.existsSync(metaPath)) {
    try {
      const m = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
      metaTimestamp = metaTimestamp || m.timestamp;
      metaTotal = metaTotal || m.total_combined_records || m.extracted_records_count;
    } catch {
      // noop
    }
  }

  const timestamp = metaTimestamp || new Date().toISOString();
  const dateStr = timestamp.slice(0, 10);

  const madridPath = path.join(snapshotsDir, 'snapshot-latest.csv');
  const camCentrosPath = path.join(snapshotsDir, 'cam-centros-latest.csv');
  const camServiciosPath = path.join(snapshotsDir, 'cam-servicios-latest.csv');

  const madridCsvText = fs.existsSync(madridPath)
    ? new TextDecoder('latin1').decode(fs.readFileSync(madridPath))
    : null;
  const camCentrosCsvText = fs.existsSync(camCentrosPath)
    ? new TextDecoder('utf-8').decode(fs.readFileSync(camCentrosPath))
    : null;
  const camServiciosCsvText = fs.existsSync(camServiciosPath)
    ? new TextDecoder('utf-8').decode(fs.readFileSync(camServiciosPath))
    : null;

  const built = buildCentresFromOfficialCSVs({
    madridCsvText,
    camCentrosCsvText,
    camServiciosCsvText,
    snapshotDate: dateStr
  });

  const neededLookupKeys = new Set<string>();
  for (const c of built.centres) {
    neededLookupKeys.add(c.centre_id);
    for (const prov of c.provenance_records) {
      const pkMatch = prov.source_dataset.match(/PK\s+(\d+)/);
      if (pkMatch) neededLookupKeys.add(`MAD-PK${pkMatch[1]}`);
      const camMatch = prov.source_dataset.match(/\(([CS]\d+)\)/);
      if (camMatch) {
        const key = camMatch[1].startsWith('S') ? `CAM-SRV-${camMatch[1]}` : `CAM-${camMatch[1]}`;
        neededLookupKeys.add(key);
      }
    }
  }

  const slimLookupRecords = Array.from(built.lookupIndex.entries()).filter(([key]) =>
    neededLookupKeys.has(key)
  );

  const payload = {
    version: '1.8',
    generated_at: timestamp,
    snapshot_date: dateStr,
    total_records: metaTotal || built.lookupIndex.size,
    active_centres_count: built.centres.length,
    lookup_records: slimLookupRecords,
    centres: built.centres
  };

  writeFileAtomicSync(
    path.join(snapshotsDir, 'catalog-classified.json'),
    JSON.stringify(payload),
    'utf-8'
  );
  return payload;
}

const isDirectExecution = process.argv[1] && path.resolve(process.argv[1]).endsWith('ingest.ts');
if (isDirectExecution) {
  if (process.argv.includes('--only-classify')) {
    const snapshotsDir = path.resolve(process.cwd(), 'public/data/snapshots');
    const payload = generatePreclassifiedCatalogFile({ snapshotsDir });
    console.log(`✓ catalog-classified.json regenerado sin descarga: ${payload.active_centres_count} recursos.`);
  } else {
    runIngestionProcess().catch(err => {
      console.error('ERROR CRÍTICO DE INGESTA (proceso detenido sin corromper datos):', err?.message || err);
      process.exit(1);
    });
  }
}
