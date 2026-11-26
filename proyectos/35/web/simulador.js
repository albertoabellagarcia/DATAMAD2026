/* Simuladores y bibliotecas del resto de la Comunidad (24/11/2026).
   - «Probar una zona» (atención primaria): ganancia de cada zona de búsqueda de 250 m abierta ella sola.
   - «Probar un refugio» (calor): ganancia de cada espacio inventariado si abriera de 12 a 21 h con acceso libre.
   - Bibliotecas públicas de fuera de Madrid capital: solo en el mapa, nivel «potencial».
   Python calcula todo (cercasalud-mad: `web.datos_simulador`, `web.datos_simulador_refugios`, etapa
   `refugios_ampliados`); aquí solo se dibuja y se enseña. Las cifras de dos zonas o espacios no se suman. */
'use strict';

const SIM = { activo: false, probadas: [], fuente: null, cache: {} };
const SIM_MAXIMO = 3;
const SIM_REGIONAL = 300;
const SIM_MARINO = [3, 64, 120];
const SIM_ROJO = [181, 29, 47];
const anteriorSimulador = { montar: montarInterfaz, zonas: capasZonas, refugios: capasRefugios, tarjeta: tarjetaFlotante,
  clic: alPulsar, comparar: pintarComparar, todo: pintarTodo };

/* Los datos son opcionales: si faltan, la página funciona igual que antes. */
async function simLeer(clave,ruta) {
  D[clave]=await cargarOpcional(clave,()=>leer(ruta));
  if($('sim-bloque')){simPintar();pintarMapa();}
}
simLeer('simulador','datos/capas/simulador.json');
simLeer('simuladorB','datos/capas/simulador_refugios.json');

/* ---------------------------------------------------------------- datos de la actuación elegida */

function simDatos() {
  const f = carteraActual();
  return f ? (f.componente === 'b1' ? D.simuladorB : D.simulador) : null;
}
function simClave() {
  const f = carteraActual(), S = simDatos();
  if (!S) return null;
  const clave = `${f.componente}|${f.objetivo}`;
  return S.orden.includes(clave) ? clave : null;
}
/* Zonas con alguna ganancia en la combinación actual, de menor a mayor (las mayores se dibujan encima).
   Cada dato es un objeto {i} y no un índice suelto: los demás módulos descartan los objetos «falsos» (0). */
function simLista(clave) {
  if (!SIM.cache[clave]) {
    const S = simDatos(), col = S.columnas.valor[clave];
    const lista = [];
    S.zonas.forEach((fila, i) => { if (fila[col] > 0) lista.push({ i }); });
    lista.sort((a, b) => S.zonas[a.i][col] - S.zonas[b.i][col]);
    SIM.cache[clave] = { lista, maximo: lista.length ? S.zonas[lista[lista.length - 1].i][col] : 1 };
  }
  return SIM.cache[clave];
}
function simActivo() { return SIM.activo && E.paso === 'comparar' && Boolean(simClave()); }

/* ---------------------------------------------------------------- mapa */

function simCapas() {
  if (!simActivo()) return [];
  const clave = simClave(), S = simDatos(), col = S.columnas.valor[clave], { lista, maximo } = simLista(clave);
  const elegidas = new Set(SIM.probadas), clavesElegidas = SIM.probadas.join(',');
  // Evaluación del 24/11/2026: a escala regional se veían miles de puntos amontonados y el clic caía en el vecino.
  // Por debajo del zoom 11 solo se dibujan las SIM_REGIONAL mejores (y siempre las elegidas).
  const regional = E.zoom < 11;
  const datos = regional ? lista.filter((d, k) => k >= lista.length - SIM_REGIONAL || elegidas.has(d.i)) : lista;
  const movil = innerWidth <= 760, radioMinimo = movil ? 5 : 3, escala = movil ? 7 : 10;
  return [new deck.ScatterplotLayer({
    id: 'simulador', data: datos, getPosition: (d) => [S.zonas[d.i][0], S.zonas[d.i][1]],
    // Blanco con borde marino: se distingue sobre el azul y sobre el rojo del mapa.
    getFillColor: (d) => (elegidas.has(d.i) ? SIM_ROJO : conAlfa(BLANCO, 225)),
    getLineColor: (d) => (elegidas.has(d.i) ? BLANCO : SIM_MARINO), stroked: true, lineWidthUnits: 'pixels',
    getLineWidth: (d) => (elegidas.has(d.i) ? 2.5 : 1.2), radiusUnits: 'pixels',
    getRadius: (d) => radioMinimo + escala * Math.sqrt(S.zonas[d.i][col] / maximo), pickable: true,
    updateTriggers: { getFillColor: clavesElegidas, getLineColor: clavesElegidas, getLineWidth: clavesElegidas,
      getRadius: clave + '|' + radioMinimo },
  })];
}
// El simulador va encima de las zonas de la cartera: la mejor zona suele ser también una zona elegida.
capasZonas = function () {
  const capas = anteriorSimulador.zonas(), texto = capas.filter((c) => c && c.id.includes('numero'));
  return [...capas.filter((c) => !texto.includes(c)), ...simCapas(), ...texto];
};

