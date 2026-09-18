import { asc, eq } from 'drizzle-orm';
import { NextResponse } from 'next/server';
import { db } from '../../../../db/client';
import { guesses, puzzleCategories, puzzles } from '../../../../db/schema';
import { sessionFor } from '../../../../lib/session';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const [puzzle] = await db.select().from(puzzles).where(eq(puzzles.slug, params.id)).limit(1);
  if (!puzzle) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  const categories = await db.select().from(puzzleCategories).where(eq(puzzleCategories.puzzleId, puzzle.id)).orderBy(asc(puzzleCategories.sliceOrder));
  let game;
  try { ({ game } = await sessionFor(puzzle.id)); } catch { return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 }); }
  const saved = await db.select().from(guesses).where(eq(guesses.gameResultId, game.id)).orderBy(asc(guesses.attemptNumber));
  const terminal = game.solved || game.attemptCount >= puzzle.maxAttempts;
  const response = NextResponse.json({ id: puzzle.slug, title: puzzle.title, context: puzzle.context ?? undefined, publishDate: puzzle.publishDate, maxAttempts: puzzle.maxAttempts, categories: categories.map(c => ({ id: c.id, label: c.label })), slices: categories.map((c, i) => ({ id: `${puzzle.id}-slice-${i}`, value: Number(c.rawValue) })), state: { attempts: game.attemptCount, solved: game.solved, guesses: saved.map(g => ({ attempt: g.attemptNumber, assignments: g.assignmentsJson, correctPositions: g.correctPositionsJson, correctCount: g.correctCount })), ...(terminal ? { reveal: categories.map(c => c.id) } : {}) } });
  return response;
}
