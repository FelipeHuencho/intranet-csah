# finanzas/urls.py
from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    path("", views.dashboard_finanzas, name="dashboard_finanzas"),

    # API SPA - Solo quedan cuotas y estadísticas basadas en Payment (flujo real)
    path("api/cuotas-pendientes/", views.cuotas_pendientes, name="cuotas_pendientes"),

    # Estadísticas
    path("api/pagos-por-mes/", views.api_pagos_por_mes, name="api_pagos_por_mes"),

    # Las siguientes rutas relacionadas a comprobantes manuales fueron eliminadas.
    # path("api/comprobantes/", views.api_comprobantes, name="api_comprobantes"),
    # path("comprobante/<int:pk>/aprobar/", views.aprobar_comprobante, name="aprobar_comprobante"),
    # path("comprobante/<int:pk>/rechazar/", views.rechazar_comprobante, name="rechazar_comprobante"),
    # path("ver-comprobante/<int:pk>", views.ver_comprobante, name="ver_comprobante"),
    # path("comprobante/<int:pk>/revertir/", views.revertir_comprobante, name="revertir_pago"),
    # path("api/estadisticas/", views.api_estadisticas_mensuales, name="estadisticas"),
    # path("api/comprobantes-por-mes/", views.api_comprobantes_por_mes, name="api_comprobantes_por_mes"),
]