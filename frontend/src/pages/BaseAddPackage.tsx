import React, { useState } from 'react';
import { api, type BatteryLine } from '../api/client';

export default function BaseAddPackage() {
  const [producerId, setProducerId] = useState('');
  const [bats, setBats] = useState<Record<string, BatteryLine>>({
    Alkaline: { pcs: 0, weight_kg: 0, price_ron: 0 },
    LiIon: { pcs: 0, weight_kg: 0, price_ron: 0 },
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const setField = (k: string, f: keyof BatteryLine, v: string) => {
    setBats((old) => ({
      ...old,
      [k]: { ...old[k], [f]: v === '' ? undefined : Number(v) },
    }));
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setMsg(null);
    try {
      const res = await api.createPackage({ producer_company_id: producerId.trim(), batteries: bats });
      setMsg(`Creat pachet ${res.package_id}`);
    } catch (e: any) {
      setMsg(e.message || 'Eroare');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '32px auto', padding: 16 }}>
      <h2>Adaugă pachet (către PRODUCĂTOR)</h2>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, maxWidth: 500 }}>
        <input
          placeholder="producer_company_id"
          value={producerId}
          onChange={(e) => setProducerId(e.target.value)}
          required
          style={{ padding: 10, border: '1px solid #ddd', borderRadius: 6 }}
        />

        {Object.keys(bats).map((k) => (
          <div key={k} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 8 }}>
            <input value={k} readOnly style={{ padding: 10, border: '1px solid #eee', borderRadius: 6 }} />
            <input type="number" placeholder="buc" onChange={e=>setField(k,'pcs',e.target.value)} />
            <input type="number" placeholder="kg" step="0.01" onChange={e=>setField(k,'weight_kg',e.target.value)} />
            <input type="number" placeholder="lei" step="0.01" onChange={e=>setField(k,'price_ron',e.target.value)} />
          </div>
        ))}

        <button disabled={loading} type="submit" style={{ padding: '10px 14px' }}>
          {loading ? 'Se salvează…' : 'Creează pachet'}
        </button>
      </form>
      {msg && <div style={{ marginTop: 8 }}>{msg}</div>}
    </div>
  );
}
