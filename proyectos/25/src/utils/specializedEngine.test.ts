import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  normalizeText,
  calculatePublicTransitTime,
  getProfileDefinition,
  centreHasSupportInSite,
  centreHasAccessibilityFeature,
  evaluateSupportCombination,
  evaluateCentre,
  runSpecializedSearch,
  auditCentreAgainstSnapshot
} from './specializedEngine';
import {
  buildCentresFromOfficialCSVs,
  classifyExplicitSpecialisations,
  formatOfficialSpanishName,
  formatMunicipalSubtypeLabel,
  formatMunicipalDistrict,
  mapCamMunicipalityName,
  utm30NToWgs84
} from './officialRegistryParser';
import { extractSpanishPhoneNumbers, formatSpanishPhone } from './phoneUtils';
import os from 'node:os';
import { computeDiffs, verifyBaselineIntegrity, writeFileAtomicSync } from '../../scripts/ingest';
import { findMunicipalityByName, MADRID_MUNICIPALITIES } from '../data/municipalitiesData';
import { CORE_PROFILES } from '../data/specializedTaxonomy';
import { runAllCanonicalTests, TEST_SUITE_CATEGORIES } from './specializedTestsSuite';
import { loadLiveSnapshotData } from './liveSnapshotParser';
import { parseValidatedSavedSearchesJson, validateSavedSearchRecord } from './savedSearchesStorage';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { escapeCsvCell, buildResultsCsv, buildResultsJsonPayload } from '../components/specialized/SpecializedResultsList';
import { SpecializedCentre, SearchQueryState } from '../types/specialized';

const MOCK_CENTRE_TEA: SpecializedCentre = {
  centre_id: 'C-TEST-TEA-01',
  provider_id: 'PROV-01',
  provider_name: 'Asociación Apoyo TEA',
  official_name: 'Centro de Día de Atención a Personas con Autismo Madrid Sur',
  resource_domain: 'social',
  sector: 'Discapacidad / Autismo',
  centre_type: 'Centro de Día',
  subtype: 'Centro de Día para Personas con Autismo',
  public_private_status: 'red_publica',
  management_type: 'pública_directa',
  address: 'Calle Mayor 10',
  postal_code: '28001',
  municipality: 'Madrid',
  district: 'Centro',
  coordinates: [40.4168, -3.7038],
  has_valid_coordinates: true,
  phone: '910000000',
  email: 'info@test.es',
  website: 'https://test.es',
  explicit_specialisations: ['autism'],
  related_services: ['Atención diurna', 'Logopedia'],
  supports: ['day_care', 'speech_therapy'],
  services_offered: [],
  allowed_life_stages: ['minor', 'adult'],
  access_route: {
    access_type: 'referral',
    competent_body: 'Consejería de Familia',
    official_description: 'Derivación oficial',
    source_url: 'https://comunidad.madrid',
    checked_at: '2026-01-01',
    next_step_action: 'Solicitar valoración previa',
    availability_known: false,
    waiting_list_known: false
  },
  availability: {
    status: 'contact_required',
    authorised_places: 30,
    vacancies_known: false,
    source_url: 'https://comunidad.madrid',
    checked_at: '2026-01-01',
    stale: false
  },
  geographic_coverage: {
    type: 'community_wide',
    requires_residence: 'yes',
    checked_at: '2026-01-01'
  },
  accessibility_features: ['Acceso cota cero rampa adaptada', 'Bucles magnéticos en recepción'],
  provenance_records: [
    {
      attribute_name: 'specialisation',
      value: 'Autismo',
      source_dataset: 'Registro Oficial',
      source_url: 'https://comunidad.madrid',
      source_type: 'official_registry',
      retrieved_at: '2026-01-01',
      extraction_method: 'structured',
      reviewer: 'Audit',
      reviewer_role: 'social',
      confidence: 'explicit',
      quality: 'A'
    }
  ],
  last_checked: '2026-01-01',
  limitations: []
};

const DEFAULT_QUERY: SearchQueryState = {
  profile: null,
  functional_needs: [],
  support_types: [],
  support_combination_mode: 'any_support',
  life_stage: null,
  municipality: null,
  radius_km: 80,
  network_preference: 'all',
  accessibility_needs: [],
  user_ephemeral_location: null,
  location_mode: 'all'
};

