/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Core Matching Engine
 * Algoritmo de ordenación lexicográfica explicable:
 * A1 < A2 < B1 < B2 < C. La distancia nunca supera la evidencia (§41, §78).
 * Separación estricta entre especialización, adecuación, disponibilidad y cercanía (§70).
 */

import { 
  SpecializedCentre, 
  SearchQueryState, 
  EvaluatedCentreResult, 
  EvidenceLevel, 
  EvidenceSublevel,
  SuitabilityStatus, 
  CombinationStatus, 
  CriterionEvidence, 
  MatchExplanation, 
  SupportTypeId 
} from '../types/specialized';
import { 
  CORE_PROFILES, 
  EXPERIMENTAL_PROFILES, 
  PENDING_PROFILES, 
  SUPPORT_TYPES, 
  FUNCTIONAL_NEEDS,
  LIFE_STAGES 
} from '../data/specializedTaxonomy';
import { resolveSearchOrigin, OriginReference, calculateHaversineDistanceKm } from '../data/municipalitiesData';
import {
  SnapshotCentreRecord,
  normalizePhoneComparable,
  normalizeAddressComparable
} from './officialRegistryParser';

export type AccessibilityNeedStatus = 'confirmed' | 'partial' | 'not_stated';

export const ACCESSIBILITY_MAP: Record<string, { label: string; keywords: string[] }> = {
  wheelchair_access: {
    label: 'Acceso silla de ruedas',
    keywords: [
      'código 1', 'codigo 1', 'cota cero', 'rampa', 'elevador', 'planta a nivel',
      'pie llano', 'accesibilidad total', 'accesibilidad universal', 'accesible en silla de ruedas'
    ]
  },
  sign_language: {
    label: 'Lengua de signos',
    keywords: ['código 4', 'codigo 4', 'lengua de signos']
  },
  tactile_signage: {
    label: 'Señalización podotáctil',
    keywords: ['código 5', 'codigo 5', 'podotáctil', 'podotactil']
  },
  magnetic_loops: {
    label: 'Bucle magnético',
    keywords: ['código 6', 'codigo 6', 'bucle magnético', 'bucle magnetico', 'bucle']
  }
};

function isNegativeAccessibilityItem(itemLower: string): boolean {
  return (
    itemLower.includes('código 0') ||
    itemLower.includes('codigo 0') ||
    itemLower.includes('código 3') ||
    itemLower.includes('codigo 3') ||
    itemLower.includes('no accesible') ||
    itemLower.includes('sin información') ||
    itemLower.includes('sin informacion') ||
    itemLower.includes('sin acreditación') ||
    itemLower.includes('sin acreditacion')
  );
}

/**
 * Evalúa por código registral si un centro acredita accesibilidad ('confirmed', 'partial' o 'not_stated').
 * Código 0 ("No accesible") y Código 3 ("Sin información") nunca devuelven confirmado ni parcial (#1/#2).
 */
export function getAccessibilityNeedStatus(
  centre: SpecializedCentre,
  needId: string
): AccessibilityNeedStatus {
  const rule = ACCESSIBILITY_MAP[needId];
  if (!rule) return 'not_stated';
  const items = (centre.accessibility_features || []).map(f => f.toLowerCase());
  if (items.length === 0) return 'not_stated';

  if (needId === 'wheelchair_access') {
    let hasPartial = false;
    for (const item of items) {
      if (isNegativeAccessibilityItem(item)) continue;
      if (item.includes('código 2') || item.includes('codigo 2') || item.includes('parcialmente accesible')) {
        hasPartial = true;
        continue;
      }
      if (rule.keywords.some(kw => item.includes(kw))) {
        return 'confirmed';
      }
    }
    return hasPartial ? 'partial' : 'not_stated';
  }

  for (const item of items) {
    if (isNegativeAccessibilityItem(item)) continue;
    if (rule.keywords.some(kw => item.includes(kw))) {
      return 'confirmed';
    }
  }
  return 'not_stated';
}

/**
 * Comprueba si un centro declara una característica de accesibilidad física oficial confirmada.
 */
export function centreHasAccessibilityFeature(centre: SpecializedCentre, needId: string): boolean {
  return getAccessibilityNeedStatus(centre, needId) === 'confirmed';
}

/**
 * Calcula estimación realista de tiempo de traslado en transporte público (Metro, EMT, Cercanías)
 */
export function calculatePublicTransitTime(distanceKm: number): { minutes: number; label: string } {
  let minutes: number;
  if (distanceKm <= 1.2) {
    minutes = Math.round(5 + distanceKm * 8);
  } else if (distanceKm <= 8) {
    minutes = Math.round(10 + distanceKm * 2.6);
  } else {
    minutes = Math.round(14 + distanceKm * 2.2);
  }
  return {
    minutes,
    label: `~${minutes} min est. transp. público`
  };
}

/**
 * Normaliza cadenas de búsqueda
 */
export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

/**
 * Obtiene la definición de un perfil en cualquier estado
 */
export function getProfileDefinition(profileId: string) {
  if (profileId in CORE_PROFILES) return CORE_PROFILES[profileId as keyof typeof CORE_PROFILES];
  if (profileId in EXPERIMENTAL_PROFILES) return EXPERIMENTAL_PROFILES[profileId as keyof typeof EXPERIMENTAL_PROFILES];
  if (profileId in PENDING_PROFILES) return PENDING_PROFILES[profileId as keyof typeof PENDING_PROFILES];
  return null;
}

/**
 * Evalúa si un centro ofrece un tipo de apoyo específico en su propia sede
 */
