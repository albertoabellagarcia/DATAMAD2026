/* Interfaz de Sites. Reutiliza las capas y los resultados precalculados de la demo.
   Los cálculos de accesibilidad, agregación y optimización permanecen en Python. */
'use strict';

const U = { tema: 'primaria', indicador: 'minutos', modo: 'transporte', franja: '9_13', ficha: null, foco: null };
const baseInterfaz = { puntos: capasPuntos, zonas: capasZonas, valor: valorSeccion, tooltip: tarjetaFlotante,
  ficha: pintarFicha, modales: montarModales, abrir3d: abrirDesglose, rotulos: capaRotulos };
const modalesConservados = ['inicio', 'datos', 'ayuda', 'demo'].map(id => $(id).outerHTML).join('');
const iconoTema = (trazo) => `<svg viewBox="0 0 24 24" aria-hidden="true">${trazo}</svg>`;
document.body.innerHTML = `
<a class="saltar" href="#panel">Ir a los controles</a>
<header id="cabecera">
 <button id="volver-inicio" class="marca" aria-label="CercaSalud Madrid, volver al diagnóstico"><img src="marca/logo.svg" alt="CercaSalud Madrid" width="642" height="204"></button>
 <nav id="pasos" role="tablist" aria-label="Recorrido de decisión"><button data-paso="diagnosticar" role="tab" aria-selected="true" aria-controls="vista-diagnosticar">1 Diagnosticar</button><button data-paso="comparar" role="tab" aria-selected="false" aria-controls="vista-comparar">2 Comparar</button><button data-paso="ficha" role="tab" aria-selected="false" aria-controls="vista-ficha">3 Ficha</button></nav>
 <div class="buscador"><label class="solo-lector" for="buscar">Buscar municipio o distrito</label>${iconoTema('<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>')}<input id="buscar" type="search" placeholder="Buscar municipio o distrito" autocomplete="off" aria-controls="sugerencias" aria-expanded="false"><ul id="sugerencias" role="listbox" hidden></ul></div>
 <div class="acciones-cabecera"><button id="abrir-datos" class="discreto">Datos</button><button id="abrir-ayuda" class="discreto">Método</button></div>
</header>
<main id="mapa" aria-label="Mapa interactivo de la Comunidad de Madrid"></main>
<div id="resumen-mapa" aria-live="polite"><span id="mapa-contexto" class="sobretitulo"></span><h1 id="mapa-titulo"></h1><p id="mapa-subtitulo"></p></div>
<aside id="panel" aria-label="Explorar el territorio" tabindex="-1">
 <div class="panel-control"><span>Explorar el territorio</span><button id="plegar" aria-expanded="true" aria-controls="contenido-panel">Ocultar</button></div>
 <div id="contenido-panel"><section id="vista-diagnosticar" class="vista" role="tabpanel">
  <h2 class="etiqueta-seccion">¿Qué quieres explorar?</h2>
  <div id="temas" class="temas" role="group" aria-label="Tema del mapa">
   <button data-tema="primaria" aria-pressed="true">${iconoTema('<path d="M4 21V7h16v14M9 7V3h6v4M2 21h20M9 21v-6h6v6M8 10h1m6 0h1"/>')}Atención primaria</button>
   <button data-tema="refugios" aria-pressed="false">${iconoTema('<path d="M3 12 12 4l9 8M5 10v11h14V10M12 9v8m-3-4h6"/>')}Refugios climáticos</button>
   <button data-tema="carencias" aria-pressed="false">${iconoTema('<circle cx="9" cy="12" r="7"/><circle cx="15" cy="12" r="7"/>')}Carencias coincidentes</button>
   <button data-tema="contexto" aria-pressed="false">${iconoTema('<path d="M4 20V11m8 9V4m8 16v-7M2 21h20"/>')}Contexto social</button>
  </div>
  <div id="controles-primaria"><fieldset class="mapa-indicadores"><legend>¿Qué quieres ver?</legend>
   <label class="casilla"><input type="radio" name="indicador" id="indicador-minutos" value="minutos" checked> Tiempo hasta un centro</label>
   <label class="casilla"><input type="radio" name="indicador" id="indicador-porcentaje" value="porcentaje"> <span id="indicador-porcentaje-texto"></span></label></fieldset>
   <div class="dos-campos"><label class="campo">Desplazamiento<select id="modo"><option value="transporte">A pie o transporte público</option><option value="pie">A pie</option></select></label><label id="campo-franja" class="campo">Franja horaria<select id="franja"><option value="9_13">9–13 h</option><option value="16_20">16–20 h</option></select></label>
   <div id="franja-fija" class="mapa-franja-fija" hidden><span>Franja analizada</span><b>9–13 h</b><p id="franja-fija-ayuda" class="micro"></p></div></div>
   <p id="escala-actual" class="mapa-escala" role="status"></p><p id="ayuda-indicador" class="nota"></p></div>
  <p id="alcance-tema" class="aviso-suave" hidden></p><div id="zona-senalada" class="tarjeta seccion" hidden></div><div id="territorio" class="tarjeta" aria-live="polite"></div><button id="ver-actuaciones" class="principal ancho">Comparar actuaciones regionales</button>
  <details class="desplegable"><summary>Capas del mapa</summary><label class="casilla"><input type="checkbox" id="ver-centros"> Centros de atención primaria</label><label class="casilla"><input type="checkbox" id="ver-mercados"> Mercados climatizados · Madrid</label></details>
  <details class="desplegable"><summary>Cómo interpretar el mapa</summary><p id="nota" class="nota"></p><div id="distribucion"></div></details>
  <details class="desplegable casos"><summary>Casos para explorar</summary><div id="ir-a"></div></details>
  <p class="pie-panel"><button id="abrir-demo" class="enlace">Recorrido guiado de la demo</button><span id="version-corta"></span></p><div id="variables" hidden></div>
 </section><section id="vista-desglose" aria-label="Desglose en 3D"><span class="sobretitulo">Una mirada en profundidad</span><h2 id="desglose-titulo"></h2><p class="nota">Explora las capas del territorio. Arrastra con el botón derecho o con Ctrl para girar.</p><div class="botones-fila"><button id="desglose-separar">Juntar o separar capas</button><button id="desglose-cerrar" class="principal">Volver al mapa</button></div><ol id="desglose-capas"></ol></section></div>
</aside>
<aside id="leyenda-mapa" aria-label="Leyenda del mapa"><div id="leyenda"></div></aside>
<section id="vista-comparar" class="vista resultados" role="tabpanel" hidden>
 <div class="control-resultados"><span>Comparar actuaciones</span><button id="plegar-resultados" aria-expanded="true">Ver mapa</button></div>
 <div class="encabezado-vista"><span id="comparar-alcance" class="sobretitulo"></span><h2>¿Dónde conviene actuar?</h2><p>Compara propuestas con los mismos recursos.</p></div>
 <div class="filtros-comparar"><label class="campo">Actuación<select id="componente"></select></label><label class="campo">Población objetivo<select id="objetivo"></select></label></div><div id="opciones-cartera" class="opciones fila" role="group" aria-label="Recursos disponibles"></div><p id="condiciones" class="nota condiciones"></p>
 <div id="barras" class="comparacion-barras"></div><p id="zonas-texto" class="nota"></p><label class="casilla destacada" id="casilla-cambia"><input type="checkbox" id="ver-cambia"> Ver quién pasa a tener opción</label><p id="cambia-texto" class="nota"></p><div id="leyenda-cambia"></div><div id="mercados-elegidos"></div>
 <details id="bloque-escenarios" class="desplegable"><summary id="titulo-escenarios">¿Qué ocurre si cambian los supuestos?</summary><div id="escenarios" class="tabla-scroll"></div><p class="nota">«Misma cartera» conserva las zonas elegidas. «Mejor cartera para ese escenario» permite elegir otras. Son escenarios calculados, no un intervalo de confianza.</p></details>
 <details class="desplegable"><summary>Supuestos y límites de la actuación</summary><p id="estado-solver" class="nota"></p><div id="b-c"></div></details><button id="abrir-ficha" class="principal ancho">Abrir ficha de decisión</button>
</section>
<section id="vista-ficha" class="vista documento" role="tabpanel" hidden>
 <div class="encabezado-documento"><div><span id="ficha-contexto" class="sobretitulo"></span><h1 id="ficha-titulo">Ficha de decisión</h1><p id="ficha-subtitulo" class="nota"></p></div><button id="ficha-volver" class="sin-imprimir">Volver a comparar</button></div>
 <p id="ficha-medida" class="nota"></p><div id="ficha-cifras" class="cifras"></div><div id="ficha-mapa" class="mapa-ficha"></div>
 <div class="documento-columnas"><div><h2>La actuación propuesta</h2><div id="ficha-resumen"></div></div><div><div id="ficha-limites" class="limites"></div><h2 class="sin-imprimir">Llevarse la decisión</h2><div id="descargas" class="botones-columna"></div></div></div><h2 id="ficha-tabla-titulo">Zonas de búsqueda elegidas</h2><div id="ficha-tabla" class="tabla-scroll"></div><details class="desplegable"><summary>Alternativas y notas de interpretación</summary><div id="ficha-alternativas"></div></details><p id="ficha-atribucion" class="micro"></p>
</section>
<div id="estado-carga" role="status">Cargando el mapa…</div><footer id="atribuciones"></footer>${modalesConservados}`;

