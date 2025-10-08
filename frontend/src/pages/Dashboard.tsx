import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { AnafSummary, CollaborationOut } from '../types/api';
import { useAuth } from '../auth';
const PUBLIC_APP = (import.meta.env.VITE_PUBLIC_APP_ORIGIN || window.location.origin).replace(/\/$/, '');
export default function Dashboard() {
  const { logout } = useAuth();

  


  // CUI Lookup (existent)
  const [cui, setCui] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<AnafSummary | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  // Invite
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMsg, setInviteMsg] = useState<string | null>(null);
    const [inviteUrl, setInviteUrl] = useState<string | null>(null); // 👈 păstrăm linkul curat
  const [inviteLoading, setInviteLoading] = useState(false);

  // Collaborations list
  const [collabs, setCollabs] = useState<CollaborationOut[]>([]);
  const [collabsLoading, setCollabsLoading] = useState(false);
  const [collabsErr, setCollabsErr] = useState<string | null>(null);

  const submitLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setData(null); setInviteMsg(null); setLoading(true);
    try {
      const res = await api.anafLookup(cui);
      setData(res);
    } catch (e: any) {
      setErr(e.message || 'Eroare la interogare ANAF');
    } finally {
      setLoading(false);
    }
  };

  const submitInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMsg(null);
    setInviteUrl(null);
    setInviteLoading(true);
    try {
      const cuiValue = data?.cui || cui;
      const res = await api.inviteCompany(cuiValue || '', inviteEmail);

      // 👇 extragem tokenul din răspuns
      const token =
        (res as any).invite_code
        ?? (res.invite_url?.split('/invite/')[1] ?? '')
        ?? '';

      if (!token) throw new Error('Nu s-a putut obține tokenul de invitație');

      // 👇 construim linkul public
      const url = `${PUBLIC_APP}/invite/${token}`;

      setInviteMsg('Invitație creată.');
      setInviteUrl(url);

      // reîncarcă lista colaborări
      await loadCollabs();
    } catch (e: any) {
      setInviteMsg(e.message || 'Eroare la trimiterea invitației');
    } finally {
      setInviteLoading(false);
    }
  };

  const loadCollabs = async () => {
    setCollabsErr(null); setCollabsLoading(true);
    try {
      const rows = await api.listCompanies();
      setCollabs(rows);
    } catch (e: any) {
      setCollabsErr(e.message || 'Eroare la încărcarea listelor de colaborări');
    } finally {
      setCollabsLoading(false);
    }
  };

  useEffect(() => { loadCollabs(); }, []);

  return (
    <div style={{ maxWidth: 1000, margin: '32px auto', padding: 16 }}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h2>Dashboard (BASE)</h2>
        <button onClick={logout}>Logout</button>
      </div>

      {/* CUI Lookup */}
      <section style={{ marginTop: 16, border:'1px solid #eee', borderRadius:8, padding:12 }}>
        <h3>CUI Lookup</h3>
        <form onSubmit={submitLookup} style={{ display:'flex', gap: 8, marginTop: 12 }}>
          <input
            placeholder="CUI sau RO+CUI"
            value={cui}
            onChange={e=>setCui(e.target.value)}
            style={{ flex:1, padding: 10, border:'1px solid #ddd', borderRadius:6 }}
          />
          <button disabled={loading} type="submit" style={{ padding: '10px 14px' }}>
            {loading ? 'Caută…' : 'Caută'}
          </button>
        </form>
        {err && <div style={{ color:'crimson', marginTop: 12 }}>{err}</div>}

        {data && (
          <div style={{ marginTop: 16 }}>
            <table>
              <tbody>
                <tr><td style={{padding:4}}>Denumire</td><td style={{padding:4}}><b>{data.denumire ?? '-'}</b></td></tr>
                <tr><td style={{padding:4}}>CUI</td><td style={{padding:4}}>{data.cui ?? '-'}</td></tr>
                <tr><td style={{padding:4}}>Adresă</td><td style={{padding:4}}>{data.address ?? '-'}</td></tr>
                <tr><td style={{padding:4}}>Telefon</td><td style={{padding:4}}>{data.phone ?? '-'}</td></tr>
                <tr><td style={{padding:4}}>Inactiv</td><td style={{padding:4}}>{fmtBool(data.inactive)}</td></tr>
                <tr><td style={{padding:4}}>e-Factura</td><td style={{padding:4}}>{fmtBool(data.e_invoice)}</td></tr>
              </tbody>
            </table>

            <div style={{ marginTop: 12 }}>
              <button onClick={()=>setShowRaw(v=>!v)} style={{ padding:'6px 10px' }}>
                {showRaw ? 'Ascunde Raw JSON' : 'Arată Raw JSON'}
              </button>
              {showRaw && (
                <pre style={{ background:'#f7f7f7', padding:12, borderRadius:6, overflow:'auto', marginTop:8 }}>
                  {JSON.stringify(data.raw, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Trimite invitație */}
      <section style={{ marginTop: 16, border:'1px solid #eee', borderRadius:8, padding:12 }}>
        <h3>Trimite invitație către firmă</h3>
        <form onSubmit={submitInvite} style={{ display:'grid', gridTemplateColumns:'2fr 3fr auto', gap: 8, alignItems:'center', marginTop: 12 }}>
          <input
            placeholder="CUI (dacă e gol, se folosește cel de mai sus)"
            value={data?.cui ?? cui}
            onChange={e=>setCui(e.target.value)}
            style={{ padding: 10, border:'1px solid #ddd', borderRadius:6 }}
          />
          <input
            placeholder="Email destinatar"
            value={inviteEmail}
            onChange={e=>setInviteEmail(e.target.value)}
            type="email"
            required
            style={{ padding: 10, border:'1px solid #ddd', borderRadius:6 }}
          />
          <button disabled={inviteLoading} type="submit" style={{ padding: '10px 14px' }}>
            {inviteLoading ? 'Se trimite…' : 'Trimite invitație'}
          </button>
        </form>

        {(inviteMsg || inviteUrl) && (
          <div style={{ marginTop: 10 }}>
            <small>
              {inviteMsg} {inviteUrl && (
                <>
                  Link: <a href={inviteUrl} target="_blank" rel="noreferrer">{inviteUrl}</a>&nbsp;
                  <button onClick={() => copyText(inviteUrl)} style={{ padding:'4px 8px' }}>Copiază</button>
                </>
              )}
            </small>
          </div>
        )}

        <small style={{color:'#666'}}>În producție vei trimite un email cu linkul de invitație.</small>
      </section>

      {/* Lista colaborări */}
      <section style={{ marginTop: 16, border:'1px solid #eee', borderRadius:8, padding:12 }}>
        <h3>Colaborări</h3>
        {collabsLoading && <div>Se încarcă…</div>}
        {collabsErr && <div style={{color:'crimson'}}>{collabsErr}</div>}
        {!collabsLoading && !collabsErr && (
          collabs.length === 0 ? <div>Nu există companii invitate încă.</div> : (
            <table style={{ width:'100%', marginTop: 8 }}>
              <thead>
                <tr>
                  <th align="left">Denumire</th>
                  <th align="left">CUI</th>
                  <th align="left">Cod</th>
                  <th align="left">Status</th>
                </tr>
              </thead>
              <tbody>
                {collabs.map(c => (
                  <tr key={c.client_company_id}>
                    <td>{c.name ?? '-'}</td>
                    <td>{c.cui}</td>
                    <td><code>{c.company_code ?? '-'}</code></td>
                    <td>{badge(c.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </section>
    </div>
  );
}

function fmtBool(v?: boolean | null) {
  return v === true ? 'Da' : v === false ? 'Nu' : '-';
}

function badge(s: string) {
  const color = s === 'ACTIVE' ? '#0a7' : s === 'PENDING' ? '#d88400' : '#888';
  return <span style={{ background: color, color:'#fff', padding:'2px 8px', borderRadius:999 }}>{s}</span>;
}

async function copyText(text: string) {
  try { await navigator.clipboard.writeText(text); } catch {}
}
