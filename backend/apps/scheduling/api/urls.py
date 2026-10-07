from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("schedules", views.ScheduleViewSet, basename="schedule")
router.register("entries", views.EntryViewSet, basename="entry")

urlpatterns = [
    path("timetable/", views.TimetableView.as_view(), name="timetable"),
    path("timetable/occurrences/", views.OccurrencesView.as_view(), name="occurrences"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("export/", views.ExportView.as_view(), name="export"),
    *router.urls,
]
