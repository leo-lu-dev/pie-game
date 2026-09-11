import Game from '../components/Game';
export default function Page({ searchParams }: { searchParams: { puzzle?: string } }) { return <Game puzzleKey={searchParams.puzzle} />; }
