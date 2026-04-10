// 5단계 신뢰 태그 enum + 색상
// See CLAUDE.md → "신뢰 태그 (5단계 뱃지)"

export enum TrustTag {
  Observed = 'observed',
  NearRealTime = 'near-real-time',
  Forecast = 'forecast',
  Derived = 'derived',
  Estimated = 'estimated',
}

export interface TrustTagMeta {
  label: string;
  color: string; // hex
  emoji: string;
  description: string;
}

export const TRUST_TAG_META: Record<TrustTag, TrustTagMeta> = {
  [TrustTag.Observed]: {
    label: 'observed',
    color: '#22c55e', // green
    emoji: '🟢',
    description: '기기 직접 측정',
  },
  [TrustTag.NearRealTime]: {
    label: 'near-real-time',
    color: '#eab308', // yellow
    emoji: '🟡',
    description: '수시간 내 처리',
  },
  [TrustTag.Forecast]: {
    label: 'forecast/model',
    color: '#f97316', // orange
    emoji: '🟠',
    description: 'CAMS, GFS 등 모델 기반',
  },
  [TrustTag.Derived]: {
    label: 'derived',
    color: '#3b82f6', // blue
    emoji: '🔵',
    description: '관측값에서 계산',
  },
  [TrustTag.Estimated]: {
    label: 'estimated',
    color: '#e5e7eb', // light gray
    emoji: '⚪',
    description: '통계/ML 추론',
  },
};
