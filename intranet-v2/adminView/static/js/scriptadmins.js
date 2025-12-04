document.addEventListener("DOMContentLoaded", () => {
  // ==============================
  // PANEL ADMIN - SPA INTERACTIVA
  // ==============================

  // --- Referencias del DOM ---
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('toggle');
  const overlay = document.getElementById('sidebar-overlay');
  const mainContent = document.getElementById('main-content');
  const title = document.getElementById('topbar-title');

  // ==========================================
  // Helper para obtener el token CSRF
  // ==========================================
  function getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        return cookie.substring(name.length + 1);
      }
    }
    return null;
  }

  // ==========================================
  // Funciones básicas
  // ==========================================
  function isMobile() {
    return window.innerWidth <= 768;
  }
  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('open');
    overlay?.classList.add('show');
    document.body.classList.add('no-scroll');
  }
  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    overlay?.classList.remove('show');
    document.body.classList.remove('no-scroll');
  }

  // --- Botón toggle y overlay ---
  toggleBtn?.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });
  overlay?.addEventListener('click', closeSidebar);
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });

  // --- Resaltar item activo ---
  function clearActive() {
    document.querySelectorAll('.menu a, .menu summary').forEach(el => el.classList.remove('active'));
  }
  const links = document.querySelectorAll('.menu a[data-section]');
  const summaries = document.querySelectorAll('.menu summary');
  summaries.forEach(summary => {
    summary.addEventListener('click', () => {
      setTimeout(() => {
        clearActive();
        if (summary.parentElement.open) summary.classList.add('active');
      }, 0);
    });
  });

// ======================================================
//  Ver Cursos (ORGANIZADO POR NIVELES) + BOTÓN BORRAR
// ======================================================
async function cargarVerCursos() {
  title.textContent = "Listado de Cursos";
  mainContent.innerHTML = `<div class="card"><p>Cargando cursos...</p></div>`;

  try {
    const response = await fetch("/adminview/api/cursos/");
    if (!response.ok) throw new Error("Error al obtener los cursos");
    const data = await response.json();

    // 1. Clasificar los cursos por nombre
    const preBasica = [];
    const basica = [];
    const media = [];

    (data.cursos || []).forEach(c => {
      const nombre = (c.curso || "").toLowerCase();

      if (nombre.includes("medio")) {
        media.push(c);
      } else if (nombre.includes("básico") || nombre.includes("basico") || /\d/.test(nombre)) {
        if (nombre.includes("kínder") || nombre.includes("kinder") || nombre.includes("play")) {
          preBasica.push(c);
        } else {
          basica.push(c);
        }
      } else {
        preBasica.push(c);
      }
    });

    // 2. Función auxiliar para generar el HTML de una lista de tarjetas
// 2. Función auxiliar para generar el HTML de una lista de tarjetas
// 2. Función auxiliar para generar el HTML de una lista de tarjetas
const renderGrid = (listaCursos) => {
  if (listaCursos.length === 0) {
    return `<p style="color:#999; font-style:italic;">No hay cursos en este nivel.</p>`;
  }

  return (
    `<div class="cursos-grid">` +
    listaCursos
      .map((c) => {
        const cantidad = c.alumnos ? c.alumnos.length : 0;
        return `
        <details class="curso-card">
          <summary class="curso-header">
            <div class="curso-titulo">
              <i class="fa-solid fa-graduation-cap"></i>
              <span>${c.curso}</span>
            </div>
            <span class="curso-badge">${cantidad} Alumnos</span>
          </summary>
          
          <div class="curso-body">
            ${
              cantidad > 0
                ? `
              <table class="tabla-generica">
                <thead>
                  <tr>
                    <th>Alumno</th>
                    <th>RUT</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  ${(c.alumnos || [])
                    .map(
                      (a) => `
                      <tr data-alumno-rut="${a.rut || ""}" data-alumno-id="${a.id || ""}">
                        <td style="font-weight:500">${a.nombre}</td>
                        <td style="color:#666">${a.rut}</td>
                        <td>
                          <button type="button" class="btn-borrar-alumno">
                            Borrar
                          </button>
                        </td>
                      </tr>
                    `
                    )
                    .join("")}
                </tbody>
              </table>
            `
                : `<p style="padding:15px; text-align:center; color:#888;">Sin alumnos.</p>`
            }
          </div>
        </details>
      `;
      })
      .join("") +
    `</div>`
  );
};



    // 3. Construir el HTML Final
    let html = ``;

    if (preBasica.length > 0) {
      html += `
        <div class="periodo-section">
          <h3 class="periodo-title">Pre-Escolar</h3>
          ${renderGrid(preBasica)}
        </div>`;
    }

    if (basica.length > 0) {
      html += `
        <div class="periodo-section">
          <h3 class="periodo-title">Enseñanza Básica</h3>
          ${renderGrid(basica)}
        </div>`;
    }

    if (media.length > 0) {
      html += `
        <div class="periodo-section">
          <h3 class="periodo-title">Enseñanza Media</h3>
          ${renderGrid(media)}
        </div>`;
    }

    if (html === ``) {
      html = `<div class="card"><p>No se encontraron cursos.</p></div>`;
    }

    mainContent.innerHTML = html;
  } catch (error) {
    console.error("Error:", error);
    mainContent.innerHTML = `<div class="error-msg">Error al cargar los cursos.</div>`;
  }
}

  // ======================================================
  //  Profesores
  // ======================================================
