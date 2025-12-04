# core/management/commands/set_guardian_pins.py

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import GuardianRelation, GuardianProfile


DEFAULT_PIN = "12345"


class Command(BaseCommand):
    help = (
        "Asigna un PIN de portal de pagos a todos los usuarios que "
        "aparezcan como apoderados en GuardianRelation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pin",
            type=str,
            default=DEFAULT_PIN,
            help=f"PIN inicial a asignar cuando el apoderado no tenga uno (por defecto: {DEFAULT_PIN})",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Si se indica este flag, se sobrescriben también los PIN que ya existan.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        pin = options["pin"]
        overwrite = options["overwrite"]

        # Traemos todas las relaciones y armamos un set de apoderados únicos
        relations = GuardianRelation.objects.select_related("guardian").all()
        guardians = {rel.guardian for rel in relations}

        total = len(guardians)
        nuevos = 0
        actualizados = 0
        sin_cambios = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Procesando {total} apoderado(s) con relación alumno–apoderado. "
                f"PIN por defecto: {pin} | overwrite={overwrite}"
            )
        )

        for guardian in guardians:
            profile, _ = GuardianProfile.objects.get_or_create(user=guardian)

            tenia_pin = bool(profile.payment_pin)

            # Si ya tiene PIN y no queremos sobrescribir → lo dejamos tal cual
            if tenia_pin and not overwrite:
                sin_cambios += 1
                self.stdout.write(
                    f"ℹ️ {guardian.rut} ya tiene PIN ({profile.payment_pin}), se mantiene."
                )
                continue

            # Asignamos / reasignamos PIN
            profile.payment_pin = pin
            profile.save(update_fields=["payment_pin"])

            if tenia_pin and overwrite:
                actualizados += 1
                self.stdout.write(
                    f"🟡 Actualizado PIN de {guardian.rut} → {pin}"
                )
            elif not tenia_pin:
                nuevos += 1
                self.stdout.write(
                    f"🟢 Asignado PIN a {guardian.rut} → {pin}"
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Listo. Apoderados únicos={total} | PIN nuevos={nuevos} | PIN actualizados={actualizados} | Sin cambios={sin_cambios}"
        ))
