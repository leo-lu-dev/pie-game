import Link from 'next/link';
import { desc } from 'drizzle-orm';
import { redirect } from 'next/navigation';
import { db } from '../../../db/client';
import { puzzleCandidates } from '../../../db/schema';
import { adminUser } from '../../../lib/admin';

export const dynamic = 'force-dynamic';

export default async function CandidatesPage() {
  if (!await adminUser()) redirect('/');
  const candidates = await db.select().from(puzzleCandidates).orderBy(desc(puzzleCandidates.createdAt));
  return <main className="mx-auto min-h-screen max-w-6xl px-6 py-10"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-[#61706a]">StatPie review</p><h1 className="mt-2 text-3xl font-black">Candidate puzzles</h1></div><Link href="/" className="text-sm font-bold underline">Back to game</Link></div><div className="mt-8 overflow-x-auto rounded-2xl border border-[#dce4de] bg-white"><table className="w-full text-left text-sm"><thead className="border-b border-[#dce4de] text-xs uppercase tracking-wider text-[#61706a]"><tr><th className="px-4 py-3">Title</th><th className="px-4 py-3">Source</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Status</th></tr></thead><tbody>{candidates.map(candidate => <tr key={candidate.id} className="border-b border-[#edf0ed] last:border-0"><td className="px-4 py-4"><Link className="font-bold hover:underline" href={`/admin/candidates/${candidate.id}`}>{candidate.title}</Link><div className="mt-1 text-xs text-[#61706a]">{candidate.topic}</div></td><td className="px-4 py-4">{candidate.sourceName}</td><td className="px-4 py-4">{candidate.transformationType}</td><td className="px-4 py-4"><span className="rounded-full bg-[#edf0ed] px-3 py-1 text-xs font-bold">{candidate.status}</span></td></tr>)}</tbody></table>{candidates.length === 0 && <p className="p-8 text-center text-sm text-[#61706a]">No candidates yet.</p>}</div></main>;
}
