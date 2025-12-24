import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from transbank.webpay.webpay_plus.transaction import Transaction

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# Variables de entorno
COMMERCE_CODE = os.environ.get("COMMERCE_CODE", "597055555532")
API_KEY = os.environ.get("API_KEY", "579B532A744DBA1A0C0D33A7C75A1F08F6B0C0C0D33A7C75A1F08F6B0C0C0D33")
BASE_URL = os.environ.get("BASE_URL", "https://webpay3gint.transbank.cl")

print("=== Variables de entorno cargadas ===")
print("COMMERCE_CODE:", COMMERCE_CODE)
print("API_KEY:", API_KEY)
print("BASE_URL:", BASE_URL)
print("=====================================")

@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json
    amount = data.get("amount", 1000)
    session_id = "sesion123"
    buy_order = "orden123"

    # Usar Transaction directamente
    tx = Transaction(commerce_code=COMMERCE_CODE, api_key=API_KEY, base_url=BASE_URL)

    response = tx.create(
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
    tx = Transaction(commerce_code=COMMERCE_CODE, api_key=API_KEY, base_url=BASE_URL)
    response = tx.commit(token)
    return jsonify(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
