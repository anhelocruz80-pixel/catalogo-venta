/* =========================================================
   CONFIG
========================================================= */
const API_URL = "https://catalogo-venta.onrender.com";

/* =========================================================
   ESTADO GLOBAL
========================================================= */
let productos = [];
let carrito = new Map();

let estado = {
  categoria: "todos",
  busqueda: "",
  orden: "asc",
  pagina: 1,
  porPagina: 4
};

/* =========================================================
   HELPERS
========================================================= */
function formatoCLP(n) {
  return `$${Number(n).toLocaleString("es-CL")}`;
}

function getProducto(id) {
  return productos.find(p => p.id === id);
}

function persistirCarrito() {
  const data = [];
  carrito.forEach(({ producto, cantidad }) => {
    data.push({ id: producto.id, cantidad });
  });
  localStorage.setItem("carrito", JSON.stringify(data));
}

/* =========================================================
   CARGAR PRODUCTOS
========================================================= */
async function cargarProductos() {
  try {
    const res = await fetch(`${API_URL}/productos`);
    if (!res.ok) throw new Error("Error cargando productos");

    const data = await res.json();

    productos = data.map(p => ({
      id: p.id,
      nombre: p.nombre,
      descripcion: p.descripcion || "",
      categoria: p.categoria || "otros",
      precio: p.precio,
      stock: p.stock,
      imagen: p.imagen || `img/${p.nombre.toLowerCase().replace(/\s+/g, "")}.png`
    }));

    renderCatalogo();
  } catch (err) {
    console.error(err);
    alert("No se pudo cargar el catálogo.");
  }
}

/* =========================================================
   FILTRO / ORDEN / PAGINACIÓN
========================================================= */
function obtenerListaFiltrada() {
  let lista = [...productos];

  if (estado.categoria !== "todos") {
    lista = lista.filter(p => p.categoria === estado.categoria);
  }

  if (estado.busqueda.trim()) {
    const q = estado.busqueda.toLowerCase();
    lista = lista.filter(p => p.nombre.toLowerCase().includes(q));
  }

  lista.sort((a, b) =>
    estado.orden === "asc" ? a.precio - b.precio : b.precio - a.precio
  );

  return lista;
}

function cambiarPagina(delta) {
  estado.pagina += delta;
  renderCatalogo();
}

function irPagina(n) {
  estado.pagina = n;
  renderCatalogo();
}

/* =========================================================
   RENDER CATÁLOGO
========================================================= */
function renderCatalogo() {
  const cont = document.getElementById("catalogo");
  const pag = document.getElementById("paginacion");
  const info = document.getElementById("info-pagina");

  cont.innerHTML = "";

  const lista = obtenerListaFiltrada();
  const total = lista.length;
  const totalPaginas = Math.max(1, Math.ceil(total / estado.porPagina));

  if (estado.pagina > totalPaginas) estado.pagina = totalPaginas;
  if (estado.pagina < 1) estado.pagina = 1;

  const inicio = (estado.pagina - 1) * estado.porPagina;
  const fin = inicio + estado.porPagina;
  const paginaItems = lista.slice(inicio, fin);

  if (total === 0) {
    cont.innerHTML = `<p>No se encontraron productos.</p>`;
  }

  paginaItems.forEach(p => {
    const agotado = p.stock <= 0;

    cont.innerHTML += `
      <div class="producto">
        <img src="${p.imagen}" alt="${p.nombre}">
        <h2>${p.nombre}</h2>
        <p class="precio">${formatoCLP(p.precio)}</p>
        <p>${p.descripcion}</p>
        <p class="stock">Stock: ${p.stock}</p>
        <button ${agotado ? "disabled" : ""} onclick="agregarAlCarrito(${p.id})">
          ${agotado ? "Agotado" : "Agregar"}
        </button>
      </div>
    `;
  });

  // paginación
  let html = `<button ${estado.pagina === 1 ? "disabled" : ""} onclick="cambiarPagina(-1)">Anterior</button>`;
  for (let i = 1; i <= totalPaginas; i++) {
    html += `<button class="${i === estado.pagina ? "activo" : ""}" onclick="irPagina(${i})">${i}</button>`;
  }
  html += `<button ${estado.pagina === totalPaginas ? "disabled" : ""} onclick="cambiarPagina(1)">Siguiente</button>`;
  pag.innerHTML = html;

  info.textContent = total
    ? `Mostrando ${inicio + 1}–${Math.min(fin, total)} de ${total}`
    : "";
}

