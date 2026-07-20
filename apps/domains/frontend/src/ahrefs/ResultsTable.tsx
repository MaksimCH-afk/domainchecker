import type { ResultRow, Tier } from "../types";

const TIER_CLASS: Record<Tier, string> = {
  A: "t-a",
  B: "t-b",
  C: "t-c",
  Review: "t-review",
  Rejected: "t-rejected",
};

function flagDots(r: ResultRow) {
  const dots: { title: string; cls: string }[] = [];
  if (r.flag_spam_floor) dots.push({ title: "spam_floor", cls: "f-spam" });
  if (r.flag_burn) dots.push({ title: "burn", cls: "f-burn" });
  if (r.flag_geo_review) dots.push({ title: "geo_review", cls: "f-geo" });
  if (r.flag_cjk) dots.push({ title: "cjk", cls: "f-cjk" });
  return dots;
}

export function ResultsTable({ rows }: { rows: ResultRow[] }) {
  return (
    <div className="table-wrap">
      <table className="results">
        <thead>
          <tr>
            <th>Target</th>
            <th>Тир</th>
            <th>Score</th>
            <th>Reject</th>
            <th>DR</th>
            <th>rd_fol</th>
            <th>fol_share</th>
            <th>bl_rd</th>
            <th>subnet_div</th>
            <th>burn</th>
            <th>Organic</th>
            <th>cc</th>
            <th>tld</th>
            <th>Флаги</th>
            <th>override</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.Target}>
              <td className="mono">{r.Target}</td>
              <td>
                <span className={`tier-badge ${TIER_CLASS[r.tier]}`}>{r.tier}</span>
              </td>
              <td className="num">{r.score == null ? "—" : r.score.toFixed(1)}</td>
              <td className="reason">{r.reject_reason || ""}</td>
              <td className="num">{r["Domain Rating"]}</td>
              <td className="num">{r.rd_fol}</td>
              <td className="num">{r.fol_share.toFixed(2)}</td>
              <td className="num">{r.bl_rd.toFixed(2)}</td>
              <td className="num">{r.subnet_div.toFixed(2)}</td>
              <td className="num">{r.burn.toFixed(1)}</td>
              <td className="num">{r["Organic / Traffic"]}</td>
              <td>{r.cc}</td>
              <td className="mono">{r.tld}</td>
              <td>
                <span className="flags">
                  {flagDots(r).map((d) => (
                    <span key={d.title} className={`dot ${d.cls}`} title={d.title} />
                  ))}
                </span>
              </td>
              <td className="reason">{r.tier_override_reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
