"""
c2pa_inspector.py

Lee y muestra el manifiesto C2PA (Content Credentials) de una imagen, si lo
tiene: con que herramienta se creo o edito, si esta marcada como generada
por IA, y el estado de validacion de la firma.

Herramienta de aprendizaje/inspeccion, AISLADA a proposito del resto del
proyecto: no importa ni modifica inject_360.py, compose_360.py ni
metadata_tools.py.

Requiere una dependencia que no esta en el requirements.txt principal, ver
requirements-c2pa.txt.

Uso:
    python c2pa_inspector.py imagen.jpg
    python c2pa_inspector.py foto1.jpg foto2.png
"""

import argparse
import json

import c2pa

# Valores de "digitalSourceType" (vocabulario IPTC) que declaran contenido
# generado o compuesto por IA dentro de un manifiesto C2PA.
FUENTES_IA = {
    "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia": "Generada por IA (algoritmo entrenado)",
    "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia": "Composicion con contenido de IA",
    "http://cv.iptc.org/newscodes/digitalsourcetype/algorithmicMedia": "Generada algoritmicamente",
}


def inspeccionar_c2pa(path: str) -> dict:
    resultado = {"archivo": path, "tiene_manifiesto": False}

    try:
        with c2pa.Reader(path) as reader:
            data = json.loads(reader.json())
    except c2pa.C2paError.ManifestNotFound:
        return resultado
    except c2pa.C2paError as e:
        resultado["error"] = str(e)
        return resultado

    resultado["tiene_manifiesto"] = True
    activo = data.get("active_manifest")
    m = data.get("manifests", {}).get(activo, {})

    resultado["titulo"] = m.get("title")
    resultado["generador"] = [g.get("name") for g in m.get("claim_generator_info", [])]

    firma = m.get("signature_info", {})
    resultado["firmante"] = firma.get("issuer") or firma.get("common_name")

    marcas_ia = []
    for a in m.get("assertions", []):
        for accion in (a.get("data") or {}).get("actions", []):
            tipo = accion.get("digitalSourceType")
            if tipo:
                marcas_ia.append(FUENTES_IA.get(tipo, tipo))
    resultado["marcado_como_ia"] = marcas_ia

    resultado["validacion"] = [
        f"{e.get('code')}: {e.get('explanation')}" for e in data.get("validation_status", [])
    ]

    return resultado


def _imprimir(r: dict):
    print(f"Archivo: {r['archivo']}")
    if not r["tiene_manifiesto"]:
        if "error" in r:
            print(f"  Error leyendo el manifiesto: {r['error']}")
        else:
            print("  Sin manifiesto C2PA (no tiene Content Credentials).")
        return

    print("  Tiene manifiesto C2PA (Content Credentials).")
    print(f"  Titulo declarado: {r.get('titulo') or '(sin titulo)'}")
    print(f"  Creado/editado con: {', '.join(r.get('generador') or []) or '(no declarado)'}")
    print(f"  Firmado por: {r.get('firmante') or '(desconocido)'}")
    if r.get("marcado_como_ia"):
        print(f"  MARCADO COMO IA: {', '.join(r['marcado_como_ia'])}")
    else:
        print("  No declara origen de IA en las acciones del manifiesto.")
    if r.get("validacion"):
        print("  Estado de la firma:")
        for v in r["validacion"]:
            print(f"    - {v}")


def main():
    parser = argparse.ArgumentParser(description="Lee el manifiesto C2PA (Content Credentials) de una o mas imagenes.")
    parser.add_argument("imagenes", nargs="+")
    args = parser.parse_args()
    for ruta in args.imagenes:
        _imprimir(inspeccionar_c2pa(ruta))
        print()


if __name__ == "__main__":
    main()
