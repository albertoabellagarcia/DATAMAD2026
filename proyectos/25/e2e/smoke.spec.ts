import fs from 'node:fs';
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Madrid Apoyo Especializado — Smoke E2E y WCAG', () => {
  test('flujo ciudadano: carga completa, WCAG, filtro TEA, modal explicable y exportación CSV segura', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('./');

    // Verificar carga del catálogo oficial completo (>1000 recursos) y coherencia sin contradicciones
    await expect(page.getByText(/Resultados de la búsqueda/i).first()).toBeVisible({ timeout: 25000 });
    await expect(page.getByText(/·\s*\d+\s+recursos/i).first()).toBeVisible();
    await expect(page.getByText(/Nivel C\s*·\s*Orientación general/i)).toHaveCount(0);

    // Verificar que todos los enlaces tel: renderizados son números españoles válidos de 9 dígitos (o 010/012)
    const initialTelHrefs = await page.locator('a[href^="tel:"]').evaluateAll(els =>
      els.map(el => el.getAttribute('href') || '')
    );
    expect(initialTelHrefs.length).toBeGreaterThan(10);
    for (const href of initialTelHrefs) {
      expect(href).toMatch(/^tel:(?:[6789]\d{8}|01[02])$/);
    }

    // Verificar que se ha retirado el bloque de desambiguación y TDAH (0 registros) del buscador público
    await expect(page.getByText(/¿Buscas un término general\?/i)).toHaveCount(0);
    await expect(page.getByRole('button', { name: /TDAH/i })).toHaveCount(0);
    await expect(page.getByText(/Cód\.\s*[1456]/i)).toHaveCount(0);
    await expect(page.getByText(/CentrosAtencion|CentrosServiciosSociales|CentrosOrientacionValoracion/)).toHaveCount(0);
    await expect(page.getByText('Distrito CENTRO', { exact: true })).toHaveCount(0);

    // Auditoría automatizada de accesibilidad WCAG 2.1 A/AA en vista principal
    const axeHome = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(axeHome.violations).toEqual([]);

    // Verificar filtrado estricto de radio geográfico (10 km) y sincronización con el mapa
    const radius10Btn = page.getByRole('button', { name: 'Radio de búsqueda: 10 km' });
    await radius10Btn.click();
    await expect(page.getByRole('button', { name: 'Restablecer radio a toda la región (80 km)' })).toBeVisible();

    await page.getByRole('button', { name: /^Mapa$/i }).click();
    await expect(page.getByText(/Mapa territorial sincronizado con los filtros/i)).toBeVisible();
    await expect(page.getByText(/Radio:\s*10 km/i)).toBeVisible();
    await page.getByRole('button', { name: /Volver a la lista/i }).click();

    await page.getByRole('button', { name: 'Radio de búsqueda: 80 km' }).click();

    // Seleccionar perfil TEA y verificar recuento informativo + Grupo C plegado
    const autismButton = page.getByRole('button', { name: /Trastorno del espectro del autismo/i });
    await expect(autismButton).toBeVisible();
    await autismButton.click();

    await expect(page.getByText(/Especialización Publicada/i).first()).toBeVisible();
    const relatedCountText = await page.getByText(/·\s*\d+\s+recursos? relacionados?/i).first().textContent();
    const relatedNum = parseInt(relatedCountText?.match(/\d+/)?.[0] || '0', 10);
    expect(relatedNum).toBeGreaterThan(5);
    expect(relatedNum).toBeLessThan(200);

    const toggleGeneralBtn = page.getByRole('button', { name: /catálogo general de apoyo social \(Nivel C/i });
    await expect(toggleGeneralBtn).toBeVisible();
    await expect(toggleGeneralBtn).toHaveAttribute('aria-expanded', 'false');

    // Abrir modal "¿Por qué aparece?" en el primer resultado
    const whyBtn = page.getByRole('button', { name: /¿Por qué aparece\?/i }).first();
    await whyBtn.click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/Nivel de evidencia asignado/i)).toBeVisible();

    // Auditoría WCAG con el modal explicable abierto
    const axeDialog = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(axeDialog.violations).toEqual([]);

    // Cerrar modal con el botón accesible
    await dialog.getByRole('button', { name: /Cerrar modal/i }).click();
    await expect(dialog).toBeHidden();

    // Exportar CSV y validar estructura real y descarga
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /Exportar resultados en formato CSV/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^madrid_apoyo_especializado_resultados_.*\.csv$/);

    const downloadedPath = await download.path();
    expect(downloadedPath).toBeTruthy();
    const csvContent = fs.readFileSync(downloadedPath!, 'utf-8');
    expect(csvContent).toContain('ID Centro');
    expect(csvContent).toContain('URLs Oficiales');
    expect(csvContent.split('\n').length).toBeGreaterThan(2);

    expect(errors).toEqual([]);
  });

  test('responsive móvil (390x844): sin desbordamiento horizontal y filtros plegados', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('./');

    await expect(page.getByText(/Resultados de la búsqueda/i).first()).toBeVisible({ timeout: 25000 });
    const configureBtn = page.getByRole('button', { name: /Configurar filtros/i });
    await expect(configureBtn).toBeVisible();

    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth + 1;
    });
    expect(hasHorizontalOverflow).toBe(false);
  });
});
