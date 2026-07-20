import { useMemo, useState } from "react";

// UI-4/UI-5: bucket table; the Review bucket gets an optional language filter
// (view-only — it does not change classification).
export function BucketTable({ rows, bucket }: { rows: any[]; bucket: string }) {
  const [lang, setLang] = useState<string>("");

  const languages = useMemo(() => {
    const s = new Set<string>();
    rows.forEach((r) => r.name_language && s.add(r.name_language));
    return Array.from(s).sort();
  }, [rows]);

  const filtered = useMemo(
    () => (lang ? rows.filter((r) => r.name_language === lang) : rows),
    [rows, lang]
  );

  return (
    <>
      {bucket === "review" && languages.length > 0 && (
        <div className="lang-filter">
          <span className="muted">фильтр по языку имени:</span>
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="">все</option>
            {languages.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <span className="count-line">
            {filtered.length} из {rows.length}
          </span>
        </div>
      )}

      <div className="table-wrap">
        <table className="results">
          <thead>
            <tr>
              <th>Домен</th>
              <th>Вердикт</th>
              <th>Категория</th>
              <th>Язык имени</th>
              <th>English?</th>
              <th>Confidence</th>
              <th>Причина</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.domain}>
                <td className="mono">{r.domain}</td>
                <td>
                  <span className={`verdict v-${r.verdict}`}>{r.verdict}</span>
                </td>
                <td>{r.category}</td>
                <td>{r.name_language}</td>
                <td className="num">{r.is_english_name ? "✓" : "—"}</td>
                <td className="num">{r.confidence.toFixed(2)}</td>
                <td className="reason">{r.reason}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="muted" style={{ padding: 16 }}>
                  пусто
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
