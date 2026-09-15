import { defineConfig } from 'drizzle-kit';
export default defineConfig({ schema: './db/schema.ts', out: './drizzle', dialect: 'postgresql', dbCredentials: { url: process.env.POSTGRES_URL || process.env.DATABASE_URL || 'postgres://pie:pie@localhost:5433/pie_game' } });
