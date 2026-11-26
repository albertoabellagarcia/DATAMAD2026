/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * Madrid Apoyo Especializado v1.8 - Notificación accesible de actualización PWA
 */

import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';

export const PWAUpdatePrompt: React.FC = () => {
  const [needRefresh, setNeedRefresh] = useState(false);
  const updateSwRef = useRef<((reloadPage?: boolean) => Promise<void>) | null>(null);

  useEffect(() => {
    let active = true;
    import('virtual:pwa-register')
      .then(({ registerSW }) => {
        if (!active) return;
        const updateSW = registerSW({
          onNeedRefresh() {
            if (active) setNeedRefresh(true);
          },
          onOfflineReady() {
            // La aplicación y el catálogo quedan disponibles sin conexión en silencio
          }
        });
        updateSwRef.current = updateSW;
      })
      .catch(() => {
        // Entornos sin registro virtual de Service Worker (por ejemplo, tests unitarios)
      });

    return () => {
      active = false;
    };
  }, []);

  if (!needRefresh) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-[60] max-w-sm bg-stone-900 text-white border border-stone-700 rounded-xl shadow-lg p-4 text-xs no-print"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="font-bold text-white flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5 text-emerald-400 shrink-0" aria-hidden="true" />
            <span>Nueva versión disponible</span>
          </div>
          <p className="text-stone-300 leading-relaxed">
            Hay una actualización publicada del catálogo o de la aplicación. Actualice cuando quiera sin perder su flujo actual.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setNeedRefresh(false)}
          aria-label="Cerrar aviso de actualización"
          className="text-stone-300 hover:text-white p-1 cursor-pointer shrink-0"
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => setNeedRefresh(false)}
          className="px-2.5 py-1.5 rounded-lg border border-stone-600 text-stone-200 hover:bg-stone-800 font-medium cursor-pointer"
        >
          Más tarde
        </button>
        <button
          type="button"
          onClick={() => {
            updateSwRef.current?.(true);
          }}
          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold cursor-pointer"
        >
          Actualizar ahora
        </button>
      </div>
    </div>
  );
};
