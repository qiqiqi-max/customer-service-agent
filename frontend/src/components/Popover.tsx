import { ChevronDown } from "lucide-react";
import { ReactNode, useEffect, useId, useRef, useState } from "react";

/** Toolbar dropdown. Closes on outside click and Escape; `children` may take a close callback. */
export function Popover(props: {
  label: string;
  value: string;
  children: ReactNode | ((close: () => void) => ReactNode);
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="popover" ref={rootRef}>
      <button
        aria-controls={panelId}
        aria-expanded={open}
        className="popover-trigger"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <em>{props.label}</em>
        <strong>{props.value}</strong>
        <ChevronDown size={14} />
      </button>
      {open && (
        <div className="popover-panel" id={panelId} role="dialog" aria-label={props.label}>
          {typeof props.children === "function" ? props.children(close) : props.children}
        </div>
      )}
    </div>
  );
}
