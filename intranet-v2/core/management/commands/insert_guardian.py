import csv
from django.core.management.base import BaseCommand
from core.models import User, GuardianRelation, Comuna, GuardianProfile


def normalize_rut(rut: str) -> str:
    """
    Deja el RUT tal como viene en el Excel,
    solo quitando espacios al inicio y al final.
    NO elimina puntos ni guion.
    """
    return (rut or "").strip()


class Command(BaseCommand):
    help = 'Importa apoderados desde un archivo CSV y los asocia con sus alumnos.'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Ruta completa del archivo CSV, ejemplo: C:/Users/Softer/Documents/guardians.csv'
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        count = 0
        relations = 0

        # ==========================
        #  Abrir CSV con 2 intentos
        # ==========================
        try:
            with open(csv_file, newline='', encoding='utf-8') as f:
                sample = f.read(2048)
                delimiter = ';' if ';' in sample else ','
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)
                raw_rows = list(reader)
        except UnicodeDecodeError:
            self.stdout.write(self.style.WARNING("⚠️ Archivo no está en UTF-8, intentando con ISO-8859-1..."))
            with open(csv_file, newline='', encoding='ISO-8859-1') as f:
                sample = f.read(2048)
                delimiter = ';' if ';' in sample else ','
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)
                raw_rows = list(reader)

        # Normalizar encabezados y filas (llaves en minúscula)
        fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
        self.stdout.write(self.style.WARNING(f"Encabezados detectados: {fieldnames}"))

        rows = []
        for r in raw_rows:
            norm = {}
            for k, v in (r or {}).items():
                key = (k or "").strip().lower()
                val = (v or "").strip()
                norm[key] = val
            rows.append(norm)

        for row in rows:
            # ==========================
            #  Datos básicos
            # ==========================
            rut = normalize_rut(row.get('rut', ''))
            if not rut:
                continue

            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            email = row.get('email', '').strip() or None
            phone = row.get('phone', '').strip() or None

            # comuna es texto para buscar/crear Comuna
            comuna_name = row.get('comuna', '').strip()
            comuna_obj = None
            if comuna_name:
                comuna_obj, _ = Comuna.objects.get_or_create(
                    nombre=comuna_name.upper()
                )

            student_rut = normalize_rut(row.get('student_rut', '').strip())

            # PIN 
            payment_pin = row.get('payment_pin') or row.get('pin') or ''
            payment_pin = payment_pin.strip() or None

            # ==========================
            #  Crear / obtener apoderado
            # ==========================
            guardian, created = User.objects.get_or_create(
                rut=rut,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'comuna': comuna_obj,     #  FK a Comuna
                    'role': User.GUARDIAN,    # SOLO para nuevos usuarios
                    'active_status': 'active',
                }
            )

            if created:
                self.stdout.write(f'🟢 Creado apoderado: {first_name} {last_name} (rol={guardian.role})')
            else:
                #  Si ya existe (puede ser GUARDIAN, ADMIN, FINANCE_ADMIN, etc.)
                # NO tocamos el rol, solo datos de contacto.
                changed = False
                update_fields = {}

                campos_actualizables = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'comuna': comuna_obj,
                    'active_status': 'active',
                }

                for field, value in campos_actualizables.items():
                    if getattr(guardian, field) != value and value is not None:
                        setattr(guardian, field, value)
                        update_fields[field] = value
                        changed = True

                if changed:
                    guardian.save(update_fields=list(update_fields.keys()))
                    self.stdout.write(
                        f'🟡 Actualizado apoderado: {guardian.first_name} {guardian.last_name} (rol={guardian.role})'
                    )
                else:
                    self.stdout.write(
                        f'ℹ️ Sin cambios en apoderado: {guardian.first_name} {guardian.last_name} (rol={guardian.role})'
                    )

            # ==========================
            #  GuardianProfile (PIN)
            # ==========================
            # Ahora GuardianProfile permite GUARDIAN / ADMIN / FINANCE_ADMIN
            if payment_pin is not None:
                GuardianProfile.objects.update_or_create(
                    user=guardian,
                    defaults={"payment_pin": payment_pin},
                )

            # ==========================
            #  Asociar con el estudiante
            # ==========================
            if student_rut:
                try:
                    student = User.objects.get(rut=student_rut, role=User.STUDENT)
                    GuardianRelation.objects.get_or_create(
                        guardian=guardian,
                        student=student
                    )
                    self.stdout.write(
                        f'   ↳ Asociado con estudiante: {student.first_name} {student.last_name}'
                    )
                    relations += 1
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ No se encontró estudiante con RUT {student_rut}')
                    )

            count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Carga completa. {count} apoderados procesados, {relations} relaciones creadas.'
        ))
