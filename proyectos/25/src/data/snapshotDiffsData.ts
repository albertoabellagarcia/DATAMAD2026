/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Dataset Snapshot Differences Fallback
 * Subsistema «Qué ha cambiado» (§84)
 * Las diferencias reales se calculan dinámicamente en scripts/ingest.ts y se publican
 * en /public/data/snapshots/snapshot-diffs.json. Sin diferencias ficticias escritas a mano.
 */

import { SnapshotDifference } from '../types/specialized';

export const CURRENT_SNAPSHOT_DATE = 'Sin diferencias pendientes (ver lectura en vivo)';
export const PREVIOUS_SNAPSHOT_DATE = 'Snapshot anterior';

export const SNAPSHOT_DIFFERENCES: SnapshotDifference[] = [];
