// Estado global
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

// Aplica filtros, búsqueda y orden, devuelve la lista filtrada
function obtenerListaFiltrada() {
  let lista = [...productos];

  // Filtro por categoría
  if (estado.categoria !== 'todos') {
    lista = lista.filter(p => p.categoria === estado.categoria);
  }

  // Búsqueda por nombre
  if (estado.busqueda.trim()) {
    const q = estado.busqueda.trim().toLowerCase();
    lista = lista.filter(p => p.nombre.toLowerCase().includes(q));
  }

  // Orden por precio
  lista.sort((a, b) => estado.orden === 'asc' ? a.precio - b.precio : b.precio - a.precio);

  return lista;
}

// Render del catálogo con paginación confiable
function renderCatalogo() {
  const cont = document.getElementById("catalogo");
  cont.innerHTML = "";

  const lista = obtenerListaFiltrada();
  const total = lista.length;
  const totalPaginas = Math.max(1, Math.ceil(total / estado.porPagina));

  // Clamp de página a rango válido
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
        <button class="btn-agregar" data-id="${p.id}">Agregar al carrito</button>
      `;
      cont.appendChild(card);
    });
  }

  renderPaginacion(total, totalPaginas, inicio, Math.min(fin, total));
  // Delegación de evento para botones de agregar
  cont.querySelectorAll(".btn-agregar").forEach(btn => {
    btn.addEventListener("click", () => agregarAlCarrito(Number(btn.dataset.id)));
  });
}

// Render de paginación con botones que funcionan
function renderPaginacion(total, totalPaginas, desde, hasta) {
  const contPag = document.getElementById("paginacion");
  const info = document.getElementById("info-pagina");

  // Botones: Anterior, números, Siguiente
  let html = `
    <button class="pag-btn" data-act="prev" ${estado.pagina === 1 ? "disabled" : ""}>Anterior</button>
  `;
  for (let i = 1; i <= totalPaginas; i++) {
    html += `<button class="pag-btn ${i === estado.pagina ? "activo" : ""}" data-page="${i}">${i}</button>`;
  }
  html += `
    <button class="pag-btn" data-act="next" ${estado.pagina === totalPaginas ? "disabled" : ""}>Siguiente</button>
  `;
  contPag.innerHTML = html;

  info.textContent = total
    ? `Mostrando ${desde + 1}–${hasta} de ${total} productos`
    : `Mostrando 0 de 0 productos`;

  // Eventos de paginación
  contPag.querySelectorAll(".pag-btn").forEach(btn => {
    const act = btn.dataset.act;
    const page = Number(btn.dataset.page);
    btn.addEventListener("click", () => {
      if (act === "prev") estado.pagina = Math.max(1, estado.pagina - 1);
      else if (act === "next") estado.pagina = estado.pagina + 1;
      else if (page) estado.pagina = page;
      renderCatalogo();
    });
  });
}

/* --- Carrito --- */
function agregarAlCarrito(id) {
  const p = productos.find(x => x.id === id);
  const entry = carrito.get(id) || { producto: p, cantidad: 0 };
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
    carrito.forEach(({ producto, cantidad }) => {
      cont.innerHTML += `
        <div class="carrito-linea">
          ${producto.nombre} x${cantidad} - ${formatoCLP(producto.precio * cantidad)}
        </div>`;
      total += producto.precio * cantidad;
      cantidadTotal += cantidad;
    });
  }

  totalEl.textContent = `Total: ${formatoCLP(total)}`;
  contadorEl.textContent = cantidadTotal;
}


function disminuirCantidad(id) {
  const entry = carrito.get(id);
  if (!entry) return;
  entry.cantidad = Math.max(0, entry.cantidad - 1);
  if (entry.cantidad === 0) carrito.delete(id);
  guardarCarrito();
  renderCarrito();
}

function aumentarCantidad(id) {
  const entry = carrito.get(id);
  if (!entry) return;
  entry.cantidad += 1;
  guardarCarrito();
  renderCarrito();
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
  if (data) {
    const arr = JSON.parse(data);
    carrito = new Map(arr);
  }
  renderCarrito();
}

// Vaciar carrito
document.addEventListener("DOMContentLoaded", () => {
  const btnVaciar = document.getElementById("btn-vaciar");
  if (btnVaciar) {
    btnVaciar.addEventListener("click", () => {
      carrito.clear();
      guardarCarrito();
      renderCarrito();
    });
  }
});

/* --- Interacciones de UI --- */
function filtrar(cat) {
  estado.categoria = cat;
  estado.pagina = 1;
  renderCatalogo();
}

function buscarProducto() {
  const input = document.getElementById("buscador");
  estado.busqueda = input ? input.value : '';
  estado.pagina = 1;
  renderCatalogo();
}

function ordenarPorPrecio(order) {
  estado.orden = order;
  estado.pagina = 1;
  renderCatalogo();
}

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  cargarCarrito();
  renderCatalogo();
});
