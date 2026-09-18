"""
inject_360.py

Convierte una foto plana en un "falso 360": inyecta metadatos de camara
RICOH THETA S (EXIF) y el bloque GPano (XMP) que Facebook / Google Photos
leen para decidir si abren la imagen en el visor esferico.

Puntos clave que el snippet original (solo piexif) NO cubria:
  - GPano:ProjectionType vive en un paquete XMP, no en EXIF. piexif por si
    solo jamas activa el visor porque nunca escribe XMP.
  - El visor esferico exige, ademas de ProjectionType, las dimensiones
    Cropped*/FullPano* para saber como envolver la imagen en la esfera.

Aviso honesto: esto no convierte la foto en una panoramica real. Si la
imagen no es una equirectangular genuina (relacion 2:1, sin costuras),
Facebook la va a envolver igual, pero el resultado visual sera una
distorsion tipo "planeta" / "burbuja", util como gancho llamativo en el
feed, no una fotografia 360 real.

Uso:
    python inject_360.py entrada.jpg salida.jpg
    python inject_360.py entrada.jpg salida.jpg --fov 90
    python inject_360.py --batch carpeta_entrada carpeta_salida
"""

import argparse
import io
import struct
import sys
from pathlib import Path

import piexif
from PIL import Image

XMP_APP1_ID = b"http://ns.adobe.com/xap/1.0/\x00"


def build_exif_bytes(make: str, model: str, software: str) -> bytes:
    zeroth_ifd = {
        piexif.ImageIFD.Make: make,
        piexif.ImageIFD.Model: model,
        piexif.ImageIFD.Software: software,
    }
    exif_dict = {"0th": zeroth_ifd, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    return piexif.dump(exif_dict)


def build_xmp_packet(width: int, height: int, fov: float, stitching_software: str) -> bytes:
    xmp = f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.6-c140">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:GPano="http://ns.google.com/photos/1.0/panorama/">
      <GPano:UsePanoramaViewer>True</GPano:UsePanoramaViewer>
      <GPano:ProjectionType>equirectangular</GPano:ProjectionType>
      <GPano:StitchingSoftware>{stitching_software}</GPano:StitchingSoftware>
      <GPano:PoseHeadingDegrees>0.0</GPano:PoseHeadingDegrees>
      <GPano:InitialViewHeadingDegrees>0</GPano:InitialViewHeadingDegrees>
      <GPano:InitialViewPitchDegrees>0</GPano:InitialViewPitchDegrees>
      <GPano:InitialViewRollDegrees>0</GPano:InitialViewRollDegrees>
      <GPano:InitialHorizontalFOVDegrees>{fov}</GPano:InitialHorizontalFOVDegrees>
      <GPano:CroppedAreaLeftPixels>0</GPano:CroppedAreaLeftPixels>
      <GPano:CroppedAreaTopPixels>0</GPano:CroppedAreaTopPixels>
      <GPano:CroppedAreaImageWidthPixels>{width}</GPano:CroppedAreaImageWidthPixels>
      <GPano:CroppedAreaImageHeightPixels>{height}</GPano:CroppedAreaImageHeightPixels>
      <GPano:FullPanoWidthPixels>{width}</GPano:FullPanoWidthPixels>
      <GPano:FullPanoHeightPixels>{height}</GPano:FullPanoHeightPixels>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
    return xmp.encode("utf-8")


def insert_xmp_segment(jpeg_bytes: bytes, xmp_packet: bytes) -> bytes:
    if jpeg_bytes[0:2] != b"\xff\xd8":
        raise ValueError("El archivo no es un JPEG valido (falta el marcador SOI).")

    segment = XMP_APP1_ID + xmp_packet
    app1 = b"\xff\xe1" + struct.pack(">H", len(segment) + 2) + segment

    # Se inserta despues de los segmentos APP0/APP1 ya existentes (JFIF/Exif)
    # para que quede justo despues de la cabecera, como esperan los lectores.
    pos = 2
    while jpeg_bytes[pos:pos + 2] in (b"\xff\xe0", b"\xff\xe1"):
        seg_len = struct.unpack(">H", jpeg_bytes[pos + 2:pos + 4])[0]
        pos += 2 + seg_len

    return jpeg_bytes[:pos] + app1 + jpeg_bytes[pos:]


def procesar_imagen_360(
    input_path: str,
    output_path: str,
    make: str = "RICOH",
    model: str = "RICOH THETA S",
    software: str = "DropMetrics_360_Engine",
    stitching_software: str = "RICOH THETA Stitcher",
    fov: float = 75.0,
    quality: int = 95,
) -> str:
    img = Image.open(input_path)
    if img.mode not in ("RGB",):
        img = img.convert("RGB")
    width, height = img.size

    # Se reconstruye la imagen solo a partir de los pixeles (sin su EXIF/XMP/
    # ICC/chunks originales) antes de inyectar los datos 360. Esto es
    # deliberado: si la foto viene de una IA (Midjourney, Stable Diffusion,
    # etc.) o de otra camara, sus metadatos previos no deben mezclarse con
    # los que estamos por escribir.
    img = Image.frombytes(img.mode, img.size, img.tobytes())

    ratio = width / height
    if abs(ratio - 2.0) > 0.05:
        print(
            f"  [aviso] {Path(input_path).name}: relacion {width}x{height} "
            f"({ratio:.2f}:1) no es 2:1. El visor 360 la va a envolver igual, "
            f"pero se vera deformada tipo 'planeta', no como panoramica real."
        )

    exif_bytes = build_exif_bytes(make, model, software)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, exif=exif_bytes)
    jpeg_bytes = buf.getvalue()

    xmp_packet = build_xmp_packet(width, height, fov, stitching_software)
    final_bytes = insert_xmp_segment(jpeg_bytes, xmp_packet)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(final_bytes)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Inyecta metadatos 360 (EXIF + GPano/XMP) en fotos JPEG.")
    parser.add_argument("input", help="Imagen de entrada, o carpeta de entrada si se usa --batch")
    parser.add_argument("output", help="Imagen de salida, o carpeta de salida si se usa --batch")
    parser.add_argument("--batch", action="store_true", help="Procesa todos los .jpg/.jpeg de la carpeta de entrada")
    parser.add_argument("--fov", type=float, default=75.0, help="Campo de vision horizontal inicial en grados (default: 75)")
    parser.add_argument("--make", default="RICOH", help="Valor EXIF Make")
    parser.add_argument("--model", default="RICOH THETA S", help="Valor EXIF Model")
    parser.add_argument("--quality", type=int, default=95, help="Calidad JPEG de salida (1-100)")
    args = parser.parse_args()

    if args.batch:
        in_dir, out_dir = Path(args.input), Path(args.output)
        files = sorted([*in_dir.glob("*.jpg"), *in_dir.glob("*.jpeg"), *in_dir.glob("*.JPG"), *in_dir.glob("*.JPEG")])
        if not files:
            print(f"No se encontraron .jpg/.jpeg en {in_dir}")
            sys.exit(1)
        for f in files:
            out_path = out_dir / f.name
            procesar_imagen_360(str(f), str(out_path), make=args.make, model=args.model, fov=args.fov, quality=args.quality)
            print(f"OK: {f.name} -> {out_path}")
        print(f"\nListo: {len(files)} imagen(es) procesada(s) en {out_dir}")
    else:
        out = procesar_imagen_360(args.input, args.output, make=args.make, model=args.model, fov=args.fov, quality=args.quality)
        print(f"Listo: {out}")


if __name__ == "__main__":
    main()
