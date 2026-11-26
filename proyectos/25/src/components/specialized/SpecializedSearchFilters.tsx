/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Search & Cumulative Taxonomy Filters
 * Principio v1.4: perfil + necesidad funcional + apoyo + etapa vital + ubicación + red
 * se aplican conjuntamente mediante lógica AND entre dimensiones y OR controlado dentro de una misma dimensión (§62.1).
 * Novedad v1.8: Filtros de accesibilidad literales por código datos.madrid.es y rutas relativas compatibles con BASE_URL.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  SpecializedCentre,
  SearchQueryState, 
  SupportTypeId, 
  FunctionalNeedId, 
  LifeStage, 
  NetworkPreference
} from '../../types/specialized';
import { 
  CORE_PROFILES, 
  EXPERIMENTAL_PROFILES, 
  PENDING_PROFILES,
  SUPPORT_TYPES, 
  FUNCTIONAL_NEEDS, 
  LIFE_STAGES 
} from '../../data/specializedTaxonomy';
import { getProfileDefinition } from '../../utils/specializedEngine';
import { 
  MapPin, 
  Navigation, 
  RotateCcw, 
  ChevronDown, 
  ChevronUp, 
  Info,
  Building2,
  Accessibility,
  Ear,
  Type,
  MessageCircle
} from 'lucide-react';

const ACCESSIBILITY_FEATURES = [
  { id: 'wheelchair_access', label: 'Acceso silla de ruedas', easyLabel: 'Acceso en silla de ruedas', icon: Accessibility },
  { id: 'sign_language', label: 'Lengua de signos', easyLabel: 'Lengua de signos', icon: MessageCircle },
  { id: 'tactile_signage', label: 'Señalización podotáctil', easyLabel: 'Suelo táctil (personas ciegas)', icon: Type },
  { id: 'magnetic_loops', label: 'Bucle magnético', easyLabel: 'Bucle magnético (audífonos)', icon: Ear }
];

import { MADRID_MUNICIPALITIES } from '../../data/municipalitiesData';

interface MunicipalityOption {
  code: string;
  name: string;
  search_name: string;
  lat: number;
  lon: number;
}

interface SearchFiltersProps {
  query: SearchQueryState;
  setQuery: React.Dispatch<React.SetStateAction<SearchQueryState>>;
  totalResults: number;
  hasMatchedProfileSubset?: boolean;
  centres?: SpecializedCentre[];
  onResetFilters: () => void;
  easyReadMode?: boolean;
}

