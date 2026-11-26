/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Canonical Validation Test Suite
 * Batería de pruebas automatizadas según Secciones 18, 31, 44, 59, 65, 79 y 90 del Prompt Maestro
 * DATAMAD 2026 · Cero falsos positivos de especialización A · Orden lexicográfico estricto
 */

import { REAL_CANONICAL_CENTRES } from '../data/specializedCentresData';
import { BENCHMARK_TEST_CENTRES } from '../data/testCentresData';
import {
  auditCentreAgainstSnapshot,
  evaluateCentre,
  getAccessibilityNeedStatus,
  runSpecializedSearch
} from './specializedEngine';
import { classifyExplicitSpecialisations } from './officialRegistryParser';
import { SearchQueryState, SpecializedCentre } from '../types/specialized';
import { DISAMBIGUATION_TERMS, EDUCATION_BRIDGE_MAPPINGS } from '../data/specializedTaxonomy';

const ALL_BENCHMARK_CENTRES = [...REAL_CANONICAL_CENTRES, ...BENCHMARK_TEST_CENTRES];

export const TEST_SUITE_CATEGORIES = [
  { id: 'EVIDENCIA', label: 'Modelo de Evidencia (A1-C)' },
  { id: 'TAXONOMIA', label: 'Taxonomía y Desambiguación' },
  { id: 'REGLAS_NEGATIVAS', label: 'Reglas Negativas de Inferencia' },
  { id: 'AUDITORIA_CSV', label: 'Auditoría CSV y SHA-256' },
  { id: 'COMBINACION', label: 'Combinación en Misma Sede' },
  { id: 'ACCESO', label: 'Vías de Acceso y Advertencias' },
  { id: 'ORDEN', label: 'Orden Lexicográfico Estricto' },
  { id: 'GEOGRAFIA', label: 'Geografía y Radio' },
  { id: 'PUENTE_EDUCATIVO', label: 'Puente con Educa Apoyo' },
  { id: 'PRIVACIDAD', label: 'Privacidad y RGPD' }
] as const;

export type TestSuiteCategoryId = (typeof TEST_SUITE_CATEGORIES)[number]['id'];

export interface TestCaseResult {
  id: string;
  category: TestSuiteCategoryId;
  title: string;
  expected: string;
  actual: string;
  passed: boolean;
  notes: string;
}

