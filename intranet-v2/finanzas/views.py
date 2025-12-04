from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from core.models import User, Payment 
from django.db.models.functions import ExtractMonth
from django.db.models import Count


def finance_required(user):
    return user.is_authenticated and user.role == User.FINANCE_ADMIN


@login_required
@user_passes_test(finance_required)
def dashboard_finanzas(request):
    # Esta vista solo carga Finanzas.html
    return render(request, "finanzas/Finanzas.html")


@login_required
def cuotas_pendientes(request):
    cuotas = Payment.objects.filter(
        status__in=["pending", "rejected"]
    ).select_related("student")
    
    data = [
        {
            "id": p.id,
            "alumno": f"{p.student.first_name} {p.student.last_name}",
            "rut": p.student.rut,
            "concept": p.concept,
            "monto": int(p.amount),
            "fecha_vencimiento": p.due_date.strftime("%d-%m-%Y") if p.due_date else "",
            "status": p.status,   
        }
        for p in cuotas
    ]

    return JsonResponse({"cuotas": data})


@login_required
@user_passes_test(finance_required)
def api_pagos_por_mes(request):
    pagos = (
        Payment.objects
        .filter(status="paid", paid_at__isnull=False)
        .annotate(month=ExtractMonth("paid_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    data = [0] * 12

    for item in pagos:
        if item["month"]:
            data[item["month"] - 1] = item["total"]

    return JsonResponse({
        "labels": labels,
        "data": data
    })