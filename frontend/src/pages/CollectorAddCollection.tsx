import React, { useMemo, useState } from 'react';
import { api } from '../api/client';
import { LABELS, PORTABLE_KEYS, KG_KEYS } from '../features/rates';

// local UI types
type NumOrEmpty = number | '';
type Line = { pcs: NumOrEmpty; weight_kg: NumOrEmpty; price_ron: NumOrEmpty };
type BatteriesState = Record<string, Line>;

const ALL_KEYS = [...PORTABLE_KEYS, ...KG_KEYS];
const round2 = (n: number) => Math.round(n * 100) / 100;
const toNum = (v: NumOrEmpty) => (v === '' ? 0 : Number(v));
const fmt2 = (n: number) =>
  n === 0 ? '' : n.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CollectorAddCollection() {
  const [bats, setBats] = useState<BatteriesState>(() => {
    const init: BatteriesState = {};
    for (const k of ALL_KEYS) init[k] = { pcs: '', weight_kg: '', price_ron: '' };
    return init;
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const totals = useMemo(() => {
    let totalWeight = 0, totalCost = 0;
    for (const k of ALL_KEYS) {
      const ln = bats[k];
      totalWeight += toNum(ln.weight_kg);
      totalCost   += toNum(ln.price_ron);
    }
    return { totalWeight: round2(totalWeight), totalCost: round2(totalCost) };
  }, [bats]);

  const canSubmit = useMemo(
    () => ALL_KEYS.some(k => {
      const ln = bats[k];
      return toNum(ln.pcs) > 0 || toNum(ln.weight_kg) > 0 || toNum(ln.price_ron) > 0;
    }),
    [bats]
  );

 const onInt = (key: string, val: string) => {
  const s = val.trim();
  const num = Number(s.replace(',', '.')); // <-- always a number
  const valid = s !== '' && Number.isFinite(num) && num >= 0;
  setBats(p => ({
    ...p,
    [key]: { ...p[key], pcs: valid ? Math.floor(num) : '' }
  }));
};

const onFloat = (key: string, field: 'weight_kg' | 'price_ron', val: string) => {
  const s = val.trim();
  const num = Number(s.replace(',', '.')); // <-- always a number
  const valid = s !== '' && Number.isFinite(num) && num >= 0;
  setBats(p => ({
    ...p,
    [key]: { ...p[key], [field]: valid ? num : '' }
  }));
};


  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setOk(null);
    if (!canSubmit) { setErr('Completează cel puțin un câmp (> 0).'); return; }

    setSaving(true);
    try {
      const batteries: Record<string, { pcs?: number; weight_kg?: number; price_ron?: number }> = {};
      for (const k of ALL_KEYS) {
        const ln = bats[k];
        const pcs = toNum(ln.pcs), kg = toNum(ln.weight_kg), ron = toNum(ln.price_ron);
        if (pcs > 0 || kg > 0 || ron > 0) {
          batteries[k] = {};
          if (pcs > 0) batteries[k].pcs = pcs;
          if (kg > 0)  batteries[k].weight_kg = round2(kg);
          if (ron > 0) batteries[k].price_ron = round2(ron);
        }
      }

      // collector uses /collections (server uses claims.company_id)
      await api.createCollection({ batteries });
      setOk('Colectarea a fost creată.');
      const reset: BatteriesState = {};
      for (const k of ALL_KEYS) reset[k] = { pcs: '', weight_kg: '', price_ron: '' };
      setBats(reset);
    } catch (e: any) {
      setErr(e?.message || 'Eroare la creare colectare');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 980, margin: '24px auto', padding: 16 }}>
      <h2>Adaugă colectare</h2>

      <form onSubmit={submit} style={{ display: 'grid', gap: 18, marginTop: 12 }}>
        <section>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Tip</th>
                <th style={{ width: 150, textAlign: 'center' }}>Bucăți</th>
                <th style={{ width: 150, textAlign: 'center' }}>Greutate (kg)</th>
                <th style={{ width: 180, textAlign: 'center' }}>Valoare (lei)</th>
              </tr>
            </thead>
            <tbody>
              {ALL_KEYS.map(k => (
                <tr key={k}>
                  <td style={{ padding: 6 }}>{LABELS[k] || k}</td>
                  <td style={{ textAlign: 'center' }}>
                    <input type="number" min={0} step={1} placeholder="0"
                      value={bats[k].pcs === '' ? '' : bats[k].pcs}
                      onChange={e => onInt(k, e.target.value)} style={{ width: 120 }} />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <input type="number" min={0} step={0.01} placeholder="0.00"
                      value={bats[k].weight_kg === '' ? '' : bats[k].weight_kg}
                      onChange={e => onFloat(k, 'weight_kg', e.target.value)} style={{ width: 120 }} />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <input type="number" min={0} step={0.01} placeholder="0.00"
                      value={bats[k].price_ron === '' ? '' : bats[k].price_ron}
                      onChange={e => onFloat(k, 'price_ron', e.target.value)} style={{ width: 140 }} />
                  </td>
                </tr>
              ))}
              <tr style={{ background: '#fafafa', fontWeight: 600 }}>
                <td colSpan={2} />
                <td style={{ textAlign: 'right', paddingRight: 8 }}>Total greutate</td>
                <td style={{ textAlign: 'center' }}>{fmt2(totals.totalWeight)} kg</td>
              </tr>
              <tr style={{ background: '#fafafa', fontWeight: 600 }}>
                <td colSpan={2} />
                <td style={{ textAlign: 'right', paddingRight: 8 }}>Total valoare</td>
                <td style={{ textAlign: 'center' }}>{fmt2(totals.totalCost)} lei</td>
              </tr>
            </tbody>
          </table>
        </section>

        {err && <div style={{ color: 'crimson' }}>{err}</div>}
        {ok && <div style={{ color: 'seagreen' }}>{ok}</div>}

        <div>
          <button disabled={!canSubmit || saving} type="submit">
            {saving ? 'Se salvează…' : 'Creează'}
          </button>
        </div>
      </form>
    </div>
  );
}
