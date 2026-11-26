/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Recálculo reproducible de diferencias entre una captura CSV base (--prev) y snapshot-latest.csv.
 */

import fs from 'node:fs';
import path from 'node:path';
import { computeDiffs, writeFileAtomicSync } from './ingest.ts';
import { parseSemicolonCSV } from '../src/utils/officialRegistryParser.ts';

function getArg(flag: string): string | undefined {
  const idx = process.argv.indexOf(flag);
  return idx >= 0 ? process.argv[idx + 1] : undefined;
}

const dir = path.resolve(process.cwd(), 'public/data/snapshots');
const prevPathArg = getArg('--prev');
const prevPath = prevPathArg
  ? path.resolve(process.cwd(), prevPathArg)
  : path.join(dir, 'snapshot-2026-11-15.csv');
const currPath = path.join(dir, 'snapshot-latest.csv');

if (!fs.existsSync(prevPath)) {
  console.error(`No se encontró la captura base en: ${prevPath}`);
  process.exit(1);
}
if (!fs.existsSync(currPath)) {
  console.error(`No se encontró la captura vigente en: ${currPath}`);
  process.exit(1);
}

const prevDate = getArg('--prev-date') || '2026-11-15';
const currDate = getArg('--curr-date') || '2026-11-17';

const prevRows = parseSemicolonCSV(new TextDecoder('latin1').decode(fs.readFileSync(prevPath)));
const currRows = parseSemicolonCSV(new TextDecoder('latin1').decode(fs.readFileSync(currPath)));
const diffs = computeDiffs('madrid_municipal', prevRows, currRows, prevDate, currDate);

const payload = {
  generated_at: new Date().toISOString(),
  previous_snapshot: prevDate,
  current_snapshot: currDate,
  total_changes: diffs.length,
  diffs
};

writeFileAtomicSync(path.join(dir, 'snapshot-diffs.json'), JSON.stringify(payload, null, 2), 'utf-8');
console.log(`✓ ${diffs.length} diferencias reales regeneradas (${prevDate} -> ${currDate}).`);
