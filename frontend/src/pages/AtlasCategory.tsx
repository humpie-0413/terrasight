import { useParams } from 'react-router-dom';

export default function AtlasCategory() {
  const { categorySlug } = useParams<{ categorySlug: string }>();
  return (
    <main style={{ padding: '24px' }}>
      <h1>Atlas — {categorySlug}</h1>
      <p>Category detail page (TBD).</p>
    </main>
  );
}
