import React, { createContext, useContext, useState, useCallback } from "react";

// ---------------- toast ----------------
type Toast = { id: number; text: string; kind: "ok" | "err" | "info" };
const ToastCtx = createContext<(text: string, kind?: Toast["kind"]) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, kind: Toast["kind"] = "info") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, text, kind }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 w-80">
        {items.map((t) => (
          <div key={t.id}
            className={`px-4 py-3 rounded shadow-lg text-sm text-white ${
              t.kind === "ok" ? "bg-status-ok" : t.kind === "err" ? "bg-status-high" : "bg-slate-800"}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ---------------- small bits ----------------
export function Pill({ tone, children }: { tone: string; children: React.ReactNode }) {
  const map: Record<string, string> = {
    ok: "bg-green-100 text-green-800", warn: "bg-orange-100 text-orange-800",
    high: "bg-red-100 text-red-800", crit: "bg-purple-100 text-purple-800",
    info: "bg-sky-100 text-sky-800", slate: "bg-slate-100 text-slate-700",
    blue: "bg-brand-100 text-brand-800",
  };
  return <span className={`pill ${map[tone] || map.slate}`}>{children}</span>;
}

export function StatusDot({ tone }: { tone: string }) {
  const c: Record<string, string> = { ok: "bg-status-ok", warn: "bg-status-warn", high: "bg-status-high",
    crit: "bg-status-crit", info: "bg-status-info", slate: "bg-slate-400" };
  return <span className={`inline-block w-2 h-2 rounded-full ${c[tone] || c.slate}`} />;
}

export function Spinner() {
  return <div className="w-5 h-5 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin" />;
}

export function Modal({ open, onClose, title, children, wide }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode; wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className={`card ${wide ? "max-w-3xl" : "max-w-lg"} w-full max-h-[85vh] overflow-auto`}
        onClick={(e) => e.stopPropagation()}>
        <div className="card-h sticky top-0 bg-white">
          <div className="card-t">{title}</div>
          <button className="text-slate-400 hover:text-slate-700" onClick={onClose}>✕</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
