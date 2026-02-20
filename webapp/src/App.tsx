import { useState, useEffect } from "react";
import { Calendar } from "./components/Calendar";
import { Meetings } from "./components/Meetings";
import { Settings } from "./components/Settings";
import { useTelegram } from "./hooks/useTelegram";

type Tab = "schedule" | "meetings" | "settings";

export default function App() {
  const [tab, setTab] = useState<Tab>("schedule");
  const { ready, expand } = useTelegram();

  useEffect(() => {
    ready();
    expand();
  }, []);

  return (
    <>
      {tab === "schedule" && <Calendar />}
      {tab === "meetings" && <Meetings />}
      {tab === "settings" && <Settings />}

      <nav className="nav-tabs">
        <button
          className={`nav-tab${tab === "schedule" ? " active" : ""}`}
          onClick={() => setTab("schedule")}
        >
          <span className="icon">📅</span>
          <span>Расписание</span>
        </button>
        <button
          className={`nav-tab${tab === "meetings" ? " active" : ""}`}
          onClick={() => setTab("meetings")}
        >
          <span className="icon">🎯</span>
          <span>Встречи</span>
        </button>
        <button
          className={`nav-tab${tab === "settings" ? " active" : ""}`}
          onClick={() => setTab("settings")}
        >
          <span className="icon">⚙️</span>
          <span>Настройки</span>
        </button>
      </nav>
    </>
  );
}
