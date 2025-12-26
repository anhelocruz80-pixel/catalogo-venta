import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

# Transbank SDK
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# Webpay options (TEST)
options = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST  # Cambiar a LIVE en producción
)
tx = Transaction(options)

# Simulación de catálogo con stock (en memoria)
productos = {
    1: {"id": 1, "nombre": "Notebook Usado", "precio": 120000, "categoria": "electronica", "stock": 1},
    2: {"id": 2, "nombre": "Zapatos de Cuero", "precio": 25000, "categoria": "vestuario", "stock": 3},
    3: {"id": 3, "nombre": "Mesa de Madera", "precio": 50000, "categoria": "hogar", "stock": 2},
    4: {"id": 4, "nombre": "Reloj de Pared", "precio": 10000, "categoria": "accesorios", "stock": 2},
    5: {"id": 5, "nombre": "Silla de Madera", "precio": 20000, "categoria": "hogar", "stock": 4},
    6: {"id": 6, "nombre": "Celular Usado", "precio": 80000, "categoria": "electronica", "stock": 1},
    7: {"id": 7, "nombre": "Chaqueta Invierno", "precio": 30000, "categoria": "vestuario", "stock": 3},
    8: {"id": 8, "nombre": "Lámpara Escritorio", "precio": 15000, "categoria": "hogar", "stock": 2},
    9: {"id": 9, "nombre": "Audífonos Bluetooth", "precio": 35000, "categoria": "electronica", "stock": 2},
    10: {"id": 10, "nombre": "Bolso Deportivo", "precio": 18000, "categoria": "accesorios", "stock": 5},
}

# Guardar transacciones con sus items
transacciones = {}

@app.route("/")
def home():
    return "Backend funcionando correctamente 🚀"

@app.route("/productos", methods=["GET"])
def listar_productos():
    return jsonify(list(productos.values()))

@app.route("/agregar-carrito", methods=["POST"])
def agregar_carrito():
    data = request.json
    producto_id = int(data.get("id"))
    cantidad = int(data.get("cantidad", 1))

    if producto_id not in productos:
        return jsonify({"error": "Producto no existe"}), 404

    if productos[producto_id]["stock"] < cantidad:
        return jsonify({"error": "Stock insuficiente", "stock": productos[producto_id]["stock"]}), 400

    productos[producto_id]["stock"] -= cantidad
    return jsonify({"message": "Agregado", "producto": productos[producto_id]})

@app.route("/devolver-carrito", methods=["POST"])
def devolver_carrito():
    data = request.json  # items: [{id, cantidad}]
    items = data.get("items", [])
    for it in items:
        pid = int(it.get("id"))
        qty = int(it.get("cantidad", 0))
        if pid in productos:
            productos[pid]["stock"] += qty
    return jsonify({"message": "Stock devuelto"})

@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json or {}
    amount = int(data.get("amount", 1000))
    items = data.get("items", [])

    # Si vienen items, recomputar el total y validar stock
    if items:
        total_calc = 0
        for it in items:
            pid = int(it.get("id"))
            qty = int(it.get("cantidad", 1))
            prod = productos.get(pid)
            if not prod:
                return jsonify({"error": f"Producto {pid} no existe"}), 400
            if prod["stock"] < qty:
                return jsonify({"error": "Stock insuficiente", "producto": prod["nombre"], "stock": prod["stock"]}), 400
            total_calc += prod["precio"] * qty
        amount = total_calc

    session_id = f"sesion-{uuid.uuid4().hex[:8]}"
    buy_order = f"orden-{uuid.uuid4().hex[:12]}"

    response = tx.create(
        buy_order=buy_order,
        session_id=session_id,
        amount=amount,
        return_url="https://anhelocruz80-pixel.github.io/catalogo-venta/commit"
    )

    # Guardamos los items asociados a esta transacción
    transacciones[buy_order] = {"items": items}

    return jsonify({
        "token": response["token"],
        "url": response["url"]
    })

@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws") or request.form.get("token_ws")
    if not token:
        return jsonify({"status": "ERROR", "message": "Falta token_ws"}), 400

    response = tx.commit(token)
    buy_order = response.get("buy_order")
    status = response.get("status")

    # Si el pago falla, devolver stock
    if status not in ["AUTHORIZED", "SUCCESS"]:
        if buy_order in transacciones:
            items = transacciones[buy_order]["items"]
            for it in items:
                pid = int(it.get("id"))
                qty = int(it.get("cantidad", 0))
                if pid in productos:
                    productos[pid]["stock"] += qty
            del transacciones[buy_order]

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
