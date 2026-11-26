/* Navegación lateral, ficha territorial y leyenda. Las cifras vienen preparadas en Python. */
'use strict';
const PT = {listo:false,abierto:true,drawer:false,leyenda:false,leyendaPlegable:false,leyendaAbierta:false,clave:null,variable:null};
const anteriorTerritorio = {montar:montarInterfaz,todo:pintarTodo,territorio:pintarTerritorio,leyenda:pintarLeyenda,
  ir:irATerritorio,clic:alPulsar,tema:activarTema,vista:vistaParaCaja,desglose:abrirDesglose,grafico:abrirGraficoCruce,cerrarGrafico:cerrarGraficoCruce,seleccionar:seleccionarCruce};

montarInterfaz = function(){
  anteriorTerritorio.montar();
  const ficha=el('aside',{id:'detalle-territorio','aria-label':'Información del territorio seleccionado',tabindex:'-1'});
  ficha.innerHTML=`<div class="pt-cabecera"><div><span id="pt-tipo" class="sobretitulo"></span><h2 id="pt-nombre"></h2><p id="pt-poblacion"></p></div><div class="pt-acciones"><button id="pt-ampliar" aria-expanded="false">Ampliar</button><button id="pt-cerrar" aria-label="Cerrar información territorial">Cerrar</button></div></div>
   <nav class="pt-indice" aria-label="Apartados del territorio"><button data-apartado="pt-primaria">Primaria</button><button data-apartado="pt-calor">Calor</button><button data-apartado="pt-contexto">Contexto</button></nav>
   <button id="pt-3d" class="pt-3d" hidden>Ver todas las capas en 3D</button><div id="pt-contenido"><section id="pt-indicador"><p class="pt-kicker">Indicador del mapa</p><div id="pt-activo"></div></section><div id="pt-seccion"></div>
   <details id="pt-primaria" class="pt-bloque" open><summary>Acceso a atención primaria</summary><p class="nota">Las tres formas de acceso, con sus umbrales y horarios.</p><div id="pt-modos"></div><p class="micro">Proximidad potencial. No mide citas, capacidad ni listas de espera.</p></details>
   <details id="pt-calor" class="pt-bloque"><summary>Refugios y calor</summary><div id="pt-calor-base"></div><div id="pt-refugios"></div><div id="pt-carencias"></div></details>
   <details id="pt-contexto" class="pt-bloque"><summary>Renta del entorno</summary><div id="pt-renta"></div><p class="micro">La renta describe el entorno y no modifica la optimización.</p></details>
   <details class="pt-bloque"><summary>Cómo interpretar y reproducir</summary><div id="pt-interpretacion"></div><p class="nota">A y B no se suman. Un dato desconocido se mantiene como no evaluable. Fuentes y supuestos completos en Datos y Método.</p></details>
   <button id="pt-comparar" class="principal ancho">Comparar actuaciones regionales</button><p class="pt-pie">CercaSalud Madrid · Resultados precalculados</p></div>`;
  document.body.append(ficha);
  const drawer=el('aside',{id:'opciones-mapa','aria-label':'Ajustar mapa',hidden:''});
  drawer.innerHTML='<div class="pt-drawer-titulo"><h2>Ajustar mapa</h2><button id="pt-opciones-cerrar">Cerrar</button></div><div id="pt-filtros"></div><div id="pt-capas"></div>';
  document.body.append(drawer);
  const verLeyenda=el('button',{id:'pt-leyenda-toggle',hidden:'','aria-controls':'leyenda','aria-expanded':'false',texto:'Ver leyenda del mapa'});$('leyenda-mapa').prepend(verLeyenda);
  verLeyenda.addEventListener('click',()=>{PT.leyendaAbierta=!PT.leyendaAbierta;actualizarDisposicion();});
  const poblacion=el('section',{id:'pt-solas'});$('pt-contexto').append(poblacion);$('pt-contexto').querySelector('summary').textContent='Contexto social';
  $('pt-filtros').append($('controles-cruce'));
  const accionesRelacion=el('div',{id:'relacion-acciones',hidden:''});accionesRelacion.append($('cruce-grafico'),$('cruce-csv'));drawer.append(accionesRelacion);
  $('pt-activo').append($('territorio'));$('pt-seccion').append($('zona-senalada'));
  $('pt-interpretacion').append($('nota'),$('distribucion'));
  if($('refugios-ampliados'))$('pt-refugios').append($('refugios-ampliados'));
  for(const id of ['controles-primaria','controles-contexto','alcance-tema'])$('pt-filtros').append($(id));
  for(const d of [...$('vista-diagnosticar').querySelectorAll(':scope>details')]){
    if(d.querySelector('#ver-centros')){d.id='capas-referencia';d.querySelector('summary').textContent='Capas de referencia';d.open=false;$('pt-capas').append(d);}
    else if(d.querySelector('#ir-a')){d.id='mapa-casos';d.open=false;drawer.append(d);}
    else d.hidden=true;
  }
  const r=$('refugios-ampliados');
  if(D.refugios&&r){
  for(const d of [...r.querySelectorAll(':scope>details')]){
    if(d.querySelector('#rf-niveles')||d.querySelector('#rf-aparte')){$('pt-capas').append(d);d.dataset.refugioCapa='1';}
  }
  const verdes=$('rf-aparte').closest('details');verdes.open=false;
  verdes.querySelector('summary').textContent='Capas de referencia';
  $('pt-capas').prepend(verdes);
  const verVerdes=el('button',{id:'pt-ver-verdes',clase:'principal ancho',texto:'Ver zonas verdes de toda la Comunidad'});
  $('rf-aparte').before(verVerdes);
  verVerdes.addEventListener('click',verZonasVerdesComunidad);
  }
  $('pt-contenido').append($('vista-desglose'));
  $('vista-diagnosticar').querySelector('.etiqueta-seccion').hidden=true;
  const acciones=el('div',{clase:'pt-rail-acciones'});
  const nuevo=(id,texto,dibujo)=>el('button',{id,clase:'pt-rail-boton','aria-label':texto},[el('span',{clase:'pt-rail-icono',texto:dibujo}),el('span',{texto})]);
  const opciones=nuevo('pt-opciones','Mapa','☷');opciones.setAttribute('aria-expanded','false');opciones.setAttribute('aria-controls','opciones-mapa');
  const informacion=nuevo('pt-informacion','Información','i');informacion.setAttribute('aria-expanded','true');informacion.setAttribute('aria-controls','detalle-territorio');
  const general=nuevo('pt-general','Vista general','◎');general.setAttribute('title','Ver toda la Comunidad de Madrid');general.setAttribute('aria-label','Ver toda la Comunidad de Madrid');
  const cruces=$('abrir-cruces');cruces.className='pt-rail-boton';cruces.innerHTML='<span class="pt-rail-icono">⊞</span><span>Relacionar<br>datos</span>';cruces.setAttribute('aria-controls','opciones-mapa');cruces.setAttribute('title','Relacionar contexto social y acceso a recursos');
  $('ver-actuaciones').className='pt-rail-boton';
  acciones.append(opciones,cruces,informacion,general,$('ver-actuaciones'));
  $('temas').after(acciones);
  $('pie-panel')?.remove();
  $('vista-diagnosticar').querySelector('.pie-panel').hidden=true;
  $('pt-opciones').addEventListener('click',()=>abrirOpciones(!PT.drawer));
  $('pt-opciones-cerrar').addEventListener('click',()=>abrirOpciones(false));
  $('pt-informacion').addEventListener('click',()=>{if(esCruce()&&PT.drawer){abrirOpciones(false);abrirDetalle(true);}else abrirDetalle(!PT.abierto);});
  $('pt-cerrar').addEventListener('click',()=>{abrirDetalle(false);$('pt-informacion').focus();});
  $('pt-ampliar').addEventListener('click',()=>{document.body.classList.toggle('detalle-ampliado');$('pt-ampliar').textContent=document.body.classList.contains('detalle-ampliado')?'Ver mapa':'Ampliar';$('pt-ampliar').setAttribute('aria-expanded',String(document.body.classList.contains('detalle-ampliado')));});
  $('pt-general').addEventListener('click',()=>{PT.leyendaPlegable=true;PT.leyendaAbierta=false;abrirOpciones(false);cerrarGraficoCruce(false);if(E.paso!=='diagnosticar')iniciarVista();irATerritorio('comunidad:28');$('buscar').value='';if(innerWidth<=760){abrirDetalle(false);encuadrar(D.territorios['comunidad:28'].caja,false);}});
  $('pt-comparar').addEventListener('click',()=>$('ver-actuaciones').click());
  $('pt-3d').addEventListener('click',()=>abrirDesglose(E.territorio));
  document.querySelectorAll('[data-apartado]').forEach(b=>b.addEventListener('click',()=>{
    const d=$(b.dataset.apartado);d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'});
  }));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&PT.drawer){abrirOpciones(false);$('pt-opciones').focus();}});
  PT.listo=true;actualizarFicha();actualizarDisposicion();
};

