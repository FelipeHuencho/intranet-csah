from django.shortcuts import render
from django.http import JsonResponse, HttpResponse 
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import datetime 
from django.utils import timezone
import json # Necesario para leer el JSON que envía Getnet en el webhook
from .getnet_service import GetnetService 
from core.models import (
    Enrollment,
    GuardianRelation,
    Subject,
    SubjectSchedule,
    Evaluation,
    GradeResult,
    Payment,

)


# ============================
# DASHBOARD DEL ALUMNO
# ============================
@login_required
def dashboard(request):
    user = request.user

    enrollment = (
        Enrollment.objects
        .select_related("class_group__grade")
        .filter(student=user, active_status="active")
        .first()
    )

    curso = enrollment.class_group.grade.curso_nombre if enrollment else "Sin curso asignado"

    context = {
        "nombre": f"{user.first_name} {user.last_name}",
        "rut": user.rut,
        "email": user.email,
        "rol": user.get_role_display(),
        "estado": user.active_status,
        "curso": curso,
    }

    return render(request, "studentView/student.html", context)


# ============================
# PERFIL DEL ALUMNO
# ============================
@login_required
def perfil_data(request):
    user = request.user

    if user.role != "student":
        return JsonResponse({"error": "Solo alumnos pueden acceder a este perfil."}, status=403)

    enrollment = (
        Enrollment.objects.filter(student=user, active_status="active")
        .select_related("class_group__grade")
        .first()
    )

    curso = enrollment.class_group.grade.curso_nombre if enrollment else "--"

    relation = GuardianRelation.objects.filter(student=user).select_related("guardian").first()

    apoderado_data = {}
    if relation:
        apoderado = relation.guardian
        apoderado_data = {
            "apoderado_nombre": f"{apoderado.first_name} {apoderado.last_name}",
            "apoderado_parentesco": getattr(apoderado, "relationship", "--"),
            "apoderado_telefono": apoderado.phone or "--",
            "apoderado_correo": apoderado.email or "--",
        }

    data = {
        "nombre": f"{user.first_name} {user.last_name}",
        "username": user.first_name.lower(),
        "email": user.email or "--",
        "rut": user.rut or "--",
        "curso": curso,
        "telefono": user.phone or "--",
        **apoderado_data,
    }

    return JsonResponse(data)

# ============================
# MIS ASIGNATURAS (CON HORARIOS)
# ============================
@login_required
def mis_asignaturas(request):
    user = request.user

    enrollment = (
        Enrollment.objects
        .select_related("class_group")
        .filter(student=user, active_status="active")
        .first()
    )

    if not enrollment:
        return JsonResponse({"asignaturas": [], "detalle": "Sin curso asignado"}, status=200)

    class_group = enrollment.class_group

    subjects = (
        Subject.objects
        .filter(class_group=class_group)
        .order_by("name")
    )

    data = []
    for sub in subjects:
        horarios = list(
            SubjectSchedule.objects
            .filter(subject=sub)
            .values("day_of_week", "start_time", "end_time")
            .order_by("day_of_week", "start_time")
        )
        data.append({
            "id": sub.id,
            "nombre": sub.name,
            "profesor": f"{sub.teacher.first_name} {sub.teacher.last_name}" if sub.teacher else "--",
            "horarios": horarios,
        })

    return JsonResponse({"asignaturas": data})

# ============================
# EVALUACIONES (CALENDARIO)
# ============================
@login_required
def evaluaciones_mias(request):
    alumno = request.user

    class_ids = (
        Enrollment.objects
        .filter(student=alumno, active_status="active")
        .values_list("class_group_id", flat=True)
    )

    evals = (
        Evaluation.objects
        .filter(class_group_id__in=class_ids)
        .select_related("subject", "class_group", "evaluation_type", "class_group__grade")
        .order_by("date")
    )

    data = []
    for ev in evals:
        curso_nombre = ""
        if ev.class_group and ev.class_group.grade:
            curso_nombre = f"{ev.class_group.grade.curso_nombre} {ev.class_group.year}"

        data.append({
            "id": ev.id,
            "title": f"{ev.subject.name} - {ev.description}",
            "start": ev.date.isoformat(),
            "allDay": True,
            "curso": curso_nombre,
            "tipo": getattr(ev.evaluation_type, "name", ""),
        })

    return JsonResponse(data, safe=False)


