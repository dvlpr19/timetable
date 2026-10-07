from django.contrib import admin

from .models import SolverRun


@admin.register(SolverRun)
class SolverRunAdmin(admin.ModelAdmin):
    list_display = ("pk", "semester", "faculty", "form", "status", "lessons_placed", "objective")
    list_filter = ("status", "algorithm")
