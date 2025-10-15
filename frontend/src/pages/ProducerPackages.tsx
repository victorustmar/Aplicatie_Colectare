import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { PackageOut } from '../types/api';

export default function ProducerPackages() {
  const [rows, setRows] = useState<PackageOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setErr(null); setLoading(true);
      try {
        const data = await api.listPackages();
        setRows(data as PackageOut[]);
      } catch (e: any) {
        setErr(e?.message || 'Eroare la încărcare pachete');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 1000, margin: '24px auto', padding: 16 }}>
      <h2>Pachetele mele</h2>
      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: 'crimson' }}>{err}</div>}
      {!loading && !err && (
        rows.length === 0 ? <div>Nu există pachete încă.</div> : (
          <table style={{ width:'100%', marginTop: 12 }}>
            <thead>
              <tr>
                <th align="left">Status</th>
                <th align="left">Greutate totală</th>
                <th align="left">Valoare totală</th>
                <th align="left">Creat la</th>
                <th align="left">Validat la</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.package_id}>
                  <td>{badge(r.status)}</td>
                  <td>{fmtNum(r.total_weight)} kg</td>
                  <td>{fmtNum(r.total_cost)} lei</td>
                  <td>{fmtDate(r.created_at)}</td>
                  <td>{r.validated_at ? fmtDate(r.validated_at) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  );
}

function badge(s?: string|null) {
  const color = s === 'VALIDATED' ? '#0a7' : s === 'PENDING' ? '#d88400' : '#888';
  return <span style={{ background: color, color:'#fff', padding:'2px 8px', borderRadius:999 }}>{s}</span>;
}
function fmtNum(v: any) {
  const n = Number(v || 0);
  return n.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(d?: any) {
  if (!d) return '-';
  return new Date(d).toLocaleString('ro-RO');
}