async function cargarProfesores() {
  try {
    const response = await fetch("/adminview/api/profesores/");
    if (!response.ok) throw new Error("Error al obtener los profesores");

    const data = await response.json();

    let html = `
      <div class="profesores-lista">
        <div class="profesores-header">
          <h2>Listado de Profesores</h2>
          <button id="btn-nuevo-profesor" class="btn-nuevo">+</button>
        </div>
        <table class="tabla-profesores">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Asignatura(s)</th>
              <th>Correo</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
    `;

    data.profesores.forEach(p => {
      const nombreCompleto = `${p.first_name} ${p.last_name}`.trim();

      html += `
        <tr data-id="${p.id}">
          <td>
            <input type="text" name="first_name" value="${nombreCompleto}" disabled>
          </td>
          <td>
            <input type="text" name="asignaturas" value="${p.asignaturas || ""}" disabled>
          </td>
          <td>
            <input type="text" name="email" value="${p.email || ""}" disabled>
          </td>
          <td>
            <div class="acciones">
              <button class="btn-carga-horaria">Carga horaria</button>
              <button class="btn-editar">Editar</button>
              <button class="btn-guardar" disabled>Guardar</button>
              <button class="btn-eliminar">Eliminar</button>
            </div>
          </td>
        </tr>`;
    });

    html += `
          </tbody>
        </table>
      </div>`;

    mainContent.innerHTML = html;
    title.textContent = "Profesores";

    // =====================================================
    //  Botón "Nuevo profesor"
    // =====================================================
    document.getElementById("btn-nuevo-profesor")?.addEventListener("click", () => {
      title.textContent = "Agregar Profesor";
      mainContent.innerHTML = `
        <div class="formulario-profesor">
          <div class="form-top">
            <h2>Registrar Profesor</h2>
            <button id="volver-profesores" class="btn-volver">← Volver</button>
          </div>
          <form id="form-profesor">
            <label>RUT:</label>
            <input type="text" name="rut" required autocomplete="off">

            <label>Nombre:</label>
            <input type="text" name="first_name" required autocomplete="off">

            <label>Apellido:</label>
            <input type="text" name="last_name" required autocomplete="off">

            <label>Correo electrónico:</label>
            <input type="email" name="email" required autocomplete="off">

            <!-- 🔹 Primero elegir curso (desde BD) -->
            <label>Curso asignado:</label>
            <select name="curso_id" id="select-curso" required>
              <option value="">Cargando cursos...</option>
            </select>

            <label>Año:</label>
            <input type="number" name="year" id="input-year" value="2025" required>

            <!-- 🔹 Luego elegir asignatura del curso (desde BD) -->
            <label>Asignatura:</label>
            <select name="asignatura" id="select-asignatura" required>
              <option value="">Selecciona primero un curso...</option>
            </select>

            <label>Título:</label>
            <input type="text" name="title" autocomplete="off">

            <label>¿Es jefe de curso?</label>
            <select name="is_head_teacher">
              <option value="false">No</option>
              <option value="true">Sí</option>
            </select>

            <div class="form-actions">
              <button type="submit" class="btn-guardar">Registrar Profesor</button>
            </div>
          </form>
        </div>`;

      const btnVolver = document.getElementById("volver-profesores");
      const form = document.getElementById("form-profesor");
      const selectCurso = document.getElementById("select-curso");
      const selectAsignatura = document.getElementById("select-asignatura");
      const inputYear = document.getElementById("input-year");
      aplicarFormatoRutInput(document.querySelector('input[name="rut"]'));

      // Volver al listado
      btnVolver?.addEventListener("click", async () => {
        await cargarProfesores();
      });

      // =====================================================
      // 1) Cargar cursos desde la BD
      //    Endpoint esperado: /adminview/api/cursos-simple/
      //    Respuesta: { cursos: [ { "curso_id": "1", "curso_nombre": "1° Básico A", "year": 2025 }, ... ] }
      // =====================================================
      (async function poblarCursos() {
        try {
          const resp = await fetch("/adminview/api/cursos-simple/");
          if (!resp.ok) throw new Error("Error al obtener cursos");

          const data = await resp.json();
          const cursos = data.cursos || [];

          if (!cursos.length) {
            selectCurso.innerHTML = `<option value="">No hay cursos configurados</option>`;
            return;
          }

          selectCurso.innerHTML = `<option value="">Seleccionar curso...</option>`;
          cursos.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.curso_id; // esto se manda como "curso_id" al backend
            opt.textContent = `${c.curso_nombre} (${c.year})`;
            opt.dataset.year = c.year;
            selectCurso.appendChild(opt);
          });
        } catch (err) {
          console.error("Error al cargar cursos:", err);
          selectCurso.innerHTML = `<option value="">Error al cargar cursos</option>`;
        }
      })();

      // =====================================================
      // 2) Cuando el usuario elige un curso -> cargar asignaturas de ese curso
      //    Endpoint esperado: /adminview/api/asignaturas/por-curso/?curso_id=XX&year=YYYY
      //    Respuesta: { asignaturas: [ { "name": "Lenguaje" }, ... ] }
      // =====================================================
      selectCurso.addEventListener("change", async () => {
        const cursoId = selectCurso.value;
        const year = inputYear.value || new Date().getFullYear();

        if (!cursoId) {
          selectAsignatura.innerHTML = `<option value="">Selecciona primero un curso...</option>`;
          return;
        }

        try {
          const url = `/adminview/api/asignaturas/por-curso/?curso_id=${encodeURIComponent(
            cursoId
          )}&year=${encodeURIComponent(year)}`;

          const resp = await fetch(url);
          if (!resp.ok) throw new Error("Error al obtener asignaturas");

          const data = await resp.json();
          const asignaturas = data.asignaturas || [];

          if (!asignaturas.length) {
            selectAsignatura.innerHTML = `
              <option value="">
                No hay asignaturas registradas para este curso (${year})
              </option>`;
            return;
          }

          selectAsignatura.innerHTML = `<option value="">Seleccionar asignatura...</option>`;
          asignaturas.forEach(a => {
            const opt = document.createElement("option");
            opt.value = a.name;        // se envía como "asignatura" al backend
            opt.textContent = a.name;
            selectAsignatura.appendChild(opt);
          });
        } catch (err) {
          console.error("Error al cargar asignaturas:", err);
          selectAsignatura.innerHTML = `<option value="">Error al cargar asignaturas</option>`;
        }
      });

      // =====================================================
      // 3) Enviar formulario (usa los valores seleccionados)
      // =====================================================
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = Object.fromEntries(new FormData(form).entries());
        formData.role = "teacher";

        try {
          const response = await fetch("/adminview/api/profesores/crear/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify(formData),
          });

          const result = await response.json();
          if (response.ok) {
            alert(result.message || "✅ Profesor registrado correctamente.");
            await cargarProfesores();
          } else {
            alert("⚠️ Error: " + (result.error || "No se pudo registrar el profesor."));
          }
        } catch (error) {
          console.error("Error:", error);
          alert("❌ No se pudo conectar con el servidor.");
        }
      });
    });

  } catch (error) {
    console.error("Error al cargar profesores", error);
    mainContent.innerHTML = `
      <div class="error-msg">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Error al cargar los profesores
      </div>`;
  }
}


