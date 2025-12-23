// --- Filtro por categoría ---
function filtrar(categoria) {
  const productos = document.querySelectorAll(".producto");
  productos.forEach(producto => {
    if (categoria === "todos" || producto.dataset.categoria === categoria) {
      producto.classList.remove("oculto");
    } else {
      producto.classList.add("oculto");
    }
  });
  reiniciarPaginacion();
}

// --- Buscador ---
function buscarProducto() {
  const texto = document.getElementById("buscador").value.toLowerCase();
  const productos = document.querySelectorAll(".producto");
  productos.forEach(producto => {
    const nombre = producto.querySelector("h2").textContent.toLowerCase();
    if (nombre.includes(texto)) {
      producto.classList.remove("oculto");
    } else {
      producto.classList.add("oculto");
    }
  });
  reiniciarPaginacion();
}

// --- Paginación dinámica con numeración y mensaje ---
let paginaActual = 1;
const productosPorPagina = 3;

function mostrarPagina(pagina) {
  const productosVisibles = Array.from(document.querySelectorAll(".producto")).filter(p => !p.classList.contains("oculto"));
  const totalProductos = productosVisibles.length;
  const totalPaginas = Math.ceil(totalProductos / productosPorPagina);

  if (pagina < 1) pagina = 1;
  if (pagina > totalPaginas) pagina = totalPaginas;

  paginaActual = pagina;
  const inicio = (pagina - 1) * productosPorPagina;
  const fin = inicio + productosPorPagina;

  productosVisibles.forEach((p, i) => {
    p.style.display = (i >= inicio && i < fin) ? "block" : "none";
  });

  // Botones de paginación con numeración
  let botones = `<button onclick="cambiarPagina(-1)" ${pagina === 1 ? "disabled" : ""}>Anterior</button>`;
  for (let i = 1; i <= totalPaginas; i++) {
    botones += `<button onclick="mostrarPagina(${i})" ${i === pagina ? "disabled" : ""}>${i}</button>`;
  }
  botones += `<button onclick="cambiarPagina(1)" ${pagina === totalPaginas ? "disabled" : ""}>Siguiente</button>`;
  document.getElementById("paginacion").innerHTML = botones;

  // Mensaje dinámico: "Mostrando X–Y de Z productos"
  const desde = inicio + 1;
  const hasta = Math.min(fin, totalProductos);
  document.getElementById("info-pagina").textContent = `Mostrando ${desde}–${hasta} de ${totalProductos} productos`;
}

function cambiarPagina(delta) {
  mostrarPagina(paginaActual + delta);
}

function reiniciarPaginacion() {
  mostrarPagina(1);
}

document.addEventListener("DOMContentLoaded", () => {
  reiniciarPaginacion();
});
