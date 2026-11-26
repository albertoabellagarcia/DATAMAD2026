/* Cruces de contexto: todos los valores y clases proceden de preparar_cruces.py.
   Este módulo solo selecciona, filtra y dibuja los resultados exportados. */
'use strict';

const XC = {vista:'renta',social:'renta',recurso:'primaria',modo:'transporte',corte:10,seleccion:null,grupo:null,grafico:false,autoPlegado:false};
const CT = {dato:'renta',edad:'total'};
function variableDeContexto(){return CT.dato==='renta'?'quintil_renta':CT.edad==='65'?'solas_65_mas':'solas_total';}
const anteriorCruces = {
  montar:montarInterfaz,sincronizar:sincronizarControles,tema:activarTema,territorio:pintarTerritorio,
  leyenda:pintarLeyenda,titulo:actualizarTituloMapa,secciones:capaSecciones,seleccion:capaSeleccion,
  tooltip:tarjetaFlotante,clic:alPulsar,paso:irAPaso,todo:pintarTodo,vista:vistaParaCaja,
  comparar:pintarComparar,ficha:pintarFicha,irATerritorio,
};
function esCapaSocial(){return Boolean(D.cruces&&D.barriosCruces)&&E.paso==='diagnosticar'&&['cruce','solas_total','solas_65_mas'].includes(E.variable);}
function esCruce(){return esCapaSocial()&&E.variable==='cruce';}
function perfilCruce(){return D.cruces.perfiles[`${XC.social}_${XC.recurso}_${XC.recurso==='primaria'?XC.modo:'refugios'}`];}
function basesCruce(p=perfilCruce()){return p.unidad==='seccion'?D.cruces.secciones:D.cruces.barrios;}
function filaDeCruce(idx,p=perfilCruce()){if(!p._indice)p._indice=new Map(p.filas.map(f=>[f.idx,f]));return p._indice.get(idx);}
function claseDeCruce(f){return f?.clases[D.cruces.cortes_y.indexOf(Number(XC.corte))]??-1;}
function baseBarrio(idx){return D.cruces.barrios[idx];}
function nombreVariableSolas(){return E.variable==='solas_65_mas'?'solas_65_mas':'solas_total';}
function variosContextos(){return XC.social==='solas_ambas';}
function sincronizarContextosCruce(){
  document.querySelectorAll('[data-contexto-social]').forEach(c=>{c.checked=c.dataset.contextoSocial===XC.social||(variosContextos()&&['solas','solas65'].includes(c.dataset.contextoSocial));});
  $('cruce-social-nota').textContent=variosContextos()?'Se buscan barrios que cumplen ambos criterios sociales. Las personas de 65 años o más están incluidas en el total; no se suman los conteos.':'Puedes marcar los dos conteos por barrio a la vez. La renta se consulta por sección censal, en una vista distinta.';
  $('cruce-grafico').textContent=variosContextos()?'Ver ambos gráficos y territorios':'Ver gráfico y territorios';
  $('cruce-csv').textContent=variosContextos()?'Descargar ambos conteos (CSV)':'Descargar datos (CSV)';
}
function cambiarContextosCruce(evento){
  const c=evento.target,casillas=[...document.querySelectorAll('[data-contexto-social]')];
  if(c.checked){for(const otra of casillas)if((c.dataset.contextoSocial==='renta')!==(otra.dataset.contextoSocial==='renta'))otra.checked=false;}
  const elegidas=casillas.filter(x=>x.checked).map(x=>x.dataset.contextoSocial);
  if(!elegidas.length){c.checked=true;$('cruce-social-nota').textContent='Mantén al menos un contexto seleccionado para mostrar el mapa.';return;}
  $('cruce-social').value=elegidas.includes('solas')&&elegidas.includes('solas65')?'solas_ambas':elegidas[0];
  $('cruce-social').dispatchEvent(new Event('change'));
}
function colorCruce(f){if(!f)return [0,0,0,0];const c=claseDeCruce(f);const color=c<0?'#AEB9C2':D.cruces.paleta_cruces[c];return conAlfa(rgb(color),XC.grupo!==null&&c!==XC.grupo?45:232);}
function indiceSeleccion(){return XC.seleccion===null?null:Number(XC.seleccion);}
function textoGrupo(c,p=perfilCruce()){
  if(c<0)return 'Sin clasificación: información incompleta';
  return `${p.leyenda_x[c===1||c===3?1:0]} · ${c>=2?'≥':'<'} ${XC.corte} % sin opción`;
}

