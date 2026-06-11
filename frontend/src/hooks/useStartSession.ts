import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/lib/api";
import { useActiveSession } from "@/stores/activeSession";

/** Start a new session (or jump back into the active one) and navigate to the logger. */
export function useStartSessionFlow() {
  const navigate = useNavigate();
  const { sessionId, start } = useActiveSession();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startOrResume = async () => {
    if (sessionId) {
      navigate("/session/active");
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const session = await api.startSession({});
      start(session.id, session.started_at);
      navigate("/session/active");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start session");
    } finally {
      setStarting(false);
    }
  };

  return { startOrResume, starting, error, hasActive: sessionId !== null };
}
