import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';
import { supabaseConfig } from './config';

let client: SupabaseClient | undefined;
export function createSupabaseBrowserClient() {
  if (!client) { const { url, key } = supabaseConfig(); client = createBrowserClient(url, key); }
  return client;
}

export async function ensureAnonymousSession() {
  const supabase = createSupabaseBrowserClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (session) return session;
  const { data, error } = await supabase.auth.signInAnonymously();
  if (error || !data.session) throw error || new Error('Unable to start anonymous session');
  return data.session;
}
