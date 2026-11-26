// Presentación de Kuanto: navegación, pasos, renders animados y modo orador.
// Sin dependencias ni red. Lienzo y exportación según AgentBuff Presentation (MIT);
// el modo orador sigue el método de guizang-ppt-skill (notas, tiempo por bloque), escrito de cero.

// === GUION: lo que dice cada orador, tiempo previsto (s) y avisos ===
const NOTAS = {
  'corto': { s: 35, texto: '', cue: 'El corto se reproduce solo y al acabar pasa a la siguiente. Yeray sale al escenario durante el fundido. Sin vídeo, la pantalla queda en negro: avanza con la flecha.' },
  'ciudad': { s: 5, texto: '«Una ciudad es muchas cosas.» [PAUSA]' },
  'luz': { s: 12, texto: '«Es una luz que se enciende en una ventana.» [→] «Es el trayecto de cada mañana.» [→] «Es el sitio al que vuelves cuando todo lo demás ha terminado.» [PAUSA]' },
  'cuenta': { s: 7, texto: '«Y durante años, vivir en ella se ha convertido en una cuenta que no sale.» [→ fórmula] [PAUSA LARGA]' },
  'cifra': { s: 16, texto: '«En la Comunidad de Madrid, uno de cada tres hogares que viven de alquiler dedica más del 40 % de lo que ingresa a la vivienda.» [→] «En la ciudad de Madrid, el alquiler mediano ya pesa un 19,6 % de la renta de los hogares.» [→] «Y no pesa igual en todas partes: del 12,6 % de Villanueva de la Cañada al 24,0 % de Centro.» [PAUSA]', cue: '1 de cada 3 = 36,0 % (ECV 2025, intervalo 28,6–43,4; estimado). El render: altura y color, lo que pesa el alquiler en cada zona.' },
  'creemos-1': { s: 4, texto: '«Creemos que nadie debería descubrir demasiado tarde que su casa cuesta más de lo que parecía.»' },
  'creemos-2': { s: 4, texto: '«Creemos que el tiempo que pasas en el transporte público también es un precio.»' },
  'creemos-3': { s: 4, texto: '«Y creemos que una decisión así merece algo más que un presentimiento.» [PAUSA]' },
  'respuesta': { s: 6, texto: '«Merece una respuesta.» [→ el mapa y el logo] «Esto es Kuanto. Alex.»' },
  'directo': { s: 210, texto: '«Os presento a Lucía. Treinta años, vive sola, gana 24.000 euros brutos y trabaja en Getafe. Todos los portales le dicen cuánto cuesta el alquiler. Kuanto le dice cuánto le sobra.» Demo en directo. Cierre: «176 euros más al mes en Parla, a cambio de catorce horas más de transporte público. ¿Le compensa? Ahora lo decide sabiendo. Izan.»', cue: 'Pestaña del túnel ya abierta con el estado de Lucía. Recorrido: tarjetas → «Ver el mapa» con «Lo que sobra» → Parla (467 €, 25,9 h) → «Horas de viaje» y «Precio de la hora» → «Otros escenarios»: fin del descuento. Vuelve aquí y avanza.' },
  'capas': { s: 18, texto: '«Hay muchos proyectos que miran el alquiler. Algunos añaden el tiempo. Nosotros hacemos la cuenta entera: siete capas. El neto con el IRPF de 2026, el abono más barato para cada persona, la cesta según ingresos, el hogar y, sobre todo, desde dónde trabajas tú.»' },
  'lucia-mapa': { s: 20, texto: '«Y esto es lo que cambia. La misma Lucía, con el mismo sueldo: en Salamanca le faltan 482 euros al mes. En Villarejo de Salvanés le sobran 703, pero con casi 70 horas de transporte público al mes. En diez zonas, directamente, no le llega.»', cue: 'Verde hacia arriba: le sobra. Rojo hacia abajo: no le llega.' },
  'engana': { s: 14, texto: '«Mirar solo el alquiler engaña. En Chamartín el alquiler es más caro que en Centro, y aun así pesa menos: 16 % frente a 24 %.» [→] «Allí se gana un 78 % más.»' },
  'horas': { s: 12, texto: '«Y el tiempo. Con el sueldo mínimo, irse lejos para pagar menos solo compensa las horas de transporte público, valoradas a lo que ganas por hora, en una de cada siete combinaciones.»' },
  'bono': { s: 18, texto: '«Casi cuatro de cada cinco solicitudes del Bono Alquiler Joven se quedaron sin ayuda: más de 40.000. Y la proporción aceptada no cambia con lo que pesa el alquiler.» [→] «Y con el sueldo mínimo, Madrid capital se queda fuera del tope del Bono por 79 euros.»', cue: '51.735 solicitudes, 11.477 aceptadas (22,2 %). Si preguntan: p = 0,82, estimado.' },
  'abono': { s: 11, texto: '«Y lo que viene: si todo el descuento del abono termina con 2026, hasta 33 euros más al mes por adulto. A 21 de noviembre no se había publicado ninguna prórroga. Kuanto ya lo calcula, corona a corona.»' },
  'ia': { s: 12, texto: '«¿Y una IA? Lo probamos. ChatGPT y Gemini miraron entre cuatro y seis zonas, erraron el neto y cada uno puso un municipio en la zona de abono equivocada. Kuanto da cifra en 99. Yeray os cuenta cómo.»', cue: 'Cuatro respuestas: ilustra, no mide.' },
  'timeline': { s: 22, texto: '«Lo organizamos como una empresa. Cuatro líneas de trabajo con un responsable cada una, y nueve hitos: las reglas y la CI antes de analizar un solo dato; luego los contratos de datos, la API, el cálculo validado, el MCP; dos congelaciones de datos y el informe. 259 pull requests, 215 issues, 393 veredictos de agentes, 993 tests. Y ni una fusión sin la CI en verde.»' },
  'tuberia': { s: 16, texto: '«Así funciona por dentro. 89 fuentes oficiales, cada una con su huella. Un motor de trece mil quinientas líneas que aplica la ley y los horarios. Una API estática y congelada. Y de ahí, cinco salidas: la web, un MCP para asistentes de IA, Smart Data Models, DCAT-AP y el informe técnico. Sin servidor.»' },
  'muro': { s: 16, texto: '«Detrás de cada número: casi medio millón de alquileres declarados, cuarenta y dos mil trayectos calculados, trescientas diez mil viviendas cuadradas con Hacienda al 99,9 %, 393 veredictos de agentes. Y cero cifras públicas sin fuente.»', cue: 'Los recuadros se dibujan sobre las cinco cifras que se dicen en voz alta.' },
  'metodos': { s: 16, texto: '«Cada cifra tiene su método y su prueba. El neto, contra ocho casos calculados aparte sobre el BOE. Los tiempos, contra 494 viajes. El alquiler, de contratos, no de anuncios. Horquillas en vez de puntos. Y en el Bono, registro previo y nueve especificaciones publicadas, también las que no salen.»' },
  'maquinas': { s: 16, texto: '«Somos tres personas. Pero hemos construido un equipo: agentes que escriben el código y otros que lo auditan. Doce especialistas, ocho revisores con auditoría adversarial, dieciséis guardias automáticos. 393 veredictos documentados y más de cinco mil líneas de conocimiento experto escrito. Ningún cambio de un área con revisor entra sin su veredicto.»' },
  'privacidad': { s: 11, texto: '«Y en un momento en que nuestros datos valen más que nunca, una promesa sencilla: tu sueldo nunca sale de tu móvil.»' },
  'negocio': { s: 18, texto: '«Un motor, tres mercados. Las personas, gratis, para decidir dónde vivir. La Administración, para medir dónde no llega su política de vivienda. Y empresas e IA, que pueden usar nuestra cifra dentro de sus productos. Coste de servir: cero euros de servidor. Replicable en otra región, con sus propias fuentes.»' },
  'datamad': { s: 6, texto: '«Datos de la Comunidad dentro del cálculo. Viable. Abierto. Con valor social.»' },
  'cierre': { s: 12, texto: '«Empezamos diciendo que una ciudad es muchas cosas. Para demasiada gente, también es una cuenta que no sale.» [PAUSA] «Nadie debería descubrir demasiado tarde cuánto le cuesta su casa.» [→] «Esto es Kuanto. Gracias.»', cue: 'Tecla A: anexo para las preguntas.' },
  'ysi': { s: 16, texto: '«Y lo que asusta es lo que viene. Si el alquiler sube un 10 %, a Lucía le sobran 90 euros menos: un 31 %. Si acaba el descuento del abono, su transporte sube un 70 %. Si tuviera 25 años, al cumplir 26 perdería el Abono Joven. Y todo junto: un 35 % menos cada mes. Y un 10 % no es exagerado: en 2024 el precio de los contratos nuevos subió un 9,2 %. Kuanto calcula cada ¿y si…? antes de que ocurra.»', cue: 'Escenarios del motor de la app, estimados.' },
  'del-dato': { s: 12, texto: '«Y sin cajas negras: cada capa tiene su fuente, su método, su validación y su incertidumbre declarada. Si algo no lo sabemos, lo decimos.»', cue: 'Una mirada a la tabla; el detalle, para las preguntas.' },
  'recomendaciones': { s: 14, texto: '«Y esto no se queda en un mapa. Tres decisiones que la Administración puede tomar mañana: publicar por qué se rechaza cada solicitud del Bono, decir qué renta cuenta para quien no declara, que cambia el resultado de 122 municipios a ninguno, y anunciar ya si el descuento del abono sigue en 2027.»' },
  'no-hacemos': { s: 18, texto: '«Y también es rigor lo que no hacemos. No damos un índice de ‹dónde vivir› con pesos que alguien elige. No usamos precios de anuncios. No pintamos ceros donde no hay datos. No calculamos el neto fuera de lo validado, y lo que se imputa sale marcado como estimado. Porque llegar a fin de mes es una decisión demasiado seria para darla a medias. No es que no sepamos hacerlo: es que no queremos hacerlo a medias. Está en nuestra hoja de ruta, con las mismas reglas.»' },
  'apoyo': { s: 15, texto: '«Félix Peralta y Alberto Martos revisaron el proyecto y nos dieron feedback durante el desarrollo. Y cuando lo contamos en LinkedIn, tuvo 40 reacciones y 17 comentarios positivos, según nuestro recuento. ¿Saber, antes de firmar, si vas a llegar a fin de mes?»', cue: 'Cuando lleguen sus frases literales, se leen aquí.' },
  'c-apertura': { s: 60, texto: '«Una ciudad es muchas cosas.» [→] «Es una luz que se enciende en una ventana. Es el trayecto de cada mañana. Es el sitio al que vuelves.» [→] «Y vivir en ella se ha convertido en una cuenta que no sale.» [→] «En la Comunidad de Madrid, uno de cada tres hogares que viven de alquiler dedica más del 40 % de lo que ingresa a la vivienda. En la ciudad de Madrid, el alquiler mediano ya pesa un 19,6 %.» [→] «Creemos que nadie debería descubrir demasiado tarde que su casa cuesta más de lo que parecía. Que el tiempo en el transporte público también es un precio. Y que una decisión así merece algo más que un presentimiento.» [→] «Merece una respuesta.» [→] «Esto es Kuanto. Alex.»', cue: 'Con ?corto en la URL, el corto se ve primero dentro de esta diapositiva.' },
  'c-directo': { s: 210, texto: '«Os presento a Lucía: 30 años, 24.000 euros brutos, trabaja en Getafe. Todos los portales le dicen cuánto cuesta el alquiler. Kuanto le dice cuánto le sobra.» [→ capas] «Siete capas en una sola cifra.» Tecla W o el botón: demo en directo. [→ al volver] «Getafe, 291 euros y doce horas; Parla, 467 pero veintiséis horas; en Centro no le llega. Ahora lo decide sabiendo. Izan.»', cue: 'W abre la portada de kuantoapp.github.io en otra pestaña; desde ahí, «Ver cuánto me sobra» y el estado de Lucía.' },
  'c-porque': { s: 120, texto: '«La misma Lucía, con el mismo sueldo: de menos 482 euros en Salamanca a más 703 en Villarejo, con casi 70 horas de transporte público.» [→] «Mirar solo el alquiler engaña: Chamartín es más caro y pesa menos.» [→] «Con el sueldo mínimo, vivir lejos compensa en una de cada siete combinaciones.» [→] «Casi cuatro de cada cinco solicitudes del Bono, sin ayuda; Madrid capital fuera del tope por 79 euros.» [→] «¿Y si sube el alquiler y se acaba el descuento? Un 35 % menos cada mes.» [→] «Y una IA miró entre cuatro y seis zonas; Kuanto, 99. Yeray os cuenta cómo.»' },
  'c-rigor': { s: 90, texto: '«Quince días, cuatro líneas de trabajo y nueve hitos, con las reglas y la CI antes de analizar un solo dato.» [→] «De 89 descargas oficiales y abiertas a cinco salidas, sin servidor.» [→] «Detrás de cada número: casi medio millón de alquileres, 42.785 trayectos, viviendas cuadradas con Hacienda al 99,9 %, 393 veredictos de agentes y cero cifras sin fuente.» [→] «Tres personas y un equipo de agentes que audita cada cambio.» [→] «Cada capa, con su validación. Y lo que no hacemos, todavía, porque no queremos hacerlo a medias.»' },
  'c-cierre': { s: 60, texto: '«Tu sueldo nunca sale de tu móvil.» [→] «Tres decisiones que la Administración puede tomar mañana.» [→] «Un motor, tres mercados, cero euros de servidor.» [→] «Félix Peralta y Alberto Martos revisaron el proyecto; el post de LinkedIn tuvo 40 reacciones, según nuestro recuento.» [→] «Lo que DataMad pide, cumplido.» [→] «Nadie debería descubrir demasiado tarde cuánto le cuesta su casa. Esto es Kuanto. Gracias.»' },
  'anexo-fuentes': { s: 0, texto: 'Anexo: fuentes por publicador. Esc para volver al cierre.' },
  'anexo-metodo': { s: 0, texto: 'Anexo: método y validación.' },
  'anexo-harness': { s: 0, texto: 'Anexo: cómo trabajan los agentes.' },
};

