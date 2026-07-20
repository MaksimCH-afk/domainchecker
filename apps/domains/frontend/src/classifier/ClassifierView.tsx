import { useEffect, useState } from "react";

// Part 2 lands here next iteration. For now it fully realizes the BRIDGE:
// Targets that survived the Ahrefs quantitative gate arrive pre-filled in the
// textarea, ready to run through the name classifier.
export function ClassifierView({ bridgedTargets }: { bridgedTargets: string[] }) {
  const [text, setText] = useState("");

  useEffect(() => {
    if (bridgedTargets.length) setText(bridgedTargets.join("\n"));
  }, [bridgedTargets]);

  const lines = text.split("\n").map((s) => s.trim()).filter(Boolean);

  return (
    <div className="view">
      <header className="view-head">
        <h1>Классификатор по имени · качественный гейт</h1>
        <p className="muted">
          Часть 2: нейросеть (OpenAI/OpenRouter) судит домен по названию —
          pharma/casino/adult/скам/язык — и раскладывает good / bad / на проверку.
          Оркестрация (батчи, ретраи, схема, история) появится следующей итерацией.
        </p>
      </header>

      {bridgedTargets.length > 0 && (
        <div className="bridge-note">
          ↳ Получено из Ahrefs-фильтра: <b>{bridgedTargets.length}</b> доменов
          прошедших тиров. Мост между двумя частями работает.
        </div>
      )}

      <label className="field wide">
        <span>Домены (по одному в строке)</span>
        <textarea
          rows={14}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="example.com&#10;anothersite.net"
        />
      </label>
      <div className="count-line">Распознано строк: {lines.length}</div>

      <button className="primary" disabled title="Появится в Части 2">
        Проверить (Часть 2 — в разработке)
      </button>
    </div>
  );
}
