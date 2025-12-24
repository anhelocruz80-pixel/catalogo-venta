import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# Importaciones del SDK de Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

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

    # Usar directamente los helpers de integración
    response = Transaction.create(
        buy_order=buy_order,
        session_id=session_id,
        amount=amount,
        return_url="https://anhelocruz80-pixel.github.io/catalogo-venta/commit",
        commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
        api_key=IntegrationApiKeys.WEBPAY
    )

    return jsonify({
        "token": response["token"],
        "url": response["url"]
    })

@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws")

    response = Transaction.commit(
        token,
        commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
        api_key=IntegrationApiKeys.WEBPAY
    )

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
