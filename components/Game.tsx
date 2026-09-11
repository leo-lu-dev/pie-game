'use client';

import { useEffect, useState } from 'react';
import PieBoard from './PieBoard';
import AccountUpgrade from './AccountUpgrade';
import { ensureAnonymousSession } from '../lib/supabase/browser';
import { normalizeValues } from '../lib/normalize';
import type { GuessResponse, PublicPuzzle, SavedGuess } from '../lib/types';
import type { PlayerStatistics } from '../lib/types';
import { shareText } from '../lib/sharing';

type Props = { puzzleKey?: string; devOptions?: { fixture?: string; date?: string; state?: string } };

export default function Game({ puzzleKey, devOptions }: Props) {
  const [puzzle, setPuzzle] = useState<PublicPuzzle | null>(null);
  const [mapping, setMapping] = useState<(string | null)[]>(Array(5).fill(null));
  const [locked, setLocked] = useState<boolean[]>(Array(5).fill(false));
  const [selected, setSelected] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [result, setResult] = useState<'playing' | 'won' | 'lost'>('playing');
  const [shaking, setShaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [statistics, setStatistics] = useState<PlayerStatistics | null>(null);
  const [copied, setCopied] = useState(false);
  const [submittedGuesses, setSubmittedGuesses] = useState<SavedGuess[]>([]);
  const [showResults, setShowResults] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setPuzzle(null); setMapping(Array(5).fill(null)); setLocked(Array(5).fill(false)); setSelected(null); setAttempts(0); setResult('playing'); setError(null); setStatistics(null); setCopied(false); setSubmittedGuesses([]); setShowResults(true);
    const endpoint = puzzleKey ? `/api/puzzles/${encodeURIComponent(puzzleKey)}` : `/api/puzzle/today${devOptions ? `?${new URLSearchParams(Object.entries(devOptions).filter((entry): entry is [string, string] => Boolean(entry[1])))}` : ''}`;
    ensureAnonymousSession().then(() => fetch(endpoint)).then(async response => { if (!response.ok) throw new Error((await response.json()).error || 'Unable to load puzzle'); return response.json() as Promise<PublicPuzzle>; }).then(data => {
      if (cancelled) return;
      const state = data.state;
      setSubmittedGuesses(state?.guesses || []);
      if (state && state.guesses.length) {
        const lockedPositions = Array(data.slices.length).fill(false) as boolean[];
        state.guesses.forEach(guess => guess.correctPositions.forEach((correct, index) => { lockedPositions[index] ||= correct; }));
        const latest = state.guesses[state.guesses.length - 1];
        setLocked(lockedPositions);
        setMapping(latest.assignments.map((id, index) => lockedPositions[index] ? id : null));
      }
      setAttempts(state?.attempts || 0);
      if (state?.solved) {
        const latest = state.guesses[state.guesses.length - 1];
        setMapping(state.reveal || latest?.assignments || []);
        setResult('won'); setShowResults(true);
      } else if ((state?.attempts || 0) >= data.maxAttempts) {
        setMapping(state?.reveal || []);
        setResult('lost'); setShowResults(true);
      }
      setPuzzle(data);
      if (state?.solved || (state?.attempts || 0) >= data.maxAttempts) fetch('/api/stats').then(response => response.ok ? response.json() : null).then(data => { if (!cancelled && data) setStatistics(data.stats); });
    }).catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to load puzzle'); });
    return () => { cancelled = true; };
  }, [puzzleKey]);

  if (error) return <main className="mx-auto max-w-xl px-6 py-20 text-center"><h1 className="text-2xl font-black">Could not load puzzle</h1><p className="mt-3 text-[#61706a]">{error}</p></main>;
  if (!puzzle) return <main className="mx-auto max-w-xl px-6 py-20 text-center text-sm font-bold text-[#61706a]">Loading today&apos;s pie…</main>;

  const values = normalizeValues(puzzle.slices.map(slice => slice.value));
  const complete = mapping.every(Boolean) && new Set(mapping).size === 5;
  const pool = puzzle.categories.filter(category => !mapping.includes(category.id));
  const labelFor = (id: string | null) => puzzle.categories.find(category => category.id === id)?.label;
  const puzzleUrl = `/api/puzzles/${encodeURIComponent(puzzle.id)}`;
  const distributionMax = Math.max(1, ...Object.values(statistics?.guessDistribution || {}));

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
      setAttempts(data.attempt); setSubmittedGuesses(current => [...current, { attempt: data.attempt, assignments: mapping as string[], correctPositions: data.correctPositions, correctCount: data.correctCount }]); setLocked(current => current.map((value, i) => value || data.correctPositions[i]));
      if (data.solved || data.reveal) { setMapping(data.reveal || mapping); setResult(data.solved ? 'won' : 'lost'); setShowResults(true); fetch('/api/stats').then(response => response.ok ? response.json() : null).then(statsData => { if (statsData) setStatistics(statsData.stats); }); }
    else { setShaking(true); window.setTimeout(() => { setShaking(false); setMapping(current => current.map((value, i) => data.correctPositions[i] ? value : null)); setSelected(null); }, 420); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Guess could not be submitted'); }
    finally { setSubmitting(false); }
  }
  async function copyResult() {
    await navigator.clipboard.writeText(shareText(puzzle!.id, attempts, puzzle!.maxAttempts, submittedGuesses));
    setCopied(true); window.setTimeout(() => setCopied(false), 1800);
  }

  return <main className="mx-auto min-h-screen max-w-[1440px] px-3 py-4 sm:px-8">
    <header className="mb-4 flex items-center justify-between"><a href="/" className="text-xl font-black tracking-tight">pie<span className="text-[#f06d3c]">.</span>of the day</a><div className="rounded-full bg-[#17221f] px-4 py-2 text-xs font-bold uppercase tracking-widest text-white">{puzzle.id}</div></header>
    <section className="text-center"><h1 className="text-lg font-bold leading-snug sm:text-2xl">{puzzle.title}</h1><p className="mt-2 text-sm text-[#61706a]">Match each label to a slice. Drag to place or click two items to swap.</p></section>
    <section className={`game-area ${shaking ? 'animate-[shake_.42s_ease-in-out]' : ''}`}>
      <PieBoard values={values} mapping={mapping} locked={locked} selected={selected} disabled={shaking || result !== 'playing'} labelFor={labelFor} onClick={clickSlot} onDragStart={startDrag} onDrop={dropOnSlot} />
      <div onDragOver={event => event.preventDefault()} onDrop={dropInPool} className="mt-4 min-h-28 border-t border-[#edf0ed] pt-6"><p className="mb-3 text-center text-xs font-bold uppercase tracking-widest text-[#8a9690]">{selected ? 'Choose another item to swap' : 'Drag labels to slices · drag back here to remove'}</p><div className="option-pool">{puzzle.categories.map(category => { const inPool = pool.some(item => item.id === category.id); return <button key={category.id} draggable={inPool && result === 'playing'} onDragStart={event => startDrag(event, category.id)} onClick={() => clickCategory(category.id)} disabled={!inPool || result !== 'playing'} className={`answer-card ${!inPool ? 'pointer-events-none invisible' : 'cursor-grab border-[#dce4de] bg-white hover:border-[#f06d3c] active:cursor-grabbing'} ${selected === category.id ? 'border-[#f06d3c] bg-[#fff0e9] text-[#c64c22]' : ''}`}>{category.label}</button>; })}</div></div>
      <div className="mt-4 flex items-center justify-center gap-6"><span className="text-sm font-bold text-[#61706a]">{attempts} / {puzzle.maxAttempts} guesses</span><button onClick={submit} disabled={submitting || !complete || result !== 'playing'} className="rounded-full bg-[#f06d3c] px-6 py-3 text-sm font-black text-white shadow-lg shadow-[#f06d3c]/20 transition hover:bg-[#db5b2c] disabled:cursor-not-allowed disabled:bg-[#d8dfda] disabled:shadow-none">{submitting ? 'Checking…' : 'Submit guess'}</button></div>
      {error && <p className="mt-4 text-center text-sm font-bold text-[#c64c22]">{error}</p>}
      {result !== 'playing' && !showResults && <div className="mt-6 text-center"><button onClick={() => setShowResults(true)} className="rounded-full bg-[#17221f] px-5 py-3 text-sm font-black text-white">View result</button></div>}
      {result !== 'playing' && showResults && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#17221f]/45 p-4" role="dialog" aria-modal="true" aria-labelledby="result-title">
          <div className="relative max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-3xl bg-[#f8f4ec] p-5 shadow-2xl sm:p-7">
            <button onClick={() => setShowResults(false)} aria-label="Close results" className="absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full text-2xl text-[#61706a] transition hover:bg-[#17221f]/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#17221f]">×</button>
            <div className="px-7 pt-3 text-center">
              <p className="text-xs font-bold uppercase tracking-widest text-[#61706a]">Daily result</p>
              <h2 id="result-title" className="mt-2 text-2xl font-black">{result === 'won' ? 'You nailed it!' : 'That was a tough one.'}</h2>
              <p className="mt-2 text-sm text-[#61706a]">
                {result === 'won' ? `Solved in ${attempts} of ${puzzle.maxAttempts} guesses.` : `${attempts} of ${puzzle.maxAttempts} guesses used. View the answer on the board.`}
              </p>
            </div>
            <div className="mb-6 mt-5">
              <button onClick={copyResult} className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#17221f] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#2e4038] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#17221f]">
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></svg>
                <span aria-live="polite">{copied ? 'Copied!' : 'Copy result'}</span>
              </button>
              <p className="mt-2 text-center text-xs text-[#61706a]">Share this puzzle’s result, spoiler-free.</p>
            </div>
            <section className="rounded-2xl border border-[#e2e7df] bg-white/80 p-4 sm:p-5" aria-labelledby="statistics-title">
              <div className="flex items-center justify-between gap-3">
                <h3 id="statistics-title" className="font-black">Your stats</h3>
                <span className="text-xs text-[#61706a]">All time</span>
              </div>
              {statistics ? <>
                <dl className="mt-4 grid grid-cols-3 gap-x-3 gap-y-5 text-center">
                  {[
                    ['Played', statistics.gamesPlayed],
                    ['Won', statistics.gamesWon],
                    ['Win rate', `${statistics.winPercentage}%`],
                    ['Current streak', statistics.currentStreak],
                    ['Best streak', statistics.maximumStreak],
                    ['Avg. guesses / win', statistics.averageAttemptsOnWins || '—'],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-[11px] leading-4 text-[#61706a]">{label}</dt>
                      <dd className="mt-1 text-2xl font-black tabular-nums">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-5 border-t border-[#edf0ed] pt-4">
                  <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-[#61706a]">Guess distribution</h4>
                  <div className="space-y-2">
                    {Array.from({ length: puzzle.maxAttempts }, (_, index) => index + 1).map(attempt => {
                      const count = statistics.guessDistribution[attempt] ?? 0;
                      return (
                      <div key={attempt} className="flex items-center gap-3 text-xs tabular-nums" aria-label={`${attempt} guesses: ${count} wins`}>
                        <span className="w-3 font-bold">{attempt}</span>
                        <span className="h-5 flex-1 overflow-hidden rounded bg-[#edf0ed]"><span className="block h-full rounded bg-[#f06d3c]" style={{ width: `${Math.round((count / distributionMax) * 100)}%` }} /></span>
                        <span className="w-7 text-right font-bold">{count}</span>
                      </div>
                      );
                    })}
                  </div>
                </div>
              </> : <p className="mt-3 text-sm text-[#61706a]">Loading your stats…</p>}
            </section>
            <AccountUpgrade />
          </div>
        </div>
      )}
    </section>
    <footer className="mx-auto mt-4 flex max-w-4xl items-center justify-center text-xs text-[#8a9690]"><span>New puzzle every day</span></footer>
  </main>;
}
