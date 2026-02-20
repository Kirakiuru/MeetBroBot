import { useEffect, useState, useCallback } from "react";
import { getMeetings, voteMeeting } from "../api";
import type { Meeting } from "../api";
import { useTelegram } from "../hooks/useTelegram";

export function Meetings() {
  const { haptic } = useTelegram();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [votingId, setVotingId] = useState<number | null>(null);

  const fetchMeetings = useCallback(async () => {
    try {
      const data = await getMeetings();
      setMeetings(data);
    } catch (e) {
      console.error("Failed to load meetings", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  const handleVote = async (meetingId: number, choice: string) => {
    setVotingId(meetingId);
    try {
      await voteMeeting(meetingId, choice);
      haptic?.impactOccurred("medium");
      await fetchMeetings();
    } catch (e) {
      console.error("Vote failed", e);
      haptic?.notificationOccurred("error");
    } finally {
      setVotingId(null);
    }
  };

  const formatDate = (iso: string | null): string => {
    if (!iso) return "Без даты";
    const d = new Date(iso);
    return d.toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDeadline = (iso: string | null): string | null => {
    if (!iso) return null;
    const d = new Date(iso);
    return d.toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="loader">
        <div className="spinner" />
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <div className="page">
        <div className="page-title">🎯 Встречи</div>
        <div className="empty-state">
          <div className="icon">🎯</div>
          <p>
            Пока нет активных встреч.
            <br />
            Создай в групповом чате: <strong>/meet</strong>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-title">🎯 Встречи</div>

      {meetings.map((m) => {
        const deadline = formatDeadline(m.vote_deadline);
        return (
          <div className="meeting-card" key={m.id}>
            <div className="meeting-title">{m.title}</div>
            <div className="meeting-meta">
              <span>📅 {formatDate(m.proposed_datetime)}</span>
              {m.location && <span>📍 {m.location}</span>}
            </div>
            <div className="meeting-meta">
              <span>👤 {m.creator_name}</span>
              {deadline && <span>⏰ до {deadline}</span>}
            </div>

            {/* Votes summary */}
            <div className="votes-summary">
              {m.votes.yes?.length ? (
                <div>✅ Идут ({m.votes.yes.length}): {m.votes.yes.join(", ")}</div>
              ) : null}
              {m.votes.no?.length ? (
                <div>❌ Не могут ({m.votes.no.length}): {m.votes.no.join(", ")}</div>
              ) : null}
              {m.votes.maybe?.length ? (
                <div>🤔 Не уверены ({m.votes.maybe.length}): {m.votes.maybe.join(", ")}</div>
              ) : null}
              {!m.votes.yes?.length && !m.votes.no?.length && !m.votes.maybe?.length && (
                <div>🗳 Пока никто не проголосовал</div>
              )}
            </div>

            {/* Vote buttons */}
            <div className="vote-buttons">
              <button
                className={`vote-btn${m.my_vote === "yes" ? " selected" : ""}`}
                onClick={() => handleVote(m.id, "yes")}
                disabled={votingId === m.id}
              >
                ✅ Иду
              </button>
              <button
                className={`vote-btn${m.my_vote === "maybe" ? " selected-maybe" : ""}`}
                onClick={() => handleVote(m.id, "maybe")}
                disabled={votingId === m.id}
              >
                🤔 Может
              </button>
              <button
                className={`vote-btn${m.my_vote === "no" ? " selected-no" : ""}`}
                onClick={() => handleVote(m.id, "no")}
                disabled={votingId === m.id}
              >
                ❌ Нет
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
