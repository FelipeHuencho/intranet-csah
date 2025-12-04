from django.urls import path
from . import views

app_name = "profesorView"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("perfil-data/", views.perfil_data, name="perfil-data"),
    path("cursos/", views.cursos_docente, name="cursos"),
    path("curso/<int:class_id>/alumnos/", views.alumnos_por_curso, name="alumnos-curso"),
    path("curso/<int:class_id>/asignaturas/", views.asignaturas_por_curso, name="asignaturas-curso"),
    path("evaluation-types/", views.evaluation_types, name="evaluation-types"),
    path("crear-evaluacion/", views.crear_evaluacion, name="crear-evaluacion"),
    path("evaluacion/<int:eval_id>/notas/guardar/", views.guardar_notas, name="guardar-notas"),
    path("evaluacion/<int:eval_id>/alumnos-notas/", views.alumnos_con_notas, name="alumnos-con-notas"),
    path("curso/<int:class_id>/evaluaciones/", views.evaluaciones_por_curso, name="evaluaciones-curso"),
    path("mis-cursos-notas/", views.mis_cursos_y_notas, name="mis_cursos_notas"),
    path("proximas-evaluaciones/", views.proximas_evaluaciones),
    path("clases-hoy/", views.clases_hoy, name="clases_hoy"),
]
