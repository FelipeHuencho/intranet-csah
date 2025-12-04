from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.http import JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
import json
import time
from .forms import LoginForm
from core.models import User, GuardianRelation, GuardianProfile


# ===========================================================
# Función: Redirige dashboard según rol
# ===========================================================
def role_redirect_name(user):
    """Retorna la ruta correspondiente según el rol del usuario."""

    if getattr(user, "role", None) == "admin":
        return "administrador:admin_dashboard"

    if user.is_superuser or user.is_staff:
        return "admin:index"

    if getattr(user, "role", None) == "teacher":
        return "profesorView:dashboard"

    if getattr(user, "role", None) == "student":
        return "studentView:dashboard"
    
    if getattr(user, "role", None) == "finance_admin":
        return "finanzas:dashboard_finanzas"

    return "inicioSesion:login"


# ===========================================================
# Redirección para la ruta raíz "/"
# ===========================================================
def root_redirect(request):
    """Envía al dashboard si está logueado, si no al login."""
    if request.user.is_authenticated:
        return redirect(role_redirect_name(request.user))
    return redirect("inicioSesion:login")


# ===========================================================
# Login con bloqueo de intentos + no-cache
# ===========================================================
@never_cache
def login_view(request):
    """Vista de login con:
        - Prevención de navegación con 'atrás'
        - Bloqueo tras múltiples intentos fallidos (por RUT)
        - Bloqueo tras múltiples intentos de enumeración (por IP)
        - Cookie para persistir estado de bloqueo tras F5/cerrar página
    """

    # Si ya está logeado, evita mostrar login
    if request.user.is_authenticated:
        return redirect(role_redirect_name(request.user))

    # Seguridad: límites (RUT)
    LOCK_TIME = 480     # 8 minutos 
    MAX_ATTEMPTS = 5
    
    # Seguridad: límites (IP)
    IP_LOCK_TIME = 300  # 5 minutos
    MAX_IP_ATTEMPTS = 10 # 10 intentos


    # -----------------------------------------------------------------
    # --- 1. BLOQUEO DE ACCESO POR IP (Check inicial y más severo) ---
    # -----------------------------------------------------------------
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    cache_key_ip = f"login_attempts_ip_{ip}"
    ip_attempts = cache.get(cache_key_ip, 0)
    
    # Checkear si la IP está bloqueada AHORA
    is_ip_locked = False
    ip_lock_remaining_seconds = 0
    
    if ip_attempts >= MAX_IP_ATTEMPTS:
        ip_lock_time_start = cache.get(f"{cache_key_ip}_time", time.time())
        ip_lock_remaining_seconds = max(0, IP_LOCK_TIME - int(time.time() - ip_lock_time_start))
        
        if ip_lock_remaining_seconds > 0:
            is_ip_locked = True
        else:
            # El tiempo de bloqueo de IP expiró, reiniciar contador de IP
            cache.delete(cache_key_ip)
            cache.delete(f"{cache_key_ip}_time")
            ip_attempts = 0 # resetear para el flujo de POST
    
    # -----------------------------------------------------------------
    # --- 2. Lógica de Bloqueo por RUT (pre-POST) ---
    # -----------------------------------------------------------------
    rut_input = (request.POST.get("rut") or request.COOKIES.get("last_rut") or "").strip()
    cache_key = f"login_attempts_{rut_input}" if rut_input else None

    rut_attempts = 0
    rut_elapsed = 0
    rut_lock_time_start = time.time() # Inicializar para evitar errores si no hay cache_key

    if cache_key:
        data = cache.get(cache_key, {"count": 0, "time": time.time()})
        rut_attempts = data["count"]
        rut_lock_time_start = data["time"]
        rut_elapsed = time.time() - rut_lock_time_start

    is_rut_locked = rut_attempts >= MAX_ATTEMPTS and rut_elapsed < LOCK_TIME
    rut_lock_remaining_seconds = max(0, LOCK_TIME - int(rut_elapsed)) if is_rut_locked else 0


    # =========================================================================
    # CONSOLIDACIÓN DE BLOQUEO (Bloqueo más severo prevalece para el render)
    # =========================================================================
    
    # El bloqueo será TRUE si está bloqueado por IP O por RUT
    locked = is_ip_locked or is_rut_locked
    
    # El tiempo restante es el del bloqueo que esté activo
    remaining_seconds = 0
    
    # Si IP está bloqueada y su tiempo restante es mayor que el de RUT, gana IP
    if is_ip_locked:
        remaining_seconds = ip_lock_remaining_seconds
        # Mensaje por defecto de bloqueo IP
        messages.error(request, f"Se detectó actividad sospechosa desde tu red (Exceso de intentos globales). Espera unos minutos.")
    
    # Si RUT está bloqueado y su tiempo restante es mayor o igual al de IP, o si IP no estaba bloqueada, gana RUT
    if is_rut_locked and rut_lock_remaining_seconds >= remaining_seconds:
        remaining_seconds = rut_lock_remaining_seconds
        # Mensaje por defecto de bloqueo RUT
        messages.error(request, "Demasiados intentos fallidos para este RUT. Espera unos minutos.")


    # =========================
    # 3. Procesamiento POST
    # =========================
    if request.method == "POST":
        form = LoginForm(request.POST)

        # Si el usuario ya está bloqueado (por IP o RUT), no procesamos la validación del formulario.
        if locked:
            # Re-renderizar con el estado de bloqueo actual. Los mensajes ya se cargaron arriba.
            pass
        
        elif form.is_valid():
            rut = form.cleaned_data["rut"]
            password = form.cleaned_data["password"]
            remember = form.cleaned_data["remember"]

            if not rut or not password:
                messages.error(request, "Debes ingresar tu RUT y contraseña.")
                return render(request, "login.html", {
                        "form": form,
                        "locked": locked,
                        "remaining_seconds": remaining_seconds,
                        })
                            
            

            # Actualizar datos de RUT/Cache si el formulario es válido
            cache_key = f"login_attempts_{rut}"
            data = cache.get(cache_key, {"count": 0, "time": time.time()})
            rut_attempts = data["count"]
            rut_lock_time_start = data["time"]
            rut_elapsed = time.time() - rut_lock_time_start
            is_rut_locked = rut_attempts >= MAX_ATTEMPTS and rut_elapsed < LOCK_TIME

            if is_rut_locked:
                messages.error(request, "Demasiados intentos fallidos. Espera unos minutos.")
            else:
                # Reiniciar bloque si ya pasó el tiempo
                if rut_attempts >= MAX_ATTEMPTS and rut_elapsed >= LOCK_TIME:
                    rut_attempts = 0

                # Validación usuario
                user = authenticate(request, username=rut, password=password)

                if user:
                    # ÉXITO: Iniciar sesión
                    login(request, user)
                    request.session.set_expiry(60*60*24*14 if remember else 0) 
                    cache.delete(cache_key)
                    
                    # Limpiar cache de IP al tener un login exitoso
                    cache.delete(cache_key_ip) 
                    cache.delete(f"{cache_key_ip}_time")

                    # Limpiar cookie RUT y redirigir
                    response = redirect(role_redirect_name(user))
                    response.delete_cookie("last_rut")
                    return response

                # 4. FALLO: Incrementar intentos
                # Incrementar intento fallido por RUT
                rut_attempts += 1
                cache.set(cache_key, {"count": rut_attempts, "time": time.time()}, LOCK_TIME)

                # Incrementar intento fallido global por IP (Anti-enumeración)
                ip_attempts += 1
                cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
                # Almacenar el tiempo de inicio del bloqueo de IP si alcanza el límite
                if ip_attempts >= MAX_IP_ATTEMPTS:
                    # Solo guardamos el tiempo de inicio cuando se alcanza el límite
                    cache.set(f"{cache_key_ip}_time", time.time(), IP_LOCK_TIME) 
                
                # Mostrar mensajes de error
                is_rut_locked = rut_attempts >= MAX_ATTEMPTS
                if is_rut_locked:
                    messages.error(request, "Has superado los intentos por este RUT. Espera unos minutos.")
                else:
                    messages.error(request, f"Credenciales incorrectas. Intento {rut_attempts}/{MAX_ATTEMPTS}")

                
            # Re-calcular estado de bloqueo final para el render
            locked = is_ip_locked or is_rut_locked
            
            # Recalcular el tiempo restante más severo
            rut_lock_remaining_seconds = max(0, LOCK_TIME - int(time.time() - cache.get(cache_key, {"time": 0})["time"])) if is_rut_locked else 0
            ip_lock_remaining_seconds = max(0, IP_LOCK_TIME - int(time.time() - cache.get(f"{cache_key_ip}_time", 0))) if is_ip_locked else 0
            
            remaining_seconds = max(rut_lock_remaining_seconds, ip_lock_remaining_seconds)
            
            # Si hay bloqueo, el mensaje ya se generó antes de form.is_valid() o se generó aquí
            
    else:
        form = LoginForm()

    # =========================
    # 5. Render del login
    # =========================
    response = render(request, "inicioSesion/login.html", {
        "form": form,
        "locked": locked,              # Booleano: True si está bloqueado por RUT o IP
        "remaining_seconds": remaining_seconds, # Tiempo restante del bloqueo activo
    })

    # Guardar cookie para mantener bloqueo entre recargas
    if rut_input:
        response.set_cookie("last_rut", rut_input, max_age=600, samesite="Strict")

    # Evitar caché del navegador
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


