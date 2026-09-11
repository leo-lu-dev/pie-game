'use client';

import { useEffect, useState } from 'react';
import PieBoard from './PieBoard';
import { normalizeValues } from '../lib/normalize';
import type { GuessResponse, PublicPuzzle } from '../lib/types';

type Props = { puzzleKey?: string };

export default function Game({ puzzleKey = 'households' }: Props) {
  const [puzzle, setPuzzle] = useState<PublicPuzzle | null>(null);
  const [mapping, setMapping] = useState<(string | null)[]>(Array(5).fill(null));
  const [locked, setLocked] = useState<boolean[]>(Array(5).fill(false));
  const [selected, setSelected] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [result, setResult] = useState<'playing' | 'won' | 'lost'>('playing');
  const [shaking, setShaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPuzzle(null); setMapping(Array(5).fill(null)); setLocked(Array(5).fill(false)); setSelected(null); setAttempts(0); setResult('playing'); setError(null);
    fetch(`/api/puzzles/${encodeURIComponent(puzzleKey)}`).then(async response => { if (!response.ok) throw new Error((await response.json()).error || 'Unable to load puzzle'); return response.json() as Promise<PublicPuzzle>; }).then(data => { if (!cancelled) setPuzzle(data); }).catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to load puzzle'); });
    return () => { cancelled = true; };
  }, [puzzleKey]);

  if (error) return <main className="mx-auto max-w-xl px-6 py-20 text-center"><h1 className="text-2xl font-black">Could not load puzzle</h1><p className="mt-3 text-[#61706a]">{error}</p></main>;
  if (!puzzle) return <main className="mx-auto max-w-xl px-6 py-20 text-center text-sm font-bold text-[#61706a]">Loading today&apos;s pie…</main>;

  const values = normalizeValues(puzzle.slices.map(slice => slice.value));
  const complete = mapping.every(Boolean) && new Set(mapping).size === 5;
  const pool = puzzle.categories.filter(category => !mapping.includes(category.id));
  const labelFor = (id: string | null) => puzzle.categories.find(category => category.id === id)?.label;
  const puzzleUrl = `/api/puzzles/${encodeURIComponent(puzzle.id)}`;

  function canMove(id: string) { const source = mapping.indexOf(id); return source < 0 || !locked[source]; }
  function place(index: number, id: string | null) {
    if (shaking || result !== 'playing' || locked[index] || !id || !canMove(id)) return;
    setMapping(current => { const source = current.indexOf(id); return current.map((value, i) => i === index ? id : source >= 0 && i === source ? current[index] : value); }); setSelected(null);
  }
  function clickSlot(index: number) { if (locked[index] || result !== 'playing') return; if (selected) place(index, selected); else if (mapping[index]) setSelected(mapping[index]); }
  function clickCategory(id: string) { if (result !== 'playing' || !canMove(id)) return; if (!selected) setSelected(id); else { const source = mapping.indexOf(selected); if (source >= 0) place(source, id); else setSelected(id); } }
  function startDrag(event: React.DragEvent<HTMLButtonElement>, id: string) { event.dataTransfer.setData('text/plain', id); setSelected(id); }
  function dropOnSlot(event: React.DragEvent<HTMLButtonElement>, index: number) { event.preventDefault(); place(index, event.dataTransfer.getData('text/plain')); }
  function dropInPool(event: React.DragEvent<HTMLDivElement>) { event.preventDefault(); const id = event.dataTransfer.getData('text/plain'); const source = mapping.indexOf(id); if (source >= 0 && !locked[source] && result === 'playing') setMapping(current => current.map((value, i) => i === source ? null : value)); setSelected(null); }

  async function submit() {
    if (!complete || submitting || result !== 'playing') return;
    setSubmitting(true); setError(null);
    try {
      const response = await fetch(`${puzzleUrl}/guess`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assignments: mapping }) });
      const data = await response.json() as GuessResponse & { error?: string };
      if (!response.ok) throw new Error(data.error || 'Guess could not be submitted');
      setAttempts(data.attempt); setLocked(current => current.map((value, i) => value || data.correctPositions[i]));
      if (data.solved || data.reveal) { setMapping(data.reveal || mapping); setResult(data.solved ? 'won' : 'lost'); }
      else { setShaking(true); window.setTimeout(() => { setShaking(false); setMapping(current => current.map((value, i) => data.correctPositions[i] ? value : null)); setSelected(null); }, 420); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Guess could not be submitted'); }
    finally { setSubmitting(false); }
  }
  async function reset() { await fetch(`${puzzleUrl}/reset`, { method: 'POST' }); setMapping(Array(5).fill(null)); setLocked(Array(5).fill(false)); setSelected(null); setAttempts(0); setResult('playing'); setError(null); }

  return <main className="mx-auto min-h-screen max-w-[1440px] px-3 py-4 sm:px-8">
    <header className="mb-4 flex items-center justify-between"><a href="/" className="text-xl font-black tracking-tight">pie<span className="text-[#f06d3c]">.</span>of the day</a><div className="rounded-full bg-[#17221f] px-4 py-2 text-xs font-bold uppercase tracking-widest text-white">{puzzle.id}</div></header>
    <section className="text-center"><h1 className="text-lg font-bold leading-snug sm:text-2xl">{puzzle.title}</h1><p className="mt-2 text-sm text-[#61706a]">Match each label to a slice. Drag to place or click two items to swap.</p></section>
    <section className={`game-area ${shaking ? 'animate-[shake_.42s_ease-in-out]' : ''}`}>
      <PieBoard values={values} mapping={mapping} locked={locked} selected={selected} disabled={shaking || result !== 'playing'} labelFor={labelFor} onClick={clickSlot} onDragStart={startDrag} onDrop={dropOnSlot} />
      <div onDragOver={event => event.preventDefault()} onDrop={dropInPool} className="mt-4 min-h-28 border-t border-[#edf0ed] pt-6"><p className="mb-3 text-center text-xs font-bold uppercase tracking-widest text-[#8a9690]">{selected ? 'Choose another item to swap' : 'Drag labels to slices · drag back here to remove'}</p><div className="option-pool">{puzzle.categories.map(category => { const inPool = pool.some(item => item.id === category.id); return <button key={category.id} draggable={inPool && result === 'playing'} onDragStart={event => startDrag(event, category.id)} onClick={() => clickCategory(category.id)} disabled={!inPool || result !== 'playing'} className={`answer-card ${!inPool ? 'pointer-events-none invisible' : 'cursor-grab border-[#dce4de] bg-white hover:border-[#f06d3c] active:cursor-grabbing'} ${selected === category.id ? 'border-[#f06d3c] bg-[#fff0e9] text-[#c64c22]' : ''}`}>{category.label}</button>; })}</div></div>
      <div className="mt-4 flex items-center justify-center gap-6"><span className="text-sm font-bold text-[#61706a]">{attempts} / {puzzle.maxAttempts} guesses</span><button onClick={submit} disabled={submitting || !complete || result !== 'playing'} className="rounded-full bg-[#f06d3c] px-6 py-3 text-sm font-black text-white shadow-lg shadow-[#f06d3c]/20 transition hover:bg-[#db5b2c] disabled:cursor-not-allowed disabled:bg-[#d8dfda] disabled:shadow-none">{submitting ? 'Checking…' : 'Submit guess'}</button></div>
      {error && <p className="mt-4 text-center text-sm font-bold text-[#c64c22]">{error}</p>}
      {result !== 'playing' && <div className={`mt-7 rounded-2xl p-5 ${result === 'won' ? 'bg-[#e2f5ed]' : 'bg-[#fff0e9]'}`}><div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-black">{result === 'won' ? 'You nailed it!' : 'That was a tough one.'}</h2><p className="mt-1 text-sm text-[#61706a]">{result === 'won' ? `Solved in ${attempts} ${attempts === 1 ? 'guess' : 'guesses'}.` : 'Here is the complete reveal.'}</p></div><button onClick={reset} className="rounded-full border border-[#b8c9bf] px-4 py-2 text-xs font-bold">Play again</button></div><div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-5">{puzzle.categories.map(category => { const index = mapping.indexOf(category.id); return <div key={category.id} className="rounded-xl bg-white/70 p-3"><div className="text-xs font-bold text-[#61706a]">{category.label}</div><div className="mt-1 text-lg font-black">{index >= 0 ? `${values[index]}%` : '—'}</div></div>; })}</div></div>}
    </section>
    <footer className="mx-auto mt-4 flex max-w-4xl flex-wrap items-center justify-between gap-3 text-xs text-[#8a9690]"><span>New puzzle every day · local prototype</span><span>Try another: <a className="font-bold underline" href="/?puzzle=spending">spending</a> · <a className="font-bold underline" href="/?puzzle=commuters">commuters</a> · <a className="font-bold underline" href="/?puzzle=videos">videos</a></span></footer>
  </main>;
}
