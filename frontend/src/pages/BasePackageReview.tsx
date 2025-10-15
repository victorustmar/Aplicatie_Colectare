import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { PackageOut } from '../types/api';
import { LABELS } from '../features/rates';

export default function BasePackageReview() {
  const { id = '' } = useParams();
  const nav = useNavigate();

  const [row, setRow] = useState<PackageOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setErr(null); setLoading(true);
    try {
      const data = await api.getPackage(id);
      setRow(data as PackageOut);
    } catch (e: any) {
      setErr(e?.message || 'Nu s-a găsit pachetul');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const lines = useMemo(() => {
    if (!row?.batteries) return [];
    return Object.entries(row.batteries).map(([key, v]: any) => {
      const pcs = Number(v?.pcs || 0);
      const kg  = Number(v?.weight_kg || 0);
      const ron = Number(v?.price_ron || 0);
      const qty = [];
      if (pcs > 0) qty.push(`${pcs} buc`);
      if (kg  > 0) qty.push(`${kg.toFixed(2)} kg`);
      return {
        key,
        label: LABELS[key] || key,
        qty_display: qty.length ? qty.join(' / ') : '-',
        line_total: ron,
      };
    });
  }, [row]);

  const validate = async () => {
    setSaving(true); setErr(null);
    try {
      const updated = await api.validatePackage(id);
      setRow(updated as PackageOut);
    } catch (e: any) {
      setErr(e?.message || 'Validarea a eșuat');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 920, margin:'24px auto', padding:16 }}>
      <button onClick={() => nav(-1)} style={{ marginBottom: 12 }}>‹ Înapoi</button>
      <h2>Review pachet</h2>

      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color:'crimson' }}>{err}</div>}

      {row && (
        <>
          <div style={{ margin: '8px 0', color:'#555' }}>
            <b>Producător:</b> {row.producer_name ?? row.producer_company_id}
            <br/>
            <b>Status:</b> {badge(row.status)}
            <br/>
            <b>Creat:</b> {fmtDate(row.created_at)}{row.validated_at ? <> · <b>Validat:</b> {fmtDate(row.validated_at)}</> : null}
          </div>

          <table style={{ width:'100%', marginTop: 12 }}>
            <thead>
              <tr>
                <th align="left">Tip</th>
                <th align="left">Cantitate</th>
                <th align="right">Valoare linie (lei)</th>
              </tr>
            </thead>
            <tbody>
              {lines.map(l => (
                <tr key={l.key}>
                  <td>{l.label}</td>
                  <td>{l.qty_display}</td>
                  <td style={{ textAlign:'right' }}>{fmtMoney(l.line_total)}</td>
                </tr>
              ))}
              <tr style={{ background:'#fafafa', fontWeight:600 }}>
                <td />
                <td style={{ textAlign:'right', paddingRight: 8 }}>Total</td>
                <td style={{ textAlign:'right' }}>{fmtMoney(Number(row.total_cost || 0))}</td>
              </tr>
            </tbody>
          </table>

          <div style={{ marginTop: 16 }}>
            <button disabled={row.status === 'VALIDATED' || saving} onClick={validate}>
              {saving ? 'Se validează…' : row.status === 'VALIDATED' ? 'Deja validat' : 'Validează'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function badge(s?: string|null) {
  const color = s === 'VALIDATED' ? '#0a7' : s === 'PENDING' ? '#d88400' : '#888';
  return <span style={{ background: color, color:'#fff', padding:'2px 8px', borderRadius:999 }}>{s}</span>;
}
function fmtMoney(n: number) {
  return Number(n || 0).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(d?: any) {
  if (!d) return '-';
  return new Date(d).toLocaleString('ro-RO');
}
