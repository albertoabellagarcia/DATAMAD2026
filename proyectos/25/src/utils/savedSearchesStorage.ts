/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Validación estricta de búsquedas guardadas en localStorage
 * Protege frente a JSON corrupto o alterado manualmente y bloquea la persistencia de GPS exacto (RGPD).
 */

import {
  SavedSearch,
  SupportTypeId,
  FunctionalNeedId,
  LifeStage,
  NetworkPreference,
  CombinationMode
} from '../types/specialized';

export const SAVED_SEARCHES_STORAGE_KEY = 'madrid_apoyo_saved_searches_v18';
export const LEGACY_SAVED_SEARCHES_STORAGE_KEY = 'madrid_apoyo_saved_searches_v17';

const VALID_NETWORKS = new Set<NetworkPreference>(['all', 'public_network', 'private_authorised']);
const VALID_COMBINATION_MODES = new Set<CombinationMode>(['any_support', 'all_supports_same_centre']);
const VALID_LIFE_STAGES = new Set<LifeStage>(['early_childhood', 'minor', 'adult', 'older_adult']);

function isNonEmptyString(val: unknown): val is string {
  return typeof val === 'string' && val.trim().length > 0;
}

function isStringArray(val: unknown): val is string[] {
  return Array.isArray(val) && val.every((item) => typeof item === 'string');
}

export function validateSavedSearchRecord(raw: unknown): SavedSearch | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const obj = raw as Record<string, unknown>;

  if (!isNonEmptyString(obj.saved_search_id) || !isNonEmptyString(obj.name)) {
    return null;
  }

  const filtersRaw = obj.filters;
  if (!filtersRaw || typeof filtersRaw !== 'object' || Array.isArray(filtersRaw)) {
    return null;
  }
  const f = filtersRaw as Record<string, unknown>;

  const profile =
    f.profile === null || f.profile === undefined
      ? null
      : typeof f.profile === 'string'
      ? f.profile
      : null;
  if (f.profile !== null && f.profile !== undefined && typeof f.profile !== 'string') {
    return null;
  }

  if (!isStringArray(f.support_types) || !isStringArray(f.functional_needs)) {
    return null;
  }

  const accessibilityNeeds =
    f.accessibility_needs === undefined
      ? []
      : isStringArray(f.accessibility_needs)
      ? f.accessibility_needs
      : null;
  if (accessibilityNeeds === null) return null;

  const lifeStage =
    f.life_stage === null || f.life_stage === undefined
      ? null
      : typeof f.life_stage === 'string' && VALID_LIFE_STAGES.has(f.life_stage as LifeStage)
      ? (f.life_stage as LifeStage)
      : 'INVALID';
  if (lifeStage === 'INVALID') return null;

  const municipality =
    f.municipality === null || f.municipality === undefined
      ? null
      : typeof f.municipality === 'string'
      ? f.municipality
      : 'INVALID';
  if (municipality === 'INVALID') return null;

  const radiusKm = typeof f.radius_km === 'number' && Number.isFinite(f.radius_km) && f.radius_km > 0 && f.radius_km <= 200
    ? f.radius_km
    : 80;

  const networkPref =
    typeof f.network_preference === 'string' && VALID_NETWORKS.has(f.network_preference as NetworkPreference)
      ? (f.network_preference as NetworkPreference)
      : 'all';

  const combMode =
    typeof f.support_combination_mode === 'string' && VALID_COMBINATION_MODES.has(f.support_combination_mode as CombinationMode)
      ? (f.support_combination_mode as CombinationMode)
      : 'any_support';

  return {
    saved_search_id: obj.saved_search_id.trim(),
    name: obj.name.trim(),
    created_at: isNonEmptyString(obj.created_at) ? obj.created_at : new Date().toISOString(),
    updated_at: isNonEmptyString(obj.updated_at) ? obj.updated_at : new Date().toISOString(),
    filters: {
      profile,
      functional_needs: f.functional_needs as FunctionalNeedId[],
      support_types: f.support_types as SupportTypeId[],
      support_combination_mode: combMode,
      life_stage: lifeStage,
      municipality,
      radius_km: radiusKm,
      network_preference: networkPref,
      accessibility_needs: accessibilityNeeds
    },
    taxonomy_version: isNonEmptyString(obj.taxonomy_version) ? obj.taxonomy_version : '1.9.0',
    dataset_snapshot: isNonEmptyString(obj.dataset_snapshot) ? obj.dataset_snapshot : ''
  };
}

export function parseValidatedSavedSearchesJson(rawJson: string | null): SavedSearch[] {
  if (!rawJson) return [];
  try {
    const parsed: unknown = JSON.parse(rawJson);
    if (!Array.isArray(parsed)) return [];
    const validated: SavedSearch[] = [];
    for (const item of parsed) {
      const clean = validateSavedSearchRecord(item);
      if (clean) validated.push(clean);
    }
    return validated;
  } catch {
    return [];
  }
}

export function loadValidatedSavedSearches(): SavedSearch[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw =
      window.localStorage.getItem(SAVED_SEARCHES_STORAGE_KEY) ||
      window.localStorage.getItem(LEGACY_SAVED_SEARCHES_STORAGE_KEY);
    return parseValidatedSavedSearchesJson(raw);
  } catch {
    return [];
  }
}

export function persistSavedSearches(list: SavedSearch[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(SAVED_SEARCHES_STORAGE_KEY, JSON.stringify(list));
  } catch {
    // Ignorar error de cuota/almacenamiento bloqueado sin romper UI
  }
}