// === ESTADO ===
const todas = [...document.querySelectorAll('.slide')];
const idDe = (s) => s.dataset.id;
let modo = 'normal'; // normal | anexo
const recorrido = () => todas.filter((s) => (modo === 'normal' ? !s.classList.contains('oculta') : idDe(s).startsWith('anexo')));
let lista = recorrido();
let i = 0, paso = 0, generacion = 0;
const canal = 'BroadcastChannel' in window ? new BroadcastChannel('kuanto-pitch') : null;
const ES_ORADOR = new URLSearchParams(location.search).has('orador');
const ESTATICO = navigator.webdriver && !new URLSearchParams(location.search).has('animado');

// === LIENZO: escala 1920×1080 entero a la ventana ===
function encajar() {
  const s = Math.min(innerWidth / 1920, innerHeight / 1080);
  document.getElementById('escenario').style.transform = `translate(${(innerWidth - 1920 * s) / 2}px,${(innerHeight - 1080 * s) / 2}px) scale(${s})`;
}

// === NAVEGACIÓN ===
const pasosDe = (s) => Number(s.dataset.pasos || 0);
const avisar = () => canal?.postMessage({ tipo: 'estado', id: idDe(lista[i]), paso, i, total: lista.length });
function mostrar(n, p = 0) {
  const antes = lista[i];
  i = Math.max(0, Math.min(lista.length - 1, n));
  paso = p;
  const s = lista[i];
  if (antes && antes !== s) salir(antes);
  todas.forEach((x) => x.classList.toggle('active', x === s));
  aplicarPasos(s);
  if (antes !== s || p === 0) entrar(s);
  history.replaceState(null, '', `#${idDe(s)}`);
  document.getElementById('progreso').style.width = `${((i + 1) / lista.length) * 100}%`;
  pintarNotas();
  avisar();
}
function siguiente() {
  if (cerrarCorto()) return;
  const s = lista[i];
  if (paso < pasosDe(s)) { paso++; aplicarPasos(s); alPaso(s); pintarNotas(); avisar(); return; }
  if (i < lista.length - 1) mostrar(i + 1);
}
function anterior() {
  if (paso > 0) { paso--; aplicarPasos(lista[i]); pintarNotas(); avisar(); return; }
  if (i > 0) mostrar(i - 1, pasosDe(lista[i - 1]));
}
function aplicarPasos(s) {
  // .ya: ya ha entrado; .actual: es el paso en curso (foco en la versión corta); data-hasta: desaparece después de ese paso.
  s.querySelectorAll('[data-paso]').forEach((el) => {
    const n = Number(el.dataset.paso);
    el.classList.toggle('ya', n <= paso);
    el.classList.toggle('actual', n === paso);
  });
  s.querySelectorAll('[data-hasta]').forEach((el) => el.classList.toggle('fuera', paso > Number(el.dataset.hasta)));
  // data-oculto: pasos en los que un bloque sale un momento y luego vuelve (versión corta).
  s.querySelectorAll('[data-oculto]').forEach((el) => el.classList.toggle('fuera', el.dataset.oculto.split(',').map(Number).includes(paso)));
  s.classList.toggle('completa', paso === pasosDe(s));
  moverCarril(s, paso);
}

