import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

const rootDir = path.resolve(import.meta.dirname, '..');
const masterLogo = path.join(rootDir, 'docs', 'assets', 'logo-1024.png');
const publicDir = path.join(rootDir, 'public');

if (!existsSync(masterLogo)) {
  console.error(`No se encontró el logotipo maestro en ${masterLogo}`);
  process.exit(1);
}

const runConvert = (args) => {
  execFileSync('convert', args, { stdio: 'inherit' });
};

runConvert([masterLogo, '-resize', '192x192', '-strip', `PNG24:${path.join(publicDir, 'pwa-192x192.png')}`]);
runConvert([masterLogo, '-resize', '512x512', '-strip', `PNG24:${path.join(publicDir, 'pwa-512x512.png')}`]);
runConvert([masterLogo, '-resize', '180x180', '-strip', `PNG24:${path.join(publicDir, 'apple-touch-icon.png')}`]);
runConvert([
  masterLogo,
  '-crop',
  '540x540+242+242',
  '+repage',
  '-resize',
  '316x316',
  '-gravity',
  'center',
  '-background',
  '#F5F5F3',
  '-extent',
  '512x512',
  '-strip',
  `PNG24:${path.join(publicDir, 'pwa-maskable-512x512.png')}`,
]);

console.log('Iconos PWA reales generados en formato PNG en public/.');
