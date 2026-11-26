# Equipo 46: Kuanto

**Cuánto dinero te sobra al mes según dónde vivas en la Comunidad de Madrid.**

- Repositorio completo (código, datos, documentación): https://github.com/Kuantoapp/kuantoapp.github.io
- Aplicación publicada: https://kuantoapp.github.io/
- **Ver la presentación en el navegador: https://izan-diaz.github.io/DATAMAD2026/**
- Ficheros de la presentación (HTML): [presentacion/index.html](presentacion/index.html), que empieza con el vídeo de Kuanto ([presentacion/video/corto.mp4](presentacion/video/corto.mp4)).

## Cómo ver la presentación

Lo más fácil: abre https://izan-diaz.github.io/DATAMAD2026/ (la misma presentación, publicada con GitHub Pages).

GitHub no abre ficheros HTML al pincharlos: muestra su código. Para verla sin conexión:

1. Descarga el repositorio con **Code → Download ZIP** y descomprímelo. Hace falta la carpeta `presentacion/` entera: el `index.html` solo no basta, porque usa los estilos, scripts, fuentes, imágenes y el vídeo de esa carpeta.
2. Abre `proyectos/46/presentacion/index.html` en el navegador (Chrome, Edge o Firefox).
3. El vídeo arranca al principio; si el navegador lo bloquea, pulsa play. Al acabar, avanza con las flechas del teclado. Para saltarte el vídeo, añade `?sin-corto` al final de la dirección.

## Qué hace

Al elegir dónde vivir se compara el alquiler, pero lo que importa es lo que queda a fin de mes. Kuanto pide tu sueldo, tu hogar y dónde trabajas, y para cada zona de la Comunidad (municipios y distritos de Madrid) calcula sueldo neto − alquiler − transporte más barato hasta el trabajo − cesta básica, y lo pinta en un mapa junto a las horas de viaje al mes. La cuenta se hace en el navegador: los datos del usuario no salen de su dispositivo.

## Equipo

[@yeraybc](https://github.com/yeraybc), [@izan-diaz](https://github.com/izan-diaz) y [@alexjimenez-git](https://github.com/alexjimenez-git).

## Datos

Catálogo de Datos Abiertos de la Comunidad de Madrid (renta disponible municipal, Bono Alquiler Joven 2022, gasto de los hogares de la EPF y redes de transporte del CRTM), cruzado con INE, SERPAVI (Ministerio de Vivienda), AEAT, GTFS del CRTM, BOE/BOCM y OpenStreetMap. Lista completa con URL, licencia y huella SHA-256: [data/README.md](https://github.com/Kuantoapp/kuantoapp.github.io/blob/main/data/README.md).
