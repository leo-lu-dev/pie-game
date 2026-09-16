'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CandidateReviewActions({ candidateId }: { candidateId: string }) {
  const router = useRouter();
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function review(action: 'approved' | 'rejected' | 'needs_review') {
    setSaving(true); setError(null);
    try {
      const response = await fetch(`/api/admin/candidates/${candidateId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, notes }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not save review');
      router.refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save review'); }
    finally { setSaving(false); }
  }

  return <section className="mt-5 rounded-2xl border border-[#dce4de] bg-white p-5"><h2 className="font-black">Human review</h2><textarea value={notes} onChange={event => setNotes(event.target.value)} placeholder="Optional reviewer notes" className="mt-4 min-h-24 w-full rounded-xl border border-[#dce4de] bg-[#f8f4ec] p-3 text-sm outline-none focus:border-[#f06d3c]" /><div className="mt-4 flex flex-wrap gap-3"><button disabled={saving} onClick={() => review('approved')} className="rounded-full bg-[#2e7d5b] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Approve</button><button disabled={saving} onClick={() => review('needs_review')} className="rounded-full bg-[#d38b25] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Needs investigation</button><button disabled={saving} onClick={() => review('rejected')} className="rounded-full bg-[#b44d3c] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Reject</button></div>{error && <p className="mt-3 text-sm font-bold text-[#b44d3c]">{error}</p>}</section>;
}
