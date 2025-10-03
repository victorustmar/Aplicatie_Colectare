import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { InvoiceOut } from "../types/api";

export default function BaseInvoices() {
  const [rows, setRows] = useState<InvoiceOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.listInvoices();
        setRows(data);
      } catch (e: any) {
        setErr(e?.message || "Eroare la listare facturi");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const download = async (id: string) => {
    try {
      await api.downloadInvoicePdf(id);
    } catch (e: any) {
      alert(e?.message || "Eroare la descărcare PDF");
    }
  };

  return (
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 16 }}>
      <h2>Facturi</h2>
      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead><tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Număr</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Emisă</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Scadență</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Subtotal</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>TVA</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Total</th>
            <th></th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.invoice_id}>
                <td style={{ padding: 6 }}>{r.invoice_number}</td>
                <td style={{ padding: 6 }}>{r.issue_date}</td>
                <td style={{ padding: 6 }}>{r.due_date}</td>
                <td style={{ padding: 6 }}>{r.subtotal} {r.currency}</td>
                <td style={{ padding: 6 }}>{r.vat_amount} {r.currency}</td>
                <td style={{ padding: 6 }}><b>{r.total} {r.currency}</b></td>
                <td style={{ padding: 6 }}>
                  <button onClick={() => download(r.invoice_id)}>Descarcă PDF</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && !rows.length && <div className="muted">Nu există facturi.</div>}
    </div>
  );
}