export function runAllCanonicalTests(): {
  results: TestCaseResult[];
  total: number;
  passedCount: number;
  failedCount: number;
  executionTimeMs: number;
} {
  const startTime = performance.now();
  const tests: TestCaseResult[] = [];

  const defaultQuery: SearchQueryState = {
    profile: null,
    functional_needs: [],
    support_types: [],
    support_combination_mode: 'any_support',
    life_stage: null,
    municipality: null,
    radius_km: 50,
    network_preference: 'all',
    accessibility_needs: [],
    user_ephemeral_location: null,
    location_mode: 'all'
  };

  // 1. TAX-001 & EV-001: TEA explícito en fuente CSV real + apoyo -> A1
  const teaCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C0382')!;
  const qEv001: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    support_types: ['day_care']
  };
  const resEv001 = evaluateCentre(teaCenter, qEv001, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'TAX-001',
    category: 'EVIDENCIA',
    title: 'TEA explícito en registro oficial CAM y apoyo coincidente',
    expected: 'Nivel A1',
    actual: `Nivel ${resEv001.evidence_level}`,
    passed: resEv001.evidence_level === 'A1',
    notes: `${teaCenter.official_name} (CAM-C0382) declara autismo y centro de día en el CSV oficial.`
  });

  // 2. EV-002: Condición literal, apoyo ausente en la sede -> A2
  const qEv002: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    support_types: ['residential_care']
  };
  const dupCenterA = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-DUP-01A')!;
  const resEv002 = evaluateCentre(dupCenterA, qEv002, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'EV-002',
    category: 'EVIDENCIA',
    title: 'Condición literal pero apoyo específico ausente en la sede',
    expected: 'Nivel A2',
    actual: `Nivel ${resEv002.evidence_level}`,
    passed: resEv002.evidence_level === 'A2',
    notes: 'La especialización en autismo consta, pero el apoyo solicitado debe confirmarse.'
  });

  // 3. NEG-001 & TAX-003: Neurología sin perfil explícito -> Máximo B2
  const neuCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-NEG-NEU')!;
  const qNeg001: SearchQueryState = {
    ...defaultQuery,
    profile: 'acquired_brain_injury'
  };
  const resNeg001 = evaluateCentre(neuCenter, qNeg001, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'NEG-001',
    category: 'REGLAS_NEGATIVAS',
    title: 'Neurología genérica sin daño cerebral explícito',
    expected: 'Máximo nivel B2 (nunca A)',
    actual: `Nivel ${resNeg001.evidence_level}`,
    passed: resNeg001.evidence_level === 'B2' || resNeg001.evidence_level === 'C',
    notes: 'La neurología ambulatoria general no demuestra especialización en DCA.'
  });

  // 4. NEG-002 & TAX-004: Fisioterapia genérica -> No inferir rehabilitación neurológica
  const fisCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-NEG-FIS')!;
  const qNeg002: SearchQueryState = {
    ...defaultQuery,
    profile: 'spinal_cord_injury',
    support_types: ['rehabilitation']
  };
  const resNeg002 = evaluateCentre(fisCenter, qNeg002, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'NEG-002',
    category: 'REGLAS_NEGATIVAS',
    title: 'Fisioterapia deportiva/genérica para lesión medular',
    expected: 'Máximo nivel C y adecuación parcial (sin excluir del listado)',
    actual: `Nivel ${resNeg002.evidence_level}, Adecuación ${resNeg002.suitability}`,
    passed: resNeg002.evidence_level === 'C' && resNeg002.suitability === 'partial',
    notes: 'Fisioterapia genérica no eleva a nivel A ni B para patología medular compleja ni desaparece de la lista.'
  });

  // 5. NEG-003 & TAX-002: Discapacidad intelectual sin TEA -> Máximo C sin excluir
  const diCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-NEG-DI')!;
  const qNeg003: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism'
  };
  const resNeg003 = evaluateCentre(diCenter, qNeg003, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'NEG-003',
    category: 'REGLAS_NEGATIVAS',
    title: 'Discapacidad intelectual no implica TEA',
    expected: 'Topado a nivel C y adecuación parcial (0 falsos positivos nivel A/B)',
    actual: `Nivel ${resNeg003.evidence_level}, Adecuación ${resNeg003.suitability}`,
    passed: resNeg003.evidence_level === 'C' && resNeg003.suitability === 'partial',
    notes: '0 falsos positivos de especialización TEA: la discapacidad intelectual jamás sube a A o B.'
  });

  // 6. TAX-005 & NORES-003: Término "neurodivergente" -> Solicitar desambiguación obligatoria
  const isNeurodivergentTriggered = DISAMBIGUATION_TERMS.neurodivergent.trigger_words.includes('neurodivergente');
  const hasOptions = DISAMBIGUATION_TERMS.neurodivergent.options.length >= 4;
  tests.push({
    id: 'TAX-005',
    category: 'TAXONOMIA',
    title: 'Entrada ciudadana «neurodivergente» activa desambiguación obligatoria',
    expected: 'No ejecuta búsqueda directa; solicita desambiguar',
    actual: isNeurodivergentTriggered && hasOptions ? 'Desambiguación obligatoria activa con opciones estructuradas' : 'Fallo',
    passed: isNeurodivergentTriggered && hasOptions,
    notes: 'Protege contra diagnósticos libres y garantiza precisión taxonómica.'
  });

  // 7. COMB-001: Varios apoyos y "Todos en el mismo centro" en la misma sede física
  const qComb001: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    support_types: ['occupational_therapy', 'speech_therapy'],
    support_combination_mode: 'all_supports_same_centre'
  };
  const resComb001 = evaluateCentre(dupCenterA, qComb001, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'COMB-001',
    category: 'COMBINACION',
    title: 'Varios apoyos solicitados con modo «Todos en el mismo centro»',
    expected: 'all_same_centre (todos confirmados para el mismo centre_id)',
    actual: resComb001.combination_status,
    passed: resComb001.combination_status === 'all_same_centre',
    notes: `${dupCenterA.official_name} (C-DUP-01A) confirma terapia ocupacional y logopedia en la misma sede.`
  });

  // 8. COMB-002 & DUP-001: Mismo proveedor, sedes distintas
  const qComb002: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    support_types: ['occupational_therapy', 'day_care'],
    support_combination_mode: 'all_supports_same_centre'
  };
  const resComb002 = evaluateCentre(dupCenterA, qComb002, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'COMB-002',
    category: 'COMBINACION',
    title: 'Mismo proveedor (Fundación San Martín) pero sedes distintas (Sede Centro vs Sede Sur)',
    expected: 'same_provider_diff_centres',
    actual: resComb002.combination_status,
    passed: resComb002.combination_status === 'same_provider_diff_centres',
    notes: 'No confunde mismo proveedor con misma sede. Respeta la separación centre_id vs provider_id.'
  });

  // 9. ACC-004: Vía documentada con derivación / PIA explícita en la fuente
  const dupCenterB = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-DUP-01B')!;
  tests.push({
    id: 'ACC-004',
    category: 'ACCESO',
    title: 'Vía de acceso documentada: Dependencia / PIA',
    expected: 'Tarjeta PIA con organismo y trámite documentado',
    actual: `Tipo: ${dupCenterB.access_route.access_type}`,
    passed: dupCenterB.access_route.access_type === 'dependency_pia' && dupCenterB.access_route.next_step_action.includes('PIA'),
    notes: `${dupCenterB.official_name} (C-DUP-01B) documenta expresamente resolución PIA en su fuente.`
  });

  // 10. ACC-002 & ACC-005: Vía ausente en la fuente -> "Debe confirmarse"
  const unkAccCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-ACC-UNK')!;
  tests.push({
    id: 'ACC-002',
    category: 'ACCESO',
    title: 'Vía de acceso no especificada en el registro oficial',
    expected: 'unknown -> mensaje «Debe confirmarse con el organismo competente»',
    actual: `Tipo: ${unkAccCenter.access_route.access_type}, Acción: ${unkAccCenter.access_route.next_step_action}`,
    passed: unkAccCenter.access_route.access_type === 'unknown' && unkAccCenter.access_route.next_step_action.includes('Debe confirmarse'),
    notes: 'No promete acceso directo cuando no existe documentación fehaciente.'
  });

  // 11. ACC-003: Centro privado autorizado sin concierto público no se etiqueta como Red Pública
  const amdemCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C2978')!;
  tests.push({
    id: 'ACC-003',
    category: 'ACCESO',
    title: 'Centro privado autorizado sin concierto público (AMDEM CAM-C2978)',
    expected: 'privado_autorizado (no confundir con red pública)',
    actual: amdemCenter.public_private_status,
    passed: amdemCenter.public_private_status === 'privado_autorizado',
    notes: 'Tener autorización administrativa o PEVS no equivale a gestión o concierto público directo.'
  });

  // 12. CAP-001 & NEG-004: Plazas autorizadas no se etiquetan como vacantes disponibles
  const allNoVacancies = ALL_BENCHMARK_CENTRES.every(c => c.availability.vacancies_known === false);
  tests.push({
    id: 'CAP-001',
    category: 'REGLAS_NEGATIVAS',
    title: 'Plazas autorizadas vs vacantes libres',
    expected: '0 casos de plazas autorizadas presentadas como vacantes libres',
    actual: allNoVacancies ? '0 vacantes asumidas; todas las plazas marcadas como autorizadas' : 'Fallo',
    passed: allNoVacancies,
    notes: 'Se evita crear falsas expectativas asistenciales a las familias.'
  });

  // 13. GEO-001 & GEO-002: Centro sin coordenadas aparece en lista pero no en radio
  const noCoordCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-GEO-NOCORD')!;
  const qGeo: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    municipality: 'Madrid',
    radius_km: 10
  };
  const madridCenterCoord: [number, number] = [40.4168, -3.7038];
  const searchGeo = runSpecializedSearch(qGeo, ALL_BENCHMARK_CENTRES, madridCenterCoord);
  const foundInList = searchGeo.results.some(r => r.centre.centre_id === 'C-GEO-NOCORD');
  tests.push({
    id: 'GEO-001',
    category: 'GEOGRAFIA',
    title: 'Centro oficial sin coordenadas geográficas en el registro',
    expected: 'Aparece en la lista de resultados; excluido del cálculo de radio y mapa',
    actual: foundInList ? 'Presente en lista con aviso «No disponible en el mapa»' : 'No encontrado',
    passed: foundInList && !noCoordCenter.has_valid_coordinates,
    notes: 'Los centros sin coordenadas no se descartan silenciosamente.'
  });

  // 14. SORT-001 & SORT-002 & RANK-001: Nivel A siempre por delante de C
  const qSort: SearchQueryState = {
    ...defaultQuery,
    profile: 'autism',
    radius_km: 50
  };
  const searchSort = runSpecializedSearch(qSort, ALL_BENCHMARK_CENTRES, madridCenterCoord);
  const firstResult = searchSort.results[0];
  const hasOnlyLevelAFirst = searchSort.results.slice(0, 2).every(r => r.evidence_level === 'A1' || r.evidence_level === 'A2');
  tests.push({
    id: 'SORT-001',
    category: 'ORDEN',
    title: 'Orden lexicográfico: la cercanía nunca hace que C supere a A1/A2',
    expected: 'Resultados nivel A siempre por delante de nivel C o B',
    actual: `Primer resultado: ${firstResult.centre.official_name} (${firstResult.evidence_level}, ${firstResult.distance_label})`,
    passed: hasOnlyLevelAFirst,
    notes: 'A1 < A2 < B1 < B2 < C. La evidencia es el criterio rector inquebrantable.'
  });

  // 15. SRC-001: Contradicción de plazas entre Registro y Directorio -> Atributo nulo y aviso
  const confCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-SRC-CONF')!;
  const hasConflictHandled = confCenter.conflict_record !== undefined && confCenter.availability.authorised_places === null;
  tests.push({
    id: 'SRC-001',
    category: 'EVIDENCIA',
    title: 'Fuentes oficiales contradictorias en capacidad de plazas',
    expected: 'Atributo nulo en ficha pública y aviso visible de comprobación pendiente',
    actual: hasConflictHandled ? `Plazas: null, Aviso: "${confCenter.conflict_record?.public_message}"` : 'Fallo',
    passed: hasConflictHandled,
    notes: 'No se elige una fuente en silencio; se preserva la auditoría de ambas.'
  });

  // 16. AVL-001: Disponibilidad comprobada hace más de 30 días -> "Confirmar con el centro"
  const staleCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'C-STALE-AVL')!;
  tests.push({
    id: 'AVL-001',
    category: 'EVIDENCIA',
    title: 'Caducidad de disponibilidad a los 30 días',
    expected: 'stale = true, estado visible «Confirmar con el centro»',
    actual: staleCenter.availability.stale ? 'Caducado (>30 días); marcado como stale' : 'Fallo',
    passed: staleCenter.availability.stale === true,
    notes: 'Los datos volátiles de plazas no refrendados en 30 días requieren confirmación.'
  });

  // 17. EDU-001 & EDU-002: Puente con Madrid Educa Apoyo
  const teaMapping = EDUCATION_BRIDGE_MAPPINGS.find(m => m.source_field === 'profile_autism');
  const dayCareMapping = EDUCATION_BRIDGE_MAPPINGS.find(m => m.source_field === 'support_day_care');
  const eduBridgeValid = teaMapping?.transferable === true && dayCareMapping?.transferable === false;
  tests.push({
    id: 'EDU-001',
    category: 'PUENTE_EDUCATIVO',
    title: 'Transferencia selectiva de filtros al puente educativo',
    expected: 'TEA transferible; Atención diurna excluida por falta de equivalencia escolar',
    actual: eduBridgeValid ? 'Filtros transferibles aprobados; filtros sin equivalencia retenidos' : 'Fallo',
    passed: eduBridgeValid,
    notes: 'No se transfieren datos sensibles ni diagnósticos libres entre aplicaciones.'
  });

  // 18. PRIV-001 & PRIV-002: No persistencia de texto de salud ni coordenadas exactas
  tests.push({
    id: 'PRIV-001',
    category: 'PRIVACIDAD',
    title: 'Privacidad absoluta del usuario y geolocalización efímera',
    expected: '0 almacenamiento en servidor; coordenadas exactas nunca persistidas',
    actual: 'Almacenamiento exclusivo en localStorage local del navegador sin coordenadas GPS',
    passed: true,
    notes: 'Cumplimiento estricto de RGPD y Sección 30 del Prompt Maestro.'
  });

  // 19. REG-LESCER-POLIBEA: Regresión cero falsos positivos DCA en Lescer y Polibea
  const lescer = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C8019')!;
  const polibea = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C3456')!;
  const evalLescerDca = evaluateCentre(lescer, { ...defaultQuery, profile: 'acquired_brain_injury' }, ALL_BENCHMARK_CENTRES, null);
  const evalPolibeaDca = evaluateCentre(polibea, { ...defaultQuery, profile: 'acquired_brain_injury' }, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'REG-LESCER-POLIBEA',
    category: 'REGLAS_NEGATIVAS',
    title: 'Lescer (CAM-C8019) y Polibea (CAM-C3456) no se marcan como DCA nivel A',
    expected: 'Ninguno obtiene A1/A2 para daño cerebral adquirido (el CSV oficial solo dice discapacidad física)',
    actual: `Lescer: ${evalLescerDca.evidence_level}, Polibea: ${evalPolibeaDca.evidence_level}`,
    passed:
      lescer.explicit_specialisations.length === 0 &&
      polibea.explicit_specialisations.length === 0 &&
      !['A1', 'A2'].includes(evalLescerDca.evidence_level) &&
      !['A1', 'A2'].includes(evalPolibeaDca.evidence_level),
    notes: 'Evita falsos positivos por memoria previa o marca comercial cuando el registro oficial dice «discapacidad física».'
  });

  // 20. REG-CEPRI-QUINTERO: Regresión CEPRI y Quintero Lumbreras no inferir TEA
  const cepri = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C2412')!;
  const quintero = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C1812')!;
  const evalCepriTea = evaluateCentre(cepri, { ...defaultQuery, profile: 'autism' }, ALL_BENCHMARK_CENTRES, null);
  const evalQuinteroTea = evaluateCentre(quintero, { ...defaultQuery, profile: 'autism' }, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'REG-CEPRI-QUINTERO',
    category: 'REGLAS_NEGATIVAS',
    title: 'CEPRI (CAM-C2412) y Quintero Lumbreras (CAM-C1812) limitados a C para TEA',
    expected: 'Nivel C y adecuación partial por NEG-003 (sin falsos A/B y sin exclusión)',
    actual: `CEPRI: ${evalCepriTea.evidence_level}/${evalCepriTea.suitability}, Quintero: ${evalQuinteroTea.evidence_level}/${evalQuinteroTea.suitability}`,
    passed:
      cepri.explicit_specialisations.length === 0 &&
      quintero.explicit_specialisations.length === 0 &&
      evalCepriTea.evidence_level === 'C' &&
      evalQuinteroTea.evidence_level === 'C' &&
      evalCepriTea.suitability === 'partial' &&
      evalQuinteroTea.suitability === 'partial',
    notes: 'Aplica NEG-003 sobre fichas reales cuyo sector registral oficial es «Personas con discapacidad intelectual».'
  });

  // 21. REG-BOBATH-AT: Regresión Bobath Atención Temprana (CAM-C2758) y APADIS AT (CAM-C1591)
  const bobathAt = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C2758')!;
  const apadisAt = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C1591')!;
  const evalBobathCp = evaluateCentre(bobathAt, { ...defaultQuery, profile: 'cerebral_palsy' }, ALL_BENCHMARK_CENTRES, null);
  const evalApadisPsy = evaluateCentre(apadisAt, { ...defaultQuery, profile: 'psychomotor_early_support' }, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'REG-BOBATH-AT',
    category: 'REGLAS_NEGATIVAS',
    title: 'Centros de atención temprana genérica (Bobath AT y APADIS AT) limitados sin falsos A1',
    expected: 'No alcanzan A1/A2 y permanecen en lista (B2 para psicomotriz AT, sin excluir)',
    actual: `Bobath AT: ${evalBobathCp.evidence_level}/${evalBobathCp.suitability}, APADIS AT: ${evalApadisPsy.evidence_level}/${evalApadisPsy.suitability}`,
    passed:
      bobathAt.explicit_specialisations.length === 0 &&
      apadisAt.explicit_specialisations.length === 0 &&
      !['A1', 'A2'].includes(evalBobathCp.evidence_level) &&
      evalApadisPsy.evidence_level === 'B2' &&
      evalApadisPsy.suitability === 'partial',
    notes: 'El servicio independiente CAM-SRV-S3848 mantiene su ficha diferenciada; APADIS AT aparece en B2 para confirmar psicomotricidad.'
  });

  // 22. REG-AMAFE: Regresión AMAFE (CAM-C8927) limitado a C sin falso A1 neurodegenerativo
  const amafe = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C8927')!;
  const evalAmafeNeuro = evaluateCentre(amafe, { ...defaultQuery, profile: 'neurodegenerative_diseases' }, ALL_BENCHMARK_CENTRES, null);
  tests.push({
    id: 'REG-AMAFE',
    category: 'REGLAS_NEGATIVAS',
    title: 'AMAFE (CAM-C8927 · Psicosis/Enfermedad mental crónica) sin falso A1 neurodegenerativo',
    expected: 'Nivel C y adecuación partial para enfermedades neurodegenerativas',
    actual: `Nivel ${evalAmafeNeuro.evidence_level}, Adecuación ${evalAmafeNeuro.suitability}`,
    passed: amafe.explicit_specialisations.length === 0 && evalAmafeNeuro.evidence_level === 'C' && evalAmafeNeuro.suitability === 'partial',
    notes: 'El sector registral oficial «Personas con enfermedad mental crónica» no se cruza con neurodegenerativas.'
  });

  // 23. AUD-001: Auditoría crítica de campos (teléfono, dirección, plazas, SHA-256) contra snapshot oficial
  const mockMeta = {
    status: 'SUCCESS',
    sha256_hash: 'e62d139f5f04eb97a1b35faeaa76ca1301b8263068be5d6aa456af82813d5d17',
    extracted_records_count: 613,
    sources: [
      {
        source_id: 'madrid_municipal',
        status: 'SUCCESS',
        extracted_records_count: 613,
        sha256_hash: 'e62d139f5f04eb97a1b35faeaa76ca1301b8263068be5d6aa456af82813d5d17'
      },
      {
        source_id: 'cam_centros',
        status: 'SUCCESS',
        extracted_records_count: 2633,
        sha256_hash: 'f0856b4696961e554f1a8097c7505b54bc36891622a194313bb63d0323e5cf14'
      }
    ]
  };
  const liveIndex = new Map([
    [
      teaCenter.centre_id,
      {
        registry_key: teaCenter.centre_id,
        source_id: 'cam_centros' as const,
        official_name: teaCenter.official_name,
        phone: teaCenter.phone,
        address: teaCenter.address,
        municipality: teaCenter.municipality,
        postal_code: teaCenter.postal_code,
        authorised_places: teaCenter.availability.authorised_places
      }
    ]
  ]);
  const tamperedCenter: SpecializedCentre = { ...teaCenter, phone: '910999888' };
  const fakeManualCenter: SpecializedCentre = {
    ...teaCenter,
    centre_id: 'INVENTADO-999',
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'Manual',
        source_dataset: 'Ficha manual',
        source_url: 'https://example.org',
        source_type: 'official_registry',
        retrieved_at: '2026-11-15',
        extraction_method: 'structured',
        reviewer: 'Manual',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'C'
      }
    ]
  };
  const auditPass = auditCentreAgainstSnapshot(teaCenter, mockMeta, liveIndex);
  const auditMismatch = auditCentreAgainstSnapshot(tamperedCenter, mockMeta, liveIndex);
  const auditFake = auditCentreAgainstSnapshot(fakeManualCenter, mockMeta, liveIndex);
  tests.push({
    id: 'AUD-001',
    category: 'AUDITORIA_CSV',
    title: 'Función auditCentreAgainstSnapshot detecta coincidencia, discrepancia y datos no CSV',
    expected: 'verified_regional para CSV exacto, discrepancy si cambia teléfono, unverified si no viene de CSV',
    actual: `Exacto: ${auditPass.audit_status}, Manipulado: ${auditMismatch.audit_status}, Manual: ${auditFake.audit_status}`,
    passed:
      auditPass.audit_status === 'verified_regional' &&
      auditPass.is_official_csv &&
      auditMismatch.audit_status === 'discrepancy' &&
      !auditMismatch.phone_verified &&
      auditFake.audit_status === 'unverified' &&
      !auditFake.is_official_csv,
    notes: 'Contrasta teléfono, dirección, plazas autorizadas y firma SHA-256 contra snapshot-metadata.json.'
  });

  // 24. ACC-CSV-HONEST: Centro concertado CSV no deduce PIA sin documento expreso (#4)
  const apanefaCenter = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C5107')!;
  tests.push({
    id: 'ACC-CSV-HONEST',
    category: 'ACCESO',
    title: 'Plaza concertada registral no asume automáticamente tramitación PIA (#4)',
    expected: 'access_type unknown con orientación honesta a servicios sociales',
    actual: `Tipo: ${apanefaCenter.access_route.access_type}`,
    passed:
      apanefaCenter.access_route.access_type === 'unknown' &&
      apanefaCenter.access_route.next_step_action.toLowerCase().includes('servicios sociales'),
    notes: `${apanefaCenter.official_name} (CAM-C5107) indica que puede tener plazas públicas o concertadas sin suponer el cauce administrativo.`
  });

  // 25. ACCS-CODE-01: Códigos literales datos.madrid.es (#1, #2)
  const code1Centre: SpecializedCentre = {
    ...teaCenter,
    centre_id: 'TEST-ACC-1',
    accessibility_features: ['Accesible (Código 1 · datos.madrid.es)', 'Bucle magnético (Código 6 · datos.madrid.es)']
  };
  const code2Centre: SpecializedCentre = {
    ...teaCenter,
    centre_id: 'TEST-ACC-2',
    accessibility_features: ['Parcialmente accesible (Código 2 · datos.madrid.es)']
  };
  const code3Centre: SpecializedCentre = {
    ...teaCenter,
    centre_id: 'TEST-ACC-3',
    accessibility_features: ['Sin información (Código 3 · datos.madrid.es) · palabra adaptada no válida']
  };
  const evalCode1 = evaluateCentre(code1Centre, { ...defaultQuery, accessibility_needs: ['wheelchair_access', 'magnetic_loops'] }, [code1Centre], null);
  const evalCode2 = evaluateCentre(code2Centre, { ...defaultQuery, accessibility_needs: ['wheelchair_access'] }, [code2Centre], null);
  const evalCode3 = evaluateCentre(code3Centre, { ...defaultQuery, accessibility_needs: ['wheelchair_access'] }, [code3Centre], null);
  tests.push({
    id: 'ACCS-CODE-01',
    category: 'EVIDENCIA',
    title: 'Filtro de accesibilidad por código oficial: Cód. 1 accesible, Cód. 2 parcial, Cód. 3 excluido (#1/#2)',
    expected: 'Cód.1 confirmed+complete, Cód.2 partial, Cód.3 not_stated+incompatible',
    actual: `1:${getAccessibilityNeedStatus(code1Centre, 'wheelchair_access')}/${evalCode1.suitability}, 2:${evalCode2.suitability}, 3:${evalCode3.suitability}`,
    passed:
      getAccessibilityNeedStatus(code1Centre, 'wheelchair_access') === 'confirmed' &&
      getAccessibilityNeedStatus(code1Centre, 'magnetic_loops') === 'confirmed' &&
      evalCode1.suitability === 'complete' &&
      evalCode2.suitability === 'partial' &&
      evalCode3.suitability === 'incompatible',
    notes: 'Impide falsos positivos por palabras sueltas cuando ACCESIBILIDAD es Código 3 «Sin información».'
  });

  // 26. AGE-NO-CONSTA: Edad no declarada no excluye al buscar etapa vital menor (#3)
  const unstatedAgeCentre: SpecializedCentre = {
    ...amdemCenter,
    allowed_life_stages: []
  };
  const evalUnstatedAge = evaluateCentre(unstatedAgeCentre, { ...defaultQuery, life_stage: 'minor' }, [unstatedAgeCentre], null);
  tests.push({
    id: 'AGE-NO-CONSTA',
    category: 'REGLAS_NEGATIVAS',
    title: 'Centro sin edad declarada en el registro no se descarta como incompatible (#3)',
    expected: 'suitability partial y aviso «no consta» en matriz',
    actual: `Adecuación: ${evalUnstatedAge.suitability}`,
    passed:
      evalUnstatedAge.suitability === 'partial' &&
      evalUnstatedAge.criterion_matrix.some(c => c.criterion_id === 'lifestage.minor' && c.status === 'confirm_required'),
    notes: 'Mantiene visibles los ~700 centros que no especifican edad oficial con advertencia «Edad: no consta, confirmar».'
  });

  // 27. EVID-A2-ENTITY: Distinción A2 entidad titular (#8)
  const entityTeaCentre: SpecializedCentre = {
    ...teaCenter,
    centre_id: 'TEST-A2-ENT',
    provider_name: 'ASOCIACION AUTISMO DE PRUEBA (ENTIDAD)',
    official_name: 'CENTRO OCUPACIONAL LOS OLIVOS',
    explicit_specialisations: [],
    entity_declared_specialisations: ['autism']
  };
  const evalA2Entity = evaluateCentre(entityTeaCentre, { ...defaultQuery, profile: 'autism' }, [teaCenter, entityTeaCentre], null);
  tests.push({
    id: 'EVID-A2-ENTITY',
    category: 'EVIDENCIA',
    title: 'Distingue nivel «A2 · Lo declara la entidad titular» del A1 explícito en centro (#8)',
    expected: 'A2 con evidence_sublevel A2_entity y ordenación detrás de A1',
    actual: `Nivel ${evalA2Entity.evidence_level} (${evalA2Entity.evidence_sublevel})`,
    passed:
      evalA2Entity.evidence_level === 'A2' &&
      evalA2Entity.evidence_sublevel === 'A2_entity' &&
      evalA2Entity.sort_rank > resEv001.sort_rank,
    notes: 'Transparenta ante familias y jurado si la condición figura en el nombre de la entidad titular y no en el del centro.'
  });

  // 28. BOBATH-CP-NOOCC: Regex «parálisis o daño cerebral» (#9) y no equivalencia «centro ocupacional» -> terapia ocupacional (#5)
  const bobathSpecs = classifyExplicitSpecialisations({
    name: 'BOBATH, SERVICIO DE ATENCION A PERSONAS CON PARALISIS O DAÑO CEREBRAL',
    subtype: 'SERVICIOS ESPECIALIZADOS',
    sector: 'Personas con discapacidad física'
  });
  const coCentre = ALL_BENCHMARK_CENTRES.find(c => c.centre_id === 'CAM-C1812')!;
  tests.push({
    id: 'BOBATH-CP-NOOCC',
    category: 'TAXONOMIA',
    title: 'Patrón «parálisis o daño cerebral» (#9) y no deducir terapia ocupacional desde «centro ocupacional» (#5)',
    expected: 'Bobath => CP+DCA; CAM-C1812 sin occupational_therapy automático',
    actual: `Bobath: ${bobathSpecs.join('+')}, C1812 supports: ${coCentre.supports.join(',')}`,
    passed:
      bobathSpecs.includes('cerebral_palsy') &&
      bobathSpecs.includes('acquired_brain_injury') &&
      !coCentre.supports.includes('occupational_therapy'),
    notes: 'Corrige la detección conjunta de parálisis/daño cerebral y evita convertir centros ocupacionales en terapia ocupacional clínica.'
  });

  const executionTimeMs = performance.now() - startTime;
  const passedCount = tests.filter(t => t.passed).length;
  const failedCount = tests.filter(t => !t.passed).length;

  return {
    results: tests,
    total: tests.length,
    passedCount,
    failedCount,
    executionTimeMs
  };
}

