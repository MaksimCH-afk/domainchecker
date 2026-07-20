import { useEffect, useState } from "react";
import { api } from "../api";
import type { Config } from "../types";
import { setPath } from "../configUtil";

interface Props {
  config: Config;
  setConfig: (c: Config) => void;
}

// One numeric field bound to a dotted config path.
function Num({
  config,
  setConfig,
  path,
  label,
  step = 1,
}: Props & { path: string; label: string; step?: number }) {
  const value = path.split(".").reduce((o: any, k) => o?.[k], config);
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => setConfig(setPath(config, path, Number(e.target.value)))}
      />
    </label>
  );
}

// Comma-separated list bound to a config path (geo allowlist / cjk set).
function ListField({
  config,
  setConfig,
  path,
  label,
  placeholder,
}: Props & { path: string; label: string; placeholder?: string }) {
  const arr: string[] = path.split(".").reduce((o: any, k) => o?.[k], config) ?? [];
  return (
    <label className="field wide">
      <span>{label}</span>
      <input
        type="text"
        placeholder={placeholder}
        value={arr.join(", ")}
        onChange={(e) =>
          setConfig(
            setPath(
              config,
              path,
              e.target.value
                .split(",")
                .map((s) => s.trim().toLowerCase())
                .filter(Boolean)
            )
          )
        }
      />
    </label>
  );
}