# ===========================================================
# Logout
# ===========================================================
@login_required
def logout_view(request):
    """Cerrar sesión limpiamente y mostrar mensaje."""
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("inicioSesion:login")


# Sólo para compatibilidad / redirecciones internas
@login_required
def post_login(request):
    return redirect(role_redirect_name(request.user))


def validate_family_and_send_link(request):
    """
    API protegida con Rate Limiting por IP.
    Recibe JSON con datos y envía un correo con link de reset si todo coincide.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)

    # === 1. RATE LIMITING POR IP (Anti-Spam de Correos) ===
    IP_LOCK_TIME = 300 
    MAX_IP_ATTEMPTS = 2

    # Obtener IP real
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    cache_key_ip = f"reset_attempts_ip_{ip}"
    ip_attempts = cache.get(cache_key_ip, 0)

    # Bloqueo IP
    if ip_attempts >= MAX_IP_ATTEMPTS:
        return JsonResponse({
            "ok": False,
            "msg": "Has superado los intentos de recuperación. Por favor, espera unos minutos."
        }, status=429)

    # Incrementar antes de procesar errores
    ip_attempts += 1

    try:
        data = json.loads(request.body)
        recovery_type = data.get('type')  # 'student' o 'staff'

        user_target = None
        email_destino = None

        # ==========================================================
        # 1. VALIDACIÓN TIPO ALUMNO (Apoderado)
        # ==========================================================
        if recovery_type == 'student':
            rut_alumno = data.get('rut_alumno', '').upper().strip()
            rut_apoderado = data.get('rut_apoderado', '').upper().strip()
            correo_apoderado = data.get('correo', '').strip().lower()

            try:
                alumno = User.objects.get(rut=rut_alumno, role='student')
            except User.DoesNotExist:
                cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
                return JsonResponse({"ok": False, "msg": "Los datos ingresados no coinciden con un registro."}, status=400)

            relation = GuardianRelation.objects.filter(
                student=alumno,
                guardian__rut=rut_apoderado,
                guardian__email=correo_apoderado
            ).first()

            if not relation:
                cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
                return JsonResponse({"ok": False, "msg": "Los datos del apoderado no coinciden con el alumno."}, status=400)

            user_target = alumno
            email_destino = correo_apoderado

        # ==========================================================
        # 2. VALIDACIÓN STAFF (Profesor/Admin)
        # ==========================================================
        elif recovery_type == 'staff':
            rut_usuario = data.get('rut_usuario', '').upper().strip()
            correo = data.get('correo', '').strip().lower()

            try:
                staff_user = User.objects.exclude(role='student').get(rut=rut_usuario, email=correo)

                if not staff_user.is_active:
                    cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
                    return JsonResponse({"ok": False, "msg": "Esta cuenta está desactivada."}, status=400)

                user_target = staff_user
                email_destino = correo

            except User.DoesNotExist:
                cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
                return JsonResponse({"ok": False, "msg": "Los datos ingresados no coinciden con un registro."}, status=400)

        else:
            cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
            return JsonResponse({"ok": False, "msg": "Tipo de recuperación inválido"}, status=400)

        # ==========================================================
        # 3. ENVÍO DEL CORREO con mensaje personalizado
        # ==========================================================
        if user_target and email_destino:

            # Token + URL
            token = default_token_generator.make_token(user_target)
            uid = urlsafe_base64_encode(force_bytes(user_target.pk))

            domain = request.get_host()
            link = reverse('inicioSesion:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            reset_url = f"http://{domain}{link}"

            asunto = "Restablecer Contraseña - Colegio San Agustín de Hipona"

            # ===============================
            # MENSAJE SEGÚN EL TIPO
            # ===============================
            if recovery_type == "student":
                mensaje = f"""