// === CINTA VERTICAL (apertura de la versión corta): sube hasta centrar el tramo del paso ===
function moverCarril(s, n) {
  const carril = s.querySelector('.carril');
  if (!carril) return;
  const tramos = [...carril.querySelectorAll('.tramo')], t = tramos[Math.min(n, tramos.length - 1)];
  carril.style.transform = `translateY(${540 - (t.offsetTop + t.offsetHeight / 2)}px)`;
  tramos.forEach((x, k) => x.classList.toggle('actual', k === n));
}

// === DEMO EN DIRECTO: la web con el estado de Lucía (tecla W o botón [data-demo]) ===
const DEMO_URL = 'https://kuantoapp.github.io/';
document.querySelectorAll('[data-demo]').forEach((a) => { a.href = DEMO_URL; });

// === CORTO DENTRO DE LA PRIMERA DIAPOSITIVA (versión corta, con ?corto) ===
const capaCorto = document.getElementById('cortoCapa');
if (capaCorto && new URLSearchParams(location.search).has('sin-corto')) capaCorto.remove();
function cerrarCorto() {
  const c = document.getElementById('cortoCapa');
  if (!c) return false;
  c.querySelector('video').pause();
  c.remove();
  return true;
}
if (document.getElementById('cortoCapa')) {
  const v = document.querySelector('#cortoCapa video');
  v.onended = cerrarCorto;
  v.play().catch(() => {});
}
function cambiarModo(nuevo, volverA) {
  modo = nuevo;
  lista = recorrido();
  i = 0;
  mostrar(Math.max(0, volverA ? lista.findIndex((s) => idDe(s) === volverA) : 0));
}

