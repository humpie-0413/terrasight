import { useParams } from 'react-router-dom';

export default function Guide() {
  const { guideSlug } = useParams<{ guideSlug: string }>();
  return (
    <main style={{ padding: '24px' }}>
      <h1>Guide — {guideSlug}</h1>
      <p>Educational guide page (TBD).</p>
    </main>
  );
}
