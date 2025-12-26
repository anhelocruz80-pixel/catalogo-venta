import os
import uuid
from datetime import datetime, timedelta
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

# Reservas de stock
# - reservas_click: reservas creadas al agregar al carrito (sin buy_order aún)
# - reservas_tx: reservas asociadas a una transacción (buy_order) en curso
reservas_click = []  # [{id, cantidad, expira: datetime}]
reservas_tx = {}     # {buy_order: {"items": [{id, cantidad}], "expira": datetime}}

# Transacciones registradas (para commit y devoluciones por fallo)
transacciones = {}

# Utilidad: liberar reservas vencidas (click y transacción)
def liberar_reservas_vencidas():
    ahora = datetime.now()

    # Liberar reservas de clic vencidas
    i = 0
    while i < len(reservas_click):
        r = reservas_click[i]
        if r["expira"] < ahora:
            pid = int(r["id"])
            qty = int(r["cantidad"])
            if pid in productos:
                productos[pid]["stock"] += qty
            reservas_click.pop(i)
        else:
            i += 1

    # Liberar reservas de transacción vencidas (caso: nunca se llamó a commit)
    expiradas = [bo for bo, r in reservas_tx.items() if r["expira"] < ahora]
    for bo in expiradas:
        items = reservas_tx[bo]["items"]
        for it in items:
            pid = int(it["id"])
            qty = int(it["cantidad"])
            if pid in productos:
                productos[pid]["stock"] += qty
        del reservas_tx[bo]

@app.route("/")
def home():
    return "Backend funcionando correctamente 🚀"

@app.route("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat()})

# Catálogo: libera reservas vencidas antes de responder
@app.route("/productos", methods=["GET"])
def listar_productos():
    liberar_reservas_vencidas()
    return jsonify(list(productos.values()))

# Decrementa stock y crea reserva temporal al agregar al carrito
@app.route("/agregar-carrito", methods=["POST"])
def agregar_carrito():
    liberar_reservas_vencidas()

    data = request.json
    producto_id = int(data.get("id"))
    cantidad = int(data.get("cantidad", 1))

    if producto_id not in productos:
        return jsonify({"error": "Producto no existe"}), 404

    if productos[producto_id]["stock"] < cantidad:
        return jsonify({"error": "Stock insuficiente", "stock": productos[producto_id]["stock"]}), 400

    # Descuento y reserva con expiración
    productos[producto_id]["stock"] -= cantidad
    reservas_click.append({
        "id": producto_id,
        "cantidad": cantidad,
        "expira": datetime.now() + timedelta(minutes=10)
    })

    return jsonify({"message": "Agregado", "producto": productos[producto_id]})

# Devuelve stock al cancelar/vaciar (y elimina reservas de clic correspondientes)
@app.route("/devolver-carrito", methods=["POST"])
def devolver_carrito():
    liberar_reservas_vencidas()

    data = request.json  # items: [{id, cantidad}]
    items = data.get("items", [])

    # Sumar stock
    for it in items:
        pid = int(it.get("id"))
        qty = int(it.get("cantidad", 0))
        if pid in productos:
            productos[pid]["stock"] += qty

    # Consumir reservas_click equivalentes para evitar doble liberación posterior
    for it in items:
        pid = int(it.get("id"))
        qty = int(it.get("cantidad", 0))
        j = 0
        while j < len(reservas_click) and qty > 0:
            r = reservas_click[j]
            if int(r["id"]) == pid:
                if r["cantidad"] <= qty:
                    qty -= r["cantidad"]
                    reservas_click.pop(j)
                else:
                    r["cantidad"] -= qty
                    qty = 0
                    j += 1
            else:
                j += 1

    return jsonify({"message": "Stock devuelto"})

# Crear transacción: valida stock, consolida reservas y asocia buy_order con expiración
@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    liberar_reservas_vencidas()

    data = request.json or {}
    items = data.get("items", [])
    amount = 0

    # Validar stock disponible (puede estar parcialmente reservado vía agregar-carrito)
    for it in items:
        pid = int(it["id"])
        qty = int(it["cantidad"])
        prod = productos.get(pid)
        if not prod:
            return jsonify({"error": f"Producto {pid} no existe"}), 400
        if prod["stock"] < qty:
            return jsonify({
                "error": "Stock insuficiente",
                "producto": prod["nombre"],
                "stock": prod["stock"]
            }), 400
        amount += prod["precio"] * qty

    # Evitar doble descuento:
    # - Consumimos reservas_click equivalentes primero
    # - Si queda remanente, recién entonces restamos del stock
    for it in items:
        pid = int(it["id"])
        qty = int(it["cantidad"])

        # Consumir reservas_click del mismo producto
        j = 0
        rem = qty
        while j < len(reservas_click) and rem > 0:
            r = reservas_click[j]
            if int(r["id"]) == pid:
                if r["cantidad"] <= rem:
                    rem -= r["cantidad"]
                    reservas_click.pop(j)
                else:
                    r["cantidad"] -= rem
                    rem = 0
                    j += 1
            else:
                j += 1

        # Si aún queda remanente, descuéntalo del stock (flujo directo sin agregar-carrito)
        if rem > 0:
            if productos[pid]["stock"] < rem:
                return jsonify({
                    "error": "Stock insuficiente al consolidar",
                    "producto": productos[pid]["nombre"],
                    "stock": productos[pid]["stock"]
                }), 400
            productos[pid]["stock"] -= rem

    session_id = f"sesion-{uuid.uuid4().hex[:8]}"
    buy_order = f"orden-{uuid.uuid4().hex[:12]}"
    return_url = "https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"

    # Reserva asociada a la transacción con expiración
    reservas_tx[buy_order] = {"items": items, "expira": datetime.now() + timedelta(minutes=10)}
    transacciones[buy_order] = {"items": items}

    response = tx.create(
        buy_order=buy_order,
        session_id=session_id,
        amount=amount,
        return_url=return_url
    )

    return jsonify({
        "token": response["token"],
        "url": response["url"]
    })

# Confirmar transacción y manejar reservas/stock según resultado
@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    liberar_reservas_vencidas()

    token = request.args.get("token_ws") or request.form.get("token_ws")
    if not token:
        return jsonify({"status": "ERROR", "message": "Falta token_ws"}), 400

    response = tx.commit(token)
    buy_order = response.get("buy_order")
    status = response.get("status")

    # Pago exitoso: eliminar reserva asociada (stock ya está descontado)
    if status in ["AUTHORIZED", "SUCCESS"]:
        reservas_tx.pop(buy_order, None)
        transacciones.pop(buy_order, None)

    # Pago fallido o no autorizado: devolver stock y eliminar reservas
    else:
        items = []
        if buy_order in reservas_tx:
            items = reservas_tx[buy_order]["items"]
        elif buy_order in transacciones:
            items = transacciones[buy_order]["items"]

        for it in items:
            pid = int(it["id"])
            qty = int(it["cantidad"])
            if pid in productos:
                productos[pid]["stock"] += qty

        reservas_tx.pop(buy_order, None)
        transacciones.pop(buy_order, None)

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
