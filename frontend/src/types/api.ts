export type Role = 'ADMIN' | 'BASE' | 'CLIENT';

export interface User {
  user_id: string;
  role: Role;
  company_id?: string | null;
  full_name: string;
  company_name?: string | null;
}

export interface LoginIn {
  email: string;
  password: string;
}

export interface LoginOut {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export interface AnafSummary {
  cui?: string | null;
  denumire?: string | null;
  address?: string | null;   // NEW
  phone?: string | null;     // NEW
  vat_payer?: boolean | null;
  vat_cash?: boolean | null;
  inactive?: boolean | null;
  e_invoice?: boolean | null;
  raw?: any;
}

export interface InviteOut {
  token: string;
  invite_url: string;
  company: {
    company_id: string;
    cui: string;
    name?: string | null;
    company_code?: string | null;
  };
}

// Collections
export type CollectionStatus = "PENDING" | "VALIDATED";

export interface CollectionCreate {
  batteries: Record<string, number>;
  total_weight?: number | null;
  total_cost?: number | null;
}

export interface CollectionOut {
  collection_id: string;
  client_company_id: string;
  status: CollectionStatus;
  batteries: Record<string, number>;
  total_weight?: number | null;
  total_cost?: number | null;
  created_at: string;
  validated_at?: string | null;
}

// Invoices
export interface InvoiceItemOut {
  item_id: string;
  line_no: number;
  description: string;
  qty: number;
  unit: string;
  unit_price: number;
  line_total: number;
}

export interface InvoiceOut {
  invoice_id: string;
  base_company_id: string;
  client_company_id: string;
  collection_id?: string | null;
  invoice_number: string;
  issue_date: string; // yyyy-mm-dd
  due_date: string;   // yyyy-mm-dd
  currency: string;
  vat_rate: number;
  subtotal: number;
  vat_amount: number;
  total: number;
  status: string;
  created_at: string;
  items: InvoiceItemOut[];
  pdf_path?: string | null;
}

// Billing
export interface BillingProfile {
  company_id: string;
  legal_name: string;
  cui: string;
  reg_com?: string | null;
  address_line?: string | null;
  city?: string | null;
  county?: string | null;
  postal_code?: string | null;
  country: string;
  bank_name?: string | null;
  iban?: string | null;
  email_billing?: string | null;
  phone_billing?: string | null;
  vat_payer?: boolean | null;
  vat_cash?: boolean | null;
  e_invoice?: boolean | null;
  updated_from_anaf_at?: string | null;
  source: string;
}

export interface BillingProfileUpdate {
  legal_name?: string;
  reg_com?: string;
  address_line?: string;
  city?: string;
  county?: string;
  postal_code?: string;
  country?: string;
  bank_name?: string;
  iban?: string;
  email_billing?: string;
  phone_billing?: string;
}

export interface InvoiceSettings {
  base_company_id: string;
  series_code: string;
  next_number: number;
  year_reset: boolean;
  due_days: number;
  default_vat_rate: number;
}

export interface InvoiceSettingsUpdate {
  series_code?: string;
  year_reset?: boolean;
  due_days?: number;
  default_vat_rate?: number;
  next_number?: number;
}

// Companies / Collaborations
// --- Collaborations (BASE <-> CLIENT) ---
export type CollaborationStatus = 'PENDING' | 'ACTIVE' | 'REJECTED';

export interface CollaborationOut {
  client_company_id: string;
  cui: string;
  name: string | null;
  status: CollaborationStatus;
  company_code?: string | null;
}



