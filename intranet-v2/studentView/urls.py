# studentView/urls.py
from django.urls import path
from . import views

app_name = "studentView"

urlpatterns = [
   path("", views.dashboard, name="dashboard"),
    path("perfil-data/", views.perfil_data, name="perfil_data"),
    path("mis-asignaturas/", views.mis_asignaturas, name="mis_asignaturas"),
    path("evaluaciones/", views.evaluaciones_mias, name="evaluaciones-alumno"),
    path("mis-notas/", views.mis_notas, name="mis-notas"),
    path("mis-notas-debug/", views.mis_notas_debug, name="mis-notas-debug"),
    path("validar-pin/", views.validar_pin, name="validar_pin"),
    path("obtener-pagos/", views.obtener_pagos, name="obtener_pagos"),
    path("close-pin/", views.close_pin, name="close_pin"),
    path('api/promedio/', views.api_promedio_alumno, name='api_promedio_alumno'),
    path("cambiar-pin/", views.cambiar_pin_apoderado, name="cambiar_pin"),
    path('api/proximas-evaluaciones/', views.api_proximas_evaluaciones, name='api_proximas_evaluaciones'),


    path(
        "iniciar-pago/<int:payment_id>/",
        views.iniciar_pago_getnet, 
        name="iniciar_pago_getnet",
    ),

    # RUTA 2: CONFIRMACIÓN WEBHOOK (Llamada por el servidor de Getnet)
    path("confirmacion-getnet/", views.confirmacion_getnet, name="confirmacion_getnet"), #

    # RUTA 3: RETORNO DEL CLIENTE (Llamada por el navegador del alumno)
    path("pago-finalizado/", views.pago_finalizado, name="pago_finalizado"),
    
]
