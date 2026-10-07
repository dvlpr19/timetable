from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
for prefix, viewset in [
    ("faculties", views.FacultyViewSet),
    ("departments", views.DepartmentViewSet),
    ("education-levels", views.EducationLevelViewSet),
    ("education-forms", views.EducationFormViewSet),
    ("lesson-times", views.LessonTimeViewSet),
    ("blocked-periods", views.BlockedPeriodViewSet),
    ("programs", views.ProgramViewSet),
    ("program-forms", views.ProgramFormViewSet),
    ("academic-years", views.AcademicYearViewSet),
    ("semesters", views.SemesterViewSet),
    ("teaching-periods", views.TeachingPeriodViewSet),
    ("calendar-days", views.CalendarDayViewSet),
    ("buildings", views.BuildingViewSet),
    ("room-types", views.RoomTypeViewSet),
    ("rooms", views.RoomViewSet),
    ("lesson-types", views.LessonTypeViewSet),
    ("subjects", views.SubjectViewSet),
    ("curriculum", views.CurriculumItemViewSet),
    ("groups", views.GroupViewSet),
    ("subgroups", views.SubGroupViewSet),
    ("streams", views.StreamViewSet),
    ("teachers", views.TeacherViewSet),
    ("teacher-availability", views.TeacherAvailabilityViewSet),
    ("students", views.StudentViewSet),
    ("assignments", views.TeachingAssignmentViewSet),
]:
    router.register(prefix, viewset, basename=prefix)

urlpatterns = router.urls
