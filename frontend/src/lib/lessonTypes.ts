/** Lesson type → design-token classes (text + background), see tailwind.config.ts. */
export const LESSON_TYPE_CLASSES: Record<string, { pill: string; card: string; dot: string }> = {
  lecture: {
    pill: 'bg-lesson-lecture-bg text-lesson-lecture',
    card: 'bg-lesson-lecture-bg',
    dot: 'bg-lesson-lecture',
  },
  practice: {
    pill: 'bg-lesson-practice-bg text-lesson-practice',
    card: 'bg-lesson-practice-bg',
    dot: 'bg-lesson-practice',
  },
  seminar: {
    pill: 'bg-lesson-seminar-bg text-lesson-seminar',
    card: 'bg-lesson-seminar-bg',
    dot: 'bg-lesson-seminar',
  },
  lab: {
    pill: 'bg-lesson-lab-bg text-lesson-lab',
    card: 'bg-lesson-lab-bg',
    dot: 'bg-lesson-lab',
  },
};

export function lessonTypeClasses(code: string) {
  return LESSON_TYPE_CLASSES[code] ?? LESSON_TYPE_CLASSES.lecture;
}
