const params = new URLSearchParams(window.location.search);
const status = params.get("status");
const order = params.get("order");

const cont = document.getElementById("resultado-pago");

// 🛡️ Caso: acceso directo o sin parámetros
if (!status) {
  cont.innerHTML = `
    <div class="card">
      <h2>ℹ️ Sin información de pago</h2>
      <p>No hay una transacción asociada.</p>
      <a href="index.html">Ir a la tienda</a>
    </div>
  `;

} else if (status === "AUTHORIZED") {
  cont.innerHTML = `
    <div class="card">
      <h2>✅ Pago exitoso</h2>
      ${order ? `<p>Orden: ${order}</p>` : ""}
      <a href="index.html">Volver a la tienda</a>
    </div>
  `;

} else if (status === "ABORTED") {
  cont.innerHTML = `
    <div class="card">
      <h2>⚠️ Compra cancelada</h2>
      <p>No se realizó ningún cargo.</p>
      <a href="index.html">Volver a la tienda</a>
    </div>
  `;

} else {
  cont.innerHTML = `
    <div class="card">
      <h2>❌ Pago rechazado</h2>
      <p>El banco no autorizó el pago.</p>
      <a href="index.html">Volver</a>
    </div>
  `;
}
