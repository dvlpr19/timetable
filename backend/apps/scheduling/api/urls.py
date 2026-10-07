from django.urls import path
from rest_framework.routers import DefaultRouter

from . import personal, views

router = DefaultRouter()
router.register("schedules", views.ScheduleViewSet, basename="schedule")
router.register("entries", views.EntryViewSet, basename="entry")
router.register(
    "reschedule-requests", personal.RescheduleRequestViewSet, basename="reschedule-request"
)

urlpatterns = [
    path("timetable/", views.TimetableView.as_view(), name="timetable"),
    path("timetable/occurrences/", views.OccurrencesView.as_view(), name="occurrences"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("export/", views.ExportView.as_view(), name="export"),
    path("export/ics/", personal.IcsView.as_view(), name="export-ics"),
    path("free-rooms/", personal.FreeRoomsView.as_view(), name="free-rooms"),
    *router.urls,
]
