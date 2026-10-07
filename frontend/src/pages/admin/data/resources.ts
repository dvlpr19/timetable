/**
 * Data sections of the admin panel. One generic page (ResourcePage) renders each of them:
 * list with search/filters, create/edit form, delete, Excel import.
 * Labels are translation keys in the "data" namespace.
 */
import {
  BookOpen,
  Briefcase,
  Building2,
  CalendarX,
  ClipboardList,
  Clock,
  DoorOpen,
  GraduationCap,
  Layers,
  Lock,
  Network,
  UserRound,
  Users,
  UserSquare,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type Row = Record<string, unknown> & { id: number };

export type FieldType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'time'
  | 'date'
  | 'translated' // name_uz (required) + name_ru + name_en
  | 'choice' // fixed values, labels from data:choices.<choices>.<value>
  | 'choices' // several fixed values (array)
  | 'remote' // foreign key loaded from another endpoint
  | 'remotes'; // many-to-many

export interface Field {
  key: string;
  label: string; // data:fields.<label>
  type: FieldType;
  required?: boolean;
  choices?: string; // for choice/choices
  values?: (string | number)[];
  path?: string; // for remote/remotes
  /** Hide on edit (e.g. natural keys that should not change) */
  createOnly?: boolean;
  min?: number;
  max?: number;
}

export interface Column {
  key: string;
  label: string; // data:fields.<label>
  /** How to show the value: plain, a choice label, yes/no, or a custom formatter key */
  kind?: 'text' | 'choice' | 'bool' | 'load' | 'hours';
  choices?: string;
}

export interface Filter {
  param: string;
  label: string;
  path?: string; // remote options
  choices?: string; // fixed options
  values?: (string | number)[];
}

export interface Resource {
  key: string; // URL segment and permission key
  path: string; // API path
  icon: LucideIcon;
  columns: Column[];
  fields: Field[];
  filters?: Filter[];
  search?: boolean;
  importable?: boolean;
  /** roles that may open the section (the API decides what they may change) */
  roles?: string[];
}

const LANGS = ['uz', 'ru', 'en', 'ar'];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];
const STAFF = ['admin', 'dekanat', 'kafedra_mudiri'];

