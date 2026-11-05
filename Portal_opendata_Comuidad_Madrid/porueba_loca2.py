
import requests

# URL del recurso CSV del catálogo de datos abiertos
url = "https://datos.comunidad.madrid/dataset/calidad_aire_estaciones/resource/c05f6436-783e-4b04-b0d2-47848daea984/download/red-de-calidad-del-aire-estaciones.csv"

# Nombre del archivo de destino
archivo = "estaciones.csv"

try:
    # Descargar el recurso
    respuesta = requests.get(url, timeout=30)

    # Comprobar que la descarga se ha realizado correctamente
    respuesta.raise_for_status()

    # Guardar el contenido en un archivo CSV
    with open(archivo, "wb") as f:
        f.write(respuesta.content)

    print(f"Descarga completada. Archivo guardado como: {archivo}")

except requests.exceptions.RequestException as e:
    print(f"Error al descargar el archivo: {e}")
