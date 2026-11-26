/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Official CSV Registry Parser & Evidence Classifier
 * Convierte de forma determinista y sin extrapolaciones los 3 CSV oficiales descargados:
 *   1. Catálogo de Centros de Atención Social (datos.madrid.es)
 *   2. Registro General de Centros de Atención Social (datos.comunidad.madrid)
 *   3. Registro General de Servicios de Atención Social (datos.comunidad.madrid)
 */

import {
  SpecializedCentre,
  ProfileId,
  SupportTypeId,
  LifeStage,
  AccessRouteType,
  AttributeProvenance
} from '../types/specialized';
import { extractSpanishPhoneNumbers } from './phoneUtils';

export const OFFICIAL_DATASET_URLS = {
  madrid_municipal: 'https://datos.madrid.es/dataset/212774-0-atencion-social',
  cam_centros: 'https://datos.comunidad.madrid/dataset/atencion_social_registro_centros',
  cam_servicios: 'https://datos.comunidad.madrid/dataset/atencion_social_registro_servicios'
};

export interface SnapshotCentreRecord {
  registry_key: string;
  source_id: 'madrid_municipal' | 'cam_centros' | 'cam_servicios';
  official_name: string;
  phone: string;
  address: string;
  municipality: string;
  postal_code: string;
  authorised_places: number | null;
  accessibility_code?: string;
}

export function parseSemicolonCSV(text: string): string[][] {
  const clean = text.replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentVal = '';
  let insideQuote = false;

  for (let i = 0; i < clean.length; i++) {
    const char = clean[i];
    const nextChar = clean[i + 1];

    if (char === '"' && insideQuote && nextChar === '"') {
      currentVal += '"';
      i++;
    } else if (char === '"') {
      insideQuote = !insideQuote;
    } else if (char === ';' && !insideQuote) {
      currentRow.push(currentVal.trim());
      currentVal = '';
    } else if ((char === '\r' || char === '\n') && !insideQuote) {
      if (char === '\r' && nextChar === '\n') i++;
      currentRow.push(currentVal.trim());
      if (currentRow.length > 1) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentVal = '';
    } else {
      currentVal += char;
    }
  }
  if (currentRow.length > 1) {
    currentRow.push(currentVal.trim());
    rows.push(currentRow);
  }
  return rows;
}

/**
 * Conversión exacta ETRS89 UTM Huso 30N (EPSG:25830) -> WGS84 [lat, lon]
 */
