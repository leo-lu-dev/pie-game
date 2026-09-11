import { expect, it } from 'vitest';
import { shareText } from './sharing';

it('creates spoiler-free result text', () => {
  expect(shareText('128', 3, 4, [{ correctPositions: [true, false, false, true, false] }])).toBe('PIE #128 3/4\n\n🟩⬜⬜🟩⬜');
});
