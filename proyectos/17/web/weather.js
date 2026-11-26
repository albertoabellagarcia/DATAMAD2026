"use strict";
window.views ||= {};
window.views.weather = async function weather(el, ui) {
  const q = (selector) => el.querySelector(selector);
  const number = (v, d = 1) => Number.isFinite(v) ? ui.number(v, d) : "s/d";
  const formatDay = (d) => new Date(d + "T12:00:00Z").toLocaleDateString("es-ES", {
    timeZone: "Europe/Madrid", day: "numeric", month: "short",
  });
  const timestamp = (d) => new Date(d).toLocaleString("es-ES", {timeZone: "Europe/Madrid", dateStyle: "short", timeStyle: "short"});
  const locations = Object.fromEntries(ui.municipalities.map(m => [m.cod_ine, m.nombre]));
  const heading = ui.heading("Meteorología", "Previsión a siete días",
    "Elige un día para ver dónde se espera más calor. Selecciona tu municipio para consultar la lluvia, el viento y la hora de actualización. Más abajo encontrarás la estimación diaria basada en el historial de incendios.");
  el.innerHTML = heading + '<div class="toolbar"><button id="wx-refresh" type="button">Actualizar previsiones</button><span id="wx-status" role="status"></span></div><div id="wx-main"></div>';
  let data, selected = String(ui.state.ine || "28079"), day, order = "vpd", generation = 0;
  const button = q("#wx-refresh"), main = q("#wx-main"), status = q("#wx-status");

  async function read(refresh) {
    button.disabled = true;
    status.textContent = refresh ? "Consultando Open-Meteo por lotes…" : "Leyendo la copia local…";
    try {
      const res = await fetch(refresh ? "/api/weather/refresh" : "/api/weather", {
        method: refresh ? "POST" : "GET", cache: "no-store",
      });
      if (!res.ok) throw new Error("Sin respuesta");
      const received = await res.json();
      if (!received.dates || !received.locations) throw new Error("Respuesta incompleta");
      data = received;
      if (!data.dates.includes(day)) day = data.dates[0];
      status.textContent = data.notice || (data.issues?.length ?
        "Actualización parcial o fallida. Se conservan los datos disponibles." : "Datos guardados en este equipo.");
      render();
    } catch {
      status.textContent = "El servicio local de previsiones no responde. Puedes reintentar la consulta.";
      if (!data) main.innerHTML = '<div class="note">Las demás secciones del atlas siguen disponibles.</div>';
    } finally {
      button.disabled = false;
    }
  }

  function render() {
    const version = ++generation;
    const idx = data.dates.indexOf(day), previous = data.dates[idx - 1];
    const rows = Object.entries(data.locations).flatMap(([ine, days]) => {
      const values = days[day];
      if (!values || !Number.isFinite(values.tmax)) return [];
      const old = days[previous]?.tmax;
      const change = Number.isFinite(old) ? +(values.tmax - old).toFixed(2) : null;
      return [{ine, nombre: locations[ine] || ine, ...values, change}];
    });
    const values = Object.fromEntries(rows.map(r => [r.ine, r.tmax]));
    const dates = data.dates;
    const chosen = data.locations[selected]?.[day];
    const sorted = rows.filter(r => order === "vpd" || (Number.isFinite(r.change) && (order === "up" ? r.change > 0 : r.change < 0)))
      .sort((a, b) => order === "vpd" ? b.tmax - a.tmax || a.nombre.localeCompare(b.nombre) :
        (order === "up" ? b.change - a.change : a.change - b.change) || a.nombre.localeCompare(b.nombre));
    const age = chosen ? Math.max(0, Math.floor((new Date(data.now) - new Date(chosen.fetched_at)) / 3600000)) : null;
    main.innerHTML = (data.archived
      ? '<div class="note error"><strong>Archivo de previsiones caducadas.</strong> Estas fechas pertenecen a una consulta anterior. Actualiza para obtener el horizonte vigente.</div>' : '')
      + '<div class="toolbar"><label>Fecha<select id="wx-date">' + dates.map(d => '<option value="'+d+'"'+(d===day?' selected':'')+'>'+formatDay(d)+'</option>').join('')
      + '</select></label><label>Municipio<select id="wx-mun">'+ ui.municipalSelect(selected) + '</select></label></div>'
      + '<div class="twocol"><section class="panel"><div class="panelhead"><div><h2>Temperatura máxima prevista</h2><p class="muted">El mapa muestra el calor previsto para cada municipio. Verde indica menos calor y rojo más calor.</p></div></div><div id="wx-map"></div><p class="muted"><small>'
      + rows.length+' de '+ui.municipalities.length+' municipios con temperatura para el '+formatDay(day)+'.</small></p></section>'
      + '<section class="panel"><h2>Comparación del día</h2><label>Ordenar municipios<select id="wx-order">'
      + [['vpd','Más calor'],['up','Mayor aumento desde ayer'],['down','Mayor descenso desde ayer']].map(([v,t])=>'<option value="'+v+'"'+(order===v?' selected':'')+'>'+t+'</option>').join('')
      + '</select></label><ol class="ranklist">'+sorted.slice(0,8).map((r,i)=>'<li><span class="rnum">'+(i+1)+'</span><button type="button" data-city="'+r.ine+'">'+ui.escape(r.nombre)+'</button><b>'+number(order==="vpd"?r.tmax:r.change,2)+' °C</b></li>').join('')
      + '</ol>'+(!sorted.length?'<p class="muted">'+(!idx && order!=="vpd"?'Selecciona el segundo día o uno posterior para comparar con la víspera.':'Sin valores comparables para este orden.')+'</p>':'')
      + '<button type="button" id="wx-csv">Descargar datos del día</button></section></div>'
      + '<section class="panel rowgap"><div class="panelhead"><div><p class="eyebrow">Punto municipal</p><h2>'+ui.escape(locations[selected]||selected)+'</h2><p class="muted">'+(chosen?'Descargado el '+timestamp(chosen.fetched_at)+' (Madrid), hace '+age+' h.':'Sin previsión disponible para la fecha elegida.')+'</p></div></div>'
      + '<div class="metrics">'+[['Lluvia',chosen?.rain,'mm',1],['T. máxima',chosen?.tmax,'°C',1],['Humedad mín.',chosen?.rh,'%',0],['Racha máx.',chosen?.gust,'km/h',1]].map(([k,v,u,d])=>'<div class="metric"><span class="label">'+k+'</span><strong>'+number(v,d)+'</strong><small>'+u+'</small></div>').join('')+'</div>'
      + '<p>La lluvia se mide en milímetros. Un milímetro equivale a un litro de agua por metro cuadrado.</p><div id="wx-history"></div>'
      + '<h3>Evolución prevista</h3><div id="wx-series"></div><div id="wx-table"></div></section>'
      + '<div class="note"><b>Incertidumbre.</b> El pronóstico corresponde a un punto de cada municipio. Dos localidades cercanas pueden compartir el mismo pronóstico, aunque en una ladera o en un valle el viento y la temperatura sean distintos.</div>'
      + '<small>Fuente meteorológica: <a href="https://open-meteo.com/en/docs" target="_blank" rel="noopener">Open-Meteo, CC BY 4.0</a>. Fechas civiles de Madrid. Lluvia antecedente calculada a partir de la serie modelizada.</small>';
    q("#wx-date").onchange = e => { day = e.target.value; render(); };
    q("#wx-order").onchange = e => { order = e.target.value; render(); };
    const pick = ine => { selected = String(ine); ui.state.ine = selected; render(); };
    q("#wx-mun").onchange = e => pick(e.target.value);
    main.querySelectorAll("[data-city]").forEach(b => { b.onclick = () => pick(b.dataset.city); });
    q("#wx-csv").onclick = () => {
      const exports = ui.municipalities.map(m => {
        const r = data.locations[m.cod_ine]?.[day] || {};
        return {cod_ine:m.cod_ine,municipio:m.nombre,fecha:day,dpv_kPa:r.vpd??"",t_max_C:r.tmax??"",t_min_C:r.tmin??"",
          hr_min_pct:r.rh??"",lluvia_mm:r.rain??"",lluvia_previa_3d_mm:r.rain3??"",viento_max_kmh:r.wind??"",racha_max_kmh:r.gust??"",
          descarga_utc:r.fetched_at??"",fuente:"Open-Meteo · CC BY 4.0"};
      });
      ui.download("prevision-"+day+".csv",exports);
    };
    ui.map(q("#wx-map"),{values,title:"Temperatura máxima",domain:[10,20,28,35],unit:"°C",onSelect:pick,selected,formatter:v=>number(v,1)+" °C"});
    const series = dates.map(d => ({date:formatDay(d), ...data.locations[selected]?.[d]}));
    const chart = q("#wx-series");
    const max = Math.max(...series.map(s=>s.tmax || 0),0.1);
    chart.innerHTML='<div class="bars">'+series.map(s=>'<div class="barrow"><span>'+s.date+'</span><div class="bartrack"><div class="barfill" style="width:'+((s.tmax||0)/max*100).toFixed(2)+'%"></div></div><span>'+number(s.tmax,1)+' °C</span></div>').join('')+'</div>';
    ui.table(q("#wx-table"),series,[
      {key:"date",label:"Día"},...[
        ["tmin","Mín. °C"],["tmax","Máx. °C"],["rh","HR mín. %"],["rain","Precip. mm"],
        ["rain3","Precip. 3 días previos mm"],["wind","Viento máx. km/h"],["gust","Racha máx. km/h"],
      ].map(([key,label])=>({key,label,format:v=>number(v)})),
    ]);
    if (window.dailyOccurrence) {
      window.dailyOccurrence(selected,day).then(r=>{
        if (version !== generation || !r || !Number.isFinite(r.p)) return;
        const target = q("#wx-history");
        if (target) {
          target.className="note";
          target.textContent="Probabilidad de registrar al menos un incendio · "+number(100*r.p,2)+" % estimado para un día como este en el municipio. Modelo de calendario ajustado con partes EGIF. Esta estimación se calcula independientemente de la previsión meteorológica mostrada.";
        }
      }).catch(()=>{});
    }
  }
  button.onclick = () => read(true);
  await read(false);
};

