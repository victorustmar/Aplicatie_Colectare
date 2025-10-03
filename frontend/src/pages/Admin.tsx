import React from 'react';
import { useAuth } from '../auth';

export default function Admin() {
const { logout } = useAuth();
   return (
    <div style={{ maxWidth: 900, margin:'32px auto', padding:16 }}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h2>Admin</h2>
        <button onClick={logout}>Logout</button>
      </div>
      <p>Placeholder pentru azi...</p>
    </div>
  );
}
