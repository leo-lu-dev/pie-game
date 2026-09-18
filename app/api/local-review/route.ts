import { asc, desc, eq } from 'drizzle-orm';
import { NextRequest, NextResponse } from 'next/server';
import { db } from '../../../db/client';
import { candidateAgentReviews, candidateCategories, candidateValidations, puzzleCandidates } from '../../../db/schema';

export const dynamic = 'force-dynamic';

function localOnly() {
  return process.env.NODE_ENV !== 'production';
}

export async function GET() {
  if (!localOnly()) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  let candidates: typeof puzzleCandidates.$inferSelect[] = [];
  let categories: typeof candidateCategories.$inferSelect[] = [];
  let reviews: typeof candidateAgentReviews.$inferSelect[] = [];
  let storageWarning: string | null = null;
  try {
    [candidates, categories, reviews] = await Promise.all([
      db.select().from(puzzleCandidates).orderBy(asc(puzzleCandidates.createdAt)),
      db.select().from(candidateCategories).orderBy(asc(candidateCategories.displayOrder)),
      db.select().from(candidateAgentReviews).orderBy(desc(candidateAgentReviews.createdAt)),
    ]);
  } catch {
    storageWarning = 'Local candidate database is unavailable. No candidates can be loaded.';
  }
  const categoriesByCandidate = new Map<string, typeof categories>();
  categories.forEach(category => {
    const existing = categoriesByCandidate.get(category.candidateId) || [];
    existing.push(category);
    categoriesByCandidate.set(category.candidateId, existing);
  });
  const latestReviewByCandidate = new Map<string, typeof reviews[number]>();
  reviews.forEach(review => { if (!latestReviewByCandidate.has(review.candidateId)) latestReviewByCandidate.set(review.candidateId, review); });

  const candidateItems = candidates.map(candidate => {
    const candidateCategories = categoriesByCandidate.get(candidate.id) || [];
    const puzzle = {
      id: candidate.id,
      title: candidate.title,
      context: candidate.context || undefined,
      maxAttempts: 4,
      categories: candidateCategories.map(category => ({ id: category.categoryKey, label: category.label })),
      slices: candidateCategories.map((category, index) => ({ id: `${candidate.id}-slice-${index}`, value: Number(category.rawValue) })),
    };
    const review = latestReviewByCandidate.get(candidate.id);
    return {
      kind: 'candidate' as const,
      id: candidate.id,
      title: candidate.title,
      status: candidate.status,
      humanStatus: candidate.humanStatus,
      agentReview: review?.reviewJson || null,
      puzzle,
      answer: candidateCategories.map(category => category.categoryKey),
    };
  });

  return NextResponse.json({ items: candidateItems, storageWarning });
}

export async function POST(request: NextRequest) {
  if (!localOnly()) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  let body: { kind?: string; id?: string; decision?: string; reviewer?: string };
  try { body = await request.json(); } catch { return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 }); }
  if (body.kind !== 'candidate' || !body.id || !['approved', 'rejected'].includes(body.decision || '')) {
    return NextResponse.json({ error: 'kind, id, and a valid decision are required' }, { status: 400 });
  }

  const [candidate] = await db.select().from(puzzleCandidates).where(eq(puzzleCandidates.id, body.id)).limit(1);
  if (!candidate) return NextResponse.json({ error: 'Candidate not found' }, { status: 404 });
  if (candidate.status === 'promoted') return NextResponse.json({ error: 'Promoted candidates cannot be reviewed again' }, { status: 409 });
  if (body.decision === 'approved') {
    const [validation] = await db.select().from(candidateValidations).where(eq(candidateValidations.candidateId, body.id)).orderBy(desc(candidateValidations.createdAt)).limit(1);
    if (!validation || !validation.technicalValid || !validation.dimensionValid || !validation.transformationValid) {
      return NextResponse.json({ error: 'Candidate requires a passing validation before approval' }, { status: 409 });
    }
  }

  const now = new Date();
  const status = body.decision === 'approved' ? 'approved' : 'rejected';
  await db.update(puzzleCandidates).set({ status, humanStatus: status, reviewedBy: body.reviewer || 'local', reviewedAt: now, updatedAt: now }).where(eq(puzzleCandidates.id, body.id));
  return NextResponse.json({ ok: true, status });
}
