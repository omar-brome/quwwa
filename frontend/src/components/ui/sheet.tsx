import { type ReactNode } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

/** Mobile bottom sheet. */
export function Sheet({ open, onClose, title, children, className }: SheetProps) {
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div
        className={cn(
          "absolute inset-x-0 bottom-0 mx-auto max-h-[88dvh] w-full max-w-md overflow-y-auto rounded-t-2xl border-t border-border bg-card p-4 pb-[max(1.25rem,env(safe-area-inset-bottom))]",
          className,
        )}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
        {title && <h2 className="mb-3 text-base font-semibold">{title}</h2>}
        {children}
      </div>
    </div>,
    document.body,
  );
}