export function SettingsView({ config, setConfig }: Props) {
  const [section, setSection] = useState<"scoring" | "ai">("scoring");
  const [presets, setPresets] = useState<string[]>([]);
  const [presetName, setPresetName] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.listPresets().then(setPresets).catch(() => {});
  }, []);

  useEffect(() => {
    api
      .validateConfig(config)
      .then((r) => setWarnings(r.warnings))
      .catch(() => {});
  }, [config]);

  async function reload() {
    setPresets(await api.listPresets());
  }

  async function save() {
    if (!presetName.trim()) return;
    await api.savePreset(presetName.trim(), config);
    setMsg(`Пресет «${presetName.trim()}» сохранён.`);
    setPresetName("");
    await reload();
  }

  async function load(name: string) {
    setConfig(await api.getPreset(name));
    setMsg(`Пресет «${name}» загружен.`);
  }

  async function resetDefaults() {
    setConfig(await api.getDefaultConfig());
    setMsg("Сброшено к значениям по умолчанию.");
  }

  return (
    <div className="view">
      <header className="view-head">
        <h1>Настройки модуля «Домены»</h1>
        <p className="muted">
          Одна вкладка на обе части пайплайна: <b>Scoring</b> — параметры
          количественного Ahrefs-фильтра; <b>AI</b> — провайдер и прогон
          классификатора по имени (Часть 2).
        </p>
      </header>

      <div className="seg">
        <button
          className={section === "scoring" ? "on" : ""}
          onClick={() => setSection("scoring")}
        >
          Scoring (Ahrefs)
        </button>
        <button
          className={section === "ai" ? "on" : ""}
          onClick={() => setSection("ai")}
        >
          AI (Классификатор)
        </button>
      </div>

      {warnings.length > 0 && (
        <div className="warn">
          {warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      )}
      {msg && <div className="ok">{msg}</div>}

      {section === "scoring" ? (
        <ScoringSettings config={config} setConfig={setConfig} />
      ) : (
        <AiSettingsStub />
      )}

      <div className="presets">
        <h3>Пресеты (профиль под нишу/гео)</h3>
        <div className="preset-row">
          <input
            placeholder="имя пресета…"
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
          />
          <button onClick={save}>Сохранить</button>
          <button onClick={resetDefaults}>Сбросить к дефолтам</button>
        </div>
        <div className="preset-list">
          {presets.length === 0 && <span className="muted">пока нет сохранённых</span>}
          {presets.map((p) => (
            <span key={p} className="preset-tag">
              <button onClick={() => load(p)}>{p}</button>
              <button
                className="x"
                onClick={async () => {
                  await api.deletePreset(p);
                  await reload();
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScoringSettings({ config, setConfig }: Props) {
  const p = { config, setConfig };
  return (
    <div className="settings-grid">
      <section className="card">
        <h3>Веса скора (§6)</h3>
        <div className="fields">
          <Num {...p} path="score.weights.dr" label="dr" step={0.01} />
          <Num {...p} path="score.weights.rd_fol" label="rd_fol" step={0.01} />
          <Num {...p} path="score.weights.subnets" label="subnets" step={0.01} />
          <Num {...p} path="score.weights.org" label="org" step={0.01} />
          <Num {...p} path="score.weights.spam_pen" label="spam_pen" step={0.01} />
        </div>
      </section>

      <section className="card">
        <h3>Нормализация (caps)</h3>
        <div className="fields">
          <Num {...p} path="score.caps.dr" label="dr" />
          <Num {...p} path="score.caps.rd_fol" label="rd_fol" />
          <Num {...p} path="score.caps.subnets" label="subnets" />
          <Num {...p} path="score.caps.org" label="org" />
          <Num {...p} path="score.spam_pen.bl_rd_base" label="spam_pen base" step={0.1} />
          <Num {...p} path="score.spam_pen.cap" label="spam_pen cap" />
        </div>
      </section>

      <section className="card">
        <h3>Границы тиров (§7)</h3>
        <div className="fields">
          <Num {...p} path="tiers.A_min" label="A_min" />
          <Num {...p} path="tiers.B_min" label="B_min" />
          <Num {...p} path="tiers.C_min" label="C_min" />
        </div>
      </section>

      <section className="card">
        <h3>Отсев · dead / spam_blast (§5)</h3>
        <div className="fields">
          <Num {...p} path="reject.spam_blast.bl_rd_min" label="spam bl_rd_min" step={0.1} />
          <Num {...p} path="reject.spam_blast.bl_rd_max" label="spam bl_rd_max" step={0.1} />
          <Num {...p} path="reject.spam_blast.rd_all_min" label="spam rd_all_min" />
        </div>
      </section>

      <section className="card">
        <h3>Отсев · thin / burn_hacked (§5)</h3>
        <div className="fields">
          <Num {...p} path="reject.thin.rd_fol_max" label="thin rd_fol_max" />
          <Num {...p} path="reject.thin.dr_max" label="thin dr_max" />
          <Num {...p} path="reject.burn_hacked.burn_min" label="burn_min" />
          <Num {...p} path="reject.burn_hacked.dr_max" label="burn dr_max" />
        </div>
      </section>

      <section className="card">
        <h3>Флаги (§8)</h3>
        <div className="fields">
          <Num {...p} path="flags.spam_floor.rd_all_min" label="spam_floor rd_all_min" />
          <Num {...p} path="flags.spam_floor.rd_all_max" label="spam_floor rd_all_max" />
          <Num {...p} path="flags.spam_floor.fol_share_max" label="fol_share_max" step={0.05} />
          <Num {...p} path="flags.burn.burn_min" label="flag burn_min" />
        </div>
        <ListField {...p} path="flags.geo.allowlist" label="geo allowlist" placeholder="напр. au, nz" />
        <ListField {...p} path="flags.cjk.set" label="cjk set" placeholder="cn, jp, kr, tw, hk, mo" />
        <label className="field wide">
          <span>cjk action</span>
          <select
            value={config.flags.cjk.action}
            onChange={(e) => setConfig(setPath(config, "flags.cjk.action", e.target.value))}
          >
            <option value="review">review (переопределяет тир)</option>
            <option value="reject">reject (жёстко режет)</option>
            <option value="flag_only">flag_only (только пометка)</option>
          </select>
        </label>
      </section>
    </div>
  );
}

function AiSettingsStub() {
  return (
    <div className="card ai-stub">
      <h3>AI · Классификатор по имени (Часть 2)</h3>
      <p className="muted">
        Появится в следующей итерации. Здесь будут: провайдер (OpenAI / OpenRouter),
        API-ключи (маскируются, не в логах), модель (список + ручной ввод),
        Batch API (−50%), temperature, размер пакета, concurrency, ретраи,
        порог confidence и оценка стоимости.
      </p>
      <div className="fields disabled">
        <label className="field">
          <span>Провайдер</span>
          <select disabled>
            <option>OpenAI</option>
            <option>OpenRouter</option>
          </select>
        </label>
        <label className="field">
          <span>Модель</span>
          <input disabled placeholder="gpt-5.4-mini" />
        </label>
        <label className="field">
          <span>Порог confidence</span>
          <input disabled placeholder="0.7" />
        </label>
      </div>
    </div>
  );
}