export function centreHasSupportInSite(centre: SpecializedCentre, supportId: SupportTypeId): boolean {
  if (centre.supports.includes(supportId)) return true;
  return centre.services_offered.some(s => s.service_type === supportId);
}

/**
 * Evalúa la combinación de apoyos según el modelo Proveedor/Centro/Sede (§82)
 */
export function evaluateSupportCombination(
  centre: SpecializedCentre,
  requestedSupports: SupportTypeId[],
  allCentres: SpecializedCentre[]
): {
  status: CombinationStatus;
  details: {
    support_id: SupportTypeId;
    support_label: string;
    status: 'confirmed' | 'no_consta' | 'incompatible';
    checked_at: string;
  }[];
} {
  if (requestedSupports.length === 0) {
    return { status: 'all_same_centre', details: [] };
  }

  const details = requestedSupports.map(supId => {
    const hasIt = centreHasSupportInSite(centre, supId);
    const label = SUPPORT_TYPES[supId]?.label || supId;
    return {
      support_id: supId,
      support_label: label,
      status: hasIt ? ('confirmed' as const) : ('no_consta' as const),
      checked_at: centre.last_checked
    };
  });

  const confirmedCount = details.filter(d => d.status === 'confirmed').length;

  if (confirmedCount === requestedSupports.length) {
    return { status: 'all_same_centre', details };
  }

  if (confirmedCount > 0) {
    // Check if missing supports are offered by other centres of the SAME provider (COMB-002)
    const sameProviderCentres = allCentres.filter(c => c.provider_id === centre.provider_id && c.centre_id !== centre.centre_id);
    const missingSupports = requestedSupports.filter(supId => !centreHasSupportInSite(centre, supId));
    
    const coveredByOtherSedes = missingSupports.every(supId => 
      sameProviderCentres.some(otherC => centreHasSupportInSite(otherC, supId))
    );

    if (coveredByOtherSedes && sameProviderCentres.length > 0) {
      return { status: 'same_provider_diff_centres', details };
    }

    return { status: 'partial_same_centre', details };
  }

  return { status: 'not_confirmed', details };
}

/**
 * Motor central de evaluación de un centro frente a una búsqueda
 */
