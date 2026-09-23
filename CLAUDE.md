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

## C2PA — proyecto aparte, aislado a proposito (desde 2026-09-23)

`c2pa_inspector.py` + `requirements-c2pa.txt` son un proyecto de APRENDIZAJE
sobre el estandar C2PA (Content Credentials), completamente aislado del
resto (no lo importan ni lo modifican inject_360.py/compose_360.py/
metadata_tools.py/app.py). Contexto: el usuario nota que Meta le esta
bajando rendimiento a anuncios con imagenes de IA (marcadas via C2PA y
SynthID). Limite claro ya establecido con el usuario: NO se construye nada
que elimine/falsee marcas de IA para evadir esa deteccion (a diferencia del
truco EXIF del 360, C2PA es un sistema de autenticidad real con firma
criptografica real). Lo que SI se construyo y es legitimo:

- `inspeccionar_c2pa()` — lee el manifiesto real de un archivo (que
  herramienta lo creo/edito, si declara `digitalSourceType` de IA, quien
  firmo, estado de validacion). Usa el SDK oficial `c2pa-python`.
- Verificado end-to-end: se firmo una imagen de prueba con los certificados
  de test oficiales del propio SDK (`es256_certs.pem`/`es256_private.key`,
  publicados en contentauth/c2pa-python) y el inspector la leyo bien.
- Se descargo y leyo una imagen REAL de Adobe Firefly
  (`contentauth/example-assets`, `Firefly_tabby_cat.jpg`) para comparar
  numeros reales: `issuer: Adobe Inc.`, `alg: Ps256`, numero de serie real,
  vs. los de nuestro certificado de prueba. Confirma que certificados y
  firmas son, en el fondo, numeros (serial number, clave publica/privada).
- Se encontro la lista de confianza oficial real de C2PA (2025):
  `github.com/c2pa-org/conformance-public/blob/main/trust-list/C2PA-TRUST-LIST.pem`
  (30 certificados: Google, DigiCert, SSL.com, vivo, Encypher, etc.).

**Pendiente sin resolver:** cargar esa lista de confianza en nuestro propio
`c2pa.Reader` (via `Settings`/`Context` o el `load_settings` legacy) no hizo
que el veredicto pasara de `signingCredential.untrusted` a confiable, ni
siquiera para la firma real de Adobe. Puede ser una inconsistencia real de
la libreria entre versiones de schema (hay un issue conocido en
contentauth/c2pa-rs sobre migracion de `trust.trust_anchors` legacy). Se
instalo `c2pa-python==0.37.10` (usa `c2pa-rs` 0.90.19 internamente).

**Proxima prueba propuesta (sin terminar):** en vez de pelear con la lista
real, aislar el problema firmando una imagen con nuestra PROPIA cadena de
prueba completa (`es256_certs.pem` de c2pa-python, que es leaf+intermediate
pero SIN su root) + agregar la raiz que le falta
(`github.com/contentauth/c2patool/blob/main/sample/trust_anchors.pem`, es
la raiz de esa misma cadena de test) como `trust_anchors` de nuestro lector,
para ver si asi si cambia a "confiable". Si funciona con nuestra propia
raiz mas no con la real, el problema esta en como arma la cadena la lista
real (le pueden faltar intermedios). Si tampoco funciona con nuestra propia
raiz, es un bug de la libreria en esta version.

## Como correr

```bash
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000
```
