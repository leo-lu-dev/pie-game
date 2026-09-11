import { NextResponse } from 'next/server';
import { getFixture, toPublicPuzzle } from '../../../../lib/fixtures';
import { cookieName, sessionFor } from '../../../../lib/session';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const fixture = getFixture(params.id);
  if (!fixture) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  const { id, isNew } = sessionFor(params.id);
  const response = NextResponse.json(toPublicPuzzle(fixture));
  if (isNew) response.cookies.set(cookieName, id, { httpOnly: true, sameSite: 'lax', path: '/' });
  return response;
}
