'use strict';
window.views ||= {};
(() => {
const groups = [
 ['Observatorio',[['home','Centro de mando','M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z'],['explorer','Explorador territorial','M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z M9 3v15 M15 6v15'],['history','Histórico de incendios','M3 12a9 9 0 1 0 3-7 M3 3v6h6 M12 7v6l4 2']]],
 ['Planificación',[['weather','Próximos siete días','M4 17a4 4 0 0 1 1-8 6 6 0 0 1 12-1 5 5 0 0 1 1 10H4z'],['season','Campaña 2027–2030','M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4 M8 14h3 M13 17h3'],['planning','Prevención','M12 3l8 3v6c0 4-3 7-8 10-5-3-8-6-8-10V6z M8 12l3 3 5-6']]],
 ['Análisis',[['profile','Ficha municipal','M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5'],['compare','Comparador','M3 20h18 M6 16V9h4v7z M14 16V4h4v12z'],['simulator','Simulador climático','M4 6h16 M4 12h16 M4 18h16 M8 3v6 M15 9v6 M10 15v6'],['lab','Laboratorio científico','M9 3h6 M10 3v7l-6 9a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2l-6-9V3 M8 15h8']]],
 ['Proyecto',[['data','Datos abiertos','M3 6q9-7 18 0-9 7-18 0z M3 6v12q9 7 18 0V6 M3 12q9 7 18 0'],['about','Acerca del proyecto','M12 3a9 9 0 1 0 .1 0 M12 11v6 M12 7v1']]]
];
const months=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const state={ine:'28079',month:7};
const dataRoot='/data/processed/';
const dataCache=new Map();
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numeric=v=>(v===null||v===undefined||String(v).trim()===''||!Number.isFinite(Number(v)))?null:Number(v);
const number=(v,digits=1)=>numeric(v)===null?'s/d':Number(v).toLocaleString('es-ES',{maximumFractionDigits:digits,minimumFractionDigits:digits,useGrouping:'always'});
const pct=v=>numeric(v)===null?'s/d':number(100*v,1)+' %';
const sum=(rows,key)=>rows.reduce((s,r)=>s+(numeric(r[key])??0),0);
function parseCSV(text){
 const records=[];let record=[],value='',quoted=false;
 text=text.replace(/^\uFEFF/,'');
 for(let i=0;i<text.length;i++){const c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){value+='"';i++}else quoted=!quoted}
  else if(c===','&&!quoted){record.push(value);value=''}
  else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;record.push(value);records.push(record);record=[];value=''}
  else value+=c;
 }
 if(value||record.length){record.push(value);records.push(record)}
 const keys=records.shift()||[];return records.filter(r=>r.length>1||r[0]).map(r=>Object.fromEntries(keys.map((k,i)=>[k,r[i]??''])));
}
async function load(path){
 if(!dataCache.has(path))dataCache.set(path,(async()=>{
  const response=await fetch(path);if(!response.ok)throw Error('HTTP '+response.status+' · '+path);
  return /\.csv(?:\?|$)/i.test(path)?parseCSV(await response.text()):response.json();
 })().catch(e=>{dataCache.delete(path);throw e}));return dataCache.get(path);
}
function download(filename,rows){
 if(!rows?.length)return;const csvv=v=>'"'+String(v??'').replaceAll('"','""')+'"';
 const keys=Object.keys(rows[0]);const text='\uFEFF'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(a=>a.map(csvv).join(',')).join('\r\n');
 const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1500);
}
function heading(eyebrow,title,intro=''){return '<header class="heading"><div class="eyebrow">'+esc(eyebrow)+'</div><h1>'+esc(title)+'</h1><p class="intro">'+esc(intro)+'</p></header>'}
const panelhead=(title,sub='')=>'<div class="panelhead"><div><h2>'+esc(title)+'</h2><small>'+esc(sub)+'</small></div></div>';
const metrics=items=>'<div class="metrics">'+items.map(([label,value,hint])=>'<div class="metric"><span class="label">'+esc(label)+'</span><strong>'+esc(value)+'</strong><small>'+esc(hint)+'</small></div>').join('')+'</div>';
function table(el,rows,columns){if(!el)return;el.innerHTML=rows.length?'<div class="tablewrap"><table><thead><tr>'+columns.map(c=>'<th scope="col">'+esc(c.label)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+columns.map(c=>'<td>'+esc(c.format?c.format(r[c.key],r):r[c.key]??'s/d')+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>':'<p class="muted">Sin observaciones para esta selección.</p>'}
function bar(el,items){if(!el)return;const max=Math.max(0,...items.map(d=>Number(d.value)||0));el.innerHTML='<div class="bars">'+items.map(x=>'<div class="barrow"><span>'+esc(x.label)+'</span><div class="bartrack"><div class="barfill" style="width:'+Math.max(0,Math.min(100,max?100*x.value/max:0))+'%"></div></div><b>'+esc(x.text??number(x.value,0))+'</b></div>').join('')+'</div>'}
function timeline(el,rows,x,y,unit){
 const points=rows.filter(r=>numeric(r[y])!==null);if(!points.length){el.textContent='Sin observaciones para este periodo.';return}
 const W=650,H=200,L=55,R=18,T=20,B=28,mx=Math.max(...points.map(r=>Number(r[y])),1);
 const xs=r=>L+(Number(r[x])-Number(rows[0][x]))/(Number(rows.at(-1)[x])-Number(rows[0][x])||1)*(W-L-R);
 const ys=r=>H-B-Number(r[y])/mx*(H-T-B);
 let svg='';for(let i=0;i<=3;i++){const yy=H-B-i*(H-T-B)/3;svg+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yy+'" y2="'+yy+'" stroke="#d8e2d3"/><text x="'+(L-6)+'" y="'+(yy+4)+'" text-anchor="end">'+esc(number(mx*i/3,0))+'</text>'}
 let path='';let open=false;for(const r of rows){if(numeric(r[y])===null){open=false;continue}path+=(open?'L':'M')+xs(r)+' '+ys(r)+' ';open=true}
 svg+='<path d="'+path+'" fill="none" stroke="#24664c" stroke-width="3"/>';
 for(const r of points)svg+='<circle cx="'+xs(r)+'" cy="'+ys(r)+'" r="3" fill="#24664c"><title>'+esc(r[x]+' · '+number(r[y],0)+' '+unit)+'</title></circle>';
 for(const i of [...new Set([0,Math.floor((rows.length-1)/2),rows.length-1])])svg+='<text x="'+xs(rows[i])+'" y="'+(H-5)+'" text-anchor="middle">'+esc(rows[i][x])+'</text>';
 el.innerHTML='<svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(unit+' por año, '+rows[0][x]+' a '+rows.at(-1)[x])+'">'+svg+'</svg>';
}
let municipalities=[],geo,regional=[],events=[],occ=[],zar=[],model={},paths=[],byCode=new Map(),registry=new Map();
const nname=ine=>byCode.get(String(ine))?.nombre||String(ine);
const byName=(a,b)=>a.nombre.localeCompare(b.nombre,'es');
const municipalSelect=(sel=state.ine)=>municipalities.slice().sort(byName).map(r=>'<option value="'+esc(r.cod_ine)+'" '+(r.cod_ine===sel?'selected':'')+'>'+esc(r.nombre)+'</option>').join('');
const monthSelect=(sel=state.month)=>months.map((m,i)=>'<option value="'+(i+1)+'" '+(i+1===Number(sel)?'selected':'')+'>'+m+'</option>').join('');
const options=(items,sel)=>items.map(v=>'<option value="'+esc(v)+'" '+(String(v)===String(sel)?'selected':'')+'>'+esc(v)+'</option>').join('');
function go(view,ine){if(ine&&byCode.has(String(ine)))state.ine=String(ine);if(location.hash==='#'+view)render();else location.hash=view}
function prepGeometry(){
 const all=geo.features.map(f=>({id:String(f.properties.cod_ine),rings:f.geometry.type==='MultiPolygon'?f.geometry.coordinates.flat():f.geometry.coordinates}));
 const xy=all.flatMap(f=>f.rings.flat());const [x0,x1,y0,y1]=[Math.min(...xy.map(p=>p[0])),Math.max(...xy.map(p=>p[0])),Math.min(...xy.map(p=>p[1])),Math.max(...xy.map(p=>p[1]))];
 const cos=Math.cos((y0+y1)*Math.PI/360),s=Math.min(530/((x1-x0)*cos),355/(y1-y0));const dx=(570-(x1-x0)*cos*s)/2,dy=(382-(y1-y0)*s)/2;
 paths=all.map(f=>({id:f.id,d:f.rings.map(r=>r.map((p,i)=>(i?'L':'M')+((p[0]-x0)*cos*s+dx).toFixed(2)+','+((y1-p[1])*s+dy).toFixed(2)).join('')+'Z').join('')}));
}
const defaultColors=['#579e65','#bad36b','#ffdb65','#f39442','#ce4236'];
function map(el,{values={},title='Mapa municipal',unit='',onSelect,selected,formatter,palette,domain,discrete,continuous=false}={}){
 if(!el)return;const lookup=id=>values instanceof Map?values.get(id):values[id];
 const valid=paths.map(p=>numeric(lookup(p.id))).filter(v=>v!==null).sort((a,b)=>a-b);
 const cs=Array.isArray(palette)&&palette.length?palette:defaultColors;const fmt=formatter||((v)=>number(v,1)+(unit?' '+unit:''));
 const cuts=domain||[.025,.075,.15,.30];
 const anchors=[[0,[104,177,116]],[.025,[176,212,110]],[.075,[248,220,91]],[.15,[250,164,63]],[.30,[226,85,50]],[1,[135,17,37]]];
 function ramp(v){
   const end=anchors.findIndex(([x])=>x>=v);
   if(end<=0)return end===0?'rgb(104,177,116)':'rgb(135,17,37)';
   const [lo,left]=anchors[end-1],[hi,right]=anchors[end],weight=(v-lo)/(hi-lo);
   return 'rgb('+left.map((x,i)=>Math.round(x+(right[i]-x)*weight)).join(',')+')';
 }
 const getColor=v=>v===null?'#d5d8d1':continuous?ramp(v):discrete?.[v]?.color||cs[Math.min(cs.length-1,cuts.filter(c=>v>c).length)];
 const desc=id=>nname(id)+' · '+(numeric(lookup(id))===null?'sin dato':fmt(Number(lookup(id))));
 const pathHTML=paths.map(p=>'<path data-ine="'+esc(p.id)+'" d="'+p.d+'" fill-rule="evenodd" fill="'+getColor(numeric(lookup(p.id)))+'" class="'+(selected===p.id?'selected':'')+'"><title>'+esc(desc(p.id))+'</title></path>').join('');
 let legend='';if(continuous)legend=anchors.map(([x])=>'<span><i class="swatch" style="background:'+ramp(x)+'"></i>'+pct(x)+'</span>').join('')+' · Escala continua fija';else if(discrete)legend=Object.entries(discrete).map(([,v])=>'<span><i class="swatch" style="background:'+v.color+'"></i>'+esc(v.label)+'</span>').join('');
 else if(valid.length){const labels=cuts.length?cuts.map((v,i)=>(i?'>'+fmt(cuts[i-1])+' – ':'≤ ')+fmt(v)).concat('> '+fmt(cuts.at(-1))):[fmt(valid[0])];legend=labels.map((v,i)=>'<span><i class="swatch" style="background:'+cs[i]+'"></i>'+esc(v)+'</span>').join('')}
 if(valid.length<paths.length)legend+='<span><i class="swatch" style="background:#d5d8d1"></i>Sin dato</span>';
 el.innerHTML='<div class="mapbox"><svg viewBox="0 0 570 382" role="img" aria-label="'+esc(title)+'">'+pathHTML+'</svg><span class="mapread" aria-live="polite">'+esc(selected?desc(selected):title)+'</span><span class="north" aria-hidden="true">↑ N</span><div class="mapbuttons"><button aria-label="Ampliar">+</button><button aria-label="Reducir">−</button><button aria-label="Restablecer encuadre">↺</button></div></div><div class="legend" aria-label="Leyenda">'+legend+'</div>';
 const svg=el.querySelector('svg'),read=el.querySelector('.mapread');let z=1,cx=285,cy=191;
 function zoom(){cx=Math.min(570-285/z,Math.max(285/z,cx));cy=Math.min(382-191/z,Math.max(191/z,cy));svg.setAttribute('viewBox',[cx-285/z,cy-191/z,570/z,382/z].join(' '))}
 el.querySelectorAll('.mapbuttons button').forEach((b,i)=>b.onclick=()=>{if(i===2){z=1;cx=285;cy=191}else{if(i===0&&z===1&&selected){const p=svg.querySelector('[data-ine="'+selected+'"]');if(p){const bb=p.getBBox();cx=bb.x+bb.width/2;cy=bb.y+bb.height/2}}z=Math.max(1,Math.min(6,i===0?z*1.5:z/1.5))}zoom()});
 let drag=null,moved=false;svg.onpointerdown=e=>{moved=false;if(z>1){drag=[e.clientX,e.clientY,cx,cy];svg.style.cursor='grabbing';svg.setPointerCapture(e.pointerId)}};
 svg.onpointermove=e=>{if(drag){const factor=1/(svg.getScreenCTM()?.a||1);const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(Math.abs(dx)+Math.abs(dy)>3)moved=true;cx=drag[2]-dx*factor;cy=drag[3]-dy*factor;zoom()}else if(e.target.dataset.ine){read.textContent=desc(e.target.dataset.ine)}};
 svg.onpointerup=e=>{drag=null;svg.style.cursor='';if(!moved){const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-ine]');if(target){const id=target.dataset.ine;onSelect?onSelect(id):go('profile',id)}}};svg.onpointercancel=()=>{drag=null};svg.onpointerleave=()=>{if(!drag)read.textContent=selected?desc(selected):title};
}
function rank(el,rows,key,fmt=(v=>number(v,0)),limit=7){
 const ranked=rows.filter(r=>numeric(r[key])!==null).slice().sort((a,b)=>Number(b[key])-Number(a[key])||nname(a.cod_ine).localeCompare(nname(b.cod_ine),'es')).slice(0,limit);
 el.innerHTML=ranked.length?'<ol class="ranklist">'+ranked.map((r,i)=>'<li><span class="rnum">'+String(i+1).padStart(2,'0')+'</span><button data-code="'+esc(r.cod_ine)+'">'+esc(nname(r.cod_ine))+'</button><b>'+esc(fmt(r[key]))+'</b></li>').join('')+'</ol>':'<p>Sin datos para este filtro.</p>';
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>go('profile',b.dataset.code));
}
const rowsBy=(rows,key='cod_ine')=>new Map(rows.map(r=>[r[key],r]));
const vals=(rows,key)=>Object.fromEntries(rows.map(r=>[r.cod_ine,r[key]]));
const monthly=()=>occ.filter(r=>Number(r.mes)===state.month);
const years=()=>[...new Set(events.map(r=>Number(r.anio||r.fecha.slice(0,4))))].sort((a,b)=>a-b);
function summarize(rows){const result=new Map(municipalities.map(r=>[r.cod_ine,{cod_ine:r.cod_ine,count:0,area:0,known:0}]));for(const e of rows){const r=result.get(e.ine);if(!r)continue;r.count++;if(numeric(e.superficie_ha)!==null){r.known++;r.area+=Number(e.superficie_ha)}}return [...result.values()].map(r=>({...r,area:r.count&&!r.known?null:r.area}))}
const contourSVG='<svg class="contours" aria-hidden="true" viewBox="0 0 380 160" preserveAspectRatio="xMaxYMid slice"><g fill="none" stroke="#a7c396" stroke-width=".85">'+Array.from({length:18},(_,i)=>'<path d="M'+(90+i*10)+' -18 C'+(185+i*9)+' 53 '+(-100+i*12)+' 109 '+(100+i*13)+' 180"/>').join('')+'</g></svg>';
const card=(id,title,detail)=>'<a class="panel linkcard" href="#'+id+'"><h3>'+esc(title)+' <span>↗</span></h3><p>'+esc(detail)+'</p></a>';
function home(el){
 const rr=monthly(),yy=years(),mm=Array(12).fill(0);
 for(const e of events)mm[Number(e.fecha.slice(5,7))-1]++;
 const peak=months[mm.indexOf(Math.max(...mm))],latest=regional.at(-1);
 el.innerHTML='<section class="hero"><div><div class="eyebrow">Observatorio de incendios forestales</div><h1>Centro de mando</h1><p>Elige un mes para comparar los 179 municipios. El mapa muestra dónde estima el modelo que es más probable que se registre algún incendio ese mes. Pulsa un municipio para consultar sus datos.</p></div>'+contourSVG+'</section>'+
 metrics([['Territorio',number(municipalities.length,0),'municipios en el mapa'],['Incendios registrados',number(events.length,0),'partes · '+yy[0]+'–'+yy.at(-1)],['Mes con más registros',peak,'mes con más partes'],['Última campaña con meteorología','2026','observaciones hasta octubre · incendios regionales hasta '+latest.anio]])+
 '<div class="twocol"><section class="panel">'+panelhead('Probabilidad de incendio en el mes','Por ejemplo, un 10 % equivale a una posibilidad entre diez de registrar uno o más incendios en ese municipio durante el mes.')+'<div class="toolbar"><label>Mes de referencia<select id="month">'+monthSelect()+'</select></label></div><div id="mainmap"></div></section><section class="panel"><div class="eyebrow">Selección territorial</div>'+panelhead('Municipios con mayor estimación',months[state.month-1]+' · referencia histórica')+'<div id="rank"></div><a class="btn" href="#explorer">Explorar todas las capas →</a></section></div>'+
 '<div class="grid-3 linkcards">'+card('weather','Próximos siete días','Consulta el pronóstico y sus fechas de actualización.')+card('season','Campaña 2027–2030','Compara meses y escenarios de sequedad.')+card('planning','Planificar visitas','Elige cuántas visitas hay disponibles y compara el reparto por municipio.')+'</div>';
 el.querySelector('#month').onchange=e=>{state.month=Number(e.target.value);home(el)};
 map(el.querySelector('#mainmap'),{values:vals(rr,'probabilidad'),title:'Probabilidad mensual · '+months[state.month-1],formatter:pct});
 rank(el.querySelector('#rank'),rr,'probabilidad',pct); 
}
const soilAvailable=()=>municipalities.some(r=>numeric(r.ha_forestal)!==null);
const eventYears=e=>Number(e.anio||e.fecha.slice(0,4));
function explorer(el){
 const layerOpts=[
 ['p','Probabilidad de al menos un incendio en el mes'],['count','Partes registrados'],['area','Superficie afectada (ha)'],['dry','Temperatura habitual del mes'],['zar','Designación preventiva ZAR 2026'],['uncertainty','Amplitud del intervalo histórico'],['density','Densidad de población']];
 el.innerHTML=heading('Observatorio','Explorador territorial','Elige qué quieres ver en el mapa. Para contar incendios, selecciona un año. Si eliges «Todos», se suman los registros de 2006 a 2023. Para consultar una probabilidad, selecciona el mes que te interesa.')+'<section class="panel"><div class="toolbar"><label>Qué muestra el mapa<select id="layer">'+layerOpts.map(([k,n])=>'<option value="'+k+'">'+n+'</option>').join('')+'</select></label><label>Zona<select id="zone">'+options(['Todas',...new Set(municipalities.map(r=>r.zona).sort())])+'</select></label><label id="emonth">Mes<select id="month">'+monthSelect()+'</select></label><label id="eyear">Año del registro<select id="year">'+options(['Todos',...years()])+'</select></label><label>Municipio<select id="pick">'+municipalSelect()+'</select></label></div><div class="twocol"><div id="emap"></div><aside><h2 id="lname"></h2><p id="ldesc" class="muted"></p><div id="picked" class="note"></div><div id="erank"></div></aside></div></section>';
 const q=s=>el.querySelector(s);
 async function update(){
  const key=q('#layer').value,zone=q('#zone').value,year=q('#year').value;state.month=Number(q('#month').value);state.ine=q('#pick').value;
  q('#emonth').hidden=!['p','dry','uncertainty'].includes(key);q('#eyear').hidden=!['count','area'].includes(key);
  let rows,fmt,desc,discrete;const label=layerOpts.find(x=>x[0]===key)[1];
  if(['p','uncertainty'].includes(key)){rows=monthly().map(r=>({...r,value:key==='p'?r.probabilidad:(numeric(r.wilson_sup)===null||numeric(r.wilson_inf)===null?null:Number(r.wilson_sup)-Number(r.wilson_inf))}));fmt=key==='p'?pct:v=>number(100*v,1)+' pp';desc=key==='p'?'El modelo utiliza los registros de 2020 a 2023 para estimar la posibilidad de que haya al menos un incendio en un mes como el elegido.':'Indica cuánta incertidumbre hay en la frecuencia histórica. Cuanto más amplio es el margen, menos precisa es la cifra. Se mide en puntos porcentuales (pp) con el método de Wilson.'}
  else if(['count','area'].includes(key)){rows=summarize(events.filter(e=>year==='Todos'||eventYears(e)===Number(year))).map(r=>({...r,value:r[key]}));fmt=key==='count'?v=>number(v,0):v=>number(v,1)+' ha';desc='Partes EGIF atribuidos al municipio de inicio. La superficie afectada corresponde al parte y puede atravesar límites municipales.'}
  else if(key==='dry'){const climate=await load('/results/escenarios.csv');if(q('#layer')?.value!==key)return;rows=climate.filter(r=>Number(r.mes)===state.month&&r.escenario==='Central').map(r=>({...r,value:r.tmax_c}));fmt=v=>number(v,1)+' °C';desc='Media de las temperaturas máximas en el mes histórico elegido como referencia para la estación del municipio.'}
  else if(key==='zar'){rows=zar.map(r=>({cod_ine:r.ine,value:r.zar_2026}));fmt=v=>Number(v)?'Incluido':'Sin designación';discrete={0:{label:'Sin designación',color:'#dae2cd'},1:{label:'Incluido en el anexo',color:'#dd883a'}};desc='Municipios enumerados en el Anexo II del Plan anual regional de 2026. Esta designación administrativa aporta contexto territorial a la prevención.'}
  else{const fields={distance:['distancia_km','km','Distancia desde el punto municipal a la estación asignada. La representatividad local disminuye con la distancia y los contrastes de relieve.'],forest:['ha_forestal','ha','La superficie forestal exige cartografía de coberturas del suelo. Los valores ausentes se muestran en gris.'],density:['densidad','hab./km²','Población dividida por superficie municipal. Describe exposición demográfica, sin evaluar la vulnerabilidad individual.']};const [field,unit,t]=fields[key];rows=municipalities.map(r=>({...r,value:r[field]}));fmt=v=>number(v,1)+' '+unit;desc=t}
  rows=rows.filter(r=>zone==='Todas'||byCode.get(r.cod_ine)?.zona===zone);
  q('#lname').textContent=label;q('#ldesc').textContent=desc;const selected=rows.find(r=>r.cod_ine===state.ine);
  q('#picked').innerHTML='<b>'+esc(nname(state.ine))+'</b><p>'+esc(selected&&numeric(selected.value)!==null?fmt(selected.value):'Sin dato en esta selección')+'</p><button id="openf">Ver ficha municipal →</button>';q('#openf').onclick=()=>go('profile',state.ine);
  map(q('#emap'),{values:vals(rows,'value'),selected:state.ine,title:label,formatter:fmt,domain:({count:[1,5,20,50],area:[1,10,50,200],dry:[10,20,28,35],density:[25,100,500,1500],uncertainty:[.15,.30,.50,.70]})[key],discrete,onSelect:ine=>{q('#pick').value=ine;update()}});
  rank(q('#erank'),rows,'value',fmt,5);
 }
 el.querySelectorAll('select').forEach(s=>s.onchange=update);return update();
}
function history(el){
 const yy=years();
 el.innerHTML=heading('Observatorio','Histórico de incendios','El gráfico superior resume toda la Comunidad de Madrid por años. Debajo puedes explorar los incendios registrados entre 2006 y 2023 según el municipio donde empezaron. Cada parte es el registro de un episodio.')+
 '<section class="panel">'+panelhead('Serie regional anual','Desde 2003. «Siniestros» incluye los conatos, que afectan a menos de una hectárea, y los incendios que alcanzan una hectárea o más. Una hectárea equivale a 100 × 100 metros.')+'<div class="toolbar"><label>Indicador regional<select id="indicator"><option value="siniestros">Siniestros</option><option value="incendios">Incendios</option><option value="conatos">Conatos</option><option value="ha_quemadas">Superficie afectada (ha)</option></select></label></div><div id="line"></div></section>'+
 '<section class="panel">'+panelhead('Archivo de partes EGIF',yy[0]+'–'+yy.at(-1)+' · selección temporal y territorial')+'<div class="toolbar"><label>Desde<select id="from">'+options(yy,yy[0])+'</select></label><label>Hasta<select id="to">'+options(yy,yy.at(-1))+'</select></label><label>Clase por superficie<select id="type">'+options(['Todas','Conato (< 1 ha)','Incendio (≥ 1 ha)'])+'</select></label><button id="export">Descargar partes filtrados ↓</button></div><div id="estats"></div><div class="grid-2"><div><h3>Distribución por mes</h3><div id="mbars"></div></div><div><h3>Municipios con más partes</h3><div id="hrank"></div></div></div><details><summary>Comparación anual entre fuentes</summary><div id="hcompare"></div></details></section>';
 const q=s=>el.querySelector(s);function update(){
 let lo=Number(q('#from').value),hi=Number(q('#to').value);if(lo>hi){if(document.activeElement===q('#from'))hi=lo;else lo=hi;q('#from').value=lo;q('#to').value=hi}
 const type=q('#type').selectedIndex,rows=events.filter(e=>eventYears(e)>=lo&&eventYears(e)<=hi&&(!type||(numeric(e.superficie_ha)!==null&&(type===1?Number(e.superficie_ha)<1:Number(e.superficie_ha)>=1))));
 const areas=rows.filter(e=>numeric(e.superficie_ha)!==null);
 q('#estats').innerHTML=metrics([['Partes',number(rows.length,0),lo+'–'+hi],['Superficie registrada',number(sum(areas,'superficie_ha'),1)+' ha',number(areas.length,0)+' partes con dato'],['Municipios con parte',number(new Set(rows.map(e=>e.ine)).size,0),'según filtros seleccionados']]);
 const m=Array(12).fill(0);rows.forEach(e=>m[Number(e.fecha.slice(5,7))-1]++);bar(q('#mbars'),m.map((value,i)=>({label:months[i],value})));
 rank(q('#hrank'),summarize(rows).filter(r=>r.count),'count',v=>number(v,0),8);
 q('#export').disabled=!rows.length;q('#export').onclick=()=>download('EGIF-'+lo+'-'+hi+'.csv',rows);
 const regionalBy=new Map(regional.map(r=>[Number(r.anio),r]));table(q('#hcompare'),yy.filter(y=>y>=lo&&y<=hi).map(y=>({anio:y,egif:events.filter(e=>eventYears(e)===y).length,cam:regionalBy.get(y)?.siniestros,area:regionalBy.get(y)?.ha_quemadas})),[{key:'anio',label:'Año'},{key:'egif',label:'EGIF · todos los partes'},{key:'cam',label:'CAM · todos los siniestros',format:v=>number(v,0)},{key:'area',label:'CAM · ha',format:v=>number(v,0)}]);
 }function line(){const sel=q('#indicator');timeline(q('#line'),regional.slice(regional.findIndex(r=>['siniestros','incendios','conatos','ha_quemadas'].every(k=>numeric(r[k])!==null))),'anio',sel.value,sel.selectedOptions[0].text)}
 q('#indicator').onchange=line;el.querySelectorAll('#from,#to,#type').forEach(s=>s.onchange=update);line();update();
}
function listInfo(r){
 const p=r.estacion?('Estación '+r.estacion+' · '+number(r.distancia_km,1)+' km'):'Sin estación asignada';
 return [['Población',number(r.poblacion,0)+' hab. ('+r.anio_poblacion+')'],['Superficie municipal',number(r.superficie_km2,2)+' km²'],['Densidad',number(r.densidad,1)+' hab./km²'],['Cota máxima documentada',numeric(r.cota_max_m)===null?'Sin dato':number(r.cota_max_m,0)+' m'],['Observación meteorológica',p]];
}
async function profile(el){
 const r=byCode.get(state.ine)||municipalities[0],local=events.filter(e=>e.ine===r.cod_ine),rr=monthly(),o=rr.find(a=>a.cod_ine===r.cod_ine)||{},regProb=rr.length?sum(rr,'probabilidad')/rr.length:null;
 const dz=zar.find(a=>a.ine===r.cod_ine),yr=years();
 el.innerHTML=heading('Ficha municipal · '+r.zona,r.nombre,'Elige un mes para ver la probabilidad estimada de incendio, el puesto del municipio entre los 179 y cuántas veces hubo algún registro en ese mismo mes.')+
 '<div class="toolbar"><label>Municipio<select id="mun">'+municipalSelect(r.cod_ine)+'</select></label><label>Mes<select id="mon">'+monthSelect()+'</select></label><button id="rep">Descargar ficha CSV ↓</button><button id="print">Imprimir ficha</button></div>'+
 metrics([['Probabilidad de incendio en el mes',pct(o.probabilidad),months[state.month-1]+' · al menos un parte'],['Puesto entre los 179 municipios',numeric(o.rango)===null?'s/d':o.rango+' / '+municipalities.length,'1 = mayor probabilidad estimada para ese mes'],['Incendios registrados',number(local.length,0),'partes · '+yr[0]+'–'+yr.at(-1)],['Promedio municipal',pct(regProb),'media simple de las estimaciones']])+
 '<div class="grid-2"><section class="panel">'+panelhead('Territorio y observación','Código INE '+r.cod_ine)+'<div id="facts"></div><p class="note">'+(Number(dz?.zar_2026)?'Municipio incluido':'Municipio sin mención nominal')+' en el Anexo II del Plan anual regional de 2026.</p></section><section class="panel">'+panelhead('Lectura de la estimación',months[state.month-1])+'<p>'+esc(r.nombre)+' registró al menos un parte en '+esc(o.anios_con_parte??'s/d')+' de '+esc(o.anios_observados??'s/d')+' años analizados para ese mes. Eso supone un '+pct(o.frecuencia_observada)+'.</p><p class="muted">Intervalo de Wilson del 95 % de la frecuencia observada: '+pct(o.wilson_inf)+' a '+pct(o.wilson_sup)+'.</p><div id="effects"></div><p><a href="#lab">Ver validación y método →</a></p></section></div><div class="grid-2 rowgap"><section class="panel">'+panelhead('El municipio mes a mes','Probabilidad estimada de registrar al menos un incendio')+'<div id="pbars"></div></section><section class="panel">'+panelhead('Evolución de los partes','Incendios registrados · municipio de inicio')+'<div id="prow"></div><div id="metnote"></div><p><a href="#weather">Abrir la previsión municipal →</a></p></section></div>';
 const q=s=>el.querySelector(s);table(q('#facts'),listInfo(r).map(([attr,val])=>({attr,val})),[{key:'attr',label:'Variable'},{key:'val',label:'Valor'}]);
 if(numeric(o.odds_municipio)!==null&&numeric(o.odds_mes)!==null){q('#effects').innerHTML='<details><summary>Detalle técnico del modelo</summary><p>El modelo compara la probabilidad de registrar un incendio con la de no registrarlo. El cociente entre ambas se denomina <i>odds</i>. Factores estimados sobre ese cociente: municipio ×'+number(o.odds_municipio,2)+' y mes ×'+number(o.odds_mes,2)+'. Ambos factores se interpretan junto con los demás términos de la regresión logística.</p></details>'}
 bar(q('#pbars'),occ.filter(a=>a.cod_ine===r.cod_ine).sort((a,b)=>a.mes-b.mes).map(a=>({label:months[a.mes-1],value:Number(a.probabilidad),text:pct(a.probabilidad)})));
 timeline(q('#prow'),yr.map(y=>({year:y,count:local.filter(e=>eventYears(e)===y).length})),'year','count','Partes');
 q('#mun').onchange=e=>{state.ine=e.target.value;profile(el)};q('#mon').onchange=e=>{state.month=Number(e.target.value);profile(el)};q('#print').onclick=()=>window.print();
 q('#rep').onclick=()=>download('ficha-'+r.cod_ine+'-'+state.month+'.csv',[{...r,...o,partes_egif:local.length,periodo_egif:yr[0]+'–'+yr.at(-1),zar_2026:dz?.zar_2026??'',media_municipal:regProb}]);
 const clim=await load('/results/escenarios.csv');if(!el.isConnected||state.ine!==r.cod_ine)return;
 const c=clim.find(a=>a.cod_ine===r.cod_ine&&Number(a.mes)===state.month&&a.escenario==='Central');
 if(c&&q('#metnote'))q('#metnote').innerHTML='<p class="note">Mes análogo central ('+esc(c.anio_analogo)+'): temperatura máxima media '+esc(number(c.tmax_c,1))+' °C en la estación asociada.</p>';
}
const ui={state,get geo(){return geo},get municipalities(){return municipalities},load,number,escape:esc,map,bar,table,download,go,heading,municipalSelect};
async function render(){const id=location.hash.slice(1)||'home';const el=document.querySelector('#content');document.querySelector('#location').textContent=groups.flatMap(g=>g[1]).find(g=>g[0]===id)?.[1]||'Observatorio';try{await ({home,explorer,history,profile,...window.views}[id]||home)(el,ui)}catch(e){el.innerHTML=heading('Consulta','Datos pendientes',e.message)}}
document.querySelector('#navigation').innerHTML=groups.map(([label,items])=>'<div class="navgroup">'+label+'</div>'+items.map(([id,title])=>'<a class="navlink" href="#'+id+'">'+title+'</a>').join('')).join('');
document.querySelector('#menu').onclick=()=>document.querySelector('#rail').classList.toggle('open');
(async()=>{[municipalities,geo,regional,events,occ,zar]=await Promise.all([load(dataRoot+'municipios.csv'),load(dataRoot+'municipios.geojson'),load(dataRoot+'incendios_regionales.csv'),load('/sources/egif/partes_madrid.csv'),load('/results/ocurrencia_mensual.csv'),load(dataRoot+'zar_2026.csv')]);byCode=new Map(municipalities.map(r=>[r.cod_ine,r]));prepGeometry();await render();window.addEventListener('hashchange',render)})().catch(e=>document.querySelector('#content').textContent=e.message);
})();
