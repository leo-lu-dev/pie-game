import { fixtures } from '../lib/fixtures';
import { eq } from 'drizzle-orm';
import { db, client } from './client';
import { puzzleCategories, puzzles } from './schema';

async function seed() {
  for (const fixture of Object.values(fixtures)) {
    const sliceOrderByOriginalIndex = fixture.slices.map((_, index) => index)
      .sort((a, b) => fixture.slices[b].value - fixture.slices[a].value || a - b)
      .reduce<Record<number, number>>((order, originalIndex, displayIndex) => {
        order[originalIndex] = displayIndex;
        return order;
      }, {});
    await db.insert(puzzles).values({ id: fixture.id, slug: fixture.id, title: fixture.title, context: fixture.context ?? null, maxAttempts: fixture.maxAttempts, status: 'published', publishDate: new Date().toISOString().slice(0, 10), sourceName: 'Pie of the Day', sourceUrl: null }).onConflictDoUpdate({ target: puzzles.id, set: { title: fixture.title, maxAttempts: fixture.maxAttempts, updatedAt: new Date() } });
    await db.delete(puzzleCategories).where(eq(puzzleCategories.puzzleId, fixture.id));
    await db.insert(puzzleCategories).values(fixture.categories.map(category => {
      const originalSliceIndex = fixture.answer.indexOf(category.id);
      return { id: category.id, puzzleId: fixture.id, categoryKey: category.id, label: category.label, rawValue: String(fixture.slices[originalSliceIndex].value), sliceOrder: sliceOrderByOriginalIndex[originalSliceIndex] };
    }));
  }
  console.log(`Seeded ${Object.keys(fixtures).length} puzzles`);
  await client.end();
}
seed().catch(error => { console.error(error); process.exitCode = 1; });
