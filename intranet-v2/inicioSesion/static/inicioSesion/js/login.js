document.addEventListener('DOMContentLoaded', function() {

  window.loginLocked = (window.loginLocked === "True" || window.loginLocked === "true");
  window.lockSeconds = parseInt(window.lockSeconds || "0");
  
  // ==========================================
  // 1. FORMATO RUT AUTOMÁTICO (XX.XXX.XXX-X)
  // ==========================================
  function aplicarFormatoRut(inputElement) {
    if (!inputElement) return;

    inputElement.addEventListener('input', function(e) {
      let valor = e.target.value;

      // Limpiar: Eliminar cualquier caracter que NO sea número o K
      valor = valor.replace(/[^0-9kK]/g, "");

      // Limitar largo máximo
      if (valor.length > 9) {
        valor = valor.slice(0, 9);
      }

      // Lógica de formato visual
      if (valor.length > 1) {
        const cuerpo = valor.slice(0, -1);
        const dv = valor.slice(-1).toUpperCase();
        // Poner puntos
        const cuerpoFormateado = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        e.target.value = `${cuerpoFormateado}-${dv}`;
      } else {
        e.target.value = valor;
      }
    });
  }

  // APLICAR A TODOS LOS INPUTS DE RUT 
  // (Login + Modal Alumno + Modal Profe - Agregamos #rut-staff aquí)
  const inputsRut = document.querySelectorAll('#id_rut, #rut-alumno, #rut-apoderado, #rut-staff');
  inputsRut.forEach(function(input) {
    aplicarFormatoRut(input);
  });


  // ==========================================
  // 2. TOGGLE PASSWORD (Ver/Ocultar)
  // ==========================================
  const togglePassword = document.querySelector('#toggle-password');
  const passwordInput = document.querySelector('#id_password');

  if (togglePassword && passwordInput) {
    togglePassword.style.cursor = 'pointer';

    togglePassword.addEventListener('click', function() {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);

      const svg = togglePassword.querySelector('svg');
      if (type === 'text') {
        // Ícono Ojo Tachado
        svg.innerHTML = `
          <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
          <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
          <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
          <line x1="2" x2="22" y1="2" y2="22"/>`;
        svg.setAttribute('viewBox', '0 0 24 24');
      } else {
        // Ícono Ojo Normal
        svg.innerHTML = `
          <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/>
          <circle cx="12" cy="12" r="3"/>`;
      }
    });
  }

  // ==========================================
  // 3. LÓGICA DEL MODAL "OLVIDASTE CONTRASEÑA"
  // ==========================================
  const forgotLink = document.getElementById("forgot-link");
  const forgotModal = document.getElementById("forgot-modal");

  // Helper para CSRF Token
  function getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let c of cookies) {
      c = c.trim();
      if (c.startsWith(name + "=")) {
        return decodeURIComponent(c.substring(name.length + 1));
      }
    }
    return "";
  }

  if (forgotLink && forgotModal) {
    const steps = {
      rut: forgotModal.querySelector(".step-rut"),
      email: forgotModal.querySelector(".step-email"),
    };

    // Función para mostrar pasos (Formulario -> Éxito)
    function showStep(name) {
      Object.values(steps).forEach(s => s && (s.style.display = "none"));
      if (steps[name]) steps[name].style.display = "block";
      forgotModal.querySelectorAll(".estado").forEach(e => e.textContent = "");
    }

    function resetForgotModal() {
      // Limpiar todos los inputs (text, email)
      const inputs = forgotModal.querySelectorAll("input:not([type='radio'])");
      inputs.forEach(i => i.value = "");
      
      // Resetear radios a "student" por defecto
      const radioStudent = forgotModal.querySelector('input[value="student"]');
      if (radioStudent) radioStudent.checked = true;
      
      // Resetear visibilidad de campos (mostrar student, ocultar staff)
      const fStudent = document.getElementById('fields-student');
      const fStaff = document.getElementById('fields-staff');
      if(fStudent) fStudent.style.display = 'block';
      if(fStaff) fStaff.style.display = 'none';

      showStep("rut");
    }

    // Abrir/Cerrar Modal
    function openForgot() {
      forgotModal.classList.add("show");
      resetForgotModal();
    }
    function closeForgot() {
      forgotModal.classList.remove("show");
      resetForgotModal();
    }

    forgotLink.addEventListener("click", (e) => {
      e.preventDefault();
      openForgot();
    });

    forgotModal.querySelectorAll(".btn-cancel").forEach(btn => {
      btn.addEventListener("click", closeForgot);
    });

    // ---------------------------------------------------------
    // A) DETECTAR CAMBIO DE ROL (ALUMNO vs STAFF)
    // ---------------------------------------------------------
    const radios = document.querySelectorAll('input[name="recovery_role"]');
    const fieldsStudent = document.getElementById('fields-student');
    const fieldsStaff = document.getElementById('fields-staff');
    const estadoMsg = forgotModal.querySelector(".estado");

    radios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        const role = e.target.value;
        if(estadoMsg) estadoMsg.textContent = ""; // Limpiar errores al cambiar
        
        if (role === 'student') {
          if(fieldsStudent) fieldsStudent.style.display = 'block';
          if(fieldsStaff) fieldsStaff.style.display = 'none';
        } else {
          if(fieldsStudent) fieldsStudent.style.display = 'none';
          if(fieldsStaff) fieldsStaff.style.display = 'block';
        }
      });
    });

    // ---------------------------------------------------------
    // B) ENVIAR FORMULARIO AL BACKEND
    // ---------------------------------------------------------
    const formStepRut = forgotModal.querySelector("#form-step-rut");
    if (formStepRut) {
      formStepRut.addEventListener("submit", (e) => {
        e.preventDefault();
        
        // 1. Verificar qué rol está seleccionado
        const roleRadio = document.querySelector('input[name="recovery_role"]:checked');
        const roleSelected = roleRadio ? roleRadio.value : 'student';
        
        let payload = {};

        // 2. Recolectar datos según selección
        if (roleSelected === 'student') {
            const rutA = document.getElementById("rut-alumno")?.value.trim();
            const rutP = document.getElementById("rut-apoderado")?.value.trim();
            const mailP = document.getElementById("correo-apoderado")?.value.trim();

            if (!rutA || !rutP || !mailP) {
                if(estadoMsg) estadoMsg.textContent = "Por favor completa todos los campos del alumno/apoderado.";
                return;
            }
            payload = { type: 'student', rut_alumno: rutA, rut_apoderado: rutP, correo: mailP };

        } else {
            // Caso STAFF
            const rutS = document.getElementById("rut-staff")?.value.trim();
            const mailS = document.getElementById("correo-staff")?.value.trim();

            if (!rutS || !mailS) {
                if(estadoMsg) estadoMsg.textContent = "Por favor ingresa tu RUT y correo.";
                return;
            }
            payload = { type: 'staff', rut_usuario: rutS, correo: mailS };
        }

        if(estadoMsg) estadoMsg.textContent = "Validando datos...";

        // 3. Enviar a Django
        fetch("/inicioSesion/auth/forgot/validate-family/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify(payload)
        })
        .then(async (r) => {
          // Verificar si no es JSON (error 500 html, etc)
          const ct = r.headers.get("content-type") || "";
          if (!ct.includes("application/json")) {
             console.error("Respuesta no es JSON", await r.text());
             return { ok: false, msg: "Error del servidor." };
          }
          return r.json();
        })
        .then(data => {
          if (data.ok) {
            // Éxito: Mostrar paso de correo enviado
            showStep("email");
          } else {
            // Error: Mostrar mensaje rojo
            if(estadoMsg) estadoMsg.textContent = data.msg || "Datos incorrectos.";
          }
        })
        .catch(err => {
          console.error("Error fetch:", err);
          if(estadoMsg) estadoMsg.textContent = "Error de conexión.";
        });
      });
    }
  }
