/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Live Snapshot & Preclassified Offline Catalog Loader
 * Prioriza el catálogo pre-clasificado cacheado offline (catalog-classified.json, ~1.079 recursos)
 * usando import.meta.env.BASE_URL (compatible con GitHub Pages subpath), con fallback directo
 * a los 3 CSV oficiales en vivo y carga perezosa del catálogo de reserva en caso de fallo (#6, #7).
 */

import { SpecializedCentre, SnapshotDifference } from '../types/specialized';
import {
  buildCentresFromOfficialCSVs,
  parseSemicolonCSV,
  SnapshotCentreRecord
} from './officialRegistryParser';
import {
  setSnapshotVerificationContext,
  SnapshotMetadataSummary,
  SnapshotSourceMeta
} from './specializedEngine';

export interface DynamicIngestionState {
  loaded: boolean;
  load_source?: 'preclassified_json' | 'csv_runtime' | 'reserve_fallback';
  used_fallback?: boolean;
  timestamp: string;
  previous_timestamp: string | null;
  sha256_hash: string;
  total_csv_records: number;
  active_centres_count: number;
  updated_centres_count: number;
  sources: SnapshotSourceMeta[];
  diffs: SnapshotDifference[];
  error: string | null;
}

export const parseCSVClient = parseSemicolonCSV;

export function resolvePublicAssetUrl(relativePath: string): string {
  const rawBase =
    (typeof import.meta !== 'undefined' &&
      (import.meta as unknown as { env?: { BASE_URL?: string } }).env?.BASE_URL) ||
    '/';
  const baseWithSlash = rawBase.endsWith('/') ? rawBase : `${rawBase}/`;
  const cleanRel = relativePath.startsWith('/') ? relativePath.slice(1) : relativePath;
  return `${baseWithSlash}${cleanRel}`;
}

export async function loadLiveSnapshotData(
  baseCentresProvider?: SpecializedCentre[] | (() => Promise<SpecializedCentre[]>)
): Promise<{
  centres: SpecializedCentre[];
  state: DynamicIngestionState;
  metadata: SnapshotMetadataSummary | null;
  lookupIndex: Map<string, SnapshotCentreRecord>;
}> {
  const resolveFallbackCentres = async (): Promise<SpecializedCentre[]> => {
    if (typeof baseCentresProvider === 'function') {
      return baseCentresProvider();
    }
    if (Array.isArray(baseCentresProvider)) {
      return baseCentresProvider;
    }
    const mod = await import('../data/specializedCentresData');
    return mod.SPECIALIZED_CENTRES;
  };

  const state: DynamicIngestionState = {
    loaded: false,
    load_source: undefined,
    used_fallback: false,
    timestamp: new Date().toISOString(),
    previous_timestamp: null,
    sha256_hash: '',
    total_csv_records: 0,
    active_centres_count: Array.isArray(baseCentresProvider) ? baseCentresProvider.length : 0,
    updated_centres_count: 0,
    sources: [],
    diffs: [],
    error: null
  };

  let metaJson: SnapshotMetadataSummary | null = null;

  try {
    // 1. Obtener metadatos multi-fuente, diferencias reales y catálogo pre-clasificado JSON (#6, #7)
    const [metaRes, diffsRes, catalogRes] = await Promise.all([
      fetch(resolvePublicAssetUrl('data/snapshots/snapshot-metadata.json')).catch(() => null),
      fetch(resolvePublicAssetUrl('data/snapshots/snapshot-diffs.json')).catch(() => null),
      fetch(resolvePublicAssetUrl('data/snapshots/catalog-classified.json')).catch(() => null)
    ]);

    if (metaRes && metaRes.ok) {
      const rawMeta = await metaRes.json();
      metaJson = rawMeta;
      state.timestamp = rawMeta.timestamp || state.timestamp;
      state.previous_timestamp = rawMeta.previous_timestamp || null;
      state.sha256_hash = rawMeta.sha256_hash || '';
      state.total_csv_records = rawMeta.total_combined_records || rawMeta.extracted_records_count || 0;
      state.sources = Array.isArray(rawMeta.sources) ? rawMeta.sources : [];
    }

    if (diffsRes && diffsRes.ok) {
      const diffsJson = await diffsRes.json();
      if (Array.isArray(diffsJson?.diffs)) {
        state.diffs = diffsJson.diffs;
        state.updated_centres_count = diffsJson.diffs.length;
      }
    }

    // Ruta rápida y cacheable offline (Workbox PWA): JSON pre-clasificado con los ~1.079 recursos
    if (catalogRes && catalogRes.ok) {
      try {
        const catalogJson = await catalogRes.json();
        if (Array.isArray(catalogJson?.centres) && catalogJson.centres.length > 0) {
          const lookupIndex = new Map<string, SnapshotCentreRecord>(
            Array.isArray(catalogJson.lookup_records) ? catalogJson.lookup_records : []
          );
          setSnapshotVerificationContext(metaJson, lookupIndex);

          state.loaded = true;
          state.load_source = 'preclassified_json';
          state.used_fallback = false;
          state.active_centres_count = catalogJson.centres.length;
          if (state.total_csv_records === 0) {
            state.total_csv_records = catalogJson.total_records || lookupIndex.size;
          }

          return {
            centres: catalogJson.centres as SpecializedCentre[],
            state,
            metadata: metaJson,
            lookupIndex
          };
        }
      } catch {
        // Si fallase la lectura del JSON pre-clasificado, continúa con los CSV en vivo
      }
    }

    // 2. Ruta alternativa en vivo: descargar los 3 ficheros CSV oficiales en sus codificaciones exactas
    const [madRes, camCentrosRes, camServiciosRes] = await Promise.all([
      fetch(resolvePublicAssetUrl('data/snapshots/snapshot-latest.csv')),
      fetch(resolvePublicAssetUrl('data/snapshots/cam-centros-latest.csv')),
      fetch(resolvePublicAssetUrl('data/snapshots/cam-servicios-latest.csv'))
    ]);

    let madridCsvText: string | null = null;
    if (madRes.ok) {
      const buf = await madRes.arrayBuffer();
      madridCsvText = new TextDecoder('latin1').decode(buf);
    }

    let camCentrosCsvText: string | null = null;
    if (camCentrosRes.ok) {
      const buf = await camCentrosRes.arrayBuffer();
      camCentrosCsvText = new TextDecoder('utf-8').decode(buf);
    }

    let camServiciosCsvText: string | null = null;
    if (camServiciosRes.ok) {
      const buf = await camServiciosRes.arrayBuffer();
      camServiciosCsvText = new TextDecoder('utf-8').decode(buf);
    }

    if (!madridCsvText && !camCentrosCsvText && !camServiciosCsvText) {
      throw new Error('No se pudo cargar ninguno de los ficheros oficiales desde data/snapshots/.');
    }

    const { centres, lookupIndex } = buildCentresFromOfficialCSVs({
      madridCsvText,
      camCentrosCsvText,
      camServiciosCsvText,
      snapshotDate: state.timestamp.slice(0, 10)
    });

    if (centres.length === 0) {
      throw new Error('Los ficheros CSV cargados no devolvieron registros válidos.');
    }

    setSnapshotVerificationContext(metaJson, lookupIndex);

    state.loaded = true;
    state.load_source = 'csv_runtime';
    state.used_fallback = false;
    state.active_centres_count = centres.length;
    if (state.total_csv_records === 0) {
      state.total_csv_records = lookupIndex.size;
    }

    return { centres, state, metadata: metaJson, lookupIndex };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Fallo de lectura de los archivos de captura oficial';
    console.warn('Error al cargar dinámicamente los snapshots oficiales:', err);
    const fallbackCentres = await resolveFallbackCentres();
    state.loaded = false;
    state.load_source = 'reserve_fallback';
    state.used_fallback = true;
    state.error = message;
    state.active_centres_count = fallbackCentres.length;
    return { centres: fallbackCentres, state, metadata: metaJson, lookupIndex: new Map() };
  }
}
