import { describe, expect, it } from 'vitest';
import { boardGeometry } from './PieBoard';
import { normalizeValues } from '../lib/normalize';
import { fixtures } from '../lib/fixtures';

describe('board layout across fixtures and viewport widths', () => {
  for (const width of [296, 351, 566, 600, 960, 1376]) {
    for (const puzzle of Object.values(fixtures)) {
      it(`${puzzle.id} at ${width}px keeps cards separate and connectors attached`, () => {
        const g = boardGeometry(width, normalizeValues(puzzle.slices.map(slice => slice.value)));
        for (const card of g.cards) {
          expect(card.x).toBeGreaterThanOrEqual(0);
          expect(card.y).toBeGreaterThanOrEqual(0);
          expect(card.x + g.cardWidth).toBeLessThanOrEqual(width);
          expect(card.y + g.cardHeight).toBeLessThanOrEqual(g.height);
          expect(Math.hypot(card.ax - g.cx, card.ay - g.cy)).toBeCloseTo(g.radius);
          expect(card.path.endsWith(`H ${card.left ? card.x + g.cardWidth : card.x}`)).toBe(true);
          expect(card.path.match(/ L /g)).toHaveLength(1);
          expect(card.path.match(/ H /g)).toHaveLength(1);
          expect(card.outwardDot).toBeGreaterThan(0);
          const nearestX = Math.max(card.x, Math.min(g.cx, card.x + g.cardWidth));
          const nearestY = Math.max(card.y, Math.min(g.cy, card.y + g.cardHeight));
          expect(Math.hypot(nearestX - g.cx, nearestY - g.cy)).toBeGreaterThanOrEqual(g.radius + g.clearance - .01);
          for (const other of g.cards.filter(c => c.index !== card.index)) {
            const overlaps = card.x < other.x + g.cardWidth && card.x + g.cardWidth > other.x && card.y < other.y + g.cardHeight && card.y + g.cardHeight > other.y;
            expect(overlaps).toBe(false);
          }
        }
      });
    }
  }
});
