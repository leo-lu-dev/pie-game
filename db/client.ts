import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

const connectionString = process.env.POSTGRES_URL || process.env.DATABASE_URL || 'postgres://pie:pie@localhost:5433/pie_game';
const client = postgres(connectionString, { max: 10, prepare: false });
export const db = drizzle(client, { schema });
export { client };
