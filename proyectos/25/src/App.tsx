/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Aplicación Principal
 * Buscador transversal de centros y servicios de atención social autorizados de la Comunidad de Madrid
 * DATAMAD 2026 · Código abierto · Orientación, no diagnóstico
 * Cumple estrictamente con el Prompt Maestro v1.8 y la Universal Frontend Design Constitution
 */

import React, { useState, useMemo, useEffect, useRef, useDeferredValue, Suspense, lazy } from 'react';
import { 
  SpecializedCentre,
  SearchQueryState, 
  EvaluatedCentreResult 
} from './types/specialized';
import { runSpecializedSearch, evaluateCentre } from './utils/specializedEngine';
import { loadLiveSnapshotData, DynamicIngestionState } from './utils/liveSnapshotParser';
import { loadValidatedSavedSearches } from './utils/savedSearchesStorage';
import { resolveSearchOrigin, OriginReference } from './data/municipalitiesData';
import { SpecializedHeader } from './components/specialized/SpecializedHeader';
import { SpecializedSearchFilters } from './components/specialized/SpecializedSearchFilters';
import { SpecializedResultsList } from './components/specialized/SpecializedResultsList';
import { WhyAppearsModal } from './components/specialized/WhyAppearsModal';
import { PrintableContactCardModal } from './components/specialized/PrintableContactCardModal';
import { SavedSearchesModal } from './components/specialized/SavedSearchesModal';
import { EasyReadGlossaryModal } from './components/specialized/EasyReadGlossaryModal';
import { LifeStageTransitionBanner } from './components/specialized/LifeStageTransitionBanner';
import { PWAUpdatePrompt } from './components/pwa/PWAUpdatePrompt';

const SpecializedMapView = lazy(() =>
  import('./components/specialized/SpecializedMapView').then(m => ({ default: m.SpecializedMapView }))
);
const SpecializedComparatorView = lazy(() =>
  import('./components/specialized/SpecializedComparatorView').then(m => ({ default: m.SpecializedComparatorView }))
);
const TaxonomyGovernanceView = lazy(() =>
  import('./components/specialized/TaxonomyGovernanceView').then(m => ({ default: m.TaxonomyGovernanceView }))
);
const SpecializedTestsRunnerView = lazy(() =>
  import('./components/specialized/SpecializedTestsRunnerView').then(m => ({ default: m.SpecializedTestsRunnerView }))
);
const WhatChangedModal = lazy(() =>
  import('./components/specialized/WhatChangedModal').then(m => ({ default: m.WhatChangedModal }))
);

import { AlertTriangle, RotateCcw } from 'lucide-react';
import { CORE_PROFILES, EXPERIMENTAL_PROFILES, PENDING_PROFILES, LIFE_STAGES, SUPPORT_TYPES, FUNCTIONAL_NEEDS } from './data/specializedTaxonomy';
import { findMunicipalityByName } from './data/municipalitiesData';
import { ProfileId, SupportTypeId, FunctionalNeedId, LifeStage, NetworkPreference, CombinationMode } from './types/specialized';

const DEFAULT_QUERY: SearchQueryState = {
  profile: null,
  functional_needs: [],
  support_types: [],
  support_combination_mode: 'any_support',
  life_stage: null,
  municipality: null,
  radius_km: 80,
  network_preference: 'all',
  accessibility_needs: [],
  user_ephemeral_location: null,
  location_mode: 'all'
};

/**
 * Validación exhaustiva de parámetros de URL contra taxonomía y municipios oficiales (§62.2)
 */