montarInterfaz = function(){
  anteriorCruces.montar();
  D.mapa.variables.cruce={titulo:'Relacionar datos',escala:'cruces',nota:'Comparación territorial descriptiva de dos indicadores; no modifica la optimización.'};
  D.mapa.variables.solas_total={titulo:'Personas que viven solas',escala:'barrios',nota:'Conteos por barrio del Padrón a 1 de enero de 2026. Vivir solo no equivale a soledad no deseada.'};
  D.mapa.variables.solas_65_mas={titulo:'Personas de 65 años o más que viven solas',escala:'barrios',nota:D.mapa.variables.solas_total.nota};
  const controles=el('div',{id:'controles-contexto'});
  controles.innerHTML=`<label class="campo">¿Qué dato quieres ver?<select id="contexto-dato"><option value="renta">Renta del entorno</option><option value="solas">Personas que viven solas</option></select></label><label id="campo-contexto-edad" class="campo" hidden>Población<select id="contexto-edad"><option value="total">Todas las edades</option><option value="65">65 años o más</option></select></label>
  <div id="controles-cruce" hidden>
   <details class="relacion-guia" open><summary id="relacion-guia-titulo">Relaciona contextos y acceso</summary><p>Descubre dónde coinciden uno o varios contextos sociales y las dificultades para llegar a un recurso.</p>
    <div class="relacion-esquema" aria-label="Un contexto social más el acceso a un recurso forman cuatro grupos en el mapa"><span class="relacion-dato">${iconoTema('<circle cx="12" cy="7" r="3"/><path d="M5 21v-4a7 7 0 0 1 14 0v4"/>')}Contexto<br>social</span><b aria-hidden="true">+</b><span class="relacion-dato">${iconoTema('<path d="M4 21V7h16v14M9 7V3h6v4M9 21v-6h6v6"/>')}Acceso a<br>recursos</span><b aria-hidden="true">=</b><span class="relacion-dato"><span class="relacion-muestra" aria-hidden="true">${(D.cruces?.paleta_cruces||[]).map(c=>`<i style="background:${c}"></i>`).join('')}</span>Cuatro<br>grupos</span></div>
    <p class="relacion-instruccion">Marca los contextos que quieres estudiar y elige un recurso. Pulsa un color para filtrar o una zona para ver su detalle.</p>
   </details>
   <h3 class="relacion-configurar">¿Qué quieres relacionar?</h3>
   <fieldset class="relacion-contextos" aria-describedby="cruce-social-nota"><legend>Contextos sociales</legend>
    <label><input type="checkbox" data-contexto-social="renta"><span>Renta del entorno<small>Por sección censal · Vista separada</small></span></label>
    <label><input type="checkbox" data-contexto-social="solas"><span>Personas que viven solas<small>Todas las edades · Por barrio</small></span></label>
    <label><input type="checkbox" data-contexto-social="solas65"><span>Personas de 65 años o más que viven solas<small>Por barrio · Incluidas en el total</small></span></label>
   </fieldset><p id="cruce-social-nota" class="relacion-contextos-nota" role="status"></p>
   <select id="cruce-social" hidden aria-hidden="true" tabindex="-1"><option value="renta">Renta del entorno</option><option value="solas">Personas que viven solas</option><option value="solas65">Personas de 65 años o más que viven solas</option><option value="solas_ambas">Ambos conteos de personas solas</option></select>
   <label class="campo">Recurso al que llegar<select id="cruce-recurso"><option value="primaria">Atención primaria</option><option value="refugios">Refugios climáticos</option></select></label>
   <label id="campo-cruce-modo" class="campo">Desplazamiento y horario<select id="cruce-modo"><option value="transporte">A pie o transporte · 9–13 h · 30 min</option><option value="transporte_16_20">A pie o transporte · 16–20 h · 30 min</option><option value="pie">A pie · 15 min</option></select></label><label class="campo">Dificultad de acceso: población sin opción<select id="cruce-corte"><option value="5">A partir del 5 %</option><option value="10" selected>A partir del 10 %</option><option value="20">A partir del 20 %</option></select></label><p class="micro">Este corte solo agrupa los colores del mapa. No cambia los tiempos de acceso calculados.</p>
   <button id="cruce-grafico" class="principal ancho">Ver gráfico y territorios</button><a id="cruce-csv" class="boton" download>Descargar datos (CSV)</a></div>`;
  $('controles-primaria').before(controles);
  const titulo=$('vista-diagnosticar').querySelector('.etiqueta-seccion');const fila=el('div',{clase:'titulo-con-cruce'});titulo.before(fila);fila.append(titulo);const acceso=el('button',{id:'abrir-cruces',clase:'enlace',texto:'Relacionar datos'});fila.append(acceso);
  acceso.addEventListener('click',()=>activarCruces());
  for(const id of ['contexto-dato','contexto-edad'])$(id).addEventListener('change',()=>{CT.dato=$('contexto-dato').value;CT.edad=$('contexto-edad').value;aplicarVistaContexto();});
  document.querySelectorAll('[data-contexto-social]').forEach(c=>c.addEventListener('change',cambiarContextosCruce));
  for(const [id,prop]of[['cruce-social','social'],['cruce-recurso','recurso'],['cruce-modo','modo'],['cruce-corte','corte']])$(id).addEventListener('change',()=>{XC[prop]=prop==='corte'?Number($(id).value):$(id).value;XC.seleccion=null;XC.grupo=null;if(prop==='social'||prop==='recurso'){$('cruce-buscar').value='';E.territorio=perfilCruce().ambito;$('buscar').value=E.territorio==='municipio:28079'?'Madrid':'';}pintarTodo();if(prop==='social'||prop==='recurso')encuadrar(D.territorios[perfilCruce().ambito].caja);});
  $('cruce-grafico').addEventListener('click',abrirGraficoCruce);
  const inspector=el('aside',{id:'analisis-cruce','aria-label':'Gráfico y listado de indicadores',hidden:''});
  inspector.innerHTML=`<div class="cabecera-analisis"><div><span class="sobretitulo">Relacionar datos</span><h2>Gráfico y territorios</h2></div><button id="cruce-cerrar" aria-label="Cerrar gráfico y ver el mapa">Ver mapa</button></div><button id="cruce-configurar" class="relacion-volver">Cambiar los datos relacionados</button><p id="cruce-grafico-descripcion" class="nota"></p><div id="cruce-dispersion"></div><div id="cruce-seleccion-resumen" class="aviso-suave" hidden></div><label class="campo">Buscar en el listado<input id="cruce-buscar" type="search" placeholder="Nombre o código del territorio"></label><p id="cruce-listado-cuenta" class="micro"></p><div id="cruce-listado" class="tabla-scroll"></div><p class="micro">Selecciona un punto o una fila para localizarlo en el mapa. Los indicadores describen el territorio, no identifican a las mismas personas.</p>`;
  document.body.append(inspector);$('cruce-cerrar').addEventListener('click',cerrarGraficoCruce);$('cruce-buscar').addEventListener('input',pintarListadoCruce);let reajuste;window.addEventListener('resize',()=>{if(XC.grafico){clearTimeout(reajuste);reajuste=setTimeout(pintarGraficoCruce,100);}});
  inspector.addEventListener('keydown',e=>{if(e.key==='Escape')cerrarGraficoCruce();});
  $('cruce-configurar').addEventListener('click',()=>abrirOpciones(true));
  $('cruce-dispersion').addEventListener('click',e=>{const n=e.target.closest('[data-cruce-idx]');if(n)seleccionarCruce(Number(n.dataset.cruceIdx),true);});
  $('cruce-listado').addEventListener('click',e=>{const n=e.target.closest('[data-cruce-idx]');if(n)seleccionarCruce(Number(n.dataset.cruceIdx),true);});
  const eq=el('section',{id:'equidad-cartera',clase:'equidad',hidden:''});$('barras').after(eq);
  const fichaEq=el('section',{id:'ficha-equidad',clase:'equidad',hidden:''});$('ficha-mapa').after(fichaEq);
  const fuentes=el('section',{clase:'fuentes-cruces'});fuentes.innerHTML=`<h2>Contexto social y cruces</h2><p>Personas que viven solas: Padrón municipal de Madrid a 1 de enero de 2026, total y mayores de 65 años, por barrio. Población de referencia: INE 2025. Renta: ADRH 2024. La accesibilidad conserva los supuestos y horarios de la base del proyecto.</p><p>El número de personas que viven solas no se divide entre una población de otro año ni se traslada a secciones censales. Los cruces no identifican qué personas coinciden ni modifican la optimización.</p><p>Geometría de barrios: origen de los datos, Ayuntamiento de Madrid; reproyección a WGS84 y simplificación cartográfica. Licencia CC BY 4.0, verificada en el catálogo oficial.</p><ul><li><a href="https://datos.madrid.es/dataset/300431-0-personas-viven-solas" target="_blank" rel="noopener">Personas que viven solas: fuente municipal</a></li><li><a href="https://datos.madrid.es/dataset/300496-0-barrios-madrid" target="_blank" rel="noopener">Barrios municipales y licencia</a></li><li><a href="datos/cruces.json" download>Datos preparados de los cruces y metadatos</a></li></ul>`;if(D.cruces)fuentes.append(el('p',{texto:`La agregación de accesibilidad por barrios deja fuera ${D.cruces.metadatos.barrios.poblacion_sin_barrio_texto} habitantes estimados sin asignación espacial a barrio. Los datos no evaluables se mantienen separados.`}));$('datos-contenido').append(fuentes);
  $('ayuda-contenido').append(el('h2',{texto:'Cómo leer los cruces'}),el('p',{texto:'Renta: el criterio social identifica los quintiles Q1–Q2. Personas que viven solas: identifica los barrios cuyo conteo alcanza la mediana de los 131 barrios. El segundo criterio compara el porcentaje de población total sin opción verificada con el corte visible del mapa. Una evaluación incompleta se conserva en gris.'}),el('p',{texto:'Las ganancias por quintil se agregan desde las unidades beneficiadas sin redondear. El reparto entero conserva el total publicado; los quintiles describen la renta del entorno, no la renta individual de quienes mejoran.'}));
};

