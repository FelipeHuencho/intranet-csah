import json
import locale
import calendar
import unicodedata
import re
from datetime import datetime, date, time

from django.utils import timezone
from django.utils.timezone import localtime, make_aware, now
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from collections import defaultdict

from core.models import (
    User,
    Payment,
    Class,
    Grade,
    Subject,
    SubjectSchedule,
    Enrollment,
    GuardianRelation,
    GradeResult,
    Attendance,
    Comuna,
    GuardianProfile,
)

# =====================================================
#  FUNCIONES AUXILIARES
# =====================================================

def is_admin(user):
    """Permite acceso solo a usuarios con rol admin o finance_admin."""
    return user.is_authenticated and user.role in [User.ADMIN, User.FINANCE_ADMIN]


# =====================================================
#  DASHBOARD PRINCIPAL
# =====================================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_students = User.objects.filter(role=User.STUDENT).count()
    total_teachers = User.objects.filter(role=User.TEACHER).count()
    total_guardians = User.objects.filter(role=User.GUARDIAN).count()
    total_payments = Payment.objects.count()

    return render(request, "adminView/admins.html", {
        "usuario": request.user,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_guardians": total_guardians,
        "total_payments": total_payments,
    })


# =====================================================
#  USUARIOS Y LISTADOS
# =====================================================

@login_required
@user_passes_test(is_admin)
def users_list(request):
    users = User.objects.all().order_by("role", "first_name")
    return render(request, "adminView/users.html", {"users": users})


# =====================================================
#  PAGOS
# =====================================================

@login_required
@user_passes_test(is_admin)
def payments(request):
    pagos = Payment.objects.all().order_by("-issue_date")
    return render(request, "adminView/payments.html", {"pagos": pagos})


from collections import OrderedDict
from django.utils.timezone import localtime, make_aware
from datetime import datetime, time

@login_required
@user_passes_test(is_admin)
def api_ver_pagos(request):
    """
    Agrupa pagos por estado -> curso -> alumno.
    Respuesta:
    {
      "pendientes": [
        { "curso": "1° Básico A (2025)", "pagos": [ { ... }, ... ] },
        ...
      ],
      "pagados": [...],
      ...
    }
    """
    pagos = Payment.objects.select_related("student").order_by("issue_date")

    status_map = {
        "pending": "pendientes",
        "paid": "pagados",
        "failed": "fallidos",
        "refunded": "reembolsados",
    }

    # temp[estado][curso] = [ pagos... ]
    temp = {v: defaultdict(list) for v in status_map.values()}

    for p in pagos:
        # ----- Estado -----
        estado = status_map.get(p.status, "pendientes")

        # ----- Curso del alumno -----
        curso_nombre = "Sin curso asignado"
        enrollment = (
            Enrollment.objects
            .filter(student=p.student, active_status="active")
            .select_related("class_group__grade")
            .order_by("-class_group__year")
            .first()
        )
        if enrollment and enrollment.class_group and enrollment.class_group.grade:
            curso_nombre = (
                f"{enrollment.class_group.grade.curso_nombre} "
                f"({enrollment.class_group.year})"
            )

        # ----- Fecha segura -----
        fecha = p.issue_date or p.created_at
        if isinstance(fecha, datetime):
            dt = localtime(fecha)
        else:
            fecha_dt = make_aware(datetime.combine(fecha, time(8, 0)))
            dt = localtime(fecha_dt)

        registro = {
            "alumno": f"{p.student.first_name} {p.student.last_name}",
            "concepto": p.concept or "—",
            "monto": f"{p.amount:,.0f}".replace(",", "."),
            "fecha": dt.strftime("%d-%m-%Y"),
        }

        temp[estado][curso_nombre].append(registro)

    # ----- Convertir a listas ordenadas -----
    buckets = {}
    for estado, cursos_dict in temp.items():
        cursos_list = []
        for curso in sorted(cursos_dict.keys()):
            pagos_lista = cursos_dict[curso]
            pagos_lista.sort(key=lambda x: x["alumno"])  # dentro del curso, por alumno
            cursos_list.append({
                "curso": curso,
                "pagos": pagos_lista,
            })
        buckets[estado] = cursos_list

    return JsonResponse(buckets)



# =====================================================
#  CURSOS Y PROFESORES
# =====================================================

@login_required
@user_passes_test(is_admin)
def ver_cursos(request):
    clases = (
        Class.objects
        .select_related("grade", "teacher")
        .prefetch_related("enrollment_set__student")
        .order_by("year", "grade__curso_nombre")
    )

    cursos_data = []
    for c in clases:
        alumnos = [e.student for e in c.enrollment_set.all() if e.active_status == "active"]
        cursos_data.append({
            "curso": c.grade.curso_nombre,
            "year": c.year,
            "profesor": f"{c.teacher.first_name} {c.teacher.last_name}" if c.teacher else "Sin asignar",
            "alumnos": alumnos,
        })

    return render(request, "adminView/ver_cursos.html", {
        "usuario": request.user,
        "cursos_data": cursos_data
    })


