export type PublicCategory = { id: string; label: string };
export type PublicSlice = { id: string; value: number };
export type SavedGuess = { attempt: number; assignments: string[]; correctPositions: boolean[]; correctCount: number };
export type PublicPuzzle = { id: string; title: string; context?: string; categories: PublicCategory[]; slices: PublicSlice[]; maxAttempts: number; state?: { attempts: number; solved: boolean; guesses: SavedGuess[]; reveal?: string[] } };
export type GuessResponse = { attempt: number; correctPositions: boolean[]; correctCount: number; solved: boolean; remainingAttempts: number; reveal?: string[] };
export type PlayerStatistics = { gamesPlayed: number; gamesWon: number; winPercentage: number; currentStreak: number; maximumStreak: number; averageAttemptsOnWins: number; guessDistribution: Record<number, number> };
