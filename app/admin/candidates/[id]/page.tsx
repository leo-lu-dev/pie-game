import Link from 'next/link';
import { eq } from 'drizzle-orm';
import { notFound, redirect } from 'next/navigation';
import { db } from '../../../../db/client';
import { candidateAgentReviews, candidateCategories, candidateValidations, puzzleCandidates } from '../../../../db/schema';
import { adminUser } from '../../../../lib/admin';

export const dynamic = 'force-dynamic';

export default async function CandidateDetailPage({ params }: { params: { id: string } }) {
  if (!await adminUser()) redirect('/');
  const [candidate] = await db.select().from(puzzleCandidates).where(eq(puzzleCandidates.id, params.id)).limit(1);
  if (!candidate) notFound();
  const [categories, validations, reviews] = await Promise.all([
    db.select().from(candidateCategories).where(eq(candidateCategories.candidateId, params.id)).orderBy(candidateCategories.displayOrder),
    db.select().from(candidateValidations).where(eq(candidateValidations.candidateId, params.id)),
    db.select().from(candidateAgentReviews).where(eq(candidateAgentReviews.candidateId, params.id)).orderBy(candidateAgentReviews.createdAt),
  ]);
  return <main className="mx-auto min-h-screen max-w-4xl px-6 py-10"><Link href="/admin/candidates" className="text-sm font-bold underline">← All candidates</Link><p className="mt-8 text-xs font-bold uppercase tracking-widest text-[#61706a]">{candidate.sourceName} · {candidate.status}</p><h1 className="mt-2 text-3xl font-black">{candidate.title}</h1>{candidate.context && <p className="mt-3 text-[#61706a]">{candidate.context}</p>}<section className="mt-8 rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-black">Categories</h2><div className="mt-4 divide-y divide-[#edf0ed]">{categories.map(category => <div key={category.id} className="flex justify-between gap-4 py-3"><span className="font-bold">{category.label}</span><span className="tabular-nums">{category.rawValue}</span></div>)}</div></section><section className="mt-5 rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-black">Source and transformation</h2><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-[#61706a]">Dataset</dt><dd className="font-bold">{candidate.sourceDatasetId}</dd></div><div><dt className="text-[#61706a]">Transformation</dt><dd className="font-bold">{candidate.transformationType}</dd></div><div><dt className="text-[#61706a]">Geography</dt><dd>{candidate.geography || '—'}</dd></div><div><dt className="text-[#61706a]">Time period</dt><dd>{candidate.timePeriod || '—'}</dd></div></dl><pre className="mt-4 overflow-x-auto rounded-xl bg-[#17221f] p-4 text-xs text-white">{JSON.stringify(candidate.transformationMetadataJson, null, 2)}</pre></section><section className="mt-5 rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-black">Deterministic validation</h2>{validations.map(validation => <pre key={validation.id} className="mt-4 overflow-x-auto rounded-xl bg-[#edf0ed] p-4 text-xs">{JSON.stringify({ technicalValid: validation.technicalValid, dimensionValid: validation.dimensionValid, transformationValid: validation.transformationValid, diagnostics: validation.diagnosticsJson, issues: validation.issuesJson }, null, 2)}</pre>)}</section><section className="mt-5 rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-black">Agent reviews</h2>{reviews.length ? reviews.map(review => <pre key={review.id} className="mt-4 overflow-x-auto rounded-xl bg-[#edf0ed] p-4 text-xs">{JSON.stringify(review.reviewJson, null, 2)}</pre>) : <p className="mt-3 text-sm text-[#61706a]">No agent review yet.</p>}</section></main>;
}
