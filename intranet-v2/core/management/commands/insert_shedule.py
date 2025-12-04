import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Class, Subject, SubjectSchedule, User


def parse_time(value: str):
    """Convierte '8:00' o '09:45' en time()."""
    s = (value or "").strip()
    if not s:
        return None
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Hora inválida: {value!r}")


DAY_MAP = {
    "lunes": SubjectSchedule.MON,
    "martes": SubjectSchedule.TUE,
    "miercoles": SubjectSchedule.WED,
    "miércoles": SubjectSchedule.WED,
    "jueves": SubjectSchedule.THU,
    "viernes": SubjectSchedule.FRI,
}


def clean_rut_excel(rut: str) -> str:
    """RUT tal como viene en el Excel (solo strip)."""
    return (rut or "").strip()


def to_compact_rut(rut: str) -> str:
    """RUT sin puntos ni espacios, mantiene guion (formato viejo)."""
    rut = (rut or "").strip()
    rut = rut.replace(".", "").replace(" ", "").replace("\t", "")
    return rut


class Command(BaseCommand):
    help = "Importa horarios (Subject + SubjectSchedule) desde un CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Ruta completa del CSV de horarios",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]

        created_subjects = 0
        created_schedules = 0
        skipped = 0
        errors = 0

        # ==========================
        #  Abrir CSV (UTF-8 / ISO)
        # ==========================
        try:
            try:
                f = open(csv_path, newline="", encoding="utf-8-sig", errors="ignore")
            except UnicodeDecodeError:
                f = open(csv_path, newline="", encoding="ISO-8859-1", errors="ignore")

            with f:
                sample = f.read(4096)
                f.seek(0)
                # detectar delimitador
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
                    reader = csv.DictReader(f, dialect=dialect)
                except csv.Error:
                    reader = csv.DictReader(f, delimiter=";")

                # normalizar encabezados
                fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
                self.stdout.write(self.style.WARNING(f"Encabezados: {fieldnames}"))

                for idx, row in enumerate(reader, start=2):  # fila 2 = primera con datos
                    try:
                        # normalizar claves y valores
                        row = {
                            (k or "").strip().lower(): (v or "").strip()
                            for k, v in (row or {}).items()
                        }

                        curso_id = row.get("curso_id") or row.get("curso") or ""
                        year_str = row.get("year") or ""
                        subject_name = row.get("subject_name") or row.get("asignatura") or ""
                        teacher_rut_raw = row.get("teacher_rut") or ""
                        day_name = row.get("day_of_week") or row.get("dia") or ""
                        start_time_str = row.get("start_time") or ""
                        end_time_str = row.get("end_time") or ""

                        if not curso_id or not year_str or not subject_name or not day_name:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Fila {idx}: datos básicos incompletos, saltada."
                            ))
                            continue

                        try:
                            year = int(year_str)
                        except ValueError:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Fila {idx}: year inválido '{year_str}', saltada."
                            ))
                            continue

                        # ==========================
                        #  Buscar Class (curso + año)
                        # ==========================
                        try:
                            class_group = Class.objects.get(
                                grade__curso_id=str(curso_id),
                                year=year,
                            )
                        except Class.DoesNotExist:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Fila {idx}: no se encontró Class para curso_id={curso_id}, year={year}."
                            ))
                            continue

                        # ==========================
                        #  Mapear día de la semana
                        # ==========================
                        day_key = day_name.strip().lower()
                        if day_key not in DAY_MAP:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Fila {idx}: día '{day_name}' no reconocido, saltada."
                            ))
                            continue
                        day_of_week = DAY_MAP[day_key]

                        # ==========================
                        #  Parsear horas
                        # ==========================
                        try:
                            start_time = parse_time(start_time_str)
                            end_time = parse_time(end_time_str)
                        except ValueError as e_time:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Fila {idx}: {e_time}, saltada."
                            ))
                            continue

                        # ==========================
                        #  Buscar profesor (opcional)
                        # ==========================
                        teacher = None
                        if teacher_rut_raw and teacher_rut_raw.lower() not in ("no asignado", "null", "none", "n/a"):
                            rut_excel = clean_rut_excel(teacher_rut_raw)
                            rut_compact = to_compact_rut(teacher_rut_raw)
                            teacher = User.objects.filter(
                                role=User.TEACHER
                            ).filter(
                                Q(rut=rut_excel) | Q(rut=rut_compact)
                            ).first()
                            if not teacher:
                                self.stdout.write(self.style.WARNING(
                                    f"⚠️ Fila {idx}: profesor con RUT '{teacher_rut_raw}' no encontrado, se deja sin profesor."
                                ))

                        # ==========================
                        #  Subject (por curso + nombre)
                        # ==========================
                        subject, created = Subject.objects.get_or_create(
                            name=subject_name,
                            class_group=class_group,
                            defaults={"teacher": teacher},
                        )

                        # si ya existía pero no tenía teacher y ahora sí, lo actualizamos
                        if not created and teacher is not None and subject.teacher != teacher:
                            subject.teacher = teacher
                            subject.save(update_fields=["teacher"])

                        if created:
                            created_subjects += 1

                        # ==========================
                        #  SubjectSchedule
                        # ==========================
                        sched, sched_created = SubjectSchedule.objects.get_or_create(
                            subject=subject,
                            day_of_week=day_of_week,
                            start_time=start_time,
                            end_time=end_time,
                        )
                        if sched_created:
                            created_schedules += 1
                            self.stdout.write(
                                f"🟢 Fila {idx}: horario creado → {subject} {day_name} {start_time_str}-{end_time_str}"
                            )

                    except Exception as e_row:
                        errors += 1
                        self.stdout.write(self.style.ERROR(
                            f"❌ Error en fila {idx}: {e_row}"
                        ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ Archivo no encontrado: {csv_path}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"✅ Carga completa. Subjects creados: {created_subjects} | Horarios creados: {created_schedules} | "
            f"Filas saltadas: {skipped} | Errores: {errors}"
        ))
