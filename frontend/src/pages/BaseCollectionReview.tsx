import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";
import {
  PORTABLE_KEYS, KG_KEYS, LABELS,
  PORTABLE_RATES, PORTABLE_WEIGHTS_KG, KG_RATES,
} from "../features/rates";

const round2 = (n: number) => Math.round(n * 100) / 100;
const fmt = (n: number) => n.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

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
    const lineTotals: Record<string, number> = {};
    let portableSubtotal = 0;
    let kgSubtotal = 0;

    for (const k of PORTABLE_KEYS) {
      const qty = Number(b[k] || 0);
      const val = qty * PORTABLE_RATES[k];
      lineTotals[k] = round2(val);
      portableSubtotal += val;
    }
    for (const k of KG_KEYS) {
      const w = Number(b[k] || 0);
      const val = w * KG_RATES[k];
      lineTotals[k] = round2(val);
      kgSubtotal += val;
    }
    portableSubtotal = round2(portableSubtotal);
    kgSubtotal = round2(kgSubtotal);
    const subtotal = round2(portableSubtotal + kgSubtotal);

    return { lineTotals, portableSubtotal, kgSubtotal, subtotal };
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
        setErr(
          `${detail} · Completează profilul de facturare și setările de facturi înainte de validare.`
        );
      } else {
        setErr(e.message || "Eroare la validare");
      }
    } finally {
      setValidating(false);
    }
  };

  if (loading) return <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>Se încarcă…</div>;
  if (err) return <div style={{ maxWidth: 980, margin: "24px auto", padding: 16, color: "crimson" }}>{err}</div>;
  if (!row || !calc) return null;

  const b = row.batteries || {};

  return (
    <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>
      <h2>Revizuire colectare</h2>
      <div style={{ color: "#555", marginBottom: 12 }}>
        <div><b>ID:</b> {row.collection_id}</div>
        <div><b>Client:</b> {row.client_company_id}</div>
        <div><b>Status curent:</b> {row.status}</div>
        <div><b>Creată la:</b> {new Date(row.created_at).toLocaleString()}</div>
      </div>

      {/* Portable */}
      <section>
        <h3>Baterii portabile (buc)</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Tip</th>
              <th>Tarif (lei/buc)</th>
              <th>Greutate (kg/buc)</th>
              <th>Cantitate</th>
              <th>Valoare (lei)</th>
            </tr>
          </thead>
          <tbody>
            {PORTABLE_KEYS.map(k => (
              <tr key={k}>
                <td>{LABELS[k]}</td>
                <td style={{ textAlign: "center" }}>{PORTABLE_RATES[k]}</td>
                <td style={{ textAlign: "center" }}>{PORTABLE_WEIGHTS_KG[k]}</td>
                <td style={{ textAlign: "center" }}>{Number(b[k] || 0)}</td>
                <td style={{ textAlign: "right" }}>{fmt(calc.lineTotals[k] || 0)}</td>
              </tr>
            ))}
            <tr style={{ background: "#fafafa", fontWeight: 600 }}>
              <td colSpan={4} style={{ textAlign: "right", paddingRight: 8 }}>Subtotal portabile</td>
              <td style={{ textAlign: "right" }}>{fmt(calc.portableSubtotal)} lei</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* Auto & Industrial */}
      <section style={{ marginTop: 18 }}>
        <h3>Baterii auto și industriale (kg)</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Tip</th>
              <th>Tarif (lei/kg)</th>
              <th>Cantitate (kg)</th>
              <th>Valoare (lei)</th>
            </tr>
          </thead>
          <tbody>
            {KG_KEYS.map(k => (
              <tr key={k}>
                <td>{LABELS[k]}</td>
                <td style={{ textAlign: "center" }}>{KG_RATES[k]}</td>
                <td style={{ textAlign: "center" }}>{Number(b[k] || 0)}</td>
                <td style={{ textAlign: "right" }}>{fmt(calc.lineTotals[k] || 0)}</td>
              </tr>
            ))}
            <tr style={{ background: "#fafafa", fontWeight: 600 }}>
              <td colSpan={3} style={{ textAlign: "right", paddingRight: 8 }}>Subtotal auto & industriale</td>
              <td style={{ textAlign: "right" }}>{fmt(calc.kgSubtotal)} lei</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* Totals */}
      <div style={{ display: "flex", gap: 24, alignItems: "center", marginTop: 16 }}>
        <div><strong>Greutate totală (din server):</strong> {row.total_weight ?? 0} kg</div>
        <div><strong>Subtotal estimat (calc):</strong> {fmt(calc.subtotal)} lei</div>
        <div><strong>Cost total (din server):</strong> {fmt(Number(row.total_cost || 0))} lei</div>
      </div>

      {/* Actions */}
      <div style={{ marginTop: 18, display: "flex", gap: 12 }}>
        <button onClick={goBack}>Nu valida</button>
        <button onClick={doValidate} disabled={validating || row.status === "VALIDATED"}>
          {validating ? "Se validează…" : "Validează"}
        </button>
      </div>

      {/* Helpful links if 422 */}
      {err && err.includes("profilul") && (
        <div style={{ marginTop: 10 }}>
          <Link to="/billing/profile">→ Completează profilul de facturare</Link>
          {" · "}
          <Link to="/billing/settings">→ Setări facturi</Link>
        </div>
      )}
    </div>
  );
}
