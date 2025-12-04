from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager


# ==========================
#  User Manager (usa RUT)
# ==========================
class CustomUserManager(DjangoUserManager):
    use_in_migrations = True

    def _create_user(self, rut, email=None, password=None, **extra_fields):
        if not rut:
            raise ValueError("El RUT es obligatorio")
        email = self.normalize_email(email)

        user = self.model(rut=str(rut).strip(), email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, rut, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(rut, email, password, **extra_fields)

    def create_superuser(self, rut, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(rut, email, password, **extra_fields)


# ==========================
#  Catálogo de Comunas
# ==========================
class Comuna(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# ==========================
#  Usuario
# ==========================
class User(AbstractUser):
    STUDENT = "student"
    GUARDIAN = "guardian"
    TEACHER = "teacher"
    ADMIN = "admin"
    FINANCE_ADMIN = "finance_admin"

    ROLE_CHOICES = [
        (STUDENT, "Alumno"),
        (GUARDIAN, "Apoderado"),
        (TEACHER, "Profesor"),
        (ADMIN, "Administrador"),
        (FINANCE_ADMIN, "Administrador de Finanzas"),
    ]

    username = None
    rut = models.CharField(max_length=15, unique=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=STUDENT)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    ingreso_date = models.DateField(null=True, blank=True)
    active_status = models.CharField(
        max_length=20,
        choices=[("active", "Activo"), ("inactive", "Inactivo")],
        default="active"
    )

    #  Soluciona conflicto con auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',   # nombre único
        blank=True,
        help_text='Los grupos a los que pertenece este usuario.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_permissions_set',  # nombre único
        blank=True,
        help_text='Permisos específicos para este usuario.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = "rut"
    REQUIRED_FIELDS = ["first_name", "last_name", "email"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"

    # Helpers opcionales para perfilar más fácil
    @property
    def tprofile(self):
        """Acceso rápido al perfil de profesor."""
        from .models import TeacherProfile  # import local para evitar ciclos
        if self.role != User.TEACHER:
            return None
        profile, _ = TeacherProfile.objects.get_or_create(user=self)
        return profile

    @property
    def gprofile(self):
        """
        Acceso rápido al perfil de apoderado.
        Cualquier usuario (admin, teacher, guardian, etc.) puede tener
        un GuardianProfile y por lo tanto actuar como apoderado.
        """
        from .models import GuardianProfile
        profile, _ = GuardianProfile.objects.get_or_create(user=self)
        return profile


# ==========================
#  Managers por rol (opcionales)
# ==========================
class StudentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.STUDENT)


class TeacherManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.TEACHER)


class GuardianManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.GUARDIAN)


# ==========================
#  Perfiles por rol
# ==========================
class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.TEACHER},
        related_name="teacher_profile",
    )
    department = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=150, null=True, blank=True)
    position = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return f"Perfil profesor: {self.user.rut}"


class GuardianProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guardian_profile",  # sin limit_choices_to
    )
    payment_pin = models.CharField(
        max_length=12,
        null=True,
        blank=True,
        help_text="PIN de autorización de pagos del apoderado",
    )

    def __str__(self):
        return f"Perfil apoderado: {self.user.rut}"




# ==========================
#  Grados y Clases
# ==========================
class Grade(models.Model):
    curso_id = models.CharField(max_length=5, primary_key=True)
    curso_nombre = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return f"{self.curso_id} - {self.curso_nombre}"


class Class(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    year = models.IntegerField()
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, limit_choices_to={"role": User.TEACHER}
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["grade", "year"], name="unique_class_per_year")
        ]

    def __str__(self):
        return f"{self.grade} - {self.year}"


# ==========================
#  Asignaturas
# ==========================
class Subject(models.Model):
    name = models.CharField(max_length=100)
    class_group = models.ForeignKey(Class, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, limit_choices_to={"role": User.TEACHER}
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "class_group"], name="unique_subject_per_class")
        ]

    def __str__(self):
        return f"{self.name} ({self.class_group})"


class SubjectSchedule(models.Model):
    MON, TUE, WED, THU, FRI = range(5)
    DOW_CHOICES = [
        (MON, "Lunes"),
        (TUE, "Martes"),
        (WED, "Miércoles"),
        (THU, "Jueves"),
        (FRI, "Viernes"),
    ]

    subject = models.ForeignKey(
        "core.Subject",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DOW_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F("start_time")),
                name="sched_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["subject", "day_of_week", "start_time", "end_time"],
                name="uniq_subject_timeslot",
            ),
        ]

    def __str__(self):
        return f"{self.subject} • {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


