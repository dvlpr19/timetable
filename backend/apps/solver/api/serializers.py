from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.academics.models import EducationForm, Faculty
from apps.scheduling.models import Schedule
from apps.scheduling.validators import DEFAULT_WEIGHTS

from ..models import SolverRun
from ..service import MAX_TIME_LIMIT


def localized(diagnostics: list[dict]) -> list[dict]:
    lang = (get_language() or "uz")[:2]
    return [
        {
            "code": d["code"],
            "severity": d["severity"],
            "assignment_id": d.get("assignment_id"),
            "message": d["message"].get(lang) or d["message"].get("uz", ""),
        }
        for d in diagnostics
    ]


class SolverRunSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    faculty_name = serializers.CharField(source="faculty.name", read_only=True, default=None)
    form_name = serializers.CharField(source="form.name", read_only=True, default=None)
    base_name = serializers.CharField(source="base_schedule.name", read_only=True, default=None)
    result_name = serializers.CharField(source="result_schedule.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    diagnostics = serializers.SerializerMethodField()

    class Meta:
        model = SolverRun
        fields = (
            "id",
            "semester",
            "faculty",
            "faculty_name",
            "form",
            "form_name",
            "algorithm",
            "base_schedule",
            "base_name",
            "result_schedule",
            "result_name",
            "params",
            "status",
            "status_display",
            "progress",
            "created_by_name",
            "created_at",
            "started_at",
            "finished_at",
            "objective",
            "best_bound",
            "lessons_total",
            "lessons_placed",
            "hard_violations",
            "soft_violations",
            "diagnostics",
            "model_stats",
        )
        read_only_fields = fields

    def get_diagnostics(self, run) -> list[dict]:
        return localized(run.diagnostics)


class StartSerializer(serializers.Serializer):
    """What the dispatcher chooses before a run."""

    faculty = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), required=False, allow_null=True
    )
    form = serializers.PrimaryKeyRelatedField(
        queryset=EducationForm.objects.all(), required=False, allow_null=True
    )
    base_schedule = serializers.PrimaryKeyRelatedField(
        queryset=Schedule.objects.all(), required=False, allow_null=True
    )
    mode = serializers.ChoiceField(choices=("rebuild", "fill"), default="rebuild")
    time_limit = serializers.IntegerField(min_value=10, max_value=MAX_TIME_LIMIT, default=90)
    seed = serializers.IntegerField(min_value=0, default=0)
    weights = serializers.DictField(
        child=serializers.FloatField(min_value=0, max_value=100), required=False
    )

    def validate_weights(self, value):
        unknown = set(value) - set(DEFAULT_WEIGHTS)
        if unknown:
            raise serializers.ValidationError(
                _("Unknown soft constraints: %(names)s") % {"names": ", ".join(sorted(unknown))}
            )
        return value
