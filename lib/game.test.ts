import { describe, expect, it } from 'vitest';
import { evaluateGuess, normalizeValues } from './game';
describe('normalizeValues', () => {
  it('normalizes and sums to approximately 100', () => { const values = normalizeValues([312, 261, 206, 156, 101]); expect(values.reduce((a, b) => a + b, 0)).toBeCloseTo(100, 5); });
  it('rejects invalid values', () => { expect(normalizeValues([10, 0])).toEqual([]); });
});
describe('evaluateGuess', () => {
  it('solves five correct assignments', () => { expect(evaluateGuess(['a','b','c','d','e'], ['a','b','c','d','e'])).toEqual({ correctPositions: [true,true,true,true,true], correctCount: 5, solved: true }); });
  it('reports only exact positions', () => { const result = evaluateGuess(['a','b','c','d','e'], ['b','a','c','e','d']); expect(result.correctPositions).toEqual([false,false,true,false,false]); expect(result.correctCount).toBe(1); expect(result.solved).toBe(false); });
  it('does not accept incomplete or duplicate guesses as solved', () => { expect(evaluateGuess(['a','b','c','d','e'], ['a','a','c','d','e']).solved).toBe(false); expect(evaluateGuess(['a','b','c','d','e'], ['a','b','c','d']).solved).toBe(false); });
});
