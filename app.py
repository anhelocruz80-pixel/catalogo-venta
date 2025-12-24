import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# Importaciones del SDK de Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# Configuración de credenciales (usa tus variables de entorno en Render)
COMMERCE_CODE = "597055555532"   # Código de integración Webpay Plus
API_KEY = "579B532A744DBBD2F1F2A0F96F5F6A6C"  # API Key de integración

# Configurar Transaction globalmente
Transaction.configure_for_options(
    WebpayOptions(
        commerce_code=COMMERCE_CODE,
        api_key=API_KEY,
        integration_type=IntegrationType.TEST  # Cambia a LIVE en producción
    )
)

@app.route("/")
def home():
    return "Backend funcionando correctamente 🚀"

@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json
    amount = data.get("amount", 1000)
    session_id = "sesion123"
    buy_order = "orden123"

    response = Transaction.create(
        buy_order=buy_order,
        session_id=session_id,
        amount=amount,
        return_url="https://anhelocruz80-pixel.github.io/catalogo-venta/commit"
    )

    return jsonify({
        "token": response["token"],
        "url": response["url"]
    })

@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws")
    response = Transaction.commit(token)
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