export const SpecializedSearchFilters: React.FC<SearchFiltersProps> = ({
  query,
  setQuery,
  totalResults,
  hasMatchedProfileSubset = false,
  centres,
  onResetFilters,
  easyReadMode = false
}) => {
  const [municipalities, setMunicipalities] = useState<MunicipalityOption[]>(MADRID_MUNICIPALITIES);
  const [geoStatus, setGeoStatus] = useState<'idle' | 'requesting' | 'granted' | 'denied' | 'timeout'>('idle');
  const [showAdvancedNeeds, setShowAdvancedNeeds] = useState(false);
  const [isMobileFiltersOpen, setIsMobileFiltersOpen] = useState(false);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (query.profile) count++;
    count += query.support_types.length;
    if (query.life_stage) count++;
    if (query.network_preference !== 'all') count++;
    if (query.municipality || query.location_mode === 'browser') count++;
    if (query.radius_km < 80) count++;
    count += query.accessibility_needs.length;
    count += query.functional_needs.length;
    return count;
  }, [query]);

  const scrollToResults = () => {
    setIsMobileFiltersOpen(false);
    if (typeof document !== 'undefined') {
      document.getElementById('results-list-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Carga del catálogo oficial de municipios de la Comunidad de Madrid
  useEffect(() => {
    const baseUrl = import.meta.env.BASE_URL || '/';
    const muniUrl = `${baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`}data/municipalities.json`;
    fetch(muniUrl)
      .then(res => res.json())
      .then((data: MunicipalityOption[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setMunicipalities(data);
        }
      })
      .catch(() => {});

    // Solicitud/activación inicial de ubicación de referencia por defecto
    if (query.location_mode === 'browser' && !query.municipality) {
      requestBrowserLocation();
    }
  }, []);

  // Geolocalización efímera del navegador (§67): sin suplantación si el usuario deniega o falla el GPS
  const requestBrowserLocation = () => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setGeoStatus('denied');
      setQuery(prev => ({
        ...prev,
        municipality: null,
        user_ephemeral_location: null,
        location_mode: 'all'
      }));
      return;
    }

    setGeoStatus('requesting');
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      setGeoStatus('timeout');
      setQuery(prev => ({
        ...prev,
        municipality: null,
        user_ephemeral_location: null,
        location_mode: 'all'
      }));
    }, 5000);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        setGeoStatus('granted');
        setQuery(prev => ({
          ...prev,
          user_ephemeral_location: [pos.coords.latitude, pos.coords.longitude],
          location_mode: 'browser',
          municipality: null
        }));
      },
      (err) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        setGeoStatus(err?.code === 3 ? 'timeout' : 'denied');
        setQuery(prev => ({
          ...prev,
          user_ephemeral_location: null,
          location_mode: 'all',
          municipality: null
        }));
      },
      { timeout: 5000, maximumAge: 60000, enableHighAccuracy: false }
    );
  };

  const handleSelectMunicipality = (muniName: string) => {
    setGeoStatus('idle');
    if (!muniName) {
      // Sin municipio seleccionado, vuelve al ámbito regional completo (Comunidad de Madrid)
      setQuery(prev => ({
        ...prev,
        municipality: null,
        user_ephemeral_location: null,
        location_mode: 'all'
      }));
      return;
    }
    const selected = municipalities.find(m => m.name === muniName);
    if (!selected) return;
    // Seleccionar un municipio desactiva obligatoriamente el GPS y asigna el nuevo origen municipal
    setQuery(prev => ({
      ...prev,
      municipality: selected.name,
      user_ephemeral_location: [selected.lat, selected.lon],
      location_mode: 'municipality'
    }));
  };

  const toggleSupport = (id: SupportTypeId) => {
    setQuery(prev => {
      const exists = prev.support_types.includes(id);
      return {
        ...prev,
        support_types: exists 
          ? prev.support_types.filter(s => s !== id)
          : [...prev.support_types, id]
      };
    });
  };

  const toggleFunctionalNeed = (id: FunctionalNeedId) => {
    setQuery(prev => {
      const exists = prev.functional_needs.includes(id);
      return {
        ...prev,
        functional_needs: exists
          ? prev.functional_needs.filter(n => n !== id)
          : [...prev.functional_needs, id]
      };
    });
  };

  // Definición del perfil seleccionado para filtrado dinámico contextual
  const activeProfileDef = useMemo(() => {
    if (!query.profile) return null;
    return getProfileDefinition(query.profile);
  }, [query.profile]);

  // Conteo real en catálogo de apoyos y perfiles para transparencia previa al filtrado
  const supportCounts = useMemo(() => {
    const counts: Partial<Record<SupportTypeId, number>> = {};
    for (const id of Object.keys(SUPPORT_TYPES) as SupportTypeId[]) {
      counts[id] = 0;
    }
    if (centres && centres.length > 0) {
      for (const c of centres) {
        for (const sup of c.supports || []) {
          counts[sup] = (counts[sup] || 0) + 1;
        }
      }
    }
    return counts;
  }, [centres]);

  const profileCounts = useMemo(() => {
    const counts: Record<string, { a1: number; a2: number; total: number }> = {};
    if (centres && centres.length > 0) {
      for (const c of centres) {
        for (const p of c.explicit_specialisations || []) {
          if (!counts[p]) counts[p] = { a1: 0, a2: 0, total: 0 };
          counts[p].a1 += 1;
          counts[p].total += 1;
        }
        for (const p of c.entity_declared_specialisations || []) {
          if (!counts[p]) counts[p] = { a1: 0, a2: 0, total: 0 };
          counts[p].a2 += 1;
          counts[p].total += 1;
        }
      }
    }
    return counts;
  }, [centres]);

  // Solo ofrecer al público perfiles con evidencia verificable en el catálogo vigente (evita callejones sin salida como TDAH con 0 registros)
  const selectableProfiles = useMemo(() => {
    const all = [
      ...Object.values(CORE_PROFILES),
      ...Object.values(EXPERIMENTAL_PROFILES),
      ...Object.values(PENDING_PROFILES)
    ];
    if (!centres || centres.length === 0) {
      return all.filter(prof => prof.id !== 'adhd');
    }
    return all.filter(prof => (profileCounts[prof.id]?.total || 0) > 0);
  }, [centres, profileCounts]);

  // Tipos de apoyo dinámicos adaptados a la taxonomía seleccionada
  const displayedSupportTypes = useMemo(() => {
    if (!activeProfileDef || !activeProfileDef.typical_supports || activeProfileDef.typical_supports.length === 0) {
      return Object.values(SUPPORT_TYPES);
    }
    return activeProfileDef.typical_supports
      .map(id => SUPPORT_TYPES[id])
      .filter(Boolean);
  }, [activeProfileDef]);

  // Etapas vitales dinámicas autorizadas para el perfil seleccionado
  const displayedLifeStages = useMemo(() => {
    if (!activeProfileDef || !activeProfileDef.allowed_life_stages || activeProfileDef.allowed_life_stages.length === 0) {
      return Object.entries(LIFE_STAGES);
    }
    return Object.entries(LIFE_STAGES).filter(([key]) => 
      activeProfileDef.allowed_life_stages.includes(key as LifeStage)
    );
  }, [activeProfileDef]);

  // Necesidades funcionales dinámicas observables pertinentes a la condición seleccionada
  const displayedFunctionalNeeds = useMemo(() => {
    if (!activeProfileDef || !activeProfileDef.typical_needs || activeProfileDef.typical_needs.length === 0) {
      return Object.values(FUNCTIONAL_NEEDS);
    }
    return activeProfileDef.typical_needs
      .map(id => FUNCTIONAL_NEEDS[id])
      .filter(Boolean);
  }, [activeProfileDef]);

  // Auto-limpieza preventiva: si el usuario cambia de perfil, retira apoyos o necesidades no pertinentes
  useEffect(() => {
    if (!activeProfileDef) return;

    setQuery(prev => {
      let changed = false;
      let nextSupports = prev.support_types;
      let nextNeeds = prev.functional_needs;
      let nextStage = prev.life_stage;

      if (activeProfileDef.typical_supports && activeProfileDef.typical_supports.length > 0) {
        const filtered = prev.support_types.filter(s => activeProfileDef.typical_supports!.includes(s));
        if (filtered.length !== prev.support_types.length) {
          nextSupports = filtered;
          changed = true;
        }
      }

      if (activeProfileDef.typical_needs && activeProfileDef.typical_needs.length > 0) {
        const filtered = prev.functional_needs.filter(n => activeProfileDef.typical_needs!.includes(n));
        if (filtered.length !== prev.functional_needs.length) {
          nextNeeds = filtered;
          changed = true;
        }
      }

      if (activeProfileDef.allowed_life_stages && prev.life_stage) {
        if (!activeProfileDef.allowed_life_stages.includes(prev.life_stage)) {
          nextStage = null;
          changed = true;
        }
      }

      if (!changed) return prev;
      return {
        ...prev,
        support_types: nextSupports,
        functional_needs: nextNeeds,
        life_stage: nextStage
      };
    });
  }, [query.profile, activeProfileDef]);

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4 sm:p-5 shadow-xs mb-6 sm:mb-8">
      {/* Cabecera compacta móvil con plegado de filtros y acceso directo a resultados */}
      <div className="md:hidden flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-stone-100">
        <button
          type="button"
          aria-expanded={isMobileFiltersOpen}
          onClick={() => setIsMobileFiltersOpen(prev => !prev)}
          className="flex items-center gap-2 text-xs font-bold text-stone-900 py-1.5 px-2.5 rounded-lg border border-stone-200 bg-stone-50 hover:bg-stone-100 cursor-pointer"
        >
          <span>
            {isMobileFiltersOpen ? 'Ocultar filtros' : 'Configurar filtros'}
            {activeFiltersCount > 0 ? ` (${activeFiltersCount})` : ''}
          </span>
          {isMobileFiltersOpen ? (
            <ChevronUp className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
          )}
        </button>

        <button
          type="button"
          onClick={scrollToResults}
          className="px-3.5 py-1.5 bg-stone-900 text-white text-xs font-semibold rounded-lg hover:bg-stone-800 transition-colors cursor-pointer"
        >
          Ver {totalResults}{' '}
          {hasMatchedProfileSubset
            ? totalResults === 1 ? 'relacionado' : 'relacionados'
            : totalResults === 1 ? 'recurso' : 'recursos'}
        </button>
      </div>

      <div className={`${isMobileFiltersOpen ? 'block pt-4' : 'hidden md:block'} space-y-6`}>
      <h2 className="sr-only">Filtros de búsqueda</h2>
      {/* 2. Dimensión 1: Perfiles oficiales verificados */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
          <h3 className={`font-bold uppercase tracking-wider text-stone-700 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
            {easyReadMode ? '¿Qué situación o perfil buscas?' : 'Perfil o condición'}
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {selectableProfiles.map((prof) => {
            const isSelected = query.profile === prof.id;
            const visibleLabel = prof.preferred_label.replace(' (Reserva/Experimental)', '').replace(' (Experimental)', '');
            return (
              <button
                key={prof.id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => {
                  const newProfile = isSelected ? null : prof.id;
                  setQuery(prev => {
                    if (!newProfile) {
                      return { ...prev, profile: null, support_types: [], functional_needs: [] };
                    }
                    const def = getProfileDefinition(newProfile);
                    const allowedStages = def?.allowed_life_stages || [];
                    const nextStage = prev.life_stage && !allowedStages.includes(prev.life_stage) ? null : prev.life_stage;
                    const allowedSupports = def?.typical_supports || [];
                    const allowedNeeds = def?.typical_needs || [];
                    const nextSupports = allowedSupports.length > 0 
                      ? prev.support_types.filter(s => allowedSupports.includes(s))
                      : prev.support_types;
                    const nextNeeds = allowedNeeds.length > 0
                      ? prev.functional_needs.filter(n => allowedNeeds.includes(n))
                      : prev.functional_needs;
                    return {
                      ...prev,
                      profile: newProfile,
                      life_stage: nextStage,
                      support_types: nextSupports,
                      functional_needs: nextNeeds
                    };
                  });
                }}
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex items-center justify-between gap-2 ${
                  isSelected
                    ? 'border-stone-900 bg-stone-900 text-white shadow-xs'
                    : 'border-stone-200 bg-white hover:bg-stone-50 text-stone-900'
                }`}
              >
                <span className={`${easyReadMode ? 'text-sm' : 'text-xs'} font-bold leading-snug`}>
                  {visibleLabel}
                </span>
              </button>
            );
          })}
        </div>

        {centres && centres.length > 0 && query.profile && (profileCounts[query.profile]?.total || 0) === 0 && (
          <div className="mt-2 text-xs bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-amber-950 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-amber-700 shrink-0" aria-hidden="true" />
              <span>
                Los registros públicos actuales no incluyen centros acreditados específicamente para «{activeProfileDef?.preferred_label.replace(' (Reserva/Experimental)', '').replace(' (Experimental)', '') || query.profile}». Consulta los recursos de orientación general abajo o retira este filtro.
              </span>
            </div>
            <button
              type="button"
              onClick={() => setQuery(prev => ({ ...prev, profile: null }))}
              className="px-2.5 py-1 rounded bg-stone-900 text-white font-semibold hover:bg-stone-800 cursor-pointer shrink-0"
            >
              Quitar filtro de perfil
            </button>
          </div>
        )}
      </div>

      <div className="h-px bg-stone-100" />

      {/* Dimensión 2: Tipos de Apoyo (Dinámicos según la taxonomía seleccionada) */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2">
            <h3 className={`font-bold uppercase tracking-wider text-stone-700 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
              {easyReadMode ? '¿Qué ayuda o centro necesitas?' : 'Tipos de apoyo'}
            </h3>
            {activeProfileDef && (
              <span className="text-[11px] font-semibold text-emerald-800">
                · Adaptados a {activeProfileDef.preferred_label.split('(')[0].trim()}
              </span>
            )}
          </div>

          {/* Selector de modo de combinación */}
          <div
            role="group"
            aria-label="Modo de combinación de apoyos"
            className="inline-flex p-0.5 bg-stone-100 rounded-lg border border-stone-200 text-xs"
          >
            <button
              type="button"
              aria-pressed={query.support_combination_mode === 'any_support'}
              onClick={() => setQuery(prev => ({ ...prev, support_combination_mode: 'any_support' }))}
              className={`px-2.5 py-1 font-medium rounded-md transition-colors cursor-pointer ${
                query.support_combination_mode === 'any_support'
                  ? 'bg-stone-900 text-white shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Cualquier apoyo
            </button>
            <button
              type="button"
              aria-pressed={query.support_combination_mode === 'all_supports_same_centre'}
              onClick={() => setQuery(prev => ({ ...prev, support_combination_mode: 'all_supports_same_centre' }))}
              title="Exige que todos los apoyos marcados estén confirmados en el mismo centro físico"
              className={`px-2.5 py-1 font-medium rounded-md transition-colors flex items-center gap-1 cursor-pointer ${
                query.support_combination_mode === 'all_supports_same_centre'
                  ? 'bg-stone-900 text-white shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              <Building2 className="w-3 h-3" aria-hidden="true" />
              <span>Todos en la misma sede</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {displayedSupportTypes.map((st) => {
            const isChecked = query.support_types.includes(st.id);
            return (
              <button
                key={st.id}
                type="button"
                aria-pressed={isChecked}
                onClick={() => toggleSupport(st.id)}
                className={`p-2.5 rounded-lg border text-left transition-colors cursor-pointer flex items-center ${
                  isChecked
                    ? 'border-stone-900 bg-stone-900 text-white font-semibold shadow-xs'
                    : 'border-stone-200 hover:bg-stone-50 text-stone-700'
                }`}
              >
                <span className={`${easyReadMode ? 'text-sm' : 'text-xs'} leading-snug`}>{st.label}</span>
              </button>
            );
          })}
        </div>

        {query.support_combination_mode === 'all_supports_same_centre' && query.support_types.length > 1 && (
          <div className="mt-2 text-xs bg-stone-50 border border-stone-200 rounded-lg p-2.5 text-stone-700 flex items-center gap-2">
            <Info className="w-4 h-4 text-stone-500 shrink-0" aria-hidden="true" />
            <span>
              <strong>Sede unificada activa:</strong> Se comprobarán los apoyos en el mismo centro físico.
            </span>
          </div>
        )}

        {centres &&
          centres.length > 0 &&
          query.support_types.some(s => (supportCounts[s] || 0) === 0) && (
            <div className="mt-2 text-xs bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-amber-950 flex items-center gap-2">
              <Info className="w-4 h-4 text-amber-700 shrink-0" aria-hidden="true" />
              <span>
                <strong>Desglose no especificado en el registro oficial:</strong> Los ficheros públicos actuales no detallan servicios de{' '}
                {query.support_types
                  .filter(s => (supportCounts[s] || 0) === 0)
                  .map(s => SUPPORT_TYPES[s]?.label || s)
                  .join(' ni ')}
                . Los centros compatibles se muestran como «Coincidencia parcial» para que pueda confirmarlo al llamar.
              </span>
            </div>
          )}
      </div>

      <div className="h-px bg-stone-100" />

      {/* Dimensiones: Etapa Vital, Preferencia de Red y Localización */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Etapa Vital (Dinámica según las etapas autorizadas en la taxonomía) */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className={`font-bold uppercase tracking-wider text-stone-700 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
              {easyReadMode ? 'Edad de la persona' : 'Etapa vital'}
            </h3>
            {activeProfileDef && (
              <span className="text-[10px] text-stone-500 font-medium">
                {displayedLifeStages.length} autorizada{displayedLifeStages.length === 1 ? '' : 's'}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {displayedLifeStages.map(([key, item]) => {
              const isSelected = query.life_stage === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setQuery(prev => ({
                    ...prev,
                    life_stage: isSelected ? null : (key as LifeStage)
                  }))}
                  className={`px-3 py-2 text-xs rounded-lg border text-left transition-colors cursor-pointer ${
                    isSelected
                      ? 'border-stone-900 bg-stone-900 text-white font-semibold'
                      : 'border-stone-200 hover:bg-stone-50 text-stone-700'
                  }`}
                >
                  <div className="font-medium">{item.label}</div>
                  <div className={`text-[10px] ${isSelected ? 'text-stone-300' : 'text-stone-500'}`}>
                    {item.ageRange}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Titularidad y Red */}
        <div>
          <h3 className={`font-bold uppercase tracking-wider text-stone-700 block mb-2 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
            {easyReadMode ? 'Tipo de centro (público o privado)' : 'Red y titularidad'}
          </h3>
          <div className="space-y-1.5 text-xs">
            {[
              { id: 'all', label: 'Todas las titularidades' },
              { id: 'public_network', label: 'Red Pública y Concertada' },
              { id: 'private_authorised', label: 'Privados autorizados' }
            ].map(opt => (
              <label 
                key={opt.id}
                className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                  query.network_preference === opt.id
                    ? 'border-stone-900 bg-stone-50 font-medium text-stone-900'
                    : 'border-stone-200 text-stone-600 hover:bg-stone-50'
                }`}
              >
                <input
                  type="radio"
                  name="network_pref"
                  checked={query.network_preference === opt.id}
                  onChange={() => setQuery(prev => ({ ...prev, network_preference: opt.id as NetworkPreference }))}
                  className="accent-stone-900"
                />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Localización territorial y radio */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className={`font-bold uppercase tracking-wider text-stone-700 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
              {easyReadMode ? '¿En qué zona quieres buscar?' : 'Ubicación y radio'}
            </h3>
          </div>

          <div className="space-y-2">
            {/* Botón preferido: Usar mi ubicación (§67.1) */}
            <button
              type="button"
              onClick={requestBrowserLocation}
              disabled={geoStatus === 'requesting'}
              className={`w-full py-2 px-3 text-xs font-medium rounded-lg border flex items-center justify-center gap-2 transition-colors cursor-pointer ${
                query.location_mode === 'browser' && query.user_ephemeral_location
                  ? 'border-emerald-600 bg-emerald-50 text-emerald-900 font-semibold shadow-xs'
                  : 'border-stone-300 bg-white text-stone-700 hover:bg-stone-50'
              }`}
            >
              <Navigation className="w-3.5 h-3.5" aria-hidden="true" />
              <span>
                {geoStatus === 'requesting'
                  ? 'Obteniendo posición...'
                  : query.location_mode === 'browser' && query.user_ephemeral_location
                  ? '✓ Usando tu ubicación actual (GPS)'
                  : 'Usar mi ubicación'}
              </span>
            </button>

            {(geoStatus === 'denied' || geoStatus === 'timeout') && (
              <div
                role="status"
                aria-live="polite"
                className="text-[11px] text-amber-950 bg-amber-50 border border-amber-200 rounded-lg p-2 leading-snug"
              >
                {geoStatus === 'timeout'
                  ? 'Tiempo de espera agotado al obtener tu GPS. Selecciona un municipio en el desplegable inferior para fijar el origen.'
                  : 'No se pudo acceder a la ubicación GPS del navegador. Selecciona tu municipio en el desplegable inferior para ordenar por distancia.'}
              </div>
            )}

            {/* Selector de municipio alternativo (§67.1) */}
            <div className="flex items-center gap-1.5">
              <select
                aria-label="Seleccionar municipio de la Comunidad de Madrid para origen de distancias"
                value={query.location_mode === 'municipality' ? (query.municipality || '') : ''}
                onChange={(e) => handleSelectMunicipality(e.target.value)}
                className="w-full text-xs py-2 px-2.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-none focus:border-stone-900 cursor-pointer"
              >
                <option value="">Seleccionar municipio para cambiar de origen...</option>
                {municipalities.map((m) => (
                  <option key={m.code} value={m.name}>
                    {m.name}
                  </option>
                ))}
              </select>
              {query.location_mode === 'municipality' && query.municipality && (
                <button
                  type="button"
                  onClick={() => handleSelectMunicipality('')}
                  aria-label="Quitar municipio de origen y volver a toda la Comunidad de Madrid"
                  title="Volver a toda la Comunidad de Madrid"
                  className="px-2 py-2 text-xs text-stone-600 hover:text-stone-900 border border-stone-300 rounded-lg bg-white hover:bg-stone-50 shrink-0 cursor-pointer"
                >
                  ×
                </button>
              )}
            </div>

            {/* Selector de radio en kilómetros */}
            <div className="flex items-center gap-2 text-xs text-stone-600 pt-1" role="group" aria-label="Radio de búsqueda">
              <span className="shrink-0 font-medium">Radio:</span>
              {[5, 10, 20, 30, 50, 80].map((r) => (
                <button
                  key={r}
                  type="button"
                  aria-pressed={query.radius_km === r}
                  aria-label={`Radio de búsqueda: ${r} km`}
                  onClick={() => setQuery(prev => ({ ...prev, radius_km: r }))}
                  className={`px-2 py-1 rounded text-xs transition-colors cursor-pointer ${
                    query.radius_km === r
                      ? 'bg-stone-900 text-white font-bold'
                      : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                  }`}
                >
                  {r} km
                </button>
              ))}
            </div>

            {/* Indicador de origen de distancias activo (§67) */}
            <div className="flex items-center gap-1.5 text-[11px] text-stone-600 bg-stone-50 p-2 rounded-lg border border-stone-200">
              <MapPin className="w-3.5 h-3.5 text-stone-700 shrink-0" aria-hidden="true" />
              <span>
                <strong className="text-stone-800">Origen de cálculo:</strong>{' '}
                {query.location_mode === 'browser' && query.user_ephemeral_location
                  ? 'Tu ubicación actual (GPS efímero)'
                  : query.municipality
                  ? `${query.municipality} (centroide oficial)`
                  : query.radius_km < 80
                  ? `Madrid centro (Km 0 · radio ≤ ${query.radius_km} km)`
                  : 'Comunidad de Madrid (desde Km 0 · toda la región)'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Accesibilidad física oficial por códigos */}
      <div>
        <h3 className={`font-bold uppercase tracking-wider text-stone-700 block mb-2.5 ${easyReadMode ? 'text-sm normal-case tracking-normal text-stone-900' : 'text-xs'}`}>
          {easyReadMode ? 'Accesibilidad del edificio' : 'Accesibilidad oficial (Ayuntamiento de Madrid)'}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {ACCESSIBILITY_FEATURES.map((feat) => {
            const isChecked = query.accessibility_needs.includes(feat.id);
            return (
              <button
                key={feat.id}
                type="button"
                aria-pressed={isChecked}
                onClick={() => setQuery(prev => ({
                  ...prev,
                  accessibility_needs: isChecked
                    ? prev.accessibility_needs.filter(id => id !== feat.id)
                    : [...prev.accessibility_needs, feat.id]
                }))}
                className={`p-2.5 rounded-lg border text-left text-xs transition-colors flex items-center gap-2 cursor-pointer ${
                  isChecked
                    ? 'border-stone-900 bg-stone-900 text-white font-semibold shadow-xs'
                    : 'border-stone-200 hover:bg-stone-50 text-stone-700'
                }`}
              >
                <feat.icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>{easyReadMode ? feat.easyLabel : feat.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 5. Necesidades funcionales transversales (desplegable opcional) */}
      <div>
        <button
          type="button"
          aria-expanded={showAdvancedNeeds}
          onClick={() => setShowAdvancedNeeds(prev => !prev)}
          className="text-xs font-semibold text-stone-700 hover:text-stone-950 flex items-center gap-1.5 cursor-pointer"
        >
          {showAdvancedNeeds ? <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" /> : <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />}
          <span>
            {easyReadMode
              ? 'Otras necesidades (comunicación, alimentación, movilidad...)'
              : 'Necesidades funcionales observables (comunicación, deglución, motricidad, regulación sensorial...)'}
          </span>
          {activeProfileDef && (
            <span className="text-[11px] text-emerald-800 font-semibold">
              · {displayedFunctionalNeeds.length} relevantes
            </span>
          )}
          {query.functional_needs.length > 0 && (
            <span className="text-[11px] font-mono text-stone-900 font-bold">
              ({query.functional_needs.length} activas)
            </span>
          )}
        </button>

        {showAdvancedNeeds && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3 pt-3 border-t border-stone-100">
            {displayedFunctionalNeeds.map((need) => {
              const isSelected = query.functional_needs.includes(need.id);
              return (
                <button
                  key={need.id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => toggleFunctionalNeed(need.id)}
                  className={`p-2 rounded-md border text-left text-xs transition-colors cursor-pointer ${
                    isSelected
                      ? 'border-stone-900 bg-stone-900 text-white font-medium'
                      : 'border-stone-200 bg-white hover:bg-stone-50 text-stone-700'
                  }`}
                >
                  <div className="font-semibold">{need.label}</div>
                  <div className={`text-[10px] mt-0.5 line-clamp-1 ${isSelected ? 'text-stone-300' : 'text-stone-500'}`}>
                    {need.description}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 6. Barra resumen de criterios activos y reset (§62.1) */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-stone-200">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="font-bold text-stone-800">{easyReadMode ? 'Filtros elegidos:' : 'Criterios acumulativos activos:'}</span>
          {query.profile && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              {(CORE_PROFILES[query.profile as keyof typeof CORE_PROFILES]?.preferred_label || 
                EXPERIMENTAL_PROFILES[query.profile as keyof typeof EXPERIMENTAL_PROFILES]?.preferred_label || 
                PENDING_PROFILES[query.profile as keyof typeof PENDING_PROFILES]?.preferred_label || 
                query.profile)
                .replace(' (Reserva/Experimental)', '')
                .replace(' (Experimental)', '')}
              <button 
                type="button"
                aria-label="Eliminar filtro de perfil o condición"
                onClick={() => setQuery(prev => ({ ...prev, profile: null }))}
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          )}

          {query.support_types.map(s => (
            <span key={s} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              {SUPPORT_TYPES[s]?.label || s}
              <button 
                type="button"
                aria-label={`Eliminar filtro de apoyo: ${SUPPORT_TYPES[s]?.label || s}`}
                onClick={() => toggleSupport(s)} 
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          ))}

          {query.life_stage && (
            <span key={query.life_stage} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              {LIFE_STAGES[query.life_stage]?.label}
              <button 
                type="button"
                aria-label={`Eliminar filtro de etapa vital: ${LIFE_STAGES[query.life_stage]?.label}`}
                onClick={() => setQuery(prev => ({ ...prev, life_stage: null }))} 
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          )}

          {query.municipality && query.location_mode === 'municipality' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              {query.municipality} (±{query.radius_km} km)
              <button 
                type="button"
                aria-label={`Eliminar filtro de municipio: ${query.municipality}`}
                onClick={() => setQuery(prev => ({ ...prev, municipality: null, user_ephemeral_location: null, location_mode: 'all' }))} 
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          )}

          {query.location_mode === 'browser' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              Cerca de tu ubicación (±{query.radius_km} km)
              <button 
                type="button"
                aria-label="Eliminar filtro de ubicación GPS"
                onClick={() => setQuery(prev => ({ ...prev, user_ephemeral_location: null, location_mode: 'all' }))} 
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          )}

          {query.location_mode === 'all' && query.radius_km < 80 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              Radio ≤ {query.radius_km} km (Madrid centro)
              <button
                type="button"
                aria-label="Restablecer radio a toda la región (80 km)"
                onClick={() => setQuery(prev => ({ ...prev, radius_km: 80 }))}
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          )}

          {query.accessibility_needs.map(accId => {
            const feat = ACCESSIBILITY_FEATURES.find(f => f.id === accId);
            const accLabel = feat ? (easyReadMode ? feat.easyLabel : feat.label) : accId;
            return (
              <span key={accId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
                <span>{accLabel}</span>
                <button
                  type="button"
                  aria-label={`Eliminar filtro de accesibilidad: ${accLabel}`}
                  onClick={() => setQuery(prev => ({
                    ...prev,
                    accessibility_needs: prev.accessibility_needs.filter(id => id !== accId)
                  }))}
                  className="hover:text-stone-900 ml-1 cursor-pointer"
                >
                  <span aria-hidden="true">×</span>
                </button>
              </span>
            );
          })}

          {query.functional_needs.map(fnId => (
            <span key={fnId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-200">
              {FUNCTIONAL_NEEDS[fnId]?.label || fnId}
              <button 
                type="button"
                aria-label={`Eliminar filtro de necesidad funcional: ${FUNCTIONAL_NEEDS[fnId]?.label || fnId}`}
                onClick={() => toggleFunctionalNeed(fnId)} 
                className="hover:text-stone-900 ml-1 cursor-pointer"
              >
                <span aria-hidden="true">×</span>
              </button>
            </span>
          ))}

          {(!query.profile && 
            query.support_types.length === 0 && 
            !query.life_stage && 
            !query.municipality && 
            !query.user_ephemeral_location &&
            query.radius_km === 80 &&
            query.accessibility_needs.length === 0 &&
            query.functional_needs.length === 0) && (
            <span className="text-stone-500 italic">Mostrando todos los centros autorizados de la Comunidad de Madrid</span>
          )}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs font-mono font-bold text-stone-900">
            {totalResults}{' '}
            {hasMatchedProfileSubset
              ? totalResults === 1 ? 'recurso relacionado' : 'recursos relacionados'
              : totalResults === 1 ? 'recurso oficial' : 'recursos oficiales'}
          </span>
          <button
            type="button"
            onClick={onResetFilters}
            className="text-xs text-stone-600 hover:text-stone-900 flex items-center gap-1 font-medium transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" aria-hidden="true" />
            <span>Limpiar filtros</span>
          </button>
        </div>
      </div>
      </div>
    </div>
  );
};
