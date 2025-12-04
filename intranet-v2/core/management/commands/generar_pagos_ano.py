import calendar
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Enrollment, Payment, User


class Command(BaseCommand):
    help = "Genera matrícula y mensualidades para todos los alumnos activos de un año"

    def add_arguments(self, parser):
        parser.add_argument("anio", type=int, help="Año académico (ej: 2025)")
        parser.add_argument(
            "--matricula",
            type=int,
            default=0,
            help="Monto de la matrícula (ej: 500000)",
        )
        parser.add_argument(
            "--mensualidad",
            type=int,
            default=0,
            help="Monto de cada mensualidad (ej: 250000)",
        )
        parser.add_argument(
            "--dia_venc",
            type=int,
            default=5,
            help="Día de vencimiento de cada cuota (ej: 5)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        anio = options["anio"]
        monto_matricula = options["matricula"]
        monto_mensualidad = options["mensualidad"]
        dia_venc = options["dia_venc"]

        # Meses de clases en Chile (marzo a diciembre)
        meses_mensualidad = list(range(3, 13))  # 3..12

        self.stdout.write(self.style.NOTICE(
            f"Generando pagos para el año {anio} "
            f"(matrícula={monto_matricula}, mensualidad={monto_mensualidad})"
        ))

        # Buscar alumnos activos del año
        enrollments = (
            Enrollment.objects
            .select_related("student", "class_group")
            .filter(
                active_status="active",
                class_group__year=anio
            )
        )

        total_alumnos = enrollments.count()
        self.stdout.write(f"Alumnos activos encontrados: {total_alumnos}")

        creados = 0
        saltados = 0

        for enr in enrollments:
            alumno = enr.student  # User con role student

            # -----------------------------
            # 1) Matrícula
            # -----------------------------
            if monto_matricula > 0:
                concepto_mat = f"Matrícula {anio}"
                due_mat = date(anio, 3, min(dia_venc, 28))  # ej: 5 de marzo

                existe_mat = Payment.objects.filter(
                    student=alumno,
                    concept=concepto_mat,
                    due_date=due_mat
                ).exists()

                if existe_mat:
                    saltados += 1
                else:
                    Payment.objects.create(
                        student=alumno,
                        amount=monto_matricula,
                        concept=concepto_mat,
                        due_date=due_mat,
                        status="pending",
                    )
                    creados += 1

            # -----------------------------
            # 2) Mensualidades marzo–diciembre
            # -----------------------------
            if monto_mensualidad > 0:
                for mes in meses_mensualidad:
                    nombre_mes = calendar.month_name[mes].capitalize()
                    concepto_mens = f"Mensualidad {nombre_mes} {anio}"

                    # Evitar días inválidos (ej: 31 de febrero)
                    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
                    dia_real = min(dia_venc, ultimo_dia_mes)
                    due_mens = date(anio, mes, dia_real)

                    existe_mens = Payment.objects.filter(
                        student=alumno,
                        concept=concepto_mens,
                        due_date=due_mens,
                    ).exists()

                    if existe_mens:
                        saltados += 1
                    else:
                        Payment.objects.create(
                            student=alumno,
                            amount=monto_mensualidad,
                            concept=concepto_mens,
                            due_date=due_mens,
                            status="pending",
                        )
                        creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pagos creados: {creados} | Pagos saltados (ya existían): {saltados}"
        ))
