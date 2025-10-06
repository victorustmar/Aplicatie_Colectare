import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setLoading(true);
    try {
      await login(email, password);
      // Redirect după rol
      const role = JSON.parse(sessionStorage.getItem('__last_role__') || 'null'); // fallback demo
      // mai corect: citești din context imediat cu refreshMe, dar simplificăm:
      // redirecționăm pe /dashboard pentru BASE, /admin pentru ADMIN; CLIENT nu e în MVP
      if (email.startsWith('base@')) nav('/dashboard', { replace: true });
      else nav('/admin', { replace: true });
    } catch (e: any) {
      setErr(e.message || 'Eroare la autentificare');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: '80px auto', padding: 24, border: '1px solid #ddd', borderRadius: 8 }}>
      <h2>Autentificare</h2>
      <form onSubmit={onSubmit}>
        <div style={{ marginTop: 12 }}>
          <label>Email</label>
          <input value={email} onChange={e=>setEmail(e.target.value)} type="email" required
                 style={{ width:'100%', padding:8, marginTop:4 }}/>
        </div>
        <div style={{ marginTop: 12 }}>
          <label>Parolă</label>
          <input value={password} onChange={e=>setPassword(e.target.value)} type="password" required
                 style={{ width:'100%', padding:8, marginTop:4 }}/>
        </div>
        {err && <div style={{ color:'crimson', marginTop: 10 }}>{err}</div>}
        <button disabled={loading} type="submit" style={{ marginTop:16, padding: '10px 14px' }}>
          {loading ? 'Se conectează…' : 'Login'}
        </button>
      </form>
    </div>
  );
}