// === TECLADO, CLIC Y TÁCTIL ===
addEventListener('keydown', (e) => {
  if (ES_ORADOR) return;
  const k = e.key;
  if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(k)) { e.preventDefault(); siguiente(); }
  else if (['ArrowLeft', 'PageUp'].includes(k)) { e.preventDefault(); anterior(); }
  else if (k === 'Home') mostrar(0);
  else if (k === 'End') mostrar(lista.length - 1);
  else if (k === 'f' || k === 'F') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  else if (k === 'n' || k === 'N') document.getElementById('notas').classList.toggle('on');
  else if (k === 'p' || k === 'P') window.open(`${location.pathname}?orador#${idDe(lista[i])}`, 'kuanto-orador', 'width=1200,height=800');
  else if (k === 'a' || k === 'A') modo === 'anexo' ? cambiarModo('normal', 'cierre') : cambiarModo('anexo');
  else if (k === 'Escape' && modo !== 'normal') cambiarModo('normal', 'cierre');
  else if (k === 'l' || k === 'L') document.body.classList.toggle('ligero');
  else if (k === 'w' || k === 'W') window.open(DEMO_URL, '_blank', 'noopener');
});
addEventListener('click', (e) => { if (!ES_ORADOR && !e.target.closest('a,button,video')) (e.clientX > innerWidth / 3 ? siguiente : anterior)(); });
let toqueX = null;
addEventListener('touchstart', (e) => { toqueX = e.touches[0].clientX; }, { passive: true });
addEventListener('touchend', (e) => { if (toqueX === null) return; const d = e.changedTouches[0].clientX - toqueX; if (Math.abs(d) > 50) (d < 0 ? siguiente : anterior)(); toqueX = null; });
if (canal) canal.onmessage = (m) => {
  if (ES_ORADOR) return window.pintarOrador?.(m.data);
  if (m.data.tipo === 'orden') ({ siguiente, anterior })[m.data.orden]?.();
  if (m.data.tipo === 'hola') avisar();
};

