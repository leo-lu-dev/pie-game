import { describe, expect, it } from 'vitest';
import { boardGeometry } from './PieBoard';
import { normalizeValues } from '../lib/normalize';
import { fixtures } from '../lib/fixtures';

type Point = [number, number];
function crosses(a: Point, b: Point, c: Point, d: Point) {
  const side = (p: Point, q: Point, r: Point) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  return side(a, b, c) * side(a, b, d) < -1e-6 && side(c, d, a) * side(c, d, b) < -1e-6;
}

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
          expect(card.path.endsWith(`H ${card.left ? card.x + g.cardWidth : card.x}`)).toBe(true);
          expect(card.path.match(/[MLH]/g)).toEqual(['M', 'L', 'H']);
          expect(card.left ? card.elbow > card.x + g.cardWidth : card.elbow < card.x).toBe(true);
          expect(card.outwardDot).toBeGreaterThan(0);
          const nearestX = Math.max(card.x, Math.min(g.cx, card.x + g.cardWidth));
          const nearestY = Math.max(card.y, Math.min(g.cy, card.y + g.cardHeight));
          expect(Math.hypot(nearestX - g.cx, nearestY - g.cy)).toBeGreaterThanOrEqual(g.radius + g.clearance - .01);
          for (const other of g.cards.filter(c => c.index !== card.index)) {
            const a: Point = [card.ax, card.ay], b: Point = [card.elbow, card.y + g.cardHeight / 2], e: Point = [card.edge, b[1]];
            const c: Point = [other.ax, other.ay], d: Point = [other.elbow, other.y + g.cardHeight / 2], f: Point = [other.edge, d[1]];
            expect(crosses(a, b, c, d) || crosses(a, b, d, f) || crosses(b, e, c, d)).toBe(false);
            const overlaps = card.x < other.x + g.cardWidth && card.x + g.cardWidth > other.x && card.y < other.y + g.cardHeight && card.y + g.cardHeight > other.y;
            expect(overlaps).toBe(false);
          }
        }
      });
    }
  }
});
