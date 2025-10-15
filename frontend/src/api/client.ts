import type {
  InviteOut,
  CollectionCreate,
  CollectionOut,
  InvoiceOut,
  BillingProfile,
  BillingProfileUpdate,
  InvoiceSettings,
  InvoiceSettingsUpdate,
  LoginOut,
  CollaborationOut,
  // NEW:
  RecyclingCreate, RecyclingOut,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

type AcceptInvitePayload = {
  token: string;
  password: string;
  full_name: string;
  phone?: string;
};

export type PartnerRole = 'CLIENT' | 'RECYCLER' | 'PRODUCER' | 'COLLECTOR';




type InvitePartnerIn = {
  email: string;
  target_role: PartnerRole;
  cui?: string;
  company_name?: string;
  expires_in_days?: number;
};

export function getToken(): string | null {
  return localStorage.getItem('access_token');
}
export function setToken(t: string) {
  localStorage.setItem('access_token', t);
}
export function clearToken() {
  localStorage.removeItem('access_token');
}

export type ApiError = Error & { status?: number; data?: any };
export type BatteryLine = { pcs?: number; weight_kg?: number; price_ron?: number };

type PackageCreate = {
  producer_company_id: string;
  batteries: Record<string, BatteryLine>;
};
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');

  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // non-JSON response
  }

  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`;
    const err: ApiError = Object.assign(new Error(msg), { status: res.status, data });
    throw err;
  }
  return data as T;
}

export const api = {
  // AUTH
  login: (email: string, password: string) =>
    request<LoginOut>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<import('../types/api').User>('/auth/me'),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),

  // ANAF
  anafLookup: (cui: string) =>
    request<import('../types/api').AnafSummary>('/anaf/lookup', {
      method: 'POST',
      body: JSON.stringify({ cui }),
    }),

  // ----------------------------
  // INVITES (new, supports roles)
  // ----------------------------
  invitePartner: (payload: {
    email: string;
    target_role: PartnerRole;               // 'CLIENT' | 'RECYCLER' | 'PRODUCER'
    cui?: string;
    company_name?: string;
    expires_in_days?: number;               // optional (default server-side 14)
  }) =>
    request<InviteOut>('/invites', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Backward compatibility: keep the previous signature and route it to /invites with target_role='CLIENT'
  inviteCompany: (cui: string, email: string) =>
    request<InviteOut>('/invites', {
      method: 'POST',
      body: JSON.stringify({ cui, email, target_role: 'CLIENT' as PartnerRole }),
    }),

  // Companies list (collaborations view / relationships view)
  listCompanies: () => request<CollaborationOut[]>('/companies'),

  // ACCEPT INVITE
  acceptInvite: (payload: AcceptInvitePayload) =>
    request<LoginOut>('/invites/accept', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // COLLECTIONS
  createCollection: (payload: CollectionCreate) =>
    request<CollectionOut>('/collections', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listCollections: () => request<CollectionOut[]>('/collections'),

  getCollection: (id: string) => request<CollectionOut>(`/collections/${id}`),

  validateCollection: (collectionId: string) =>
    request<CollectionOut>(`/collections/${collectionId}/validate`, { method: 'POST' }),

  // INVOICES
  listInvoices: () => request<InvoiceOut[]>('/invoices'),

  downloadInvoicePdf: async (invoiceId: string): Promise<void> => {
    const token = getToken();
    const res = await fetch(`${BASE_URL}/invoices/${invoiceId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      let detail = '';
      try {
        const t = await res.text();
        detail = t ? (JSON.parse(t)?.detail || '') : '';
      } catch {}
      const err: ApiError = Object.assign(new Error(detail || `HTTP ${res.status}`), {
        status: res.status,
      });
      throw err;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `invoice-${invoiceId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  // BILLING
  getBillingProfile: () => request<BillingProfile>('/billing/profile'),

  updateBillingProfile: (p: BillingProfileUpdate) =>
    request<BillingProfile>('/billing/profile', {
      method: 'PUT',
      body: JSON.stringify(p),
    }),

  getInvoiceSettings: () => request<InvoiceSettings>('/billing/settings'),

  updateInvoiceSettings: (p: InvoiceSettingsUpdate) =>
    request<InvoiceSettings>('/billing/settings', {
      method: 'PUT',
      body: JSON.stringify(p),
    }),
    // RECYCLINGS (Recycler + Base)
  


  // RECYCLER
  createRecycling: (payload: RecyclingCreate) =>
    request<RecyclingOut>('/recyclings', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),


  // src/api/client.ts


// types: addă-ți RecyclingOut / RecyclingCreate în ../types/api

listRecyclings: () => request<import('../types/api').RecyclingOut[]>('/recyclings'),

getRecycling: (id: string) =>
  request<import('../types/api').RecyclingOut>(`/recyclings/${id}`),

validateRecycling: (id: string) =>
  request<import('../types/api').RecyclingOut>(`/recyclings/${id}/validate`, { method: 'POST' }),

  createPackage: (p: PackageCreate) =>
    request<{ ok: boolean; package_id: string }>('/packages', {
      method: 'POST',
      body: JSON.stringify(p),
    }),

  listPackages: () =>
    request<any[]>('/packages'),

  getPackage: (id: string) =>
    request<any>(`/packages/${id}`),

  validatePackage: (id: string) =>
    request<any>(`/packages/${id}/validate`, { method: 'POST' }),

};
