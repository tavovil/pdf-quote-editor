from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import shutil
import os
import io
import re
import json
import uuid
import base64

CARPETA_SUBIDAS = "subidos"
CARPETA_PLANTILLAS = "plantillas"

# Las carpetas se crean ANTES de montarlas, para que el proyecto
# arranque bien aunque se descargue desde GitHub sin ellas.
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
os.makedirs(CARPETA_PLANTILLAS, exist_ok=True)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/subidos", StaticFiles(directory=CARPETA_SUBIDAS), name="subidos")


def nombre_seguro(nombre: str) -> str:
    """Deja solo el nombre del archivo (sin rutas) y caracteres seguros."""
    nombre = os.path.basename(nombre.replace("\\", "/"))
    nombre = re.sub(r"[^\w.\-]", "_", nombre)
    return nombre or "archivo"


class CampoPDF(BaseModel):
    pagina: int
    x: float
    y: float
    texto: str
    tamano: float = 7


class ImagenPDF(BaseModel):
    pagina: int
    x: float
    y: float
    ancho: float
    alto: float
    data_url: str


class DatosGuardado(BaseModel):
    nombre_archivo: str
    escala: float
    campos: list[CampoPDF]
    imagenes: list[ImagenPDF] = []


class CampoPlantilla(BaseModel):
    pagina: int
    x: float
    y: float


class DatosPlantilla(BaseModel):
    nombre: str
    escala: float
    campos: list[CampoPlantilla]


@app.get("/", response_class=HTMLResponse)
def inicio():
    with open("static/index.html", "r", encoding="utf-8") as archivo:
        return archivo.read()


@app.post("/subir-pdf")
def subir_pdf(archivo: UploadFile = File(...)):
    limpio = nombre_seguro(archivo.filename or "documento.pdf")

    if not limpio.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    # Prefijo único: dos archivos con el mismo nombre ya no se sobrescriben.
    nombre_guardado = uuid.uuid4().hex[:8] + "_" + limpio
    ruta_destino = os.path.join(CARPETA_SUBIDAS, nombre_guardado)

    with open(ruta_destino, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)

    return {"nombre_guardado": nombre_guardado}


@app.post("/guardar-pdf")
def guardar_pdf(datos: DatosGuardado):
    nombre_archivo = nombre_seguro(datos.nombre_archivo)
    ruta_original = os.path.join(CARPETA_SUBIDAS, nombre_archivo)

    if not os.path.isfile(ruta_original):
        raise HTTPException(status_code=404, detail="PDF no encontrado")

    lector = PdfReader(ruta_original)
    escritor = PdfWriter()

    campos_por_pagina = {}
    for campo in datos.campos:
        campos_por_pagina.setdefault(campo.pagina, []).append(campo)

    imagenes_por_pagina = {}
    for imagen in datos.imagenes:
        imagenes_por_pagina.setdefault(imagen.pagina, []).append(imagen)

    for numero_pagina in range(len(lector.pages)):
        pagina_original = lector.pages[numero_pagina]

        pagina_original.transfer_rotation_to_content()

        ancho = float(pagina_original.mediabox.width)
        alto = float(pagina_original.mediabox.height)
        origen_x = float(pagina_original.mediabox.left)
        origen_y = float(pagina_original.mediabox.bottom)

        numero_pagina_humano = numero_pagina + 1

        campos_de_esta_pagina = campos_por_pagina.get(numero_pagina_humano, [])
        imagenes_de_esta_pagina = imagenes_por_pagina.get(numero_pagina_humano, [])

        if campos_de_esta_pagina or imagenes_de_esta_pagina:
            buffer = io.BytesIO()
            lienzo = canvas.Canvas(buffer, pagesize=(ancho, alto))

            for campo in campos_de_esta_pagina:
                x_real = ((campo.x + 3) / datos.escala) + origen_x
                y_real_pantalla = (campo.y + 3) / datos.escala
                y_pdf = (alto - y_real_pantalla - campo.tamano * 0.85) + origen_y

                lienzo.setFont("Helvetica", campo.tamano)
                lienzo.drawString(x_real, y_pdf, campo.texto)

            for imagen in imagenes_de_esta_pagina:
                _, datos_base64 = imagen.data_url.split(",", 1)
                bytes_imagen = base64.b64decode(datos_base64)
                lector_imagen = ImageReader(io.BytesIO(bytes_imagen))

                x_real = (imagen.x / datos.escala) + origen_x
                y_real_pantalla = imagen.y / datos.escala
                ancho_real = imagen.ancho / datos.escala
                alto_real = imagen.alto / datos.escala
                y_pdf = (alto - y_real_pantalla - alto_real) + origen_y

                lienzo.drawImage(
                    lector_imagen,
                    x_real,
                    y_pdf,
                    width=ancho_real,
                    height=alto_real,
                    mask="auto",
                )

            lienzo.save()
            buffer.seek(0)

            pdf_overlay = PdfReader(buffer)
            pagina_original.merge_page(pdf_overlay.pages[0])

        escritor.add_page(pagina_original)

    ruta_salida = os.path.join(CARPETA_SUBIDAS, "resultado_" + nombre_archivo)
    with open(ruta_salida, "wb") as f:
        escritor.write(f)

    return FileResponse(
        ruta_salida,
        media_type="application/pdf",
        filename="cotizacion_completada.pdf",
    )


@app.post("/guardar-plantilla")
def guardar_plantilla(datos: DatosPlantilla):
    base = re.sub(r"[^\w\-]", "_", datos.nombre.strip()) or "plantilla"
    nombre_archivo = base + ".json"
    ruta = os.path.join(CARPETA_PLANTILLAS, nombre_archivo)

    contenido = {
        "nombre": datos.nombre,
        "escala": datos.escala,
        "campos": [campo.model_dump() for campo in datos.campos],
    }

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)

    return {"mensaje": "Plantilla guardada", "archivo": nombre_archivo}


@app.get("/listar-plantillas")
def listar_plantillas():
    nombres = []

    for archivo in os.listdir(CARPETA_PLANTILLAS):
        if archivo.endswith(".json"):
            ruta = os.path.join(CARPETA_PLANTILLAS, archivo)
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                nombres.append({"archivo": archivo, "nombre": contenido["nombre"]})

    return nombres


@app.get("/cargar-plantilla/{nombre_archivo}")
def cargar_plantilla(nombre_archivo: str):
    ruta = os.path.join(CARPETA_PLANTILLAS, nombre_seguro(nombre_archivo))

    if not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)
