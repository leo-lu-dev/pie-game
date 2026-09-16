import { desc } from 'drizzle-orm';
import { NextResponse } from 'next/server';
import { db } from '../../../../db/client';
import { puzzleCandidates } from '../../../../db/schema';
import { adminUser } from '../../../../lib/admin';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (!await adminUser()) return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
  const candidates = await db.select().from(puzzleCandidates).orderBy(desc(puzzleCandidates.createdAt));
  return NextResponse.json({ candidates });
}
