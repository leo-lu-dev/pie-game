import { eq } from 'drizzle-orm';
import { NextResponse } from 'next/server';
import { db } from '../../../../../db/client';
import { candidateAgentReviews, candidateCategories, candidateValidations, puzzleCandidates } from '../../../../../db/schema';
import { adminUser } from '../../../../../lib/admin';

export const dynamic = 'force-dynamic';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  if (!await adminUser()) return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
  const [candidate] = await db.select().from(puzzleCandidates).where(eq(puzzleCandidates.id, params.id)).limit(1);
  if (!candidate) return NextResponse.json({ error: 'Candidate not found' }, { status: 404 });
  const [categories, validations, reviews] = await Promise.all([
    db.select().from(candidateCategories).where(eq(candidateCategories.candidateId, params.id)).orderBy(candidateCategories.displayOrder),
    db.select().from(candidateValidations).where(eq(candidateValidations.candidateId, params.id)),
    db.select().from(candidateAgentReviews).where(eq(candidateAgentReviews.candidateId, params.id)).orderBy(candidateAgentReviews.createdAt),
  ]);
  return NextResponse.json({ candidate, categories, validations, reviews });
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  const user = await adminUser();
  if (!user) return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 }); }
  const action = body && typeof body === 'object' ? (body as { action?: unknown }).action : null;
  const notes = body && typeof body === 'object' ? (body as { notes?: unknown }).notes : null;
  if (!['approved', 'rejected', 'needs_review'].includes(String(action))) return NextResponse.json({ error: 'Invalid review action' }, { status: 400 });
  const [candidate] = await db.update(puzzleCandidates).set({ status: String(action) as 'approved' | 'rejected' | 'needs_review', humanStatus: String(action) as 'approved' | 'rejected' | 'needs_review', humanNotes: typeof notes === 'string' ? notes : null, reviewedBy: user.email || user.id, reviewedAt: new Date(), updatedAt: new Date() }).where(eq(puzzleCandidates.id, params.id)).returning();
  if (!candidate) return NextResponse.json({ error: 'Candidate not found' }, { status: 404 });
  return NextResponse.json({ candidate });
}
