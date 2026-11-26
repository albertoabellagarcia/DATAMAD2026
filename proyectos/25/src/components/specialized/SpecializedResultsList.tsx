/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Results List Container
 * Resultados agrupados por fuerza de evidencia A1/A2, B1/B2 y C (§37.1)
 * Manejo estricto de incertidumbre y cero resultados sin relajar en silencio (§38).
 */

import React, { useState, useEffect } from 'react';
import { EvaluatedCentreResult, SearchQueryState } from '../../types/specialized';
import { SpecializedCentreCard } from './SpecializedCentreCard';
import { 
  AlertCircle, 
  RotateCcw, 
  ChevronDown, 
  ChevronUp, 
  Share2, 
  Download, 
  FileSpreadsheet, 
  Check,
  ShieldCheck,
  Layers,
  Compass
} from 'lucide-react';

interface ResultsListProps {
  results: EvaluatedCentreResult[];
  incompatibleResults: EvaluatedCentreResult[];
  query: SearchQueryState;
  onWhyAppears: (item: EvaluatedCentreResult) => void;
  onPrepareContact: (item: EvaluatedCentreResult) => void;
  comparedIds: string[];
  onToggleCompare: (centreId: string) => void;
  onResetFilters: () => void;
  easyReadMode: boolean;
}

/**
 * Neutraliza inyección de fórmulas en hojas de cálculo (Excel / LibreOffice / Sheets)
 * prefijando valores que comiencen por =, +, -, @, tabulación o retorno de carro.
 */
export function escapeCsvCell(value: unknown): string {
  const raw = value === null || value === undefined ? '' : String(value);
  const safe = /^[=+\-@\t\r]/.test(raw) ? `'${raw}` : raw;
  return `"${safe.replace(/"/g, '""')}"`;
}

export function buildResultsCsv(results: EvaluatedCentreResult[]): string {
  const headers = [
    'ID Centro',
    'Nombre Oficial',
    'Municipio',
    'Distrito',
    'Dirección',
    'Teléfono',
    'Correo Electrónico',
    'Web Oficial',
    'Plazas Autorizadas',
    'Coordenadas (Lat, Lon)',
    'Nivel Evidencia',
    'Subnivel Evidencia',
    'Adecuación',
    'Distancia (km)',
    'Estimación Transporte Público',
    'Titularidad',
    'Tipo Centro',
    'Subtipo',
    'Apoyos Confirmados',
    'Trazabilidad Registral',
    'URLs Oficiales'
  ];

  const rows = results.map(r => [
    escapeCsvCell(r.centre.centre_id),
    escapeCsvCell(r.centre.official_name),
    escapeCsvCell(r.centre.municipality),
    escapeCsvCell(r.centre.district || ''),
    escapeCsvCell(r.centre.address),
    escapeCsvCell(r.centre.phone || ''),
    escapeCsvCell(r.centre.email || ''),
    escapeCsvCell(r.centre.website || ''),
    escapeCsvCell(r.centre.availability.authorised_places ?? 'N/D'),
    escapeCsvCell(r.centre.coordinates ? r.centre.coordinates.join(', ') : 'Sin coordenadas'),
    escapeCsvCell(r.evidence_level),
    escapeCsvCell(r.evidence_sublevel),
    escapeCsvCell(r.suitability),
    escapeCsvCell(r.distance_km !== null ? r.distance_km.toFixed(1) : 'Sin coords'),
    escapeCsvCell(r.transit_time_label || 'Sin estimación'),
    escapeCsvCell(r.centre.public_private_status),
    escapeCsvCell(r.centre.centre_type),
    escapeCsvCell(r.centre.subtype || ''),
    escapeCsvCell(r.centre.supports.join('; ')),
    escapeCsvCell(r.centre.provenance_records.map(p => `${p.attribute_name}:${p.source_dataset}`).join('; ')),
    escapeCsvCell(Array.from(new Set(r.centre.provenance_records.map(p => p.source_url).filter(Boolean))).join(' | '))
  ]);

  return '\uFEFF' + [headers.map(escapeCsvCell).join(','), ...rows.map(row => row.join(','))].join('\n');
}

