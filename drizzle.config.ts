import { defineConfig } from 'drizzle-kit';
const databaseUrl = process.env.NODE_ENV === 'production'
  ? process.env.POSTGRES_URL || process.env.DATABASE_URL
  : process.env.DATABASE_URL || process.env.POSTGRES_URL;

export default defineConfig({ schema: './db/schema.ts', out: './drizzle', dialect: 'postgresql', dbCredentials: { url: databaseUrl || 'postgres://pie:pie@localhost:5433/pie_game' } });
