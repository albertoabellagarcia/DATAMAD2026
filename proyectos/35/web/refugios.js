/* Ampliación de refugios. Selecciona resultados calculados y dibuja el inventario. */
'use strict';
const RF = {dia:'laborable_julio',edad:'total',iniciado:false};
const anteriorRefugios = {montar:montarInterfaz,todo:pintarTodo,tema:activarTema,territorio:pintarTerritorio,leyenda:pintarLeyenda,titulo:actualizarTituloMapa,clic:alPulsar};

montarInterfaz = function(){
  anteriorRefugios.montar();
  if(!D.refugios)return;
  const caja=el('section',{id:'refugios-ampliados','aria-label':'Refugios ampliados',hidden:''});
  $('ver-actuaciones').before(caja);
  $('ver-mercados').closest('label').id='casilla-mercados';
  caja.innerHTML=`<div class="rf-cabecera"><h2>Refugios frente al calor</h2><p class="micro">Madrid capital · Actualizado el 23/11/2026</p></div>
    <div id="rf-coberturas"><p class="nota">Personas a 10 min a pie. Las tres líneas son alternativas y no se suman entre sí ni con atención primaria.</p>
    <div class="dos-campos rf-filtros"><label class="campo">Periodo<select id="rf-dia"><option value="laborable_julio">Laborable de julio</option><option value="laborable_agosto">Laborable de agosto</option><option value="fin_de_semana">Fin de semana</option></select></label><label class="campo">Población<select id="rf-edad"><option value="total">Total</option><option value="75+">75 o más</option></select></label></div>
    <p id="rf-ambito" class="micro"></p><div id="rf-lineas" aria-live="polite"></div>
    <p class="rf-aviso">Color del mapa: cobertura de los 43 mercados en julio. Los filtros cambian las cifras de este panel; los puntos muestran el inventario ampliado.</p></div>
    <details class="desplegable" open><summary>Espacios por nivel de evidencia</summary><p class="nota">628 espacios. Marca los niveles que quieras ver; pulsa un punto para consultar su evidencia y horario. El inventario no indica si está abierto ahora.</p><div id="rf-niveles"></div><details class="desplegable"><summary>Tipos de espacio y colores</summary><ul id="rf-tipos" class="rf-tipos"></ul></details></details>
    <details class="desplegable"><summary>Parques, agua y piscinas</summary><p class="nota">Capas aparte: no son refugios y no entran en ninguna cobertura.</p><div id="rf-aparte"></div><p class="micro">2.164 fuentes operativas · 19 piscinas municipales al aire libre · 6.579 zonas verdes de toda la Comunidad (actualización del 23/11/2026).</p></details>
    <details class="desplegable"><summary>Horarios: 51 más codificados, 106 pendientes</summary><p class="nota">Además de las 36 bibliotecas municipales, 51 de los otros 157 espacios con respaldo tienen algún tramo de verano codificado.</p><div id="rf-horarios" class="tabla-scroll"></div><div id="rf-motivos"></div><p class="nota">Julio mejora porque varios centros culturales abren hasta las 21 o 21:30 h. Agosto cambia menos porque muchos centros cierran.</p><p class="nota">Cada horario se codifica texto a texto. Las comprobaciones exigen que cada hora esté escrita en la fuente y cada cierre de agosto esté nombrado; los casos sin codificar no pueden contener una referencia de verano sin revisar.</p></details>
    <details class="desplegable"><summary>Método, límites y descarga</summary><p id="rf-metodo" class="nota"></p><ul id="rf-limites" class="rf-limites"></ul><p class="nota">La línea verificada reproduce la base: 87.621,6 personas en la peor hora de julio. La ampliación no recalcula las carteras B1 ni los cruces sociales, que siguen usando la base de mercados.</p><a class="rf-descarga" href="datos/descargas/refugios_ampliados_lineas.csv" download>Descargar resultados de refugios (CSV)</a></details><details class="desplegable"><summary>Cobertura base de mercados y vista 3D</summary><div id="rf-base"></div></details>`;
  for(const id of ['rf-dia','rf-edad'])$(id).addEventListener('change',()=>{RF.dia=$('rf-dia').value;RF.edad=$('rf-edad').value;pintarCifrasRefugios();pintarTerritorio();});
  const r=D.refugios;
  r.niveles.forEach((n,i)=>{
    const entrada=el('input',{type:'checkbox',id:`rf-nivel-${i}`});
    entrada.addEventListener('change',()=>{entrada.checked?E.niveles.add(i):E.niveles.delete(i);pintarMapa();});
    $('rf-niveles').append(el('div',{clase:'rf-nivel'},[el('label',{clase:'casilla'},[entrada,el('span',{clase:`rf-forma rf-forma-${i}`}),`${n.etiqueta} (${miles(n.total)})`]),el('p',{clase:'nota',texto:n.texto})]));
  });
  r.tipos.forEach(t=>$('rf-tipos').append(el('li',{},[el('i',{style:`background:${t.color}`}),el('span',{texto:t.etiqueta})])));
  for(const clave of ['parques','refresco']){
    const entrada=el('input',{type:'checkbox',id:`rf-${clave}`});
    entrada.addEventListener('change',()=>{E[clave]=entrada.checked;pintarTodo();});
    $('rf-aparte').append(el('label',{clase:'casilla'},[entrada,r.casillas[clave]]));
  }
  $('rf-aparte').append(el('ul',{clase:'leyenda-tipos'},r.clases_parques.map(c=>el('li',{},[el('i',{style:`display:inline-block;width:14px;height:14px;background:${c.color};margin-right:7px`}),el('span',{texto:`${c.etiqueta} (${miles(c.total)})`})]))),el('p',{clase:'nota',texto:r.texto_parques}));
  $('rf-horarios').append(tabla({columnas:['Tipo','Con horario','Pendientes'],filas:r.detalle.horarios.map(h=>[h.tipo,`${h.codificados} de ${h.total}`,String(h.pendientes)])}));
  r.detalle.horarios.forEach(h=>$('rf-motivos').append(el('p',{clase:'nota',texto:`${h.tipo}: ${h.motivo}`})));
  $('rf-metodo').textContent=r.detalle.metodo;
  r.detalle.limites.forEach(texto=>$('rf-limites').append(el('li',{texto})));
  pintarCifrasRefugios();
};

