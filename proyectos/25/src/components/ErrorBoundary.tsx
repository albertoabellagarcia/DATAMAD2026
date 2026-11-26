/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Global ErrorBoundary
 */

import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Madrid Apoyo Especializado - Error inesperado de renderizado:', error, errorInfo);
  }

  private handleReload = () => {
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#FBF9F5] text-stone-900 flex items-center justify-center p-6 font-sans antialiased">
          <div
            role="alert"
            className="max-w-lg w-full bg-white rounded-2xl border border-stone-200 shadow-sm p-8 text-center space-y-4"
          >
            <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-700">
              <AlertTriangle className="w-6 h-6" aria-hidden="true" />
            </div>
            <h1 className="text-lg font-bold text-stone-900">
              Se ha producido un fallo inesperado en la vista
            </h1>
            <p className="text-xs text-stone-600 leading-relaxed">
              Tus búsquedas guardadas localmente permanecen intactas en tu navegador. Recarga la aplicación para restaurar la sesión sin pérdida de datos.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={this.handleReload}
                className="px-4 py-2 bg-stone-900 text-white rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Recargar aplicación</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
