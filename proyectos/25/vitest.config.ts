import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['src/utils/**/*.ts', 'scripts/ingest.ts'],
      exclude: ['**/*.test.ts', 'src/utils/specializedTestsSuite.ts'],
      thresholds: {
        lines: 65,
        functions: 70,
        branches: 55
      }
    }
  }
});
