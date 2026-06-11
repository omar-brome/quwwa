import { create } from "zustand";
import { persist } from "zustand/middleware";

/** A set as logged locally. serverId is null until the POST succeeds, so an
 * offline gym session survives — pending sets are retried before finishing. */
export interface LoggedEntry {
  clientId: string;
  serverId: string | null;
  exerciseId: string;
  exerciseName: string;
  muscleGroups: string[];
  setNumber: number;
  weightKg: number | null;
  reps: number | null;
  rpe: number | null;
  isWarmup: boolean;
}

export interface CurrentExercise {
  id: string;
  name: string;
  muscleGroups: string[];
}

interface ActiveSessionState {
  sessionId: string | null;
  startedAt: string | null;
  entries: LoggedEntry[];
  currentExercise: CurrentExercise | null;
  start: (sessionId: string, startedAt: string) => void;
  setCurrentExercise: (exercise: CurrentExercise | null) => void;
  addEntry: (entry: LoggedEntry) => void;
  updateEntry: (clientId: string, patch: Partial<LoggedEntry>) => void;
  removeEntry: (clientId: string) => void;
  clear: () => void;
}

/** Persisted to localStorage so closing the browser mid-session loses nothing. */
export const useActiveSession = create<ActiveSessionState>()(
  persist(
    (set) => ({
      sessionId: null,
      startedAt: null,
      entries: [],
      currentExercise: null,
      start: (sessionId, startedAt) =>
        set({ sessionId, startedAt, entries: [], currentExercise: null }),
      setCurrentExercise: (currentExercise) => set({ currentExercise }),
      addEntry: (entry) => set((s) => ({ entries: [...s.entries, entry] })),
      updateEntry: (clientId, patch) =>
        set((s) => ({
          entries: s.entries.map((e) => (e.clientId === clientId ? { ...e, ...patch } : e)),
        })),
      removeEntry: (clientId) =>
        set((s) => ({ entries: s.entries.filter((e) => e.clientId !== clientId) })),
      clear: () =>
        set({ sessionId: null, startedAt: null, entries: [], currentExercise: null }),
    }),
    { name: "quwwa-active-session" },
  ),
);

interface LastWeightsState {
  weights: Record<string, { weightKg: number | null; reps: number | null }>;
  remember: (exerciseId: string, weightKg: number | null, reps: number | null) => void;
}

/** Remembers the last weight/reps used per exercise to pre-populate the logger. */
export const useLastWeights = create<LastWeightsState>()(
  persist(
    (set) => ({
      weights: {},
      remember: (exerciseId, weightKg, reps) =>
        set((s) => ({ weights: { ...s.weights, [exerciseId]: { weightKg, reps } } })),
    }),
    { name: "quwwa-last-weights" },
  ),
);