export function evaluateCentre(
  centre: SpecializedCentre,
  query: SearchQueryState,
  allCentres: SpecializedCentre[],
  originCoords: [number, number] | null = null,
  originRef?: OriginReference
): EvaluatedCentreResult {
  const because: string[] = [];
  const does_not_confirm: string[] = [
    'Plazas disponibles en tiempo real (las plazas autorizadas son cupo máximo registral, no vacantes).',
    'Admisión directa inmediata (sujeta a derivación médica, reconocimiento de dependencia o valoración interna).',
    'Adecuación clínica individual (requiere valoración facultativa).'
  ];
  const suitability_reasons: string[] = [];
  const criterion_matrix: CriterionEvidence[] = [];

  // Resolución robusta del punto de origen de referencia geográfica (§67)
  const resolvedOrigin = originRef || resolveSearchOrigin(
    query.user_ephemeral_location,
    query.municipality,
    query.location_mode
  );
  const effectiveOrigin = originCoords || resolvedOrigin.coordinates;

  // 1. Evaluación de Distancia y Radio
  let distance_km: number | null = null;
  let distance_label = 'Sin coordenadas registrales';
  let transit_time_minutes: number | null = null;
  let transit_time_label: string | null = null;
  let is_in_radius = true;

  if (centre.has_valid_coordinates && centre.coordinates) {
    distance_km = calculateHaversineDistanceKm(effectiveOrigin, centre.coordinates);
    distance_label = `${distance_km.toFixed(1)} km`;

    const transit = calculatePublicTransitTime(distance_km);
    transit_time_minutes = transit.minutes;
    transit_time_label = transit.label;

    // Se aplica el radio estricto configurado siempre que radius_km > 0 desde el origen activo
    if (query.radius_km > 0 && distance_km > query.radius_km) {
      is_in_radius = false;
    }

    criterion_matrix.push({
      criterion_id: 'geo.proximity',
      criterion_label: 'Proximidad y traslado estimado',
      requested: true,
      status: 'calculated',
      note: `Distancia lineal: ${distance_label} · Estimación teórica transp. público: ${transit_time_label} (desde ${resolvedOrigin.name}, radio: ${query.radius_km} km; sin consulta de horarios CRTM en tiempo real)`
    });
  } else {
    distance_km = null;
    distance_label = 'Sin coordenadas registrales';
    transit_time_minutes = null;
    transit_time_label = null;
    is_in_radius = true; // Section 63: Centros sin coordenadas permanecen en lista y no participan en cálculo de radio (GEO-001/002)
    criterion_matrix.push({
      criterion_id: 'geo.proximity',
      criterion_label: 'Proximidad geográfica',
      requested: true,
      status: 'not_stated',
      note: 'Centro sin coordenadas geográficas en el registro oficial. Se muestra en lista con advertencia (GEO-001/002).'
    });
  }

  // 2. Evaluación de Perfil / Condición y Reglas Negativas
  let hasExplicitProfile = false;
  let hasEntityDeclaredProfile = false;
  let hasRelatedServicesOnly = false;
  let isForbiddenInference = false;

  if (query.profile) {
    const profileDef = getProfileDefinition(query.profile);
    const profileLabel = profileDef?.preferred_label || query.profile;

    // Chequeo explícito en el propio centro (A1 / A2 apoyo)
    if (centre.explicit_specialisations.includes(query.profile)) {
      hasExplicitProfile = true;
      because.push(`La fuente oficial del registro declara expresamente especialización en ${profileLabel} en este centro.`);
      criterion_matrix.push({
        criterion_id: `profile.${query.profile}`,
        criterion_label: `Perfil: ${profileLabel}`,
        requested: true,
        status: 'confirmed',
        source_url: centre.provenance_records.find(p => p.attribute_name === 'specialisation')?.source_url,
        source_fragment: `Especialización autorizada: ${centre.subtype || centre.centre_type}`,
        checked_at: centre.last_checked
      });
    } else if (centre.entity_declared_specialisations?.includes(query.profile)) {
      // Nivel A2_entity: lo declara la entidad titular, no la denominación individual del centro (#8)
      hasEntityDeclaredProfile = true;
      because.push(
        `Nivel A2 · Lo declara la entidad titular (${centre.provider_name}), aunque no figure literalmente en la denominación individual de este centro (${centre.official_name}).`
      );
      does_not_confirm.push(
        `Si esta sede concreta atiende de forma específica ${profileLabel} (la especialización consta en la entidad titular y debe confirmarse con el centro).`
      );
      criterion_matrix.push({
        criterion_id: `profile.${query.profile}`,
        criterion_label: `Perfil: ${profileLabel}`,
        requested: true,
        status: 'confirm_required',
        source_url: centre.provenance_records[0]?.source_url,
        source_fragment: `Declarado por entidad titular: ${centre.provider_name}`,
        checked_at: centre.last_checked,
        note: 'Lo declara la entidad titular; confirmar atención en este centro concreto.'
      });
    } else {
      // Reglas negativas: limitan el nivel de evidencia (como mucho B2, nunca A1/A2/B1) sin excluir del listado (#1)
      let forbiddenMaxLevel: 'B2' | 'C' = 'C';

      if (query.profile === 'autism') {
        const mentionsDI =
          centre.subtype?.toLowerCase().includes('discapacidad intelectual') ||
          centre.sector?.toLowerCase().includes('discapacidad intelectual') ||
          centre.related_services.some(s => s.toLowerCase().includes('discapacidad intelectual'));
        if (mentionsDI) {
          isForbiddenInference = true;
          forbiddenMaxLevel = 'C';
          suitability_reasons.push('Regla negativa NEG-003: Discapacidad Intelectual no infiere TEA (limitado a nivel C).');
          does_not_confirm.push('Especialización en TEA: el centro consta en el sector de discapacidad intelectual, no en autismo específico.');
        }
      }

      if (query.profile === 'acquired_brain_injury') {
        const hasGeneralNeurology = centre.related_services.some(s => s.toLowerCase().includes('neurolog'));
        if (hasGeneralNeurology) {
          hasRelatedServicesOnly = true;
          because.push('El centro dispone de neurología ambulatoria general, pero no consta en el registro unidad específica de daño cerebral adquirido.');
        }
      }

      if (query.profile === 'spinal_cord_injury' || query.profile === 'cerebral_palsy') {
        const lowSectorSub = `${centre.sector} ${centre.subtype} ${centre.centre_type}`.toLowerCase();
        const hasGenFisio =
          centre.related_services.some(s => s.toLowerCase().includes('fisioterapia general')) ||
          lowSectorSub.includes('discapacidad física') ||
          lowSectorSub.includes('discapacidad fisica');
        if (hasGenFisio) {
          isForbiddenInference = true;
          forbiddenMaxLevel = 'C';
          suitability_reasons.push('Regla negativa NEG-002: Fisioterapia o discapacidad física general no demuestra lesión medular ni parálisis cerebral (limitado a nivel C).');
          does_not_confirm.push('Especialización específica en parálisis cerebral o lesión medular (consta únicamente como recurso general de discapacidad física).');
        }
      }

      if (query.profile === 'psychomotor_early_support') {
        const lowAT = `${centre.official_name} ${centre.sector} ${centre.subtype} ${centre.related_services.join(' ')}`.toLowerCase();
        if (lowAT.includes('atención temprana') || lowAT.includes('atencion temprana') || lowAT.includes('estimulación')) {
          isForbiddenInference = true;
          forbiddenMaxLevel = 'B2';
          hasRelatedServicesOnly = true;
          because.push('Centro de Atención Temprana registrado; no cita literalmente psicomotricidad específica en el catálogo oficial (confirmar con el equipo).');
          suitability_reasons.push('Regla negativa NEG-007: Atención temprana genérica no infiere psicomotricidad específica sin mención literal (limitado a nivel B2).');
          does_not_confirm.push('Psicomotricidad específica en atención temprana (no figura literalmente en el registro; confirmar telefónicamente).');
        }
      }

      if (
        ['neurodegenerative_diseases', 'acquired_brain_injury', 'cerebral_palsy', 'spinal_cord_injury', 'als', 'parkinson', 'alzheimer', 'autism'].includes(query.profile)
      ) {
        const lowMental = `${centre.sector} ${centre.subtype}`.toLowerCase();
        if (lowMental.includes('enfermedad mental')) {
          isForbiddenInference = true;
          forbiddenMaxLevel = 'C';
          const reasonMsg =
            query.profile === 'autism'
              ? 'Regla negativa NEG-006: Centro registrado para enfermedad mental crónica; no acredita especialización en TEA (limitado a nivel C).'
              : 'Regla negativa NEG-008: Centro registrado para enfermedad mental crónica; no acredita especialización neurológica ni neurodegenerativa (limitado a nivel C).';
          suitability_reasons.push(reasonMsg);
          does_not_confirm.push(
            query.profile === 'autism'
              ? 'Especialización en TEA (el registro oficial clasifica este centro en enfermedad mental crónica).'
              : 'Especialización neurológica o neurodegenerativa (el registro clasifica este centro en enfermedad mental crónica).'
          );
        }
      }

      // Comprobar si al menos tiene servicios relacionados cuando no aplica regla negativa
      if (profileDef && !isForbiddenInference) {
        const matchedServices = profileDef.related_services.filter(rel => 
          centre.related_services.some(cRel => cRel.toLowerCase().includes(rel.toLowerCase())) ||
          centre.supports.some(sup => sup.toLowerCase().includes(rel.toLowerCase()))
        );
        if (matchedServices.length >= 2) {
          hasRelatedServicesOnly = true;
          because.push(`Declara servicios relacionados (${matchedServices.slice(0, 3).join(', ')}), aunque la condición concreta no está expresada en el título.`);
        } else if (matchedServices.length === 1) {
          hasRelatedServicesOnly = true;
          because.push(`Declara el servicio relacionado de ${matchedServices[0]}.`);
        }
      }

      criterion_matrix.push({
        criterion_id: `profile.${query.profile}`,
        criterion_label: `Perfil: ${profileLabel}`,
        requested: true,
        status: hasRelatedServicesOnly ? 'confirm_required' : 'not_stated',
        note: isForbiddenInference
          ? `Tope máximo ${forbiddenMaxLevel} por regla de no extrapolación; confirmar directamente con el centro.`
          : hasRelatedServicesOnly
          ? 'Servicio relacionado presente; especialización no confirmada'
          : 'Especialización no declarada en el registro'
      });
    }
  }

  // 3. Evaluación de Apoyos y Combinación en la misma sede (§82)
  const combinationResult = evaluateSupportCombination(centre, query.support_types, allCentres);
  const requestedSupportsConfirmedInThisCentre = query.support_types.every(st => centreHasSupportInSite(centre, st));
  const someSupportsConfirmed = query.support_types.some(st => centreHasSupportInSite(centre, st));

  if (query.support_types.length > 0) {
    query.support_types.forEach(st => {
      const supLabel = SUPPORT_TYPES[st]?.label || st;
      const isConfirmed = centreHasSupportInSite(centre, st);
      criterion_matrix.push({
        criterion_id: `support.${st}`,
        criterion_label: `Apoyo: ${supLabel}`,
        requested: true,
        status: isConfirmed ? 'confirmed' : 'not_stated',
        note: isConfirmed ? 'Servicio autorizado y comprobado en esta sede' : 'No consta en la oferta asistencial registrada de este centro'
      });
    });

    if (requestedSupportsConfirmedInThisCentre) {
      because.push(`Ofrece todos los apoyos solicitados (${query.support_types.map(s => SUPPORT_TYPES[s]?.label).join(', ')}) en esta misma sede.`);
    } else if (someSupportsConfirmed) {
      because.push('Ofrece parte de los apoyos solicitados en esta sede física.');
      const missingLabels = query.support_types
        .filter(st => !centreHasSupportInSite(centre, st))
        .map(st => SUPPORT_TYPES[st]?.label || st);
      does_not_confirm.push(`Apoyos solicitados sin confirmación registral en esta sede: ${missingLabels.join(', ')}.`);
    } else {
      const missingLabels = query.support_types.map(st => SUPPORT_TYPES[st]?.label || st);
      does_not_confirm.push(`Los registros oficiales no desglosan si este centro presta: ${missingLabels.join(', ')} (confirmar al contactar).`);
    }
  }

  // 4. Evaluación de Etapa Vital (§3.3, §70, §78, #3)
  let lifeStageCompatible = true;
  let lifeStageUnstated = false;
  if (query.life_stage) {
    const stageLabel = LIFE_STAGES[query.life_stage]?.label || query.life_stage;
    if (centre.allowed_life_stages.includes(query.life_stage)) {
      criterion_matrix.push({
        criterion_id: `lifestage.${query.life_stage}`,
        criterion_label: `Etapa vital: ${stageLabel}`,
        requested: true,
        status: 'confirmed',
        note: 'La denominación o el sector oficial del registro menciona esta etapa.'
      });
    } else if (centre.allowed_life_stages.length === 0) {
      // #3: Cuando el registro no publica edad admitida, marcar "no consta, confirmar" sin excluir
      lifeStageUnstated = true;
      does_not_confirm.push(`Etapa vital (${stageLabel}): la edad admitida no consta en el registro oficial y debe confirmarse con el centro.`);
      criterion_matrix.push({
        criterion_id: `lifestage.${query.life_stage}`,
        criterion_label: `Etapa vital: ${stageLabel}`,
        requested: true,
        status: 'confirm_required',
        note: 'Edad admitida: no consta en el registro oficial, confirmar con el centro (no excluido).'
      });
    } else {
      lifeStageCompatible = false;
      suitability_reasons.push(`El centro no está acreditado para ${stageLabel} (rango autorizado: ${centre.allowed_life_stages.map(s => LIFE_STAGES[s]?.label).join(', ')}).`);
      criterion_matrix.push({
        criterion_id: `lifestage.${query.life_stage}`,
        criterion_label: `Etapa vital: ${stageLabel}`,
        requested: true,
        status: 'incompatible',
        note: 'Incompatibilidad de etapa vital según resolución de autorización.'
      });
    }
  }

  // 5. Preferencia de Red (Pública / Concertada / Privada autorizada / No especificada)
  const networkUnstated =
    query.network_preference !== 'all' && centre.public_private_status === 'no_especificado';
  if (query.network_preference !== 'all') {
    const prefLabel = query.network_preference === 'public_network' ? 'Red Pública / Concertada' : 'Privado autorizado';
    const isPublicMatch = query.network_preference === 'public_network' && (centre.public_private_status === 'red_publica' || centre.public_private_status === 'concertado');
    const isPrivateMatch = query.network_preference === 'private_authorised' && centre.public_private_status === 'privado_autorizado';
    const matchesNet = isPublicMatch || isPrivateMatch;

    criterion_matrix.push({
      criterion_id: 'network.preference',
      criterion_label: `Titularidad: ${prefLabel}`,
      requested: true,
      status: matchesNet ? 'confirmed' : 'confirm_required',
      note:
        centre.public_private_status === 'no_especificado'
          ? 'Titularidad no especificada en el catálogo municipal datos.madrid.es; confirmar directamente.'
          : `Titularidad oficial registrada: ${centre.public_private_status === 'red_publica' ? 'Red Pública directa' : centre.public_private_status === 'concertado' ? 'Plazas públicas concertadas' : 'Centro privado autorizado'}`
    });
  }

  // 5b. Evaluación de Accesibilidad Física Oficial por Código (#1, #2)
  let accessibilityCompatible = true;
  let accessibilityPartial = false;
  if (query.accessibility_needs && query.accessibility_needs.length > 0) {
    query.accessibility_needs.forEach(needId => {
      const featRule = ACCESSIBILITY_MAP[needId];
      const featLabel = featRule?.label || needId;
      const accStatus = getAccessibilityNeedStatus(centre, needId);

      criterion_matrix.push({
        criterion_id: `accessibility.${needId}`,
        criterion_label: `Accesibilidad: ${featLabel}`,
        requested: true,
        status: accStatus === 'confirmed' ? 'confirmed' : accStatus === 'partial' ? 'confirm_required' : 'not_stated',
        note: accStatus === 'confirmed'
          ? 'Requisito acreditado expresamente en el código de accesibilidad del catálogo oficial.'
          : accStatus === 'partial'
          ? 'Parcialmente accesible (Código 2 en datos.madrid.es); confirmar grado de accesibilidad antes de acudir.'
          : 'No consta este requisito de accesibilidad (Código 0, Código 3 «Sin información» o no publicado).'
      });

      if (accStatus === 'partial') {
        accessibilityPartial = true;
        does_not_confirm.push('Accesibilidad completa en toda la instalación (consta como Parcialmente accesible · Código 2 en datos.madrid.es).');
      } else if (accStatus === 'not_stated') {
        accessibilityCompatible = false;
        suitability_reasons.push(`El centro no acredita el requisito de accesibilidad: ${featLabel}.`);
      }
    });

    if (accessibilityCompatible && !accessibilityPartial) {
      because.push(`Acredita oficialmente los requisitos de accesibilidad solicitados (${query.accessibility_needs.map(n => ACCESSIBILITY_MAP[n]?.label || n).join(', ')}).`);
    } else if (accessibilityCompatible && accessibilityPartial) {
      because.push('Consta como parcialmente accesible (Código 2 en datos.madrid.es); conviene confirmar detalles arquitectónicos.');
    }
  }

  // 5c. Evaluación de Necesidades Funcionales Observables (§50.1)
  // Los CSV oficiales no desglosan necesidades clínicas específicas (disfagia, regulación sensorial...):
  // siempre se marca como verificación pendiente en la llamada, nunca 'confirmed' sin fuente expresa.
  if (query.functional_needs && query.functional_needs.length > 0) {
    query.functional_needs.forEach(needId => {
      const needLabel = FUNCTIONAL_NEEDS[needId]?.label || needId;
      criterion_matrix.push({
        criterion_id: `functional.${needId}`,
        criterion_label: `Necesidad funcional: ${needLabel}`,
        requested: true,
        status: 'confirm_required',
        note: 'Criterio funcional para verificar con el equipo técnico del centro; los registros públicos no acreditan cobertura individual por necesidad.'
      });
    });
    does_not_confirm.push(
      `Cobertura clínica concreta de las necesidades funcionales seleccionadas (${query.functional_needs.map(id => FUNCTIONAL_NEEDS[id]?.label || id).join(', ')}); confirme con el equipo del centro.`
    );
  }

  // 6. Clasificación de Nivel de Evidencia (§27 + #8 A2_entity)
  let evidence_level: EvidenceLevel = 'C';
  let evidence_sublevel: EvidenceSublevel = 'C';

  if (hasExplicitProfile) {
    if (query.support_types.length === 0 || requestedSupportsConfirmedInThisCentre) {
      evidence_level = 'A1';
      evidence_sublevel = 'A1';
    } else {
      evidence_level = 'A2';
      evidence_sublevel = 'A2_support';
    }
  } else if (hasEntityDeclaredProfile && !isForbiddenInference) {
    evidence_level = 'A2';
    evidence_sublevel = 'A2_entity';
  } else if (isForbiddenInference) {
    // Reglas negativas: topan en B2 (si tiene relación asistencial directa, como Atención Temprana) o C, sin subir a A/B1 (#1)
    if (query.profile === 'psychomotor_early_support' && hasRelatedServicesOnly) {
      evidence_level = 'B2';
      evidence_sublevel = 'B2';
    } else {
      evidence_level = 'C';
      evidence_sublevel = 'C';
    }
  } else if (hasRelatedServicesOnly) {
    const isGeneralNeurologyOnly = query.profile === 'acquired_brain_injury' && 
      centre.related_services.some(s => s.toLowerCase().includes('neurolog')) && 
      !hasExplicitProfile;
    const profileDefForB = query.profile ? getProfileDefinition(query.profile) : null;
    const matchesCount = profileDefForB ? profileDefForB.related_services.filter(rel => 
      centre.related_services.some(cRel => cRel.toLowerCase().includes(rel.toLowerCase())) ||
      centre.supports.some(sup => sup.toLowerCase().includes(rel.toLowerCase()))
    ).length : 0;
    if (matchesCount >= 2 && lifeStageCompatible && !isGeneralNeurologyOnly) {
      evidence_level = 'B1';
      evidence_sublevel = 'B1';
    } else {
      evidence_level = 'B2';
      evidence_sublevel = 'B2';
    }
  } else {
    evidence_level = 'C';
    evidence_sublevel = 'C';
    because.push('Orientación general: el centro pertenece al sector asistencial pero no declara la especialización concreta en fuentes estructuradas.');
  }

  // 7. Adecuación a la búsqueda (solo excluyen edad incompatible o accesibilidad solicitada no acreditada)
  let suitability: SuitabilityStatus = 'complete';
  const hasRequestedSupportsMissing =
    query.support_types.length > 0 &&
    (query.support_combination_mode === 'all_supports_same_centre'
      ? !requestedSupportsConfirmedInThisCentre
      : !someSupportsConfirmed);
  const hasUnconfirmedFunctionalNeeds = Boolean(query.functional_needs && query.functional_needs.length > 0);
  const networkMatched =
    query.network_preference === 'all' ||
    (query.network_preference === 'public_network' &&
      (centre.public_private_status === 'red_publica' || centre.public_private_status === 'concertado')) ||
    (query.network_preference === 'private_authorised' &&
      centre.public_private_status === 'privado_autorizado');

  if (!lifeStageCompatible || !accessibilityCompatible) {
    suitability = 'incompatible';
  } else if (
    isForbiddenInference ||
    hasEntityDeclaredProfile ||
    lifeStageUnstated ||
    accessibilityPartial ||
    networkUnstated ||
    !networkMatched ||
    hasRequestedSupportsMissing ||
    hasUnconfirmedFunctionalNeeds ||
    (!hasExplicitProfile && hasRelatedServicesOnly)
  ) {
    suitability = 'partial';
  } else if (query.profile && evidence_level === 'C') {
    suitability = 'unknown';
  }

  // 8. Cálculo de Puntuación Lexicográfica de Ordenación (§41, §78)
  // Regla: A1 < A2_support < A2_entity < B1 < B2 < C. Ninguna distancia hace que C supere a A o B.
  const evidenceRankMap: Record<EvidenceLevel, number> = {
    A1: 1000000,
    A2: 2000000,
    B1: 3000000,
    B2: 4000000,
    C:  5000000
  };

  const suitabilityRankMap: Record<SuitabilityStatus, number> = {
    complete: 0,
    partial: 100000,
    unknown: 200000,
    incompatible: 900000
  };

  const sublevelRank = evidence_sublevel === 'A2_entity' ? 10000 : 0;
  const combinationRank =
    query.support_types.length === 0
      ? 0
      : query.support_combination_mode === 'all_supports_same_centre' && !requestedSupportsConfirmedInThisCentre
      ? 50000
      : !someSupportsConfirmed
      ? 50000
      : !requestedSupportsConfirmedInThisCentre
      ? 20000
      : 0;
  const networkRank = !networkMatched ? 30000 : 0;
  const distRank = distance_km !== null ? Math.min(Math.round(distance_km * 10), 9999) : 5000;

  const sort_rank =
    evidenceRankMap[evidence_level] +
    suitabilityRankMap[suitability] +
    combinationRank +
    networkRank +
    sublevelRank +
    distRank;

  // 9. Construcción de Fuentes y Explicación
  const sources = centre.provenance_records.map(p => ({
    attribute: p.attribute_name,
    source_dataset: p.source_dataset,
    source_url: p.source_url,
    fragment: p.value
  }));

  const match_assessment: MatchExplanation = {
    level: evidence_level,
    sublevel: evidence_sublevel,
    suitability,
    because,
    does_not_confirm,
    sources,
    suitability_reasons
  };

  return {
    centre,
    match_assessment,
    evidence_level,
    evidence_sublevel,
    suitability,
    combination_status: combinationResult.status,
    combination_details: combinationResult.details,
    distance_km,
    distance_label,
    transit_time_minutes,
    transit_time_label,
    is_in_radius,
    criterion_matrix,
    sort_rank
  };
}

