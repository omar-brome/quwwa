import { format, parseISO } from "date-fns";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import type { SessionSummary } from "@/lib/api";
import { formatWeight, type Units } from "@/lib/units";

export function SessionListItem({
  session,
  units,
}: {
  session: SessionSummary;
  units: Units;
}) {
  return (
    <Link
      to={`/session/${session.id}`}
      className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 active:bg-muted/50"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">
            {format(parseISO(session.started_at), "EEE d MMM")}
          </span>
          {session.rpe !== null && <Badge variant="muted">RPE {session.rpe}</Badge>}
        </div>
        <div className="mt-0.5 truncate text-sm text-muted-foreground">
          {session.exercise_names.join(" · ") || "Empty session"}
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          {session.working_sets} sets · {formatWeight(session.total_volume_kg, units)} total
        </div>
      </div>
      <ChevronRight size={18} className="shrink-0 text-muted-foreground" />
    </Link>
  );
}
