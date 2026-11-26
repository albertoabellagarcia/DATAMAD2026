/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Desambiguación Obligatoria de Términos Amplios
 * Tratamiento de «neurodivergente» y «psicomotriz» sin realizar diagnósticos libres (§54)
 */

import React, { useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { DISAMBIGUATION_TERMS } from '../../data/specializedTaxonomy';
import { SearchQueryState, ProfileId, SupportTypeId, FunctionalNeedId } from '../../types/specialized';
import { X, ArrowRight, ShieldAlert } from 'lucide-react';

interface DisambiguationModalProps {
  term: 'neurodivergent' | 'psychomotor' | null;
  onClose: () => void;
  setQuery: React.Dispatch<React.SetStateAction<SearchQueryState>>;
}

export const DisambiguationModal: React.FC<DisambiguationModalProps> = ({
  term,
  onClose,
  setQuery
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, !!term);

  React.useEffect(() => {
    if (!term) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [term, onClose]);

  if (!term) return null;

  const data = DISAMBIGUATION_TERMS[term];

  const handleSelectOption = (opt: { id: string; label: string; type: string }) => {
    if (opt.type === 'profile' || opt.type === 'profile_exp' || opt.type === 'profile_pending') {
      setQuery(prev => ({
        ...prev,
        profile: opt.id as ProfileId
      }));
    } else if (opt.type === 'support') {
      setQuery(prev => ({
        ...prev,
        support_types: prev.support_types.includes(opt.id as SupportTypeId)
          ? prev.support_types
          : [...prev.support_types, opt.id as SupportTypeId]
      }));
    } else if (opt.type === 'need') {
      setQuery(prev => ({
        ...prev,
        functional_needs: prev.functional_needs.includes(opt.id as FunctionalNeedId)
          ? prev.functional_needs
          : [...prev.functional_needs, opt.id as FunctionalNeedId]
      }));
    }
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="disambiguation-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        ref={modalRef}
        className="bg-white rounded-2xl max-w-xl w-full border border-stone-200 shadow-xl overflow-hidden my-8"
        tabIndex={-1}
      >
        {/* Cabecera */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-start justify-between gap-4 bg-stone-50">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0" />
            <div>
              <h2 id="disambiguation-modal-title" className="text-base font-bold text-stone-900">
                {data.title}
              </h2>
              <div className="text-[11px] text-stone-500">
                Rigor metodológico y prevención de diagnósticos automáticos
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal de desambiguación"
            className="p-1.5 text-stone-400 hover:text-stone-700 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Explicación y opciones */}
        <div className="p-6 space-y-4 text-xs text-stone-700">
          <p className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-950 leading-relaxed font-medium">
            {data.warning}
          </p>

          <div>
            <div className="font-bold text-stone-900 uppercase tracking-wider text-[11px] mb-2">
              Seleccione la necesidad concreta u objetivo de apoyo:
            </div>
            <div className="space-y-1.5">
              {data.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleSelectOption(opt)}
                  className="w-full p-3 rounded-lg border border-stone-200 hover:border-stone-900 hover:bg-stone-50 transition-all text-left flex items-center justify-between group cursor-pointer"
                >
                  <div className="font-semibold text-stone-900 group-hover:text-stone-950">
                    {opt.label}
                  </div>
                  <ArrowRight className="w-4 h-4 text-stone-400 group-hover:text-stone-900 group-hover:translate-x-0.5 transition-all" aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Pie */}
        <div className="px-6 py-3 border-t border-stone-200 bg-stone-50 flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold text-stone-600 hover:text-stone-900 cursor-pointer"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};
