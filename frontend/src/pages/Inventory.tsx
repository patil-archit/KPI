import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Pill } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

export default function Inventory() {
  const { data, loading, error } = useApi<any[]>(() => api.get("/api/erp/inventory"), []);
  const cats = [...new Set(data?.map((m) => m.category) || [])];
  return (
    <div>
      <PageHead title="Inventory" sub="MMBE · stock on hand, Plant 1000" />
      <Loading loading={loading} error={error}>
        {cats.map((cat) => (
          <div key={cat} className="mb-5">
            <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">{cat}</div>
            <div className="card overflow-hidden">
              <table className="w-full">
                <thead><tr>{["Code", "Material", "Location", "On hand", "Reorder pt", ""].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                <tbody>
                  {data?.filter((m) => m.category === cat).map((m) => (
                    <tr key={m.code} className="hover:bg-slate-50">
                      <td className="td font-mono text-xs text-brand-700">{m.code}</td>
                      <td className="td">{m.name}</td>
                      <td className="td text-xs text-slate-500">{m.location}</td>
                      <td className="td tabular-nums">{m.stock.toLocaleString()} {m.uom}</td>
                      <td className="td tabular-nums text-slate-500">{m.reorder_point.toLocaleString()}</td>
                      <td className="td">{m.below_reorder && <Pill tone="warn">Below reorder</Pill>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </Loading>
    </div>
  );
}
