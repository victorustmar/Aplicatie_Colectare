
export type PartnerRole = 'CLIENT' | 'RECYCLER' | 'PRODUCER' | 'COLLECTOR'| 'PRODUCER_2';
// src/types/api.ts
export type Role = 'ADMIN' | 'BASE' | 'PRODUCER' | 'COLLECTOR' | 'RECYCLER';


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

/* =========================
   Collections
   ========================= */

export type CollectionStatus = 'PENDING' | 'VALIDATED';


export interface CollectionCreate {
  /** Doar bateriile; serverul sumează greutatea și costul total */
  batteries: Record<string, BatteryLine>;
}

export interface CollectionOut {
  collection_id: string;
  client_company_id: string;
  client_name?: string;
  status: CollectionStatus;

  /** Harta tip -> { pcs, weight_kg, price_ron } */
  batteries: Record<string, BatteryLine>;

  /** Sume totale (kg și lei) – pot veni ca string din DECIMAL */
  total_weight?: number | string | null;
  total_cost?: number | string | null;

  /** Rezumat prietenos pentru listări */
  batteries_summary?: string | null;

  created_at: string;
  validated_at?: string | null;
}

/* =========================
   Invoices
   ========================= */

export interface InvoiceItemOut {
  item_id: string;
  line_no: number;
  description: string;
  /** Poate veni ca string din DECIMAL */
  qty: number | string;
  unit: string;
  unit_price: number | string;
  line_total: number | string;
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
  vat_rate: number | string;
  subtotal: number | string;
  vat_amount: number | string;
  total: number | string;
  status: string;
  created_at: string;
  items: InvoiceItemOut[];
  pdf_path?: string | null;
}

/* =========================
   Billing
   ========================= */

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

/* =========================
   Companies / Collaborations
   ========================= */

export type CollaborationStatus = 'PENDING' | 'ACTIVE' | 'REJECTED';

export interface CollaborationOut {
  client_company_id: string;
  cui: string;
  name: string | null;
  status: CollaborationStatus;
  company_code?: string | null;
}

export interface InviteCreateIn {
  email: string;
  target_role: PartnerRole;
  cui?: string;
  company_name?: string;
}

// src/types/api.ts
// ⬇️ Add these (or update if they already exist)



export type RecyclingCreate = {
  batteries: Record<string, BatteryLine>;
};

export type RecyclingOut = {
  recycling_id: string;
  recycler_company_id: string;
  status: 'PENDING' | 'VALIDATED';
  batteries: Record<string, BatteryLine | number>; // compatibility with older rows
  total_weight?: number | string | null;
  total_cost?: number | string | null;
  created_at: string;
  validated_at?: string | null;
  batteries_summary?: string | null; // server-side pretty summary (optional)
};

// --- extinde rolurile ---
//export type Role = 'ADMIN' | 'BASE' | 'CLIENT' | 'RECYCLER' | 'PRODUCER';

// --- tipuri reutilizate ---
export type BatteryLine = { pcs?: number; weight_kg?: number; price_ron?: number };

// =========================
// Packages (PRODUCER ↔ BASE)
// =========================
export type PackageStatus = 'PENDING' | 'VALIDATED';

export interface PackageOut {
  package_id: string;
  producer_company_id: string;
  producer_name?: string | null;

  status: PackageStatus;

  batteries: Record<string, BatteryLine>;
  batteries_summary?: string | null;

  total_weight?: number | string | null;
  total_cost?: number | string | null;

  created_at: string;
  validated_at?: string | null;
}