function pintarCifrasRefugios(){
  const r=D.refugios.detalle.resultados[`${RF.dia}|${RF.edad}`];
  $('rf-ambito').textContent=`Madrid capital · ${r.poblacion} ${RF.edad==='total'?'habitantes':'personas de 75 años o más'} · Ventana 12–21 h`;
  $('rf-lineas').replaceChildren(...[1,0,2].map(i=>{
    const l=r.lineas[i];
    const card=el('article',{clase:`rf-linea rf-linea-${i}`},[el('h3',{texto:D.refugios.lineas[i].titulo})]);
    if(i===2){card.append(el('div',{clase:'rf-valor',texto:l.alguna.porcentaje}),el('p',{texto:`${l.alguna.personas} personas · Techo hipotético`}),el('p',{clase:'nota',texto:`Supone los ${miles(D.refugios.espacios.length)} espacios abiertos a todas horas y con acceso libre. No es cobertura observada.`}));return card;}
    const dato=(titulo,d)=>el('div',{},[el('b',{clase:'rf-valor',texto:d.porcentaje}),el('span',{texto:titulo}),el('small',{texto:`${d.personas} personas`})]);
    card.append(el('div',{clase:'rf-metricas'},[dato(`Peor hora · ${l.peor_hora}`,l.peor),dato('A alguna hora · 12–21 h',l.alguna)]));
    card.append(el('p',{clase:'rf-acreditable',texto:`Acreditable sin supuesto de acceso, a alguna hora: ${l.acreditable.personas} (${l.acreditable.porcentaje}).`}));
    if(l.acreditable&&Number(l.acreditable.personas.replaceAll('.','').replace(',','.'))<0.5)card.append(el('p',{clase:'nota',texto:D.textos.b_c.acreditable_cero}));
    card.append(el('p',{clase:'nota',texto:i===0?'Acceso supuesto en horario comercial. «Verificado» se refiere a la lista y la climatización.':'Incluye los mercados y los espacios con respaldo y horario de verano conocido. El acceso fuera de las bibliotecas es un supuesto.'}));
    return card;
  }));
}

