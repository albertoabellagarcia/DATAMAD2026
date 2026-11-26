import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(() => {
  const base = process.env.VITE_BASE_PATH || '/';

  return {
    base,
    plugins: [
      {
        name: 'inject-production-csp',
        apply: 'build',
        transformIndexHtml(html) {
          const cspMeta =
            '    <meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\' data: blob: https://tile.openstreetmap.org https://*.tile.openstreetmap.org; style-src \'self\' \'unsafe-inline\'; connect-src \'self\'; font-src \'self\'; worker-src \'self\'; manifest-src \'self\'" />';
          return html.replace('<meta name="viewport"', `${cspMeta}\n    <meta name="viewport"`);
        },
      },
      react(),
      tailwindcss(),
      VitePWA({
        registerType: 'prompt',
        includeAssets: ['apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png', 'pwa-maskable-512x512.png', 'og-image.png'],
        workbox: {
          maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2,json}'],
          globIgnores: [
            '**/data/snapshots/*.csv',
            '**/data/snapshots/snapshot-202*.csv',
            '**/data/snapshots/catalog-classified.json',
          ],
          runtimeCaching: [
            {
              urlPattern: /\/data\/snapshots\/catalog-classified\.json$/i,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'datamad-catalog-classified-v1',
                expiration: {
                  maxEntries: 2,
                  maxAgeSeconds: 60 * 60 * 24 * 14,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /\/data\/(?:snapshots\/(?:snapshot-metadata|snapshot-diffs)|municipalities)\.json$/i,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'datamad-reference-json-v1',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 14,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
          ],
        },
        manifest: {
          id: base,
          lang: 'es',
          name: 'Madrid Apoyo Especializado',
          short_name: 'MadridApoyo',
          description: 'Buscador de recursos de atención social autorizados de Madrid y Comunidad de Madrid',
          categories: ['government', 'accessibility'],
          theme_color: '#ffffff',
          background_color: '#FBF9F5',
          display: 'standalone',
          start_url: base,
          scope: base,
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'pwa-maskable-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
        devOptions: {
          enabled: true,
          type: 'module',
        },
      }),
    ],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/leaflet')) return 'leaflet';
            if (id.includes('node_modules/lucide-react')) return 'icons';
            if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) {
              return 'vendor-react';
            }
            return undefined;
          },
        },
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, '.'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
