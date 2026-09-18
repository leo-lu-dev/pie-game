'use client';

import { useEffect, useMemo, useState } from 'react';
import Game from './Game';
import type { PublicPuzzle } from '../lib/types';

type Decision = 'approved' | 'rejected';
type ReviewItem = {
  kind: 'candidate';
  id: string;
  title: string;
  status: string;
  humanStatus: Decision | null;
  agentReview: { verdict?: string; issues?: string[]; general_audience_fit?: number; intuition_potential?: number } | null;
  puzzle: PublicPuzzle;
  answer: string[];
};

const ghostPuzzle: PublicPuzzle = {
  id: 'ghost-preview',
  title: 'Sample topic distribution',
  context: 'Ghost board preview for checking the local game interface.',
  maxAttempts: 4,
  categories: ['Whatever', 'Something else', 'Another thing', 'The other thing', 'Etcetera']
    .map((label, index) => ({ id: `ghost-${index}`, label })),
  slices: [
    { id: 'ghost-slice-0', value: 31 },
    { id: 'ghost-slice-1', value: 24 },
    { id: 'ghost-slice-2', value: 19 },
    { id: 'ghost-slice-3', value: 15 },
    { id: 'ghost-slice-4', value: 11 },
  ],
};
const ghostAnswer = ghostPuzzle.categories.map(category => category.id);

export default function LocalReviewMode() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const item = items[index];
  const decision = item?.humanStatus || null;
  const progressLabel = useMemo(() => items.length ? `${index + 1} / ${items.length}` : '', [index, items.length]);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/local-review').then(async response => {
      if (!response.ok) throw new Error((await response.json()).error || 'Unable to load local review queue');
      return response.json() as Promise<{ items: ReviewItem[]; storageWarning?: string | null }>;
    }).then(data => {
      if (!cancelled) {
        setItems(data.items);
        setStorageWarning(data.storageWarning || null);
      }
    }).catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to load local review queue'); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  function move(offset: number) { setIndex(current => Math.max(0, Math.min(items.length - 1, current + offset))); }

  async function decide(nextDecision: Decision) {
    if (!item || saving) return;
    setSaving(true); setError(null);
    try {
      const response = await fetch('/api/local-review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: item.kind, id: item.id, decision: nextDecision }) });
      const data = await response.json() as { error?: string };
      if (!response.ok) throw new Error(data.error || 'Could not save decision');
      if (nextDecision === 'rejected') {
        setItems(current => current.filter(entry => entry.id !== item.id));
        setIndex(current => Math.max(0, Math.min(current, items.length - 2)));
      } else {
        setItems(current => current.map((entry, entryIndex) => entryIndex === index ? { ...entry, status: nextDecision, humanStatus: nextDecision } : entry));
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save decision'); }
    finally { setSaving(false); }
  }

  if (loading) return <main className="mx-auto max-w-xl px-6 py-20 text-center text-sm font-bold text-[#61706a]">Loading local review queue…</main>;
  if (error) return <main className="mx-auto max-w-xl px-6 py-20 text-center"><h1 className="text-2xl font-black">Local review unavailable</h1><p className="mt-3 text-[#61706a]">{error}</p><p className="mt-5 text-sm text-[#61706a]">Check that DATABASE_URL points to your local database and that migrations have been applied.</p></main>;
  if (!item) return <div className="ghost-preview min-h-screen bg-[#f8f4ec] px-3 py-4 sm:px-8"><p className="mx-auto mb-4 max-w-[1440px] rounded-full bg-[#fff8dc] px-4 py-2 text-center text-xs font-bold uppercase tracking-widest text-[#806b28]">Ghost board preview · no candidates awaiting review</p><Game localPuzzle={ghostPuzzle} localAnswer={ghostAnswer} /></div>;

  return <main className="min-h-screen bg-[#f8f4ec] px-3 py-4 sm:px-8">
    <header className="mx-auto mb-5 flex max-w-[1440px] items-center justify-between gap-4">
      <a href="/" className="text-xl font-black tracking-tight">Split Decision</a>
      <div className="rounded-full bg-[#17221f] px-4 py-2 text-xs font-bold uppercase tracking-widest text-white">Local review · {progressLabel}</div>
    </header>
    <section className="mx-auto mb-4 flex max-w-[1440px] flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#dce4de] bg-white/70 p-3">
      <button onClick={() => move(-1)} disabled={index === 0} className="rounded-full border border-[#dce4de] px-4 py-2 text-sm font-black disabled:cursor-not-allowed disabled:opacity-40">← Back</button>
      <div className="min-w-0 flex-1 text-center"><p className="truncate text-xs font-bold uppercase tracking-widest text-[#8a9690]">Candidate · {item.status}</p><p className="truncate text-sm font-black">{item.title}</p></div>
      <button onClick={() => move(1)} disabled={index === items.length - 1} className="rounded-full border border-[#dce4de] px-4 py-2 text-sm font-black disabled:cursor-not-allowed disabled:opacity-40">Next →</button>
    </section>
    <section className="mx-auto mb-4 flex max-w-[1440px] flex-wrap items-center justify-center gap-3">
      <button onClick={() => decide('rejected')} disabled={saving} className={`rounded-full border-2 px-6 py-3 text-sm font-black transition ${decision === 'rejected' ? 'border-[#c64c22] bg-[#fff0e9] text-[#c64c22]' : 'border-[#dce4de] bg-white hover:border-[#c64c22]'}`}>{saving ? 'Saving…' : 'Reject'}</button>
      <span className="rounded-full bg-[#edf0ed] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[#61706a]">{decision || 'Not reviewed'}</span>
      <button onClick={() => decide('approved')} disabled={saving} className={`rounded-full border-2 px-6 py-3 text-sm font-black transition ${decision === 'approved' ? 'border-[#26735a] bg-[#e9f5ee] text-[#26735a]' : 'border-[#dce4de] bg-white hover:border-[#26735a]'}`}>Approve</button>
    </section>
    {item.agentReview && <section className="mx-auto mb-4 max-w-2xl rounded-2xl border border-[#dce4de] bg-white/70 p-4 text-center text-sm"><span className="font-black">Agent: {item.agentReview.verdict || 'reviewed'}</span>{item.agentReview.issues?.length ? <p className="mt-2 text-[#61706a]">{item.agentReview.issues.join(' · ')}</p> : <p className="mt-2 text-[#61706a]">No issues reported · audience {item.agentReview.general_audience_fit ?? '—'}/5 · intuition {item.agentReview.intuition_potential ?? '—'}/5</p>}</section>}
    {storageWarning && <p className="mx-auto mb-4 max-w-2xl rounded-xl border border-[#ead9a7] bg-[#fff8dc] px-4 py-3 text-center text-sm font-bold text-[#806b28]">{storageWarning} Start local Postgres and reload to include candidates.</p>}
    {error && <p className="mx-auto mb-4 max-w-xl text-center text-sm font-bold text-[#c64c22]">{error}</p>}
    <Game localPuzzle={item.puzzle} localAnswer={item.answer} />
  </main>;
}
