import { boolean, date, integer, jsonb, pgTable, text, timestamp, unique } from 'drizzle-orm/pg-core';
import type { PuzzleStatus } from '../lib/types';

const timestamps = {
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
};

export const puzzles = pgTable('puzzles', {
  id: text('id').primaryKey(), slug: text('slug').notNull().unique(), title: text('title').notNull(),
  context: text('context'), maxAttempts: integer('max_attempts').notNull(), status: text('status').$type<PuzzleStatus>().notNull(),
  publishDate: date('publish_date').notNull(), sourceName: text('source_name'), sourceUrl: text('source_url'), sourceMetadata: jsonb('source_metadata').$type<Record<string, unknown>>(), candidateId: text('candidate_id'), ...timestamps,
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

export const puzzleCandidates = pgTable('puzzle_candidates', {
  id: text('id').primaryKey(), sourceName: text('source_name').notNull(), sourceDatasetId: text('source_dataset_id').notNull(), sourceUrl: text('source_url'),
  topic: text('topic').notNull(), title: text('title').notNull(), context: text('context'), geography: text('geography'), timePeriod: text('time_period'), unit: text('unit'), populationUniverse: text('population_universe'),
  transformationType: text('transformation_type').notNull(), transformationMetadataJson: jsonb('transformation_metadata_json').notNull(), sourceMetadataJson: jsonb('source_metadata_json').notNull(), rawPayloadJson: jsonb('raw_payload_json').notNull(),
  status: text('status').$type<'ingested' | 'validated' | 'agent_reviewed' | 'needs_review' | 'approved' | 'rejected' | 'promoted'>().notNull(), humanStatus: text('human_status').$type<'approved' | 'rejected' | 'needs_review'>(), humanNotes: text('human_notes'), reviewedBy: text('reviewed_by'), reviewedAt: timestamp('reviewed_at', { withTimezone: true }), ...timestamps,
});

export const candidateCategories = pgTable('candidate_categories', {
  id: text('id').primaryKey(), candidateId: text('candidate_id').notNull().references(() => puzzleCandidates.id, { onDelete: 'cascade' }), categoryKey: text('category_key').notNull(), label: text('label').notNull(), rawValue: text('raw_value').notNull(), displayOrder: integer('display_order').notNull(), createdAt: timestamps.createdAt,
});

export const candidateValidations = pgTable('candidate_validations', {
  id: text('id').primaryKey(), candidateId: text('candidate_id').notNull().references(() => puzzleCandidates.id, { onDelete: 'cascade' }), technicalValid: boolean('technical_valid').notNull(), dimensionValid: boolean('dimension_valid').notNull(), transformationValid: boolean('transformation_valid').notNull(), diagnosticsJson: jsonb('diagnostics_json').notNull(), issuesJson: jsonb('issues_json').notNull(), createdAt: timestamps.createdAt,
});

export const candidateAgentReviews = pgTable('candidate_agent_reviews', {
  id: text('id').primaryKey(), candidateId: text('candidate_id').notNull().references(() => puzzleCandidates.id, { onDelete: 'cascade' }), model: text('model').notNull(), promptVersion: text('prompt_version').notNull(), verdict: text('verdict').notNull(), reviewJson: jsonb('review_json').notNull(), createdAt: timestamps.createdAt,
});