// ======================================================
//  Formulario: Carga horaria -> seleccionar curso y ramo
// ======================================================
async function cargarFormularioCargaHoraria(profesorId, nombreProfesor) {
  title.textContent = `Carga horaria de ${nombreProfesor}`;

  mainContent.innerHTML = `
    <div class="formulario-carga-horaria">
      <div class="form-top">
        <h2>Asignar carga horaria</h2>
        <button id="volver-profesores" class="btn-volver">← Volver</button>
      </div>

      <p style="margin-bottom: 1rem;">
        Profesor seleccionado: <strong>${nombreProfesor}</strong>
      </p>

      <form id="form-carga-horaria">
        <label>Curso:</label>
        <select name="curso_id" id="select-curso-horario" required>
          <option value="">Cargando cursos...</option>
        </select>

        <label>Ramo / Asignatura:</label>
        <select name="asignatura" id="select-ramo-horario" required>
          <option value="">Selecciona primero un curso...</option>
        </select>

        <div class="form-actions">
          <button type="submit" class="btn-guardar">Guardar carga horaria</button>
        </div>
      </form>
    </div>
  `;

  const btnVolver   = document.getElementById("volver-profesores");
  const selectCurso = document.getElementById("select-curso-horario");
  const selectRamo  = document.getElementById("select-ramo-horario");
  const form        = document.getElementById("form-carga-horaria");

  // Volver al listado de profesores
  btnVolver?.addEventListener("click", async () => {
    await cargarProfesores();
  });

  // ==========================================
  // 1) Poblar cursos (misma lógica que crear profe)
  // ==========================================
  (async function poblarCursosParaHorario() {
    try {
      const resp = await fetch("/adminview/api/cursos-simple/");
      if (!resp.ok) throw new Error("Error al obtener cursos");

      const data = await resp.json();
      const cursos = data.cursos || [];

      if (!cursos.length) {
        selectCurso.innerHTML = `<option value="">No hay cursos configurados</option>`;
        return;
      }

      selectCurso.innerHTML = `<option value="">Seleccionar curso...</option>`;

      cursos.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.curso_id; // se enviará como curso_id
        opt.textContent = `${c.curso_nombre} (${c.year})`;
        opt.dataset.year = c.year; // guardamos year en el option
        selectCurso.appendChild(opt);
      });
    } catch (err) {
      console.error("Error al cargar cursos (carga horaria):", err);
      selectCurso.innerHTML = `<option value="">Error al cargar cursos</option>`;
    }
  })();

  // ==========================================
  // 2) Cuando el usuario elige un curso -> cargar ramos
  // ==========================================
  selectCurso.addEventListener("change", async () => {
    const optionSel = selectCurso.options[selectCurso.selectedIndex];
    const cursoId   = optionSel?.value;
    const year      = optionSel?.dataset.year || new Date().getFullYear();

    if (!cursoId) {
      selectRamo.innerHTML = `<option value="">Selecciona primero un curso...</option>`;
      return;
    }

    try {
      const url = `/adminview/api/asignaturas/por-curso/?curso_id=${encodeURIComponent(
        cursoId
      )}&year=${encodeURIComponent(year)}`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error("Error al obtener asignaturas");

      const data = await resp.json();
      const asignaturas = data.asignaturas || [];

      if (!asignaturas.length) {
        selectRamo.innerHTML = `<option value="">No hay ramos para este curso (${year})</option>`;
        return;
      }

      selectRamo.innerHTML = `<option value="">Seleccionar ramo...</option>`;
      asignaturas.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a.name;
        opt.textContent = a.name;
        selectRamo.appendChild(opt);
      });
    } catch (err) {
      console.error("Error al cargar ramos (carga horaria):", err);
      selectRamo.innerHTML = `<option value="">Error al cargar ramos</option>`;
    }
  });

  // ==========================================
  // 3) Enviar formulario → solo profesor_id, curso_id y asignatura
  // ==========================================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const cursoId    = selectCurso.value;
    const asignatura = selectRamo.value;

    if (!cursoId || !asignatura) {
      alert("Debes seleccionar curso y ramo.");
      return;
    }

    const payload = {
      profesor_id: profesorId,
      curso_id: cursoId,
      asignatura: asignatura,
    };

    console.log("Payload carga horaria:", payload);

    try {
      const resp = await fetch("/adminview/api/carga-horaria/agregar/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify(payload),
      });

      const result = await resp.json();

      if (resp.ok) {
        alert(result.message || "✅ Carga horaria registrada.");
        await cargarProfesores(); // volver al listado
      } else {
        alert("⚠️ Error: " + (result.error || "No se pudo guardar la carga horaria."));
      }
    } catch (error) {
      console.error("Error al guardar carga horaria:", error);
      alert("❌ No se pudo conectar con el servidor.");
    }
  });
}





