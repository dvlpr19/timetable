"""Run the automatic timetabler from the command line (experiments, acceptance check).

python manage.py run_solver --faculty ISL --time-limit 120
"""

from django.core.management.base import BaseCommand, CommandError

from apps.academics.models import EducationForm, Faculty
from apps.scheduling.api.views import current_semester

from ... import service
from ...models import SolverRun


class Command(BaseCommand):
    help = "Build a timetable draft with CP-SAT and print the numbers."

    def add_arguments(self, parser):
        parser.add_argument("--faculty", help="faculty code, e.g. ISL")
        parser.add_argument("--form", help="education form code, e.g. kunduzgi")
        parser.add_argument("--mode", choices=("rebuild", "fill"), default="rebuild")
        parser.add_argument("--time-limit", type=int, default=90)
        parser.add_argument("--seed", type=int, default=0)
        parser.add_argument("--workers", type=int, default=8)

    def handle(self, *args, **opts):
        try:
            faculty = Faculty.objects.get(code=opts["faculty"]) if opts["faculty"] else None
            form = EducationForm.objects.get(code=opts["form"]) if opts["form"] else None
        except (Faculty.DoesNotExist, EducationForm.DoesNotExist) as e:
            raise CommandError(str(e)) from e
        semester = current_semester()
        run = SolverRun.objects.create(
            semester=semester,
            faculty=faculty,
            form=form,
            base_schedule=service.base_schedule_for(semester),
            params={
                "mode": opts["mode"],
                "time_limit": opts["time_limit"],
                "seed": opts["seed"],
                "workers": opts["workers"],
            },
        )
        run = service.execute(run.pk)
        seconds = (run.finished_at - run.started_at).total_seconds()
        self.stdout.write(
            f"run #{run.pk}: {run.status} in {seconds:.1f}s — placed {run.lessons_placed}/"
            f"{run.lessons_total}, hard conflicts {run.hard_violations}, "
            f"soft score {run.soft_violations.get('score')}"
        )
        if run.result_schedule_id:
            self.stdout.write(f"draft: {run.result_schedule.name} (id {run.result_schedule_id})")
        for d in run.diagnostics:
            if d["severity"] != "info":
                self.stdout.write(f"  [{d['severity']}] {d['message']['en']}")
