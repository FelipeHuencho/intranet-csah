import csv
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import User, Comuna, TeacherProfile

def clean_rut_excel(rut: str) -> str:
    return (rut or "").strip()

def to_compact_rut(rut: str) -> str:
    rut = (rut or "").strip()
    return rut.replace(".", "").replace(" ", "").replace("\t", "")

def detectar_encoding(path):
    """Detecta codificación sin chardet."""
    for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            with open(path, encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'

class Command(BaseCommand):
    help = "Crea/actualiza profesores desde matrizteacher.csv (tildes OK)"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta del archivo CSV')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        fila_num = 0
        actualizados = 0
        creados = 0
        errores = 0

        try:
            # --- detectar encoding automáticamente ---
            encoding = detectar_encoding(csv_path)
            self.stdout.write(f"📌 Usando codificación detectada: {encoding}")

            with open(csv_path, newline='', encoding=encoding) as f:
                sample = f.read(2048)
                f.seek(0)

                # detectar delimitador
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t'])
                    reader = csv.DictReader(f, dialect=dialect)
                except csv.Error:
                    reader = csv.DictReader(f, delimiter=';')

                for row in reader:
                    fila_num += 1
                    try:
                        row = {(k or '').strip().lower(): (v or '').strip()
                               for k, v in (row or {}).items()}

                        rut_raw = row.get('rut') or ''
                        rut_excel = clean_rut_excel(rut_raw)
                        rut_compact = to_compact_rut(rut_raw)

                        if not rut_excel:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️  Fila {fila_num}: sin RUT, saltada"
                            ))
                            continue

                        first_name = row.get('first_name', '')
                        last_name = row.get('last_name', '')

                        email_raw = (row.get('email') or '').strip()
                        email = email_raw.lower() if email_raw else None

                        phone = (row.get('phone') or '').strip() or None

                        comuna_name = (row.get('comuna') or '').strip()
                        comuna_obj = None
                        if comuna_name:
                            comuna_obj, _ = Comuna.objects.get_or_create(
                                nombre=comuna_name.upper()
                            )

                        department = (row.get('department') or row.get('departamento') or '').strip() or None
                        title = (row.get('title') or row.get('titulo') or '').strip() or None
                        position = (row.get('position') or row.get('cargo') or '').strip() or None

                        # buscar existente
                        user = User.objects.filter(
                            Q(rut=rut_excel) | Q(rut=rut_compact)
                        ).first()

                        if not user:
                            user = User.objects.create(
                                rut=rut_excel,
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                                phone=phone,
                                comuna=comuna_obj,
                                role=User.TEACHER,
                                active_status='active',
                            )
                            creados += 1
                            self.stdout.write(self.style.SUCCESS(
                                f"🟢 Creado profesor: {first_name} {last_name} ({rut_excel})"
                            ))
                        else:
                            changed = False
                            for field, value in {
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': email,
                                'phone': phone,
                                'comuna': comuna_obj,
                                'role': User.TEACHER,
                                'active_status': 'active',
                            }.items():
                                if value is not None and getattr(user, field) != value:
                                    setattr(user, field, value)
                                    changed = True

                            if changed:
                                user.save()
                                actualizados += 1
                                self.stdout.write(
                                    f"🟡 Actualizado: {user.first_name} {user.last_name} ({user.rut})"
                                )

                        TeacherProfile.objects.update_or_create(
                            user=user,
                            defaults={
                                "department": department,
                                "title": title,
                                "position": position,
                            }
                        )

                    except Exception as e_row:
                        errores += 1
                        self.stdout.write(self.style.ERROR(
                            f"❌ Error fila {fila_num} (rut='{row.get('rut','')}'): {e_row}"
                        ))

            self.stdout.write(self.style.SUCCESS('✅ Proceso finalizado'))
            self.stdout.write(self.style.SUCCESS(
                f"📊 Creados: {creados} | Actualizados: {actualizados} | Errores: {errores}"
            ))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f"❌ Error inesperado: {e}"))
            self.stdout.write(self.style.WARNING(traceback.format_exc()))
