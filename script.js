// Estado global
let productos = [];
let carrito = new Map();
let estado = {
  categoria: 'todos',
  busqueda: '',
  orden: 'asc',
  pagina: 1,
  porPagina: 4
};

// Helpers
function formatoCLP(n) {
  return `$${n.toLocaleString('es-CL')}`;
}
function getProducto(id) {
  return productos.find(x => x.id === id);
}

/* --- Cargar productos desde backend --- */
async function cargarProductos() {
  try {
    const res = await fetch("https://catalogo-venta.onrender.com/productos", {
      headers: { "Content-Type": "application/json" }
    });
    productos = await res.json();

    // Normaliza campos por si faltan en backend
    productos = productos.map(p => ({
      id: p.id,
      nombre: p.nombre,
      precio: p.precio,
      categoria: p.categoria || 'otros',
      imagen: p.imagen || `img/${(p.nombre || 'producto').toLowerCase().replace(/\s+/g,'')}.png`,
      descripcion: p.descripcion || '',
      stock: typeof p.stock === 'number' ? p.stock : 0
    }));

    renderCatalogo();
  } catch (error) {
    console.error("Error cargando productos:", error);
    alert("No se pudo cargar el catálogo desde el servidor.");
  }
}

/* --- Filtro, orden y paginación --- */
function obtenerListaFiltrada() {
  let lista = [...productos];
  if (estado.categoria !== 'todos') {
    lista = lista.filter(p => p.categoria === estado.categoria);
  }
  if (estado.busqueda.trim()) {
    const q = estado.busqueda.trim().toLowerCase();
    lista = lista.filter(p => p.nombre.toLowerCase().includes(q));
  }
  lista.sort((a, b) => estado.orden === 'asc' ? a.precio - b.precio : b.precio - a.precio);
  return lista;
}

function renderPaginacion(total, totalPaginas, desde, hasta) {
  const contPag = document.getElementById("paginacion");
  const info = document.getElementById("info-pagina");

  let html = `<button onclick="cambiarPagina(-1)" ${estado.pagina===1?"disabled":""}>Anterior</button>`;
  for (let i=1; i<=totalPaginas; i++) {
    html += `<button onclick="irPagina(${i})" class="${i===estado.pagina?"activo":""}">${i}</button>`;
  }
  html += `<button onclick="cambiarPagina(1)" ${estado.pagina===totalPaginas?"disabled":""}>Siguiente</button>`;
  contPag.innerHTML = html;

  info.textContent = total
    ? `Mostrando ${desde+1}–${hasta} de ${total} productos`
    : `Mostrando 0 de 0 productos`;
}

function cambiarPagina(delta) {
  estado.pagina += delta;
  renderCatalogo();
}
function irPagina(num) {
  estado.pagina = num;
  renderCatalogo();
}

/* --- Render catálogo --- */
function renderCatalogo() {
  const cont = document.getElementById("catalogo");
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
    cont.innerHTML = `<div class="mensaje-vacio">No se encontraron productos.</div>`;
  } else {
    paginaItems.forEach(p => {
      const agotado = p.stock <= 0;
      const card = document.createElement("div");
      card.className = "producto";
      card.innerHTML = `
        <img src="${p.imagen}" alt="${p.nombre}">
        <h2>${p.nombre}</h2>
        <p class="precio">${formatoCLP(p.precio)}</p>
        <p class="descripcion">${p.descripcion}</p>
        <p class="stock">Stock: ${p.stock}</p>
        <button 
          onclick="agregarAlCarrito(${p.id})"
          ${agotado ? "disabled" : ""}
          class="${agotado ? "btn-agregar agotado" : "btn-agregar"}"
          aria-label="${agotado ? "Producto agotado" : "Agregar al carrito"}"
        >
          ${agotado ? "Agotado" : "Agregar al carrito"}
        </button>
      `;
      cont.appendChild(card);
    });
  }

  renderPaginacion(total, totalPaginas, inicio, Math.min(fin, total));
}

/* --- Carrito con stock en backend --- */
async function agregarAlCarrito(id) {
  try {
    const res = await fetch("https://catalogo-venta.onrender.com/agregar-carrito", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ id, cantidad: 1 })
    });
    const data = await res.json();

    if (data.error) {
      alert("No se pudo agregar: " + data.error);
      return;
    }

    const p = getProducto(id);
    if (p) p.stock = data.producto?.stock ?? (p.stock - 1); // usa stock devuelto por backend si existe

    const entry = carrito.get(id) || { producto: p, cantidad: 0 };
    entry.cantidad += 1;
    carrito.set(id, entry);

    renderCatalogo();
    renderCarrito();
  } catch (error) {
    console.error("Error al agregar al carrito:", error);
    alert("Error al agregar al carrito.");
  }
}

function renderCarrito() {
  const cont = document.getElementById("carrito-items");
  const totalEl = document.getElementById("carrito-total");
  const contadorEl = document.getElementById("carrito-contador");
  cont.innerHTML = "";
  let total = 0;
  let cantidadTotal = 0;

  if (carrito.size === 0) {
    cont.innerHTML = `<div class="carrito-vacio">Tu carrito está vacío</div>`;
  } else {
    carrito.forEach(({producto,cantidad})=>{
      cont.innerHTML += `
        <div class="carrito-linea"> 
          <span class="nombre-producto">${producto.nombre} x${cantidad}</span> 
          <span class="precio-producto">${formatoCLP(producto.precio*cantidad)}</span> 
          <button class="btn-eliminar" onclick="quitarDelCarrito(${producto.id})" aria-label="Eliminar producto">✕</button> 
        </div>
      `;
      total += producto.precio*cantidad;
      cantidadTotal += cantidad;
    });
  }

  totalEl.textContent = `Total: ${formatoCLP(total)}`;
  contadorEl.textContent = cantidadTotal;
}

