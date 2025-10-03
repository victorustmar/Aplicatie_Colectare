import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <main style={{ padding: 16, maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </main>
    </div>
  );
}
