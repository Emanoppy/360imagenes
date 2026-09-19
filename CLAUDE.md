# 360imagenes — contexto para retomar el proyecto

Herramienta que inyecta metadatos de camara 360 (EXIF RICOH THETA S + XMP GPano
equirectangular) en JPEGs para que Facebook los muestre con el visor de esfera
y giroscopio. Uso principal: anuncios de Facebook publicados como Dark Post.

## Estado (2026-09-19)

- Flujo probado en real por el usuario: foto -> pagina web local -> descarga ->
  publicacion en la Fan Page -> Dark Post en Ads Manager. El visor 360 funciono.
- Todo esta subido a https://github.com/Emanoppy/360imagenes (rama main).

## Archivos

- `inject_360.py` — motor: limpia metadatos previos (reconstruye desde pixeles) e inyecta EXIF + XMP GPano. CLI y `--batch`.
- `compose_360.py` — une 2-4 imagenes en una tira 2:1 (antes/despues/oferta) con etiquetas, degradado en costuras e indicador "Desliza para ver mas" (se apaga con `--sin-indicador`). Solo CLI por ahora.
- `metadata_tools.py` — `inspeccionar` (detecta marcas de IA en EXIF/XMP/PNG) y `limpiar`.
- `app.py` + `templates/index.html` — pagina local (Flask): arrastrar fotos, boton "Ver 360" (vista previa Three.js en marco de celular 9:16, con giroscopio), X para quitar fotos, descarga .zip. Cada foto se procesa por separado.

## Decisiones tomadas

- Fotos individuales pueden tener cualquier proporcion; `compose_360.py` las recorta a su panel y el resultado final sale 2:1 automaticamente.
- Una foto suelta que no es 2:1 igual activa el visor, pero se ve deformada tipo "planeta".
- FOV inicial recomendado: 75 (60-65 mas zoom al gancho, 85-90 mas contexto).
- Three.js fijado en `three@0.130.0` porque `DeviceOrientationControls` se elimino de versiones nuevas.
- Publicar SIEMPRE como Dark Post ("Usar publicacion existente"), ubicacion solo Feed de Facebook en celular. Subir el archivo directo al selector de creativos del Ads Manager pierde el XMP.
- Video 360 queda en pausa (mas ambicioso; seria inyeccion de Spherical Video Metadata en MP4). Primero mejorar lo de fotos.

## Hallazgos de investigacion

- Especificacion GPano (Google): 7 campos obligatorios, todos cubiertos. No hay firma, checksum ni verificacion de camara: un archivo inyectado es indistinguible de uno real a nivel de metadatos.
- Riesgo real es de politica, no tecnico: Meta tiene la categoria "Circumventing Systems" que podria aplicarse. No se encontraron casos publicos de bloqueos por este truco (en fotos organicas es una tecnica vieja y documentada). Riesgo sube con volumen; no escalar presupuesto hasta ver comportamiento real por un par de semanas.

## Pendiente

1. Conectar `compose_360.py` a la pagina web (con interruptor para el indicador de giro).
2. Probar con imagenes de producto finales y vigilar aprobacion/caida de anuncios.
3. Video 360 (en veremos).

## Como correr

```bash
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000
```
