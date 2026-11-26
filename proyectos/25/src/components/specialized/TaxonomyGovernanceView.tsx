/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Panel de Gestión Taxonómica y Utilidad Administrativa
 * Gobernanza de categorías, ciclo de vida, reglas de inferencia y vacíos territoriales reales (§33, §58)
 * Cero métricas inventadas: todos los conteos y distancias proceden del catálogo CSV cargado en vivo.
 */

import React, { useState, useMemo } from 'react';
import { SpecializedCentre, ProfileId } from '../../types/specialized';
import { calculateHaversineDistanceKm } from '../../data/municipalitiesData';
import { 
  TAXONOMY_METADATA, 
  CORE_PROFILES, 
  EXPERIMENTAL_PROFILES, 
  PENDING_PROFILES, 
  FORBIDDEN_INFERENCES,
  TaxonomyProfileDefinition
} from '../../data/specializedTaxonomy';
import { 
  AlertTriangle, 
  MapPin, 
  CheckCircle2,
  ShieldCheck
} from 'lucide-react';

interface TaxonomyGovernanceViewProps {
  centres?: SpecializedCentre[];
}

interface TerritorialZoneSpec {
  zone: string;
  municipality: string;
  coords: [number, number];
}

const MONITORED_ZONES: TerritorialZoneSpec[] = [
  { zone: 'Sierra Norte (Buitrago del Lozoya)', municipality: 'Buitrago del Lozoya', coords: [40.9936, -3.6350] },
  { zone: 'Cuenca del Alberche (San Martín de Valdeiglesias)', municipality: 'San Martín de Valdeiglesias', coords: [40.3622, -4.3992] },
  { zone: 'Comarca Sureste (Chinchón)', municipality: 'Chinchón', coords: [40.1408, -3.4214] },
  { zone: 'Sur Metropolitano (Aranjuez)', municipality: 'Aranjuez', coords: [40.0333, -3.6000] },
  { zone: 'Sierra Oeste (San Lorenzo de El Escorial)', municipality: 'San Lorenzo de El Escorial', coords: [40.5917, -4.1481] },
  { zone: 'Corredor del Henares (Alcalá de Henares)', municipality: 'Alcalá de Henares', coords: [40.4819, -3.3635] }
];

