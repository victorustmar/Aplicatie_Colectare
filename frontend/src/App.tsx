import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { RequireAuth } from './components/RequireAuth';
import { useAuth } from './auth';


import Login from './pages/Login';
import InviteAccept from './pages/InviteAcceptPage';

import Dashboard from './pages/Dashboard';
import Admin from './pages/Admin';
import ClientHome from './pages/ClientHome';
import ClientAddCollection from './pages/ClientAddCollection';
import ClientCollections from './pages/ClientCollections';
import BaseCollections from './pages/BaseCollections';
import BaseInvoices from './pages/BaseInvoices';
import BillingProfilePage from './pages/BillingProfile';
import BillingSettingsPage from './pages/BillingSettings';
import BaseCollectionReview from "./pages/BaseCollectionReview";
import Layout from './components/Layout';

export default function App() {
  const { user } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();

  // Redirect după login, în funcție de rol
  useEffect(() => {
    if (!user) return;
    if (loc.pathname === '/' || loc.pathname === '/login') {
      if (user.role === 'BASE') nav('/dashboard', { replace: true });
      else if (user.role === 'CLIENT') nav('/client', { replace: true });
      else nav('/admin', { replace: true });
    }
  }, [user, loc.pathname, nav]);

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/invite/:token" element={<InviteAccept />} />
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* BASE */}
      <Route element={<RequireAuth allow={['BASE']} />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/collections" element={<BaseCollections />} />
          <Route path="/invoices" element={<BaseInvoices />} />
          <Route path="/billing/profile" element={<BillingProfilePage />} />
          <Route path="/billing/settings" element={<BillingSettingsPage />} />
          <Route path="/collections/:id/review" element={<BaseCollectionReview />} />
        </Route>
      </Route>

      {/* CLIENT */}
      <Route element={<RequireAuth allow={['CLIENT']} />}>
        <Route element={<Layout />}>
          <Route path="/client" element={<ClientHome />} />
          <Route path="/client/add" element={<ClientAddCollection />} />
          <Route path="/client/collections" element={<ClientCollections />} />
        </Route>
      </Route>

      {/* ADMIN */}
      <Route element={<RequireAuth allow={['ADMIN']} />}>
        <Route element={<Layout />}>
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Route>

      {/* 404 */}
      <Route path="*" element={<div style={{ padding: 24 }}>404</div>} />
    </Routes>
  );
}