function abrirOpciones(abierto){if(abierto&&XC.grafico)cerrarGraficoCruce(false);PT.drawer=abierto;$('opciones-mapa').hidden=!abierto;$('pt-opciones').setAttribute('aria-expanded',String(abierto));actualizarDisposicion();if(abierto){$('pt-opciones-cerrar').focus();$('pt-filtros').scrollTop=0;if(esCruce())encuadrar(D.territorios[E.territorio].caja,false);}}
function abrirDetalle(abierto=true){PT.abierto=abierto;actualizarDisposicion();}
abrirPanelMovil = function(ampliar=false){abrirDetalle(true);document.body.classList.toggle('detalle-ampliado',ampliar);$('pt-ampliar').textContent=ampliar?'Ver mapa':'Ampliar';$('pt-ampliar').setAttribute('aria-expanded',String(ampliar));};

function actualizarDisposicion(){
  if(!PT.listo)return;
  const configurando=esCruce()&&PT.drawer;
  const visible=PT.abierto&&E.paso==='diagnosticar'&&!XC.grafico&&!configurando;
  $('detalle-territorio').hidden=!visible;document.body.classList.toggle('detalle-visible',visible);
  document.body.classList.toggle('relacion-configurando',configurando);
  $('opciones-mapa').querySelector('h2').textContent=esCruce()?'Relacionar datos':`Ajustar mapa · ${textosMapa().temas[U.tema]||'Mapa'}`;
  $('opciones-mapa').setAttribute('aria-label',esCruce()?'Relacionar contexto social y acceso a recursos':'Ajustar mapa');
  $('pt-opciones-cerrar').textContent=esCruce()?'Ver mapa':'Cerrar';
  $('relacion-acciones').hidden=!esCruce();
  const leyendaRegional=PT.leyendaPlegable&&E.territorio==='comunidad:28'&&E.paso==='diagnosticar'&&!E.desglose;
  $('pt-leyenda-toggle').hidden=!leyendaRegional;$('pt-leyenda-toggle').textContent=PT.leyendaAbierta?'Ocultar leyenda':'Ver leyenda del mapa';$('pt-leyenda-toggle').setAttribute('aria-expanded',String(PT.leyendaAbierta));
  $('leyenda-mapa').classList.toggle('leyenda-compacta',leyendaRegional&&!PT.leyendaAbierta);
  document.body.classList.toggle('en-carencias',E.paso==='diagnosticar'&&E.variable==='carencias');
  $('pt-informacion').setAttribute('aria-expanded',String(visible));
  $('opciones-mapa').hidden=!PT.drawer||E.paso!=='diagnosticar'||Boolean(E.desglose);
  for(const d of document.querySelectorAll('[data-refugio-capa]'))d.hidden=U.tema!=='refugios';
  $('capas-referencia').hidden=!['primaria','carencias'].includes(U.tema);
  $('ver-centros').closest('label').hidden=!['primaria','carencias'].includes(U.tema);
  $('ver-mercados').closest('label').hidden=U.tema!=='carencias';
  $('pt-filtros').querySelector('.casos')?.setAttribute('data-atajos','');
  $('ver-actuaciones').hidden=false;$('ver-actuaciones').textContent='Comparar';
  $('pt-comparar').textContent=U.tema==='refugios'?'Comparar ampliaciones de horario':'Comparar actuaciones regionales';
  $('pt-3d').hidden=E.variable==='carencias'||D.territorios[E.territorio].tipo==='comunidad'||Boolean(E.desglose);
  for(const [i] of (D.refugios?.niveles||[]).entries())$(`rf-nivel-${i}`).checked=E.niveles.has(i);
  for(const clave of ['parques','refresco'])if($(`rf-${clave}`))$(`rf-${clave}`).checked=E[clave];
  $('abrir-cruces').setAttribute('aria-pressed',String(esCruce()));
  const subterritorio=esCapaSocial()&&XC.seleccion!==null;
  $('territorio').classList.toggle('pt-subterritorio',subterritorio);
  $('pt-indicador').querySelector('.pt-kicker').textContent=E.variable==='carencias'?'Resumen disponible':subterritorio?'Detalle de la selección en el mapa':'Indicador del mapa';
  const capital=E.territorio==='municipio:28079';
  if($('refugios-ampliados')){
  $('refugios-ampliados').hidden=!capital;
  $('rf-coberturas').hidden=!capital;
  $('refugios-ampliados').querySelector('.rf-aviso').textContent=U.tema==='refugios'?'El color por sección conserva la cobertura de los 43 mercados en julio. Los filtros cambian solo las cifras de este panel.':'Este resumen de calor corresponde a Madrid capital. Sus filtros no cambian la capa que estás viendo en el mapa.';
  }
  // El desglose antiguo vive ahora en la ficha; no debe trasladar el resumen activo al bloque de calor.
  if($('territorio').parentElement!==$('pt-activo'))$('pt-activo').append($('territorio'));
}

