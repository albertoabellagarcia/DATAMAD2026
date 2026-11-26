/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Taxonomy Subsystem
 * Taxonomía externa, ampliable, versionada y gobernada (v1.8.0)
 * Fecha de publicación: 2026-11-08 · DATAMAD 2026
 */

import { 
  CoreProfileId, 
  ExperimentalProfileId, 
  PendingProfileId, 
  ProfileId, 
  SupportTypeId, 
  FunctionalNeedId, 
  LifeStage, 
  AccessRouteType 
} from '../types/specialized';

export interface TaxonomyProfileDefinition {
  id: ProfileId;
  status: 'approved' | 'experimental' | 'pending_review' | 'deprecated';
  preferred_label: string;
  category_family: 'neurológicos' | 'neurodesarrollo' | 'discapacidad_fisica_sensorial' | 'salud_mental' | 'dependencia';
  explicit_terms: string[];
  synonyms: string[];
  excluded_terms: string[];
  related_services: string[];
  allowed_life_stages: LifeStage[];
  typical_supports?: SupportTypeId[];
  typical_needs?: FunctionalNeedId[];
  forbidden_inferences: string[];
  access_routes: AccessRouteType[];
  evidence_thresholds: {
    level_a_precision: number;
    level_b_precision: number;
    minimum_explicit_centres: number;
  };
  review_date: string;
  reviewer_roles: ('healthcare' | 'social_services' | 'accessibility')[];
  description: string;
}

export interface TaxonomySupportDefinition {
  id: SupportTypeId;
  label: string;
  official_terms: string[];
  description: string;
  typical_domain: 'social' | 'healthcare' | 'both';
}

export interface TaxonomyNeedDefinition {
  id: FunctionalNeedId;
  label: string;
  description: string;
  observable_criteria: string[];
}

export interface LifeStageTransitionDef {
  current_stage: LifeStage;
  next_stage: LifeStage;
  label: string;
  description: string;
  alert_title: string;
  recommended_action: string;
}

export const TAXONOMY_METADATA = {
  version: '1.9.0',
  released_at: '2026-11-19',
  status: 'current',
  active_profiles_count: 3,
  experimental_profiles_count: 3,
  pending_profiles_count: 7,
  deprecated_profiles_count: 0,
  governance_rules_count: 8,
  canonical_queries_count: 28,
  minimum_review_requirements: {
    level_a_precision: 0.95,
    level_b_precision: 0.85,
    minimum_explicit_centres: 3
  }
};

/**
 * 4 Perfiles núcleo del MVP obligatorio (§3.1, §88.2)
 */
