import Game from '../components/Game';
import LocalReviewMode from '../components/LocalReviewMode';

export default function Page() {
  const dev = process.env.NODE_ENV !== 'production';
  return dev ? <LocalReviewMode /> : <Game />;
}
