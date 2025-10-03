import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, setToken } from '../api/client';
import { useAuth } from '../auth';

function InviteAccept() {
  const { token } = useParams<{ token: string }>();
  const nav = useNavigate();
  const { refreshMe } = useAuth();

  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) { setErr('Lipsește token-ul'); return; }
    setErr(null); setLoading(true);
    try {
      const res = await api.acceptInvite(token, password, fullName || 'Utilizator');
      setToken(res.access_token);
      await refreshMe();
      nav('/client', { replace: true });
    } catch (e: any) {
      setErr(e.message || 'Eroare la acceptarea invitației');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin:'80px auto', padding: 24, border:'1px solid #ddd', borderRadius:8 }}>
      <h2>Acceptă invitația</h2>
      <p style={{color:'#666', marginTop:8}}>Setează-ți numele și parola pentru a-ți activa contul.</p>
      <form onSubmit={submit}>
        <div style={{ marginTop: 12 }}>
          <label>Nume complet</label>
          <input value={fullName} onChange={e=>setFullName(e.target.value)}
                 style={{ width:'100%', padding:8, marginTop:4 }}/>
        </div>
        <div style={{ marginTop: 12 }}>
          <label>Parolă</label>
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required
                 style={{ width:'100%', padding:8, marginTop:4 }}/>
        </div>
        {err && <div style={{ color:'crimson', marginTop: 10 }}>{err}</div>}
        <button disabled={loading} type="submit" style={{ marginTop:16, padding:'10px 14px' }}>
          {loading ? 'Se activează…' : 'Activează contul'}
        </button>
      </form>
    </div>
  );
}

export default InviteAccept;
