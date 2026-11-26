/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Ficha para Preparar el Contacto
 * Documento imprimible con preguntas clave, vía de acceso y advertencias (§32.1, §81.1)
 */

import React, { useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { EvaluatedCentreResult } from '../../types/specialized';
import { 
  X, 
  Printer, 
  AlertCircle, 
  FileText
} from 'lucide-react';
import { LIFE_STAGES } from '../../data/specializedTaxonomy';
import { extractSpanishPhoneNumbers } from '../../utils/phoneUtils';

interface PrintableContactCardProps {
  item: EvaluatedCentreResult | null;
  onClose: () => void;
}

export const PrintableContactCardModal: React.FC<PrintableContactCardProps> = ({ item, onClose }) => {
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

  const { centre, match_assessment } = item;
  const today = new Date().toISOString().split('T')[0];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 printable-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="contact-card-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        ref={modalRef}
        className="bg-white rounded-2xl max-w-2xl w-full border border-stone-200 shadow-xl overflow-hidden my-8 max-h-[90vh] flex flex-col printable-modal-sheet"
        tabIndex={-1}
      >
        {/* Cabecera modal con botón Imprimir */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50 no-print">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-stone-700" />
            <h2 id="contact-card-modal-title" className="text-base font-bold text-stone-900">
              Ficha para Preparar el Contacto con el Centro
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="px-3.5 py-1.5 bg-stone-900 text-white rounded-lg hover:bg-stone-800 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Printer className="w-4 h-4" aria-hidden="true" />
              <span>Imprimir / Guardar PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar modal"
              className="p-1.5 text-stone-400 hover:text-stone-700 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Cuerpo de la ficha imprimible */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-stone-800 print:p-0 print:m-0">
          {/* Membrete institucional */}
          <div className="border-b border-stone-300 pb-3 flex items-start justify-between">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-stone-500">
                Madrid Apoyo Especializado v1.9 · DATAMAD 2026
              </div>
              <h2 className="text-lg font-bold text-stone-900 mt-1">
                {centre.official_name}
              </h2>
              <div className="text-stone-600 mt-0.5">
                {centre.subtype || centre.centre_type} · {centre.municipality}
              </div>
            </div>
            <div className="text-right text-[11px] text-stone-500 font-mono">
              Fecha de consulta: {today}
              <div>ID oficial: {centre.centre_id}</div>
            </div>
          </div>

          {/* Datos de contacto oficiales */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-stone-50 rounded-lg border border-stone-200">
            <div>
              <span className="font-semibold text-stone-600 block">Dirección oficial:</span>
              <span className="font-medium">
                {[
                  centre.address,
                  [centre.postal_code, centre.municipality].filter(Boolean).join(' ')
                ]
                  .filter(Boolean)
                  .join(', ')}
              </span>
              {item.distance_label && (
                <div className="text-[11px] text-stone-600 mt-1">
                  Distancia lineal orientativa: <strong>{item.distance_label}</strong>
                  {item.transit_time_label && (
                    <span> · <strong>{item.transit_time_label}</strong> (cálculo teórico aproximado)</span>
                  )}
                </div>
              )}
            </div>
            <div>
              <span className="font-semibold text-stone-600 block">Teléfono y web:</span>
              {(() => {
                const parsedPhones = extractSpanishPhoneNumbers(centre.phone || '');
                if (parsedPhones.validNumbers.length > 0) {
                  return (
                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 font-mono font-medium">
                      {parsedPhones.validNumbers.map((num, idx) => (
                        <a
                          key={num}
                          href={`tel:${num}`}
                          className="text-stone-900 underline decoration-stone-300 hover:text-stone-700"
                        >
                          {parsedPhones.formattedNumbers[idx]}
                        </a>
                      ))}
                    </div>
                  );
                }
                return (
                  <span className="font-medium">
                    {centre.phone ? `${centre.phone} (incompleto en registro)` : 'No publicado'}
                  </span>
                );
              })()}
              {centre.website && <div className="text-stone-600 truncate mt-0.5">{centre.website}</div>}
            </div>
          </div>

          {/* Bloque 1: Qué declara oficialmente */}
          <div>
            <h3 className="font-bold text-stone-900 uppercase tracking-wider text-[11px] mb-1.5">
              1. Qué declara oficialmente el centro en el registro
            </h3>
            <ul className="list-disc list-inside space-y-1 text-stone-700 pl-1">
              {match_assessment.because.map((b: string, i: number) => (
                <li key={i}>{b}</li>
              ))}
              <li>
                Titularidad y gestión: {centre.management_type} ({
                  centre.public_private_status === 'red_publica'
                    ? 'Pública directa'
                    : centre.public_private_status === 'concertado'
                    ? 'Plazas públicas concertadas'
                    : centre.public_private_status === 'no_especificado'
                    ? 'Titularidad no especificada en registro municipal'
                    : 'Privado autorizado'
                }).
              </li>
              <li>
                Etapas vitales autorizadas: {centre.allowed_life_stages.length > 0
                  ? centre.allowed_life_stages.map(s => LIFE_STAGES[s]?.label || s).join(', ')
                  : 'No consta en el registro oficial (confirmar con el centro)'}.
              </li>
            </ul>
          </div>

          {/* Bloque 2: Vía de acceso requerida */}
          <div className="p-3 bg-stone-100/70 border border-stone-200 rounded-lg">
            <h3 className="font-bold text-stone-900 uppercase tracking-wider text-[11px] mb-1">
              2. Procedimiento oficial de acceso o derivación
            </h3>
            <p className="text-stone-800 leading-relaxed font-medium">
              {centre.access_route.next_step_action}
            </p>
            <div className="mt-2 text-[11px] text-stone-600">
              Organismo competente: <strong>{centre.access_route.competent_body}</strong>
            </div>
          </div>

          {/* Bloque 3: Advertencia de vacantes y disponibilidad */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-950">
            <h3 className="font-bold uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-amber-700" />
              <span>3. Qué debe confirmarse antes de desplazarse</span>
            </h3>
            <ul className="list-disc list-inside space-y-0.5 text-stone-700 pl-1 text-[11px]">
              <li>
                <strong>Plazas disponibles:</strong>{' '}
                {typeof centre.availability.authorised_places === 'number'
                  ? `El centro cuenta con ${centre.availability.authorised_places} plazas autorizadas, pero este dato NO significa que existan plazas libres de ingreso inmediato.`
                  : 'El registro oficial no publica cupo de plazas autorizadas para este recurso; confirme la disponibilidad actual directamente.'}
              </li>
              <li>
                <strong>Adecuación al caso concreto:</strong> Confirme si el servicio específico requerido tiene disponibilidad horaria y equipo especializado disponible.
              </li>
              <li>
                <strong>Condiciones de admisión:</strong>{' '}
                {centre.resource_domain === 'healthcare'
                  ? 'Si es plaza concertada o sanitaria, requiere derivación del SERMAS o valoración clínica. Si es plaza privada, consulte tarifas vigentes.'
                  : 'Si es plaza pública o concertada, puede requerir resolución de PIA o valoración de Servicios Sociales. Si es plaza privada, consulte tarifas vigentes.'}
              </li>
            </ul>
          </div>

          {/* Bloque 4: Lista de preguntas recomendadas para hacer en la llamada */}
          <div>
            <h3 className="font-bold text-stone-900 uppercase tracking-wider text-[11px] mb-2">
              4. Preguntas recomendadas para la llamada o entrevista inicial
            </h3>
            <div className="space-y-1.5 text-stone-700">
              <label className="flex items-start gap-2">
                <input type="checkbox" className="mt-0.5" />
                <span>¿Tienen actualmente plazas libres en el servicio o existe lista de espera?</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="checkbox" className="mt-0.5" />
                <span>¿El acceso a la plaza que necesito es por concierto público (PIA / derivación médica) o privada?</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="checkbox" className="mt-0.5" />
                <span>¿Disponen de todos los apoyos de fisioterapia, logopedia y terapia ocupacional en esta misma sede o requieren acudir a otro centro?</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="checkbox" className="mt-0.5" />
                <span>¿Qué informes médicos o sociales debo aportar en la primera entrevista de valoración?</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="checkbox" className="mt-0.5" />
                <span>¿Disponen de servicio de transporte adaptado o comedor en el centro de día?</span>
              </label>
            </div>
          </div>

          {/* Notas para la familia */}
          <div className="border-t border-dashed border-stone-300 pt-3">
            <span className="font-semibold text-stone-600 block mb-1">Anotaciones de la conversación / Fecha de contacto:</span>
            <div className="h-16 border border-stone-200 rounded-lg bg-stone-50/50 p-2 text-stone-400">
              Escriba aquí el nombre de la persona de contacto, fecha y acuerdos...
            </div>
          </div>
        </div>

        {/* Pie modal */}
        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-between no-print">
          <span className="text-[11px] text-stone-500">
            Documento generado por Madrid Apoyo Especializado · Código abierto DATAMAD 2026
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold text-stone-700 hover:text-stone-900 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
