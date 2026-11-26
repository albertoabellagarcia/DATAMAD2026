/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Type Definitions
 * Buscador transversal de recursos de atención social autorizados de la Comunidad de Madrid
 * DATAMAD 2026 · Código abierto · Orientación, no diagnóstico
 */

export type CoreProfileId = 
  | 'autism' 
  | 'acquired_brain_injury' 
  | 'cerebral_palsy' 
  | 'neurodegenerative_diseases';

export type ExperimentalProfileId = 
  | 'spinal_cord_injury' 
  | 'psychomotor_early_support';

export type PendingProfileId = 
  | 'adhd' 
  | 'als' 
  | 'parkinson' 
  | 'alzheimer' 
  | 'rare_diseases' 
  | 'hearing_disability' 
  | 'visual_disability';

export type ProfileId = CoreProfileId | ExperimentalProfileId | PendingProfileId | string;

export type LifeStage = 'early_childhood' | 'minor' | 'adult' | 'older_adult';

export type SupportTypeId = 
  | 'rehabilitation' 
  | 'day_care' 
  | 'occupational_therapy' 
  | 'speech_therapy' 
  | 'residential_care' 
  | 'employment_support' 
  | 'psychological_support' 
  | 'respiratory_physiotherapy';

export type FunctionalNeedId = 
  | 'communication' 
  | 'mobility' 
  | 'fine_gross_motor' 
  | 'swallowing' 
  | 'daily_autonomy' 
  | 'cognition_memory' 
  | 'sensory_regulation' 
  | 'social_skills' 
  | 'work_preparation' 
  | 'family_respite';

export type NetworkPreference = 'all' | 'public_network' | 'private_authorised';

export type EvidenceLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C';

export type SuitabilityStatus = 'complete' | 'partial' | 'incompatible' | 'unknown';

export type AccessRouteType = 
  | 'direct' 
  | 'referral' 
  | 'dependency_pia' 
  | 'private_contact' 
  | 'unknown';

export type AvailabilityStatus = 
  | 'available_confirmed' 
  | 'waiting_list' 
  | 'no_places' 
  | 'admission_closed' 
  | 'contact_required' 
  | 'not_published' 
  | 'stale';

export type ExtractionMethod = 'structured' | 'manual_review' | 'controlled_mapping';
export type ReviewerRole = 'social' | 'healthcare' | 'accessibility' | 'data_steward';
export type SourceQualityRank = 'A' | 'B' | 'C' | 'D';

export type CombinationMode = 'any_support' | 'all_supports_same_centre';

export type CombinationStatus = 
  | 'all_same_centre' 
  | 'partial_same_centre' 
  | 'same_provider_diff_centres' 
  | 'coordinated_network' 
  | 'not_confirmed';

export interface AttributeProvenance {
  attribute_name: string;
  value: string;
  source_dataset: string;
  source_url: string;
  source_type: 'official_registry' | 'official_directory' | 'official_webpage' | 'manual_confirmation';
  source_version?: string;
  retrieved_at: string;
  published_at?: string;
  extraction_method: ExtractionMethod;
  reviewer: string;
  reviewer_role: ReviewerRole;
  confidence: 'explicit' | 'functional' | 'potential';
  quality: SourceQualityRank;
}

export interface CriterionEvidence {
  criterion_id: string;
  criterion_label: string;
  requested: boolean;
  status: 'confirmed' | 'not_stated' | 'incompatible' | 'calculated' | 'confirm_required';
  source_url?: string;
  source_fragment?: string;
  checked_at?: string;
  note?: string;
}

export type EvidenceSublevel = 'A1' | 'A2_support' | 'A2_entity' | 'B1' | 'B2' | 'C';

export interface MatchExplanation {
  level: EvidenceLevel;
  sublevel?: EvidenceSublevel;
  suitability: SuitabilityStatus;
  because: string[];
  does_not_confirm: string[];
  sources: {
    attribute: string;
    source_dataset: string;
    source_url: string;
    fragment?: string;
  }[];
  suitability_reasons: string[];
}

export type MatchAssessment = MatchExplanation;

export interface LifeStageTransitionDef {
  current_stage: LifeStage;
  next_stage: LifeStage;
  label: string;
  description: string;
  alert_title: string;
  recommended_action: string;
}

export interface AccessRouteDetail {
  access_type: AccessRouteType;
  competent_body: string;
  official_description: string;
  source_url: string;
  checked_at: string;
  next_step_action: string;
  availability_known: boolean;
  waiting_list_known: boolean;
}

export interface AvailabilityDetail {
  status: AvailabilityStatus;
  authorised_places: number | null;
  vacancies_known: boolean; // Must always be false unless official live source
  source_url: string;
  checked_at: string;
  valid_until?: string;
  stale: boolean;
}

