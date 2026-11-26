/* Escenario ampliado: parques y piscinas incluidos; fuentes de agua excluidas.
   Las coberturas y clases se calculan en Python/R5; aquí solo se seleccionan y dibujan. */
'use strict';
const RT = {edad:'total'};
const previoRT = {leer:leerRefugios,montar:montarInterfaz,tema:activarTema,territorio:pintarTerritorio,
  ficha:actualizarFicha,leyenda:pintarLeyenda,titulo:actualizarTituloMapa,valor:valorSeccion,
  tarjeta:tarjetaSeccion,secciones:capaSecciones,parques:capaParques,todo:pintarTodo,
  comparar:pintarComparar,puntos:capasPuntos,modales:montarModales,desglose:capasDeDesglose};
function datosRT(){return D.refugios?.todos;}
function resumenRT(){const d=datosRT();return d?.territorios[E.territorio]?.[RT.edad]||d?.territorios['comunidad:28'][RT.edad];}
function edadRT(){return RT.edad==='total'?'Todas las edades':`${RT.edad} años`;}
leerRefugios = async function(){const r=await previoRT.leer();r.todos=await leer('datos/refugios_todos.json');return r;};
function aplicarRT(){
  const d=datosRT();if(!d)return;
  D.sec.refugio_mercados_horas ||= D.sec.refugio;
  D.sec.k_refugio_mercados_horas ||= D.sec.k_refugio;
  D.sec.refugio=d.secciones[RT.edad].filas.map(r=>r?.pct??null);
  D.sec.k_refugio=d.secciones[RT.edad].clases;
  D.sec.paletas.refugio=d.paleta.map(rgb);
  const titulo='Población con refugio a 10 min (%)';
  D.mapa.variables.refugio={titulo,escala:'celdas',paleta:d.paleta,etiquetas:d.etiquetas,nota:d.nota};
  D.mapa.desglose_refugio={capa:'refugio',nombre:titulo,texto:d.nota,paleta:d.paleta,etiquetas:d.etiquetas,
    por_territorio:Object.fromEntries(Object.entries(d.territorios).map(([k,r])=>[k,`${r[RT.edad].texto.con} personas (${r[RT.edad].pct_texto}) con refugio potencial`]))};
  D.refugios.casillas.parques='Parques, jardines, áreas recreativas y monte o bosque · Refugios al aire libre';
  D.refugios.casillas.refresco='Piscinas (refugios) y fuentes (solo hidratación)';
  D.refugios.casillas.bibliotecas='Bibliotecas de otros municipios · Incluidas en la cobertura';
  D.refugios.texto_aparte='Parques y piscinas se incluyen como refugios. Las fuentes solo son hidratación y no aportan cobertura.';
  D.refugios.aparte.parque.aviso='Refugio al aire libre del escenario ampliado. Acceso y sombra no verificados; cobertura por contactos con la red peatonal.';
  D.refugios.aparte.fuente.aviso='Solo hidratación. No cuenta como refugio ni aporta cobertura.';
  D.refugios.aparte.piscina.aviso='Refugio y punto de refresco del escenario ampliado; consulta horario y condiciones de acceso.';
  D.refugios.bibliotecas_cm.aviso='Incluida en la cobertura potencial. La ubicación no acredita climatización ni apertura.';
}
function tarjetaResumenRT(r,titulo){
  return [el('p',{clase:'etiqueta-valor',texto:titulo}),el('div',{clase:'valor-principal',texto:r.pct_texto}),
    filaDato('Personas con un refugio a 10 min',r.texto.con),filaDato('Sin opción potencial a 10 min',r.texto.sin),
    filaDato('No evaluable por conexión o enlace',r.texto.no_evaluable),
    el('p',{clase:'nota',texto:`${miles(datosRT().inventario.total)} refugios: equipamientos, bibliotecas, parques y piscinas. Las fuentes de agua quedan excluidas. Cada persona cuenta una vez.`}),
    el('p',{clase:'micro',texto:'Cobertura potencial · 3,0 km/h · '+edadRT()+'. Supone disponibilidad y acceso sin restricciones.'})];
}
pintarCifrasRefugios = function(){
  if(!datosRT()||!$('rf-lineas'))return;
  const r=resumenRT();$('rf-ambito').textContent=`${D.territorios[E.territorio]?.nombre||'Comunidad de Madrid'} · ${edadRT()}`;
  $('rf-lineas').replaceChildren(...tarjetaResumenRT(r,'Cobertura potencial · Todos los refugios'));
};
montarInterfaz = function(){
  aplicarRT();previoRT.montar();if(!datosRT())return;aplicarRT();
  const d=datosRT(),n=d.inventario;
  const section=$('refugios-ampliados');section.querySelector('.rf-cabecera .micro').textContent='Comunidad de Madrid · Inventario completo';
  const intro=$('rf-coberturas').querySelector(':scope>p.nota');intro.textContent=`${miles(n.total)} refugios: ${miles(n.equipamientos)} equipamientos, ${miles(n.bibliotecas_comunidad)} bibliotecas de otros municipios, ${miles(n.zonas_verdes)} zonas verdes y ${miles(n.piscinas)} piscinas. Las ${miles(d.fuentes_hidratacion)} fuentes de agua no cuentan.`;
  $('rf-coberturas').querySelector('.rf-filtros').hidden=true;
  const label=el('label',{clase:'campo',texto:'Población'}),select=el('select',{id:'rt-edad'});
  for(const [value,texto]of[['total','Todas las edades'],['65+','65 años o más'],['75+','75 años o más']])select.append(el('option',{value,texto}));
  label.append(select);$('rf-ambito').before(label);
  select.addEventListener('change',()=>{RT.edad=select.value;aplicarRT();pintarTodo();if(E.seccion!==null)mostrarZonaSenalada(E.seccion);});
  section.querySelector('.rf-aviso').textContent=d.nota;
  $('rf-niveles').closest('details').querySelector('summary').textContent='Refugios interiores · Nivel de evidencia';
  $('rf-niveles').closest('details').querySelector('p.nota').textContent='Todos los niveles cuentan en la cobertura potencial. Estas casillas solo cambian la visibilidad del mapa.';
  const outdoor=$('rf-aparte').closest('details');outdoor.querySelector('summary').textContent='Refugios al aire libre e hidratación';
  outdoor.querySelector('p.nota').textContent='Parques y piscinas cuentan como refugios. Las fuentes solo se muestran para hidratación y no entran en el cálculo.';
  outdoor.querySelector('p.micro').textContent=`${miles(n.piscinas)} piscinas y ${miles(n.zonas_verdes)} zonas verdes incluidas · ${miles(d.fuentes_hidratacion)} fuentes excluidas. Los polígonos partidos se cuentan como un solo recurso.`;
  $('rf-metodo').textContent=d.nota;
  $('rf-limites').replaceChildren(el('li',{texto:'Parques: acceso por la red peatonal cartografiada; no se han verificado entradas, sombra ni condiciones de uso.'}),el('li',{texto:'La cobertura es de proximidad potencial y no acredita la disponibilidad real. Los fallos de conexión o enlace se conservan como no evaluables.'}));
  const link=section.querySelector('.rf-descarga');link.href='datos/descargas/refugios_todos_territorios.csv';link.textContent='Descargar cobertura de todos los refugios (CSV)';
  const method=$('rf-metodo').closest('details');for(const p of method.querySelectorAll(':scope>p.nota'))if(p.id!=='rf-metodo')p.textContent='Las comparaciones B1 de horarios se conservan como referencia del escenario anterior de mercados; no representan este escenario de disponibilidad total.';
  const bib=$('rf-bibliotecas')?.closest('.rf-bibliotecas');if(bib)bib.querySelector('p.nota').textContent='Bibliotecas incluidas en la cobertura potencial. Consulta la evidencia y el horario en cada ficha.';
  $('ver-actuaciones').dataset.refugiosReferencia='1';
  if(new URLSearchParams(location.search).get('vista')==='refugios')setTimeout(()=>activarTema('refugios'),0);
};
activarTema = function(tema){
  if(tema==='refugios'&&datosRT()){RF.iniciado=true;E.niveles=new Set([0,1,2]);E.refresco=true;E.bibliotecasCM=true;}
  previoRT.tema(tema);
  if(tema==='refugios'&&datosRT()){E.niveles=new Set([0,1,2]);E.refresco=true;E.bibliotecasCM=true;pintarTodo();}
};
pintarTerritorio = function(){
  if(!datosRT()||!['refugios','carencias'].includes(U.tema)||E.paso!=='diagnosticar')return previoRT.territorio();
  const r=resumenRT();actualizarFicha();
  if(U.tema==='refugios')$('territorio').replaceChildren(...tarjetaResumenRT(r,'Población con refugio potencial a 10 min'));
  else $('territorio').replaceChildren(el('p',{clase:'etiqueta-valor',texto:'Carencias coincidentes · Escenario ampliado'}),
    el('div',{clase:'valor-principal',texto:r.texto.carencias}),el('p',{clase:'nota',texto:'Personas sin primaria a 30 min en transporte y sin ningún refugio potencial a 10 min a pie. Solo donde ambas evaluaciones están completas.'}),
    filaDato('Población no evaluable en alguna de las dos dimensiones',miles(Math.round(r.carencias_no_evaluable))),el('p',{clase:'micro',texto:'Ámbito: '+D.territorios[E.territorio].nombre+' · '+edadRT()+'. Todos los recursos disponibles por supuesto; no se suman personas de A y B.'}));
};
actualizarFicha = function(){
  previoRT.ficha();if(!datosRT()||!PT.listo)return;
  const r=resumenRT();
  $('pt-calor-base').replaceChildren(el('p',{clase:'nota',texto:`${r.texto.con} personas (${r.pct_texto}) con algún refugio potencial a 10 min. Incluye parques y piscinas; excluye fuentes. No evaluable: ${r.texto.no_evaluable}.`}));
  $('pt-carencias').replaceChildren(el('h3',{texto:'Carencias coincidentes · '+edadRT()}),el('p',{texto:`${r.texto.carencias} personas sin opción de primaria ni refugio potencial dentro de los umbrales, entre los casos evaluables.`}));
};
pintarTodo = function(){previoRT.todo();if(!datosRT()||U.tema!=='refugios'||E.paso!=='diagnosticar')return;
  $('pt-activo').append($('territorio'));$('rf-coberturas').hidden=false;$('alcance-tema').textContent='Comunidad de Madrid · Todos los refugios · Cobertura potencial a 10 min a pie';
  $('ver-actuaciones').textContent='Referencia anterior: horarios de mercados';pintarCifrasRefugios();};
