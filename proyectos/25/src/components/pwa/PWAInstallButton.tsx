import React, { useState, useEffect, useRef } from 'react';
import { usePWAInstall } from './usePWAInstall';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Download } from 'lucide-react';

export const PWAInstallButton: React.FC = () => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, showIOSGuide);

  useEffect(() => {
    if (!showIOSGuide) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowIOSGuide(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showIOSGuide]);

  // If already running as an installed PWA, hide the button
  if (isInstalled) {
    return null;
  }

  // Chromium / Android / Desktop flow
  if (isInstallable) {
    return (
      <button
        type="button"
        onClick={install}
        aria-label="Instalar App en tu dispositivo"
        className="flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 transition-colors cursor-pointer"
      >
        <Download className="w-3.5 h-3.5" aria-hidden="true" />
        Instalar App
      </button>
    );
  }

  // iOS Safari flow (beforeinstallprompt is not supported by WebKit)
  if (isIOS) {
    return (
      <>
        <button
          type="button"
          onClick={() => setShowIOSGuide(true)}
          aria-label="Instalar en iOS: ver instrucciones para iPhone o iPad"
          className="flex items-center gap-2 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 hover:bg-stone-50 transition-colors cursor-pointer"
        >
          <Download className="w-3.5 h-3.5 text-stone-500" aria-hidden="true" />
          Instalar en iOS
        </button>

        {showIOSGuide && (
          <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 p-4 backdrop-blur-xs"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ios-install-title"
            onClick={(e) => {
              if (e.target === e.currentTarget) setShowIOSGuide(false);
            }}
          >
            <div 
              ref={modalRef}
              className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl border border-stone-200"
              tabIndex={-1}
            >
              <h3 id="ios-install-title" className="text-base font-bold text-stone-900">Instalar en iPhone / iPad</h3>
              <p className="mt-2 text-xs text-stone-600 leading-relaxed">
                1. Toca el botón <strong>Compartir</strong> en la barra de herramientas de Safari.<br />
                2. Desliza hacia abajo y toca <strong>Añadir a la pantalla de inicio</strong>.
              </p>
              <button
                type="button"
                onClick={() => setShowIOSGuide(false)}
                className="mt-4 w-full rounded-lg bg-stone-100 py-2 text-xs font-semibold text-stone-800 hover:bg-stone-200 cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        )}
      </>
    );
  }

  return null;
};