function filaDato(etiqueta, valor) { return el('div', {clase:'cifra-fila'}, [el('span',{texto:etiqueta}),el('b',{texto:valor})]); }
function variableDeControles() {
  if (U.indicador === 'porcentaje') return U.modo === 'pie' ? 'pct_sin_pie' : 'pct_sin_transporte';
  return U.modo === 'pie' ? 'min_pie' : `min_tp_${U.franja}`;
}
function textosMapa(){return D.textos.controles_mapa;}
function etiquetaPorcentaje(modo=U.modo){return textosMapa().porcentaje[modo==='pie'?'pie':'transporte'];}
function etiquetaFuera(modo=U.modo){return `A más de ${textosMapa().umbral[modo==='pie'?'pie':'transporte']} min`;}
function sincronizarControles() {
  const v=E.variable;
  if(E.paso==='diagnosticar')U.tema=v==='refugio'?'refugios':v==='carencias'?'carencias':v==='quintil_renta'?'contexto':'primaria';
  if(E.paso==='diagnosticar'&&U.tema==='primaria'){U.indicador=v.startsWith('pct_')?'porcentaje':'minutos';U.modo=variableActual().modo==='pie'?'pie':'transporte';if(v==='min_tp_16_20')U.franja='16_20';else if(v==='min_tp_9_13')U.franja='9_13';}
  for(const radio of document.querySelectorAll('input[name=indicador]'))radio.checked=radio.value===U.indicador;
  $('indicador-porcentaje-texto').textContent=etiquetaPorcentaje();$('modo').value=U.modo;$('franja').value=U.franja;
  $('controles-primaria').hidden=U.tema!=='primaria';$('campo-franja').hidden=U.modo==='pie'||U.indicador==='porcentaje';
  $('franja-fija').hidden=U.modo==='pie'||U.indicador!=='porcentaje';
  $('franja-fija-ayuda').textContent=textosMapa().franja_porcentaje;
  $('escala-actual').textContent=U.indicador==='porcentaje'?textosMapa().escala_porcentaje:textosMapa().escala_tiempos;
  $('ayuda-indicador').textContent=U.indicador==='porcentaje'?textosMapa().ayuda_porcentaje:'Pasa el ratón por el mapa para identificar la sección; pulsa para ver su información.';
  document.querySelectorAll('[data-tema]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tema===U.tema)));
  const alcance={refugios:'Madrid capital · Horas de acceso entre 12 y 21 h en un laborable de julio, con acceso supuesto en horario comercial.',carencias:'Madrid capital · Resumen de carencias coincidentes. El mapa sitúa el ámbito del análisis.',contexto:'Renta neta media por persona · ADRH 2024. Quintiles de la Comunidad de Madrid.'}[U.tema];
  $('alcance-tema').hidden=!alcance;$('alcance-tema').textContent=alcance||'';
  $('ver-actuaciones').hidden=U.tema==='contexto'||U.tema==='carencias';
  $('ver-actuaciones').textContent=U.tema==='refugios'?'Comparar ampliaciones de horario':'Comparar actuaciones regionales';
  $('ver-centros').checked=E.centros;$('ver-mercados').checked=E.mercados;
}
function salirDel3d() { if(!E.desglose)return;E.desglose=null;document.body.classList.remove('en-desglose');D.deck.setProps({controller:{doubleClickZoom:true,dragRotate:false,touchRotate:false}}); }
function abrirPanelMovil(ampliar=false){$('panel').classList.remove('plegado');document.body.classList.remove('panel-oculto');document.body.classList.toggle('panel-ampliado',ampliar);$('plegar').textContent=ampliar?'Ver mapa':'Ampliar';$('plegar').setAttribute('aria-expanded','true');}
function activarTema(tema){
  salirDel3d();E.seccion=null;$('zona-senalada').hidden=true;U.tema=tema;
  E.variable=tema==='refugios'?'refugio':tema==='carencias'?'carencias':tema==='contexto'?'quintil_renta':variableDeControles();
  E.mercados=tema==='refugios';E.centros=false;
  if(tema==='refugios'||tema==='carencias'){E.territorio='municipio:28079';$('buscar').value='Madrid';}
  irAPaso('diagnosticar');encuadrar(D.territorios[E.territorio].caja);
}
montarInterfaz = function(){
  D.mapa.variables.refugio={titulo:'Horas con un refugio próximo',escala:'celdas',paleta:D.mapa.desglose_refugio.paleta,etiquetas:D.mapa.desglose_refugio.etiquetas,nota:D.mapa.desglose_refugio.texto};
  D.mapa.variables.carencias={titulo:'Carencias coincidentes',escala:'territorio',paleta:['#eceff1'],etiquetas:['Ámbito del resumen'],nota:D.textos.b_c.c.join(' ')};
  document.querySelectorAll('[data-tema]').forEach(b=>b.addEventListener('click',()=>activarTema(b.dataset.tema)));
  const cambiarAcceso=()=>{U.indicador=document.querySelector('input[name=indicador]:checked').value;U.modo=$('modo').value;U.franja=$('franja').value;E.variable=variableDeControles();E.seccion=null;XC.seleccion=null;$('zona-senalada').hidden=true;pintarTodo();};
  for(const campo of [...document.querySelectorAll('input[name=indicador]'),$('modo'),$('franja')])campo.addEventListener('change',cambiarAcceso);
  for(const b of document.querySelectorAll('[data-paso]'))b.addEventListener('click',()=>irAPaso(b.dataset.paso));
  $('pasos').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const bs=[...$('pasos').querySelectorAll('button')],i=bs.indexOf(document.activeElement);const j=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;bs[j].click();bs[j].focus();});
  $('volver-inicio').addEventListener('click',()=>{U.indicador='minutos';U.modo='transporte';U.franja='9_13';E.territorio='comunidad:28';$('buscar').value='';activarTema('primaria');});
  $('ver-centros').addEventListener('change',e=>{E.centros=e.target.checked;pintarMapa();});$('ver-mercados').addEventListener('change',e=>{E.mercados=e.target.checked;pintarMapa();});
  $('ver-actuaciones').addEventListener('click',()=>{E.cartera=U.tema==='refugios'?'b1|total|3_12':U.modo==='pie'?'a_pie|total|3':'a_transporte|total|3';irAPaso('comparar');});
  $('abrir-ficha').addEventListener('click',()=>irAPaso('ficha'));$('ficha-volver').addEventListener('click',()=>irAPaso('comparar'));
  $('plegar-resultados').addEventListener('click',()=>{const plegado=document.body.classList.toggle('resultados-ocultos');$('plegar-resultados').textContent=plegado?'Ver resultados':'Ver mapa';$('plegar-resultados').setAttribute('aria-expanded',String(!plegado));encuadrarActuacion();});
  $('ver-cambia').addEventListener('change',e=>{E.cambia=e.target.checked;pintarTodo();if(E.cambia&&carteraActual().ganan)encuadrar(carteraActual().ganan.caja);});
  $('plegar').addEventListener('click',()=>{if(innerWidth<=760){if($('panel').classList.contains('plegado'))abrirPanelMovil();else if(!document.body.classList.contains('panel-ampliado'))abrirPanelMovil(true);else{$('panel').classList.add('plegado');document.body.classList.remove('panel-ampliado');document.body.classList.add('panel-oculto');$('plegar').textContent='Abrir panel';$('plegar').setAttribute('aria-expanded','false');}}else{const cerrado=$('panel').classList.toggle('plegado');document.body.classList.toggle('panel-oculto',cerrado);$('plegar').textContent=cerrado?'Abrir':'Ocultar';$('plegar').setAttribute('aria-expanded',String(!cerrado));}});
  $('desglose-separar').addEventListener('click',()=>{if(E.desglose)animarSeparacion(E.desglose.separacion>0?0:E.desglose.objetivo,800);});$('desglose-cerrar').addEventListener('click',cerrarDesglose);
  montarBuscador();montarComparar();montarModales();montarDemo();
  const demoCerrar=el('button',{texto:'Cerrar',id:'demo-cerrar'});demoCerrar.addEventListener('click',()=>{$('demo').hidden=true;$('inicio').hidden=true;const url=new URL(location.href);url.searchParams.delete('demo');history.replaceState(null,'',url);$('abrir-demo').focus();});$('demo').append(demoCerrar);
  const casos=[['Boadilla del Monte','Acceso a primaria en transporte','primaria','municipio:28022'],['Madrid capital','Cobertura y horarios de refugios','refugios','municipio:28079'],['Rivas-Vaciamadrid','Acceso a primaria y actuaciones regionales','primaria','municipio:28123']];
  $('ir-a').replaceChildren(...casos.map(([nombre,texto,tema,clave])=>{const b=el('button',{},[el('strong',{texto:nombre}),el('span',{texto})]);b.addEventListener('click',()=>{activarTema(tema);irATerritorio(clave);});return b;}));
  $('version-corta').textContent=`Datos: ${D.textos.fuentes.fecha_version} · Resultados precalculados`;
  $('atribuciones').replaceChildren(el('a',{href:'https://www.openstreetmap.org/copyright',target:'_blank',rel:'noopener',texto:'© colaboradores de OpenStreetMap (ODbL)'}),' · ',el('a',{href:'http://www.crtm.es/',target:'_blank',rel:'noopener',texto:'Powered by CRTM'}),el('span',{clase:'creditos-largos',texto:' · INE · Comunidad de Madrid · Ayuntamiento de Madrid · Natural Earth'}));
  const fuentes=el('button',{texto:'Fuentes y atribuciones'});fuentes.addEventListener('click',()=>{abrirDialogo('datos');$('titulo-atribuciones').scrollIntoView({block:'start'});});$('atribuciones').prepend(fuentes);
  if(innerWidth<=760)$('plegar').textContent='Ampliar';
};