(() => {
const original=window.views.weather;
window.views.weather=async function(el,ui){
 await original(el,ui);
 const section=document.createElement('section');section.className='panel rowgap';el.append(section);
 const today=el.querySelector('#wx-date')?.value||new Date().toISOString().slice(0,10);
 section.innerHTML='<h2>Probabilidad de incendio en un día</h2><p>Probabilidad de registrar al menos un parte en cada municipio durante el día seleccionado. Modelo municipal y calendario entrenado con EGIF 2020–2023.</p><label>Fecha de estimación<input id="daily-date" type="date" value="'+today+'"></label><div id="daily-map"></div><div id="daily-table"></div><button id="daily-csv">Descargar probabilidades</button><p class="note">Este porcentaje depende del municipio y de la época del año. El pronóstico de lluvia y temperatura se muestra por separado. En 2023 hubo al menos un incendio en aproximadamente 3 de cada 1.000 combinaciones de municipio y día. Puedes consultar los resultados de la evaluación en el Laboratorio científico.</p>';
 let generation=0;
 async function draw(){
  const run=++generation,date=section.querySelector('#daily-date').value;if(!date)return;
  const rows=await Promise.all(ui.municipalities.map(async m=>{const r=await window.dailyOccurrence(m.cod_ine,date);return {cod_ine:m.cod_ine,nombre:m.nombre,fecha:date,probabilidad:r?.p??null}}));
  if(run!==generation||!section.isConnected)return;
  ui.map(section.querySelector('#daily-map'),{values:Object.fromEntries(rows.map(r=>[r.cod_ine,r.probabilidad])),title:'Probabilidad diaria de ocurrencia',domain:[.001,.003,.007,.015],unit:'probabilidad',formatter:v=>ui.number(100*v,2)+' %',onSelect:ine=>ui.go('profile',ine)});
  ui.table(section.querySelector('#daily-table'),rows.sort((a,b)=>b.probabilidad-a.probabilidad).slice(0,20),[{key:'nombre',label:'Municipio'},{key:'probabilidad',label:'Probabilidad diaria',format:v=>ui.number(100*v,2)+' %'}]);
  section.querySelector('#daily-csv').onclick=()=>ui.download('ocurrencia-diaria-'+date+'.csv',rows);
 }
 el.addEventListener('change',e=>{if(e.target.id==='wx-date'){section.querySelector('#daily-date').value=e.target.value;draw()}});
 section.querySelector('#daily-date').onchange=draw;await draw();
};
})();
