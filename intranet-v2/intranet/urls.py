
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from django.contrib.auth import views as auth_views
from inicioSesion import views as is_views
from inicioSesion.views import root_redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),  
    path('inicioSesion/', include('inicioSesion.urls')),
    path('', root_redirect),
    path('', LoginView.as_view(template_name='inicioSesion/login.html'), name='login'),
    path('studentView/', include('studentView.urls')),
    path('adminview/', include('adminView.urls')), 
    path('profesorView/', include('profesorView.urls')),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('finanzas/', include('finanzas.urls')),

    
]
