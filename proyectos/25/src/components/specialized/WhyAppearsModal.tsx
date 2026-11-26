/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Modal «¿Por qué aparece este centro?»
 * Explicabilidad completa, procedencia por atributo y matriz criterio por criterio (§14, §27.1, §71)
 */

import React, { useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { EvaluatedCentreResult } from '../../types/specialized';
import { 
  X, 
  CheckCircle2, 
  HelpCircle, 
  AlertTriangle, 
  ExternalLink, 
  Building2
} from 'lucide-react';

interface WhyAppearsModalProps {
  item: EvaluatedCentreResult | null;
  onClose: () => void;
}

export const WhyAppearsModal: React.FC<WhyAppearsModalProps> = ({ item, onClose }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, !!item);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!item) return null;

  const { centre, match_assessment, evidence_level, evidence_sublevel, combination_details, criterion_matrix } = item;

  const hasProfileCriterion = criterion_matrix.some(c => c.criterion_id.startsWith('profile.'));

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="why-appears-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        ref={modalRef}
        className="bg-white rounded-2xl max-w-3xl w-full border border-stone-200 shadow-xl overflow-hidden my-8 max-h-[90vh] flex flex-col"
        tabIndex={-1}
      >
        {/* Cabecera del modal */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-start justify-between gap-4 bg-stone-50">
          <div>
            <div className="text-xs uppercase tracking-wider font-mono font-bold text-stone-500">
              Auditoría y Procedencia de Datos Oficiales · {centre.centre_id}
            </div>
            <h2 id="why-appears-modal-title" className="text-lg font-bold text-stone-900 mt-0.5">
              ¿Por qué aparece este centro?
            </h2>
            <div className="text-xs text-stone-600 mt-1">
              {centre.official_name} · {centre.municipality}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="p-1.5 text-stone-500 hover:text-stone-800 rounded-lg hover:bg-stone-200/50 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Contenido desplazable */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs text-stone-700">
          {/* 1. Nivel de Evidencia y Razonamiento Literal (§27.1) */}
          <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/70 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold text-stone-900 text-sm">
                Nivel de evidencia asignado:{' '}
                <span className="font-mono">
                  {evidence_sublevel === 'A2_entity' ? 'A2 (entidad titular)' : evidence_level}
                </span>
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-stone-200 text-stone-800">
                {evidence_level === 'A1' && 'Especialización y apoyo publicados'}
                {evidence_level === 'A2' && evidence_sublevel === 'A2_entity' && 'Lo declara la entidad titular; confirmar en este centro'}
                {evidence_level === 'A2' && evidence_sublevel !== 'A2_entity' && 'Especialización publicada; confirme el apoyo'}
                {evidence_level === 'B1' && 'Servicios relacionados revisados'}
                {evidence_level === 'B2' && 'Posible recurso; requiere confirmación'}
                {evidence_level === 'C' && (hasProfileCriterion ? 'Orientación general (sin especialización publicada)' : 'Catálogo oficial autorizado')}
              </span>
            </div>

            {centre.allowed_life_stages.length === 0 && (
              <div className="px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-950 text-[11px] font-medium">
                Edad o etapa vital: no consta en el registro oficial para este centro; confirmar directamente con la entidad si atiende su tramo de edad.
              </div>
            )}

            <div>
              <div className="font-semibold text-stone-800 mb-1">Motivos por los que se incluye en los resultados:</div>
              <ul className="list-disc list-inside space-y-1 text-stone-700 pl-1">
                {match_assessment.because.map((r: string, i: number) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>

            {/* Qué NO confirma este resultado (§27.1, §72) */}
            <div className="pt-2 border-t border-stone-200/60">
              <div className="font-semibold text-amber-900 mb-1 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                <span>Qué NO confirma este buscador (Verificaciones pendientes):</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-stone-600 pl-1">
                {match_assessment.does_not_confirm.map((d: string, i: number) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* 2. Desglose de combinación de apoyos en esta sede (§82.4) */}
          {combination_details.length > 0 && (
            <div>
              <h3 className="font-bold text-stone-900 mb-2 flex items-center gap-1.5 text-sm">
                <Building2 className="w-4 h-4 text-stone-600" />
                <span>Comprobación de apoyos en esta sede física ({centre.centre_id})</span>
              </h3>
              <div className="border border-stone-200 rounded-lg overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-stone-100 text-stone-700 font-semibold border-b border-stone-200">
                      <th className="p-2.5">Apoyo solicitado</th>
                      <th className="p-2.5">Estado en esta sede</th>
                      <th className="p-2.5">Fecha comprobación</th>
                      <th className="p-2.5">Fuente</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {combination_details.map((cd, i) => (
                      <tr key={i} className="hover:bg-stone-50/50">
                        <td className="p-2.5 font-medium text-stone-900">{cd.support_label}</td>
                        <td className="p-2.5">
                          {cd.status === 'confirmed' ? (
                            <span className="text-emerald-700 font-semibold flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Confirmado en sede</span>
                            </span>
                          ) : (
                            <span className="text-amber-700 font-medium flex items-center gap-1">
                              <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
                              <span>No consta expresamente</span>
                            </span>
                          )}
                        </td>
                        <td className="p-2.5 font-mono text-stone-500">{cd.checked_at}</td>
                        <td className="p-2.5 text-stone-600">
                          {centre.centre_id.startsWith('MAD-PK')
                            ? 'datos.madrid.es'
                            : centre.centre_id.startsWith('CAM-SRV-')
                            ? centre.provenance_records.some(p => p.source_dataset.includes('datos.madrid.es'))
                              ? 'CAM Servicios / datos.madrid.es'
                              : 'CAM Servicios'
                            : centre.provenance_records.some(p => p.source_dataset.includes('datos.madrid.es'))
                            ? 'CAM Centros / datos.madrid.es'
                            : 'Registro oficial CAM'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 3. Matriz de Explicación Criterio por Criterio (§71) */}
          <div>
            <h3 className="font-bold text-stone-900 mb-2 text-sm">
              Matriz de adecuación criterio por criterio
            </h3>
            <div className="border border-stone-200 rounded-lg overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-stone-100 text-stone-700 font-semibold border-b border-stone-200">
                    <th className="p-2.5">Criterio evaluado</th>
                    <th className="p-2.5">Estado del recurso</th>
                    <th className="p-2.5">Detalle o comprobación</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {criterion_matrix.map((cm, i) => (
                    <tr key={i} className="hover:bg-stone-50/50">
                      <td className="p-2.5 font-medium text-stone-900">{cm.criterion_label}</td>
                      <td className="p-2.5">
                        {cm.status === 'confirmed' && (
                          <span className="text-emerald-700 font-semibold">Confirmado</span>
                        )}
                        {cm.status === 'not_stated' && (
                          <span className="text-stone-500 font-medium">No consta</span>
                        )}
                        {cm.status === 'calculated' && (
                          <span className="text-sky-700 font-semibold">Calculado por GIS</span>
                        )}
                        {cm.status === 'confirm_required' && (
                          <span className="text-amber-700 font-semibold">Debe confirmarse</span>
                        )}
                        {cm.status === 'incompatible' && (
                          <span className="text-rose-700 font-bold">Incompatible</span>
                        )}
                      </td>
                      <td className="p-2.5 text-stone-600">
                        {cm.note || cm.source_fragment || 'Verificado con el catálogo oficial.'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 4. Tabla de Procedencia por Atributo (§14) */}
          <div>
            <h3 className="font-bold text-stone-900 mb-2 text-sm flex items-center justify-between">
              <span>Procedencia por atributo y trazabilidad institucional</span>
              <span className="text-[11px] font-normal text-stone-500">Fuentes: registros públicos oficiales</span>
            </h3>
            <div className="border border-stone-200 rounded-lg overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-stone-100 text-stone-700 font-semibold border-b border-stone-200 text-[11px]">
                    <th className="p-2">Atributo</th>
                    <th className="p-2">Valor oficial</th>
                    <th className="p-2">Fuente de datos</th>
                    <th className="p-2">Método</th>
                    <th className="p-2">Revisor</th>
                    <th className="p-2">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 text-[11px]">
                  {centre.provenance_records.map((prov, i) => (
                    <tr key={i} className="hover:bg-stone-50/50">
                      <td className="p-2 font-mono font-medium text-stone-900">{prov.attribute_name}</td>
                      <td className="p-2 text-stone-800 font-medium">{prov.value}</td>
                      <td className="p-2 text-stone-600">
                        <a 
                          href={prov.source_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="hover:text-stone-900 underline inline-flex items-center gap-1"
                        >
                          <span>{prov.source_dataset}</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </td>
                      <td className="p-2 font-mono text-stone-500">{prov.extraction_method}</td>
                      <td className="p-2 text-stone-600">{prov.reviewer} ({prov.reviewer_role})</td>
                      <td className="p-2 font-mono text-stone-500">{prov.retrieved_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Pie del modal */}
        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-between">
          <div className="text-[11px] text-stone-500">
            Última revisión técnica: <span className="font-mono">{centre.last_checked}</span> · DATAMAD 2026
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-stone-900 text-white rounded-lg hover:bg-stone-800 text-xs font-semibold transition-colors cursor-pointer"
          >
            Cerrar ficha de auditoría
          </button>
        </div>
      </div>
    </div>
  );
};
