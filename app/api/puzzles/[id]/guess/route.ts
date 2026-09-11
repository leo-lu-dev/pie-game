import { and, asc, eq } from 'drizzle-orm';
import { randomUUID } from 'crypto';
import { NextResponse } from 'next/server';
import { db } from '../../../../../db/client';
import { gameResults, guesses, puzzleCategories, puzzles } from '../../../../../db/schema';
import { sessionFor } from '../../../../../lib/session';

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const [puzzle] = await db.select().from(puzzles).where(eq(puzzles.slug, params.id)).limit(1);
  if (!puzzle) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  const categories = await db.select().from(puzzleCategories).where(eq(puzzleCategories.puzzleId, puzzle.id)).orderBy(asc(puzzleCategories.sliceOrder));
  let playerId: string, game;
  try { ({ playerId, game } = await sessionFor(puzzle.id)); } catch { return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 }); }
  let body: unknown; try { body = await request.json(); } catch { return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 }); }
  const assignments = body && typeof body === 'object' && Array.isArray((body as { assignments?: unknown }).assignments) ? (body as { assignments: unknown[] }).assignments : null;
  if (!assignments || assignments.length !== categories.length || assignments.some(v => typeof v !== 'string')) return NextResponse.json({ error: `Exactly ${categories.length} assignments are required` }, { status: 400 });
  const ids = assignments as string[], valid = new Set(categories.map(c => c.id));
  if (new Set(ids).size !== categories.length || ids.some(id => !valid.has(id))) return NextResponse.json({ error: 'Assignments must contain each category exactly once' }, { status: 400 });
  if (game.solved) return NextResponse.json({ error: 'Puzzle already solved' }, { status: 409 });
  if (game.attemptCount >= puzzle.maxAttempts) return NextResponse.json({ error: 'Attempt limit reached' }, { status: 409 });
  const correctPositions = categories.map((c, i) => c.id === ids[i]);
  const correctCount = correctPositions.filter(Boolean).length, attempt = game.attemptCount + 1, solved = correctCount === categories.length, terminal = solved || attempt >= puzzle.maxAttempts;
  await db.transaction(async tx => {
    await tx.insert(guesses).values({ id: randomUUID(), gameResultId: game.id, attemptNumber: attempt, assignmentsJson: ids, correctPositionsJson: correctPositions, correctCount });
    await tx.update(gameResults).set({ attemptCount: attempt, solved, completedAt: terminal ? new Date() : null, updatedAt: new Date() }).where(and(eq(gameResults.id, game.id), eq(gameResults.playerId, playerId)));
  });
  const response = NextResponse.json({ attempt, correctPositions, correctCount, solved, remainingAttempts: puzzle.maxAttempts - attempt, ...(terminal ? { reveal: categories.map(c => c.id) } : {}) });
  return response;
}
