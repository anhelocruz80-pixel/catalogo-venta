import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Transbank SDK
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType

# Flask + CORS
app = Flask(__name__)
CORS(app, supports_credentials=True,
     resources={r"/*": {"origins": ["https://anhelocruz80-pixel.github.io"]}})

# Conexión a PostgreSQL (Railway)
PGHOST = os.environ.get("PGHOST")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE")
PGUSER = os.environ.get("PGUSER", "postgres")
PGPASSWORD = os.environ.get("PGPASSWORD")

db_url = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
engine = create_engine(db_url, poolclass=NullPool, future=True)

# Transbank (TEST)
options = WebpayOptions(
    commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
    api_key=IntegrationApiKeys.WEBPAY,
    integration_type=IntegrationType.TEST  # Cambiar a LIVE en producción
)
tx = Transaction(options)

# --- Helpers ---
def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

# --- Inicialización de tablas ---
def init_db():
    schema_sql = """
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    CREATE TABLE IF NOT EXISTS productos (
      id SERIAL PRIMARY KEY,
      nombre VARCHAR(120) NOT NULL,
      descripcion VARCHAR(500),
      categoria VARCHAR(50) NOT NULL,
      precio INTEGER NOT NULL,
      stock INTEGER NOT NULL CHECK (stock >= 0),
      activo BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS carritos (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      estado VARCHAR(20) NOT NULL DEFAULT 'abierto',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS carrito_items (
      id SERIAL PRIMARY KEY,
      carrito_id UUID NOT NULL REFERENCES carritos(id) ON DELETE CASCADE,
      producto_id INTEGER NOT NULL REFERENCES productos(id),
      cantidad INTEGER NOT NULL CHECK (cantidad > 0),
      precio_unitario INTEGER NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS transacciones (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      buy_order VARCHAR(40) UNIQUE NOT NULL,
      tb_token VARCHAR(120),
      tb_status VARCHAR(40), -- AUTHORIZED | FAILED | REVERSED | PENDING
      monto_total INTEGER NOT NULL,
      currency VARCHAR(10) NOT NULL DEFAULT 'CLP',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ
    );

    CREATE TABLE IF NOT EXISTS transaccion_items (
      id SERIAL PRIMARY KEY,
      buy_order VARCHAR(40) NOT NULL REFERENCES transacciones(buy_order) ON DELETE CASCADE,
      producto_id INTEGER NOT NULL REFERENCES productos(id),
      cantidad INTEGER NOT NULL CHECK (cantidad > 0),
      precio_unitario INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_stock (
      id BIGSERIAL PRIMARY KEY,
      producto_id INTEGER NOT NULL REFERENCES productos(id),
      cambio INTEGER NOT NULL, -- negativo para decremento
      motivo VARCHAR(80) NOT NULL, -- reserva | pago | reversa | cancelación | ajuste
      referencia VARCHAR(200), -- buy_order, carrito_id, token, etc.
      actor VARCHAR(40) NOT NULL DEFAULT 'api',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
        count = conn.execute(text("SELECT COUNT(*) FROM productos")).scalar_one()
        if count == 0:
            conn.execute(text("""
                INSERT INTO productos (nombre, descripcion, categoria, precio, stock)
                VALUES
                ('Notebook Usado', 'Equipo en buen estado', 'electronica', 120000, 1),
                ('Zapatos de Cuero', 'Zapatos talla 42', 'vestuario', 25000, 3),
                ('Mesa de Madera', 'Mesa comedor', 'hogar', 50000, 2),
                ('Reloj de Pared', 'Reloj clásico', 'accesorios', 10000, 2),
                ('Silla de Madera', 'Silla resistente', 'hogar', 20000, 4),
                ('Celular Usado', 'Celular Android', 'electronica', 80000, 1),
                ('Chaqueta Invierno', 'Chaqueta abrigada', 'vestuario', 30000, 3),
                ('Lámpara Escritorio', 'Lámpara ajustable', 'hogar', 15000, 2),
                ('Audífonos Bluetooth', 'Audífonos inalámbricos', 'electronica', 35000, 2),
                ('Bolso Deportivo', 'Bolso amplio', 'accesorios', 18000, 5);
            """))

# Ejecuta inicialización
init_db()

# --- Endpoints públicos ---

@app.route("/")
def home():
    return "Backend funcionando correctamente 🚀"

@app.route("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat()})

# Lista de productos para frontend
@app.route("/productos", methods=["GET"])
def listar_productos():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, nombre, descripcion, categoria, precio, stock, activo
            FROM productos WHERE activo = TRUE ORDER BY id
        """)).mappings().all()
    return jsonify(list(rows))

# Agrega al carrito: descuenta stock y audita (igual que tu flujo actual)
@app.route("/agregar-carrito", methods=["POST"])
def agregar_carrito():
    data = request.json or {}
    producto_id = int(data.get("id"))
    cantidad = int(data.get("cantidad", 1))

    with engine.begin() as conn:
        prod = conn.execute(text("SELECT stock, precio FROM productos WHERE id=:id AND activo=TRUE"),
                            {"id": producto_id}).first()
        if not prod:
            return jsonify({"error": "Producto no existe"}), 404
        stock, precio = prod
        if stock < cantidad:
            return jsonify({"error": "Stock insuficiente", "stock": stock}), 400

        # Descarga stock
        conn.execute(text("UPDATE productos SET stock = stock - :c WHERE id=:id"),
                     {"c": cantidad, "id": producto_id})

        # Auditoría de reserva (no requiere carrito_id porque tu frontend no lo maneja)
        conn.execute(text("""
            INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
            VALUES (:pid, :chg, 'reserva', 'click')
        """), {"pid": producto_id, "chg": -cantidad})

    return jsonify({"message": "Agregado", "producto": {"id": producto_id, "stock": stock - cantidad}})

