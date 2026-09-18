import { fixtures } from '../lib/fixtures';
import { eq } from 'drizzle-orm';
import { db, client } from './client';
import { puzzleCategories, puzzles } from './schema';
import { fixtureSchedule } from '../lib/fixtures';

async function seed() {
  const fixturesToSeed = Object.values(fixtures);
  for (let index = 0; index < fixturesToSeed.length; index += 1) {
    const fixture = fixturesToSeed[index];
    const publishDate = new Date();
    publishDate.setUTCDate(publishDate.getUTCDate() + fixtureSchedule[fixture.id].dateOffset);
    const sliceOrderByOriginalIndex = fixture.slices.map((_, index) => index)
      .sort((a, b) => fixture.slices[b].value - fixture.slices[a].value || a - b)
      .reduce<Record<number, number>>((order, originalIndex, displayIndex) => {
        order[originalIndex] = displayIndex;
        return order;
      }, {});
    const schedule = fixtureSchedule[fixture.id];
    await db.insert(puzzles).values({ id: fixture.id, slug: fixture.id, title: fixture.title, context: fixture.context ?? null, maxAttempts: fixture.maxAttempts, status: schedule.status, publishDate: publishDate.toISOString().slice(0, 10), sourceName: 'Split Decision', sourceUrl: null, sourceMetadata: { fixture: true, fixtureId: fixture.id } }).onConflictDoUpdate({ target: puzzles.id, set: { title: fixture.title, maxAttempts: fixture.maxAttempts, publishDate: publishDate.toISOString().slice(0, 10), status: schedule.status, sourceMetadata: { fixture: true, fixtureId: fixture.id }, updatedAt: new Date() } });
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