irATerritorio = function(clave){if(!D.territorios[clave])return;salirDel3d();E.territorio=clave;E.seccion=null;$('zona-senalada').hidden=true;$('buscar').value=D.territorios[clave].nombre;pintarTodo();encuadrar(D.territorios[clave].caja);};
pintarTodo = function(){sincronizarControles();pintarTerritorio();pintarLeyenda();pintarComparar();pintarFicha();actualizarTituloMapa();$('nota').textContent=variableActual().nota||'';pintarMapa();};
pintarTerritorio = function(){
  const t=D.territorios[E.territorio],caja=$('territorio');caja.replaceChildren(el('h3',{texto:t.nombre}),el('p',{clase:'micro',texto:`${t.poblacion} habitantes · INE 2025`}));
  if(U.tema==='primaria'){
    const modo=variableActual().modo||U.modo,m=t.modos[modo];caja.append(el('div',{clase:'valor-principal',texto:U.indicador==='porcentaje'?m.sin_opcion_pct:m.con_acceso}),el('p',{clase:'etiqueta-valor',texto:U.indicador==='porcentaje'?etiquetaFuera(modo):'con un centro dentro del umbral'}),el('p',{clase:'micro',texto:m.etiqueta}),filaDato(etiquetaFuera(modo),m.sin_opcion),filaDato('No evaluable',m.no_evaluable));
    const otros=el('details',{},[el('summary',{texto:'Otras franjas y desplazamientos'})]);for(const k of ['transporte','transporte_16_20','pie'])if(k!==modo)otros.append(filaDato(t.modos[k].etiqueta,t.modos[k].con_acceso));caja.append(otros,el('p',{clase:'nota',texto:textosMapa().ayuda_porcentaje}));
  }else if(U.tema==='refugios'){
    const regional=t.tipo==='comunidad',capital=E.territorio==='municipio:28079';
    const resultado=D.refugios.detalle.resultados[`${RF.dia}|${RF.edad}`];
    const linea=resultado.lineas[regional?0:1];
    const resumen=D.mapa.desglose_refugio.por_territorio[E.territorio];
    caja.append(el('div',{clase:'valor-principal',texto:regional?linea.alguna.porcentaje:capital?linea.peor.porcentaje:resumen?'12–21 h':'No evaluable'}),
      el('p',{clase:'etiqueta-valor',texto:regional?'Cobertura evaluable solo en Madrid capital · A alguna hora · 43 mercados':capital?`Con respaldo · Peor hora ${linea.peor_hora} · Madrid capital`:'Cobertura base de mercados · Laborable de julio'}));
    if(regional){caja.append(el('p',{clase:'nota',texto:'Resto de la Comunidad: no evaluable, sin lista oficial de refugios.'}));const b=el('button',{clase:'pt-enlace',texto:'Ver Madrid capital'});b.addEventListener('click',()=>{irATerritorio('municipio:28079');$('pt-calor').open=true;});caja.append(b);}
    else if(resumen)caja.append(el('p',{clase:'nota',texto:resumen}),el('p',{clase:'micro',texto:'La cobertura supone acceso a la zona climatizada durante el horario comercial. Sin ese supuesto, la documentación no acredita cobertura.'}));
  }else if(U.tema==='contexto'){
    const renta=D.detalleTerritorios.perfiles[E.territorio].renta;
    const fraccion=renta.filas.filter(f=>f.quintil<=2).reduce((s,f)=>s+f.fraccion,0);
    caja.append(el('div',{clase:'valor-principal',texto:`${(100*fraccion).toFixed(1).replace('.',',')} %`}),el('p',{clase:'etiqueta-valor',texto:'Población en Q1–Q2 · Quintiles de menor renta'}),el('p',{clase:'micro',texto:'La renta aporta contexto; no interviene en el cálculo del acceso.'}));
  }else{
    const numero=D.textos.b_c.c[0].match(/:\s*([\d.]+)\s+personas/),madrid=t.clave==='municipio:28079'||t.tipo==='comunidad';
    caja.append(el('div',{clase:'valor-principal',texto:madrid&&numero?numero[1]:'Sin dato'}));
    if(madrid){
      caja.append(el('p',{clase:'etiqueta-valor',texto:'Personas con carencias coincidentes · Madrid capital'}),el('p',{clase:'nota',texto:D.textos.b_c.explicacion_c}),el('p',{clase:'aviso-suave',texto:'Resumen agregado, sin desglose por sección censal. El contorno azul señala el ámbito del análisis.'}),...D.textos.b_c.c.map(x=>el('p',{clase:'nota',texto:x})));const a=el('button',{clase:'pt-enlace',texto:'Ver dónde faltan centros (A)'});a.addEventListener('click',()=>{U.modo='transporte';U.franja='9_13';U.indicador='minutos';activarTema('primaria');irATerritorio('municipio:28079');});const b=el('button',{clase:'pt-enlace',texto:'Ver refugios en Madrid (B)'});b.addEventListener('click',()=>{activarTema('refugios');irATerritorio('municipio:28079');});caja.append(a,b);
    }else{
      caja.append(el('p',{clase:'etiqueta-valor',texto:'Carencias coincidentes sin desglose para este territorio'}),el('p',{clase:'nota',texto:'El resumen disponible corresponde a Madrid capital. No se atribuye a otros municipios ni a distritos. Sin dato no significa ausencia de carencias.'}));
      const verMadrid=el('button',{clase:'pt-enlace',texto:'Ver resumen de Madrid capital'});verMadrid.addEventListener('click',()=>activarTema('carencias'));caja.append(verMadrid);
    }
  }
};

