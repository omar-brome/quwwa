import { Dumbbell, House, UserRound } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useStartSessionFlow } from "@/hooks/useStartSession";
import { useActiveSession } from "@/stores/activeSession";
import { cn } from "@/lib/utils";

export function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const hasActive = useActiveSession((s) => s.sessionId !== null);
  const { startOrResume, starting } = useStartSessionFlow();

  if (location.pathname === "/session/active") return null;

  const item = (path: string, label: string, icon: React.ReactNode) => (
    <button
      onClick={() => navigate(path)}
      className={cn(
        "flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px]",
        location.pathname === path ? "text-primary" : "text-muted-foreground",
      )}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
      <div className="mx-auto flex w-full max-w-md items-center">
        {item("/", "Home", <House size={20} />)}
        <button
          onClick={() => void startOrResume()}
          disabled={starting}
          className="relative -top-4 mx-2 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/25 active:scale-95 disabled:opacity-60"
          aria-label={hasActive ? "Resume session" : "Start session"}
        >
          <Dumbbell size={24} />
          {hasActive && (
            <span className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-card bg-success" />
          )}
        </button>
        {item("/profile", "Profile", <UserRound size={20} />)}
      </div>
    </nav>
  );
}