export const TaxonomyGovernanceView: React.FC<TaxonomyGovernanceViewProps> = ({ centres = [] }) => {
  const [activeTab, setActiveTab] = useState<'categories' | 'rules' | 'voids' | 'analytics'>('categories');

  // Conteo real por perfil sobre los centros oficiales cargados
  const profileCoverageMap = useMemo(() => {
    const map: Record<string, { a1: number; a2Entity: number; totalA: number }> = {};
    const allProfiles: TaxonomyProfileDefinition[] = [
      ...Object.values(CORE_PROFILES),
      ...Object.values(EXPERIMENTAL_PROFILES),
      ...Object.values(PENDING_PROFILES)
    ];

    for (const prof of allProfiles) {
      let a1 = 0;
      let a2Entity = 0;
      for (const c of centres) {
        if (c.explicit_specialisations?.includes(prof.id as ProfileId)) {
          a1++;
        } else if (c.entity_declared_specialisations?.includes(prof.id as ProfileId)) {
          a2Entity++;
        }
      }
      map[prof.id] = { a1, a2Entity, totalA: a1 + a2Entity };
    }
    return map;
  }, [centres]);

  const allProfilesList = useMemo<TaxonomyProfileDefinition[]>(
    () => [
      ...Object.values(CORE_PROFILES),
      ...Object.values(EXPERIMENTAL_PROFILES),
      ...Object.values(PENDING_PROFILES)
    ],
    []
  );

  const approvedList = useMemo(
    () => allProfilesList.filter(p => p.status === 'approved'),
    [allProfilesList]
  );
  const expList = useMemo(
    () => allProfilesList.filter(p => p.status === 'experimental'),
    [allProfilesList]
  );
  const pendingList = useMemo(
    () => allProfilesList.filter(p => p.status === 'pending_review'),
    [allProfilesList]
  );

  // Vacíos territoriales calculados por distancia Haversine real desde zonas periféricas a recursos A1/A2_entity geocodificados
  const territorialVoids = useMemo(() => {
    if (centres.length === 0) return [];
    const computed: {
      zone: string;
      profile: string;
      minDistanceKm: number | null;
      closestCentreName: string;
      closestMunicipality: string;
      matchingCount: number;
    }[] = [];

    for (const zone of MONITORED_ZONES) {
      for (const prof of approvedList) {
        const matching = centres.filter(
          c =>
            (c.explicit_specialisations?.includes(prof.id as ProfileId) ||
              c.entity_declared_specialisations?.includes(prof.id as ProfileId)) &&
            c.has_valid_coordinates &&
            c.coordinates
        );

        let minDistanceKm: number | null = null;
        let closestCentreName = 'Sin centros georreferenciados en los CSV oficiales';
        let closestMunicipality = '';

        for (const c of matching) {
          const dist = calculateHaversineDistanceKm(zone.coords, c.coordinates!);
          if (minDistanceKm === null || dist < minDistanceKm) {
            minDistanceKm = dist;
            closestCentreName = c.official_name;
            closestMunicipality = c.municipality;
          }
        }

        if (minDistanceKm === null || minDistanceKm >= 25) {
          computed.push({
            zone: zone.zone,
            profile: prof.preferred_label,
            minDistanceKm,
            closestCentreName,
            closestMunicipality,
            matchingCount: matching.length
          });
        }
      }
    }

    return computed.sort((a, b) => (b.minDistanceKm ?? 999) - (a.minDistanceKm ?? 999));
  }, [centres, approvedList]);

  return (
    <div className="space-y-6">
      {/* Cabecera */}
      <div className="border-b border-stone-200 pb-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-[11px] text-stone-500 font-mono uppercase tracking-wider">
              Taxonomía v{TAXONOMY_METADATA.version} · Liberada {TAXONOMY_METADATA.released_at} · Catálogo vivo: {centres.length} recursos
            </div>
            <h2 className="text-xl font-bold text-stone-900 mt-1">
              Gobernanza Taxonómica y Auditoría Territorial
            </h2>
            <p className="text-xs text-stone-600 mt-1 max-w-3xl leading-relaxed">
              La taxonomía es un subsistema versionable gobernado con reglas explícitas de evidencia. Todos los recuentos y distancias territoriales de este panel se calculan directamente sobre los registros CSV cargados, sin analíticas sintéticas.
            </p>
          </div>

          {/* Estadísticas de gobernanza */}
          <div className="flex items-center gap-3 text-xs shrink-0">
            <div className="p-2.5 bg-stone-50 border border-stone-200 rounded-lg text-center">
              <div className="font-mono font-bold text-stone-900 text-sm">{approvedList.length}</div>
              <div className="text-[10px] text-stone-500 uppercase">Perfiles Aprobados</div>
            </div>
            <div className="p-2.5 bg-stone-50 border border-stone-200 rounded-lg text-center">
              <div className="font-mono font-bold text-stone-900 text-sm">{expList.length}</div>
              <div className="text-[10px] text-stone-500 uppercase">Experimentales</div>
            </div>
            <div className="p-2.5 bg-stone-50 border border-stone-200 rounded-lg text-center">
              <div className="font-mono font-bold text-stone-900 text-sm">{pendingList.length}</div>
              <div className="text-[10px] text-stone-500 uppercase">En revisión</div>
            </div>
          </div>
        </div>

        {/* Pestañas de gobernanza */}
        <div className="flex items-center gap-2 mt-6 overflow-x-auto text-xs font-semibold" role="tablist" aria-label="Secciones de gobernanza taxonómica">
          {([
            { id: 'categories', label: 'Catálogo y Ciclo de Vida' },
            { id: 'rules', label: 'Reglas Negativas de Inferencia' },
            { id: 'voids', label: 'Vacíos Territoriales Calculados' },
            { id: 'analytics', label: 'Candidatos en Cola (Auditoría CSV)' }
          ] as const).map((t, index, allTabs) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              tabIndex={activeTab === t.id ? 0 : -1}
              aria-selected={activeTab === t.id}
              aria-controls={`tabpanel-${t.id}`}
              onClick={() => setActiveTab(t.id)}
              onKeyDown={(e) => {
                let targetIndex: number | null = null;
                if (e.key === 'ArrowRight') targetIndex = (index + 1) % allTabs.length;
                else if (e.key === 'ArrowLeft') targetIndex = (index - 1 + allTabs.length) % allTabs.length;
                else if (e.key === 'Home') targetIndex = 0;
                else if (e.key === 'End') targetIndex = allTabs.length - 1;
                if (targetIndex !== null) {
                  e.preventDefault();
                  const nextId = allTabs[targetIndex].id;
                  setActiveTab(nextId);
                  document.getElementById(`tab-${nextId}`)?.focus();
                }
              }}
              className={`px-3 py-1.5 rounded-lg border transition-colors whitespace-nowrap cursor-pointer ${
                activeTab === t.id
                  ? 'bg-stone-900 text-white border-stone-900'
                  : 'bg-white text-stone-700 border-stone-200 hover:bg-stone-50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Pestaña 1: Catálogo y Ciclo de vida (§51, §52) */}
      {activeTab === 'categories' && (
        <div role="tabpanel" id="tabpanel-categories" aria-labelledby="tab-categories" tabIndex={0} className="space-y-6">
          <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-700 leading-relaxed">
            <strong>Puerta de Aceptación:</strong> Un perfil solo pasa a estado <em>approved</em> si cuenta con al menos 3 centros explícitos en registro, reglas negativas documentadas y trazabilidad literal en fuentes oficiales.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Aprobados */}
            <div className="space-y-3">
              <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider flex items-center justify-between">
                <span>Perfiles Aprobados (Puerta &ge; 3 A1)</span>
                <span className="font-mono text-emerald-700">{approvedList.length} activos</span>
              </h3>
              {approvedList.map((prof) => {
                const cov = profileCoverageMap[prof.id] || { a1: 0, a2Entity: 0, totalA: 0 };
                return (
                  <div key={prof.id} className="p-3.5 rounded-xl border border-stone-200 bg-white space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-stone-900">{prof.preferred_label}</span>
                      <span className="text-[10px] font-mono uppercase text-emerald-800 font-bold shrink-0">
                        {prof.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-600 leading-snug">
                      {prof.description}
                    </p>
                    <div className="pt-2 border-t border-stone-100 flex items-center justify-between text-[10px] text-stone-600 font-mono">
                      <span>CSV real: {cov.a1} A1 · {cov.a2Entity} A2 entidad</span>
                      <span>Rev: {prof.review_date}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Experimentales / Reserva */}
            <div className="space-y-3">
              <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider flex items-center justify-between">
                <span>Perfiles Experimentales</span>
                <span className="font-mono text-amber-700">{expList.length} en evaluación</span>
              </h3>
              {expList.map((prof) => {
                const cov = profileCoverageMap[prof.id] || { a1: 0, a2Entity: 0, totalA: 0 };
                return (
                  <div key={prof.id} className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/30 space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-amber-950">{prof.preferred_label}</span>
                      <span className="text-[10px] font-mono uppercase text-amber-900 font-bold shrink-0">
                        {prof.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-600 leading-snug">
                      {prof.description}
                    </p>
                    <div className="pt-2 border-t border-amber-100 flex items-center justify-between text-[10px] text-stone-600 font-mono">
                      <span>CSV real: {cov.a1} A1 · {cov.a2Entity} A2 entidad</span>
                      <span>Rev: {prof.review_date}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pendientes de revisión experta */}
            <div className="space-y-3">
              <h3 className="font-bold text-stone-900 text-xs uppercase tracking-wider flex items-center justify-between">
                <span>En Cola de Revisión</span>
                <span className="font-mono text-stone-500">{pendingList.length} candidatos</span>
              </h3>
              {pendingList.map((prof) => {
                const cov = profileCoverageMap[prof.id] || { a1: 0, a2Entity: 0, totalA: 0 };
                return (
                  <div key={prof.id} className="p-3.5 rounded-xl border border-stone-200 bg-stone-50/50 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-stone-800">{prof.preferred_label}</span>
                      <span className="text-[10px] font-mono uppercase text-stone-600 font-semibold shrink-0">
                        pending
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-500 line-clamp-2">
                      {prof.description}
                    </p>
                    <div className="pt-1 text-[10px] font-mono text-stone-500">
                      CSV real: {cov.a1} A1 · {cov.a2Entity} A2 entidad
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Pestaña 2: Reglas Negativas de Inferencia (§26.1) */}
      {activeTab === 'rules' && (
        <div role="tabpanel" id="tabpanel-rules" aria-labelledby="tab-rules" tabIndex={0} className="space-y-3">
          <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-700 leading-relaxed">
            Las <strong>reglas negativas obligatorias</strong> impiden que el motor de coincidencia extrapole competencias clínicas sin evidencia expresa. Su cumplimiento se comprueba automáticamente antes de publicar la aplicación.
          </div>

          <div className="border border-stone-200 rounded-xl bg-white overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-stone-100 text-stone-800 font-bold border-b border-stone-200">
                  <th className="p-3 w-24">Código</th>
                  <th className="p-3">Regla Negativa de Inferencia</th>
                  <th className="p-3">Consecuencia Estricta en el Motor</th>
                  <th className="p-3 w-28 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {FORBIDDEN_INFERENCES.map((item) => (
                  <tr key={item.id} className="hover:bg-stone-50/50">
                    <td className="p-3 font-mono font-bold text-stone-900">{item.id}</td>
                    <td className="p-3 font-medium text-stone-800">{item.rule}</td>
                    <td className="p-3 text-stone-600">{item.consequence}</td>
                    <td className="p-3 text-center">
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Blindada</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pestaña 3: Vacíos Territoriales Calculados en Tiempo Real (§33) */}
      {activeTab === 'voids' && (
        <div role="tabpanel" id="tabpanel-voids" aria-labelledby="tab-voids" tabIndex={0} className="space-y-4">
          <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-700 leading-relaxed">
            <strong>Auditoría geográfica automatizada:</strong> Cruce directo entre 6 cabeceras comarcales de la Comunidad de Madrid y los centros con especialización publicada (nivel A1 o A2 por entidad titular) en los CSV oficiales activos. Se muestran los casos donde el recurso especializado más cercano está a &ge; 25 km en línea recta.
          </div>

          {centres.length === 0 ? (
            <div className="p-6 bg-white rounded-xl border border-stone-200 text-xs text-stone-500 text-center">
              Cargando catálogo oficial para calcular distancias territoriales...
            </div>
          ) : territorialVoids.length === 0 ? (
            <div className="p-6 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-900">
              Todas las zonas monitorizadas cuentan con al menos un recurso A1/A2 a menos de 25 km.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {territorialVoids.map((voidItem, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-amber-200 bg-amber-50/40 space-y-2 text-xs">
                  <div className="font-bold text-stone-900 text-sm flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-amber-700 shrink-0" />
                    <span>{voidItem.zone}</span>
                  </div>
                  <div className="text-stone-700">
                    <strong>Perfil analizado:</strong> {voidItem.profile}
                  </div>
                  <div className="text-amber-900 font-mono font-bold">
                    {voidItem.minDistanceKm !== null
                      ? `Distancia Haversine mínima a recurso A1/A2: ${voidItem.minDistanceKm.toFixed(1)} km`
                      : 'Sin recursos georreferenciados en los CSV sociales'}
                  </div>
                  <p className="text-[11px] text-stone-600 leading-relaxed pt-1 border-t border-amber-200/50">
                    Recurso A1/A2 más próximo: <strong>{voidItem.closestCentreName}</strong>
                    {voidItem.closestMunicipality ? ` (${voidItem.closestMunicipality})` : ''}. Base evaluada: {voidItem.matchingCount} sedes con coordenadas.
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pestaña 4: Auditoría de cobertura de los 13 perfiles en el catálogo CSV real */}
      {activeTab === 'analytics' && (
        <div role="tabpanel" id="tabpanel-analytics" aria-labelledby="tab-analytics" tabIndex={0} className="space-y-4">
          <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-700 leading-relaxed flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <strong>Cero telemetría en servidor (RGPD):</strong> La aplicación no envía ni registra consultas ciudadanas en servidores externos. En lugar de cifras simuladas, esta tabla audita la evidencia real en los 3 CSV oficiales para los {allProfilesList.length} perfiles taxonómicos respecto a su puerta mínima de aceptación (&ge; 3 centros explícitos A1).
            </div>
          </div>

          <div className="border border-stone-200 rounded-xl bg-white overflow-x-auto text-xs">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-stone-100 text-stone-800 font-bold border-b border-stone-200">
                  <th className="p-3">Perfil taxonómico</th>
                  <th className="p-3 text-center">Explícitos en centro (A1)</th>
                  <th className="p-3 text-center">Declarados entidad (A2)</th>
                  <th className="p-3">Puerta de aceptación (&ge; {TAXONOMY_METADATA.minimum_review_requirements.minimum_explicit_centres} explícitos A1)</th>
                  <th className="p-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {allProfilesList.map((prof) => {
                  const cov = profileCoverageMap[prof.id] || { a1: 0, a2Entity: 0, totalA: 0 };
                  const minRequired = Math.max(
                    TAXONOMY_METADATA.minimum_review_requirements.minimum_explicit_centres,
                    prof.evidence_thresholds.minimum_explicit_centres
                  );
                  const passesNumericGate = cov.a1 >= minRequired;
                  return (
                    <tr key={prof.id} className="hover:bg-stone-50/50">
                      <td className="p-3 font-semibold text-stone-900">{prof.preferred_label}</td>
                      <td className="p-3 font-mono font-bold text-stone-900 text-center">{cov.a1}</td>
                      <td className="p-3 font-mono text-stone-700 text-center">{cov.a2Entity}</td>
                      <td className="p-3 text-stone-700">
                        {prof.status === 'approved' && passesNumericGate ? (
                          <span className="text-emerald-800 font-medium">
                            Aprobado y vigente ({cov.a1} &ge; {minRequired})
                          </span>
                        ) : passesNumericGate ? (
                          <span className="text-emerald-800 font-medium">
                            Cumple umbral numérico ({cov.a1} &ge; {minRequired}); pendiente de revisión colegiada
                          </span>
                        ) : (
                          <span className="text-amber-800 flex items-center gap-1 font-medium">
                            <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                            <span>Insuficiente en CSV sociales actuales ({cov.a1}/{minRequired})</span>
                          </span>
                        )}
                      </td>
                      <td className="p-3">
                        <span className={`text-[11px] font-mono uppercase font-bold ${
                          prof.status === 'approved'
                            ? 'text-emerald-800'
                            : prof.status === 'experimental'
                            ? 'text-amber-800'
                            : 'text-stone-600'
                        }`}>
                          {prof.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