# Devuelve stock (vaciar carrito, quitar ítem): suma y audita cancelación
@app.route("/devolver-carrito", methods=["POST"])
def devolver_carrito():
    data = request.json or {}
    items = data.get("items", [])

    if not isinstance(items, list):
        return jsonify({"error": "Formato inválido"}), 400

    with engine.begin() as conn:
        for it in items:
            pid = int(it.get("id"))
            qty = int(it.get("cantidad", 0))
            if qty <= 0:
                continue

            conn.execute(text("UPDATE productos SET stock = stock + :c WHERE id=:id"),
                         {"c": qty, "id": pid})
            conn.execute(text("""
                INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                VALUES (:pid, :chg, 'cancelación', 'manual')
            """), {"pid": pid, "chg": qty})

    return jsonify({"message": "Stock devuelto"})

# Crea transacción Webpay: valida stock actual, guarda buy_order y items; NO descuenta nuevamente
@app.route("/create-transaction", methods=["POST", "OPTIONS"])
def create_transaction():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json or {}
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "Carrito vacío"}), 400

    # Calcula monto total desde DB (para evitar manipulación en frontend)
    amount = 0
    with engine.begin() as conn:
        for it in items:
            pid = int(it["id"])
            qty = int(it["cantidad"])
            row = conn.execute(text("""
                SELECT precio, stock FROM productos WHERE id=:id AND activo=TRUE
            """), {"id": pid}).first()

            if not row:
                return jsonify({"error": f"Producto {pid} no existe"}), 400

            precio, stock = row
            # En tu flujo, el stock ya fue descontado al agregar-carrito.
            # Validamos que no esté negativo (consistencia).
            if stock < 0:
                return jsonify({"error": "Inconsistencia de stock"}), 409

            amount += precio * qty

    session_id = f"sesion-{uuid.uuid4().hex[:8]}"
    buy_order = f"orden-{uuid.uuid4().hex[:12]}"
    return_url = "https://anhelocruz80-pixel.github.io/catalogo-venta/commit.html"

    # Crea transacción en Transbank
    try:
        response = tx.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=return_url
        )
    except Exception as e:
        log(f"Error creando transacción: {e}")
        return jsonify({"error": "No se pudo iniciar el pago"}), 500

    token = response.get("token")
    url = response.get("url")
    if not token or not url:
        return jsonify({"error": "Respuesta inválida de Webpay"}), 502

    # Guarda transacción y los items (para reversas si falla)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO transacciones (buy_order, tb_token, tb_status, monto_total)
            VALUES (:bo, :tok, 'PENDING', :monto)
        """), {"bo": buy_order, "tok": token, "monto": amount})

        for it in items:
            pid = int(it["id"])
            qty = int(it["cantidad"])
            precio = conn.execute(text("SELECT precio FROM productos WHERE id=:id"), {"id": pid}).scalar_one()
            conn.execute(text("""
                INSERT INTO transaccion_items (buy_order, producto_id, cantidad, precio_unitario)
                VALUES (:bo, :pid, :qty, :precio)
            """), {"bo": buy_order, "pid": pid, "qty": qty, "precio": precio})

    log(f"Transacción creada: Orden {buy_order}, monto {amount}, token {token}")
    return jsonify({"token": token, "url": url})

# Confirmar transacción: AUTHORIZED mantiene stock; fallo → devolver stock usando items guardados
@app.route("/commit", methods=["POST", "GET"])
def commit_transaction():
    token = request.args.get("token_ws") or request.form.get("token_ws")
    if not token:
        return jsonify({"status": "ERROR", "message": "Falta token_ws"}), 400

    try:
        response = tx.commit(token)
    except Exception as e:
        log(f"Error en commit: {e}")
        return jsonify({"status": "ERROR", "message": "Fallo al confirmar pago"}), 500

    buy_order = response.get("buy_order")
    status = response.get("status")

    with engine.begin() as conn:
        # Actualiza estado en DB
        conn.execute(text("""
            UPDATE transacciones
            SET tb_status = :st, updated_at = NOW()
            WHERE buy_order = :bo
        """), {"st": status, "bo": buy_order})

        if status in ["AUTHORIZED", "SUCCESS"]:
            # Pago ok: no movemos stock (ya fue reservado al agregar-carrito)
            conn.execute(text("""
                INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                SELECT producto_id, 0, 'pago', :bo FROM transaccion_items WHERE buy_order=:bo
            """), {"bo": buy_order})
            log(f"Pago exitoso: {buy_order}")

        else:
            # Pago fallido: devolver stock por cada item de la transacción
            items = conn.execute(text("""
                SELECT producto_id, cantidad FROM transaccion_items WHERE buy_order=:bo
            """), {"bo": buy_order}).all()

            for pid, qty in items:
                conn.execute(text("UPDATE productos SET stock = stock + :c WHERE id=:id"),
                             {"c": qty, "id": pid})
                conn.execute(text("""
                    INSERT INTO audit_stock (producto_id, cambio, motivo, referencia)
                    VALUES (:pid, :chg, 'reversa', :ref)
                """), {"pid": pid, "chg": qty, "ref": buy_order})
            log(f"Pago rechazado: {buy_order}, stock devuelto")

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