Estimado/a Apoderado(a),

Se ha solicitado restablecer la contraseña del alumno con RUT: {user_target.rut}.

Para continuar con el proceso, haga clic en el siguiente enlace:

{reset_url}

Si usted no solicitó este cambio, puede ignorar este mensaje.

Atentamente,
Equipo de Soporte
"""
            else:
                mensaje = f"""
Estimado/a {user_target.first_name},

Hemos recibido una solicitud para restablecer la contraseña de su cuenta (RUT: {user_target.rut}).

Para generar una nueva contraseña, por favor utilice el siguiente enlace:

{reset_url}

Si usted no solicitó este cambio, puede ignorar este mensaje.

Atentamente,
Equipo de Soporte
"""

            # Enviar correo
            send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [email_destino], fail_silently=False)

            # Guardar intento
            cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)

            return JsonResponse({"ok": True, "msg": "Correo enviado."})

    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "msg": "Solicitud JSON inválida."}, status=400)

    except Exception as e:
        cache.set(cache_key_ip, ip_attempts, IP_LOCK_TIME)
        print(f"Error en recuperación de contraseña: {e}")
        return JsonResponse({"ok": False, "msg": "Ocurrió un error interno. Intente más tarde."}, status=500)





# ===========================================================
#  VISTA: Ingresar Nueva Contraseña (Link del Correo)
# ===========================================================
def password_reset_confirm(request, uidb64, token):
    """
    Vista a la que llega el usuario tras hacer clic en el correo.
    Valida el token y permite setear password y opcionalmente el PIN del apoderado.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True

        if request.method == 'POST':
            new_pass = request.POST.get('password')
            confirm_pass = request.POST.get('confirm_password')
            new_pin = request.POST.get('guardian_payment_pin')  # PIN opcional

            # -----------------------------
            # Validaciones de datos
            # -----------------------------
            if not new_pass or not confirm_pass:
                messages.error(request, "Por favor, completa ambos campos.")
            elif new_pass != confirm_pass:
                messages.error(request, "Las contraseñas no coinciden.")
            elif len(new_pass) < 4:
                messages.error(request, "La contraseña es muy corta.")
            elif new_pin and len(new_pin) < 4:
                messages.error(request, "El PIN debe tener al menos 4 dígitos.")
            else:
                # -----------------------------
                # 1️ Cambiar contraseña del usuario
                # -----------------------------
                user.set_password(new_pass)
                user.save()

                # -----------------------------
                # 2️ Si el usuario es alumno → cambiar PIN del apoderado
                # -----------------------------
                if new_pin and user.role == User.STUDENT:
                    guardian_relation = user.student_relations.first()
                    if guardian_relation:
                        guardian = guardian_relation.guardian

                        # Obtener o crear el profile correcto del apoderado
                        profile, _ = GuardianProfile.objects.get_or_create(user=guardian)
                        profile.payment_pin = new_pin
                        profile.save(update_fields=["payment_pin"])

                # -----------------------------
                # 3️ Finalizar
                # -----------------------------
                messages.success(
                    request,
                    "¡Contraseña (y PIN si lo ingresaste) actualizados correctamente! Ahora puedes iniciar sesión."
                )
                return redirect('inicioSesion:login')

    else:
        validlink = False

    return render(request, 'inicioSesion/password_reset_form.html', {'validlink': validlink})