activarTema = function(tema){
  if(D.refugios){
    if(tema==='refugios'&&!RF.iniciado){E.niveles=new Set([0,1]);RF.iniciado=true;}
  }
  anteriorRefugios.tema(tema);
  if(tema==='refugios')E.mercados=false;
  pintarTodo();
};
pintarTodo = function(){
  anteriorRefugios.todo();
  if(!$('refugios-ampliados'))return;
  const activo=U.tema==='refugios'&&E.paso==='diagnosticar';
  $('refugios-ampliados').hidden=!activo;
  if(activo&&D.mapa.desglose_refugio.por_territorio[E.territorio])$('rf-base').append($('territorio'));else $('refugios-ampliados').before($('territorio'));
  $('rf-coberturas').hidden=!D.mapa.desglose_refugio.por_territorio[E.territorio];
  $('casilla-mercados').hidden=activo;
  if(activo){E.mercados=false;$('ver-mercados').checked=false;$('alcance-tema').textContent=E.parques?'Zonas verdes: Comunidad de Madrid · Cobertura de refugios: solo Madrid capital':'Madrid capital · 10 min a pie · 3,0 km/h';}
  D.refugios.niveles.forEach((n,i)=>{$(`rf-nivel-${i}`).checked=E.niveles.has(i);});
  for(const clave of ['parques','refresco'])$(`rf-${clave}`).checked=E[clave];
};
pintarTerritorio = function(){
  anteriorRefugios.territorio();
  if(U.tema==='refugios'&&D.mapa.desglose_refugio.por_territorio[E.territorio]){
    const caja=$('territorio');caja.querySelector('.etiqueta-valor').textContent='Mapa base: solo los 43 mercados · julio';
    caja.querySelectorAll('p.nota,p.micro').forEach((p,i)=>{if(i>0)p.remove();});
    caja.append(el('p',{clase:'nota',texto:'Las cifras ampliadas de abajo corresponden al conjunto de Madrid capital; no están desglosadas por distrito.'}));
  }
};
pintarLeyenda = function(){anteriorRefugios.leyenda();if(E.variable==='refugio')$('leyenda').querySelector('.leyenda-titulo').textContent='Solo 43 mercados · Horas de acceso en julio';};
actualizarTituloMapa = function(){anteriorRefugios.titulo();if(U.tema==='refugios'&&E.paso==='diagnosticar'){$('mapa-titulo').textContent=E.parques?'Zonas verdes de la Comunidad y refugios':'Refugios: evidencia y cobertura';$('mapa-subtitulo').textContent=E.parques?'Verde: espacios abiertos, no refugios · Puntos y cobertura de refugios: Madrid capital':'Puntos: inventario ampliado · Color: horas con un mercado a 10 min a pie';}};
alPulsar = function(info){
  if(info.object&&['espacios','parques','refresco'].includes(info.layer?.id)){
    const tarjeta=$('zona-senalada');tarjeta.innerHTML=tarjetaRefugio(info.layer.id,info.object);tarjeta.hidden=false;
    const cerrar=el('button',{texto:'Cerrar ficha',clase:'enlace'});cerrar.addEventListener('click',()=>{tarjeta.hidden=true;});tarjeta.append(cerrar);
    if(innerWidth<=760)abrirPanelMovil(true);
    tarjeta.scrollIntoView({block:'nearest'});return;
  }
  anteriorRefugios.clic(info);
};
