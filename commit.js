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
} else {
  cont.innerHTML = `
    <div class="card">
      <h2>❌ Pago rechazado</h2>
      <a href="index.html">Volver</a>
    </div>
  `;
}
