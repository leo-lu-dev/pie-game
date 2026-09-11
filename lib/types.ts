export type PublicCategory = { id: string; label: string };
export type PublicSlice = { id: string; value: number };
export type PublicPuzzle = { id: string; title: string; context?: string; categories: PublicCategory[]; slices: PublicSlice[]; maxAttempts: number };
export type GuessResponse = { attempt: number; correctPositions: boolean[]; correctCount: number; solved: boolean; remainingAttempts: number; reveal?: string[] };
