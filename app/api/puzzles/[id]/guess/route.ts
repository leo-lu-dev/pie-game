import { NextResponse } from 'next/server';
import { getFixture } from '../../../../../lib/fixtures';
import { cookieName, sessionFor } from '../../../../../lib/session';

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const fixture = getFixture(params.id);
  if (!fixture) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  const { id, session } = sessionFor(params.id);
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 }); }
  const assignments = body && typeof body === 'object' && Array.isArray((body as { assignments?: unknown }).assignments) ? (body as { assignments: unknown[] }).assignments : null;
  if (!assignments || assignments.length !== 5 || assignments.some(value => typeof value !== 'string')) return NextResponse.json({ error: 'Exactly five assignments are required' }, { status: 400 });
  const ids = assignments as string[];
  const validCategories = new Set(fixture.categories.map(category => category.id));
  if (new Set(ids).size !== 5) return NextResponse.json({ error: 'Assignments must be unique' }, { status: 400 });
  if (ids.some(categoryId => !validCategories.has(categoryId))) return NextResponse.json({ error: 'Unknown category ID' }, { status: 400 });
  if (session.solved) return NextResponse.json({ error: 'Puzzle already solved' }, { status: 409 });
  if (session.attempts >= fixture.maxAttempts) return NextResponse.json({ error: 'Attempt limit reached' }, { status: 409 });
  const correctPositions = fixture.answer.map((categoryId, index) => categoryId === ids[index]);
  const correctCount = correctPositions.filter(Boolean).length;
  const solved = correctCount === 5;
  session.attempts += 1; session.solved = solved;
  const terminal = solved || session.attempts >= fixture.maxAttempts;
  const response = NextResponse.json({ attempt: session.attempts, correctPositions, correctCount, solved, remainingAttempts: fixture.maxAttempts - session.attempts, ...(terminal ? { reveal: fixture.answer } : {}) });
  response.cookies.set(cookieName, id, { httpOnly: true, sameSite: 'lax', path: '/' });
  return response;
}
