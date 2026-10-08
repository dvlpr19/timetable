import type { Language } from '@/i18n';

export type Role = 'admin' | 'dekanat' | 'kafedra_mudiri' | 'oqituvchi' | 'talaba';

export interface CurrentUser {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email?: string;
  phone?: string;
  date_joined?: string;
  last_login?: string | null;
  role: Role;
  language: Language;
  language_auto: boolean;
  student: {
    id: number;
    hemis_id?: string;
    middle_name?: string;
    group: { id: number; name: string; course: number };
    subgroup: number | null;
    program: string;
    faculty?: string;
    form: string;
    form_name?: string;
    teaching_language?: string;
    shift?: number;
  } | null;
  teacher: {
    id: number;
    short_name: string;
    middle_name?: string;
    department: string;
    faculty?: string;
    position: string;
    degree?: string | null;
    employment?: string;
    max_weekly_lessons?: number;
    annual_load_hours?: number;
    teaching_languages?: string[];
    subjects?: string[];
  } | null;
  faculty_name?: string | null;
  department_name?: string | null;
}