function leyendaActual(){const v=variableActual();if(E.variable.startsWith('pct_sin_'))return {filas:v.paleta.map((color,i)=>({color,etiqueta:v.etiquetas[i]})),extra:[{color:'#bebebe',etiqueta:'No evaluable'}]};if(E.variable==='refugio')return {filas:v.paleta.map((color,i)=>({color,etiqueta:v.etiquetas[i]})),extra:[{color:'#bebebe',etiqueta:'No evaluable fuera de Madrid capital'}]};if(E.variable==='carencias')return {filas:[{color:'#eceff1',etiqueta:'Ámbito: Madrid capital'}],extra:[]};return v.escala==='municipios'?D.mapa.leyendas.municipios[E.variable]:(D.mapa.leyendas[E.territorio]||{})[E.variable];}
pintarLeyenda = function(){
  const v=variableActual(),datos=leyendaActual(),caja=$('leyenda');caja.replaceChildren();$('distribucion').replaceChildren();if(!datos)return;
  let titulo=E.variable==='refugio'?'Horas medias con refugio a 10 min a pie':E.variable==='carencias'?'Resumen sin mapa por sección':E.variable==='quintil_renta'?'Quintil de renta · ADRH 2024':E.variable.startsWith('pct_sin_')?etiquetaPorcentaje(v.modo):'Minutos hasta atención primaria';
  if(modoCambia()){
    caja.append(el('div',{clase:'leyenda-titulo',texto:'Efecto de la actuación de primaria'}),...D.mapa.leyenda_cambia.map(x=>filaLeyenda({...x,pct:null,texto:''})),el('p',{clase:'micro',texto:'Una sección puede incluir personas que mejoran y otras que siguen fuera.'}));return;
  }
  caja.append(el('div',{clase:'leyenda-titulo',texto:titulo}));
  if(E.variable==='carencias'){caja.append(el('p',{clase:'nota',texto:'Contorno azul: ámbito de Madrid capital. Hay un resumen agregado, sin desglose por sección. El color no representa la intensidad de las carencias.'}));return;}
  const style=`grid-template-columns:repeat(${datos.filas.length},1fr)`;
  caja.append(el('div',{clase:'leyenda-colores',style},datos.filas.map(f=>el('i',{style:`background:${f.color}`}))));
  const textos=E.variable==='refugio'?['0','≤2','2–4','4–6','>6']:E.variable==='quintil_renta'?['Q1','Q2','Q3','Q4','Q5']:v.escala==='municipios'?['0','≤1','1–5','5–10','10–25','25–50','>50']:datos.filas.map(f=>f.etiqueta.replace(' min',''));
  caja.append(el('div',{clase:'leyenda-ticks',style},textos.map(texto=>el('span',{texto}))));
  const detalle=el('div',{clase:'leyenda-detalle'});
  if(v.umbral)detalle.append(el('span',{clase:'umbral-compacto',texto:`Umbral: ${v.umbral} min`}));
  if(v.escala==='municipios')detalle.append(el('span',{texto:textosMapa().escala_porcentaje}));
  if(v.escala==='celdas')detalle.append(el('span',{texto:E.variable==='refugio'?'Media de horas por sección':E.variable==='quintil_renta'?'Q1: menor renta · Q5: mayor renta':E.variable.startsWith('pct_sin_')?'Color = porcentaje de la sección':'Color = mediana de la sección'}));
  detalle.append(...(datos.extra||[]).map(f=>el('span',{},[el('i',{clase:'muestra',style:`background:${f.color}`}),el('span',{texto:f.etiqueta})])));caja.append(detalle);
  $('distribucion').append(...datos.filas.map(f=>filaLeyenda(f)),...(datos.extra||[]).map(f=>filaLeyenda(f)));
};