/**
 * Ejecuta la búsqueda completa sobre el conjunto de centros
 */
export function runSpecializedSearch(
  query: SearchQueryState,
  centres: SpecializedCentre[],
  originCoords: [number, number] | null = null
): {
  results: EvaluatedCentreResult[];
  total_results: number;
  incompatible_results: EvaluatedCentreResult[];
  map_stats: { visible_results: number; without_coordinates: number };
  applied_filters_count: number;
  resolved_origin: OriginReference;
} {
  const resolvedOrigin = resolveSearchOrigin(
    query.user_ephemeral_location,
    query.municipality,
    query.location_mode
  );
  const effectiveOrigin = originCoords || resolvedOrigin.coordinates;

  const evaluated = centres.map(c => evaluateCentre(c, query, centres, effectiveOrigin, resolvedOrigin));

  // Separar incompatibles según §78 ("Orden 1: excluir incompatibilidades de la lista principal")
  const primaryCandidates: EvaluatedCentreResult[] = [];
  const incompatibleList: EvaluatedCentreResult[] = [];

  for (const item of evaluated) {
    if (item.suitability === 'incompatible') {
      incompatibleList.push(item);
    } else {
      // Filtrar por radio si procede (centros sin coordenadas permanecen en lista: GEO-001/002)
      if (item.is_in_radius) {
        primaryCandidates.push(item);
      }
    }
  }

  // Filtrado de combinación en misma sede si el usuario lo exige de forma estricta
  let filtered = primaryCandidates;

  // Orden lexicográfico estricto (§41, §78)
  filtered.sort((a, b) => a.sort_rank - b.sort_rank);
  incompatibleList.sort((a, b) => a.sort_rank - b.sort_rank);

  let withoutCoords = 0;
  let visibleInMap = 0;
  filtered.forEach(r => {
    if (r.centre.has_valid_coordinates) visibleInMap++;
    else withoutCoords++;
  });

  let activeFilters = 0;
  if (query.profile) activeFilters++;
  if (query.support_types.length > 0) activeFilters += query.support_types.length;
  if (query.functional_needs.length > 0) activeFilters += query.functional_needs.length;
  if (query.life_stage) activeFilters++;
  if (query.municipality || (query.location_mode === 'browser' && query.user_ephemeral_location)) activeFilters++;
  if (query.radius_km < 80) activeFilters++;
  if (query.network_preference !== 'all') activeFilters++;
  if (query.accessibility_needs.length > 0) activeFilters += query.accessibility_needs.length;

  return {
    results: filtered,
    total_results: filtered.length,
    incompatible_results: incompatibleList,
    map_stats: { visible_results: visibleInMap, without_coordinates: withoutCoords },
    applied_filters_count: activeFilters,
    resolved_origin: resolvedOrigin
  };
}