// ======================================================
// 🎯 Delegación de eventos (Editar / Guardar / Eliminar / Borrar alumno / Carga horaria)
// ======================================================
mainContent.addEventListener("click", async (e) => {
  // Asegurarnos de capturar el botón aunque hagan click en un <span> o icono dentro
  const btn = e.target.closest("button");
  if (!btn) return;

  const row = btn.closest("tr");

  // Solo reaccionamos a estos botones
  if (
    !btn.classList.contains("btn-editar") &&
    !btn.classList.contains("btn-guardar") &&
    !btn.classList.contains("btn-eliminar") &&
    !btn.classList.contains("btn-borrar-alumno") &&   // alumnos (cursos)
    !btn.classList.contains("btn-carga-horaria")      // 👈 NUEVO
  ) {
    return;
  }

  if (!row) return;

  // ============================
  // 🆕 CARGA HORARIA PROFESOR
  // ============================
  if (btn.classList.contains("btn-carga-horaria")) {
    const profesorId = row.dataset.id;
    const nombre = row.querySelector('input[name="first_name"]')?.value || "Profesor";

    if (!profesorId) {
      alert("No se pudo identificar al profesor.");
      return;
    }

    await cargarFormularioCargaHoraria(profesorId, nombre);
    return;
  }

  // ============================
  // 🧽 BORRAR ALUMNO (cursos)
  // ============================
  if (btn.classList.contains("btn-borrar-alumno")) {
    const alumnoId = row.dataset.alumnoId;              // <tr data-alumno-id="123">
    const nombre = row.querySelector("td")?.textContent || "Alumno";

    if (!alumnoId) {
      alert("No se pudo identificar al alumno.");
      return;
    }

    if (!confirm(`¿Seguro que deseas borrar al alumno "${nombre}"?`)) {
      return;
    }

    try {
      const resp = await fetch(`/adminview/api/alumnos/${alumnoId}/eliminar/`, {
        method: "DELETE",
        headers: {
          "X-CSRFToken": getCSRFToken(),
        },
      });

      const result = await resp.json();

      if (resp.ok) {
        // Quitar la fila de la tabla
        row.remove();

        // Actualizar badge de cantidad de alumnos en la tarjeta del curso
        const card = row.closest("details.curso-card");
        const badge = card?.querySelector(".curso-badge");
        if (badge) {
          const match = badge.textContent.match(/\d+/);
          if (match) {
            const nuevo = Math.max(parseInt(match[0], 10) - 1, 0);
            badge.textContent = `${nuevo} Alumnos`;
          }
        }

        alert(result.message || "✅ Alumno eliminado correctamente.");
      } else {
        alert("⚠️ Error: " + (result.error || "No se pudo eliminar el alumno."));
      }
    } catch (error) {
      console.error("Error al eliminar alumno:", error);
      alert("❌ No se pudo conectar con el servidor.");
    }
    return; // importante para no seguir a los otros casos
  }

  // ============================
  // 🧑‍🏫 LÓGICA EXISTENTE PROFESORES
  // ============================

  // --- EDITAR ---
  if (btn.classList.contains("btn-editar")) {
    const inputs = row.querySelectorAll("input");
    inputs.forEach((i) => {
      // 👇 No permitimos editar las asignaturas desde aquí (solo nombre y correo)
      if (i.name !== "asignaturas") {
        i.disabled = false;
      }
    });
    row.querySelector(".btn-guardar").disabled = false;
    row.classList.add("editando");
    return;
  }

  // --- GUARDAR ---
  if (btn.classList.contains("btn-guardar")) {
    const id = row.dataset.id;

    const inputNombre = row.querySelector('input[name="first_name"]');
    const inputEmail = row.querySelector('input[name="email"]');

    const data = {
      // El backend espera "first_name" con el NOMBRE COMPLETO, y él se encarga de separar
      first_name: inputNombre ? inputNombre.value.trim() : "",
      email: inputEmail ? inputEmail.value.trim() : "",
    };

    try {
      const response = await fetch(`/adminview/api/profesores/${id}/actualizar/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();
      if (response.ok) {
        btn.textContent = "✅ Guardado";
        row.classList.remove("editando");

        // Volver a bloquear inputs
        row.querySelectorAll("input").forEach((i) => (i.disabled = true));
        setTimeout(() => {
          btn.textContent = "Guardar";
          btn.disabled = true;
        }, 1500);
      } else {
        alert(" Error: " + (result.error || "No se pudo actualizar."));
      }
    } catch (error) {
      console.error("Error al actualizar:", error);
      alert(" No se pudo conectar con el servidor.");
    }
    return;
  }

  // --- ELIMINAR PROFESOR ---
  if (btn.classList.contains("btn-eliminar")) {
    const id = row.dataset.id;
    const nombre = row.querySelector('input[name="first_name"]')?.value || "Profesor";

    if (!confirm(`¿Seguro que deseas eliminar al profesor "${nombre}"?`)) return;

    try {
      const response = await fetch(`/adminview/api/profesores/${id}/eliminar/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCSRFToken() },
      });

      const result = await response.json();
      if (response.ok) {
        row.remove();
        alert(` Profesor "${nombre}" eliminado correctamente.`);
      } else {
        // 👇 AQUÍ estaba el error: faltaba un paréntesis al final
        alert(" Error: " + (result.error || "No se pudo eliminar."));
      }
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert(" No se pudo conectar con el servidor.");
    }
    return;
  }
});




