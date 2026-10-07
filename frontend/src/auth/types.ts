import type { Language } from '@/i18n';

export type Role = 'admin' | 'dekanat' | 'kafedra_mudiri' | 'oqituvchi' | 'talaba';

export interface CurrentUser {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  language: Language;
  language_auto: boolean;
  student: {
    id: number;
    group: { id: number; name: string; course: number };
    subgroup: number | null;
    program: string;
    form: string;
  } | null;
  teacher: { id: number; short_name: string; department: string; position: string } | null;
}
