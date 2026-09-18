import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'Split Decision', description: 'A daily data guessing game.' };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
