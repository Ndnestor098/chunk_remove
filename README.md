# Control Image Project

Este proyecto es una herramienta automatizada para el procesamiento, limpieza y geoetiquetado de imágenes JPEG.

## Funcionalidades Principales

### 1. Limpieza de Imágenes (Chunk Removal)
El módulo `chunk_removal.py` implementa un algoritmo de limpieza estricta ("Chunk Removal") para archivos JPEG.
- **Eliminación de Metadatos**: Elimina segementos no esenciales como EXIF originales, comentarios, y otros marcadores de aplicación (APPn) que no son necesarios para la visualización de la imagen.
- **Reconstrucción Segura**: Reescribe el archivo conservando únicamente los marcadores esenciales (SOF, DHT, DQT, etc.) y el stream de datos comprimidos (scan data) sin recomprimir la imagen (Lossless).
- **Verificación**: Incluye rutinas de test para asegurar que las imágenes procesadas no contienen marcadores prohibidos.

### 2. Geoetiquetado (Geotagging)
El módulo `geotag.py` permite inyectar coordenadas GPS (Latitud/Longitud) en los metadatos EXIF de las imágenes procesadas.
- **Mapeo por Nombre**: Utiliza el nombre del archivo para determinar la ubicación. Busca coincidencias en el archivo `geolocation.json`.
- **Inyección EXIF**: Inserta los datos GPS estándar en la estructura EXIF de la imagen.

## Estructura del Proyecto

- `app.py`: Script principal que orquesta el flujo de trabajo:
    1. Procesa imágenes desde la carpeta `no_working/` hacia `working/` aplicando limpieza.
    2. Verifica la integridad de la limpieza.
    3. Aplica geoetiquetado basado en `geolocation.json`.
    4. Verifica que los datos GPS se hayan insertado correctamente.
- `chunk_removal.py`: Lógica principal de limpieza JPEG de bajo nivel.
- `geotag.py`: Funciones para manejo de EXIF y conversión de coordenadas.
- `geolocation.json`: Base de datos JSON que mapea nombres de lugares a coordenadas.

## Uso

1. Coloca las imágenes originales en la carpeta `no_working/`.
2. Asegúrate de que `geolocation.json` contenga las coordenadas para los lugares referenciados en los nombres de archivo.
3. Ejecuta el script principal:

```bash
python app.py
```

El script generará las imágenes procesadas en la carpeta `working/`.

## Licencia

**PROHIBIDO EL USO SIN AUTORIZACIÓN.**
Ver archivo `LICENSE` para más detalles. Este software es propietario y confidencial.
