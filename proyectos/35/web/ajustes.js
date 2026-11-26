/* Ajustes de la evaluación de la web del 24/11/2026 (cuatro revisiones: estética, comprensión, legibilidad y flujo).
   Solo cambian la presentación y la navegación: ningún dato ni cifra. Se carga el último. */
'use strict';

const anteriorAjustes = { montar: montarInterfaz, paso: irAPaso, leyenda: pintarLeyenda, comparar: pintarComparar };
const AJ = { tema: null, comparada: false };

/* Etiquetas más claras (revisión de comprensión): el texto visible cambia; la función de cada botón, no. */
const AJ_ETIQUETAS = {
  'pt-opciones': ['Ajustar mapa', 'Ajustar qué muestra el mapa'],
  'pt-informacion': ['Cifras', 'Mostrar u ocultar las cifras del territorio'],
  'pt-general': ['Toda la Comunidad', 'Ver toda la Comunidad de Madrid'],
};
// La «regla simple» no se definía en pantalla. Definición de `construccion.carteras_a_transporte` y `carteras_a`:
// las k zonas con más población sin opción en su propia celda.
const AJ_REGLA_SIMPLE = 'Regla simple: elegir las zonas con más personas sin opción dentro de su propia celda de 250 m, '
  + 'sin calcular a quién más llegan. La cartera calculada elige todas las zonas a la vez y no cuenta dos veces a nadie.';

function ajEtiquetas() {
  for (const [id, [texto, ayuda]] of Object.entries(AJ_ETIQUETAS)) {
    const boton = $(id);
    if (!boton) continue;
    const etiqueta = boton.querySelector('span:last-child');
    if (etiqueta) etiqueta.textContent = texto;
    boton.setAttribute('aria-label', ayuda);
    boton.setAttribute('title', ayuda);
  }
  if ($('abrir-datos')) $('abrir-datos').textContent = 'Para quién y fuentes';
  const cabecera = document.querySelector('.acciones-cabecera');
  if (cabecera) cabecera.prepend($('abrir-demo'));
  $('abrir-demo').className = 'discreto';
  $('abrir-demo').textContent = 'Demo';
  $('abrir-demo').title = 'Recorrido guiado de la demo';
  $('datos-contenido').append($('version-corta'));
}

montarInterfaz = function () {
  anteriorAjustes.montar();
  ajEtiquetas();
  if ($('barras') && !$('aj-regla-simple')) {
    $('barras').after(el('p', { id: 'aj-regla-simple', clase: 'nota aj-regla', texto: AJ_REGLA_SIMPLE }));
  }
  const aviso = el('p', {id:'ficha-ejemplo',clase:'nota'}, ['Ficha de la actuación de ejemplo. ', el('button',{clase:'enlace',texto:'Elige otra en Comparar'})]);
  aviso.querySelector('button').addEventListener('click',()=>irAPaso('comparar'));
  $('ficha-medida').before(aviso);
  const resumen=el('section',{id:'comparar-resumen-compacto','aria-label':'Resumen de la comparación'});
  $('vista-comparar').querySelector('.encabezado-vista').after(resumen);
  let reajusteMapa;
  window.addEventListener('resize',()=>{
    clearTimeout(reajusteMapa);
    reajusteMapa=setTimeout(()=>{
      if(!D.deck||E.desglose)return;
      actualizarDisposicion();pintarLeyenda();
      if(E.paso==='comparar'){
        if(SIM.activo&&simClave())simEncuadrarMejores();else encuadrarActuacion();
      }else if(E.paso==='diagnosticar'&&E.territorio==='comunidad:28'&&E.seccion===null){
        encuadrar(D.territorios[E.territorio].caja,false);
      }
    },150);
  });
};

/* La pestaña «Comparar» tiene en cuenta el tema, como el botón de la barra lateral (que se oculta por duplicado):
   desde Refugios abre la ampliación de horarios; desde primaria, la actuación del modo elegido. Al volver a
   Diagnosticar se recupera el tema que había (antes se volvía siempre a atención primaria). */
