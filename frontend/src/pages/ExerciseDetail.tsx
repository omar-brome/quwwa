import { format, parseISO } from "date-fns";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { E1rmChart } from "@/components/E1rmChart";
import { ExerciseVideos } from "@/components/ExerciseVideos";
import { PlateauCard } from "@/components/PlateauCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useExerciseHistory, useProfile } from "@/hooks/queries";
import { formatWeight } from "@/lib/units";

export function ExerciseDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useExerciseHistory(id);
  const { data: profile } = useProfile();
  const units = profile?.units ?? "kg";

  if (isLoading) return <Skeleton className="mt-4 h-48 w-full" />;
  if (!data) return <p className="pt-8 text-center text-muted-foreground">Exercise not found.</p>;

  return (
    <div className="space-y-4">
      <header className="pt-2">
        <Link to="/" className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft size={16} /> Home
        </Link>
        <h1 className="mt-2 text-xl font-bold">{data.exercise.name}</h1>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {data.exercise.muscle_groups.map((m) => (
            <Badge key={m} variant="muted">
              {m}
            </Badge>
          ))}
          {data.exercise.equipment && <Badge variant="outline">{data.exercise.equipment}</Badge>}
          {data.exercise.category && <Badge variant="outline">{data.exercise.category}</Badge>}
        </div>
      </header>

      {id && <PlateauCard exerciseId={id} />}

      <Card>
        <CardTitle className="mb-2">Estimated 1RM ({units})</CardTitle>
        <E1rmChart sessions={data.sessions} units={units} />
      </Card>

      <ExerciseVideos exerciseName={data.exercise.name} />

      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          History
        </h2>
        {data.sessions.length === 0 && (
          <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Never logged — time to fix that.
          </p>
        )}
        {data.sessions.map((s) => (
          <Link
            key={s.session_id}
            to={`/session/${s.session_id}`}
            className="block rounded-xl border border-border bg-card p-3 active:bg-muted/50"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {format(parseISO(s.date), "EEE d MMM yyyy")}
              </span>
              {s.best_e1rm !== null && (
                <Badge>e1RM {formatWeight(s.best_e1rm, units)}</Badge>
              )}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {s.sets
                .map(
                  (set) =>
                    `${formatWeight(set.weight_kg, units)}×${set.reps ?? "—"}${
                      set.rpe !== null ? `@${set.rpe}` : ""
                    }${set.is_warmup ? " (w)" : ""}`,
                )
                .join("  ·  ")}
            </div>
          </Link>
        ))}
      </section>
    </div>
  );
}
