import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";
import { BATTERY_LABELS, BATTERY_SECTIONS } from "../lib/batteries";

const nf2 = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function toNum(x: number | string | null | undefined): number {
  if (x === null || x === undefined) return 0;
  if (typeof x === "number") return Number.isFinite(x) ? x : 0;
  const n = Number(x);
  return Number.isFinite(n) ? n : 0;
}

export default function BaseCollectionReview() {
  const { id = "" } = useParams<{ id: string }>();
  const nav = useNavigate();

  const [row, setRow] = useState<CollectionOut | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true); setErr(null);
      try {
        const data = await api.getCollection(id);
        setRow(data);
      } catch (e: any) {
        setErr(e?.message || "Eroare la încărcare");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const calc = useMemo(() => {
    if (!row) return null;
    const b = row.batteries || {};
    let subtotalLei = 0;
    let totalKg = 0;

    for (const [_, v] of Object.entries<any>(b)) {
      const kg = toNum(v?.weight_kg);
      const lei = toNum(v?.price_ron);
      subtotalLei += lei;
      totalKg += kg;
    }
    return {
      subtotalLei,
      totalKg,
    };
  }, [row]);

  const goBack = () => nav("/collections");

  const doValidate = async () => {
    if (!row) return;
    setErr(null); setValidating(true);
    try {
      await api.validateCollection(row.collection_id);
      goBack();
    } catch (e: any) {
      if (e.status === 422) {
        const detail = e?.data?.detail || e.message || "Date de facturare incomplete.";
        setErr(`${detail} · Completează profilul de facturare și setările de facturi înainte de validare.`);
      } else {
        setErr(e.message || "Eroare la validare");
      }
    } finally {
      setValidating(false);
    }
  };

  if (loading) return <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>Se încarcă…</div>;
  if (err && !row) return <div style={{ maxWidth: 980, margin: "24px auto", padding: 16, color: "crimson" }}>{err}</div>;
  if (!row || !calc) return null;

  const b = row.batteries || {};
  const statusLabel = row.status === "VALIDATED" ? "Validată" : "În așteptare";

  return (
    <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>
      <h2>Revizuire colectare</h2>
      <div style={{ color: "#555", marginBottom: 12 }}>
        <div><b>ID:</b> {row.collection_id}</div>
        <div><b>Client:</b> {row.client_company_id}</div>
        <div><b>Status curent:</b> {statusLabel}</div>
        <div><b>Creată la:</b> {new Date(row.created_at).toLocaleString()}</div>
      </div>

      {/* Secțiuni: Portabile 1&2 / Auto 3 / Industriale 4 */}
      {BATTERY_SECTIONS.map(section => (
        <section key={section.id} style={{ marginTop: 18 }}>
          <h3>{section.title}</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Tip</th>
                <th style={{ textAlign: "center", borderBottom: "1px solid #eee", padding: 6 }}>Nr. bucăți</th>
                <th style={{ textAlign: "center", borderBottom: "1px solid #eee", padding: 6 }}>Greutate totală (kg)</th>
                <th style={{ textAlign: "right", borderBottom: "1px solid #eee", padding: 6 }}>Valoare (lei)</th>
              </tr>
            </thead>
            <tbody>
              {section.keys.map(k => {
                const ln: any = (b as any)[k] || {};
                const pcs = toNum(ln?.pcs);
                const kg = toNum(ln?.weight_kg);
                const lei = toNum(ln?.price_ron);
                return (
                  <tr key={k}>
                    <td style={{ padding: 6 }}>{BATTERY_LABELS[k] || k}</td>
                    <td style={{ textAlign: "center", padding: 6 }}>{pcs ? pcs : 0}</td>
                    <td style={{ textAlign: "center", padding: 6 }}>{nf2.format(kg)}</td>
                    <td style={{ textAlign: "right", padding: 6 }}>{nf2.format(lei)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}

      {/* Totaluri */}
      <div style={{ display: "flex", gap: 24, alignItems: "center", marginTop: 16 }}>
        <div><strong>Greutate totală (din server):</strong> {row.total_weight ?? 0} kg</div>
        <div><strong>Subtotal (calcul local):</strong> {nf2.format(calc.subtotalLei)} lei</div>
        <div><strong>Cost total (din server):</strong> {typeof row.total_cost === "number" || typeof row.total_cost === "string" ? nf2.format(Number(row.total_cost)) : "0,00"} lei</div>
      </div>

      {/* Acțiuni */}
      <div style={{ marginTop: 18, display: "flex", gap: 12 }}>
        <button onClick={goBack}>Nu valida</button>
        <button onClick={doValidate} disabled={validating || row.status === "VALIDATED"}>
          {validating ? "Se validează…" : "Validează"}
        </button>
      </div>

      {/* Linkuri utile dacă apare 422 */}
      {err && (
        <div style={{ marginTop: 10, color: "crimson" }}>
          {err}
          <div style={{ marginTop: 6 }}>
            <Link to="/billing/profile">→ Completează profilul de facturare</Link>
            {" · "}
            <Link to="/billing/settings">→ Setări facturi</Link>
          </div>
        </div>
      )}
    </div>
  );
}
