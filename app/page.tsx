import Game from '../components/Game';
export default function Page({ searchParams }: { searchParams: { puzzle?: string; fixture?: string; date?: string; state?: string } }) {
  const dev = process.env.NODE_ENV !== 'production';
  return <Game puzzleKey={dev ? searchParams.puzzle : undefined} devOptions={dev ? { fixture: searchParams.fixture, date: searchParams.date, state: searchParams.state } : undefined} />;
}
