import { randomUUID } from 'crypto';
import { cookies } from 'next/headers';

export type Session = { attempts: number; solved: boolean };
const sessions = new Map<string, Session>();
export const cookieName = 'pie-session';

export function sessionFor(scope = 'default') {
  const existing = cookies().get(cookieName)?.value;
  const id = existing || randomUUID();
  const key = `${id}:${scope}`;
  const session = sessions.get(key) || { attempts: 0, solved: false };
  sessions.set(key, session);
  return { id, session, isNew: !existing };
}

export function resetSession(scope = 'default') {
  const id = cookies().get(cookieName)?.value || randomUUID();
  sessions.set(`${id}:${scope}`, { attempts: 0, solved: false });
  return id;
}