function actualizarFicha(){
  if(!PT.listo)return;
  const t=D.territorios[E.territorio],p=D.detalleTerritorios.perfiles[E.territorio];
  if(!t||!p)return;
  $('pt-tipo').textContent=t.tipo==='comunidad'?'Panorama regional':t.tipo==='distrito'?'Distrito de Madrid':'Localidad seleccionada';
  $('pt-nombre').textContent=t.nombre;$('pt-poblacion').textContent=`${t.poblacion} habitantes · INE 2025`;
  if(PT.clave===E.territorio)return;
  PT.clave=E.territorio;
  $('pt-modos').replaceChildren(...[['pie','A pie','15 min · 3,0 km/h'],['transporte','A pie o transporte','30 min · 9–13 h'],['transporte_16_20','A pie o transporte','30 min · 16–20 h']].map(([k,n,h])=>{
    const m=t.modos[k];return el('article',{clase:'pt-modo'},[el('div',{},[el('strong',{texto:n}),el('p',{clase:'micro',texto:h})]),el('b',{texto:m.con_acceso}),el('p',{clase:'pt-modo-extra',texto:`${etiquetaFuera(k)}: ${m.sin_opcion} (${m.sin_opcion_pct}) · No evaluable: ${m.no_evaluable}`})]);
  }));
  $('pt-calor-base').replaceChildren(el('p',{clase:'nota',texto:p.refugios_base?`${p.refugios_base}. Base de 43 mercados, laborable de julio; acceso supuesto en horario comercial.`:'No evaluable con un inventario verificado para este territorio. No significa ausencia de refugios.'}));
  if(t.tipo==='distrito'||t.tipo==='comunidad'){
    const b=el('button',{clase:'pt-enlace',texto:'Ver la ampliación de Madrid capital'});b.addEventListener('click',()=>{irATerritorio('municipio:28079');$('pt-calor').open=true;$('refugios-ampliados').scrollIntoView({block:'start'});});
    $('pt-calor-base').append(el('p',{clase:'micro',texto:'Los resultados ampliados no están desglosados por distrito ni por el conjunto de la Comunidad.'}),b);
  }
  $('pt-carencias').replaceChildren(el('h3',{texto:'Carencias coincidentes · Madrid capital'}),...(E.territorio==='municipio:28079'||t.tipo==='comunidad'?D.textos.b_c.c:['El resumen de carencias coincidentes solo está disponible para Madrid capital, sin desglose para este territorio.']).map(texto=>el('p',{clase:'nota',texto})));
  $('pt-renta').replaceChildren(el('h3',{texto:'Renta del entorno · ADRH 2024'}),el('p',{clase:'nota',texto:'Población por quintil de renta de la sección. Los cortes se fijan en la Comunidad de Madrid.'}),...p.renta.filas.map(f=>el('div',{clase:'pt-quintil'},[el('span',{texto:`Q${f.quintil}`}),el('div',{clase:'pt-quintil-pista'},el('i',{style:`width:${100*f.fraccion}%;background:${f.color}`})),el('b',{texto:f.porcentaje})])),el('p',{clase:'micro',texto:`${p.renta.secciones} secciones · Renta sin dato: ${p.renta.sin_dato} habitantes.`}));
  const calidad=p.renta.calidad,cotas=(calidad.cota_superior||0)+(calidad.cota_inferior||0);
  $('pt-renta').append(el('p',{clase:'pt-renta-calidad',texto:`El Q3 es el tramo central y tiene datos. Calidad en este territorio: ${calidad.dato||0} secciones con valor publicado, ${cotas} con una cota por secreto estadístico y ${calidad.media_comarca||0} con media de la comarca, sin valor propio.`}));
  $('pt-solas').replaceChildren(el('h3',{texto:'Personas que viven solas · 2026'}));
  if(p.personas_solas){
    const s=p.personas_solas;$('pt-solas').append(el('p',{clase:'micro',texto:`Ámbito: ${s.ambito} · ${s.barrios} barrios`}),filaDato('Todas las edades',s.total),filaDato('65 años o más',s.mayores),el('p',{clase:'nota',texto:'Conteos del Padrón 2026. Se mantienen separados de la población de 2025; no se presentan como tasas.'}));
  }else $('pt-solas').append(el('p',{clase:'nota',texto:'Esta capa solo cubre los barrios de Madrid capital. No hay un conteo comparable exportado para esta localidad.'}));
}

