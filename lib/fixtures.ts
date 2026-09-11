import type { PublicPuzzle, PuzzleStatus } from './types';

type Fixture = PublicPuzzle & { answer: string[] };
const make = (id: string, title: string, labels: string[], values: number[], answer: number[]): Fixture => ({
  id, title, maxAttempts: 4,
  categories: labels.map((label, index) => ({ id: `${id}-${index}`, label })),
  slices: values.map((value, index) => ({ id: `${id}-slice-${index}`, value })),
  answer: answer.map(index => `${id}-${index}`),
});

export const fixtures: Record<string, Fixture> = {
  households: make('households', 'How are households distributed by household size?', ['1 person', '2 people', '3 people', '4 people', '5+ people'], [34, 16, 29, 8, 13], [1, 2, 0, 4, 3]),
  spending: make('spending', 'How is household spending divided?', ['Housing', 'Food', 'Transportation', 'Recreation', 'Other'], [17, 16, 30, 28, 9], [1, 2, 0, 4, 3]),
  videos: make('videos', "How are views split among this fictional creator's five most-viewed videos?", ['Moonlight Drive', 'The Last Paper Crane', '24 Hours in a Tiny House', 'Making a Clay Keyboard', 'A Walk Through the Clouds'], [261000000, 206000000, 312000000, 101000000, 156000000], [1, 2, 0, 4, 3]),
  commuters: make('commuters', 'How are commuters split among these transportation methods?', ['Car', 'Public transit', 'Walking', 'Cycling', 'Work from home'], [22, 16, 37, 14, 11], [1, 2, 0, 4, 3]),
  close: make('close', 'Can you place these close slices in order?', ['24%', '22%', '20%', '18%', '16%'], [22, 20, 24, 16, 18], [1, 2, 0, 4, 3]),
  dominant: make('dominant', 'Can you spot the dominant slice?', ['51%', '19%', '13%', '10%', '7%'], [19, 13, 51, 7, 10], [1, 2, 0, 4, 3]),
};

export const fixtureSchedule: Record<string, { dateOffset: number; status: PuzzleStatus }> = {
  households: { dateOffset: 0, status: 'published' },
  spending: { dateOffset: -1, status: 'published' },
  videos: { dateOffset: -2, status: 'published' },
  commuters: { dateOffset: -3, status: 'published' },
  close: { dateOffset: 2, status: 'scheduled' },
  dominant: { dateOffset: -4, status: 'published' },
};

export const fixtureAliases: Record<string, string> = { household: 'households', householdsize: 'households' };
export function getFixture(id: string) { return fixtures[fixtureAliases[id] || id]; }
export function toPublicPuzzle(fixture: Fixture): PublicPuzzle { const { answer: _answer, ...publicPuzzle } = fixture; return publicPuzzle; }