// === NOTAS EN PANTALLA (tecla N) ===
function pintarNotas() {
  const n = NOTAS[idDe(lista[i])] || {};
  document.getElementById('notas').textContent = `${lista[i].dataset.quien} · ${idDe(lista[i])} (${i + 1}/${lista.length}, paso ${paso}/${pasosDe(lista[i])}) — ${n.texto || '—'}${n.cue ? ` · Aviso: ${n.cue}` : ''}`;
}

// === ANIMACIONES POR DIAPOSITIVA ===
const entradas = {
  corto(s) { const v = s.querySelector('video'); v.currentTime = 0; v.play().catch(() => {}); v.onended = () => { if (lista[i] === s) siguiente(); }; },
  cifra() { iso(document.getElementById('isoEsfuerzo'), RENDER_ESFUERZO); },
  respuesta(s) { s.querySelector('#mereceFrase').style.opacity = 1; limpiar('particulas'); },
  'lucia-mapa'() { iso(document.getElementById('isoLucia'), RENDER_LUCIA); },
  'c-porque'() { iso(document.getElementById('isoLucia'), RENDER_LUCIA); },
};
const pasos = {
  respuesta(s) { s.querySelector('#mereceFrase').style.opacity = 0; particulas(); },
  'c-apertura'() {
    if (paso === 3) iso(document.getElementById('isoEsfuerzo'), RENDER_ESFUERZO);
  },
};
function entrar(s) {
  generacion++;
  entradas[idDe(s)]?.(s);
  s.querySelectorAll('[data-cuenta]').forEach((el) => contar(el, Number(el.dataset.cuenta), 0, '', 1800));
  if (paso) alPaso(s);
}
function alPaso(s) { pasos[idDe(s)]?.(s); }
function salir(s) { if (idDe(s) === 'corto') s.querySelector('video').pause(); }

function contar(el, fin, dec, sufijo, ms) {
  const g = generacion, t0 = performance.now();
  (function f(t) {
    if (g !== generacion) return;
    const k = Math.min(1, (t - t0) / ms), v = fin * (1 - Math.pow(1 - k, 4));
    el.textContent = v.toLocaleString('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: 'always' }) + sufijo;
    if (k < 1) requestAnimationFrame(f);
  })(t0);
}

// === RENDER ISOMÉTRICO: el mapa de zonas con una columna por zona y una órbita lenta de cámara ===
const POLIGONOS = window.MAPA.zonas.map((z) => z.d.split('Z').filter(Boolean).map((p) => p.replace('M', '').split('L').map((q) => q.split(',').map(Number))));
const mezcla = (a, b, k) => a.map((v, j) => Math.round(v + (b[j] - v) * k));
const RENDER_ESFUERZO = {
  valor: (z) => z.e,
  altura: (v) => v * 1100, // proporcional desde cero
  color: (v) => { const k = Math.min(1, Math.max(0, (v - 0.12) / 0.12)); return k < 0.5 ? mezcla([47, 124, 246], [156, 194, 245], k * 2) : mezcla([156, 194, 245], [255, 107, 107], (k - 0.5) * 2); },
  etiquetas: { '2807901': ['Centro', 120, 120], '28176': ['Villanueva de la Cañada', 140, -190] },
};
const RENDER_LUCIA = {
  valor: (z) => z.s,
  altura: (v) => v * 0.22,
  color: (v) => (v >= 0 ? [61, 220, 151] : [255, 107, 107]),
  etiquetas: { '28065': ['Getafe', 120, 190], '28106': ['Parla', 70, -170], '2807901': ['Centro', 230, -60] },
};
function iso(canvas, cfg) {
  const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, g = generacion;
  const zonas = window.MAPA.zonas, t0 = performance.now();
  const barras = zonas.map((z) => ({ z, v: cfg.valor(z) })).filter((b) => b.v !== null);
  const proy = (x, y, h, th) => {
    const dx = x - 450, dy = y - 450, c = Math.cos(th), s = Math.sin(th);
    return [W / 2 + (dx * c - dy * s) * 1.2, H * 0.52 + (dx * s + dy * c) * 0.62 - h];
  };
  const pintar = (crece, th) => {
    ctx.clearRect(0, 0, W, H);
    POLIGONOS.forEach((polys, k) => {
      ctx.beginPath();
      for (const p of polys) p.forEach(([x, y], j) => { const [X, Y] = proy(x, y, 0, th); if (j) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); });
      ctx.fillStyle = cfg.valor(zonas[k]) === null ? 'rgba(255,255,255,0.025)' : 'rgba(47,124,246,0.08)';
      ctx.strokeStyle = 'rgba(156,194,245,0.22)';
      ctx.lineWidth = 0.8;
      ctx.fill(); ctx.stroke();
    });
    const rotulos = [];
    // Las que no llegan (negativas) se pintan al final para que no las tapen las demás.
    const orden = barras.map((b) => ({ ...b, p: proy(b.z.c[0], b.z.c[1], 0, th) })).sort((a, b) => (a.v < 0) - (b.v < 0) || a.p[1] - b.p[1]);
    for (const b of orden) {
      const k = Math.min(1, Math.max(0, crece * 1.6 - Math.hypot(b.z.c[0] - 450, b.z.c[1] - 450) / 900));
      const h = cfg.altura(b.v) * (1 - Math.pow(1 - k, 3));
      const [r, gg, bl] = cfg.color(b.v), w = b.v < 0 ? 7 : 5;
      const esq = [[-w, -w], [w, -w], [w, w], [-w, w]].map(([a, c]) => [b.z.c[0] + a, b.z.c[1] + c]);
      const base = esq.map(([x, y]) => proy(x, y, 0, th)), techo = esq.map(([x, y]) => proy(x, y, h, th));
      const caras = [0, 1, 2, 3].map((j) => ({ j, y: (base[j][1] + base[(j + 1) % 4][1]) / 2 })).sort((a, c) => a.y - c.y);
      for (const { j } of caras) {
        const n = (j + 1) % 4, luz = j % 2 ? 0.55 : 0.75;
        ctx.beginPath(); ctx.moveTo(...base[j]); ctx.lineTo(...base[n]); ctx.lineTo(...techo[n]); ctx.lineTo(...techo[j]); ctx.closePath();
        ctx.fillStyle = `rgba(${Math.round(r * luz)},${Math.round(gg * luz)},${Math.round(bl * luz)},0.95)`; ctx.fill();
      }
      ctx.beginPath(); techo.forEach((q, j) => (j ? ctx.lineTo(...q) : ctx.moveTo(...q))); ctx.closePath();
      ctx.fillStyle = `rgb(${r},${gg},${bl})`; ctx.shadowColor = `rgba(${r},${gg},${bl},0.8)`; ctx.shadowBlur = 12; ctx.fill(); ctx.shadowBlur = 0;
      if (cfg.etiquetas[b.z.id] && k > 0.9) rotulos.push([cfg.etiquetas[b.z.id], proy(b.z.c[0], b.z.c[1], Math.max(h, 0), th)]);
    }
    for (const [[texto, alto, dx], [X, Y]] of rotulos) {
      ctx.strokeStyle = 'rgba(245,245,247,0.7)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(X, Y - 6); ctx.lineTo(X + dx, Y - alto); ctx.stroke();
      ctx.font = '600 28px "Instrument Sans", sans-serif'; ctx.textAlign = 'center';
      const ancho = ctx.measureText(texto).width + 28;
      ctx.fillStyle = 'rgba(0,0,0,0.85)'; ctx.fillRect(X + dx - ancho / 2, Y - alto - 44, ancho, 42);
      ctx.fillStyle = '#f5f5f7'; ctx.fillText(texto, X + dx, Y - alto - 13);
    }
  };
  if (ESTATICO) { pintar(1, -0.35); return; }
  (function f(t) {
    if (g !== generacion) return;
    const seg = (t - t0) / 1000;
    pintar(Math.min(1, seg / 2.4), -0.35 + 0.22 * Math.sin(seg * 0.22));
    if (!document.body.classList.contains('ligero') || seg < 3) requestAnimationFrame(f);
  })(t0);
}

