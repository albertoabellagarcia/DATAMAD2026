# Guion · ForMadrid (5 minutos)

Presenta: Barbara Cui. Daniel asiste y responde las preguntas de método y datos. Diapositivas: https://claude.ai/artifact/2tfDS3NesHoVGCTyyRXziT (el guion también está en las notas de cada diapositiva).
Ritmo objetivo: ~130 palabras por minuto. Total ≈ 640 palabras. Marcas de tiempo acumuladas.

---

## D1 · Portada · 0:00 – 0:30

Buenos días. Somos **ForMadrid**, el equipo de JiaJie Daniel Zheng y Barbara Cui.

Nuestra pregunta es muy concreta: **¿en qué municipios de la Comunidad de Madrid hace más falta reforzar la formación para el empleo?** Para responderla hemos construido un índice de desajuste del mercado laboral para los 179 municipios, con datos abiertos de la Comunidad, y una herramienta para que ayuntamientos y centros de formación lo usen.

## D2 · Problema y datos · 0:30 – 1:45

El problema: en marzo de 2025 había **casi 294.000 parados registrados** en la Comunidad, pero el empleo, el paro y la formación no están repartidos igual por el territorio. Hay municipios con mucho paro y poco empleo local, y otros donde hay empleo, pero de sectores distintos a los que conocen sus parados.

Para medirlo cruzamos **siete conjuntos de datos del Portal de Datos Abiertos** de la Comunidad: el empleo por centro de trabajo, los afiliados por lugar de residencia, el paro registrado por sector, el perfil de cualificación y de contrato, los cursos de formación para el empleo y las secciones censales para el mapa. Todo se descarga automáticamente por la **API CKAN**.

Y una cosa importante *(señalar el gráfico)*: en los afiliados por residencia, **uno de cada seis no tiene municipio asignado**, y ese porcentaje crece cada año. Si no lo corriges, parece que el empleo crece más que la población trabajadora: es un artefacto del dato. Lo hemos corregido y lo hemos comprobado con la población del INE.

## D3 · Resultados · 1:45 – 4:15

Con esos datos calculamos, para cada municipio y cada año, **tres componentes**: cuánto empleo local hay por cada trabajador residente, cuánta presión de paro hay, y cuánto se parecen los sectores de los parados a los sectores del empleo del municipio. El índice es la media de los tres, en términos relativos.

*(Señalar el mapa)* En rojo, los municipios con mayor desajuste: el sur y el este de la región, como Villarejo de Salvanés o Colmenar de Oreja, y la sierra oeste. En azul, Madrid y su corona norte y oeste.

Cuatro cifras:
1. Los **26 municipios** con mayor desajuste suman unos **16.000 parados**.
2. **Más de 18.000 parados** tendrían que cambiar de sector para encajar con el empleo de su propio municipio. Eso es exactamente lo que puede hacer la formación.
3. La recuperación no llega igual: entre 2021 y 2025 el paro cae un **35 % en los polos de empleo**, pero solo un **19,5 % en los municipios pequeños**.
4. La oferta de cursos presenciales es **casi la mitad donde más se necesita**, con la cautela de que solo podemos localizar una parte de los cursos.

Y el resultado es **robusto**: si cambiamos el denominador por la población del INE, el ranking prácticamente no cambia.

¿Para quién? Para los **ayuntamientos**, que pueden ver su posición y qué sectores les faltan, y para los **centros de formación**, que pueden decidir dónde abrir cursos. Y es **viable**: todo son datos abiertos, el código está en GitHub y se actualiza cada año en minutos.

## D4 · Herramienta · 4:15 – 5:00

Y esta es la herramienta: un mapa interactivo que se abre en cualquier navegador. Al pasar por un municipio aparece su ficha: su índice y su puesto, el paro y cómo ha evolucionado, el desajuste sectorial, la cualificación de sus trabajadores y los cursos que tiene.

Por ejemplo, **Villarejo de Salvanés**: puesto 25 de 179, un tercio de sus parados viene de sectores que no tienen empleo en el municipio, y no tiene ningún curso presencial localizado. **Ahí es donde reforzaríamos la formación.**

Muchas gracias.

---

## Consejos para el ensayo

- Si vas justa de tiempo, recorta en D3 la frase sobre los tres componentes (se puede explicar en las preguntas).
- Las cifras que hay que decir exactas: **179 municipios · 7 conjuntos de datos · 1 de cada 6 sin municipio · 16.000 parados · 18.000 cambiar de sector · 35 % frente a 19,5 % · Spearman 0,985**.
- Si la sala tiene conexión, se puede abrir `Mapa/ForMadrid_mapa.html` en D4 y pasar el ratón por Villarejo de Salvanés; si no, la captura basta.
- Decir «índice relativo» y no «tasa»: compara municipios entre sí; no es una cifra oficial.
