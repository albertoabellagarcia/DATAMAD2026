/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Benchmark Test Centres Dataset
 * Registros de prueba y reglas negativas para la suite de validación canónica.
 * Separados de los registros canónicos de producción (DATAMAD 2026).
 */

import { SpecializedCentre } from '../types/specialized';

export const BENCHMARK_TEST_CENTRES: SpecializedCentre[] = [
  // Test COMB-002 y DUP-001: Mismo proveedor en sedes distintas
  {
    centre_id: 'C-DUP-01A',
    provider_id: 'PROV-SAN-MARTIN',
    provider_name: 'Fundación San Martín',
    official_name: 'Fundación San Martín - Sede Centro (Terapia y Logopedia)',
    resource_domain: 'social',
    sector: 'Atención Social y Terapéutica',
    centre_type: 'Centro de Tratamiento Ambulatorio (Sede A)',
    subtype: 'Servicios de apoyo ambulatorio',
    public_private_status: 'concertado',
    management_type: 'Concertado con Consejería de Asuntos Sociales',
    address: 'Calle Mayor, 82',
    postal_code: '28013',
    municipality: 'Madrid',
    district: 'Centro',
    coordinates: [40.4155, -3.7112],
    has_valid_coordinates: true,
    phone: '915 48 20 10',
    email: 'centro@sanmartin.org',
    website: 'https://fundacionsanmartin.org',
    explicit_specialisations: ['autism', 'cerebral_palsy'],
    related_services: ['terapia ocupacional', 'logopedia', 'apoyo familiar'],
    supports: ['occupational_therapy', 'speech_therapy'],
    services_offered: [
      {
        service_id: 'SRV-DUP-01A-TO',
        centre_id: 'C-DUP-01A',
        service_name: 'Terapia Ocupacional Funcional',
        service_type: 'occupational_therapy',
        target_populations: ['autism', 'cerebral_palsy'],
        allowed_life_stages: ['minor', 'adult'],
        access_routes: ['direct'],
        source_dataset: 'Registro de Centros de Atención Social CAM',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/sm01',
        checked_at: '2026-10-01'
      },
      {
        service_id: 'SRV-DUP-01A-LOG',
        centre_id: 'C-DUP-01A',
        service_name: 'Logopedia y Comunicación',
        service_type: 'speech_therapy',
        target_populations: ['autism', 'cerebral_palsy'],
        allowed_life_stages: ['minor', 'adult'],
        access_routes: ['direct'],
        source_dataset: 'Registro de Centros de Atención Social CAM',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/sm01',
        checked_at: '2026-10-01'
      }
    ],
    allowed_life_stages: ['minor', 'adult'],
    access_route: {
      access_type: 'direct',
      competent_body: 'Fundación San Martín',
      official_description: 'Acceso directo a terapias ambulatorias previa entrevista con el equipo técnico.',
      source_url: 'https://fundacionsanmartin.org/admisiones',
      checked_at: '2026-10-01',
      next_step_action: 'Contacte con la secretaría de la Sede Centro para valorar disponibilidad horaria.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: 30,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/serviciossociales/centros/sm01',
      checked_at: '2026-10-01',
      stale: false
    },
    geographic_coverage: { type: 'community_wide', requires_residence: 'no', checked_at: '2026-10-01' },
    accessibility_features: ['Acceso con rampa y elevador adaptado'],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'autismo y parálisis cerebral',
        source_dataset: 'Registro Social CAM (SM01)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/sm01',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'J. M. Sánchez',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'A'
      }
    ],
    last_checked: '2026-10-01',
    limitations: ['En esta sede NO se presta Atención Diurna ni Residencia. Se prestan en la Sede Sur en Leganés.']
  },
  {
    centre_id: 'C-DUP-01B',
    provider_id: 'PROV-SAN-MARTIN',
    provider_name: 'Fundación San Martín',
    official_name: 'Fundación San Martín - Sede Sur Leganés (Centro de Día)',
    resource_domain: 'social',
    sector: 'Atención Social Diurna',
    centre_type: 'Centro de Día de Adultos (Sede B)',
    subtype: 'Estancia diurna especializada',
    public_private_status: 'concertado',
    management_type: 'Concertado con Consejería de Asuntos Sociales',
    address: 'Avenida del Rey Juan Carlos I, 90',
    postal_code: '28916',
    municipality: 'Leganés',
    coordinates: [40.3245, -3.7554],
    has_valid_coordinates: true,
    phone: '916 88 12 40',
    email: 'sedesur@sanmartin.org',
    website: 'https://fundacionsanmartin.org/sedesur',
    explicit_specialisations: ['autism', 'cerebral_palsy'],
    related_services: ['atención diurna', 'talleres ocupacionales', 'comedor adaptado'],
    supports: ['day_care'],
    services_offered: [
      {
        service_id: 'SRV-DUP-01B-DAY',
        centre_id: 'C-DUP-01B',
        service_name: 'Plazas de Centro de Día de Adultos',
        service_type: 'day_care',
        target_populations: ['autism', 'cerebral_palsy'],
        allowed_life_stages: ['adult'],
        access_routes: ['dependency_pia'],
        source_dataset: 'Registro de Centros de Atención Social CAM (Nº SM02)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/sm02',
        checked_at: '2026-10-01'
      }
    ],
    allowed_life_stages: ['adult'],
    access_route: {
      access_type: 'dependency_pia',
      competent_body: 'Servicios Sociales Leganés y Consejería de Familia',
      official_description: 'Plazas concertadas de Centro de Día concedidas mediante resolución del PIA.',
      source_url: 'https://fundacionsanmartin.org/acceso-pia',
      checked_at: '2026-10-01',
      next_step_action: 'Solicite plaza en Sede Sur mediante PIA con su trabajador/a social.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: 40,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/serviciossociales/centros/sm02',
      checked_at: '2026-10-01',
      stale: false
    },
    geographic_coverage: { type: 'multiple_municipalities', included_area_codes: ['0745', '0652', '0584'], requires_residence: 'yes', checked_at: '2026-10-01' },
    accessibility_features: ['Planta baja accesible', 'Baños adaptados'],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'autismo y parálisis cerebral',
        source_dataset: 'Registro Social CAM (SM02)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/sm02',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'J. M. Sánchez',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'A'
      }
    ],
    last_checked: '2026-10-01',
    limitations: ['Esta sede solo dispone de Centro de Día; las terapias ambulatorias se prestan en Sede Centro (Madrid).']
  },

  // Test NEG-001 y TAX-003: Neurología sin DCA explícito -> genera máximo B2
  {
    centre_id: 'C-NEG-NEU',
    provider_id: 'PROV-SERMAS',
    provider_name: 'SERMAS',
    official_name: 'Centro de Especialidades Médicas Los Pinos (Consulta de Neurología)',
    resource_domain: 'healthcare',
    sector: 'Sanitario Público',
    centre_type: 'Centro de Especialidades Periféricas',
    subtype: 'Consultas externas generales de especialidades médicas',
    public_private_status: 'red_publica',
    management_type: 'Pública directa (SERMAS)',
    address: 'Calle de los Pinos, 18',
    postal_code: '28028',
    municipality: 'Madrid',
    district: 'Salamanca',
    coordinates: [40.4321, -3.6622],
    has_valid_coordinates: true,
    phone: '914 02 11 00',
    email: 'cep.lospinos@salud.madrid.org',
    website: 'https://comunidad.madrid/sanidad/centros/cep-pinos',
    explicit_specialisations: [],
    related_services: ['neurología', 'diagnóstico electroencefalográfico'],
    supports: ['rehabilitation'],
    services_offered: [
      {
        service_id: 'SRV-NEG-NEU-01',
        centre_id: 'C-NEG-NEU',
        service_name: 'Consulta Externa de Neurología Clínica General',
        service_type: 'rehabilitation',
        target_populations: [],
        allowed_life_stages: ['adult', 'older_adult'],
        access_routes: ['referral'],
        source_dataset: 'Registro General de Centros Sanitarios (REGCESS)',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs9901',
        checked_at: '2026-10-01'
      }
    ],
    allowed_life_stages: ['adult', 'older_adult'],
    access_route: {
      access_type: 'referral',
      competent_body: 'Atención Primaria SERMAS',
      official_description: 'Cita previa tramitada exclusivamente por derivación del médico de familia.',
      source_url: 'https://comunidad.madrid/sanidad/regcess/cs9901',
      checked_at: '2026-10-01',
      next_step_action: 'Solicite interconsulta en su centro de salud.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'not_published',
      authorised_places: null,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/sanidad/regcess/cs9901',
      checked_at: '2026-10-01',
      stale: false
    },
    geographic_coverage: { type: 'district', requires_residence: 'yes', checked_at: '2026-10-01' },
    accessibility_features: ['Accesibilidad estándar ambulatoria'],
    provenance_records: [
      {
        attribute_name: 'services',
        value: 'neurología general',
        source_dataset: 'REGCESS Comunidad de Madrid',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs9901',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'Dr. C. Moreno',
        reviewer_role: 'healthcare',
        confidence: 'functional',
        quality: 'B'
      }
    ],
    last_checked: '2026-10-01',
    limitations: ['Consulta diagnóstica general; no es unidad monográfica de neurorrehabilitación intensiva de daño cerebral sobrevenido (máximo B2).']
  },

  // Test NEG-002 y TAX-004: Fisioterapia genérica -> no demuestra rehabilitación neurológica
  {
    centre_id: 'C-NEG-FIS',
    provider_id: 'PROV-LESCER',
    provider_name: 'Privado',
    official_name: 'Policlínica de Fisioterapia y Masoterapia Castellana',
    resource_domain: 'healthcare',
    sector: 'Sanitario Privado',
    centre_type: 'Consulta de Fisioterapia Privada',
    subtype: 'Fisioterapia traumatológica y deportiva',
    public_private_status: 'privado_autorizado',
    management_type: 'Privada autorizada',
    address: 'Paseo de la Castellana, 180',
    postal_code: '28046',
    municipality: 'Madrid',
    district: 'Chamartín',
    coordinates: [40.4589, -3.6892],
    has_valid_coordinates: true,
    phone: '913 50 11 88',
    email: 'contacto@fisio-castellana.com',
    website: 'https://fisio-castellana.com',
    explicit_specialisations: [],
    related_services: ['fisioterapia general', 'masoterapia', 'punción seca'],
    supports: ['rehabilitation'],
    services_offered: [
      {
        service_id: 'SRV-NEG-FIS-01',
        centre_id: 'C-NEG-FIS',
        service_name: 'Sesiones de Fisioterapia Traumatológica',
        service_type: 'rehabilitation',
        target_populations: [],
        allowed_life_stages: ['adult', 'older_adult'],
        access_routes: ['direct'],
        source_dataset: 'Registro General de Centros Sanitarios (REGCESS)',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs8804',
        checked_at: '2026-09-10'
      }
    ],
    allowed_life_stages: ['adult', 'older_adult'],
    access_route: {
      access_type: 'direct',
      competent_body: 'Dirección técnica de la clínica',
      official_description: 'Centro privado autorizado. Consulta y cita directa.',
      source_url: 'https://fisio-castellana.com',
      checked_at: '2026-09-10',
      next_step_action: 'Contacte con la clínica para tarifas y reserva.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: 10,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/sanidad/regcess/cs8804',
      checked_at: '2026-09-10',
      stale: false
    },
    geographic_coverage: { type: 'on_site_only', requires_residence: 'no', checked_at: '2026-09-10' },
    accessibility_features: ['Planta a nivel'],
    provenance_records: [
      {
        attribute_name: 'services',
        value: 'fisioterapia general',
        source_dataset: 'REGCESS',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs8804',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'Dra. E. Garrido',
        reviewer_role: 'healthcare',
        confidence: 'functional',
        quality: 'B'
      }
    ],
    last_checked: '2026-09-10',
    limitations: ['Fisioterapia general; no cuenta con acreditación de neurorrehabilitación intensiva para patología neurológica grave.']
  },

  // Test NEG-003 y TAX-002: Discapacidad intelectual sin mención a TEA -> NO debe inferir TEA
  {
    centre_id: 'C-NEG-DI',
    provider_id: 'PROV-CAM-DISCAP',
    provider_name: 'Red Pública Discapacidad',
    official_name: 'Centro Ocupacional Santa Ana para Discapacidad Intelectual',
    resource_domain: 'social',
    sector: 'Atención Social a la Discapacidad Intelectual',
    centre_type: 'Centro Ocupacional',
    subtype: 'Capacitación ocupacional para personas con discapacidad intelectual ligera o media',
    public_private_status: 'concertado',
    management_type: 'Concertado con Consejería de Asuntos Sociales',
    address: 'Calle Pintor Velázquez, 40',
    postal_code: '28935',
    municipality: 'Móstoles',
    coordinates: [40.3205, -3.8711],
    has_valid_coordinates: true,
    phone: '916 18 20 44',
    email: 'santa.ana@mostoles.org',
    website: 'https://comunidad.madrid/centros/co-santa-ana',
    explicit_specialisations: [],
    related_services: ['talleres ocupacionales', 'habilidades para la autonomía', 'atención diurna', 'apoyo laboral'],
    supports: ['day_care', 'employment_support'],
    services_offered: [
      {
        service_id: 'SRV-NEG-DI-01',
        centre_id: 'C-NEG-DI',
        service_name: 'Talleres Ocupacionales y de Ajuste Personal',
        service_type: 'day_care',
        target_populations: [],
        allowed_life_stages: ['adult'],
        access_routes: ['dependency_pia'],
        source_dataset: 'Registro de Centros de Atención Social CAM (Nº C-0520)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/c0520',
        checked_at: '2026-09-15'
      }
    ],
    allowed_life_stages: ['adult'],
    access_route: {
      access_type: 'dependency_pia',
      competent_body: 'Servicios Sociales Municipales de Móstoles y CAM',
      official_description: 'Plaza concertada gestionada mediante PIA con baremo de discapacidad intelectual.',
      source_url: 'https://comunidad.madrid/servicios/asuntos-sociales/dependencia-guia-acceso',
      checked_at: '2026-09-15',
      next_step_action: 'Consulte con su trabajadora social en Móstoles.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: 75,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/serviciossociales/centros/c0520',
      checked_at: '2026-09-15',
      stale: false
    },
    geographic_coverage: { type: 'municipality', included_area_codes: ['0921'], requires_residence: 'yes', checked_at: '2026-09-15' },
    accessibility_features: ['Señalización clara en texto grande'],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'discapacidad intelectual',
        source_dataset: 'Registro Social CAM',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/c0520',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'L. Valverde',
        reviewer_role: 'social',
        confidence: 'potential',
        quality: 'A'
      }
    ],
    last_checked: '2026-09-15',
    limitations: ['Regla negativa verificada: la discapacidad intelectual NO implica especialización en TEA.']
  },

  // Test GEO-001 y GEO-002: Centro sin coordenadas -> aparece en lista, excluido de radio y mapa
  {
    centre_id: 'C-GEO-NOCORD',
    provider_id: 'PROV-CAM-DISCAP',
    provider_name: 'Red Pública Regional',
    official_name: 'Centro Itinerante de Apoyo Comunitario y Orientación Familiar',
    resource_domain: 'social',
    sector: 'Atención Social en la Comunidad',
    centre_type: 'Servicio Comunitario Itinerante',
    subtype: 'Orientación psicopedagógica y social móvil',
    public_private_status: 'red_publica',
    management_type: 'Pública directa CAM',
    address: 'Sede administrativa en tramitación / Sin dirección fija abierta al público',
    postal_code: '28010',
    municipality: 'Madrid',
    coordinates: null,
    has_valid_coordinates: false,
    phone: '912 76 00 00',
    email: 'itinerante.apoyo@madrid.org',
    website: 'https://comunidad.madrid/serviciossociales/itinerante',
    explicit_specialisations: ['autism'],
    related_services: ['apoyo familiar', 'orientación a centros', 'logopedia'],
    supports: ['speech_therapy'],
    services_offered: [
      {
        service_id: 'SRV-GEO-01',
        centre_id: 'C-GEO-NOCORD',
        service_name: 'Orientación de Comunicación en Entorno Familiar',
        service_type: 'speech_therapy',
        target_populations: ['autism'],
        allowed_life_stages: ['early_childhood', 'minor'],
        access_routes: ['direct'],
        source_dataset: 'BOCM Disposición Reguladora',
        source_url: 'https://comunidad.madrid/bocm/itinerante-2026',
        checked_at: '2026-10-01'
      }
    ],
    allowed_life_stages: ['early_childhood', 'minor'],
    access_route: {
      access_type: 'direct',
      competent_body: 'Coordinación regional de servicios sociales',
      official_description: 'Servicio telefónico y presencial a demanda para familias.',
      source_url: 'https://comunidad.madrid/serviciossociales/itinerante',
      checked_at: '2026-10-01',
      next_step_action: 'Llamar al teléfono oficial para solicitar intervención en su zona.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: null,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/bocm/itinerante-2026',
      checked_at: '2026-10-01',
      stale: false
    },
    geographic_coverage: { type: 'community_wide', requires_residence: 'yes', checked_at: '2026-10-01' },
    accessibility_features: [],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'autismo',
        source_dataset: 'BOCM Publicación Oficial',
        source_url: 'https://comunidad.madrid/bocm/itinerante-2026',
        source_type: 'official_webpage',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'J. M. Sánchez',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'A'
      }
    ],
    last_checked: '2026-10-01',
    limitations: ['Centro sin coordenadas geográficas: permanece visible en la lista con aviso explícito pero no se computa en cálculo de radio ni se ubica en el mapa.']
  },

  // Test SRC-001: Contradicción de plazas entre Registro y Directorio -> bloquea atributo y muestra aviso
  {
    centre_id: 'C-SRC-CONF',
    provider_id: 'PROV-LESCER',
    provider_name: 'Grupo Norte Terapia',
    official_name: 'Centro Terapéutico y Asistencial Las Tablas',
    resource_domain: 'sociosanitary',
    sector: 'Sociosanitario',
    centre_type: 'Centro Ambulatorio y de Día',
    subtype: 'Rehabilitación y atención de día',
    public_private_status: 'privado_autorizado',
    management_type: 'Privada autorizada',
    address: 'Paseo de la Tierra de Melide, 24',
    postal_code: '28050',
    municipality: 'Madrid',
    district: 'Fuencarral-El Pardo',
    coordinates: [40.5098, -3.6702],
    has_valid_coordinates: true,
    phone: '918 22 10 30',
    email: 'tablas@terapia-norte.es',
    website: 'https://terapia-norte.es',
    explicit_specialisations: ['acquired_brain_injury'],
    related_services: ['rehabilitación', 'fisioterapia', 'terapia ocupacional'],
    supports: ['rehabilitation', 'occupational_therapy'],
    services_offered: [
      {
        service_id: 'SRV-SRC-01',
        centre_id: 'C-SRC-CONF',
        service_name: 'Neurorrehabilitación Funcional',
        service_type: 'rehabilitation',
        target_populations: ['acquired_brain_injury'],
        allowed_life_stages: ['adult'],
        access_routes: ['direct'],
        source_dataset: 'Registro General de Centros Sanitarios',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs7122',
        checked_at: '2026-10-01'
      }
    ],
    allowed_life_stages: ['adult'],
    access_route: {
      access_type: 'direct',
      competent_body: 'Dirección del centro',
      official_description: 'Admisión privada directa.',
      source_url: 'https://terapia-norte.es',
      checked_at: '2026-10-01',
      next_step_action: 'Contactar directamente.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: null,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/sanidad/regcess/cs7122',
      checked_at: '2026-10-01',
      stale: false
    },
    conflict_record: {
      attribute: 'authorised_places',
      source_a: { value: 30, date: '2026-10-01', type: 'Registro Oficial REGCESS' },
      source_b: { value: 25, date: '2026-09-15', type: 'Directorio Especializado Discapacidad' },
      status: 'unresolved',
      public_value: null,
      public_message: 'La capacidad publicada no es coincidente entre registros oficiales (30 según REGCESS vs 25 según Directorio). Atributo bloqueado pendiente de subsanación.'
    },
    geographic_coverage: { type: 'community_wide', requires_residence: 'no', checked_at: '2026-10-01' },
    accessibility_features: ['Acceso con rampa'],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'daño cerebral adquirido',
        source_dataset: 'REGCESS Comunidad de Madrid',
        source_url: 'https://comunidad.madrid/sanidad/regcess/cs7122',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'Dr. C. Moreno',
        reviewer_role: 'healthcare',
        confidence: 'explicit',
        quality: 'A'
      }
    ],
    last_checked: '2026-10-01',
    limitations: ['Conflicto de fuentes detectado en plazas autorizadas: ambas evidencias se registran sin alterar silenciosamente el dato.']
  },

  // Test ACC-002 y ACC-005: Vía de acceso no documentada -> muestra "Debe confirmarse con el organismo competente"
  {
    centre_id: 'C-ACC-UNK',
    provider_id: 'PROV-SAN-MARTIN',
    provider_name: 'Asociación Local',
    official_name: 'Gabinete Comunitario de Estimulación Funcional Alcobendas',
    resource_domain: 'social',
    sector: 'Atención Social de Base',
    centre_type: 'Centro Asistencial Menor',
    subtype: 'Apoyo y estimulación cognitiva',
    public_private_status: 'privado_autorizado',
    management_type: 'Entidad social local',
    address: 'Calle del Fuego, 15',
    postal_code: '28100',
    municipality: 'Alcobendas',
    coordinates: [40.5420, -3.6391],
    has_valid_coordinates: true,
    phone: '916 51 00 22',
    email: 'contacto@alcobendas-estimulacion.org',
    website: 'https://alcobendas-estimulacion.org',
    explicit_specialisations: ['cerebral_palsy'],
    related_services: ['rehabilitación', 'fisioterapia'],
    supports: ['rehabilitation'],
    services_offered: [
      {
        service_id: 'SRV-ACC-UNK-01',
        centre_id: 'C-ACC-UNK',
        service_name: 'Fisioterapia y Mantenimiento Postural',
        service_type: 'rehabilitation',
        target_populations: ['cerebral_palsy'],
        allowed_life_stages: ['adult'],
        access_routes: ['unknown'],
        source_dataset: 'Registro Social CAM',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/g081',
        checked_at: '2026-09-01'
      }
    ],
    allowed_life_stages: ['adult'],
    access_route: {
      access_type: 'unknown',
      competent_body: 'Organismo titular pendiente de contrastar',
      official_description: 'Vía de acceso o derivación no especificada en el registro oficial vigente.',
      source_url: 'https://comunidad.madrid/serviciossociales/centros/g081',
      checked_at: '2026-09-01',
      next_step_action: 'Debe confirmarse con el organismo competente o contactar al centro antes de desplazarse.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'contact_required',
      authorised_places: 15,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/serviciossociales/centros/g081',
      checked_at: '2026-09-01',
      stale: false
    },
    geographic_coverage: { type: 'municipality', included_area_codes: ['0066'], requires_residence: 'yes', checked_at: '2026-09-01' },
    accessibility_features: [],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'parálisis cerebral',
        source_dataset: 'Registro Social CAM (G081)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/g081',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'L. Valverde',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'A'
      }
    ],
    last_checked: '2026-09-01',
    limitations: ['Vía de acceso ausente en fuente oficial: no se infiere acceso directo.']
  },

  // Test AVL-001: Disponibilidad de hace >30 días -> estado "Confirmar con el centro"
  {
    centre_id: 'C-STALE-AVL',
    provider_id: 'PROV-FEMM',
    provider_name: 'Fundación NeuroSalud',
    official_name: 'Residencia Asistida de Enfermedades Neurodegenerativas Los Rosales',
    resource_domain: 'social',
    sector: 'Atención Social Residencial',
    centre_type: 'Residencia Especializada',
    subtype: 'Atención continuada 24 horas',
    public_private_status: 'concertado',
    management_type: 'Concertada CAM',
    address: 'Camino de los Vinateros, 102',
    postal_code: '28030',
    municipality: 'Madrid',
    district: 'Moratalaz',
    coordinates: [40.4071, -3.6521],
    has_valid_coordinates: true,
    phone: '914 30 55 99',
    email: 'losrosales@neurosalud.org',
    website: 'https://neurosalud.org/rosales',
    explicit_specialisations: ['neurodegenerative_diseases'],
    related_services: ['residencia', 'fisioterapia', 'terapia ocupacional'],
    supports: ['residential_care', 'rehabilitation'],
    services_offered: [
      {
        service_id: 'SRV-STALE-01',
        centre_id: 'C-STALE-AVL',
        service_name: 'Alojamiento Asistido Continuado',
        service_type: 'residential_care',
        target_populations: ['neurodegenerative_diseases'],
        allowed_life_stages: ['adult', 'older_adult'],
        access_routes: ['dependency_pia'],
        source_dataset: 'Registro de Centros de Atención Social CAM',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/r044',
        checked_at: '2026-08-10'
      }
    ],
    allowed_life_stages: ['adult', 'older_adult'],
    access_route: {
      access_type: 'dependency_pia',
      competent_body: 'Consejería de Asuntos Sociales',
      official_description: 'Plaza concertada asignada por PIA.',
      source_url: 'https://comunidad.madrid/serviciossociales/centros/r044',
      checked_at: '2026-08-10',
      next_step_action: 'Compruebe con Servicios Sociales de Moratalaz.',
      availability_known: false,
      waiting_list_known: false
    },
    availability: {
      status: 'stale',
      authorised_places: 45,
      vacancies_known: false,
      source_url: 'https://comunidad.madrid/serviciossociales/centros/r044',
      checked_at: '2026-08-10',
      stale: true
    },
    geographic_coverage: { type: 'community_wide', requires_residence: 'yes', checked_at: '2026-08-10' },
    accessibility_features: ['Baños geriátricos', 'Montacamillas'],
    provenance_records: [
      {
        attribute_name: 'specialisation',
        value: 'enfermedades neurodegenerativas',
        source_dataset: 'Registro Social CAM (R044)',
        source_url: 'https://comunidad.madrid/serviciossociales/centros/r044',
        source_type: 'official_registry',
        retrieved_at: '2026-11-08',
        extraction_method: 'structured',
        reviewer: 'J. M. Sánchez',
        reviewer_role: 'social',
        confidence: 'explicit',
        quality: 'B'
      }
    ],
    last_checked: '2026-08-10',
    limitations: ['Dato de disponibilidad verificado hace más de 30 días: clasificado como "Confirmar con el centro".']
  }
];
