// ============================
// PANEL ALUMNO - COLEGIO SAN AGUSTÍN
// ============================

console.log("ui_student.js ALUMNO con Portal de Pagos v2 cargado");

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  const content = document.getElementById("content-area");
  const menuLinks = document.querySelectorAll(".menu a[data-section]");
  const topbarTitle = document.getElementById("topbar-title");

  console.log("DOMContentLoaded - menuLinks encontrados:", menuLinks.length);

  // ============================
  // SIDEBAR
  // ============================
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      document.body.classList.toggle("menu-open");
      if (overlay) {
        overlay.style.display = sidebar.classList.contains("open") ? "block" : "none";
      }
    });
  }

  if (overlay) {
    overlay.addEventListener("click", () => {
      sidebar.classList.remove("open");
      document.body.classList.remove("menu-open");
      overlay.style.display = "none";
    });
  }

  window.addEventListener("resize", () => {
    if (window.innerWidth > 992) {
      sidebar.classList.remove("open");
      document.body.classList.remove("menu-open");
      if (overlay) overlay.style.display = "none";
    }
  });

  // ============================
  // RENDERIZADORES
  // ============================

  async function renderCalendario(container) {
    container.innerHTML = `
      <div class="card">
        <h2 class="card-title"><i class="fa-solid fa-calendar-days"></i> Calendario de Evaluaciones</h2>
        <div id="calendar" style="margin-top: 20px;"></div>
      </div>
    `;

    const calendarEl = container.querySelector("#calendar");

    let eventos = [];
    try {
      const resp = await fetch("/studentView/evaluaciones/");
      if (resp.ok) {
        eventos = await resp.json();
      }
    } catch (err) {
      console.warn("No se pudieron cargar las evaluaciones", err);
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: "dayGridMonth",
      height: "auto",
      locale: "es",
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "dayGridMonth,timeGridWeek,timeGridDay",
      },
      events: eventos,
      selectable: false,
      eventClick: function (info) {
        const extra = info.event.extendedProps || {};
        alert(
          [
            `Evaluación: ${info.event.title}`,
            extra.curso ? `Curso: ${extra.curso}` : "",
            extra.tipo ? `Tipo: ${extra.tipo}` : "",
            `Fecha: ${info.event.startStr}`,
          ]
            .filter(Boolean)
            .join("\n")
        );
      },
    });

    calendar.render();
  }

    // DASHBOARD