sincronizarControles = function(){
  if(!esCapaSocial()){anteriorCruces.sincronizar();$('controles-contexto').hidden=U.tema!=='contexto';$('controles-cruce').hidden=true;if(E.variable==='quintil_renta')$('contexto-dato').value='renta';return;}
  U.tema='contexto';$('controles-primaria').hidden=true;$('controles-contexto').hidden=false;$('contexto-dato').value=XC.vista==='renta'?'renta':'solas';$('controles-cruce').hidden=!esCruce();$('ver-actuaciones').hidden=true;
  document.querySelectorAll('[data-tema]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tema==='contexto')));
  $('ver-centros').checked=E.centros;$('ver-mercados').checked=E.mercados;$('alcance-tema').hidden=false;
  if(esCruce()){
    const p=perfilCruce();$('cruce-social').value=XC.social;$('cruce-recurso').value=XC.recurso;$('cruce-modo').value=XC.modo;$('cruce-corte').value=String(XC.corte);$('campo-cruce-modo').hidden=XC.recurso!=='primaria';$('alcance-tema').textContent=`${p.anos} · ${p.unidad==='barrio'?'Barrios de Madrid capital':'Secciones censales'}`;$('cruce-csv').href=p.csv;
  }else{$('alcance-tema').textContent='Madrid capital · Personas por barrio · Padrón a 1 de enero de 2026. Vivir solo no equivale a soledad no deseada.';}
};
activarTema = function(tema){const vista=XC.vista;XC.seleccion=null;XC.grupo=null;if(tema!=='contexto')cerrarGraficoCruce(false);anteriorCruces.tema(tema);if(tema==='contexto'){XC.vista=vista;aplicarVistaContexto();}};
function aplicarVistaContexto(){
  if(CT.dato==='solas'&&!D.cruces){CT.dato='renta';$('contexto-dato').value='renta';avisarCarga(D.fallos.cruces||D.fallos.barrios||'datos/cruces.json');return;}
  iniciarVista();U.tema='contexto';E.variable=variableDeContexto();XC.vista=CT.dato==='renta'?'renta':E.variable;
  if(CT.dato==='solas')E.territorio='municipio:28079';
  $('buscar').value=E.territorio==='comunidad:28'?'':D.territorios[E.territorio].nombre;
  pintarTodo();ordenarCifrasTema();encuadrar(D.territorios[E.territorio].caja,false);
}

pintarTerritorio = function(){
  if(!esCapaSocial())return anteriorCruces.territorio();const caja=$('territorio');caja.replaceChildren();$('zona-senalada').hidden=true;
  if(esCruce()){
    const p=perfilCruce(),idx=indiceSeleccion(),f=idx===null?null:filaDeCruce(idx,p),base=idx===null?null:basesCruce(p)[idx];
    if(idx===null&&p.ambito==='municipio:28079'&&E.territorio!==p.ambito){
      const distrito=E.territorio.startsWith('distrito:');
      caja.append(el('p',{clase:'aviso-suave',texto:distrito?'El resumen de este cruce corresponde a Madrid capital; no hay un resumen propio de este distrito.':'Fuera del ámbito de este cruce (solo Madrid capital).'}));
      const volver=el('button',{clase:'pt-enlace',texto:'Volver a Madrid capital'});
      volver.addEventListener('click',()=>irATerritorio('municipio:28079'));caja.append(volver);return;
    }
    if(f&&base){caja.append(el('p',{clase:'sobretitulo',texto:p.unidad==='barrio'?'Barrio seleccionado':'Sección seleccionada'}),el('h3',{texto:base.nombre}),el('p',{clase:'micro',texto:base.id}),el('div',{clase:'valor-principal',texto:f.x_texto}),el('p',{clase:'etiqueta-valor',texto:p.etiqueta_x}));if(variosContextos())caja.append(filaDato('65 años o más que viven solos',f.x_mayores_texto));caja.append(filaDato('Sin opción verificada',f.y_texto),filaDato('Personas sin opción',f.sin_texto),filaDato('Personas no evaluables',f.no_evaluable_texto),el('p',{clase:'micro',texto:`${base.poblacion_texto} habitantes · INE 2025`}),el('p',{clase:'grupo-seleccionado',texto:textoGrupo(claseDeCruce(f),p)}));if(base.calidad&&XC.social==='renta')caja.append(el('p',{clase:'micro',texto:`Calidad de renta: ${D.cruces.calidad_textos[base.calidad]||'Calidad no documentada'}`}));
    }else{const resumen=p.resumen[String(XC.corte)],g=XC.grupo;const n=g===null?resumen.grupos[3]:g<0?resumen.no_evaluable:resumen.grupos[g];caja.append(el('h3',{texto:'Coincidencia territorial'}),el('div',{clase:'valor-principal',texto:miles(n)}),el('p',{clase:'etiqueta-valor',texto:`${p.unidad==='barrio'?'barrios':'secciones'} ${g===null?'cumplen ambos criterios':g<0?'con información incompleta':'en el grupo seleccionado'}`}),el('p',{clase:'micro',texto:`Criterio social: ${p.criterio_x}`}),el('p',{clase:'micro',texto:`Dificultad de acceso: al menos ${XC.corte} % sin opción verificada.`}),filaDato('Sin clasificación',String(resumen.no_evaluable)));}
    caja.append(el('p',{clase:'nota',texto:XC.social==='renta'?'La renta describe el entorno de la sección; no la renta individual de sus habitantes.':'Comparación por barrio: no identifica qué personas que viven solas tienen dificultades de acceso.'}));
    if(variosContextos())caja.append(el('p',{clase:'relacion-contextos-nota',texto:'Las personas de 65 años o más forman parte del total. Se muestran ambos conteos sin sumarlos. El mapa exige que se cumplan los dos criterios sociales.'}));
    if(idx===null)caja.append(el('p',{clase:'micro',texto:`Ámbito del resumen del cruce: ${D.territorios[p.ambito].nombre}. Selecciona una zona para consultar su dato.`}));
    if(XC.recurso==='refugios'&&p.resumen[String(XC.corte)].grupos[0]+p.resumen[String(XC.corte)].grupos[1]===0)caja.prepend(el('p',{clase:'aviso-suave',texto:D.cruces.aviso_sin_discriminacion}));
    if(XC.recurso==='refugios')caja.append(el('p',{clase:'micro',texto:D.refugios?.todos?'Todos los refugios, incluidos parques: proximidad potencial a 10 min, suponiendo disponibilidad y acceso. El porcentaje se refiere a toda la población del territorio.':'Refugios: peor hora 20–21 h de un laborable de julio, con acceso supuesto en horario comercial. El porcentaje se refiere a toda la población del territorio.'}));
  }else{
    const campo=nombreVariableSolas(),b=XC.seleccion===null?null:baseBarrio(XC.seleccion);
    caja.append(el('h3',{texto:b?b.nombre:'Personas que viven solas'}));
    if(b)caja.append(el('p',{clase:'sobretitulo',texto:'Barrio seleccionado'}),el('p',{clase:'micro',texto:`Barrio ${b.id}`}),el('div',{clase:'valor-principal',texto:b[campo+'_texto']}),el('p',{clase:'etiqueta-valor',texto:campo==='solas_65_mas'?'personas de 65 años o más que viven solas':'personas que viven solas'}),el('p',{clase:'micro',texto:'Conteo del Padrón a 1 de enero de 2026'}),filaDato('Habitantes · INE 2025',b.poblacion_texto));
    else caja.append(el('p',{clase:'nota',texto:'Selecciona un barrio en el mapa para consultar su conteo. La capa cubre Madrid capital.'}));
    caja.append(el('p',{clase:'micro',texto:'El número de personas que viven solas se mantiene separado de la población de otro año; no se presenta como porcentaje.'}));
  }
};

pintarLeyenda = function(){
  if(!esCapaSocial())return anteriorCruces.leyenda();const caja=$('leyenda');caja.replaceChildren();$('distribucion').replaceChildren();
  if(esCruce()){
    const p=perfilCruce();caja.append(el('div',{clase:'leyenda-titulo',texto:variosContextos()?'Ambos contextos y acceso':'Dos datos, cuatro grupos'}));const matriz=el('div',{clase:'matriz-cruce',role:'group','aria-label':'Filtrar grupos del mapa'});
    for(const g of(XC.social==='renta'?[3,2,1,0]:[2,3,0,1])){const b=el('button',{'data-cruce-grupo':String(g),'aria-pressed':String(XC.grupo===g),style:`background:${D.cruces.paleta_cruces[g]};color:${g===3?'#fff':'#203341'}`},[el('b',{texto:p.leyenda_x[g===1||g===3?1:0]}),el('span',{texto:`${g>=2?'≥':'<'} ${XC.corte} % sin opción`})]);b.addEventListener('click',()=>{XC.grupo=XC.grupo===g?null:g;pintarTodo();});matriz.append(b);}caja.append(matriz);if(XC.recurso==='refugios'){caja.prepend(el('p',{clase:'aviso-suave',texto:p.etiqueta_y}));const r=p.resumen[String(XC.corte)];if(r.grupos[0]+r.grupos[1]===0)caja.prepend(el('p',{clase:'aviso-suave',texto:D.cruces.aviso_sin_discriminacion}));}
    const d=el('div',{clase:'leyenda-detalle'});const todos=el('button',{clase:'enlace',texto:XC.grupo===null?'Todos los grupos':'Mostrar todos'});todos.addEventListener('click',()=>{XC.grupo=null;pintarTodo();});d.append(todos);const gris=el('button',{clase:'enlace',texto:'Gris: evaluación incompleta'});gris.addEventListener('click',()=>{XC.grupo=XC.grupo===-1?null:-1;pintarTodo();});d.append(gris);if(perfilCruce().ambito==='municipio:28079')d.append(el('span',{texto:'Fuera del ámbito (solo Madrid capital): sin relleno'}));caja.append(d);
    $('nota').textContent=p.nota;
  }else{const p=D.cruces.paletas_solas[nombreVariableSolas()];caja.append(el('div',{clase:'leyenda-titulo',texto:nombreVariableSolas()==='solas_65_mas'?'Personas de 65+ que viven solas':'Personas que viven solas'}),...p.etiquetas.map((etiqueta,i)=>filaLeyenda({color:p.colores[i],etiqueta})),el('p',{clase:'micro',texto:'Conteos por barrio · Madrid capital · 2026'}));}
};

actualizarTituloMapa = function(){
  if(!esCapaSocial())return anteriorCruces.titulo();$('mapa-contexto').textContent=esCruce()?'Relacionar datos':'Contexto social · Madrid capital';
  if(esCruce()){const p=perfilCruce();$('mapa-titulo').textContent=p.titulo;$('mapa-subtitulo').textContent=`${p.unidad==='barrio'?'Barrios de Madrid capital':p.ambito==='municipio:28079'?'Secciones de Madrid capital':'Secciones de la Comunidad'} · Corte de acceso: ${XC.corte} %`;}
  else{$('mapa-titulo').textContent=nombreVariableSolas()==='solas_65_mas'?'Mayores de 65 años que viven solos':'Personas que viven solas';$('mapa-subtitulo').textContent='Padrón 2026 · Conteos por barrio';}
};

capaSecciones = function(){
  if(!esCapaSocial())return anteriorCruces.secciones();
  if(esCruce()){
    const p=perfilCruce();filaDeCruce(-1,p);const seccion=p.unidad==='seccion';const data=seccion?D.sec.partes:D.barriosCruces.partes;
    // Conservar ID y geometría al cambiar el indicador: solo se actualizan los colores.
    return new deck.PolygonLayer({id:seccion?'secciones':'contexto-barrios',data,getPolygon:d=>d.p,getFillColor:d=>colorCruce(filaDeCruce(seccion?d.s:d.b,p)),stroked:seccion?!deLejos():true,getLineColor:[255,255,255,230],lineWidthUnits:'pixels',getLineWidth:seccion?.7:1.1,pickable:true,autoHighlight:true,highlightColor:[255,255,255,95],updateTriggers:{getFillColor:[E.variable,XC.social,XC.recurso,XC.modo,XC.corte,XC.grupo]}});
  }
  const campo=nombreVariableSolas(),paleta=D.cruces.paletas_solas[campo];return new deck.PolygonLayer({id:'contexto-barrios',data:D.barriosCruces.partes,getPolygon:d=>d.p,getFillColor:d=>{const c=baseBarrio(d.b)['clase_'+campo];return conAlfa(rgb(c<0?'#AEB9C2':paleta.colores[c]),235);},stroked:true,getLineColor:[255,255,255,235],getLineWidth:1.1,lineWidthUnits:'pixels',pickable:true,autoHighlight:true,highlightColor:[255,255,255,90],updateTriggers:{getFillColor:E.variable}});
};
capaSeleccion = function(){if(!esCapaSocial()||XC.seleccion===null)return anteriorCruces.seleccion();const seccion=esCruce()&&perfilCruce().unidad==='seccion';const data=(seccion?D.sec.partes:D.barriosCruces.partes).filter(d=>(seccion?d.s:d.b)===Number(XC.seleccion));return[new deck.PolygonLayer({id:'cruce-seleccion-borde',data,getPolygon:d=>d.p,filled:false,stroked:true,getLineColor:[255,255,255],getLineWidth:5,lineWidthUnits:'pixels'}),new deck.PolygonLayer({id:'cruce-seleccion',data,getPolygon:d=>d.p,filled:false,stroked:true,getLineColor:[3,64,120],getLineWidth:2.5,lineWidthUnits:'pixels'})];};
tarjetaFlotante = function(info){
  const id=info.layer?.id;if(!['cruce-secciones','cruce-barrios','contexto-barrios'].includes(id)&&!(id==='secciones'&&esCruce()))return anteriorCruces.tooltip(info);if(!info.object)return null;const idx=id==='secciones'||id==='cruce-secciones'?info.object.s:info.object.b;let html;
  if(!esCruce()){const b=baseBarrio(idx),campo=nombreVariableSolas();html=htmlTarjeta(b.nombre,`Barrio ${b.id}`,b[campo+'_texto'],'personas que viven solas · 2026',[campo==='solas_65_mas'?'Personas de 65 años o más':'Todas las edades']);}
  else{const p=perfilCruce(),f=filaDeCruce(idx,p),b=basesCruce(p)[idx];if(!f||!b)return null;html=htmlTarjeta(b.nombre,b.id,f.x_texto,p.etiqueta_x,[...(variosContextos()?[`${f.x_mayores_texto} · 65 años o más que viven solos`]:[]),`${f.y_texto} · ${p.etiqueta_y.replace(/\s*\(%\)/g,'')}`,textoGrupo(claseDeCruce(f),p)]);}
  return{html,style:{backgroundColor:'#fff',color:'#1a1a1a',padding:'12px 16px',borderRadius:'8px',maxWidth:'350px',fontFamily:FUENTE}};
};
alPulsar = function(info){const id=info.layer?.id;if(!info.object)return;if(['cruce-secciones','cruce-barrios','contexto-barrios'].includes(id)||(id==='secciones'&&esCruce())){const idx=id==='secciones'||id==='cruce-secciones'?info.object.s:info.object.b;if(esCruce()&&!filaDeCruce(idx))return;seleccionarCruce(idx,false);return;}anteriorCruces.clic(info);};
function seleccionarCruce(idx,centrar){
  XC.seleccion=Number(idx);const b=esCruce()?basesCruce()[idx]:baseBarrio(idx);if(!b)return;if(D.territorios[b.territorio])E.territorio=b.territorio;$('buscar').value=b.nombre;pintarTodo();
  if(innerWidth<=760&&XC.grafico)cerrarGraficoCruce(false);if(centrar)encuadrar(b.caja);$('territorio').scrollIntoView({behavior:'smooth',block:'nearest'});
}

function abrirGraficoCruce(){XC.grafico=true;XC.autoPlegado=innerWidth>760&&innerWidth<=1100&&!$('panel').classList.contains('plegado');if(XC.autoPlegado){$('panel').classList.add('plegado');document.body.classList.add('panel-oculto');}$('analisis-cruce').hidden=false;document.body.classList.add('cruce-con-grafico');pintarGraficoCruce();encuadrar(D.territorios[perfilCruce().ambito].caja);$('cruce-cerrar').focus();}
function cerrarGraficoCruce(foco=true){XC.grafico=false;const panel=$('analisis-cruce');if(panel)panel.hidden=true;document.body.classList.remove('cruce-con-grafico');if(XC.autoPlegado){$('panel').classList.remove('plegado');document.body.classList.remove('panel-oculto');XC.autoPlegado=false;}if(foco)$('cruce-grafico')?.focus();}
vistaParaCaja = function(caja){if(!esCruce()||!XC.grafico||innerWidth<=760)return anteriorCruces.vista(caja);const w=$('mapa').clientWidth,h=$('mapa').clientHeight,right=$('analisis-cruce').getBoundingClientRect().width+40;return new deck.WebMercatorViewport({width:w,height:h}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],{padding:{left:anchoPanel()+30,right,top:65,bottom:70}});};

