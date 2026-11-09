import React from "react";
import { Spinner } from "../lib/ui";

export function PageHead({ title, sub, action }: { title: string; sub?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between mb-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">{title}</h1>
        {sub && <p className="text-sm text-slate-500">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

export function Loading({ loading, error, children }: { loading: boolean; error: string | null; children: React.ReactNode }) {
  if (loading) return <div className="p-10 grid place-items-center"><Spinner /></div>;
  if (error) return <div className="card p-4 text-sm text-status-high">⚠ {error}</div>;
  return <>{children}</>;
}
