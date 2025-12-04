from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    User, Payment, Grade, Class, Subject, Enrollment,
    GuardianRelation, EvaluationType, Evaluation, GradeResult, Attendance,
    Student, Guardian  # proxies 
)

# Forms para que el admin sepa que el "usuario" se identifica por RUT (no username)
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("rut", "first_name", "last_name", "email", "role")

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("rut", "first_name", "last_name", "email", "role", "is_active", "is_staff", "is_superuser")


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ("rut", "first_name", "last_name", "role", "email", "is_active", "is_staff")
    list_filter  = ("role", "is_active", "is_staff")
    search_fields = ("rut", "first_name", "last_name", "email")
    ordering = ("rut",)

    # Campos del formulario de edición
    fieldsets = (
        (None, {"fields": ("rut", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email", "phone", "address", "birth_date", "comuna", "ingreso_date")}),
        ("Rol y estado", {"fields": ("role", "active_status", "department", "title", "position")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    # Campos del formulario de creación
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("rut", "first_name", "last_name", "email", "role", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )

#  Mostramos proxies como secciones separadas
@admin.register(Student)
class StudentProxyAdmin(admin.ModelAdmin):
    list_display = ("rut", "first_name", "last_name", "email", "active_status")
    search_fields = ("rut", "first_name", "last_name", "email")

@admin.register(Guardian)
class GuardianProxyAdmin(admin.ModelAdmin):
    list_display = ("rut", "first_name", "last_name", "email", "active_status")
    search_fields = ("rut", "first_name", "last_name", "email")

# Resto de modelos para gestionarlos desde /admin/

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "concept", "amount", "status", "issue_date", "due_date", "paid_at", "is_overdue")
    list_filter = ("status", "issue_date", "due_date")
    search_fields = ("student__first_name", "student__last_name", "student__rut", "concept")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(Grade)
admin.site.register(Class)
admin.site.register(Subject)
admin.site.register(Enrollment)
admin.site.register(GuardianRelation)
admin.site.register(EvaluationType)
admin.site.register(Evaluation)
admin.site.register(GradeResult)
admin.site.register(Attendance)
