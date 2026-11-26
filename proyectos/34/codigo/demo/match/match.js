/* Dónde cabes: mapa que se va cerrando. Plain JS + MapLibre GL JS 5.24.1 (BSD-3-Clause).
   Idea of side panel, bottom sheet and short camera flights taken from Oasis-Madrid
   (github.com/ariaslombardero/Oasis-Madrid, Apache-2.0); no code copied.
   Nothing typed here leaves the page: no requests, no storage. */
(() => {
  const D = JSON.parse(document.getElementById('match-data').textContent);
  const M = D.municipalities, BY = Object.fromEntries(M.map(m => [m.ine, m]));
  const FID = {};
  D.outlines.features.forEach(f => { if (f.properties.ine) FID[f.properties.ine] = f.id; });
  const $ = id => document.getElementById(id), root = () => $('match');
  const NF = new Intl.NumberFormat('es-ES', { useGrouping: 'always', maximumFractionDigits: 2 }), nf = n => NF.format(n); // 1.301, not 1301
  const eur = n => new Intl.NumberFormat('es-ES', { useGrouping: 'always', maximumFractionDigits: 1 }).format(n) + ' €'; // data values as they come (rent can have one decimal)
  const eurDown = n => nf(Math.floor(n + 1e-9)) + ' €'; // cap and what is left: rounded down, as in the rest of the app
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const narrow = matchMedia('(max-width: 760px)');
  const hasLayer = k => D.layers.includes(k);

  // What each countable thing is called: [one, many]
  const THING = {
    health_centres: ['centro de salud o consultorio', 'centros de salud o consultorios', 'salud'],
    pharmacies: ['farmacia', 'farmacias', 'farmacia'],
    schools: ['colegio o instituto', 'colegios e institutos', 'colegios'],
    sports: ['instalación deportiva', 'instalaciones deportivas', 'deporte'],
    cultural: ['equipamiento cultural', 'equipamientos culturales', 'cultura'],
    parks: ['parque', 'parques', 'parques'],
    bus_stops: ['parada de bus interurbano', 'paradas de bus interurbano', 'bus interurbano'],
    metro_stations: ['estación de metro', 'estaciones de metro', 'metro'],
    rail_stations: ['estación de Cercanías', 'estaciones de Cercanías', 'Cercanías'],
    light_rail_stops: ['parada de metro ligero', 'paradas de metro ligero', 'metro ligero'],
    vets: ['centro veterinario', 'centros veterinarios', 'veterinario'],
    worship: ['lugar de culto', 'lugares de culto', 'lugares de culto'],
    dog_areas: ['zona canina (para perros)', 'zonas caninas (para perros)', 'zona canina'],
  };
  const TRANSPORT = ['metro_stations', 'rail_stations', 'light_rail_stops', 'bus_stops'];
  const SERVICES = ['health_centres', 'pharmacies', 'sports', 'cultural', 'parks', ...(hasLayer('worship') ? ['worship'] : [])];
  const DOG = ['parks', ...['dog_areas', 'vets'].filter(hasLayer)]; // pet: shown in «why»; the rule uses parks or dog areas

  // ---------- state ----------
  let S, history = [], opener = null, onClose = null;
  const fresh = o => ({
    annual: o.annual, share: o.share, earners: o.earners === 2 ? 2 : 1, capOverride: null,
    people: o.earners === 2 ? 2 : 1, size: 3, roomNotice: false, kids: false, school: false, room: false, dog: false,
    transport: [], services: [], work: null, showFinal: true,
  });
  const cap = s => s.capOverride ?? s.annual * s.share * s.earners / 1200;

  // requirement list: [label, key, test(m) -> true | false | null]
  const count = (m, k) => m.around[k] === undefined ? undefined : m.around[k];
  function reqs(s) {
    const r = [['tu tope de alquiler', 'rent', m => m.rent ? m.rent.value * 1200 <= (s.capOverride != null
      ? s.capOverride * 1200 : s.annual * s.share * s.earners) : null]];
    const has = k => m => { const v = count(m, k); return v == null ? (v === undefined ? true : null) : v > 0; };
    if (s.kids) r.push(['peques de 0 a 4', 'kids', m => (m.nurseries > 0 || m.private_early > 0) ? true
      : (m.nurseries == null || m.private_early == null) ? null : false]);
    if (s.school) r.push(['edad escolar', 'schools', has('schools')]);
    // dog: a park or a dog area. dog_areas/vets are never 0 (OpenStreetMap: missing is not none), so this can only be yes or unknown
    if (s.dog) r.push(['mascota: parque o zona canina', 'dog', m => (m.around.parks > 0 || m.around.dog_areas > 0) ? true : null]);
    (s.transport || []).forEach(k => r.push([THING[k][2], k, has(k)]));
    (s.services || []).forEach(k => r.push([THING[k][2], k, has(k)]));
    return r;
  }
  function evaluate(s) {
    const R = reqs(s), out = { in: [], unknown: [], out: [], why: new Map() };
    for (const m of M) {
      let fail = null; const miss = [];
      for (const [label, , t] of R) { const v = t(m); if (v === false) { fail = label; break; } if (v === null) miss.push(label); }
      if (fail) { out.out.push(m); out.why.set(m.ine, fail); } else if (miss.length) out.unknown.push([m, miss]); else out.in.push(m);
    }
    const w = s.work && BY[s.work];
    out.in.sort(w ? (a, b) => km(a, w) - km(b, w) : (a, b) => a.rent.value - b.rent.value);
    return out;
  }
  function km(a, b) {
    if (!a.centre || !b.centre) return Infinity;
    const r = Math.PI / 180, [x1, y1] = a.centre, [x2, y2] = b.centre;
    const h = Math.sin((y2 - y1) * r / 2) ** 2 + Math.cos(y1 * r) * Math.cos(y2 * r) * Math.sin((x2 - x1) * r / 2) ** 2;
    return 12742 * Math.asin(Math.sqrt(h));
  }

  // ---------- dashboard UI (encargo mapa-dashboard): filters left, map centre, results right ----------
  const P = d => `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="${d}"/></svg>`;
  const ICON = {
    kids: P('M7 18a2 2 0 1 0 4 0a2 2 0 1 0-4 0M15 18a2 2 0 1 0 4 0a2 2 0 1 0-4 0M4 5h2l2 8h11l2-6H8'),
    school: P('M3 9l9-5l9 5l-9 5zM7 11.5V16c0 1.5 2.5 3 5 3s5-1.5 5-3v-4.5'),
    room: P('M4 20V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v15M15 20h5M11 12h.01M2 20h2'),
    dog: P('M8 8.5a1.5 1.5 0 1 0 0-.01M16 8.5a1.5 1.5 0 1 0 0-.01M5 13a1.5 1.5 0 1 0 0-.01M19 13a1.5 1.5 0 1 0 0-.01M12 13c-2.5 0-4.5 2.5-4.5 4.5c0 1.5 1.5 2 2.5 1.6c1.3-.5 2.7-.5 4 0c1 .4 2.5-.1 2.5-1.6c0-2-2-4.5-4.5-4.5'),
    metro_stations: P('M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M8 16V8l4 5l4-5v8'),
    rail_stations: P('M7 3h10a2 2 0 0 1 2 2v9a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V5a2 2 0 0 1 2-2zM5 10h14M8 21l2-4M16 21l-2-4M9 14h.01M15 14h.01'),
    light_rail_stops: P('M8 3h8M12 3v3M7 6h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2zM5 12h14M8 21l1.5-4M16 21l-1.5-4'),
    bus_stops: P('M6 3h12a2 2 0 0 1 2 2v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a2 2 0 0 1 2-2zM4 11h16M7 20v-3M17 20v-3M8 14h.01M16 14h.01'),
    health_centres: P('M9 3h6v6h6v6h-6v6H9v-6H3V9h6z'),
    pharmacies: P('M10.5 4.5a5 5 0 0 1 7 7l-6 6a5 5 0 0 1-7-7zM8 9l7 7'),
    sports: P('M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M3.5 9.5c5 1 12 1 17 0M3.5 14.5c5-1 12-1 17 0M12 3c-3 4-3 14 0 18M12 3c3 4 3 14 0 18'),
    cultural: P('M3 21h18M5 21v-9M10 21v-9M14 21v-9M19 21v-9M3 10l9-6l9 6z'),
    parks: P('M12 21v-6M12 3c-3.5 0-6 2.8-6 6c0 3 2.5 6 6 6s6-3 6-6c0-3.2-2.5-6-6-6z'),
    worship: P('M4 21V11l8-6l8 6v10M4 21h16M10 21v-5a2 2 0 0 1 4 0v5'),
    tick: P('M5 12.5l4.5 4.5L19 7.5'),
    vets: P('M12 21c-4-3-7-6-7-9.5A3.5 3.5 0 0 1 12 9a3.5 3.5 0 0 1 7 2.5c0 3.5-3 6.5-7 9.5zM12 12v4M10 14h4'),
  };
  ICON.schools = ICON.school; ICON.dog_areas = ICON.dog;
  // One colour per layer (entender.md): the same in filter rows, chips, list, legend and map dots, always with its name.
  const COLOR = { health_centres: '#ff6b6b', pharmacies: '#30d158', schools: '#64d2ff', sports: '#ff9f0a', cultural: '#bf8cff', parks: '#a3e635',
    metro_stations: '#0a84ff', rail_stations: '#ff9fb2', light_rail_stops: '#7d7aff', bus_stops: '#5fe0d6', dog_areas: '#d4a373', vets: '#f4a6ff', worship: '#d1d1d6',
    kids: '#ffb86b', school: '#64d2ff', room: '#c3d0d9', dog: '#d4a373' };
  for (const k in COLOR) COLOR[k] = '#dfe7ec'; // design report: glyphs tell layers apart; yellow only for «on» and «fits»
  const LABEL = { kids: 'Peques 0 a 4', school: 'Edad escolar', room: 'Habitación', dog: 'Mascota',
    metro_stations: 'Metro', rail_stations: 'Cercanías', light_rail_stops: 'Metro ligero', bus_stops: 'Bus',
    health_centres: 'Salud', pharmacies: 'Farmacia', sports: 'Deporte', cultural: 'Cultura', parks: 'Parques', worship: 'Lugares de culto' };
  const CHIP = { schools: 'school', dog_areas: 'dog', vets: 'health_centres' }, CHIPL = { schools: 'Colegios', dog_areas: 'Zonas caninas', vets: 'Veterinarios', bus_stops: 'Bus', light_rail_stops: 'M. ligero' };
  const on = (s, f) => f === 'kids' || f === 'school' || f === 'room' || f === 'dog' ? !!s[f]
    : TRANSPORT.includes(f) ? s.transport.includes(f) : s.services.includes(f);
  // iOS grouped rows: coloured icon, name, how many municipalities have it (and how many lack data), clear switch.
  const KEY = { kids: null, school: 'schools', room: null, dog: 'parks' };
  const TINT = f => ['kids', 'school', 'room', 'dog'].includes(f) ? 'h' : TRANSPORT.includes(f) ? 't' : 'c';
  function rowCount(f) {
    if (f === 'room') return 'sin precio de habitación';
    if (f === 'kids') return M.filter(m => m.nurseries > 0 || m.private_early > 0).length;
    if (f === 'dog') return M.filter(m => m.around.parks > 0 || m.around.dog_areas > 0).length;
    const k = KEY[f] || f;
    return M.filter(m => m.around[k] > 0).length; // municipalities with at least one; those without the figure go to «sin dato»
  }
  const tile = f => `<button type="button" class="mt-tile" data-f="${f}" aria-pressed="false"><i class="mt-ico" style="background:${COLOR[f]}">${ICON[f]}${ICON.tick}</i><span><b>${LABEL[f]}</b></span><em title="Municipios con al menos uno">${rowCount(f)}</em></button>`;
  const SEGL = { people: 'Personas que van a vivir', dwelling: 'Piso o habitación', earners: 'Sueldos que entran' };
  const segBtns = (k, opts) => `<div class="mt-seg" role="group" aria-label="${SEGL[k]}"><span class="mt-pill" aria-hidden="true"></span>${opts.map(([v, l]) => `<button type="button" class="mt-opt" data-k="${k}" data-v="${v}" aria-pressed="false">${l}</button>`).join('')}</div>`;
  const ROOM = 'Sin precio de habitaciones: el mapa compara con el alquiler de una vivienda entera y el recuento no cambia. <a href="https://www.idealista.com/alquiler-habitacion/madrid-provincia/" target="_blank" rel="noopener">Precios de habitación en idealista</a>.';
  const cover = k => M.filter(m => m.around[k] != null).length;
  const PET = () => `Se queda si tiene un parque o una zona canina. Las zonas caninas son para perros; los parques no garantizan que admitan animales (${D.definitions.parks_for_dogs || 'no consta'}). Hay dato de parques en ${cover('parks')} municipios${hasLayer('dog_areas') ? `, de zonas caninas en ${cover('dog_areas')} y de centros veterinarios en ${cover('vets')} (listas incompletas: el número es un mínimo)` : ''}.`;
  const CAP_MIN = 200, CAP_MAX = 2500;

  function buildFilters() {
    const services = [...SERVICES];
    $('mt-filters').innerHTML = `
      <fieldset><legend>Hogar</legend>
        <p class="mt-q">Personas que van a vivir</p>
        ${segBtns('people', [['1', '1'], ['2', '2'], ['3', '3'], ['4', '4 o más']])}
        <div class="mt-two">${segBtns('dwelling', [['piso', 'Piso'], ['habitacion', 'Habitación']])}${segBtns('earners', [['1', '1 sueldo'], ['2', '2 sueldos']])}</div>
        <p class="mt-note" id="mt-room-lock" hidden>Con tres o más personas, solo piso.</p>
        <p class="mt-note mt-warn2" id="mt-room-moved" hidden role="status">Con tres o más personas solo hay piso: lo hemos cambiado a piso.</p>
        <p class="mt-note" id="mt-note-room" hidden>${ROOM}</p>
        <div class="mt-grid">${['kids', 'school', 'dog'].map(tile).join('')}</div>
        <p class="mt-note" id="mt-note-dog" hidden>Zonas caninas: para perros. Parques: no consta si admiten animales.</p>
        <label class="mt-slider"><span>Tope</span><input type="range" id="mt-cap" min="${CAP_MIN}" max="${CAP_MAX}" step="10" aria-label="Tope de alquiler en euros al mes"><output id="mt-cap-out"></output></label>
      </fieldset>
      <fieldset><legend>Transporte <small>· municipios con al menos uno</small></legend><div class="mt-grid">${TRANSPORT.map(tile).join('')}</div></fieldset>
      <fieldset><legend>Cerca, en el municipio</legend><div class="mt-grid">${services.map(tile).join('')}</div>
        ${hasLayer('worship') && D.definitions.worship ? `<p class="mt-note" id="mt-note-worship" hidden>${D.definitions.worship} Esta respuesta no sale de la página.</p>` : ''}</fieldset>
      <fieldset><legend>Trabajo o estudios</legend>
        <label class="mt-field"><span class="mt-sr">Municipio donde trabajas o estudias (ordena por línea recta, no por tiempo de viaje)</span><select id="mt-work"><option value="">Sin decir</option>${[...M].sort((a, b) => a.name.localeCompare(b.name, 'es')).map(m => `<option value="${m.ine}">${m.name}</option>`).join('')}</select></label>
      </fieldset>`;
  }
  function syncFilters() {
    const f = $('mt-filters');
    f.querySelectorAll('[data-f]').forEach(b => b.setAttribute('aria-pressed', String(on(S, b.dataset.f))));
    f.querySelectorAll('[data-k=people]').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.v === S.people)));
    f.querySelectorAll('[data-k=dwelling]').forEach(b => { const room = b.dataset.v === 'habitacion'; b.setAttribute('aria-pressed', String(room === !!S.room)); if (room) { b.disabled = S.people >= 3; b.title = b.disabled ? 'Con tres o más personas, solo piso' : ''; } });
    $('mt-room-lock').hidden = S.people < 3; $('mt-room-moved').hidden = !S.roomNotice;
    f.querySelectorAll('[data-k=earners]').forEach(b => { b.setAttribute('aria-pressed', String(+b.dataset.v === S.earners)); b.disabled = S.people === 1 && b.dataset.v === '2'; });
    const c = Math.floor(cap(S) + 1e-9), r = $('mt-cap');
    r.value = Math.min(CAP_MAX, Math.max(CAP_MIN, c)); r.setAttribute('aria-valuetext', c + ' euros al mes');
    r.style.setProperty('--fill', ((r.value - CAP_MIN) / (CAP_MAX - CAP_MIN) * 100) + '%');
    $('mt-cap-out').textContent = eurDown(cap(S));
    $('mt-work').value = S.work || '';
    $('mt-note-room').hidden = !S.room; $('mt-note-dog').hidden = !S.dog;
    if ($('mt-note-worship')) $('mt-note-worship').hidden = !S.services.includes('worship');
    placePills();
  }
  function movePill(sg, btn, animate) {
    const pill = sg.querySelector('.mt-pill'); if (!pill) return;
    sg.querySelectorAll('.mt-opt').forEach(o => o.classList.toggle('is-on', o === btn));
    if (!btn || !btn.offsetWidth) { pill.style.opacity = 0; return; }
    const to = { transform: `translateX(${btn.offsetLeft - 3}px)`, width: btn.offsetWidth + 'px', opacity: 1 };
    if (animate && window.Motion && !reduced.matches && pill.style.opacity === '1') Motion.animate(pill, to, { type: 'spring', bounce: 0, duration: 0.32 });
    else Object.assign(pill.style, to);
  }
  const placePills = () => document.querySelectorAll('#mt-filters .mt-seg').forEach(sg => movePill(sg, sg.querySelector('[aria-pressed=true]'), false));

  let shown = 0, roll = null;
  function rollTo(el, n) {
    if (roll) roll.stop();
    if (!window.Motion || reduced.matches || shown === n) { shown = n; el.textContent = n; return; }
    roll = Motion.animate(shown, n, { type: 'spring', bounce: 0, duration: 0.4, onUpdate: v => { shown = Math.round(v); el.textContent = shown; } });
  }
  function render(moved) {
    const r = evaluate(S);
    syncFilters();
    $('mt-undo').disabled = !history.length;
    const low = r.in.length ? r.in.reduce((a, m) => m.rent.value < a.rent.value ? m : a) : null;
    $('mt-stats').innerHTML = `
      <div class="mt-stat is-main"><b id="mt-n">${shown}</b><span>de ${M.length} municipios cumplen</span></div>
      <div class="mt-stat"><b>${eurDown(cap(S))}</b><span>tu tope al mes</span></div>
      <div class="mt-stat"><b>${low ? eur(low.rent.value) : '—'}</b><span>${low ? 'alquiler mediano más bajo: ' + low.name : 'ninguno cumple'}</span></div>
      <button type="button" class="mt-stat mt-stat-btn" id="mt-unk-btn"><b>${r.unknown.length}</b><span><i class="mt-sw mt-sw-unk"></i>municipios sin los datos que pides: ver cuáles</span></button>`;
    rollTo($('mt-n'), r.in.length);
    renderResult(r); renderDrops(r);
    $('mt-result').insertAdjacentHTML('beforeend', insideMadrid(r));
    if (!hasGL || !window.maplibregl || mapFailed) noMap(r);
    paint(r);
    if (moved) frame(r);
  }

  function renderResult(r) {
    const box = $('mt-result'), c = cap(S);
    if (!r.in.length) {
      // a design state, not a hole: say what to change, with the number it brings back
      const low = M.filter(m => m.rent).reduce((a, m) => m.rent.value < a.rent.value ? m : a);
      // cambio4: blame the budget ONLY when the numbers prove it (dropping it brings matches, dropping any other does not)
      const d = dropCounts(r), rentGain = (d.find(x => x[2] === 'rent') || [0, 0])[1];
      const others = d.filter(x => x[2] !== 'rent'), best = others.find(x => x[1] > 0);
      const budget = rentGain > 0 && !best, raise = Math.ceil(low.rent.value);
      const unk = r.unknown.map(([m]) => m.name), shown = unk.slice(0, 6).join(', ') + (unk.length > 6 ? ` y ${unk.length - 6} más` : '');
      box.innerHTML = `<h3>Tres opciones para empezar a explorar</h3><div class="mt-empty" id="mt-diag"><p><b>No hay coincidencias confirmadas.</b></p>
        ${unk.length ? `<p>${unk.length === 1 ? 'Un candidato tiene' : `${nf(unk.length)} candidatos tienen`} información incompleta: ${shown}. Podrían cumplir; falta el dato.</p>` : ''}
        ${budget ? `<p>El presupuesto es insuficiente: ningún alquiler mediano cabe en ${eurDown(c)}. El más bajo es ${eur(low.rent.value)}, en ${low.name}.</p><button type="button" class="mt-btn mt-btn-on" data-cap="${raise}">Subir el límite a ${eurDown(raise)}</button>`
          : best ? `<p>Esta combinación de requisitos deja fuera las opciones conocidas. Sin «${best[0]}» cumplirían ${nf(best[1])}.</p><button type="button" class="mt-btn mt-btn-on" data-drop="${best[2]}">Quitar «${best[0]}»</button>`
          : `<p>Esta combinación de requisitos deja fuera las opciones conocidas. Quitar un solo requisito no basta: quita dos o más.</p>`}</div>`;
      return;
    }
    const keys = [...new Set([...(S.school ? ['schools'] : []), ...(S.dog ? DOG : []), ...S.transport, ...S.services])];
    box.innerHTML = `<h3>Tus mejores municipios</h3>
      ${S.room ? `<p class="mt-warn2">El mapa compara con el alquiler de una vivienda entera. Para precios de habitación, mira <a href="https://www.idealista.com/alquiler-habitacion/madrid-provincia/" target="_blank" rel="noopener">idealista</a>. Elegir habitación no cambia el recuento.</p>` : ''}
      <p class="mt-note">El número de personas no cambia el precio: no hay alquiler por tamaño de vivienda.</p>
      <p class="mt-note">${S.work ? 'Por distancia en línea recta a ' + BY[S.work].name : 'Por alquiler, de menos a más'}. Los recuentos no ordenan. Madrid capital cuenta entera.</p>
      <ol class="mt-cards">${r.in.slice(0, 3).map((m, i) => {
        const pct = Math.min(100, m.rent.value / c * 100), w = S.work && BY[S.work];
        return `<li class="mt-card">
          <button type="button" class="mt-pick" data-fly="${m.ine}"><i>${i + 1}</i><span>${m.name}</span></button>
          <p class="mt-say">En ${m.name}, el alquiler típico es <b>${eur(m.rent.value)} al mes</b>${m.rent.type === 'detached' ? ' (casas, no pisos)' : ''}. Con tu tope de ${eurDown(c)} cabe y sobran ${eurDown(c - m.rent.value)}.</p>
          <div class="mt-bar" role="img" aria-label="Alquiler típico ${eur(m.rent.value)} frente a un tope de ${eurDown(c)}"><span style="width:${pct}%"></span></div>
          ${w ? `<p class="mt-dist">${w === m ? 'Es donde trabajas o estudias' : km(m, w).toFixed(0) + ' km en línea recta a ' + w.name}</p>` : ''}
          ${keys.length ? `<ul class="mt-chips">${keys.filter(k => m.around[k] != null).map(k => `<li title="${THING[k][1]}"><i class="mt-ico mt-ico-s" style="background:${COLOR[k]}">${ICON[k]}</i><span>${CHIPL[k] || LABEL[k]}</span><b>${(k === 'dog_areas' || k === 'vets') ? '≥' : ''}${nf(m.around[k])}</b></li>`).join('')}</ul>` : ''}
          ${figures(m)}
          ${placesList(m, keys)}
          <p class="mt-unit">Mediana de 2024 por vivienda completa, de lo declarado en el IRPF. No es el precio de los anuncios de hoy.</p>
          <details><summary>Cómo se calcula</summary><ul>${why(m, S).map(t => `<li>${t}</li>`).join('')}<li>«Alquiler típico» es la mediana de 2024 del Ministerio de Vivienda. ${D.sources['alquiler-mivau'].note || ''}</li></ul></details>
        </li>`; }).join('')}</ol>`;
    if (moved_ && window.Motion && !reduced.matches) Motion.animate('#mt-result .mt-card', { opacity: [0, 1], transform: ['translateX(16px)', 'none'] }, { type: 'spring', bounce: 0, duration: 0.35, delay: Motion.stagger(0.05) });
  }
  let moved_ = false;
  // extra.json figures: shown with their year, never used to rank or discard
  const XDEF = D.extra_definitions || {};
  function figures(m) {
    const x = m.extra || {}, f = [];
    if ('unemployment' in x || XDEF.unemployment) f.push(['Paro registrado', x.unemployment ? `${nf(x.unemployment.value)} por 100 hab. (${x.unemployment.year})` : `No existe este dato para ${m.name}`, XDEF.unemployment]);
    if ('income' in x || XDEF.income) f.push(['Renta por habitante', x.income ? `${nf(x.income.value)} € al año (${x.income.year})` : `No existe este dato para ${m.name}`, XDEF.income]);
    if ('commute' in x) f.push(['Tiempo al trabajo', x.commute ? `${nf(x.commute.value)} ${x.commute.unit === 'minutes' ? 'min' : x.commute.unit} (${x.commute.year})` : `No existe este dato para ${m.name}`, XDEF.commute]);
    return f.length ? `<dl class="mt-figs">${f.map(([k, v, d]) => `<div${d ? ` title="${d.replace(/"/g, '&quot;')}"` : ''}><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>` : '';
  }
  // Inside Madrid: postcodes by rent, marked when the average fits the cap
  function insideMadrid(r) {
    const pcs = D.postcodes || []; if (!pcs.length) return '';
    if (!(r.in.some(m => m.ine === '28079') || S.work === '28079')) return '';
    const c = cap(S), list = pcs.filter(p => p.rent != null).sort((a, b) => a.rent - b.rent), fit = list.filter(p => p.rent <= c).length;
    return `<section class="mt-inside"><h3>Dentro de Madrid</h3>
      <p class="mt-note">${fit} de ${list.length} códigos postales tienen un alquiler medio dentro de tu tope. ${XDEF.rent || 'Es media, no mediana.'}</p>
      <ul class="mt-pcs">${list.map(p => `<li class="${p.rent <= c ? 'is-fit' : ''}"><b>${p.cp}</b><span>${p.name}</span><em>${eur(p.rent)}</em><small>${p.rent_m2 != null ? nf(p.rent_m2) + ' €/m²' : 'sin €/m²'} · ${p.metres != null ? p.metres + ' m²' : 'sin metros'}</small><i>${p.rent <= c ? 'Cabe' : 'No cabe'}</i></li>`).join('')}</ul></section>`;
  }
  const placeRow = (m, k, i, p) => `<li><button type="button" class="mt-place" data-pt="${m.ine}|${k}|${i}"><i class="mt-ico mt-ico-s" style="background:${COLOR[k]}">${ICON[k]}</i><span>${p[2] ? nice(p[2]) : THING[k][0][0].toUpperCase() + THING[k][0].slice(1)}${p[3] ? `<small>${nice(p[3])}</small>` : ''}</span></button></li>`;
  function placesList(m, keys) {
    let n = 0, html = '';
    keys.forEach(k => { const pts = (m.pts[k] || []).slice(0, Math.max(0, PLACE_MAX - n)); if (!pts.length) return; n += pts.length;
      html += `<li class="mt-pl-h">${LABEL[k] || THING[k][1][0].toUpperCase() + THING[k][1].slice(1)}</li>` + pts.map((p, i) => placeRow(m, k, i, p)).join(''); });
    const total = keys.reduce((a, k) => a + (m.pts[k] || []).length, 0);
    return n ? `<details class="mt-pl"><summary>Lugares (${nf(total)})</summary><ul class="mt-places">${html}</ul>${total > n ? `<p class="mt-note">Se enseñan ${nf(n)} de ${nf(total)}.</p>` : ''}</details>` : '';
  }
  // ponytail: DOM markers, capped at PLACE_MAX per municipality; a symbol layer if lists grow
  const PLACE_MAX = 150, DOT_MAX = 25;
  let dots = [], focusPt = null, camBack = null;
  const TYPE = k => { const t = THING[k][0]; return t[0].toUpperCase() + t.slice(1); };
  function showDots(ine, keys) {
    dots.forEach(d => d.remove()); dots = []; mapLegend(ine, keys);
    const m = BY[ine]; let n = 0;
    keys.forEach(k => (m.pts[k] || []).forEach((p, i) => {
      if (i >= DOT_MAX && focusPt !== `${ine}|${k}|${i}`) return; // few marks at once; the list has them all
      if (n++ >= PLACE_MAX) return;
      const el = document.createElement('button'); el.type = 'button'; el.className = 'mt-dot'; el.dataset.pt = `${ine}|${k}|${i}`; el.style.background = COLOR[k]; el.innerHTML = ICON[k];
      el.setAttribute('aria-label', (p[2] ? nice(p[2]) : THING[k][0]) + ', ' + (LABEL[k] || THING[k][2]));
      dots.push(new maplibregl.Marker({ element: el }).setLngLat([p[0], p[1]]).addTo(map));
    }));
  }
  function focusPlace(id) {
    const [ine, k, i] = id.split('|'), p = BY[ine].pts[k][+i];
    if (!camBack) { const c = map.getCenter(); camBack = { lng: c.lng, lat: c.lat, zoom: map.getZoom(), pitch: map.getPitch() }; }
    focusPt = id;
    if (!dots.some(d => d.getElement().dataset.pt === id)) showDots(ine, [...new Set([...layersFor(ine), k])]);
    dots.forEach(d => { const el = d.getElement(), me = el.dataset.pt === id; el.classList.toggle('is-on', me); el.querySelector('.mt-pop')?.remove(); if (me) el.insertAdjacentHTML('beforeend', `<span class="mt-pop"><em>${TYPE(k)}</em>${p[2] ? nice(p[2]) : ''}${p[3] ? `<small>${nice(p[3])}</small>` : ''}</span>`); if (me) el.parentNode && el.style.setProperty('z-index', 3); });
    document.querySelectorAll('.mt-place').forEach(r => r.setAttribute('aria-current', String(r.dataset.pt === id)));
    const row = document.querySelector(`.mt-place[data-pt="${id}"]`);
    if (row) { const d = row.closest('details'); if (d) d.open = true; row.scrollIntoView({ block: 'nearest', behavior: reduced.matches ? 'auto' : 'smooth' }); }
    if (narrow.matches && sheetY === 0) setSheet(lowY()); // keep the map visible on phones
    $('mt-backmap').hidden = false;
    goCam({ lng: p[0], lat: p[1], zoom: 15, pitch: 0 });
  }
  function unfocus() {
    if (!camBack) return;
    dots.forEach(d => d.remove()); dots = []; focusPt = null; mapLegend(null);
    document.querySelectorAll('.mt-place[aria-current=true]').forEach(r => r.setAttribute('aria-current', 'false'));
    $('mt-backmap').hidden = true; const b = camBack; camBack = null; goCam(b); // back by the same path
  }
  // How many each active filter discards: municipalities that would be in without it (computed, not estimated).
  function dropCounts(r) {
    return reqs(S).map(([label, key]) => {
      const t = JSON.parse(JSON.stringify(S));
      if (key === 'rent') t.capOverride = 1e9; else dropReq(t, key);
      return [key === 'rent' ? 'Tope de alquiler' : label[0].toUpperCase() + label.slice(1), evaluate(t).in.length - r.in.length, key];
    }).sort((a, b) => b[1] - a[1]);
  }
  function renderDrops(r) {
    const rows = dropCounts(r);
    const max = Math.max(1, ...rows.map(x => x[1]));
    $('mt-drops').innerHTML = `<h3>Cuántos descarta cada filtro</h3><p class="mt-note">Municipios que volverían si quitas solo ese filtro.</p>
      <ul class="mt-drop">${rows.map(([l, n, k]) => `<li><span class="mt-drop-l">${l}</span><span class="mt-drop-bar"><span style="width:${n / max * 100}%"></span></span><b>${n}</b>${n && k !== 'rent' ? `<button type="button" class="mt-mini" data-drop="${k}" aria-label="Quitar ${l}">Quitar</button>` : '<span></span>'}</li>`).join('')}</ul>`;
  }

  function sheetBody() {
    const r = evaluate(S);
    $('mt-sheet-body').innerHTML = `
      <section id="mt-unk-list"><h4>Sin los datos que pides: ${r.unknown.length} ${r.unknown.length === 1 ? 'municipio' : 'municipios'}</h4><ul>${r.unknown.map(([m, miss]) => `<li><b>${m.name}</b>: no existe el dato de ${miss.join(', ').replace('tu tope de alquiler', 'alquiler')}</li>`).join('') || '<li>Ninguno con lo que has marcado.</li>'}</ul></section>
      <section><h4>Reglas</h4><p>El tope sale de tu sueldo y no se guarda ni se envía. El lugar de trabajo ordena por distancia en línea recta, no por tiempo de viaje.</p><p>Mascota: ${PET()}</p><p>El número de personas no cambia el precio: no hay alquiler por tamaño de vivienda.</p><p>Se queda un municipio si su alquiler mediano cabe en tu tope (alquiler × 1.200 ≤ sueldo × porcentaje × sueldos) y tiene al menos uno de cada cosa marcada. Sin dato no cuenta como sí ni como no: va a la lista de arriba. Tope y lo que sobra, redondeados hacia abajo.</p><p>Alquiler: ${D.definitions.rent} ${D.sources['alquiler-mivau'].note || ''}</p></section>
      <section><h4>Fuentes</h4><p>Mapa: MapLibre GL JS 5.24.1, BSD-3-Clause. Calles al acercarte: IGN, CC BY 4.0 scne.es. Movimiento: Motion 14.14.0, MIT. Idea de panel y vuelos: Oasis-Madrid, Apache-2.0 (sin su código). Letra: Avenir Next del sistema.</p>
      ${[...new Map([...Object.values(D.sources), ...Object.values(D.extra_sources || {})].filter(x => x.credit).map(x => [x.credit, x.link])).entries()].map(([c, l]) => `<p>${c}${l ? ` <a href="${l}" target="_blank" rel="noopener">${l}</a>` : ''}</p>`).join('')}</section>`;
  }
  function openSheet(toUnknown) {
    sheetBody(); const d = $('mt-sheet'); d.showModal();
    if (window.Motion && !reduced.matches) Motion.animate(d, { opacity: [0, 1], transform: ['translateY(24px)', 'none'] }, { type: 'spring', bounce: 0, duration: 0.35 });
    if (toUnknown) $('mt-unk-list').scrollIntoView({ block: 'start' });
  }

  function change(fn, moved = true) { if (camBack) { dots.forEach(d => d.remove()); dots = []; camBack = null; $('mt-backmap').hidden = true; mapLegend(null); } history.push(JSON.stringify(S)); fn(S); moved_ = true; render(moved); moved_ = false; }

  function why(m, s) {
    const c = cap(s), r = m.rent, w = s.work && BY[s.work], L = [];
    L.push(`Alquiler mediano de ${eur(r.value)} al mes (${r.year}). Con tu tope de ${eurDown(c)} sobran ${eurDown(c - r.value)}.`);
    if (r.p25 != null && r.p75 != null) L.push(`La mitad central de los alquileres (P25 a P75) va de ${eur(r.p25)} a ${eur(r.p75)}.`);
    if (r.type === 'detached') L.push('Solo hay dato de casas unifamiliares, no de pisos.');
    if (w) L.push(w === m ? 'Es donde trabajas o estudias.' : `${km(m, w).toFixed(0)} km en línea recta hasta ${w.name}. No es tiempo de viaje.`);
    if (s.kids) L.push(`${m.nurseries} ${m.nurseries === 1 ? 'escuela infantil' : 'escuelas infantiles'} y ${m.private_early} ${m.private_early === 1 ? 'centro privado' : 'centros privados'} de infantil.`);
    const keys = [...new Set([...(s.school ? ['schools'] : []), ...(s.dog ? DOG : []), ...(s.transport || []), ...(s.services || [])])];
    keys.forEach(k => {
      const n = m.around[k], names = (m.names[k] || []).map(nice);
      if (n == null) return;
      L.push(`${k === 'dog_areas' || k === 'vets' ? 'Al menos ' : ''}${n} ${n === 1 ? THING[k][0] : THING[k][1]}${names.length ? ': ' + names.join(', ') + (n > names.length ? ' y más' : '') : ''}.`);
    });
    if (s.dog && m.around.parks > 0) L.push('No consta si esos parques admiten animales.');
    const unk = Object.keys(m.around).filter(k => m.around[k] == null && THING[k]).map(k => THING[k][2]);
    if (unk.length) L.push(`Estos datos no existen para ${m.name}: ${unk.join(', ')}.`);
    return L;
  }
  const SMALL = new Set(['de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'en', 'a']);
  const ROMAN = /^(i{1,3}|iv|vi{0,3}|ix|xi{0,3})$/;
  // presentation only: words that arrive in capitals are shown in normal case (roman numerals stay)
  const nice = t => t.replace(/[A-ZÁÉÍÓÚÜÑ]{2,}/g, (w, i) => { const l = w.toLowerCase(); return ROMAN.test(l) ? w : i && SMALL.has(l) ? l : l[0].toUpperCase() + l.slice(1); });

  function dropReq(s, key) {
    if (key === 'kids') s.kids = false;
    else if (key === 'schools') s.school = false;
    else if (key === 'dog') s.dog = false;
    if (s.transport) s.transport = s.transport.filter(k => k !== key);
    if (s.services) s.services = s.services.filter(k => k !== key);
  }

  // ---------- map ----------
  let ready = false, map, tween = {}, fade = null, labels = [], stats = null;
  const IGN = 'https://www.ign.es/wmts/ign-base?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=IGNBaseTodo&STYLE=default&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}';
  const REGION = [[-4.58, 39.88], [-3.05, 41.17]];
  function hatch() {
    const n = 12, c = document.createElement('canvas'); c.width = c.height = n;
    const x = c.getContext('2d'); x.fillStyle = '#0f1c28'; x.fillRect(0, 0, n, n);
    x.strokeStyle = '#8796a3'; x.lineWidth = 2;
    x.beginPath(); x.moveTo(0, n); x.lineTo(n, 0); x.moveTo(-n / 2, n / 2); x.lineTo(n / 2, -n / 2); x.moveTo(n / 2, n * 1.5); x.lineTo(n * 1.5, n / 2); x.stroke();
    return x.getImageData(0, 0, n, n);
  }
  let mapFailed = false;
  const hasGL = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; } })();
  function noMap(r) { // fallback without WebGL: say so and list the municipalities that fit
    const lg = document.querySelector('#match .mt-legend'); if (lg) lg.hidden = true;
    $('mt-map').innerHTML = `<div class="mt-nomap"><p><b>El mapa no está disponible en este navegador; puedes continuar con la lista.</b> Municipios que cumplen:</p><ol>${r.in.map(m => `<li>${m.name} · ${eur(m.rent.value)}</li>`).join('')}</ol></div>`;
  }
  function makeMap() {
    if (!hasGL || !window.maplibregl) { map = null; return; }
    const st = k => ['coalesce', ['feature-state', k], 0];
    const sources = { mun: { type: 'geojson', data: D.outlines } };
    const layers = [{ id: 'bg', type: 'background', paint: { 'background-color': '#08121c' } }];
    const online = navigator.onLine;
    if (online) {
      sources.ign = { type: 'raster', tiles: [IGN], tileSize: 256, minzoom: 6, maxzoom: 18, attribution: '' };
      layers.push({ id: 'ign', type: 'raster', source: 'ign', minzoom: 9.5,
        paint: { 'raster-saturation': -1, 'raster-brightness-max': 0.38, 'raster-contrast': 0.1, 'raster-opacity': ['interpolate', ['linear'], ['zoom'], 9.5, 0, 10.5, 1] } });
    }
    const lit = ['+', st('lit'), st('top')];
    layers.push(
      { id: 'fill', type: 'fill', source: 'mun', paint: {
        'fill-color': ['interpolate', ['linear'], lit, 0, '#0f1c28', 1, '#c9921a', 2, '#ffcf4a'],
        // close in (a place, a street) the fill steps back so dots and outlines read
        'fill-opacity': ['interpolate', ['linear'], ['zoom'], 10, 1, 13, ['interpolate', ['linear'], lit, 0, 0.6, 1, 0.22, 2, 0.28]] } },
      { id: 'unk', type: 'fill', source: 'mun', paint: { 'fill-pattern': 'hatch', 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 9.5, st('unk'), 10.5, ['*', 0.6, st('unk')]] } },
      { id: 'line', type: 'line', source: 'mun', paint: { 'line-color': ['interpolate', ['linear'], lit, 0, '#1f3346', 1, '#08121c', 2, '#08121c'], 'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.6, 12, 1.6] } },
      { id: 'top', type: 'line', source: 'mun', paint: { 'line-color': '#fff6d6', 'line-width': 2.5, 'line-opacity': st('top') } });
    map = new maplibregl.Map({ container: 'mt-map', style: { version: 8, sources, layers }, bounds: REGION,
      fitBoundsOptions: { padding: pad() }, dragRotate: false, pitchWithRotate: false, touchPitch: false, maxZoom: 15, minZoom: 7,
      attributionControl: { compact: false, customAttribution: 'IGN CC BY 4.0 · © OpenStreetMap · Powered by CRTM' } });
    map.touchZoomRotate.disableRotation();
    map.addImage('hatch', hatch());
    map.on('error', e => { // offline or IGN down: drop the street layer once, keep the map quiet
      if (e.sourceId === 'ign') { if (map.getLayer('ign')) { map.removeLayer('ign'); map.removeSource('ign'); } }
      else console.warn('mapa:', e.error && e.error.message);
    });
    map.on('movestart', e => { if (e.originalEvent && camAnim) { camAnim.stop(); camBusy = false; } }); // a drag or wheel takes over the camera
    map.on('click', 'fill', e => { const ine = e.features[0].properties.ine; if (ine) flyTo(ine); });
    map.on('load', () => { ready = true; render(true); });
  }
  const pad = () => ({ top: 48, left: 40, right: 40, bottom: 56 });
  function paint(r) {
    if (!ready) return;
    const target = {}, topSet = S.showFinal ? new Set(r.in.slice(0, 3).map(m => m.ine)) : new Set();
    // at the end the three best stay bright and the rest of the lit ones step back
    r.in.forEach(m => target[m.ine] = { lit: 1, top: topSet.has(m.ine) ? 1 : 0, unk: 0 });
    r.unknown.forEach(([m]) => target[m.ine] = { lit: 0, top: 0, unk: 1 });
    M.forEach(m => { target[m.ine] ||= { lit: 0, top: 0, unk: 0 }; });
    const from = {};
    for (const ine in target) from[ine] = tween[ine] || { lit: 0, top: 0, unk: 0 };
    if (fade) fade.stop();
    const apply = e => {
      for (const ine in target) {
        if (FID[ine] === undefined) continue;
        const a = from[ine], b = target[ine], v = { lit: a.lit + (b.lit - a.lit) * e, top: a.top + (b.top - a.top) * e, unk: a.unk + (b.unk - a.unk) * e };
        if (a.lit !== b.lit || a.top !== b.top || a.unk !== b.unk || e === 1) map.setFeatureState({ source: 'mun', id: FID[ine] }, v);
        tween[ine] = v;
      }
    };
    // lights go out and on with one Motion tween over all municipalities; reduced motion: at once
    if (reduced.matches || !window.Motion) apply(1);
    else fade = Motion.animate(0, 1, { type: 'spring', bounce: 0, duration: 0.35, onUpdate: apply });
    // names on the map only when few are left: labels are HTML, no remote glyphs
    labels.forEach(l => l.remove()); labels = [];
    const named = r.in.slice(0, 3);
    const w = S.work && BY[S.work];
    if (w && w.centre && S.workSet) {
      const el = document.createElement('div'); el.className = 'mt-label mt-work'; el.textContent = (topSet.has(w.ine) ? '' : 'Trabajas o estudias en ') + w.name;
      if (!topSet.has(w.ine)) labels.push(new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat(w.centre).addTo(map));
    }
    named.forEach((m, i) => {
      if (!m.centre) return;
      const el = document.createElement('div'); el.className = 'mt-label' + (topSet.has(m.ine) ? ' is-top' : '');
      el.innerHTML = topSet.has(m.ine) ? `<i>${i + 1}</i>${m.name}` : m.name;
      labels.push(new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat(m.centre).addTo(map));
    });
  }
  function bboxOf(list) {
    const b = [180, 90, -180, -90];
    list.forEach(m => { if (!m.bbox) return; b[0] = Math.min(b[0], m.bbox[0]); b[1] = Math.min(b[1], m.bbox[1]); b[2] = Math.max(b[2], m.bbox[2]); b[3] = Math.max(b[3], m.bbox[3]); });
    return b[0] > b[2] ? REGION : [[b[0], b[1]], [b[2], b[3]]];
  }
  function frame(r) {
    if (!ready) return;
    camTo(r.in.length ? bboxOf(S.work ? [...r.in, BY[S.work]] : r.in) : REGION, 11, 0); // fly to what is left
  }
  // Opening a municipality shows only the layers asked for, or health and rail if there are none (entender.md).
  const askedLayers = () => [...new Set([...(S.school ? ['schools'] : []), ...(S.dog ? DOG : []), ...S.transport, ...S.services])];
  function layersFor(ine) {
    const m = BY[ine], asked = askedLayers();
    return asked.length ? asked : ['health_centres', 'metro_stations', 'rail_stations'].filter(k => m.around[k] > 0);
  }
  function flyTo(ine) {
    const m = BY[ine]; if (!m || !m.bbox || !ready) return;
    if (!camBack) { const c = map.getCenter(); camBack = { lng: c.lng, lat: c.lat, zoom: map.getZoom(), pitch: map.getPitch() }; }
    showDots(ine, layersFor(ine)); $('mt-backmap').hidden = false;
    camTo(bboxOf([m]), 13.5, 0);
  }
  function mapLegend(ine, keys) {
    const L = document.querySelector('#match .mt-legend');
    if (!ine) { L.innerHTML = L.dataset.base; return; }
    L.innerHTML = keys.filter(k => (BY[ine].pts[k] || []).length).map(k => `<span><i class="mt-ico mt-ico-s" style="background:${COLOR[k]}">${ICON[k]}</i>${LABEL[k] || THING[k][1][0].toUpperCase() + THING[k][1].slice(1)} <b>${nf(BY[ine].pts[k].length)}</b></span>`).join('') || 'Sin lugares de lo marcado';
  }
  // Camera: one spring on a plain object {lng, lat, zoom, pitch}, applied with jumpTo each frame.
  // A new answer retargets the same object, so Motion keeps the velocity: no jump, no restart.
  let cam = null, camAnim = null, camBusy = false;
  function camTo(bounds, maxZoom, pitch) {
    const c = map.cameraForBounds(bounds, { padding: pad(), maxZoom });
    if (!c) return;
    goCam({ lng: c.center.lng, lat: c.center.lat, zoom: c.zoom, pitch });
  }
  function goCam(to) {
    const pitch = to.pitch;
    if (reduced.matches || !window.Motion) { map.jumpTo({ center: [to.lng, to.lat], zoom: to.zoom, pitch: reduced.matches ? 0 : pitch }); return; }
    if (!camBusy || !cam) { const n = map.getCenter(); cam = { lng: n.lng, lat: n.lat, zoom: map.getZoom(), pitch: map.getPitch() }; }
    camBusy = true;
    const t = [], run = { last: performance.now(), on: true };
    const tick = now => { if (!run.on) return; t.push(now - run.last); run.last = now; requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    const mine = camAnim = Motion.animate(cam, to, { type: 'spring', visualDuration: 0.85, bounce: 0,
      onUpdate: () => map.jumpTo({ center: [cam.lng, cam.lat], zoom: cam.zoom, pitch: cam.pitch }) });
    mine.finished.then(() => {
      run.on = false; const f = t.slice(1);
      window.__mtFrames = { frames: f.length, avgMs: +(f.reduce((a, b) => a + b, 0) / (f.length || 1)).toFixed(1), worstMs: +Math.max(0, ...f).toFixed(1), over33: f.filter(x => x > 33.4).length };
      if (camAnim === mine) camBusy = false;
    }, () => { run.on = false; });
  }

  // ---------- events ----------
  const root2 = $('match');
  root2.addEventListener('pointerdown', e => { const b = e.target.closest('.mt-seg .mt-opt'); if (b && !b.disabled) movePill(b.parentNode, b, true); }); // feedback on press
  root2.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b || b.disabled) return;
    const d = b.dataset;
    if (b.classList.contains('mt-grip')) return;
    if (d.pt) return focusPlace(d.pt);
    if (b.id === 'mt-backmap') return unfocus();
    if (b.id === 'mt-back') return close();
    if (b.id === 'mt-undo') { if (history.length) { S = JSON.parse(history.pop()); render(true); } return; }
    if (b.id === 'mt-src') return openSheet(false);
    if (b.id === 'mt-unk-btn') return openSheet(true);
    if (b.id === 'mt-sheet-close') return $('mt-sheet').close();
    if (d.fly) return flyTo(d.fly);
    if (d.drop) return change(s => dropReq(s, d.drop));
    if (d.cap) return change(s => { s.capOverride = +d.cap; });
    if (d.size) return change(s => { s.size = Math.min(12, Math.max(3, s.size + +d.size)); }, false);
    if (d.f) return change(s => {
      const f = d.f;
      if (['kids', 'school', 'room', 'dog'].includes(f)) s[f] = !s[f];
      else { const k = TRANSPORT.includes(f) ? 'transport' : 'services'; s[k] = s[k].includes(f) ? s[k].filter(x => x !== f) : [...s[k], f]; }
    });
    if (d.k === 'people') return change(s => { s.people = +d.v; s.roomNotice = false; if (s.people === 1) { s.earners = 1; s.capOverride = null; } if (s.people >= 3 && s.room) { s.room = false; s.roomNotice = true; } });
    if (d.k === 'dwelling') { if (d.v === 'habitacion' && S.people >= 3) return; return change(s => { s.room = d.v === 'habitacion'; s.roomNotice = false; }); }
    if (d.k === 'earners') return change(s => { s.earners = +d.v; s.capOverride = null; });
  });
  // Escape: first back from a close-up, then close the map with list (the Sources dialog closes itself)
  addEventListener('keydown', e => { if (e.key !== 'Escape' || $('match').hidden || $('mt-sheet').open) return; e.preventDefault(); if (camBack) unfocus(); else close(); });
  let capStart = null;
  root2.addEventListener('input', e => {
    if (e.target.id !== 'mt-cap') return;
    if (capStart === null) { capStart = JSON.stringify(S); }
    S.capOverride = +e.target.value; render(false); // live while dragging; the camera waits for release
  });
  root2.addEventListener('change', e => {
    if (e.target.id === 'mt-cap') { if (capStart) history.push(capStart); capStart = null; render(true); }
    if (e.target.id === 'mt-work') change(s => { s.work = e.target.value || null; });
  });
  narrow.addEventListener('change', () => { panel.style.transform = ''; sheetY = liveY = 0; if (map) { map.resize(); frame(evaluate(S)); } });


  // ---------- bottom sheet on phones: drag the grip, flick or tap; Enter/Space toggles ----------
  const panel = $('mt-panel'), grip = panel.querySelector('.mt-grip');
  // Apple «Designing Fluid Interfaces»: start from the live value, track 1:1, rubber-band past the top,
  // project the flick (d = 0.998) to pick the snap point, hand the finger's velocity to the spring.
  let sheetY = 0, liveY = 0, drag = null, dragged = false, sheetAnim = null;
  const lowY = () => Math.max(0, panel.offsetHeight - 132);
  const putY = y => { liveY = y; panel.style.transform = `translateY(${y}px)`; };
  const rubber = (o, dim) => (o * dim * 0.55) / (dim + 0.55 * Math.abs(o));
  function setSheet(y, velocity = 0) {
    sheetY = y; grip.setAttribute('aria-expanded', String(y === 0));
    if (sheetAnim) sheetAnim.stop();
    if (window.Motion && !reduced.matches) sheetAnim = Motion.animate(liveY, y, { type: 'spring', velocity, bounce: 0, duration: 0.4, onUpdate: putY });
    else putY(y);
    if (map) setTimeout(() => frame(evaluate(S)), reduced.matches ? 0 : 220);
  }
  grip.addEventListener('pointerdown', e => {
    if (!narrow.matches || drag) return; // one pointer at a time
    if (sheetAnim) sheetAnim.stop(); // grab it mid-flight
    grip.setPointerCapture(e.pointerId); drag = { id: e.pointerId, y0: e.clientY, base: liveY, hist: [[performance.now(), e.clientY]] }; dragged = false;
  });
  grip.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dy = e.clientY - drag.y0; if (Math.abs(dy) > 6) dragged = true;
    let y = drag.base + dy, low = lowY();
    if (y < 0) y = -rubber(-y, innerHeight); else if (y > low) y = low + rubber(y - low, innerHeight);
    putY(y); drag.hist.push([performance.now(), e.clientY]); if (drag.hist.length > 5) drag.hist.shift();
  });
  grip.addEventListener('pointerup', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const h = drag.hist, a = h[0], z = h[h.length - 1], v = z[0] > a[0] ? (z[1] - a[1]) / (z[0] - a[0]) * 1000 : 0; // px/s
    drag = null;
    if (!dragged) return;
    const projected = liveY + (v / 1000) * 0.998 / (1 - 0.998);
    setSheet(projected > lowY() / 2 ? lowY() : 0, v);
  });
  grip.addEventListener('click', () => { if (dragged) { dragged = false; return; } setSheet(sheetY === 0 ? lowY() : 0); });

  let viaKeys = false;
  addEventListener('keydown', () => { viaKeys = true; }, true);
  addEventListener('pointerdown', () => { viaKeys = false; }, true);
  const parts = () => [$('mt-filters'), $('mt-panel'), $('mt-stats'), document.querySelector('#match .mt-top')];
  function open(o) {
    opener = document.activeElement; onClose = o.onClose || null; history = [];
    S = fromAnswers(o);
    $('match').hidden = false; document.documentElement.classList.add('mt-open');
    if (!$('mt-filters').firstElementChild) buildFilters();
    document.querySelector('#match .mt-legend').dataset.base ||= document.querySelector('#match .mt-legend').innerHTML;
    if (!map && !mapFailed) { try { makeMap(); } catch (e) { console.warn('mapa:', e.message); map = null; mapFailed = true; } } else if (map) map.resize();
    render(!!map && ready);
    enter();
    const f = viaKeys ? document.querySelector('#mt-filters button') : $('mt-title'); if (f) f.focus({ preventScroll: true });
  }
  // Entrance (ios-cambio1): filters from the left, results from the right (the sheet from below), figures from above.
  // Critically damped springs, transform and opacity only, settled under 900 ms; clickable from the first frame.
  function enter() {
    if (narrow.matches) { sheetY = lowY(); putY(sheetY); grip.setAttribute('aria-expanded', 'false'); } // results peek; filters reachable
    if (!window.Motion) return;
    const A = Motion.animate, sp = { type: 'spring', bounce: 0, duration: 0.4 };
    if (reduced.matches) { A(parts(), { opacity: [0, 1] }, { duration: 0.2 }); return; }
    A($('mt-filters').querySelectorAll('fieldset'), { transform: ['translateX(-32px)', 'none'], opacity: [0, 1] }, { ...sp, delay: Motion.stagger(0.04) });
    A($('mt-stats').children, { transform: ['translateY(-14px)', 'none'], opacity: [0, 1] }, { ...sp, delay: Motion.stagger(0.04) });
    if (narrow.matches) { if (sheetAnim) sheetAnim.stop(); sheetAnim = A(panel.offsetHeight, sheetY, { ...sp, onUpdate: putY }); }
    else A(panel, { transform: ['translateX(40px)', 'none'], opacity: [0, 1] }, { ...sp, delay: 0.08 });
  }
  // Exit by the same sides; then hide.
  function close() {
    if (!window.Motion || reduced.matches) return hide();
    const A = Motion.animate, sp = { type: 'spring', bounce: 0, duration: 0.3 };
    A($('mt-filters'), { transform: 'translateX(-32px)', opacity: 0 }, sp);
    A($('mt-stats'), { transform: 'translateY(-14px)', opacity: 0 }, sp);
    const out = narrow.matches ? A(liveY, panel.offsetHeight, { ...sp, onUpdate: putY }) : A(panel, { transform: 'translateX(40px)', opacity: 0 }, sp);
    out.finished.then(hide, hide);
  }
  function hide() {
    if ($('match').hidden) return;
    parts().forEach(el => { el.style.transform = el.style.opacity = ''; }); sheetY = liveY = 0;
    $('match').hidden = true; document.documentElement.classList.remove('mt-open');
    document.dispatchEvent(new CustomEvent('dondecabes:matchclose'));
    if (onClose) onClose();
    if (opener && opener.focus) opener.focus();
  }
  // Public rule for WEB (encargo preguntas): one place decides. Keys documented in equipo/estado/mapa.md.
  function fromAnswers(o) {
    const s = fresh(o), a = o.answers || {}, bool = v => v === true;
    const ppl = { solo: 1, pareja: 2 }[a.people] ?? (a.people === 'familia' ? 3 : +a.people);
    if (ppl >= 1) s.people = Math.min(4, Math.floor(ppl));
    if (s.people === 1) s.earners = 1;
    if ((a.earners === 1 || a.earners === 2) && !(s.people === 1 && a.earners === 2)) s.earners = a.earners;
    if (Number.isInteger(a.size) && a.size >= 3 && a.size <= 12) s.size = a.size;
    for (const k of ['kids', 'school', 'dog']) s[k] = bool(a[k]);
    s.room = (a.dwelling === 'habitacion' || bool(a.room)) && s.people < 3; // three or more people: flat only
    s.roomNotice = (a.dwelling === 'habitacion' || bool(a.room)) && s.people >= 3;
    s.transport = (Array.isArray(a.transport) ? a.transport : []).filter(k => TRANSPORT.includes(k));
    s.services = (Array.isArray(a.services) ? a.services : []).filter(k => SERVICES.includes(k));
    s.work = BY[a.work] ? a.work : null;
    if (typeof a.cap === 'number' && a.cap > 0) s.capOverride = a.cap;
    return s;
  }
  function publicEvaluate(o) {
    const s = fromAnswers({ annual: o.annual, share: o.share, earners: o.earners, answers: o.answers || o });
    if (!(s.annual > 0) && s.capOverride == null) return null;
    const r = evaluate(s), base = m => ({ ine: m.ine, name: m.name, rent: m.rent ? m.rent.value : null });
    return { cap: cap(s), rule: D.rule, people: s.people, dwelling: s.room ? 'habitacion' : 'piso', dwellingChanged: s.roomNotice,
      in: r.in.map(base),
      unknown: r.unknown.map(([m, miss]) => ({ ...base(m), status: 'unknown', missing: miss })),
      out: r.out.map(m => ({ ...base(m), status: 'out', reason: r.why.get(m.ine) })),
      counts: { in: r.in.length, unknown: r.unknown.length, out: r.out.length } };
  }
  const icons = Object.fromEntries(Object.keys(COLOR).filter(k => ICON[k]).map(k => [k, { svg: ICON[k], color: COLOR[k], label: LABEL[k] || THING[k][1] }]));
  window.dondeCabes = Object.assign(window.dondeCabes || {}, { openMatch: open, closeMatch: close, evaluate: publicEvaluate, icons,
    keys: { transport: TRANSPORT, services: SERVICES } });
})();
