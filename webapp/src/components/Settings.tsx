import { useEffect, useState, useCallback } from "react";
import { getSettings, updateSettings } from "../api";
import type { Settings as SettingsType } from "../api";
import { useTelegram } from "../hooks/useTelegram";

const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const HOURS = [9, 12, 15, 18, 21];

export function Settings() {
  const { haptic, user } = useTelegram();
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await getSettings();
      setSettings(data);
    } catch (e) {
      console.error("Failed to load settings", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const update = async (patch: Partial<SettingsType>) => {
    try {
      const updated = await updateSettings(patch);
      setSettings(updated);
      haptic?.impactOccurred("light");
    } catch (e) {
      console.error("Update failed", e);
    }
  };

  if (loading || !settings) {
    return (
      <div className="loader">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-title">⚙️ Настройки</div>

      <div className="card">
        <div className="card-title">📅 Напоминание о расписании</div>
        <div className="card-subtitle">
          Еженедельное напоминание заполнить расписание, если на неделю нет
          слотов.
        </div>

        {/* Toggle */}
        <div className="settings-row">
          <span className="settings-label">Включено</span>
          <button
            className={`toggle${settings.schedule_remind ? " on" : ""}`}
            onClick={() => update({ schedule_remind: !settings.schedule_remind })}
          />
        </div>

        {settings.schedule_remind && (
          <>
            {/* Day picker */}
            <div style={{ marginTop: 12 }}>
              <div className="card-subtitle" style={{ marginBottom: 6 }}>
                День недели:
              </div>
              <div className="chip-group">
                {DAYS.map((name, i) => (
                  <button
                    key={i}
                    className={`chip${settings.schedule_remind_day === i ? " active" : ""}`}
                    onClick={() => update({ schedule_remind_day: i })}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>

            {/* Hour picker */}
            <div style={{ marginTop: 12 }}>
              <div className="card-subtitle" style={{ marginBottom: 6 }}>
                Время:
              </div>
              <div className="chip-group">
                {HOURS.map((h) => (
                  <button
                    key={h}
                    className={`chip${settings.schedule_remind_hour === h ? " active" : ""}`}
                    onClick={() => update({ schedule_remind_hour: h })}
                  >
                    {h}:00
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* User info */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">👤 Профиль</div>
        <div className="card-subtitle">
          {user?.first_name} {user?.last_name || ""}
          {user?.username ? ` · @${user.username}` : ""}
        </div>
      </div>

      {/* About */}
      <div className="card" style={{ marginTop: 8 }}>
        <div className="card-title">ℹ️ О боте</div>
        <div className="card-subtitle">
          MeetBroBot v0.2 — организатор тусовок.
          <br />
          <a
            href="https://github.com/Kirakiuru/MeetBroBot"
            style={{ color: "var(--tg-link)" }}
          >
            GitHub
          </a>{" "}
          · @kikir_kir · @KirillFain
        </div>
      </div>
    </div>
  );
}