// ============================
//  DASHBOARD (Diseño Clean / Lista)
// ============================
async function renderDashboard(container) {
  
  // 1. Preparamos el HTML base con las tarjetas de estadísticas (sin cambios aquí)
  // Pero dejamos un placeholder para las evaluaciones
  let dashboardHtml = `
    <div class="card">
      <h2 class="card-title">Bienvenido, ${alumno.nombre}</h2>
      <p style="color: #64748b; margin-bottom: 25px;">${alumno.curso} - Panel personal de estudiante.</p>

      <div class="stat-cards-container">
        <div class="stat-card" style="--card-color: var(--color-primary);">
          <i class="fa-solid fa-book card-icon"></i>
          <div class="card-info">
            <div class="card-num" id="stat-asignaturas">...</div>
            <div class="card-label">Tus asignaturas</div>
          </div>
        </div>
        <div class="stat-card" style="--card-color: var(--color-secondary);">
          <i class="fa-solid fa-list-check card-icon"></i>
          <div class="card-info">
            <div class="card-num" id="stat-promedio">...</div>
            <div class="card-label">Promedio general</div>
          </div>
        </div>
      </div>

      <div style="margin-top: 40px;">
        <h3 style="font-size: 1.25rem; color: var(--color-primary); font-weight: 700; margin-bottom: 20px;">
            Próximas Evaluaciones
        </h3>
        
        <div id="lista-evaluaciones-clean">
            <p style="color:#999;">Cargando...</p>
        </div>
      </div>

    </div>
  `;

  container.innerHTML = dashboardHtml;

  // 2. Lógica para cargar Promedios (Igual que antes)
  try {
    const resp = await fetch("/studentView/api/promedio/");
    if (resp.ok) {
        const data = await resp.json();
        const promedio = data.promedio ?? 0;
        const cantAsignaturas = data.cantidad_asignaturas ?? 0;
        
        const nodoProm = document.getElementById("stat-promedio");
        const nodoAsig = document.getElementById("stat-asignaturas");
        if (nodoProm) nodoProm.textContent = promedio.toFixed(1);
        if (nodoAsig) nodoAsig.textContent = cantAsignaturas;
    }
  } catch (err) { console.error("Error promedio:", err); }

  // 3. LÓGICA VISUAL: LISTA DE EVALUACIONES
  try {
    const respEv = await fetch("/studentView/api/proximas-evaluaciones/");
    const divLista = document.getElementById("lista-evaluaciones-clean");
    
    if (!respEv.ok) throw new Error("Error fetching evaluaciones");
    const dataEv = await respEv.json();
    const evaluaciones = dataEv.evaluaciones || [];

    divLista.innerHTML = ""; // Limpiar carga

    if (evaluaciones.length === 0) {
        divLista.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #64748b; background: #f8fafc; border-radius: 12px;">
                <i class="fa-solid fa-mug-hot" style="margin-bottom: 8px;"></i> No tienes evaluaciones próximas.
            </div>`;
    } else {
        evaluaciones.forEach(ev => {
            // Lógica de texto para días restantes
            let diasTexto = `Faltan ${ev.dias_restantes} días`;
            let diasColor = "#64748b"; // Gris por defecto

            if (ev.dias_restantes === 0) {
                diasTexto = "¡Es hoy!";
                diasColor = "#ef4444"; // Rojo
            } else if (ev.dias_restantes === 1) {
                diasTexto = "Mañana";
                diasColor = "#f59e0b"; // Naranja
            }

            // HTML de cada fila (FLEXBOX para replicar la imagen)
            const fila = `
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: flex-start; 
                    padding: 18px 0; 
                    border-bottom: 1px solid #f1f5f9;
                ">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-weight: 600; font-size: 1rem; color: #0F294C;">
                            ${ev.tipo}
                        </span>
                        <span style="font-size: 0.85rem; color: #64748b;">
                            ${alumno.curso} — ${ev.asignatura}
                        </span>
                    </div>

                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                        <span style="font-weight: 700; font-size: 0.95rem; color: #0F294C;">
                            ${ev.fecha}
                        </span>
                        <span style="font-size: 0.8rem; font-weight: 600; color: ${diasColor};">
                            ${diasTexto}
                        </span>
                    </div>
                </div>
            `;
            divLista.innerHTML += fila;
        });
    }

  } catch (err) {
    console.error("Error cargando evaluaciones:", err);
    const divLista = document.getElementById("lista-evaluaciones-clean");
    if(divLista) divLista.innerHTML = `<p style="color:red;">No se pudieron cargar los datos.</p>`;
  }
}



  // ============================
  // MIS CLASES (Formato Horario - Tabla)
  // ============================
  function renderClases(container) {
    const nombreAlumno = alumno.nombre || "Estudiante";
    const nombreCurso = alumno.curso || "Sin curso";

    container.innerHTML = `
      <div class="card horario-card-grid">
        
        <div style="margin-bottom: 20px;">
            <h2 class="card-title-grid">
                <i class="fa-solid fa-calendar-days" style="margin-right:8px; opacity:0.8;"></i>
                Horario Semanal de ${nombreAlumno}
            </h2>
            <div class="horario-meta">
                <span class="meta-label">Horario curso:</span>
                <span class="curso-badge">${nombreCurso}</span>
            </div>
        </div>
        
        <div class="table-responsive-grid">
          <table class="horario-table-styled">
            <thead>
              <tr>
                <th class="time-header">Hora</th>
                <th>Lunes</th>
                <th>Martes</th>
                <th>Miércoles</th>
                <th>Jueves</th>
                <th>Viernes</th>
              </tr>
            </thead>
            <tbody id="clases-grid-body">
              <tr><td colspan="6" style="text-align:center; padding:30px;">Cargando horario...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;

    const tbody = container.querySelector("#clases-grid-body");
    const daysToShow = [0, 1, 2, 3, 4]; // Lunes a Viernes

    fetch("/studentView/mis-asignaturas/")
      .then((r) => r.json())
      .then((data) => {
        const asignaturas = data.asignaturas || [];

        if (!asignaturas.length) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px; color: #7f8c8d; font-style: italic;">No tienes asignaturas inscritas.</td></tr>`;
          return;
        }

        const gridData = {}; 
        const timeSlotsSet = new Set();

        asignaturas.forEach(asig => {
            if (asig.horarios) {
                asig.horarios.forEach(h => {
                    if (daysToShow.includes(h.day_of_week)) {
                        const start = h.start_time.slice(0,5);
                        const end = h.end_time.slice(0,5);
                        const timeLabel = `${start} - ${end}`;
                        
                        timeSlotsSet.add(timeLabel);

                        if (!gridData[timeLabel]) {
                            gridData[timeLabel] = {};
                        }
                        gridData[timeLabel][h.day_of_week] = {
                            subject: asig.nombre,
                            teacher: asig.profesor || "--"
                        };
                    }
                });
            }
        });
        

        const sortedTimeSlots = Array.from(timeSlotsSet).sort();

        if (sortedTimeSlots.length === 0) {
             tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px; color: #7f8c8d;">No hay horarios definidos de Lunes a Viernes.</td></tr>`;
             return;
        }

        tbody.innerHTML = "";
        
        sortedTimeSlots.forEach(timeLabel => {
            const row = document.createElement("tr");
            row.innerHTML = `<td class="time-cell-styled">${timeLabel}</td>`;
            
            daysToShow.forEach(dayIdx => {
                const cellData = gridData[timeLabel][dayIdx];
                let cellContent = '<span class="empty-cell" style="color:#eee;">-</span>';
                
                if (cellData) {
                    cellContent = `
                        <div class="subject-name">${cellData.subject}</div>
                        <div class="teacher-name">${cellData.teacher}</div>
                    `;
                }
                row.innerHTML += `<td>${cellContent}</td>`;
            });
            tbody.appendChild(row);
        });

      })
      .catch((err) => {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#e74c3c;">Error al cargar datos.</td></tr>`;
      });
}

  function renderNotas(container) {
    container.innerHTML = `
      <div class="tabla-card">
        <div class="tabla-header">
          <h2><i class="fa-solid fa-list-check"></i> Notas</h2>
          <p style="margin-top:4px;">(se excluyen Acto Cívico, Almuerzo, Orientación y Liga)</p>
        </div>

        <div class="tabla-body">
          <table class="tabla-notas">
            <thead>
              <tr>
                <th>Asignatura</th>
                <th>Nota 1</th>
                <th>Nota 2</th>
                <th>Nota 3</th>
                <th>Nota 4</th>
                <th>Nota 5</th>
                <th>Nota 6</th>
                <th>Nota 7</th>
                <th>Promedio</th>
              </tr>
            </thead>
            <tbody id="tabla-body">
              <tr><td colspan="9">Cargando...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;

    const tbody = container.querySelector("#tabla-body");

    fetch("/studentView/mis-notas/")
      .then((r) => r.json())
      .then((data) => {
        let materias = [];

        if (Array.isArray(data)) {
          materias = data;
        } else if (Array.isArray(data.notas)) {
          materias = data.notas;
        } else if (Array.isArray(data.raw)) {
          const tmp = {};
          data.raw.forEach((item) => {
            const asig = item.subject || "Sin asignatura";
            if (!tmp[asig]) tmp[asig] = [];
            tmp[asig].push({
              score: Number(item.score),
              description: item.evaluation_description || "",
              date: item.date || null,
            });
          });
          materias = Object.entries(tmp).map(([asignatura, notas]) => ({
            asignatura,
            notas,
          }));
        }

        const excluidas = [
          "acto cívico",
          "acto civico",
          "almuerzo",
          "orientación",
          "orientacion",
          "liga",
        ];

        const visibles = materias.filter((m) => {
          const nombre = (m.asignatura || "").toLowerCase();
          return !excluidas.includes(nombre);
        });

        if (!visibles.length) {
          tbody.innerHTML = `<tr><td colspan="9">No hay notas registradas.</td></tr>`;
          return;
        }

        tbody.innerHTML = "";
        visibles.forEach((m) => {
          const notas = (m.notas || []).map((n) => Number(n.score));
          const celdas = [];

          for (let i = 0; i < 7; i++) {
            celdas.push(`<td>${notas[i] ? notas[i].toFixed(1) : "--"}</td>`);
          }

          let prom = "--";
          if (notas.length) {
            const suma = notas.reduce((a, b) => a + b, 0);
            prom = (suma / notas.length).toFixed(1);
          }

          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${m.asignatura}</td>
            ${celdas.join("")}
            <td><strong>${prom}</strong></td>
          `;
          tbody.appendChild(tr);
        });
      })
      .catch((err) => {
        console.error("❌ error cargando notas", err);
        tbody.innerHTML = `<tr><td colspan="9">Error al cargar notas.</td></tr>`;
      });
  }

  async function renderPerfil(container) {
  const res = await fetch("/studentView/perfil-data/");
  const alumno = await res.json();

  container.innerHTML = `
    <div class="perfil-card">
      <div class="perfil-header">
        <div class="perfil-banner"></div>
        <div class="perfil-avatar">
          <div class="avatar-circle">${alumno.nombre.split(" ").map(p => p[0]).join("").slice(0,2).toUpperCase()}</div>
          <h2>${alumno.nombre}</h2>
          <p class="perfil-username">${alumno.username || alumno.email || "usuario"}</p>
          <p class="perfil-sub">${alumno.curso || "--"} • RUT ${alumno.rut || "--"}</p>
        </div>
      </div>

      <div class="perfil-body">
        <div class="perfil-info-box">
          <h3>Información básica</h3>
          <table>
            <tr><td>Nombre completo</td><td>${alumno.nombre}</td></tr>
            <tr><td>Curso</td><td>${alumno.curso || "--"}</td></tr>
            <tr><td>RUT</td><td>${alumno.rut || "--"}</td></tr>

          </table>
        </div>

        <div class="perfil-info-box">
          <h3>Información del apoderado</h3>
          <table>
            <tr><td>Nombre</td><td>${alumno.apoderado_nombre || "--"}</td></tr>

            <tr><td>Teléfono</td><td>${alumno.apoderado_telefono || "--"}</td></tr>
            <tr><td>Correo</td><td>${alumno.apoderado_correo || "--"}</td></tr>
          </table>
        </div>
      </div>
    </div>
  `;
}

  // ============================
  // PORTAL DE PAGOS: PIN + CUOTAS
  // ============================

  function pedirPinApoderado() {
    console.log("Mostrar modal PIN apoderado");
    const html = `
    <div class="modal-pin">
        <div class="modal-pin-box">
            <h3>Acceso al Portal de Pagos</h3>
            <p>Ingrese el PIN del apoderado para continuar:</p>

            <input type="password" id="pin-input" class="modal-pin-input" placeholder="PIN de apoderado">

            <button id="btn-validar-pin" class="modal-pin-btn confirm">
                Validar
            </button>

            <button id="btn-cancel-pin" class="modal-pin-btn cancel">
                Cancelar
            </button>

            <div id="pin-error" style="display:none; color:#ff5252; margin-top:8px;"></div>
        </div>
    </div>`;

    document.body.insertAdjacentHTML("beforeend", html);

    const btnValidar = document.getElementById("btn-validar-pin");
    const btnCancel = document.getElementById("btn-cancel-pin");

    if (btnValidar) btnValidar.onclick = validarPin;
    if (btnCancel) btnCancel.onclick = () => {
      const modal = document.querySelector(".modal-pin");
      if (modal) modal.remove();
      loadSection("dashboard");
    };
  }

  // VALIDAR PIN APODERADO
  async function validarPin() {
    const input = document.getElementById("pin-input");
    const errorBox = document.getElementById("pin-error");

    if (!input) return;
    const pin = input.value;

    if (!pin) {
      if (errorBox) {
        errorBox.textContent = "Ingrese un PIN";
        errorBox.style.display = "block";
      }
      return;
    }

    let formData = new FormData();
    formData.append("pin", pin);

    const csrftoken = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1];

    console.log("Enviando PIN al backend...");

    const resp = await fetch("/studentView/validar-pin/", {
      method: "POST",
      headers: { "X-CSRFToken": csrftoken },
      body: formData,
    });

    const data = await resp.json();
    console.log("Respuesta validar_pin:", data);

    if (data.success) {
      sessionStorage.setItem("pagos_autorizado", "1");
      
      // 1. Quitar el Modal del PIN
      const modal = document.querySelector(".modal-pin");
      if (modal) modal.remove();

      // ====================================================
      // ===CERRAR SIDEBAR MÓVIL AUTOMÁTICAMENTE ===
      // ====================================================
      if (window.innerWidth <= 992) {
          const sidebar = document.getElementById("sidebar");
          const overlay = document.getElementById("overlay");
          
          // Quitamos la clase 'open' para que se esconda
          if(sidebar) sidebar.classList.remove("open");
          
          // Quitamos el bloqueo del body
          document.body.classList.remove("menu-open");
          
          // Escondemos el fondo oscuro
          if(overlay) overlay.style.display = "none";
      }
      // ====================================================

      // 2. Marcar menú activo
      const menuLinks = document.querySelectorAll(".menu a[data-section]");
      menuLinks.forEach((a) => a.classList.remove("active"));
      const pagosMenu = document.querySelector('.menu a[data-section="pagos"]');
      if (pagosMenu) pagosMenu.classList.add("active");

      // 3. Cargar la sección
      loadSection("pagos");

    } else {
      if (errorBox) {
        errorBox.textContent = data.message || "PIN incorrecto";
        errorBox.style.display = "block";
      }
    }
  }

