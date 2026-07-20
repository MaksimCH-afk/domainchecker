import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { AnalyzeResponse, Config, ResultRow, Tier, UploadStats } from "../types";
import { setPath } from "../configUtil";
import { SummaryBar } from "./SummaryBar";
import { ResultsTable } from "./ResultsTable";

const ALL_TIERS: Tier[] = ["A", "B", "C", "Review", "Rejected"];

interface Props {
  config: Config;
  setConfig: (c: Config) => void;
  onBridge: (targets: string[]) => void;
}

export function AhrefsView({ config, setConfig, onBridge }: Props) {
  const [stats, setStats] = useState<UploadStats | null>(null);
  const [resp, setResp] = useState<AnalyzeResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeRaw, setIncludeRaw] = useState(false);

  // filters (view only — do not change classification)
  const [tierFilter, setTierFilter] = useState<Set<Tier>>(new Set(ALL_TIERS));
  const [search, setSearch] = useState("");
  const [bridgeTiers, setBridgeTiers] = useState<Set<Tier>>(
    new Set<Tier>(["A", "B", "C"])
  );

  const debounceRef = useRef<number | null>(null);

  // §9: recompute on config change WITHOUT re-upload (cheap pure function).
  useEffect(() => {
    if (!stats) return;
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      runAnalyze(stats.dataset_id);
    }, 250);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, stats]);

  async function runAnalyze(datasetId: string) {
    setBusy(true);
    setError(null);
    try {
      setResp(await api.analyze(datasetId, config));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File) {
    setBusy(true);
    setError(null);
    setResp(null);
    try {
      const s = await api.uploadFile(file);
      setStats(s);
      await runAnalyze(s.dataset_id);
    } catch (e: any) {
      setError(e.message);
      setStats(null);
    } finally {
      setBusy(false);
    }
  }

  const filtered = useMemo(() => {
    if (!resp) return [] as ResultRow[];
    const q = search.trim().toLowerCase();
    return resp.rows.filter(
      (r) =>
        tierFilter.has(r.tier) &&
        (q === "" || r.Target.toLowerCase().includes(q))
    );
  }, [resp, tierFilter, search]);

  function toggle<T>(set: Set<T>, v: T): Set<T> {
    const n = new Set(set);
    n.has(v) ? n.delete(v) : n.add(v);
    return n;
  }

  async function download(format: "csv" | "txt") {
    if (!stats) return;
    const blob = await api.exportBlob(stats.dataset_id, config, format, includeRaw);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ahrefs_filter.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyTargets() {
    const text = filtered.map((r) => r.Target).join("\n");
    await navigator.clipboard.writeText(text);
  }

  async function bridge() {
    if (!stats) return;
    const tiers = ALL_TIERS.filter((t) => bridgeTiers.has(t));
    const { targets } = await api.bridgeTargets(stats.dataset_id, config, tiers);
    onBridge(targets);
  }

  return (
    <div className="view">
      <header className="view-head">
        <h1>Ahrefs-фильтр · количественный гейт</h1>
        <p className="muted">
          Загрузите выгрузку Ahrefs Batch Analysis (UTF-16/таб или UTF-8/запятая).
          Отсев мусора, композитный скор, тиры и флаги. Пороги — в «Настройках»,
          пересчёт мгновенный без повторной загрузки.
        </p>
      </header>

      <UploadArea onFile={onUpload} stats={stats} busy={busy} />

      {error && <div className="error">Ошибка: {error}</div>}
      {resp?.warnings?.length ? (
        <div className="warn">
          {resp.warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      ) : null}

      {resp && (
        <>
          <SummaryBar summary={resp.summary} />

          {/* Inline tier calibration — the thresholds are a business decision. */}
          <div className="calibrate">
            <span className="calibrate-label">Границы тиров:</span>
            {(["A_min", "B_min", "C_min"] as const).map((k) => (
              <label key={k} className="mini-field">
                {k}
                <input
                  type="number"
                  value={config.tiers[k]}
                  onChange={(e) =>
                    setConfig(setPath(config, `tiers.${k}`, Number(e.target.value)))
                  }
                />
              </label>
            ))}
            {busy && <span className="recompute">пересчёт…</span>}
          </div>

          <div className="toolbar">
            <div className="filters">
              {ALL_TIERS.map((t) => (
                <button
                  key={t}
                  className={`filter-chip ${tierFilter.has(t) ? "on" : ""}`}
                  onClick={() => setTierFilter(toggle(tierFilter, t))}
                >
                  {t}
                </button>
              ))}
              <input
                className="search"
                placeholder="поиск по домену…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="actions">
              <label className="raw-toggle">
                <input
                  type="checkbox"
                  checked={includeRaw}
                  onChange={(e) => setIncludeRaw(e.target.checked)}
                />
                passthrough колонок Ahrefs
              </label>
              <button onClick={copyTargets}>Копировать домены</button>
              <button onClick={() => download("csv")}>Экспорт CSV</button>
              <button onClick={() => download("txt")}>Экспорт TXT</button>
            </div>
          </div>

          <div className="bridge">
            <span className="bridge-label">Мост → Классификатор по имени:</span>
            {ALL_TIERS.filter((t) => t !== "Rejected").map((t) => (
              <button
                key={t}
                className={`filter-chip ${bridgeTiers.has(t) ? "on" : ""}`}
                onClick={() => setBridgeTiers(toggle(bridgeTiers, t))}
              >
                {t}
              </button>
            ))}
            <button className="primary" onClick={bridge}>
              Отправить выбранные тиры в Классификатор →
            </button>
          </div>

          <div className="count-line">
            Показано {filtered.length} из {resp.rows.length}
          </div>
          <ResultsTable rows={filtered} />
        </>
      )}
    </div>
  );
}

function UploadArea({
  onFile,
  stats,
  busy,
}: {
  onFile: (f: File) => void;
  stats: UploadStats | null;
  busy: boolean;
}) {
  const [drag, setDrag] = useState(false);
  return (
    <div
      className={`upload ${drag ? "drag" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
      }}
    >
      <input
        id="file"
        type="file"
        accept=".csv,.txt,.tsv"
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
      />
      <label htmlFor="file" className="upload-cta">
        {busy ? "Обработка…" : "Перетащите файл выгрузки или нажмите, чтобы выбрать"}
      </label>
      {stats && (
        <div className="upload-stats">
          <b>{stats.filename ?? "dataset"}</b> · распознано {stats.recognized} ·
          дублей убрано {stats.duplicates_removed} · всего строк {stats.total_rows}
        </div>
      )}
    </div>
  );
}
