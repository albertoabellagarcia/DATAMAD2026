/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Spanish Official Registry Phone Parser
 * Separa múltiples teléfonos registrales, resuelve sufijos abreviados (/06, -07) y bloques pegados,
 * y garantiza enlaces tel: estrictamente marcables en España.
 */

export interface ParsedPhoneField {
  validNumbers: string[];
  formattedNumbers: string[];
  displayText: string;
  rawNote: string | null;
  hasMalformedRaw: boolean;
}

const VALID_SPANISH_9_DIGIT_RE = /^[6789]\d{8}$/;
const VALID_SHORT_PUBLIC_RE = /^(010|012)$/;

export function formatSpanishPhone(num: string): string {
  const digits = num.replace(/\D/g, '');
  if (digits.length !== 9) return digits;
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)}`;
}

function splitConcatenatedNineDigitRuns(digits: string): string[] {
  if (digits.length === 9 && VALID_SPANISH_9_DIGIT_RE.test(digits)) {
    return [digits];
  }
  if (digits.length >= 18 && digits.length % 9 === 0) {
    const chunks: string[] = [];
    for (let i = 0; i < digits.length; i += 9) {
      const slice = digits.slice(i, i + 9);
      if (!VALID_SPANISH_9_DIGIT_RE.test(slice)) return [];
      chunks.push(slice);
    }
    return chunks;
  }
  return [];
}

/**
 * Extrae teléfonos españoles válidos y marcables desde un campo bruto de registro oficial
 * (p. ej. "917345138 - 695424170", "911048988655597499", "91 694 53 05 / 06", "91 383 99 27 / 89 62").
 */
export function extractSpanishPhoneNumbers(raw: string): ParsedPhoneField {
  const trimmed = (raw || '').trim();
  if (!trimmed || /^(RESERVADO|N\/D|-+)$/i.test(trimmed)) {
    return {
      validNumbers: [],
      formattedNumbers: [],
      displayText: '',
      rawNote: null,
      hasMalformedRaw: false
    };
  }

  // Extraer notas textuales (p. ej. "Esta línea sólo será atendida..." o "Cita previa:...")
  const textMatches = trimmed.match(/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][^0-9\n/;-]{3,}.*$/);
  const rawNote = textMatches ? textMatches[0].trim() : null;
  const numericRegion = rawNote ? trimmed.slice(0, trimmed.indexOf(rawNote)).trim() : trimmed;

  // Normalizar separadores raros (¿ por codificación, saltos de línea, :, ;, ,)
  // y re-unir casos tipo "91/ 673 24 64" o guiones usados entre 2 números ("917345138 - 695424170")
  let normalized = numericRegion
    .replace(/\r?\n/g, ' / ')
    .replace(/[¿;,:]+/g, ' / ')
    .replace(/\b(?:0034|\+34)\s*/g, '')
    // "91/ 673 24 64" -> "91 673 24 64"
    .replace(/\b(9\d)\s*\/\s*(\d)/g, '$1 $2')
    // Dos números separados por guion ("917345138 - 695424170", "91 628 30 29 - 683369080", "914781011-60886253")
    .replace(/(\d[\d.\s]{7,14}\d)\s*-\s*(\d[\d.\s]{5,14}\d)/g, '$1 / $2')
    // Sufijo corto tras número completo separado por guion ("91 532 07 09-07")
    .replace(/(\d[\d.\s]{7,14}\d)\s*-\s*(\d{2,4})(?=\s|$|\/)/g, '$1 / $2')
    // Espacios amplios entre bloques que forman ya 9+ dígitos ("911048988 655597499", "913993245  699086699")
    .replace(/\b([6789](?:[\s.-]?\d){8})\s+([6789](?:[\s.-]?\d){8})/g, '$1 / $2')
    .replace(/\b([6789](?:[\s.-]?\d){8})\s+([6789](?:[\s.-]?\d){8})/g, '$1 / $2');

  const rawSegments = normalized
    .split(/\s*\/\s*/)
    .map(s => s.trim())
    .filter(Boolean);

  const validSet = new Set<string>();
  const validList: string[] = [];
  let lastValidNine = '';
  let hasMalformedRaw = false;

  const pushValid = (num: string) => {
    if (!validSet.has(num)) {
      validSet.add(num);
      validList.push(num);
    }
    if (num.length === 9) {
      lastValidNine = num;
    }
  };

  for (const seg of rawSegments) {
    // Limpiar todo excepto dígitos para inspeccionar longitud real del segmento
    const digitsOnly = seg.replace(/\D/g, '');
    if (!digitsOnly) continue;

    // 1. Teléfono estándar o múltiples pegados (9, 18, 27 dígitos)
    const splitRuns = splitConcatenatedNineDigitRuns(digitsOnly);
    if (splitRuns.length > 0) {
      splitRuns.forEach(pushValid);
      continue;
    }

    // 2. Dos números pegados con puntos/espacios internos irregulares ("91112498391.437.88.56")
    if (digitsOnly.length > 9 && digitsOnly.length % 9 === 0) {
      const splitMulti = splitConcatenatedNineDigitRuns(digitsOnly);
      if (splitMulti.length > 0) {
        splitMulti.forEach(pushValid);
        continue;
      }
    }

    // 3. Códigos cortos institucionales (010, 012)
    if (VALID_SHORT_PUBLIC_RE.test(digitsOnly)) {
      pushValid(digitsOnly);
      continue;
    }

    // 4. Sufijos abreviados respecto al número anterior (p. ej. /06, /8962, /3207176)
    if (lastValidNine.length === 9 && (digitsOnly.length === 2 || digitsOnly.length === 3 || digitsOnly.length === 4 || digitsOnly.length === 7)) {
      const expanded = lastValidNine.slice(0, 9 - digitsOnly.length) + digitsOnly;
      if (VALID_SPANISH_9_DIGIT_RE.test(expanded)) {
        pushValid(expanded);
        continue;
      }
    }

    // 5. Fallback: buscar sub-cadenas de 9 dígitos dentro de separadores blancos en el segmento
    const tokens = seg.split(/\s+/).filter(Boolean);
    let extractedInSeg = false;
    let buf = '';
    for (const tok of tokens) {
      const td = tok.replace(/\D/g, '');
      if (!td) continue;
      buf += td;
      if (buf.length === 9 && VALID_SPANISH_9_DIGIT_RE.test(buf)) {
        pushValid(buf);
        buf = '';
        extractedInSeg = true;
      } else if (buf.length > 9) {
        const subRuns = splitConcatenatedNineDigitRuns(buf);
        if (subRuns.length > 0) {
          subRuns.forEach(pushValid);
          buf = '';
          extractedInSeg = true;
        }
      }
    }

    if (!extractedInSeg) {
      hasMalformedRaw = true;
    }
  }

  const formattedNumbers = validList.map(formatSpanishPhone);
  const displayText =
    formattedNumbers.length > 0
      ? formattedNumbers.join(' / ')
      : trimmed;

  return {
    validNumbers: validList,
    formattedNumbers,
    displayText,
    rawNote,
    hasMalformedRaw
  };
}
