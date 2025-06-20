import os
import json
import base64
import hashlib
import io
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import redis
from PIL import Image, ImageFilter

app = Flask(__name__)
CORS(app)

# --- Configuración de entorno ---
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")
REDIS_URL         = os.getenv("REDIS_URL")
MAX_IMAGE_BYTES   = 5 * 1024 * 1024   # 5 MB

# --- Cliente Redis para caché ---
cache = None
if REDIS_URL:
    cache = redis.from_url(REDIS_URL, decode_responses=True)

def preprocess_image(base64_str: str) -> str:
    """Convierte base64 a imagen, la binariza y devuelve nuevo base64."""
    raw = base64.b64decode(base64_str)
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Imagen demasiado grande")
    img = Image.open(io.BytesIO(raw)).convert("L")  # escala de grises
    img = img.filter(ImageFilter.MedianFilter(3))
    # umbral adaptativo simple
    img = img.point(lambda p: 0 if p < 128 else 255)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()

def ocr_space_request(base64_img: str, language: str) -> str:
    """Llama a OCR.space con hasta 2 reintentos."""
    payload = {
        'base64Image': f'data:image/jpeg;base64,{base64_img}',
        'language': language or 'spa',
        'isOverlayRequired': False,
        'apikey': OCR_SPACE_API_KEY
    }
    for attempt in range(2):
        resp = requests.post('https://api.ocr.space/parse/image', data=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("ParsedResults", [{}])[0].get("ParsedText", "")
        time.sleep(1)
    resp.raise_for_status()

@app.route("/ocr", methods=["POST"])
def ocr():
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image_base64")
        language  = data.get("language", "spa")
        if not image_b64:
            return jsonify({"error": "Falta campo image_base64"}), 400

        # clave para caching
        key = hashlib.sha256(image_b64.encode()).hexdigest()
        if cache:
            cached = cache.get(key)
            if cached:
                return jsonify({"text": cached, "cached": True})

        # preprocesar
        try:
            image_b64 = preprocess_image(image_b64)
        except ValueError as e:
            return jsonify({"error": str(e)}), 413

        # llamada a OCR.space
        text = ocr_space_request(image_b64, language).strip()

        # limpieza básica
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        result_text = "\n".join(lines)

        # guardar en caché 24h
        if cache:
            cache.setex(key, 24*3600, result_text)

        return jsonify({"text": result_text})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error de red con OCR.space: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"Error interno OCR: {e}"}), 500

@app.route("/", methods=["GET"])
def root():
    return "Servicio OCR activo. Usa POST /ocr con JSON {image_base64, language?}."

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
