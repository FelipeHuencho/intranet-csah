from django.urls import path
from . import views

app_name = 'finanzas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),              # /finanzas/
    path('pagos/', views.api_pagos, name='api_pagos'),        # GET lista
    path('pagos/<int:pk>/aprobar/', views.api_aprobar, name='api_aprobar'),
    path('pagos/<int:pk>/rechazar/', views.api_rechazar, name='api_rechazar'),
]
