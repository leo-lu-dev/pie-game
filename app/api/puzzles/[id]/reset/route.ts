import { NextResponse } from 'next/server';
import { getFixture } from '../../../../../lib/fixtures';
import { cookieName, resetSession } from '../../../../../lib/session';

export async function POST(_: Request, { params }: { params: { id: string } }) {
  if (!getFixture(params.id)) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  const response = NextResponse.json({ ok: true });
  response.cookies.set(cookieName, resetSession(params.id), { httpOnly: true, sameSite: 'lax', path: '/' });
  return response;
}
