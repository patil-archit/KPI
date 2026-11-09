import { useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Modal } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

export default function Files() {
  const [share, setShare] = useState("corp");
  const { data, loading, error } = useApi<any[]>(() => api.get(`/api/eng/files?share=${share}`), [share]);
  const [doc, setDoc] = useState<any | null>(null);
  const openDoc = async (id: number) => setDoc(await api.get(`/api/eng/files/${id}`));

  const folders = [...new Set(data?.map((d) => d.folder) || [])];
  return (
    <div>
      <PageHead title="Document Share" sub="Corporate and engineering file shares"
        action={
          <div className="flex gap-1 bg-slate-100 p-1 rounded">
            {[["corp", "Corporate"], ["eng-ws", "Engineering WS"]].map(([v, l]) => (
              <button key={v} onClick={() => setShare(v)}
                className={`px-3 py-1 rounded text-sm ${share === v ? "bg-white shadow-sm font-medium text-brand-700" : "text-slate-500"}`}>{l}</button>
            ))}
          </div>} />
      <Loading loading={loading} error={error}>
        {folders.map((f) => (
          <div key={f} className="mb-4">
            <div className="text-xs font-mono text-slate-400 mb-1">{f}</div>
            <div className="card divide-y divide-slate-100">
              {data?.filter((d) => d.folder === f).map((d) => (
                <button key={d.id} onClick={() => openDoc(d.id)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 text-left">
                  <span className="text-slate-400">▦</span>
                  <span className="flex-1 text-sm text-slate-700">{d.name}</span>
                  <span className="text-xs text-slate-400">{d.owner}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </Loading>
      <Modal open={!!doc} onClose={() => setDoc(null)} title={doc?.name || ""} wide>
        <pre className="text-xs font-mono whitespace-pre-wrap bg-slate-50 p-4 rounded border border-slate-200 text-slate-700">
          {doc?.content}
        </pre>
      </Modal>
    </div>
  );
}
