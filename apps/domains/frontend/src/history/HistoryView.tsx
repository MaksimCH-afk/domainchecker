import { useEffect, useState } from "react";
import { api } from "../api";
import { BucketTable } from "../classifier/BucketTable";

// UI-11 / UI-12: run history + logs. Open a past run to re-copy/re-export.
export function HistoryView() {
  const [runs, setRuns] = useState<any[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [tab, setTab] = useState<"good" | "bad" | "review" | "logs">("good");

  useEffect(() => {
    api.listRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  async function open(id: string) {
    setOpenId(id);
    setTab("good");
    const [view, lg] = await Promise.all([api.getRun(id), api.getLogs(id)]);
    setDetail(view);
    setLogs(lg);
  }

  async function download(bucket: string, format: "csv" | "txt") {
    if (!openId) return;
    const blob = await api.exportRun(openId, format, bucket === "all" ? null : bucket);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `classify_${bucket}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const fmt = (ts: number) => (ts ? new Date(ts * 1000).toLocaleString() : "—");

  return (
    <div className="view">
      <header className="view-head">
        <h1>История и логи</h1>
        <p className="muted">Прошлые прогоны классификатора: разбивка, стоимость, логи.</p>
      </header>

      <div className="table-wrap">
        <table className="results">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Статус</th>
              <th>Провайдер</th>
              <th>Модель</th>
              <th>Всего</th>
              <th>good</th>
              <th>bad</th>
              <th>review</th>
              <th>errors</th>
              <th>≈ $</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{fmt(r.created_at)}</td>
                <td>{r.status}</td>
                <td>{r.provider}</td>
                <td className="mono">{r.model}</td>
                <td className="num">{r.total}</td>
                <td className="num">{r.good}</td>
                <td className="num">{r.bad}</td>
                <td className="num">{r.review}</td>
                <td className="num">{r.errors}</td>
                <td className="num">{r.est_cost ? r.est_cost.toFixed(4) : "—"}</td>
                <td>
                  <button onClick={() => open(r.id)}>Открыть</button>
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={11} className="muted" style={{ padding: 16 }}>
                  прогонов пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="detail">
          <div className="seg bucket-seg">
            {(["good", "bad", "review", "logs"] as const).map((t) => (
              <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
                {t === "logs" ? "Логи" : `${t} · ${detail.buckets[t]?.length ?? 0}`}
              </button>
            ))}
          </div>

          {tab !== "logs" ? (
            <>
              <div className="actions bucket-actions">
                <button onClick={() => download(tab, "csv")}>Экспорт CSV</button>
                <button onClick={() => download(tab, "txt")}>Экспорт TXT</button>
              </div>
              <BucketTable rows={detail.buckets[tab] ?? []} bucket={tab} />
            </>
          ) : (
            <div className="logs">
              {logs.map((l, i) => (
                <div key={i} className={`log-line lvl-${l.level.toLowerCase()}`}>
                  <span className="log-ts">{fmt(l.ts)}</span>
                  <span className="log-lvl">{l.level}</span>
                  <span>{l.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
