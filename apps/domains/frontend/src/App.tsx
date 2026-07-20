import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Config } from "./types";
import { AhrefsView } from "./ahrefs/AhrefsView";
import { SettingsView } from "./settings/SettingsView";
import { ClassifierView } from "./classifier/ClassifierView";
import { HistoryView } from "./history/HistoryView";

type Drawer = null | "settings" | "history";

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  // The bridge: Targets handed from Part 1 (Ahrefs) to Part 2 (classifier).
  const [bridgedTargets, setBridgedTargets] = useState<string[]>([]);
  const [drawer, setDrawer] = useState<Drawer>(null);
  const classifierRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getDefaultConfig().then(setConfig).catch(() => setConfig({}));
  }, []);

  function sendToClassifier(targets: string[]) {
    setBridgedTargets(targets);
    // Both tools live in one window — just scroll down to the classifier.
    classifierRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (!config) return <div className="loading">Загрузка конфигурации…</div>;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">◧</span>
          <div>
            <div className="brand-title">monopanel · Домены</div>
            <div className="brand-sub">
              Единый пайплайн отбора: авторитет/спам&nbsp;→&nbsp;имя
            </div>
          </div>
        </div>
        <div className="topbar-actions">
          <button onClick={() => setDrawer("settings")}>⚙ Настройки</button>
          <button onClick={() => setDrawer("history")}>🕘 История и логи</button>
        </div>
      </header>

      {/* Both tools in ONE window — no tab switching. */}
      <main className="content">
        <section className="tool-section">
          <AhrefsView config={config} setConfig={setConfig} onBridge={sendToClassifier} />
        </section>

        <div className="tool-divider">
          <span>↓ Мост: домены из тиров выше можно отправить в классификатор ↓</span>
        </div>

        <section className="tool-section" ref={classifierRef}>
          <ClassifierView bridgedTargets={bridgedTargets} />
        </section>
      </main>

      {drawer && (
        <div className="drawer-overlay" onClick={() => setDrawer(null)}>
          <aside className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <span>{drawer === "settings" ? "Настройки" : "История и логи"}</span>
              <button className="drawer-close" onClick={() => setDrawer(null)}>
                ✕
              </button>
            </div>
            <div className="drawer-body">
              {drawer === "settings" ? (
                <SettingsView config={config} setConfig={setConfig} />
              ) : (
                <HistoryView />
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
