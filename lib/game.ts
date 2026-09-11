export { normalizeValues } from './normalize';

export type GuessResult = { correctPositions: boolean[]; correctCount: number; solved: boolean };

export function evaluateGuess(correctMapping: string[], submittedMapping: string[]): GuessResult {
  const correctPositions = correctMapping.map((id, index) => id === submittedMapping[index]);
  const correctCount = correctPositions.filter(Boolean).length;
  return { correctPositions, correctCount, solved: correctCount === correctMapping.length };
}
