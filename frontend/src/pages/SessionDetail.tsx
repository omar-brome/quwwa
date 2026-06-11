import { differenceInMinutes, format, parseISO } from "date-fns";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInvalidateTrainingData, useProfile, useSession } from "@/hooks/queries";
import { api, type SetOut } from "@/lib/api";
import { formatWeight } from "@/lib/units";

export function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading } = useSession(id);
  const { data: profile } = useProfile();
  const invalidate = useInvalidateTrainingData();
  const units = profile?.units ?? "kg";

  const groups = useMemo(() => {
    if (!session) return [];
    const map = new Map<string, SetOut[]>();
    for (const s of session.sets) {
      if (!map.has(s.exercise_id)) map.set(s.exercise_id, []);
      map.get(s.exercise_id)!.push(s);
    }
    return [...map.values()];
  }, [session]);

  const handleDelete = async () => {
    if (!id || !window.confirm("Delete this session and all its sets?")) return;
    await api.deleteSession(id);
    invalidate();
    navigate("/", { replace: true });
  };

  if (isLoading) return <Skeleton className="mt-4 h-48 w-full" />;
  if (!session) return <p className="pt-8 text-center text-muted-foreground">Session not found.</p>;

  const duration =
    session.ended_at !== null
      ? differenceInMinutes(parseISO(session.ended_at), parseISO(session.started_at))
      : null;

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between pt-2">
        <Link to="/" className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft size={16} /> Home
        </Link>
        <Button variant="ghost" size="icon" onClick={() => void handleDelete()} aria-label="Delete session">
          <Trash2 size={17} className="text-muted-foreground" />
        </Button>
      </header>

      <div>
        <h1 className="text-xl font-bold">
          {format(parseISO(session.started_at), "EEEE d MMMM")}
        </h1>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge variant="muted">{session.working_sets} working sets</Badge>
          <Badge variant="muted">{formatWeight(session.total_volume_kg, units)} volume</Badge>
          {duration !== null && <Badge variant="muted">{duration} min</Badge>}
          {session.rpe !== null && <Badge>RPE {session.rpe}</Badge>}
          {session.bodyweight_kg !== null && (
            <Badge variant="outline">BW {formatWeight(session.bodyweight_kg, units)}</Badge>
          )}
        </div>
      </div>

      {Object.keys(session.volume_by_muscle).length > 0 && (
        <Card>
          <CardTitle className="mb-2">Sets by muscle</CardTitle>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(session.volume_by_muscle)
              .sort((a, b) => b[1] - a[1])
              .map(([muscle, sets]) => (
                <Badge key={muscle} variant="muted">
                  {muscle} · {sets}
                </Badge>
              ))}
          </div>
        </Card>
      )}

      {groups.map((sets) => (
        <section key={sets[0].exercise_id}>
          <Link
            to={`/exercise/${sets[0].exercise_id}`}
            className="mb-1.5 block text-sm font-semibold text-primary"
          >
            {sets[0].exercise_name}
          </Link>
          <div className="divide-y divide-border rounded-xl border border-border bg-card">
            {sets.map((s) => (
              <div key={s.id} className="flex items-center gap-2 p-3">
                <span className="w-6 text-xs tabular-nums text-muted-foreground">
                  #{s.set_number}
                </span>
                <span className="flex-1 text-sm font-medium tabular-nums">
                  {formatWeight(s.weight_kg, units)} × {s.reps ?? "—"}
                </span>
                {s.is_warmup && <Badge variant="muted">warmup</Badge>}
                {s.rpe !== null && <Badge variant="outline">RPE {s.rpe}</Badge>}
              </div>
            ))}
          </div>
        </section>
      ))}

      {session.notes && (
        <Card>
          <CardTitle className="mb-2">Notes</CardTitle>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{session.notes}</p>
        </Card>
      )}
    </div>
  );
}
