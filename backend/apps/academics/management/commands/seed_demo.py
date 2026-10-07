from django.core.management.base import BaseCommand

from apps.academics.seed.builder import build_demo


class Command(BaseCommand):
    help = "Wipe the database and load the deterministic demo dataset."

    def handle(self, *args, **options):
        summary = build_demo(self.stdout)
        width = max(len(k) for k in summary)
        for key, value in summary.items():
            self.stdout.write(f"  {key:<{width}}  {value}")
        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