@login_required
@user_passes_test(is_admin)
def api_ver_cursos(request):
    clases = Class.objects.select_related("grade", "teacher").all()
    data = []

    for c in clases:
        alumnos = Enrollment.objects.filter(class_group=c).select_related("student")
        data.append({
            "curso": c.grade.curso_nombre,
            "year": c.year,
            "profesor": f"{c.teacher.first_name} {c.teacher.last_name}" if c.teacher else "Sin profesor asignado",
            "alumnos": [
                {
                    "rut": a.student.rut,
                    "nombre": f"{a.student.first_name} {a.student.last_name}",
                    "correo": a.student.email or "",
                }
                for a in alumnos
            ]
        })

    return JsonResponse({"cursos": data})


@login_required
@user_passes_test(is_admin)
def api_ver_profesores(request):
    try:
        profesores = User.objects.filter(role=User.TEACHER).prefetch_related("subject_set")
        data = []

        for prof in profesores:
            # Curso Jefe
            clase = Class.objects.filter(teacher=prof).select_related("grade").first()
            curso_jefe = clase.grade.curso_id if clase else "—"
            year = clase.year if clase else "—"

            # Asignaturas únicas
            asignaturas_query = prof.subject_set.values_list("name", flat=True)
            asignaturas_unicas = list(dict.fromkeys(asignaturas_query))
            asignaturas_str = ", ".join(asignaturas_unicas) if asignaturas_unicas else "—"

            data.append({
                "id": prof.id,
                "first_name": prof.first_name,
                "last_name": prof.last_name,
                "email": prof.email or "",
                "telefono": prof.phone or "—",
                "curso_jefe": curso_jefe,
                "year": year,
                "asignaturas": asignaturas_str,
            })

        return JsonResponse({"profesores": data})

    except Exception as e:
        print("❌ Error en api_ver_profesores:", str(e))
        return JsonResponse({"error": str(e)}, status=500)


import io
import json
import unicodedata # <--- NECESARIO para manejar tildes/eñes
from openpyxl import Workbook
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from email.mime.image import MIMEImage
from django.conf import settings
from django.contrib.auth.hashers import make_password 
from django.db import transaction

# ASUMO LA EXISTENCIA DE ESTOS MODELOS SEGÚN TU CÓDIGO ANTERIOR
# from .models import User, Grade, Class, Subject, SubjectSchedule 


# =====================================================
#  FUNCIONES DE UTILIDAD PARA LA CONTRASEÑA
# =====================================================

def normalize_text(text):
    """Limpia tildes (acentos) y la letra ñ, esencial para la lógica de la contraseña."""
    if not text:
        return ""
    # 1. Normaliza para separar los acentos y luego ignora los caracteres no ASCII (los acentos)
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    # 2. Reemplaza explícitamente la ñ por n (después de la normalización, solo para asegurar)
    normalized = normalized.replace('ñ', 'n').replace('Ñ', 'N')
    return normalized

def build_password_initial(nombres, apellidos, rut):
    """
    Genera una contraseña inicial estructurada según tu lógica:
    [2 letras del nombre en MAYÚS] + [5 letras del apellido en MINÚS, sin tildes/ñ] + [4 primeros dígitos del RUT]
    """
    
    # 1. Nombre (2 letras en MAYÚS)
    first_name_part = nombres[:2].upper() if nombres and len(nombres) >= 2 else (nombres.upper() + 'X')[:2]
    
    # 2. Apellido (5 letras en MINÚS, sin tildes ni ñ)
    # Solo consideramos el primer apellido
    primer_apellido = apellidos.split(' ')[0] if apellidos else 'sinapellido'
    normalized_last_name = normalize_text(primer_apellido)
    last_name_part = normalized_last_name[:5].lower()

    # 3. RUT (4 primeros dígitos)
    # Extrae solo dígitos del RUT
    rut_cleaned = ''.join(filter(str.isdigit, rut.replace('-', '')))
    rut_part = rut_cleaned[:4] if rut_cleaned and len(rut_cleaned) >= 4 else (rut_cleaned + '0000')[:4]
    
    # Concatenar las partes. Ejemplo: Juan Pérez, RUT 12.345.678-9 -> JUperer1234
    return f"{first_name_part}{last_name_part}{rut_part}"


# =====================================================
#  CRUD PROFESORES
# =====================================================



