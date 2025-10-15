import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { CollectionOut } from '../types/api';

export default function CollectorCollections() {
  const [rows, setRows] = useState<CollectionOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setErr(null); setLoading(true);
      try {
        const data = await api.listCollections();
        setRows(data);
      } catch (e: any) {
        setErr(e?.message || 'Eroare la încărcarea colectărilor');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 980, margin: '24px auto', padding: 16 }}>
      <h2>Colectările mele</h2>

      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: 'crimson' }}>{err}</div>}
      {!loading && !err && (
        rows.length === 0 ? <div>Nu există colectări încă.</div> : (
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
            <thead>
              <tr>
                <th align="left">Data</th>
                <th align="left">Status</th>
                <th align="right">Greutate totală (kg)</th>
                <th align="right">Valoare totală (lei)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.collection_id}>
                  <td>{new Date(r.created_at).toLocaleString('ro-RO')}</td>
                  <td>{badge(r.status)}</td>
                  <td align="right">{num(r.total_weight)} </td>
                  <td align="right">{num(r.total_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  );
}

function num(v: any) {
  const n = typeof v === 'string' ? Number(v) : (v ?? 0);
  if (!isFinite(n)) return '-';
  return n.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function badge(s: string) {
  const color = s === 'VALIDATED' ? '#0a7' : '#d88400';
  return <span style={{ background: color, color:'#fff', padding:'2px 8px', borderRadius: 999 }}>{s}</span>;
}
