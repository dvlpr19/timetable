from django.conf import settings
from django.db import connection
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core import clock


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    """Public app info; texts follow the Accept-Language header."""
    return Response(
        {
            "app_name": _("Timetable"),
            "academy_name": _("International Islamic Academy of Uzbekistan"),
            "language": get_language(),
            "languages": [code for code, _name in settings.LANGUAGES],
            "now": clock.now().isoformat(timespec="seconds"),
            "today": clock.today().isoformat(),
            "demo_date": clock.is_demo(),
        }
    )
