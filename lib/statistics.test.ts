import { describe, expect, it } from 'vitest';
import { calculateStatistics } from './statistics';

const result = (publishDate: string, solved: boolean, attemptCount: number) => ({ puzzleId: publishDate, publishDate, solved, attemptCount, completedAt: `${publishDate}T12:00:00Z` });

describe('calculateStatistics', () => {
  it('derives totals, distribution, and verified streaks from results', () => {
    const stats = calculateStatistics([
      result('2026-09-08', true, 3), result('2026-09-09', true, 2), result('2026-09-10', false, 4),
      result('2026-09-06', true, 1), result('2026-09-01', true, 2),
    ]);
    expect(stats.gamesPlayed).toBe(5);
    expect(stats.gamesWon).toBe(4);
    expect(stats.winPercentage).toBe(80);
    expect(stats.currentStreak).toBe(0);
    expect(stats.maximumStreak).toBe(2);
    expect(stats.averageAttemptsOnWins).toBe(2);
    expect(stats.guessDistribution).toEqual({ 1: 1, 2: 2, 3: 1 });
  });
});
