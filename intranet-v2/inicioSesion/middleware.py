from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.conf import settings

class LoginRequiredMiddleware:
    """
    Middleware que protege el sitio completo.
    
    Funciones principales:
    - Obliga a autenticarse para acceder a cualquier vista protegida.
    - Permite acceso libre a rutas específicas (login, logout, admin, estáticos, etc.).
    - Impide volver a páginas autenticadas usando el botón "Atrás" del navegador
      mediante cabeceras anti-cache.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Rutas que pueden ser accedidas sin autenticación por prefijo
        self.exempt_prefixes = (
            "/admin/",
            "/static/",
            "/media/",
            "/favicon.ico",
            "/inicioSesion/reset/",
            "/inicioSesion/auth/", # Libera todas las rutas de autenticación/API
        )

        # Nombres de rutas que NO requieren sesión
        # (importante: deben existir en urls.py)
        self.exempt_names = {
            "inicioSesion:login",
            "inicioSesion:post_login",
            "inicioSesion:logout",
            "inicioSesion:diag_login",
            "admin:login",
            "inicioSesion:validate_family"
        }

        # Convertir nombres de rutas en paths para comparación directa
        self.exempt_paths = set()
        for name in self.exempt_names:
            try:
                self.exempt_paths.add(reverse(name))
            except Exception:
                pass

    def _no_cache(self, response):
        """
        Fuerza al navegador a no guardar caché para evitar volver
        a páginas privadas con el botón Atrás.
        """
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

    def __call__(self, request):
        path = request.path

        # 1) Acceso libre al panel admin
        if path.startswith("/admin"):
            response = self.get_response(request)
            return self._no_cache(response)

        # 2) Acceso libre a archivos estáticos / media / Prefijos exentos
        if any(path.startswith(p) for p in self.exempt_prefixes):
            return self.get_response(request)

        # 3) Acceso libre a rutas explícitamente exentas
        if path in self.exempt_paths:
            response = self.get_response(request)
            return self._no_cache(response)

        # 4) Detectar vista por nombre (namespace:url_name)
        try:
            resolved = resolve(path)
            urlname = (
                f"{resolved.namespace}:{resolved.url_name}"
                if resolved.namespace else resolved.url_name
            )
        except Exception:
            urlname = None

        if urlname in self.exempt_names:
            response = self.get_response(request)
            return self._no_cache(response)

        # 5) Usuario autenticado
        if request.user.is_authenticated:

            # Si intenta acceder al login estando logueado -> redirigir a dashboard según rol
            try:
                if path == reverse("inicioSesion:login"):
                    # Si es staff/superuser usar admin nativo
                    if request.user.is_superuser or request.user.is_staff:
                        return redirect("/admin/")

                    role = getattr(request.user, "role", None)
                    if role == "admin":
                        return redirect(reverse("administrador:admin_dashboard"))
                    if role == "teacher":
                        return redirect(reverse("profesorView:dashboard"))
                    if role == "student":
                        return redirect(reverse("studentView:dashboard"))
                    if role == "finance_admin":
                        return redirect("/finanzas/")


                    return redirect("/")
            except Exception:
                return redirect("/")

            # Si está autenticado y no es login -> permitir y evitar caché
            response = self.get_response(request)
            return self._no_cache(response)

        # 6) Usuario NO autenticado -> mandar a login
        try:
            login_url = reverse(settings.LOGIN_URL)
        except Exception:
            login_url = "/inicioSesion/login/"

        # Guardar "next" para redirigir después del login
        if path != login_url:
            return redirect(f"{login_url}?next={request.get_full_path()}")

        # 7) Página de login también sin caché
        response = self.get_response(request)
        return self._no_cache(response)