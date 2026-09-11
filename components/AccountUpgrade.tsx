'use client';

import { useState } from 'react';
import { createSupabaseBrowserClient } from '../lib/supabase/browser';

export default function AccountUpgrade() {
  const [emailMode, setEmailMode] = useState(false);
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  async function linkProvider(provider: 'google' | 'azure') {
    setWorking(true); setMessage(null);
    const { error } = await createSupabaseBrowserClient().auth.linkIdentity({ provider, options: { redirectTo: `${window.location.origin}/auth/callback` } });
    if (error) setMessage(error.message.includes('provider') ? 'This sign-in provider is not configured yet.' : error.message);
    setWorking(false);
  }
  async function linkEmail(event: React.FormEvent) {
    event.preventDefault(); setWorking(true); setMessage(null);
    const { error } = await createSupabaseBrowserClient().auth.updateUser({ email }, { emailRedirectTo: window.location.origin });
    setMessage(error ? error.message : 'Check your email to finish saving your progress.'); setWorking(false);
  }
  return <div className="mt-5 border-t border-[#b8c9bf] pt-5"><p className="text-sm font-bold">Save your progress across devices</p><p className="mt-1 text-xs text-[#61706a]">Keep this game history when you return from another device.</p><div className="mt-3 flex flex-wrap gap-2"><button disabled={working} onClick={() => linkProvider('google')} className="rounded-full border border-[#b8c9bf] px-3 py-2 text-xs font-bold disabled:opacity-50">Continue with Google</button><button disabled={working} onClick={() => linkProvider('azure')} className="rounded-full border border-[#b8c9bf] px-3 py-2 text-xs font-bold disabled:opacity-50">Continue with Microsoft</button><button disabled={working} onClick={() => setEmailMode(current => !current)} className="rounded-full border border-[#b8c9bf] px-3 py-2 text-xs font-bold disabled:opacity-50">Continue with email</button></div>{emailMode && <form onSubmit={linkEmail} className="mt-3 flex max-w-md gap-2"><input required type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" className="min-w-0 flex-1 rounded-full border border-[#b8c9bf] bg-white px-4 py-2 text-sm" /><button disabled={working} className="rounded-full bg-[#17221f] px-4 py-2 text-xs font-bold text-white disabled:opacity-50">Send link</button></form>}{message && <p className="mt-3 text-xs font-bold text-[#c64c22]">{message}</p>}</div>;
}
