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
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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
    // non-JSON
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

  // COMPANIES / INVITES
  inviteCompany: (cui: string, email: string) =>
    request<InviteOut>('/companies/invite', {
      method: 'POST',
      body: JSON.stringify({ cui, email }),
    }),

  listCompanies: () => request<CollaborationOut[]>('/companies'),

  acceptInvite: (token: string, password: string, full_name: string) =>
    request<LoginOut>('/invites/accept', {
      method: 'POST',
      body: JSON.stringify({ token, password, full_name }),
    }),

  // COLLECTIONS
  createCollection: (payload: CollectionCreate) =>
    request<CollectionOut>('/collections', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listCollections: () => request<CollectionOut[]>('/collections'),

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
};