function validateAndParseUrlParams(): { query: SearchQueryState; errors: string[]; isBlocked: boolean } {
  if (typeof window === 'undefined' || !window.location.search) {
    return { query: DEFAULT_QUERY, errors: [], isBlocked: false };
  }

  const params = new URLSearchParams(window.location.search);
  const errors: string[] = [];

  const rawProfile = params.get('profile');
  const rawMuni = params.get('municipality');
  const rawRadius = params.get('radius');
  const rawSupports = params.get('supports');
  const rawNeeds = params.get('needs');
  const rawStage = params.get('stage');
  const rawNet = params.get('net');
  const rawComb = params.get('comb');
  const rawAccess = params.get('access');
  const rawLoc = params.get('loc');

  const validProfileKeys = [
    ...Object.keys(CORE_PROFILES),
    ...Object.keys(EXPERIMENTAL_PROFILES),
    ...Object.keys(PENDING_PROFILES)
  ];
  const validStages = Object.keys(LIFE_STAGES);
  const validSupports = Object.keys(SUPPORT_TYPES);
  const validNeeds = Object.keys(FUNCTIONAL_NEEDS);
  const validNets = ['all', 'public_network', 'private_authorised'];
  const validCombs = ['any_support', 'all_supports_same_centre'];
  const validLocs = ['all', 'municipality', 'browser'];
  const validAccess = ['wheelchair_access', 'sign_language', 'tactile_signage', 'magnetic_loops'];

  let profile: ProfileId | null = null;
  if (rawProfile !== null && rawProfile !== '') {
    if (validProfileKeys.includes(rawProfile)) {
      profile = rawProfile as ProfileId;
    } else {
      errors.push(`Perfil o condición no reconocida en la taxonomía oficial: "${rawProfile}"`);
    }
  }

  let municipality: string | null = null;
  if (rawMuni !== null && rawMuni !== '') {
    const matchedMuni = findMunicipalityByName(rawMuni);
    if (matchedMuni) {
      municipality = matchedMuni.name;
    } else {
      errors.push(`Municipio no perteneciente a la Comunidad de Madrid: "${rawMuni}"`);
    }
  }

  let stage: LifeStage | null = null;
  if (rawStage !== null && rawStage !== '') {
    if (validStages.includes(rawStage)) {
      stage = rawStage as LifeStage;
    } else {
      errors.push(`Etapa vital desconocida: "${rawStage}"`);
    }
  }

  const support_types: SupportTypeId[] = [];
  if (rawSupports) {
    const items = rawSupports.split(',').map(s => s.trim()).filter(Boolean);
    for (const item of items) {
      if (validSupports.includes(item)) {
        support_types.push(item as SupportTypeId);
      } else {
        errors.push(`Tipo de apoyo no reconocido: "${item}"`);
      }
    }
  }

  const functional_needs: FunctionalNeedId[] = [];
  if (rawNeeds) {
    const items = rawNeeds.split(',').map(n => n.trim()).filter(Boolean);
    for (const item of items) {
      if (validNeeds.includes(item)) {
        functional_needs.push(item as FunctionalNeedId);
      } else {
        errors.push(`Necesidad funcional no reconocida: "${item}"`);
      }
    }
  }

  let radius_km = DEFAULT_QUERY.radius_km;
  if (rawRadius !== null && rawRadius !== '') {
    const parsed = parseInt(rawRadius, 10);
    if (!isNaN(parsed) && parsed > 0 && parsed <= 200) {
      radius_km = parsed;
    } else {
      errors.push(`Radio de búsqueda no válido (debe ser entre 1 y 200 km): "${rawRadius}"`);
    }
  }

  let network_preference: NetworkPreference = 'all';
  if (rawNet !== null && rawNet !== '') {
    if (validNets.includes(rawNet)) {
      network_preference = rawNet as NetworkPreference;
    } else {
      errors.push(`Preferencia de red no válida: "${rawNet}"`);
    }
  }

  let support_combination_mode: CombinationMode = 'any_support';
  if (rawComb !== null && rawComb !== '') {
    if (validCombs.includes(rawComb)) {
      support_combination_mode = rawComb as CombinationMode;
    } else {
      errors.push(`Modo de combinación no válido: "${rawComb}"`);
    }
  }

  let location_mode: SearchQueryState['location_mode'] = municipality ? 'municipality' : 'all';
  if (rawLoc !== null && rawLoc !== '') {
    if (validLocs.includes(rawLoc)) {
      location_mode = rawLoc as SearchQueryState['location_mode'];
    } else {
      errors.push(`Modo de ubicación no válido: "${rawLoc}"`);
    }
  }

  const accessibility_needs: string[] = [];
  if (rawAccess) {
    const items = rawAccess.split(',').map(a => a.trim()).filter(Boolean);
    for (const item of items) {
      if (validAccess.includes(item)) {
        accessibility_needs.push(item);
      } else {
        errors.push(`Requisito de accesibilidad no reconocido: "${item}"`);
      }
    }
  }

  return {
    query: {
      ...DEFAULT_QUERY,
      profile,
      municipality,
      radius_km,
      support_types,
      functional_needs,
      life_stage: stage,
      network_preference,
      support_combination_mode,
      accessibility_needs,
      location_mode
    },
    errors,
    isBlocked: errors.length > 0
  };
}

