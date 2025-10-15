

import CollectorAddCollection from './pages/CollectorAddCollection';
import CollectorCollections from './pages/CollectorCollections';


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
import BaseCollectionReview from './pages/BaseCollectionReview';
import Layout from './components/Layout';

// 👇 NEW imports for the recycler feature
import BaseRecyclings from './pages/BaseRecyclings';
import BaseRecyclingReview from './pages/BaseRecyclingReview';
import RecyclerAddRecycling from './pages/RecyclerAddRecycling';
import RecyclerRecyclings from './pages/RecyclerRecyclings';


import ProducerHome from './pages/ProducerHome';
import ProducerAddPackage from './pages/ProducerAddPackage';
import ProducerPackages from './pages/ProducerPackages';
import BasePackages from './pages/BasePackages';
import BasePackageReview from './pages/BasePackageReview';

export default function App() {
  const { user } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();

  // Redirect after login, by role
/*   useEffect(() => {
    if (!user) return;
    if (loc.pathname === '/' || loc.pathname === '/login') {
      if (user.role === 'BASE') nav('/dashboard', { replace: true });
      else if (user.role === 'CLIENT') nav('/client', { replace: true });
      else if (user.role === 'RECYCLER') nav('/recycler/add', { replace: true });
      else if (user.role === 'PRODUCER') nav('/producer', { replace: true }); // simple placeholder route below
      else nav('/admin', { replace: true });
    }
  }, [user, loc.pathname, nav]); */
// App.tsx (inside component)
useEffect(() => {
  if (!user) return;
  if (loc.pathname === '/' || loc.pathname === '/login') {
    switch (user.role) {
      case 'BASE':
        nav('/dashboard', { replace: true });
        break;
      case 'PRODUCER':
        nav('/producer', { replace: true });
        break;
      case 'COLLECTOR':
        nav('/collector', { replace: true });
        break;
      case 'RECYCLER':
        nav('/recycler', { replace: true });
        break;
      case 'ADMIN':
        nav('/admin', { replace: true });
        break;
      default:
        // Unknown role → keep them on login (don’t bounce)
        nav('/login', { replace: true });
    }
  }
}, [user?.role, loc.pathname, nav]);

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/invite/:token" element={<InviteAccept />} />
      <Route path="/" element={<Navigate to="/login" replace />} />

{/* COLLECTOR */}
 <Route element={<RequireAuth allow={['COLLECTOR']} />}>
  <Route element={<Layout />}>
  <Route path="/collector/ping" element={<div>collector block mounted</div>} />
    <Route path="/collector" element={<Navigate to="/collector/add" replace />} />
    <Route path="/collector/add" element={<CollectorAddCollection />} />
    <Route path="/collector/collections" element={<CollectorCollections />} />
  </Route>
</Route> 

      {/* BASE */}
      <Route element={<RequireAuth allow={['BASE']} />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/collections" element={<BaseCollections />} />
          <Route path="/collections/:id/review" element={<BaseCollectionReview />} />
          <Route path="/recyclings" element={<BaseRecyclings />} />                {/* NEW */}
          <Route path="/recyclings/:id/review" element={<BaseRecyclingReview />} />{/* NEW */}
          <Route path="/packages" element={<BasePackages />} />
    <Route path="/packages/:id/review" element={<BasePackageReview />} />
          <Route path="/invoices" element={<BaseInvoices />} />
          <Route path="/billing/profile" element={<BillingProfilePage />} />
          <Route path="/billing/settings" element={<BillingSettingsPage />} />
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

      {/* RECYCLER */}
      <Route element={<RequireAuth allow={['RECYCLER']} />}>
        <Route element={<Layout />}>
          <Route path="/recycler" element={<Navigate to="/recycler/recyclings" replace />} />
          <Route path="/recycler/add" element={<RecyclerAddRecycling />} />
          <Route path="/recycler/recyclings" element={<RecyclerRecyclings />} />
        </Route>
      </Route>


      {/* ADMIN */}
      <Route element={<RequireAuth allow={['ADMIN']} />}>
        <Route element={<Layout />}>
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Route>

      {/* PRODUCER */}
      <Route element={<RequireAuth allow={['PRODUCER']} />}>
  <Route element={<Layout />}>
    <Route path="/producer" element={<ProducerHome />} />
    <Route path="/producer/add" element={<ProducerAddPackage />} />
    <Route path="/producer/packages" element={<ProducerPackages />} />
  </Route>
</Route>

      {/* 404 */}
      <Route path="*" element={<div style={{ padding: 24 }}>404</div>} />
    </Routes>
  );
}
