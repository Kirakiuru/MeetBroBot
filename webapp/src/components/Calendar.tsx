import { useEffect, useState, useCallback } from "react";
import { format, addDays, startOfWeek, isSameDay } from "date-fns";
import { ru } from "date-fns/locale";
import { getSlots, createSlot, deleteSlot } from "../api";
import type { Slot } from "../api";
import { useTelegram } from "../hooks/useTelegram";

const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23];

export function Calendar() {
  const { haptic } = useTelegram();
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);
  const [saving, setSaving] = useState<string | null>(null);

  const today = new Date();
  const weekStart = startOfWeek(addDays(today, weekOffset * 7), {
    weekStartsOn: 1,
  });

  const dates = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const fetchSlots = useCallback(async () => {
    try {
      const data = await getSlots();
      setSlots(data);
    } catch (e) {
      console.error("Failed to load slots", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSlots();
  }, [fetchSlots]);

  // Check if a cell is active (has a slot)
  const isActive = (date: Date, hour: number): Slot | undefined => {
    const dateStr = format(date, "yyyy-MM-dd");
    const dayOfWeek = (date.getDay() + 6) % 7; // 0=Mon

    return slots.find((s) => {
      const startH = parseInt(s.start_time.split(":")[0]);
      const endH = parseInt(s.end_time.split(":")[0]);

      if (s.specific_date === dateStr) {
        return startH <= hour && hour < endH;
      }
      if (s.is_recurring && s.day_of_week === dayOfWeek) {
        return startH <= hour && hour < endH;
      }
      return false;
    });
  };

  const toggleCell = async (date: Date, hour: number) => {
    const cellKey = `${format(date, "yyyy-MM-dd")}-${hour}`;
    if (saving) return;
    setSaving(cellKey);

    try {
      const existingSlot = isActive(date, hour);

      if (existingSlot) {
        // Delete
        await deleteSlot(existingSlot.id);
        haptic?.impactOccurred("light");
      } else {
        // Create 1-hour slot for this specific date
        const startTime = `${hour.toString().padStart(2, "0")}:00`;
        const endTime = `${(hour + 1).toString().padStart(2, "0")}:00`;
        await createSlot({
          start_time: startTime,
          end_time: endTime,
          is_recurring: false,
          specific_date: format(date, "yyyy-MM-dd"),
        });
        haptic?.impactOccurred("medium");
      }

      await fetchSlots();
    } catch (e) {
      console.error("Toggle failed", e);
    } finally {
      setSaving(null);
    }
  };

  // Quick presets
  const applyPreset = async (
    preset: "morning" | "day" | "evening" | "all"
  ) => {
    const ranges: Record<string, [number, number]> = {
      morning: [8, 12],
      day: [12, 18],
      evening: [18, 23],
      all: [8, 23],
    };
    const [start, end] = ranges[preset];

    setSaving("preset");
    try {
      for (const date of dates) {
        for (let h = start; h < end; h++) {
          if (!isActive(date, h)) {
            const startTime = `${h.toString().padStart(2, "0")}:00`;
            const endTime = `${(h + 1).toString().padStart(2, "0")}:00`;
            await createSlot({
              start_time: startTime,
              end_time: endTime,
              is_recurring: false,
              specific_date: format(date, "yyyy-MM-dd"),
            });
          }
        }
      }
      haptic?.notificationOccurred("success");
      await fetchSlots();
    } catch (e) {
      console.error("Preset failed", e);
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return (
      <div className="loader">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-title">📅 Расписание</div>

      {/* Week navigation */}
      <div className="week-nav">
        <button
          className="week-nav-btn"
          onClick={() => setWeekOffset((w) => w - 1)}
        >
          ← 
        </button>
        <span className="week-nav-label">
          {format(dates[0], "d MMM", { locale: ru })} –{" "}
          {format(dates[6], "d MMM", { locale: ru })}
        </span>
        <button
          className="week-nav-btn"
          onClick={() => setWeekOffset((w) => w + 1)}
        >
           →
        </button>
      </div>

      {/* Quick presets */}
      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        <button className="btn btn-sm btn-outline" onClick={() => applyPreset("morning")}>
          🌅 Утро
        </button>
        <button className="btn btn-sm btn-outline" onClick={() => applyPreset("day")}>
          ☀️ День
        </button>
        <button className="btn btn-sm btn-outline" onClick={() => applyPreset("evening")}>
          🌙 Вечер
        </button>
        <button className="btn btn-sm btn-outline" onClick={() => applyPreset("all")}>
          📅 Вся неделя
        </button>
      </div>

      {/* Calendar grid */}
      <div className="calendar">
        {/* Day headers */}
        <div className="calendar-header">
          <div className="calendar-header-cell"></div>
          {dates.map((d, i) => (
            <div
              key={i}
              className="calendar-header-cell"
              style={isSameDay(d, today) ? { color: "var(--tg-btn)" } : {}}
            >
              <div>{DAYS[i]}</div>
              <div style={{ fontSize: 11, fontWeight: 400 }}>
                {format(d, "d")}
              </div>
            </div>
          ))}
        </div>

        {/* Time rows */}
        {HOURS.map((hour) => (
          <div className="calendar-row" key={hour}>
            <div className="calendar-time">{hour}:00</div>
            {dates.map((date, dayIdx) => {
              const active = !!isActive(date, hour);
              const key = `${format(date, "yyyy-MM-dd")}-${hour}`;
              return (
                <button
                  key={dayIdx}
                  className={`calendar-cell${active ? " active" : ""}`}
                  onClick={() => toggleCell(date, hour)}
                  disabled={saving !== null}
                  style={saving === key ? { opacity: 0.5 } : {}}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Existing slots summary */}
      {slots.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="card-subtitle">
            Всего слотов: {slots.length}
          </div>
        </div>
      )}
    </div>
  );
}