// === PARTÍCULAS QUE FORMAN LA COMUNIDAD ===
function limpiar(id) { const c = document.getElementById(id); c.getContext('2d').clearRect(0, 0, c.width, c.height); }
function particulas() {
  const c = document.getElementById('particulas'), ctx = c.getContext('2d'), g = generacion;
  const P = window.MAPA.puntos.map(([x, y]) => ({ x: 960 + (Math.random() - 0.5) * 2400, y: 540 + (Math.random() - 0.5) * 1400, tx: 510 + x, ty: 90 + y, d: Math.random() * 700 }));
  const t0 = performance.now();
  (function f(t) {
    if (g !== generacion) return;
    ctx.clearRect(0, 0, 1920, 1080);
    ctx.fillStyle = '#9cc2f5';
    const fin = (t - t0) / 1000;
    for (const p of P) {
      const k = Math.min(1, Math.max(0, (t - t0 - p.d) / 1600)), e = 1 - Math.pow(1 - k, 4);
      ctx.globalAlpha = (0.15 + 0.6 * e) * (fin > 2.2 ? Math.max(0.2, 1 - (fin - 2.2) * 0.8) : 1);
      ctx.beginPath(); ctx.arc(p.x + (p.tx - p.x) * e, p.y + (p.ty - p.y) * e, 2.4, 0, 7); ctx.fill();
    }
    if (fin < 4) requestAnimationFrame(f);
  })(t0);
}