export const CORE_PROFILES: Record<CoreProfileId, TaxonomyProfileDefinition> = {
  autism: {
    id: 'autism',
    status: 'approved',
    preferred_label: 'Trastorno del espectro del autismo (TEA)',
    category_family: 'neurodesarrollo',
    explicit_terms: ['trastorno del espectro del autismo', 'TEA', 'autismo', 'síndrome de asperger'],
    synonyms: ['condición del espectro autista', 'CEA'],
    excluded_terms: ['discapacidad intelectual', 'salud mental genérica'],
    related_services: ['atención temprana', 'logopedia', 'terapia ocupacional', 'apoyo social', 'habilidades sociales'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult', 'older_adult'],
    typical_supports: ['speech_therapy', 'occupational_therapy', 'day_care', 'employment_support', 'psychological_support'],
    typical_needs: ['communication', 'social_skills', 'sensory_regulation', 'daily_autonomy', 'work_preparation', 'family_respite'],
    forbidden_inferences: [
      'TEA no se infiere desde discapacidad intelectual.',
      'TEA no se infiere desde neurodivergencia sin desambiguar.',
      'Atención temprana no implica especialización en TEA a menos que conste literalmente.'
    ],
    access_routes: ['direct', 'referral', 'dependency_pia', 'private_contact'],
    evidence_thresholds: {
      level_a_precision: 0.96,
      level_b_precision: 0.88,
      minimum_explicit_centres: 5
    },
    review_date: '2026-11-08',
    reviewer_roles: ['healthcare', 'social_services', 'accessibility'],
    description: 'Condición del neurodesarrollo caracterizada por diferencias en comunicación, interacción social y patrones de comportamiento e intereses.'
  },
  acquired_brain_injury: {
    id: 'acquired_brain_injury',
    status: 'approved',
    preferred_label: 'Daño cerebral adquirido (DCA)',
    category_family: 'neurológicos',
    explicit_terms: ['daño cerebral adquirido', 'DCA', 'ictus y secuelas', 'traumatismo craneoencefálico'],
    synonyms: ['anoxia cerebral', 'lesión cerebral sobrevenida'],
    excluded_terms: ['neurología ambulatoria general', 'fisioterapia osteopática'],
    related_services: ['neurología', 'rehabilitación neurológica', 'fisioterapia', 'terapia ocupacional', 'logopedia', 'neuropsicología'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult', 'older_adult'],
    typical_supports: ['rehabilitation', 'speech_therapy', 'occupational_therapy', 'day_care', 'psychological_support', 'respiratory_physiotherapy'],
    typical_needs: ['mobility', 'communication', 'swallowing', 'fine_gross_motor', 'cognition_memory', 'daily_autonomy', 'family_respite'],
    forbidden_inferences: [
      'Neurología genérica no demuestra especialización en daño cerebral adquirido (máximo B2).',
      'Fisioterapia general no demuestra rehabilitación neurológica intensiva.',
      'Centro de día de mayores no equivale a centro de día especializado en DCA.'
    ],
    access_routes: ['referral', 'dependency_pia', 'direct', 'private_contact'],
    evidence_thresholds: {
      level_a_precision: 0.97,
      level_b_precision: 0.89,
      minimum_explicit_centres: 4
    },
    review_date: '2026-11-08',
    reviewer_roles: ['healthcare', 'social_services'],
    description: 'Lesión sobrevenida y súbita en las estructuras cerebrales tras el nacimiento, debida a ictus, traumatismos, anoxias o tumores.'
  },
  cerebral_palsy: {
    id: 'cerebral_palsy',
    status: 'experimental',
    preferred_label: 'Parálisis cerebral y patologías afines',
    category_family: 'neurológicos',
    explicit_terms: ['parálisis cerebral', 'patologías afines', 'encefalopatía motora'],
    synonyms: ['PC', 'PCI'],
    excluded_terms: ['discapacidad física genérica sin especificar', 'geriatría general'],
    related_services: ['rehabilitación', 'fisioterapia especializada', 'logopedia y deglución', 'terapia ocupacional'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult', 'older_adult'],
    typical_supports: ['rehabilitation', 'speech_therapy', 'occupational_therapy', 'day_care', 'residential_care'],
    typical_needs: ['mobility', 'fine_gross_motor', 'swallowing', 'communication', 'daily_autonomy', 'family_respite'],
    forbidden_inferences: [
      'Centro para discapacidad física no demuestra parálisis cerebral ni patologías afines (máximo C).',
      'Fisioterapia general sin neurorrehabilitación no eleva a nivel A.'
    ],
    access_routes: ['dependency_pia', 'referral', 'direct', 'private_contact'],
    evidence_thresholds: {
      level_a_precision: 0.95,
      level_b_precision: 0.86,
      minimum_explicit_centres: 3
    },
    review_date: '2026-11-15',
    reviewer_roles: ['healthcare', 'social_services'],
    description: 'Grupo de trastornos del desarrollo psicomotor y postural causados por lesión o malformación no progresiva del cerebro fetal o infantil. En evaluación (2/3 centros explícitos A1 en CSV sociales actuales).'
  },
  neurodegenerative_diseases: {
    id: 'neurodegenerative_diseases',
    status: 'approved',
    preferred_label: 'Esclerosis múltiple y enf. neurodegenerativas',
    category_family: 'neurológicos',
    explicit_terms: ['esclerosis múltiple', 'enfermedades neurodegenerativas', 'enfermedades degenerativas'],
    synonyms: ['EM', 'patologías neurodegenerativas'],
    excluded_terms: ['electromedicina', 'urgencias hospitalarias generales'],
    related_services: ['neurología', 'fisioterapia motora', 'terapia ocupacional', 'rehabilitación neurológica'],
    allowed_life_stages: ['adult', 'older_adult'],
    typical_supports: ['rehabilitation', 'occupational_therapy', 'day_care', 'psychological_support', 'speech_therapy'],
    typical_needs: ['mobility', 'fine_gross_motor', 'cognition_memory', 'daily_autonomy', 'swallowing', 'family_respite'],
    forbidden_inferences: [
      'Neurología general no demuestra especialización en esclerosis múltiple ni enfermedades degenerativas.',
      'Fisioterapia deportiva no demuestra mantenimiento funcional neurológico.'
    ],
    access_routes: ['dependency_pia', 'referral', 'direct', 'private_contact'],
    evidence_thresholds: {
      level_a_precision: 0.95,
      level_b_precision: 0.87,
      minimum_explicit_centres: 3
    },
    review_date: '2026-11-08',
    reviewer_roles: ['healthcare', 'social_services'],
    description: 'Trastornos neurológicos caracterizados por la pérdida progresiva y continua de estructura o función de las neuronas.'
  }
};

/**
 * 2 Perfiles experimentales con métricas separadas (§25.2, §88.2)
 */
export const EXPERIMENTAL_PROFILES: Record<ExperimentalProfileId, TaxonomyProfileDefinition> = {
  spinal_cord_injury: {
    id: 'spinal_cord_injury',
    status: 'experimental',
    preferred_label: 'Lesión medular (Reserva/Experimental)',
    category_family: 'discapacidad_fisica_sensorial',
    explicit_terms: ['lesión medular', 'tetraplejia', 'paraplejia'],
    synonyms: ['traumatismo medular'],
    excluded_terms: ['discapacidad física sin lesión medular'],
    related_services: ['rehabilitación médica', 'fisioterapia intensiva', 'terapia ocupacional', 'adaptación del entorno'],
    allowed_life_stages: ['minor', 'adult', 'older_adult'],
    typical_supports: ['rehabilitation', 'occupational_therapy', 'respiratory_physiotherapy', 'residential_care'],
    typical_needs: ['mobility', 'fine_gross_motor', 'daily_autonomy', 'family_respite'],
    forbidden_inferences: [
      'Discapacidad física general no demuestra atención a lesión medular (máximo C).',
      'Fisioterapia ambulatoria básica no garantiza transferencias ni manejo vesical.'
    ],
    access_routes: ['referral', 'dependency_pia', 'direct'],
    evidence_thresholds: {
      level_a_precision: 0.90,
      level_b_precision: 0.82,
      minimum_explicit_centres: 2
    },
    review_date: '2026-10-15',
    reviewer_roles: ['healthcare', 'social_services'],
    description: 'Afectación de la médula espinal que conduce a la alteración o pérdida de la función motora, sensitiva o autonómica.'
  },
  psychomotor_early_support: {
    id: 'psychomotor_early_support',
    status: 'experimental',
    preferred_label: 'Atención temprana y necesidades psicomotrices (Experimental)',
    category_family: 'neurodesarrollo',
    explicit_terms: ['atención temprana psicomotriz', 'psicomotricidad en atención temprana'],
    synonyms: ['trastorno psicomotor infantil'],
    excluded_terms: ['gimnasia infantil'],
    related_services: ['fisioterapia pediátrica', 'terapia ocupacional infantil', 'estimulación temprana', 'logopedia infantil'],
    allowed_life_stages: ['early_childhood'],
    typical_supports: ['rehabilitation', 'occupational_therapy', 'speech_therapy', 'psychological_support'],
    typical_needs: ['mobility', 'fine_gross_motor', 'sensory_regulation', 'communication', 'family_respite'],
    forbidden_inferences: [
      'Atención temprana genérica no prueba psicomotricidad específica si la fuente no lo expresa literalmente.',
      'Fisioterapia u ocupacional genérica de adultos no aplican a la primera infancia.'
    ],
    access_routes: ['referral', 'direct', 'dependency_pia'],
    evidence_thresholds: {
      level_a_precision: 0.91,
      level_b_precision: 0.80,
      minimum_explicit_centres: 2
    },
    review_date: '2026-10-20',
    reviewer_roles: ['healthcare', 'social_services', 'accessibility'],
    description: 'Intervención integral dirigida a la primera infancia (0-6 años) con alteraciones o riesgo en el desarrollo psicomotor.'
  }
};

/**
 * 7 Perfiles pendientes de revisión experta (en Gobernanza Taxonómica)
 */
export const PENDING_PROFILES: Record<PendingProfileId, TaxonomyProfileDefinition> = {
  adhd: {
    id: 'adhd',
    status: 'pending_review',
    preferred_label: 'TDAH (Trastorno por déficit de atención e hiperactividad)',
    category_family: 'neurodesarrollo',
    explicit_terms: ['TDAH', 'déficit de atención'],
    synonyms: ['TDA'],
    excluded_terms: [],
    related_services: ['apoyo psicopedagógico', 'entrenamiento neurocognitivo'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult'],
    typical_supports: ['psychological_support', 'occupational_therapy', 'employment_support'],
    typical_needs: ['cognition_memory', 'social_skills', 'daily_autonomy', 'work_preparation', 'family_respite'],
    forbidden_inferences: ['TDAH no se confunde con TEA ni discapacidad intelectual.'],
    access_routes: ['direct', 'referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2026-12-01',
    reviewer_roles: ['healthcare', 'accessibility'],
    description: 'Condición neurobiológica caracterizada por dificultades para mantener la atención, control de impulsos o hiperactividad.'
  },
  als: {
    id: 'als',
    status: 'pending_review',
    preferred_label: 'Esclerosis lateral amiotrófica (ELA)',
    category_family: 'neurológicos',
    explicit_terms: ['ELA', 'esclerosis lateral amiotrófica'],
    synonyms: [],
    excluded_terms: [],
    related_services: ['fisioterapia respiratoria', 'comunicación aumentativa', 'terapia ocupacional'],
    allowed_life_stages: ['adult', 'older_adult'],
    typical_supports: ['respiratory_physiotherapy', 'speech_therapy', 'occupational_therapy', 'rehabilitation', 'psychological_support'],
    typical_needs: ['swallowing', 'communication', 'mobility', 'fine_gross_motor', 'daily_autonomy', 'family_respite'],
    forbidden_inferences: ['Requiere validación de centros con unidad multidisciplinar.'],
    access_routes: ['referral', 'dependency_pia'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2026-12-01',
    reviewer_roles: ['healthcare'],
    description: 'Enfermedad neuromuscular degenerativa progresiva que afecta a las neuronas motoras.'
  },
  parkinson: {
    id: 'parkinson',
    status: 'pending_review',
    preferred_label: 'Enfermedad de Párkinson',
    category_family: 'neurológicos',
    explicit_terms: ['párkinson', 'parkinsonismo'],
    synonyms: [],
    excluded_terms: [],
    related_services: ['fisioterapia neurológica', 'logopedia y voz', 'terapia ocupacional'],
    allowed_life_stages: ['adult', 'older_adult'],
    typical_supports: ['rehabilitation', 'speech_therapy', 'occupational_therapy', 'day_care', 'psychological_support'],
    typical_needs: ['mobility', 'fine_gross_motor', 'communication', 'swallowing', 'daily_autonomy', 'cognition_memory'],
    forbidden_inferences: ['No confundir con temblor esencial no catalogado.'],
    access_routes: ['direct', 'dependency_pia', 'referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2026-12-15',
    reviewer_roles: ['healthcare'],
    description: 'Trastorno neurodegenerativo del sistema nervioso central que afecta el control motor y la dopamina.'
  },
  alzheimer: {
    id: 'alzheimer',
    status: 'pending_review',
    preferred_label: 'Enfermedad de Alzheimer y demencias',
    category_family: 'dependencia',
    explicit_terms: ['alzheimer', 'demencia tipo alzheimer', 'deterioro cognitivo severo'],
    synonyms: [],
    excluded_terms: [],
    related_services: ['estimulación cognitiva', 'centro de día terapéutico', 'residencia especializada'],
    allowed_life_stages: ['older_adult', 'adult'],
    typical_supports: ['day_care', 'residential_care', 'psychological_support', 'occupational_therapy'],
    typical_needs: ['cognition_memory', 'daily_autonomy', 'family_respite', 'social_skills', 'mobility'],
    forbidden_inferences: ['No equiparar residencia ordinaria sin módulo de psicogeriatría.'],
    access_routes: ['dependency_pia', 'referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2026-12-15',
    reviewer_roles: ['social_services', 'healthcare'],
    description: 'Enfermedad neurodegenerativa que causa problemas con la memoria, el pensamiento y el comportamiento.'
  },
  rare_diseases: {
    id: 'rare_diseases',
    status: 'pending_review',
    preferred_label: 'Enfermedades raras y poco frecuentes',
    category_family: 'neurológicos',
    explicit_terms: ['enfermedades raras', 'enfermedades poco frecuentes'],
    synonyms: [],
    excluded_terms: [],
    related_services: ['atención multidisciplinar', 'rehabilitación integral'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult'],
    typical_supports: ['rehabilitation', 'speech_therapy', 'occupational_therapy', 'psychological_support'],
    typical_needs: ['mobility', 'communication', 'swallowing', 'daily_autonomy', 'family_respite'],
    forbidden_inferences: ['Exige acreditación específica de CSUR o centro colaborador.'],
    access_routes: ['referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2027-01-10',
    reviewer_roles: ['healthcare'],
    description: 'Patologías con baja prevalencia que precisan abordaje sociosanitario altamente especializado.'
  },
  hearing_disability: {
    id: 'hearing_disability',
    status: 'pending_review',
    preferred_label: 'Discapacidad auditiva y sordoceguera',
    category_family: 'discapacidad_fisica_sensorial',
    explicit_terms: ['discapacidad auditiva', 'sordera', 'sordoceguera'],
    synonyms: ['hipoacusia'],
    excluded_terms: [],
    related_services: ['logopedia auditivo-verbal', 'intérprete LSE', 'apoyo a la comunicación'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult', 'older_adult'],
    typical_supports: ['speech_therapy', 'employment_support', 'occupational_therapy'],
    typical_needs: ['communication', 'social_skills', 'work_preparation', 'sensory_regulation'],
    forbidden_inferences: ['No confundir con centros educativos ordinarios sin recursos específicos.'],
    access_routes: ['direct', 'referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2027-01-15',
    reviewer_roles: ['accessibility', 'social_services'],
    description: 'Pérdida auditiva sensorial o mixta y condiciones de doble discapacidad sensorial.'
  },
  visual_disability: {
    id: 'visual_disability',
    status: 'pending_review',
    preferred_label: 'Discapacidad visual y baja visión',
    category_family: 'discapacidad_fisica_sensorial',
    explicit_terms: ['discapacidad visual', 'ceguera', 'baja visión'],
    synonyms: [],
    excluded_terms: [],
    related_services: ['rehabilitación visual', 'tiflotecnología', 'entrenamiento en movilidad'],
    allowed_life_stages: ['early_childhood', 'minor', 'adult', 'older_adult'],
    typical_supports: ['occupational_therapy', 'employment_support', 'day_care'],
    typical_needs: ['daily_autonomy', 'mobility', 'work_preparation', 'social_skills'],
    forbidden_inferences: ['Requiere convenio ONCE o servicio reconocido.'],
    access_routes: ['direct', 'referral'],
    evidence_thresholds: { level_a_precision: 0.95, level_b_precision: 0.85, minimum_explicit_centres: 3 },
    review_date: '2027-01-15',
    reviewer_roles: ['accessibility'],
    description: 'Disminución significativa de la agudeza o campo visual no corregible con lentes convencionales.'
  }
};

/**
 * 6 Tipos de apoyo iniciales (§3.2, §17)
 */
export const SUPPORT_TYPES: Record<SupportTypeId, TaxonomySupportDefinition> = {
  rehabilitation: {
    id: 'rehabilitation',
    label: 'Rehabilitación física y neurológica',
    official_terms: ['rehabilitación', 'fisioterapia neurológica', 'fisioterapia especializada'],
    typical_domain: 'healthcare',
    description: 'Tratamiento terapéutico destinado a restablecer o mantener la máxima capacidad funcional e independencia motora.'
  },
  day_care: {
    id: 'day_care',
    label: 'Atención diurna (Centro de Día / Ocupacional)',
    official_terms: ['centro de día', 'atención diurna', 'centro ocupacional'],
    typical_domain: 'social',
    description: 'Servicio socioasistencial diurno de soporte para el desarrollo de la autonomía personal y estimulación continuada.'
  },
  occupational_therapy: {
    id: 'occupational_therapy',
    label: 'Terapia ocupacional y autonomía',
    official_terms: ['terapia ocupacional', 'entrenamiento en actividades de la vida diaria'],
    typical_domain: 'both',
    description: 'Intervención enfocada en capacitar a la persona para participar en las actividades cotidianas del hogar y comunidad.'
  },
  speech_therapy: {
    id: 'speech_therapy',
    label: 'Logopedia y comunicación',
    official_terms: ['logopedia', 'comunicación aumentativa y alternativa', 'terapia miofuncional y deglución'],
    typical_domain: 'both',
    description: 'Prevención, diagnóstico y tratamiento de trastornos de la comunicación, lenguaje, habla, voz y deglución.'
  },
  residential_care: {
    id: 'residential_care',
    label: 'Alojamiento o atención residencial',
    official_terms: ['residencia', 'vivienda tutelada', 'atención residencial asistida'],
    typical_domain: 'social',
    description: 'Servicio residencial continuado con apoyo y supervisión profesional adaptado al nivel de dependencia.'
  },
  employment_support: {
    id: 'employment_support',
    label: 'Apoyo laboral y ocupacional',
    official_terms: ['inserción laboral', 'empleo con apoyo', 'capacitación ocupacional'],
    typical_domain: 'social',
    description: 'Orientación, formación y adaptación de puestos de trabajo para favorecer la inclusión en el mercado laboral ordinario o protegido.'
  },
  psychological_support: {
    id: 'psychological_support',
    label: 'Apoyo psicológico y neuropsicología',
    official_terms: ['neuropsicología', 'psicología clínica especializada', 'apoyo psicológico'],
    typical_domain: 'both',
    description: 'Evaluación e intervención neuropsicológica y apoyo emocional a personas y familias.'
  },
  respiratory_physiotherapy: {
    id: 'respiratory_physiotherapy',
    label: 'Fisioterapia respiratoria y deglutoria',
    official_terms: ['fisioterapia respiratoria', 'manejo de secreciones', 'rehabilitación pulmonar'],
    typical_domain: 'healthcare',
    description: 'Técnicas de aclaramiento mucociliar, mantenimiento de volúmenes pulmonares y prevención de aspiraciones.'
  }
};

/**
 * 10 Necesidades funcionales transversales (§50.1)
 */
export const FUNCTIONAL_NEEDS: Record<FunctionalNeedId, TaxonomyNeedDefinition> = {
  communication: {
    id: 'communication',
    label: 'Comunicación y lenguaje',
    description: 'Dificultades en expresión o comprensión oral, habla o necesidad de sistemas aumentativos (SAAC).',
    observable_criteria: ['Comprensión verbal', 'Expresión verbal', 'Uso de pictogramas o pulsadores', 'Articulación']
  },
  mobility: {
    id: 'mobility',
    label: 'Movilidad, equilibrio y coordinación',
    description: 'Dificultad para desplazamientos autónomos, marcha, bipedestación o control postural.',
    observable_criteria: ['Uso de silla de ruedas', 'Bipedestación asistida', 'Caídas frecuentes', 'Transferencias']
  },
  fine_gross_motor: {
    id: 'fine_gross_motor',
    label: 'Motricidad fina y gruesa',
    description: 'Manipulación de objetos cotidianos, prensión, coordinación visomotora o tono muscular.',
    observable_criteria: ['Pinza digital', 'Fuerza en extremidades', 'Espasticidad', 'Coordinación manual']
  },
  swallowing: {
    id: 'swallowing',
    label: 'Deglución y alimentación segura',
    description: 'Dificultad o atragantamientos al tragar líquidos o sólidos (disfagia).',
    observable_criteria: ['Disfagia a líquidos', 'Espesantes', 'Riesgo de aspiración', 'Alimentación adaptada']
  },
  daily_autonomy: {
    id: 'daily_autonomy',
    label: 'Autonomía y actividades diarias (AVD)',
    description: 'Higiene personal, vestido, aseo, manejo de dinero o preparación de alimentos.',
    observable_criteria: ['Ducha autónoma', 'Vestido y calzado', 'Manejo de utensilios', 'Seguridad en casa']
  },
  cognition_memory: {
    id: 'cognition_memory',
    label: 'Cognición, atención y memoria',
    description: 'Deterioro o alteración en funciones ejecutivas, concentración, orientación o memoria inmediata.',
    observable_criteria: ['Desorientación temporoespacial', 'Olvidos de tareas', 'Planificación secuencial']
  },
  sensory_regulation: {
    id: 'sensory_regulation',
    label: 'Regulación sensorial y propiocepción',
    description: 'Hipersensibilidad o hiposensibilidad a ruidos, texturas, luces o necesidad de calma sensorial.',
    observable_criteria: ['Sobrecarga acústica', 'Defensa táctil', 'Búsqueda vestibular', 'Aislamiento sensorial']
  },
  social_skills: {
    id: 'social_skills',
    label: 'Habilidades sociales y conducta',
    description: 'Interacción con iguales, comprensión de normas sociales, manejo de la frustración.',
    observable_criteria: ['Contacto visual', 'Turno de palabra', 'Gestión de crisis emocionales', 'Empatía']
  },
  work_preparation: {
    id: 'work_preparation',
    label: 'Preparación laboral y ocupacional',
    description: 'Desarrollo de competencias laborales, puntualidad, destreza técnica y hábitos de trabajo.',
    observable_criteria: ['Cumplimiento de tareas', 'Manejo de herramientas', 'Adaptación al puesto']
  },
  family_respite: {
    id: 'family_respite',
    label: 'Apoyo familiar y respiro',
    description: 'Carga de cuidados familiares, necesidad de respiro de fin de semana o estancia temporal.',
    observable_criteria: ['Sobrecarga del cuidador', 'Atención en periodos vacacionales', 'Orientación a familias']
  }
};

/**
 * 4 Etapas vitales (§3.3)
 */
export const LIFE_STAGES: Record<LifeStage, { label: string; ageRange: string; description: string }> = {
  early_childhood: {
    label: 'Primera infancia',
    ageRange: '0 a 6 años',
    description: 'Etapa de atención temprana y neurodesarrollo temprano.'
  },
  minor: {
    label: 'Menor / Etapa escolar',
    ageRange: '6 a 17 años',
    description: 'Etapa escolar obligatoria y desarrollo en educación primaria y secundaria.'
  },
  adult: {
    label: 'Persona adulta',
    ageRange: '18 a 64 años',
    description: 'Etapa adulta con necesidad de rehabilitación, autonomía personal o inserción laboral.'
  },
  older_adult: {
    label: 'Persona mayor',
    ageRange: '65+ años',
    description: 'Atención especializada únicamente cuando la fuente declare expresamente compatibilidad con personas mayores.'
  }
};

/**
 * Avisos de transición entre etapas vitales (§85)
 */
export const LIFE_STAGE_TRANSITIONS: Record<LifeStage, LifeStageTransitionDef | null> = {
  early_childhood: {
    current_stage: 'early_childhood',
    next_stage: 'minor',
    label: 'De atención temprana a etapa escolar',
    alert_title: 'Aviso de transición preventiva: Fin de atención temprana (6 años)',
    description: 'Al cumplir 6 años finaliza la cobertura del Servicio de Atención Temprana de la Comunidad de Madrid. Es fundamental preparar con antelación el apoyo educativo y los recursos sociosanitarios ambulatorios.',
    recommended_action: 'Ver recursos compatibles de etapa escolar o consultar el puente con Madrid Educa Apoyo.'
  },
  minor: {
    current_stage: 'minor',
    next_stage: 'adult',
    label: 'De servicios para menores a servicios para personas adultas',
    alert_title: 'Aviso de transición a la vida adulta (18 años)',
    description: 'A partir de los 18 años los recursos cambian a la red de atención a personas adultas con discapacidad, centros de día y centros ocupacionales. Requiere trámite previo de PIA.',
    recommended_action: 'Planificar el reconocimiento de grado y la valoración de recursos ocupacionales de adultos.'
  },
  adult: null,
  older_adult: null
};

/**
 * Desambiguación obligatoria de términos amplios (§54)
 */
export const DISAMBIGUATION_TERMS = {
  neurodivergent: {
    trigger_words: ['neurodivergente', 'neurodivergencia', 'neurodiversidad'],
    title: 'Desambiguación obligatoria: "Neurodivergente"',
    warning: 'Por rigor ético y metodológico, la aplicación no diagnostica ni utiliza "neurodivergente" como categoría médica o administrativa final. Por favor, precise el apoyo concreto que busca:',
    options: [
      { id: 'autism', label: 'Trastorno del espectro del autismo (TEA)', type: 'profile' },
      { id: 'adhd', label: 'TDAH (Déficit de atención e hiperactividad)', type: 'profile_pending' },
      { id: 'communication', label: 'Apoyo a la comunicación y lenguaje', type: 'need' },
      { id: 'sensory_regulation', label: 'Regulación sensorial e integración', type: 'need' },
      { id: 'social_skills', label: 'Habilidades sociales y relacionales', type: 'need' },
      { id: 'speech_therapy', label: 'Servicio de logopedia especializada', type: 'support' },
      { id: 'employment_support', label: 'Apoyo ocupacional e inserción laboral', type: 'support' }
    ]
  },
  psychomotor: {
    trigger_words: ['psicomotriz', 'psicomotricidad', 'psicomotor'],
    title: 'Desambiguación obligatoria: "Psicomotriz"',
    warning: 'La psicomotricidad se divide en necesidades funcionales observables. La fisioterapia genérica no prueba psicomotricidad si la fuente oficial no lo declara explícitamente.',
    options: [
      { id: 'psychomotor_early_support', label: 'Atención temprana psicomotriz (0-6 años)', type: 'profile_exp' },
      { id: 'mobility', label: 'Movilidad, marcha y equilibrio', type: 'need' },
      { id: 'fine_gross_motor', label: 'Motricidad fina y manipulación', type: 'need' },
      { id: 'sensory_regulation', label: 'Integración sensorial', type: 'need' },
      { id: 'occupational_therapy', label: 'Terapia ocupacional especializada', type: 'support' }
    ]
  }
};

/**
 * Reglas de inferencia negativa obligatorias (§26.1, §31, §44)
 */
export const FORBIDDEN_INFERENCES = [
  {
    id: 'NEG-001',
    rule: 'Neurología genérica no demuestra especialización en Daño Cerebral Adquirido o Enfermedad Neurodegenerativa.',
    consequence: 'Máximo nivel B2 (Servicio relacionado; confirmación requerida). Nunca nivel A.'
  },
  {
    id: 'NEG-002',
    rule: 'Centro de discapacidad física genérica no demuestra lesión medular ni parálisis cerebral.',
    consequence: 'Limitado a nivel C (orientación general; no alcanza nivel A ni B sin mención expresa, sin excluir del listado).'
  },
  {
    id: 'NEG-003',
    rule: 'Discapacidad intelectual no implica ni infiere Trastorno del Espectro del Autismo (TEA).',
    consequence: 'Limitado a nivel C (0 falsos positivos como especializado en TEA, manteniendo visible el recurso con aviso).'
  },
  {
    id: 'NEG-004',
    rule: 'Plazas autorizadas no demuestran vacantes ni disponibilidad de ingreso.',
    consequence: 'Siempre etiquetar "Plazas autorizadas según registro oficial. No confundir con vacantes libres".'
  },
  {
    id: 'NEG-005',
    rule: 'Autorización privada no demuestra concierto ni financiación pública.',
    consequence: 'No clasificar como Red Pública. Etiquetar como "Privado autorizado".'
  },
  {
    id: 'NEG-006',
    rule: 'Salud mental crónica no se infiere hacia TEA ni hacia trastornos neurológicos o neurodegenerativos.',
    consequence: 'Limitado a nivel C con aviso de confirmación; nunca nivel A ni B.'
  },
  {
    id: 'NEG-007',
    rule: 'Atención temprana no implica psicomotricidad específica si no consta literalmente.',
    consequence: 'Limitado como máximo a nivel B2 (servicio relacionado pendiente de confirmar con el centro, sin excluir).'
  },
  {
    id: 'NEG-008',
    rule: 'La cercanía geográfica nunca puede situar un resultado nivel C por delante de un nivel A1 o A2.',
    consequence: 'Orden lexicográfico estricto: Evidencia > Adecuación > Disponibilidad > Cobertura > Distancia.'
  }
];

/**
 * Mapeo de Interoperabilidad con Madrid Educa Apoyo (§86)
 */
export const EDUCATION_BRIDGE_MAPPINGS = [
  {
    source_field: 'municipality',
    target_field: 'municipality',
    label: 'Municipio territorial',
    transferable: true,
    action: 'transfer'
  },
  {
    source_field: 'profile_autism',
    target_field: 'need_tea',
    label: 'TEA -> Alumnado con TEA (Aulas de Apoyo TEA / Preferente)',
    transferable: true,
    action: 'transfer'
  },
  {
    source_field: 'profile_cerebral_palsy',
    target_field: 'need_motora',
    label: 'Parálisis cerebral -> Discapacidad motora en colegios',
    transferable: true,
    action: 'transfer'
  },
  {
    source_field: 'support_speech_therapy',
    target_field: 'resource_al',
    label: 'Logopedia -> Maestro/a de Audición y Lenguaje (AL)',
    transferable: true,
    action: 'transfer'
  },
  {
    source_field: 'support_occupational_therapy',
    target_field: 'resource_pt',
    label: 'Terapia Ocupacional -> Pedagogía Terapéutica (PT) / Fisioterapeuta escolar',
    transferable: true,
    action: 'transfer'
  },
  {
    source_field: 'support_day_care',
    target_field: 'none',
    label: 'Atención diurna (Centro de Día social)',
    transferable: false,
    action: 'no_transfer',
    reason: 'Sin equivalencia directa en la red escolar ordinaria.'
  },
  {
    source_field: 'support_residential',
    target_field: 'none',
    label: 'Alojamiento residencial',
    transferable: false,
    action: 'no_transfer',
    reason: 'Servicio social no aplicable a colegios e institutos.'
  }
];