// ======================================================
// 🔹 Función para aplicar formato RUT automático
// ======================================================
function aplicarFormatoRutInput(inputElement) {
    if (!inputElement) return;

    inputElement.addEventListener('input', function(e) {
        let valor = e.target.value;
        // Eliminar todo lo que no sea número o K
        valor = valor.replace(/[^0-9kK]/g, "");
        if (valor.length > 9) valor = valor.slice(0, 9);

        if (valor.length > 1) {
            const cuerpo = valor.slice(0, -1);
            const dv = valor.slice(-1).toUpperCase();
            const cuerpoFormateado = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
            e.target.value = `${cuerpoFormateado}-${dv}`;
        } else {
            e.target.value = valor;
        }
    });
}
  // ======================================================
  // 🔹 Agregar Alumno
  // ======================================================
  async function cargarAgregarAlumno() {
    title.textContent = "Agregar Alumno";

    mainContent.innerHTML = `
      <div class="formulario-alumno">
        <div class="form-top">
          <h2>Registro de Alumno</h2>
          <button id="volver-cursos" class="btn-volver">← Volver</button>
        </div>

        <form id="form-alumno" class="form-alumno">
          <div class="form-section">
            <h3>Datos del Alumno</h3>

            <label>RUT:</label>
            <input type="text" name="rut" placeholder="Ej: 21.345.678-9" required autocomplete="off">

            <label>Nombres:</label>
            <input type="text" name="nombres" required autocomplete="off">

            <label>Apellidos:</label>
            <input type="text" name="apellidos" required autocomplete="off">

            <label>Fecha de Nacimiento:</label>
            <input type="date" name="fecha_nacimiento" required autocomplete="off">

            <label>Comuna:</label>
            <input type="text" name="comuna" placeholder="Ej: San Antonio" autocomplete="off">

            <label>Curso:</label>
            <select name="curso" required>
              <option value="">Seleccionar curso...</option>
              <option value="PG">Playgroup</option>
              <option value="PK">Prekínder</option>
              <option value="K">Kínder</option>
              <option value="1">1° Básico</option>
              <option value="2">2° Básico</option>
              <option value="3">3° Básico</option>
              <option value="4">4° Básico</option>
              <option value="5">5° Básico</option>
              <option value="6">6° Básico</option>
              <option value="7">7° Básico</option>
              <option value="8">8° Básico</option>
              <option value="1M">1° Medio</option>
              <option value="2M">2° Medio</option>
              <option value="3M">3° Medio</option>
              <option value="4M">4° Medio</option>
            </select>

            <label>Estado:</label>
            <select name="estado_alumno">
              <option value="active">Activo</option>
              <option value="inactive">Inactivo</option>
            </select>
          </div>

          <div class="form-section">
            <h3>Datos del Apoderado</h3>

            <label>RUT Apoderado:</label>
            <input type="text" name="rut_apoderado" required autocomplete="off">

            <label>Nombre Apoderado:</label>
            <input type="text" name="nombre_apoderado" required autocomplete="off">

            <label>Apellidos Apoderado:</label>
            <input type="text" name="apellidos_apoderado" required>

            <label>Correo Apoderado:</label>
            <input type="email" name="email_apoderado" placeholder="ejemplo@correo.com" autocomplete="off">

            <label>Teléfono:</label>
            <input type="text" name="telefono_apoderado" placeholder="+56 9 1234 5678" autocomplete="off">
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-guardar">Registrar Alumno</button>
          </div>
        </form>
      </div>
    `;

    document.getElementById("volver-cursos")?.addEventListener("click", async () => {
      await cargarVerCursos();
    });
     // 🔹 Aplicar formato RUT automáticamente
    aplicarFormatoRutInput(document.querySelector('input[name="rut"]'));
    aplicarFormatoRutInput(document.querySelector('input[name="rut_apoderado"]'));

    const form = document.getElementById("form-alumno");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(form);

      try {
        const response = await fetch("/adminview/api/alumnos/registrar/", {
          method: "POST",
          headers: { "X-CSRFToken": getCSRFToken() },
          body: formData,
        });

        const result = await response.json();

        if (response.ok) {
          alert(result.message || "✅ Alumno registrado correctamente.");
          form.reset();
        } else {
          alert("⚠️ Error: " + (result.error || "No se pudo registrar el alumno."));
        }
      } catch (error) {
        console.error("Error:", error);
        alert("❌ No se pudo conectar con el servidor.");
      }
    });
  }

  /// ======================================================
  // 🔹 Ver Pagos (Lógica Original - Diseño Lista Moderna)
  // ======================================================
