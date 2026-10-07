from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/meta/", views.meta, name="meta"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.academics.api.urls")),
    path("api/", include("apps.scheduling.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
