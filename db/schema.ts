import { boolean, date, integer, jsonb, pgTable, text, timestamp, unique } from 'drizzle-orm/pg-core';
import type { PuzzleStatus } from '../lib/types';

const timestamps = {
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
};

export const puzzles = pgTable('puzzles', {
  id: text('id').primaryKey(), slug: text('slug').notNull().unique(), title: text('title').notNull(),
  context: text('context'), maxAttempts: integer('max_attempts').notNull(), status: text('status').$type<PuzzleStatus>().notNull(),
  publishDate: date('publish_date').notNull(), sourceName: text('source_name'), sourceUrl: text('source_url'), sourceMetadata: jsonb('source_metadata').$type<Record<string, unknown>>(), ...timestamps,
}, table => ({ publishDateUnique: unique('puzzles_publish_date_unique').on(table.publishDate) }));

export const puzzleCategories = pgTable('puzzle_categories', {
  id: text('id').primaryKey(), puzzleId: text('puzzle_id').notNull().references(() => puzzles.id, { onDelete: 'cascade' }),
  categoryKey: text('category_key').notNull(), label: text('label').notNull(), rawValue: text('raw_value').notNull(),
  sliceOrder: integer('slice_order').notNull(), createdAt: timestamps.createdAt,
});

export const gameResults = pgTable('game_results', {
  id: text('id').primaryKey(), playerId: text('player_id').notNull(), puzzleId: text('puzzle_id').notNull().references(() => puzzles.id, { onDelete: 'cascade' }),
  startedAt: timestamp('started_at', { withTimezone: true }).defaultNow().notNull(), completedAt: timestamp('completed_at', { withTimezone: true }),
  solved: boolean('solved').default(false).notNull(), attemptCount: integer('attempt_count').default(0).notNull(), ...timestamps,
}, table => ({ playerPuzzle: unique().on(table.playerId, table.puzzleId) }));

export const guesses = pgTable('guesses', {
  id: text('id').primaryKey(), gameResultId: text('game_result_id').notNull().references(() => gameResults.id, { onDelete: 'cascade' }),
  attemptNumber: integer('attempt_number').notNull(), assignmentsJson: jsonb('assignments_json').$type<string[]>().notNull(),
  correctPositionsJson: jsonb('correct_positions_json').$type<boolean[]>().notNull(), correctCount: integer('correct_count').notNull(), createdAt: timestamps.createdAt,
}, table => ({ resultAttempt: unique().on(table.gameResultId, table.attemptNumber) }));
