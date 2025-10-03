import { useAuth } from '../auth';

export default function ClientHome() {
  const { logout } = useAuth();
  return (
    <div style={{ maxWidth: 900, margin:'32px auto', padding:16 }}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h2>Workspace Client</h2>
        <button onClick={logout}>Logout</button>
      </div>
      <p>Bun venit! Aici vor apărea colectările și facturile (viitoare sprint-uri).</p>
    </div>
  );
}
