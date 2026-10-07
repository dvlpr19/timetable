from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("solver-runs", views.SolverRunViewSet, basename="solver-run")

urlpatterns = router.urls
