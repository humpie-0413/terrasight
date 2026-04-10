interface SourceLabelProps {
  source: string; // e.g. "NOAA GML Mauna Loa"
  url?: string;
}

/**
 * 출처 기관명 표시. CLAUDE.md: "출처 기관명을 반드시 표시"
 */
export default function SourceLabel({ source, url }: SourceLabelProps) {
  const content = <span>Source: {source}</span>;
  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '11px', color: '#64748b' }}>
        {content}
      </a>
    );
  }
  return <span style={{ fontSize: '11px', color: '#64748b' }}>{content}</span>;
}
