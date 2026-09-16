import { createSupabaseServerClient } from './supabase/server';

export async function adminUser() {
  const { data: { user } } = await createSupabaseServerClient().auth.getUser();
  const email = user?.email?.toLowerCase();
  const allowed = (process.env.ADMIN_EMAILS || '').split(',').map(value => value.trim().toLowerCase()).filter(Boolean);
  return email && allowed.includes(email) ? user : null;
}