async function cargarPortalPagos() {
  console.log("cargarPortalPagos() llamado");

  const resp = await fetch("/studentView/obtener-pagos/");
  const data = await resp.json();

  console.log("Datos obtener_pagos:", data);

  // ─────────────────────────────────────────────
  // VALIDACIONES DE ERROR
  // ─────────────────────────────────────────────
  if (data.error) {
    if (data.error.includes("Acceso no autorizado")) {
      sessionStorage.removeItem("pagos_autorizado");
      pedirPinApoderado();
      return;
    }

    content.innerHTML = `<div class="card error-card">${data.error}</div>`;
    return;
  }

  // ─────────────────────────────────────────────
  // VARIABLES PRINCIPALES
  // ─────────────────────────────────────────────
  const apoderado = data.apoderado || "Apoderado";
  const alumnoNombre = data.alumno || "Alumno";
  const pagos = data.pagos || [];

  const pagadas = pagos.filter((p) => p.status === "paid").length;
  const total = pagos.length || 1;
  const porcentaje = Math.round((pagadas / total) * 100);

  // ─────────────────────────────────────────────
  // ENCABEZADO DEL PORTAL
  // ─────────────────────────────────────────────
  let html = `
    <div class="pagos-top">
        <h2>Portal de Pagos</h2>
        <p class="sub">Bienvenid@ <strong>${apoderado}</strong></p>
        <p class="sub" style="margin-top:-8px;">Alumno: <strong>${alumnoNombre}</strong></p>

        <div class="barra-progreso">
            <div class="progreso" style="width:${porcentaje}%"></div>
        </div>
        <p class="tiny">${pagadas} cuotas pagadas de ${total} (${porcentaje}%)</p>
    </div>

    <div class="tarjetas-pagos">
  `;

  // ─────────────────────────────────────────────
  // TARJETAS DE PAGOS
  // ─────────────────────────────────────────────
  pagos.forEach((p) => {
    let estadoClase, estadoTxt, accion;

    if (p.status === "paid") {
      estadoClase = "ok";
      estadoTxt = "Pagado";
      accion = `<span class="ic-check">✔</span>`;

    } else if (p.status === "pending_review") {
      estadoClase = "review";
      estadoTxt = "En revisión";
      accion = `
        <button class="btn-pay-card" disabled style="background:#b5b5b5; cursor:not-allowed;">
            📄 En revisión
        </button>
      `;

    } else if (p.status === "rejected") {
      estadoClase = "rejected";
      estadoTxt = "Rechazado";
      accion = `
        <button class="btn-pay-card"
            onclick="iniciarPagoGetnet(${p.id})"
            style="background:var(--color-secondary); border:1px solid #c8a256;">
             Reintentar con Getnet
        </button>
      `;

    } else {
      estadoClase = "pend";
      estadoTxt = "Pendiente";
      accion = `
        <button class="btn-pay-card" onclick="iniciarPagoGetnet(${p.id})">
             Pagar
        </button>
      `;
    }

    // CARD
    html += `
      <div class="pago-card ${estadoClase}">
          <div class="pc-mes">${p.concept}</div>
          <div class="pc-det">
              <span>${p.due_date}</span>
              <span class="pc-monto">$${p.amount.toLocaleString()}</span>
          </div>
          <div class="pc-footer">
              <span class="badge-${estadoClase}">${estadoTxt}</span>
              ${accion}
          </div>
      </div>
    `;
  });

  // ─────────────────────────────────────────────
  // BOTÓN CERRAR ACCESO
  // ─────────────────────────────────────────────
  html += `
    </div>
    <button id="cerrar-accesso" class="btn-cerrar-elegante">
      Cerrar acceso apoderado
    </button>
  `;

    content.innerHTML = html;

    const btnCerrar = document.getElementById("cerrar-accesso");
    if (btnCerrar) {
      btnCerrar.onclick = () => {
        sessionStorage.removeItem("pagos_autorizado");
        fetch("/studentView/close-pin/");
        const dashLink = document.querySelector('.menu a[data-section="dashboard"]');
        if (dashLink) dashLink.click();
        else loadSection("dashboard");
      };
    }
  
}





