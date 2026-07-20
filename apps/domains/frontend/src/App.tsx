import { useEffect, useState } from "react";
import { api } from "./api";
import type { Config } from "./types";
import { AhrefsView } from "./ahrefs/AhrefsView";
import { SettingsView } from "./settings/SettingsView";
import { ClassifierView } from "./classifier/ClassifierView";
import { HistoryView } from "./history/HistoryView";

type Tab = "ahrefs" | "classifier" | "settings" | "history";

const TABS: { id: Tab; label: string; hint: string }[] = [
  { id: "ahrefs", label: "Ahrefs-фильтр", hint: "Количественный гейт" },
  { id: "classifier", label: "Классификатор", hint: "Гейт по имени" },
  { id: "settings", label: "Настройки", hint: "Scoring + AI" },
  { id: "history", label: "История и логи", hint: "" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("ahrefs");
  const [config, setConfig] = useState<Config | null>(null);
  // The bridge: Targets handed from Part 1 (Ahrefs) to Part 2 (classifier).
  const [bridgedTargets, setBridgedTargets] = useState<string[]>([]);

  useEffect(() => {
    api.getDefaultConfig().then(setConfig).catch(() => setConfig({}));
  }, []);

  function sendToClassifier(targets: string[]) {
    setBridgedTargets(targets);
    setTab("classifier");
  }

  if (!config) return <div className="loading">Загрузка конфигурации…</div>;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◧</span>
          <div>
            <div className="brand-title">monopanel</div>
            <div className="brand-sub">apps / domains</div>
          </div>
        </div>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-item ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              <span>{t.label}</span>
              {t.hint && <em>{t.hint}</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          Единый пайплайн отбора доменов:
          <br /> авторитет/спам → имя.
        </div>
      </aside>

      <main className="content">
        {tab === "ahrefs" && (
          <AhrefsView
            config={config}
            setConfig={setConfig}
            onBridge={sendToClassifier}
          />
        )}
        {tab === "classifier" && (
          <ClassifierView bridgedTargets={bridgedTargets} />
        )}
        {tab === "settings" && (
          <SettingsView config={config} setConfig={setConfig} />
        )}
        {tab === "history" && <HistoryView />}
      </main>
    </div>
  );
}