# ==========================
#  Matrículas
# ==========================
class Enrollment(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": User.STUDENT}
    )
    class_group = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    active_status = models.CharField(
        max_length=20,
        choices=[("active", "Activo"), ("inactive", "Inactivo")],
        default="active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "class_group"], name="unique_enrollment")
        ]

    def __str__(self):
        return f"{self.student} en {self.class_group}"


# ==========================
#  Relación Apoderado - Alumno
# ==========================
class GuardianRelation(models.Model):
    guardian = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="guardian_relations",
        # cualquier usuario puede ser apoderado (teacher, admin, guardian, etc.)
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_relations",
        limit_choices_to={"role": User.STUDENT},
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["guardian", "student"],
                name="unique_guardian_student"
            )
        ]

    def __str__(self):
        return f"{self.guardian} -> {self.student}"



# ==========================
#  Evaluaciones y Resultados
# ==========================
class EvaluationType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class Evaluation(models.Model):
    class_group = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": User.TEACHER}
    )
    evaluation_type = models.ForeignKey(EvaluationType, on_delete=models.CASCADE)
    date = models.DateField()
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.evaluation_type} ({self.date})"


class GradeResult(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": User.STUDENT}
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "student"], name="unique_grade_result")
        ]

    def __str__(self):
        return f"{self.student} - {self.evaluation.subject.name}: {self.score}"


# ==========================
#  Asistencia
# ==========================
class Attendance(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": User.STUDENT}
    )
    class_group = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField()
    present = models.BooleanField()
    justified_absence = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "class_group", "date"], name="unique_attendance")
        ]

    def __str__(self):
        return f"{self.student} - {self.date}: {'Presente' if self.present else 'Ausente'}"


# ==========================
#  Pagos (Versión Getnet)
# ==========================
class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("pending_review", "En revisión"),
        ("rejected", "Rechazado"),
        ("overdue", "Vencido"),
        ("paid", "Pagado"),
        ("failed", "Fallido"),
        ("refunded", "Reembolsado"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"}
    )

    # Datos principales del pago
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    concept = models.CharField(max_length=100, default="Mensualidad")

    # Fechas importantes
    issue_date = models.DateField(auto_now_add=True, help_text="Fecha de emisión del pago")
    due_date = models.DateField(null=True, blank=True, help_text="Fecha de vencimiento")
    paid_at = models.DateField(null=True, blank=True, help_text="Fecha en que se completó el pago")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    #  PROPIEDADES ESPECÍFICAS DE GETNET
 
    getnet_request_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        unique=True,
        help_text="ID de solicitud de sesión enviado a Getnet (Reference)"
    )

    #   token real de la transacción
    getnet_token = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        help_text="Token de transacción recibido al crear la sesión (lo usa el webhook)"
    )

    getnet_transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="ID de transacción final devuelto por Getnet (Webhook)"
    )

    getnet_auth_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Código de autorización bancario (Autorización)"
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.status == "pending"
            and self.due_date
            and self.due_date < timezone.localdate()
        )

    @property
    def days_late(self):
        from django.utils import timezone
        if self.is_overdue:
            return (timezone.localdate() - self.due_date).days
        return 0

    def __str__(self):
        estado = self.get_status_display()
        return f"{self.student} - {self.concept}: ${self.amount} ({estado})"


# --- PROXIES para Admins separados ---
class Student(User):
    objects = StudentManager()

    class Meta:
        proxy = True
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"


class Guardian(User):
    objects = GuardianManager()

    class Meta:
        proxy = True
        verbose_name = "Apoderado"
        verbose_name_plural = "Apoderados"


class Teacher(User):
    objects = TeacherManager()

    class Meta:
        proxy = True
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"


# ==========================
#  Comunicados
# ==========================
class Comunicado(models.Model):
    DESTINO_CHOICES = [
        ("todos", "Todos los usuarios"),
        ("curso", "Por curso"),
        ("manual", "Correo manual"),
    ]

    asunto = models.CharField(max_length=200, help_text="Título o asunto del comunicado")
    mensaje = models.TextField(help_text="Contenido del mensaje a enviar")
    destino = models.CharField(
        max_length=20,
        choices=DESTINO_CHOICES,
        help_text="Destino del comunicado (todos, curso o manual)"
    )

    destinatarios = models.TextField(
        blank=True,
        help_text="Correos separados por coma a los que se envió este comunicado"
    )

    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comunicados_enviados"
    )

    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_envio"]
        verbose_name = "Comunicado"
        verbose_name_plural = "Comunicados"

    def __str__(self):
        return f"{self.asunto} - {self.fecha_envio.strftime('%d/%m/%Y %H:%M')}"
