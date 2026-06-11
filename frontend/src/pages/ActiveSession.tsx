import { differenceInSeconds, parseISO } from "date-fns";
import { ChevronDown, Flag, Pencil, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ExercisePicker } from "@/components/ExercisePicker";
import { RpeInput, Stepper } from "@/components/inputs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { useInvalidateTrainingData, useProfile } from "@/hooks/queries";
import { api, type Exercise } from "@/lib/api";
import { formatWeight, fromDisplay, toDisplay, weightStep } from "@/lib/units";
import { cn } from "@/lib/utils";
import {
  useActiveSession,
  useLastWeights,
  type LoggedEntry,
} from "@/stores/activeSession";

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [, force] = useState(0);
  useEffect(() => {
    const id = setInterval(() => force((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const total = Math.max(0, differenceInSeconds(new Date(), parseISO(startedAt)));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    <span className="tabular-nums text-muted-foreground">
      {h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`}
    </span>
  );
}

export function ActiveSession() {
  const navigate = useNavigate();
  const store = useActiveSession();
  const lastWeights = useLastWeights();
  const { data: profile } = useProfile();
  const invalidate = useInvalidateTrainingData();
  const units = profile?.units ?? "kg";

  const [pickerOpen, setPickerOpen] = useState(false);
  const [finishOpen, setFinishOpen] = useState(false);
  const [weight, setWeight] = useState<number | null>(null); // display units
  const [reps, setReps] = useState<number | null>(null);
  const [rpe, setRpe] = useState<number | null>(null);
  const [isWarmup, setIsWarmup] = useState(false);
  const [editing, setEditing] = useState<string | null>(null); // clientId
  const [logError, setLogError] = useState<string | null>(null);
  const [sessionRpe, setSessionRpe] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [bodyweight, setBodyweight] = useState<number | null>(null);
  const [finishing, setFinishing] = useState(false);
  const inFlight = useRef<Set<string>>(new Set());

  const groups = useMemo(() => {
    const map = new Map<string, LoggedEntry[]>();
    for (const e of store.entries) {
      if (!map.has(e.exerciseId)) map.set(e.exerciseId, []);
      map.get(e.exerciseId)!.push(e);
    }
    return [...map.values()];
  }, [store.entries]);

  if (!store.sessionId || !store.startedAt) return <Navigate to="/" replace />;
  const sessionId = store.sessionId;

  const selectExercise = (exercise: Exercise) => {
    store.setCurrentExercise({
      id: exercise.id,
      name: exercise.name,
      muscleGroups: exercise.muscle_groups,
    });
    setEditing(null);
    const remembered = lastWeights.weights[exercise.id];
    const kg = remembered?.weightKg ?? exercise.last_weight_kg;
    setWeight(kg != null ? Math.round((toDisplay(kg, units) ?? 0) * 10) / 10 : null);
    setReps(remembered?.reps ?? exercise.last_reps ?? null);
    setRpe(null);
    setIsWarmup(false);
  };

  const pushToServer = async (clientId: string) => {
    // Always act on the latest store state: a stale closure here would
    // double-POST a set that another code path already synced.
    const entry = useActiveSession.getState().entries.find((e) => e.clientId === clientId);
    if (!entry || entry.serverId !== null || inFlight.current.has(clientId)) return;
    inFlight.current.add(clientId);
    try {
      const saved = await api.logSet(sessionId, {
        exercise_id: entry.exerciseId,
        reps: entry.reps,
        weight_kg: entry.weightKg,
        rpe: entry.rpe,
        is_warmup: entry.isWarmup,
      });
      store.updateEntry(clientId, { serverId: saved.id, setNumber: saved.set_number });
      setLogError(null);
    } catch (err) {
      setLogError(err instanceof Error ? err.message : "Could not sync set — will retry");
    } finally {
      inFlight.current.delete(clientId);
    }
  };

  const flushPending = async () => {
    const pending = useActiveSession.getState().entries.filter((e) => e.serverId === null);
    for (const entry of pending) await pushToServer(entry.clientId);
  };

  const logSet = async () => {
    const exercise = store.currentExercise;
    if (!exercise) return setPickerOpen(true);
    const kg = fromDisplay(weight, units);

    if (editing) {
      const entry = store.entries.find((e) => e.clientId === editing);
      if (entry) {
        store.updateEntry(editing, { weightKg: kg, reps, rpe, isWarmup });
        if (entry.serverId) {
          try {
            await api.patchSet(entry.serverId, {
              weight_kg: kg,
              reps,
              rpe,
              is_warmup: isWarmup,
            });
            setLogError(null);
          } catch (err) {
            setLogError(err instanceof Error ? err.message : "Could not update set");
          }
        }
      }
      setEditing(null);
      setRpe(null);
      return;
    }

    const entry: LoggedEntry = {
      clientId: crypto.randomUUID(),
      serverId: null,
      exerciseId: exercise.id,
      exerciseName: exercise.name,
      muscleGroups: exercise.muscleGroups,
      setNumber: store.entries.filter((e) => e.exerciseId === exercise.id).length + 1,
      weightKg: kg,
      reps,
      rpe,
      isWarmup,
    };
    store.addEntry(entry);
    lastWeights.remember(exercise.id, kg, reps);
    setIsWarmup(false);
    // Pushes the new entry and retries any earlier sets that failed to sync.
    await flushPending();
  };

  const startEdit = (entry: LoggedEntry) => {
    setEditing(entry.clientId);
    store.setCurrentExercise({
      id: entry.exerciseId,
      name: entry.exerciseName,
      muscleGroups: entry.muscleGroups,
    });
    setWeight(
      entry.weightKg != null ? Math.round((toDisplay(entry.weightKg, units) ?? 0) * 10) / 10 : null,
    );
    setReps(entry.reps);
    setRpe(entry.rpe);
    setIsWarmup(entry.isWarmup);
  };

  const deleteEntry = async (entry: LoggedEntry) => {
    store.removeEntry(entry.clientId);
    if (editing === entry.clientId) setEditing(null);
    if (entry.serverId) {
      try {
        await api.deleteSet(entry.serverId);
      } catch {
        /* already gone or offline — local state is authoritative for this UI */
      }
    }
  };

  const finishSession = async () => {
    setFinishing(true);
    try {
      await flushPending();
      await api.patchSession(sessionId, {
        ended_at: new Date().toISOString(),
        rpe: sessionRpe,
        notes: notes.trim() || null,
        bodyweight_kg: fromDisplay(bodyweight, units),
      });
      navigate(`/session/${sessionId}`, { replace: true });
      // Clear only after the route commits: clearing while this page is still
      // mounted re-renders it with no session and the guard below bounces the
      // user to "/" instead of the session summary.
      setTimeout(() => {
        useActiveSession.getState().clear();
        invalidate();
      }, 0);
    } catch (err) {
      setLogError(err instanceof Error ? err.message : "Could not finish session");
    } finally {
      setFinishing(false);
    }
  };

  return (
    <div className="pb-[290px]">
      {/* Sticky header: elapsed time + finish — never navigate away by accident */}
      <header className="sticky top-0 z-30 -mx-4 mb-3 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div>
          <div className="text-sm font-semibold">Active session</div>
          <ElapsedTimer startedAt={store.startedAt} />
        </div>
        <Button size="sm" variant="outline" onClick={() => setFinishOpen(true)}>
          <Flag size={15} /> Finish
        </Button>
      </header>

      {/* Logged sets, grouped by exercise */}
      <div className="space-y-4">
        {groups.length === 0 && (
          <p className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            Pick an exercise below and log your first set.
          </p>
        )}
        {groups.map((entries) => (
          <section key={entries[0].exerciseId}>
            <Link
              to={`/exercise/${entries[0].exerciseId}`}
              className="mb-1.5 block text-sm font-semibold text-primary"
            >
              {entries[0].exerciseName}
            </Link>
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {entries.map((e) => (
                <div
                  key={e.clientId}
                  className={cn(
                    "flex items-center gap-2 p-3",
                    editing === e.clientId && "bg-primary/5",
                  )}
                >
                  <span className="w-6 text-xs tabular-nums text-muted-foreground">
                    #{e.setNumber}
                  </span>
                  <span className="flex-1 text-sm font-medium tabular-nums">
                    {formatWeight(e.weightKg, units)} × {e.reps ?? "—"}
                  </span>
                  {e.isWarmup && <Badge variant="muted">warmup</Badge>}
                  {e.rpe !== null && <Badge variant="outline">RPE {e.rpe}</Badge>}
                  {e.serverId === null && (
                    <Badge variant="warning" title="Not synced yet">
                      pending
                    </Badge>
                  )}
                  <button
                    onClick={() => startEdit(e)}
                    className="p-1.5 text-muted-foreground"
                    aria-label="Edit set"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    onClick={() => void deleteEntry(e)}
                    className="p-1.5 text-muted-foreground"
                    aria-label="Delete set"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Fixed logger panel */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur">
        <div className="mx-auto w-full max-w-md space-y-3 px-4 pt-3">
          <button
            onClick={() => setPickerOpen(true)}
            className="flex w-full items-center justify-between rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-left"
          >
            <span className={cn("font-medium", !store.currentExercise && "text-muted-foreground")}>
              {store.currentExercise?.name ?? "Choose exercise"}
            </span>
            <ChevronDown size={16} className="text-muted-foreground" />
          </button>

          <div className="flex gap-3">
            <Stepper
              label={`Weight (${units})`}
              value={weight}
              onChange={setWeight}
              step={weightStep(units)}
            />
            <Stepper label="Reps" value={reps} onChange={setReps} step={1} decimals={0} />
          </div>

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <RpeInput value={rpe} onChange={setRpe} />
            </div>
            <button
              type="button"
              onClick={() => setIsWarmup((w) => !w)}
              className={cn(
                "h-9 rounded-lg px-3 text-xs font-medium",
                isWarmup ? "bg-warning/20 text-warning" : "bg-muted text-muted-foreground",
              )}
            >
              warmup
            </button>
          </div>

          <div className="flex gap-2">
            <Button className="flex-1" size="lg" onClick={() => void logSet()}>
              {editing ? "Update set" : "Log set"}
            </Button>
            {editing && (
              <Button
                variant="outline"
                size="lg"
                onClick={() => {
                  setEditing(null);
                  setRpe(null);
                }}
              >
                Cancel
              </Button>
            )}
          </div>
          {logError && <p className="text-xs text-destructive">{logError}</p>}
        </div>
      </div>

      <ExercisePicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={selectExercise}
        units={units}
      />

      <Sheet open={finishOpen} onClose={() => setFinishOpen(false)} title="Finish session">
        <div className="space-y-4">
          <div>
            <div className="mb-1.5 text-sm text-muted-foreground">
              How hard was the session overall? (optional)
            </div>
            <div className="flex gap-1">
              {[5, 6, 7, 8, 9, 10].map((n) => (
                <button
                  key={n}
                  onClick={() => setSessionRpe(sessionRpe === n ? null : n)}
                  className={cn(
                    "h-10 flex-1 rounded-lg text-sm font-semibold",
                    sessionRpe === n
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-1.5 text-sm text-muted-foreground">Bodyweight ({units}, optional)</div>
            <Stepper
              label=""
              value={bodyweight}
              onChange={setBodyweight}
              step={units === "kg" ? 0.5 : 1}
            />
          </div>
          <Textarea
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <Button
            size="lg"
            className="w-full"
            onClick={() => void finishSession()}
            disabled={finishing}
          >
            {finishing ? "Saving…" : "Finish session"}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}
