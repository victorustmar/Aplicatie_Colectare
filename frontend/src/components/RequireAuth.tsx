// import React from 'react';
// import { Navigate, Outlet, useLocation } from 'react-router-dom';
// import { useAuth } from '../auth';
// import type { Role } from '../types/api';

// export const RequireAuth: React.FC<{ allow?: Role[] }> = ({ allow }) => {
//   const { user, loading } = useAuth();
//   if (loading) return <div style={{ padding: 24 }}>Se încarcă…</div>;
//   if (!user) return <Navigate to="/login" replace />;

//   if (allow && !allow.includes(user.role)) {
//     // role mismatch → du-l pe root potrivit rolului
//     return <Navigate to={user.role === 'BASE' ? '/dashboard' : '/admin'} replace />;
//   }
//   return <Outlet />;
// };

import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

export function RequireAuth({ allow }: { allow?: string[] }) {
  const { user, loading } = useAuth();
  const loc = useLocation();

  if (loading) return <div style={{padding:24}}>Se încarcă…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />;
  if (allow && !allow.includes(user.role)) return <Navigate to="/login" replace />;
  return <Outlet />;
}
