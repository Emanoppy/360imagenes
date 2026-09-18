"""
metadata_tools.py

Inspeccionar o limpiar los metadatos de una imagen. Pensado para el caso de
imagenes generadas con IA: suelen traer metadatos que delatan el origen
(herramienta usada, prompt, marcas de "Content Credentials"/C2PA) y hay que
verlos y limpiarlos antes de inyectarles los metadatos de RICOH THETA S.

Uso:
    python metadata_tools.py inspeccionar entrada.jpg
    python metadata_tools.py limpiar entrada.jpg salida.jpg
"""

import argparse
from pathlib import Path

import piexif
from PIL import Image

MARCADORES_IA = [
    "midjourney", "dall-e", "dalle", "stable diffusion", "stability",
    "comfyui", "automatic1111", "leonardo.ai", "firefly", "runway",
    "c2pa", "content credentials", "generative", "diffusion", "sdxl",
]


def inspeccionar_metadatos(path: str) -> dict:
    resultado = {
        "archivo": path,
        "formato": None,
        "dimensiones": None,
        "exif": {},
        "xmp_presente": False,
        "xmp_extracto": None,
        "chunks_texto": {},
        "posibles_marcas_ia": [],
    }

    img = Image.open(path)
    resultado["formato"] = img.format
    resultado["dimensiones"] = img.size

    exif_raw = img.info.get("exif")
    if exif_raw:
        try:
            exif_dict = piexif.load(exif_raw)
            for ifd in ("0th", "Exif"):
                for tag, val in exif_dict.get(ifd, {}).items():
                    tabla = piexif.TAGS.get(ifd, {})
                    nombre = tabla[tag]["name"] if tag in tabla else str(tag)
                    resultado["exif"][nombre] = val
        except Exception:
            pass

    with open(path, "rb") as f:
        raw = f.read()
    if b"ns.adobe.com/xap" in raw or b"<x:xmpmeta" in raw:
        resultado["xmp_presente"] = True
        ini = raw.find(b"<x:xmpmeta")
        fin = raw.find(b"</x:xmpmeta>")
        if ini != -1 and fin != -1:
            resultado["xmp_extracto"] = raw[ini:fin + 12].decode("utf-8", errors="ignore")[:2000]

    if img.format == "PNG":
        for k, v in (img.info or {}).items():
            if isinstance(v, str):
                resultado["chunks_texto"][k] = v[:500]

    texto_junto = " ".join([
        str(resultado["exif"]),
        resultado["xmp_extracto"] or "",
        str(resultado["chunks_texto"]),
    ]).lower()
    resultado["posibles_marcas_ia"] = [m for m in MARCADORES_IA if m in texto_junto]

    return resultado


def limpiar_metadatos(input_path: str, output_path: str, quality: int = 95) -> str:
    """Reconstruye la imagen solo a partir de los pixeles, descartando
    cualquier EXIF/XMP/ICC/IPTC/chunk de texto del archivo original."""
    img = Image.open(input_path)
    if img.mode not in ("RGB",):
        img = img.convert("RGB")

    limpio = Image.frombytes(img.mode, img.size, img.tobytes())

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    limpio.save(output_path, format="JPEG", quality=quality)
    return output_path


def _imprimir(resultado: dict):
    print(f"Archivo: {resultado['archivo']}")
    print(f"Formato: {resultado['formato']}  Dimensiones: {resultado['dimensiones']}")
    print(f"EXIF: {resultado['exif'] or '(vacio)'}")
    print(f"XMP presente: {resultado['xmp_presente']}")
    if resultado["chunks_texto"]:
        print(f"Chunks de texto (PNG): {list(resultado['chunks_texto'].keys())}")
    if resultado["posibles_marcas_ia"]:
        print(f"AVISO - posibles marcas de IA encontradas: {resultado['posibles_marcas_ia']}")
    else:
        print("Sin marcas conocidas de IA en los metadatos.")


def main():
    parser = argparse.ArgumentParser(description="Inspeccionar o limpiar metadatos de una imagen.")
    sub = parser.add_subparsers(dest="accion", required=True)

    p_insp = sub.add_parser("inspeccionar", help="Muestra los metadatos actuales de una imagen")
    p_insp.add_argument("archivo")

    p_lim = sub.add_parser("limpiar", help="Elimina todos los metadatos de una imagen")
    p_lim.add_argument("entrada")
    p_lim.add_argument("salida")

    args = parser.parse_args()

    if args.accion == "inspeccionar":
        _imprimir(inspeccionar_metadatos(args.archivo))
    elif args.accion == "limpiar":
        out = limpiar_metadatos(args.entrada, args.salida)
        print(f"Listo, metadatos eliminados: {out}")


if __name__ == "__main__":
    main()
