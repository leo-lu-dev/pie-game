export type CanonicalGameResult = {
  puzzleId: string;
  publishDate: string;
  completedAt: Date | string | null;
  solved: boolean;
  attemptCount: number;
};

export type PlayerStatistics = {
  gamesPlayed: number;
  gamesWon: number;
  winPercentage: number;
  currentStreak: number;
  maximumStreak: number;
  averageAttemptsOnWins: number;
  guessDistribution: Record<number, number>;
};

const dayBefore = (date: string) => {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() - 1);
  return value.toISOString().slice(0, 10);
};

/** Calculates stats from terminal game-result rows. Aggregates are intentionally not accepted here. */
export function calculateStatistics(results: CanonicalGameResult[], publishedDates?: string[]): PlayerStatistics {
  const completed = results
    .filter(result => result.completedAt !== null)
    .sort((a, b) => b.publishDate.localeCompare(a.publishDate));
  const wins = completed.filter(result => result.solved);
  const distribution: Record<number, number> = {};
  wins.forEach(result => { distribution[result.attemptCount] = (distribution[result.attemptCount] || 0) + 1; });

  const byDate = new Map(completed.map(result => [result.publishDate, result]));
  let currentStreak = 0;
  const orderedPublishedDates = Array.from(new Set(publishedDates?.length ? publishedDates : completed.map(result => result.publishDate))).sort((a, b) => b.localeCompare(a));
  if (byDate.get(orderedPublishedDates[0])?.solved) {
    let date = orderedPublishedDates[0];
    while (byDate.get(date)?.solved) {
      currentStreak += 1;
      date = dayBefore(date);
    }
  }

  let maximumStreak = 0;
  let run = 0;
  let previousDate: string | undefined;
  const datesForStreak = Array.from(new Set(publishedDates?.length ? publishedDates : Array.from(byDate.keys()))).sort();
  datesForStreak.forEach(date => {
    if (previousDate && dayBefore(date) !== previousDate) run = 0;
    if (byDate.get(date)?.solved) run += 1;
    else run = 0;
    maximumStreak = Math.max(maximumStreak, run);
    previousDate = date;
  });
  const attempts = wins.reduce((total, result) => total + result.attemptCount, 0);
  return {
    gamesPlayed: completed.length,
    gamesWon: wins.length,
    winPercentage: completed.length ? Math.round((wins.length / completed.length) * 100) : 0,
    currentStreak,
    maximumStreak,
    averageAttemptsOnWins: wins.length ? Number((attempts / wins.length).toFixed(1)) : 0,
    guessDistribution: distribution,
  };
}
