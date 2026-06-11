import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useCreateExercise, useExercises } from "@/hooks/queries";
import { MUSCLE_GROUPS, type Exercise } from "@/lib/api";
import { formatWeight, type Units } from "@/lib/units";
import { cn } from "@/lib/utils";

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (exercise: Exercise) => void;
  units: Units;
}

/** Search-first picker; the list comes pre-sorted by most-recently-used and is
 * served from localStorage when offline. */
export function ExercisePicker({ open, onClose, onSelect, units }: Props) {
  const { data: exercises } = useExercises();
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [newMuscles, setNewMuscles] = useState<string[]>([]);
  const createExercise = useCreateExercise();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!exercises) return [];
    if (!q) return exercises;
    return exercises.filter(
      (e) =>
        e.name.toLowerCase().includes(q) ||
        e.muscle_groups.some((m) => m.includes(q)),
    );
  }, [exercises, query]);

  const exactMatch = filtered.some((e) => e.name.toLowerCase() === query.trim().toLowerCase());

  const handleCreate = async () => {
    const created = await createExercise.mutateAsync({
      name: query.trim(),
      muscle_groups: newMuscles,
    });
    setCreating(false);
    setQuery("");
    setNewMuscles([]);
    onSelect(created);
  };

  const close = () => {
    setCreating(false);
    setQuery("");
    onClose();
  };

  return (
    <Sheet open={open} onClose={close} title="Pick exercise" className="h-[88dvh]">
      <Input
        autoFocus
        placeholder="Search exercises…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="mb-3"
      />

      {creating ? (
        <div className="space-y-3">
          <div className="text-sm">
            Creating <span className="font-semibold">{query.trim()}</span> — which muscles does
            it train?
          </div>
          <div className="flex flex-wrap gap-1.5">
            {MUSCLE_GROUPS.map((m) => (
              <button
                key={m}
                onClick={() =>
                  setNewMuscles((cur) =>
                    cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m],
                  )
                }
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium",
                  newMuscles.includes(m)
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {m}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={() => void handleCreate()}
              disabled={createExercise.isPending || !query.trim()}
            >
              Create exercise
            </Button>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Back
            </Button>
          </div>
          {createExercise.isError && (
            <p className="text-xs text-destructive">
              {createExercise.error instanceof Error ? createExercise.error.message : "Failed"}
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-1">
          {query.trim() && !exactMatch && (
            <button
              onClick={() => setCreating(true)}
              className="flex w-full items-center gap-2 rounded-lg border border-dashed border-border p-3 text-sm text-primary"
            >
              <Plus size={16} /> Create “{query.trim()}”
            </button>
          )}
          {filtered.map((e) => (
            <button
              key={e.id}
              onClick={() => {
                onSelect(e);
                close();
              }}
              className="flex w-full items-center justify-between gap-2 rounded-lg p-3 text-left active:bg-muted"
            >
              <div className="min-w-0">
                <div className="truncate font-medium">{e.name}</div>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {e.muscle_groups.slice(0, 3).map((m) => (
                    <Badge key={m} variant="muted" className="text-[10px]">
                      {m}
                    </Badge>
                  ))}
                </div>
              </div>
              {e.last_weight_kg !== null && (
                <div className="shrink-0 text-right text-xs text-muted-foreground">
                  last
                  <div className="font-medium text-foreground">
                    {formatWeight(e.last_weight_kg, units)}
                    {e.last_reps != null && ` × ${e.last_reps}`}
                  </div>
                </div>
              )}
            </button>
          ))}
          {exercises && filtered.length === 0 && !query.trim() && (
            <p className="py-8 text-center text-sm text-muted-foreground">No exercises yet.</p>
          )}
        </div>
      )}
    </Sheet>
  );
}
