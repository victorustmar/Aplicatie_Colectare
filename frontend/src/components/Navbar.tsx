/* import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth';

type LinkDef = { to: string; label: string };

export default function Navbar() {
  const { user, logout } = useAuth();

  const baseLinks: LinkDef[] = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/collections', label: 'Colectări' },
    { to: '/recyclings', label: 'Reciclări' },            // 👈 listă de reciclari pt. validare (BASE)
    { to: '/invoices', label: 'Facturi' },
    { to: '/billing/profile', label: 'Profil facturare' },
    { to: '/billing/settings', label: 'Setări facturi' },
  ];

  const clientLinks: LinkDef[] = [
    { to: '/client', label: 'Acasă' },
    { to: '/client/add', label: 'Adaugă colectare' },
    { to: '/client/collections', label: 'Colectările mele' },
  ];

  const recyclerLinks: LinkDef[] = [
    { to: '/recycler', label: 'Acasă' },
    { to: '/recycler/add', label: 'Adaugă reciclare' },
    { to: '/recycler/recyclings', label: 'Reciclările mele' },
  ];

  const adminLinks: LinkDef[] = [{ to: '/admin', label: 'Admin' }];

  const links =
    user?.role === 'BASE'     ? baseLinks     :
    user?.role === 'CLIENT'   ? clientLinks   :
    user?.role === 'RECYCLER' ? recyclerLinks :
    user?.role === 'ADMIN'    ? adminLinks    : [];

  return (
    <header style={styles.header}>
      <div style={styles.brand}>App Suite</div>

      <nav style={styles.nav}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            style={({ isActive }) => ({
              ...styles.link,
              ...(isActive ? styles.linkActive : {}),
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>

      <div style={styles.right}>
        <span style={styles.userBadge}>
          {user?.full_name} · {user?.role}
        </span>
        <button onClick={logout} style={styles.logoutBtn}>Logout</button>
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    justifyContent: 'space-between',
    padding: '10px 16px',
    borderBottom: '1px solid #eee',
    position: 'sticky',
    top: 0,
    background: '#fff',
    zIndex: 10,
  },
  brand: { fontWeight: 700 },
  nav: { display: 'flex', gap: 10, flex: 1, marginLeft: 12 },
  link: {
    textDecoration: 'none',
    color: '#333',
    padding: '6px 10px',
    borderRadius: 6,
  },
  linkActive: {
    background: '#eef6ff',
    color: '#0b62d6',
    border: '1px solid #cfe3ff',
  },
  right: { display: 'flex', alignItems: 'center', gap: 10 },
  userBadge: { fontSize: 12, color: '#666' },
  logoutBtn: {
    padding: '6px 10px',
    border: '1px solid #ddd',
    borderRadius: 6,
    background: '#fff',
    cursor: 'pointer',
  },
};
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth';

type LinkDef = { to: string; label: string };

export default function Navbar() {
  const { user, logout } = useAuth();

  const baseLinks: LinkDef[] = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/collections', label: 'Colectări' },  // colector → bază
    { to: '/packages', label: 'Pachete' },       // producător → bază
    { to: '/recyclings', label: 'Reciclări' },   // reciclator → bază
    { to: '/invoices', label: 'Facturi' },
    { to: '/billing/profile', label: 'Profil facturare' },
    { to: '/billing/settings', label: 'Setări facturi' },
  ];

  const producerLinks: LinkDef[] = [
    { to: '/producer', label: 'Acasă' },
    { to: '/producer/add', label: 'Adaugă pachet' },
    { to: '/producer/packages', label: 'Pachetele mele' },
  ];

  const clientLinks: LinkDef[] = [
    { to: '/client', label: 'Acasă' },
    { to: '/client/add', label: 'Adaugă colectare' },
    { to: '/client/collections', label: 'Colectările mele' },
  ];

  const recyclerLinks: LinkDef[] = [
    { to: '/recycler', label: 'Acasă' },
    { to: '/recycler/add', label: 'Adaugă reciclare' },
    { to: '/recycler/recyclings', label: 'Reciclările mele' },
  ];

  const adminLinks: LinkDef[] = [{ to: '/admin', label: 'Admin' }];



;

const collectorLinks: LinkDef[] = [
  { to: '/collector', label: 'Acasă' },
  { to: '/collector/add', label: 'Adaugă colectare' },
  { to: '/collector/collections', label: 'Colectările mele' },
];

const links =
  user?.role === 'BASE'      ? baseLinks      :
  user?.role === 'CLIENT'    ? clientLinks    :
  user?.role === 'PRODUCER'  ? clientLinks    : // if Producer still uses client pages for now
  user?.role === 'RECYCLER'  ? recyclerLinks  :
  user?.role === 'COLLECTOR' ? collectorLinks :
  user?.role === 'ADMIN'     ? adminLinks     : [];


  return (
    <header style={styles.header}>
      <div style={styles.brand}>App Suite</div>

      <nav style={styles.nav}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            style={({ isActive }) => ({
              ...styles.link,
              ...(isActive ? styles.linkActive : {}),
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>

      <div style={styles.right}>
        <span style={styles.userBadge}>
          {user?.full_name} · {user?.role}
        </span>
        <button onClick={logout} style={styles.logoutBtn}>Logout</button>
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    justifyContent: 'space-between',
    padding: '10px 16px',
    borderBottom: '1px solid #eee',
    position: 'sticky',
    top: 0,
    background: '#fff',
    zIndex: 10,
  },
  brand: { fontWeight: 700 },
  nav: { display: 'flex', gap: 10, flex: 1, marginLeft: 12 },
  link: {
    textDecoration: 'none',
    color: '#333',
    padding: '6px 10px',
    borderRadius: 6,
  },
  linkActive: {
    background: '#eef6ff',
    color: '#0b62d6',
    border: '1px solid #cfe3ff',
  },
  right: { display: 'flex', alignItems: 'center', gap: 10 },
  userBadge: { fontSize: 12, color: '#666' },
  logoutBtn: {
    padding: '6px 10px',
    border: '1px solid #ddd',
    borderRadius: 6,
    background: '#fff',
    cursor: 'pointer',
  },
};
