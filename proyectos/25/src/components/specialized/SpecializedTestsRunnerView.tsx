/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Canonical Validation Test Suite Runner
 * Ejecutor interactivo de las pruebas canónicas de las Secciones 31, 44, 59, 65, 79 y 90
 */

import React, { useState } from 'react';
import { runAllCanonicalTests, TEST_SUITE_CATEGORIES } from '../../utils/specializedTestsSuite';
import { 
  CheckCircle2, 
  XCircle, 
  Play, 
  RotateCcw, 
  Filter
} from 'lucide-react';

export const SpecializedTestsRunnerView: React.FC = () => {
  const [suiteResult, setSuiteResult] = useState(() => runAllCanonicalTests());
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [isRunning, setIsRunning] = useState(false);

  const handleRunTests = () => {
    setIsRunning(true);
    setTimeout(() => {
      setSuiteResult(runAllCanonicalTests());
      setIsRunning(false);
    }, 200);
  };

  const categories = [
    { id: 'ALL', label: 'Todas las pruebas' },
    ...TEST_SUITE_CATEGORIES
  ];

  const filteredTests = selectedCategory === 'ALL'
    ? suiteResult.results
    : suiteResult.results.filter(t => t.category === selectedCategory);

  return (
    <div className="space-y-6">
      {/* Cabecera y métricas globales */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-200 pb-5">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-widest text-stone-500">
            Suite Canónica v1.9 · {suiteResult.total} Casos de Prueba Oficiales
          </div>
          <h2 className="text-xl font-bold text-stone-900 mt-1">
            Matriz de Validación y Pruebas Críticas
          </h2>
          <p className="text-xs text-stone-600 mt-1 max-w-2xl leading-relaxed">
            Ejecuta en vivo el conjunto de pruebas canónicas que verifican la ausencia de inferencias prohibidas, la separación de sedes físicas, la no confusión de plazas y el orden lexicográfico.
          </p>
        </div>

        {/* Botón de re-ejecución */}
        <button
          type="button"
          onClick={handleRunTests}
          disabled={isRunning}
          aria-label="Re-ejecutar pruebas canónicas"
          className="px-4 py-2 bg-stone-900 text-white rounded-lg hover:bg-stone-800 text-xs font-semibold flex items-center gap-2 transition-colors self-start shrink-0 cursor-pointer disabled:opacity-50"
        >
          {isRunning ? <RotateCcw className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Play className="w-4 h-4" aria-hidden="true" />}
          <span>{isRunning ? 'Ejecutando suite...' : 'Re-ejecutar pruebas canónicas'}</span>
        </button>
      </div>

      {/* KPI Cards de validación */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-stone-200 bg-white">
          <div className="text-[11px] font-bold uppercase tracking-wider text-stone-500">Pruebas Totales</div>
          <div className="text-2xl font-mono font-bold text-stone-900 mt-1">
            {suiteResult.total}
          </div>
          <div className="text-[11px] text-stone-500 mt-0.5">Casos evaluados</div>
        </div>

        <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/50" role="status" aria-live="polite">
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">Pruebas Superadas</div>
          <div className="text-2xl font-mono font-bold text-emerald-900 mt-1">
            {suiteResult.passedCount} / {suiteResult.total}
          </div>
          <div className="text-[11px] text-emerald-700 font-semibold mt-0.5">
            {((suiteResult.passedCount / suiteResult.total) * 100).toFixed(0)}% de éxito (Objetivo: 100%)
          </div>
        </div>

        {(() => {
          const negTests = suiteResult.results.filter(t => t.category === 'REGLAS_NEGATIVAS');
          const negFailed = negTests.filter(t => !t.passed).length;
          return (
            <div className="p-4 rounded-xl border border-stone-200 bg-white">
              <div className="text-[11px] font-bold uppercase tracking-wider text-stone-500">Reglas Negativas</div>
              <div className="text-2xl font-mono font-bold text-stone-900 mt-1">
                {negFailed} fallos / {negTests.length}
              </div>
              <div className={`text-[11px] font-semibold mt-0.5 ${negFailed === 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                {negFailed === 0 ? 'Blindadas al 100%' : 'Revisar incidencias'}
              </div>
            </div>
          );
        })()}

        <div className="p-4 rounded-xl border border-stone-200 bg-white">
          <div className="text-[11px] font-bold uppercase tracking-wider text-stone-500">Tiempo de Ejecución</div>
          <div className="text-2xl font-mono font-bold text-stone-900 mt-1">
            {suiteResult.executionTimeMs.toFixed(1)} ms
          </div>
          <div className="text-[11px] text-stone-500 mt-0.5">&lt; 3 seg (umbral interactivo)</div>
        </div>
      </div>

      {/* Filtros por categoría */}
      <div className="flex items-center gap-1.5 overflow-x-auto text-xs pb-1" role="group" aria-label="Categorías de pruebas">
        <Filter className="w-3.5 h-3.5 text-stone-400 shrink-0 mr-1" aria-hidden="true" />
        {categories.map((cat) => (
          <button
            key={cat.id}
            type="button"
            aria-pressed={selectedCategory === cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 rounded-lg border whitespace-nowrap transition-colors font-medium cursor-pointer ${
              selectedCategory === cat.id
                ? 'bg-stone-900 text-white border-stone-900 font-semibold'
                : 'bg-white text-stone-700 border-stone-200 hover:bg-stone-50'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Tabla detallada de casos de prueba */}
      <div className="bg-white rounded-xl border border-stone-200 overflow-x-auto shadow-xs text-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-stone-100 text-stone-800 font-bold border-b border-stone-200 text-[11px]">
              <th className="p-3 w-28">Código ID</th>
              <th className="p-3">Escenario de Prueba</th>
              <th className="p-3">Resultado Esperado</th>
              <th className="p-3">Resultado Obtenido</th>
              <th className="p-3 w-28 text-center">Veredicto</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {filteredTests.map((test) => (
              <tr key={test.id} className="hover:bg-stone-50/50">
                <td className="p-3 font-mono font-bold text-stone-900">
                  {test.id}
                </td>
                <td className="p-3 font-medium text-stone-900">
                  <div>{test.title}</div>
                  <div className="text-[11px] text-stone-500 mt-0.5">{test.notes}</div>
                </td>
                <td className="p-3 text-stone-700 font-mono text-[11px]">
                  {test.expected}
                </td>
                <td className="p-3 text-stone-800 font-mono text-[11px]">
                  {test.actual}
                </td>
                <td className="p-3 text-center">
                  {test.passed ? (
                    <span className="inline-flex items-center gap-1 font-mono font-bold text-emerald-800 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 shrink-0" aria-hidden="true" />
                      <span>SUPERADA</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 font-mono font-bold text-rose-800 text-[11px]">
                      <XCircle className="w-3.5 h-3.5 text-rose-700 shrink-0" aria-hidden="true" />
                      <span>FALLIDA</span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
