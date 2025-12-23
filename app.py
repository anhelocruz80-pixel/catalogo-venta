import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 🔑 Variables de entorno (se definen en Render → Settings → Environment Variables)
COMMERCE_CODE = os.environ.get("COMMERCE_CODE", "597055555532")  # valor por defecto: integración
API_KEY = os.environ.get("API_KEY", "YourApiKeyHere")
BASE_URL = os.environ.get("BASE_URL", "https://webpay3gint.transbank.cl")  # integración

@app.route("/create-transaction", methods=["POST"])
def create_transaction():
    data = request.json
    amount = data.get("amount", 1000)  # monto en CLP
    session_id = "sesion123"
    buy_order = "orden123"

    payload = {
        "buy_order": buy_order,
        "session_id": session_id,
        "amount": amount,
        "return_url": "https://tu-frontend.github.io/catalogo-venta/commit"  
        # ⚠️ Cambia esta URL al dominio real de tu frontend
    }

    headers = {
        "Tbk-Api-Key-Id": COMMERCE_CODE,
        "Tbk-Api-Key-Secret": API_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.post(
        f"{BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions",
        json=payload,
        headers=headers
    )

    return jsonify(resp.json())

@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws")
    headers = {
        "Tbk-Api-Key-Id": COMMERCE_CODE,
        "Tbk-Api-Key-Secret": API_KEY,
        "Content-Type": "application/json"
    }
    resp = requests.put(
        f"{BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}",
        headers=headers
    )
    return jsonify(resp.json())

if __name__ == "__main__":
    # Render usa gunicorn en producción, pero para pruebas locales puedes usar flask run
    app.run(port=5000, debug=True)
