import { asc, desc, eq, or } from 'drizzle-orm';
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
      db.select().from(puzzleCandidates).where(
        // Only candidates with an AI-approved status are considered here. The
        // full acceptance gate is applied below using the saved review JSON.
        // Human-approved candidates remain visible until they are promoted.
        or(eq(puzzleCandidates.status, 'agent_reviewed'), eq(puzzleCandidates.status, 'approved')),
      ).orderBy(asc(puzzleCandidates.createdAt)),
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

  const candidateItems = candidates.filter(candidate => {
    if (candidate.status === 'approved') return true;
    const review = latestReviewByCandidate.get(candidate.id)?.reviewJson as Record<string, unknown> | undefined;
    return candidate.status === 'agent_reviewed'
      && review?.verdict === 'approve'
      && review?.recommended_action === 'approve'
      && review?.semantic_validity === true
      && review?.denominator_clear === true
      && review?.question_accurate === true;
  }).map(candidate => {
    const candidateCategories = [...(categoriesByCandidate.get(candidate.id) || [])].sort((a, b) => Number(b.rawValue) - Number(a.rawValue) || a.displayOrder - b.displayOrder);
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