valorSeccion = function(capa,s){if(datosRT()&&capa==='carencias'){const r=datosRT().secciones[RT.edad].filas[s];return{valor:r?.texto.carencias||'No evaluable',etiqueta:'Personas sin primaria ni refugio potencial dentro del umbral'};}if(datosRT()&&capa==='refugio'){const r=datosRT().secciones[RT.edad].filas[s];return{valor:r?.pct_texto||'No evaluable',etiqueta:'Población con refugio potencial a 10 min · '+edadRT()};}return previoRT.valor(capa,s);};
tarjetaSeccion = function(s){if(datosRT()&&E.variable==='refugio'){const r=datosRT().secciones[RT.edad].filas[s];return htmlTarjeta(D.sec.lugares[D.sec.t[s]],`Sección censal ${D.sec.cusec[s]}`,r?.pct_texto||'No evaluable','Población con algún refugio a 10 min',r?[`${r.texto.con} personas · ${edadRT()}`,`No evaluable: ${r.texto.no_evaluable}`,'Incluye parques y todos los recursos; disponibilidad supuesta.']:[]);}return previoRT.tarjeta(s);};
capaSecciones = function(){if(!datosRT()||E.variable!=='refugio')return previoRT.secciones();return new deck.PolygonLayer({id:'secciones',data:D.sec.partes,getPolygon:d=>d.p,getFillColor:d=>conAlfa(colorSeccion('refugio',d.s),OPACIDAD),stroked:!deLejos(),getLineColor:[255,255,255,230],lineWidthUnits:'pixels',getLineWidth:E.zoom>=11?1:.5,pickable:true,autoHighlight:true,highlightColor:[255,255,255,90],updateTriggers:{getFillColor:[E.variable,RT.edad],getLineWidth:E.zoom>=11}});};
capaParques = function(){if(!datosRT())return previoRT.parques();if(E.paso!=='diagnosticar'||U.tema!=='refugios'||!E.parques)return null;return new deck.PolygonLayer({id:'parques',data:D.refugios.poligonosParques,getPolygon:d=>d.p,filled:false,stroked:true,getLineColor:d=>D.refugios.coloresVerdes[d.c],getLineWidth:1.3,lineWidthUnits:'pixels',pickable:true});};
pintarLeyenda = function(){if(datosRT()&&E.variable==='carencias'&&E.paso==='diagnosticar'){$('leyenda').replaceChildren(el('h2',{clase:'leyenda-titulo',texto:'Carencias coincidentes · Resumen territorial'}),el('p',{clase:'nota',texto:'Comunidad de Madrid · Todos los refugios incluidos. Los contornos sitúan los municipios; no representan intensidad.'}));$('distribucion').replaceChildren();return;}if(!datosRT()||E.variable!=='refugio'||E.paso!=='diagnosticar')return previoRT.leyenda();const d=datosRT();
  $('leyenda').replaceChildren(el('div',{clase:'pt-leyenda-top'},[el('div',{},[el('h2',{clase:'leyenda-titulo',texto:'Población con refugio a 10 min (%)'}),el('p',{clase:'pt-leyenda-contexto',texto:'Fuentes excluidas · '+edadRT()+' · Color por sección'})])]),
    el('div',{clase:'pt-escala-color'},d.paleta.map((color,i)=>el('span',{style:`background:${color}`,title:d.etiquetas[i]}))),
    el('div',{clase:'pt-marcas'},[el('strong',{texto:'0 %'}),el('strong',{texto:'50 %'}),el('strong',{texto:'100 %'})]),
    el('p',{clase:'micro',texto:'Rojo: menor · Azul: mayor · Gris: no evaluable.'}),
    el('p',{clase:'micro',texto:'Contornos verdes: parques incluidos.'}));
  $('distribucion').replaceChildren(...d.etiquetas.map((etiqueta,i)=>filaLeyenda({color:d.paleta[i],etiqueta})));};