async function quitarDelCarrito(id) {
  const entry = carrito.get(id);
  if (!entry) return;

  try {
    await fetch("https://catalogo-venta.onrender.com/devolver-carrito", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ items: [{ id, cantidad: entry.cantidad }] })
    });
  } catch (error) {
    console.error("Error devolviendo stock:", error);
  }

  carrito.delete(id);
  await cargarProductos(); // refresca stock global
  renderCarrito();
}

document.getElementById("btn-vaciar").addEventListener("click", async ()=>{
  const items = [];
  carrito.forEach(({producto, cantidad}) => {
    items.push({ id: producto.id, cantidad });
  });

  try {
    await fetch("https://catalogo-venta.onrender.com/devolver-carrito", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ items })
    });
  } catch (error) {
    console.error("Error devolviendo stock:", error);
  }

  carrito.clear();
  await cargarProductos();
  renderCarrito();
});

/* --- Interacciones --- */
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
function ordenarPorPrecio(order) {
  estado.orden = order;
  estado.pagina = 1;
  renderCatalogo();
}

/* --- Inicialización --- */
document.addEventListener("DOMContentLoaded", async ()=>{
  const saved = JSON.parse(localStorage.getItem("carrito") || "[]"); 
  if (saved.length > 0) { 
    try { 
	   await fetch("https://catalogo-venta.onrender.com/devolver-carrito", { 
	     method: "POST", 
	     headers: {"Content-Type":"application/json"}, 
		 body: JSON.stringify({ items: saved }) 
	   }); 
	} catch(e) { console.error("Error devolviendo stock al refrescar:", e); } 
  }
  carrito.clear();
  localStorage.removeItem("carrito");
  renderCarrito();
  await cargarProductos();
});

/* --- Pago con Webpay (valida y muestra errores claros) --- */
async function pagarCarrito() {
  try {
    let total = 0;
    const items = [];
    carrito.forEach(({producto, cantidad}) => {
      total += producto.precio * cantidad;
      items.push({ id: producto.id, cantidad });
    });

    if (total <= 0) {
      alert("Tu carrito está vacío, agrega productos antes de pagar.");
      return;
    }

    const res = await fetch("https://catalogo-venta.onrender.com/create-transaction", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ amount: total, items })
    });

    const data = await res.json();

    // Mensaje claro si backend rechazó por stock u otro motivo
    if (data.error) {
      alert("No se pudo iniciar el pago: " + data.error);
      await cargarProductos(); // sincroniza stock si hubo reserva liberada o rechazo
      return;
    }

    if (data.token && data.url) {
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
    } else {
      alert("Error iniciando pago. Revisa la consola para más detalles.");
      console.error("Respuesta inesperada:", data);
      await cargarProductos();
    }
  } catch (error) {
    console.error("Error en pagarCarrito:", error);
    alert("No se pudo iniciar el pago. Verifica la conexión con el backend.");
  }
}

/* --- Procesar commit (commit.html) --- */
async function procesarCommit() {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token_ws");

    const cont = document.getElementById("resultado-pago");

    if (!token) {
      cont.innerHTML = `
        <div class="card">
          <h2>⚠️ Falta token</h2>
          <p>No se recibió el token de pago.</p>
          <button class="warning" onclick="window.location.href='https://anhelocruz80-pixel.github.io/catalogo-venta/'">
            🔙 Volver a la tienda
          </button>
        </div>
      `;
      return;
    }

    const res = await fetch(`https://catalogo-venta.onrender.com/commit?token_ws=${token}`, {
      method: "GET",
      headers: {"Content-Type":"application/json"}
    });

    const data = await res.json();

    if (data.status === "AUTHORIZED" || data.status === "SUCCESS") {
      // Limpia carrito tras pago exitoso
      carrito.clear();
      localStorage.removeItem("carrito");

      cont.innerHTML = `
        <div class="card">
          <h2>✅ Pago exitoso</h2>
          <p><strong>Orden:</strong> ${data.buy_order}</p>
          <p><strong>Monto:</strong> ${formatoCLP(Number(data.amount || 0))}</p>
          <p><strong>Fecha:</strong> ${data.transaction_date || ''}</p>
          <button class="success" onclick="window.location.href='https://anhelocruz80-pixel.github.io/catalogo-venta/'">
            🔙 Volver a la tienda
          </button>
        </div>
      `;
    } else {
      // Pago rechazado → backend ya devolvió stock (según app.py)
      cont.innerHTML = `
        <div class="card">
          <h2>❌ Pago rechazado</h2>
          <p><strong>Estado:</strong> ${data.status || 'UNKNOWN'}</p>
          <p><strong>Código de respuesta:</strong> ${data.response_code ?? '—'}</p>
          <p><strong>Autorización:</strong> ${data.authorization_code ?? '—'}</p>
          <p><strong>Fecha:</strong> ${data.transaction_date ?? '—'}</p>
          <button class="error" onclick="window.location.href='https://anhelocruz80-pixel.github.io/catalogo-venta/'">
            🔙 Volver a la tienda
          </button>
        </div>
      `;
    }

  } catch (error) {
    console.error("Error al procesar commit:", error);
    const cont = document.getElementById("resultado-pago");
    cont.innerHTML = `
      <div class="card">
        <h2>⚠️ Error al confirmar el pago</h2>
        <p>Revisa la consola para más detalles.</p>
        <button class="warning" onclick="window.location.href='https://anhelocruz80-pixel.github.io/catalogo-venta/'">
          🔙 Volver a la tienda
        </button>
      </div>
    `;
  }
}
