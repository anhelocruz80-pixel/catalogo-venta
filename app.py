import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType

# -----------------------------------------------------------------------------
# Configuración Flask
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# -----------------------------------------------------------------------------
# PostgreSQL (Railway)
# -----------------------------------------------------------------------------
db_url = (
    f"postgresql+psycopg://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
    f"@{os.environ['PGHOST']}:{os.environ.get('PGPORT','5432')}/{os.environ['PGDATABASE']}"
)
engine = create_engine(db_url, poolclass=NullPool, future=True)

# -----------------------------------------------------------------------------
# Webpay TEST
# -----------------------------------------------------------------------------
tx = Transaction(WebpayOptions(
    IntegrationCommerceCodes.WEBPAY_PLUS,
    IntegrationApiKeys.WEBPAY,
    IntegrationType.TEST
))

# -----------------------------------------------------------------------------
# Productos
# -----------------------------------------------------------------------------
@app.route("/productos")
def productos():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, nombre, descripcion, categoria, precio, stock
            FROM productos WHERE activo = true
            ORDER BY id
        """)).mappings().all()
    return jsonify([dict(r) for r in rows])

# -----------------------------------------------------------------------------
# Carrito (reserva stock)
# -----------------------------------------------------------------------------
@app.route("/agregar-carrito", methods=["POST"])
def agregar_carrito():
    data = request.json
    pid = int(data["id"])
    qty = int(data.get("cantidad", 1))

    with engine.begin() as conn:
        prod = conn.execute(
            text("SELECT stock FROM productos WHERE id=:id AND activo=true"),
            {"id": pid}
        ).first()

        if not prod or prod.stock < qty:
            return jsonify({"error": "Stock insuficiente"}), 400

        conn.execute(
            text("UPDATE productos SET stock = stock - :q WHERE id=:id"),
            {"q": qty, "id": pid}
        )

        conn.execute(text("""
            INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
            VALUES (:pid, :chg, 'reserva', 'pendiente')
        """), {"pid": pid, "chg": -qty})

    return jsonify({"ok": True})

# -----------------------------------------------------------------------------
# Devolver stock
# -----------------------------------------------------------------------------
@app.route("/devolver-carrito", methods=["POST"])
def devolver_carrito():
    items = request.json.get("items", [])
    with engine.begin() as conn:
        for it in items:
            conn.execute(
                text("UPDATE productos SET stock = stock + :q WHERE id=:id"),
                {"q": it["cantidad"], "id": it["id"]}
            )
    return jsonify({"ok": True})

# -----------------------------------------------------------------------------
# Crear transacción
# -----------------------------------------------------------------------------
@app.route("/create-transaction", methods=["POST"])
def create_transaction():
    items = request.json["items"]

    total = 0
    with engine.begin() as conn:
        for it in items:
            precio = conn.execute(
                text("SELECT precio FROM productos WHERE id=:id"),
                {"id": it["id"]}
            ).scalar_one()
            total += precio * it["cantidad"]

    buy_order = f"orden-{uuid.uuid4().hex[:12]}"
    session_id = uuid.uuid4().hex[:8]
    return_url = "https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"

    resp = tx.create(buy_order, session_id, total, return_url)

    with engine.begin() as conn:
        # 1️⃣ guardar transacción
        conn.execute(text("""
            INSERT INTO transacciones (buy_order, tb_token, tb_status, monto_total)
            VALUES (:bo, :tok, 'PENDING', :m)
        """), {"bo": buy_order, "tok": resp["token"], "m": total})

        # 🔗 2️⃣ ASOCIAR RESERVAS "pendiente" A ESTA ORDEN
        conn.execute(text("""
            UPDATE audit_stock
            SET referencia = :bo
            WHERE referencia = 'pendiente'
              AND motivo = 'reserva'
        """), {"bo": buy_order})

        # 3️⃣ guardar items
        for it in items:
            conn.execute(text("""
                INSERT INTO transaccion_items (buy_order, producto_id, cantidad, precio_unitario)
                VALUES (:bo, :pid, :q,
                        (SELECT precio FROM productos WHERE id=:pid))
            """), {"bo": buy_order, "pid": it["id"], "q": it["cantidad"]})

    return jsonify(resp)

# -----------------------------------------------------------------------------
# Commit Webpay (REDIRECCIÓN)
# -----------------------------------------------------------------------------
@app.route("/commit", methods=["POST", "GET"])
def commit():
    token = request.values.get("token_ws")
    if not token:
        return "Token faltante", 400

    try:
        resp = tx.commit(token)
    except Exception as e:
        print("Error Webpay commit:", e)
        return "Error confirmando pago", 500

    buy_order = resp.get("buy_order")
    status = resp.get("status")

    with engine.begin() as conn:
        # actualizar estado
        conn.execute(text("""
            UPDATE transacciones
            SET tb_status = :st, updated_at = NOW()
            WHERE buy_order = :bo
        """), {"st": status, "bo": buy_order})

        if status == "AUTHORIZED":
            # pago exitoso
            conn.execute(text("""
                INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                SELECT producto_id, 0, 'pago', :ref
                FROM transaccion_items
                WHERE buy_order = :bo
            """), {"bo": buy_order, "ref": buy_order})

        else:
        # 🔥 DEVOLVER STOCK SOLO SI HUBO RESERVA
        reservas = conn.execute(text("""
            SELECT producto_id, SUM(-cambio) AS cantidad
            FROM audit_stock
            WHERE referencia = :ref
              AND motivo = 'reserva'
            GROUP BY producto_id
        """), {"ref": buy_order}).all()

        for pid, qty in reservas:
            conn.execute(text("""
                UPDATE productos
                SET stock = stock + :q
                WHERE id = :pid
            """), {"q": qty, "pid": pid})

            conn.execute(text("""
                INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                VALUES (:pid, :chg, 'reversa', :ref)
            """), {
                "pid": pid,
                "chg": qty,
                "ref": buy_order
              })

    # 👉 REDIRECCIÓN FINAL (SIEMPRE)
    return redirect(
        f"https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"
        f"?status={status}&order={buy_order}"
    )
    
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