export function utm30NToWgs84(easting: number, northing: number): [number, number] | null {
  if (!Number.isFinite(easting) || !Number.isFinite(northing)) return null;
  if (easting < 300000 || easting > 550000 || northing < 4400000 || northing > 4600000) {
    return null;
  }

  const a = 6378137.0;
  const f = 1 / 298.257222101;
  const k0 = 0.9996;
  const e2 = 2 * f - f * f;
  const ep2 = e2 / (1 - e2);
  const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));

  const x = easting - 500000.0;
  const y = northing;

  const M = y / k0;
  const mu =
    M /
    (a *
      (1 - e2 / 4 - (3 * e2 * e2) / 64 - (5 * e2 * e2 * e2) / 256));

  const phi1 =
    mu +
    ((3 * e1) / 2 - (27 * Math.pow(e1, 3)) / 32) * Math.sin(2 * mu) +
    ((21 * Math.pow(e1, 2)) / 16 - (55 * Math.pow(e1, 4)) / 32) * Math.sin(4 * mu) +
    ((151 * Math.pow(e1, 3)) / 96) * Math.sin(6 * mu) +
    ((1097 * Math.pow(e1, 4)) / 512) * Math.sin(8 * mu);

  const sinPhi1 = Math.sin(phi1);
  const cosPhi1 = Math.cos(phi1);
  const tanPhi1 = Math.tan(phi1);

  const N1 = a / Math.sqrt(1 - e2 * sinPhi1 * sinPhi1);
  const T1 = tanPhi1 * tanPhi1;
  const C1 = ep2 * cosPhi1 * cosPhi1;
  const R1 = (a * (1 - e2)) / Math.pow(1 - e2 * sinPhi1 * sinPhi1, 1.5);
  const D = x / (N1 * k0);

  const latRad =
    phi1 -
    ((N1 * tanPhi1) / R1) *
      ((D * D) / 2 -
        ((5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * Math.pow(D, 4)) / 24 +
        ((61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * Math.pow(D, 6)) / 720);

  const lonRad =
    (-3 * Math.PI) / 180 +
    (D -
      ((1 + 2 * T1 + C1) * Math.pow(D, 3)) / 6 +
      ((5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * Math.pow(D, 5)) / 120) /
      cosPhi1;

  const lat = Number(((latRad * 180) / Math.PI).toFixed(6));
  const lon = Number(((lonRad * 180) / Math.PI).toFixed(6));

  if (lat < 39.8 || lat > 41.25 || lon < -4.65 || lon > -3.0) {
    return null;
  }
  return [lat, lon];
}

export function normalizeStrict(text: string): string {
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

export function normalizePhoneComparable(phone: string): string {
  if (!phone) return '';
  const clean = phone.trim().toUpperCase();
  if (clean === 'RESERVADO' || clean === 'N/D') return '';
  const parsed = extractSpanishPhoneNumbers(phone);
  if (parsed.validNumbers.length > 0) {
    return parsed.validNumbers[0];
  }
  const firstSegment = clean.split(/[\/;,]/)[0].trim();
  const digits = firstSegment.replace(/\D/g, '');
  return digits.length >= 9 ? digits.slice(0, 9) : digits;
}

function normalizePhoneFieldForCatalog(rawPhone: string): string {
  const clean = (rawPhone || '').trim();
  if (!clean || /^(RESERVADO|N\/D)$/i.test(clean)) return '';
  const parsed = extractSpanishPhoneNumbers(clean);
  if (parsed.formattedNumbers.length > 0) {
    return parsed.formattedNumbers.join(' / ');
  }
  return clean;
}

export function decodeHtmlEntities(text: string): string {
  if (!text || !text.includes('&')) return text || '';
  return text
    .replace(/&amp;/gi, '&')
    .replace(/&ntilde;/g, 'ñ')
    .replace(/&Ntilde;/g, 'Ñ')
    .replace(/&aacute;/g, 'á')
    .replace(/&Aacute;/g, 'Á')
    .replace(/&eacute;/g, 'é')
    .replace(/&Eacute;/g, 'É')
    .replace(/&iacute;/g, 'í')
    .replace(/&Iacute;/g, 'Í')
    .replace(/&oacute;/g, 'ó')
    .replace(/&Oacute;/g, 'Ó')
    .replace(/&uacute;/g, 'ú')
    .replace(/&Uacute;/g, 'Ú')
    .replace(/&uuml;/g, 'ü')
    .replace(/&Uuml;/g, 'Ü')
    .replace(/&quot;/g, '"');
}

export function normalizeAddressComparable(address: string): string {
  return normalizeStrict(decodeHtmlEntities(address))
    .replace(/^(calle|cl|c|avda|av|avenida|plaza|pl|pza|paseo|ps|pso|cmno|cam|camino|ronda|rda|bulevar|bulv|bulev|ctra|carretera|glorieta|gta|trva|travesia|cstan|costanilla|pque|parque)\s+/g, '')
    .replace(/\b(de la|del|de los|de las|de|la|el|los|las)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const PRESERVED_SPANISH_ACRONYMS = new Set([
  'TEA', 'DCA', 'ELA', 'TDAH', 'TDA', 'ASPACE', 'AMDEM', 'CEPRI', 'APADIS',
  'CRECOVI', 'ONCE', 'CRPS', 'CRL', 'CD', 'CO', 'COFOIL', 'CAD', 'CAT', 'CAM',
  'PAUTA', 'AUCAVI', 'APNA', 'AFEM', 'AMAFE', 'FAMMA', 'ASION', 'ATIPADACE',
  'APANEFA', 'ADELA', 'FEDER', 'AVIVA', 'EASC', 'SAT', 'SA', 'SL', 'SLU', 'SAU',
  'SAL', 'SLL', 'SERMAS', 'PEVS', 'PIA', 'RGPD', 'IMSERSO', 'COCEMFE', 'FEAPS',
  'AFANIAS', 'APANID', 'INTRESS', 'APASCOVI', 'POLIBEA', 'AFA', 'ENVERA',
  'CIRVITE', 'PAU', 'UAD', 'CMM', 'CEAPAT', 'ALCER', 'ASINDOWN', 'FUNDOWN',
  'ASEM', 'ADISLI', 'ANFAS', 'AETAPI', 'FESORCAM', 'ASCASAM', 'ACUDEM', 'APROCOR',
  'APAMA', 'APAMP', 'AMAS', 'ALEPH', 'AVANTE', 'FMP', 'AFEAM', 'DNI', 'NIF', 'II', 'III', 'IV',
  'VI', 'VII', 'VIII', 'IX', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XXI', 'XXIII'
]);

const LOWERCASE_SPANISH_PREPOSITIONS = new Set([
  'de', 'del', 'en', 'y', 'e', 'a', 'o', 'u',
  'al', 'con', 'contra', 'para', 'por', 'sin', 'su', 'sus'
]);

const LOWERCASE_SPANISH_ARTICLES = new Set(['la', 'las', 'los', 'el']);

const RESTORED_SPANISH_DIACRITICS: Record<string, string> = {
  accion: 'acción',
  alarcon: 'alarcón',
  alcala: 'alcalá',
  alcorcon: 'alcorcón',
  angel: 'ángel',
  angeles: 'ángeles',
  animacion: 'animación',
  animo: 'ánimo',
  apostol: 'apóstol',
  area: 'área',
  areas: 'áreas',
  arguelles: 'argüelles',
  asociacion: 'asociación',
  atencion: 'atención',
  autonomia: 'autonomía',
  bahia: 'bahía',
  basica: 'básica',
  basico: 'básico',
  becquer: 'bécquer',
  benefico: 'benéfico',
  betica: 'bética',
  bifida: 'bífida',
  calderon: 'calderón',
  carmenes: 'cármenes',
  chamartin: 'chamartín',
  chamberi: 'chamberí',
  circulo: 'círculo',
  clarin: 'clarín',
  clinica: 'clínica',
  clinico: 'clínico',
  comunicacion: 'comunicación',
  confederacion: 'confederación',
  congregacion: 'congregación',
  consejeria: 'consejería',
  cooperacion: 'cooperación',
  corazon: 'corazón',
  crispin: 'crispín',
  cronica: 'crónica',
  cronicos: 'crónicos',
  dali: 'dalí',
  dedicacion: 'dedicación',
  dia: 'día',
  dias: 'días',
  diaz: 'díaz',
  educacion: 'educación',
  estimulacion: 'estimulación',
  federacion: 'federación',
  fermin: 'fermín',
  fernandez: 'fernández',
  fisica: 'física',
  fisico: 'físico',
  fisicos: 'físicos',
  formacion: 'formación',
  fundacion: 'fundación',
  garcia: 'garcía',
  genero: 'género',
  geriatrica: 'geriátrica',
  geriatrico: 'geriátrico',
  gestion: 'gestión',
  gomez: 'gómez',
  guia: 'guía',
  habilitacion: 'habilitación',
  hepatico: 'hepático',
  hernandez: 'hernández',
  inclusion: 'inclusión',
  indice: 'índice',
  informacion: 'información',
  iniciacion: 'iniciación',
  insercion: 'inserción',
  institucion: 'institución',
  integracion: 'integración',
  interpretes: 'intérpretes',
  intervencion: 'intervención',
  investigacion: 'investigación',
  jaen: 'jaén',
  jardineria: 'jardinería',
  jazmin: 'jazmín',
  jesus: 'jesús',
  jimenez: 'jiménez',
  jose: 'josé',
  jovenes: 'jóvenes',
  leganes: 'leganés',
  leon: 'león',
  lesion: 'lesión',
  limite: 'límite',
  linea: 'línea',
  lopez: 'lópez',
  maria: 'maría',
  martin: 'martín',
  martinez: 'martínez',
  mediacion: 'mediación',
  medica: 'médica',
  medico: 'médico',
  minusvalido: 'minusválido',
  minusvalidos: 'minusválidos',
  miopia: 'miopía',
  mostoles: 'móstoles',
  multiple: 'múltiple',
  multiples: 'múltiples',
  neurologica: 'neurológica',
  neurologico: 'neurológico',
  neuropsicologica: 'neuropsicológica',
  nicolas: 'nicolás',
  orientacion: 'orientación',
  paralisis: 'parálisis',
  paralitico: 'paralítico',
  paraliticos: 'paralíticos',
  paraplejicos: 'parapléjicos',
  participacion: 'participación',
  patologia: 'patología',
  pechuan: 'pechuán',
  pedagogia: 'pedagogía',
  pedagogica: 'pedagógica',
  pedagogicos: 'pedagógicos',
  pediatria: 'pediatría',
  perez: 'pérez',
  pingarron: 'pingarrón',
  planificacion: 'planificación',
  potenciacion: 'potenciación',
  preparacion: 'preparación',
  prestacion: 'prestación',
  prevencion: 'prevención',
  principe: 'príncipe',
  promocion: 'promoción',
  proteccion: 'protección',
  psicogeriatrico: 'psicogeriátrico',
  psicologica: 'psicológica',
  psiquiatria: 'psiquiatría',
  psiquica: 'psíquica',
  psiquico: 'psíquico',
  psiquicos: 'psíquicos',
  publica: 'pública',
  publico: 'público',
  ramon: 'ramón',
  recuperacion: 'recuperación',
  reeducacion: 'reeducación',
  rehabilitacion: 'rehabilitación',
  riñon: 'riñón',
  rodriguez: 'rodríguez',
  roldan: 'roldán',
  sanchez: 'sánchez',
  sebastian: 'sebastián',
  simon: 'simón',
  sindrome: 'síndrome',
  sofia: 'sofía',
  tecnica: 'técnica',
  tecnicas: 'técnicas',
  tecnico: 'técnico',
  tellez: 'téllez',
  terapeutica: 'terapéutica',
  terapeutico: 'terapéutico',
  terapeuticos: 'terapéuticos',
  tetuan: 'tetuán',
  torrejon: 'torrejón',
  trebol: 'trébol',
  unica: 'única',
  unicas: 'únicas',
  unico: 'único',
  union: 'unión',
  valoracion: 'valoración',
  via: 'vía',
  vicalvaro: 'vicálvaro',
  vision: 'visión',
  yebenes: 'yébenes',
  zurbaran: 'zurbarán'
};

function restoreSpanishDiacriticsWord(lowerWord: string): string {
  if (RESTORED_SPANISH_DIACRITICS[lowerWord]) {
    return RESTORED_SPANISH_DIACRITICS[lowerWord];
  }
  if (/^[a-zñü]{4,}(cion|sion)$/.test(lowerWord)) {
    return `${lowerWord.slice(0, -3)}ión`;
  }
  return lowerWord;
}

/**
 * Convierte denominaciones registrales escritas íntegramente en MAYÚSCULAS a formato legible
 * con mayúscula inicial en español y tildes ortográficas restituidas, respetando siglas oficiales (#13).
 */
export function formatOfficialSpanishName(raw: string): string {
  const s = (raw || '')
    .trim()
    .replace(/(\p{L}{2,})\.(\p{L}{2,})/gu, '$1. $2')
    .replace(/,(?=\p{L})/gu, ', ');
  if (!s || /^RESERVADO$/i.test(s)) return s;

  const letters = s.match(/\p{L}/gu) || [];
  if (letters.length === 0) return s;
  const upperCount = letters.filter(ch => ch === ch.toLocaleUpperCase('es-ES') && ch !== ch.toLocaleLowerCase('es-ES')).length;

  // Si ya viene en formato mixto, normalizamos siglas clave, conectores españoles y tildes ortográficas
  if (upperCount / letters.length <= 0.6) {
    const MIXED_CASE_ACRONYMS = new Set(['FMP', 'AFEAM', 'TEA', 'DCA', 'ELA', 'TDAH']);
    let seenWord = false;
    let prevSeparator = '';
    let prevLowerWord = '';
    return s
      .split(/(\s+|[-/,():"“”«»])/)
      .map((part) => {
        if (!part) return '';
        if (/^(\s+|[-/,():"“”«»])$/.test(part)) {
          if (!/^\s+$/.test(part)) prevSeparator = part;
          return part;
        }
        return part.replace(/\b(\p{L}+)\b/gu, (token) => {
          const upper = token.toLocaleUpperCase('es-ES');
          if (
            (PRESERVED_SPANISH_ACRONYMS.has(upper) && token === upper) ||
            MIXED_CASE_ACRONYMS.has(upper)
          ) {
            seenWord = true;
            prevSeparator = '';
            prevLowerWord = upper.toLocaleLowerCase('es-ES');
            return upper;
          }
          const lower = restoreSpanishDiacriticsWord(token.toLocaleLowerCase('es-ES'));
          const allowConnectorLowercase =
            seenWord &&
            prevSeparator !== ':' &&
            prevSeparator !== '(' &&
            prevSeparator !== '«' &&
            prevSeparator !== '"' &&
            (LOWERCASE_SPANISH_PREPOSITIONS.has(lower) ||
              (LOWERCASE_SPANISH_ARTICLES.has(lower) &&
                (LOWERCASE_SPANISH_PREPOSITIONS.has(prevLowerWord) || prevLowerWord === 'o')));
          if (allowConnectorLowercase) {
            prevSeparator = '';
            prevLowerWord = lower;
            return lower;
          }
          seenWord = true;
          prevSeparator = '';
          prevLowerWord = lower;
          const startsUpper = token.charAt(0) === token.charAt(0).toLocaleUpperCase('es-ES');
          return startsUpper ? lower.charAt(0).toLocaleUpperCase('es-ES') + lower.slice(1) : lower;
        });
      })
      .join('');
  }

  const parts = s.split(/(\s+|[-/,()"“”«»])/);
  let seenWord = false;
  let prevSeparator = '';
  let prevLowerWord = '';

  const formatSingleWord = (word: string): string => {
    if (!word) return '';
    const cleanUpper = word.toLocaleUpperCase('es-ES');
    if (PRESERVED_SPANISH_ACRONYMS.has(cleanUpper)) {
      seenWord = true;
      prevSeparator = '';
      prevLowerWord = cleanUpper.toLocaleLowerCase('es-ES');
      return cleanUpper;
    }

    const lower = restoreSpanishDiacriticsWord(word.toLocaleLowerCase('es-ES'));
    const allowConnectorLowercase =
      seenWord &&
      prevSeparator !== '(' &&
      prevSeparator !== '«' &&
      prevSeparator !== '"' &&
      (LOWERCASE_SPANISH_PREPOSITIONS.has(lower) ||
        (LOWERCASE_SPANISH_ARTICLES.has(lower) &&
          (LOWERCASE_SPANISH_PREPOSITIONS.has(prevLowerWord) || prevLowerWord === 'o')));

    if (allowConnectorLowercase) {
      prevSeparator = '';
      prevLowerWord = lower;
      return lower;
    }

    seenWord = true;
    prevSeparator = '';
    prevLowerWord = lower;
    return lower.charAt(0).toLocaleUpperCase('es-ES') + lower.slice(1);
  };

  return parts
    .map((part) => {
      if (!part) return '';
      if (/^(\s+|[-/,()"“”«»])$/.test(part)) {
        if (!/^\s+$/.test(part)) {
          prevSeparator = part;
        }
        return part;
      }

      const cleanUpper = part.toLocaleUpperCase('es-ES');
      const dottedPrefixMatch = cleanUpper.match(
        /^((?:[A-ZÁÉÍÓÚÜÑ]\.){2,}(?:[A-ZÁÉÍÓÚÜÑ](?=$))?|(?:[A-ZÁÉÍÓÚÜÑ]\.)+[A-ZÁÉÍÓÚÜÑ](?=$))(.*)$/
      );
      if (dottedPrefixMatch) {
        const [, dottedAcronym, restUpper] = dottedPrefixMatch;
        seenWord = true;
        prevSeparator = '';
        prevLowerWord = dottedAcronym.toLocaleLowerCase('es-ES');
        if (!restUpper) {
          return dottedAcronym;
        }
        const restOffset = dottedAcronym.length;
        const formattedRest = part
          .slice(restOffset)
          .split(/(\.)/)
          .map((sub) => (sub === '.' ? '.' : formatSingleWord(sub)))
          .join('');
        return dottedAcronym + formattedRest;
      }

      if (part.includes('.')) {
        return part
          .split(/(\.)/)
          .map((sub) => {
            if (!sub) return '';
            if (sub === '.') {
              prevSeparator = '.';
              return '.';
            }
            return formatSingleWord(sub);
          })
          .join('');
      }

      return formatSingleWord(part);
    })
    .join('');
}

/**
 * Clasifica ÚNICAMENTE si los campos oficiales del registro declaran literalmente la condición.
 * Cero inferencias por discapacidad intelectual -> TEA, discapacidad física -> DCA/LM,
 * atención temprana -> parálisis cerebral / psicomotricidad, ni enfermedad mental -> neurodegenerativas.
 */
export function classifyExplicitSpecialisations(parts: {
  name: string;
  subtype: string;
  sector: string;
  entity?: string;
}): ProfileId[] {
  const combinedRaw = [parts.name, parts.subtype, parts.sector, parts.entity || ''].join(' ');
  const norm = normalizeStrict(combinedRaw)
    // Evitar falso positivo por "San Juan Bautista"
    .replace(/\bbautista\b/g, ' ');

  const matched: ProfileId[] = [];

  if (/\b(autism[oa]s?|autist[ae]s?|tea|trastornos? del espectro (?:del )?autism[oa]|asperger)\b/.test(norm)) {
    matched.push('autism');
  }

  if (/\b(dano cerebral adquirido|dano cerebral sobrevenido|dano cerebral|dca|ictus|traumatismo craneoencefalico|rehabictus|paralisis\s+[yo]\s+(?:el\s+)?dano\s+cerebral(?:es)?)\b/.test(norm)) {
    matched.push('acquired_brain_injury');
  }

  if (/\b(paralisis cerebral|paraliticos? cerebrales?|paralisis\s+[yo]\s+(?:el\s+)?dano\s+cerebral(?:es)?)\b/.test(norm)) {
    matched.push('cerebral_palsy');
  }

  if (/\b(esclerosis multiple|enfermedades? neurodegenerativas?|patologias? neurodegenerativas?)\b/.test(norm)) {
    matched.push('neurodegenerative_diseases');
  }

  if (/\b(lesion medular|lesionado medular|lesionados medulares|paraplejic[oa]s?|paraplejia|tetraplejia)\b/.test(norm)) {
    matched.push('spinal_cord_injury');
  }

  if (/\b(psicomotricidad|psicomotricistas?|psicomotri[cz][a-z]*)\b/.test(norm)) {
    matched.push('psychomotor_early_support');
  }

  if (/\b(tdah|deficit de atencion(?: e hiperactividad)?)\b/.test(norm)) {
    matched.push('adhd');
  }

  if (/\b(esclerosis lateral amiotrofica|adela|asistencia personal ela)\b/.test(norm)) {
    matched.push('als');
  }

  if (/\b(parkinson|parkinsonismo)\b/.test(norm)) {
    matched.push('parkinson');
  }

  if (/\b(alzheimer|demencias?)\b/.test(norm)) {
    matched.push('alzheimer');
  }

  if (/\b(enfermedades? raras|enfermedades? poco frecuentes)\b/.test(norm)) {
    matched.push('rare_diseases');
  }

  if (/\b(discapacidad auditiva|sordera|sordoceguera|personas sordas|personas sordociegas|hipoacusia|implante coclear)\b/.test(norm)) {
    matched.push('hearing_disability');
  }

  if (/\b(discapacidad visual|ceguera|baja vision|personas ciegas|sordoceguera|personas sordociegas|deficiencia visual)\b/.test(norm)) {
    matched.push('visual_disability');
  }

  return matched;
}

export function mapCamMunicipalityName(raw: string): string {
  const s = (raw || '').trim();
  if (!s || s.toUpperCase() === 'RESERVADO') return 'Madrid (ubicación reservada)';
  const articleMatch = s.match(/^(.+?),\s*(El|La|Los|Las)$/i);
  if (articleMatch) {
    const base = articleMatch[1].trim();
    const rawArticle = articleMatch[2].toLowerCase();
    const article = rawArticle.charAt(0).toUpperCase() + rawArticle.slice(1);
    const normalizedBase =
      base === 'Vellon' ? 'Vellón' : base === 'Alamo' ? 'Álamo' : base;
    return `${article} ${normalizedBase}`;
  }
  return s;
}

const MUNICIPAL_SUBTYPE_LABELS: Record<string, string> = {
  CentrosAtencionSocialPersonasDiscapacidad: 'Centros de Atención Social · Personas con Discapacidad',
  CentrosOrientacionValoracion: 'Centros de Orientación y Valoración',
  CentrosAtencionTemprana: 'Centros de Atención Temprana',
  CentrosServiciosSociales: 'Centros de Servicios Sociales'
};

export function formatMunicipalSubtypeLabel(tipoPath: string): string {
  const raw = (tipoPath || '').split('/').pop()?.trim() || '';
  if (!raw) return 'Centro registrado';
  if (MUNICIPAL_SUBTYPE_LABELS[raw]) return MUNICIPAL_SUBTYPE_LABELS[raw];
  if (!/[a-z][A-Z]/.test(raw)) return formatOfficialSpanishName(raw);
  const spaced = raw.replace(/([a-zñáéíóú])([A-ZÁÉÍÓÚÑ])/g, '$1 $2');
  return formatOfficialSpanishName(spaced);
}

export function formatMunicipalDistrict(raw: string): string | undefined {
  const clean = decodeHtmlEntities(raw || '').trim();
  if (!clean || /^(DISTRITO|RESERVADO|N\/D)$/i.test(clean)) return undefined;
  const formatted = formatOfficialSpanishName(clean);
  if (formatted.toLocaleLowerCase('es-ES') === 'san blas') {
    return 'San Blas-Canillejas';
  }
  return formatted;
}

function inferSupportsFromOfficialFields(
  tipo: string,
  subtipo: string,
  denom: string
): { supports: SupportTypeId[]; extraRelated: string[] } {
  const norm = normalizeStrict(`${tipo} ${subtipo} ${denom}`);
  const supports = new Set<SupportTypeId>();
  const extraRelated = new Set<string>();

  if (/\b(centro de dia|centros de dia|atencion diurna)\b/.test(norm)) {
    supports.add('day_care');
  }
  if (/\b(ocupacional|centro ocupacional|centros ocupacionales)\b/.test(norm)) {
    supports.add('day_care');
    extraRelated.add('centro ocupacional');
  }
  if (/\bterapia ocupacional\b/.test(norm) && !/\b(centro ocupacional|centros ocupacionales)\b/.test(norm)) {
    supports.add('occupational_therapy');
  }
  if (/\b(residencia|residencias|residencial|piso tutelado|pisos tutelados|vivienda comunitaria|viviendas comunitarias|hogar)\b/.test(norm)) {
    supports.add('residential_care');
  }
  if (
    /\b(rehabilitacion|fisioterapia)\b/.test(norm) ||
    (/\brecuperacion\b/.test(norm) && !/\brecuperacion profesional\b/.test(norm))
  ) {
    supports.add('rehabilitation');
  }
  if (/\b(atencion temprana)\b/.test(norm)) {
    extraRelated.add('atención temprana');
  }
  if (
    /\b(insercion laboral|insercion socio laboral|insercion sociolaboral|empleo|rehabilitacion laboral|recuperacion profesional|preparacion laboral|laboral)\b/.test(
      norm
    )
  ) {
    supports.add('employment_support');
  }
  if (/\b(psicosocial|psico social|apoyo psicologico|psicologia|grupos de ayuda mutua)\b/.test(norm)) {
    supports.add('psychological_support');
  }
  if (/\b(logopedia|comunicacion)\b/.test(norm)) {
    supports.add('speech_therapy');
  }
  return { supports: Array.from(supports), extraRelated: Array.from(extraRelated) };
}

function inferLifeStagesFromOfficialFields(sector: string, denom: string, tipo: string): LifeStage[] {
  const norm = normalizeStrict(`${sector} ${denom} ${tipo}`);
  const stages = new Set<LifeStage>();

  if (/\b(atencion temprana)\b/.test(norm)) {
    stages.add('early_childhood');
    return ['early_childhood'];
  }
  if (/\b(infancia)\b/.test(norm)) stages.add('early_childhood');
  if (/\b(infancia|adolescencia|menores?|ninos|infantil|jovenes)\b/.test(norm)) stages.add('minor');
  if (/\b(adult[oa]s?|ocupacional|laboral|insercion)\b/.test(norm)) stages.add('adult');
  if (/\b(mayores?|alzheimer|parkinson|demencia)\b/.test(norm)) stages.add('older_adult');

  // Si no hay indicación explícita de edad, devolver [] (no consta; no excluir búsquedas por edad)
  return Array.from(stages);
}

function mapPublicPrivateStatus(
  gest: string,
  isDirectPublic: boolean,
  isUnstatedMunicipal = false
): {
  status: 'red_publica' | 'concertado' | 'privado_autorizado' | 'no_especificado';
  accessType: AccessRouteType;
  nextStep: string;
} {
  if (isDirectPublic) {
    return {
      status: 'red_publica',
      accessType: 'unknown',
      nextStep: 'Centro de titularidad pública directa; pregunte en su Centro de Servicios Sociales o Centro Base cómo solicitar acceso.'
    };
  }
  if (isUnstatedMunicipal) {
    return {
      status: 'no_especificado',
      accessType: 'unknown',
      nextStep: 'El catálogo municipal datos.madrid.es no detalla si este recurso es público, concertado o privado; confirme condiciones de acceso directamente con la entidad o en Servicios Sociales.'
    };
  }
  const g = normalizeStrict(gest);
  if (g.includes('propia') || g.includes('publica directa')) {
    return {
      status: 'red_publica',
      accessType: 'unknown',
      nextStep: 'Puede tener plazas públicas; pregunte en sus servicios sociales cómo solicitar acceso.'
    };
  }
  if (g.includes('concertada')) {
    return {
      status: 'concertado',
      accessType: 'unknown',
      nextStep: 'Puede tener plazas públicas o concertadas; pregunte en sus servicios sociales.'
    };
  }
  return {
    status: 'privado_autorizado',
    accessType: 'unknown',
    nextStep: 'Entidad privada autorizada; consulte condiciones directamente con el centro o en sus servicios sociales.'
  };
}

/**
 * Traducción literal según ficha de estructura oficial de datos.madrid.es (Catálogo 212774-0):
 * 0 = No accesible | 1 = Accesible | 2 = Parcialmente accesible | 3 = Sin información
 * 4 = Lengua de signos | 5 = Señalización podotáctil | 6 = Bucle magnético
 */
function mapAccessibilityFromCode(rawCode: string): string[] {
  const code = (rawCode || '').trim();
  if (!code) return [];
  const tokens = code.split(',').map(t => t.trim());
  const features: string[] = [];
  if (tokens.includes('1')) {
    features.push('Accesible (Código 1 · datos.madrid.es)');
  } else if (tokens.includes('2')) {
    features.push('Parcialmente accesible (Código 2 · datos.madrid.es)');
  } else if (tokens.includes('3')) {
    features.push('Sin información (Código 3 · datos.madrid.es)');
  } else if (tokens.includes('0')) {
    features.push('No accesible (Código 0 · datos.madrid.es)');
  }
  if (tokens.includes('4')) features.push('Lengua de signos (Código 4 · datos.madrid.es)');
  if (tokens.includes('5')) features.push('Señalización podotáctil (Código 5 · datos.madrid.es)');
  if (tokens.includes('6')) features.push('Bucle magnético (Código 6 · datos.madrid.es)');
  return features;
}

function isLegalOrganizationName(name: string): boolean {
  const n = normalizeStrict(name);
  return /\b(asociacion|fundacion|s l|sl|s a|sa|sociedad|cooperativa|federacion|confederacion|ayuntamiento|comunidad|centro|instituto|cruz roja|caritas|hermanas|congregacion|congregacion|orden|obra social|mutua|empresa|grupo|clinica|hospital|residencia|entidad)\b/.test(n);
}

function sanitizePersonalPractitionerRecord(params: {
  regId: string;
  nif: string;
  entity: string;
  denom: string;
  subtipo: string;
  tipo: string;
  explicitSpecs: ProfileId[];
  entitySpecs: ProfileId[];
}): {
  officialName: string;
  providerName: string;
  isIndividualPractitioner: boolean;
} {
  const { nif, entity, denom, subtipo, tipo, explicitSpecs, entitySpecs } = params;
  const cleanNif = nif.trim();
  const looksLikePersonEntity =
    !cleanNif && Boolean(entity.trim()) && !isLegalOrganizationName(entity) && entity.trim().split(/\s+/).length >= 2;

  if (!looksLikePersonEntity) {
    return {
      officialName: formatOfficialSpanishName(denom),
      providerName: formatOfficialSpanishName(entity || denom),
      isIndividualPractitioner: false
    };
  }

  const serviceLabel = subtipo || tipo || 'Servicio de Atención Social autorizado';
  const hasAls = explicitSpecs.includes('als') || entitySpecs.includes('als') || /\bela\b/.test(normalizeStrict(denom));
  const condTag = hasAls ? ' (ELA)' : '';
  const prettyType = formatOfficialSpanishName(serviceLabel);

  return {
    officialName: `${prettyType}${condTag} · Profesional individual autorizado`,
    providerName: 'Profesional autónomo acreditado en Registro CAM (nombre omitido por privacidad)',
    isIndividualPractitioner: true
  };
}

function isRelevantCamRow(
  sector: string,
  tipo: string,
  subtipo: string,
  denom: string,
  entity: string,
  allSpecs: ProfileId[]
): boolean {
  if (allSpecs.length > 0) return true;
  const norm = normalizeStrict(`${sector} ${tipo} ${subtipo} ${denom} ${entity}`);
  return (
    norm.includes('discapacidad') ||
    norm.includes('atencion temprana') ||
    norm.includes('enfermedad mental')
  );
}

function isRelevantMadridRow(nombre: string, equipamiento: string, tipoUrl: string, explicitSpecs: ProfileId[]): boolean {
  if (explicitSpecs.length > 0) return true;
  const norm = normalizeStrict(`${nombre} ${equipamiento} ${tipoUrl}`);
  return (
    norm.includes('discapacidad') ||
    norm.includes('atencion temprana') ||
    norm.includes('enfermedad mental') ||
    norm.includes('centrosatencionsocialpersonasdiscapacidad') ||
    norm.includes('centrosatenciontemprana')
  );
}

export interface OfficialCatalogBuildResult {
  centres: SpecializedCentre[];
  lookupIndex: Map<string, SnapshotCentreRecord>;
}

function formatSupportRelatedNames(supports: SupportTypeId[]): string[] {
  return supports.map(s =>
    s === 'day_care'
      ? 'atención diurna'
      : s === 'residential_care'
      ? 'residencia'
      : s === 'rehabilitation'
      ? 'rehabilitación'
      : s === 'occupational_therapy'
      ? 'terapia ocupacional'
      : s === 'employment_support'
      ? 'apoyo laboral'
      : s === 'psychological_support'
      ? 'apoyo psicosocial'
      : s === 'respiratory_physiotherapy'
      ? 'fisioterapia respiratoria'
      : 'logopedia'
  );
}

export function buildCentresFromOfficialCSVs(params: {
  madridCsvText?: string | null;
  camCentrosCsvText?: string | null;
  camServiciosCsvText?: string | null;
  snapshotDate?: string;
}): OfficialCatalogBuildResult {
  const checkDate = params.snapshotDate || new Date().toISOString().slice(0, 10);
  const lookupIndex = new Map<string, SnapshotCentreRecord>();
  const centres: SpecializedCentre[] = [];

  interface MadridParsedRow {
    pk: string;
    name: string;
    equipamiento: string;
    transporte: string;
    accCode: string;
    contentUrl: string;
    address: string;
    postalCode: string;
    district: string;
    coords: [number, number] | null;
    phone: string;
    email: string;
    tipoPath: string;
    usedByCam: boolean;
  }

  const madridRows: MadridParsedRow[] = [];
  const madridByPhone = new Map<string, MadridParsedRow[]>();
  const madridByNormAddr = new Map<string, MadridParsedRow[]>();

  if (params.madridCsvText) {
    const rows = parseSemicolonCSV(params.madridCsvText);
    if (rows.length > 1) {
      const h = rows[0].map(c => c.trim().toUpperCase());
      const col = (name: string) => h.indexOf(name);

      for (let i = 1; i < rows.length; i++) {
        const r = rows[i];
        const pk = r[col('PK')]?.trim();
        if (!pk) continue;
        const rawName = decodeHtmlEntities(r[col('NOMBRE')] || `Centro Municipal PK ${pk}`);
        const name = formatOfficialSpanishName(rawName);
        const clase = decodeHtmlEntities(r[col('CLASE-VIAL')] || '');
        const via = decodeHtmlEntities(r[col('NOMBRE-VIA')] || '');
        const num = decodeHtmlEntities(r[col('NUM')] || '');
        const address = [clase, via, num].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
        const postalCode = (r[col('CODIGO-POSTAL')] || '').trim();
        const district = formatMunicipalDistrict(r[col('DISTRITO')] || '') || '';
        const lat = parseFloat(r[col('LATITUD')] || '');
        const lon = parseFloat(r[col('LONGITUD')] || '');
        const coords: [number, number] | null =
          Number.isFinite(lat) && Number.isFinite(lon) && lat !== 0 && lon !== 0
            ? [Number(lat.toFixed(6)), Number(lon.toFixed(6))]
            : null;
        const phone = normalizePhoneFieldForCatalog(r[col('TELEFONO')] || '');
        const email = (r[col('EMAIL')] || '').trim();
        const accCode = (r[col('ACCESIBILIDAD')] || '').trim();
        const contentUrl = (r[col('CONTENT-URL')] || '').trim();
        const equipamiento = decodeHtmlEntities((r[col('EQUIPAMIENTO')] || '').trim());
        const transporte = decodeHtmlEntities((r[col('TRANSPORTE')] || '').trim());
        const tipoPath = (r[col('TIPO')] || '').trim();

        const key = `MAD-PK${pk}`;
        lookupIndex.set(key, {
          registry_key: key,
          source_id: 'madrid_municipal',
          official_name: name,
          phone,
          address,
          municipality: 'Madrid',
          postal_code: postalCode,
          authorised_places: null,
          accessibility_code: accCode
        });

        const parsed: MadridParsedRow = {
          pk,
          name,
          equipamiento,
          transporte,
          accCode,
          contentUrl,
          address,
          postalCode,
          district,
          coords,
          phone,
          email,
          tipoPath,
          usedByCam: false
        };
        madridRows.push(parsed);

        const normPhone = normalizePhoneComparable(phone);
        if (normPhone) {
          const list = madridByPhone.get(normPhone) || [];
          list.push(parsed);
          madridByPhone.set(normPhone, list);
        }
        const normAddrOnly = normalizeAddressComparable(address);
        if (normAddrOnly) {
          const list = madridByNormAddr.get(normAddrOnly) || [];
          list.push(parsed);
          madridByNormAddr.set(normAddrOnly, list);
        }
      }
    }
  }

  // 2. Parsear Comunidad de Madrid - Registro de Centros
  const trackedEntities = new Set<string>([
    'lescer', 'polibea', 'cepri', 'bobath', 'amafe', 'apadis', 'aspaym',
    'alicia koplowitz', 'atenpace', 'aleph', 'nuevo horizonte', 'apanefa',
    'atipadace', 'adela', 'feder', 'pita lopez', 'parkinson', 'esclerosis', 'alzheimer'
  ]);

  if (params.camCentrosCsvText) {
    const rows = parseSemicolonCSV(params.camCentrosCsvText);
    if (rows.length > 1) {
      const h = rows[0].map(c => c.trim().toLowerCase());
      const col = (name: string) => h.indexOf(name);

      for (let i = 1; i < rows.length; i++) {
        const r = rows[i];
        const regId = r[col('numero_registro')]?.trim();
        if (!regId) continue;

        const sector = (r[col('sector')] || '').trim();
        const tipo = (r[col('tipo')] || '').trim();
        const subtipo = (r[col('subtipo')] || '').trim();
        const rawDenom = (r[col('denominacion')] || '').trim();
        const denom = formatOfficialSpanishName(rawDenom);
        const plazasRaw = (r[col('plazas_autorizadas_numero')] || '').trim();
        const placesNum = /^\d+$/.test(plazasRaw) && parseInt(plazasRaw, 10) > 0 ? parseInt(plazasRaw, 10) : null;
        const muniRaw = (r[col('municipio_nombre')] || '').trim();
        const municipality = mapCamMunicipalityName(muniRaw);
        const viaTipo = (r[col('direccion_via_tipo')] || '').trim();
        const viaName = (r[col('direccion_via_nombre')] || '').trim();
        const portal = (r[col('direccion_portal')] || '').trim();
        const addressRaw = [viaTipo, viaName, portal].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
        const address = addressRaw.toUpperCase().includes('RESERVADO')
          ? 'Dirección reservada en el registro público oficial'
          : addressRaw;
        const postalCode = (r[col('direccion_codigo_postal')] || '').trim();
        const district = formatMunicipalDistrict(r[col('direccion_distrito')] || '') || '';
        const utmX = parseFloat(r[col('direccion_coor_x')] || '');
        const utmY = parseFloat(r[col('direccion_coor_y')] || '');
        const coords = utm30NToWgs84(utmX, utmY);
        const rawPhone = (r[col('contacto_telefono')] || '').trim();
        const phone = normalizePhoneFieldForCatalog(rawPhone);
        const email = (r[col('contacto_correo')] || '').trim().split(';')[0]?.trim() || '';
        const entityRaw = (r[col('entidad_denominacion')] || '').trim();
        const entityNif = (r[col('entidad_nif')] || '').trim();
        const isSoleProprietorPerson =
          !entityNif &&
          Boolean(entityRaw) &&
          !isLegalOrganizationName(entityRaw) &&
          entityRaw.split(/\s+/).length >= 2;
        const safeProviderName = isSoleProprietorPerson
          ? 'Persona física titular acreditada en Registro CAM (nombre omitido por privacidad)'
          : formatOfficialSpanishName(entityRaw || rawDenom);
        const entity = isSoleProprietorPerson ? '' : entityRaw;
        const gest = (r[col('tipo_gestion')] || '').trim();

        const key = `CAM-${regId}`;
        lookupIndex.set(key, {
          registry_key: key,
          source_id: 'cam_centros',
          official_name: denom,
          phone,
          address,
          municipality,
          postal_code: postalCode,
          authorised_places: placesNum
        });

        // Evidencia separada: centro (denominacion/subtipo/sector) vs entidad titular (#8)
        const centreExplicitSpecs = classifyExplicitSpecialisations({
          name: denom,
          subtype: subtipo || tipo,
          sector
        });
        const entityOnlyAllSpecs = entity
          ? classifyExplicitSpecialisations({ name: '', subtype: '', sector: '', entity })
          : [];
        const entityDeclaredSpecs = entityOnlyAllSpecs.filter(s => !centreExplicitSpecs.includes(s));
        const allMatchedSpecs = Array.from(new Set([...centreExplicitSpecs, ...entityDeclaredSpecs]));

        if (!isRelevantCamRow(sector, tipo, subtipo, denom, entityRaw, allMatchedSpecs)) {
          continue;
        }

        // Enlace robusto multi-catálogo CAM <-> datos.madrid.es (#10)
        // Prefiere candidatos aún no enlazados (usedByCam === false) con mayor coincidencia de tipo/nombre y dirección/teléfono
        let linkedMadrid: MadridParsedRow | null = null;
        const normCamAddr = normalizeAddressComparable(address);
        const normCamName = normalizeStrict(denom);
        const normCamAll = normalizeStrict(`${denom} ${subtipo} ${tipo} ${entity}`);
        const camPhone = normalizePhoneComparable(phone);

        const stripStreetNum = (normAddr: string) => normAddr.replace(/\s+\d+[a-z]*$/i, '').trim();
        const camStreetStem = stripStreetNum(normCamAddr);

        const scoreMadridCandidate = (m: MadridParsedRow, requireStreetMatch: boolean): number => {
          const mAddr = normalizeAddressComparable(m.address);
          const mStreetStem = stripStreetNum(mAddr);
          const exactAddr = Boolean(normCamAddr && mAddr && normCamAddr === mAddr);
          const partialAddr = Boolean(normCamAddr && mAddr && (normCamAddr.includes(mAddr) || mAddr.includes(normCamAddr)));
          const sameStem = Boolean(camStreetStem && mStreetStem && camStreetStem === mStreetStem);
          if (requireStreetMatch && !exactAddr && !partialAddr && !sameStem) return -1;

          let score = 0;
          if (!m.usedByCam) score += 20;
          if (exactAddr) score += 12;
          else if (partialAddr) score += 6;
          else if (sameStem) score += 4;
          if (camPhone && normalizePhoneComparable(m.phone) === camPhone) score += 10;
          if (postalCode && m.postalCode === postalCode) score += 3;

          const mNormName = normalizeStrict(m.name);
          if (mNormName === normCamName) score += 15;
          const stopWords = new Set(['centro', 'centros', 'personas', 'discapacidad', 'madrid', 'fundacion', 'asociacion', 'para', 'social', 'atencion']);
          const mTokens = mNormName.split(' ').filter(w => w.length > 3 && !stopWords.has(w));
          for (const tok of mTokens) {
            if (normCamName.includes(tok)) score += 6;
            else if (normCamAll.includes(tok)) score += 3;
          }
          // Preferir coincidencia de tipología exacta (Residencia <-> Residencia, Día <-> Día, Ocupacional <-> Ocupacional)
          if (normCamName.includes('residencia') && mNormName.includes('residencia')) score += 8;
          if (normCamName.includes('ocupacional') && mNormName.includes('ocupacional')) score += 8;
          if ((normCamName.includes('dia') || normCamName.includes('diurna')) && mNormName.includes('dia')) score += 8;
          if (normCamName.includes('temprana') && mNormName.includes('temprana')) score += 8;
          return score;
        };

        const addrCandidates = normCamAddr ? madridByNormAddr.get(normCamAddr) || [] : [];
        if (addrCandidates.length > 0) {
          const ranked = addrCandidates
            .map(m => ({ m, score: scoreMadridCandidate(m, false) }))
            .filter(x => x.score >= 12)
            .sort((a, b) => b.score - a.score);
          linkedMadrid = ranked[0]?.m || null;
        }

        if (!linkedMadrid && camPhone) {
          const phoneCandidates = madridByPhone.get(camPhone) || [];
          const ranked = phoneCandidates
            .map(m => ({ m, score: scoreMadridCandidate(m, true) }))
            .filter(x => x.score >= 16)
            .sort((a, b) => b.score - a.score);
          linkedMadrid = ranked[0]?.m || null;
        }

        if (linkedMadrid) {
          linkedMadrid.usedByCam = true;
          // Absorber posibles duplicados internos en datos.madrid.es que comparten exactamente misma dirección y teléfono
          if (camPhone) {
            const samePhonePeers = madridByPhone.get(camPhone) || [];
            for (const peer of samePhonePeers) {
              if (peer === linkedMadrid || peer.usedByCam) continue;
              const pAddr = normalizeAddressComparable(peer.address);
              const pStem = stripStreetNum(pAddr);
              if (
                (normCamAddr && pAddr === normCamAddr) ||
                (camStreetStem && pStem === camStreetStem && scoreMadridCandidate(peer, true) >= 16)
              ) {
                // Solo fusionar si no hay otra ficha CAM distinta en la misma dirección que lo represente mejor
                const peerTokens = normalizeStrict(peer.name).split(' ').filter(w => w.length > 3);
                const matchesThisCam = peerTokens.some(t => normCamAll.includes(t));
                if (matchesThisCam) {
                  peer.usedByCam = true;
                }
              }
            }
          }
        }

        const finalCoords = coords || linkedMadrid?.coords || null;
        const supportResult = inferSupportsFromOfficialFields(tipo, subtipo, denom);
        const supports = supportResult.supports;
        const lifeStages = inferLifeStagesFromOfficialFields(sector, denom, tipo);
        const isMunicipalPublic = Boolean(
          linkedMadrid &&
            (normalizeStrict(linkedMadrid.name).includes('municipal') ||
              normalizeStrict(entity).includes('ayuntamiento'))
        );
        const netInfo = mapPublicPrivateStatus(gest, isMunicipalPublic);
        const provenance: AttributeProvenance[] = [
          {
            attribute_name: centreExplicitSpecs.length > 0 ? 'specialisation' : entityDeclaredSpecs.length > 0 ? 'entity_specialisation' : 'sector',
            value: centreExplicitSpecs.length > 0
              ? `${denom} · ${subtipo || tipo} (${sector})`
              : entityDeclaredSpecs.length > 0
              ? `Entidad titular: ${safeProviderName} (Denominación centro: ${denom})`
              : `${sector} · ${subtipo || tipo}`,
            source_dataset: `Registro de Centros de Atención Social CAM (${regId})`,
            source_url: OFFICIAL_DATASET_URLS.cam_centros,
            source_type: 'official_registry',
            retrieved_at: checkDate,
            extraction_method: 'structured',
            reviewer: 'Portal de Datos Abiertos Comunidad de Madrid (CSV oficial)',
            reviewer_role: 'data_steward',
            confidence: centreExplicitSpecs.length > 0 ? 'explicit' : 'potential',
            quality: 'A'
          }
        ];

        if (linkedMadrid) {
          provenance.push({
            attribute_name: 'municipal_registry_link',
            value: `${linkedMadrid.name} (Accesibilidad código ${linkedMadrid.accCode || 'N/D'})`,
            source_dataset: `Catálogo de Centros de Atención Social (datos.madrid.es PK ${linkedMadrid.pk})`,
            source_url: linkedMadrid.contentUrl || OFFICIAL_DATASET_URLS.madrid_municipal,
            source_type: 'official_registry',
            retrieved_at: checkDate,
            extraction_method: 'structured',
            reviewer: 'Portal de Datos Abiertos Ayuntamiento de Madrid (CSV oficial)',
            reviewer_role: 'data_steward',
            confidence: 'potential',
            quality: 'A'
          });
        }

        const accFeatures = linkedMadrid ? mapAccessibilityFromCode(linkedMadrid.accCode) : [];
        const limitations: string[] = [];
        if (centreExplicitSpecs.length === 0 && entityDeclaredSpecs.length > 0) {
          limitations.push(
            `La especialización proviene de la entidad titular (${safeProviderName}), no de la denominación individual del centro (${denom}).`
          );
        } else if (centreExplicitSpecs.length === 0) {
          limitations.push(
            `El registro oficial declara sector "${sector}" y denominación "${denom}", sin mencionar literalmente una patología específica.`
          );
        }
        if (supportResult.extraRelated.includes('centro ocupacional')) {
          limitations.push('Centro ocupacional: confirmar con la entidad si dispone de terapia ocupacional clínica diferenciada.');
        }
        if (supportResult.extraRelated.includes('atención temprana')) {
          limitations.push('Centro de atención temprana: confirmar con el equipo qué especialidades terapéuticas concretas presta.');
        }
        if (lifeStages.length === 0) {
          limitations.push('Etapa vital o edad admitida no consta en el registro oficial (confirmar con el centro).');
        }
        if (!finalCoords) {
          limitations.push('Centro sin coordenadas válidas en el registro oficial (GEO-001/002).');
        }
        if (accFeatures.length === 0) {
          limitations.push('El registro regional de centros no publica detalle de accesibilidad física.');
        }

        const relatedServices = [
          subtipo || tipo,
          ...formatSupportRelatedNames(supports),
          ...supportResult.extraRelated
        ].filter(Boolean);

        centres.push({
          centre_id: key,
          provider_id: `PROV-${normalizeStrict(entityNif || (isSoleProprietorPerson ? regId : entityRaw) || regId).replace(/\s+/g, '-').slice(0, 28)}`,
          provider_name: safeProviderName,
          official_name: denom,
          resource_domain: 'social',
          sector: sector || 'Atención Social',
          centre_type: tipo || 'Centro de Atención Social',
          subtype: subtipo || tipo || 'Centro autorizado',
          public_private_status: netInfo.status,
          management_type: gest || 'Autorizado en Registro CAM',
          address,
          postal_code: postalCode,
          municipality,
          district: district || linkedMadrid?.district || undefined,
          coordinates: finalCoords,
          has_valid_coordinates: Boolean(finalCoords),
          phone: phone || linkedMadrid?.phone || '',
          email: email || linkedMadrid?.email || '',
          website: linkedMadrid?.contentUrl || OFFICIAL_DATASET_URLS.cam_centros,
          explicit_specialisations: centreExplicitSpecs,
          entity_declared_specialisations: entityDeclaredSpecs,
          related_services: Array.from(new Set(relatedServices)),
          supports,
          services_offered: supports.map((sup, idx) => ({
            service_id: `SRV-${key}-${idx}`,
            centre_id: key,
            service_name: `${tipo || 'Servicio'} (${subtipo || sector})`,
            service_type: sup,
            target_populations: centreExplicitSpecs,
            allowed_life_stages: lifeStages,
            access_routes: [netInfo.accessType],
            source_dataset: `Registro de Centros de Atención Social CAM (${regId})`,
            source_url: OFFICIAL_DATASET_URLS.cam_centros,
            checked_at: checkDate
          })),
          allowed_life_stages: lifeStages,
          access_route: {
            access_type: netInfo.accessType,
            competent_body:
              netInfo.status === 'privado_autorizado'
                ? 'Entidad titular autorizada / Servicios Sociales'
                : 'Servicios Sociales municipales / Consejería de Familia (CAM)',
            official_description: `Régimen registral oficial: ${gest || 'no especificado'} (la gestión pública/concertada no especifica por sí sola el procedimiento individual de acceso).`,
            source_url: OFFICIAL_DATASET_URLS.cam_centros,
            checked_at: checkDate,
            next_step_action: netInfo.nextStep,
            availability_known: false,
            waiting_list_known: false
          },
          availability: {
            status: 'contact_required',
            authorised_places: placesNum,
            vacancies_known: false,
            source_url: OFFICIAL_DATASET_URLS.cam_centros,
            checked_at: checkDate,
            stale: false
          },
          geographic_coverage: {
            type: 'community_wide',
            requires_residence: netInfo.status === 'red_publica' ? 'yes' : 'unknown',
            checked_at: checkDate
          },
          accessibility_features: accFeatures,
          provenance_records: provenance,
          last_checked: checkDate,
          limitations
        });
      }
    }
  }

  // 3. Incorporar centros de datos.madrid.es no vinculados a ningún registro CAM físico
  for (const m of madridRows) {
    if (m.usedByCam) continue;
    const explicitSpecs = classifyExplicitSpecialisations({
      name: m.name,
      subtype: m.tipoPath,
      sector: m.equipamiento
    });
    if (!isRelevantMadridRow(m.name, m.equipamiento, m.tipoPath, explicitSpecs)) continue;

    const key = `MAD-PK${m.pk}`;
    const isSocialServicesOffice = normalizeStrict(m.tipoPath).includes('centrosserviciossociales');
    const supportResult = inferSupportsFromOfficialFields(
      m.tipoPath,
      isSocialServicesOffice ? '' : m.equipamiento,
      m.name
    );
    const supports = supportResult.supports;
    const lifeStages = inferLifeStagesFromOfficialFields(m.equipamiento, m.name, m.tipoPath);
    const normMadOnlyName = normalizeStrict(m.name);
    const isDirectPublic =
      /\bmunicipal\b/.test(normMadOnlyName) ||
      normMadOnlyName.startsWith('centro base') ||
      normMadOnlyName.startsWith('centro de servicios sociales') ||
      normMadOnlyName.startsWith('ayuntamiento de madrid');
    const netInfo = mapPublicPrivateStatus(
      isDirectPublic ? 'PUBLICA DIRECTA' : '',
      isDirectPublic,
      !isDirectPublic
    );

    const limitations: string[] = [
      'El catálogo municipal datos.madrid.es no publica número de plazas autorizadas.'
    ];
    if (!isDirectPublic) {
      limitations.push(
        'El catálogo municipal datos.madrid.es no especifica si la entidad titular tiene plazas públicas concertadas o privadas.'
      );
    }
    if (explicitSpecs.length === 0) {
      limitations.push(`La ficha municipal no menciona literalmente patología concreta (${m.equipamiento || m.name}).`);
    }
    if (lifeStages.length === 0) {
      limitations.push('Etapa vital o edad admitida no consta en el registro oficial (confirmar con el centro).');
    }

    centres.push({
      centre_id: key,
      provider_id: `PROV-MAD-${m.pk}`,
      provider_name: m.name,
      official_name: m.name,
      resource_domain: 'social',
      sector: m.equipamiento ? m.equipamiento.slice(0, 120) : 'Catálogo Atención Social Ayuntamiento de Madrid',
      centre_type: 'Centro de Atención Social (Madrid)',
      subtype: formatMunicipalSubtypeLabel(m.tipoPath),
      public_private_status: netInfo.status,
      management_type: isDirectPublic
        ? 'Público Directo (Ayuntamiento / Comunidad de Madrid)'
        : 'Titularidad no especificada en datos.madrid.es',
      address: m.address,
      postal_code: m.postalCode,
      municipality: 'Madrid',
      district: m.district || undefined,
      coordinates: m.coords,
      has_valid_coordinates: Boolean(m.coords),
      phone: m.phone,
      email: m.email,
      website: m.contentUrl || OFFICIAL_DATASET_URLS.madrid_municipal,
      explicit_specialisations: explicitSpecs,
      entity_declared_specialisations: [],
      related_services: Array.from(
        new Set([
          ...(m.equipamiento ? [m.equipamiento.slice(0, 140)] : ['atención social']),
          ...formatSupportRelatedNames(supports),
          ...supportResult.extraRelated
        ])
      ),
      supports,
      services_offered: supports.map((sup, idx) => ({
        service_id: `SRV-${key}-${idx}`,
        centre_id: key,
        service_name: m.name,
        service_type: sup,
        target_populations: explicitSpecs,
        allowed_life_stages: lifeStages,
        access_routes: [netInfo.accessType],
        source_dataset: `Catálogo de Centros de Atención Social (datos.madrid.es PK ${m.pk})`,
        source_url: OFFICIAL_DATASET_URLS.madrid_municipal,
        checked_at: checkDate
      })),
      allowed_life_stages: lifeStages,
      access_route: {
        access_type: netInfo.accessType,
        competent_body: isDirectPublic ? 'Ayuntamiento / Comunidad de Madrid · Servicios Sociales' : 'Entidad titular / Servicios Sociales',
        official_description: 'Registro municipal de centros de atención social.',
        source_url: OFFICIAL_DATASET_URLS.madrid_municipal,
        checked_at: checkDate,
        next_step_action: netInfo.nextStep,
        availability_known: false,
        waiting_list_known: false
      },
      availability: {
        status: 'contact_required',
        authorised_places: null,
        vacancies_known: false,
        source_url: OFFICIAL_DATASET_URLS.madrid_municipal,
        checked_at: checkDate,
        stale: false
      },
      geographic_coverage: {
        type: 'municipality',
        requires_residence: 'unknown',
        checked_at: checkDate
      },
      accessibility_features: mapAccessibilityFromCode(m.accCode),
      provenance_records: [
        {
          attribute_name: explicitSpecs.length > 0 ? 'specialisation' : 'sector',
          value: `${m.name} · ${m.equipamiento || 'Catálogo datos.madrid.es'}`,
          source_dataset: `Catálogo de Centros de Atención Social (datos.madrid.es PK ${m.pk})`,
          source_url: m.contentUrl || OFFICIAL_DATASET_URLS.madrid_municipal,
          source_type: 'official_registry',
          retrieved_at: checkDate,
          extraction_method: 'structured',
          reviewer: 'Portal de Datos Abiertos Ayuntamiento de Madrid (CSV oficial)',
          reviewer_role: 'data_steward',
          confidence: explicitSpecs.length > 0 ? 'explicit' : 'potential',
          quality: 'A'
        }
      ],
      last_checked: checkDate,
      limitations
    });
  }

  // 4. Parsear Comunidad de Madrid - Registro de Servicios (aporta recursos ambulatorios/especializados únicos Sxxxx)
  if (params.camServiciosCsvText) {
    const rows = parseSemicolonCSV(params.camServiciosCsvText);
    if (rows.length > 1) {
      const h = rows[0].map(c => c.trim().toLowerCase());
      const col = (name: string) => h.indexOf(name);

      for (let i = 1; i < rows.length; i++) {
        const r = rows[i];
        const regId = r[col('numero_registro')]?.trim();
        if (!regId) continue;

        const sector = (r[col('sector')] || '').trim();
        const tipo = (r[col('tipo')] || '').trim();
        const subtipo = (r[col('subtipo')] || '').trim();
        const denom = (r[col('denominacion')] || '').trim();
        const muniRaw = (r[col('municipio_nombre')] || '').trim();
        const municipality = mapCamMunicipalityName(muniRaw);
        const viaTipo = (r[col('direccion_via_tipo')] || '').trim();
        const viaName = (r[col('direccion_via_nombre')] || '').trim();
        const portal = (r[col('direccion_portal')] || '').trim();
        const addressRaw = [viaTipo, viaName, portal].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
        const address = addressRaw.toUpperCase().includes('RESERVADO')
          ? 'Dirección reservada en el registro público oficial'
          : addressRaw;
        const postalCode = (r[col('direccion_codigo_postal')] || '').trim();
        const district = formatMunicipalDistrict(r[col('direccion_distrito')] || '') || '';
        const utmX = parseFloat(r[col('direccion_coor_x')] || '');
        const utmY = parseFloat(r[col('direccion_coor_y')] || '');
        const coords = utm30NToWgs84(utmX, utmY);
        const rawPhone = (r[col('contacto_telefono')] || '').trim();
        const phone = normalizePhoneFieldForCatalog(rawPhone);
        const email = (r[col('contacto_correo')] || '').trim().split(';')[0]?.trim() || '';
        const entity = (r[col('entidad_denominacion')] || '').trim();
        const nif = (r[col('entidad_nif')] || '').trim();
        const gest = (r[col('tipo_gestion')] || '').trim();

        const serviceExplicitSpecs = classifyExplicitSpecialisations({
          name: denom,
          subtype: subtipo || tipo,
          sector
        });
        const entityOnlyAllSpecs = entity
          ? classifyExplicitSpecialisations({ name: '', subtype: '', sector: '', entity })
          : [];
        const entityDeclaredSpecs = entityOnlyAllSpecs.filter(s => !serviceExplicitSpecs.includes(s));
        const allSpecs = Array.from(new Set([...serviceExplicitSpecs, ...entityDeclaredSpecs]));

        const lowAll = normalizeStrict(`${denom} ${entity}`);
        const matchesTrackedEntity = Array.from(trackedEntities).some(t => lowAll.includes(t));

        // Incluir servicios con especialización literal declarada o de entidades clave monitorizadas
        if (allSpecs.length === 0 && !matchesTrackedEntity) continue;

        const sanitized = sanitizePersonalPractitionerRecord({
          regId,
          nif,
          entity,
          denom,
          subtipo,
          tipo,
          explicitSpecs: serviceExplicitSpecs,
          entitySpecs: entityDeclaredSpecs
        });

        const safeAddress = sanitized.isIndividualPractitioner
          ? 'Dirección particular omitida por privacidad (RGPD · Registro CAM)'
          : address;
        const safePhone = sanitized.isIndividualPractitioner ? '' : phone;

        const key = `CAM-SRV-${regId}`;
        lookupIndex.set(key, {
          registry_key: key,
          source_id: 'cam_servicios',
          official_name: sanitized.officialName,
          phone: safePhone,
          address: safeAddress,
          municipality,
          postal_code: sanitized.isIndividualPractitioner ? '' : postalCode,
          authorised_places: null
        });

        const supportResult = inferSupportsFromOfficialFields(tipo, subtipo, denom);
        const supports = supportResult.supports;
        const lifeStages = inferLifeStagesFromOfficialFields(sector, denom, tipo);
        const netInfo = mapPublicPrivateStatus(gest, false);

        const limitations: string[] = [
          'El Registro de Servicios de la Comunidad de Madrid no publica número de plazas ni accesibilidad física.'
        ];
        if (sanitized.isIndividualPractitioner) {
          limitations.push(
            `Titular persona física (RGPD): nombre, teléfono personal, dirección exacta y coordenadas omitidos por privacidad; consulte el expediente oficial ${regId} en el Portal CAM.`
          );
        }
        if (serviceExplicitSpecs.length === 0 && entityDeclaredSpecs.length > 0) {
          limitations.push(
            `La especialización proviene de la entidad titular (${sanitized.providerName}), no del nombre del servicio.`
          );
        } else if (serviceExplicitSpecs.length === 0) {
          limitations.push(`El servicio declara "${sanitized.officialName}" bajo sector "${sector}" sin mención literal de patología.`);
        }
        if (lifeStages.length === 0) {
          limitations.push('Etapa vital o edad admitida no consta en el registro oficial (confirmar con la entidad).');
        }

        const safeCoords = sanitized.isIndividualPractitioner ? null : coords;
        const safeEmail = sanitized.isIndividualPractitioner ? '' : email;

        centres.push({
          centre_id: key,
          provider_id: `PROV-${normalizeStrict(nif || (sanitized.isIndividualPractitioner ? regId : entity) || regId).replace(/\s+/g, '-').slice(0, 28)}`,
          provider_name: sanitized.providerName,
          official_name: sanitized.officialName,
          resource_domain: 'social',
          sector: sector || 'Servicios Sociales CAM',
          centre_type: tipo || 'Servicio Especializado',
          subtype: subtipo || tipo || 'Servicio autorizado',
          public_private_status: netInfo.status,
          management_type: gest || 'Servicio autorizado en Registro CAM',
          address: safeAddress,
          postal_code: sanitized.isIndividualPractitioner ? '' : postalCode,
          municipality,
          district: district || undefined,
          coordinates: safeCoords,
          has_valid_coordinates: Boolean(safeCoords),
          phone: safePhone,
          email: safeEmail,
          website: OFFICIAL_DATASET_URLS.cam_servicios,
          explicit_specialisations: serviceExplicitSpecs,
          entity_declared_specialisations: entityDeclaredSpecs,
          related_services: Array.from(
            new Set([tipo, subtipo, ...formatSupportRelatedNames(supports), ...supportResult.extraRelated].filter(Boolean))
          ),
          supports,
          services_offered: supports.map((sup, idx) => ({
            service_id: `SRV-${key}-${idx}`,
            centre_id: key,
            service_name: sanitized.officialName,
            service_type: sup,
            target_populations: serviceExplicitSpecs,
            allowed_life_stages: lifeStages,
            access_routes: [netInfo.accessType],
            source_dataset: `Registro de Servicios de Atención Social CAM (${regId})`,
            source_url: OFFICIAL_DATASET_URLS.cam_servicios,
            checked_at: checkDate
          })),
          allowed_life_stages: lifeStages,
          access_route: {
            access_type: netInfo.accessType,
            competent_body:
              netInfo.status === 'privado_autorizado'
                ? 'Entidad titular autorizada / Servicios Sociales'
                : 'Servicios Sociales municipales / Consejería de Familia (CAM)',
            official_description: `Servicio autorizado en registro regional (${gest || 'CAM'}).`,
            source_url: OFFICIAL_DATASET_URLS.cam_servicios,
            checked_at: checkDate,
            next_step_action: netInfo.nextStep,
            availability_known: false,
            waiting_list_known: false
          },
          availability: {
            status: 'contact_required',
            authorised_places: null,
            vacancies_known: false,
            source_url: OFFICIAL_DATASET_URLS.cam_servicios,
            checked_at: checkDate,
            stale: false
          },
          geographic_coverage: {
            type: 'community_wide',
            requires_residence: 'unknown',
            checked_at: checkDate
          },
          accessibility_features: [],
          provenance_records: [
            {
              attribute_name: serviceExplicitSpecs.length > 0 ? 'specialisation' : entityDeclaredSpecs.length > 0 ? 'entity_specialisation' : 'sector',
              value: `${sanitized.officialName} · ${sanitized.providerName} (${sector})`,
              source_dataset: `Registro de Servicios de Atención Social CAM (${regId})`,
              source_url: OFFICIAL_DATASET_URLS.cam_servicios,
              source_type: 'official_registry',
              retrieved_at: checkDate,
              extraction_method: 'structured',
              reviewer: 'Portal de Datos Abiertos Comunidad de Madrid (CSV oficial)',
              reviewer_role: 'data_steward',
              confidence: serviceExplicitSpecs.length > 0 ? 'explicit' : 'potential',
              quality: 'A'
            }
          ],
          last_checked: checkDate,
          limitations,
          is_individual_practitioner: sanitized.isIndividualPractitioner
        });
      }
    }
  }

  return { centres, lookupIndex };
}

