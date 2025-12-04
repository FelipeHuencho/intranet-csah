document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("toggle");
  const overlay = document.getElementById("overlay");
  const content = document.getElementById("content-area");
  const topbarTitle = document.getElementById("topbar-title");
  const menuLinks = document.querySelectorAll(".menu a[data-section]");

  // 👇 agregamos TODOS los endpoints que usa el JS
  const API = {
  cursos: "/profesorView/cursos/",
  perfil: "/profesorView/perfil-data/",
  alumnos: (classId) => `/profesorView/curso/${classId}/alumnos/`,
  asignaturas: (classId) => `/profesorView/curso/${classId}/asignaturas/`,
  crearEvaluacion: "/profesorView/crear-evaluacion/",
  evaluacionesCurso: (classId) => `/profesorView/curso/${classId}/evaluaciones/`,
  guardarNotas: (evalId) => `/profesorView/evaluacion/${evalId}/notas/guardar/`,

  // ✅ NUEVO: alumnos + nota (si existe) para una evaluación
  alumnosConNotas: (evalId) => `/profesorView/evaluacion/${evalId}/alumnos-notas/`,
};


  function setTitle(section) {
    const pretty = section.replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase());
    if (topbarTitle) topbarTitle.textContent = pretty;
  }
  // =========================
  // UTILIDADES PARA FECHAS
  // =========================

  // Calcula cuántos días faltan
  function diasFaltan(fecha) {
    // fecha = "15-11-2025"
    const [dia, mes, año] = fecha.split("-").map(Number);

    // convertir a Date válido en JS
    const f = new Date(año, mes - 1, dia);

    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    const diff = f - hoy;

    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  // Define color según urgencia
  function colorFecha(dias) {
    if (dias <= 2) return "danger";     // rojo
    if (dias <= 5) return "warning";   // amarillo
    return "normal";                   // azul
  }

  function limpiarNombreCurso(texto) {
    // deja solo: "6° Básico", "1° Medio", etc.
    // busca el primer "°" y corta antes para obtener el número real
    const match = texto.match(/\d+°\s+(Básico|Medio)/i);
    return match ? match[0] : texto;
  }



  // =========================
  // router
  // =========================
  function load(section) {
    setTitle(section);

    // marcar menú
    menuLinks.forEach((l) => l.classList.remove("active"));
    const current = document.querySelector(`.menu a[data-section="${section}"]`);
    if (current) current.classList.add("active");

    // RUTAS:
    if (section === "dashboard") return renderDashboard();
    if (section === "mis-cursos") return renderCursos();
    if (section === "crear-evaluacion") return renderCrearEval();
    if (section === "ingresar-notas") return renderIngresarNotas();
    if (section === "mis-notas") return renderMisNotas();
    if (section === "perfil") return renderPerfil();

    content.innerHTML = `<div class="card">Sección "${section}" no implementada.</div>`;
  }

  async function renderDashboard() {
    content.innerHTML = `
    <div class="card dash-card">
      <h2 class="card-title">Bienvenido, ${profesor.nombre}</h2>

      <p id="msg-hoy" class="hoy-box">
        Cargando clases de hoy...
      </p>
    </div>

    <div id="eval-card"></div>
  `;

    cargarClasesHoy();
    cargarProximasEvaluaciones();
  }
  // js:
async function cargarClasesHoy() {
    const msg = document.getElementById("msg-hoy");

    try {
        const r = await fetch("/profesorView/clases-hoy/");
        const data = await r.json();

        // **NUEVOS CAMBIOS EN JS**
        const hoy = new Date();
        const diaSemana = hoy.getDay(); // 0 (Dom) a 6 (Sáb)

        // Asignaturas del día (vacío si es fin de semana)
        let cursosVisibles = [];
        
        // Excluir Sábado (6) y Domingo (0)
        if (diaSemana !== 0 && diaSemana !== 6) { 
            cursosVisibles = data.cursos.map(c => limpiarNombreCurso(c));
        }

        // Determinar la lista de asignaturas para mostrar
        const lista = cursosVisibles.length
            ? cursosVisibles.join(", ")
            : "ningún curso programado para hoy"; // Texto ligeramente mejorado para el caso vacío

        // **CAMBIO DEL TEXTO DE SALIDA**
        msg.innerHTML = `
        Hoy es: <strong>${data.dia}</strong>.
        Tus asignaturas: <strong>${lista}</strong>.
        `;

    } catch (err) {
        msg.textContent = "No se pudieron cargar tus clases de hoy.";
    }
  }


  async function cargarProximasEvaluaciones() {
    const cont = document.getElementById("eval-card");

    try {
      const r = await fetch("/profesorView/proximas-evaluaciones/");
      const data = await r.json();
      const evaluaciones = data.evaluaciones || [];

      if (!evaluaciones.length) {
        cont.innerHTML = `
        <div class="card">
          <h3 class="card-title"> Próximas Evaluaciones</h3>
          <p>No tienes evaluaciones próximas.</p>
        </div>
      `;
        return;
      }

      cont.innerHTML = `
  <div class="prox-card">
    <h3 class="prox-title"><i></i> Próximas Evaluaciones</h3>

    ${evaluaciones
          .map((ev) => {
            const dias = diasFaltan(ev.fecha);
            const color = colorFecha(dias);

            return `
          <div class="prox-item">
            <div class="prox-left">
              <span class="prox-desc">${ev.descripcion}</span>
              <span class="prox-meta">${ev.curso} — ${ev.asignatura}</span>
            </div>

            <span class="prox-date ${color}">
              ${ev.fecha}
              <small style="display:block; font-size:11px; opacity:.8;">
                Faltan ${dias} días
              </small>
            </span>
          </div>
        `;
          })
          .join("")}

  </div>
`;




    } catch (err) {
      cont.innerHTML = `
      <div class="card">
        <h3 class="card-title"> Próximas Evaluaciones</h3>
        <p>Error al cargar.</p>
      </div>
    `;
    }
  }

  // =========================
  // cursos del profe
  // =========================
  // =========================

  async function renderCursos() {

    content.innerHTML = `
        <h2 class="card-title" style="font-size:28px; margin-bottom:20px;">
            <i class="#"></i> Mis Cursos
        </h2>

        <div class="clases-grid" id="cursos-grid"></div>
    `;

    const grid = document.getElementById("cursos-grid");

    let cursos = [];

    try {
      const r = await fetch(API.cursos);
      cursos = await r.json();
    } catch (err) {
      grid.innerHTML = "<p>Error al cargar.</p>";
      return;
    }

    if (!cursos.length) {
      grid.innerHTML = "<p>No tienes cursos asignados.</p>";
      return;
    }

    cursos.forEach(curso => {
      const card = document.createElement("div");
      card.className = "course-card";

      card.innerHTML = `
            <div class="course-header">
                <i class="#"></i>
                
            </div>

            <div class="course-body">
                <h3 class="course-title">${curso.nombre}</h3>

                <div class="actions">
                    <button class="btn-academic blue" data-ver="${curso.id}">
                        Ver alumnos
                    </button>

                    <button class="btn-academic yellow" data-eval="${curso.id}">
                        Crear evaluación
                    </button>
                </div>
            </div>
        `;

      grid.appendChild(card);
    });

    grid.addEventListener("click", (e) => {
      const btnVer = e.target.closest("[data-ver]");
      const btnEval = e.target.closest("[data-eval]");

      if (btnVer) {
        const id = btnVer.dataset.ver;
        return renderAlumnos(id, "Curso");
      }

      if (btnEval) {
        const id = btnEval.dataset.eval;
        return renderCrearEval(id);
      }
    });
  }



  // =========================
  // alumnos de un curso
  // =========================
  async function renderAlumnos(classId, nombreCurso) {

    content.innerHTML = `<div class="card">Cargando alumnos...</div>`;

    let alumnos = [];
    try {
      const r = await fetch(API.alumnos(classId));
      alumnos = await r.json();
    } catch (err) {
      content.innerHTML = `<div class="card">No se pudieron cargar los alumnos.</div>`;
      return;
    }

    // SI NO HAY ALUMNOS
    if (!Array.isArray(alumnos) || alumnos.length === 0) {
      content.innerHTML = `
        <div class="card">
            <h2 class="card-title">${nombreCurso} — Alumnos</h2>
            <p>No hay alumnos en este curso.</p>
            <a href="#" data-section="mis-cursos" id="link-volver-cursos">Volver a cursos</a>
        </div>`;
      return;
    }

    // HTML FINAL
    content.innerHTML = `
        <div class="card">
            <h2 class="card-title">
                ${nombreCurso} — Alumnos 
                <span class="badge-count">${alumnos.length} estudiantes</span>
            </h2>

            <div class="alumnos-grid">
                ${alumnos.map(a => `
                    <div class="alumno-card">
                        <div class="alumno-icon"></div>
                        <div class="alumno-info">
                            <h4>${a.nombre}</h4>
                            <span class="rut">${a.rut || "--"}</span>
                        </div>
                    </div>
                `).join("")}
            </div>

            <a href="#" data-section="mis-cursos" id="link-volver-cursos" class="volver-link">Volver a cursos</a>
        </div>
    `;

    // botón volver
    const back = document.getElementById("link-volver-cursos");
    if (back) {
      back.addEventListener("click", (e) => {
        e.preventDefault();
        load("mis-cursos");
      });
    }
  }


  // =========================
  // PERFIL
  // =========================
  async function renderPerfil() {
    content.innerHTML = `<div class="card">Cargando perfil...</div>`;
    let p = {};
    try {
      const r = await fetch(API.perfil);
      p = await r.json();
    } catch (err) {
      content.innerHTML = `<div class="card">No se pudo cargar el perfil.</div>`;
      return;
    }

    content.innerHTML = `
  <div class="perfil-container">

      <div class="perfil-header">
          <div class="perfil-banner"></div>

          <div class="perfil-avatar">
              <div class="avatar-circle">
                  ${(p.nombre || "--")
        .split(" ")
        .map((s) => s[0] || "")
        .join("")
        .slice(0, 2)
        .toUpperCase()}
              </div>

              <h2 class="perfil-nombre">${p.nombre}</h2>
              <p class="perfil-sub">
                  RUT ${p.rut || "--"} · ${p.email || "--"}
              </p>
          </div>
      </div>

      <div class="perfil-body">

          <div class="perfil-info-box">
              <h3>Información Personal</h3>
              <table>
                  <tr><td>Nombre</td><td>${p.nombre}</td></tr>
                  <tr><td>RUT</td><td>${p.rut || "--"}</td></tr>
                  <tr><td>Correo</td><td>${p.email || "--"}</td></tr>
              </table>
          </div>

      </div>

  </div>
  `;

  }

  // =========================
  // CREAR EVALUACIÓN (2 pasos)
  // =========================
  async function renderCrearEval(preselectedClassId = null) {
    content.innerHTML = `
    <div class="card eval-card">
      <h2 class="card-title">Crear evaluación</h2>
      <p class="eval-subtitle">Selecciona el curso y completa los datos.</p>

      <div class="eval-form-grid">
        <div style="grid-column: span 2;">
          <label class="eval-label">Curso</label>
          <select id="select-curso" class="eval-select">
            <option value="">Cargando cursos...</option>
          </select>
        </div>
      </div>

      <div id="eval-form-wrap" style="margin-top:1rem;"></div>
    </div>
  `;

    const selCurso = document.getElementById("select-curso");
    const formWrap = document.getElementById("eval-form-wrap");

    // cargar cursos
    let cursos = [];
    try {
      const r = await fetch(API.cursos);
      cursos = await r.json();
    } catch (err) {
      selCurso.innerHTML = `<option value="">Error al cargar cursos</option>`;
      return;
    }

    if (!Array.isArray(cursos) || cursos.length === 0) {
      selCurso.innerHTML = `<option value="">No tienes cursos</option>`;
      return;
    }

    selCurso.innerHTML = `<option value="">-- elegir curso --</option>`;
    cursos.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.nombre;
      selCurso.appendChild(opt);
    });

    if (preselectedClassId) {
      selCurso.value = preselectedClassId;
      await buildEvalForm(preselectedClassId, formWrap);
    }

    selCurso.addEventListener("change", async () => {
      const classId = selCurso.value;
      formWrap.innerHTML = "";
      if (!classId) return;
      await buildEvalForm(classId, formWrap);
    });
  }


  async function buildEvalForm(classId, container) {
    container.innerHTML = `
  <div class="eval-form-grid">

      <div>
          <label class="eval-label">Asignatura</label>
          <select id="subject-select" class="input-field">
              <option value="">Cargando...</option>
          </select>
      </div>

      <div>
          <label class="eval-label">Nombre / descripción</label>
          <input id="eval-desc" class="input-field" placeholder="Ej: Prueba unidad 1">
      </div>

      <div>
          <label class="eval-label">Fecha</label>
          <input type="date" id="eval-date" class="input-field">
      </div>

      <div>
          <label class="eval-label">Ponderación</label>
          <input type="number" id="eval-weight" class="input-field" step="0.1" value="1">
      </div>

      <div>
          <label class="eval-label">Tipo de evaluación</label>
          <input id="eval-type-name" class="input-field" placeholder="Ej: Prueba, Control">
      </div>

      <button id="btn-save-eval" class="btn-academic blue btn-full">
          Crear evaluación
      </button>

  </div>
  `;



    const selSubject = document.getElementById("subject-select");

    // cargar asignaturas del profe en ese curso
    try {
      const r = await fetch(API.asignaturas(classId));
      const asignaturas = await r.json();
      selSubject.innerHTML = "";
      if (Array.isArray(asignaturas) && asignaturas.length) {
        selSubject.innerHTML = `<option value="">-- elegir asignatura --</option>`;
        asignaturas.forEach((s) => {
          const opt = document.createElement("option");
          opt.value = s.id;
          opt.textContent = s.name || s.nombre || "Asignatura";
          selSubject.appendChild(opt);
        });
      } else {
        selSubject.innerHTML = `<option value="">(no tienes asignaturas en este curso)</option>`;
      }
    } catch (err) {
      selSubject.innerHTML = `<option value="">Error al cargar asignaturas</option>`;
    }

    const btnSave = document.getElementById("btn-save-eval");
    btnSave.addEventListener("click", async () => {
      const subjectId = selSubject.value;
      const desc = document.getElementById("eval-desc").value.trim();
      const date = document.getElementById("eval-date").value;
      const weight = document.getElementById("eval-weight").value || "1";
      const typeName = document.getElementById("eval-type-name").value.trim();

      if (!subjectId) return alert("Debes elegir una asignatura");
      if (!desc) return alert("Debes escribir una descripción");
      if (!date) return alert("Debes elegir una fecha");
      if (!typeName) return alert("Debes indicar el tipo de evaluación");

      const fd = new FormData();
      fd.append("class_id", classId);
      fd.append("subject_id", subjectId);
      fd.append("description", desc);
      fd.append("date", date);
      fd.append("weight", weight);
      fd.append("evaluation_type_name", typeName);

      const r = await fetch(API.crearEvaluacion, {
        method: "POST",
        body: fd,
        headers: {
          "X-CSRFToken": profesor.csrf,
        },
      });
      const res = await r.json();
      if (res.success) {
        alert("Evaluación creada ✅");
        load("mis-cursos");
      } else {
        alert(res.error || "Error al crear la evaluación");
      }
    });
  }

  // =========================
  // INGRESAR NOTAS (lo que enviaste)
  // =========================
  // =========================
  // INGRESAR NOTAS (con notas existentes)
  // =========================
  async function renderIngresarNotas() {
    content.innerHTML = `
      <div class="ingresar-card">
          <h2 class="card-title">Ingresar notas</h2>

          <div class="ingresar-grid">

              <div>
                  <label class="ingresar-label">Curso</label>
                  <select id="notas-select-curso" class="ingresar-select">
                      <option value="">Cargando cursos...</option>
                  </select>
              </div>

              <div>
                  <label class="ingresar-label">Evaluación</label>
                  <select id="notas-select-eval" class="ingresar-select" disabled>
                      <option value="">Primero elige un curso</option>
                  </select>
              </div>

          </div>

          <div id="notas-alumnos-wrap" style="margin-top:2rem;"></div>
      </div>
    `;

    const selCurso = document.getElementById("notas-select-curso");
    const selEval = document.getElementById("notas-select-eval");
    const alumnosWrap = document.getElementById("notas-alumnos-wrap");

    // 1) Cargar cursos del profe
    let cursos = [];
    try {
      const r = await fetch(API.cursos);
      cursos = await r.json();
    } catch (err) {
      console.error(err);
      selCurso.innerHTML = `<option value="">Error al cargar cursos</option>`;
      return;
    }

    if (!Array.isArray(cursos) || cursos.length === 0) {
      selCurso.innerHTML = `<option value="">No tienes cursos</option>`;
      return;
    }

    selCurso.innerHTML = `<option value="">-- elegir curso --</option>`;
    cursos.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.nombre;
      selCurso.appendChild(opt);
    });

    // 2) Al elegir curso -> cargar evaluaciones
    selCurso.addEventListener("change", async () => {
      const classId = selCurso.value;
      selEval.innerHTML = `<option value="">Cargando evaluaciones...</option>`;
      selEval.disabled = true;
      alumnosWrap.innerHTML = "";

      if (!classId) return;

      let evals = [];
      try {
        const r = await fetch(API.evaluacionesCurso(classId));
        if (r.ok) {
          evals = await r.json();
        } else {
          selEval.innerHTML = `<option value="">(Error al cargar evaluaciones)</option>`;
          return;
        }
      } catch (err) {
        console.error(err);
        selEval.innerHTML = `<option value="">No se pudieron cargar</option>`;
        return;
      }

      if (!Array.isArray(evals) || evals.length === 0) {
        selEval.innerHTML = `<option value="">No hay evaluaciones para este curso</option>`;
        return;
      }

      selEval.disabled = false;
      selEval.innerHTML = `<option value="">-- elegir evaluación --</option>`;
      evals.forEach((ev) => {
        const opt = document.createElement("option");
        opt.value = ev.id;
        opt.textContent = `${ev.description || ev.nombre || "Evaluación"} (${ev.date || ""})`;
        selEval.appendChild(opt);
      });
    });

    // 3) Al elegir evaluación -> alumnos + notas (si hay)
    selEval.addEventListener("change", async () => {
      const evalId = selEval.value;
      alumnosWrap.innerHTML = "";

      if (!evalId) return;

      let alumnos = [];
      try {
        // 👇 ahora usamos alumnosConNotas, no API.alumnos(classId)
        const r = await fetch(API.alumnosConNotas(evalId));
        if (!r.ok) {
          alumnosWrap.innerHTML = `<p>No se pudieron cargar los alumnos.</p>`;
          return;
        }
        alumnos = await r.json();
      } catch (err) {
        console.error(err);
        alumnosWrap.innerHTML = `<p>No se pudieron cargar los alumnos.</p>`;
        return;
      }

      if (!Array.isArray(alumnos) || alumnos.length === 0) {
        alumnosWrap.innerHTML = `<p>Este curso no tiene alumnos.</p>`;
        return;
      }

      // 4) Pintar tabla con inputs y notas pre-llenadas (si existen)
      alumnosWrap.innerHTML = `
        <form id="form-notas">
          <div class="tabla-card">
            <div class="tabla-body">
              <table class="tabla-notas">
                <thead>
                  <tr><th>Alumno</th><th>RUT</th><th>Nota</th></tr>
                </thead>
                <tbody>
                  ${alumnos
                    .map((a) => {
                      const valor = (a.nota !== null && a.nota !== undefined) ? a.nota : "";
                      return `
                        <tr>
                          <td>${a.nombre}</td>
                          <td>${a.rut || "--"}</td>
                          <td>
                            <input
                              type="number"
                              min="1"
                              max="7"
                              step="0.1"
                              name="${a.id}"
                              placeholder="7.0"
                              value="${valor}"
                            >
                          </td>
                        </tr>
                      `;
                    })
                    .join("")}
                </tbody>
              </table>
            </div>
          </div>
          <button type="submit" class="btn" style="margin-top:1rem;">Guardar notas</button>
        </form>
      `;

      // 5) Guardar (crea o actualiza notas)
      const form = document.getElementById("form-notas");
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);

        try {
          const r = await fetch(API.guardarNotas(evalId), {
            method: "POST",
            body: fd,
            headers: {
              "X-CSRFToken": profesor.csrf,
            },
          });
          const res = await r.json();
          if (res.success) {
            alert(`Notas guardadas ✅${res.actualizadas ? " (" + res.actualizadas + " registro(s))" : ""}`);
          } else {
            alert(res.error || "Error al guardar notas");
          }
        } catch (err) {
          console.error(err);
          alert("Error al guardar notas");
        }
      });
    });
  }

  function limpiarCurso(texto) {
    // elimina todo antes del primer "–" (en-dash) o "-"
    return texto.replace(/^[^-–]+[-–]\s*/, "");
  }


  function renderMisNotas() {
  const content = document.getElementById("content-area");
  if (!content) {
    console.error("No encontré #content-area");
    return;
  }

  content.innerHTML = `
    <div class="card">
      <h2 class="card-title">Mis cursos y notas</h2>
      <p>Cargando información...</p>
    </div>
  `;

  fetch("/profesorView/mis-cursos-notas/")
    .then((r) => r.json())
    .then((data) => {
      const cursos = data.cursos || [];
      if (!cursos.length) {
        content.innerHTML = `
          <div class="card">
            <h2 class="card-title">Mis cursos y notas</h2>
            <p>No tienes cursos asignados.</p>
          </div>
        `;
        return;
      }

      let html = "";

      cursos.forEach((c, index) => {
        const alumnos = c.alumnos || [];

        // ================================
        // 1) Calcular cuántas columnas de notas hay
        //    y tomar nombres de evaluaciones
        // ================================
        let maxNotas = 0;
        alumnos.forEach((al) => {
          const len = (al.notas || []).length;
          if (len > maxNotas) maxNotas = len;
        });

        // Cabeceras dinámicas para las notas
        let headerNotas = "";
        if (maxNotas > 0) {
          // Usamos las notas del primer alumno como referencia para nombres de evaluaciones
          const refNotas = (alumnos[0]?.notas) || [];
          for (let i = 0; i < maxNotas; i++) {
            const etiqueta = refNotas[i]?.evaluacion || `Nota ${i + 1}`;
            headerNotas += `<th>${etiqueta}</th>`;
          }
        } else {
          headerNotas = `<th>Notas</th>`;
        }

        // ================================
        // 2) Construir tabla de alumnos
        // ================================
        let alumnosHtml = `
          <table class="tabla-alumnos">
            <thead>
              <tr>
                <th>Alumno</th>
                ${headerNotas}
              </tr>
            </thead>
            <tbody>
        `;

        alumnos.forEach((al) => {
          const notas = al.notas || [];
          let celdasNotas = "";

          if (maxNotas === 0) {
            celdasNotas = `<td>Sin notas</td>`;
          } else {
            for (let i = 0; i < maxNotas; i++) {
              const n = notas[i];
              const valor = (n && n.nota != null) ? n.nota : "-";
              celdasNotas += `<td>${valor}</td>`;
            }
          }

          alumnosHtml += `
            <tr>
              <td>${al.nombre}</td>
              ${celdasNotas}
            </tr>
          `;
        });

        alumnosHtml += `
            </tbody>
          </table>
        `;

        // ================================
        // 3) Acordeón por curso
        // ================================
        html += `
          <div class="acordeon-item">
              <div class="acordeon-header" data-acc="${index}">
                  <div class="acc-texts">
                      <div class="acc-title">${c.asignatura}</div>
                      <div class="acc-sub">${limpiarCurso(c.curso)}</div>
                  </div>
                  <span class="acordeon-arrow">▶</span>
              </div>

              <div class="acordeon-body" id="acc-body-${index}">
                  ${alumnosHtml}
              </div>
          </div>
        `;
      });

      content.innerHTML = html;

      // ================================
      // 4) Comportamiento del acordeón
      // ================================
      document.querySelectorAll(".acordeon-header").forEach((header) => {
        header.addEventListener("click", () => {
          const id = header.getAttribute("data-acc");
          const body = document.getElementById(`acc-body-${id}`);
          const arrow = header.querySelector(".acordeon-arrow");
          const item = header.parentElement;

          const isOpen = body.classList.contains("open");

          // Cerrar todos
          document.querySelectorAll(".acordeon-body").forEach((b) =>
            b.classList.remove("open")
          );
          document.querySelectorAll(".acordeon-item").forEach((i) =>
            i.classList.remove("opened")
          );
          document
            .querySelectorAll(".acordeon-arrow")
            .forEach((a) => (a.style.transform = "rotate(0deg)"));

          // Abrir el seleccionado
          if (!isOpen) {
            body.classList.add("open");
            item.classList.add("opened");
            arrow.style.transform = "rotate(90deg)";
          }
        });
      });
    })
    .catch((err) => {
      console.error(err);
      content.innerHTML = `
        <div class="card">
          <h2 class="card-title">Mis cursos y notas</h2>
          <p>Error al cargar los datos.</p>
        </div>
      `;
    });
}




  // ====== NAV ====== (esto ya lo tenías)
  menuLinks.forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const section = a.getAttribute("data-section");
      load(section);

      if (sidebar && sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
        document.body.classList.remove("menu-open");
        if (overlay) overlay.style.display = "none";
      }
    });
  });
  // =======================================================
// AÑADIDO EXACTO (SIN MODIFICAR NADA DEL CÓDIGO EXISTENTE)
// =======================================================

// Detectar cambios de tamaño y ajustar layout si es necesario
window.addEventListener("resize", () => {
  const width = window.innerWidth;

  // si la pantalla es pequeña, cerrar sidebar
  if (width < 900) {
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("show");
  }
});

// Abrir/cerrar menú lateral
if (toggleBtn) {
  toggleBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
  });
}

// Cerrar sidebar al hacer click fuera
if (overlay) {
  overlay.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
  });
}
// Cerrar sidebar al hacer click fuera en vista móvil
document.addEventListener("click", (e) => {
  const isClickInsideSidebar = sidebar.contains(e.target);
  const isClickOnToggle = toggleBtn.contains(e.target);

  if (!isClickInsideSidebar && !isClickOnToggle && sidebar.classList.contains("open")) {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
  }
});


  // vista inicial
  load("dashboard");
});  
