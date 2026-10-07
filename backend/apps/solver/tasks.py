from celery import shared_task

from . import service


@shared_task(name="solver.run")
def run_solver(run_id: int) -> str:
    return service.execute(run_id).status
