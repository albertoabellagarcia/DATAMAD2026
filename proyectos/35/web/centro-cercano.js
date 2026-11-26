/* Destino de primaria del cálculo guardado: selección y dibujo, sin calcular rutas en el navegador. */
'use strict';
const CP = {datos:null,promesa:null,clic:null,seleccion:null,error:false,encuadre:null};
const previoCP = {clic:alPulsar,mapa:pintarMapa,puntos:capasPuntos,tarjeta:tarjetaFlotante};
const CP_VARIABLES = ['min_pie','min_tp_9_13','min_tp_16_20','pct_sin_pie','pct_sin_transporte'];

function cpZonaCalida(s){
  if(E.paso!=='diagnosticar'||U.tema!=='primaria'||E.desglose||!CP_VARIABLES.includes(E.variable))return false;
  // Incluye desde el salmón claro de minutos y el naranja/rojo de porcentajes.
  return Number.isInteger(s)&&D.sec['k_'+E.variable]?.[s]>=3;
}
function cpModo(){return variableActual().modo;}
function cpPosicion(info){
  if(info.coordinate?.length>=2&&info.coordinate.slice(0,2).every(Number.isFinite))return info.coordinate.slice(0,2);
  const puntos=info.object?.p?.flat();
  if(puntos?.length){const xs=puntos.map(p=>p[0]),ys=puntos.map(p=>p[1]);return[(Math.min(...xs)+Math.max(...xs))/2,(Math.min(...ys)+Math.max(...ys))/2];}
  return null;
}
async function cpCargar(){
  if(CP.datos||CP.promesa)return CP.promesa;
  CP.error=false;
  CP.promesa=leer('datos/centros_cercanos.json').then(datos=>{CP.datos=datos;}).catch(()=>{CP.error=true;}).finally(()=>{
    CP.promesa=null;
    pintarMapa();
  });
  return CP.promesa;
}
function cpActualizar(){
  const anterior=CP.seleccion?.clave;
  CP.seleccion=null;
  if(!CP.clic||E.seccion!==CP.clic.s){CP.clic=null;return;}
  if(!cpZonaCalida(E.seccion)||!CP.datos)return;
  const seccion=CP.datos.secciones[D.sec.cusec[E.seccion]],modo=cpModo();
  if(!seccion?.unidades?.length)return;
  const punto=CP.clic.posicion||seccion.unidades[0].slice(0,2);
  // Proximidad de selección entre puntos residenciales ya exportados de la sección.
  const escala=Math.cos(punto[1]*Math.PI/180);
  let unidad=seccion.unidades[0],distancia=Infinity;
  for(const f of seccion.unidades){const d=((f[0]-punto[0])*escala)**2+(f[1]-punto[1])**2;if(d<distancia){unidad=f;distancia=d;}}
  const offset=2+CP.datos.modos.indexOf(modo)*3;
  const centro=CP.datos.centros[unidad[offset]],minutos=unidad[offset+1],tipo=unidad[offset+2];
  if(!centro)return;
  const origen=tipo===1?seccion.origen_transporte:unidad.slice(0,2);
  const clave=[E.seccion,modo,centro.id,...origen].join('|');
  CP.seleccion={clave,centro,minutos,tipo,origen,modo,punto};
  if(clave!==anterior){
    cancelAnimationFrame(CP.encuadre);
    CP.encuadre=requestAnimationFrame(()=>{if(CP.seleccion?.clave===clave)cpEncuadrar();});
  }
}
function cpEncuadrar(){
  const f=CP.seleccion;if(!f||!cpZonaCalida(E.seccion))return;
  const xs=[f.punto[0],f.origen[0],f.centro.lon],ys=[f.punto[1],f.origen[1],f.centro.lat];
  const caja=[Math.min(...xs)-.0015,Math.min(...ys)-.0015,Math.max(...xs)+.0015,Math.max(...ys)+.0015];
  if(innerWidth>760){encuadrar(caja);return;}
  // En móvil la leyenda y la hoja ocupan el pie: encuadrar en el espacio que queda libre.
  const mapa=$('mapa').getBoundingClientRect(),h=mapa.height,w=mapa.width;
  const panel=$('panel').getBoundingClientRect(),leyenda=$('leyenda-mapa'),ficha=$('detalle-territorio');
  const top=Math.max(24,panel.bottom-mapa.top+24);
  const limites=[h-30];
  for(const n of[leyenda,ficha])if(n&&!n.hidden&&n.getBoundingClientRect().height)limites.push(n.getBoundingClientRect().top-mapa.top-28);
  const bottom=Math.min(...limites);
  if(bottom-top<65)return;
  const vista=new deck.WebMercatorViewport({width:w,height:h}).fitBounds([[caja[0],caja[1]],[caja[2],caja[3]]],
    {padding:{left:30,right:30,top,bottom:h-bottom}});
  E.zoom=Math.max(8,Math.min(15,Math.floor(vista.zoom)));E.nivelContexto=nivelContexto(vista.zoom);
  D.deck.setProps({initialViewState:{longitude:vista.longitude,latitude:vista.latitude,zoom:Math.min(vista.zoom,14.5),
    pitch:0,bearing:0,minZoom:ZOOM_MIN,transitionDuration:500,transitionInterpolator:new deck.FlyToInterpolator()}});
  pintarMapa();
}
function cpTextoTiempo(f){
  if(f.tipo===2)return 'Sin tiempo de recorrido calculado';
  const modo=f.tipo===0?'A pie · 3,0 km/h':`A pie o transporte · ${f.modo==='transporte_16_20'?'16–20':'9–13'} h`;
  return `≈ ${f.minutos} min · ${modo}`;
}
function cpPintarFicha(){
  $('centro-cercano')?.remove();
  if(!CP.clic||!cpZonaCalida(E.seccion))return;
  const caja=$('zona-senalada');if(!caja||caja.hidden)return;
  const ficha=el('section',{id:'centro-cercano',clase:'cp-ficha','aria-label':'Centro de atención primaria próximo','aria-live':'polite'});
  const f=CP.seleccion;
  if(!f){
    ficha.append(el('p',{clase:'nota',texto:CP.error?'No se ha podido cargar el centro próximo.':'Localizando el centro más cercano…'}));
    if(CP.error){const boton=el('button',{clase:'pt-enlace',texto:'Reintentar'});boton.addEventListener('click',()=>{cpCargar();cpPintarFicha();});ficha.append(boton);}
  }else{
    ficha.append(el('h3',{texto:f.tipo===2?'Centro próximo por distancia':'Centro más cercano en el cálculo'}),
      el('strong',{clase:'cp-nombre',texto:f.centro.nombre}),el('p',{clase:'cp-direccion',texto:f.centro.direccion}),
      el('p',{clase:'cp-tiempo',texto:cpTextoTiempo(f)}),
      el('p',{clase:'micro',texto:f.tipo===2?'Señalado por distancia en línea recta; no hay un recorrido evaluable desde esta referencia.':
        f.tipo===1?'Tiempo desde la referencia residencial de la sección, señalada en el mapa.':'Tiempo desde el punto residencial del estudio más próximo al clic, señalado en el mapa.'}));
    const ver=el('button',{clase:'pt-enlace',texto:'Ver zona y centro'});ver.addEventListener('click',cpEncuadrar);
    const ocultar=el('button',{clase:'pt-enlace',texto:'Ocultar centro'});ocultar.addEventListener('click',()=>{CP.clic=null;CP.seleccion=null;pintarMapa();});
    ficha.append(el('div',{clase:'cp-acciones'},[ver,ocultar]),el('p',{clase:'micro cp-nota',texto:'Referencia de proximidad del estudio; no indica el centro asignado.'}));
  }
  const cabecera=caja.querySelector('h3');if(cabecera)cabecera.after(ficha);else caja.prepend(ficha);
}
function cpCapas(){
  const f=CP.seleccion;if(!f)return[];
  const datos=[f.centro],posicion=d=>[d.lon,d.lat];
  // Orientación estable durante la animación: el rótulo apunta hacia el espacio entre ambos puntos.
  const xs=[f.punto[0],f.origen[0],f.centro.lon];
  const etiquetaIzquierda=f.centro.lon>=(Math.min(...xs)+Math.max(...xs))/2;
  return[
    new deck.ScatterplotLayer({id:'cp-origen',data:[f.origen],getPosition:d=>d,getRadius:5,radiusUnits:'pixels',getFillColor:[255,255,255],stroked:true,getLineColor:[18,48,70],getLineWidth:2,lineWidthUnits:'pixels'}),
    new deck.ScatterplotLayer({id:'cp-centro-halo',data:datos,getPosition:posicion,getRadius:17,radiusUnits:'pixels',getFillColor:[255,255,255,235],stroked:true,getLineColor:[18,48,70],getLineWidth:2,lineWidthUnits:'pixels'}),
    new deck.ScatterplotLayer({id:'cp-centro',data:datos,getPosition:posicion,getRadius:12,radiusUnits:'pixels',getFillColor:[18,48,70],pickable:true}),
    new deck.TextLayer({id:'cp-centro-cruz',data:datos,getPosition:posicion,getText:()=>'+',getColor:BLANCO,getSize:22,fontFamily:FUENTE,fontWeight:'bold',characterSet:'+'}),
    new deck.TextLayer({id:'cp-centro-nombre',data:datos,getPosition:posicion,getText:()=>f.tipo===2?'Centro próximo por distancia':'Centro más cercano',getSize:14,getColor:[18,48,70],getPixelOffset:[etiquetaIzquierda?-23:23,0],getTextAnchor:etiquetaIzquierda?'end':'start',background:true,getBackgroundColor:[255,255,255,245],backgroundPadding:[7,5],fontFamily:FUENTE,fontWeight:'bold',characterSet:'auto'}),
  ];
}
capasPuntos=function(){return[...previoCP.puntos(),...cpCapas()];};
pintarMapa=function(){cpActualizar();previoCP.mapa();cpPintarFicha();};
alPulsar=function(info){
  if(info.layer?.id==='cp-centro'&&CP.seleccion){PT.abierto=true;actualizarDisposicion();cpPintarFicha();$('centro-cercano')?.scrollIntoView({block:'nearest'});return;}
  if(info.layer?.id==='secciones'&&info.object&&!E.desglose){
    CP.clic=cpZonaCalida(info.object.s)?{s:info.object.s,posicion:cpPosicion(info)}:null;
    CP.seleccion=null;
  }
  previoCP.clic(info);
  if(CP.clic&&cpZonaCalida(E.seccion)){if(!CP.datos)cpCargar();pintarMapa();}
};
tarjetaFlotante=function(info){
  if(info.layer?.id==='cp-centro'&&CP.seleccion){const f=CP.seleccion;return simEstilo(htmlTarjeta(f.centro.nombre,f.centro.id,cpTextoTiempo(f),f.centro.direccion));}
  return previoCP.tarjeta(info);
};
