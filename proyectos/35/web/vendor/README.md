# Librerías de terceros de la página web

Copias locales para que la página funcione sin internet (decisión del usuario del 16/11/2026: página HTML local al estilo WikiBarrio, con permiso para descargar las librerías al equipo).

| Archivo | Origen | Versión | Licencia | Comprobación |
|---|---|---|---|---|
| `deckgl-9.3.12.min.js` | Paquete npm `deck.gl`, `https://registry.npmjs.org/deck.gl/-/deck.gl-9.3.12.tgz`, archivo `package/dist.min.js` | 9.3.12 (publicada el 30/10/2026; misma serie 9.3 que usa pydeck 0.9.3) | MIT (`LICENSE-deckgl.txt`, copia de `package/LICENSE`) | Integridad del paquete: sha512 `+yP0dlxHod209CJ66NHhhfBn4OCpMdZvLUVnxaQmVXesW9pzeyKwdA7sjQ5h64K48R1/vsMOX2AwNWkOKiYdPw==`, igual a la del registro (16/11/2026). SHA-256 del archivo: `9a58a99e0590185cd4e12acbfece94cd77ad433688a5b27f184731704d03f108` |

El archivo contiene direcciones de internet de funciones opcionales que la página no usa (cargadores de H3 y Draco, geocodificador de Google). La comprobación de red de la página (ninguna petición fuera de 127.0.0.1) es la que acredita que no se piden.

No se modifica: para cambiar de versión, descargar el paquete, comprobar su integridad con el registro y actualizar esta tabla.
