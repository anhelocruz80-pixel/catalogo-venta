import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)

# 👇 habilita CORS solo para tu frontend en GitHub Pages
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# 🔑 Variables de entorno en Render
COMMERCE_CODE = os.environ.get("COMMERCE_CODE", "597055555532")  # código integración
API_KEY = os.environ.get("API_KEY", "579B532A744DBA1A0C0D33A7C75A1F08F6B0C0C0D33A7C75A1F08F6B0C0C0D33") # clave dummy
BASE_URL = os.environ.get("BASE_URL", "https://webpay3gint.transbank.cl")

# 👇 imprime las variables al iniciar el backend
print("=== Variables de entorno cargadas ===")
print("COMMERCE_CODE:", COMMERCE_CODE)
print("API_KEY:", API_KEY)
print("BASE_URL:", BASE_URL)
print("=====================================")

@app.route("/")
def home():
    return "Backend Flask funcionando en Render 🚀"

@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        # Respuesta al preflight de CORS
        return jsonify({"status": "ok"}), 200

    data = request.json
    amount = data.get("amount", 1000)
    session_id = "sesion123"
    buy_order = "orden123"

    payload = {
        "buy_order": buy_order,
        "session_id": session_id,
        "amount": amount,
        "return_url": "https://anhelocruz80-pixel.github.io/catalogo-venta/commit"
    }

    headers = {
        "Tbk-Api-Key-Id": str(COMMERCE_CODE),   # 👈 convertir a string
        "Tbk-Api-Key-Secret": str(API_KEY),     # 👈 convertir a string
        "Content-Type": "application/json"
    }
    
    print("=== Headers enviados a Transbank ===") 
    print(headers) 
    print("=== Payload enviado ===") 
    print(payload)

    resp = requests.post(
        f"{BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions",
        json=payload,
        headers=headers
    )

    return jsonify(resp.json()), resp.status_code

@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws")
    headers = {
        "Tbk-Api-Key-Id": str(COMMERCE_CODE),   # 👈 convertir a string
        "Tbk-Api-Key-Secret": str(API_KEY),     # 👈 convertir a string
        "Content-Type": "application/json"
    }
    resp = requests.put(
        f"{BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}",
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

if __name__ == "__main__":
    # 👇 Render asigna el puerto dinámicamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