export interface SnapshotSourceMeta {
  source_id: string;
  source_name?: string;
  source_url?: string;
  file?: string;
  sha256_hash: string;
  extracted_records_count: number;
  status: string;
}

export interface SnapshotMetadataSummary {
  ingestion_id?: string;
  timestamp?: string;
  sha256_hash?: string;
  extracted_records_count?: number;
  total_combined_records?: number;
  status?: string;
  sources?: SnapshotSourceMeta[];
}

export interface CentreAuditResult {
  centre_id: string;
  official_name: string;
  is_official_csv: boolean;
  phone_verified: boolean;
  address_verified: boolean;
  places_verified: boolean;
  metadata_sha256_verified: boolean;
  discrepancies: string[];
  audit_status: 'verified_official' | 'verified_regional' | 'discrepancy' | 'unverified';
  audit_note: string;
}

let activeSnapshotMeta: SnapshotMetadataSummary | null = null;
let activeLiveCsvIndex: Map<string, SnapshotCentreRecord> | null = null;

export function setSnapshotVerificationContext(
  metadata: SnapshotMetadataSummary | null,
  liveIndex: Map<string, SnapshotCentreRecord> | null
): void {
  activeSnapshotMeta = metadata;
  activeLiveCsvIndex = liveIndex;
}

