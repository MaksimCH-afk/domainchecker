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
        <AiSettings />
      )}

      {section === "scoring" && (
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
      )}
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

const MODEL_SUGGESTIONS = ["gpt-5.4-mini", "gpt-5-nano", "gpt-4.1-nano"];

function AiSettings() {
  const [s, setS] = useState<any | null>(null);
  const [keysSet, setKeysSet] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [keyInputs, setKeyInputs] = useState<{ openai: string; openrouter: string }>({
    openai: "",
    openrouter: "",
  });

  useEffect(() => {
    api.getAiSettings().then((r) => {
      setS(r.settings);
      setKeysSet(r.settings.api_keys_set || {});
    });
  }, []);

  if (!s) return <div className="muted">Загрузка настроек AI…</div>;

  const set = (k: string, v: any) => setS({ ...s, [k]: v });

  async function save() {
    const patch: any = { ...s };
    delete patch.api_keys_set;
    // Only send non-empty keys so blanks leave existing keys untouched.
    const api_keys: any = {};
    if (keyInputs.openai) api_keys.openai = keyInputs.openai;
    if (keyInputs.openrouter) api_keys.openrouter = keyInputs.openrouter;
    if (Object.keys(api_keys).length) patch.api_keys = api_keys;
    const r = await api.saveAiSettings(patch);
    setS(r.settings);
    setKeysSet(r.settings.api_keys_set || {});
    setKeyInputs({ openai: "", openrouter: "" });
    setMsg("Настройки AI сохранены.");
  }

  return (
    <div className="settings-grid">
      <section className="card">
        <h3>Провайдер и модель</h3>
        <div className="fields">
          <label className="field">
            <span>Провайдер</span>
            <select value={s.provider} onChange={(e) => set("provider", e.target.value)}>
              <option value="openai">OpenAI (основной)</option>
              <option value="openrouter">OpenRouter (резерв)</option>
              <option value="mock">Mock (офлайн-демо)</option>
            </select>
          </label>
          <label className="field">
            <span>Модель</span>
            <input
              list="models"
              value={s.model}
              onChange={(e) => set("model", e.target.value)}
            />
            <datalist id="models">
              {MODEL_SUGGESTIONS.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </label>
          <label className="field wide">
            <span>base_url (необязательно, OpenAI-совместимый)</span>
            <input value={s.base_url} onChange={(e) => set("base_url", e.target.value)} />
          </label>
          <label className="field wide raw-toggle">
            <input
              type="checkbox"
              checked={s.batch_api}
              onChange={(e) => set("batch_api", e.target.checked)}
            />
            Batch API (−50% к стоимости)
          </label>
        </div>
      </section>

      <section className="card">
        <h3>API-ключи (маскируются, не в логах)</h3>
        <div className="fields">
          <label className="field wide">
            <span>OpenAI {keysSet.openai ? "· задан ✓" : "· не задан"}</span>
            <input
              type="password"
              placeholder={keysSet.openai ? "•••••••• (оставьте пустым)" : "sk-…"}
              value={keyInputs.openai}
              onChange={(e) => setKeyInputs({ ...keyInputs, openai: e.target.value })}
            />
          </label>
          <label className="field wide">
            <span>OpenRouter {keysSet.openrouter ? "· задан ✓" : "· не задан"}</span>
            <input
              type="password"
              placeholder={keysSet.openrouter ? "•••••••• (оставьте пустым)" : "sk-or-…"}
              value={keyInputs.openrouter}
              onChange={(e) => setKeyInputs({ ...keyInputs, openrouter: e.target.value })}
            />
          </label>
        </div>
      </section>

      <section className="card">
        <h3>Параметры прогона</h3>
        <div className="fields">
          <label className="field">
            <span>temperature</span>
            <input type="number" step={0.1} value={s.temperature}
              onChange={(e) => set("temperature", Number(e.target.value))} />
          </label>
          <label className="field">
            <span>batch_size</span>
            <input type="number" value={s.batch_size}
              onChange={(e) => set("batch_size", Number(e.target.value))} />
          </label>
          <label className="field">
            <span>concurrency</span>
            <input type="number" value={s.concurrency}
              onChange={(e) => set("concurrency", Number(e.target.value))} />
          </label>
          <label className="field">
            <span>max_retries</span>
            <input type="number" value={s.max_retries}
              onChange={(e) => set("max_retries", Number(e.target.value))} />
          </label>
          <label className="field">
            <span>порог confidence</span>
            <input type="number" step={0.05} value={s.confidence_threshold}
              onChange={(e) => set("confidence_threshold", Number(e.target.value))} />
          </label>
        </div>
      </section>

      <section className="card">
        <h3>Стоимость (цена за 1K токенов)</h3>
        <div className="fields">
          <label className="field">
            <span>вход $/1K</span>
            <input type="number" step={0.0001} value={s.price_in_per_1k}
              onChange={(e) => set("price_in_per_1k", Number(e.target.value))} />
          </label>
          <label className="field">
            <span>выход $/1K</span>
            <input type="number" step={0.0001} value={s.price_out_per_1k}
              onChange={(e) => set("price_out_per_1k", Number(e.target.value))} />
          </label>
        </div>
      </section>

      <div className="ai-save">
        <button className="primary" onClick={save}>Сохранить настройки AI</button>
        {msg && <span className="ok inline">{msg}</span>}
      </div>
    </div>
  );
}
