import { and, eq } from 'drizzle-orm';
import { NextResponse } from 'next/server';
import { db } from '../../../../../db/client';
import { gameResults, guesses, puzzles } from '../../../../../db/schema';
import { sessionFor } from '../../../../../lib/session';

export async function POST(_: Request, { params }: { params: { id: string } }) {
  const [puzzle] = await db.select().from(puzzles).where(eq(puzzles.slug, params.id)).limit(1);
  if (!puzzle) return NextResponse.json({ error: 'Unknown puzzle' }, { status: 404 });
  let playerId: string, game;
  try { ({ playerId, game } = await sessionFor(puzzle.id)); } catch { return NextResponse.json({ error: 'Anonymous authentication is required' }, { status: 401 }); }
  await db.transaction(async tx => {
    await tx.delete(guesses).where(eq(guesses.gameResultId, game.id));
    await tx.update(gameResults).set({ attemptCount: 0, solved: false, completedAt: null, updatedAt: new Date() }).where(and(eq(gameResults.id, game.id), eq(gameResults.playerId, playerId)));
  });
  return NextResponse.json({ ok: true });
}