// ===========================
// FUNCIONES DE UTILIDAD
// ===========================

// 1. UTILIDAD: Necesaria para obtener el token CSRF para peticiones POST
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Implementación simple de toast/notificación para feedback
function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 1000;
            display: flex; flex-direction: column; gap: 10px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    let bgColor;
    if (type === 'success') bgColor = '#4CAF50';
    else if (type === 'error') bgColor = '#F44336';
    else bgColor = '#2196F3'; // info
    
    toast.style.cssText = `
        background-color: ${bgColor}; color: white; padding: 15px; border-radius: 5px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); opacity: 0; transition: opacity 0.5s, transform 0.5s;
        transform: translateY(-20px); min-width: 250px; font-weight: 500; cursor: pointer;
    `;
    
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);

    const timeoutId = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 500);
    }, duration);
    
    toast.onclick = () => {
        clearTimeout(timeoutId);
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 500);
    };
}


window.iniciarPagoGetnet = async function(paymentId) {
    console.log(`Iniciando pago Getnet para Payment ID: ${paymentId}`);

    alert("Iniciando conexión con Getnet...");

    try {
        const csrftoken = getCookie('csrftoken');
        
        // Llama a la vista de Django que inicia la transacción en Getnet
        const url = `/studentView/iniciar-pago/${paymentId}/`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken 
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (response.ok && data.success) {
            alert("Redirigiendo a la pasarela de pagos...");
            
            // Redirigir al usuario a la URL de Getnet
            window.location.href = data.redirect_url;
            
        } else {
            const errorMsg = data.error || "Error desconocido al preparar el pago.";
            alert(`Error: ${errorMsg}`);
            console.error("Error al iniciar pago con Getnet:", errorMsg);
        }

    } catch (e) {
        alert("Error de red o conexión al servidor.");
        console.error("Error en iniciarPagoGetnet:", e);
    }
};
  // ============================
  // NAVEGACIÓN (ESTÁNDAR: SIDEBAR SIEMPRE VISIBLE EN PC)
  // ============================
  function loadSection(section) {
    console.log("loadSection:", section);
    
    // 1. Actualizar Título
    if(topbarTitle) {
        topbarTitle.textContent = section.charAt(0).toUpperCase() + section.slice(1).replace("-", " ");
    }

    // 2. Mostrar Spinner de Carga
    content.innerHTML = "<div class='card'>Cargando...</div>";

    // 3. RESTAURAR VISTA ESTÁNDAR EN ESCRITORIO
    // Nos aseguramos de que el sidebar esté abierto y el margen correcto en TODAS las secciones
    const sidebar = document.getElementById("sidebar");
    const main = document.querySelector(".main");
    const toggleBtn = document.getElementById("toggle");

    if (window.innerWidth > 992) {
        if (sidebar) sidebar.classList.remove("closed"); // Asegurar sidebar abierto
        if (main) main.style.marginLeft = "var(--sidebar-width)"; // Asegurar margen
        if (toggleBtn) toggleBtn.style.display = ""; // Ocultar botón toggle (lo maneja el CSS)
    }

    // 4. Renderizar el Contenido
    switch (section) {
      case "dashboard":
        renderDashboard(content);
        break;
      case "mis-clases":
        renderClases(content);
        break;
      case "tareas":
      case "mis-notas":
        renderNotas(content);
        break;
      case "calendario":
        renderCalendario(content);
        break;
      case "perfil":
        renderPerfil(content);
        break;
      case "pagos":
        cargarPortalPagos();
        break;
      default:
        content.innerHTML = `<div class="card">Sección "${section}" no implementada aún.</div>`;
        break;
    }
  }

  // LISTENER DE MENÚ
  menuLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const section = link.getAttribute("data-section");
      
      // Validación PIN para pagos
      if (section === "pagos") {
        if (sessionStorage.getItem("pagos_autorizado") === "1") {
          actualizarMenuActivo(link);
          loadSection("pagos");
        } else {
          pedirPinApoderado();
        }
        return;
      }

      actualizarMenuActivo(link);
      loadSection(section);

      // Cerrar menú móvil al hacer click
      if (window.innerWidth <= 992 && sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
        document.body.classList.remove("menu-open");
        if (overlay) overlay.style.display = "none";
      }
    });
  });
  

  function actualizarMenuActivo(linkActivo) {
      menuLinks.forEach((l) => l.classList.remove("active"));
      linkActivo.classList.add("active");
  }

  // Carga inicial
  loadSection("dashboard");
});


