/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Glosario en Lectura Fácil
 * Definiciones breves y claras de conceptos administrativos y sociosanitarios (§30)
 */

import React, { useState, useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { X, BookOpen, Search, ExternalLink } from 'lucide-react';

interface EasyReadGlossaryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface GlossaryEntry {
  term: string;
  simple: string;
  technical: string;
  links?: { label: string; url: string }[];
}

const GLOSSARY_TERMS: GlossaryEntry[] = [
  {
    term: 'Nivel A1 (Evidencia oficial completa)',
    simple: 'El centro tiene publicado en los registros de la Comunidad de Madrid que atiende exactamente su condición y dispone del servicio concreto que busca.',
    technical: 'Coincidencia explícita literal en condición y oferta asistencial en fuente estructurada oficial.'
  },
  {
    term: 'Nivel A2 · Lo declara la entidad titular',
    simple: 'La asociación o fundación dueña del centro sí está especializada en esa condición (por ejemplo TEA), pero el nombre individual del centro no lo especifica. Conviene llamar para confirmar esa sede concreta.',
    technical: 'Especialización declarada en el campo registral entidad_denominacion y diferenciada del nivel A1 del centro concreto.'
  },
  {
    term: 'Nivel A2 (Especialización publicada, apoyo a confirmar)',
    simple: 'El centro declara oficialmente la condición (por ejemplo daño cerebral), pero debe confirmar por teléfono si tiene el servicio específico que usted pide.',
    technical: 'Condición explícita publicada; apoyo concreto no desglosado en registro.'
  },
  {
    term: 'Nivel B1 (Servicios relacionados)',
    simple: 'El centro no menciona el nombre exacto de la enfermedad, pero tiene servicios que ayudan (como rehabilitación o logopedia) y no consta incompatibilidad de edad.',
    technical: 'Dos o más servicios funcionalmente relacionados sin exclusión explícita de etapa vital.'
  },
  {
    term: 'Códigos oficiales de accesibilidad (0 a 6 · datos.madrid.es)',
    simple: 'Significado literal oficial en el Ayuntamiento de Madrid: 0 = No accesible · 1 = Accesible · 2 = Parcialmente accesible · 3 = Sin información · 4 = Lengua de signos · 5 = Señalización podotáctil · 6 = Bucle magnético. El código 3 nunca se interpreta como accesible.',
    technical: 'Codificación literal del campo ACCESIBILIDAD según la ficha de estructura oficial del catálogo 212774-0 del Ayuntamiento de Madrid.',
    links: [
      {
        label: 'Ficha de estructura oficial (PDF · datos.madrid.es)',
        url: 'https://datos.madrid.es/egob/catalogo/212774-0-atencion-social.pdf'
      },
      {
        label: 'Conjunto de datos 212774-0 (datos.madrid.es)',
        url: 'https://datos.madrid.es/dataset/212774-0-atencion-social'
      }
    ]
  },
  {
    term: 'PIA (Programa Individual de Atención)',
    simple: 'Es el documento oficial de la Ley de Dependencia donde la trabajadora social escribe a qué centro de día o residencia tiene derecho la persona.',
    technical: 'Resolución administrativa que determina las modalidades de intervención y servicios del Catálogo de Dependencia.'
  },
  {
    term: 'Plazas autorizadas vs Vacantes',
    simple: 'Plazas autorizadas es el número máximo de personas que caben en el edificio según la ley. NO significa que haya plazas libres hoy.',
    technical: 'Capacidad máxima de ocupación registral; no equivale a vacantes disponibles en tiempo real.'
  },
  {
    term: 'Centro de Día',
    simple: 'Lugar donde las personas acuden durante el día (por ejemplo de 9 a 17h) para recibir apoyo, talleres y rehabilitación, y vuelven a dormir a su casa.',
    technical: 'Servicio socioasistencial diurno para fomento de autonomía personal y respiro familiar.'
  },
  {
    term: 'Centro de Atención Temprana (CAT)',
    simple: 'Centros para niños de 0 a 6 años que necesitan ayuda con el lenguaje, el movimiento o la conducta.',
    technical: 'Dispositivo ambulatorio para el tratamiento integral de trastornos del neurodesarrollo en la primera infancia.'
  },
  {
    term: 'CRECOVI',
    simple: 'Oficina oficial de la Comunidad de Madrid que revisa a los niños pequeños y decide si necesitan atención temprana gratuita.',
    technical: 'Centro Regional de Coordinación y Valoración Infantil de la Comunidad de Madrid.'
  },
  {
    term: 'Misma sede (mismo edificio)',
    simple: 'Todos los servicios están dentro del mismo edificio o dirección. No tiene que viajar a otro sitio para hacer la logopedia o la fisioterapia.',
    technical: 'Identificador físico unívoco de establecimiento, diferenciado de la entidad gestora o proveedor.'
  },
  {
    term: 'Titularidad no especificada (datos.madrid.es)',
    simple: 'Cuando un centro solo aparece en el catálogo municipal del Ayuntamiento sin ficha enlazada en la Comunidad de Madrid, la fuente no dice si tiene plazas públicas concertadas o si es privado. La app lo indica claramente para que lo confirme al llamar.',
    technical: 'Marcado como «Titularidad no especificada» para evitar atribuir concierto o titularidad sin respaldo registral.'
  },
  {
    term: 'REGCESS (futuro interoperable)',
    simple: 'El registro oficial sanitario donde constan clínicas y hospitales autorizados. Esta versión v1.9 consulta los 3 registros oficiales de Atención Social; la integración sanitaria REGCESS queda prevista para la siguiente fase.',
    technical: 'Registro General de Centros, Servicios y Establecimientos Sanitarios (ámbito sanitario no incluido aún en los 3 CSV sociales).'
  }
];

export const EasyReadGlossaryModal: React.FC<EasyReadGlossaryModalProps> = ({ isOpen, onClose }) => {
  const [filter, setFilter] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isOpen);

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = GLOSSARY_TERMS.filter(t => 
    t.term.toLowerCase().includes(filter.toLowerCase()) ||
    t.simple.toLowerCase().includes(filter.toLowerCase()) ||
    t.technical.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="glossary-modal-title"
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
            <BookOpen className="w-5 h-5 text-stone-700" />
            <h2 id="glossary-modal-title" className="text-base font-bold text-stone-900">
              Glosario en Lectura Fácil y Siglas Oficiales
            </h2>
          </div>
          <button 
            type="button"
            onClick={onClose} 
            aria-label="Cerrar modal"
            className="p-1.5 text-stone-500 hover:text-stone-800 rounded-lg cursor-pointer"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Buscador de términos */}
        <div className="p-4 border-b border-stone-200 bg-stone-50/50 space-y-1.5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" aria-hidden="true" />
            <input
              type="text"
              aria-label="Buscar término o sigla en el glosario"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Buscar término, sigla o código (ej. bucle, 0 a 6, PIA, entidad titular)..."
              className="w-full pl-9 pr-9 py-2 text-xs border border-stone-300 rounded-lg bg-white focus:outline-none focus:border-stone-900"
            />
            {filter && (
              <button
                type="button"
                onClick={() => setFilter('')}
                aria-label="Limpiar búsqueda en el glosario"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-stone-500 hover:text-stone-900 cursor-pointer"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            )}
          </div>
          <div className="text-[11px] text-stone-500 font-mono" aria-live="polite">
            {filtered.length} {filtered.length === 1 ? 'término mostrado' : 'términos mostrados'} de {GLOSSARY_TERMS.length}
          </div>
        </div>

        {/* Lista de términos */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1 text-xs">
          {filtered.length === 0 ? (
            <div className="py-10 text-center space-y-3 text-stone-600">
              <p>
                No se encontraron definiciones para «<strong>{filter}</strong>».
              </p>
              <button
                type="button"
                onClick={() => setFilter('')}
                className="px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-stone-50 text-stone-900 font-semibold cursor-pointer"
              >
                Mostrar todos los términos
              </button>
            </div>
          ) : (
            filtered.map((item, idx) => (
              <div key={idx} className="p-3.5 rounded-xl border border-stone-200 bg-white space-y-1.5">
                <h3 className="font-bold text-stone-900 text-sm">
                  {item.term}
                </h3>
                <p className="text-stone-800 leading-relaxed font-medium bg-amber-50/60 p-2 rounded-lg border border-amber-100">
                  {item.simple}
                </p>
                <div className="text-[11px] text-stone-500 pt-1">
                  <strong>Definición administrativa:</strong> {item.technical}
                </div>
                {item.links && item.links.length > 0 && (
                  <div className="flex flex-wrap gap-3 pt-1">
                    {item.links.map((lk) => (
                      <a
                        key={lk.url}
                        href={lk.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-stone-800 underline hover:text-stone-950"
                      >
                        <span>{lk.label}</span>
                        <ExternalLink className="w-3 h-3" aria-hidden="true" />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 cursor-pointer"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