async function cargarVerPagos() {
  try {
    const response = await fetch("/adminview/api/pagos/");
    if (!response.ok) throw new Error("Error al obtener los pagos");
    const data = await response.json();

    let html = `<div class="finance-dashboard">`;
    
    const secciones = [
      { titulo: "Pendientes",   key: "pendientes",   color: "warning", icon: "fa-clock" },
      { titulo: "Pagados",      key: "pagados",      color: "success", icon: "fa-check-circle" },
      { titulo: "Fallidos",     key: "fallidos",     color: "danger",  icon: "fa-circle-xmark" },
      { titulo: "Reembolsados", key: "reembolsados", color: "neutral", icon: "fa-rotate-left" },
    ];

    secciones.forEach(sec => {
      const cursos = data[sec.key] || [];  // 👈 ahora es una lista

      if (!cursos.length) return;

      html += `
        <div class="finance-section ${sec.color}">
          <h3 class="section-header">
            <i class="fa-solid ${sec.icon}"></i> ${sec.titulo}
          </h3>
      `;

      // cursos = [ { curso: "...", pagos: [ ... ] }, ... ]
      cursos.forEach(entry => {
        const curso = entry.curso;
        const pagos = entry.pagos || [];

        html += `
          <details class="month-group">
            <summary class="month-header">
              <span class="month-label">${curso}</span>
              <span class="month-count">${pagos.length} movimientos</span>
            </summary>

            <div class="transaction-list">
              ${pagos.map(p => {
                const inicial = p.alumno ? p.alumno.charAt(0).toUpperCase() : "?";
                return `
                <div class="transaction-item">
                  <div class="tx-left">
                    <div class="tx-avatar ${sec.color}">${inicial}</div>
                    <div class="tx-info">
                      <div class="tx-name">${p.alumno}</div>
                      <div class="tx-concept">${p.concepto}</div>
                    </div>
                  </div>

                  <div class="tx-right">
                    <div class="tx-date">
                      <i class="fa-regular fa-calendar"></i> ${p.fecha}
                    </div>
                    <div class="tx-amount">$ ${p.monto}</div>
                  </div>
                </div>`;
              }).join("")}
            </div>
          </details>
        `;
      });

      html += `</div>`;
    });

    html += `</div>`;
    mainContent.innerHTML = html;
    title.textContent = "Historial de Pagos";

  } catch (error) {
    console.error("Error al cargar pagos", error);
    mainContent.innerHTML = `<div class="error-msg">Error cargando datos.</div>`;
  }
}



  // ======================================================
  // 🔹 Comunicados
  // ======================================================
  async function cargarComunicados() {
  title.textContent = "Comunicados";

  mainContent.innerHTML = `
    <div class="comunicados-layout">

      <div class="comunicados-form">
        <h2><i class="fa-solid fa-bullhorn"></i> Enviar Comunicado</h2>

        <form id="form-comunicado">

          <div class="form-group">
            <label>Asunto:</label>
            <input type="text" name="asunto" placeholder="Escribe el asunto del mensaje..." required>
          </div>

          <div class="form-group">
            <label>Mensaje:</label>
            <textarea name="mensaje" rows="6" placeholder="Escribe aquí el comunicado..." required></textarea>
          </div>

          <div class="form-group">
            <label>Enviar a:</label>
            <select name="destino" id="destino">
              <option value="todos">Todos los usuarios</option>
              <option value="curso">Por curso</option>
              <option value="alumno">Alumno específico</option>
              <option value="manual">Correo manual</option>
            </select>
          </div>

          <!-- 🔹 AHORA ES UN SELECT QUE SE LLENA DESDE LA BD -->
          <div id="filtro-curso" class="filtro-extra" style="display:none;">
            <label>Seleccionar curso:</label>
            <select name="curso_id" id="select-curso-comunicado">
              <option value="">Cargando cursos...</option>
            </select>
          </div>

          <div id="filtro-alumno" class="filtro-extra" style="display:none;">
            <label>RUT del alumno:</label>
            <input type="text" name="rut" placeholder="Ej: 12345678-9">
          </div>

          <div id="filtro-manual" class="filtro-extra" style="display:none;">
            <label>Correo electrónico destino:</label>
            <input type="email" name="email_manual" placeholder="Ej: nombre@correo.com">
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-guardar">Enviar Comunicado</button>
          </div>

        </form>
      </div>


      <div class="comunicados-lista">

        <div class="header-lista">
          <h3><i class="fa-solid fa-address-book"></i> Listado de Apoderados</h3>

          <div class="tabla-toolbar">
            <input 
              type="text" 
              id="buscar-apoderado" 
              class="input-busqueda"
              placeholder=" Buscar alumno, RUT o apoderado..."
            >
          </div>
        </div>

        <div class="tabla-wrapper">
          <table class="tabla-apoderados">
            <thead>
              <tr>
                <th>Alumno</th>
                <th>RUT</th>
                <th>Apoderado</th>
                <th>Correo</th>
              </tr>
            </thead>

            <tbody id="tabla-apoderados-body">
              <tr><td colspan="4">Cargando datos...</td></tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>
  `;

  // Mostrar/ocultar filtros extra según el destino
  const destino = document.getElementById("destino");
  destino.addEventListener("change", (e) => {
    document.querySelectorAll(".filtro-extra").forEach(div => div.style.display = "none");

    if (e.target.value === "curso") {
      document.getElementById("filtro-curso").style.display = "block";
    }
    if (e.target.value === "alumno") {
      document.getElementById("filtro-alumno").style.display = "block";
    }
    if (e.target.value === "manual") {
      document.getElementById("filtro-manual").style.display = "block";
    }
  });

  // Cargar tabla de apoderados
  await cargarApoderadosEnTabla();

  // 🔹 NUEVO: Cargar cursos de la BD para el select
  await poblarCursosComunicados();

  // ======================================================
  // 🔍 Buscador funcional de apoderados
  // ======================================================
  const buscador = document.getElementById("buscar-apoderado");

  buscador.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    const filas = document.querySelectorAll("#tabla-apoderados-body tr");

    filas.forEach(row => {
      const texto = row.textContent.toLowerCase();
      row.style.display = texto.includes(term) ? "" : "none";
    });
  });

  // Enviar comunicado
  const form = document.getElementById("form-comunicado");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(form);

    try {
      const response = await fetch("/adminview/api/comunicados/enviar/", {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": getCSRFToken() },
      });

      const result = await response.json();
      alert("✅ " + result.message);
      form.reset();
    }
    catch (error) {
      console.error("Error al enviar comunicado:", error);
      alert("❌ Error al conectar con el servidor.");
    }
  });

  // ================================================
  // 🔹 Helper interno: poblar combo de cursos
  // ================================================
  async function poblarCursosComunicados() {
    const selectCurso = document.getElementById("select-curso-comunicado");
    if (!selectCurso) return;

    try {
      const resp = await fetch("/adminview/api/cursos/");
      if (!resp.ok) throw new Error("Error al obtener cursos");

      const data = await resp.json();
      const cursos = data.cursos || [];

      if (!cursos.length) {
        selectCurso.innerHTML = `<option value="">No hay cursos configurados</option>`;
        return;
      }

      // Limpia y agrega opciones
      selectCurso.innerHTML = `<option value="">Seleccionar curso...</option>`;

      cursos.forEach(c => {
        // Intentamos usar curso_id si viene, si no, usamos el nombre
        const value = c.curso_id || c.curso;
        const label = c.curso;   // lo que ya usas en cargarVerCursos()

        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = label;
        selectCurso.appendChild(opt);
      });

    } catch (err) {
      console.error("Error al cargar cursos para comunicados:", err);
      selectCurso.innerHTML = `<option value="">Error al cargar cursos</option>`;
    }
  }
}







  async function cargarApoderadosEnTabla() {
    const tbody = document.getElementById("tabla-apoderados-body");
    try {
      const response = await fetch("/adminview/api/apoderados/");
      const data = await response.json();

      tbody.innerHTML = "";
      if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4">No hay apoderados registrados.</td></tr>`;
        return;
      }

      data.forEach(item => {
        tbody.innerHTML += `
          <tr>
            <td>${item.alumno}</td>
            <td>${item.rut}</td>
            <td>${item.apoderado}</td>
            <td>${item.email || "—"}</td>
          </tr>
        `;
      });
    } catch (error) {
      console.error("Error al cargar apoderados:", error);
      tbody.innerHTML = `<tr><td colspan="4">Error al cargar datos.</td></tr>`;
    }
  }

