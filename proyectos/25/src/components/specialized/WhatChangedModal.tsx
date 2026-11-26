/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Función «Qué ha cambiado»
 * Detección de cambios reales entre snapshots del registro oficial (§84, §110)
 */

import React, { useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { SNAPSHOT_DIFFERENCES } from '../../data/snapshotDiffsData';
import { DynamicIngestionState } from '../../utils/liveSnapshotParser';
import {
  X,
  History,
  CheckCircle2
} from 'lucide-react';

interface WhatChangedModalProps {
  isOpen: boolean;
  onClose: () => void;
  dynamicState?: DynamicIngestionState | null;
  inline?: boolean;
}

export const WhatChangedModal: React.FC<WhatChangedModalProps> = ({
  isOpen,
  onClose,
  dynamicState,
  inline = false
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isOpen && !inline);

  React.useEffect(() => {
    if (!isOpen || inline) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, inline, onClose]);

  if (!isOpen) return null;

  const activeDiffs = dynamicState ? dynamicState.diffs : SNAPSHOT_DIFFERENCES;
  const formattedTimestamp = dynamicState?.timestamp
    ? new Date(dynamicState.timestamp).toLocaleString('es-ES')
    : 'Pendiente de lectura';

  const cardBody = (
    <div
      ref={modalRef}
      className={
        inline
          ? 'bg-white rounded-2xl w-full border border-stone-200 shadow-xs overflow-hidden flex flex-col'
          : 'bg-white rounded-2xl max-w-3xl w-full border border-stone-200 shadow-xl overflow-hidden my-8 max-h-[90vh] flex flex-col'
      }
      tabIndex={-1}
    >
      {/* Cabecera */}
      <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-stone-700" />
          <div>
            {inline ? (
              <h3 id="what-changed-modal-title" className="text-base font-bold text-stone-900">
                ¿Qué ha cambiado entre versiones del registro oficial?
              </h3>
            ) : (
              <h2 id="what-changed-modal-title" className="text-base font-bold text-stone-900">
                ¿Qué ha cambiado entre versiones del registro oficial?
              </h2>
            )}
            <div className="text-[11px] text-stone-500 font-mono">
              {dynamicState?.loaded ? (
                <span className="text-emerald-700 font-bold">
                  ✓ {dynamicState.load_source === 'preclassified_json'
                    ? 'Catálogo oficial pre-clasificado en caché offline'
                    : 'Evaluado en vivo desde 3 CSV oficiales'}{' '}
                  ({dynamicState.total_csv_records} filas registrales · {dynamicState.active_centres_count} recursos activos · {formattedTimestamp})
                </span>
              ) : dynamicState?.used_fallback || dynamicState?.error ? (
                <span className="text-amber-800 font-bold">
                  Catálogo de reserva activo ({dynamicState.active_centres_count} recursos): {dynamicState.error || 'snapshot oficial no accesible'}
                </span>
              ) : (
                'Cargando verificación SHA-256 de snapshots oficiales...'
              )}
            </div>
          </div>
        </div>
        {!inline && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="p-1.5 text-stone-500 hover:text-stone-800 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Contenido con trazabilidad SHA-256 real por fuente */}
      <div className="p-6 overflow-y-auto space-y-4 text-xs">
        <div className="p-3 bg-stone-100/70 border border-stone-200 rounded-lg text-stone-700 leading-relaxed">
          <strong>Comparativa real automatizada:</strong> El script de ingesta compara cada descarga oficial (Ayuntamiento de Madrid y Comunidad de Madrid Centros/Servicios) frente al snapshot inmediatamente anterior y verifica las firmas criptográficas SHA-256 exactas en disco.
        </div>

        {dynamicState?.sources && dynamicState.sources.length > 0 && (
          <div className="border border-stone-200 rounded-xl overflow-x-auto">
            <table className="w-full text-left border-collapse text-[11px]">
              <thead>
                <tr className="bg-stone-100 text-stone-700 font-bold border-b border-stone-200">
                  <th className="p-2.5">Fuente oficial CSV</th>
                  <th className="p-2.5">Registros</th>
                  <th className="p-2.5">Huella SHA-256 verificada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {dynamicState.sources.map((src) => (
                  <tr key={src.source_id}>
                    <td className="p-2.5 font-medium text-stone-900">{src.source_name || src.source_id}</td>
                    <td className="p-2.5 font-mono text-stone-700">{src.extracted_records_count}</td>
                    <td className="p-2.5 font-mono text-stone-600 break-all">{src.sha256_hash.slice(0, 24)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeDiffs.length === 0 ? (
          <div className="p-6 rounded-xl border border-emerald-200 bg-emerald-50/50 text-center space-y-2">
            <CheckCircle2 className="w-6 h-6 text-emerald-700 mx-auto" />
            <div className="text-sm font-bold text-stone-900">
              Sin diferencias respecto al snapshot oficial anterior
            </div>
            <p className="text-stone-600 max-w-lg mx-auto leading-relaxed">
              Las firmas SHA-256 de los ficheros CSV descargados coinciden con la captura previa. No se muestran cambios ficticios ni manipulados; cualquier alta, baja o cambio futuro de teléfono o dirección aparecerá aquí automáticamente.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeDiffs.map((diff) => {
              let badgeColor = 'bg-stone-100 text-stone-800 border-stone-200';
              if (diff.category === 'alta') {
                badgeColor = 'bg-emerald-50 text-emerald-900 border-emerald-200';
              } else if (diff.category === 'servicio') {
                badgeColor = 'bg-sky-50 text-sky-900 border-sky-200';
              } else if (diff.category === 'acceso') {
                badgeColor = 'bg-teal-50 text-teal-900 border-teal-200';
              } else if (diff.category === 'vigencia') {
                badgeColor = 'bg-amber-50 text-amber-900 border-amber-200';
              } else if (diff.category === 'incidencia_fuente' || diff.category === 'baja') {
                badgeColor = 'bg-rose-50 text-rose-900 border-rose-200';
              }

              return (
                <div
                  key={diff.change_id}
                  className="p-4 rounded-xl border border-stone-200 bg-white hover:border-stone-300 transition-colors space-y-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${badgeColor}`}>
                        {diff.category}
                      </span>
                      {inline ? (
                        <h4 className="font-bold text-stone-900 text-sm">
                          {diff.centre_name}
                        </h4>
                      ) : (
                        <h3 className="font-bold text-stone-900 text-sm">
                          {diff.centre_name}
                        </h3>
                      )}
                    </div>
                    <span className="font-mono text-[11px] text-stone-500 shrink-0">
                      {diff.change_id}
                    </span>
                  </div>

                  <p className="text-stone-700 leading-relaxed">
                    {diff.detail}
                  </p>

                  <div className="pt-2 border-t border-stone-100 flex items-center justify-between text-[11px] text-stone-500">
                    <div>
                      <strong>Motivo registral:</strong> {diff.reason}
                    </div>
                    <div className="font-mono">
                      {diff.previous_snapshot} ➔ {diff.current_snapshot}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pie */}
      <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-between text-xs">
        <span className="text-stone-500 font-mono">
          {activeDiffs.length} cambios calculados | SHA-256 principal: {dynamicState?.sha256_hash ? `${dynamicState.sha256_hash.slice(0, 16)}...` : 'Pendiente'}
        </span>
        {!inline && (
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors cursor-pointer"
          >
            Cerrar
          </button>
        )}
      </div>
    </div>
  );

  if (inline) {
    return cardBody;
  }

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="what-changed-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {cardBody}
    </div>
  );
};
