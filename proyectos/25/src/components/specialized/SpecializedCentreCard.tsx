/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Verified Centre Result Card (Simplified)
 * Disciplina Zero-Pill y diseño compacto y limpio (§14, §27, §42)
 */

import React, { useMemo } from 'react';
import { EvaluatedCentreResult } from '../../types/specialized';
import { auditCentreAgainstSnapshot } from '../../utils/specializedEngine';
import { extractSpanishPhoneNumbers } from '../../utils/phoneUtils';
import { 
  MapPin, 
  Phone, 
  ExternalLink, 
  Printer, 
  ArrowRight,
  Bus,
  ShieldCheck,
  AlertTriangle,
  Check,
  Layers,
  Compass
} from 'lucide-react';

interface CentreCardProps {
  item: EvaluatedCentreResult;
  onWhyAppears: (item: EvaluatedCentreResult) => void;
  onPrepareContact: (item: EvaluatedCentreResult) => void;
  isCompared: boolean;
  onToggleCompare: (centreId: string) => void;
  easyReadMode: boolean;
}

export const SpecializedCentreCard: React.FC<CentreCardProps> = ({
  item,
  onWhyAppears,
  onPrepareContact,
  isCompared,
  onToggleCompare,
  easyReadMode
}) => {
  const { centre, evidence_level, evidence_sublevel, suitability, distance_label, transit_time_label, criterion_matrix } = item;
  const auditResult = useMemo(() => auditCentreAgainstSnapshot(centre), [centre]);
  const parsedPhones = useMemo(() => extractSpanishPhoneNumbers(centre.phone || ''), [centre.phone]);
  const hasProfileCriterion = useMemo(
    () => criterion_matrix.some(c => c.criterion_id.startsWith('profile.')),
    [criterion_matrix]
  );

  const a2Label = easyReadMode
    ? evidence_sublevel === 'A2_entity'
      ? 'La entidad atiende este perfil (confirmar sede)'
      : 'Centro especializado (confirmar este servicio)'
    : evidence_sublevel === 'A2_entity'
      ? 'Nivel A2 · Lo declara la entidad titular'
      : 'Nivel A2 · Confirme el apoyo';

  const evidenceConfig: Record<string, { label: string; textClass: string; Icon: React.ComponentType<{ className?: string }> }> = {
    A1: {
      label: easyReadMode ? 'Especialización confirmada en el registro' : 'Nivel A1 · Especialización publicada',
      textClass: 'text-emerald-800',
      Icon: ShieldCheck
    },
    A2: { label: a2Label, textClass: 'text-teal-800', Icon: ShieldCheck },
    B1: {
      label: easyReadMode ? 'Servicios parecidos (preguntar antes)' : 'Nivel B1 · Servicios relacionados',
      textClass: 'text-sky-800',
      Icon: Layers
    },
    B2: {
      label: easyReadMode ? 'Posible recurso (preguntar antes)' : 'Nivel B2 · Posible recurso',
      textClass: 'text-indigo-800',
      Icon: Layers
    },
    C: {
      label: easyReadMode
        ? 'Recurso general (preguntar al llamar)'
        : hasProfileCriterion
        ? 'Nivel C · Orientación general'
        : 'Catálogo oficial autorizado',
      textClass: 'text-stone-700',
      Icon: Compass
    }
  };

  const evInfo = evidenceConfig[evidence_level] || evidenceConfig.C;
  const EvidenceIcon = evInfo.Icon;

  const suitabilityText =
    evidence_level === 'C'
      ? hasProfileCriterion
        ? suitability === 'partial'
          ? 'Coincidencia parcial (confirmar con el centro)'
          : 'Sin especialización publicada para este perfil'
        : suitability === 'complete'
        ? 'Cumple los filtros aplicados'
        : suitability === 'partial'
        ? 'Cumplimiento parcial (confirmar datos)'
        : null
      : suitability === 'complete'
      ? 'Coincidencia completa'
      : suitability === 'partial'
      ? 'Coincidencia parcial'
      : 'Sin datos suficientes';

  return (
    <article className="bg-white rounded-xl border border-stone-200 p-4 sm:p-5 shadow-xs transition-shadow hover:shadow-sm space-y-3">
      {/* 1. Cabecera: Nombre oficial, línea editorial de ubicación y comparar */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-base font-bold text-stone-900 leading-snug">
            {centre.official_name}
          </h3>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-stone-600 mt-1.5">
            <span className="font-semibold text-stone-800">{centre.municipality}</span>
            {centre.district && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span>Distrito {centre.district}</span>
              </>
            )}
            <span aria-hidden="true" className="text-stone-300">·</span>
            <span>{centre.subtype || centre.centre_type}</span>
            <span aria-hidden="true" className="text-stone-300">·</span>
            <span>
              {centre.public_private_status === 'red_publica'
                ? 'Red Pública'
                : centre.public_private_status === 'concertado'
                ? 'Red Concertada'
                : centre.public_private_status === 'no_especificado'
                ? 'Titularidad no especificada'
                : 'Privado'}
            </span>
            {distance_label && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="font-mono text-stone-900 font-semibold inline-flex items-center gap-1 whitespace-nowrap">
                  <MapPin className="w-3 h-3 text-stone-500 shrink-0" aria-hidden="true" />
                  {distance_label}
                </span>
              </>
            )}
            {transit_time_label && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span
                  className="font-mono text-sky-900 font-semibold inline-flex items-center gap-1 whitespace-nowrap"
                  title="Estimación orientativa a partir de la distancia en línea recta desde el origen seleccionado (sin consulta de horarios ni líneas CRTM en tiempo real)"
                >
                  <Bus className="w-3 h-3 text-sky-700 shrink-0" aria-hidden="true" />
                  {transit_time_label}
                </span>
              </>
            )}
          </div>
        </div>

        <label className="flex items-center gap-1.5 text-xs text-stone-700 cursor-pointer self-start shrink-0 px-2 py-1 rounded hover:bg-stone-50 border border-transparent hover:border-stone-200 transition-colors">
          <input
            type="checkbox"
            checked={isCompared}
            onChange={() => onToggleCompare(centre.centre_id)}
            aria-label={`Comparar ${centre.official_name}`}
            className="rounded border-stone-300 accent-stone-900 cursor-pointer"
          />
          <span className="select-none font-medium">Comparar</span>
        </label>
      </div>

      {/* 2. Franja editorial de evidencia, adecuación y procedencia (Disciplina Zero-Pill) */}
      <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 pt-2.5 border-t border-stone-100 ${easyReadMode ? 'text-sm' : 'text-xs'}`}>
        <span className={`inline-flex items-center gap-1.5 font-bold ${evInfo.textClass}`}>
          <EvidenceIcon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>{evInfo.label}</span>
        </span>

        {!easyReadMode && (
          <>
            {suitabilityText && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="inline-flex items-center gap-1 text-stone-700 font-medium">
                  {suitability === 'complete' && <Check className="w-3.5 h-3.5 text-emerald-700 shrink-0" aria-hidden="true" />}
                  <span>{suitabilityText}</span>
                </span>
              </>
            )}

            {auditResult.audit_status === 'verified_official' && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="inline-flex items-center gap-1 text-emerald-900 font-medium" title={auditResult.audit_note}>
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-700 shrink-0" aria-hidden="true" />
                  <span>Registro Ayuntamiento de Madrid</span>
                </span>
              </>
            )}

            {auditResult.audit_status === 'verified_regional' && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="inline-flex items-center gap-1 text-sky-900 font-medium" title={auditResult.audit_note}>
                  <ShieldCheck className="w-3.5 h-3.5 text-sky-700 shrink-0" aria-hidden="true" />
                  <span>Registro Comunidad de Madrid</span>
                </span>
              </>
            )}

            {auditResult.audit_status === 'discrepancy' && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="inline-flex items-center gap-1 text-rose-800 font-semibold" title={auditResult.audit_note}>
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-700 shrink-0" aria-hidden="true" />
                  <span>Discrepancia registral: {auditResult.discrepancies.join(', ')}</span>
                </span>
              </>
            )}

            {auditResult.audit_status === 'unverified' && (
              <>
                <span aria-hidden="true" className="text-stone-300">·</span>
                <span className="inline-flex items-center gap-1 text-amber-900 font-semibold" title={auditResult.audit_note}>
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" aria-hidden="true" />
                  <span>Pendiente de enlace con registro vivo</span>
                </span>
              </>
            )}
          </>
        )}

        {typeof centre.availability.authorised_places === 'number' && (
          <>
            <span aria-hidden="true" className="text-stone-300">·</span>
            <span className="font-mono text-stone-700 font-medium text-[11px] tabular-nums" title="Cupo máximo registral (no indica vacantes libres)">
              {centre.availability.authorised_places} plazas autorizadas
            </span>
          </>
        )}

        {centre.allowed_life_stages.length === 0 && (
          <>
            <span aria-hidden="true" className="text-stone-300">·</span>
            <span
              className="text-amber-900 font-medium text-[11px]"
              title="El registro oficial no especifica rango de edad ni etapa vital para este recurso"
            >
              Edad: no consta, confirmar
            </span>
          </>
        )}
      </div>

      {/* 3. Vía de acceso oficial */}
      <div className={`${easyReadMode ? 'text-sm p-3' : 'text-xs p-2.5'} text-stone-700 bg-stone-50/90 rounded-lg border border-stone-200 flex items-start gap-2`}>
        <ArrowRight className="w-3.5 h-3.5 text-stone-500 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="leading-relaxed">
          <span className="font-semibold text-stone-900">{easyReadMode ? 'Cómo pedir acceso: ' : 'Acceso: '}</span>
          {centre.access_route.next_step_action}
        </div>
      </div>

      {/* Lectura fácil si está activado */}
      {easyReadMode && (
        <div className="p-2.5 bg-amber-50/80 border border-amber-200/90 rounded-lg text-xs text-amber-950 leading-relaxed">
          <span className="font-bold">Lectura fácil: </span>
          {centre.centre_id.startsWith('MAD-PK')
            ? 'Recurso publicado en el catálogo oficial del Ayuntamiento de Madrid (datos.madrid.es).'
            : 'Centro o servicio con autorización oficial de la Comunidad de Madrid.'}{' '}
          {centre.public_private_status === 'red_publica' || centre.public_private_status === 'concertado'
            ? 'Puede contar con plazas públicas o concertadas; consulte en sus servicios sociales cómo solicitar acceso.'
            : centre.public_private_status === 'no_especificado'
            ? 'Consulte directamente con la entidad o en sus servicios sociales las vías de acceso y condiciones.'
            : 'Entidad privada autorizada; consulte directamente con el centro las condiciones de admisión.'}
        </div>
      )}

      {/* 4. Acciones inferiores y contacto */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-stone-100">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onWhyAppears(item)}
            aria-label={`¿Por qué aparece? Ver informe de trazabilidad de ${centre.official_name}`}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-stone-900 text-white hover:bg-stone-800 transition-colors cursor-pointer"
          >
            ¿Por qué aparece?
          </button>

          <button
            type="button"
            onClick={() => onPrepareContact(item)}
            aria-label={`Preparar contacto con ${centre.official_name} e imprimir ficha`}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-stone-300 text-stone-700 hover:bg-stone-50 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5 text-stone-500" aria-hidden="true" />
            <span>Preparar contacto</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-stone-600">
          {parsedPhones.validNumbers.length > 0 ? (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              {parsedPhones.validNumbers.slice(0, 2).map((num, idx) => (
                <a
                  key={num}
                  href={`tel:${num}`}
                  aria-label={`Llamar a ${centre.official_name} al teléfono ${parsedPhones.formattedNumbers[idx]}`}
                  className="inline-flex items-center gap-1 hover:text-stone-950 font-medium font-mono underline decoration-stone-300 underline-offset-2"
                >
                  {idx === 0 && <Phone className="w-3.5 h-3.5 text-stone-500 shrink-0" aria-hidden="true" />}
                  <span>{parsedPhones.formattedNumbers[idx]}</span>
                </a>
              ))}
              {parsedPhones.validNumbers.length > 2 && (
                <span className="text-[11px] text-stone-600">
                  +{parsedPhones.validNumbers.length - 2} en ficha
                </span>
              )}
            </div>
          ) : centre.phone ? (
            <span
              className="inline-flex items-center gap-1 text-stone-600 font-mono text-[11px]"
              title="Número incompleto o no estándar en el CSV oficial"
            >
              <Phone className="w-3.5 h-3.5 text-stone-500 shrink-0" aria-hidden="true" />
              <span>{centre.phone} (formato incompleto en registro)</span>
            </span>
          ) : null}
          {centre.website && (
            <a 
              href={centre.website}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-stone-950 p-1 rounded"
              title="Web oficial"
              aria-label={`Visitar web oficial de ${centre.official_name} (se abre en nueva pestaña)`}
            >
              <ExternalLink className="w-3.5 h-3.5 text-stone-500" aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
};
