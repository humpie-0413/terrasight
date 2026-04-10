import { useParams } from 'react-router-dom';

export default function Ranking() {
  const { rankingSlug } = useParams<{ rankingSlug: string }>();
  return (
    <main style={{ padding: '24px' }}>
      <h1>Ranking — {rankingSlug}</h1>
      <p>Fact ranking page (TBD).</p>
    </main>
  );
}
