import { asc, eq, inArray } from 'drizzle-orm';
import { NextResponse } from 'next/server';
import { db } from '../../../db/client';
import { gameResults, guesses, puzzles } from '../../../db/schema';
import { createSupabaseServerClient } from '../../../lib/supabase/server';
import { calculateStatistics } from '../../../lib/statistics';

export async function GET() {
  const { data: { user }, error } = await createSupabaseServerClient().auth.getUser();
  if (error || !user) return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 });
  const playerId = user.id;
  const rows = await db.select({ result: gameResults, publishDate: puzzles.publishDate })
    .from(gameResults).innerJoin(puzzles, eq(gameResults.puzzleId, puzzles.id))
    .where(eq(gameResults.playerId, playerId));
  const results = rows.map(row => ({ ...row.result, publishDate: row.publishDate }));
  const published = await db.select({ publishDate: puzzles.publishDate, maxAttempts: puzzles.maxAttempts }).from(puzzles).where(eq(puzzles.status, 'published'));
  const stats = calculateStatistics(results, published.map(puzzle => puzzle.publishDate));
  const maxAttempts = Math.max(0, ...published.map(puzzle => puzzle.maxAttempts));
  stats.guessDistribution = Object.fromEntries(Array.from({ length: maxAttempts }, (_, index) => [index + 1, stats.guessDistribution[index + 1] || 0]));
  const completedIds = results.filter(result => result.completedAt !== null).map(result => result.id);
  const saved = completedIds.length ? await db.select().from(guesses).where(inArray(guesses.gameResultId, completedIds)).orderBy(asc(guesses.attemptNumber)) : [];
  return NextResponse.json({ stats, results: results.map(result => ({ puzzleId: result.puzzleId, publishDate: result.publishDate, solved: result.solved, attempts: result.attemptCount, guesses: saved.filter(guess => guess.gameResultId === result.id).map(guess => ({ correctPositions: guess.correctPositionsJson })) })) });
}