// === TIMELINE: días, PR fusionados por día (gh pr list) y fases según los PR y docs/decisiones.md ===
const PR_DIA = [5, 7, 20, 24, 23, 28, 10, 19, 20, 31, 9, 10, 18, 19, 16];
// Líneas de trabajo (fechas de los PR de cada responsable) y nueve hitos (PR que los cierran).
const LINEAS = [
  { ini: 11, fin: 25, t: 'Gobierno, datos y euros', q: 'Yeray', c: '#9cc2f5' },
  { ini: 11, fin: 25, t: 'Territorio, tiempos, web y MCP', q: 'Izan', c: '#2f7cf6' },
  { ini: 22, fin: 25, t: 'Diseño y marca', q: 'Alex', c: '#ffd27a' },
  { ini: 12, fin: 26, t: 'Calidad automatizada', q: 'agentes', c: '#3ddc97' },
];
const PUERTAS = [
  [13, 'G1', 'Reglas y CI'], [14, 'G2', 'Contratos de datos'], [15, 'G3', 'API estática v1'],
  [17, 'G4', 'Cálculo validado'], [19, 'G5', 'MCP'], [21, 'G6', 'Datos congelados I'],
  [23, 'G7', 'Datos congelados II'], [25, 'G8', 'Informe técnico'], [26, 'G9', 'Jurado'],
];
function construirTimeline() {
  const caja = document.getElementById('lineaTiempo');
  if (!caja || caja.querySelector('.linea')) return;
  const x = (d) => ((d - 11) / 15) * 1600, retardo = (d) => `${0.4 + ((d - 11) / 15) * 3.2}s`;
  const dias = document.getElementById('dias'), prs = document.getElementById('prs');
  for (let d = 11; d <= 26; d++) {
    const s = document.createElement('span');
    s.style.left = `${x(d)}px`;
    s.textContent = d === 11 ? '11 nov' : d === 26 ? '26 nov' : String(d);
    dias.appendChild(s);
  }
  PR_DIA.forEach((n, k) => {
    const b = document.createElement('i');
    b.dataset.n = n;
    b.style.left = `${x(11 + k)}px`;
    b.style.setProperty('--h', `${(n / 31) * 110}px`);
    b.style.setProperty('--d', retardo(11 + k));
    prs.appendChild(b);
  });
  LINEAS.forEach((l, k) => {
    const el = document.createElement('div');
    el.className = 'linea';
    Object.assign(el.style, { left: `${x(l.ini)}px`, top: `${10 + k * 68}px`, width: `${x(l.fin) - x(l.ini)}px` });
    el.style.setProperty('--d', `${0.3 + k * 0.25}s`);
    el.style.setProperty('--c', l.c);
    const t = document.createElement('b'); t.textContent = `${l.t} `;
    const q = document.createElement('span'); q.textContent = `· ${l.q}`;
    t.appendChild(q);
    el.append(t, document.createElement('i'));
    caja.appendChild(el);
  });
  PUERTAS.forEach(([d, g, texto], k) => {
    const p = document.createElement('div');
    p.className = 'puerta';
    Object.assign(p.style, { left: `${x(d)}px`, top: `${k % 2 ? 418 : 380}px` });
    p.style.setProperty('--d', retardo(d));
    const e = document.createElement('em'); e.textContent = g;
    p.append(e, texto);
    caja.appendChild(p);
    const h = document.createElement('div');
    h.className = 'hito';
    h.style.left = `${x(d)}px`;
    h.style.setProperty('--d', retardo(d));
    caja.appendChild(h);
  });
}

// === ARQUITECTURA: conectores con datos que fluyen ===
function construirTuberia() {
  const svg = document.getElementById('tuberiaSvg');
  if (!svg || svg.childElementCount) return;
  const ns = 'http://www.w3.org/2000/svg';
  const rutas = [[280, 320, 340, 320], [620, 320, 680, 320], [960, 320, 1020, 320], ...[0, 132, 264, 396, 528].map((y) => [1300, 320, 1360, y + 50])];
  rutas.forEach(([x1, y1, x2, y2], k) => {
    const d = `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`;
    const p = document.createElementNS(ns, 'path');
    p.setAttribute('d', d); p.setAttribute('class', 'conector');
    svg.appendChild(p);
    for (let j = 0; j < 3; j++) {
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('r', '5'); c.setAttribute('class', 'gota');
      const m = document.createElementNS(ns, 'animateMotion');
      m.setAttribute('dur', '1.8s'); m.setAttribute('repeatCount', 'indefinite'); m.setAttribute('path', d);
      m.setAttribute('begin', `${(k * 0.25 + j * 0.6).toFixed(2)}s`);
      c.appendChild(m);
      svg.appendChild(c);
    }
  });
}

// === SALA DE MÁQUINAS: el bucle de cada cambio ===
const BUCLE = ['Issue', 'Worktree', 'Skill del área', 'Hooks y tests', 'Commit', 'Revisor', 'Pull request', 'CI y merge'];
function construirBucle() {
  const svg = document.getElementById('bucle');
  if (!svg || svg.childElementCount) return;
  const cx = 410, cy = 360, r = 250, ns = 'http://www.w3.org/2000/svg';
  for (const [cls, largo] of [['arco', ''], ['vivo', '2000']]) {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('class', cls); c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', r);
    if (largo) c.setAttribute('pathLength', largo);
    svg.appendChild(c);
  }
  BUCLE.forEach((t, k) => {
    const a = -Math.PI / 2 + (k / BUCLE.length) * 2 * Math.PI, x = cx + r * Math.cos(a), y = cy + r * Math.sin(a), c = Math.cos(a);
    const gr = document.createElementNS(ns, 'g'); gr.setAttribute('class', 'paso');
    const p = document.createElementNS(ns, 'circle'); p.setAttribute('cx', x); p.setAttribute('cy', y); p.setAttribute('r', 16);
    const tx = document.createElementNS(ns, 'text');
    tx.setAttribute('x', x + c * 30); tx.setAttribute('y', y + Math.sin(a) * 34 + 8);
    tx.style.textAnchor = c > 0.3 ? 'start' : c < -0.3 ? 'end' : 'middle';
    tx.textContent = t;
    gr.append(p, tx);
    svg.appendChild(gr);
  });
  const t1 = document.createElementNS(ns, 'text');
  t1.setAttribute('x', cx); t1.setAttribute('y', cy); t1.style.cssText = 'fill:#f5f5f7;font:600 44px "Instrument Sans";text-anchor:middle';
  t1.textContent = 'Un cambio';
  const t2 = document.createElementNS(ns, 'text');
  t2.setAttribute('x', cx); t2.setAttribute('y', cy + 44); t2.style.cssText = 'fill:#a3aab6;font:400 24px "Instrument Sans";text-anchor:middle';
  t2.textContent = 'de la idea al merge';
  svg.append(t1, t2);
}

