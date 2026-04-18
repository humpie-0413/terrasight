export interface SourceLabelProps {
  source: string;
  url?: string;
}

export function SourceLabel({ source, url }: SourceLabelProps) {
  const style = { fontSize: '11px', color: '#64748b' } as const;
  const text = `Source: ${source}`;
  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" style={style}>
        {text}
      </a>
    );
  }
  return <span style={style}>{text}</span>;
}