export interface GeographicCoverage {
  type: 'on_site_only' | 'municipality' | 'district' | 'multiple_municipalities' | 'community_wide' | 'home_service_area' | 'not_published';
  included_area_codes?: string[];
  requires_residence: 'yes' | 'no' | 'unknown';
  source_url?: string;
  checked_at: string;
}

export interface ServiceRecord {
  service_id: string;
  centre_id: string;
  service_name: string;
  service_type: SupportTypeId;
  target_populations: ProfileId[];
  allowed_life_stages: LifeStage[];
  access_routes: AccessRouteType[];
  source_dataset: string;
  source_url: string;
  checked_at: string;
}

export interface ProviderRecord {
  provider_id: string;
  legal_name: string;
  public_name: string;
  management_type: 'pública_directa' | 'privada_concertada' | 'privada_autorizada' | 'social_entidad';
  official_id: string;
}

export interface ConflictRecord {
  attribute: string;
  source_a: { value: string | number; date: string; type: string };
  source_b: { value: string | number; date: string; type: string };
  status: 'unresolved' | 'resolved';
  public_value: string | number | null;
  public_message: string;
}

export interface SpecializedCentre {
  centre_id: string;
  provider_id: string;
  provider_name: string;
  official_name: string;
  resource_domain: 'social' | 'healthcare' | 'sociosanitary';
  sector: string;
  centre_type: string;
  subtype: string;
  public_private_status: 'red_publica' | 'concertado' | 'privado_autorizado' | 'no_especificado';
  management_type: string;
  address: string;
  postal_code: string;
  municipality: string;
  district?: string;
  coordinates: [number, number] | null; // null if unknown
  has_valid_coordinates: boolean;
  phone: string;
  email: string;
  website: string;
  explicit_specialisations: ProfileId[];
  entity_declared_specialisations?: ProfileId[];
  related_services: string[];
  supports: SupportTypeId[];
  services_offered: ServiceRecord[];
  allowed_life_stages: LifeStage[];
  access_route: AccessRouteDetail;
  availability: AvailabilityDetail;
  geographic_coverage: GeographicCoverage;
  accessibility_features: string[];
  provenance_records: AttributeProvenance[];
  conflict_record?: ConflictRecord;
  last_checked: string;
  limitations: string[];
  is_individual_practitioner?: boolean;
}

export interface SearchQueryState {
  profile: ProfileId | null;
  functional_needs: FunctionalNeedId[];
  support_types: SupportTypeId[];
  support_combination_mode: CombinationMode;
  life_stage: LifeStage | null;
  municipality: string | null;
  radius_km: number;
  network_preference: NetworkPreference;
  accessibility_needs: string[];
  user_ephemeral_location: [number, number] | null;
  location_mode: 'browser' | 'municipality' | 'all';
}

export interface EvaluatedCentreResult {
  centre: SpecializedCentre;
  match_assessment: MatchAssessment;
  evidence_level: EvidenceLevel;
  evidence_sublevel?: EvidenceSublevel;
  suitability: SuitabilityStatus;
  combination_status: CombinationStatus;
  combination_details: {
    support_id: SupportTypeId;
    support_label: string;
    status: 'confirmed' | 'no_consta' | 'incompatible';
    checked_at: string;
  }[];
  distance_km: number | null;
  distance_label: string;
  transit_time_minutes: number | null;
  transit_time_label: string | null;
  is_in_radius: boolean;
  criterion_matrix: CriterionEvidence[];
  sort_rank: number; // Lexicographic sort score
}

export interface SavedSearch {
  saved_search_id: string;
  name: string;
  created_at: string;
  updated_at: string;
  filters: {
    profile: ProfileId | null;
    functional_needs: FunctionalNeedId[];
    support_types: SupportTypeId[];
    support_combination_mode: CombinationMode;
    life_stage: LifeStage | null;
    municipality: string | null;
    radius_km: number;
    network_preference: NetworkPreference;
    accessibility_needs: string[];
  };
  taxonomy_version: string;
  dataset_snapshot: string;
}

export interface SnapshotDifference {
  change_id: string;
  change_type: 
    | 'centre_added'
    | 'centre_removed'
    | 'centre_renamed'
    | 'service_added'
    | 'service_removed'
    | 'access_route_changed'
    | 'availability_expired'
    | 'source_broken'
    | 'merged_record';
  centre_id: string;
  centre_name: string;
  previous_snapshot: string;
  current_snapshot: string;
  detail: string;
  reason: string;
  category: 'alta' | 'baja' | 'servicio' | 'acceso' | 'vigencia' | 'incidencia_fuente' | 'deduplicacion';
}

export interface CitizenCorrection {
  correction_id: string;
  centre_id: string;
  centre_name: string;
  reason: 'phone' | 'closed' | 'address' | 'service_not_provided' | 'age_incorrect' | 'duplicate' | 'broken_link' | 'other';
  reason_label: string;
  user_details: string;
  created_at: string;
  status: 'received' | 'in_review' | 'verified' | 'rejected' | 'applied';
}
