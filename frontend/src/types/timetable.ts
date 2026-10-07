export interface LessonTimeRef {
  id: number;
  number: number;
  start: string;
  end: string;
  shift: number;
}

export interface TimetableEntry {
  id: number;
  schedule: number;
  assignment: number;
  weekday: number | null;
  week_parity: 'every' | 'odd' | 'even' | null;
  date: string | null;
  lesson_time: LessonTimeRef;
  form: string;
  subject: { id: number; name: string };
  lesson_type: { code: string; name: string };
  teacher: { id: number; short_name: string; full_name: string };
  groups: { id: number; name: string }[];
  subgroup: number | null;
  stream: string | null;
  student_count: number;
  room: { id: number; name: string; building: string; floor: number; capacity: number } | null;
  online_url: string;
  is_locked: boolean;
  note: string;
}

export interface Occurrence extends TimetableEntry {
  status: 'scheduled' | 'cancelled' | 'reschedule';
}

export interface Violation {
  code: string;
  constraint?: number;
  entries?: number[];
  message: string;
}

export interface ScheduleVersion {
  id: number;
  semester: number;
  name: string;
  status: 'draft' | 'published' | 'archived';
  based_on: number | null;
  created_at: string;
  published_at: string | null;
  entry_count: number;
}

export interface GridCell {
  weekday?: number;
  date?: string;
  lesson_time: number;
  number: number;
  ok: boolean;
  room: number | null;
  free_rooms: number[];
  reasons: string[];
}

export interface UnplacedItem {
  assignment: number;
  subject: string;
  lesson_type: { code: string; name: string };
  teacher: string;
  target: string;
  form: string;
  student_count: number;
  placed: number;
  required: number;
}

export interface EducationForm {
  id: number;
  code: string;
  name: string;
  schedule_mode: 'weekly' | 'session';
  requires_room: boolean;
  study_weekdays: number[];
  lesson_times: {
    id: number;
    form: number;
    number: number;
    start: string;
    end: string;
    shift: number;
  }[];
}

export interface BlockedPeriod {
  id: number;
  name: string;
  weekday: number | null;
  start: string;
  end: string;
  form: number | null;
  is_hard: boolean;
}
