// Crea la encuesta de DATAMAD en Google Forms.
// Uso: script.google.com > Nuevo proyecto > pega este archivo > Ejecutar crearEncuesta.
// Al terminar, el registro de ejecución muestra el enlace para responder y el de edición.

function crearEncuesta() {
  var form = FormApp.create('¿Te fías de cuándo llega el bus o el tren?');
  form.setDescription(
    'Encuesta anónima de un proyecto universitario para el datatón DATAMAD 2026 de la Comunidad de Madrid. ' +
    'Queremos saber cuánto fallan los anuncios de las apps de transporte público y cómo te afecta. ' +
    'Se tarda unos 2 minutos. No pedimos nombre, correo ni ningún dato personal.'
  );
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setProgressBar(true);
  form.setConfirmationMessage('¡Gracias! Tu respuesta nos ayuda a medir cuánto fallan las apps de transporte.');

  form.addCheckboxItem()
    .setTitle('¿Qué transporte público usas más?')
    .setChoiceValues(['Bus de la EMT', 'Bus interurbano', 'Metro', 'Cercanías', 'Metro Ligero', 'Otro'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Cuántos días a la semana lo usas?')
    .setChoiceValues(['1 o 2', '3 o 4', '5 o más', 'Menos de una vez por semana'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Miras en una app cuánto falta para que llegue?')
    .setChoiceValues(['Siempre', 'A veces', 'Nunca'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('En el último mes, ¿has llegado tarde a algún sitio por culpa del transporte?')
    .setChoiceValues(['Ninguna vez', '1 o 2 veces', '3 veces o más'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Te ha pasado que la app dijera una hora y el bus o el tren llegara mucho más tarde?')
    .setChoiceValues(['Nunca', 'Alguna vez', 'A menudo'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Te has ido de la parada creyendo que no venía y ha pasado justo después?')
    .setChoiceValues(['Sí', 'No'])
    .setRequired(true);

  form.addScaleItem()
    .setTitle('¿Cuánto te fías de lo que anuncia la app?')
    .setBounds(1, 5)
    .setLabels('Nada', 'Totalmente')
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Sales antes de casa «por si acaso»? ¿Cuántos minutos?')
    .setChoiceValues(['No', 'Unos 5 minutos', 'Unos 10 minutos', '15 minutos o más'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Has dejado de coger algún transporte porque no te fiabas de que llegara a tiempo?')
    .setChoiceValues(['Sí', 'No'])
    .setRequired(true);

  form.addTextItem()
    .setTitle('Si has respondido que sí, ¿cuál dejaste de coger?')
    .setRequired(false);

  form.addMultipleChoiceItem()
    .setTitle('Si la app te dijera «suele llegar entre 19 y 26 minutos» en vez de «21 minutos», ¿te sería…')
    .setChoiceValues(['Más útil', 'Igual de útil', 'Menos útil'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('¿Avisarías a otros viajeros de retrasos o de buses llenos desde la app?')
    .setChoiceValues(['Sí', 'No', 'Depende'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Edad')
    .setChoiceValues(['Menos de 25', '25 a 44', '45 a 64', '65 o más'])
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('¿Quieres contarnos alguna vez que te falló el transporte? (opcional, sin nombres)')
    .setRequired(false);

  Logger.log('Para responder: ' + form.getPublishedUrl());
  Logger.log('Para editar: ' + form.getEditUrl());
}