/* ---------------------------------------------------------------- textos de una zona o espacio */

function simPuesto(i, clave) {
  const S = simDatos(), puesto = S.zonas[i][S.columnas.puesto[clave]];
  if (!puesto) return S.textos.sin_ganancia;
  return S.textos.puesto.replace('{puesto}', miles(puesto)).replace('{total}', miles(S.resumen[clave].zonas_con_ganancia));
}
/* Tipo y nivel de evidencia (refugios) y parte sin refugio a ninguna hora. */
function simDetalles(i, clave) {
  const S = simDatos(), z = S.zonas[i], c = S.columnas, lineas = [];
  if (c.tipo !== undefined) lineas.push(`${S.tipos[z[c.tipo]]} · ${S.niveles[z[c.nivel]]}`);
  if (c.extra && z[c.valor[clave]] > 0) lineas.push(S.textos.extra.replace('{n}', miles(z[c.extra[clave]])));
  return lineas;
}
function simTarjeta(i) {
  const clave = simClave(), S = simDatos(), z = S.zonas[i];
  return htmlTarjeta(S.lugares[z[2]], '', miles(z[S.columnas.valor[clave]]), S.textos.frase.replace('{n} ', ''),
    [...simDetalles(i, clave), simPuesto(i, clave)]);
}
function simElegir(i) {
  SIM.lleno = false;
  if (SIM.probadas.includes(i)) return;
  if (SIM.probadas.length >= SIM_MAXIMO) SIM.lleno = true; else SIM.probadas.push(i);
  simPintar(); pintarMapa(); simAvisoMovil();
}
function simQuitar(i) {
  SIM.probadas = SIM.probadas.filter((x) => x !== i);
  SIM.lleno = false;
  simPintar(); pintarMapa(); simAvisoMovil();
}
/* En móvil el resultado queda en el panel oculto: la barra «Comparar actuaciones» enseña la última zona elegida. */
function simAvisoMovil() {
  const barra = document.querySelector('#vista-comparar .control-resultados span');
  if (!barra) return;
  if (SIM.textoBarra === undefined) SIM.textoBarra = barra.textContent;
  const S = simDatos(), clave = simClave(), ultima = SIM.probadas[SIM.probadas.length - 1];
  barra.textContent = innerWidth <= 760 && SIM.activo && S && clave && ultima !== undefined
    ? S.lugares[S.zonas[ultima][2]] + ' · ' + miles(S.zonas[ultima][S.columnas.valor[clave]]) : SIM.textoBarra;
}
/* Al activar, el mapa se acerca a las tres mejores zonas de la combinación actual. */
function simEncuadrarMejores() {
  const clave = simClave(), S = simDatos();
  if (!clave) return;
  const mejores = simLista(clave).lista.slice(-3).map((d) => S.zonas[d.i]);
  if (!mejores.length) return;
  const lon = mejores.map((z) => z[0]), lat = mejores.map((z) => z[1]), margen = 0.02;
  encuadrar([Math.min(...lon) - margen, Math.min(...lat) - margen, Math.max(...lon) + margen, Math.max(...lat) + margen]);
}

/* ---------------------------------------------------------------- panel de Comparar */