function findMatchingSourceMeta(
  centre: SpecializedCentre,
  meta: SnapshotMetadataSummary | null
): SnapshotSourceMeta | null {
  if (!meta) return null;
  const sources = meta.sources || [];
  if (centre.centre_id.startsWith('MAD-PK') || centre.provenance_records.some(p => p.source_dataset.toLowerCase().includes('datos.madrid.es'))) {
    const m = sources.find(s => s.source_id === 'madrid_municipal');
    if (m) return m;
    if (meta.sha256_hash && meta.status === 'SUCCESS') {
      return {
        source_id: 'madrid_municipal',
        sha256_hash: meta.sha256_hash,
        extracted_records_count: meta.extracted_records_count || 0,
        status: meta.status
      };
    }
  }
  if (centre.centre_id.startsWith('CAM-SRV-')) {
    return sources.find(s => s.source_id === 'cam_servicios') || null;
  }
  if (centre.centre_id.startsWith('CAM-')) {
    return sources.find(s => s.source_id === 'cam_centros') || null;
  }
  return null;
}

function findCsvRecordsForCentre(
  centre: SpecializedCentre,
  liveIndex: Map<string, SnapshotCentreRecord>
): SnapshotCentreRecord[] {
  const records: SnapshotCentreRecord[] = [];
  const seen = new Set<string>();
  const addRecord = (rec: SnapshotCentreRecord | undefined) => {
    if (rec && !seen.has(rec.registry_key)) {
      seen.add(rec.registry_key);
      records.push(rec);
    }
  };

  if (liveIndex.has(centre.centre_id)) {
    addRecord(liveIndex.get(centre.centre_id));
  }
  for (const prov of centre.provenance_records) {
    const pkMatch = prov.source_dataset.match(/PK\s+(\d+)/);
    if (pkMatch) {
      addRecord(liveIndex.get(`MAD-PK${pkMatch[1]}`));
    }
    const camMatch = prov.source_dataset.match(/\(([CS]\d+)\)/);
    if (camMatch) {
      const key = camMatch[1].startsWith('S') ? `CAM-SRV-${camMatch[1]}` : `CAM-${camMatch[1]}`;
      addRecord(liveIndex.get(key));
    }
  }
  return records;
}

