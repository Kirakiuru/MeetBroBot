import WebApp from "@twa-dev/sdk";

const BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": WebApp.initData,
      ...options.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────

export interface Slot {
  id: number;
  day_of_week: number | null;
  start_time: string; // HH:MM
  end_time: string;
  is_recurring: boolean;
  specific_date: string | null; // YYYY-MM-DD
}

export interface SlotCreate {
  day_of_week?: number | null;
  start_time: string;
  end_time: string;
  is_recurring?: boolean;
  specific_date?: string | null;
}

export interface Meeting {
  id: number;
  title: string;
  status: string;
  proposed_datetime: string | null;
  location: string | null;
  creator_name: string;
  vote_deadline: string | null;
  votes: Record<string, string[]>;
  my_vote: string | null;
}

export interface Settings {
  schedule_remind: boolean;
  schedule_remind_day: number;
  schedule_remind_hour: number;
}

// ── Schedule ───────────────────────────────────────

export const getSlots = () => request<Slot[]>("/schedule");

export const createSlot = (data: SlotCreate) =>
  request<Slot>("/schedule", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const deleteSlot = (id: number) =>
  request<{ ok: boolean }>(`/schedule/${id}`, { method: "DELETE" });

export const clearSlots = () =>
  request<{ ok: boolean; deleted: number }>("/schedule", { method: "DELETE" });

// ── Meetings ───────────────────────────────────────

export const getMeetings = () => request<Meeting[]>("/meetings");

export const voteMeeting = (meetingId: number, choice: string) =>
  request<{ ok: boolean; choice: string; changed: boolean }>(
    `/meetings/${meetingId}/vote`,
    { method: "POST", body: JSON.stringify({ choice }) }
  );

// ── Settings ───────────────────────────────────────

export const getSettings = () => request<Settings>("/settings");

export const updateSettings = (data: Partial<Settings>) =>
  request<Settings>("/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