function simMontar() {
  if ($('sim-bloque') || !$('barras')) return;
  const bloque = el('section', { id: 'sim-bloque', clase: 'sim-bloque', 'aria-live': 'polite' });
  bloque.hidden = true;
  bloque.innerHTML = '<h3 id="sim-titulo"></h3><p id="sim-texto" class="nota"></p>'
    + '<label class="casilla destacada"><input type="checkbox" id="sim-ver"> <span id="sim-casilla"></span></label>'
    + '<div id="sim-zonas"></div><details id="sim-supuestos" class="desplegable"><summary id="sim-supuestos-titulo">'
    + '</summary><p id="sim-aviso" class="nota"></p><p id="sim-limites" class="nota"></p></details>';
  // Evaluación del 24/11/2026: abajo del panel nadie lo encontraba; va justo debajo de las barras de la comparación.
  $('barras').after(bloque);
  $('sim-ver').addEventListener('change', (e) => {
    SIM.activo = e.target.checked;
    SIM.lleno = false;
    if (!SIM.activo) SIM.probadas = [];
    simPintar(); pintarMapa(); simAvisoMovil();
    if (SIM.activo) simEncuadrarMejores();
  });
}

function simPintar() {
  const caja = $('sim-bloque');
  if (!caja) return;
  const clave = simClave(), S = simDatos();
  caja.hidden = !clave;
  if(!S){
    SIM.activo=false;caja.hidden=false;
    const archivo=carteraActual().componente==='b1'?'datos/capas/simulador_refugios.json':'datos/capas/simulador.json';
    $('sim-titulo').textContent='Simulador no disponible';
    $('sim-texto').textContent=`Simulador no disponible: falta su archivo de datos (${archivo}). Recarga la página para reintentar.`;
    $('sim-ver').closest('label').hidden=true;$('sim-supuestos').hidden=true;$('sim-zonas').replaceChildren();return;
  }
  $('sim-ver').closest('label').hidden=false;
  if (!clave) return;
  // Al pasar de zonas de primaria a espacios de refugio (o al revés), las elegidas dejan de tener sentido.
  if (SIM.fuente !== S) {
    const cambio = SIM.fuente !== null;
    SIM.probadas = []; SIM.lleno = false; SIM.fuente = S;
    // Al pasar de primaria a refugios (o al revés) con el simulador activo, el mapa se acerca a los mejores.
    if (cambio && SIM.activo) setTimeout(simEncuadrarMejores, 60);
  }
  const t = S.textos, f = carteraActual();
  $('sim-titulo').textContent = t.titulo;
  $('sim-casilla').textContent = t.casilla;
  $('sim-ver').checked = SIM.activo;
  $('sim-texto').textContent = `${t.texto} ${t.modos[f.componente]} · ${f.objetivo_texto}.`;
  $('sim-supuestos-titulo').textContent = t.supuestos || 'Supuestos';
  $('sim-supuestos').hidden = !SIM.activo;
  $('sim-aviso').textContent = t.aviso;
  $('sim-limites').textContent = t.limites;
  if (!SIM.activo) { $('sim-zonas').replaceChildren(); return; }
  const aviso = SIM.lleno ? [el('p', { clase: 'sim-lleno', texto: t.lleno })] : [];
  if (!SIM.probadas.length) { $('sim-zonas').replaceChildren(el('p', { clase: 'nota', texto: t.vacia })); return; }
  const col = S.columnas.valor[clave];
  $('sim-zonas').replaceChildren(...SIM.probadas.map((i) => {
    const z = S.zonas[i];
    const quitar = el('button', { texto: t.quitar, clase: 'enlace sim-quitar' });
    quitar.addEventListener('click', () => simQuitar(i));
    return el('article', { clase: 'sim-zona' }, [
      el('span', { clase: 'sim-etiqueta', texto: t.etiqueta || 'Simulación' }),
      el('b', { texto: S.lugares[z[2]] }),
      el('div', { clase: 'sim-cifra' }, [el('strong', { texto: miles(z[col]) }), el('span', { texto: t.frase.replace('{n} ', '') })]),
      ...simDetalles(i, clave).map((x) => el('p', { clase: 'nota', texto: x })),
      el('p', { clase: 'micro', texto: simPuesto(i, clave) }), quitar]);
  }), ...aviso);
}

