import type { RunStatus, SolverRun } from '@/types/solver';

export const STATUS_PILL: Record<RunStatus, string> = {
  queued: 'bg-subtle text-ink-muted',
  running: 'bg-warning-bg text-warning-fg',
  succeeded: 'bg-lesson-lecture-bg text-lesson-lecture',
  infeasible: 'bg-danger-bg text-danger-fg',
  failed: 'bg-danger-bg text-danger-fg',
  cancelled: 'bg-subtle text-ink-muted',
};

export const isActive = (status: RunStatus) => status === 'queued' || status === 'running';

export function duration(run: SolverRun): number | null {
  if (!run.started_at || !run.finished_at) return null;
  return Math.round(
    (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000,
  );
}