function porcentajeSeccion(s,modo){
  const n=D.sec['sin_'+modo]?.[s];return D.sec.g[s]>0&&Number.isFinite(n)?`${String(n).replace('.',',')} %`:'No evaluable';
}
function municipioSeccion(s){return D.territorios['municipio:'+String(D.sec.cusec[s]).slice(0,5)];}
valorSeccion = function(capa,s){
  if(capa.startsWith('pct_sin_'))return {valor:porcentajeSeccion(s,variableActual().modo),etiqueta:etiquetaFuera(variableActual().modo)+' · población de la sección'};
  if(capa==='carencias')return {valor:'Sin desglose por sección',etiqueta:textosMapa().mapa_carencias};
  if(capa==='refugio')return {valor:D.sec.refugio[s]===null?(String(D.sec.cusec[s]).startsWith('28079')?'No evaluable: cobertura no disponible para esta sección de Madrid capital':'No evaluable: fuera de Madrid capital no hay lista oficial de refugios'):`${String(D.sec.refugio[s]).replace('.',',')} h`,etiqueta:'Media de horas con un refugio a 10 min a pie · 12–21 h, laborable de julio'};
  return baseInterfaz.valor(capa,s);
};
function detallePorcentaje(s){
  const t=municipioSeccion(s),modo=variableActual().modo;
  return [textosMapa().detalle_porcentaje,...(t?[`Municipio: ${t.nombre} · ${t.modos[modo].sin_opcion_pct} ${etiquetaFuera(modo).toLowerCase()}`]:[]),textosMapa().casos_seccion];
}
tarjetaSeccion = function(s){
  if(E.variable==='refugio'){const v=valorSeccion('refugio',s);return htmlTarjeta(D.sec.lugares[D.sec.t[s]],`Sección censal ${D.sec.cusec[s]}`,v.valor,v.etiqueta,[`${miles(D.sec.g[s])} habitantes`,'Cobertura actual, con acceso supuesto en horario comercial']);}
  return htmlSeccionPrimaria(s);
};
function htmlSeccionPrimaria(s){
  const v=valorSeccion(E.variable,s),modo=variableActual().modo||'transporte',codigo=`Sección censal ${D.sec.cusec[s]}`;
  if(modoCambia()){const f=cambiaPorSeccion().get(s);return htmlTarjeta(D.sec.lugares[D.sec.t[s]],codigo,`${miles(f?f[2]:0)} personas`,'pasan a tener un centro dentro del umbral',[`${miles(f?f[3]:0)} siguen sin opción verificada`]);}
  const extras=[`${miles(D.sec.g[s])} habitantes`];
  if(E.variable.startsWith('pct_sin_'))extras.push(...detallePorcentaje(s));
  else if(U.tema==='primaria')extras.push(`${porcentajeSeccion(s,modo)} ${etiquetaFuera(modo).toLowerCase()}`,textosMapa().casos_seccion);
  return htmlTarjeta(D.sec.lugares[D.sec.t[s]],codigo,v.valor,v.etiqueta,extras);
}
mostrarZonaSenalada = function(s){
  const v=valorSeccion(E.variable,s),caja=$('zona-senalada');
  caja.replaceChildren(el('p',{clase:'sobretitulo',texto:'Sección censal seleccionada'}),el('h3',{texto:D.sec.lugares[D.sec.t[s]]}),el('p',{clase:'micro',texto:`Sección censal ${D.sec.cusec[s]}`}),el('div',{clase:'valor-principal',texto:v.valor}),el('p',{clase:'etiqueta-valor',texto:v.etiqueta}),filaDato('Habitantes',miles(D.sec.g[s])));
  if(E.variable.startsWith('pct_sin_'))caja.append(...detallePorcentaje(s).map(texto=>el('p',{clase:'nota',texto})));
  else if(U.tema==='primaria')caja.append(filaDato(etiquetaFuera(variableActual().modo),porcentajeSeccion(s,variableActual().modo)),el('p',{clase:'micro',texto:textosMapa().casos_seccion}));
  caja.hidden=false;
};
alPulsar = function({layer,object}){if(!layer||!object||E.desglose)return;if(layer.id==='secciones'){E.seccion=object.s;const clave=D.sec.territorio[object.s];if(D.territorios[clave])E.territorio=clave;$('buscar').value=D.territorios[E.territorio].nombre;pintarTerritorio();pintarLeyenda();mostrarZonaSenalada(object.s);actualizarTituloMapa();pintarMapa();}else if(layer.id==='municipios'){const t=D.mapa.territorios.find(x=>x.tipo==='municipio'&&x.nombre===object.l);if(t)irATerritorio(t.clave);}};

