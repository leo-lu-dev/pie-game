export type ShareGuess = { correctPositions: boolean[] };

export function shareText(puzzleNumber: string, attempts: number, maxAttempts: number, guesses: ShareGuess[]): string {
  const rows = guesses.map(guess => guess.correctPositions.map(correct => correct ? '🟩' : '⬜').join(''));
  return [`SPLIT DECISION ${puzzleNumber} ${attempts}/${maxAttempts}`, '', ...rows].join('\n');
}