export function buildResultsJsonPayload(results: EvaluatedCentreResult[], query: SearchQueryState) {
  return {
    exported_at: new Date().toISOString(),
    taxonomy_version: '1.9.0',
    total_results: results.length,
    query: {
      profile: query.profile,
      functional_needs: query.functional_needs,
      support_types: query.support_types,
      support_combination_mode: query.support_combination_mode,
      life_stage: query.life_stage,
      municipality: query.municipality,
      radius_km: query.radius_km,
      network_preference: query.network_preference,
      accessibility_needs: query.accessibility_needs,
      location_mode: query.location_mode
    },
    results
  };
}

export const SpecializedResultsList: React.FC<ResultsListProps> = ({
  results,
  incompatibleResults,
  query,
  onWhyAppears,
  onPrepareContact,
  comparedIds,
  onToggleCompare,
  onResetFilters,
  easyReadMode
}) => {
  const [showIncompatibles, setShowIncompatibles] = useState(false);
  const [showGeneralOrientation, setShowGeneralOrientation] = useState(false);
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const [displayLimit, setDisplayLimit] = useState(40);

  useEffect(() => {
    setDisplayLimit(40);
  }, [results]);

  useEffect(() => {
    setShowGeneralOrientation(false);
  }, [query.profile]);

  const allGroupA = results.filter(r => r.evidence_level === 'A1' || r.evidence_level === 'A2');
  const allGroupB = results.filter(r => r.evidence_level === 'B1' || r.evidence_level === 'B2');
  const allGroupC = results.filter(r => r.evidence_level === 'C');

  const totalGroupA = allGroupA.length;
  const totalGroupB = allGroupB.length;
  const totalGroupC = allGroupC.length;
  const matchedCount = totalGroupA + totalGroupB;
  const hasActiveProfile = query.profile !== null;
  const collapseGroupC = hasActiveProfile && matchedCount > 0;

  const displayedPool = collapseGroupC && !showGeneralOrientation ? [...allGroupA, ...allGroupB] : results;
  const visibleSlice = displayedPool.slice(0, displayLimit);
  const groupA = visibleSlice.filter(r => r.evidence_level === 'A1' || r.evidence_level === 'A2');
  const groupB = visibleSlice.filter(r => r.evidence_level === 'B1' || r.evidence_level === 'B2');
  const groupC = visibleSlice.filter(r => r.evidence_level === 'C');

  // Copiar enlace de reproducibilidad con fallback seguro en iframes restringidos
  const handleCopyShareLink = async () => {
    if (typeof window === 'undefined') return;
    const url = window.location.href;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url);
      } else {
        const ta = document.createElement('textarea');
        ta.value = url;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        if (!ok) throw new Error('copy_failed');
      }
      setCopyStatus('copied');
    } catch {
      setCopyStatus('error');
    } finally {
      setTimeout(() => setCopyStatus('idle'), 2800);
    }
  };

  // Descarga CSV de resultados con neutralización de fórmulas y trazabilidad completa
  const handleExportCSV = () => {
    const csvStr = buildResultsCsv(displayedPool);
    const blob = new Blob([csvStr], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `madrid_apoyo_especializado_resultados_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Descarga JSON estructurado con metadatos de consulta (sin coordenadas GPS personales)
  const handleExportJSON = () => {
    const payload = buildResultsJsonPayload(displayedPool, query);
    const jsonStr = JSON.stringify(payload, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `madrid_apoyo_especializado_resultados_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Si no hay resultados (§38: Diseño para incertidumbre y ausencia de resultados)
  if (results.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-stone-200 p-8 shadow-xs text-center max-w-xl mx-auto my-8 space-y-4">
        <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-700">
          <AlertCircle className="w-6 h-6" aria-hidden="true" />
        </div>
        <h2 className="text-base font-bold text-stone-900">
          No consta especialización en las fuentes consultadas
        </h2>
        <p className="text-xs text-stone-600 leading-relaxed max-w-md mx-auto">
          Ningún centro autorizado de la Comunidad de Madrid cumple simultáneamente todos los criterios seleccionados con los filtros actuales.
        </p>

        <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-left text-xs space-y-2 text-stone-700">
          <div className="font-bold text-stone-800">Alternativas recomendadas:</div>
          <ul className="list-disc list-inside space-y-1 text-stone-600 pl-1">
            {query.radius_km < 80 && (
              <li>Ampliar el radio geográfico de búsqueda (actualmente en {query.radius_km} km).</li>
            )}
            {query.support_combination_mode === 'all_supports_same_centre' && (
              <li>Cambiar el modo de combinación a «Cualquier apoyo» para permitir servicios coordinados en distintas sedes.</li>
            )}
            <li>Retirar el filtro de titularidad para incluir centros privados autorizados o de la red pública.</li>
          </ul>
        </div>

        <button
          type="button"
          onClick={onResetFilters}
          className="px-4 py-2 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Restablecer criterios de búsqueda</span>
        </button>
      </div>
    );
  }

  return (
    <div id="results-list-anchor" className="space-y-6 scroll-mt-28">
      {/* Barra de cabecera de la lista con exportaciones y compartir */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-stone-200 pb-3">
        <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
          <h2 className={`${easyReadMode ? 'text-lg' : 'text-base'} font-bold text-stone-900`}>
            {easyReadMode ? 'Centros encontrados para tu búsqueda' : 'Resultados de la búsqueda'}
          </h2>
          {collapseGroupC ? (
            <>
              <span className="text-xs font-mono font-semibold text-stone-800 tabular-nums">
                · {matchedCount} {matchedCount === 1 ? 'recurso relacionado' : 'recursos relacionados'}
              </span>
              <span className="text-[11px] text-stone-500">
                ({totalGroupA} con especialización publicada · {totalGroupB} relacionados)
              </span>
            </>
          ) : (
            <span className="text-xs font-mono font-semibold text-stone-600 tabular-nums">
              · {results.length} {results.length === 1 ? 'recurso' : 'recursos'}
            </span>
          )}
        </div>

        {/* Acciones de exportación y enlace compartible */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            type="button"
            onClick={handleCopyShareLink}
            className="px-2.5 py-1.5 bg-white border border-stone-300 hover:bg-stone-50 text-stone-800 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Copiar enlace URL con todos los criterios de esta búsqueda"
            aria-label={
              copyStatus === 'copied'
                ? 'Enlace copiado al portapapeles'
                : copyStatus === 'error'
                ? 'Copie la URL de la barra del navegador'
                : 'Compartir búsqueda: copiar enlace URL con los criterios actuales'
            }
          >
            {copyStatus === 'copied' ? (
              <Check className="w-3.5 h-3.5 text-emerald-700" aria-hidden="true" />
            ) : (
              <Share2 className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
            )}
            <span>
              {copyStatus === 'copied'
                ? 'Enlace copiado'
                : copyStatus === 'error'
                ? 'Copie la URL de la barra'
                : 'Compartir búsqueda'}
            </span>
          </button>

          <button
            type="button"
            onClick={handleExportCSV}
            className="px-2.5 py-1.5 bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 rounded-lg font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Exportar resultados en formato CSV con fuentes y procedencia"
            aria-label="Exportar resultados en formato CSV con fuentes y procedencia"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
            <span>CSV</span>
          </button>

          <button
            type="button"
            onClick={handleExportJSON}
            className="px-2.5 py-1.5 bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 rounded-lg font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Exportar estructurado completo en JSON"
            aria-label="Exportar estructurado completo en JSON"
          >
            <Download className="w-3.5 h-3.5 text-stone-600" aria-hidden="true" />
            <span>JSON</span>
          </button>

          <span className="sr-only" aria-live="polite">
            {copyStatus === 'copied'
              ? 'Enlace de búsqueda copiado al portapapeles.'
              : copyStatus === 'error'
              ? 'No se pudo copiar automáticamente; use la dirección del navegador.'
              : ''}
          </span>
        </div>
      </div>

      <div className="space-y-8">
        {/* Grupo A: Especialización publicada (A1 y A2) */}
        {groupA.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center justify-between border-b border-emerald-200 pb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" aria-hidden="true" />
                <h3 className={`${easyReadMode ? 'text-base' : 'text-sm'} font-bold text-stone-900`}>
                  {easyReadMode ? 'Centros especializados' : 'Especialización Publicada'} ({groupA.length < totalGroupA ? `${groupA.length} mostrados de ${totalGroupA}` : totalGroupA})
                </h3>
              </div>
              <span className="text-[11px] text-stone-500">
                {easyReadMode ? 'Confirman este apoyo o perfil' : 'Mención en registro oficial'}
              </span>
            </div>

            <div className="space-y-4">
              {groupA.map((item) => (
                <SpecializedCentreCard
                  key={item.centre.centre_id}
                  item={item}
                  onWhyAppears={onWhyAppears}
                  onPrepareContact={onPrepareContact}
                  isCompared={comparedIds.includes(item.centre.centre_id)}
                  onToggleCompare={onToggleCompare}
                  easyReadMode={easyReadMode}
                />
              ))}
            </div>
          </section>
        )}

        {/* Grupo B: Servicios relacionados (B1 y B2) */}
        {groupB.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center justify-between border-b border-sky-200 pb-2">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-700 shrink-0" aria-hidden="true" />
                <h3 className={`${easyReadMode ? 'text-base' : 'text-sm'} font-bold text-stone-900`}>
                  {easyReadMode ? 'Centros con servicios parecidos' : 'Servicios Relacionados'} ({groupB.length < totalGroupB ? `${groupB.length} mostrados de ${totalGroupB}` : totalGroupB})
                </h3>
              </div>
              <span className="text-[11px] text-stone-500">
                {easyReadMode ? 'Conviene preguntar antes por teléfono' : 'Recursos del sector relacionado'}
              </span>
            </div>

            <div className="space-y-4">
              {groupB.map((item) => (
                <SpecializedCentreCard
                  key={item.centre.centre_id}
                  item={item}
                  onWhyAppears={onWhyAppears}
                  onPrepareContact={onPrepareContact}
                  isCompared={comparedIds.includes(item.centre.centre_id)}
                  onToggleCompare={onToggleCompare}
                  easyReadMode={easyReadMode}
                />
              ))}
            </div>
          </section>
        )}

        {/* Grupo C: Orientación general (plegado bajo demanda cuando hay perfil activo con recursos A/B) */}
        {totalGroupC > 0 && (
          collapseGroupC ? (
            <section className="space-y-4 pt-2 border-t border-stone-200">
              <button
                type="button"
                aria-expanded={showGeneralOrientation}
                onClick={() => setShowGeneralOrientation(prev => !prev)}
                className="text-xs font-semibold text-stone-700 hover:text-stone-950 flex items-center justify-between w-full p-3.5 rounded-xl bg-stone-50 border border-stone-200 hover:bg-stone-100/70 transition-colors cursor-pointer text-left gap-3"
              >
                <span className="flex items-center gap-2 min-w-0">
                  <Compass className="w-4 h-4 text-stone-600 shrink-0" aria-hidden="true" />
                  <span>
                    {showGeneralOrientation
                      ? `Ocultar catálogo general de apoyo social (Nivel C · ${totalGroupC} recursos sin especialización publicada)`
                      : `Ver también catálogo general de apoyo social (Nivel C · ${totalGroupC} recursos sin especialización publicada para este perfil)`}
                  </span>
                </span>
                {showGeneralOrientation
                  ? <ChevronUp className="w-4 h-4 shrink-0 text-stone-600" aria-hidden="true" />
                  : <ChevronDown className="w-4 h-4 shrink-0 text-stone-600" aria-hidden="true" />}
              </button>

              {showGeneralOrientation && groupC.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-stone-200 pb-2">
                    <div className="flex items-center gap-2">
                      <Compass className="w-4 h-4 text-stone-600 shrink-0" aria-hidden="true" />
                      <h3 className={`${easyReadMode ? 'text-base' : 'text-sm'} font-bold text-stone-900`}>
                        {easyReadMode ? 'Otros centros de atención social' : 'Orientación General'} ({groupC.length < totalGroupC ? `${groupC.length} mostrados de ${totalGroupC}` : totalGroupC})
                      </h3>
                    </div>
                    <span className="text-[11px] text-stone-500">
                      {easyReadMode ? 'Recursos generales para consultar' : 'Sin especialización publicada; confirmar por teléfono'}
                    </span>
                  </div>

                  <div className="space-y-4">
                    {groupC.map((item) => (
                      <SpecializedCentreCard
                        key={item.centre.centre_id}
                        item={item}
                        onWhyAppears={onWhyAppears}
                        onPrepareContact={onPrepareContact}
                        isCompared={comparedIds.includes(item.centre.centre_id)}
                        onToggleCompare={onToggleCompare}
                        easyReadMode={easyReadMode}
                      />
                    ))}
                  </div>
                </div>
              )}
            </section>
          ) : groupC.length > 0 ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between border-b border-stone-200 pb-2">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-stone-600 shrink-0" aria-hidden="true" />
                  <h3 className={`${easyReadMode ? 'text-base' : 'text-sm'} font-bold text-stone-900`}>
                    {hasActiveProfile
                      ? (easyReadMode ? 'Otros centros de atención social' : 'Orientación General')
                      : (easyReadMode ? 'Todos los centros oficiales' : 'Catálogo Oficial Autorizado')}{' '}
                    ({groupC.length < totalGroupC ? `${groupC.length} mostrados de ${totalGroupC}` : totalGroupC})
                  </h3>
                </div>
                <span className="text-[11px] text-stone-500">
                  {hasActiveProfile
                    ? (easyReadMode ? 'Recursos generales para consultar' : 'Sector asistencial compatible')
                    : 'Registro oficial de la Comunidad de Madrid y Ayuntamiento'}
                </span>
              </div>

              <div className="space-y-4">
                {groupC.map((item) => (
                  <SpecializedCentreCard
                    key={item.centre.centre_id}
                    item={item}
                    onWhyAppears={onWhyAppears}
                    onPrepareContact={onPrepareContact}
                    isCompared={comparedIds.includes(item.centre.centre_id)}
                    onToggleCompare={onToggleCompare}
                    easyReadMode={easyReadMode}
                  />
                ))}
              </div>
            </section>
          ) : null
        )}
      </div>

      {displayedPool.length > displayLimit && (
        <div className="flex flex-col items-center gap-2 pt-2">
          <div className="text-xs text-stone-500 font-mono tabular-nums">
            Mostrando {visibleSlice.length} de {displayedPool.length} recursos oficiales
          </div>
          <button
            type="button"
            onClick={() => setDisplayLimit(prev => prev + 40)}
            className="px-5 py-2 bg-white border border-stone-300 text-stone-900 rounded-lg text-xs font-semibold hover:bg-stone-50 transition-colors shadow-xs cursor-pointer"
          >
            Mostrar más recursos (+40)
          </button>
        </div>
      )}

      {/* 4. Sección de Centros Incompatibles Excluidos de la Lista Principal (§78) */}
      {incompatibleResults.length > 0 && (
        <div className="pt-6 border-t border-stone-200">
          <button
            type="button"
            aria-expanded={showIncompatibles}
            onClick={() => setShowIncompatibles(prev => !prev)}
            className="text-xs font-bold text-stone-700 hover:text-stone-900 flex items-center justify-between w-full p-3 rounded-lg bg-stone-100 border border-stone-200 cursor-pointer"
          >
            <span>
              Recursos excluidos por incompatibilidad de criterios ({incompatibleResults.length})
            </span>
            {showIncompatibles ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
          </button>

          {showIncompatibles && (
            <div className="space-y-3 mt-3">
              {incompatibleResults.map((item) => (
                <div key={item.centre.centre_id} className="opacity-75">
                  <SpecializedCentreCard
                    item={item}
                    onWhyAppears={onWhyAppears}
                    onPrepareContact={onPrepareContact}
                    isCompared={comparedIds.includes(item.centre.centre_id)}
                    onToggleCompare={onToggleCompare}
                    easyReadMode={easyReadMode}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
