from django.urls import path
from . import views

app_name = "inicioSesion"

# ----------------------------------------------------
# Rutas del módulo de inicio de sesión
# ----------------------------------------------------
urlpatterns = [
    # Ruta raíz de la app /inicioSesion/
    # Decide si enviar al login o al dashboard según estado de sesión
    path("", views.root_redirect, name="root_redirect"),

    # Página de login
    path("login/", views.login_view, name="login"),

    # Redirección después de iniciar sesión
    path("post_login/", views.post_login, name="post_login"),

    # Cerrar sesión
    path("logout/", views.logout_view, name="logout"),
    
    # 1. API que usa el Modal (Fetch JavaScript)
    path("auth/forgot/validate-family/", views.validate_family_and_send_link, name="validate_family"),
    
    # Página donde aterriza el link del correo (Nueva contraseña)
    path("reset/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
]
