import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType
from flask import session

# -----------------------------------------------------------------------------
# Configuración Flask
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# -----------------------------------------------------------------------------
# session_id
# -----------------------------------------------------------------------------

@app.before_request
def ensure_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

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
            INSERT INTO audit_stock (producto_id, cambio, motivo, referencia, session_id)
            VALUES (:pid, :chg, 'reserva', 'pendiente', :sid)
        """), {"pid": pid, "chg": -qty, "sid": session["session_id"]})

    return jsonify({"ok": True})
        
# -----------------------------------------------------------------------------
# Liberar Reservas Vencidas (CORRECTO)
# -----------------------------------------------------------------------------  

from datetime import datetime, timedelta

@app.route("/liberar-reservas-vencidas", methods=["POST"])
def liberar_reservas_vencidas():
    LIMITE_MINUTOS = 10
    limite = datetime.utcnow() - timedelta(minutes=LIMITE_MINUTOS)

    with engine.begin() as conn:
        # 1️⃣ Buscar reservas vencidas NO procesadas
        reservas = conn.execute(text("""
            SELECT producto_id, referencia, SUM(-cambio) AS cantidad
            FROM audit_stock
            WHERE motivo = 'reserva'
              AND referencia = 'pendiente'
              AND created_at < :limite
            GROUP BY producto_id, referencia
        """), {"limite": limite}).all()

        for pid, ref, qty in reservas:
            # 2️⃣ devolver stock
            conn.execute(text("""
                UPDATE productos
                SET stock = stock + :q
                WHERE id = :pid
            """), {"q": qty, "pid": pid})

            # 3️⃣ auditar timeout
            conn.execute(text("""
                INSERT INTO audit_stock
                    (producto_id, cambio, motivo, referencia, actor)
                VALUES
                    (:pid, :chg, 'timeout', 'timeout', 'cron')
            """), {"pid": pid, "chg": qty})

            # 4️⃣ CERRAR reserva para que NO vuelva a procesarse
            conn.execute(text("""
                UPDATE audit_stock
                SET referencia = 'cerrada'
                WHERE motivo = 'reserva'
                  AND referencia = 'pendiente'
                  AND producto_id = :pid
            """), {"pid": pid})

    return {"status": "ok", "liberadas": len(reservas)}

# -----------------------------------------------------------------------------
# Devolver stock
# -----------------------------------------------------------------------------

@app.route("/devolver-carrito", methods=["POST"])
def devolver_carrito():
    items = request.json.get("items", [])

    with engine.begin() as conn:
        for it in items:
            pid = it["id"]
            qty = it["cantidad"]

            # 1️⃣ devolver stock
            conn.execute(text("""
                UPDATE productos
                SET stock = stock + :q
                WHERE id = :pid
            """), {"q": qty, "pid": pid})

            # 2️⃣ cerrar reservas pendientes
            conn.execute(text("""
                UPDATE audit_stock
                SET motivo = 'liberada',
                    referencia = 'liberada'
                WHERE producto_id = :pid
                  AND motivo = 'reserva'
                  AND referencia = 'pendiente'
                  AND session_id = :sid
            """), {"pid": pid, "sid": session["session_id"]
})

            # 3️⃣ registrar evento explícito
            conn.execute(text("""
                INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                VALUES (:pid, :chg, 'liberacion', 'carrito')
            """), {"pid": pid, "chg": qty})

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
    return_url = "https://catalogo-venta.onrender.com/commit"

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

@app.route("/commit", methods=["GET", "POST"])
def commit():
    token = request.values.get("token_ws")

    # 🔹 Usuario canceló o volvió sin token
    # ❗ NO se toca stock aquí
    if not token:
        return redirect(
            "https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"
            "?status=ABORTED"
        )

    # 1️⃣ Confirmar con Webpay
    try:
        resp = tx.commit(token)
    except Exception as e:
        print("ERROR COMMIT WEBPAY:", e)
        return "Error confirmando pago", 500

    buy_order = resp["buy_order"]
    status = resp["status"]

    with engine.begin() as conn:
        # 2️⃣ Actualizar transacción
        conn.execute(
            text("""
                UPDATE transacciones
                SET tb_status = :st
                WHERE buy_order = :bo
            """),
            {"st": status, "bo": buy_order}
        )

        # 3️⃣ Si NO fue autorizado → devolver stock SOLO de esta orden
        if status != "AUTHORIZED":
            reservas = conn.execute(
                text("""
                    SELECT producto_id, SUM(-cambio) AS cantidad
                    FROM audit_stock
                    WHERE referencia = :bo
                      AND motivo = 'reserva'
                    GROUP BY producto_id
                """),
                {"bo": buy_order}
            ).all()

            for pid, qty in reservas:
                # devolver stock
                conn.execute(
                    text("""
                        UPDATE productos
                        SET stock = stock + :q
                        WHERE id = :pid
                    """),
                    {"q": qty, "pid": pid}
                )

                # auditar reversa
                conn.execute(
                    text("""
                        INSERT INTO audit_stock
                            (producto_id, cambio, motivo, referencia)
                        VALUES
                            (:pid, :chg, 'reversa', :ref)
                    """),
                    {"pid": pid, "chg": qty, "ref": buy_order}
                )

    # 4️⃣ Redirigir SIEMPRE al frontend
    return redirect(
        f"https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"
        f"?status={status}&order={buy_order}"
    )

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