pintarComparar = function () { anteriorSimulador.comparar(); simPintar(); };

/* ---------------------------------------------------------------- bibliotecas del resto de la Comunidad */

function bibActivas() {
  return E.bibliotecasCM && E.paso === 'diagnosticar' && U.tema === 'refugios' && Boolean(D.refugios?.bibliotecas_cm);
}
capasRefugios = function () {
  const capas = anteriorSimulador.refugios();
  if (!bibActivas()) return capas;
  const b = D.refugios.bibliotecas_cm, tipo = D.refugios.tipos.find((x) => x.clave === 'biblioteca');
  capas.push(new deck.ScatterplotLayer({
    id: 'bibliotecas_cm', data: b.puntos, getPosition: (d) => [d[0], d[1]], getFillColor: BLANCO,
    getLineColor: rgb(tipo ? tipo.color : '#6A3D9A'), stroked: true, radiusUnits: 'pixels', getRadius: RADIO_NIVEL[2],
    lineWidthUnits: 'pixels', getLineWidth: BORDE_NIVEL[2], pickable: true,
  }));
  return capas;
};
function bibTarjeta(d) {
  const b = D.refugios.bibliotecas_cm;
  return htmlTarjeta(d[2], '', b.tipo, b.aviso, [d[3], b.horarios[d[4]], b.evidencias[d[5]], b.fuente]);
}
function bibMontar() {
  const b = D.refugios?.bibliotecas_cm;
  if (!b || !$('rf-niveles') || $('rf-bibliotecas')) return;
  const entrada = el('input', { type: 'checkbox', id: 'rf-bibliotecas' });
  entrada.addEventListener('change', () => { E.bibliotecasCM = entrada.checked; pintarTodo(); });
  $('rf-niveles').append(el('div', { clase: 'rf-nivel rf-bibliotecas' }, [
    el('label', { clase: 'casilla' }, [entrada, el('span', { clase: 'rf-forma rf-forma-2' }), D.refugios.casillas.bibliotecas]),
    el('p', { clase: 'nota', texto: 'Fuera de Madrid capital no hay lista oficial de refugios: estos puntos no cambian ninguna cifra. Ubicadas con OpenStreetMap; la climatización no consta.' })]));
}

/* ---------------------------------------------------------------- enganches */

montarInterfaz = function () { anteriorSimulador.montar(); simMontar(); bibMontar(); };
pintarTodo = function () {
  anteriorSimulador.todo();
  if ($('rf-bibliotecas')) $('rf-bibliotecas').checked = Boolean(E.bibliotecasCM);
  simPintar();
};
tarjetaFlotante = function (info) {
  if (info.layer?.id === 'simulador' && info.object) return simEstilo(simTarjeta(info.object.i));
  if (info.layer?.id === 'bibliotecas_cm' && info.object) return simEstilo(bibTarjeta(info.object));
  return anteriorSimulador.tarjeta(info);
};
/* El mismo aspecto que las demás tarjetas flotantes del motor (`tarjetaFlotante` de app.js). */
function simEstilo(html) {
  return { html, className: 'tarjeta-flotante',
    style: { backgroundColor: '#FFFFFF', color: '#1A1A1A', padding: '12px 16px', borderRadius: '6px',
      border: '1px solid #D0D0D0', boxShadow: '0 3px 12px rgba(0,0,0,.18)', maxWidth: '340px', fontFamily: FUENTE } };
}
alPulsar = function (info) {
  if (info.layer?.id === 'simulador' && info.object) { simElegir(info.object.i); return; }
  if (info.layer?.id === 'bibliotecas_cm' && info.object) {
    const tarjeta = $('zona-senalada');
    tarjeta.innerHTML = bibTarjeta(info.object);
    tarjeta.hidden = false;
    const cerrarFicha = el('button', { texto: 'Cerrar ficha', clase: 'enlace' });
    cerrarFicha.addEventListener('click', () => { tarjeta.hidden = true; });
    tarjeta.append(cerrarFicha);
    if (innerWidth <= 760 && typeof abrirPanelMovil === 'function') abrirPanelMovil(true);
    tarjeta.scrollIntoView({ block: 'nearest' });
    return;
  }
  anteriorSimulador.clic(info);
};
