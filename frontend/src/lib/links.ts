/** Stand-in link the automatic timetabler puts on distance lessons (backend LINK_PLACEHOLDER).
 * It never resolves; such lessons still need a real link before publishing. */
const LINK_PLACEHOLDER = 'https://link-kerak.invalid/';

export const needsLink = (url: string) => !url || url.startsWith(LINK_PLACEHOLDER);
