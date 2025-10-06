import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, setToken, clearToken } from '../api/client';  // <-- add clearToken
import { useAuth } from '../auth';

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const { refreshMe } = useAuth();                           // <-- use auth refresh
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (!token) { setErr('Token lipsă'); return; }
    if (!phone.trim()) { setErr('Te rugăm să introduci numărul de telefon.'); return; }

    setLoading(true);
    try {
      // 1) drop any existing BASE token
      clearToken();

      // 2) accept invite (API MUST return { access_token, user })
      const res = await api.acceptInvite({
        token,
        password,
        full_name: fullName,
        phone: phone.trim(),
      });

      // 3) install new CLIENT token and refresh identity
      setToken(res.access_token);
      await refreshMe();

      // 4) hard redirect so every provider/axios sees the new token
      window.location.replace('/'); // or '/client' if you have a client home
    } catch (e: any) {
      setErr(e.message || 'Eroare la acceptarea invitației');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{maxWidth: 460, margin: '40px auto'}}>
      <h2>Acceptă invitația</h2>
      <form onSubmit={onSubmit} style={{display:'grid', gap:12, marginTop:16}}>
        <label>
          Nume complet
          </label>
          <input value={fullName} onChange={e=>setFullName(e.target.value)} required />
        
        <label>
          Număr de telefon
         </label>
          <input value={phone} onChange={e=>setPhone(e.target.value)} type="tel" required />
        
        <label>
          Parolă
           </label>
           <input value={password} onChange={e=>setPassword(e.target.value)} type="password" required />
       
        {err && <div style={{color:'crimson'}}>{err}</div>}
        <button disabled={loading} type="submit">
          {loading ? 'Se procesează…' : 'Creează cont'}
        </button>
      </form>
    </div>
  );
}
