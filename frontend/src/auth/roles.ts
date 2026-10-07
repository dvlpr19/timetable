import type { Role } from './types';

export const STAFF_ROLES: Role[] = ['admin', 'dekanat', 'kafedra_mudiri'];

export function isStaff(role: Role | undefined): boolean {
  return Boolean(role && STAFF_ROLES.includes(role));
}

/** Which data sections a role may change (the server checks the same and the scope). */
const WRITE: Record<Role, string[] | '*'> = {
  admin: '*',
  dekanat: ['groups', 'streams', 'students', 'curriculum', 'assignments'],
  kafedra_mudiri: ['teachers', 'assignments'],
  oqituvchi: [],
  talaba: [],
};

export function canWrite(role: Role | undefined, resource: string): boolean {
  if (!role) return false;
  const allowed = WRITE[role];
  return allowed === '*' || allowed.includes(resource);
}