export default function App() {
  const initialTab = useMemo(() => {
    if (typeof window === 'undefined' || !window.location.search) return 'search';
    const p = new URLSearchParams(window.location.search);
    const t = p.get('tab');
    const validTabs = ['search', 'map', 'comparator', 'what_changed', 'governance', 'tests'];
    return validTabs.includes(t || '') ? t! : 'search';
  }, []);

  // Pestañas de Madrid Apoyo Especializado: 'search' | 'map' | 'comparator' | 'what_changed' | 'governance' | 'tests'
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const isFirstTabRender = useRef(true);
  useEffect(() => {
    if (isFirstTabRender.current) {
      isFirstTabRender.current = false;
      return;
    }
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'auto' });
    }
  }, [activeTab]);

  // Estado accesible
  const [easyReadMode, setEasyReadMode] = useState<boolean>(false);

  // Inicialización y validación estricta de parámetros URL (§62.2)
  const initialUrlState = useMemo(() => validateAndParseUrlParams(), []);
  const [query, setQuery] = useState<SearchQueryState>(initialUrlState.query);
  const [urlValidationErrors, setUrlValidationErrors] = useState<string[]>(initialUrlState.errors);
  const [isUrlBlocked, setIsUrlBlocked] = useState<boolean>(initialUrlState.isBlocked);

  const handleSetQuery: React.Dispatch<React.SetStateAction<SearchQueryState>> = (value) => {
    if (isUrlBlocked) {
      setIsUrlBlocked(false);
      setUrlValidationErrors([]);
    }
    setQuery(value);
  };

  const handleClearUrlErrorsAndReset = () => {
    setIsUrlBlocked(false);
    setUrlValidationErrors([]);
    setQuery(DEFAULT_QUERY);
    setActiveTab('search');
    setDismissedTransition(false);
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, '', window.location.pathname);
    }
  };

  // Sincronización transparente de todas las dimensiones en la URL sin almacenar salud ni datos personales (§62.2, LOC-006)
  useEffect(() => {
    if (isUrlBlocked) return;
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams();
      if (activeTab !== 'search') params.set('tab', activeTab);
      if (query.profile) params.set('profile', query.profile);
      if (query.municipality) params.set('municipality', query.municipality);
      if (query.radius_km !== DEFAULT_QUERY.radius_km) params.set('radius', query.radius_km.toString());
      if (query.support_types.length > 0) params.set('supports', query.support_types.join(','));
      if (query.functional_needs.length > 0) params.set('needs', query.functional_needs.join(','));
      if (query.life_stage) params.set('stage', query.life_stage);
      if (query.network_preference !== 'all') params.set('net', query.network_preference);
      if (query.support_combination_mode !== 'any_support') params.set('comb', query.support_combination_mode);
      if (query.accessibility_needs.length > 0) params.set('access', query.accessibility_needs.join(','));
      if (query.location_mode !== 'all') params.set('loc', query.location_mode);
      
      const newQs = params.toString();
      const newUrl = newQs ? `${window.location.pathname}?${newQs}` : window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    }
  }, [
    isUrlBlocked,
    activeTab,
    query.profile, 
    query.municipality, 
    query.radius_km, 
    query.support_types,
    query.functional_needs,
    query.life_stage,
    query.network_preference,
    query.support_combination_mode,
    query.accessibility_needs,
    query.location_mode
  ]);

  // Carga del catálogo pre-clasificado (cacheado offline PWA) o CSVs en vivo (#6, #7, #12)
  const [activeCentres, setActiveCentres] = useState<SpecializedCentre[]>([]);
  const [isCatalogLoading, setIsCatalogLoading] = useState<boolean>(true);
  const [isRetryingCatalog, setIsRetryingCatalog] = useState<boolean>(false);
  const [catalogFatalError, setCatalogFatalError] = useState<string | null>(null);
  const [dynamicState, setDynamicState] = useState<DynamicIngestionState | null>(null);

  const fetchCatalog = (isRetry = false) => {
    if (isRetry) setIsRetryingCatalog(true);
    setCatalogFatalError(null);
    let cancelled = false;
    loadLiveSnapshotData()
      .then(({ centres: liveCentres, state }) => {
        if (cancelled) return;
        setActiveCentres(liveCentres);
        setDynamicState(state);
        setCatalogFatalError(null);
        setIsCatalogLoading(false);
        setIsRetryingCatalog(false);
      })
      .catch((err) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Error desconocido al cargar los ficheros del catálogo.';
          setCatalogFatalError(message);
          setIsCatalogLoading(false);
          setIsRetryingCatalog(false);
        }
      });
    return () => {
      cancelled = true;
    };
  };

  useEffect(() => {
    return fetchCatalog(false);
  }, []);

  // Seleccion de centros para comparar (hasta 3 centros §15)
  const [comparedCentreIds, setComparedCentreIds] = useState<string[]>([]);
  const [compareLimitNotice, setCompareLimitNotice] = useState<string | null>(null);
  const [selectedMapCentreId, setSelectedMapCentreId] = useState<string | null>(null);

  // Modales
  const [whyAppearsItem, setWhyAppearsItem] = useState<EvaluatedCentreResult | null>(null);
  const [printableContactItem, setPrintableContactItem] = useState<EvaluatedCentreResult | null>(null);
  const [isSavedSearchesOpen, setIsSavedSearchesOpen] = useState(false);
  const [isWhatChangedOpen, setIsWhatChangedOpen] = useState(false);
  const [isGlossaryOpen, setIsGlossaryOpen] = useState(false);
  const [dismissedTransition, setDismissedTransition] = useState(false);

  // Contador de búsquedas guardadas (validación estricta de esquema en localStorage)
  const [savedCount, setSavedCount] = useState(0);
  useEffect(() => {
    setSavedCount(loadValidatedSavedSearches().length);
  }, [isSavedSearchesOpen]);

  const deferredQuery = useDeferredValue(query);

  // Origen de coordenadas para cálculo de distancia garantizado (§67)
  const resolvedOrigin = useMemo<OriginReference>(() => {
    return resolveSearchOrigin(
      deferredQuery.user_ephemeral_location,
      deferredQuery.municipality,
      deferredQuery.location_mode
    );
  }, [deferredQuery.user_ephemeral_location, deferredQuery.municipality, deferredQuery.location_mode]);

  // Ejecución del motor de búsqueda verificable (§27, §41, §78)
  const searchOutput = useMemo(() => {
    if (isUrlBlocked) {
      return { results: [], incompatible_results: [], total_results: 0 };
    }
    return runSpecializedSearch(deferredQuery, activeCentres, resolvedOrigin.coordinates);
  }, [isUrlBlocked, deferredQuery, activeCentres, resolvedOrigin]);

  const matchedProfileCount = useMemo(() => {
    if (!deferredQuery.profile) return searchOutput.total_results;
    const abCount = searchOutput.results.filter(r => r.evidence_level !== 'C').length;
    return abCount > 0 ? abCount : searchOutput.total_results;
  }, [deferredQuery.profile, searchOutput]);

  // Centros en el comparador (mantiene los seleccionados independientemente de filtros de radio o estado)
  const comparedCentres = useMemo(() => {
    const allEvaluated = [...searchOutput.results, ...searchOutput.incompatible_results];
    const matched = allEvaluated.filter(r => comparedCentreIds.includes(r.centre.centre_id));
    if (matched.length === comparedCentreIds.length) return matched;

    const missingIds = comparedCentreIds.filter(id => !matched.some(m => m.centre.centre_id === id));
    const missingEvaluated = missingIds.map(id => {
      const raw = activeCentres.find(c => c.centre_id === id);
      return raw ? evaluateCentre(raw, deferredQuery, activeCentres, resolvedOrigin.coordinates) : null;
    }).filter(Boolean) as EvaluatedCentreResult[];

    return [...matched, ...missingEvaluated];
  }, [searchOutput.results, searchOutput.incompatible_results, comparedCentreIds, deferredQuery, activeCentres, resolvedOrigin]);

  const toggleCompare = (id: string) => {
    setComparedCentreIds(prev => {
      if (prev.includes(id)) {
        setCompareLimitNotice(null);
        return prev.filter(cId => cId !== id);
      }
      if (prev.length >= 3) {
        setCompareLimitNotice('Puede comparar un máximo de 3 centros a la vez. Quite uno del comparador antes de añadir otro.');
        return prev;
      }
      setCompareLimitNotice(null);
      return [...prev, id];
    });
  };

  const resetAllFilters = () => {
    setIsUrlBlocked(false);
    setUrlValidationErrors([]);
    setQuery(DEFAULT_QUERY);
    setDismissedTransition(false);
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, '', window.location.pathname);
    }
  };

  return (
    <div className="min-h-screen flex flex-col font-sans bg-[#FBF9F5] text-stone-900 antialiased">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-stone-900 focus:text-white focus:rounded-lg focus:text-xs focus:font-semibold focus:shadow-lg no-print"
      >
        Saltar al contenido principal
      </a>

      {/* 1. Header con contrato de barra superior de 3 zonas (§2 de frontend-design) */}
      <SpecializedHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        easyReadMode={easyReadMode}
        setEasyReadMode={setEasyReadMode}
        savedSearchesCount={savedCount}
        comparedCount={comparedCentreIds.length}
        openSavedSearches={() => setIsSavedSearchesOpen(true)}
        openGlossary={() => setIsGlossaryOpen(true)}
        onOpenWhatChanged={() => setActiveTab('what_changed')}
        snapshotDate={dynamicState?.timestamp?.slice(0, 10)}
      />

      {/* Alerta de validación de URL cuando hay parámetros rechazados */}
      {urlValidationErrors.length > 0 && (
        <div role="alert" className="bg-amber-50 border-b border-amber-300 text-amber-950 py-3 px-4 text-xs shadow-xs no-print">
          <div className="max-w-7xl mx-auto w-full flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <span className="font-bold text-stone-900 block sm:inline">
                  Validación estricta de URL:
                </span>{' '}
                <span>
                  Se han rechazado {urlValidationErrors.length} parámetro(s) por no pertenecer al catálogo oficial. Se ha pausado la búsqueda para evitar mostrar resultados engañosos.
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleClearUrlErrorsAndReset}
              className="px-3 py-1.5 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors flex items-center gap-1 shrink-0 self-end sm:self-center cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Ver catálogo general completo</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Contenedor principal de vistas */}
      <main
        id="main-content"
        tabIndex={-1}
        className={`flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 outline-none ${printableContactItem ? 'no-print' : ''}`}
      >
        {/* PESTAÑA: BÚSQUEDA Y RESULTADOS */}
        {activeTab === 'search' && (
          <div>
            {compareLimitNotice && (
              <div role="status" aria-live="polite" className="mb-4 p-3 rounded-xl border border-amber-300 bg-amber-50 text-amber-950 text-xs flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" aria-hidden="true" />
                  <span>{compareLimitNotice}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setActiveTab('comparator')}
                    className="px-2.5 py-1 rounded bg-stone-900 text-white font-semibold hover:bg-stone-800 cursor-pointer"
                  >
                    Ir al comparador
                  </button>
                  <button
                    type="button"
                    onClick={() => setCompareLimitNotice(null)}
                    aria-label="Cerrar aviso"
                    className="px-2 py-1 text-stone-600 hover:text-stone-900 cursor-pointer"
                  >
                    <span aria-hidden="true">×</span>
                  </button>
                </div>
              </div>
            )}

            {/* Aviso de transición vital si la etapa seleccionada lo prevé (§85) */}
            {!dismissedTransition && !isUrlBlocked && (
              <LifeStageTransitionBanner
                currentLifeStage={query.life_stage}
                onTransitionToNextStage={(next) => {
                  setQuery(prev => ({ ...prev, life_stage: next }));
                }}
                onDismiss={() => setDismissedTransition(true)}
              />
            )}

            {/* Filtros acumulativos con lógica AND entre dimensiones y OR en apoyos */}
            <SpecializedSearchFilters
              query={query}
              setQuery={handleSetQuery}
              totalResults={isUrlBlocked ? 0 : matchedProfileCount}
              hasMatchedProfileSubset={Boolean(deferredQuery.profile) && matchedProfileCount < searchOutput.total_results}
              centres={activeCentres}
              onResetFilters={resetAllFilters}
              easyReadMode={easyReadMode}
            />

            {(dynamicState?.used_fallback || dynamicState?.error) && (
              <div role="status" aria-live="polite" className="mb-4 p-3.5 rounded-xl border border-amber-300 bg-amber-50 text-amber-950 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
                  <div>
                    <strong className="text-stone-900">
                      Aviso de catálogo de reserva ({activeCentres.length} centros):
                    </strong>{' '}
                    <span>
                      No se pudo cargar el catálogo oficial completo ({dynamicState.error || 'error de red o ruta'}). Se muestran únicamente los centros canónicos de respaldo mientras se restablece el acceso a los ficheros oficiales.
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    disabled={isRetryingCatalog}
                    onClick={() => fetchCatalog(true)}
                    className="px-2.5 py-1 rounded border border-amber-400 bg-white text-stone-900 font-semibold hover:bg-amber-100 cursor-pointer disabled:opacity-60 inline-flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" aria-hidden="true" />
                    <span>{isRetryingCatalog ? 'Reintentando...' : 'Reintentar'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('what_changed')}
                    className="px-2.5 py-1 rounded bg-stone-900 text-white font-semibold hover:bg-stone-800 cursor-pointer"
                  >
                    Ver detalle técnico
                  </button>
                </div>
              </div>
            )}

            {/* Estado bloqueado, carga inicial o Lista de resultados */}
            {isUrlBlocked ? (
              <div className="bg-white rounded-xl border border-amber-200 p-8 shadow-xs text-center max-w-xl mx-auto my-8 space-y-4">
                <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-700">
                  <AlertTriangle className="w-6 h-6" aria-hidden="true" />
                </div>
                <h2 className="text-base font-bold text-stone-900">
                  Búsqueda pausada por parámetros de URL no reconocidos
                </h2>
                <p className="text-xs text-stone-600 leading-relaxed max-w-md mx-auto">
                  La dirección de enlace introducida contiene filtros que no pertenecen al catálogo de taxonomías ni al registro oficial de la Comunidad de Madrid. Para evitar presentar resultados engañosos, el buscador no muestra resultados parciales.
                </p>

                <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-left text-xs space-y-2 text-stone-700">
                  <div className="font-bold text-stone-800">Detalle de parámetros rechazados por el sistema:</div>
                  <ul className="list-disc list-inside space-y-1 text-amber-900 pl-1 font-mono text-[11px]">
                    {urlValidationErrors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>

                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleClearUrlErrorsAndReset}
                    className="px-4 py-2 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Restablecer y ver todos los recursos oficiales</span>
                  </button>
                </div>
              </div>
            ) : isCatalogLoading && activeCentres.length === 0 ? (
              <div
                role="status"
                aria-live="polite"
                className="space-y-4"
              >
                <div className="text-xs font-mono text-stone-600 px-1">
                  Cargando catálogo oficial verificado de la Comunidad de Madrid...
                </div>
                {[0, 1, 2].map((skeletonIdx) => (
                  <div
                    key={skeletonIdx}
                    className="bg-white rounded-xl border border-stone-200 p-5 space-y-3 animate-pulse"
                    aria-hidden="true"
                  >
                    <div className="h-4 bg-stone-200 rounded w-2/3" />
                    <div className="h-3 bg-stone-100 rounded w-1/2" />
                    <div className="h-8 bg-stone-50 rounded border border-stone-100" />
                  </div>
                ))}
              </div>
            ) : catalogFatalError && activeCentres.length === 0 ? (
              <div
                role="alert"
                className="bg-white rounded-xl border border-red-200 p-6 shadow-xs text-center max-w-xl mx-auto my-8 space-y-3"
              >
                <div className="w-11 h-11 rounded-full bg-red-50 border border-red-200 flex items-center justify-center mx-auto text-red-700">
                  <AlertTriangle className="w-5 h-5" aria-hidden="true" />
                </div>
                <h2 className="text-base font-bold text-stone-900">
                  No se pudo inicializar el catálogo de recursos
                </h2>
                <p className="text-xs text-stone-600 leading-relaxed max-w-md mx-auto">
                  Se produjo un fallo inesperado al cargar tanto los snapshots oficiales como la copia local de respaldo ({catalogFatalError}).
                </p>
                <div className="pt-1">
                  <button
                    type="button"
                    disabled={isRetryingCatalog}
                    onClick={() => fetchCatalog(true)}
                    className="px-4 py-2 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-60"
                  >
                    <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>{isRetryingCatalog ? 'Reintentando carga...' : 'Reintentar carga'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <SpecializedResultsList
                results={searchOutput.results}
                incompatibleResults={searchOutput.incompatible_results}
                query={query}
                onWhyAppears={(item) => setWhyAppearsItem(item)}
                onPrepareContact={(item) => setPrintableContactItem(item)}
                comparedIds={comparedCentreIds}
                onToggleCompare={toggleCompare}
                onResetFilters={resetAllFilters}
                easyReadMode={easyReadMode}
              />
            )}
          </div>
        )}


        {/* PESTAÑA: MAPA SINCRONIZADO (§63) */}
        {activeTab === 'map' && (
          <div className="space-y-6">
            <div className="border-b border-stone-200 pb-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-stone-900">
                  Mapa territorial sincronizado con los filtros
                </h2>
                <p className="text-xs text-stone-600 mt-0.5">
                  Los marcadores reflejan exactamente los recursos filtrados. La cercanía nunca sitúa un resultado C por delante de un nivel A.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('search')}
                className="px-3 py-1.5 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 cursor-pointer shrink-0"
              >
                Volver a la lista
              </button>
            </div>

            <Suspense fallback={<div className="p-8 text-center text-xs text-stone-500">Cargando mapa territorial...</div>}>
              <SpecializedMapView
                results={searchOutput.results}
                selectedCentreId={selectedMapCentreId}
                onSelectCentre={(id) => setSelectedMapCentreId(id)}
                onWhyAppears={(item) => setWhyAppearsItem(item)}
                originCoords={resolvedOrigin.coordinates}
                originName={resolvedOrigin.name}
                radiusKm={query.radius_km}
                hasActiveProfile={Boolean(deferredQuery.profile)}
              />
            </Suspense>
          </div>
        )}

        {/* PESTAÑA: COMPARADOR CIUDADANO (§15) */}
        {activeTab === 'comparator' && (
          <Suspense fallback={<div className="p-8 text-center text-xs text-stone-500">Cargando comparador...</div>}>
            <SpecializedComparatorView
              comparedCentres={comparedCentres}
              onRemoveFromCompare={toggleCompare}
              onClearCompare={() => setComparedCentreIds([])}
              onGoToSearch={() => setActiveTab('search')}
              onWhyAppears={(item) => setWhyAppearsItem(item)}
            />
          </Suspense>
        )}

        {/* PESTAÑA: QUÉ HA CAMBIADO (§84) */}
        {activeTab === 'what_changed' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h2 className="text-lg font-bold text-stone-900">
                  Auditoría de cambios entre snapshots del registro oficial
                </h2>
                <p className="text-xs text-stone-600 mt-0.5">
                  Trazabilidad de altas, servicios incorporados, vigencia de disponibilidad caducada e incidencias técnicas.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('search')}
                className="px-3.5 py-1.5 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 cursor-pointer"
              >
                Ir al buscador
              </button>
            </div>
            <Suspense fallback={<div className="p-8 text-center text-xs text-stone-500">Cargando histórico de cambios...</div>}>
              <WhatChangedModal
                isOpen={true}
                inline={true}
                onClose={() => setActiveTab('search')}
                dynamicState={dynamicState}
              />
            </Suspense>
          </div>
        )}

        {/* PESTAÑA: GOBERNANZA TAXONÓMICA Y UTILIDAD ADMINISTRATIVA (§33, §58) */}
        {activeTab === 'governance' && (
          <Suspense fallback={<div className="p-8 text-center text-xs text-stone-500">Cargando gobernanza taxonómica...</div>}>
            <TaxonomyGovernanceView centres={activeCentres} />
          </Suspense>
        )}

        {/* PESTAÑA: PRUEBAS CANÓNICAS EN VIVO (§31, §44, §79, §90) */}
        {activeTab === 'tests' && (
          <Suspense fallback={<div className="p-8 text-center text-xs text-stone-500">Cargando suite canónica de validación...</div>}>
            <SpecializedTestsRunnerView />
          </Suspense>
        )}
      </main>

      {/* 4. Modales del sistema */}
      {whyAppearsItem && (
        <WhyAppearsModal
          item={whyAppearsItem}
          onClose={() => setWhyAppearsItem(null)}
        />
      )}

      {printableContactItem && (
        <PrintableContactCardModal
          item={printableContactItem}
          onClose={() => setPrintableContactItem(null)}
        />
      )}

      <SavedSearchesModal
        isOpen={isSavedSearchesOpen}
        onClose={() => setIsSavedSearchesOpen(false)}
        currentQuery={query}
        datasetSnapshot={dynamicState?.timestamp?.slice(0, 10)}
        onLoadSearch={(filters) => {
          setQuery(prev => ({
            ...prev,
            ...filters,
            accessibility_needs: filters.accessibility_needs || [],
            user_ephemeral_location: null,
            location_mode: filters.municipality ? 'municipality' : 'all'
          }));
        }}
        onOpenWhatChanged={() => {
          setIsSavedSearchesOpen(false);
          setIsWhatChangedOpen(true);
        }}
      />

      {isWhatChangedOpen && (
        <Suspense fallback={null}>
          <WhatChangedModal
            isOpen={isWhatChangedOpen}
            onClose={() => setIsWhatChangedOpen(false)}
            dynamicState={dynamicState}
          />
        </Suspense>
      )}

      <EasyReadGlossaryModal
        isOpen={isGlossaryOpen}
        onClose={() => setIsGlossaryOpen(false)}
      />

      {/* 5. Pie de página institucional sobrio (Zero-Pill Discipline) */}
      <footer className="mt-auto border-t border-stone-200 bg-white text-stone-600 text-xs py-8 px-4 no-print">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-1">
            <div className="font-bold text-stone-900 text-sm">
              Madrid Apoyo Especializado v1.9 · DATAMAD 2026
            </div>
            <p className="text-stone-500 max-w-2xl leading-relaxed">
              DATAMAD 2026: Buscador independiente basado en los registros oficiales de Atención Social del Ayuntamiento de Madrid y la Comunidad de Madrid. Orientación verificable (sin finalidad diagnóstica). Código abierto bajo licencia Apache-2.0. Sin telemetría ni almacenamiento de datos de salud.
              {dynamicState?.loaded && dynamicState.timestamp ? ` · Última captura oficial verificada: ${dynamicState.timestamp.slice(0, 10)}.` : ''}
            </p>
          </div>

          <div className="flex items-center gap-4 flex-wrap text-stone-700">
            <button
              type="button"
              onClick={() => setActiveTab('governance')}
              className="hover:text-stone-950 underline underline-offset-2 cursor-pointer"
            >
              Gobernanza Taxonómica
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('what_changed')}
              className="hover:text-stone-950 underline underline-offset-2 cursor-pointer"
            >
              Histórico de Cambios
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('tests')}
              className="hover:text-stone-950 underline underline-offset-2 font-mono cursor-pointer"
            >
              Suite Canónica de Validación
            </button>
          </div>
        </div>
      </footer>

      <PWAUpdatePrompt />
    </div>
  );
}
