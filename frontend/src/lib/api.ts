const BASE = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (typeof init.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, {
    ...init,
    headers: { ...headers, ...(init.headers as Record<string, string> | undefined) },
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    throw new ApiError(
      res.status,
      typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : res.statusText,
    );
  }
  return data as T;
}

// ---------------------------------------------------------------------------
// Types (mirror backend/app/schemas.py)

export interface Exercise {
  id: string;
  name: string;
  muscle_groups: string[];
  category: string | null;
  equipment: string | null;
  is_custom: boolean;
  last_used_at: string | null;
  last_weight_kg: number | null;
  last_reps: number | null;
}

export interface SetOut {
  id: string;
  session_id: string;
  exercise_id: string;
  exercise_name: string;
  muscle_groups: string[];
  set_number: number;
  reps: number | null;
  weight_kg: number | null;
  rpe: number | null;
  is_warmup: boolean;
  notes: string | null;
  logged_at: string;
}

export interface SessionSummary {
  id: string;
  started_at: string;
  ended_at: string | null;
  rpe: number | null;
  notes: string | null;
  bodyweight_kg: number | null;
  total_sets: number;
  working_sets: number;
  total_volume_kg: number;
  exercise_names: string[];
  muscle_groups: string[];
}

export interface SessionDetail extends SessionSummary {
  sets: SetOut[];
  volume_by_muscle: Record<string, number>;
}

export interface Profile {
  user_id: string;
  training_goal: "strength" | "hypertrophy" | "recomp" | "endurance";
  experience: "beginner" | "intermediate" | "advanced";
  training_days: number;
  equipment: string[];
  injury_notes: string | null;
  units: "kg" | "lbs";
}

export interface HistorySession {
  session_id: string;
  date: string;
  sets: {
    set_number: number;
    reps: number | null;
    weight_kg: number | null;
    rpe: number | null;
    is_warmup: boolean;
  }[];
  best_e1rm: number | null;
}

export interface ExerciseHistory {
  exercise: Exercise;
  sessions: HistorySession[];
}

export interface MuscleVolume {
  muscle: string;
  sets: number;
  min_sets: number | null;
  max_sets: number | null;
}

// --- Coaching content shapes -------------------------------------------------

export interface PlannedExercise {
  exercise_name: string;
  sets: number;
  target_reps: string;
  target_weight_kg: number;
  progression_reason: string;
  rpe_target: number;
}

export interface NextSessionPlan {
  session_focus: string;
  coaching_note: string;
  exercises: PlannedExercise[];
  deload_recommended: boolean;
  deload_reason: string | null;
}

export interface PlateauReport {
  status: "progressing" | "plateaued" | "regressing" | "fatigued";
  trend_summary: string;
  recommendation: string;
  urgency: "low" | "medium" | "high";
}

export interface WeeklyReview {
  headline: string;
  positives: string[];
  concerns: string[];
  focus_next_week: string;
  volume_status: { muscle_group: string; status: "under" | "optimal" | "over" }[];
}

export interface DeloadAdvice {
  deload_needed: boolean;
  confidence: "low" | "medium" | "high";
  rationale: string;
  deload_type: "full" | "volume" | "intensity" | null;
  deload_protocol: string | null;
}

export interface CoachingEnvelope<T> {
  status: "fresh" | "stale" | "no_api_key" | "insufficient_data" | "empty";
  request?: { muscles?: string[]; [k: string]: unknown };
  content?: T;
  generated_at?: string;
  cached_content?: T;
  cached_generated_at?: string;
  detail?: string;
}

export interface PlateauAlert {
  exercise_id: string;
  exercise_name: string;
  status: string;
  urgency: string;
  generated_at: string;
}

export interface ImportResult {
  sessions_created: number;
  sets_created: number;
  exercises_created: string[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Calls

export const api = {
  health: () =>
    request<{ status: string; ai_configured: boolean; model: string }>("/health"),

  listExercises: () => request<Exercise[]>("/exercises"),
  createExercise: (body: {
    name: string;
    muscle_groups: string[];
    category?: string | null;
    equipment?: string | null;
  }) => request<Exercise>("/exercises", { method: "POST", body: JSON.stringify(body) }),
  exerciseHistory: (id: string) => request<ExerciseHistory>(`/exercises/${id}/history`),

  startSession: (body: { started_at?: string; bodyweight_kg?: number | null }) =>
    request<SessionSummary>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  listSessions: (limit = 20, offset = 0) =>
    request<{ items: SessionSummary[]; total: number }>(
      `/sessions?limit=${limit}&offset=${offset}`,
    ),
  getSession: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  patchSession: (
    id: string,
    body: Partial<{
      ended_at: string;
      notes: string | null;
      rpe: number | null;
      bodyweight_kg: number | null;
    }>,
  ) => request<SessionSummary>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteSession: (id: string) => request<void>(`/sessions/${id}`, { method: "DELETE" }),

  logSet: (
    sessionId: string,
    body: {
      exercise_id: string;
      reps: number | null;
      weight_kg: number | null;
      rpe: number | null;
      is_warmup: boolean;
    },
  ) =>
    request<SetOut>(`/sessions/${sessionId}/sets`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  patchSet: (
    id: string,
    body: Partial<{
      reps: number | null;
      weight_kg: number | null;
      rpe: number | null;
      is_warmup: boolean;
    }>,
  ) => request<SetOut>(`/sets/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteSet: (id: string) => request<void>(`/sets/${id}`, { method: "DELETE" }),

  getProfile: () => request<Profile>("/profile"),
  updateProfile: (body: Omit<Profile, "user_id">) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(body) }),

  weeklyVolume: () =>
    request<{ week_start: string; muscles: MuscleVolume[] }>("/stats/weekly-volume"),

  coachingGet: <T>(path: string) => request<CoachingEnvelope<T>>(path),
  plateauAlerts: () => request<{ alerts: PlateauAlert[] }>("/coaching/plateau-alerts"),

  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportResult>("/import/csv", { method: "POST", body: form });
  },
};

export const MUSCLE_GROUPS = [
  "chest",
  "back",
  "shoulders",
  "biceps",
  "triceps",
  "forearms",
  "quads",
  "hamstrings",
  "glutes",
  "calves",
  "core",
] as const;

export const EQUIPMENT_TYPES = ["barbell", "dumbbell", "cable", "machine", "bodyweight"] as const;

export const MUSCLE_PRESETS: Record<string, string[] | undefined> = {
  Auto: undefined,
  Push: ["chest", "shoulders", "triceps"],
  Pull: ["back", "biceps", "forearms"],
  Legs: ["quads", "hamstrings", "glutes", "calves"],
  Upper: ["chest", "back", "shoulders", "biceps", "triceps"],
};