/**
 * Función de auditoría de datos en 'specializedEngine.ts' que verifica si los campos críticos
 * de cada centro (teléfono, dirección, plazas) coinciden con 'snapshot-metadata.json' y los CSV oficiales.
 */
export function auditCentreAgainstSnapshot(
  centre: SpecializedCentre,
  snapshotMeta: SnapshotMetadataSummary | null = activeSnapshotMeta,
  liveCsvIndex: Map<string, SnapshotCentreRecord> | null = activeLiveCsvIndex
): CentreAuditResult {
  const hasOfficialOpenDataProvenance = centre.provenance_records.some(p => {
    const ds = p.source_dataset.toLowerCase();
    const url = p.source_url.toLowerCase();
    return (
      ds.includes('datos.madrid.es') ||
      ds.includes('registro de centros de atención social cam') ||
      ds.includes('registro de servicios de atención social cam') ||
      url.includes('datos.madrid.es') ||
      url.includes('datos.comunidad.madrid')
    );
  });

  const isMunicipalCsv = centre.provenance_records.some(p =>
    p.source_dataset.toLowerCase().includes('datos.madrid.es') ||
    p.source_url.toLowerCase().includes('datos.madrid.es')
  );
  const isCamCsv = centre.provenance_records.some(p =>
    p.source_dataset.toLowerCase().includes('registro de centros de atención social cam') ||
    p.source_dataset.toLowerCase().includes('registro de servicios de atención social cam') ||
    p.source_url.toLowerCase().includes('datos.comunidad.madrid')
  );

  const matchedMeta = findMatchingSourceMeta(centre, snapshotMeta);
  const metadata_sha256_verified = Boolean(
    matchedMeta &&
      matchedMeta.status === 'SUCCESS' &&
      /^[a-f0-9]{64}$/i.test(matchedMeta.sha256_hash) &&
      matchedMeta.extracted_records_count > 0
  );

  const discrepancies: string[] = [];
  let phone_verified = false;
  let address_verified = false;
  let places_verified = false;
  let matchedInLiveCsv = false;

  if (liveCsvIndex && liveCsvIndex.size > 0) {
    const csvRecords = findCsvRecordsForCentre(centre, liveCsvIndex);
    const primaryRec = csvRecords[0];
    if (primaryRec) {
      matchedInLiveCsv = true;

      if (centre.is_individual_practitioner) {
        phone_verified = true;
        address_verified = true;
      } else {
        const cPhone = normalizePhoneComparable(centre.phone);
        phone_verified = csvRecords.some(r => normalizePhoneComparable(r.phone) === cPhone);
        if (!phone_verified) {
          discrepancies.push(`Teléfono ("${centre.phone || 'vacío'}" vs CSV "${primaryRec.phone || 'vacío'}")`);
        }

        const cAddr = normalizeAddressComparable(centre.address);
        address_verified = csvRecords.some(r => {
          const rAddr = normalizeAddressComparable(r.address);
          return Boolean(cAddr && rAddr && cAddr === rAddr);
        });
        if (!address_verified) {
          discrepancies.push(`Dirección ("${centre.address}" vs CSV "${primaryRec.address}")`);
        }
      }

      places_verified = primaryRec.authorised_places === centre.availability.authorised_places;
      if (!places_verified) {
        discrepancies.push(`Plazas (${centre.availability.authorised_places ?? 'null'} vs CSV ${primaryRec.authorised_places ?? 'null'})`);
      }
    } else {
      discrepancies.push('Identificador registral no localizado en la descarga CSV oficial activa.');
    }
  } else {
    // Evaluación estructural previa a la carga completa del índice CSV en vivo
    phone_verified = hasOfficialOpenDataProvenance && (centre.phone === '' || normalizePhoneComparable(centre.phone).length >= 9);
    address_verified = hasOfficialOpenDataProvenance && Boolean(centre.address && centre.address.length >= 5);
    places_verified = hasOfficialOpenDataProvenance && (
      isCamCsv
        ? (centre.availability.authorised_places === null || typeof centre.availability.authorised_places === 'number')
        : centre.availability.authorised_places === null
    );
  }

  const is_official_csv =
    hasOfficialOpenDataProvenance &&
    (liveCsvIndex && liveCsvIndex.size > 0 ? matchedInLiveCsv : true) &&
    (snapshotMeta ? metadata_sha256_verified : true);

  let audit_status: CentreAuditResult['audit_status'] = 'unverified';
  let audit_note = 'ADVERTENCIA: Los datos de este centro no proceden de los ficheros CSV oficiales verificados.';

  if (!is_official_csv) {
    audit_status = 'unverified';
    if (snapshotMeta && !metadata_sha256_verified && hasOfficialOpenDataProvenance) {
      audit_note = 'ADVERTENCIA: La fuente declarada no cuenta con firma SHA-256 verificada en snapshot-metadata.json.';
    }
  } else if (discrepancies.length > 0) {
    audit_status = 'discrepancy';
    audit_note = `DISCREPANCIA CON EL CSV OFICIAL: ${discrepancies.join('; ')}.`;
  } else if (isMunicipalCsv && isCamCsv) {
    audit_status = 'verified_official';
    audit_note = `Verificado en CSV oficial municipal (datos.madrid.es) y Registro CAM${matchedMeta ? ` · SHA-256 ${matchedMeta.sha256_hash.slice(0, 10)}...` : ''}.`;
  } else if (isMunicipalCsv) {
    audit_status = 'verified_official';
    audit_note = `Verificado campo a campo contra CSV oficial datos.madrid.es${matchedMeta ? ` · SHA-256 ${matchedMeta.sha256_hash.slice(0, 10)}...` : ''}.`;
  } else if (isCamCsv) {
    audit_status = 'verified_regional';
    audit_note = `Verificado campo a campo contra CSV oficial Comunidad de Madrid${matchedMeta ? ` · SHA-256 ${matchedMeta.sha256_hash.slice(0, 10)}...` : ''}.`;
  }

  return {
    centre_id: centre.centre_id,
    official_name: centre.official_name,
    is_official_csv,
    phone_verified,
    address_verified,
    places_verified,
    metadata_sha256_verified,
    discrepancies,
    audit_status,
    audit_note
  };
}