irAPaso = function (paso) {
  const desdeDiagnostico = E.paso === 'diagnosticar';
  if (paso !== 'diagnosticar' && desdeDiagnostico) AJ.tema = {tema: U.tema, modo: U.modo, franja: U.franja, indicador: U.indicador};
  if (paso === 'comparar' && desdeDiagnostico && E.cartera) {
    const componente = U.tema === 'refugios' ? 'b1' : U.modo === 'pie' ? 'a_pie' : 'a_transporte';
    if (componenteDe(E.cartera) !== componente) E.cartera = componente === 'b1' ? 'b1|total|3_12' : `${componente}|total|3`;
  }
  if (paso === 'comparar') AJ.comparada = true;
  anteriorAjustes.paso(paso);
  if (paso === 'diagnosticar') {
    const anterior = AJ.tema;
    AJ.tema = null;
    if (!desdeDiagnostico && anterior && ['primaria', 'refugios', 'carencias', 'contexto'].includes(anterior.tema)) {
      Object.assign(U, anterior);
      activarTema(anterior.tema);
    }
  }
  const aviso = $('ficha-ejemplo');
  if (aviso) aviso.hidden = AJ.comparada;
};

/* Leyenda: la de zonas verdes solo tiene sentido en Diagnosticar; en Comparar salía sobre el mapa de mercados. */
pintarLeyenda = function () {
  if (E.paso !== 'diagnosticar' && E.parques) {
    E.parques = false;
    try { anteriorAjustes.leyenda(); } finally { E.parques = true; }
    return;
  }
  anteriorAjustes.leyenda();
};

/* Definición y explicación de la comparación, exportadas por Python en refugios. */
pintarComparar = function () {
  anteriorAjustes.comparar();
  const f = carteraActual();
  if($('comparar-resumen-compacto')){
    const barras=f.barras.filter(b=>['Hoy','Regla simple','Cartera calculada'].includes(b.etiqueta));
    $('comparar-resumen-compacto').replaceChildren(
      el('p',{clase:'micro',texto:f.componente==='b1'?'Personas con acceso en la peor hora':'Personas que pasan a tener opción'}),
      el('dl',{},barras.map(b=>el('div',{},[el('dt',{texto:b.etiqueta}),el('dd',{texto:b.texto})]))));
  }
  if ($('aj-regla-simple')) {
    $('aj-regla-simple').hidden = !f;
    $('aj-regla-simple').textContent = f?.componente === 'b1' ? D.textos.b_c.regla_b1 : AJ_REGLA_SIMPLE;
  }
  let explicacion = $('aj-explicacion-regla');
  if (!explicacion) {$('barras').after(explicacion = el('p', {id:'aj-explicacion-regla',clase:'nota'}));}
  explicacion.textContent = f?.explicacion_regla || '';
  explicacion.hidden = !f?.explicacion_regla;
  // Los códigos internos de la especificación («(D-33)») no dicen nada al jurado.
  if ($('condiciones')) $('condiciones').textContent = $('condiciones').textContent.replace(/\s*\(D-\d+\)/g, '');
};

/* Las tarjetas se mantienen sobre los paneles y permiten seguir moviendo o pulsando el mapa. */
const tooltipAntesDeAjustes=tarjetaFlotante;
let medidaTarjeta=null;
function altoTarjeta(html,ancho){
  if(!medidaTarjeta){const nodo=el('div',{clase:'medida-tarjeta','aria-hidden':'true'});document.body.append(nodo);medidaTarjeta={nodo};}
  if(medidaTarjeta.html!==html||medidaTarjeta.ancho!==ancho){
    Object.assign(medidaTarjeta.nodo.style,{width:`${ancho}px`});medidaTarjeta.nodo.innerHTML=html;
    Object.assign(medidaTarjeta,{html,ancho,alto:medidaTarjeta.nodo.getBoundingClientRect().height});
  }
  return medidaTarjeta.alto;
}
tarjetaFlotante=function(info){
  const tarjeta=tooltipAntesDeAjustes(info);if(!tarjeta)return tarjeta;
  const mapa=$('mapa'),ancho=Math.min(350,mapa.clientWidth-24),alto=Math.min(altoTarjeta(tarjeta.html,ancho),mapa.clientHeight-24);
  const x=Math.max(12,Math.min(info.x+12,mapa.clientWidth-ancho-12)),y=Math.max(12,Math.min(info.y+12,mapa.clientHeight-alto-12));
  return {...tarjeta,className:'tarjeta-flotante',style:{...tarjeta.style,zIndex:'12',pointerEvents:'none',width:`${ancho}px`,maxWidth:'calc(100vw - 24px)',fontSize:'14px',maxHeight:`${mapa.clientHeight-24}px`,overflow:'hidden',boxSizing:'border-box',transform:`translate(${x}px, ${y}px)`}};
};
