import { and, asc, eq } from 'drizzle-orm';
import { NextRequest, NextResponse } from 'next/server';
import { db } from '../../../../db/client';
import { guesses, puzzleCategories, puzzles } from '../../../../db/schema';
import { sessionFor } from '../../../../lib/session';

export const dynamic = 'force-dynamic';

const today = (timeZone: string) => {
  let formatter: Intl.DateTimeFormat;
  try {
    formatter = new Intl.DateTimeFormat('en-US', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' });
  } catch {
    formatter = new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit' });
  }
  const parts = Object.fromEntries(formatter.formatToParts(new Date()).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
};

export async function GET(request: NextRequest) {
  const timeZone = request.nextUrl.searchParams.get('timezone') || 'UTC';
  const date = today(timeZone);
  const [puzzle] = await db.select().from(puzzles).where(and(eq(puzzles.publishDate, date), eq(puzzles.status, 'published'))).orderBy(asc(puzzles.publishDate), asc(puzzles.slug)).limit(1);
  if (!puzzle) return NextResponse.json({ error: 'No published puzzle is available for today' }, { status: 404 });

  const categories = await db.select().from(puzzleCategories).where(eq(puzzleCategories.puzzleId, puzzle.id)).orderBy(asc(puzzleCategories.sliceOrder));
  let game;
  try { ({ game } = await sessionFor(puzzle.id)); } catch { return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 }); }
  const saved = await db.select().from(guesses).where(eq(guesses.gameResultId, game.id)).orderBy(asc(guesses.attemptNumber));
  const terminal = game.solved || game.attemptCount >= puzzle.maxAttempts;
  const state = { attempts: game.attemptCount, solved: game.solved, guesses: saved.map(guess => ({ attempt: guess.attemptNumber, assignments: guess.assignmentsJson, correctPositions: guess.correctPositionsJson, correctCount: guess.correctCount })), ...(terminal ? { reveal: categories.map(category => category.id) } : {}) };
  return NextResponse.json({ id: puzzle.slug, title: puzzle.title, context: puzzle.context ?? undefined, maxAttempts: puzzle.maxAttempts, categories: categories.map(category => ({ id: category.id, label: category.label })), slices: categories.map((category, index) => ({ id: `${puzzle.id}-slice-${index}`, value: Number(category.rawValue) })), state });
}