pintarTerritorio = function(){anteriorTerritorio.territorio();actualizarFicha();};
pintarTodo = function(){
  sincronizarControles();pintarTerritorio();pintarLeyenda();
  // Las vistas ocultas no se reconstruyen en cada cambio de indicador o selección.
  if(E.paso!=='diagnosticar')pintarComparar();
  if(E.paso==='ficha')pintarFicha();
  actualizarTituloMapa();$('nota').textContent=esCruce()?perfilCruce().nota:variableActual().nota||'';
  document.body.classList.toggle('en-cruce',esCruce());
  if(!esCruce()&&XC.grafico)cerrarGraficoCruce(false);
  pintarMapa();pintarGraficoCruce();actualizarFicha();actualizarDisposicion();
};
irATerritorio = function(clave){if(!D.territorios[clave])return;PT.abierto=true;salirDel3d();E.territorio=clave;E.seccion=null;XC.seleccion=null;$('zona-senalada').hidden=true;$('buscar').value=D.territorios[clave].nombre;pintarTodo();encuadrar(D.territorios[clave].caja,false);if(PT.listo)$('pt-contenido').scrollTop=0;};
alPulsar = function(info){anteriorTerritorio.clic(info);if(!info.object||E.desglose)return;PT.abierto=true;actualizarFicha();actualizarDisposicion();if(E.seccion!==null){$('pt-contenido').prepend($('pt-seccion'));$('pt-contenido').scrollTop=0;}else if(XC.seleccion!==null)$('pt-contenido').scrollTop=0;};
function iniciarVista(){salirDel3d();E.seccion=null;XC.seleccion=null;XC.grupo=null;$('zona-senalada').hidden=true;E.centros=false;E.mercados=false;cerrarGraficoCruce(false);E.paso='diagnosticar';PT.abierto=true;document.body.classList.remove('comparando','en-ficha');$('vista-diagnosticar').hidden=false;$('vista-comparar').hidden=true;$('vista-ficha').hidden=true;document.querySelectorAll('[data-paso]').forEach(b=>{b.setAttribute('aria-selected',String(b.dataset.paso==='diagnosticar'));b.tabIndex=b.dataset.paso==='diagnosticar'?0:-1;});}
activarTema = function(tema){
  if(tema==='refugios'&&!D.refugios){avisarCarga(D.fallos.refugios||'datos/capas/refugios.json');return;}
  iniciarVista();PT.leyendaPlegable=false;U.tema=tema;
  if(tema==='primaria'){E.variable=variableDeControles();XC.vista='renta';}
  if(tema==='contexto'){if(CT.dato==='solas'&&!D.cruces)CT.dato='renta';E.variable=variableDeContexto();XC.vista=E.variable==='quintil_renta'?'renta':E.variable;if(CT.dato==='solas'){E.territorio='municipio:28079';$('buscar').value='Madrid';}}
  if(tema==='refugios'||tema==='carencias'){
    E.variable=tema==='refugios'?'refugio':'carencias';
    if(tema==='refugios'){E.parques=true;E.territorio='comunidad:28';if(innerWidth<=760)PT.abierto=false;}
    else E.territorio='municipio:28079';
    $('buscar').value=D.territorios[E.territorio].nombre;
    if(tema==='refugios'&&!RF.iniciado){E.niveles=new Set([0,1]);RF.iniciado=true;}
  }
  abrirOpciones(false);pintarTodo();
  encuadrar(D.territorios[E.territorio].caja,false);
  ordenarCifrasTema();
  if(tema==='carencias')$('pt-contenido').scrollTo({top:0,behavior:'instant'});
};
function verZonasVerdesComunidad(){activarTema('refugios');}
function ordenarCifrasTema(){
  const id=U.tema==='refugios'||U.tema==='carencias'?'pt-calor':U.tema==='contexto'?'pt-contexto':'pt-primaria';
  for(const clave of ['pt-primaria','pt-calor','pt-contexto'])$(clave).open=clave===id;
  $('pt-indicador').after($(id));
  $('pt-contenido').scrollTop=0;
}
function activarCruces(){if(!D.cruces){avisarCarga(D.fallos.cruces||D.fallos.barrios||'datos/cruces.json');return;}iniciarVista();PT.leyendaPlegable=false;U.tema='cruces';XC.vista='cruce';E.variable='cruce';if(perfilCruce().ambito==='municipio:28079'&&E.territorio!=='municipio:28079'&&!E.territorio.startsWith('distrito:'))E.territorio='municipio:28079';$('buscar').value=E.territorio==='comunidad:28'?'':D.territorios[E.territorio].nombre;encuadrar(D.territorios[E.territorio].caja,false);pintarTodo();abrirOpciones(true);}
sincronizarControles = function(){
  const sola=['solas_total','solas_65_mas'].includes(E.variable);
  if(!esCapaSocial())anteriorCruces.sincronizar();else U.tema=esCruce()?'cruces':'contexto';
  if(E.paso==='diagnosticar'&&(sola||E.variable==='quintil_renta')){CT.dato=sola?'solas':'renta';if(sola)CT.edad=E.variable==='solas_65_mas'?'65':'total';}
  $('controles-primaria').hidden=U.tema!=='primaria';
  $('controles-contexto').hidden=U.tema!=='contexto';
  $('contexto-dato').value=CT.dato;$('contexto-edad').value=CT.edad;
  $('campo-contexto-edad').hidden=CT.dato!=='solas';
  $('controles-cruce').hidden=!esCruce();
  document.querySelectorAll('[data-tema]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tema===U.tema)));
  $('ver-centros').checked=E.centros;$('ver-mercados').checked=E.mercados;
  $('alcance-tema').hidden=U.tema==='primaria';
  if(esCruce()){
    const p=perfilCruce();$('cruce-social').value=XC.social;$('cruce-recurso').value=XC.recurso;$('cruce-modo').value=XC.modo;$('cruce-corte').value=String(XC.corte);$('campo-cruce-modo').hidden=XC.recurso!=='primaria';$('cruce-csv').href=p.csv;
    sincronizarContextosCruce();$('alcance-tema').textContent=`${p.anos} · ${p.unidad==='barrio'?'Barrios de Madrid capital':'Secciones censales'}`;
  }else if(U.tema==='contexto')$('alcance-tema').textContent=CT.dato==='solas'?textosMapa().contexto_solas:textosMapa().contexto_renta;
  else if(U.tema==='refugios')$('alcance-tema').textContent=textosMapa().mapa_refugios;
  else if(U.tema==='carencias')$('alcance-tema').textContent=textosMapa().mapa_carencias;
};
abrirDesglose = function(clave){PT.abierto=true;anteriorTerritorio.desglose(clave);actualizarDisposicion();};
abrirGraficoCruce = function(){abrirOpciones(false);anteriorTerritorio.grafico();if(XC.autoPlegado){$('panel').classList.remove('plegado');document.body.classList.remove('panel-oculto');XC.autoPlegado=false;}actualizarDisposicion();};
cerrarGraficoCruce = function(foco=true){anteriorTerritorio.cerrarGrafico(false);actualizarDisposicion();if(foco)$('abrir-cruces')?.focus();};
seleccionarCruce = function(idx,centrar){if(esCruce())abrirOpciones(false);anteriorTerritorio.seleccionar(idx,centrar);};
anchoPanel = function(){return E.paso==='comparar'?$('vista-comparar').getBoundingClientRect().width+24:innerWidth<=760?0:124;};
vistaParaCaja = function(caja){
  if(E.paso==='comparar'){
    const mapa=$('mapa'),r=mapa.getBoundingClientRect(),w=mapa.clientWidth,h=mapa.clientHeight;
    const visible=n=>n&&!n.hidden&&n.getBoundingClientRect().width>0;
    const panel=$('vista-comparar').getBoundingClientRect(),titulo=$('resumen-mapa').getBoundingClientRect();
    const leyenda=visible($('leyenda-mapa'))?$('leyenda-mapa').getBoundingClientRect():null;
    const movil=innerWidth<=760;
    const padding=movil?{
      left:18,right:18,top:Math.max(20,titulo.bottom-r.top+16),
      bottom:Math.max(30,r.bottom-panel.top+16,leyenda?r.bottom-leyenda.top+16:0)
    }:{
      left:Math.max(24,panel.right-r.left+18),right:24,
      top:Math.max(24,titulo.bottom-r.top+18),bottom:Math.max(30,leyenda?r.bottom-leyenda.top+18:0)
    };
    // Pantallas bajas: conservar una ventana cartográfica válida aunque los paneles ocupen mucho alto.
    if(padding.top+padding.bottom>h-80){const k=(h-80)/(padding.top+padding.bottom);padding.top*=k;padding.bottom*=k;}
    return new deck.WebMercatorViewport({width:w,height:h}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],{padding});
  }
  if(E.paso!=='diagnosticar')return anteriorTerritorio.vista(caja);
  const w=$('mapa').clientWidth,h=$('mapa').clientHeight,movil=innerWidth<=760;
  const region=D.territorios['comunidad:28'].caja.every((n,i)=>Math.abs(n-caja[i])<.000001);
  const opciones=PT.drawer&&!E.desglose,relacion=esCruce();
  const panelDerecho=XC.grafico?$('analisis-cruce'):opciones&&relacion?$('opciones-mapa'):PT.abierto?$('detalle-territorio'):null;
  const derecha=!movil&&panelDerecho&&!panelDerecho.hidden?panelDerecho.getBoundingClientRect().width+36:30;
  const izquierda=movil?20:opciones&&!relacion?$('opciones-mapa').getBoundingClientRect().right+18:124;
  const leyenda=PT.listo&&!$('leyenda-mapa').hidden?$('leyenda-mapa').getBoundingClientRect().height:150;
  const abajo=movil?(PT.abierto?Math.min(h*.43,330):leyenda+24):region&&(innerHeight<900||U.tema==='refugios'&&E.parques)?leyenda+24:region?44:210;
  return new deck.WebMercatorViewport({width:w,height:h}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],{padding:{left:izquierda,right:derecha,top:movil?98:region?28:100,bottom:Math.min(abajo,h-150)}});
};

