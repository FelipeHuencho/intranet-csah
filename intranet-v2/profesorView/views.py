from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from core.models import (
    User, Class, Subject, Enrollment,
    Evaluation, EvaluationType, GradeResult
)


# =========================================================
# SPA: Panel + Perfil
# =========================================================
@login_required
def dashboard(request):
    """
    Renderiza el panel del profesor (SPA), igual que studentView pero versión profe.
    """
    u = request.user
    ctx = {
        "nombre": f"{u.first_name} {u.last_name}",
        "rut": getattr(u, "rut", ""),
        "email": u.email,
        "rol": getattr(u, "role", ""),
    }
    return render(request, "profesorView/teacher.html", ctx)

@login_required
def perfil_data(request):
    u = request.user

    # Perfil de profesor (si es profe)
    tprofile = None
    if u.role == User.TEACHER:
        tprofile = u.tprofile  # helper que definimos en el modelo User

    data = {
        "nombre": f"{u.first_name} {u.last_name}",
        "email": u.email or "--",
        "rut": getattr(u, "rut", "--"),
        "telefono": getattr(u, "phone", "--"),
        "rol": getattr(u, "role", "--"),
        "department": getattr(tprofile, "department", "--") if tprofile else "--",
        "title": getattr(tprofile, "title", "--") if tprofile else "--",
        "position": getattr(tprofile, "position", "--") if tprofile else "--",
    }
    return JsonResponse(data)


@login_required
def clases_hoy(request):
    profe = request.user

    # cursos donde el profe enseña
    subjects = Subject.objects.filter(teacher=profe).select_related("class_group")

    cursos = []
    for s in subjects:
        nombre = str(s.class_group)
        if nombre not in cursos:
            cursos.append(nombre)

    # día actual 
    from datetime import datetime
    dia = datetime.now().strftime("%A %d de %B %Y").capitalize()

    return JsonResponse({
        "dia": dia,
        "cursos": cursos, # Siempre se devuelven todos los cursos
    })

# =========================================================
# Cursos del docente (por asignaturas que imparte)
# =========================================================
@login_required
def cursos_docente(request):
    """
    Lista los cursos donde el profesor imparte asignaturas.
    (No depende de que Class.teacher esté seteado)
    """
    profesor = request.user

    cursos = (
        Subject.objects
        .filter(teacher=profesor)
        .values(
            "class_group_id",
            "class_group__grade__curso_nombre",
            "class_group__year",
        )
        .distinct()
    )

    data = [
        {
            "id": c["class_group_id"],
            "nombre": f'{c["class_group__grade__curso_nombre"]} {c["class_group__year"]}',
        }
        for c in cursos
    ]
    return JsonResponse(data, safe=False)


# =========================================================
# Alumnos por curso (validado por docencia del profesor)
# =========================================================
@login_required
def alumnos_por_curso(request, class_id: int):
    """
    Lista alumnos de un curso (class_group) SOLO si el profesor
    imparte al menos una asignatura en ese curso.
    """
    profesor = request.user

    # 1) validar que el profesor enseña en este course (class_id)
    enseña = Subject.objects.filter(class_group_id=class_id, teacher=profesor).exists()
    if not enseña:
        # Si ni siquiera existe el curso, lanza 404; si existe pero no enseña, 403
        if not Class.objects.filter(id=class_id).exists():
            raise Http404("Curso no encontrado")
        return JsonResponse({"error": "No autorizado"}, status=403)

    # 2) listar matrículas del curso
    qs = (
        Enrollment.objects
        .select_related("student", "class_group__grade")
        .filter(class_group_id=class_id)
    )
    alumnos = [
        {
            "id": e.student.id,
            "nombre": f"{e.student.first_name} {e.student.last_name}",
            "rut": getattr(e.student, "rut", "--"),
        }
        for e in qs
    ]

    # Si el curso existe pero no tiene matrículas, devolvemos lista vacía (200)
    # Solo 404 si ni siquiera existe el curso (lo validamos arriba).
    return JsonResponse(alumnos, safe=False)





# =========================================================
# Evaluaciones: guardar notas
# =========================================================
from django.views.decorators.http import require_POST
from decimal import Decimal

