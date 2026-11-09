import { useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Pill } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

export default function Users() {
  const [q, setQ] = useState("");
  const { data, loading, error } = useApi<any[]>(() => api.get(`/api/erp/users?q=${encodeURIComponent(q)}`), [q]);
  return (
    <div>
      <PageHead title="Users & Roles" sub="SU01 · user directory"
        action={<input className="input w-64" placeholder="Search users…" value={q} onChange={(e) => setQ(e.target.value)} />} />
      <Loading loading={loading} error={error}>
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead><tr>{["Username", "Name", "Role", "Department", "Remote", "Enabled", "Last login"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>
              {data?.map((u) => (
                <tr key={u.username} className="hover:bg-slate-50">
                  <td className="td font-mono text-xs text-brand-700">{u.username}</td>
                  <td className="td">{u.full_name}</td>
                  <td className="td"><Pill tone="blue">{u.role}</Pill></td>
                  <td className="td text-xs text-slate-500">{u.department}</td>
                  <td className="td">{u.remote_access ? <Pill tone="warn">remote</Pill> : <span className="text-slate-300">—</span>}</td>
                  <td className="td">{u.enabled ? <Pill tone="ok">active</Pill> : <Pill tone="slate">disabled</Pill>}</td>
                  <td className="td text-xs text-slate-500">{u.last_login ? new Date(u.last_login).toLocaleString() : "never"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Loading>
    </div>
  );
}
