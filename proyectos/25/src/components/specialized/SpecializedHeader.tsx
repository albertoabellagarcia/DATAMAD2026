/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Top Navigation Bar (Clean & Minimalist)
 * Barra superior simplificada sin sobrecarga de elementos (§2 de frontend-design)
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  Bookmark, 
  Eye, 
  BookOpen,
  AlertCircle,
  X,
  ExternalLink,
  ShieldCheck,
  Menu
} from 'lucide-react';
import { PWAInstallButton } from '../pwa/PWAInstallButton';
import { useFocusTrap } from '../../hooks/useFocusTrap';

interface SpecializedHeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  easyReadMode: boolean;
  setEasyReadMode: (v: boolean | ((prev: boolean) => boolean)) => void;
  savedSearchesCount: number;
  comparedCount?: number;
  openSavedSearches: () => void;
  openGlossary: () => void;
  onOpenWhatChanged?: () => void;
  snapshotDate?: string;
}

export const SpecializedHeader: React.FC<SpecializedHeaderProps> = ({
  activeTab,
  setActiveTab,
  easyReadMode,
  setEasyReadMode,
  savedSearchesCount,
  comparedCount = 0,
  openSavedSearches,
  openGlossary,
  onOpenWhatChanged,
  snapshotDate
}) => {
  const [isSourcesModalOpen, setIsSourcesModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const sourcesModalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(sourcesModalRef, isSourcesModalOpen);

  useEffect(() => {
    if (!isSourcesModalOpen && !isMobileMenuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsSourcesModalOpen(false);
        setIsMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isSourcesModalOpen, isMobileMenuOpen]);

  return (
    <>
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-xs border-b border-stone-200 no-print">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-2 sm:gap-4 h-14 min-w-0">
            {/* Zona 1: Brand Wordmark limpio con h1 semántico único */}
            <div className="flex items-center min-w-0 flex-1 md:flex-initial">
              <h1 className="text-sm sm:text-lg font-extrabold tracking-tight text-stone-900 min-w-0 truncate">
                <button
                  type="button"
                  onClick={() => setActiveTab('search')}
                  aria-label="Madrid Apoyo Especializado · Volver a búsqueda"
                  className="text-left hover:text-stone-700 transition-colors cursor-pointer rounded-md py-1 truncate max-w-full"
                >
                  Madrid Apoyo Especializado
                </button>
              </h1>
            </div>

            {/* Zona 2: Navegación principal limpia */}
            <nav aria-label="Navegación principal" className="hidden md:flex items-center gap-6 h-full text-xs font-semibold shrink-0">
              {[
                { id: 'search', label: 'Búsqueda' },
                { id: 'map', label: 'Mapa' },
                { id: 'comparator', label: 'Comparador' }
              ].map((navItem) => {
                const isActive = activeTab === navItem.id;
                return (
                  <button
                    key={navItem.id}
                    type="button"
                    aria-current={isActive ? 'page' : undefined}
                    onClick={() => setActiveTab(navItem.id)}
                    className={`h-full inline-flex items-center gap-1 border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                      isActive
                        ? 'border-stone-900 text-stone-950 font-bold'
                        : 'border-transparent text-stone-600 hover:text-stone-900 hover:border-stone-300'
                    }`}
                  >
                    <span>{navItem.label}</span>
                    {navItem.id === 'comparator' && comparedCount > 0 && (
                      <span className="font-mono text-[11px] text-stone-900 tabular-nums">
                        ({comparedCount})
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>

            {/* Zona 3 (Escritorio): Utilidades esenciales */}
            <div className="hidden md:flex items-center gap-2 shrink-0">
              <button
                type="button"
                aria-pressed={easyReadMode}
                onClick={() => setEasyReadMode(prev => !prev)}
                title="Lectura fácil"
                className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer ${
                  easyReadMode
                    ? 'bg-amber-100 border-amber-400 text-amber-950 font-semibold'
                    : 'bg-white border-stone-300 text-stone-700 hover:bg-stone-50'
                }`}
              >
                <Eye className="w-3.5 h-3.5 text-stone-600 shrink-0" aria-hidden="true" />
                <span>Lectura fácil</span>
              </button>

              <PWAInstallButton />

              <button
                type="button"
                onClick={openSavedSearches}
                title="Búsquedas guardadas"
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-stone-300 bg-white text-stone-700 hover:bg-stone-50 transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
              >
                <Bookmark className="w-3.5 h-3.5 text-stone-600 shrink-0" aria-hidden="true" />
                <span>Guardadas</span>
                {savedSearchesCount > 0 && (
                  <span className="text-xs font-mono font-semibold text-stone-900 tabular-nums">
                    ({savedSearchesCount})
                  </span>
                )}
              </button>

              <button
                type="button"
                onClick={openGlossary}
                title="Glosario en lectura fácil"
                aria-label="Glosario en lectura fácil"
                className="p-2 text-stone-600 hover:text-stone-900 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer"
              >
                <BookOpen className="w-4 h-4" aria-hidden="true" />
              </button>

              <button
                type="button"
                onClick={() => setIsSourcesModalOpen(true)}
                title="Verificar fuentes oficiales"
                aria-label="Verificar fuentes oficiales"
                className="p-2 text-stone-600 hover:text-stone-900 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer"
              >
                <AlertCircle className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            {/* Zona 3 (Móvil): Botón compacto de menú para evitar desbordamiento horizontal (#4) */}
            <div className="flex md:hidden items-center gap-1.5 shrink-0">
              <button
                type="button"
                aria-expanded={isMobileMenuOpen}
                aria-controls="mobile-utilities-menu"
                onClick={() => setIsMobileMenuOpen(prev => !prev)}
                className="px-2.5 py-2 text-xs font-semibold rounded-lg border border-stone-300 bg-white text-stone-800 hover:bg-stone-50 flex items-center gap-1.5 cursor-pointer"
              >
                {isMobileMenuOpen ? (
                  <X className="w-4 h-4 shrink-0" aria-hidden="true" />
                ) : (
                  <Menu className="w-4 h-4 shrink-0" aria-hidden="true" />
                )}
                <span>Menú</span>
              </button>
            </div>
          </div>

          {/* Panel desplegable móvil con utilidades (Lectura fácil, Instalar iOS/PWA, Guardadas, Glosario, Fuentes) */}
          {isMobileMenuOpen && (
            <div
              id="mobile-utilities-menu"
              className="md:hidden py-3 border-t border-stone-200 flex flex-col gap-2 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  aria-pressed={easyReadMode}
                  onClick={() => {
                    setEasyReadMode(prev => !prev);
                    setIsMobileMenuOpen(false);
                  }}
                  className={`flex-1 min-w-[140px] px-3 py-2 font-medium rounded-lg border flex items-center justify-center gap-1.5 cursor-pointer ${
                    easyReadMode
                      ? 'bg-amber-100 border-amber-400 text-amber-950 font-semibold'
                      : 'bg-white border-stone-300 text-stone-800'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>Lectura fácil {easyReadMode ? '(Activa)' : ''}</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    openSavedSearches();
                  }}
                  className="flex-1 min-w-[140px] px-3 py-2 font-medium rounded-lg border border-stone-300 bg-white text-stone-800 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Bookmark className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>
                    Guardadas{savedSearchesCount > 0 ? ` (${savedSearchesCount})` : ''}
                  </span>
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    openGlossary();
                  }}
                  className="flex-1 min-w-[140px] px-3 py-2 font-medium rounded-lg border border-stone-300 bg-white text-stone-800 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>Glosario</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    setIsSourcesModalOpen(true);
                  }}
                  className="flex-1 min-w-[140px] px-3 py-2 font-medium rounded-lg border border-stone-300 bg-white text-stone-800 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>Verificar fuentes</span>
                </button>
              </div>

              <div className="flex items-center justify-start pt-0.5">
                <PWAInstallButton />
              </div>
            </div>
          )}

          {/* Barra móvil compacta para pestañas principales */}
          <nav aria-label="Navegación móvil" className="md:hidden flex items-center justify-around border-t border-stone-100 text-xs font-semibold">
            {[
              { id: 'search', label: 'Búsqueda' },
              { id: 'map', label: 'Mapa' },
              { id: 'comparator', label: 'Comparador' }
            ].map((navItem) => {
              const isActive = activeTab === navItem.id;
              return (
                <button
                  key={navItem.id}
                  type="button"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={() => setActiveTab(navItem.id)}
                  className={`flex-1 py-2 text-center border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                    isActive
                      ? 'border-stone-900 text-stone-950 font-bold'
                      : 'border-transparent text-stone-600 hover:text-stone-900'
                  }`}
                >
                  <span>{navItem.label}</span>
                  {navItem.id === 'comparator' && comparedCount > 0 && (
                    <span className="font-mono text-[11px] text-stone-900 tabular-nums ml-1">
                      ({comparedCount})
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Modal interno de verificación de fuentes y reporte de discrepancias */}
      {isSourcesModalOpen && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="sources-verification-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsSourcesModalOpen(false);
          }}
        >
          <div
            ref={sourcesModalRef}
            tabIndex={-1}
            className="bg-white rounded-2xl max-w-xl w-full border border-stone-200 shadow-xl overflow-hidden my-8"
          >
            <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-700" aria-hidden="true" />
                <h2 id="sources-verification-title" className="text-base font-bold text-stone-900">
                  Verificación de fuentes y reporte de discrepancias
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setIsSourcesModalOpen(false)}
                aria-label="Cerrar modal"
                className="p-1.5 text-stone-500 hover:text-stone-800 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs text-stone-700 leading-relaxed">
              <p>
                Todos los datos de centros y servicios proceden exclusivamente de los tres registros públicos abiertos de <strong>Atención Social</strong> descargados sin alterar su codificación original y contrastados por suma <strong>SHA-256</strong>
                {snapshotDate ? ` (captura vigente: ${snapshotDate})` : ''}:
              </p>

              <ul className="space-y-2 bg-stone-50 p-3.5 rounded-xl border border-stone-200">
                <li>
                  <a
                    href="https://datos.madrid.es/dataset/212774-0-atencion-social"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-stone-900 underline inline-flex items-center gap-1 hover:text-stone-700"
                  >
                    <span>Ayuntamiento de Madrid · Catálogo de Centros de Atención Social (212774-0)</span>
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                  </a>
                </li>
                <li>
                  <a
                    href="https://datos.comunidad.madrid/dataset/atencion_social_registro_centros"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-stone-900 underline inline-flex items-center gap-1 hover:text-stone-700"
                  >
                    <span>Comunidad de Madrid · Registro General de Centros de Atención Social</span>
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                  </a>
                </li>
                <li>
                  <a
                    href="https://datos.comunidad.madrid/dataset/atencion_social_registro_servicios"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-stone-900 underline inline-flex items-center gap-1 hover:text-stone-700"
                  >
                    <span>Comunidad de Madrid · Registro General de Servicios de Atención Social</span>
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                  </a>
                </li>
              </ul>

              <p className="text-stone-600">
                Si detecta un teléfono o dirección desactualizados, puede verificarlo en el portal origen o revisar la auditoría automática de descargas y huellas SHA-256. El motor no modifica datos administrativos manualmente en la aplicación.
              </p>
            </div>

            <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-between text-xs">
              {onOpenWhatChanged ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsSourcesModalOpen(false);
                    onOpenWhatChanged();
                  }}
                  className="font-semibold text-stone-900 underline hover:text-stone-700 cursor-pointer"
                >
                  Ver auditoría de snapshots y SHA-256
                </button>
              ) : <span />}
              <button
                type="button"
                onClick={() => setIsSourcesModalOpen(false)}
                className="px-4 py-1.5 bg-stone-900 text-white rounded-lg font-semibold hover:bg-stone-800 cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