// ======================================================
//  HORARIOS (Estructura Divs para Responsividad Total)
// ======================================================
async function cargarHorarios() {
    title.textContent = "Horarios de Clases";

    // Pantalla de carga
    mainContent.innerHTML = `
      <div class="card" style="text-align:center; padding:40px;">
        <i class="fa-solid fa-circle-notch fa-spin" style="font-size:2rem; color:var(--primary);"></i>
        <p style="margin-top:15px; color:#666;">Cargando horarios de los profesores...</p>
      </div>
    `;

    try {
      const resp = await fetch("/adminview/api/horarios/");
      if (!resp.ok) throw new Error("No se pudo obtener los horarios");

      const data = await resp.json();
      const profesores = data.profesores || [];

      if (!profesores.length) {
        mainContent.innerHTML = `
        <div class="card" style="text-align:center;">
          <i class="fa-regular fa-calendar-xmark" style="font-size:3rem; color:#ccc; margin-bottom:15px;"></i>
          <h2>Sin Horarios</h2>
          <p>No hay horarios registrados en el sistema.</p>
        </div>`;
        return;
      }

      let html = `<div class="horarios-wrapper">`;

      profesores.forEach(p => {
        html += `
        <details class="horario-card">
            <summary class="horario-header">
                <strong>${p.profesor}</strong>
                
            </summary>

            <div class="horario-body">
                <div class="schedule-head-row">
                    <div class="head-day">DÍA</div>
                    <div class="head-time">HORA</div>
                    <div class="head-subject">ASIGNATURA</div>
                    <div class="head-course">CURSO</div>
                </div>

                <div class="schedule-list-items">
                    ${p.horarios.map(h => `
                    <div class="schedule-item">
                        <div class="item-day">${h.dia}</div>
                        
                        <div class="item-time">
                            <span class="time-start">${h.inicio}</span>
                            <i class="fa-solid fa-arrow-right-long time-arrow"></i>
                            <span class="time-end">${h.termino}</span>
                        </div>
                        
                        <div class="item-subject">${h.asignatura}</div>
                        
                        <div class="item-course">
                            <span class="badge-curso">${h.curso || "—"}</span>
                        </div>
                    </div>`).join("")}
                </div>
            </div>
        </details>
        `;
      });

      html += `</div>`;
      mainContent.innerHTML = html;
      title.textContent = "Horarios de Clases";

    } catch (err) {
      console.error("Error al cargar horarios:", err);
      mainContent.innerHTML = `<div class="card error-card">Error al cargar los horarios.</div>`;
    }
  }
  

  // ======================================================
  //  NUEVO: Asignaturas (con estilito)
  // ======================================================
  async function cargarAsignaturas() {
    title.textContent = "Asignaturas";

    try {
      const resp = await fetch("/adminview/api/asignaturas/");
      if (!resp.ok) throw new Error("No se pudo obtener las asignaturas");
      const data = await resp.json();

      const asignaturas = data.asignaturas || [];

      let html = `
      <div class="card card-asignaturas">
        <div class="asignaturas-header">
          <div>
            <h2>Asignaturas del colegio</h2>
            <p class="card-subtitle">
              Vista consolidada de ramos por curso y año académico.
            </p>
          </div>
          <span class="badge badge-info">${asignaturas.length} registro(s)</span>
        </div>

        ${asignaturas.length === 0 ? `
          <p class="empty-msg">No hay asignaturas registradas.</p>
        ` : `
          <div class="tabla-toolbar">
            <input 
              type="text" 
              id="buscador-asignaturas" 
              class="input-busqueda" 
              placeholder="Buscar por asignatura, curso o profesor..."
            >
          </div>

          <div class="tabla-wrapper">
            <table class="tabla-generica" id="tabla-asignaturas">
              <thead>
                <tr>
                  <th>Asignatura</th>
                  <th>Curso</th>
                  <th>Año</th>
                  <th>Profesor</th>
                </tr>
              </thead>
              <tbody>
                ${asignaturas.map(a => `
                  <tr>
                    <td>${a.name}</td>
                    <td>${a.curso || "—"}</td>
                    <td>${a.year || "—"}</td>
                    <td>${a.teacher || "—"}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;

      mainContent.innerHTML = html;

      // 🔍 Filtro rápido en la tabla
      const inputBuscador = document.getElementById("buscador-asignaturas");
      if (inputBuscador) {
        const filas = Array.from(
          document.querySelectorAll("#tabla-asignaturas tbody tr")
        );

        inputBuscador.addEventListener("input", (e) => {
          const term = e.target.value.toLowerCase().trim();

          filas.forEach(row => {
            const texto = row.textContent.toLowerCase();
            row.style.display = texto.includes(term) ? "" : "none";
          });
        });
      }

    } catch (err) {
      console.error(err);
      mainContent.innerHTML = `
      <div class="error-msg">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Error al cargar las asignaturas.
      </div>
    `;
    }
  }





// ======================================================
// 🔹 Navegación SPA
// ======================================================
links.forEach(link => {
  link.addEventListener("click", async (e) => {
    e.preventDefault();

    // Actualizar estado visual
    clearActive();
    link.classList.add("active");

    const section = link.getAttribute("data-section");

    switch (section) {

     // ======================================================
      // 🟦 TABLERO (DASHBOARD FINAL - 4 ARRIBA / 2 ABAJO)
      // ======================================================
      case "tablero":
        title.textContent = "Panel de Control";

        // --- 1. Estructura HTML ---
        mainContent.innerHTML = `
          <h1>Bienvenido</h1>
          <p>Resumen general del ecosistema escolar.</p>

          <div class="tarjetas-resumen">
            <div class="tarjeta" id="card-estudiantes">Estudiantes: ...</div>
            <div class="tarjeta" id="card-profesores">Profesores: ...</div>
            <div class="tarjeta" id="card-apoderados">Apoderados: ...</div>
            <div class="tarjeta" id="card-admins">Administrativos: ...</div>
          </div>

          <div class="dashboard-charts">
            
            <div class="chart-box">
              <div class="chart-title">Distribución de Usuarios</div>
              <div class="chart-container"><canvas id="graficoUsuarios"></canvas></div>
            </div>

            <div class="chart-box">
              <div class="chart-title">Estado General de Pagos</div>
              <div class="chart-container"><canvas id="graficoPagos"></canvas></div>
            </div>

            <div class="chart-box">
              <div class="chart-title">Proporción Alumnos / Personal</div>
              <div class="chart-container"><canvas id="graficoRelacion"></canvas></div>
            </div>

            <div class="chart-box">
              <div class="chart-title">Desglose de Cobranza</div>
              <div class="chart-container"><canvas id="graficoDeuda"></canvas></div>
            </div>

            <div class="chart-box" style="grid-column: span 2; height: 450px;">
              <div class="chart-title">Detalle de Matrícula por Curso</div>
              <div class="chart-container"><canvas id="graficoAlumnosNivel"></canvas></div>
            </div>

            

          </div>
        `;

        // --- 2. Configuración Global ---
        Chart.defaults.font.family = "'Poppins', sans-serif";
        Chart.defaults.color = '#64748b';
        Chart.defaults.scale.grid.color = '#f1f5f9';
        
        const tooltipTheme = {
          backgroundColor: '#ffffff', titleColor: '#1c3162', bodyColor: '#64748b',
          borderColor: '#e2e8f0', borderWidth: 1, padding: 12, usePointStyle: true,
          titleFont: { size: 14, family: "'Poppins', sans-serif" }, displayColors: true
        };

        function createGradient(ctx, c1, c2) {
            const g = ctx.createLinearGradient(0, 0, 0, 400);
            g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
        }

        try {
          const resp = await fetch("/adminview/api/dashboard/stats/");
          const stats = await resp.json();

          // Cards
          document.getElementById("card-estudiantes").textContent = `Estudiantes: ${stats.total_students}`;
          document.getElementById("card-profesores").textContent  = `Profesores: ${stats.total_teachers}`;
          document.getElementById("card-apoderados").textContent  = `Apoderados: ${stats.total_guardians}`;
          document.getElementById("card-admins").textContent      = `Administrativos: ${stats.total_admins}`;

          // --- GRÁFICOS SUPERIORES ---

          // 1. Usuarios
          new Chart(document.getElementById("graficoUsuarios"), {
            type: "doughnut",
            data: {
              labels: ["Alumnos", "Profesores", "Apoderados", "Admin"],
              datasets: [{ data: [stats.total_students, stats.total_teachers, stats.total_guardians, stats.total_admins], backgroundColor: ["#1c3162", "#CDA758", "#60a5fa", "#94a3b8"], borderWidth: 4, borderColor: '#ffffff' }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: "70%", plugins: { legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: tooltipTheme } }
          });

          // 2. Pagos
          new Chart(document.getElementById("graficoPagos"), {
            type: "pie",
            data: {
              labels: ["Pagados", "Pendientes", "Fallidos"],
              datasets: [{ data: [stats.pagos_pagados, stats.pagos_pendientes, stats.pagos_fallidos], backgroundColor: ["#10b981", "#f59e0b", "#ef4444"], borderWidth: 4, borderColor: '#ffffff' }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: tooltipTheme } }
          });

          // 3. Relación
          const personalTotal = stats.total_teachers + stats.total_admins;
          new Chart(document.getElementById("graficoRelacion"), {
            type: "bar",
            data: {
              labels: ["Alumnos", "Personal"],
              datasets: [{ label: "Personas", data: [stats.total_students, personalTotal], backgroundColor: ["#1c3162", "#CDA758"], borderRadius: 6, barThickness: 40 }]
            },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: tooltipTheme }, scales: { x: { display: false }, y: { grid: { display: false } } } }
          });

          // 4. Deuda
          new Chart(document.getElementById("graficoDeuda"), {
            type: "polarArea",
            data: {
              labels: ["Pagado", "Pendiente", "Fallido"],
              datasets: [{ data: [stats.pagos_pagados, stats.pagos_pendientes, stats.pagos_fallidos], backgroundColor: ["rgba(16, 185, 129, 0.7)", "rgba(245, 158, 11, 0.7)", "rgba(239, 68, 68, 0.7)"], borderWidth: 1, borderColor: '#fff' }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { r: { grid: { color: '#f0f0f0' }, ticks: { display: false } } }, plugins: { legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: tooltipTheme } }
          });

          // --- GRÁFICOS INFERIORES (ANCHOS) ---

          // 5. MATRÍCULA POR NIVEL (Izquierda)
          const ctxNivel = document.getElementById("graficoAlumnosNivel").getContext('2d');
          const gradNivel = createGradient(ctxNivel, '#CDA758', '#fae8b9');
          
          // Validamos datos
          const nivelesLabels = (stats.niveles_labels && stats.niveles_labels.length) ? stats.niveles_labels : ["Sin datos"];
          const nivelesData = (stats.niveles_data && stats.niveles_data.length) ? stats.niveles_data : [0];

          new Chart(ctxNivel, {
            type: "bar",
            data: {
              labels: nivelesLabels,
              datasets: [{
                label: "Alumnos",
                data: nivelesData,
                backgroundColor: gradNivel,
                borderRadius: 6,
                barThickness: 30
              }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: tooltipTheme }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } } }
          });


          

        } catch (error) {
          console.error(error);
          mainContent.innerHTML += `<div class="error-msg">Error cargando gráficos.</div>`;
        }
        break;
      // ======================================================
      // 📚 Otras Secciones
      // ======================================================
      case "estudiantes":
        await cargarVerCursos();
        break;

      case "profesores":
        await cargarProfesores();
        break;

      case "agregar-alumno":
        await cargarAgregarAlumno();
        break;

      case "revision-pagos":
        await cargarVerPagos();
        break;

      case "comunicados":
        await cargarComunicados();
        break;

      case "asignaturas":
        await cargarAsignaturas();
        break;

      case "horarios":
        await cargarHorarios();
        break;

      default:
        mainContent.innerHTML = `
          <h1>${link.textContent}</h1>
          <p>Sección "${section}" en construcción...</p>
        `;
        title.textContent = link.textContent.trim();
    }

    if (isMobile()) closeSidebar();
  });
});


  // ======================================================
  // ⭐ Cargar TABLERO automáticamente al entrar
  // ======================================================
  const linkTablero = document.querySelector('a[data-section="tablero"]');
  if (linkTablero) linkTablero.click();
});



