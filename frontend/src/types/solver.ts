export type RunStatus = 'queued' | 'running' | 'succeeded' | 'infeasible' | 'failed' | 'cancelled';

export interface Diagnostic {
  code: string;
  severity: 'error' | 'warning' | 'info';
  assignment_id: number | null;
  message: string;
}

export interface SolverRun {
  id: number;
  semester: number;
  faculty: number | null;
  faculty_name: string | null;
  form: number | null;
  form_name: string | null;
  base_schedule: number | null;
  base_name: string | null;
  result_schedule: number | null;
  result_name: string | null;
  params: {
    mode?: 'rebuild' | 'fill';
    time_limit?: number;
    seed?: number;
    weights?: Record<string, number>;
  };
  status: RunStatus;
  status_display: string;
  progress: {
    phase?: 'placing' | 'improving';
    elapsed?: number;
    placed?: number;
    total?: number;
    objective?: number;
    solutions?: number;
  };
  created_by_name: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  objective: number | null;
  lessons_total: number;
  lessons_placed: number;
  hard_violations: number;
  soft_violations: Record<string, number>;
  diagnostics: Diagnostic[];
  model_stats: Record<string, unknown>;
}

export interface Precheck {
  lessons: number;
  units: number;
  kept: number;
  replaced: number;
  diagnostics: Diagnostic[];
}

export interface VersionSummary {
  id: number;
  name: string;
  lessons: number;
  missing: number;
  hard_conflicts: number;
  links_missing: number;
  soft: Record<string, number>;
  soft_score: number;
}

export interface Comparison {
  result: VersionSummary;
  base: VersionSummary | null;
  kept: number;
  added: number;
  removed: number;
}

export const SOFT_CODES = [
  'student_gaps',
  'teacher_gaps',
  'teacher_preference',
  'subject_crowding',
  'lecture_order',
  'building_moves',
  'building_spread',
  'shift',
  'soft_blocked',
] as const;

export const DEFAULT_WEIGHTS: Record<(typeof SOFT_CODES)[number], number> = {
  student_gaps: 10,
  teacher_gaps: 3,
  teacher_preference: 5,
  subject_crowding: 8,
  lecture_order: 4,
  building_moves: 6,
  building_spread: 2,
  shift: 6,
  soft_blocked: 1,
};