@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["POST"])
def api_crear_profesor(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        rut = data.get("rut")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        asignatura = data.get("asignatura", "")
        title = data.get("title", "")
        is_head_teacher = str(data.get("is_head_teacher", "")).lower() in ["true", "1"]
        curso_id = data.get("curso_id")
        year = int(data.get("year", 2025))

        if not all([rut, first_name, last_name, email]):
            return JsonResponse({"error": "Faltan campos obligatorios."}, status=400)
        if User.objects.filter(rut=rut).exists():
            return JsonResponse({"error": "Ya existe un profesor con este RUT."}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Ya existe un profesor con este correo."}, status=400)

        with transaction.atomic():
            
            # --- Generar contraseña inicial ---
            initial_password = build_password_initial(first_name, last_name, rut)
            
            # Crear profesor (Django hace el hash automáticamente)
            profesor = User.objects.create_user(
                rut=rut,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=User.TEACHER,
                password=initial_password,
            )

            # Guardar título en TeacherProfile
            if title:
                tprofile = profesor.tprofile
                tprofile.title = title
                tprofile.save()

            # Asignar jefe de curso y clase
            clase = None
            if curso_id:
                curso = Grade.objects.filter(curso_id=curso_id).first()
                if curso:
                    clase, _ = Class.objects.get_or_create(grade=curso, year=year)
                    if is_head_teacher:
                        clase.teacher = profesor
                        clase.save()
                else:
                    print(f"⚠️ Curso {curso_id} no encontrado, se continúa sin asignar jefe de curso.")

            # Asignaturas
            if asignatura:
                materias = [m.strip() for m in asignatura.split(",") if m.strip()]
                for nombre in materias:
                    target_class = clase or Class.objects.filter(year=year).first()
                    if not target_class:
                        continue
                    subject, created = Subject.objects.get_or_create(
                        name=nombre,
                        class_group=target_class,
                        defaults={"teacher": profesor}
                    )
                    if not created:
                        subject.teacher = profesor
                        subject.save()

            # --- Generar Excel con horario ---
            wb = Workbook()
            ws = wb.active
            ws.title = "Horario de Clases"
            ws.append(["Día", "Hora inicio", "Hora fin", "Asignatura", "Curso"])
            day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

            horarios = SubjectSchedule.objects.filter(subject__teacher=profesor)\
                .select_related("subject__class_group__grade")\
                .order_by("day_of_week", "start_time")
            
            for h in horarios:
                ws.append([
                    day_names[h.day_of_week] if h.day_of_week < 5 else str(h.day_of_week),
                    h.start_time.strftime("%H:%M"),
                    h.end_time.strftime("%H:%M"),
                    h.subject.name,
                    h.subject.class_group.grade.curso_nombre if h.subject.class_group and h.subject.class_group.grade else "—"
                ])
            
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)

            # --- Preparar envío de correo ---
            if profesor.email:
                curso_nombre = clase.grade.curso_nombre if clase and clase.grade else "—"
                periodo_academico = str(year)
                contacto_email = "UTP@HIPONA.CL"
                contacto_telefono = "+56 443159496"
                sitio_web = "https://hipona.cl/"
                logo_path = r"adminView\static\adminstyle\banner.png"

                # HTML del correo con credenciales, información y recordatorio
                credenciales_html = f"""
                <div style="border:2px solid #123159;padding:20px;margin:30px 0;background-color:#e6f0ff;border-radius:4px;">
                    <p style="font-size:17px;margin-top:0;margin-bottom:15px;color:#123159;font-weight:bold;text-align:center;">
                         Sus Credenciales de Acceso
                    </p>
                    <ul style="margin:0;padding-left:20px;font-size:16px;list-style-type:none;color:#333;">
                        <li style="margin-bottom:8px;"><strong style='color:#123159;'>Usuario:</strong> {profesor.rut}</li>
                        <li><strong style='color:#123159;'>Contraseña Inicial:</strong> {initial_password}</li>
                    </ul>
                </div>
                """
                recordatorio_cambio_pwd = f"""
                <p style="font-size:14px;margin-top:10px;color:#a00000;font-style:italic;">
                    ⚠️ Por seguridad, le recomendamos encarecidamente cambiar esta contraseña inicial lo antes posible en nuestro portal, "Recupera tu contraseña".
                </p>
                """

                html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Bienvenida - Colegio San Agustín de Hipona</title>
        </head>
        <body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,sans-serif;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
                <tr>
                    <td align="center" style="padding:30px 0;">
                        <table border="0" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;background-color:#ffffff;border-radius:6px;border:1px solid #e0e0e0;">
                            <tr>
                                <td align="center" style="background-color:#D9A84E;padding:15px 40px;border-radius:6px 6px 0 0;">
                                    <h1 style="color:#123159;margin:0;font-size:20px;font-weight:bold;line-height:1.3;">¡Bienvenido/a!</h1>
                                    <h2 style="color:#123159;margin:0;font-size:16px;font-weight:normal;">Colegio San Agustín de Hipona</h2>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:30px 40px;color:#333;line-height:1.7;">
                                    <p style="margin-top:0;font-size:16px;">Estimado/a <strong>{profesor.first_name} {profesor.last_name}</strong>:</p>
                                    <p style="font-size:16px;">Nos complace darle la bienvenida. Adjunto encontrará su horario de clases y el curso asignado para el año académico {periodo_academico}.</p>
                                    {credenciales_html}
                                    <div style="border:1px solid #D9A84E;padding:20px;margin:30px 0;background-color:#fffff0;border-radius:4px;">
                                        <p style="font-size:17px;margin-top:0;text-align:center;margin-bottom:15px;color:#123159;font-weight:bold;">Información Clave:</p>
                                        <ul style="margin:0;padding-left:20px;font-size:16px;list-style-type:disc;color:#123159;">
                                            <li style="margin-bottom:8px;"><strong style='color:#333;'>Curso asignado:</strong> {curso_nombre}</li>
                                            <li style="margin-bottom:8px;"><strong style='color:#333;'>Periodo académico:</strong> {periodo_academico}</li>
                                            <li><strong style='color:#333;'>Contacto (Dudas):</strong> <a href="mailto:{contacto_email}" style="color:#D9A84E;text-decoration:none;font-weight:bold;">{contacto_email}</a> o {contacto_telefono}</li>
                                        </ul>
                                    </div>
                                    <p style="font-size:16px;margin-bottom:5px;">Le deseamos mucho éxito en este nuevo ciclo escolar.</p>
                                    {recordatorio_cambio_pwd}
                                    <p style="font-size:16px;color:#123159;font-weight:bold;">Atentamente, La Dirección.</p>
                                </td>
                            </tr>
                            <tr>
                                <td align="left" style="padding:0 40px 30px 40px;text-align:center;">
                                    <a href="{sitio_web}" target="_blank" style="display:inline-block;padding:12px 25px;background-color:#D9A84E;color:#123159;text-decoration:none;border-radius:5px;font-weight:bold;font-size:16px;border:1px solid #D9A84E;"> Visite nuestro sitio web</a>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding:20px 40px;border-top:1px solid #e0e0e0;color:#999;font-size:12px;border-radius:0 0 6px 6px;">&copy; {periodo_academico}. <span style="color:#123159;font-weight:bold;">Colegio San Agustín de Hipona</span> — Todos los derechos reservados.</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
                """

                email_msg = EmailMultiAlternatives(
                    subject=f"Bienvenido/a {profesor.first_name} - Curso y Horario",
                    body=f"Estimado/a {profesor.first_name}, adjunto su horario y curso. Usuario: {profesor.rut}, Contraseña: {initial_password}.",
                    from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    to=[profesor.email],
                )
                email_msg.attach_alternative(html_content, "text/html")

                # Adjuntar logo si existe
                try:
                    with open(logo_path, "rb") as f:
                        logo = MIMEImage(f.read())
                        logo.add_header('Content-ID', '<logo_cid>')
                        logo.add_header('Content-Disposition', 'inline', filename='logo2.png')
                        email_msg.attach(logo)
                except FileNotFoundError:
                    print(f"⚠️ No se encontró imagen en {logo_path}")

                # Adjuntar Excel
                email_msg.attach(f"Horario_{profesor.rut}.xlsx", excel_buffer.read(),
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                email_msg.send(fail_silently=False)

            return JsonResponse({
                "message": "✅ Profesor creado y correo enviado.",
                "profesor": {
                    "id": profesor.id,
                    "nombre": f"{profesor.first_name} {profesor.last_name}",
                    "email": profesor.email,
                    "asignaturas": asignatura,
                    "curso_jefe": curso_id if is_head_teacher else "—"
                }
            }, status=201)

    except Exception as e:
        print("⚠️ Error al crear profesor:", e)
        return JsonResponse({"error": str(e)}, status=500)





@login_required
@user_passes_test(is_admin)
@require_http_methods(["PUT"])
def api_actualizar_profesor(request, id):
    try:
        data = json.loads(request.body.decode("utf-8"))
        profesor = User.objects.get(id=id, role=User.TEACHER)

        # Nombre completo viene en el campo "first_name" del formulario
        full_name = data.get("first_name")
        if full_name:
            partes = full_name.strip().split()
            if len(partes) == 1:
                profesor.first_name = partes[0]
            else:
                profesor.first_name = " ".join(partes[:-1])
                profesor.last_name = partes[-1]

        # Email
        email = data.get("email")
        if email:
            profesor.email = email

        profesor.save()

        # Title va en TeacherProfile
        tprofile = profesor.tprofile
        title = data.get("title")
        if title is not None:
            tprofile.title = title
            tprofile.save()

        return JsonResponse({
            "message": "Profesor actualizado correctamente",
            "profesor": {
                "id": profesor.id,
                "first_name": profesor.first_name,
                "last_name": profesor.last_name,
                "title": getattr(tprofile, "title", ""),
                "email": profesor.email,
            }
        })

    except User.DoesNotExist:
        return JsonResponse({"error": "Profesor no encontrado"}, status=404)
    except Exception as e:
        print(" Error al actualizar profesor:", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE"])
def api_eliminar_profesor(request, id):
    try:
        profesor = User.objects.get(id=id, role=User.TEACHER)
        profesor.delete()
        return JsonResponse({"message": "Profesor eliminado correctamente."})
    except User.DoesNotExist:
        return JsonResponse({"error": "Profesor no encontrado."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================
#  REGISTRO DE ALUMNOS
# =====================================================

def strip_accents(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def first_letters(name: str, n: int, upper=False, lower=False) -> str:
    base = strip_accents((name or "").strip())
    base = re.sub(r"[^A-Za-z]", "", base)  # solo letras
    out = base[:n]
    if upper:
        out = out.upper()
    if lower:
        out = out.lower()
    return out


def first_two_digits_of_rut(rut: str) -> str:
    digits = re.sub(r"[^0-9]", "", rut or "")
    return digits[:2] or "00"


def build_password_inline(first_name: str, last_name: str, rut: str) -> str:
    aa = first_letters(first_name, 2, upper=True)       # 2 letras nombre (mayus)
    bbbbb = first_letters(last_name, 5, lower=True)     # 5 letras apellido (minus)
    dd = first_two_digits_of_rut(rut)                   # 2 dígitos del RUT

    if len(aa) < 2:
        aa = (aa + "XX")[:2]
    if len(bbbbb) < 5:
        bbbbb = (bbbbb + "xxxxx")[:5]
    if len(dd) < 2:
        dd = (dd + "0")[:2]

    return f"{aa}{bbbbb}{dd}"


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_registrar_alumno(request):
    """
    Registrar alumno + apoderado + relación + matrícula + mensualidades +
    asignación de curso + envío de correo al apoderado (HTML personalizado).
    """
    try:
        data = request.POST or json.loads(request.body.decode("utf-8"))

        # Datos del alumno
        rut = data.get("rut")
        nombres = data.get("nombres")
        apellidos = data.get("apellidos")
        fecha_nacimiento = data.get("fecha_nacimiento")
        comuna_nombre = data.get("comuna")
        curso_id = data.get("curso")
        estado_alumno = data.get("estado_alumno", "active")

        # Datos del apoderado
        rut_apoderado       = data.get("rut_apoderado")
        nombre_apoderado    = data.get("nombre_apoderado")
        apellidos_apoderado = data.get("apellidos_apoderado")  # 👈 NUEVO
        email_apoderado     = data.get("email_apoderado")
        telefono_apoderado  = data.get("telefono_apoderado")

        # Ahora también exigimos apellido del apoderado
        if not all([rut, nombres, apellidos, rut_apoderado, nombre_apoderado, apellidos_apoderado]):
            return JsonResponse({"error": "Faltan campos obligatorios."}, status=400)

        # Generar contraseña inicial del alumno
        pwd_inicial = build_password_inline(nombres, apellidos, rut)

        # Comuna (FK)
        comuna_obj = None
        if comuna_nombre:
            comuna_obj, _ = Comuna.objects.get_or_create(
                nombre=comuna_nombre.upper()
            )

        # Crear o actualizar alumno
        alumno, creado = User.objects.get_or_create(
            rut=rut,
            defaults={
                "first_name": nombres,
                "last_name": apellidos,
                "role": User.STUDENT,
                "birth_date": fecha_nacimiento,
                "comuna": comuna_obj,
                "active_status": estado_alumno,
                "password": make_password(pwd_inicial),
            },
        )

        if not creado:
            alumno.password = make_password(pwd_inicial)
            alumno.save(update_fields=["password"])

        # Crear o actualizar apoderado (ahora con last_name)
        apoderado, creado_apo = User.objects.get_or_create(
            rut=rut_apoderado,
            defaults={
                "first_name": nombre_apoderado,
                "last_name": apellidos_apoderado,     
                "email": email_apoderado,
                "phone": telefono_apoderado,
                "role": User.GUARDIAN,
                "password": make_password(rut_apoderado),
            },
        )

        # Perfil de apoderado + PIN
        gprofile, _ = GuardianProfile.objects.get_or_create(user=apoderado)
        if not gprofile.payment_pin:
            gprofile.payment_pin = "12345"
            gprofile.save()

        # Relación alumno - apoderado
        GuardianRelation.objects.get_or_create(
            guardian=apoderado,
            student=alumno
        )

        # Asignación de curso (Enrollment)
        if curso_id:
            clase = Class.objects.filter(grade__curso_id=curso_id).first()
            if clase:
                Enrollment.objects.get_or_create(student=alumno, class_group=clase)

        # Matrícula y mensualidades
        hoy = datetime.now().date()
        year = hoy.year
        mes_inicio = hoy.month

        Payment.objects.get_or_create(
            student=alumno,
            concept=f"Matrícula {year}",
            defaults={
                "amount": 230000,
                "status": "pending",
                "issue_date": hoy,
                "due_date": date(year, mes_inicio, 5),
            },
        )

        MONTO_MENSUALIDAD = 180000
        for month in range(mes_inicio, 13):
            Payment.objects.get_or_create(
                student=alumno,
                concept=f"Mensualidad {calendar.month_name[month]} {year}",
                defaults={
                    "amount": MONTO_MENSUALIDAD,
                    "status": "pending",
                    "issue_date": hoy,
                    "due_date": date(year, month, 5),
                },
            )

        # -----------------------------
        # Envío de correo HTML personalizado
        # -----------------------------
        if apoderado.email:
            try:
                year_actual = datetime.now().year

                # Credenciales en HTML
                credenciales_html = f"""
                <div style="border: 2px solid #123159; padding: 20px; margin: 20px 0; background-color: #e6f0ff; border-radius: 4px;">
                    <p style="font-size: 17px; margin:0 0 15px 0; color:#123159; font-weight:bold; text-align:center;">
                        🔑 Credenciales del Alumno y Apoderado
                    </p>
                    <ul style="list-style:none; padding-left:0; font-size:16px; color:#333;">
                        <li><strong style="color:#123159;">Alumno:</strong> {alumno.first_name} {alumno.last_name}</li>
                        <li><strong style="color:#123159;">RUT:</strong> {alumno.rut}</li>
                        <li><strong style="color:#123159;">Contraseña inicial:</strong> {pwd_inicial}</li>
                        <li><strong style="color:#123159;">PIN apoderado:</strong> {gprofile.payment_pin}</li>
                    </ul>
                </div>
                """

                recordatorio_html = f"""
                <p style="font-size:14px; color:#a00000; font-style: italic;">
                    ⚠️ Por seguridad, le recomendamos cambiar la contraseña y el PIN iniciales en la sección "Recupera tu contraseña".
                </p>
                """

                html_content = f"""
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Registro de Alumno</title>
                </head>
                <body style="margin:0; padding:0; font-family: Arial, sans-serif; background-color:#f4f4f4;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="table-layout:fixed;">
                        <tr>
                            <td align="center" style="padding: 30px 0;">
                                <table width="600" style="max-width:600px; background-color:#fff; border-radius:6px; border:1px solid #e0e0e0;">
                                    <tr>
                                        <td align="center" style="background-color:#D9A84E; padding:15px 40px; border-radius:6px 6px 0 0;">
                                            <h1 style="color:#123159; margin:0; font-size:20px; font-weight:bold;">¡Bienvenido al Colegio!</h1>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:30px 40px; color:#333; line-height:1.6;">
                                            <p style="margin:0 0 15px 0;">
                                                Estimado/a <strong>{apoderado.first_name} {apoderado.last_name}</strong>:
                                            </p>
                                            <p style="margin:0 0 15px 0;">
                                                Se ha registrado un nuevo alumno en el sistema y se han generado sus credenciales:
                                            </p>

                                            {credenciales_html}

                                            {recordatorio_html}

                                            <p style="font-size:16px; color:#123159; font-weight:bold;">Atentamente,</p>
                                            <p style="font-size:16px; color:#123159; font-weight:bold;">Equipo de Soporte - Colegio San Agustín de Hipona</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="padding:20px 40px; border-top:1px solid #e0e0e0; color:#999; font-size:12px; border-radius:0 0 6px 6px;">
                                            &copy; {year_actual}. Colegio San Agustín de Hipona — Todos los derechos reservados.
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """

                email_msg = EmailMultiAlternatives(
                    subject=f"Registro de alumno {alumno.first_name} {alumno.last_name}",
                    body=(
                        f"Estimado/a {apoderado.first_name} {apoderado.last_name}, "
                        f"se ha registrado un nuevo alumno. "
                        f"Contraseña: {pwd_inicial}, PIN: {gprofile.payment_pin}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    to=[apoderado.email],
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send(fail_silently=False)

            except Exception as e:
                print("❌ Error al enviar correo al apoderado:", e)

        # -----------------------------
        # Respuesta JSON
        # -----------------------------
        return JsonResponse({
            "message": (
                "✅ Alumno registrado correctamente. "
                "Se generó matrícula, mensualidades, PIN 12345 para el apoderado y se asignó curso."
            ),
            "alumno": {
                "nombre": f"{alumno.first_name} {alumno.last_name}",
                "rut": alumno.rut,
                "password_inicial": pwd_inicial,
                "apoderado": f"{apoderado.first_name} {apoderado.last_name}",
            }
        }, status=201)

    except Exception as e:
        print("❌ Error en registrar alumno:", e)
        return JsonResponse({"error": str(e)}, status=500)




# =====================================================
#  COMUNICADOS
# =====================================================

@login_required
@user_passes_test(is_admin)
@require_POST
def api_enviar_comunicado(request):
    """
    API para enviar comunicados por correo.
    Recibe: asunto, mensaje, destino (todos/curso/alumno/manual)
    """
    asunto = request.POST.get("asunto", "").strip()
    mensaje = request.POST.get("mensaje", "").strip()
    destino = request.POST.get("destino", "todos")

    if not asunto or not mensaje:
        return JsonResponse({"error": "Asunto y mensaje son obligatorios."}, status=400)

    try:
        destinatarios = []

        if destino == "manual":
            email_manual = request.POST.get("email_manual", "").strip()
            if not email_manual:
                return JsonResponse({"error": "Debes indicar un correo destino."}, status=400)
            destinatarios.append(email_manual)
        else:
            if settings.EMAIL_HOST_USER:
                destinatarios.append(settings.EMAIL_HOST_USER)
            else:
                return JsonResponse(
                    {"error": "No hay correo remitente configurado en el servidor."},
                    status=500
                )

        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=destinatarios,
            fail_silently=False,
        )

        return JsonResponse({"message": "Comunicado enviado correctamente."})

    except Exception as e:
        print("Error al enviar comunicado:", e)
        return JsonResponse({"error": "Error interno al enviar el comunicado."}, status=500)


# =====================================================
#  LISTADOS GENERALES
# =====================================================

@login_required
@user_passes_test(is_admin)
def api_listar_usuarios(request):
    try:
        usuarios = User.objects.all().order_by("role", "first_name")

        data = []
        for u in usuarios:
            data.append({
                "id": u.id,
                "nombre": f"{u.first_name} {u.last_name}",
                "rut": u.rut,
                "email": u.email or "—",
                "telefono": u.phone or "—",
                "rol": u.get_role_display() if hasattr(u, "get_role_display") else u.role,
            })

        return JsonResponse({"usuarios": data})

    except Exception as e:
        print("❌ Error al listar usuarios:", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def api_listar_apoderados(request):
    try:
        relaciones = GuardianRelation.objects.select_related("guardian", "student").all()
        data = [
            {
                "alumno": f"{rel.student.first_name} {rel.student.last_name}",
                "rut": rel.student.rut,
                "apoderado": rel.guardian.first_name,
                "email": rel.guardian.email,
            }
            for rel in relaciones
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        print("❌ Error al listar apoderados:", e)
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================
#  ASIGNATURAS
# =====================================================

@login_required
@user_passes_test(is_admin)
def api_listar_asignaturas(request):
    # 1) Traemos todas las asignaturas, EXCEPTO "Almuerzo"
    asignaturas = (
        Subject.objects
        .exclude(name__icontains="almuerzo")
        .select_related("class_group", "class_group__grade", "teacher")
        .all()
    )

    data = []

    for a in asignaturas:
        curso = a.class_group.grade.curso_nombre if a.class_group and a.class_group.grade else "—"
        year = a.class_group.year if a.class_group else "—"

        profesor = (
            f"{a.teacher.first_name} {a.teacher.last_name}"
            if a.teacher else None
        )

        data.append({
            "name": a.name or "—",
            "curso": curso,
            "year": year,
            "teacher": profesor or "—",
            "has_teacher": profesor is not None,
        })

    # 2) Ordenar: primero con profesor, luego sin profesor, y por nombre
    data.sort(key=lambda x: (not x["has_teacher"], x["name"]))

    for item in data:
        item.pop("has_teacher", None)

    return JsonResponse({"asignaturas": data})


# =====================================================
#  HORARIOS PROFESORES
# =====================================================

@login_required
@user_passes_test(is_admin)
def api_listar_horarios(request):
    """
    Devuelve los horarios agrupados por profesor.
    """
    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    schedules = (
        SubjectSchedule.objects
        .select_related("subject", "subject__teacher", "subject__class_group", "subject__class_group__grade")
        .all()
        .order_by("day_of_week", "start_time")
    )

    profesores = {}  # {profe_id: {nombre: ..., horarios: [...]}}

    for sch in schedules:
        subject = sch.subject
        teacher = subject.teacher
        if not teacher:
            continue

        prof_id = teacher.id
        if prof_id not in profesores:
            profesores[prof_id] = {
                "profesor": f"{teacher.first_name} {teacher.last_name}",
                "horarios": []
            }

        profesores[prof_id]["horarios"].append({
            "dia": day_names[sch.day_of_week] if sch.day_of_week < len(day_names) else sch.day_of_week,
            "inicio": sch.start_time.strftime("%H:%M"),
            "termino": sch.end_time.strftime("%H:%M"),
            "asignatura": subject.name,
            "curso": getattr(subject.class_group.grade, "curso_nombre", "") if getattr(subject, "class_group", None) and getattr(subject.class_group, "grade", None) else "",
        })

    return JsonResponse({"profesores": list(profesores.values())})


# =====================================================
#  STATS DASHBOARD (GRÁFICOS)
# =====================================================

@login_required
def api_dashboard_stats(request):
    try:
        locale.setlocale(locale.LC_TIME, '')
    except Exception:
        pass

    stats = {
        "total_students": User.objects.filter(role=User.STUDENT).count(),
        "total_teachers": User.objects.filter(role=User.TEACHER).count(),
        "total_guardians": User.objects.filter(role=User.GUARDIAN).count(),
        "total_admins": User.objects.filter(role__in=[User.ADMIN, User.FINANCE_ADMIN]).count(),
        "pagos_pendientes": Payment.objects.filter(status="pending").count(),
        "pagos_pagados": Payment.objects.filter(status="paid").count(),
        "pagos_fallidos": Payment.objects.filter(status="failed").count(),
        "pagos_reembolsados": Payment.objects.filter(status="refunded").count(),
    }

    # Flujo de ingresos por mes
    ingresos_query = (
        Payment.objects.filter(status='paid')
        .annotate(month=TruncMonth('issue_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    ingresos_labels = []
    ingresos_data = []

    for entry in ingresos_query:
        if entry['month']:
            mes_nombre = entry['month'].strftime('%B').capitalize()
            ingresos_labels.append(mes_nombre)
            ingresos_data.append(entry['total'])

    # Matrícula por nivel
    alumnos_nivel_query = (
        Enrollment.objects.filter(active_status='active')
        .values('class_group__grade__curso_nombre')
        .annotate(total=Count('student'))
        .order_by('class_group__grade__curso_id')
    )

    niveles_labels = []
    niveles_data = []

    for entry in alumnos_nivel_query:
        nombre = entry['class_group__grade__curso_nombre']
        if nombre:
            nombre_corto = nombre.replace("Básico", "Bás").replace("Medio", "Med")
            niveles_labels.append(nombre_corto)
            niveles_data.append(entry['total'])

    stats["ingresos_labels"] = ingresos_labels
    stats["ingresos_data"] = ingresos_data
    stats["niveles_labels"] = niveles_labels
    stats["niveles_data"] = niveles_data

    return JsonResponse(stats)


# =====================================================
#  CURSOS / ASIGNATURAS PARA COMBOS
# =====================================================

@login_required
@user_passes_test(is_admin)
def api_cursos_simple(request):
    clases = (
        Class.objects
        .select_related("grade")
        .all()
    )

    cursos = []
    for c in clases:
        cursos.append({
            "curso_id": c.grade.curso_id,
            "curso_nombre": c.grade.curso_nombre,
            "year": c.year,
        })

    return JsonResponse({"cursos": cursos})


@login_required
@user_passes_test(is_admin)
def api_asignaturas_por_curso(request):
    curso_id = request.GET.get("curso_id")
    year = request.GET.get("year")

    if not curso_id or not year:
        return JsonResponse({"asignaturas": []})

    try:
        year = int(year)
    except ValueError:
        return JsonResponse({"asignaturas": []})

    materias = (
        Subject.objects
        .select_related("class_group__grade")
        .filter(
            class_group__grade__curso_id=curso_id,
            class_group__year=year
        )
    )

    data = [
        {"name": m.name}
        for m in materias
    ]
    return JsonResponse({"asignaturas": data})


# =====================================================
#  ELIMINAR ALUMNO (CASCADE LÓGICA)
# =====================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE"])
@transaction.atomic
def api_eliminar_alumno(request, rut):
    """
    Elimina al alumno, sus pagos, notas, matrículas, asistencias,
    relaciones con apoderado(s) y apoderados huérfanos.
    """
    try:
        rut_recibido = (rut or "").strip().upper()

        alumno = get_object_or_404(
            User,
            rut__iexact=rut_recibido,
            role=User.STUDENT,
        )

        nombre_alumno = (f"{alumno.first_name} {alumno.last_name}").strip() or alumno.rut

        relaciones = GuardianRelation.objects.filter(student=alumno).select_related("guardian")
        guardians = {rel.guardian for rel in relaciones}

        GradeResult.objects.filter(student=alumno).delete()
        Attendance.objects.filter(student=alumno).delete()
        Payment.objects.filter(student=alumno).delete()
        Enrollment.objects.filter(student=alumno).delete()
        relaciones.delete()

        alumno.delete()

        # Eliminar apoderados que quedan sin alumnos
        for g in guardians:
            if g.role == User.GUARDIAN and not GuardianRelation.objects.filter(guardian=g).exists():
                g.delete()

        return JsonResponse({
            "success": True,
            "message": f'Alumno "{nombre_alumno}" y datos relacionados eliminados correctamente.',
        })

    except Exception as e:
        print("❌ Error al eliminar alumno:", e)
        return JsonResponse(
            {"success": False, "error": "Error interno al eliminar al alumno."},
            status=500,
        )


# 

# =====================================================
#  AGREGAR RAMO A UN PROFESOR EN UN CURSO
# =====================================================
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
@transaction.atomic
def api_agregar_carga_horaria(request):
    """
    Asigna una asignatura a un profesor en un curso.
    NO maneja día/hora, solo curso + ramo.

    Espera JSON:
    {
        "profesor_id": 12,
        "curso_id": "4B",
        "asignatura": "Matemática"
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))

        profesor_id = data.get("profesor_id")
        curso_id    = data.get("curso_id")      # Grade.curso_id
        asignatura  = (data.get("asignatura") or "").strip()

        # --- Validaciones básicas ---
        if not profesor_id or not curso_id or not asignatura:
            return JsonResponse(
                {"success": False, "error": "Faltan campos obligatorios."},
                status=400,
            )

        # Profesor
        profesor = get_object_or_404(User, id=profesor_id, role=User.TEACHER)

        # Curso (Grade) y Clase (Class)
        grade = get_object_or_404(Grade, curso_id=curso_id)

        # Tomamos el año actual para la clase
        year_actual = timezone.now().year
        clase, _ = Class.objects.get_or_create(
            grade=grade,
            year=year_actual,
            defaults={"teacher": profesor},
        )

        # Creamos / actualizamos la asignatura para esa clase
        subject, created = Subject.objects.get_or_create(
            name=asignatura,
            class_group=clase,
            defaults={"teacher": profesor},
        )
        if not created and subject.teacher_id != profesor.id:
            subject.teacher = profesor
            subject.save(update_fields=["teacher"])

        return JsonResponse({
            "success": True,
            "message": (
                f'Ramo "{subject.name}" asignado a '
                f'{profesor.first_name} {profesor.last_name} '
                f'en el curso {grade.curso_nombre} ({year_actual}).'
            ),
            "subject": {
                "id": subject.id,
                "name": subject.name,
                "curso": grade.curso_nombre,
                "year": year_actual,
                "profesor": f"{profesor.first_name} {profesor.last_name}",
            },
        }, status=201)

    except Exception as e:
        print("❌ Error en api_agregar_carga_horaria:", e)
        return JsonResponse(
            {"success": False, "error": "Error interno al agregar la carga horaria."},
            status=500,
        )
