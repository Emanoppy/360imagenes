"""
compose_360.py

Arma una sola imagen ancha (2:1, lista para inyectar como 360) a partir de
2 a 4 imagenes sueltas (por ejemplo: gancho, antes, despues, oferta),
pegadas en fila. Pensado para que girar el anuncio revele la historia por
partes en vez de mostrarla toda de una.

Uso:
    python compose_360.py panel1.jpg panel2.jpg panel3.jpg -o tira.jpg
    python compose_360.py antes.jpg despues.jpg oferta.jpg -o tira.jpg --alto 1024 --etiquetas "ANTES,DESPUES,-30% HOY"
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANCHO_COSTURA = 24  # pixeles de degradado entre paneles, para que no se note el corte


def _ajustar_panel(img: Image.Image, ancho: int, alto: int) -> Image.Image:
    """Recorta y escala la imagen para llenar exactamente ancho x alto
    (recorte centrado, sin deformar)."""
    img = img.convert("RGB")
    ratio_objetivo = ancho / alto
    ratio_actual = img.width / img.height

    if ratio_actual > ratio_objetivo:
        nuevo_ancho = int(img.height * ratio_objetivo)
        offset = (img.width - nuevo_ancho) // 2
        img = img.crop((offset, 0, offset + nuevo_ancho, img.height))
    else:
        nuevo_alto = int(img.width / ratio_objetivo)
        offset = (img.height - nuevo_alto) // 2
        img = img.crop((0, offset, img.width, offset + nuevo_alto))

    return img.resize((ancho, alto), Image.LANCZOS)


def _dibujar_etiqueta(panel: Image.Image, texto: str) -> Image.Image:
    panel = panel.copy()
    draw = ImageDraw.Draw(panel, "RGBA")
    alto_franja = max(60, panel.height // 8)

    try:
        fuente = ImageFont.truetype("arialbd.ttf", size=alto_franja // 2)
    except OSError:
        fuente = ImageFont.load_default()

    draw.rectangle(
        [(0, panel.height - alto_franja), (panel.width, panel.height)],
        fill=(0, 0, 0, 140),
    )
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    x = (panel.width - ancho_texto) // 2
    y = panel.height - alto_franja + (alto_franja - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), texto, font=fuente, fill=(255, 255, 255, 255))
    return panel


def _dibujar_indicador_giro(panel: Image.Image, texto: str = "Desliza para ver mas →") -> Image.Image:
    """Dibuja una pastilla semi-transparente con el aviso de que se puede
    girar, quemada directamente sobre los pixeles (no es metadata)."""
    panel = panel.copy()
    draw = ImageDraw.Draw(panel, "RGBA")

    try:
        fuente = ImageFont.truetype("arialbd.ttf", size=max(18, panel.height // 24))
    except OSError:
        fuente = ImageFont.load_default()

    padding_x, padding_y = 18, 10
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]

    ancho_pastilla = ancho_texto + padding_x * 2
    alto_pastilla = alto_texto + padding_y * 2
    x0 = (panel.width - ancho_pastilla) // 2
    y0 = max(20, panel.height // 30)

    draw.rounded_rectangle(
        [(x0, y0), (x0 + ancho_pastilla, y0 + alto_pastilla)],
        radius=alto_pastilla // 2,
        fill=(0, 0, 0, 150),
    )
    draw.text(
        (x0 + padding_x, y0 + padding_y - bbox[1]),
        texto,
        font=fuente,
        fill=(255, 255, 255, 255),
    )
    return panel


def _difuminar_costuras(canvas: Image.Image, num_paneles: int) -> Image.Image:
    """Aplica un degradado suave en cada union entre paneles para que no
    se vea como una linea recta y dura."""
    ancho_panel = canvas.width // num_paneles
    pixeles = canvas.load()

    for p in range(1, num_paneles):
        x_costura = p * ancho_panel
        for dx in range(-ANCHO_COSTURA // 2, ANCHO_COSTURA // 2):
            x = x_costura + dx
            if x <= 0 or x >= canvas.width - 1:
                continue
            peso = abs(dx) / (ANCHO_COSTURA / 2)  # 0 en el centro, 1 en los bordes
            for y in range(canvas.height):
                izq = pixeles[max(x - 1, 0), y]
                der = pixeles[min(x + 1, canvas.width - 1), y]
                mezcla = tuple(
                    int(izq[c] * (1 - peso) * 0.5 + der[c] * (1 - peso) * 0.5 + pixeles[x, y][c] * peso)
                    for c in range(3)
                )
                pixeles[x, y] = mezcla

    return canvas


def componer_360(
    rutas_imagenes: list[str],
    salida: str,
    alto: int = 1024,
    etiquetas: list[str] | None = None,
    indicador_giro: bool = True,
) -> str:
    n = len(rutas_imagenes)
    if not (2 <= n <= 4):
        raise ValueError("Se necesitan entre 2 y 4 imagenes para componer la tira 360.")

    ancho_total = alto * 2  # el resultado final tiene que ser 2:1
    ancho_panel = ancho_total // n

    canvas = Image.new("RGB", (ancho_panel * n, alto))

    for i, ruta in enumerate(rutas_imagenes):
        panel = _ajustar_panel(Image.open(ruta), ancho_panel, alto)
        if etiquetas and i < len(etiquetas) and etiquetas[i]:
            panel = _dibujar_etiqueta(panel, etiquetas[i])
        if i == 0 and indicador_giro:
            panel = _dibujar_indicador_giro(panel)
        canvas.paste(panel, (i * ancho_panel, 0))

    canvas = _difuminar_costuras(canvas, n)

    if canvas.size != (ancho_total, alto):
        canvas = canvas.resize((ancho_total, alto), Image.LANCZOS)

    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(salida, format="JPEG", quality=95)
    return salida


def main():
    parser = argparse.ArgumentParser(description="Compone 2-4 imagenes en una tira 2:1 lista para inyectar como 360.")
    parser.add_argument("imagenes", nargs="+", help="2 a 4 rutas de imagenes, en el orden en que apareceran girando")
    parser.add_argument("-o", "--salida", required=True, help="Archivo de salida (.jpg)")
    parser.add_argument("--alto", type=int, default=1024, help="Alto del resultado (el ancho sera el doble)")
    parser.add_argument("--etiquetas", default=None, help='Texto por panel separado por comas, ej: "ANTES,DESPUES,-30% HOY"')
    parser.add_argument(
        "--sin-indicador", dest="indicador_giro", action="store_false", default=True,
        help='No dibujar el aviso "Desliza para ver mas" en el primer panel',
    )

    args = parser.parse_args()
    etiquetas = args.etiquetas.split(",") if args.etiquetas else None

    out = componer_360(args.imagenes, args.salida, alto=args.alto, etiquetas=etiquetas, indicador_giro=args.indicador_giro)
    print(f"Listo: {out} (ahora se le puede aplicar inject_360.py)")


if __name__ == "__main__":
    main()
