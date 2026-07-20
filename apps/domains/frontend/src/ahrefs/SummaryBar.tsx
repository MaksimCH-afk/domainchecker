import type { Summary, Tier } from "../types";

const TIER_ORDER: Tier[] = ["A", "B", "C", "Review", "Rejected"];
const TIER_CLASS: Record<Tier, string> = {
  A: "t-a",
  B: "t-b",
  C: "t-c",
  Review: "t-review",
  Rejected: "t-rejected",
};

export function SummaryBar({ summary }: { summary: Summary }) {
  return (
    <div className="summary">
      <div className="summary-row">
        {TIER_ORDER.map((t) => (
          <div key={t} className={`stat ${TIER_CLASS[t]}`}>
            <div className="stat-num">{summary.tiers[t]?.count ?? 0}</div>
            <div className="stat-label">
              {t} · {summary.tiers[t]?.pct ?? 0}%
            </div>
          </div>
        ))}
      </div>
      <div className="summary-meta">
        <span>
          Загружено строк: <b>{summary.total_input_rows}</b>
        </span>
        <span>
          Проанализировано: <b>{summary.analyzed}</b>
        </span>
        <span>
          Дублей убрано: <b>{summary.duplicates_removed}</b>
        </span>
      </div>
      <div className="summary-chips">
        {Object.entries(summary.reject_reasons)
          .filter(([, v]) => v.count > 0)
          .map(([k, v]) => (
            <span key={k} className="chip chip-reject">
              {k}: {v.count} ({v.pct}%)
            </span>
          ))}
        {Object.entries(summary.flags)
          .filter(([, v]) => v.count > 0)
          .map(([k, v]) => (
            <span key={k} className="chip chip-flag">
              {k}: {v.count} ({v.pct}%)
            </span>
          ))}
      </div>
    </div>
  );
}
