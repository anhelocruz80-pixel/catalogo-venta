import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)

# 👇 habilita CORS para tu dominio de GitHub Pages
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# 🔑 Variables de entorno en Render
COMMERCE_CODE = os.environ.get("COMMERCE_CODE", "597055555532")
API_KEY = os.environ.get("API_KEY", "YourApiKeyHere")
BASE_URL = os.environ.get("BASE_URL", "https://webpay3gint.transbank.cl")

@app.route("/")
def home():
    return "Backend Flask funcionando en Render 🚀"

@app.route("/create-transaction", methods=["POST"])
def create_transaction():
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
    app.run(port=5000, debug=True)