# ============================
# MIS NOTAS
# ============================
@login_required
def mis_notas(request):
    user = request.user

    resultados = (
        GradeResult.objects
        .select_related("evaluation", "evaluation__subject")
        .filter(student=user)
        .order_by("evaluation__subject__name", "evaluation__date")
    )

    materias = {}
    for gr in resultados:
        ev = gr.evaluation
        nombre_asig = ev.subject.name

        materias.setdefault(nombre_asig, []).append({
            "score": float(gr.score),
            "description": ev.description,
            "date": ev.date.isoformat() if ev.date else None,
        })

    data = [
        {"asignatura": nombre, "notas": notas}
        for nombre, notas in materias.items()
    ]

    return JsonResponse({"notas": data})


@login_required
def mis_notas_debug(request):
    """Devuelve TODO lo que Django ve de GradeResult para este usuario, sin agrupar."""
    user = request.user
    qs = (
        GradeResult.objects
        .select_related("evaluation", "evaluation__subject")
        .filter(student=user)
        .order_by("evaluation__date")
    )

    raw = []
    for gr in qs:
        raw.append({
            "id": gr.id,
            "score": float(gr.score),
            "evaluation_id": gr.evaluation_id,
            "evaluation_description": gr.evaluation.description,
            "subject": gr.evaluation.subject.name,
            "date": gr.evaluation.date.isoformat() if gr.evaluation.date else None,
        })

    return JsonResponse({"raw": raw}, safe=True)


