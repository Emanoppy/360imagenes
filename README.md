# 360 Imagenes — Inyector de metadatos 360 (RICOH THETA S)

Herramienta que convierte cualquier foto JPEG en un archivo que Facebook e
Instagram abren con su **visor esferico interactivo** (arrastrar para mirar
alrededor / control por giroscopio en el celular), sin necesidad de una
camara 360 real.

## Para que sirve

Pensada para pauta publicitaria: un anuncio que el usuario puede girar con
el dedo o moviendo el celular (giroscopio) rompe el scroll del feed mucho
mejor que una imagen estatica. Esta herramienta genera el archivo con los
metadatos correctos; el resto (como publicarlo para que el efecto sobreviva
en el anuncio) esta documentado mas abajo en **Como publicarla en Facebook**.

## Tecnologia

- **Python 3** — logica principal (`inject_360.py`)
- **[piexif](https://github.com/hMatoba/Piexif)** — lectura/escritura de EXIF
- **Pillow (PIL)** — apertura, conversion y recodificado del JPEG
- **Flask** — servidor web local (`app.py`) que expone la herramienta como pagina
- **HTML + JS vanilla** (`templates/index.html`) — zona de arrastrar y soltar, sin frameworks ni build step

## Que es

Facebook decide si abre una foto como "normal" o como "360" leyendo los
metadatos del archivo, no analizando el contenido de la imagen. Esta
herramienta escribe esos metadatos:

| Etiqueta | Bloque | Valor | Para que sirve |
|---|---|---|---|
| `Make` | EXIF | `RICOH` | Simula que la foto viene de una camara 360 conocida |
| `Model` | EXIF | `RICOH THETA S` | Idem |
| `GPano:UsePanoramaViewer` | XMP | `True` | Le dice a Facebook/Google que use el visor esferico |
| `GPano:ProjectionType` | XMP | `equirectangular` | Etiqueta clave: activa el visor de esfera + giroscopio |
| `GPano:FullPanoWidth/HeightPixels` | XMP | ancho/alto real de la foto | Le indica al visor como envolver la imagen en la esfera |

## Como funciona (por dentro)

1. **EXIF** se escribe con [`piexif`](https://github.com/hMatoba/Piexif) en el segmento `APP1` estandar del JPEG.
2. **XMP (GPano)** no lo puede escribir `piexif` (solo maneja EXIF), asi que
   `inject_360.py` arma a mano el paquete XML de Google Photo Sphere y lo
   inserta como un **segundo segmento `APP1`** justo despues de la cabecera
   del JPEG — el mismo mecanismo que usan las camaras 360 reales.
3. El resultado es un `.jpg` identico a simple vista, pero que Facebook,
   Instagram y Google Photos reconocen como panoramica.

## Como publicarla en Facebook (imprescindible)

**No subas el archivo directo en el selector de imagenes del Ads Manager.**
Ese pipeline (el de creativos de anuncio) re-comprime y re-codifica la
imagen, y en ese proceso se pierde el bloque XMP con `GPano` — el anuncio
sale como foto plana normal aunque el archivo que subiste estuviera bien
inyectado.

El pipeline que si respeta el GPano es el de **fotos nativas de la Pagina**
(el mismo que procesa fotos 360 reales). Por eso, para que la interactividad
sobreviva en el anuncio, hay que usar el metodo de **Dark Post** (anuncio
sobre una publicacion existente) en vez de crear el anuncio desde cero:

1. **Publicar en la Fan Page**: sube primero la imagen ya inyectada
   (`RICOH THETA S` + `GPano`) a tu pagina de Facebook de forma organica
   (publicada normalmente o como no listada). Confirma en la pagina que se
   ve el icono del mundo/brujula y que el giro funciona antes de seguir.
2. **Ir al Ads Manager**: crea la campana y el conjunto de anuncios como
   siempre.
3. **Nivel Anuncio**: en la seccion de configuracion del anuncio, en vez de
   "Crear anuncio", elegi **"Usar publicacion existente"**.
4. **Seleccionar el post**: elegi la publicacion 360 que acabas de subir a
   la Fan Page.
5. **Configurar ubicaciones**: limita las ubicaciones manuales a **Feed de
   Facebook en celular**, para asegurar que el giroscopio responda y no se
   muestre estatica en otras redes (Audience Network, Stories, Instagram,
   etc. no soportan el visor esferico).

## Aviso honesto

Esto **no convierte la foto en una panoramica real**. Si la imagen no es una
equirectangular genuina (relacion de aspecto 2:1, sin costuras), el visor la
va a envolver igual, pero se va a ver deformada tipo "planeta" o "burbuja".
Es un efecto llamativo para destacar en el feed, no una fotografia 360 real.
La herramienta avisa automaticamente cuando la foto no es 2:1.

Ademas, falsificar el metadato de camara es una forma de misrepresentar el
contenido del anuncio: Meta puede revisar y restringir cuentas por esto, mas
alla de que tecnicamente el truco funcione. Usalo bajo tu propio criterio.

## Estructura del proyecto

```
360imagenes/
├── inject_360.py       # motor: EXIF + XMP GPano, uso por linea de comandos
├── app.py              # servidor web local (Flask)
├── templates/
│   └── index.html      # pagina con zona de arrastrar y soltar
└── requirements.txt
```

## Instalacion

```bash
pip install -r requirements.txt
```

## Uso — interfaz web (recomendado)

```bash
python app.py
```

Abrir `http://127.0.0.1:5000`, arrastrar una o varias fotos `.jpg` y
descargar el `.zip` con los resultados ya listos para subir.

## Uso — linea de comandos

```bash
# una foto
python inject_360.py entrada.jpg salida.jpg

# una carpeta completa
python inject_360.py carpeta_entrada carpeta_salida --batch

# ajustar el zoom inicial del visor (campo de vision, en grados)
python inject_360.py entrada.jpg salida.jpg --fov 90
```

## Requisitos

- Python 3.10+
- `piexif`, `Pillow`, `Flask` (ver `requirements.txt`)
