# Protocolo de evaluación con usuarios (R-USR-03)

**Estado:** protocolo preparado, **no aplicado**. Solo se usará con la autorización del titular del proyecto (SPEC D-08). Hasta entonces, la necesidad real de los usuarios sigue sin contrastar (E-01) y nada de lo que diga la herramienta acredita su utilidad.

**Participantes previstos:** técnicos de salud pública regional (usuario principal, D-21). Como secundarios, técnicos municipales de equipamientos y de planificación de atención primaria. No se recogen datos personales más allá del perfil profesional genérico; las notas se anonimizan.

**Material:** la app local (`uv run cercasalud app`) con la versión de datos indicada en su barra lateral, en un portátil sin conexión. Cada sesión dura unos 30 minutos y la conduce una persona que no ayuda a resolver las tareas.

## Tareas

### T1. Localizar una carencia, de un componente o coincidente

- **Consigna:** «Encuentre una zona de la Comunidad donde una parte importante de la población no tenga un centro de atención primaria a 30 minutos en transporte público, y diga cuántas personas son y si alguna parte no se pudo evaluar». Variante: «… y donde además no haya un refugio climático a 10 minutos a pie en la peor hora».
- **Qué observar:**
  - si encuentra la pantalla adecuada (2 o 4) sin ayuda, y en cuánto tiempo;
  - si distingue «sin opción verificada» de «no evaluable»;
  - si interpreta el rojo como «no hay recurso verificado» y no como «no hay ningún recurso»;
  - si menciona la franja horaria y el umbral.
- **Éxito:** da una cifra con su estado y su supuesto (umbral y franja) y menciona lo no evaluable.

### T2. Comparar dos carteras de actuación

- **Consigna:** «Compare la mejor cartera de 3 nuevos centros pensada para toda la población con la pensada para mayores de 65 años; o la de acceso a pie con la de transporte. ¿Qué ganaría y qué perdería cada una?».
- **Qué observar:**
  - si usa el comparador (pantalla 5) y los resultados (pantalla 6);
  - si lee la ganancia como personas que pasan a tener acceso, y no como pacientes ni como salud;
  - si mira el estado del solver y la comparación con la regla simple;
  - si advierte que A y B no se suman.
- **Éxito:** enuncia la diferencia entre carteras con sus cifras y una consecuencia (quién sigue fuera).

### T3. Justificar una elección con evidencia, supuestos e incertidumbre

- **Consigna:** «Elija una de las actuaciones y prepare la ficha que llevaría a una reunión. ¿Qué supuestos la sostienen y qué podría hacer que no se cumpliera?».
- **Qué observar:**
  - si exporta la ficha (pantalla 7) y qué formato elige;
  - si cita al menos un supuesto: umbral, velocidad, franja o supuesto de acceso a los mercados;
  - si cita la robustez (p80, márgenes, otra velocidad o la franja de tarde);
  - si identifica que una zona de búsqueda no es un solar;
  - si nombra un límite del documento de límites.
- **Éxito:** la justificación incluye la evidencia (cifra y fuente), al menos un supuesto y una incertidumbre.

## Registro de cada sesión

Una fila por tarea, con estas columnas:
- participante (código anónimo);
- tarea;
- tiempo;
- éxito (sí, parcial o no);
- errores de interpretación observados;
- comentarios literales relevantes, sin datos personales;
- mejora propuesta.

## Qué no mide este protocolo

- El efecto de la herramienta sobre decisiones reales.
- La salud de la población.
- La calidad de los datos de origen.

Un buen resultado en T1–T3 indica que la herramienta se entiende y se usa como se pretende. No demuestra que sus propuestas sean las mejores ni que se vayan a adoptar.
