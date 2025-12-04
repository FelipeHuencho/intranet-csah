# core/management/commands/generar_claves_profes.py
import unicodedata
import re
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User

try:
    from openpyxl import Workbook  # type: ignore
except ImportError:
    Workbook = None


def strip_accents(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def first_letters(name: str, n: int, upper=False, lower=False) -> str:
    base = strip_accents((name or "").strip())
    base = re.sub(r"[^A-Za-z]", "", base)
    out = base[:n]
    if upper:
        out = out.upper()
    if lower:
        out = out.lower()
    return out


def first_two_digits_of_rut(rut: str) -> str:
    if not rut:
        return "00"
    digits = re.sub(r"[^0-9]", "", rut)
    return (digits[:2] or "00")


def build_password(user: User) -> str:
    aa = first_letters(user.first_name, 2, upper=True)
    bbbbb = first_letters(user.last_name, 5, lower=True)
    dd = first_two_digits_of_rut(user.rut)

    if len(aa) < 2:
        aa = (aa + "XX")[:2]
    if len(bbbbb) < 5:
        bbbbb = (bbbbb + "xxxxx")[:5]
    if len(dd) < 2:
        dd = (dd + "0")[:2]

    return f"{aa}{bbbbb}{dd}"


class Command(BaseCommand):
    help = (
        "Genera contraseñas iniciales para usuarios (por rol) con la regla: "
        "2 letras nombre (MAY) + 5 letras apellido (min) + 2 dígitos del RUT "
        "y las guarda en un Excel."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            type=str,
            default="teacher",  
            help="Rol a procesar (student, guardian, teacher, admin, finance_admin o 'all')",
        )
        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Solo usuarios sin password usable",
        )
        parser.add_argument(
            "--xlsx-path",
            type=str,
            default=r"C:\Users\Carta\Desktop\Base de datos K\profesores.xlsx",
            help="Ruta absoluta del .xlsx a generar",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No guarda en la BD, solo genera el Excel",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        if Workbook is None:
            self.stderr.write(self.style.ERROR("Debes instalar openpyxl: pip install openpyxl"))
            return

        role = opts["role"].lower()
        only_empty = opts["only_empty"]
        xlsx_path = opts["xlsx_path"]
        dry = opts["dry_run"]

        qs = User.objects.all()
        if role != "all":
            qs = qs.filter(role=role)

        if only_empty:
            qs = qs.filter(password__isnull=True) | qs.filter(password="")

        qs = qs.order_by("id")

        # preparar carpeta
        folder = os.path.dirname(xlsx_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Contraseñas"
        ws.append(["rut", "nombre", "apellido", "password_inicial"])

        count = 0

        for u in qs:
            pwd = build_password(u)
            # escribir en el excel
            ws.append([u.rut, u.first_name, u.last_name, pwd])

            # guardar en la BD si no es dry-run
            if not dry:
                u.set_password(pwd)
                u.save(update_fields=["password"])

            count += 1

        wb.save(xlsx_path)
        self.stdout.write(self.style.SUCCESS(f"Excel guardado en: {xlsx_path}"))
        self.stdout.write(self.style.SUCCESS(f"{'(DRY-RUN) ' if dry else ''}Usuarios procesados: {count}"))
