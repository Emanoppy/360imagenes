"""
app.py

Interfaz web local para inject_360.py: arrastras una o varias fotos,
el servidor les inyecta EXIF (RICOH THETA S) + XMP GPano equirectangular,
y te devuelve un .zip con los resultados listos para subir a Facebook.

Uso:
    python app.py
    -> abre http://127.0.0.1:5000 en el navegador
"""

import io
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, send_file

from inject_360 import procesar_imagen_360

app = Flask(__name__)

WORKDIR = Path(__file__).parent / "_tmp_web"
WORKDIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/procesar", methods=["POST"])
def procesar():
    files = request.files.getlist("fotos")
    fov = request.form.get("fov", "75")
    try:
        fov = float(fov)
    except ValueError:
        fov = 75.0

    if not files:
        return {"error": "No se recibio ninguna foto."}, 400

    resultados = []
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            nombre = f.filename or "foto.jpg"
            ext = Path(nombre).suffix.lower()
            if ext not in ALLOWED_EXT:
                resultados.append({"nombre": nombre, "ok": False, "detalle": "Formato no soportado (usa .jpg)"})
                continue

            in_path = WORKDIR / f"in_{nombre}"
            out_path = WORKDIR / f"360_{Path(nombre).stem}.jpg"
            f.save(in_path)

            try:
                procesar_imagen_360(str(in_path), str(out_path), fov=fov)
                zf.write(out_path, arcname=f"360_{Path(nombre).stem}.jpg")
                resultados.append({"nombre": nombre, "ok": True})
            except Exception as e:
                resultados.append({"nombre": nombre, "ok": False, "detalle": str(e)})
            finally:
                in_path.unlink(missing_ok=True)
                out_path.unlink(missing_ok=True)

    if not any(r["ok"] for r in resultados):
        return {"error": "Ninguna foto se pudo procesar.", "detalle": resultados}, 400

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="fotos_360.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
