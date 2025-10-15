import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../auth';

type BatteryLine = { pcs?: number; weight_kg?: number; price_ron?: number };
type BatterySummaryLine = {
  key: string;
  label: string;
  qty_display: string;   // ex: "3 buc / 12.5 kg"
  rate_display: string;  // ex: "250.00 lei" (valoarea liniei)
  line_total: number;    // pentru siguranță, tot valoarea liniei
};

type RecyclingDetail = {
  recycling_id: string;
  recycler_company_id: string;
  recycler_company_name?: string | null;
  status: 'PENDING' | 'VALIDATED';
  batteries: Record<string, BatteryLine>;
  batteries_summary?: BatterySummaryLine[];
  total_weight: number;
  total_cost: number;
  created_at?: string | null;
  validated_at?: string | null;
};

export default function BaseRecyclingReview() {
  const { user } = useAuth();
  const { id = '' } = useParams<{ id: string }>();
  const [data, setData] = useState<RecyclingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const res = await api.getRecycling(id);
        if (alive) setData(res as unknown as RecyclingDetail);
      } catch (e: any) {
        if (alive) setErr(e.message || 'Eroare la încărcare');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [id]);

  const lines: BatterySummaryLine[] = useMemo(() => {
    if (!data) return [];
    if (data.batteries_summary && data.batteries_summary.length) {
      return data.batteries_summary;
    }
    // fallback dacă serverul nu trimite batteries_summary
    const out: BatterySummaryLine[] = [];
    Object.entries(data.batteries || {}).forEach(([key, v]) => {
      const pcs = v?.pcs ?? 0;
      const kg = v?.weight_kg ?? 0;
      const val = +(v?.price_ron ?? 0);
      const qtyBits: string[] = [];
      if (pcs > 0) qtyBits.push(`${pcs} buc`);
      if (kg > 0) qtyBits.push(`${fmt2(kg)} kg`);
      out.push({
        key,
        label: key,
        qty_display: qtyBits.join(' / ') || '-',
        rate_display: val > 0 ? `${fmt2(val)} lei` : '-',
        line_total: val,
      });
    });
    return out;
  }, [data]);

  const canValidate = user?.role === 'BASE' && data?.status === 'PENDING';

  const onValidate = async () => {
    if (!data) return;
    setValidating(true);
    try {
      const updated = await api.validateRecycling(data.recycling_id);
      // sincronizează statusul în UI
      setData((prev) => prev ? { ...prev, status: updated.status, validated_at: updated.validated_at } : prev);
    } catch (e: any) {
      alert(e.message || 'Nu s-a putut valida reciclarea');
    } finally {
      setValidating(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '32px auto', padding: 16 }}>
      <h2 style={{ marginBottom: 8 }}>Reciclare – Review (BAZĂ)</h2>

      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: 'crimson' }}>{err}</div>}
      {!loading && !err && data && (
        <>
          <div style={{ marginBottom: 12, color: '#555' }}>
            <div><b>Reciclator:</b> {data.recycler_company_name || data.recycler_company_id}</div>
            <div>
              <b>Status:</b> <StatusBadge status={data.status} />
            </div>
            <div>
              <small>
                Creată: {fmtDate(data.created_at)}
                {data.validated_at ? ` · Validată: ${fmtDate(data.validated_at)}` : ''}
              </small>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <th style={th}>Tip baterie</th>
                <th style={th}>Cantitate (buc / kg)</th>
                <th style={th}>Valoare linie (lei)</th>
              </tr>
            </thead>
            <tbody>
              {lines.length === 0 ? (
                <tr><td colSpan={3} style={{ padding: 12, color: '#666' }}>Nu există linii.</td></tr>
              ) : (
                lines.map((ln) => (
                  <tr key={ln.key} style={{ borderBottom: '1px solid #f3f3f3' }}>
                    <td style={td}>{ln.label}</td>
                    <td style={td}>{ln.qty_display}</td>
                    <td style={td}>{ln.rate_display}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td style={{ ...td, fontWeight: 600 }}>Greutate totală</td>
                <td style={td}>{fmt2(data.total_weight)} kg</td>
                <td style={td}></td>
              </tr>
              <tr>
                <td style={{ ...td, fontWeight: 600 }}>Cost total</td>
                <td style={td}></td>
                <td style={{ ...td, fontWeight: 700 }}>{fmt2(data.total_cost)} lei</td>
              </tr>
            </tfoot>
          </table>

          <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
            <button
              onClick={onValidate}
              disabled={!canValidate || validating}
              style={{
                padding: '10px 16px',
                background: canValidate ? '#1677ff' : '#bcd3ff',
                color: '#fff',
                border: 0, borderRadius: 6, cursor: canValidate ? 'pointer' : 'not-allowed'
              }}
            >
              {validating ? 'Se validează…' : 'Validează'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: 'PENDING' | 'VALIDATED' }) {
  const bg = status === 'VALIDATED' ? '#0a7' : '#d88400';
  return (
    <span style={{ background: bg, color: '#fff', padding: '2px 8px', borderRadius: 999 }}>
      {status}
    </span>
  );
}

const th: React.CSSProperties = { textAlign: 'left', padding: 10, fontWeight: 600, color: '#444' };
const td: React.CSSProperties = { padding: 10, verticalAlign: 'top' };

function fmt2(n: number | null | undefined) {
  const v = Number(n ?? 0);
  return v.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(s?: string | null) {
  if (!s) return '-';
  try {
    return new Date(s).toLocaleString('ro-RO');
  } catch { return s; }
}