function filasFiltradas(p=perfilCruce()){return p.filas.filter(f=>XC.grupo===null||claseDeCruce(f)===XC.grupo);}
function graficoDeSerie(p,rows,base,serie,W){
  const valid=rows.filter(f=>Number.isFinite(f[serie.campo])&&Number.isFinite(f.y)),H=320,L=64,R=22,T=24,B=66,xmin=XC.social==='renta'?1:0,xmax=XC.social==='renta'?5:Math.max(1,...p.filas.map(f=>f[serie.campo]||0));
  const px=x=>L+(x-xmin)/(xmax-xmin)*(W-L-R),py=y=>H-B-y/100*(H-T-B);
  const ticksY=[0,25,50,75,100].map(y=>`<line x1="${L}" x2="${W-R}" y1="${py(y)}" y2="${py(y)}" stroke="#e0e6ea"/><text x="${L-10}" y="${py(y)+4}" text-anchor="end">${y}%</text>`).join('');
  const ticksX=XC.social==='renta'?[1,2,3,4,5]:[0,xmax/2,xmax];
  const puntos=valid.map(f=>{const seleccionado=f.idx===indiceSeleccion();return`<circle data-cruce-idx="${f.idx}" cx="${px(f[serie.campo]).toFixed(2)}" cy="${py(f.y).toFixed(2)}" r="${seleccionado?6:3.2}" fill="${D.cruces.paleta_cruces[claseDeCruce(f)]||'#AEB9C2'}" fill-opacity="${seleccionado?1:.65}" stroke="${seleccionado?'#034078':'#ffffff80'}" stroke-width="${seleccionado?2:.5}"><title>${escapar(base[f.idx].nombre)} · ${escapar(f[serie.texto])} · ${escapar(f.y_texto)}</title></circle>`;}).join('');
  const ejeX=XC.social==='renta'?'Quintil de renta del entorno':variosContextos()?'Personas (número)':serie.etiqueta+' (número)';
  return`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapar(serie.etiqueta)} frente a ${escapar(p.etiqueta_y)}"><g font-family="Segoe UI,Arial,sans-serif" font-size="14" fill="#4d5964">${ticksY}<line x1="${L}" x2="${L}" y1="${T}" y2="${H-B}" stroke="#a9b7c2"/><line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}" stroke="#a9b7c2"/>${ticksX.map(x=>`<text x="${px(x)}" y="${H-B+24}" text-anchor="middle">${XC.social==='renta'?'Q'+x:miles(Math.round(x))}</text>`).join('')}<text x="${(L+W-R)/2}" y="${H-13}" text-anchor="middle">${escapar(ejeX)}</text><text transform="translate(17 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle">Población sin opción (%)</text></g>${puntos}</svg>${valid.length?'':'<p class="nota">No hay valores completos que se puedan representar en este grupo. Puedes consultar los territorios en el listado.</p>'}`;
}
function pintarGraficoCruce(){
  if(!esCruce()||!XC.grafico)return;
  const clave=[XC.social,XC.recurso,XC.modo,XC.corte,XC.grupo,XC.seleccion,$('cruce-dispersion').clientWidth].join('|');
  if(D.claveGraficoCruce===clave)return;D.claveGraficoCruce=clave;
  const p=perfilCruce(),base=basesCruce(p),rows=filasFiltradas(p),series=p.series||[{campo:'x',texto:'x_texto',etiqueta:p.etiqueta_x}],W=Math.max(320,$('cruce-dispersion').clientWidth);
  $('cruce-grafico-descripcion').textContent=`Cada punto es ${p.unidad==='seccion'?'una sección censal':'un barrio'}. ${p.anos}.${variosContextos()?' Ambos gráficos muestran los mismos barrios. Los mayores de 65 están incluidos en el total; no se suman.':''}`;
  $('cruce-dispersion').innerHTML=series.map(s=>series.length>1?`<section class="relacion-serie" data-serie="${s.campo}"><h3>${escapar(s.etiqueta)}</h3>${graficoDeSerie(p,rows,base,s,W)}</section>`:graficoDeSerie(p,rows,base,s,W)).join('');
  const seleccionado=indiceSeleccion(),f=seleccionado===null?null:filaDeCruce(seleccionado,p);$('cruce-seleccion-resumen').hidden=!f;if(f)$('cruce-seleccion-resumen').textContent=`${base[seleccionado].nombre}: ${f.x_texto}${variosContextos()?` · 65 años o más: ${f.x_mayores_texto}`:''} · ${f.y_texto} sin opción verificada.`;
  pintarListadoCruce();
}
function pintarListadoCruce(){
  if(!esCruce())return;const p=perfilCruce(),base=basesCruce(p),normal=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(),q=normal($('cruce-buscar').value);const rows=filasFiltradas(p).filter(f=>normal(`${base[f.idx].nombre} ${base[f.idx].id}`).includes(q)).sort((a,b)=>(b.y??-1)-(a.y??-1)||(b.x??-1)-(a.x??-1));
  $('cruce-listado-cuenta').textContent=`${rows.length} territorios${rows.length>40?' · Se muestran los primeros 40; busca por nombre para localizar otro.':'.'}`;
  $('cruce-listado').classList.toggle('relacion-listado-multiple',variosContextos());
  $('cruce-listado').innerHTML=`<table><thead><tr><th scope="col">Territorio</th><th scope="col">${XC.social==='renta'?'Renta':variosContextos()?'Todas las edades':'Personas solas'}</th>${variosContextos()?'<th scope="col">65 años o más</th>':''}<th scope="col">Sin opción</th><th scope="col">Mapa</th></tr></thead><tbody>${rows.slice(0,40).map(f=>`<tr${f.idx===indiceSeleccion()?' class="fila-seleccionada"':''}><td>${escapar(base[f.idx].nombre)}<small>${escapar(base[f.idx].id)}</small></td><td>${escapar(f.x_texto)}</td>${variosContextos()?`<td>${escapar(f.x_mayores_texto)}</td>`:''}<td>${escapar(f.y_texto)}</td><td><button data-cruce-idx="${f.idx}" aria-label="Ver ${escapar(base[f.idx].nombre)} en el mapa">Ver</button></td></tr>`).join('')}</tbody></table>${rows.length?'':'<p class="nota">No hay territorios con ese nombre en el grupo seleccionado.</p>'}`;
}

