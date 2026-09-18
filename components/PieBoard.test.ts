import { describe, expect, it } from 'vitest';
import { boardGeometry } from './PieBoard';
import { normalizeValues } from '../lib/normalize';
import { fixtures } from '../lib/fixtures';

describe('board layout across fixtures and viewport widths', () => {
  for (const width of [296, 351, 566, 600, 960, 1376]) {
    for (const puzzle of [...Object.values(fixtures), { id: 'sorted-candidate', slices: [131199078, 94480845, 29074059, 15250943, 4592038].map(value => ({ value })) }]) {
      it(`${puzzle.id} at ${width}px keeps cards separate and connectors attached`, () => {
        const g = boardGeometry(width, normalizeValues(puzzle.slices.map(slice => slice.value)));
        for (const card of g.cards) {
          expect(card.x).toBeGreaterThanOrEqual(0);
          expect(card.y).toBeGreaterThanOrEqual(0);
          expect(card.x + g.cardWidth).toBeLessThanOrEqual(width);
          expect(card.y + g.cardHeight).toBeLessThanOrEqual(g.height);
          expect(Math.hypot(card.ax - g.cx, card.ay - g.cy)).toBeCloseTo(g.radius);
          expect(card.path.endsWith(g.compact ? `V ${card.y < g.cy ? card.y + g.cardHeight : card.y}` : `H ${card.left ? card.x + g.cardWidth : card.x}`)).toBe(true);
          const points = card.path.split(' ');
          const dx = Number(points[4]) - card.ax;
          const dy = Number(points[5]) - card.ay;
          expect(dx * (card.ay - g.cy) - dy * (card.ax - g.cx)).toBeCloseTo(0);
          if (!g.compact) expect(card.left ? card.elbow > card.x + g.cardWidth : card.elbow < card.x).toBe(true);
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
