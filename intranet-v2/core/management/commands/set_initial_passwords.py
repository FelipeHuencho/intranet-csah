import unicodedata
import re
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User

def strip_accents(s: str) -> str:
    if not s:
        return ""
    # Normaliza y quita tildes
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
    if not rut:
        return "00"
    digits = re.sub(r"[^0-9]", "", rut)   # deja solo dígitos
    return (digits[:2] or "00")

def build_password(user: User) -> str:
    aa = first_letters(user.first_name, 2, upper=True)   # 2 letras nombre (MAY)
    bbbbb = first_letters(user.last_name, 5, lower=True) # 5 letras apellido (min)
    dd = first_two_digits_of_rut(user.rut)               # 2 dígitos RUT
    # Si faltan letras, rellena con X / x para que no quede vacía
    if len(aa) < 2:
        aa = (aa + "XX")[:2]
    if len(bbbbb) < 5:
        bbbbb = (bbbbb + "xxxxx")[:5]
    if len(dd) < 2:
        dd = (dd + "0")[:2]
    return f"{aa}{bbbbb}{dd}"

class Command(BaseCommand):
    help = (
        "Asigna contraseñas iniciales a usuarios según regla: "
        "2 letras nombre (MAY) + 5 letras apellido (min) + 2 dígitos del RUT. "
        "Opcionalmente exporta un CSV con (rut,password)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--role", type=str, default="student",
                            help="Filtra por rol (student, guardian, teacher, admin, finance_admin) o 'all'")
        parser.add_argument("--only-empty", action="store_true",
                            help="Solo usuarios sin contraseña usable (ej: creados por CSV)")
        parser.add_argument("--export-csv", type=str, default="",
                            help="Ruta para exportar CSV con (rut, password) de los afectados")
        parser.add_argument("--dry-run", action="store_true",
                            help="No guarda cambios, solo muestra/expone CSV si se pide")

    @transaction.atomic
    def handle(self, *args, **opts):
        role = opts["role"].lower()
        only_empty = opts["only_empty"]
        export_csv = opts["export_csv"]
        dry = opts["dry_run"]

        qs = User.objects.all()
        if role != "all":
            qs = qs.filter(role=role)

        if only_empty:
            # Usuarios que no tienen password usable (por ej. set_unusable_password)
            qs = qs.filter(password__isnull=True) | qs.filter(password="")

        qs = qs.order_by("id")

        rows = []
        count = 0

        for u in qs:
            pwd = build_password(u)
            rows.append((u.rut, pwd))
            if not dry:
                u.set_password(pwd)  # guarda con hash
                u.save(update_fields=["password"])
            count += 1

        # Exporta CSV
        if export_csv:
            with open(export_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["rut", "password_inicial"])
                w.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f"CSV exportado a: {export_csv} ({len(rows)} filas)"))

        msg = f"{'(DRY-RUN) ' if dry else ''}Usuarios procesados: {count}"
        self.stdout.write(self.style.SUCCESS(msg))