function contenidoEquidad(eq){
  return[el('h2',{texto:'¿A qué entornos llega la mejora?'}),el('p',{clase:'nota',texto:'Personas que ganan opción, según el quintil de renta de su sección.'}),...eq.filas.map(f=>el('div',{clase:'barra-fila equidad-fila'},[el('span',{texto:f.etiqueta}),el('span',{clase:'barra',style:`width:${Math.max(0,100*f.fraccion)}%;background:${f.quintil?D.mapa.variables.quintil_renta.paleta[f.quintil-1]:'#aeb9c2'}`}),el('b',{texto:f.texto}),el('small',{texto:f.pct_texto})])),el('p',{clase:'micro',texto:`Total: ${eq.total_texto}. ${eq.nota}`})];
}
pintarComparar = function(){anteriorCruces.comparar();const eq=D.cruces?.equidad[E.cartera];$('equidad-cartera').hidden=!eq;if(eq)$('equidad-cartera').replaceChildren(...contenidoEquidad(eq));};
pintarFicha = function(){anteriorCruces.ficha();const eq=D.cruces?.equidad[E.cartera];$('ficha-equidad').hidden=!eq;if(eq)$('ficha-equidad').replaceChildren(...contenidoEquidad(eq));};
pintarTodo = function(){anteriorCruces.todo();document.body.classList.toggle('en-cruce',esCruce());if(esCapaSocial()){$('nota').textContent=esCruce()?perfilCruce().nota:variableActual().nota;}if(!esCruce()&&XC.grafico)cerrarGraficoCruce(false);pintarGraficoCruce();};
irAPaso = function(paso){if(paso!=='diagnosticar')cerrarGraficoCruce(false);anteriorCruces.paso(paso);};
irATerritorio = function(clave){XC.seleccion=null;anteriorCruces.irATerritorio(clave);};