# ============================
# VALIDAR PIN APODERADO
# ============================
@login_required
@csrf_exempt
def validar_pin(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    pin = None

    # 1) Intentar leer desde form-data (x-www-form-urlencoded o form-data)
    pin = request.POST.get("pin")

    # 2) Si no viene en POST, intentar leer como JSON
    if not pin and request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
            pin = data.get("pin")
        except Exception:
            pin = None

    if not pin:
        return JsonResponse({"success": False, "message": "PIN requerido"})

    alumno = request.user

    if alumno.role != "student":
        return JsonResponse({"success": False, "message": "Solo estudiantes pueden usar este portal"})

    guardianes = (
        GuardianRelation.objects
        .filter(student=alumno)
        .select_related("guardian")
    )

    for rel in guardianes:
        guardian = rel.guardian
        profile = guardian.gprofile  # crea/obtiene el GuardianProfile
        if profile and profile.payment_pin == pin:
            request.session["pagos_autorizados"] = True
            return JsonResponse({"success": True})

    return JsonResponse({"success": False, "message": "PIN incorrecto"})



# ============================
# OBTENER PAGOS DEL ALUMNO (PORTAL APODERADO)
# ============================
@login_required
def obtener_pagos(request):
    student = request.user

    if not request.session.get("pagos_autorizados", False):
        return JsonResponse({"error": "Acceso no autorizado"}, status=403)

    relation = GuardianRelation.objects.filter(student=student).select_related("guardian").first()
    if not relation:
        return JsonResponse({"error": "No se encontró apoderado asociado"}, status=400)

    guardian = relation.guardian

    pagos = Payment.objects.filter(student=student).order_by("due_date")

    data = [{
        "id": p.id,
        "concept": p.concept,
        "amount": float(p.amount),
        "due_date": p.due_date.strftime("%d-%m-%Y") if p.due_date else None,
        "status": p.status,
    } for p in pagos]

    return JsonResponse({
        "apoderado": f"{guardian.first_name} {guardian.last_name}",
        "alumno": f"{student.first_name} {student.last_name}",
        "pagos": data,
    })


# ============================
# CERRAR ACCESO DE APODERADO
# ============================
@login_required
@csrf_exempt
def close_pin(request):
    if "pagos_autorizados" in request.session:
        del request.session["pagos_autorizados"]

    return JsonResponse({"success": True})



# ============================
# 1.  INICIAR PAGO GETNET (Implementación real)
# ============================
import traceback
import logging

logger = logging.getLogger(__name__)  # usa el logger de Django

@login_required
@require_POST
def iniciar_pago_getnet(request, payment_id):
    try:
        if not request.session.get("pagos_autorizados", False):
            logger.warning(f"Acceso no autorizado para user {request.user.id}")
            return JsonResponse({"success": False, "error": "Acceso no autorizado. Ingrese el PIN de apoderado."}, status=403)

        student = request.user
        try:
            payment = Payment.objects.get(id=payment_id, student=student)
        except Payment.DoesNotExist:
            logger.warning(f"Cuota no encontrada o no pertenece al alumno {student.id}: Payment ID {payment_id}")
            return JsonResponse({"success": False, "error": "Cuota no encontrada o no pertenece al alumno."}, status=404)

        if payment.status in ["paid", "pending_review"]:
            logger.info(f"Intento de pago sobre cuota ya pagada o en revisión: Payment ID {payment_id}, status {payment.status}")
            return JsonResponse({"success": False, "error": f"La cuota ya está en estado '{payment.status}'."}, status=400)

        logger.info(f"Creando transacción Getnet para Payment ID {payment_id}, alumno {student.id}")
        getnet_service = GetnetService()
        result = getnet_service.create_transaction(payment, student_email=student.email)

        logger.debug(f"Resultado GetnetService: {result}")

        if result["success"]:
            payment.getnet_request_id = result["buy_order"]
            payment.getnet_token = result["request_token"]
            payment.status = "pending_review"
            payment.save()
            logger.info(f"Transacción creada exitosamente para Payment ID {payment_id}")
            return JsonResponse({"success": True, "redirect_url": result["redirect_url"]})
        else:
            logger.error(f"Error al crear transacción Getnet: {result['error']}")
            return JsonResponse({"success": False, "error": f"Error de Getnet: {result['error']}"}, status=500)

    except Exception as e:
        logger.exception(f"Excepción inesperada en iniciar_pago_getnet para Payment ID {payment_id}")
        traceback.print_exc()
        return JsonResponse({"success": False, "error": "Error interno del servidor"}, status=500)

    




# ============================
# 2. VISTA CALLBACK DE GETNET 
# ============================
# Esta es la URL que Getnet llama
# ============================
@csrf_exempt
@require_POST
def confirmacion_getnet(request):
    import json
    from datetime import datetime

    try:
        data = json.loads(request.body)
        token = data.get("token")
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if not token:
        return HttpResponse(status=400)

    try:
        payment = Payment.objects.get(getnet_token=token)
    except Payment.DoesNotExist:
        return HttpResponse(status=200)

    getnet_service = GetnetService()
    transaction_data = getnet_service.query_transaction_status(token)

    status = transaction_data.get("status")
    auth_code = transaction_data.get("authorization_code")

    if status == "AUTHORIZED":
        payment.status = "paid"
        payment.paid_at = datetime.now()
        payment.getnet_auth_code = auth_code or ""
        payment.save()
    elif status == "REJECTED":
        payment.status = "rejected"
        payment.save()

    return HttpResponse(status=200)




# ============================
# 3. VISTA PAGO (Llegada del alumno - Landing Page)
# ============================
# Esta es la URL a la que el NAVEGADOR del alumno llega.
@login_required
def pago_finalizado(request):
    token = request.GET.get("token")
    payment = None
    if token:
        try:
            payment = Payment.objects.get(getnet_request_id=token)
        except Payment.DoesNotExist:
            pass

    if payment and payment.status == "paid":
        mensaje = "¡Pago realizado con éxito!"
        status_display = "success"
    elif payment and payment.status == "rejected":
        mensaje = "El pago fue rechazado."
        status_display = "failure"
    else:
        mensaje = "Procesando pago..."
        status_display = "info"

    return render(request, "studentView/pago_confirmado.html", {
        "status": status_display,
        "message": mensaje,
        "payment": payment
    })

    
    
    
    
    
    
    
    
    
    
    
# ============================
# notas 
#==========================

from datetime import date
from django.db.models import Avg

# ============================
# PROMEDIO GENERAL DEL ALUMNO
# ============================
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from core.models import Enrollment, Subject, GradeResult


@login_required
def api_promedio_alumno(request):
    user = request.user

    # 1) Buscar la matrícula activa del alumno
    enrollment = (
        Enrollment.objects
        .select_related("class_group")
        .filter(student=user, active_status="active")
        .first()
    )

    # Si no tiene curso asignado, devolvemos ceros
    if not enrollment:
        return JsonResponse({
            "promedio": 0,
            "cantidad_asignaturas": 0,
        })

    class_group = enrollment.class_group

    # 2) Asignaturas del curso, EXCLUYENDO almuerzo y acto cívico
    asignaturas_qs = (
        Subject.objects
        .filter(class_group=class_group)
        .exclude(name__in=["Almuerzo", "Acto Cívico", "Acto Civico"])
    )
    cantidad_asignaturas = asignaturas_qs.count()

    # 3) Promedio general del alumno (todas sus notas)
    resultados = GradeResult.objects.filter(student=user)
    promedio = resultados.aggregate(prom=Avg("score"))["prom"] or 0

    return JsonResponse({
        "promedio": float(promedio),
        "cantidad_asignaturas": cantidad_asignaturas,
    })
    
    
@login_required
@require_POST
def cambiar_pin_apoderado(request):
    alumno = request.user
    nuevo_pin = request.POST.get("nuevo_pin")

    if not nuevo_pin or len(nuevo_pin) < 4:
        return JsonResponse({"success": False, "message": "PIN inválido. Debe tener al menos 4 dígitos."})

    # Obtener relación con apoderado
    relation = (
        GuardianRelation.objects
        .filter(student=alumno)
        .select_related("guardian")
        .first()
    )
    if not relation:
        return JsonResponse({"success": False, "message": "No se encontró apoderado asociado."})

    guardian = relation.guardian

    
    profile = guardian.gprofile          
    profile.payment_pin = nuevo_pin
    profile.save()

    return JsonResponse({"success": True, "message": "PIN actualizado correctamente."})



def api_proximas_evaluaciones(request):
    try:
        alumno = request.user
        # Buscamos el curso activo del alumno
        matricula = Enrollment.objects.filter(student=alumno, active_status='active').first()
        
        if not matricula:
            return JsonResponse({'evaluaciones': []})

        # Filtramos evaluaciones de hoy en adelante (máximo 5)
        hoy = timezone.localdate()
        evaluaciones = Evaluation.objects.filter(
            class_group=matricula.class_group,
            date__gte=hoy
        ).select_related('subject', 'evaluation_type').order_by('date')[:5]

        data = []
        for ev in evaluaciones:
            dias_restantes = (ev.date - hoy).days
            data.append({
                'asignatura': ev.subject.name,
                'tipo': ev.evaluation_type.name,
                'fecha': ev.date.strftime("%d/%m/%Y"),
                'dias_restantes': dias_restantes
            })

        return JsonResponse({'evaluaciones': data})
    except Exception as e:
        print(f"Error api_proximas_evaluaciones: {e}")
        return JsonResponse({'error': str(e)}, status=500)