export const RESOURCES: Resource[] = [
  {
    key: 'faculties',
    path: '/api/faculties/',
    icon: Building2,
    search: true,
    columns: [
      { key: 'code', label: 'code' },
      { key: 'name', label: 'name' },
      { key: 'teaching_language', label: 'teachingLanguage', kind: 'choice', choices: 'language' },
    ],
    fields: [
      { key: 'code', label: 'code', type: 'text', required: true },
      { key: 'name', label: 'name', type: 'translated', required: true },
      {
        key: 'teaching_language',
        label: 'teachingLanguage',
        type: 'choice',
        choices: 'language',
        values: LANGS,
        required: true,
      },
    ],
  },
  {
    key: 'departments',
    path: '/api/departments/',
    icon: Network,
    search: true,
    filters: [{ param: 'faculty', label: 'faculty', path: '/api/faculties/' }],
    columns: [
      { key: 'code', label: 'code' },
      { key: 'name', label: 'name' },
      { key: 'faculty', label: 'faculty' },
    ],
    fields: [
      { key: 'faculty', label: 'faculty', type: 'remote', path: '/api/faculties/', required: true },
      { key: 'code', label: 'code', type: 'text', required: true },
      { key: 'name', label: 'name', type: 'translated', required: true },
    ],
  },
  {
    key: 'programs',
    path: '/api/programs/',
    icon: GraduationCap,
    search: true,
    filters: [
      { param: 'faculty', label: 'faculty', path: '/api/faculties/' },
      { param: 'level', label: 'level', path: '/api/education-levels/' },
    ],
    columns: [
      { key: 'code', label: 'programCode' },
      { key: 'name', label: 'name' },
      { key: 'level', label: 'level' },
      { key: 'faculty', label: 'faculty' },
    ],
    fields: [
      { key: 'faculty', label: 'faculty', type: 'remote', path: '/api/faculties/', required: true },
      {
        key: 'level',
        label: 'level',
        type: 'remote',
        path: '/api/education-levels/',
        required: true,
      },
      { key: 'code', label: 'programCode', type: 'text', required: true },
      { key: 'name', label: 'name', type: 'translated', required: true },
    ],
  },
  {
    key: 'groups',
    path: '/api/groups/',
    icon: Users,
    search: true,
    importable: true,
    filters: [
      { param: 'program_form__program__faculty', label: 'faculty', path: '/api/faculties/' },
      { param: 'program_form__form', label: 'form', path: '/api/education-forms/' },
      { param: 'course', label: 'course', values: [1, 2, 3, 4, 5, 6] },
      { param: 'teaching_language', label: 'teachingLanguage', choices: 'language', values: LANGS },
    ],
    columns: [
      { key: 'name', label: 'groupName' },
      { key: 'program_form', label: 'programForm' },
      { key: 'course', label: 'course' },
      { key: 'teaching_language', label: 'teachingLanguage', kind: 'choice', choices: 'language' },
      { key: 'student_count', label: 'students' },
      { key: 'shift', label: 'shift' },
    ],
    fields: [
      {
        key: 'program_form',
        label: 'programForm',
        type: 'remote',
        path: '/api/program-forms/',
        required: true,
      },
      { key: 'name', label: 'groupName', type: 'text', required: true },
      { key: 'course', label: 'course', type: 'number', required: true, min: 1, max: 6 },
      { key: 'number', label: 'numberInCourse', type: 'number', required: true, min: 1 },
      {
        key: 'teaching_language',
        label: 'teachingLanguage',
        type: 'choice',
        choices: 'language',
        values: LANGS,
        required: true,
      },
      { key: 'student_count', label: 'students', type: 'number', required: true, min: 0 },
      {
        key: 'gender_composition',
        label: 'composition',
        type: 'choice',
        choices: 'composition',
        values: ['', 'mixed', 'male', 'female'],
      },
      {
        key: 'shift',
        label: 'shift',
        type: 'choice',
        choices: 'shift',
        values: [1, 2],
        required: true,
      },
    ],
  },
  {
    key: 'streams',
    path: '/api/streams/',
    icon: Layers,
    search: true,
    filters: [{ param: 'faculty', label: 'faculty', path: '/api/faculties/' }],
    columns: [
      { key: 'name', label: 'name' },
      { key: 'faculty', label: 'faculty' },
      { key: 'teaching_language', label: 'teachingLanguage', kind: 'choice', choices: 'language' },
      { key: 'groups', label: 'groups' },
    ],
    fields: [
      {
        key: 'semester',
        label: 'semester',
        type: 'remote',
        path: '/api/semesters/',
        required: true,
      },
      { key: 'faculty', label: 'faculty', type: 'remote', path: '/api/faculties/', required: true },
      { key: 'name', label: 'name', type: 'text', required: true },
      {
        key: 'teaching_language',
        label: 'teachingLanguage',
        type: 'choice',
        choices: 'language',
        values: LANGS,
        required: true,
      },
      { key: 'groups', label: 'groups', type: 'remotes', path: '/api/groups/', required: true },
    ],
  },
  {
    key: 'teachers',
    path: '/api/teachers/',
    icon: UserSquare,
    search: true,
    importable: true,
    roles: STAFF,
    filters: [
      { param: 'department', label: 'department', path: '/api/departments/' },
      {
        param: 'position',
        label: 'position',
        choices: 'position',
        values: ['assistant', 'teacher', 'senior_teacher', 'associate_professor', 'professor'],
      },
      {
        param: 'employment',
        label: 'employment',
        choices: 'employment',
        values: ['staff', 'part_time', 'hourly'],
      },
    ],
    columns: [
      { key: 'full_name', label: 'fullName' },
      { key: 'department', label: 'department' },
      { key: 'position', label: 'position', kind: 'choice', choices: 'position' },
      { key: 'employment', label: 'employment', kind: 'choice', choices: 'employment' },
      { key: 'weekly_lessons', label: 'weeklyLoad', kind: 'load' },
    ],
    fields: [
      { key: 'last_name', label: 'lastName', type: 'text', required: true },
      { key: 'first_name', label: 'firstName', type: 'text', required: true },
      { key: 'middle_name', label: 'middleName', type: 'text' },
      {
        key: 'department',
        label: 'department',
        type: 'remote',
        path: '/api/departments/',
        required: true,
      },
      {
        key: 'position',
        label: 'position',
        type: 'choice',
        choices: 'position',
        values: ['assistant', 'teacher', 'senior_teacher', 'associate_professor', 'professor'],
        required: true,
      },
      {
        key: 'degree',
        label: 'degree',
        type: 'choice',
        choices: 'degree',
        values: ['none', 'phd', 'dsc'],
        required: true,
      },
      {
        key: 'employment',
        label: 'employment',
        type: 'choice',
        choices: 'employment',
        values: ['staff', 'part_time', 'hourly'],
        required: true,
      },
      { key: 'annual_load_hours', label: 'annualLoad', type: 'number', required: true, min: 0 },
      { key: 'max_weekly_lessons', label: 'maxWeekly', type: 'number', required: true, min: 1 },
      {
        key: 'teaching_languages',
        label: 'teachingLanguages',
        type: 'choices',
        choices: 'language',
        values: LANGS,
        required: true,
      },
      { key: 'subjects', label: 'subjects', type: 'remotes', path: '/api/subjects/' },
    ],
  },
  {
    key: 'students',
    path: '/api/students/',
    icon: UserRound,
    search: true,
    importable: true,
    roles: ['admin', 'dekanat'],
    filters: [{ param: 'group', label: 'group', path: '/api/groups/' }],
    columns: [
      { key: 'last_name', label: 'lastName' },
      { key: 'first_name', label: 'firstName' },
      { key: 'hemis_id', label: 'hemisId' },
      { key: 'group_name', label: 'group' },
      { key: 'gender', label: 'gender', kind: 'choice', choices: 'gender' },
    ],
    fields: [
      { key: 'last_name', label: 'lastName', type: 'text', required: true },
      { key: 'first_name', label: 'firstName', type: 'text', required: true },
      { key: 'middle_name', label: 'middleName', type: 'text' },
      { key: 'hemis_id', label: 'hemisId', type: 'text', required: true },
      { key: 'group', label: 'group', type: 'remote', path: '/api/groups/', required: true },
      { key: 'subgroup', label: 'subgroup', type: 'remote', path: '/api/subgroups/' },
      {
        key: 'gender',
        label: 'gender',
        type: 'choice',
        choices: 'gender',
        values: ['m', 'f'],
        required: true,
      },
      { key: 'phone', label: 'phone', type: 'text' },
    ],
  },
  {
    key: 'rooms',
    path: '/api/rooms/',
    icon: DoorOpen,
    search: true,
    importable: true,
    filters: [
      { param: 'building', label: 'building', path: '/api/buildings/' },
      { param: 'room_type', label: 'roomType', path: '/api/room-types/' },
    ],
    columns: [
      { key: 'name', label: 'room' },
      { key: 'building_name', label: 'building' },
      { key: 'floor', label: 'floor' },
      { key: 'room_type_name', label: 'roomType' },
      { key: 'capacity', label: 'capacity' },
      { key: 'is_active', label: 'inUse', kind: 'bool' },
    ],
    fields: [
      {
        key: 'building',
        label: 'building',
        type: 'remote',
        path: '/api/buildings/',
        required: true,
      },
      { key: 'name', label: 'room', type: 'text', required: true },
      { key: 'floor', label: 'floor', type: 'number', required: true },
      {
        key: 'room_type',
        label: 'roomType',
        type: 'remote',
        path: '/api/room-types/',
        required: true,
      },
      { key: 'capacity', label: 'capacity', type: 'number', required: true, min: 1 },
      { key: 'computer_count', label: 'computers', type: 'number', min: 0 },
      { key: 'has_projector', label: 'projector', type: 'boolean' },
      { key: 'faculty', label: 'reservedFor', type: 'remote', path: '/api/faculties/' },
      { key: 'is_active', label: 'inUse', type: 'boolean' },
    ],
  },
  {
    key: 'subjects',
    path: '/api/subjects/',
    icon: BookOpen,
    search: true,
    importable: true,
    filters: [{ param: 'department', label: 'department', path: '/api/departments/' }],
    columns: [
      { key: 'code', label: 'code' },
      { key: 'name', label: 'name' },
      { key: 'department', label: 'department' },
      { key: 'is_language', label: 'languageSubject', kind: 'bool' },
    ],
    fields: [
      { key: 'code', label: 'code', type: 'text', required: true },
      { key: 'name', label: 'name', type: 'translated', required: true },
      { key: 'department', label: 'department', type: 'remote', path: '/api/departments/' },
      { key: 'is_language', label: 'languageSubject', type: 'boolean' },
      {
        key: 'practice_room_type',
        label: 'practiceRoomType',
        type: 'remote',
        path: '/api/room-types/',
      },
    ],
  },
  {
    key: 'curriculum',
    path: '/api/curriculum/',
    icon: ClipboardList,
    roles: STAFF,
    filters: [
      { param: 'program', label: 'program', path: '/api/programs/' },
      { param: 'form', label: 'form', path: '/api/education-forms/' },
      { param: 'study_semester', label: 'studySemester', values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] },
      { param: 'teaching_language', label: 'teachingLanguage', choices: 'language', values: LANGS },
    ],
    columns: [
      { key: 'subject_name', label: 'subject' },
      { key: 'program', label: 'program' },
      { key: 'form', label: 'form' },
      { key: 'study_semester', label: 'studySemester' },
      { key: 'credits', label: 'credits' },
      { key: 'hours', label: 'hoursByType', kind: 'hours' },
      { key: 'control_type', label: 'control', kind: 'choice', choices: 'control' },
    ],
    fields: [
      { key: 'program', label: 'program', type: 'remote', path: '/api/programs/', required: true },
      { key: 'form', label: 'form', type: 'remote', path: '/api/education-forms/', required: true },
      {
        key: 'teaching_language',
        label: 'planLanguage',
        type: 'choice',
        choices: 'language',
        values: ['', ...LANGS],
      },
      {
        key: 'study_semester',
        label: 'studySemester',
        type: 'number',
        required: true,
        min: 1,
        max: 12,
      },
      { key: 'subject', label: 'subject', type: 'remote', path: '/api/subjects/', required: true },
      { key: 'credits', label: 'credits', type: 'number', required: true, min: 1 },
      { key: 'hours_lecture', label: 'hoursLecture', type: 'number', min: 0 },
      { key: 'hours_practice', label: 'hoursPractice', type: 'number', min: 0 },
      { key: 'hours_seminar', label: 'hoursSeminar', type: 'number', min: 0 },
      { key: 'hours_lab', label: 'hoursLab', type: 'number', min: 0 },
      {
        key: 'control_type',
        label: 'control',
        type: 'choice',
        choices: 'control',
        values: ['exam', 'credit'],
        required: true,
      },
    ],
  },
  {
    key: 'assignments',
    path: '/api/assignments/',
    icon: Briefcase,
    search: true,
    roles: STAFF,
    filters: [
      { param: 'period', label: 'period', path: '/api/teaching-periods/' },
      { param: 'teacher', label: 'teacher', path: '/api/teachers/' },
      { param: 'group', label: 'group', path: '/api/groups/' },
    ],
    columns: [
      { key: 'subject_name', label: 'subject' },
      { key: 'lesson_type_code', label: 'lessonType', kind: 'choice', choices: 'lessonType' },
      { key: 'target_name', label: 'whom' },
      { key: 'teacher_name', label: 'teacher' },
      { key: 'weekly_lessons', label: 'perWeek' },
      { key: 'total_lessons', label: 'total' },
    ],
    fields: [
      {
        key: 'period',
        label: 'period',
        type: 'remote',
        path: '/api/teaching-periods/',
        required: true,
      },
      { key: 'subject', label: 'subject', type: 'remote', path: '/api/subjects/', required: true },
      {
        key: 'lesson_type',
        label: 'lessonType',
        type: 'remote',
        path: '/api/lesson-types/',
        required: true,
      },
      { key: 'teacher', label: 'teacher', type: 'remote', path: '/api/teachers/', required: true },
      { key: 'group', label: 'group', type: 'remote', path: '/api/groups/' },
      { key: 'stream', label: 'stream', type: 'remote', path: '/api/streams/' },
      { key: 'subgroup', label: 'subgroup', type: 'remote', path: '/api/subgroups/' },
      { key: 'weekly_lessons', label: 'perWeek', type: 'number', min: 0 },
      { key: 'alternating_lessons', label: 'everyOtherWeek', type: 'number', min: 0 },
      { key: 'total_lessons', label: 'total', type: 'number', required: true, min: 1 },
      {
        key: 'required_room_type',
        label: 'requiredRoomType',
        type: 'remote',
        path: '/api/room-types/',
      },
    ],
  },
  {
    key: 'lesson-times',
    path: '/api/lesson-times/',
    icon: Clock,
    filters: [{ param: 'form', label: 'form', path: '/api/education-forms/' }],
    columns: [
      { key: 'form', label: 'form' },
      { key: 'number', label: 'lessonNumber' },
      { key: 'start', label: 'start' },
      { key: 'end', label: 'end' },
      { key: 'shift', label: 'shift' },
    ],
    fields: [
      { key: 'form', label: 'form', type: 'remote', path: '/api/education-forms/', required: true },
      { key: 'number', label: 'lessonNumber', type: 'number', required: true, min: 1 },
      { key: 'start', label: 'start', type: 'time', required: true },
      { key: 'end', label: 'end', type: 'time', required: true },
      {
        key: 'shift',
        label: 'shift',
        type: 'choice',
        choices: 'shift',
        values: [1, 2],
        required: true,
      },
    ],
  },
  {
    key: 'blocked-periods',
    path: '/api/blocked-periods/',
    icon: Lock,
    columns: [
      { key: 'name', label: 'name' },
      { key: 'weekday', label: 'weekday', kind: 'choice', choices: 'weekday' },
      { key: 'start', label: 'start' },
      { key: 'end', label: 'end' },
      { key: 'is_hard', label: 'strict', kind: 'bool' },
    ],
    fields: [
      { key: 'name', label: 'name', type: 'translated', required: true },
      {
        key: 'weekday',
        label: 'weekday',
        type: 'choice',
        choices: 'weekday',
        values: ['', ...WEEKDAYS],
      },
      { key: 'start', label: 'start', type: 'time', required: true },
      { key: 'end', label: 'end', type: 'time', required: true },
      { key: 'form', label: 'form', type: 'remote', path: '/api/education-forms/' },
      { key: 'is_hard', label: 'strict', type: 'boolean' },
    ],
  },
  {
    key: 'calendar-days',
    path: '/api/calendar-days/',
    icon: CalendarX,
    columns: [
      { key: 'date', label: 'date' },
      { key: 'name', label: 'name' },
      { key: 'kind', label: 'dayKind', kind: 'choice', choices: 'dayKind' },
      { key: 'is_assumption', label: 'estimated', kind: 'bool' },
    ],
    fields: [
      { key: 'date', label: 'date', type: 'date', required: true },
      { key: 'name', label: 'name', type: 'translated', required: true },
      {
        key: 'kind',
        label: 'dayKind',
        type: 'choice',
        choices: 'dayKind',
        values: ['holiday', 'day_off', 'workday'],
        required: true,
      },
      {
        key: 'works_as_weekday',
        label: 'worksAs',
        type: 'choice',
        choices: 'weekday',
        values: ['', ...WEEKDAYS],
      },
      { key: 'is_assumption', label: 'estimated', type: 'boolean' },
    ],
  },
];

export function findResource(key: string | undefined): Resource | undefined {
  return RESOURCES.find((r) => r.key === key);
}
