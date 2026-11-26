/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Búsquedas Guardadas en el Navegador
 * Almacenamiento 100% local en localStorage sin persistencia de coordenadas exactas ni datos médicos (§83)
 */

import React, { useState, useEffect, useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { SavedSearch, SearchQueryState } from '../../types/specialized';
import { 
  X, 
  Bookmark, 
  Trash2, 
  History, 
  Plus, 
  ShieldCheck
} from 'lucide-react';
import { CORE_PROFILES, SUPPORT_TYPES, LIFE_STAGES, FUNCTIONAL_NEEDS } from '../../data/specializedTaxonomy';
import { getProfileDefinition, ACCESSIBILITY_MAP } from '../../utils/specializedEngine';

import {
  loadValidatedSavedSearches,
  persistSavedSearches
} from '../../utils/savedSearchesStorage';

interface SavedSearchesModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentQuery: SearchQueryState;
  onLoadSearch: (filters: SavedSearch['filters']) => void;
  onOpenWhatChanged: () => void;
  datasetSnapshot?: string;
}

export const SavedSearchesModal: React.FC<SavedSearchesModalProps> = ({
  isOpen,
  onClose,
  currentQuery,
  onLoadSearch,
  onOpenWhatChanged,
  datasetSnapshot
}) => {
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [newSearchName, setNewSearchName] = useState('');
  const [confirmClearAll, setConfirmClearAll] = useState(false);

  // Cargar y validar búsquedas locales del navegador (migrando desde v1.7 si existe)
  useEffect(() => {
    setSavedSearches(loadValidatedSavedSearches());
  }, [isOpen]);

  const saveSearchesToStorage = (list: SavedSearch[]) => {
    setSavedSearches(list);
    persistSavedSearches(list);
  };

  const handleSaveCurrent = (e: React.FormEvent) => {
    e.preventDefault();
    const name = newSearchName.trim() || `Búsqueda del ${new Date().toLocaleDateString('es-ES')}`;

    // Regla de Privacidad SAVE-001 y §83.2: NUNCA guardar coordenadas exactas GPS
    const safeFilters = {
      profile: currentQuery.profile,
      functional_needs: currentQuery.functional_needs,
      support_types: currentQuery.support_types,
      support_combination_mode: currentQuery.support_combination_mode,
      life_stage: currentQuery.life_stage,
      municipality: currentQuery.municipality,
      radius_km: currentQuery.radius_km,
      network_preference: currentQuery.network_preference,
      accessibility_needs: currentQuery.accessibility_needs
    };

    const newRecord: SavedSearch = {
      saved_search_id: `search_${Date.now()}`,
      name,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      filters: safeFilters,
      taxonomy_version: '1.9.0',
      dataset_snapshot: datasetSnapshot || new Date().toISOString().slice(0, 10)
    };

    saveSearchesToStorage([newRecord, ...savedSearches]);
    setNewSearchName('');
  };

  const handleDelete = (id: string) => {
    const updated = savedSearches.filter(s => s.saved_search_id !== id);
    saveSearchesToStorage(updated);
  };

  const handleClearAll = () => {
    if (!confirmClearAll) {
      setConfirmClearAll(true);
      return;
    }
    saveSearchesToStorage([]);
    setConfirmClearAll(false);
  };

  const handleApply = (search: SavedSearch) => {
    onLoadSearch(search.filters);
    onClose();
  };

  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isOpen);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="saved-searches-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        ref={modalRef}
        className="bg-white rounded-2xl max-w-2xl w-full border border-stone-200 shadow-xl overflow-hidden my-8 max-h-[90vh] flex flex-col"
        tabIndex={-1}
      >
        {/* Cabecera */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50">
          <div className="flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-stone-700" />
            <div>
              <h2 id="saved-searches-modal-title" className="text-base font-bold text-stone-900">
                Búsquedas guardadas en tu navegador
              </h2>
              <div className="text-[11px] text-stone-500">
                Almacenamiento 100% local (sin cuenta ni servidores · RGPD)
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="p-1.5 text-stone-500 hover:text-stone-800 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Formulario para guardar búsqueda actual */}
        <div className="p-6 border-b border-stone-200 bg-stone-50/50">
          <form onSubmit={handleSaveCurrent} className="space-y-2">
            <label htmlFor="saved-search-name-input" className="block text-xs font-bold text-stone-800">
              Guardar configuración actual de filtros
            </label>
            <div className="flex gap-2">
              <input
                id="saved-search-name-input"
                type="text"
                value={newSearchName}
                onChange={(e) => setNewSearchName(e.target.value)}
                placeholder="Nombre para esta búsqueda (ej. «DCA en Madrid con Logopedia»)"
                className="flex-1 px-3 py-2 text-xs border border-stone-300 rounded-lg focus:outline-none focus:border-stone-900 bg-white"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Guardar</span>
              </button>
            </div>
            <div className="text-[11px] text-stone-500 flex items-center gap-1 mt-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Garantía de privacidad: nunca se guardan coordenadas exactas GPS ni diagnósticos libres.</span>
            </div>
          </form>
        </div>

        {/* Lista de búsquedas guardadas */}
        <div className="p-6 overflow-y-auto space-y-3 flex-1 text-xs">
          {savedSearches.length === 0 ? (
            <div className="text-center py-8 text-stone-600">
              No tienes ninguna búsqueda guardada en este navegador.
            </div>
          ) : (
            savedSearches.map((s) => (
              <div
                key={s.saved_search_id}
                className="p-3 rounded-xl border border-stone-200 bg-white hover:border-stone-300 transition-colors space-y-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-stone-900 text-sm">
                      {s.name}
                    </h3>
                    <div className="text-[11px] text-stone-500 font-mono mt-0.5">
                      Versión taxonomía: {s.taxonomy_version} · Guardado el {new Date(s.created_at).toLocaleDateString('es-ES')}
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleApply(s)}
                      className="px-3 py-1 bg-stone-900 text-white rounded-md text-xs font-semibold hover:bg-stone-800 transition-colors cursor-pointer"
                    >
                      Abrir búsqueda
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(s.saved_search_id)}
                      className="p-1.5 text-stone-500 hover:text-rose-700 rounded-md transition-colors cursor-pointer"
                      title="Eliminar"
                      aria-label={`Eliminar búsqueda guardada ${s.name}`}
                    >
                      <Trash2 className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>

                {/* Resumen editorial de filtros */}
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-stone-700 pt-1 border-t border-stone-100">
                  {(() => {
                    const summaryParts: string[] = [];
                    if (s.filters.profile) {
                      summaryParts.push(
                        getProfileDefinition(s.filters.profile)?.preferred_label ||
                          CORE_PROFILES[s.filters.profile as keyof typeof CORE_PROFILES]?.preferred_label ||
                          s.filters.profile
                      );
                    }
                    s.filters.support_types.forEach(st => {
                      summaryParts.push(SUPPORT_TYPES[st]?.label || st);
                    });
                    if (s.filters.life_stage && LIFE_STAGES[s.filters.life_stage]?.label) {
                      summaryParts.push(LIFE_STAGES[s.filters.life_stage].label);
                    }
                    if (s.filters.municipality) {
                      summaryParts.push(`${s.filters.municipality} (±${s.filters.radius_km} km)`);
                    }
                    if (s.filters.network_preference && s.filters.network_preference !== 'all') {
                      summaryParts.push(
                        s.filters.network_preference === 'public_network'
                          ? 'Red Pública/Concertada'
                          : 'Privados autorizados'
                      );
                    }
                    if (s.filters.support_combination_mode === 'all_supports_same_centre') {
                      summaryParts.push('Todos en misma sede');
                    }
                    (s.filters.accessibility_needs || []).forEach(acc => {
                      const label = ACCESSIBILITY_MAP[acc]?.label || acc;
                      summaryParts.push(`Acceso: ${label.split('(')[0].trim()}`);
                    });
                    (s.filters.functional_needs || []).forEach(fn => {
                      summaryParts.push(FUNCTIONAL_NEEDS[fn]?.label || fn);
                    });

                    if (summaryParts.length === 0) {
                      return <span className="text-stone-500 italic">Catálogo completo sin filtros restrictivos</span>;
                    }

                    return summaryParts.map((part, idx) => (
                      <React.Fragment key={`${s.saved_search_id}-part-${idx}`}>
                        {idx > 0 && <span className="text-stone-300" aria-hidden="true">·</span>}
                        <span className="font-medium text-stone-800">{part}</span>
                      </React.Fragment>
                    ));
                  })()}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pie con botón de "Qué ha cambiado" y Limpiar todo */}
        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex flex-wrap items-center justify-between gap-2 text-xs">
          <button
            type="button"
            onClick={() => {
              onClose();
              onOpenWhatChanged();
            }}
            className="font-semibold text-stone-900 hover:text-stone-700 flex items-center gap-1.5 cursor-pointer"
          >
            <History className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
            <span>Ver qué ha cambiado en el conjunto de datos</span>
          </button>

          {savedSearches.length > 0 && (
            confirmClearAll ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="px-2.5 py-1 bg-rose-600 text-white rounded font-semibold hover:bg-rose-700 transition-colors cursor-pointer"
                >
                  Confirmar borrado
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmClearAll(false)}
                  className="text-stone-600 hover:text-stone-900 cursor-pointer"
                >
                  Cancelar
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleClearAll}
                className="text-stone-500 hover:text-rose-700 transition-colors cursor-pointer"
              >
                Borrar todas las búsquedas locales
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
};