function mercadosElegidos(){const f=carteraActual();if(f.componente!=='b1')return[];const porNombre=new Map(D.puntos.mercados.map(p=>[p.nombre,p]));return f.tabla.filas.map(([nombre,horas,numeroHoras],i)=>({...porNombre.get(nombre),horas,numeroHoras,orden:i+1}));}
capasPuntos = function(){return baseInterfaz.puntos();};
capasZonas = function(){
  if(E.paso==='diagnosticar'&&E.variable==='carencias')return[new deck.PolygonLayer({id:'carencias-ambito',data:D.municipios.filter(d=>d.l===D.territorios['municipio:28079'].nombre),getPolygon:d=>d.p,getFillColor:[23,102,173,18],getLineColor:[23,102,173,230],stroked:true,getLineWidth:2,lineWidthUnits:'pixels',pickable:false})];
  if(!enComparar()||carteraActual().componente!=='b1')return baseInterfaz.zonas();const data=mercadosElegidos();return[new deck.ScatterplotLayer({id:'mercados-elegidos',data,getPosition:p=>[p.lon,p.lat],getFillColor:[181,29,47],getLineColor:BLANCO,stroked:true,lineWidthMinPixels:2.5,getRadius:180,radiusMinPixels:12,pickable:true}),new deck.TextLayer({id:'mercados-numero',data,getPosition:p=>[p.lon,p.lat],getText:p=>String(p.orden),getSize:13,getColor:BLANCO,fontFamily:FUENTE,fontWeight:'bold',characterSet:'0123456789'})];
};
tarjetaFlotante = function(info){if(info.layer?.id==='mercados-elegidos')return {html:htmlTarjeta(info.object.nombre,'',`${info.object.numeroHoras} h`,'de ampliación propuesta',[info.object.horas,info.object.detalle]),style:{backgroundColor:'#fff',color:'#1a1a1a',padding:'12px 16px',borderRadius:'8px',maxWidth:'350px',fontFamily:FUENTE}};return baseInterfaz.tooltip(info);};
capaRotulos = function(){const capa=baseInterfaz.rotulos();if(!capa||E.zoom>=10)return capa;const nombres=new Set(['Madrid','Getafe','Alcalá de Henares','Aranjuez','Boadilla del Monte','Rivas-Vaciamadrid','Alcobendas','Collado Villalba',D.territorios[E.territorio].nombre]);return capa.clone({data:(D.mapa.rotulos[String(E.zoom)]||[]).filter(r=>nombres.has(r[2])||r[3]>=17)});};
anchoPanel = function(){return innerWidth<=760||E.paso==='ficha'?0:E.paso==='comparar'?$('vista-comparar').getBoundingClientRect().width+24:$('panel').getBoundingClientRect().width;};
vistaParaCaja = function(caja){const ancho=$('mapa').clientWidth,alto=$('mapa').clientHeight,movil=innerWidth<=760;const inferior=movil?Math.min((E.paso==='comparar'?$('vista-comparar'):$('panel')).getBoundingClientRect().height+95,alto*.62):100;return new deck.WebMercatorViewport({width:ancho,height:alto}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],{padding:{left:movil?22:anchoPanel()+40,right:movil?22:36,top:movil?85:60,bottom:movil?inferior:70}});};
abrirDesglose = function(clave){E.paso='diagnosticar';document.body.classList.remove('comparando','en-ficha');$('vista-comparar').hidden=true;$('vista-ficha').hidden=true;document.querySelectorAll('[data-paso]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.paso==='diagnosticar')));if(innerWidth<=760)abrirPanelMovil();baseInterfaz.abrir3d(clave);};

function actualizarTituloMapa(){
  const f=carteraActual(),v=variableActual();$('mapa-contexto').textContent=E.paso==='diagnosticar'?({primaria:'Atención primaria',refugios:'Refugios climáticos',contexto:'Contexto social',carencias:'Carencias coincidentes'}[U.tema]):f.componente==='b1'?'Ampliación de horarios · Madrid capital':'Actuaciones de primaria · Comunidad de Madrid';
  $('mapa-titulo').textContent=modoCambia()?'Quién gana opción con esta cartera':E.paso!=='diagnosticar'&&f.componente==='b1'?'Mercados elegidos y cobertura actual':U.tema==='primaria'?(U.indicador==='porcentaje'?etiquetaPorcentaje():'Tiempo hasta el centro de salud'):U.tema==='contexto'?'Renta neta por persona':v.titulo;
  $('mapa-subtitulo').textContent=E.paso!=='diagnosticar'&&f.componente==='b1'?'Los números identifican los mercados de la propuesta. El color muestra la cobertura actual.':`${D.territorios[E.territorio].nombre}${U.tema==='primaria'?' · '+(U.modo==='pie'?'A pie':'A pie o transporte · '+(U.indicador!=='porcentaje'&&U.franja==='16_20'?'16–20 h':'9–13 h')):''}${v.umbral?' · Umbral '+v.umbral+' min':''}${U.tema==='contexto'?' · Quintiles · ADRH 2024':''}`;
  if(E.paso==='diagnosticar'&&E.variable==='carencias')$('mapa-subtitulo').textContent='Solo Madrid capital · Resumen agregado sin desglose por sección';
}
function encuadrarActuacion(){const f=carteraActual();encuadrar(f.componente==='b1'?D.territorios['municipio:28079'].caja:f.ganan?.caja||D.territorios['comunidad:28'].caja);}
function sincronizarActuacion(reencuadrar=true){const f=carteraActual();E.variable=f.componente==='b1'?'refugio':f.componente==='a_pie'?'min_pie':'min_tp_9_13';E.territorio=f.componente==='b1'?'municipio:28079':'comunidad:28';E.mercados=f.componente==='b1';E.centros=false;E.seccion=null;E.cambia=E.cambia&&Boolean(f.ganan);$('buscar').value=f.componente==='b1'?'Madrid':'';pintarTodo();if(reencuadrar)encuadrarActuacion();}
montarComparar = function(){for(const c of D.carteras.componentes)$('componente').append(el('option',{value:c.clave,texto:c.nombre}));$('componente').addEventListener('change',()=>{const c=D.carteras.componentes.find(x=>x.clave===$('componente').value),op=c.opciones[c.objetivos[0][0]];E.cartera=(op.find(x=>/\|3(_12)?$/.test(x[0]))||op[0])[0];E.cambia=false;sincronizarActuacion();});$('objetivo').addEventListener('change',()=>{const c=D.carteras.componentes.find(x=>x.clave===$('componente').value),op=c.opciones[$('objetivo').value],actual=carteraActual().opcion;E.cartera=(op.find(x=>x[1]===actual)||op[0])[0];sincronizarActuacion();});};
pintarComparar = function(){
  const f=carteraActual(),c=D.carteras.componentes.find(x=>x.clave===f.componente);$('componente').value=f.componente;$('objetivo').replaceChildren(...c.objetivos.map(([value,texto])=>el('option',{value,texto})));$('objetivo').value=f.objetivo;$('comparar-alcance').textContent=f.componente==='b1'?'Madrid capital · Refugios climáticos':'Comunidad de Madrid · Atención primaria';
  $('opciones-cartera').replaceChildren(...c.opciones[f.objetivo].map(([clave,texto])=>{const i=el('input',{type:'radio',name:'opcion',value:clave});i.checked=clave===E.cartera;i.addEventListener('change',()=>{E.cartera=clave;sincronizarActuacion();});return el('label',{},[i,el('span',{texto:f.componente==='b1'?'Hasta '+texto:texto})]);}));
  $('condiciones').textContent=f.condiciones;
  $('barras').replaceChildren(el('p',{texto:f.componente==='b1'?'Personas con acceso a un mercado en la peor hora':'Personas que pasan a tener un centro dentro del umbral'}),...f.barras.map(b=>el('div',{clase:'barra-fila'},[el('span',{texto:b.etiqueta}),el('span',{clase:'barra',style:`width:${Math.max(1,Math.round(100*b.fraccion))}%;background:${b.color}`}),el('b',{texto:b.texto})])));
  $('zonas-texto').textContent=f.zonas.length?`Zonas para estudiar: ${f.municipios_zonas}. La cartera es regional; las celdas de búsqueda de 250 m no son solares ni centros aprobados.`:'Los recursos son límites máximos. La lista muestra los mercados y las horas realmente elegidos.';
  $('casilla-cambia').hidden=!f.ganan;$('ver-cambia').checked=E.cambia&&Boolean(f.ganan);$('cambia-texto').textContent=modoCambia()?`${f.ganan.texto} personas de la población objetivo pasan a tener un centro dentro del umbral.`:'';$('leyenda-cambia').replaceChildren();
  $('mercados-elegidos').replaceChildren(...mercadosElegidos().map(p=>el('div',{clase:'mercado-fila'},[el('span',{clase:'numero-mercado',texto:String(p.orden)}),el('div',{},[el('strong',{texto:p.nombre}),el('p',{texto:`Ampliación: ${p.horas} · ${p.numeroHoras} horas`})])])));
  $('bloque-escenarios').hidden=!f.escenarios;$('escenarios').replaceChildren(f.escenarios?tabla(f.escenarios):'');$('estado-solver').textContent=f.estado;
  $('b-c').replaceChildren(el('p',{clase:'nota',texto:f.limites}),...(f.componente==='b1'?D.textos.b_c.b:[]).map(texto=>el('p',{clase:'nota',texto})));
};

function mapaDeFicha(f){const puntos=f.componente==='b1'?mercadosElegidos():f.zonas;if(!puntos.length)return'';const caja=f.componente==='b1'?D.territorios['municipio:28079'].caja:f.ganan?.caja||D.territorios['comunidad:28'].caja;const viewport=new deck.WebMercatorViewport({width:900,height:290}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],{padding:30});const v=new deck.WebMercatorViewport({...viewport,width:900,height:290});const path=p=>p.map((q,i)=>{const [x,y]=v.project(q);return`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`;}).join(' ')+'Z';return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 290" role="img" aria-label="Localización de las zonas o mercados elegidos"><rect width="900" height="290" fill="#f6f8fa"/>${D.municipios.map(m=>`<path d="${path(m.p)}" fill="#e5ebef" stroke="#fff" stroke-width=".8"/>`).join('')}${puntos.map((p,i)=>{const[x,y]=v.project([p.lon,p.lat]);const nombre=p.nombre||p.municipio||`Zona ${i+1}`;return`<circle cx="${x}" cy="${y}" r="10" fill="#b51d2f" stroke="white" stroke-width="2"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="white" font-family="Segoe UI,Arial,sans-serif" font-size="12" font-weight="700">${i+1}</text><text x="${x+15}" y="${y+4}" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="#1a1a1a" stroke="white" stroke-width="3" paint-order="stroke">${escapar(nombre)}</text>`;}).join('')}</svg><p>Localización de la actuación propuesta. ${f.componente==='b1'?'Los números corresponden a los mercados de la tabla.':'Las marcas son zonas de búsqueda para estudiar.'}</p>`;}
pintarFicha = function(){const f=carteraActual();if(U.ficha===E.cartera)return;U.ficha=E.cartera;baseInterfaz.ficha();$('ficha-titulo').textContent='Ficha de decisión';$('ficha-contexto').textContent='CercaSalud Madrid · '+(f.componente==='b1'?'Madrid capital':'Comunidad de Madrid');$('ficha-subtitulo').textContent=f.titulo.replace(/^Ficha de decisión\s*[-–]\s*/,'');$('ficha-medida').textContent=f.componente==='b1'?'Personas con acceso a un mercado en la peor hora':'Personas que pasan a tener un centro dentro del umbral';const bs=f.componente==='b1'?[f.barras[0],f.barras[2],f.barras[1]]:[f.barras.find(b=>b.etiqueta==='Cartera calculada'),f.barras.find(b=>b.etiqueta==='Regla simple'),{texto:String(f.zonas.length),etiqueta:'Zonas de estudio'}];$('ficha-cifras').replaceChildren(...bs.map(b=>el('div',{},[el('div',{clase:'valor',texto:b.texto}),el('p',{texto:b.etiqueta})])));$('ficha-mapa').innerHTML=mapaDeFicha(f);$('ficha-atribucion').textContent=D.textos.fuentes.atribuciones.join(' · ');const html=$('descargas').querySelector('a');if(html){html.textContent='Descargar esta ficha (HTML)';html.addEventListener('click',descargarFicha);}};
async function descargarFicha(e){e.preventDefault();const css=(await Promise.all(['interfaz.css','cruces.css'].map(p=>fetch(p).then(r=>r.text())))).join('\n'),ficha=$('vista-ficha').cloneNode(true);ficha.removeAttribute('hidden');ficha.querySelectorAll('.sin-imprimir,#descargas').forEach(n=>n.remove());ficha.querySelectorAll('details').forEach(d=>d.open=true);const extra='html,body{height:auto;overflow:visible;background:white}#vista-ficha{position:static;inset:auto;margin:auto;max-width:1160px;overflow:visible;border:0;box-shadow:none}.tabla-scroll{overflow:visible}';const url=URL.createObjectURL(new Blob([`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CercaSalud Madrid · Ficha de decisión</title><style>${css}${extra}</style><body>${ficha.outerHTML}</body></html>`],{type:'text/html;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`ficha-cercasalud-${E.cartera.replaceAll('|','-')}.html`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
irAPaso = function(paso){salirDel3d();E.paso=paso;document.body.classList.remove('resultados-ocultos');$('plegar-resultados').textContent='Ver mapa';$('plegar-resultados').setAttribute('aria-expanded','true');document.body.classList.toggle('comparando',paso==='comparar');document.body.classList.toggle('en-ficha',paso==='ficha');for(const nombre of ['diagnosticar','comparar','ficha'])$(`vista-${nombre}`).hidden=nombre!==paso;document.querySelectorAll('[data-paso]').forEach(b=>{const activo=b.dataset.paso===paso;b.setAttribute('aria-selected',String(activo));b.tabIndex=activo?0:-1;});$('panel').scrollTop=0;if(paso!=='diagnosticar'){if(paso==='comparar')$('vista-comparar').scrollTop=0;else $('vista-ficha').scrollTop=0;sincronizarActuacion(paso==='comparar');}else pintarTodo();};

function abrirDialogo(id){U.foco=document.activeElement;$(id).hidden=false;$(id).querySelector('button,a,input,select')?.focus();}
montarModales = function(){baseInterfaz.modales();for(const id of ['datos','ayuda']){$(id).addEventListener('click',e=>{if(e.target===$(id)){cerrar(id);U.foco?.focus();}});}for(const [id,boton]of[['datos','abrir-datos'],['ayuda','abrir-ayuda']])$(boton).addEventListener('click',()=>abrirDialogo(id));document.querySelectorAll('[data-cerrar]').forEach(b=>b.addEventListener('click',()=>U.foco?.focus()));document.addEventListener('keydown',e=>{const modal=document.querySelector('.capa-modal:not([hidden])');if(!modal)return;if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();cerrar(modal.id);U.foco?.focus();}if(e.key==='Tab'){const focos=[...modal.querySelectorAll('button,a[href],input,select,summary')].filter(n=>n.getClientRects().length);if(!focos.length)return;const a=focos[0],b=focos[focos.length-1];if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus();}else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus();}}},true);};
