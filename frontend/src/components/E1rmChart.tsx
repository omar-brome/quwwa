import { format, parseISO } from "date-fns";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HistorySession } from "@/lib/api";
import { toDisplay, type Units } from "@/lib/units";

export function E1rmChart({
  sessions,
  units,
}: {
  sessions: HistorySession[];
  units: Units;
}) {
  const data = [...sessions]
    .reverse() // newest-first → oldest-first for the x axis
    .filter((s) => s.best_e1rm !== null)
    .map((s) => ({
      date: format(parseISO(s.date), "d MMM"),
      e1rm: Math.round((toDisplay(s.best_e1rm, units) ?? 0) * 10) / 10,
    }));

  if (data.length < 2) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        Log at least two sessions to see the estimated 1RM trend.
      </p>
    );
  }

  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 8% 17%)" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(240 6% 64%)" }} />
          <YAxis
            domain={["dataMin - 5", "dataMax + 5"]}
            tick={{ fontSize: 11, fill: "hsl(240 6% 64%)" }}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(240 11% 8%)",
              border: "1px solid hsl(240 8% 17%)",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "hsl(240 6% 64%)" }}
            formatter={(value) => [`${value} ${units}`, "e1RM"]}
          />
          <Line
            type="monotone"
            dataKey="e1rm"
            stroke="hsl(43 91% 50%)"
            strokeWidth={2}
            dot={{ r: 3, fill: "hsl(43 91% 50%)" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