/* =========================================================
   CARRITO
========================================================= */
async function agregarAlCarrito(id) {
  try {
    const res = await fetch(`${API_URL}/agregar-carrito`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, cantidad: 1 })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Error");

    const p = getProducto(id);
    p.stock -= 1;

    const entry = carrito.get(id) || { producto: p, cantidad: 0 };
    entry.cantidad += 1;
    carrito.set(id, entry);

    persistirCarrito();
    renderCatalogo();
    renderCarrito();
  } catch (e) {
    alert("No se pudo agregar al carrito.");
  }
}

function renderCarrito() {
  const cont = document.getElementById("carrito-items");
  const totalEl = document.getElementById("carrito-total");
  const contador = document.getElementById("carrito-contador");

  cont.innerHTML = "";
  let total = 0;
  let cantidad = 0;

  if (carrito.size === 0) {
    cont.innerHTML = `<p>Carrito vacío</p>`;
  }

  carrito.forEach(({ producto, cantidad: q }) => {
    total += producto.precio * q;
    cantidad += q;

    cont.innerHTML += `
      <div class="carrito-linea">
        <span>${producto.nombre} x${q}</span>
        <span>${formatoCLP(producto.precio * q)}</span>
        <button onclick="quitarDelCarrito(${producto.id})">✕</button>
      </div>
    `;
  });

  totalEl.textContent = `Total: ${formatoCLP(total)}`;
  contador.textContent = cantidad;
}

async function quitarDelCarrito(id) {
  const item = carrito.get(id);
  if (!item) return;

  await fetch(`${API_URL}/liberar-reservas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      items: [{ id, cantidad: item.cantidad }]
    })
  });

  carrito.delete(id);
  persistirCarrito();
  await cargarProductos();
  renderCarrito();
}

async function vaciarCarrito() {
  if (carrito.size === 0) return;

  const items = [];
  carrito.forEach(({ producto, cantidad }) => {
    items.push({ id: producto.id, cantidad });
  });

  await fetch(`${API_URL}/liberar-reservas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items })
  });

  carrito.clear();
  persistirCarrito();
  await cargarProductos();
  renderCarrito();
}


/* =========================================================
   PAGO
========================================================= */
async function pagarCarrito() {
  const items = [];
  carrito.forEach(({ producto, cantidad }) => {
    items.push({ id: producto.id, cantidad });
  });

  if (items.length === 0) {
    alert("El carrito está vacío.");
    return;
  }

  const res = await fetch(`${API_URL}/create-transaction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items })
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "No se pudo iniciar el pago");
    return;
  }

  const form = document.createElement("form");
  form.method = "POST";
  form.action = data.url;

  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "token_ws";
  input.value = data.token;

  form.appendChild(input);
  document.body.appendChild(form);
  form.submit();
}

/* =========================================================
   EVENTOS UI
========================================================= */
function filtrar(cat) {
  estado.categoria = cat;
  estado.pagina = 1;
  renderCatalogo();
}

function buscarProducto() {
  estado.busqueda = document.getElementById("buscador").value;
  estado.pagina = 1;
  renderCatalogo();
}

function ordenarPorPrecio(v) {
  estado.orden = v;
  estado.pagina = 1;
  renderCatalogo();
}

/* =========================================================
   INIT
========================================================= */
document.addEventListener("DOMContentLoaded", async () => {
  // 🔥 LIBERAR RESERVAS SI SE REFRESCÓ LA PÁGINA
  try {
    await fetch(`${API_URL}/liberar-reservas`, {
      method: "POST"
    });
  } catch (e) {
    console.warn("No se pudieron liberar reservas pendientes");
  }

  // limpiar estado frontend
  carrito.clear();
  localStorage.setItem("carrito", "[]");
  renderCarrito();

  // cargar productos ya con stock correcto
  await cargarProductos();

  const btnVaciar = document.getElementById("btn-vaciar");
  if (btnVaciar) {
    btnVaciar.addEventListener("click", vaciarCarrito);
  }
});


