import { useState } from 'react';

/**
 * Born-in Interactive — P1 (바이럴 핵심).
 * 출생 연도 → CO2/기온/해빙 then vs now 비교.
 * 데이터 시작점 자동 보정:
 *   - CO2 1958 이전 → "1958 (record start)"
 *   - Sea Ice 1979 이전 → "1979 (record start)"
 */
export default function BornIn() {
  const [year, setYear] = useState<number>(2000);

  return (
    <section style={{ padding: '24px', borderTop: '1px solid #e5e7eb' }}>
      <h2>Born in {year}? See how Earth changed</h2>
      <input
        type="number"
        value={year}
        min={1900}
        max={new Date().getFullYear()}
        onChange={(e) => setYear(parseInt(e.target.value, 10))}
      />
      {/* TODO: fetch and render then-vs-now comparison */}
    </section>
  );
}
