// =======================
// CONFIGURACIÓN DE COLORES (IDENTIDAD COLEGIO)
// =======================
Chart.defaults.font.family = "'Poppins', sans-serif";
Chart.defaults.color = '#64748b';

const BRAND_COLORS = {
  primary:   '#0F294C',  // Azul Oscuro Colegio
  secondary: '#CDA758',  // Dorado Colegio
  success:   '#10b981',  // Verde éxito
  warning:   '#f59e0b',  // Naranja/Amarillo alerta
  danger:    '#ef4444',  // Rojo error
  gray:      '#e2e8f0'   // Gris bordes
};

// =======================
// CSRF & UTILS
// =======================
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie("csrftoken");

// =======================
// MAIN
// =======================
document.addEventListener("DOMContentLoaded", () => {

  // Elementos DOM
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  const menuLinks = document.querySelectorAll(".menu a[data-section]");
  const content = document.getElementById("content-area");
  const title = document.getElementById("topbar-title");
  const toggleBtn = document.getElementById("toggle");

  // Sidebar móvil
  if(toggleBtn){
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("show");
      });
  }

  if(overlay){
      overlay.addEventListener("click", () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
      });
  }

  // -----------------------
  // API: obtener comprobantes
  // -----------------------
  async function getComprobantes() {
    try {
      const res = await fetch("/finanzas/api/comprobantes/");
      const raw = await res.json();
      if (Array.isArray(raw)) return raw;
      if (Array.isArray(raw.comprobantes)) return raw.comprobantes;
      return [];
    } catch {
      return [];
    }
  }

  // -----------------------
  // 1. DASHBOARD (CON GRÁFICOS ESTILIZADOS)
  // -----------------------
  async function loadDashboard() {
    content.innerHTML = '<div style="text-align:center; padding:40px; color:#A3AED0;">Cargando datos...</div>';
    const data = await getComprobantes();

    const pendientes = data.filter(x => x.estado === "pendiente").length;
    const aprobados  = data.filter(x => x.estado === "validado").length;
    const rechazados = data.filter(x => x.estado === "rechazado").length;

    content.innerHTML = `
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div>
                <h2>Panel Finanzas</h2>
                <p>Visión general del estado de los pagos.</p>
            </div>
            <div style="background:#F4F7FE; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:600; color:#0F294C;">
                ${new Date().toLocaleDateString()}
            </div>
        </div>

        <div class="stat-cards-container">
          <div class="stat-card">
            <i class="fa-solid fa-clock-rotate-left" style="background:#FFF8E1; color:#F59E0B;"></i>
            <div>
                <div class="card-num">${pendientes}</div>
                <div>Pendientes</div>
            </div>
          </div>

          <div class="stat-card">
            <i class="fa-solid fa-circle-check" style="background:#E8FBF4; color:#05CD99;"></i>
            <div>
                <div class="card-num">${aprobados}</div>
                <div>Aprobados</div>
            </div>
          </div>

          <div class="stat-card">
            <i class="fa-solid fa-circle-xmark" style="background:#FEECEB; color:#EE5D50;"></i>
            <div>
                <div class="card-num">${rechazados}</div>
                <div>Rechazados</div>
            </div>
          </div>
        </div>

        <div style="margin-top:40px;">
            <h3>Comprobantes ingresados por mes</h3>
            <div style="height:300px; width:100%;">
                <canvas id="chartIngresos"></canvas>
            </div>
        </div>
      </div>
    `;

    // --- Gráfico de ingresos (Mejorado) ---
    const res2 = await fetch("/finanzas/api/comprobantes-por-mes/");
    const stats2 = await res2.json();
    
    const ctx2 = document.getElementById("chartIngresos").getContext("2d");
    if (window._chartIngresos) window._chartIngresos.destroy();

    // Configuración Chart.js ESTILO PREMIUM
    window._chartIngresos = new Chart(ctx2, {
      type: "bar",
      data: {
        labels: stats2.labels,
        datasets: [
          { 
            label: "Subidos", 
            data: stats2.subidos, 
            backgroundColor: BRAND_COLORS.primary, 
            borderRadius: 6,
            barPercentage: 0.6
          },
          { 
            label: "Del mes", 
            data: stats2.correspondientes, 
            backgroundColor: BRAND_COLORS.secondary, 
            borderRadius: 6,
            barPercentage: 0.6
          },
          { 
            label: "Atrasados", 
            data: stats2.atrasados, 
            backgroundColor: BRAND_COLORS.danger, 
            borderRadius: 6,
            barPercentage: 0.6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle' } }
        },
        scales: {
          y: { 
              beginAtZero: true, 
              grid: { drawBorder: false, borderDash: [5, 5] }, // Líneas punteadas sutiles
              ticks: { padding: 10 }
          },
          x: { 
              grid: { display: false } // Sin líneas verticales
          }
        }
      }
    });
  }

  // -----------------------
  // 2. COMPROBANTES (Render List)
  // -----------------------
  let _cacheComprobantes = [];

  function renderList(titleStr, items) {
    const sectionId = `section-${titleStr}`;
    // Determinamos color del contador
    let countColor = "#0F294C";
    if(titleStr === 'Pendientes') countColor = "#F59E0B";
    if(titleStr === 'Rechazados') countColor = "#EE5D50";

    return `
      <div class="card accordion-card">
        <div class="accordion-header" onclick="toggleAccordion('${sectionId}', this)">
          <h3>
            ${titleStr} 
            <span class="count-soft" style="color:${countColor}; background:rgba(0,0,0,0.05);">${items.length}</span>
          </h3>
          <span class="accordion-icon"><i class="fa-solid fa-chevron-down"></i></span>
        </div>
        <div id="${sectionId}" class="accordion-body">
          <div class="filters-row">
            <div class="search-box">
              <input class="search-input"
                     placeholder="Buscar alumno o RUT..."
                     oninput="filterList('${titleStr}', this.value); showSuggestions('${titleStr}', this.value)">
              <div class="suggestions" id="sug-${titleStr}"></div>
            </div>
            <select class="filter-select" onchange="applyFilters('${titleStr}')">
              <option value="">Todos los Meses</option>
              <option>Enero</option><option>Febrero</option><option>Marzo</option>
              <option>Abril</option><option>Mayo</option><option>Junio</option>
              <option>Julio</option><option>Agosto</option><option>Septiembre</option>
              <option>Octubre</option><option>Noviembre</option><option>Diciembre</option>
            </select>
            <select class="filter-select" onchange="applyFilters('${titleStr}')">
              <option value="">Todos los Cursos</option>
              <option>1° Básico</option><option>2° Básico</option><option>3° Básico</option>
              <option>4° Básico</option><option>5° Básico</option><option>6° Básico</option>
              <option>7° Básico</option><option>8° Básico</option>
              <option>1° Medio</option><option>2° Medio</option><option>3° Medio</option><option>4° Medio</option>
            </select>
          </div>

          <div class="list-table-header">
            <span>Alumno</span><span>RUT</span><span>Curso</span><span>Mes</span>
            <span>Monto</span><span>Subido</span><span>Archivo</span><span>Estado</span><span>Acción</span>
          </div>

          <div class="list-scroll" id="list-${titleStr}">
            ${
              items.length === 0
                ? "<div style='text-align:center; padding:30px; color:#A3AED0;'>No hay registros</div>"
                : items.map(c => {
                    const url       = `/finanzas/ver-comprobante/${c.id}`;
                    // Icono de archivo más bonito
                    const archivo   = c.archivo_name 
                        ? `<a href="${url}" target="_blank" style="color:#0F294C; font-size:18px;"><i class="fa-solid fa-file-pdf"></i></a>` 
                        : "—";
                    const montoFmt  = Number(c.monto).toLocaleString("es-CL");
                    const estadoBadge =
                      c.estado === "pendiente"
                        ? `<span class="badge badge-pendiente">Pendiente</span>`
                        : c.estado === "validado"
                          ? `<span class="badge badge-aprobado">Aprobado</span>`
                          : `<span class="badge badge-rechazado">Rechazado</span>`;

                    return `
                      <div class="payment-row" data-curso="${c.curso || ""}">
                        <div style="font-weight:600; color:#0F294C;">${c.alumno}</div>
                        <div style="font-family:monospace;">${c.rut}</div>
                        <div>${c.curso || "-"}</div>
                        <div>${c.mes}</div>
                        <div style="font-weight:600;">$${montoFmt}</div>
                        <div style="font-size:13px; color:#A3AED0;">${c.fecha_subida}</div>
                        <div style="text-align:center;">${archivo}</div>
                        <div>${estadoBadge}</div>
                        <div class="acciones">
                          ${
                            c.estado === "pendiente"
                              ? `
                                <button class="btn-acc approve" title="Aprobar" onclick="aprobar(${c.id}, this)">
                                  <i class="fa-solid fa-check"></i>
                                </button>
                                <button class="btn-acc reject" title="Rechazar" onclick="rechazar(${c.id}, this)">
                                  <i class="fa-solid fa-xmark"></i>
                                </button>
                                `
                              : `
                                <button class="btn-acc revert" title="Revertir" onclick="revertir(${c.id}, this)">
                                  <i class="fa-solid fa-rotate-left"></i>
                                </button>
                                `
                          }
                        </div>
                      </div>
                    `;
                  }).join("")
            }
          </div>
        </div>
      </div>
    `;
  }

  // Helper para acordeones
  function getOpenAccordions() {
    return [...document.querySelectorAll(".accordion-body.open")].map(el => el.id);
  }

  function restoreOpenAccordions(openIds) {
    openIds.forEach(id => {
      const body = document.getElementById(id);
      if (body) {
        body.classList.add("open");
        const header = body.previousElementSibling;
        if (header) {
          const icon = header.querySelector(".accordion-icon");
          if (icon) icon.classList.add("rotated");
        }
      }
    });
  }

  async function loadComprobantes() {
    const openIds = getOpenAccordions();
    content.innerHTML = '<div style="text-align:center; padding:40px; color:#A3AED0;">Cargando comprobantes...</div>';
    
    const data = await getComprobantes();

    content.innerHTML =
      renderList("Pendientes", data.filter(x => x.estado === "pendiente")) +
      renderList("Aprobados",  data.filter(x => x.estado === "validado")) +
      renderList("Rechazados", data.filter(x => x.estado === "rechazado"));

    restoreOpenAccordions(openIds);

    // Gráfico de flujo ESTILO PREMIUM
    content.insertAdjacentHTML("beforeend", `
      <div class="card" style="margin-top:30px;">
        <h3>Flujo de revisión de comprobantes</h3>
        <div style="height:300px;">
            <canvas id="chartFlujo"></canvas>
        </div>
      </div>
    `);

    const res = await fetch("/finanzas/api/estadisticas/");
    const stats = await res.json();
    const ctx = document.getElementById("chartFlujo").getContext("2d");

    if (window._chartFlujo) window._chartFlujo.destroy();

    window._chartFlujo = new Chart(ctx, {
      type: "bar",
      data: {
        labels: stats.labels,
        datasets: [
          { label: "Aprobados", data: stats.aprobados, backgroundColor: BRAND_COLORS.success, borderRadius: 4 },
          { label: "Rechazados", data: stats.rechazados, backgroundColor: BRAND_COLORS.danger, borderRadius: 4 },
          { 
            type: "line", 
            label: "Acumulado", 
            data: stats.acumulado, 
            borderColor: BRAND_COLORS.secondary, 
            borderWidth: 3, 
            tension: 0.4, // Curva suave
            pointRadius: 4,
            pointBackgroundColor: "#fff",
            pointBorderColor: BRAND_COLORS.secondary
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'top', align: 'end', labels: { usePointStyle: true } } },
        scales: {
            y: { grid: { drawBorder: false, borderDash: [5,5] } },
            x: { grid: { display: false } }
        }
      }
    });
  }

  // -----------------------
  // ACCIONES API (POST)
  // -----------------------
  async function postActionWithComment(url, comentario, btn) {
    if (btn) {
        const original = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        btn.disabled = true;
    }

    await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: new URLSearchParams({ comentario })
    });

    await loadComprobantes();
  }

  window.aprobar = (id, btn) => {
    abrirModal("Aprobar Comprobante", false, comentario => {
      postActionWithComment(`/finanzas/comprobante/${id}/aprobar/`, comentario, btn);
    });
  };

  window.rechazar = (id, btn) => {
    abrirModal("Rechazar Comprobante", true, comentario => {
      postActionWithComment(`/finanzas/comprobante/${id}/rechazar/`, comentario, btn);
    });
  };

  window.revertir = (id, btn) => {
    if (!confirm("¿Estás seguro de revertir el estado a Pendiente?")) return;
    postActionWithComment(`/finanzas/comprobante/${id}/revertir/`, "", btn);
  };

  // -----------------------
  // 3. CUOTAS PENDIENTES
  // -----------------------
  async function loadCuotasPendientes() {
    content.innerHTML = '<div style="text-align:center; padding:40px; color:#A3AED0;">Cargando cuotas...</div>';
    const res = await fetch("/finanzas/api/cuotas-pendientes/");
    const data = await res.json();
    const cuotas = data.cuotas || [];

    content.innerHTML = `
      <div class="card cuotas-card">
        <div style="margin-bottom:25px;">
             <h2>Cuotas Pendientes</h2>
             <p>Seguimiento de morosidad.</p>
        </div>

        <div class="stat-cards-container" style="margin-bottom:30px;">
          <div class="stat-card">
            <i class="fa-solid fa-receipt" style="background:#F4F7FE; color:#0F294C;"></i>
            <div>
              <div class="card-num">${cuotas.length}</div>
              <div>Cuotas Totales</div>
            </div>
          </div>

          <div class="stat-card">
            <i class="fa-solid fa-sack-dollar" style="background:#FFF8E1; color:#F59E0B;"></i>
            <div>
              <div class="card-num">
                $${cuotas.reduce((t, c) => t + c.monto, 0).toLocaleString("es-CL")}
              </div>
              <div>Deuda Total</div>
            </div>
          </div>

          <div class="stat-card">
            <i class="fa-solid fa-triangle-exclamation" style="background:#FEECEB; color:#EE5D50;"></i>
            <div>
              <div class="card-num" id="severeCount">0</div>
              <div>Morosidad Grave (+60 días)</div>
            </div>
          </div>
        </div>

        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div style="flex:1; min-width:300px; height:300px; position:relative;">
                 <h3>Distribución de Riesgo</h3>
                 <canvas id="chartRiesgo"></canvas>
            </div>
            <div style="flex:2; min-width:400px;">
                 <div class="search-box" style="margin-bottom:20px; width:100%;">
                    <input class="search-input" placeholder="Buscar alumno o RUT en cuotas..." oninput="filterCuotas(this.value)">
                 </div>
                 
                 <div class="list-table-header">
                   <span>Alumno</span><span>RUT</span><span>Concepto</span>
                   <span>Monto</span><span>Vence</span><span>Estado</span>
                 </div>

                 <div class="list-scroll" style="height:300px;">
                   ${
                     cuotas.length === 0
                       ? "<div style='padding:20px; text-align:center; opacity:0.6;'>No hay cuotas pendientes</div>"
                       : cuotas.map(c => {
                           const estadoTxt = c.status === "rejected" ? "Rechazado" : "Pendiente";
                           // Calculo básico de atraso para color
                           return `
                             <div class="payment-row cuota-item">
                               <div style="font-weight:600;">${c.alumno}</div>
                               <div style="font-family:monospace;">${c.rut}</div>
                               <div>${c.concept}</div>
                               <div>$${c.monto.toLocaleString("es-CL")}</div>
                               <div style="color:#EE5D50; font-weight:500;">${c.fecha_vencimiento}</div>
                               <div><span class="badge badge-pendiente">${estadoTxt}</span></div>
                             </div>
                           `;
                         }).join("")
                   }
                 </div>
            </div>
        </div>
      </div>
    `;

    // Gráfico de riesgo (Donut Chart Moderno)
    setTimeout(() => {
      const today = new Date();
      let verde = 0, amarillo = 0, rojo = 0;

      cuotas.forEach(c => {
        if (!c.fecha_vencimiento || c.fecha_vencimiento.trim() === "") return;
        const [dd, mm, yyyy] = c.fecha_vencimiento.split("-");
        const fecha = new Date(`${yyyy}-${mm}-${dd}`);
        const diffDays = Math.ceil((today - fecha) / (1000 * 60 * 60 * 24));

        if (diffDays <= 0) verde++;
        else if (diffDays <= 60) amarillo++;
        else rojo++;
      });

      const severeEl = document.getElementById("severeCount");
      if (severeEl) severeEl.textContent = rojo;

      const canvas = document.getElementById("chartRiesgo");
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (window._chartRiesgo) window._chartRiesgo.destroy();

      window._chartRiesgo = new Chart(ctx, {
        type: "doughnut", // Cambio a Dona (más moderno)
        data: {
          labels: ["Al día", "Atraso leve", "Morosidad grave"],
          datasets: [{
            data: [verde, amarillo, rojo],
            backgroundColor: [BRAND_COLORS.success, BRAND_COLORS.warning, BRAND_COLORS.danger],
            borderWidth: 0, // Sin bordes
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '70%', // Dona delgada
          plugins: {
            legend: { position: "right", labels: { usePointStyle: true, pointStyle: 'circle' } }
          }
        }
      });
    }, 200);
  }

  // -----------------------
  // NAVEGACIÓN SPA
  // -----------------------
  function loadSection(sec) {
    title.textContent = sec.charAt(0).toUpperCase() + sec.slice(1);
    if (sec === "dashboard")             loadDashboard();
    if (sec === "comprobantes recibidos") loadComprobantes();
    if (sec === "cuotas")                loadCuotasPendientes();
  }

  menuLinks.forEach(link => link.addEventListener("click", e => {
    e.preventDefault();
    menuLinks.forEach(l => l.classList.remove("active"));
    link.classList.add("active");
    loadSection(link.dataset.section);
  }));

  // -----------------------
  // UTILIDADES DE FILTRADO
  // -----------------------
  window.filterList = function(titleStr, value) {
    const rows = document.querySelectorAll(`#list-${titleStr} .payment-row`);
    const term = value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\./g,"").replace(/-/g,"");

    rows.forEach(row => {
      const txt = row.textContent.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/\./g,"").replace(/-/g,"");
      row.style.display = txt.includes(term) ? "grid" : "none"; // Grid para mantener layout
    });
  };

  window.applyFilters = function(titleStr) {
    const section = document.getElementById(`section-${titleStr}`);
    const search  = section.querySelector(".search-input");
    const month   = section.querySelector(".filter-select:nth-of-type(1)");
    const curso   = section.querySelector(".filter-select:nth-of-type(2)");

    const term = search.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");
    const m = month.value.toLowerCase();
    const c = curso.value.toLowerCase();

    section.querySelectorAll(".payment-row").forEach(row => {
      const cols = row.querySelectorAll("div");
      const mes      = cols[3].textContent.toLowerCase();
      const cursoRow = row.dataset.curso?.toLowerCase() || "";
      
      // Para busqueda general usamos todo el texto de la fila
      const rowText = row.textContent.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");

      const okSearch = rowText.includes(term);
      const okMonth  = !m || mes.includes(m);
      const okClass  = !c || cursoRow.includes(c);

      row.style.display = (okSearch && okMonth && okClass) ? "grid" : "none";
    });
  };

  window.filterCuotas = function(value) {
    const term = value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");
    document.querySelectorAll(".cuota-item").forEach(row => {
      const text = row.textContent.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");
      row.style.display = text.includes(term) ? "grid" : "none";
    });
  };

  window.toggleAccordion = function(id, header) {
    const body = document.getElementById(id);
    header.querySelector(".accordion-icon").classList.toggle("rotated");
    body.classList.toggle("open");
  };

  // Sugerencias (Lógica mantenida)
  window.showSuggestions = function(titleStr, value) {
    const box = document.getElementById(`sug-${titleStr}`);
    if (!value.trim()) {
      box.innerHTML = "";
      box.style.display = "none";
      return;
    }
    const term = value.toLowerCase();
    const rows = document.querySelectorAll(`#list-${titleStr} .payment-row`);
    const results = [];
    rows.forEach(r => {
      const cols = r.querySelectorAll("div");
      const name = cols[0].textContent.trim();
      const rut  = cols[1].textContent.trim();
      const n  = name.toLowerCase();
      const rr = rut.toLowerCase().replace(/\./g,"").replace(/-/g,"");
      if (n.includes(term) || rr.includes(term.replace(/\./g,"").replace(/-/g,""))) {
        results.push({ name, rut });
      }
    });
    
    // Unique logic
    const unique = [];
    const seen = new Set();
    for (const r of results) {
      if (!seen.has(r.rut)) {
        seen.add(r.rut);
        unique.push(r);
        if (unique.length >= 5) break;
      }
    }

    box.innerHTML = "";
    unique.forEach(r => {
      const d = document.createElement("div");
      d.className = "suggest-item";
      d.innerHTML = `<strong>${r.name}</strong> <span style="color:#ccc; float:right;">${r.rut}</span>`;
      d.onclick = () => selectSuggestion(titleStr, r.name);
      box.appendChild(d);
    });
    box.style.display = unique.length ? "block" : "none";
  };

  window.selectSuggestion = function(titleStr, name) {
    const input = document.querySelector(`#section-${titleStr} .search-input`);
    input.value = name;
    filterList(titleStr, name);
    const box = document.getElementById(`sug-${titleStr}`);
    box.innerHTML = "";
    box.style.display = "none";
  };

  // -----------------------
  // MODAL (Inyección HTML limpio)
  // -----------------------
  document.body.insertAdjacentHTML("beforeend", `
    <div id="modal-bg" style="position:fixed; top:0; left:0; right:0; bottom:0;
                              background:rgba(0,0,0,0.5); display:none;
                              align-items:center; justify-content:center; z-index:9999;">
      <div style="background:white; padding:30px; width:400px; border-radius:20px; font-family:'Poppins', sans-serif;">
        <h3 id="modal-title" style="margin-top:0; font-size:18px;"></h3>
        <textarea id="modal-comentario" rows="4" placeholder="Escribe un motivo..."
                  style="width:100%; padding:15px; border:1px solid #E0E5F2; border-radius:12px; margin-bottom:20px; font-family:inherit; resize:none; background:#F4F7FE;"></textarea>
        <div style="display:flex; justify-content:flex-end; gap:10px;">
          <button id="modal-cancel" style="padding:10px 20px;">Cancelar</button>
          <button id="modal-ok" style="padding:10px 20px; color:white;">Confirmar</button>
        </div>
      </div>
    </div>
  `);

  function abrirModal(titulo, obligatorio, callback) {
    document.getElementById("modal-title").textContent = titulo;
    const input = document.getElementById("modal-comentario");
    input.value = "";
    input.focus();
    document.getElementById("modal-bg").style.display = "flex";

    document.getElementById("modal-ok").onclick = () => {
      const val = input.value.trim();
      if (obligatorio && !val) {
          input.style.border = "1px solid #EE5D50"; // Rojo error
          return;
      }
      callback(val);
      cerrarModal();
    };
    document.getElementById("modal-cancel").onclick = cerrarModal;
  }

  function cerrarModal() {
    document.getElementById("modal-bg").style.display = "none";
    document.getElementById("modal-comentario").style.border = "1px solid #E0E5F2";
  }

  // Iniciar
  loadSection("dashboard");
});