// ==========================================
// 4. VALIDACIÓN DEL FORMULARIO DE LOGIN
// ==========================================
const loginForm = document.querySelector('.form-box');  // tu <form> de login

if (loginForm) {
    loginForm.addEventListener('submit', function(e) {
        const rutInput = document.querySelector('#id_rut');
        const passInput = document.querySelector('#id_password');

        const rutVal = rutInput?.value.trim();
        const passVal = passInput?.value.trim();

        if (!rutVal || !passVal) {
            e.preventDefault();
            alert("Debes ingresar RUT y contraseña.");
        }
    });
}

//  BLOQUEO DE BOTÓN + CUENTA REGRESIVA

const btnLogin = document.getElementById("btn-login");
let locked = window.loginLocked;
let secondsRemaining = parseInt(window.lockSeconds || "0"); // en segundos

function startLockCountdown() {
    if (!locked || !btnLogin || secondsRemaining <= 0) return;

    btnLogin.disabled = true;
    btnLogin.classList.add("btn-locked"); // estilo gris

    // Mostrar contador inmediatamente
    const minutes = Math.floor(secondsRemaining / 60);
    const seconds = secondsRemaining % 60;
    btnLogin.textContent = `Vuelve a intentar en: ${minutes}:${seconds.toString().padStart(2,'0')}`;

    const interval = setInterval(() => {
        secondsRemaining--;
        const minutes = Math.floor(secondsRemaining / 60);
        const seconds = secondsRemaining % 60;

        if (secondsRemaining < 0) {
            clearInterval(interval);
            btnLogin.disabled = false;
            btnLogin.classList.remove("btn-locked");
            btnLogin.textContent = "Iniciar sesión";
        } else {
            btnLogin.textContent = `Vuelve a intentar en: ${minutes}:${seconds.toString().padStart(2,'0')}`;
        }
    }, 1000);
}


// Ejecutar al cargar la página
startLockCountdown();


  // Reload si viene de cache (back button fix)
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) window.location.reload();
  });
});