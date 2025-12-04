/* =======================================================
   LÓGICA DE VALIDACIÓN DE CONTRASEÑA
   Archivo: password_reset_form.js
   ======================================================= */

// Esperamos a que todo el HTML se cargue antes de ejecutar el código
document.addEventListener('DOMContentLoaded', function() {
    
    // Obtenemos referencias a los elementos del formulario
    const pass1 = document.getElementById('pass1'); // Input Contraseña nueva
    const pass2 = document.getElementById('pass2'); // Input Repetir contraseña
    const msg = document.getElementById('match-msg'); // Mensaje de error/éxito pequeño
    const btn = document.getElementById('submitBtn'); // Botón de enviar
    const form = document.getElementById('resetForm'); // El formulario completo

    // Solo ejecutamos si los elementos existen (para evitar errores en otras páginas)
    if (pass1 && pass2) {
        
        // Función principal que valida si coinciden y cumplen el largo
        function validar() {
            const v1 = pass1.value;
            const v2 = pass2.value;

            // Reglas: Ambas deben tener 8 o más caracteres y ser iguales
            const isLengthValid = v1.length >= 8 && v2.length >= 8;
            const isMatch = v1 === v2;
            
            // Lógica cuando el usuario ya escribió algo en el segundo campo
            if (v2.length > 0) {
                if (isLengthValid && isMatch) {
                    // CASO ÉXITO: Coinciden y son largas
                    pass2.classList.remove('invalid');
                    pass2.classList.add('valid');
                    msg.textContent = "Las contraseñas coinciden";
                    msg.style.color = "#10b981"; // Verde
                    btn.disabled = false; // Habilitar botón

                } else if (v1 !== v2) {
                    // ERROR: No son iguales
                    pass2.classList.remove('valid');
                    pass2.classList.add('invalid');
                    msg.textContent = "Las contraseñas no coinciden";
                    msg.style.color = "#ef4444"; // Rojo
                    btn.disabled = true; // Bloquear botón

                } else if (!isLengthValid) {
                    // ERROR: Son iguales pero muy cortas
                    pass2.classList.remove('valid');
                    pass2.classList.add('invalid');
                    msg.textContent = "La longitud mínima es 8 caracteres.";
                    msg.style.color = "#ef4444"; // Rojo
                    btn.disabled = true; // Bloquear botón
                }
            } else {
                // Si borra el segundo campo, limpiamos los estilos
                pass2.classList.remove('valid', 'invalid');
                msg.textContent = "";
                btn.disabled = false; // Dejamos el botón activo para que HTML5 maneje el "required"
            }
        }

        // "Escuchamos" cada vez que el usuario escribe en los campos
        pass1.addEventListener('input', validar);
        pass2.addEventListener('input', validar);
        
        // Verificación inicial: Si entra a la página y los campos están vacíos/cortos, bloqueamos
        if (pass1.value.length < 8 || pass2.value.length < 8) {
            btn.disabled = true;
        }
    }
});