// === MODO ORADOR (tecla P): ventana aparte con guion, siguiente y relojes por bloque ===
function iniciarOrador() {
  document.querySelector('.deck-viewport').style.display = 'none';
  document.getElementById('progreso').style.display = 'none';
  const plan = {};
  todas.filter((s) => !s.classList.contains('oculta')).forEach((s) => { const q = s.dataset.quien; plan[q] = (plan[q] || 0) + (NOTAS[idDe(s)]?.s || 0); });
  document.body.style.cssText = 'overflow:auto;background:#000;color:#f5f5f7;font:400 22px/1.5 "Instrument Sans",sans-serif;padding:28px 40px';
  const crear = (css) => { const d = document.createElement('div'); d.style.cssText = css; document.body.appendChild(d); return d; };
  const total = crear('font:600 64px "Instrument Sans"');
  const bloque = crear('font:600 28px "Instrument Sans";margin:14px 0 4px');
  const tit = crear('font:600 36px "Instrument Sans";margin:6px 0;color:#9cc2f5');
  const texto = crear('font:400 34px/1.45 "Instrument Sans";max-width:1500px;margin:12px 0');
  const cue = crear('color:#ffd27a;font-size:24px;margin:10px 0');
  const sig = crear('color:#a3aab6;font-size:24px;margin-top:22px;border-top:1px solid #23272f;padding-top:14px');
  crear('color:#6e7480;font-size:18px;margin-top:20px').textContent = 'Flechas: avanzar y retroceder en la presentación · R: reiniciar relojes';
  let t0 = Date.now(), quien = null, tb = Date.now(), previsto = 0;
  const mmss = (s) => `${s < 0 ? '−' : ''}${Math.floor(Math.abs(s) / 60)}:${String(Math.floor(Math.abs(s)) % 60).padStart(2, '0')}`;
  window.pintarOrador = (d) => {
    if (d.tipo !== 'estado') return;
    const s = todas.find((x) => idDe(x) === d.id), q = s.dataset.quien, n = NOTAS[d.id] || {};
    if (q !== quien) { quien = q; tb = Date.now(); }
    previsto = plan[q] || 0;
    const siguienteS = todas.slice(todas.indexOf(s) + 1).find((x) => !x.classList.contains('oculta'));
    tit.textContent = `${d.i + 1}/${d.total} · ${d.id}${pasosDe(s) ? ` · paso ${d.paso}/${pasosDe(s)}` : ''}`;
    texto.textContent = n.texto || '—';
    cue.textContent = n.cue || '';
    sig.textContent = siguienteS ? `Siguiente: ${siguienteS.dataset.id} (${siguienteS.dataset.quien})` : 'Fin';
  };
  setInterval(() => {
    total.textContent = `${mmss((Date.now() - t0) / 1000)} de 9:00`;
    if (!quien) return;
    const pasado = (Date.now() - tb) / 1000, resta = previsto - pasado;
    bloque.textContent = `${quien}: ${mmss(pasado)} de ${mmss(previsto)} · ${resta >= 0 ? `quedan ${mmss(resta)}` : `te pasas ${mmss(-resta)}`}`;
    bloque.style.color = resta < 0 ? '#ff6b6b' : resta < 15 ? '#ffd27a' : '#3ddc97';
  }, 250);
  addEventListener('keydown', (e) => {
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) canal?.postMessage({ tipo: 'orden', orden: 'siguiente' });
    if (['ArrowLeft', 'PageUp'].includes(e.key)) canal?.postMessage({ tipo: 'orden', orden: 'anterior' });
    if (e.key === 'r' || e.key === 'R') { t0 = Date.now(); tb = Date.now(); }
  });
  canal?.postMessage({ tipo: 'hola' });
}

// === ARRANQUE ===
// Se construyen antes de mostrarse para que sus transiciones se vean al entrar.
construirTimeline(); construirTuberia(); construirBucle();
if (ESTATICO) {
  // La exportación (navegador automatizado) recibe el estado final de cada diapositiva; ?animado lo evita.
  document.body.classList.add('estatico');
  iso(document.getElementById('isoEsfuerzo'), RENDER_ESFUERZO);
  iso(document.getElementById('isoLucia'), RENDER_LUCIA);
}
// La exportación ve la cinta en su último tramo.
if (ESTATICO) document.querySelectorAll('.slide').forEach((x) => { if (x.querySelector('.carril')) { x.querySelector('.carril').style.transition = 'none'; moverCarril(x, pasosDe(x)); } });
if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.body.classList.add('ligero');
  document.querySelectorAll('svg').forEach((s) => s.pauseAnimations());
}
if (ES_ORADOR) iniciarOrador();
else {
  addEventListener('resize', encajar);
  encajar();
  const desdeUrl = location.hash.slice(1);
  if (desdeUrl.startsWith('anexo')) { modo = 'anexo'; lista = recorrido(); }
  const k = lista.findIndex((s) => idDe(s) === desdeUrl);
  document.fonts.ready.then(() => mostrar(k >= 0 ? k : 0));
}
