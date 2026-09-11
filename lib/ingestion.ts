/** Boundary for future source adapters. The game only consumes this normalized shape. */
export type CandidatePuzzle = {
  sourceId: string;
  sourceName: string;
  sourceUrl?: string;
  topic: string;
  title: string;
  context?: string;
  categories: Array<{ id: string; label: string; rawValue: number }>;
  metadata?: Record<string, unknown>;
};

export type PuzzleTransformation = 'natural-five' | 'curated-five' | 'meaningful-subset' | 'four-plus-other' | 'merged-categories';

export interface PuzzleSourceAdapter {
  readonly name: string;
  collect(): Promise<CandidatePuzzle[]>;
  transform?(candidate: CandidatePuzzle): CandidatePuzzle;
}
