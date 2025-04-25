
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

OCR_SPACE_API_KEY = "K88111451588957"

@app.route("/ocr", methods=["POST"])
def ocr():
    try:
        data = request.get_json()
        image_base64 = data.get("image_base64")

        if not image_base64:
            return jsonify({"error": "No se recibió imagen en base64"}), 400

        payload = {
            'base64Image': f'data:image/jpeg;base64,{image_base64}',
            'language': 'spa',
            'isOverlayRequired': False,
            'apikey': OCR_SPACE_API_KEY
        }

        response = requests.post('https://api.ocr.space/parse/image', data=payload)
        result = response.json()
        parsed_text = result.get("ParsedResults", [{}])[0].get("ParsedText", "")

        return jsonify({"text": parsed_text})
    
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error en la llamada a OCR.space: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def root():
    return "Servicio OCR activo con OCR.space. Usá POST /ocr para enviar imágenes."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
