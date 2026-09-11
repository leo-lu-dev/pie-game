import { and, asc, eq } from 'drizzle-orm';
import { NextRequest, NextResponse } from 'next/server';
import { db } from '../../../../db/client';
import { guesses, puzzleCategories, puzzles } from '../../../../db/schema';
import { sessionFor } from '../../../../lib/session';

export const dynamic = 'force-dynamic';

const today = () => new Date().toISOString().slice(0, 10);

export async function GET(request: NextRequest) {
  const devMode = process.env.NODE_ENV !== 'production';
  const fixture = devMode ? request.nextUrl.searchParams.get('fixture') : null;
  const requestedDate = devMode ? request.nextUrl.searchParams.get('date') : null;
  const simulatedState = devMode ? request.nextUrl.searchParams.get('state') : null;
  const date = requestedDate || today();
  const [puzzle] = fixture
    ? await db.select().from(puzzles).where(eq(puzzles.slug, fixture)).limit(1)
    : await db.select().from(puzzles).where(and(eq(puzzles.publishDate, date), eq(puzzles.status, 'published'))).orderBy(asc(puzzles.publishDate), asc(puzzles.slug)).limit(1);
  if (!puzzle) return NextResponse.json({ error: 'No published puzzle is available for today' }, { status: 404 });

  const categories = await db.select().from(puzzleCategories).where(eq(puzzleCategories.puzzleId, puzzle.id)).orderBy(asc(puzzleCategories.sliceOrder));
  let game;
  try { ({ game } = await sessionFor(puzzle.id)); } catch { return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 }); }
  const saved = await db.select().from(guesses).where(eq(guesses.gameResultId, game.id)).orderBy(asc(guesses.attemptNumber));
  const terminal = game.solved || game.attemptCount >= puzzle.maxAttempts;
  const state = simulatedState === 'won'
    ? { attempts: Math.min(3, puzzle.maxAttempts), solved: true, guesses: [], reveal: categories.map(category => category.id) }
    : simulatedState === 'lost'
      ? { attempts: puzzle.maxAttempts, solved: false, guesses: [], reveal: categories.map(category => category.id) }
      : { attempts: game.attemptCount, solved: game.solved, guesses: saved.map(guess => ({ attempt: guess.attemptNumber, assignments: guess.assignmentsJson, correctPositions: guess.correctPositionsJson, correctCount: guess.correctCount })), ...(terminal ? { reveal: categories.map(category => category.id) } : {}) };
  return NextResponse.json({ id: puzzle.slug, title: puzzle.title, context: puzzle.context ?? undefined, maxAttempts: puzzle.maxAttempts, categories: categories.map(category => ({ id: category.id, label: category.label })), slices: categories.map((category, index) => ({ id: `${puzzle.id}-slice-${index}`, value: Number(category.rawValue) })), state });
}
