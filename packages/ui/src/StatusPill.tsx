import type { BlockStatus } from '@terrasight/schemas';

interface StatusPillMeta {
  label: string;
  bg: string;
  fg: string;
  border: string;
}

// Tailwind-inspired neutral palette — matches report-block policy colors.
// ok is rendered with a muted slate tone (the default "all clear" state).
const STATUS_META: Record<BlockStatus, StatusPillMeta> = {
  ok: {
    label: 'OK',
    bg: '#f1f5f9',
    fg: '#475569',
    border: '#cbd5e1',
  },
  pending: {
    label: 'Pending',
    bg: '#fef3c7',
    fg: '#92400e',
    border: '#fde68a',
  },
  error: {
    label: 'Error',
    bg: '#fee2e2',
    fg: '#b91c1c',
    border: '#fecaca',
  },
  not_configured: {
    label: 'Not configured',
    bg: '#f1f5f9',
    fg: '#475569',
    border: '#cbd5e1',
  },
};

export interface StatusPillProps {
  status: BlockStatus;
}

/**
 * Small inline pill indicating a block's data pipeline status.
 * Sits next to the block H2 / TrustBadge. Height ~18-20px.
 */
export function StatusPill({ status }: StatusPillProps) {
  const meta = STATUS_META[status];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: '18px',
        padding: '0 8px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: 600,
        lineHeight: 1,
        backgroundColor: meta.bg,
        color: meta.fg,
        border: `1px solid ${meta.border}`,
      }}
    >
      {meta.label}
    </span>
  );
}