describe('Specialized Search Engine (Funciones Puras)', () => {
  describe('normalizeText', () => {
    it('normaliza minúsculas, tildes y espacios correctamente', () => {
      expect(normalizeText('  Atención Temprana y Logopedia  ')).toBe('atencion temprana y logopedia');
      expect(normalizeText('Daño Cerebral Adquirido')).toBe('dano cerebral adquirido');
    });
  });

  describe('calculatePublicTransitTime', () => {
    it('calcula estimaciones orientativas según distancia', () => {
      const t1 = calculatePublicTransitTime(1.0);
      expect(t1.minutes).toBe(13);
      expect(t1.label).toContain('est.');
      expect(calculatePublicTransitTime(5.0).minutes).toBe(23);
      expect(calculatePublicTransitTime(20.0).minutes).toBe(58);
    });
  });

  describe('utm30NToWgs84', () => {
    it('convierte coordenadas UTM 30N oficiales a lat/lon válidos en Madrid', () => {
      const coords = utm30NToWgs84(440320, 4474200);
      expect(coords).not.toBeNull();
      expect(coords![0]).toBeGreaterThan(40.3);
      expect(coords![0]).toBeLessThan(40.6);
      expect(coords![1]).toBeGreaterThan(-4.0);
      expect(coords![1]).toBeLessThan(-3.5);
    });

    it('rechaza coordenadas fuera de rango con null', () => {
      expect(utm30NToWgs84(0, 0)).toBeNull();
    });
  });

  describe('getProfileDefinition', () => {
    it('recupera definiciones de perfiles de la taxonomía oficial', () => {
      const autismDef = getProfileDefinition('autism');
      expect(autismDef).not.toBeNull();
      expect(autismDef?.preferred_label).toContain('autismo');
    });

    it('devuelve null para IDs desconocidos', () => {
      expect(getProfileDefinition('desconocido_123')).toBeNull();
    });
  });

  describe('centreHasSupportInSite', () => {
    it('detecta apoyos declarados directamente en el array de apoyos', () => {
      expect(centreHasSupportInSite(MOCK_CENTRE_TEA, 'day_care')).toBe(true);
      expect(centreHasSupportInSite(MOCK_CENTRE_TEA, 'occupational_therapy')).toBe(false);
    });
  });

  describe('centreHasAccessibilityFeature', () => {
    it('identifica características de accesibilidad física en el centro', () => {
      expect(centreHasAccessibilityFeature(MOCK_CENTRE_TEA, 'wheelchair_access')).toBe(true);
      expect(centreHasAccessibilityFeature(MOCK_CENTRE_TEA, 'magnetic_loops')).toBe(true);
      expect(centreHasAccessibilityFeature(MOCK_CENTRE_TEA, 'tactile_signage')).toBe(false);
    });
  });

  describe('evaluateSupportCombination', () => {
    it('confirma combinación completa cuando todos los apoyos están en la misma sede', () => {
      const res = evaluateSupportCombination(MOCK_CENTRE_TEA, ['day_care', 'speech_therapy'], [MOCK_CENTRE_TEA]);
      expect(res.status).toBe('all_same_centre');
    });

    it('marca not_confirmed si no incluye los apoyos', () => {
      const res = evaluateSupportCombination(MOCK_CENTRE_TEA, ['residential_care'], [MOCK_CENTRE_TEA]);
      expect(res.status).toBe('not_confirmed');
    });
  });

  describe('classifyExplicitSpecialisations (Guardas literales)', () => {
    it('evita falsos positivos de "San Juan Bautista" como autismo', () => {
      expect(classifyExplicitSpecialisations({ name: 'Centro San Juan Bautista', subtype: '', sector: '' })).toEqual([]);
    });

    it('no infiere patologías desde "discapacidad intelectual", "discapacidad física" ni "atención temprana"', () => {
      expect(
        classifyExplicitSpecialisations({
          name: 'LESCER, CENTRO DE REHABILITACION',
          subtype: 'CENTROS DE RECUPERACIÓN',
          sector: 'Personas con discapacidad física'
        })
      ).toEqual([]);
      expect(
        classifyExplicitSpecialisations({
          name: 'CEPRI LA PEINETA, CENTRO DE DIA',
          subtype: 'CENTROS DE DÍA: OTROS',
          sector: 'Personas con discapacidad intelectual'
        })
      ).toEqual([]);
      expect(
        classifyExplicitSpecialisations({
          name: 'CENTRO ALBEA ATENCION TEMPRANA',
          subtype: 'CENTROS DE ATENCIÓN',
          sector: 'Infancia'
        })
      ).toEqual([]);
    });

    it('asigna esclerosis múltiple a enfermedades neurodegenerativas', () => {
      expect(
        classifyExplicitSpecialisations({
          name: 'ALICIA KOPLOWITZ, CENTRO DE DIA DE ESCLEROSIS MULTIPLE',
          subtype: '',
          sector: 'Personas con discapacidad física'
        })
      ).toContain('neurodegenerative_diseases');
    });
  });

  describe('evaluateCentre', () => {
    it('asigna Nivel de Evidencia A1 a especialización explícita con apoyo coincidente', () => {
      const query: SearchQueryState = {
        ...DEFAULT_QUERY,
        profile: 'autism',
        support_types: ['day_care']
      };
      const res = evaluateCentre(MOCK_CENTRE_TEA, query, [MOCK_CENTRE_TEA]);
      expect(res.evidence_level).toBe('A1');
      expect(res.suitability).toBe('complete');
    });

    it('clasifica incompatibilidad de etapa vital cuando no coincide', () => {
      const query: SearchQueryState = {
        ...DEFAULT_QUERY,
        profile: 'autism',
        life_stage: 'older_adult'
      };
      const res = evaluateCentre(MOCK_CENTRE_TEA, query, [MOCK_CENTRE_TEA]);
      expect(res.suitability).toBe('incompatible');
    });

    it('clasifica incompatibilidad por falta de requisito de accesibilidad física exigido', () => {
      const query: SearchQueryState = {
        ...DEFAULT_QUERY,
        accessibility_needs: ['tactile_signage']
      };
      const res = evaluateCentre(MOCK_CENTRE_TEA, query, [MOCK_CENTRE_TEA]);
      expect(res.suitability).toBe('incompatible');
    });
  });

  describe('runSpecializedSearch', () => {
    it('filtra y ordena resultados separando candidatos principales de incompatibles', () => {
      const query: SearchQueryState = {
        ...DEFAULT_QUERY,
        profile: 'autism'
      };
      const searchRes = runSpecializedSearch(query, [MOCK_CENTRE_TEA]);
      expect(searchRes.total_results).toBe(1);
      expect(searchRes.results[0].centre.centre_id).toBe('C-TEST-TEA-01');
      expect(searchRes.incompatible_results.length).toBe(0);
    });
  });

  describe('Canonical Test Suite (28 casos)', () => {
    it('supera el 100% de las pruebas canónicas sin regresiones', () => {
      const suite = runAllCanonicalTests();
      expect(suite.total).toBe(28);
      expect(suite.failedCount).toBe(0);
    });
  });

  describe('Mejoras v1.8 sobre el catálogo real y motor de evaluación', () => {
    const snapshotsDir = path.resolve(process.cwd(), 'public/data/snapshots');
    const meta = JSON.parse(fs.readFileSync(path.join(snapshotsDir, 'snapshot-metadata.json'), 'utf8'));
    const madridBuf = fs.readFileSync(path.join(snapshotsDir, 'snapshot-latest.csv'));
    const camCentrosBuf = fs.readFileSync(path.join(snapshotsDir, 'cam-centros-latest.csv'));
    const camServiciosBuf = fs.readFileSync(path.join(snapshotsDir, 'cam-servicios-latest.csv'));
    const classifiedJson = JSON.parse(fs.readFileSync(path.join(snapshotsDir, 'catalog-classified.json'), 'utf8'));

    const parsed = buildCentresFromOfficialCSVs({
      madridCsvText: madridBuf.toString('latin1'),
      camCentrosCsvText: camCentrosBuf.toString('utf8'),
      camServiciosCsvText: camServiciosBuf.toString('utf8'),
      snapshotDate: meta.timestamp?.slice(0, 10) || '2026-11-15'
    });

    it('verifica integridad exacta SHA-256 entre los ficheros CSV en disco y snapshot-metadata.json', () => {
      const shaMadrid = crypto.createHash('sha256').update(madridBuf).digest('hex');
      const shaCamC = crypto.createHash('sha256').update(camCentrosBuf).digest('hex');
      const shaCamS = crypto.createHash('sha256').update(camServiciosBuf).digest('hex');

      const srcMap = Object.fromEntries((meta.sources || []).map((s: any) => [s.source_id, s.sha256_hash]));
      expect(shaMadrid).toBe(srcMap.madrid_municipal);
      expect(shaCamC).toBe(srcMap.cam_centros);
      expect(shaCamS).toBe(srcMap.cam_servicios);
      expect(meta.sha256_hash).toBe(shaMadrid);
    });

    it('#1 y #2: filtro silla de ruedas solo admite Código 1/2 y bucle magnético usa Código 6', () => {
      const wheelchairRes = runSpecializedSearch(
        { ...DEFAULT_QUERY, accessibility_needs: ['wheelchair_access'] },
        parsed.centres,
        null
      );
      expect(wheelchairRes.results.length).toBeGreaterThan(50);
      expect(
        wheelchairRes.results.every(r =>
          r.centre.accessibility_features.some(f => f.includes('Código 1') || f.includes('Código 2'))
        )
      ).toBe(true);
      expect(
        wheelchairRes.results.some(r => r.centre.accessibility_features.some(f => f.includes('Código 3')))
      ).toBe(false);

      const loopRes = runSpecializedSearch(
        { ...DEFAULT_QUERY, accessibility_needs: ['magnetic_loops'] },
        parsed.centres,
        null
      );
      expect(loopRes.results.length).toBeGreaterThan(0);
    });

    it('#3: centros sin edad declarada (~700) permanecen visibles como partial al buscar minor', () => {
      const minorSearch = runSpecializedSearch(
        { ...DEFAULT_QUERY, life_stage: 'minor' },
        parsed.centres,
        null
      );
      const unstatedKept = minorSearch.results.filter(r => r.centre.allowed_life_stages.length === 0);
      expect(unstatedKept.length).toBeGreaterThan(500);
      expect(unstatedKept.every(r => r.suitability === 'partial')).toBe(true);
    });

    it('#4 y #5: sin PIA deducido por concierto y sin occupational_therapy ni falso B1/B2 en centros ocupacionales', () => {
      expect(parsed.centres.every(c => c.access_route.access_type === 'unknown')).toBe(true);
      const c1812 = parsed.centres.find(c => c.centre_id === 'CAM-C1812');
      expect(c1812).toBeDefined();
      expect(c1812!.supports).not.toContain('occupational_therapy');

      // Ningún centro ocupacional genérico debe escalar a B1/B2 por el texto de advertencia en related_services
      const evAbi = evaluateCentre(
        c1812!,
        { ...DEFAULT_QUERY, profile: 'acquired_brain_injury' },
        parsed.centres,
        null
      );
      expect(evAbi.evidence_level).toBe('C');

      // Los servicios de FORMACIÓN Y/O RECUPERACIÓN PROFESIONAL se clasifican como apoyo laboral, no rehabilitación médica
      const s6541 = parsed.centres.find(c => c.centre_id === 'CAM-SRV-S6541');
      expect(s6541).toBeDefined();
      expect(s6541!.supports).toContain('employment_support');
      expect(s6541!.supports).not.toContain('rehabilitation');

      expect(evAbi.transit_time_label).toBeTruthy();
      expect(evAbi.transit_time_label).toContain('est.');
    });

    it('#8 y #9: A2_entity en entidades de TEA y Bobath (CAM-SRV-S3848) con parálisis + daño cerebral', () => {
      const teaSearch = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'autism' }, parsed.centres, null);
      const a2EntityHits = teaSearch.results.filter(r => r.evidence_sublevel === 'A2_entity');
      expect(a2EntityHits.length).toBeGreaterThan(20);

      const bobathSrv = parsed.centres.find(c => c.centre_id === 'CAM-SRV-S3848');
      expect(bobathSrv).toBeDefined();
      expect(bobathSrv!.explicit_specialisations).toContain('acquired_brain_injury');
      expect(bobathSrv!.explicit_specialisations).toContain('cerebral_palsy');
    });

    it('clasifica correctamente MAD-PK públicos directos vs titularidad no especificada', () => {
      const centroBase1 = parsed.centres.find(c => c.centre_id === 'MAD-PK11906');
      const aspaym = parsed.centres.find(c => c.centre_id === 'MAD-PK6996740');
      expect(centroBase1).toBeDefined();
      expect(centroBase1!.public_private_status).toBe('red_publica');
      expect(aspaym).toBeDefined();
      expect(aspaym!.public_private_status).toBe('no_especificado');
    });

    it('#11: anonimización RGPD y capitalización española correcta en titulares personas físicas', () => {
      const s7705 = parsed.centres.find(c => c.centre_id === 'CAM-SRV-S7705');
      expect(s7705).toBeDefined();
      expect(s7705!.official_name).toContain('Atención');
      expect(s7705!.official_name).not.toContain('AtencióN');
      expect(s7705!.phone).toBe('');
      expect(s7705!.has_valid_coordinates).toBe(false);

      const s9981 = parsed.centres.find(c => c.centre_id === 'CAM-SRV-S9981');
      if (s9981) {
        expect(s9981.official_name).toContain('Profesional individual autorizado');
        expect(s9981.provider_name).toContain('omitido por privacidad');
        expect(s9981.phone).toBe('');
        expect(s9981.has_valid_coordinates).toBe(false);
      }
    });

    it('marca functional_needs como confirm_required en lugar de confirmed sin respaldo clínico', () => {
      const ev = evaluateCentre(
        MOCK_CENTRE_TEA,
        { ...DEFAULT_QUERY, profile: 'autism', functional_needs: ['swallowing', 'communication'] },
        [MOCK_CENTRE_TEA],
        null
      );
      const fnItems = ev.criterion_matrix.filter(c => c.criterion_id.startsWith('functional.'));
      expect(fnItems.length).toBe(2);
      expect(fnItems.every(c => c.status === 'confirm_required')).toBe(true);
      expect(ev.match_assessment.does_not_confirm.some(d => d.toLowerCase().includes('necesidades funcionales'))).toBe(true);
    });

    it('mantiene cero falsos positivos A1/A2 en todos los centros críticos vigilados', () => {
      const checkNoA = (centreId: string, profile: any) => {
        const c = parsed.centres.find(item => item.centre_id === centreId);
        expect(c).toBeDefined();
        const ev = evaluateCentre(c!, { ...DEFAULT_QUERY, profile }, parsed.centres, null);
        expect(['A1', 'A2']).not.toContain(ev.evidence_level);
      };

      checkNoA('CAM-C8019', 'acquired_brain_injury'); // Lescer
      checkNoA('CAM-C3456', 'acquired_brain_injury'); // Polibea
      checkNoA('CAM-C2412', 'autism'); // CEPRI
      checkNoA('CAM-C1812', 'autism'); // Quintero Lumbreras
      checkNoA('CAM-C2758', 'cerebral_palsy'); // Bobath AT
      checkNoA('CAM-C2758', 'psychomotor_early_support'); // Bobath AT
      checkNoA('CAM-C1591', 'psychomotor_early_support'); // APADIS AT
      checkNoA('CAM-C8927', 'neurodegenerative_diseases'); // Amafe
    });

    it('devuelve recursos A1 reales y verificables para perfiles clave', () => {
      const profilesToCheck: Array<SearchQueryState['profile']> = [
        'neurodegenerative_diseases',
        'autism',
        'acquired_brain_injury',
        'cerebral_palsy',
        'spinal_cord_injury',
        'als',
        'parkinson',
        'alzheimer'
      ];

      for (const profile of profilesToCheck) {
        const res = runSpecializedSearch({ ...DEFAULT_QUERY, profile }, parsed.centres, null);
        const aLevels = res.results.filter(r => r.evidence_level === 'A1' || r.evidence_level === 'A2');
        expect(aLevels.length).toBeGreaterThan(0);
      }
    });

    it('#7: catalog-classified.json coincide exactamente con parsed.centres y pasa auditoría CSV al 100%', () => {
      expect(classifiedJson.centres.length).toBe(parsed.centres.length);
      const slimMap = new Map<string, any>(classifiedJson.lookup_records);
      for (const centre of classifiedJson.centres) {
        const audit = auditCentreAgainstSnapshot(centre, meta, slimMap);
        expect(audit.is_official_csv).toBe(true);
        expect(audit.audit_status).not.toBe('discrepancy');
        expect(audit.audit_status).not.toBe('unverified');
      }
    });

    it('marcas de adecuación parcial y ranking honesto para apoyos ausentes, functional_needs y red privada/concertada', () => {
      const noSpeechCentre: SpecializedCentre = {
        ...MOCK_CENTRE_TEA,
        centre_id: 'MOCK-NO-SPEECH',
        supports: ['day_care']
      };
      const evMissingSupport = evaluateCentre(
        noSpeechCentre,
        { ...DEFAULT_QUERY, profile: 'autism', support_types: ['speech_therapy'] },
        [noSpeechCentre],
        null
      );
      expect(evMissingSupport.suitability).toBe('partial');

      const evFunctional = evaluateCentre(
        MOCK_CENTRE_TEA,
        { ...DEFAULT_QUERY, profile: 'autism', functional_needs: ['swallowing'] },
        [MOCK_CENTRE_TEA],
        null
      );
      expect(evFunctional.suitability).toBe('partial');

      const searchCount = runSpecializedSearch(
        { ...DEFAULT_QUERY, profile: 'autism', functional_needs: ['swallowing', 'communication'] },
        [MOCK_CENTRE_TEA],
        null
      );
      expect(searchCount.applied_filters_count).toBe(3);

      const concertadoCentre: SpecializedCentre = {
        ...MOCK_CENTRE_TEA,
        centre_id: 'MOCK-CONCERTADO',
        public_private_status: 'concertado'
      };
      const privadoCentre: SpecializedCentre = {
        ...MOCK_CENTRE_TEA,
        centre_id: 'MOCK-PRIVADO',
        public_private_status: 'privado_autorizado'
      };
      const privRes = runSpecializedSearch(
        { ...DEFAULT_QUERY, profile: 'autism', network_preference: 'private_authorised' },
        [concertadoCentre, privadoCentre],
        null
      );
      expect(privRes.results[0].centre.centre_id).toBe('MOCK-PRIVADO');
      expect(privRes.results[0].suitability).toBe('complete');
      expect(privRes.results[1].centre.centre_id).toBe('MOCK-CONCERTADO');
      expect(privRes.results[1].suitability).toBe('partial');
    });

    it('cubre el nomenclátor completo de municipios CSV, normaliza artículos y sincroniza municipalities.json', () => {
      expect(mapCamMunicipalityName('Cabrera, La')).toBe('La Cabrera');
      expect(mapCamMunicipalityName('Alamo, El')).toBe('El Álamo');
      expect(findMunicipalityByName('a')).toBeNull();
      expect(findMunicipalityByName('Cabrera, La')?.name).toBe('La Cabrera');
      expect(findMunicipalityByName('Madrid (ubicación reservada)')?.name).toBe('Madrid');

      const publicMunis = JSON.parse(
        fs.readFileSync(path.resolve(process.cwd(), 'public/data/municipalities.json'), 'utf8')
      );
      expect(publicMunis.length).toBe(MADRID_MUNICIPALITIES.length);

      for (const centre of classifiedJson.centres) {
        if (centre.municipality === 'Madrid (ubicación reservada)') continue;
        expect(findMunicipalityByName(centre.municipality)).not.toBeNull();
      }
    });

    it('exige mínimo 3 centros explícitos A1 en CSV oficiales para todos los perfiles con estado approved', () => {
      expect(CORE_PROFILES.cerebral_palsy.status).toBe('experimental');
      for (const profile of Object.values(CORE_PROFILES)) {
        if (profile.status === 'approved') {
          const explicitCount = parsed.centres.filter(c =>
            c.explicit_specialisations.includes(profile.id)
          ).length;
          expect(explicitCount).toBeGreaterThanOrEqual(3);
        }
      }
    });

    it('neutraliza inyección de fórmulas en exportación CSV y excluye GPS efímero del JSON exportado', () => {
      expect(escapeCsvCell('=CMD("calc")')).toBe('"\'=CMD(""calc"")"');
      expect(escapeCsvCell('+SUM(A1:A2)')).toBe('"\'+SUM(A1:A2)"');
      expect(escapeCsvCell('-2+3')).toBe('"\'-2+3"');
      expect(escapeCsvCell('@IMPORTXML')).toBe('"\'@IMPORTXML"');

      const ev = evaluateCentre(MOCK_CENTRE_TEA, DEFAULT_QUERY, [MOCK_CENTRE_TEA], [40.4168, -3.7038]);
      const csv = buildResultsCsv([ev]);
      expect(csv).toContain('Estimación Transporte Público');
      expect(csv).toContain('URLs Oficiales');
      expect(csv).toContain('https://comunidad.madrid');

      const jsonPayload = buildResultsJsonPayload([ev], {
        ...DEFAULT_QUERY,
        user_ephemeral_location: [40.4168, -3.7038],
        location_mode: 'browser'
      });
      expect(jsonPayload.total_results).toBe(1);
      expect('user_ephemeral_location' in jsonPayload.query).toBe(false);
    });

    it('sincroniza al 100% las categorías de la batería canónica con el visor de pruebas', () => {
      const suite = runAllCanonicalTests();
      const allowedIds = new Set<string>(TEST_SUITE_CATEGORIES.map(c => c.id));
      expect(suite.total).toBeGreaterThanOrEqual(25);
      expect(suite.failedCount).toBe(0);
      for (const testItem of suite.results) {
        expect(allowedIds.has(testItem.category)).toBe(true);
      }
    });

    it('mantiene operativo el catálogo pre-clasificado aunque falle snapshot-metadata.json en caché parcial', async () => {
      const originalFetch = globalThis.fetch;
      globalThis.fetch = (async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('snapshot-metadata.json')) {
          return Promise.reject(new Error('offline_metadata_miss'));
        }
        if (url.includes('snapshot-diffs.json')) {
          return new Response(JSON.stringify({ diffs: [] }), { status: 200 });
        }
        if (url.includes('catalog-classified.json')) {
          return new Response(
            JSON.stringify({
              centres: classifiedJson.centres.slice(0, 5),
              lookup_records: classifiedJson.lookup_records.slice(0, 5),
              total_records: 5
            }),
            { status: 200 }
          );
        }
        return new Response(null, { status: 404 });
      }) as typeof fetch;

      try {
        const loaded = await loadLiveSnapshotData([]);
        expect(loaded.state.loaded).toBe(true);
        expect(loaded.state.load_source).toBe('preclassified_json');
        expect(loaded.state.used_fallback).toBe(false);
        expect(loaded.centres.length).toBe(5);
      } finally {
        globalThis.fetch = originalFetch;
      }
    });

    it('auditoría 15 puntos: reglas negativas limitan nivel (<= B2) sin excluir, NEG-006 para TEA, Title Case y diffs de coordenadas', () => {
      // #1: Atención temprana en psicomotriz -> B2 partial sin excluir (ni desaparecer bajo 965 C)
      const psyRes = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'psychomotor_early_support' }, parsed.centres, null);
      const b2AtHits = psyRes.results.filter(r => r.evidence_level === 'B2');
      expect(b2AtHits.length).toBeGreaterThan(80);
      expect(psyRes.incompatible_results.length).toBe(0);

      // #1: Parálisis cerebral y autismo no excluyen centros de discapacidad física ni intelectual
      const cpRes = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'cerebral_palsy' }, parsed.centres, null);
      expect(cpRes.incompatible_results.length).toBe(0);
      const autismRes = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'autism' }, parsed.centres, null);
      expect(autismRes.incompatible_results.length).toBe(0);

      // #1 texto NEG-006 en TEA sobre centro de enfermedad mental crónica (AMAFE)
      const amafe = parsed.centres.find(c => c.centre_id === 'CAM-C8927')!;
      const evAmafeTea = evaluateCentre(amafe, { ...DEFAULT_QUERY, profile: 'autism' }, parsed.centres, null);
      expect(evAmafeTea.evidence_level).toBe('C');
      expect(evAmafeTea.suitability).toBe('partial');
      expect(evAmafeTea.match_assessment.suitability_reasons.some(r => r.includes('TEA') && !r.includes('neurológica'))).toBe(true);

      // #13 Title Case preservando siglas, siglas con puntos y tildes españolas restauradas
      expect(formatOfficialSpanishName('CEPRI LA PEINETA, CENTRO DE DIA')).toBe('CEPRI La Peineta, Centro de Día');
      expect(formatOfficialSpanishName('ASOCIACION DE PADRES DE PERSONAS CON AUTISMO-APNA')).toBe('Asociación de Padres de Personas con Autismo-APNA');
      expect(formatOfficialSpanishName('CENTRO DE ATENCION TEMPRANA ASPACE-TEA')).toBe('Centro de Atención Temprana ASPACE-TEA');
      expect(formatOfficialSpanishName('GRUPO 5 ACCION Y GESTION SOCIAL S.A.U.')).toBe('Grupo 5 Acción y Gestión Social S.A.U.');
      expect(formatOfficialSpanishName('EDUKATEK SOCIOSANITARIO, S.L.U')).toBe('Edukatek Sociosanitario, S.L.U');
      expect(formatOfficialSpanishName('ASOCIACION "A.F.A. ALCALÁ"')).toBe('Asociación "A.F.A. Alcalá"');
      expect(formatOfficialSpanishName('C.I.A.N. GRUPO 5')).toBe('C.I.A.N. Grupo 5');
      expect(formatOfficialSpanishName('ASOCIACION A.D.E.M.MADRID')).toBe('Asociación A.D.E.M.Madrid');
      expect(formatOfficialSpanishName('CIUDAD LINEAL')).toBe('Ciudad Lineal');
      expect(formatOfficialSpanishName('Fmp Aura: Desarrollo Global Contra La Violencia de Género')).toBe('FMP Aura: Desarrollo Global contra la Violencia de Género');
      expect(formatOfficialSpanishName('Asoc.Esclerosis Múltiple España, Servicio de Información y Orientación')).toBe('Asoc. Esclerosis Múltiple España, Servicio de Información y Orientación');
      expect(formatOfficialSpanishName('Colisee Vallecas.Centro de Rehabilitación y Recuperación')).toBe('Colisee Vallecas. Centro de Rehabilitación y Recuperación');
      expect(formatMunicipalSubtypeLabel('/entidades/CentrosAtencionSocialPersonasDiscapacidad')).toBe('Centros de Atención Social · Personas con Discapacidad');
      expect(formatMunicipalSubtypeLabel('/entidades/CentrosServiciosSociales')).toBe('Centros de Servicios Sociales');
      expect(formatMunicipalDistrict('CENTRO')).toBe('Centro');
      expect(formatMunicipalDistrict('CHAMARTIN')).toBe('Chamartín');
      expect(formatMunicipalDistrict('Chamartin')).toBe('Chamartín');
      expect(formatMunicipalDistrict('Tetuan')).toBe('Tetuán');
      expect(formatMunicipalDistrict('SAN BLAS')).toBe('San Blas-Canillejas');
      expect(formatMunicipalDistrict('DISTRITO')).toBeUndefined();

      // #2 Diffs detectan cambios de accesibilidad (Cód. 3 -> 1) y coordenadas
      const prevRows = [
        ['PK', 'NOMBRE', 'TELEFONO', 'CLASE-VIAL', 'NOMBRE-VIA', 'NUM', 'ACCESIBILIDAD', 'LATITUD', 'LONGITUD'],
        ['11906', 'Centro Base 1', '910000001', 'CALLE', 'Maqueda', '1', '3', '40.4000', '-3.7500']
      ];
      const currRows = [
        ['PK', 'NOMBRE', 'TELEFONO', 'CLASE-VIAL', 'NOMBRE-VIA', 'NUM', 'ACCESIBILIDAD', 'LATITUD', 'LONGITUD'],
        ['11906', 'Centro Base 1', '910000001', 'CALLE', 'Maqueda', '1', '1', '40.4012', '-3.7510']
      ];
      const diffs = computeDiffs('madrid_municipal', prevRows, currRows, '2026-11-15', '2026-11-17');
      expect(diffs.length).toBe(1);
      expect(diffs[0].change_type).toBe('access_route_changed');
      expect(diffs[0].detail).toContain('Accesibilidad código');
      expect(diffs[0].detail).toContain('Coordenadas');

      const coordsOnlyDiff = computeDiffs(
        'madrid_municipal',
        prevRows,
        [
          ['PK', 'NOMBRE', 'TELEFONO', 'CLASE-VIAL', 'NOMBRE-VIA', 'NUM', 'ACCESIBILIDAD', 'LATITUD', 'LONGITUD'],
          ['11906', 'Centro Base 1', '910000001', 'CALLE', 'Maqueda', '1', '3', '40.4012', '-3.7510']
        ],
        '2026-11-15',
        '2026-11-17'
      );
      expect(coordsOnlyDiff[0].change_type).toBe('access_route_changed');
      expect(coordsOnlyDiff[0].category).toBe('acceso');
    });

    it('auditoría profunda DATAMAD: cruce multi-fuente sin falsas discrepancias y CentrosServiciosSociales sin apoyos residenciales/diurnos falsos', () => {
      const slimMap = new Map<string, any>(classifiedJson.lookup_records);
      const linkedWithMad = parsed.centres.filter(c =>
        c.centre_id.startsWith('CAM-') &&
        c.provenance_records.some(p => p.source_dataset.includes('datos.madrid.es PK'))
      );
      expect(linkedWithMad.length).toBeGreaterThan(0);

      for (const centre of linkedWithMad) {
        const audit = auditCentreAgainstSnapshot(centre, meta, slimMap);
        expect(audit.audit_status).not.toBe('discrepancy');
        expect(audit.audit_status).not.toBe('unverified');
      }

      // Centros de Servicios Sociales municipales (información/tramitación) no deben heredar day_care/residential_care del texto descriptivo
      const maravillas = parsed.centres.find(c => c.centre_id === 'MAD-PK174917');
      expect(maravillas).toBeDefined();
      expect(maravillas!.supports).not.toContain('day_care');
      expect(maravillas!.supports).not.toContain('residential_care');

      const cpSearch = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'cerebral_palsy' }, parsed.centres, null);
      const cpMaravillas = cpSearch.results.find(r => r.centre.centre_id === 'MAD-PK174917');
      expect(cpMaravillas?.evidence_level).toBe('C');

      const neuroSearch = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'neurodegenerative_diseases' }, parsed.centres, null);
      const neuroMaravillas = neuroSearch.results.find(r => r.centre.centre_id === 'MAD-PK174917');
      expect(neuroMaravillas?.evidence_level).toBe('C');
    });

    it('P0/P1: verifyBaselineIntegrity bloquea discrepancias SHA-256 silenciosas y writeFileAtomicSync escribe sin temporales residuales', () => {
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'datamad-ingest-test-'));
      try {
        const csvPath = path.join(tmpDir, 'snapshot-latest.csv');
        const payload = Buffer.from('PK;NOMBRE;ACCESIBILIDAD\n11906;Centro Base 1;1\n', 'utf-8');
        writeFileAtomicSync(csvPath, payload);

        const remainingFiles = fs.readdirSync(tmpDir);
        expect(remainingFiles).toEqual(['snapshot-latest.csv']);

        const validSha = crypto.createHash('sha256').update(payload).digest('hex');
        const verified = verifyBaselineIntegrity({
          sourceId: 'madrid_municipal',
          latestPath: csvPath,
          expectedSha256: validSha
        });
        expect(verified?.equals(payload)).toBe(true);

        expect(() =>
          verifyBaselineIntegrity({
            sourceId: 'madrid_municipal',
            latestPath: csvPath,
            expectedSha256: '0'.repeat(64)
          })
        ).toThrow(/Integridad de línea base comprometida/);

        const stalePayload = Buffer.from('PK;NOMBRE;ACCESIBILIDAD\n11906;Centro Base 1;3\n', 'utf-8');
        writeFileAtomicSync(csvPath, stalePayload);

        const recoveredBuf = verifyBaselineIntegrity({
          sourceId: 'madrid_municipal',
          latestPath: csvPath,
          expectedSha256: validSha,
          gitFallbackLoader: () => payload
        });
        expect(recoveredBuf?.equals(payload)).toBe(true);
      } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    });

    it('P1: valida esquema estricto de búsquedas guardadas en localStorage y ErrorBoundary captura errores', () => {
      expect(parseValidatedSavedSearchesJson(null)).toEqual([]);
      expect(parseValidatedSavedSearchesJson('{corrupto')).toEqual([]);
      expect(parseValidatedSavedSearchesJson('{"not":"array"}')).toEqual([]);

      const validEntry = {
        saved_search_id: 'search-1',
        name: 'Búsqueda TEA Madrid',
        created_at: '2026-11-18T10:00:00.000Z',
        updated_at: '2026-11-18T10:00:00.000Z',
        taxonomy_version: '1.8.0',
        dataset_snapshot: '2026-11-17',
        filters: {
          profile: 'autism',
          functional_needs: ['communication'],
          support_types: ['day_care'],
          support_combination_mode: 'any_support',
          life_stage: 'minor',
          municipality: 'Madrid',
          radius_km: 25,
          network_preference: 'public_network',
          accessibility_needs: ['wheelchair_access']
        }
      };

      const invalidEntry = {
        saved_search_id: 999,
        name: '',
        filters: { radius_km: 9999 }
      };

      expect(validateSavedSearchRecord(validEntry)).not.toBeNull();
      expect(validateSavedSearchRecord(invalidEntry)).toBeNull();

      const parsedSaved = parseValidatedSavedSearchesJson(JSON.stringify([validEntry, invalidEntry]));
      expect(parsedSaved.length).toBe(1);
      expect(parsedSaved[0].saved_search_id).toBe('search-1');
      expect('user_ephemeral_location' in parsedSaved[0].filters).toBe(false);

      const errState = ErrorBoundary.getDerivedStateFromError();
      expect(errState.hasError).toBe(true);
    });

    it('aplica estrictamente el filtro de radio (10, 30, 50 y 80 km) también desde el origen por defecto y verifica 0 registros TDAH', () => {
      const r10 = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 10 }, parsed.centres, null);
      const r30 = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 30 }, parsed.centres, null);
      const r50 = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 50 }, parsed.centres, null);
      const r80 = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 80 }, parsed.centres, null);

      expect(r10.results.every(r => r.distance_km === null || r.distance_km <= 10)).toBe(true);
      expect(r30.results.every(r => r.distance_km === null || r.distance_km <= 30)).toBe(true);
      expect(r50.results.every(r => r.distance_km === null || r.distance_km <= 50)).toBe(true);
      expect(r80.results.every(r => r.distance_km === null || r.distance_km <= 80)).toBe(true);

      expect(r10.total_results).toBeLessThan(r30.total_results);
      expect(r30.total_results).toBeLessThan(r50.total_results);
      expect(r50.total_results).toBeLessThan(r80.total_results);

      // Confirmar que TDAH no cuenta con centros explícitos ni por entidad en los CSV oficiales actuales
      const tdahRes = runSpecializedSearch({ ...DEFAULT_QUERY, profile: 'adhd' }, parsed.centres, null);
      const tdahLevelA = tdahRes.results.filter(r => r.evidence_level === 'A1' || r.evidence_level === 'A2');
      expect(tdahLevelA.length).toBe(0);
    });

    it('radius_km = 0 actúa como distancia ilimitada y fusiona multi-fuente preservando ambos provenances y prioridad UTM > municipal', () => {
      const unlimitedRes = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 0 }, parsed.centres, null);
      const limitedRes = runSpecializedSearch({ ...DEFAULT_QUERY, radius_km: 10 }, parsed.centres, null);
      expect(unlimitedRes.total_results).toBe(parsed.centres.length - unlimitedRes.incompatible_results.length);
      expect(unlimitedRes.total_results).toBeGreaterThan(limitedRes.total_results);

      // Fusión determinista CAM <-> datos.madrid.es
      const madridCsvWithAndWithoutCam = [
        'PK;NOMBRE;CLASE-VIAL;NOMBRE-VIA;NUM;CODIGO-POSTAL;DISTRITO;LATITUD;LONGITUD;TELEFONO;EMAIL;ACCESIBILIDAD;CONTENT-URL;EQUIPAMIENTO;TRANSPORTE;TIPO',
        '99001;CENTRO TEST TEA SOL;CALLE;MAYOR;10;28013;CENTRO;40.420000;-3.710000;915551122;a@test.es;1;https://madrid.es/1;Autismo;Metro Sol;/contenido/centros',
        '99002;CENTRO TEST TEA SIN UTM CAM;CALLE;ALCALA;50;28009;RETIRO;40.421500;-3.681500;915553344;b@test.es;1;https://madrid.es/2;Autismo;Metro Retiro;/contenido/centros'
      ].join('\n');

      const camCentrosCsv = [
        'numero_registro;sector;tipo;subtipo;denominacion;plazas_autorizadas_numero;municipio_nombre;direccion_via_tipo;direccion_via_nombre;direccion_portal;direccion_codigo_postal;direccion_distrito;direccion_coor_x;direccion_coor_y;contacto_telefono;contacto_correo;entidad_denominacion;entidad_nif;tipo_gestion',
        'C9901;Personas con discapacidad;CENTROS DE DÍA;CENTROS DE DÍA PARA PERSONAS CON AUTISMO;CENTRO TEST TEA SOL;25;Madrid;CALLE;MAYOR;10;28013;CENTRO;440320;4474200;915551122;cam@test.es;ASOCIACION TEA TEST;G12345678;CONCERTADA',
        'C9902;Personas con discapacidad;CENTROS DE DÍA;CENTROS DE DÍA PARA PERSONAS CON AUTISMO;CENTRO TEST TEA SIN UTM CAM;20;Madrid;CALLE;ALCALA;50;28009;RETIRO;;;915553344;cam2@test.es;ASOCIACION TEA TEST;G12345678;PRIVADA'
      ].join('\n');

      const merged = buildCentresFromOfficialCSVs({
        madridCsvText: madridCsvWithAndWithoutCam,
        camCentrosCsvText: camCentrosCsv,
        snapshotDate: '2026-11-18'
      });

      expect(merged.centres.length).toBe(2);
      const withCamUtm = merged.centres.find(c => c.centre_id === 'CAM-C9901')!;
      const fallbackToMad = merged.centres.find(c => c.centre_id === 'CAM-C9902')!;

      expect(withCamUtm.provenance_records.some(p => p.source_dataset.includes('Registro de Centros'))).toBe(true);
      expect(withCamUtm.provenance_records.some(p => p.source_dataset.includes('datos.madrid.es PK 99001'))).toBe(true);
      // Coordenada UTM CAM prioritaria (~40.4168, -3.7038) sobre lat/lon municipal (40.42, -3.71)
      expect(withCamUtm.coordinates![0]).not.toBe(40.42);
      // Si falta UTM CAM, recurre determinísticamente a las coordenadas de datos.madrid.es
      expect(fallbackToMad.coordinates).toEqual([40.4215, -3.6815]);
      expect(fallbackToMad.provenance_records.some(p => p.source_dataset.includes('datos.madrid.es PK 99002'))).toBe(true);
    });

    it('formatOfficialSpanishName respeta formas jurídicas (S.L./S.A.), tildes mayúsculas, romanos y partículas', () => {
      expect(formatOfficialSpanishName('ÁREA DE ATENCIÓN TEMPRANA S.L.')).toBe('Área de Atención Temprana S.L.');
      expect(formatOfficialSpanishName('RESIDENCIA REINA SOFÍA II Y IV')).toBe('Residencia Reina Sofía II y IV');
      expect(formatOfficialSpanishName('CENTRO DE DÍA DEL HENARES DE LA VEGA')).toBe('Centro de Día del Henares de la Vega');
      expect(formatOfficialSpanishName('ÍNDICE DE APOYO XXI S.A.')).toBe('Índice de Apoyo XXI S.A.');
      expect(formatOfficialSpanishName('Asociación Mixta TEA Madrid')).toBe('Asociación Mixta TEA Madrid');
    });
  });

  describe('Property-Based Testing (fast-check, 1000 ejecuciones)', () => {
    const profileArb = fc.constantFrom<SearchQueryState['profile']>(
      'autism',
      'acquired_brain_injury',
      'cerebral_palsy',
      'neurodegenerative_diseases',
      'spinal_cord_injury',
      'als',
      'parkinson',
      'alzheimer',
      'psychomotor_early_support'
    );
    const supportsArb = fc.subarray(
      ['day_care', 'residential_care', 'occupational_therapy', 'speech_therapy', 'rehabilitation', 'psychological_support'] as const,
      { maxLength: 3 }
    );
    const networkArb = fc.constantFrom<SearchQueryState['network_preference']>(
      'all',
      'public_network',
      'private_authorised'
    );
    const suitabilityOrder: Record<string, number> = {
      complete: 0,
      partial: 1,
      unknown: 2,
      incompatible: 3
    };
    const evidenceOrder: Record<string, number> = {
      A1: 0,
      A2: 1,
      B1: 2,
      B2: 3,
      C: 4
    };

    const centreArb = fc.record({
      id: fc.string({ minLength: 2, maxLength: 8 }),
      explicit: fc.subarray(['autism', 'acquired_brain_injury', 'neurodegenerative_diseases', 'als', 'parkinson', 'alzheimer'] as const, { maxLength: 2 }),
      entitySpecs: fc.subarray(['autism', 'acquired_brain_injury'] as const, { maxLength: 1 }),
      supports: fc.subarray(['day_care', 'residential_care', 'occupational_therapy', 'speech_therapy', 'rehabilitation', 'psychological_support'] as const, { maxLength: 3 }),
      net: fc.constantFrom<SpecializedCentre['public_private_status']>(
        'red_publica',
        'concertado',
        'privado_autorizado',
        'no_especificado'
      ),
      coords: fc.tuple(
        fc.double({ min: 40.0, max: 40.8, noNaN: true }),
        fc.double({ min: -4.2, max: -3.2, noNaN: true })
      )
    });

    it('invariante lexicográfico: ningún peso subordinado voltea evidencia(A1 < A2 < B1 < B2 < C) ni adecuación dentro del mismo nivel', () => {
      fc.assert(
        fc.property(
          profileArb,
          supportsArb,
          networkArb,
          fc.constantFrom<'any_support' | 'all_supports_same_centre'>('any_support', 'all_supports_same_centre'),
          centreArb,
          centreArb,
          (profile, support_types, network_preference, support_combination_mode, specA, specB) => {
            const makeCentre = (spec: typeof specA, suffix: string): SpecializedCentre => ({
              ...MOCK_CENTRE_TEA,
              centre_id: `FC-${suffix}`,
              explicit_specialisations: [...spec.explicit],
              entity_declared_specialisations: spec.entitySpecs.filter(s => !spec.explicit.includes(s as any)),
              supports: [...spec.supports],
              related_services: ['Atención diurna', 'Neurología', 'Logopedia', 'Atención temprana'],
              public_private_status: spec.net,
              coordinates: spec.coords,
              has_valid_coordinates: true,
              allowed_life_stages: ['minor', 'adult']
            });

            const cA = makeCentre(specA, 'A');
            const cB = makeCentre(specB, 'B');
            const q: SearchQueryState = {
              ...DEFAULT_QUERY,
              profile,
              support_types: [...support_types],
              support_combination_mode,
              network_preference
            };

            const rA = evaluateCentre(cA, q, [cA, cB]);
            const rB = evaluateCentre(cB, q, [cA, cB]);

            if (rA.suitability !== 'incompatible' && rB.suitability !== 'incompatible') {
              const evDiff = evidenceOrder[rA.evidence_level] - evidenceOrder[rB.evidence_level];
              if (evDiff < 0) {
                expect(rA.sort_rank).toBeLessThan(rB.sort_rank);
              } else if (evDiff === 0) {
                const suitDiff = suitabilityOrder[rA.suitability] - suitabilityOrder[rB.suitability];
                if (suitDiff < 0) {
                  expect(rA.sort_rank).toBeLessThan(rB.sort_rank);
                }
              }
            }
          }
        ),
        { numRuns: 1000 }
      );
    });

    it('invariante de reglas negativas: un recurso genérico marcado con patrón negativo sin especialización explícita ni de entidad nunca obtiene A1 ni A2', () => {
      fc.assert(
        fc.property(
          fc.constantFrom<'autism' | 'acquired_brain_injury' | 'psychomotor_early_support' | 'neurodegenerative_diseases'>(
            'autism',
            'acquired_brain_injury',
            'psychomotor_early_support',
            'neurodegenerative_diseases'
          ),
          supportsArb,
          fc.constantFrom(
            'Personas con discapacidad intelectual',
            'Personas con enfermedad mental crónica',
            'Atención Temprana general',
            'Centro Ocupacional de inserción'
          ),
          (profile, support_types, negativeSector) => {
            const genericCentre: SpecializedCentre = {
              ...MOCK_CENTRE_TEA,
              centre_id: 'FC-NEG',
              official_name: negativeSector,
              subtype: negativeSector,
              sector: negativeSector,
              explicit_specialisations: [],
              entity_declared_specialisations: [],
              related_services: [negativeSector],
              supports: [...support_types]
            };

            const res = evaluateCentre(
              genericCentre,
              { ...DEFAULT_QUERY, profile, support_types: [...support_types] },
              [genericCentre]
            );
            expect(['A1', 'A2']).not.toContain(res.evidence_level);
          }
        ),
        { numRuns: 1000 }
      );
    });
  });

  describe('Parser de teléfonos españoles y coherencia de Nivel C', () => {
    it('separa múltiples teléfonos, concatenaciones de 18 dígitos y sufijos abreviados sin generar enlaces inválidos', () => {
      expect(extractSpanishPhoneNumbers('917345138 - 695424170').validNumbers).toEqual(['917345138', '695424170']);
      expect(extractSpanishPhoneNumbers('911048988655597499').validNumbers).toEqual(['911048988', '655597499']);
      expect(extractSpanishPhoneNumbers('91 694 53 05 / 06').validNumbers).toEqual(['916945305', '916945306']);
      expect(extractSpanishPhoneNumbers('91 383 99 27 / 89 62').validNumbers).toEqual(['913839927', '913838962']);
      expect(extractSpanishPhoneNumbers('914781011-60886253').validNumbers).toEqual(['914781011']);
      expect(extractSpanishPhoneNumbers('917 609 840 Esta línea funciona de lunes a viernes').validNumbers).toEqual(['917609840']);
      expect(extractSpanishPhoneNumbers('60602426').validNumbers).toEqual([]);
      expect(extractSpanishPhoneNumbers('346272035').validNumbers).toEqual([]);
      expect(extractSpanishPhoneNumbers('9.6172450').validNumbers).toEqual([]);
      expect(formatSpanishPhone('917345138')).toBe('917 345 138');
    });

    it('nunca devuelve suitability "complete" para Nivel C cuando hay un perfil activo', () => {
      const genericC: SpecializedCentre = {
        ...MOCK_CENTRE_TEA,
        centre_id: 'TEST-C-ONLY',
        official_name: 'Centro de Servicios Sociales General',
        subtype: 'Centro Municipal de Servicios Sociales',
        sector: 'Servicios Sociales',
        explicit_specialisations: [],
        entity_declared_specialisations: [],
        related_services: [],
        supports: []
      };
      const evaluated = evaluateCentre(
        genericC,
        { ...DEFAULT_QUERY, profile: 'autism' },
        [genericC]
      );
      expect(evaluated.evidence_level).toBe('C');
      expect(evaluated.suitability).not.toBe('complete');
    });
  });
});
