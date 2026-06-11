import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, type Exercise } from "@/lib/api";

const EXERCISES_CACHE_KEY = "quwwa-exercises";

/** Full exercise library, mirrored to localStorage so the picker works offline. */
export function useExercises() {
  return useQuery({
    queryKey: ["exercises"],
    queryFn: async () => {
      try {
        const data = await api.listExercises();
        localStorage.setItem(EXERCISES_CACHE_KEY, JSON.stringify(data));
        return data;
      } catch (err) {
        const cached = localStorage.getItem(EXERCISES_CACHE_KEY);
        if (cached) return JSON.parse(cached) as Exercise[];
        throw err;
      }
    },
    initialData: () => {
      const cached = localStorage.getItem(EXERCISES_CACHE_KEY);
      return cached ? (JSON.parse(cached) as Exercise[]) : undefined;
    },
    staleTime: 30_000,
  });
}

export function useExerciseHistory(id: string | undefined) {
  return useQuery({
    queryKey: ["exercise-history", id],
    queryFn: () => api.exerciseHistory(id!),
    enabled: !!id,
  });
}

export function useSessions(limit = 20) {
  return useQuery({
    queryKey: ["sessions", limit],
    queryFn: () => api.listSessions(limit),
  });
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: ["session", id],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  });
}

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
}

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 60_000 });
}

export function useWeeklyVolume() {
  return useQuery({ queryKey: ["weekly-volume"], queryFn: api.weeklyVolume });
}

export function usePlateauAlerts() {
  return useQuery({ queryKey: ["plateau-alerts"], queryFn: api.plateauAlerts });
}

/** Invalidate everything that derives from logged training data. */
export function useInvalidateTrainingData() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ["sessions"] });
    void qc.invalidateQueries({ queryKey: ["session"] });
    void qc.invalidateQueries({ queryKey: ["weekly-volume"] });
    void qc.invalidateQueries({ queryKey: ["exercises"] });
    void qc.invalidateQueries({ queryKey: ["exercise-history"] });
    void qc.invalidateQueries({ queryKey: ["coaching"] });
  };
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateProfile,
    onSuccess: (data) => {
      qc.setQueryData(["profile"], data);
      void qc.invalidateQueries({ queryKey: ["coaching"] });
    },
  });
}

export function useCreateExercise() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createExercise,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["exercises"] }),
  });
}

export function useImportCsv() {
  const invalidate = useInvalidateTrainingData();
  return useMutation({
    mutationFn: api.importCsv,
    onSuccess: invalidate,
  });
}
