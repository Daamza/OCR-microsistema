
from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import io
import base64

app = Flask(__name__)
CORS(app)

@app.route("/ocr", methods=["POST"])
def ocr():
    try:
        data = request.get_json()
        image_base64 = data.get("image_base64")

        if not image_base64:
            return jsonify({"error": "No se recibió imagen en base64"}), 400

        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)

        return jsonify({"text": text})
    
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error procesando la imagen: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def root():
    return "Servicio OCR activo. Usá POST /ocr para enviar imágenes."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
