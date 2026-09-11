import { randomUUID } from 'crypto';
import { and, eq } from 'drizzle-orm';
import { db } from '../db/client';
import { gameResults } from '../db/schema';
import { createSupabaseServerClient } from './supabase/server';

export async function sessionFor(puzzleId: string) {
  const { data: { user }, error } = await createSupabaseServerClient().auth.getUser();
  if (error || !user) throw new Error('AUTH_REQUIRED');
  const playerId = user.id;
  let [game] = await db.select().from(gameResults).where(and(eq(gameResults.playerId, playerId), eq(gameResults.puzzleId, puzzleId))).limit(1);
  if (!game) [game] = await db.insert(gameResults).values({ id: randomUUID(), playerId, puzzleId }).returning();
  return { playerId, game, user };
}