@login_required
@require_POST
def guardar_notas(request, eval_id):
    """
    Crea o actualiza notas para una evaluación.
    Espera en POST: { <student_id>: <nota>, ... }
    """
    evaluacion = get_object_or_404(Evaluation, id=eval_id)

    # Si quieres validar que el profe sea dueño de la evaluación:
    # if evaluacion.teacher_id != request.user.id:
    #     return JsonResponse({"error": "No autorizado"}, status=403)

    actualizadas = 0

    for key, value in request.POST.items():
        if key == "csrfmiddlewaretoken":
            continue
        if not value:
            continue

        try:
            student_id = int(key)
            nota = Decimal(value.replace(",", "."))
        except (ValueError, TypeError):
            continue

        # valida rango 1.0 a 7.0 (ajusta si usas otro sistema)
        if nota < 1 or nota > 7:
            continue

        GradeResult.objects.update_or_create(
            evaluation=evaluacion,
            student_id=student_id,
            defaults={"score": nota},
        )
        actualizadas += 1

    return JsonResponse({"success": True, "actualizadas": actualizadas})



@login_required
def asignaturas_por_curso(request, class_id: int):
    """Devuelve las asignaturas que ESTE profesor imparte en ese curso."""
    profe = request.user
    asignaturas = (
        Subject.objects
        .filter(class_group_id=class_id, teacher=profe)
        .values("id", "name")
    )
    return JsonResponse(list(asignaturas), safe=False)


@login_required
def evaluation_types(request):
    """Por ahora solo devuelve lo que haya en la tabla. Si está vacía, devuelve []."""
    tipos = EvaluationType.objects.all().values("id", "name")
    return JsonResponse(list(tipos), safe=False)


# profesorView/views.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from core.models import Class, Subject, Evaluation, EvaluationType

@login_required
@require_POST
def crear_evaluacion(request):
    profe = request.user

    class_id = request.POST.get("class_id")
    subject_id = request.POST.get("subject_id")
    description = request.POST.get("description") or ""
    date = request.POST.get("date")
    weight = request.POST.get("weight") or 1

    # 👇 esto viene del input de texto del profe
    type_name = (request.POST.get("evaluation_type_name") or "").strip()

    # 1) validar curso
    try:
        class_group = Class.objects.get(pk=class_id)
    except Class.DoesNotExist:
        return JsonResponse({"error": "Curso no existe"}, status=400)

    # 2) validar asignatura del profe en ese curso
    try:
        subject = Subject.objects.get(
            pk=subject_id,
            class_group=class_group,
            teacher=profe,
        )
    except Subject.DoesNotExist:
        return JsonResponse({"error": "No puedes crear evaluación para esa asignatura"}, status=400)

    # 3) asegurarnos de tener SIEMPRE un EvaluationType
    if not type_name:
      # si el profe no escribió nada, usamos un nombre genérico
      type_name = "Evaluación"

    eval_type, _ = EvaluationType.objects.get_or_create(
        name=type_name,
        defaults={"description": type_name},
    )

    # 4) crear la evaluación
    ev = Evaluation.objects.create(
        class_group=class_group,
        subject=subject,
        teacher=profe,
        evaluation_type=eval_type,   # 👈 ahora NUNCA es None
        date=date,
        description=description,
        weight=weight,
    )

    return JsonResponse({"success": True, "evaluation_id": ev.id})



@login_required
def proximas_evaluaciones(request):
    profe = request.user

    hoy = timezone.now().date()

    evaluaciones = (
        Evaluation.objects
        .select_related("class_group", "subject")
        .filter(teacher=profe, date__gte=hoy)   
        .order_by("date")
    )

    data = []
    for ev in evaluaciones:
        data.append({
            "descripcion": ev.description,
            "fecha": ev.date.strftime("%d-%m-%Y"),
            "curso": ev.class_group.grade.curso_nombre,
            "asignatura": ev.subject.name,
        })

    return JsonResponse({"evaluaciones": data})


# para las notas

from core.models import Evaluation, Subject

@login_required
def evaluaciones_por_curso(request, class_id: int):
    profe = request.user
    # evaluaciones de ese curso creadas por este profe
    qs = (
        Evaluation.objects
        .select_related("subject", "evaluation_type")
        .filter(class_group_id=class_id, teacher=profe)
        .order_by("-date")
    )
    data = [
        {
            "id": ev.id,
            "description": ev.description,
            "date": ev.date.isoformat(),
            "subject": ev.subject.name if ev.subject else "",
            "type": ev.evaluation_type.name if ev.evaluation_type else "",
        }
        for ev in qs
    ]
    return JsonResponse(data, safe=False)