pintarLeyenda = function(){
  anteriorTerritorio.leyenda();
  if(esCapaSocial()&&esCruce())return;
  if(modoCambia()||E.variable==='carencias')return;
  if(U.tema==='refugios'&&E.parques&&D.refugios){
    $('leyenda').replaceChildren(el('div',{clase:'pt-leyenda-top'},el('div',{},[el('h2',{clase:'leyenda-titulo',texto:'Zonas verdes · Comunidad de Madrid'}),el('p',{clase:'pt-leyenda-contexto',texto:'Espacios abiertos; no son refugios ni entran en las coberturas.'})])),el('div',{clase:'pt-verdes-clases'},D.refugios.clases_parques.map(c=>el('div',{clase:'pt-tramo'},[el('i',{style:`background:${c.color}`}),el('span',{texto:c.etiqueta})]))),el('p',{clase:'pt-leyenda-contexto',texto:'Cobertura de mercados, solo Madrid capital: rojo, menos horas; azul, más horas.'}));
    return;
  }
  const v=variableActual(),social=esCapaSocial(),paleta=social?D.cruces.paletas_solas[nombreVariableSolas()]:null;
  const colores=paleta?paleta.colores:v.paleta,etiquetas=paleta?paleta.etiquetas:v.etiquetas;
  if(!colores?.length)return;
  const minutos=E.variable.startsWith('min_'),renta=E.variable==='quintil_renta',refugio=E.variable==='refugio',porcentaje=E.variable.startsWith('pct_');
  const titulo=minutos?'Tiempo hasta atención primaria':renta?'Renta neta por persona':refugio?'Horas con un mercado próximo':porcentaje?etiquetaPorcentaje(v.modo):v.titulo;
  const contexto=minutos?(v.modo==='pie'?'A pie · 3,0 km/h':`A pie o transporte · ${v.modo==='transporte_16_20'?'16–20':'9–13'} h`):renta?'Quintiles regionales · INE, ADRH 2024':refugio?'43 mercados · Madrid capital · Julio, 12–21 h':porcentaje?`Color por sección censal · ${v.modo==='pie'?'A pie':'A pie o transporte · 9–13 h'}`:'Conteos por barrio · Madrid capital · 2026';
  const caja=$('leyenda');caja.replaceChildren(el('div',{clase:'pt-leyenda-top'},[el('div',{},[el('h2',{clase:'leyenda-titulo',texto:titulo}),el('p',{clase:'pt-leyenda-contexto',texto:contexto})]),el('span',{clase:'pt-escala',texto:renta?'2024':'Escala fija'})]));
  const escala=el('div',{clase:'pt-escala-color',role:'img','aria-label':etiquetas.map((e,i)=>`${e}: ${colores[i]}`).join('; ')});
  escala.append(...colores.map((c,i)=>el('span',{style:`background:${c}`,title:etiquetas[i]})));
  if(minutos){const posicion=100*(v.umbral_tras+1)/colores.length;escala.append(el('i',{clase:'pt-umbral',style:`left:${posicion}%`,'aria-label':`Umbral ${v.umbral} minutos`}));}
  caja.append(escala);
  let marcas=minutos?[etiquetas[0],`${v.umbral} min`,etiquetas.at(-1)+' min']:renta?['Q1 · Menor renta','Q3','Q5 · Mayor renta']:refugio?['0 h','2–4 h','>6 h']:porcentaje?['0 %','5–10 %','>50 %']:[etiquetas[0],'',etiquetas.at(-1)];
  const ticks=el('div',{clase:'pt-marcas'},marcas.map((texto,i)=>el('strong',{clase:i===1?'pt-marca-central':'',texto})));
  if(minutos)ticks.style.setProperty('--corte',`${100*(v.umbral_tras+1)/colores.length}%`);
  caja.append(ticks);
  const pie=el('div',{clase:'pt-leyenda-pie'});
  pie.append(el('span',{texto:minutos?`Marca: umbral de acceso de ${v.umbral} min`:renta?'Q3: tramo central con dato. Calidad en la ficha.':refugio?'Media de horas por sección':'Tramos de color del mapa'}),el('span',{clase:'pt-sin-dato'},[el('i'),el('abbr',{title:'Los datos disponibles no permiten determinar el acceso; no significa ausencia de servicio.',texto:renta?'Sin dato':'No evaluable'})]));
  caja.append(pie);
  const detalle=el('details',{clase:'pt-leyenda-detalle'});detalle.open=PT.leyenda;
  detalle.append(el('summary',{texto:'Ver todos los tramos'}),...etiquetas.map((texto,i)=>el('div',{clase:'pt-tramo'},[el('i',{style:`background:${colores[i]}`}),el('span',{texto})])));
  detalle.addEventListener('toggle',()=>{PT.leyenda=detalle.open;});caja.append(detalle);
};
