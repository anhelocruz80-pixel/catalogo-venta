Lista de productos de ejemplo
let productos = [
  {id:1, nombre:"Notebook Usado", precio:120000, categoria:"electronica", imagen:"img/notebook.png", descripcion:"Notebook funcional con 4GB RAM"},
  {id:2, nombre:"Zapatos de Cuero", precio:25000, categoria:"vestuario", imagen:"img/zapatos.png", descripcion:"Zapatos en excelente estado"},
  {id:3, nombre:"Mesa de Madera", precio:50000, categoria:"hogar", imagen:"img/mesa.png", descripcion:"Mesa robusta de pino"},
  {id:4, nombre:"Reloj de Pared", precio:10000, categoria:"accesorios", imagen:"img/reloj.png", descripcion:"Reloj en buen estado"},
  {id:5, nombre:"Silla de Madera", precio:20000, categoria:"hogar", imagen:"img/silla.png", descripcion:"Silla artesanal buen estado"},
  {id:6, nombre:"Celular Usado", precio:80000, categoria:"electronica", imagen:"img/celular.png", descripcion:"Celular en buen estado"},
  {id:7, nombre:"Chaqueta Invierno", precio:30000, categoria:"vestuario", imagen:"img/chaqueta.png", descripcion:"Chaqueta abrigada poco uso"},
  {id:8, nombre:"Lámpara Escritorio", precio:15000, categoria:"hogar", imagen:"img/lampara.png", descripcion:"Lámpara funcional para oficina"},
  {id:9, nombre:"Audífonos Bluetooth", precio:35000, categoria:"electronica", imagen:"img/audifonos.png", descripcion:"Audífonos inalámbricos buen sonido"},
  {id:10, nombre:"Bolso Deportivo", precio:18000, categoria:"accesorios", imagen:"img/bolso.png", descripcion:"Bolso resistente para gimnasio"}
];

// Estado global
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

// Filtrar lista según estado
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

// Render catálogo con paginación
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
      const card = document.createElement("div");
      card.className = "producto";
      card.innerHTML = `
        <img src="${p.imagen}" alt="${p.nombre}">
        <h2>${p.nombre}</h2>
        <p class="precio">${formatoCLP(p.precio)}</p>
        <p>${p.descripcion}</p>
        <button onclick="agregarAlCarrito(${p.id})">Agregar al carrito</button>
      `;
      cont.appendChild(card);
    });
  }

  renderPaginacion(total, totalPaginas, inicio, Math.min(fin, total));
}

// Render paginación
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

/* --- Carrito --- */
function agregarAlCarrito(id) {
  const p = productos.find(x => x.id === id);
  const entry = carrito.get(id) || { producto:p, cantidad:0 };
  entry.cantidad++;
  carrito.set(id, entry);
  guardarCarrito();
  renderCarrito();
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
          ${producto.nombre} x${cantidad} - ${formatoCLP(producto.precio*cantidad)}
          <button onclick="quitarDelCarrito(${producto.id})">✕</button>
        </div>`;
      total += producto.precio*cantidad;
      cantidadTotal += cantidad;
    });
  }

  totalEl.textContent = `Total: ${formatoCLP(total)}`;
  contadorEl.textContent = cantidadTotal;
}

function quitarDelCarrito(id) {
  carrito.delete(id);
  guardarCarrito();
  renderCarrito();
}

function guardarCarrito() {
  localStorage.setItem("carrito", JSON.stringify([...carrito]));
}
function cargarCarrito() {
  const data = localStorage.getItem("carrito");
  if(data){
    carrito = new Map(JSON.parse(data));
  }
  renderCarrito();
}

document.getElementById("btn-vaciar").addEventListener("click", ()=>{
  carrito.clear();
  guardarCarrito();
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

// Inicialización
document.addEventListener("DOMContentLoaded", ()=>{
  cargarCarrito();
  renderCatalogo();
});

async function pagarCarrito() {
  try {
    // Calcula el total del carrito
    let total = 0;
    carrito.forEach(({producto, cantidad}) => {
      total += producto.precio * cantidad;
    });

    if (total <= 0) {
      alert("Tu carrito está vacío, agrega productos antes de pagar.");
      return;
    }

    console.log("Monto total a pagar:", total);

    // Llama al backend Flask en Render
    const res = await fetch("https://catalogo-venta.onrender.com/create-transaction", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({amount: total})
    });

    if (!res.ok) {
      throw new Error("Error en la petición al backend: " + res.status);
    }

    const data = await res.json();
    console.log("Respuesta del backend:", data);

    // Verifica si la respuesta tiene token y url
    if (data.token && data.url) {
      console.log("Token recibido:", data.token);
      console.log("URL de Webpay:", data.url);

      // Redirige al formulario de pago de Webpay
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
    }
  } catch (error) {
    console.error("Error en pagarCarrito:", error);
    alert("No se pudo iniciar el pago. Verifica la conexión con el backend.");
  }
}