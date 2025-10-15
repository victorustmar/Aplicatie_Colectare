import React from 'react';
import { Link } from 'react-router-dom';

export default function ProducerHome() {
  return (
    <div style={{ maxWidth: 920, margin: '24px auto', padding: 16 }}>
      <h2>Producător — Acasă</h2>
      <p>De aici poți adăuga un pachet nou sau poți vedea lista de pachete trimise.</p>

      <div style={{ display:'flex', gap:12, marginTop:12 }}>
        <Link to="/producer/add">
          <button>Adaugă pachet</button>
        </Link>
        <Link to="/producer/packages">
          <button>Pachetele mele</button>
        </Link>
      </div>
    </div>
  );
}