actualizarTituloMapa = function(){previoRT.titulo();if(!datosRT()||E.paso!=='diagnosticar')return;
  if(U.tema==='refugios'){$('mapa-titulo').textContent='Refugios frente al calor';$('mapa-subtitulo').textContent='Parques y piscinas incluidos · Fuentes excluidas · Cobertura potencial a 10 min';}
  if(U.tema==='carencias'){$('mapa-titulo').textContent='Carencias coincidentes · Todos los refugios';$('mapa-subtitulo').textContent='Resumen del territorio seleccionado · Cobertura potencial ampliada';}};
capasPuntos = function(){if(datosRT()&&E.variable==='carencias'&&E.paso==='diagnosticar')return[new deck.PolygonLayer({id:'carencias-ambito',data:D.municipios,getPolygon:d=>d.p,filled:false,stroked:true,getLineColor:[90,100,110,140],getLineWidth:1,lineWidthUnits:'pixels',pickable:false})];return previoRT.puntos();};
pintarComparar = function(){previoRT.comparar();if(!datosRT())return;
  document.getElementById('rt-referencia-b1')?.remove();
  if(carteraActual()?.componente==='b1')$('vista-comparar').prepend(el('p',{id:'rt-referencia-b1',clase:'aviso-suave',texto:'Referencia del escenario anterior: solo mercados y sus horarios. La nueva cobertura potencial de todos los refugios supone que todos están disponibles y no se representa mediante esta cartera B1.'}));};
montarModales = function(){previoRT.modales();if(!datosRT())return;for(const id of['datos-contenido','ayuda-contenido'])$(id)?.prepend(el('p',{clase:'aviso-suave',texto:datosRT().nota+' Las tablas B1 de mercados conservan el escenario anterior con horarios.'}));};
capasDeDesglose = function(clave){const capas=previoRT.desglose(clave);if(!datosRT())return capas;if(!capas.some(c=>c.capa==='refugio'))capas.push(D.mapa.desglose_refugio);return capas.map(c=>c.capa==='inventario_refugios'?{...c,nombre:'Equipamientos interiores',texto:'Equipamientos de Madrid capital por tipo. La cobertura incluye además parques, piscinas y bibliotecas de otros municipios. Las fuentes quedan excluidas.'}:c);};
