import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";
import { Link } from "react-router-dom";

export default function BaseCollections() {
  const [rows, setRows] = useState<CollectionOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const data = await api.listCollections();
      setRows(data);
    } catch (e: any) {
      setErr(e?.message || "Eroare la listare");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const validate = async (id: string) => {
    setErr(null); setInfo(null);
    try {
      await api.validateCollection(id);
      setInfo("Colectarea a fost validată și s-a generat factura.");
      await load();
    } catch (e: any) {
      // feedback 422 → link către profile/settings
      if (e.status === 422) {
        const detail = e?.data?.detail || e.message || "Date de facturare incomplete.";
        setErr(
          <>
            <div style={{ marginBottom: 8 }}>{detail}</div>
            <div>
              <Link to="/billing/profile">→ Completează profilul de facturare</Link>
              {" · "}
              <Link to="/billing/settings">→ Setări facturi (serie/număr)</Link>
            </div>
          </> as any
        );
      } else {
        setErr(e.message || "Eroare la validare");
      }
    }
  };

  return (
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 16 }}>
      <h2>Colectări clienți</h2>
      {loading && <div>Se încarcă…</div>}
      {info && <div style={{ color: "seagreen", marginBottom: 8 }}>{info}</div>}
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}
      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead><tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>ID</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Client</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Greutate</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Cost</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Acțiuni</th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.collection_id}>
                <td style={{ padding: 6 }}>{r.collection_id}</td>
                <td style={{ padding: 6 }}>{r.client_company_id}</td>
                <td style={{ padding: 6 }}>{r.status}</td>
                <td style={{ padding: 6 }}>{r.total_weight ?? "-"}</td>
                <td style={{ padding: 6 }}>{r.total_cost ?? "-"}</td>
                <td style={{ padding: 6 }}>
                  {r.status === "PENDING" ? (
                    <button onClick={() => validate(r.collection_id)}>Validează</button>
                  ) : "VALIDATED"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && !rows.length && <div className="muted">Nu există colectări.</div>}
    </div>
  );
}
