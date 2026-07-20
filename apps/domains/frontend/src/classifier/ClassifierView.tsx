import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { BucketTable } from "./BucketTable";
import { ClassifierGuide } from "./ClassifierGuide";

type Bucket = "good" | "bad" | "review";
const BUCKETS: { id: Bucket; label: string }[] = [
  { id: "good", label: "Good" },
  { id: "bad", label: "Bad" },
  { id: "review", label: "На проверку" },
];

export function ClassifierView({ bridgedTargets }: { bridgedTargets: string[] }) {
  const [text, setText] = useState("");
  const [counts, setCounts] = useState<{ valid: number; duplicates: number; invalid: number } | null>(null);
  const [ignoreCache, setIgnoreCache] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<any>(null);
  const [buckets, setBuckets] = useState<Record<Bucket, any[]>>({ good: [], bad: [], review: [] });
  const [tab, setTab] = useState<Bucket>("good");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (bridgedTargets.length) setText(bridgedTargets.join("\n"));
  }, [bridgedTargets]);

  // Debounced preview counts.
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (text.trim()) api.preview(text).then(setCounts).catch(() => setCounts(null));
      else setCounts(null);
    }, 300);
    return () => window.clearTimeout(t);
  }, [text]);

  useEffect(() => () => { if (pollRef.current) window.clearInterval(pollRef.current); }, []);

  async function start() {
    setError(null);
    try {
      const { run_id } = await api.startRun(text, ignoreCache);
      setRunId(run_id);
      poll(run_id);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function poll(id: string) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    const tick = async () => {
      try {
        const view = await api.getRun(id);
        setRun(view.run);
        setBuckets(view.buckets);
        if (view.run.status !== "running" && pollRef.current) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        /* keep polling */
      }
    };
    tick();
    pollRef.current = window.setInterval(tick, 800);
  }

  async function cancel() {
    if (runId) await api.cancelRun(runId);
  }

  async function copyBucket(b: Bucket) {
    await navigator.clipboard.writeText(buckets[b].map((r) => r.domain).join("\n"));
  }

  async function download(b: Bucket, format: "csv" | "txt") {
    if (!runId) return;
    const blob = await api.exportRun(runId, format, b);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `classify_${b}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const running = run?.status === "running";
  const pct = run && run.total ? Math.round((100 * run.processed) / run.total) : 0;

  return (
    <div className="view">
      <header className="view-head">
        <h1>Классификатор по имени · качественный гейт</h1>
        <p className="muted">
          Нейросеть (OpenAI/OpenRouter) судит домен по названию —
          pharma/casino/adult/скам/язык — и раскладывает good / bad / на проверку.
          Провайдер и модель — в «Настройках» → AI.
        </p>
      </header>

      <ClassifierGuide />

      {bridgedTargets.length > 0 && (
        <div className="bridge-note">
          ↳ Получено из Ahrefs-фильтра: <b>{bridgedTargets.length}</b> доменов
          прошедших тиров. Мост между двумя частями работает.
        </div>
      )}

      <label className="field wide">
        <span>Домены (по одному в строке)</span>
        <textarea
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="example.com&#10;anothersite.net"
          disabled={running}
        />
      </label>

      {counts && (
        <div className="count-line">
          распознано валидных: <b>{counts.valid}</b> · дублей: {counts.duplicates} ·
          невалидных: {counts.invalid}
        </div>
      )}

      <div className="run-controls">
        <label className="raw-toggle">
          <input
            type="checkbox"
            checked={ignoreCache}
            onChange={(e) => setIgnoreCache(e.target.checked)}
          />
          игнорировать кэш
        </label>
        {!running ? (
          <button className="primary" onClick={start} disabled={!counts?.valid && !counts?.invalid}>
            Проверить
          </button>
        ) : (
          <button onClick={cancel}>Отменить</button>
        )}
      </div>

      {error && <div className="error">Ошибка: {error}</div>}

      {run && (
        <>
          <div className="progress-wrap">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
            <div className="progress-meta">
              <span>
                статус: <b>{run.status}</b>
              </span>
              <span>
                {run.processed}/{run.total} ({pct}%)
              </span>
              <span>good {run.good}</span>
              <span>bad {run.bad}</span>
              <span>review {run.review}</span>
              <span>errors {run.errors}</span>
              {run.est_cost > 0 && <span>≈ ${run.est_cost.toFixed(4)}</span>}
            </div>
          </div>

          <div className="seg bucket-seg">
            {BUCKETS.map((b) => (
              <button
                key={b.id}
                className={tab === b.id ? "on" : ""}
                onClick={() => setTab(b.id)}
              >
                {b.label} · {buckets[b.id]?.length ?? 0}
              </button>
            ))}
          </div>

          <div className="actions bucket-actions">
            <button onClick={() => copyBucket(tab)}>Выделить всё и скопировать</button>
            <button onClick={() => download(tab, "csv")}>Экспорт CSV</button>
            <button onClick={() => download(tab, "txt")}>Экспорт TXT</button>
          </div>

          <BucketTable rows={buckets[tab] ?? []} bucket={tab} />
        </>
      )}
    </div>
  );
}