# profesorView/views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from core.models import Subject, Enrollment, Evaluation, GradeResult

@login_required
def mis_cursos_y_notas(request):
    profe = request.user

    # Asignaturas que imparte este profe
    subjects = Subject.objects.filter(teacher=profe).select_related("class_group")

    cursos_data = []

    for s in subjects:
        # Alumnos del curso de esa asignatura
        enrollments = (
            Enrollment.objects
            .filter(class_group=s.class_group)
            .select_related("student")
        )

        # Evaluaciones de esa asignatura (ordenadas por fecha)
        evaluations = list(
            Evaluation.objects
            .filter(subject=s)
            .select_related("evaluation_type")
            .order_by("date")
        )

        # Para no hacer N×M queries, indexamos los GradeResult
        students = [en.student for en in enrollments]
        grade_results = GradeResult.objects.filter(
            evaluation__in=evaluations,
            student__in=students,
        )

        # results_index[student_id][evaluation_id] = GradeResult
        results_index = {}
        for gr in grade_results:
            results_index.setdefault(gr.student_id, {})[gr.evaluation_id] = gr

        alumnos_data = []

        for en in enrollments:
            student = en.student
            notas = []
            total_ponderado = 0.0
            suma_pesos = 0.0

            for ev in evaluations:
                gr = results_index.get(student.id, {}).get(ev.id)
                score = float(gr.score) if gr else None
                peso = float(ev.weight) if getattr(ev, "weight", None) is not None else 1.0

                notas.append({
                    "evaluacion": ev.description,                # igual que antes
                    "nota": score,                               # igual que antes
                    "weight": peso,                              # 👈 NUEVO: ponderación
                    "tipo": ev.evaluation_type.name
                            if ev.evaluation_type else "",
                    "fecha": ev.date.isoformat() if ev.date else None,
                })

                if score is not None:
                    total_ponderado += score * peso
                    suma_pesos += peso

            promedio_ponderado = None
            if suma_pesos > 0:
                promedio_ponderado = round(total_ponderado / suma_pesos, 2)

            alumnos_data.append({
                "nombre": f"{student.first_name} {student.last_name}",
                "rut": getattr(student, "rut", ""),
                "notas": notas,
                "promedio_ponderado": promedio_ponderado,   # 👈 NUEVO
            })

        cursos_data.append({
            "asignatura": s.name,
            "curso": str(s.class_group),
            "alumnos": alumnos_data,
        })

    return JsonResponse({"cursos": cursos_data})




from django.utils.timezone import now
from django.http import JsonResponse

DIAS = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}

MESES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}



#notas

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from core.models import (
    User,
    Enrollment,
    Evaluation,
    GradeResult,
)

# helper opcional
def is_teacher(user):
    return user.is_authenticated and user.role == User.TEACHER


@login_required
def alumnos_con_notas(request, eval_id):
    """
    Devuelve los alumnos del curso de esa evaluación + nota si existe.
    Formato:
    [
      { "id": 1, "nombre": "Juan Pérez", "rut": "11.111.111-1", "nota": 6.0 },
      ...
    ]
    """
    # Si quieres restringir a profesores:
    # if not is_teacher(request.user):
    #     return JsonResponse({"error": "Solo profesores"}, status=403)

    evaluacion = get_object_or_404(
        Evaluation.objects.select_related("class_group"),
        id=eval_id,
    )

    # alumnos matriculados en el curso de esa evaluación
    enrollments = (
        Enrollment.objects
        .select_related("student")
        .filter(class_group=evaluacion.class_group, active_status="active")
    )

    # notas ya registradas para esta evaluación
    resultados = {
        gr.student_id: gr
        for gr in GradeResult.objects.filter(evaluation=evaluacion)
    }

    data = []
    for enr in enrollments:
        st = enr.student
        gr = resultados.get(st.id)
        data.append({
            "id": st.id,
            "nombre": f"{st.first_name} {st.last_name}",
            "rut": st.rut,
            "nota": float(gr.score) if gr else None,
        })

    return JsonResponse(data, safe=False)
