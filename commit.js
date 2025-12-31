const params = new URLSearchParams(window.location.search);
const status = params.get("status");
const order = params.get("order");

const cont = document.getElementById("resultado-pago");

if (status === "AUTHORIZED") {
  cont.innerHTML = `
    <div class="card">
      <h2>✅ Pago exitoso</h2>
      <p>Orden: ${order}</p>
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
