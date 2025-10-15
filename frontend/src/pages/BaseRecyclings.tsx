import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { RecyclingOut } from "../types/api";
import { useNavigate } from "react-router-dom";

export default function BaseRecyclings() {
  const [rows, setRows] = useState<RecyclingOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      setLoading(true); setErr(null);
      try { setRows(await api.listRecyclings()); }
      catch (e: any) { setErr(e?.message || "Eroare la listare"); }
      finally { setLoading(false); }
    })();
  }, []);

  
  return (
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 16 }}>
      <h2>Reciclări (parteneri RECICLATOR)</h2>
      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}

      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Reciclator</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Greutate</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Cost</th>
              <th style={{ width: 120, borderBottom: "1px solid #eee" }} />
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.recycling_id}>
                <td style={{ padding: 6 }}>{r.recycler_company_id}</td>
                <td style={{ padding: 6 }}>{r.total_weight ?? "-"}</td>
                <td style={{ padding: 6 }}>{r.total_cost ?? "-"}</td>
                <td style={{ padding: 6, textAlign: "right" }}>
                  {r.status === "PENDING" ? (
                    <button onClick={() => nav(`/recyclings/${r.recycling_id}/review`)}>
                      Validează
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!loading && !rows.length && <div className="muted">Nu există reciclări.</div>}
    </div>
  );
}
